"""Royalty abuse and source-farm settlement audits.

Attribution correctness is not enough for a YouTube-scale royalty system. Bad
actors can register synthetic sources, duplicate works, linked accounts, or
reciprocal citation rings and still pass narrow source-level checks. This module
adds a replayable settlement gate: suspicious value must route to escrow, direct
payout must be limited to verified low-risk creators and sources, and the public
report must not disclose private prompt/source/payment text.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

ROYALTY_ABUSE_AUDIT_VERSION = "rdllm-royalty-abuse-audit/v1"
ROYALTY_ABUSE_AUDIT_SCHEMA = "docs/schemas/royalty_abuse_audit.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L117"
MINIMUM_INPUT_LEVEL = "RDLLM-L116"

DEFAULT_MAX_SOURCE_FARM_RISK = Decimal("0.20")
DEFAULT_MAX_CREATOR_PAYOUT_SHARE = Decimal("0.70")
DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD = Decimal("0.92")
HIGH_RISK_RELATION_TYPES = {
    "shared_payout_account",
    "coordinated_citation_ring",
    "reciprocal_boost",
    "reciprocal_citation_ring",
    "sybil_cluster",
    "self_dealing",
    "undisclosed_common_control",
}
DIRECT_ACTIONS = {"direct_payout", "pay", "payable", "released"}
ESCROW_ACTIONS = {
    "escrow_abuse_review",
    "held_for_abuse_review",
    "sybil_review_escrow",
    "duplicate_review_escrow",
    "source_farm_review_escrow",
    "synthetic_review_escrow",
}

DECLARED_HASH_FIELDS = (
    "royalty_abuse_audit_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "source_authenticity_hash",
    "source_confidence_hash",
    "attribution_consensus_hash",
    "creator_attribution_audit_index_hash",
    "valuation_method_audit_hash",
    "report_hash",
    "card_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_output",
    "answer_text",
    "output_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}

ACCEPTED_DEPENDENCY_STATUSES = {
    "accepted",
    "fresh",
    "ready",
    "trusted_origin",
    "verified",
    "verified_human_origin",
}


def load_royalty_abuse_audit_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a royalty abuse audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"royalty_abuse_audit_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(report: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _money(value: Decimal | str | int | float) -> str:
    return str(_decimal(value).quantize(Decimal("0.000001")))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return (numerator / denominator).quantize(Decimal("0.00000001"))


def _score(value: Any) -> Decimal:
    raw = _decimal(value)
    if raw < 0:
        return Decimal("0")
    if raw > 1:
        return Decimal("1")
    return raw.quantize(Decimal("0.00000001"))


def _policy(audit_input: dict[str, Any]) -> dict[str, Decimal]:
    policy = audit_input.get("policy", {})
    return {
        "max_source_farm_risk": _score(
            policy.get("max_source_farm_risk", DEFAULT_MAX_SOURCE_FARM_RISK)
        ),
        "max_creator_payout_share": _score(
            policy.get("max_creator_payout_share", DEFAULT_MAX_CREATOR_PAYOUT_SHARE)
        ),
        "duplicate_similarity_threshold": _score(
            policy.get(
                "duplicate_similarity_threshold",
                DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD,
            )
        ),
    }


def _artifact_bindings(audit_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "source_freshness_audit": audit_input.get("source_freshness_audit"),
        "deep_research_citation_audit": audit_input.get("deep_research_citation_audit"),
        "source_authenticity_report": audit_input.get("source_authenticity_report"),
        "source_confidence_report": audit_input.get("source_confidence_report"),
        "attribution_consensus_report": audit_input.get("attribution_consensus_report"),
        "creator_attribution_audit_index": audit_input.get("creator_attribution_audit_index"),
        "valuation_method_audit_report": audit_input.get("valuation_method_audit_report"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        if artifact is None:
            continue
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(artifact)
    return bindings


def _artifact_binding_inputs_present(audit_input: dict[str, Any]) -> bool:
    return all(
        bool(audit_input.get(name))
        for name in (
            "source_freshness_audit",
            "source_authenticity_report",
            "source_confidence_report",
            "attribution_consensus_report",
            "valuation_method_audit_report",
        )
    )


def _settlement_rows(audit_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(audit_input.get("settlement_rows", [])):
        if not isinstance(row, dict):
            continue
        action = str(row.get("settlement_action") or row.get("action") or "").lower()
        amount = _decimal(row.get("payout_amount", row.get("amount", "0")))
        normalized = {
            "settlement_id": str(row.get("settlement_id") or f"settlement_{index + 1}"),
            "source_id": str(row.get("source_id") or row.get("label") or ""),
            "creator_id_hash": str(row.get("creator_id_hash") or ""),
            "recipient_creator_id_hash": str(
                row.get("recipient_creator_id_hash") or row.get("creator_id_hash") or ""
            ),
            "payout_account_hash": str(row.get("payout_account_hash") or ""),
            "payout_amount": _money(amount),
            "settlement_action": action,
            "direct_payout": action in DIRECT_ACTIONS and amount > 0,
            "escrowed": action in ESCROW_ACTIONS or bool(row.get("escrowed")),
            "reason_code": str(row.get("reason_code") or ""),
        }
        normalized["settlement_row_hash"] = hash_payload(normalized)
        rows.append(normalized)
    return sorted(rows, key=lambda row: row["settlement_id"])


def _source_settlement_index(
    settlement_rows: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in settlement_rows:
        source_id = row["source_id"]
        if not source_id:
            continue
        current = index.setdefault(
            source_id,
            {"direct_payout": False, "escrowed": False, "settlement_hashes": []},
        )
        current["direct_payout"] = current["direct_payout"] or row["direct_payout"]
        current["escrowed"] = current["escrowed"] or row["escrowed"]
        current["settlement_hashes"].append(row["settlement_row_hash"])
    return index


def _source_rows(
    audit_input: dict[str, Any],
    settlement_index: dict[str, dict[str, Any]],
    policy: dict[str, Decimal],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(audit_input.get("source_rows", [])):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or source.get("label") or f"S{index + 1}")
        settlement = settlement_index.get(
            source_id,
            {"direct_payout": False, "escrowed": False, "settlement_hashes": []},
        )
        source_farm_risk = _score(source.get("source_farm_risk_score", "0"))
        synthetic = bool(source.get("synthetic_source"))
        ai_disclosed = bool(source.get("ai_generated_disclosed"))
        origin_verified = bool(source.get("origin_signature_verified", True))
        source_authenticity_status = str(
            source.get("source_authenticity_status") or "ready"
        ).lower()
        source_freshness_status = str(source.get("source_freshness_status") or "ready").lower()
        suspicious = (
            source_farm_risk > policy["max_source_farm_risk"]
            or synthetic
            or ai_disclosed
            or not origin_verified
            or source_authenticity_status not in ACCEPTED_DEPENDENCY_STATUSES
            or source_freshness_status not in ACCEPTED_DEPENDENCY_STATUSES
        )
        row = {
            "source_id": source_id,
            "label": str(source.get("label") or source_id),
            "creator_id_hash": str(source.get("creator_id_hash") or ""),
            "work_id_hash": hash_payload(str(source.get("work_id") or "")),
            "source_uri_hash": hash_payload(str(source.get("source_uri") or "")),
            "domain_hash": hash_payload(str(source.get("domain") or "")),
            "content_hash": str(source.get("content_hash") or ""),
            "citation_count": int(source.get("citation_count", 0) or 0),
            "claim_count": int(source.get("claim_count", 0) or 0),
            "source_farm_risk_score": str(source_farm_risk),
            "synthetic_source": synthetic,
            "ai_generated_disclosed": ai_disclosed,
            "origin_signature_verified": origin_verified,
            "source_authenticity_status": source_authenticity_status,
            "source_freshness_status": source_freshness_status,
            "direct_payout": bool(settlement["direct_payout"]),
            "escrowed": bool(settlement["escrowed"]),
            "settlement_hashes": sorted(settlement["settlement_hashes"]),
            "suspicious_source": suspicious,
            "high_source_farm_risk": source_farm_risk > policy["max_source_farm_risk"],
            "synthetic_or_ai_generated_source": synthetic or ai_disclosed,
            "unverified_origin_or_dependency": (
                not origin_verified
                or source_authenticity_status not in ACCEPTED_DEPENDENCY_STATUSES
                or source_freshness_status not in ACCEPTED_DEPENDENCY_STATUSES
            ),
            "routed_to_abuse_escrow_if_suspicious": (
                not suspicious or (bool(settlement["escrowed"]) and not settlement["direct_payout"])
            ),
        }
        row["source_abuse_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["source_id"])


def _creator_rows(
    audit_input: dict[str, Any],
    settlement_rows: list[dict[str, Any]],
    creator_pool: Decimal,
    policy: dict[str, Decimal],
) -> list[dict[str, Any]]:
    settlement_by_creator: dict[str, Decimal] = {}
    direct_by_creator: dict[str, Decimal] = {}
    for settlement in settlement_rows:
        creator_id_hash = (
            settlement.get("creator_id_hash")
            or settlement.get("recipient_creator_id_hash")
            or ""
        )
        amount = _decimal(settlement["payout_amount"])
        settlement_by_creator[creator_id_hash] = (
            settlement_by_creator.get(creator_id_hash, Decimal("0")) + amount
        )
        if settlement["direct_payout"]:
            direct_by_creator[creator_id_hash] = (
                direct_by_creator.get(creator_id_hash, Decimal("0")) + amount
            )

    rows: list[dict[str, Any]] = []
    for index, creator in enumerate(audit_input.get("creator_rows", [])):
        if not isinstance(creator, dict):
            continue
        creator_id_hash = str(
            creator.get("creator_id_hash") or hash_payload(str(creator.get("creator_id") or index))
        )
        payout_amount = settlement_by_creator.get(
            creator_id_hash,
            _decimal(creator.get("payout_amount", "0")),
        )
        direct_amount = direct_by_creator.get(creator_id_hash, Decimal("0"))
        payout_share = _ratio(payout_amount, creator_pool)
        direct_payout_share = _ratio(direct_amount, creator_pool)
        linked_accounts = sorted(str(item) for item in creator.get("linked_account_hashes", []))
        verified_identity = bool(creator.get("verified_identity"))
        prior_abuse_strikes = int(creator.get("prior_abuse_strikes", 0) or 0)
        suspicious = (
            not verified_identity
            or prior_abuse_strikes > 0
            or bool(linked_accounts)
            or direct_payout_share > policy["max_creator_payout_share"]
        )
        row = {
            "creator_id_hash": creator_id_hash,
            "payout_account_hash": str(creator.get("payout_account_hash") or ""),
            "verified_identity": verified_identity,
            "account_age_days": int(creator.get("account_age_days", 0) or 0),
            "prior_abuse_strikes": prior_abuse_strikes,
            "linked_account_hashes": linked_accounts,
            "source_count": int(creator.get("source_count", 0) or 0),
            "total_payout_amount": _money(payout_amount),
            "direct_payout_amount": _money(direct_amount),
            "payout_share": str(payout_share),
            "direct_payout_share": str(direct_payout_share),
            "suspicious_creator": suspicious,
            "creator_direct_payout_allowed": not suspicious or direct_amount == 0,
            "payout_concentration_ok": direct_payout_share
            <= policy["max_creator_payout_share"],
        }
        row["creator_abuse_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["creator_id_hash"])


def _duplicate_rows(
    audit_input: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
    policy: dict[str, Decimal],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, duplicate in enumerate(audit_input.get("duplicate_rows", [])):
        if not isinstance(duplicate, dict):
            continue
        source_a = str(duplicate.get("source_a") or duplicate.get("source_id_a") or "")
        source_b = str(duplicate.get("source_b") or duplicate.get("source_id_b") or "")
        similarity = _score(duplicate.get("similarity", duplicate.get("similarity_score", "0")))
        duplicate_match = (
            similarity >= policy["duplicate_similarity_threshold"]
            or bool(duplicate.get("content_hash_match"))
        )
        a_row = source_by_id.get(source_a, {})
        b_row = source_by_id.get(source_b, {})
        both_direct = bool(a_row.get("direct_payout")) and bool(b_row.get("direct_payout"))
        duplicate_escrowed = bool(a_row.get("escrowed")) or bool(b_row.get("escrowed"))
        row = {
            "duplicate_id": str(duplicate.get("duplicate_id") or f"duplicate_{index + 1}"),
            "source_a": source_a,
            "source_b": source_b,
            "similarity": str(similarity),
            "content_hash_match": bool(duplicate.get("content_hash_match")),
            "same_payout_account": bool(
                duplicate.get("same_payout_account")
                or duplicate.get("shared_payout_account")
            ),
            "owner_overlap": bool(duplicate.get("owner_overlap")),
            "duplicate_match": duplicate_match,
            "both_duplicates_paid_directly": duplicate_match and both_direct,
            "duplicate_value_escrowed": (not duplicate_match) or duplicate_escrowed,
        }
        row["duplicate_abuse_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["duplicate_id"])


def _collusion_rows(
    audit_input: dict[str, Any],
    creator_by_id: dict[str, dict[str, Any]],
    source_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    relation_rows = audit_input.get("relation_rows", audit_input.get("relationship_rows", []))
    for index, relation in enumerate(relation_rows):
        if not isinstance(relation, dict):
            continue
        relation_type = str(
            relation.get("relation_type") or relation.get("relationship_type") or ""
        ).lower()
        participants = sorted(
            str(item)
            for item in (
                relation.get("participant_creator_hashes")
                or relation.get("creator_id_hashes")
                or []
            )
        )
        if not participants:
            for key in ("from_creator_id_hash", "to_creator_id_hash"):
                value = str(relation.get(key) or "")
                if value:
                    participants.append(value)
            participants = sorted(set(participants))
        relation_source_ids = sorted(
            str(item) for item in relation.get("source_ids", []) if str(item)
        )
        if not participants and relation_source_ids:
            participants = sorted(
                {
                    str(source_by_id.get(source_id, {}).get("creator_id_hash") or "")
                    for source_id in relation_source_ids
                    if str(source_by_id.get(source_id, {}).get("creator_id_hash") or "")
                }
            )
        relation_risk = _score(relation.get("risk_score", relation.get("weight", "0")))
        high_risk = relation_type in HIGH_RISK_RELATION_TYPES or relation_risk >= Decimal("0.80")
        participant_direct = any(
            _decimal(creator_by_id.get(participant, {}).get("direct_payout_amount", "0")) > 0
            for participant in participants
        ) or any(
            bool(source_by_id.get(source_id, {}).get("direct_payout"))
            for source_id in relation_source_ids
        )
        row = {
            "relation_id": str(
                relation.get("relation_id")
                or relation.get("relationship_id")
                or f"relation_{index + 1}"
            ),
            "relation_type": relation_type,
            "participant_creator_hashes": participants,
            "source_ids": relation_source_ids,
            "relation_weight": str(relation_risk),
            "evidence_hash": str(relation.get("evidence_hash") or ""),
            "high_risk_relation": high_risk,
            "participants_have_direct_payout": participant_direct,
            "high_risk_relation_routed_to_escrow": not (high_risk and participant_direct),
        }
        row["collusion_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["relation_id"])


def make_royalty_abuse_audit_report(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L117 royalty-abuse audit for direct settlement gates."""

    policy = _policy(audit_input)
    creator_pool = _decimal(
        audit_input.get("creator_pool_amount")
        or audit_input.get("creator_pool")
        or "0"
    )
    settlement_rows = _settlement_rows(audit_input)
    settlement_index = _source_settlement_index(settlement_rows)
    source_rows = _source_rows(audit_input, settlement_index, policy)
    source_by_id = {row["source_id"]: row for row in source_rows}
    creator_rows = _creator_rows(audit_input, settlement_rows, creator_pool, policy)
    creator_by_id = {row["creator_id_hash"]: row for row in creator_rows}
    duplicate_rows = _duplicate_rows(audit_input, source_by_id, policy)
    collusion_rows = _collusion_rows(audit_input, creator_by_id, source_by_id)
    direct_total = sum(
        _decimal(row["payout_amount"]) for row in settlement_rows if row["direct_payout"]
    )
    escrow_total = sum(
        _decimal(row["payout_amount"]) for row in settlement_rows if row["escrowed"]
    )
    settlement_total = sum(_decimal(row["payout_amount"]) for row in settlement_rows)
    public_payload = {
        "source_abuse_rows": source_rows,
        "creator_abuse_rows": creator_rows,
        "duplicate_abuse_rows": duplicate_rows,
        "collusion_rows": collusion_rows,
        "settlement_rows": settlement_rows,
    }
    checks = {
        "settlement_window_present": bool(str(audit_input.get("settlement_window_id") or "")),
        "source_rows_present": bool(source_rows),
        "creator_rows_present": bool(creator_rows),
        "settlement_rows_present": bool(settlement_rows),
        "source_rows_have_abuse_signals": all(
            row["source_farm_risk_score"] != "" and row["content_hash"]
            for row in source_rows
        ),
        "every_high_risk_source_routed_to_escrow": all(
            row["routed_to_abuse_escrow_if_suspicious"] for row in source_rows
        ),
        "every_synthetic_or_unverified_source_routed_to_escrow": all(
            not (
                row["synthetic_or_ai_generated_source"]
                or row["unverified_origin_or_dependency"]
            )
            or (row["escrowed"] and not row["direct_payout"])
            for row in source_rows
        ),
        "every_unverified_or_linked_creator_direct_payout_blocked": all(
            row["creator_direct_payout_allowed"] for row in creator_rows
        ),
        "payout_concentration_within_policy": all(
            row["payout_concentration_ok"] for row in creator_rows
        ),
        "duplicate_source_direct_double_pay_blocked": all(
            not row["both_duplicates_paid_directly"] for row in duplicate_rows
        ),
        "duplicate_value_routes_to_escrow": all(
            row["duplicate_value_escrowed"] for row in duplicate_rows
        ),
        "collusion_relations_block_direct_payout": all(
            row["high_risk_relation_routed_to_escrow"] for row in collusion_rows
        ),
        "creator_pool_conserved": settlement_total == creator_pool,
        "artifact_bindings_hash_reproducible": all(
            value is True
            for key, value in _artifact_bindings(audit_input).items()
            if key.endswith("_hash_reproducible")
        ),
        "required_artifact_bindings_present": _artifact_binding_inputs_present(
            audit_input
        ),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_payload
        ),
    }
    suspicious_source_count = sum(1 for row in source_rows if row["suspicious_source"])
    suspicious_creator_count = sum(1 for row in creator_rows if row["suspicious_creator"])
    duplicate_match_count = sum(1 for row in duplicate_rows if row["duplicate_match"])
    high_risk_relation_count = sum(
        1 for row in collusion_rows if row["high_risk_relation"]
    )
    report: dict[str, Any] = {
        "audit_version": ROYALTY_ABUSE_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-royalty-abuse-audit-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "max_source_farm_risk": str(policy["max_source_farm_risk"]),
            "max_creator_payout_share": str(policy["max_creator_payout_share"]),
            "duplicate_similarity_threshold": str(
                policy["duplicate_similarity_threshold"]
            ),
            "high_risk_relation_types": sorted(HIGH_RISK_RELATION_TYPES),
            "suspicious_value_must_route_to_escrow": True,
        },
        "settlement_window": {
            "settlement_window_id_hash": hash_payload(
                str(audit_input.get("settlement_window_id") or "")
            ),
            "creator_pool_amount": _money(creator_pool),
            "direct_payout_total": _money(direct_total),
            "escrow_total": _money(escrow_total),
            "settlement_total": _money(settlement_total),
        },
        "artifact_bindings": _artifact_bindings(audit_input),
        "source_abuse_rows": source_rows,
        "creator_abuse_rows": creator_rows,
        "duplicate_abuse_rows": duplicate_rows,
        "collusion_rows": collusion_rows,
        "settlement_rows": settlement_rows,
        "checks": checks,
        "commitments": {
            "source_abuse_root": hash_payload([row["source_abuse_hash"] for row in source_rows]),
            "creator_abuse_root": hash_payload([row["creator_abuse_hash"] for row in creator_rows]),
            "duplicate_abuse_root": hash_payload([row["duplicate_abuse_hash"] for row in duplicate_rows]),
            "collusion_root": hash_payload([row["collusion_row_hash"] for row in collusion_rows]),
            "settlement_root": hash_payload([row["settlement_row_hash"] for row in settlement_rows]),
            "schema": ROYALTY_ABUSE_AUDIT_SCHEMA,
        },
        "schemas": {
            "royalty_abuse_audit": ROYALTY_ABUSE_AUDIT_SCHEMA,
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "source_authenticity_report": "docs/schemas/source_authenticity_report.schema.json",
            "attribution_consensus_report": "docs/schemas/attribution_consensus_report.schema.json",
        },
        "summary": {
            "status": "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "source_count": len(source_rows),
            "creator_count": len(creator_rows),
            "settlement_row_count": len(settlement_rows),
            "suspicious_source_count": suspicious_source_count,
            "suspicious_creator_count": suspicious_creator_count,
            "duplicate_match_count": duplicate_match_count,
            "high_risk_relation_count": high_risk_relation_count,
            "direct_payout_total": _money(direct_total),
            "escrow_total": _money(escrow_total),
            "creator_pool_amount": _money(creator_pool),
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_payment_account_disclosed": False,
            "public_report_uses_hashes_scores_flags_and_amounts": True,
        },
    }
    report["checks"]["private_strings_absent"] = _private_strings_absent(
        report, audit_input
    )
    report["summary"]["status"] = "ready" if all(report["checks"].values()) else "failed"
    report["royalty_abuse_audit_hash"] = hash_payload(_hashable_report(report))
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


