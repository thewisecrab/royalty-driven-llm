"""Escrow resolution and post-dispute settlement reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import canonical_json, sign_payload
from rdllm.text import stable_hash

SETTLEMENT_VERSION = "rdllm-escrow-resolution/v1"
MONEY_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class PayoutSplit:
    creator_id: str
    work_id: str
    weight: Decimal

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PayoutSplit":
        return cls(
            creator_id=data["creator_id"],
            work_id=data.get("work_id", ""),
            weight=Decimal(str(data["weight"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "work_id": self.work_id,
            "weight": str(self.weight),
        }


@dataclass(frozen=True)
class DisputeResolution:
    resolution_id: str
    conflict_id: str
    registry_report_hash: str
    resolved_at: str
    resolver: str
    reason: str
    payout_splits: tuple[PayoutSplit, ...]
    evidence_uri: str = ""
    evidence_hash: str = ""
    signature: str = ""
    status: str = "resolved"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DisputeResolution":
        splits = data.get("payout_splits", [])
        if not splits and data.get("winning_creator_id"):
            splits = [
                {
                    "creator_id": data["winning_creator_id"],
                    "work_id": data.get("winning_work_id", ""),
                    "weight": "1",
                }
            ]
        return cls(
            resolution_id=data["resolution_id"],
            conflict_id=data["conflict_id"],
            registry_report_hash=data["registry_report_hash"],
            resolved_at=data.get("resolved_at", ""),
            resolver=data.get("resolver", ""),
            reason=data.get("reason", ""),
            payout_splits=tuple(PayoutSplit.from_dict(item) for item in splits),
            evidence_uri=data.get("evidence_uri", ""),
            evidence_hash=data.get("evidence_hash", ""),
            signature=data.get("signature", ""),
            status=data.get("status", "resolved"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "resolution_id": self.resolution_id,
            "conflict_id": self.conflict_id,
            "registry_report_hash": self.registry_report_hash,
            "resolved_at": self.resolved_at,
            "resolver": self.resolver,
            "reason": self.reason,
            "evidence_uri": self.evidence_uri,
            "evidence_hash": self.evidence_hash,
            "signature": self.signature,
            "status": self.status,
            "payout_splits": [split.to_dict() for split in self.payout_splits],
        }
        if len(self.payout_splits) == 1:
            split = self.payout_splits[0]
            payload["winning_creator_id"] = split.creator_id
            payload["winning_work_id"] = split.work_id
        return payload


def load_resolution(path: str | Path) -> DisputeResolution:
    return DisputeResolution.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def resolve_registry_escrow(
    ledger_data: dict[str, Any],
    resolution: DisputeResolution,
    *,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Release registry-dispute escrow without rewriting the original ledger."""

    events = [UsageEvent.from_dict(item) for item in ledger_data.get("events", [])]
    balances_before = _balances_from_events(events)
    release_balances: dict[str, Decimal] = {}
    releases: list[dict[str, Any]] = []
    errors = _validate_resolution(resolution)

    for event in events:
        if not _event_has_conflict(event, resolution):
            continue
        escrow_shares = [
            share
            for share in event.royalty_shares
            if share.creator_id == "registry_dispute_escrow"
            and share.chunk_id == "escrow:registry_dispute"
        ]
        if not escrow_shares:
            errors.append(f"event {event.event_id} has conflict but no registry escrow share")
            continue
        for share in escrow_shares:
            event_releases = _release_share(event, share.payout, resolution)
            releases.extend(event_releases)
            for release in event_releases:
                release_balances[release["creator_id"]] = (
                    release_balances.get(release["creator_id"], Decimal("0"))
                    + Decimal(release["payout"])
                )

    if not releases:
        errors.append("no registry-dispute escrow shares matched the resolution")

    balances_after = dict(balances_before)
    total_released = sum(
        (Decimal(release["payout"]) for release in releases), Decimal("0")
    )
    if total_released:
        balances_after["registry_dispute_escrow"] = (
            balances_after.get("registry_dispute_escrow", Decimal("0")) - total_released
        )
        for creator_id, payout in release_balances.items():
            balances_after[creator_id] = balances_after.get(creator_id, Decimal("0")) + payout
    balances_after = {
        creator_id: balance
        for creator_id, balance in balances_after.items()
        if balance != Decimal("0")
    }

    report: dict[str, Any] = {
        "settlement_version": SETTLEMENT_VERSION,
        "status": "ok" if not errors else "failed",
        "resolution": resolution.to_dict(),
        "source_ledger_hash": stable_hash(canonical_json(ledger_data)),
        "summary": {
            "matched_event_count": len({release["event_id"] for release in releases}),
            "release_count": len(releases),
            "total_released": str(_quantize(total_released)),
            "creator_count": len(release_balances),
        },
        "balances_before": _decimal_map(balances_before),
        "release_balances": _decimal_map(release_balances),
        "balances_after": _decimal_map(balances_after),
        "releases": releases,
        "errors": errors,
    }
    report["report_hash"] = stable_hash(canonical_json(_hashable_report(report)))
    report["signature"] = _signature(report, signing_secret)
    return report


