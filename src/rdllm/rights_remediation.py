"""Post-publication rights remediation reports for changing creator consent."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import UsageEvent, Work
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

RIGHTS_REMEDIATION_VERSION = "rdllm-rights-remediation/v1"
RIGHTS_REMEDIATION_POLICY_VERSION = "rdllm-rights-remediation-policy/v1"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
MONEY_QUANT = Decimal("0.000001")

REMEDIATION_USES = (
    "training",
    "retrieval",
    "generation",
    "external_attribution",
    "display",
    "quote",
)


def load_ledger(path: str | Path) -> dict[str, Any]:
    """Load a private RDLLM ledger for remediation replay."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _work_content_hash(work: Work | None) -> str:
    return stable_hash(work.content) if work else ""


def _policy_record(work: Work | None) -> dict[str, Any]:
    if work is None:
        return {"state": "absent"}
    return {
        "state": "registered",
        "work_id": work.work_id,
        "creator_id": work.creator_id,
        "title": work.title,
        "source_uri": work.source_uri or f"registered://works/{work.work_id}",
        "content_hash": _work_content_hash(work),
        "policy_id": work.policy_id or f"policy:{work.work_id}",
        "license": work.license,
        "license_uri": work.license_uri,
        "allowed_uses": sorted(work.allowed_uses),
        "prohibited_uses": sorted(work.prohibited_uses),
        "jurisdictions": sorted(work.jurisdictions),
        "requires_attribution": work.requires_attribution,
        "requires_royalty": work.requires_royalty,
        "minimum_creator_pool_rate": round(work.minimum_creator_pool_rate, 8),
        "revoked": work.revoked,
        "revoked_at": work.revoked_at,
        "derived_from": sorted(
            work.derived_from,
            key=lambda item: (
                str(item.get("work_id", "")),
                str(item.get("relation", "")),
                str(item.get("source_uri", "")),
            ),
        ),
    }


def _policy_hash(work: Work | None) -> str:
    return hash_payload(_policy_record(work))


def _change_reasons(previous: Work | None, updated: Work | None) -> list[str]:
    if previous is None and updated is None:
        return []
    if previous is None:
        return ["work_added"]
    if updated is None:
        return ["work_removed_from_current_registry"]

    checks = (
        ("content_hash_changed", _work_content_hash(previous), _work_content_hash(updated)),
        ("policy_id_changed", previous.policy_id, updated.policy_id),
        ("license_changed", previous.license, updated.license),
        ("license_uri_changed", previous.license_uri, updated.license_uri),
        ("allowed_uses_changed", sorted(previous.allowed_uses), sorted(updated.allowed_uses)),
        (
            "prohibited_uses_changed",
            sorted(previous.prohibited_uses),
            sorted(updated.prohibited_uses),
        ),
        ("jurisdictions_changed", sorted(previous.jurisdictions), sorted(updated.jurisdictions)),
        ("requires_attribution_changed", previous.requires_attribution, updated.requires_attribution),
        ("requires_royalty_changed", previous.requires_royalty, updated.requires_royalty),
        (
            "minimum_creator_pool_rate_changed",
            round(previous.minimum_creator_pool_rate, 8),
            round(updated.minimum_creator_pool_rate, 8),
        ),
        ("revoked_changed", previous.revoked, updated.revoked),
        ("revoked_at_changed", previous.revoked_at, updated.revoked_at),
        ("lineage_changed", list(previous.derived_from), list(updated.derived_from)),
    )
    reasons = [name for name, before, after in checks if before != after]
    if not previous.revoked and updated.revoked:
        reasons.append("rights_revoked")
    return sorted(set(reasons))