def validate_royalty_abuse_audit_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L117 royalty abuse audit."""

    errors: list[str] = []
    required = (
        "audit_version",
        "issuer",
        "created_at",
        "policy",
        "settlement_window",
        "artifact_bindings",
        "source_abuse_rows",
        "creator_abuse_rows",
        "duplicate_abuse_rows",
        "collusion_rows",
        "settlement_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "royalty_abuse_audit_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing royalty abuse audit field: {key}")
    if errors:
        return errors
    if report.get("audit_version") != ROYALTY_ABUSE_AUDIT_VERSION:
        errors.append("royalty abuse audit version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("royalty abuse audit target certification level is unsupported")
    if "royalty_abuse_audit" not in report.get("schemas", {}):
        errors.append("missing royalty abuse audit schema")
    if _contains_private_fields(report):
        errors.append("royalty abuse audit contains private field")
    return errors


def verify_royalty_abuse_audit_report(
    report: dict[str, Any],
    *,
    audit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L117 royalty abuse audit against its private replay input."""

    errors = validate_royalty_abuse_audit_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("royalty_abuse_audit_hash"):
        errors.append("royalty abuse audit hash is not reproducible")
    expected = make_royalty_abuse_audit_report(
        audit_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "settlement_window",
        "artifact_bindings",
        "source_abuse_rows",
        "creator_abuse_rows",
        "duplicate_abuse_rows",
        "collusion_rows",
        "settlement_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"royalty abuse audit {key} does not match inputs")
    if expected.get("royalty_abuse_audit_hash") != report.get(
        "royalty_abuse_audit_hash"
    ):
        errors.append("royalty abuse audit hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("royalty abuse audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"royalty abuse audit check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("royalty abuse audit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("royalty abuse audit signature is invalid")
    return errors
