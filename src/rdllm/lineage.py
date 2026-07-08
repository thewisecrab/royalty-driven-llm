"""Derivative-work lineage reports for pass-through royalty accountability."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.models import Creator, RoyaltyShare, UsageEvent, Work
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

LINEAGE_REPORT_VERSION = "rdllm-lineage-report/v1"
DEFAULT_LINEAGE_PASS_THROUGH_RATE = Decimal("0.30")
MONEY_QUANT = Decimal("0.000001")


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _decimal(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value))


def _work_map(works: dict[str, Work] | list[Work]) -> dict[str, Work]:
    if isinstance(works, dict):
        return works
    return {work.work_id: work for work in works}


def _creator_map(creators: dict[str, Creator] | list[Creator]) -> dict[str, Creator]:
    if isinstance(creators, dict):
        return creators
    return {creator.creator_id: creator for creator in creators}


def _work_hash(work: Work) -> str:
    return stable_hash(work.content)


def _creator_name(creators: dict[str, Creator], creator_id: str) -> str:
    creator = creators.get(creator_id)
    return creator.name if creator else ""


def _is_settleable_share(share: RoyaltyShare) -> bool:
    return (
        share.payout > Decimal("0")
        and not share.chunk_id.startswith("escrow:")
        and not share.creator_id.endswith("_escrow")
    )


def _normalized_lineage_entries(work: Work) -> list[dict[str, Any]]:
    raw_entries = [
        entry
        for entry in work.derived_from
        if entry.get("work_id") and float(entry.get("weight", 0.0)) > 0
    ]
    total = sum(Decimal(str(entry.get("weight", 0.0))) for entry in raw_entries)
    if total <= 0:
        return []
    return [
        {
            "work_id": str(entry["work_id"]),
            "weight": Decimal(str(entry.get("weight", 0.0))) / total,
            "relation": str(entry.get("relation", "derived_from")),
            "source_uri": str(entry.get("source_uri", "")),
            "content_hash": str(entry.get("content_hash", "")),
        }
        for entry in raw_entries
    ]


def _lineage_edge(
    downstream: Work,
    upstream: Work | None,
    entry: dict[str, Any],
) -> dict[str, Any]:
    declared_hash = str(entry.get("content_hash", ""))
    actual_hash = _work_hash(upstream) if upstream else ""
    edge = {
        "downstream_work_id": downstream.work_id,
        "upstream_work_id": str(entry["work_id"]),
        "relation": str(entry.get("relation", "derived_from")),
        "weight": round(float(entry["weight"]), 8),
        "downstream_content_hash": _work_hash(downstream),
        "upstream_content_hash": actual_hash,
        "declared_upstream_content_hash": declared_hash,
        "declared_hash_matches": (not declared_hash) or declared_hash == actual_hash,
        "source_uri": str(entry.get("source_uri", "")),
    }
    edge["edge_hash"] = hash_payload(edge)
    return edge


def _lineage_nodes(
    works: dict[str, Work],
    creators: dict[str, Creator],
    work_ids: set[str],
) -> list[dict[str, Any]]:
    nodes = []
    for work_id in sorted(work_ids):
        work = works.get(work_id)
        if not work:
            continue
        nodes.append(
            {
                "work_id": work.work_id,
                "creator_id": work.creator_id,
                "creator_name": _creator_name(creators, work.creator_id),
                "title": work.title,
                "source_uri": work.source_uri or f"registered://works/{work.work_id}",
                "content_hash": _work_hash(work),
                "license": work.license,
                "policy_id": work.policy_id or f"policy:{work.work_id}",
            }
        )
    return nodes


def _source_share_id(index: int, share: RoyaltyShare) -> str:
    seed = f"{index}:{share.creator_id}:{share.work_id}:{share.chunk_id}:{share.payout}"
    return f"srcshare_{stable_hash(seed)[:16]}"


def _walk_obligations(
    *,
    works: dict[str, Work],
    creators: dict[str, Creator],
    source_share_id: str,
    source_share: RoyaltyShare,
    work_id: str,
    amount: Decimal,
    path: list[str],
    pass_through_rate: Decimal,
    edges: dict[str, dict[str, Any]],
    touched_work_ids: set[str],
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    work = works.get(work_id)
    if work is None:
        issues.append(
            {
                "code": "missing_upstream_work",
                "work_id": work_id,
                "lineage_path": path + [work_id],
            }
        )
        return []
    if work_id in path:
        issues.append(
            {
                "code": "lineage_cycle_detected",
                "work_id": work_id,
                "lineage_path": path + [work_id],
            }
        )
        return []

    touched_work_ids.add(work_id)
    entries = _normalized_lineage_entries(work)
    current_path = path + [work_id]
    if not entries:
        return [
            {
                "source_share_id": source_share_id,
                "source_work_id": source_share.work_id,
                "source_chunk_id": source_share.chunk_id,
                "recipient_work_id": work.work_id,
                "recipient_creator_id": work.creator_id,
                "recipient_creator_name": _creator_name(creators, work.creator_id),
                "role": "direct_owner" if not path else "terminal_upstream_owner",
                "lineage_depth": len(path),
                "lineage_path": current_path,
                "raw_payout": amount,
            }
        ]

    retained = amount * (Decimal("1") - pass_through_rate)
    obligations = [
        {
            "source_share_id": source_share_id,
            "source_work_id": source_share.work_id,
            "source_chunk_id": source_share.chunk_id,
            "recipient_work_id": work.work_id,
            "recipient_creator_id": work.creator_id,
            "recipient_creator_name": _creator_name(creators, work.creator_id),
            "role": "immediate_residual" if not path else "lineage_residual",
            "lineage_depth": len(path),
            "lineage_path": current_path,
            "raw_payout": retained,
        }
    ]
    for entry in entries:
        upstream = works.get(str(entry["work_id"]))
        edge = _lineage_edge(work, upstream, entry)
        edges[edge["edge_hash"]] = edge
        if upstream is None:
            issues.append(
                {
                    "code": "missing_upstream_work",
                    "work_id": str(entry["work_id"]),
                    "lineage_path": current_path + [str(entry["work_id"])],
                }
            )
            continue
        if not edge["declared_hash_matches"]:
            issues.append(
                {
                    "code": "declared_upstream_hash_mismatch",
                    "work_id": upstream.work_id,
                    "lineage_path": current_path + [upstream.work_id],
                }
            )
        obligations.extend(
            _walk_obligations(
                works=works,
                creators=creators,
                source_share_id=source_share_id,
                source_share=source_share,
                work_id=upstream.work_id,
                amount=amount * pass_through_rate * entry["weight"],
                path=current_path,
                pass_through_rate=pass_through_rate,
                edges=edges,
                touched_work_ids=touched_work_ids,
                issues=issues,
            )
        )
    return obligations


def _finalize_obligations(
    obligations: list[dict[str, Any]],
    source_total: Decimal,
) -> list[dict[str, Any]]:
    if not obligations:
        return []
    finalized: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    raw_total = sum((item["raw_payout"] for item in obligations), Decimal("0"))
    for index, item in enumerate(obligations):
        payload = {
            key: value for key, value in item.items() if key != "raw_payout"
        }
        if index == len(obligations) - 1:
            payout = source_total - paid_so_far
        else:
            payout = item["raw_payout"].quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            paid_so_far += payout
        share = payout / source_total if source_total > 0 else Decimal("0")
        raw_share = item["raw_payout"] / raw_total if raw_total > 0 else Decimal("0")
        payload["share_of_source_payout"] = str(
            share.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        )
        payload["raw_share_of_lineage_pool"] = str(
            raw_share.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        )
        payload["payout"] = _money(payout)
        payload["obligation_hash"] = hash_payload(payload)
        finalized.append(payload)
    return finalized


def _private_strings(event: UsageEvent, works: dict[str, Work]) -> list[str]:
    values = [event.prompt, event.output, event.answer_text]
    values.extend(work.content for work in works.values())
    values.extend(reference.quote for reference in event.source_references)
    values.extend(claim.evidence_text for claim in event.claim_support)
    return [value for value in values if len(value) >= 16]


def make_lineage_report(
    event: UsageEvent,
    *,
    works: dict[str, Work] | list[Work],
    creators: dict[str, Creator] | list[Creator],
    pass_through_rate: Decimal | str | float = DEFAULT_LINEAGE_PASS_THROUGH_RATE,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report that prevents derivative works from erasing upstream owners."""

    work_by_id = _work_map(works)
    creator_by_id = _creator_map(creators)
    rate = _decimal(pass_through_rate)
    if rate < 0 or rate > 1:
        raise ValueError("pass_through_rate must be between 0 and 1")

    source_shares = [
        share for share in event.royalty_shares if _is_settleable_share(share)
    ]
    source_share_entries: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    edges: dict[str, dict[str, Any]] = {}
    touched_work_ids: set[str] = set()
    issues: list[dict[str, Any]] = []

    for index, share in enumerate(source_shares, start=1):
        source_share_id = _source_share_id(index, share)
        work = work_by_id.get(share.work_id)
        if work is None:
            issues.append(
                {
                    "code": "missing_source_work",
                    "work_id": share.work_id,
                    "source_share_id": source_share_id,
                }
            )
            continue
        touched_work_ids.add(work.work_id)
        entry = {
            "source_share_id": source_share_id,
            "creator_id": share.creator_id,
            "work_id": share.work_id,
            "chunk_id": share.chunk_id,
            "content_hash": share.content_hash,
            "work_content_hash": _work_hash(work),
            "payout": _money(share.payout),
            "contribution_weight": str(share.contribution_weight),
            "has_upstream_lineage": bool(_normalized_lineage_entries(work)),
        }
        entry["source_share_hash"] = hash_payload(entry)
        source_share_entries.append(entry)
        raw_obligations = _walk_obligations(
            works=work_by_id,
            creators=creator_by_id,
            source_share_id=source_share_id,
            source_share=share,
            work_id=share.work_id,
            amount=share.payout,
            path=[],
            pass_through_rate=rate,
            edges=edges,
            touched_work_ids=touched_work_ids,
            issues=issues,
        )
        finalized = _finalize_obligations(raw_obligations, share.payout)
        if sum(
            (_decimal(item["payout"]) for item in finalized),
            Decimal("0"),
        ) != share.payout:
            issues.append(
                {
                    "code": "source_payout_not_conserved",
                    "source_share_id": source_share_id,
                    "work_id": share.work_id,
                }
            )
        obligations.extend(finalized)

    direct_total = sum((_decimal(item["payout"]) for item in source_share_entries), Decimal("0"))
    obligation_total = sum((_decimal(item["payout"]) for item in obligations), Decimal("0"))
    upstream_obligations = [
        item for item in obligations if item["role"] in {"terminal_upstream_owner", "lineage_residual"}
    ]
    report = {
        "report_version": LINEAGE_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "creator_pool": _money(event.creator_pool),
            "royalty_share_count": len(event.royalty_shares),
            "settleable_source_share_count": len(source_shares),
        },
        "lineage_policy": {
            "profile": "rdllm-derivative-lineage/v1",
            "pass_through_rate": str(rate),
            "recursive_pass_through": True,
            "derived_work_does_not_extinguish_upstream_obligations": True,
            "missing_or_cyclic_lineage_fails_verification": True,
        },
        "source_royalty_shares": source_share_entries,
        "lineage_graph": {
            "nodes": _lineage_nodes(work_by_id, creator_by_id, touched_work_ids),
            "edges": sorted(edges.values(), key=lambda item: item["edge_hash"]),
        },
        "settlement_obligations": obligations,
        "issues": sorted(issues, key=lambda item: canonical_json(item)),
        "commitments": {
            "event_hash": event.event_hash,
            "source_share_root": hash_payload(source_share_entries),
            "lineage_edge_root": hash_payload(sorted(edges.values(), key=lambda item: item["edge_hash"])),
            "obligation_root": hash_payload(obligations),
            "work_lineage_root": hash_payload(
                [
                    {
                        "work_id": work.work_id,
                        "content_hash": _work_hash(work),
                        "derived_from": [
                            {
                                **entry,
                                "weight": round(float(entry["weight"]), 8),
                            }
                            for entry in _normalized_lineage_entries(work)
                        ],
                    }
                    for work in sorted(work_by_id.values(), key=lambda item: item.work_id)
                ]
            ),
        },
        "summary": {
            "status": "ready" if not issues and direct_total == obligation_total else "failed",
            "source_share_count": len(source_share_entries),
            "derivative_source_count": sum(
                1 for item in source_share_entries if item["has_upstream_lineage"]
            ),
            "upstream_obligation_count": len(upstream_obligations),
            "recipient_count": len({item["recipient_creator_id"] for item in obligations}),
            "lineage_edge_count": len(edges),
            "issue_count": len(issues),
            "max_lineage_depth": max(
                (int(item["lineage_depth"]) for item in obligations),
                default=0,
            ),
            "total_direct_payout": _money(direct_total),
            "total_obligation_payout": _money(obligation_total),
            "payout_conserved": direct_total == obligation_total,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "work_text_disclosed": False,
            "report_uses_hashes_and_work_ids": True,
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


def validate_lineage_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "lineage_policy",
        "source_royalty_shares",
        "lineage_graph",
        "settlement_obligations",
        "issues",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing lineage report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != LINEAGE_REPORT_VERSION:
        errors.append("lineage report version is unsupported")
    for key in ("event_id", "event_hash", "creator_pool", "settleable_source_share_count"):
        if key not in report.get("event", {}):
            errors.append(f"missing lineage event field: {key}")
    for key in ("pass_through_rate", "recursive_pass_through"):
        if key not in report.get("lineage_policy", {}):
            errors.append(f"missing lineage policy field: {key}")
    for key in ("source_share_root", "lineage_edge_root", "obligation_root", "work_lineage_root"):
        if key not in report.get("commitments", {}):
            errors.append(f"missing lineage commitment: {key}")
    return errors


def verify_lineage_report(
    report: dict[str, Any],
    event: UsageEvent,
    *,
    works: dict[str, Work] | list[Work],
    creators: dict[str, Creator] | list[Creator],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a derivative-work lineage report against an event and registered works."""

    errors = validate_lineage_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("lineage report hash is not reproducible")

    rate = report.get("lineage_policy", {}).get(
        "pass_through_rate", str(DEFAULT_LINEAGE_PASS_THROUGH_RATE)
    )
    expected = make_lineage_report(
        event,
        works=works,
        creators=creators,
        pass_through_rate=rate,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "lineage_policy",
        "source_royalty_shares",
        "lineage_graph",
        "settlement_obligations",
        "issues",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"lineage report {key} does not match event and works")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("lineage report hash does not match event and works")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("lineage report status is not ready")
    if report.get("summary", {}).get("payout_conserved") is not True:
        errors.append("lineage obligations do not conserve source payouts")

    report_text = canonical_json(report)
    work_by_id = _work_map(works)
    for value in _private_strings(event, work_by_id):
        if value and value in report_text:
            errors.append("lineage report discloses private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("lineage report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("lineage report signature is invalid")

    return errors