def _changed_work_rows(
    previous_engine: RoyaltyDrivenLLM,
    updated_engine: RoyaltyDrivenLLM,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for work_id in sorted(set(previous_engine.works) | set(updated_engine.works)):
        previous = previous_engine.works.get(work_id)
        updated = updated_engine.works.get(work_id)
        reasons = _change_reasons(previous, updated)
        if not reasons:
            continue
        rows.append(
            {
                "work_id": work_id,
                "creator_id": (updated or previous).creator_id if (updated or previous) else "",
                "title": (updated or previous).title if (updated or previous) else "",
                "source_uri": (
                    (updated or previous).source_uri
                    or f"registered://works/{work_id}"
                    if (updated or previous)
                    else ""
                ),
                "previous_content_hash": _work_content_hash(previous),
                "updated_content_hash": _work_content_hash(updated),
                "previous_policy_hash": _policy_hash(previous),
                "updated_policy_hash": _policy_hash(updated),
                "previous_revoked": bool(previous.revoked) if previous else False,
                "updated_revoked": bool(updated.revoked) if updated else True,
                "revoked_at": updated.revoked_at if updated else "",
                "change_reasons": reasons,
            }
        )
    return rows


def _ledger_events(ledger_data: dict[str, Any]) -> list[UsageEvent]:
    return [UsageEvent.from_dict(item) for item in ledger_data.get("events", [])]


def _event_work_ids(event: UsageEvent) -> set[str]:
    work_ids: set[str] = set()
    work_ids.update(access.work_id for access in event.source_accesses)
    work_ids.update(reference.work_id for reference in event.source_references)
    work_ids.update(share.work_id for share in event.royalty_shares)
    work_ids.update(
        str(decision.get("work_id", ""))
        for decision in event.policy_decisions
        if decision.get("work_id")
    )
    return {work_id for work_id in work_ids if work_id and not work_id.startswith("escrow:")}


def _historical_event_refs(
    ledger_data: dict[str, Any],
    changed_work_ids: set[str],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for event in _ledger_events(ledger_data):
        matched_work_ids = sorted(_event_work_ids(event) & changed_work_ids)
        if not matched_work_ids:
            continue
        payout_total = sum(
            (
                share.payout
                for share in event.royalty_shares
                if share.work_id in matched_work_ids
            ),
            Decimal("0"),
        )
        refs.append(
            {
                "event_id": event.event_id,
                "event_hash": event.event_hash,
                "work_ids": matched_work_ids,
                "creator_pool": _money(event.creator_pool),
                "payout_to_changed_works": _money(payout_total),
                "source_access_count": len(
                    [
                        access
                        for access in event.source_accesses
                        if access.work_id in matched_work_ids
                    ]
                ),
                "source_reference_count": len(
                    [
                        reference
                        for reference in event.source_references
                        if reference.work_id in matched_work_ids
                    ]
                ),
                "royalty_share_count": len(
                    [
                        share
                        for share in event.royalty_shares
                        if share.work_id in matched_work_ids
                    ]
                ),
                "historical_event_preserved": True,
            }
        )
    return refs


def _policy_probe(
    engine: RoyaltyDrivenLLM,
    work: Work | None,
    *,
    work_id: str,
    use: str,
    creator_pool_rate: Decimal,
) -> dict[str, Any]:
    if work is None:
        return {
            "work_id": work_id,
            "use": use,
            "allowed": False,
            "reasons": ["deny:work_removed_from_current_registry"],
            "content_hash": "",
            "policy_hash": _policy_hash(None),
        }
    decision = engine.policy_engine.evaluate_work(
        work,
        use,
        jurisdiction=engine.jurisdiction,
        creator_pool_rate=creator_pool_rate,
    )
    return {
        "work_id": work.work_id,
        "use": use,
        "allowed": decision.allowed,
        "reasons": list(decision.reasons),
        "content_hash": decision.content_hash,
        "policy_hash": _policy_hash(work),
    }


def _retrieval_probe(engine: RoyaltyDrivenLLM, work: Work | None) -> dict[str, Any]:
    if work is None:
        return {
            "work_id": "",
            "retrieval_hit_count": 0,
            "retrieved_changed_work": False,
            "retrieval_policy_enforced": True,
        }
    hits = engine.retrieve(work.title or work.work_id, top_k=5, use="retrieval")
    changed_hits = [hit for hit in hits if hit.chunk.work_id == work.work_id]
    return {
        "work_id": work.work_id,
        "retrieval_hit_count": len(hits),
        "retrieved_changed_work": bool(changed_hits),
        "retrieval_policy_enforced": not bool(changed_hits),
    }


def _blocked_output_probe(
    engine: RoyaltyDrivenLLM,
    work: Work,
    *,
    gross_revenue: Decimal,
) -> dict[str, Any]:
    event = engine.attribute_text(
        "Rights remediation probe for updated policy enforcement",
        work.content,
        gross_revenue=gross_revenue,
    )
    payout_total = sum((share.payout for share in event.royalty_shares), Decimal("0"))
    escrow_accounts = sorted(
        {
            share.creator_id
            for share in event.royalty_shares
            if share.creator_id.endswith("_escrow")
            or share.chunk_id.startswith("escrow:")
        }
    )
    return {
        "work_id": work.work_id,
        "probe_event_id": event.event_id,
        "probe_event_hash": event.event_hash,
        "output_hash": stable_hash(work.content),
        "creator_pool": _money(event.creator_pool),
        "payout_total": _money(payout_total),
        "escrow_accounts": escrow_accounts,
        "rights_conflict_escrow_verified": (
            "rights_conflict_escrow" in escrow_accounts
            and payout_total == event.creator_pool
            and not event.source_references
        ),
        "policy_status": event.grounding_report.get("policy_status", ""),
        "grounding_status": event.grounding_report.get("status", ""),
    }


def _enforcement_probes(
    updated_engine: RoyaltyDrivenLLM,
    changed_rows: list[dict[str, Any]],
    *,
    gross_revenue: Decimal,
    creator_pool_rate: Decimal,
) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for row in changed_rows:
        work = updated_engine.works.get(str(row["work_id"]))
        policy_checks = [
            _policy_probe(
                updated_engine,
                work,
                work_id=str(row["work_id"]),
                use=use,
                creator_pool_rate=creator_pool_rate,
            )
            for use in REMEDIATION_USES
        ]
        denied_uses = [
            check["use"] for check in policy_checks if check.get("allowed") is False
        ]
        output_probe = None
        if work is not None and "external_attribution" in denied_uses:
            output_probe = _blocked_output_probe(
                updated_engine,
                work,
                gross_revenue=gross_revenue,
            )
        probes.append(
            {
                "work_id": row["work_id"],
                "updated_content_hash": row["updated_content_hash"],
                "updated_policy_hash": row["updated_policy_hash"],
                "policy_checks": policy_checks,
                "denied_uses": denied_uses,
                "retrieval_probe": _retrieval_probe(updated_engine, work),
                "blocked_output_probe": output_probe,
                "future_use_denied": bool(denied_uses),
            }
        )
    return probes


def _private_strings(
    previous_engine: RoyaltyDrivenLLM,
    updated_engine: RoyaltyDrivenLLM,
    ledger_data: dict[str, Any],
) -> list[str]:
    values: list[str] = []
    values.extend(work.content for work in previous_engine.works.values())
    values.extend(work.content for work in updated_engine.works.values())
    for event in _ledger_events(ledger_data):
        values.extend([event.prompt, event.output, event.answer_text])
        values.extend(source.quote for source in event.source_references)
        values.extend(claim.claim for claim in event.claim_support)
        values.extend(claim.evidence_text for claim in event.claim_support)
        values.extend(match.matched_text for match in event.text_matches)
    return [value for value in values if len(value.strip()) >= 16]


def make_rights_remediation_report(
    previous_engine: RoyaltyDrivenLLM,
    updated_engine: RoyaltyDrivenLLM,
    ledger_data: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report proving changed rights are enforced going forward."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    changed_rows = _changed_work_rows(previous_engine, updated_engine)
    changed_work_ids = {str(row["work_id"]) for row in changed_rows}
    historical_refs = _historical_event_refs(ledger_data, changed_work_ids)
    probes = _enforcement_probes(
        updated_engine,
        changed_rows,
        gross_revenue=gross,
        creator_pool_rate=rate,
    )
    blocked_probes = [
        probe["blocked_output_probe"]
        for probe in probes
        if probe.get("blocked_output_probe")
    ]
    escrow_required_work_count = len(
        [
            probe
            for probe in probes
            if probe.get("updated_content_hash")
            and "external_attribution" in probe.get("denied_uses", [])
        ]
    )
    future_denial_count = sum(
        1 for probe in probes for check in probe["policy_checks"] if not check["allowed"]
    )
    rights_escrow_verified = (
        len(blocked_probes) == escrow_required_work_count
        and all(
            probe.get("rights_conflict_escrow_verified") is True
            for probe in blocked_probes
        )
    )
    report = {
        "report_version": RIGHTS_REMEDIATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": RIGHTS_REMEDIATION_POLICY_VERSION,
            "creator_pool_rate": str(rate),
            "uses_checked": list(REMEDIATION_USES),
            "changed_policy_detection": "hash_previous_and_updated_policy_records",
            "future_denial_action": "deny_or_route_to_rights_conflict_escrow",
            "historical_event_policy": "preserve_event_hashes_and_issue_forward_remediation",
        },
        "economics": {
            "remediation_gross_revenue": _money(gross),
            "creator_pool_rate": str(rate),
            "creator_pool_per_blocked_probe": _money(creator_pool),
            "blocked_probe_count": len(blocked_probes),
            "escrow_verified_total": _money(creator_pool * len(blocked_probes)),
        },
        "changed_works": changed_rows,
        "historical_event_refs": historical_refs,
        "enforcement_probes": probes,
        "commitments": {
            "previous_policy_root": hash_payload(
                [
                    {
                        "work_id": work_id,
                        "policy_hash": _policy_hash(work),
                        "content_hash": _work_content_hash(work),
                    }
                    for work_id, work in sorted(previous_engine.works.items())
                ]
            ),
            "updated_policy_root": hash_payload(
                [
                    {
                        "work_id": work_id,
                        "policy_hash": _policy_hash(work),
                        "content_hash": _work_content_hash(work),
                    }
                    for work_id, work in sorted(updated_engine.works.items())
                ]
            ),
            "changed_work_root": hash_payload(changed_rows),
            "historical_event_root": hash_payload(historical_refs),
            "enforcement_probe_root": hash_payload(probes),
        },
        "summary": {
            "status": "ready",
            "changed_work_count": len(changed_rows),
            "revoked_work_count": len(
                [row for row in changed_rows if row["updated_revoked"] is True]
            ),
            "historical_event_count": len(historical_refs),
            "future_denial_count": future_denial_count,
            "escrow_required_work_count": escrow_required_work_count,
            "blocked_output_probe_count": len(blocked_probes),
            "rights_conflict_escrow_verified": rights_escrow_verified,
            "historical_events_preserved": all(
                item["historical_event_preserved"] for item in historical_refs
            ),
            "creator_pool_conserved": rights_escrow_verified,
            "post_publication_rights_remediation": True,
        },
        "privacy": {
            "work_text_disclosed": False,
            "prompt_text_disclosed": False,
            "output_text_disclosed": False,
            "claim_text_disclosed": False,
            "matched_text_disclosed": False,
            "private_ledger_disclosed": False,
            "report_uses_hashes_policy_reasons_and_event_refs": True,
        },
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_rights_remediation_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "economics",
        "changed_works",
        "historical_event_refs",
        "enforcement_probes",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing rights remediation field: {key}")
    if errors:
        return errors
    if report.get("report_version") != RIGHTS_REMEDIATION_VERSION:
        errors.append("rights remediation report version is unsupported")
    if report.get("policy", {}).get("profile") != RIGHTS_REMEDIATION_POLICY_VERSION:
        errors.append("rights remediation policy profile is unsupported")
    for row in report.get("changed_works", []):
        for key in (
            "work_id",
            "previous_policy_hash",
            "updated_policy_hash",
            "previous_content_hash",
            "updated_content_hash",
            "change_reasons",
        ):
            if key not in row:
                errors.append(f"missing changed work field: {key}")
    for probe in report.get("enforcement_probes", []):
        for key in (
            "work_id",
            "policy_checks",
            "denied_uses",
            "retrieval_probe",
            "future_use_denied",
        ):
            if key not in probe:
                errors.append(f"missing enforcement probe field: {key}")
    return errors


def verify_rights_remediation_report(
    report: dict[str, Any],
    previous_engine: RoyaltyDrivenLLM,
    updated_engine: RoyaltyDrivenLLM,
    ledger_data: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a post-publication rights remediation report."""

    errors = validate_rights_remediation_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("rights remediation report hash is not reproducible")

    expected = make_rights_remediation_report(
        previous_engine,
        updated_engine,
        ledger_data,
        gross_revenue=report.get("economics", {}).get(
            "remediation_gross_revenue", "1.00"
        ),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "economics",
        "changed_works",
        "historical_event_refs",
        "enforcement_probes",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"rights remediation {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("rights remediation report hash does not match replay")

    summary = report.get("summary", {})
    if summary.get("status") != "ready":
        errors.append("rights remediation report status is not ready")
    if summary.get("historical_events_preserved") is not True:
        errors.append("rights remediation historical event preservation failed")
    if summary.get("creator_pool_conserved") is not True:
        errors.append("rights remediation creator pool is not conserved")
    if summary.get("future_denial_count", 0) and (
        summary.get("rights_conflict_escrow_verified") is not True
    ):
        errors.append("rights remediation denied future use is not escrow verified")

    rendered = canonical_json(report)
    for value in _private_strings(previous_engine, updated_engine, ledger_data):
        if value in rendered:
            errors.append("rights remediation report leaks private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("rights remediation report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("rights remediation report signature is invalid")
    return errors