def verify_escrow_resolution(
    ledger_data: dict[str, Any],
    settlement_report: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if settlement_report.get("settlement_version") != SETTLEMENT_VERSION:
        errors.append("settlement version is unsupported")
        return errors

    actual_hash = stable_hash(canonical_json(_hashable_report(settlement_report)))
    if actual_hash != settlement_report.get("report_hash"):
        errors.append("settlement report hash is not reproducible")

    resolution = DisputeResolution.from_dict(settlement_report.get("resolution", {}))
    expected = resolve_registry_escrow(ledger_data, resolution)
    if expected.get("report_hash") != settlement_report.get("report_hash"):
        errors.append("settlement report hash does not match ledger and resolution")
    for key in ("summary", "balances_before", "release_balances", "balances_after", "releases"):
        if expected.get(key) != settlement_report.get(key):
            errors.append(f"settlement {key} does not match recomputed report")

    if signing_secret:
        signature = settlement_report.get("signature", {})
        expected_signature = sign_payload(_signature_payload(settlement_report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("settlement report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("settlement signature is invalid")
    return errors


def _validate_resolution(resolution: DisputeResolution) -> list[str]:
    errors: list[str] = []
    if resolution.status != "resolved":
        errors.append("resolution status is not resolved")
    if not resolution.conflict_id:
        errors.append("resolution conflict_id is missing")
    if not resolution.registry_report_hash:
        errors.append("resolution registry_report_hash is missing")
    if not resolution.payout_splits:
        errors.append("resolution has no payout splits")
    weight_total = sum((split.weight for split in resolution.payout_splits), Decimal("0"))
    if resolution.payout_splits and weight_total != Decimal("1"):
        errors.append(f"resolution payout split weights sum to {weight_total}, not 1")
    return errors


def _event_has_conflict(event: UsageEvent, resolution: DisputeResolution) -> bool:
    if event.grounding_report.get("registry_report_hash") != resolution.registry_report_hash:
        return False
    return any(
        decision.get("conflict_id") == resolution.conflict_id
        for decision in event.registry_decisions
    )


def _release_share(
    event: UsageEvent,
    escrow_payout: Decimal,
    resolution: DisputeResolution,
) -> list[dict[str, Any]]:
    releases: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    for index, split in enumerate(resolution.payout_splits):
        if index == len(resolution.payout_splits) - 1:
            payout = _quantize(escrow_payout - paid_so_far)
        else:
            payout = _quantize(escrow_payout * split.weight)
            paid_so_far += payout
        seed = {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "resolution_id": resolution.resolution_id,
            "conflict_id": resolution.conflict_id,
            "creator_id": split.creator_id,
            "work_id": split.work_id,
            "payout": str(payout),
        }
        releases.append(
            {
                "release_id": f"rel_{stable_hash(canonical_json(seed))[:16]}",
                "event_id": event.event_id,
                "event_hash": event.event_hash,
                "resolution_id": resolution.resolution_id,
                "conflict_id": resolution.conflict_id,
                "registry_report_hash": resolution.registry_report_hash,
                "creator_id": split.creator_id,
                "work_id": split.work_id,
                "split_weight": str(split.weight),
                "payout": str(payout),
                "source_escrow_account": "registry_dispute_escrow",
            }
        )
    return releases


def _balances_from_events(events: list[UsageEvent]) -> dict[str, Decimal]:
    balances: dict[str, Decimal] = {}
    for event in events:
        for share in event.royalty_shares:
            balances[share.creator_id] = balances.get(share.creator_id, Decimal("0")) + share.payout
    return dict(sorted(balances.items()))


def _decimal_map(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: str(_quantize(value)) for key, value in sorted(values.items())}


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _signature_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "signature"}


def _signature(report: dict[str, Any], signing_secret: str | None) -> dict[str, str]:
    if not signing_secret:
        return {"algorithm": "UNSIGNED", "value": ""}
    return {
        "algorithm": "HMAC-SHA256",
        "value": sign_payload(_signature_payload(report), signing_secret),
    }
