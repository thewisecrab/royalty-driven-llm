"""Evidence-force calibration for cited claims.

Grounded citations can still mislead when the cited source is real and relevant
but the answer overstates what the source warrants. This module creates a public
hash-only audit that compares each cited claim's asserted force against the
supporting evidence force across relation, modality, scope, temporal, and numeric
axes before a footer row can be treated as verified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

EVIDENCE_FORCE_CALIBRATION_VERSION = "rdllm-evidence-force-calibration/v1"
EVIDENCE_FORCE_CALIBRATION_SCHEMA = (
    "docs/schemas/evidence_force_calibration.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L119"
MINIMUM_INPUT_LEVEL = "RDLLM-L118"

REQUIRED_AXES = ("relation", "modality", "scope", "temporal", "numeric")
DEFAULT_MIN_SUPPORT_SCORE = 0.72
DEFAULT_MIN_CONFIDENCE = 0.70

FORCE_RANKS: dict[str, dict[str, int]] = {
    "relation": {
        "none": 0,
        "topical": 1,
        "mentions": 1,
        "correlational": 2,
        "association": 2,
        "supports": 3,
        "causal": 4,
        "mechanistic": 5,
    },
    "modality": {
        "none": 0,
        "speculative": 1,
        "possible": 2,
        "may": 2,
        "likely": 3,
        "suggests": 3,
        "asserted": 4,
        "certain": 5,
    },
    "scope": {
        "none": 0,
        "anecdotal": 1,
        "single_case": 1,
        "local": 2,
        "sample": 3,
        "population": 4,
        "universal": 5,
    },
    "temporal": {
        "none": 0,
        "undated": 0,
        "historical": 1,
        "time_bound": 2,
        "as_of": 3,
        "current": 4,
        "future": 5,
    },
    "numeric": {
        "none": 0,
        "directional": 1,
        "approximate": 2,
        "range": 3,
        "exact": 4,
    },
}

PASSING_FOOTER_STATUSES = {"verified", "calibrated"}
PASSING_SETTLEMENT_ACTIONS = {"direct_payout_allowed", "payable", "settled"}
SAFE_OVERCLAIM_ACTIONS = {
    "warrant_review_escrow",
    "answer_blocked",
    "claim_rewrite_required",
    "warning_footer",
    "review",
    "escrow",
}

DECLARED_HASH_FIELDS = (
    "evidence_force_calibration_hash",
    "consent_revocation_propagation_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "evidence_sufficiency_report_hash",
    "counterevidence_report_hash",
    "source_confidence_report_hash",
    "citation_footer_contract_hash",
    "grounded_source_footer_hash",
    "claim_source_attribution_report_hash",
    "calibrated_attribution_report_hash",
    "report_hash",
    "receipt_hash",
    "card_hash",
    "contract_hash",
    "footer_hash",
    "envelope_hash",
    "manifest_hash",
)

REQUIRED_ARTIFACT_BINDINGS = (
    "source_freshness_audit",
    "deep_research_citation_audit",
    "evidence_sufficiency_report",
    "counterevidence_report",
    "source_confidence_report",
    "citation_footer_contract",
    "grounded_source_footer",
    "claim_source_attribution_report",
    "calibrated_attribution_report",
    "consent_revocation_propagation",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_model_output",
    "claim_text",
    "raw_claim",
    "source_text",
    "evidence_text",
    "quote",
    "matched_text",
    "document_text",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "payment_account",
    "bank_account",
    "account_number",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_evidence_force_calibration_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L119 evidence-force audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"evidence_force_calibration_hash", "signature"}
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


def _private_strings_absent(
    report: dict[str, Any], calibration_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in calibration_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _rank(axis: str, value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "none").strip().lower().replace("-", "_").replace(" ", "_")
    return FORCE_RANKS.get(axis, {}).get(text, 0)


def _force_label(axis: str, value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"rank:{int(value)}"
    text = str(value or "none").strip().lower().replace("-", "_").replace(" ", "_")
    if text in FORCE_RANKS.get(axis, {}):
        return text
    return "none"


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _policy(calibration_input: dict[str, Any]) -> dict[str, Any]:
    policy = calibration_input.get("policy", {})
    required_axes = tuple(policy.get("required_axes") or REQUIRED_AXES)
    return {
        "profile": "rdllm-evidence-force-calibration-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_axes": list(required_axes),
        "min_support_score": _float(
            policy.get("min_support_score"), DEFAULT_MIN_SUPPORT_SCORE
        ),
        "min_confidence": _float(policy.get("min_confidence"), DEFAULT_MIN_CONFIDENCE),
        "require_force_raise_controls": bool(
            policy.get("require_force_raise_controls", True)
        ),
        "verified_footer_requires_calibration": bool(
            policy.get("verified_footer_requires_calibration", True)
        ),
        "direct_settlement_requires_calibration": bool(
            policy.get("direct_settlement_requires_calibration", True)
        ),
    }


def _axis_rows(claim: dict[str, Any], required_axes: tuple[str, ...]) -> list[dict[str, Any]]:
    claim_force = claim.get("claim_force", {})
    evidence_force = claim.get("evidence_force", {})
    rows: list[dict[str, Any]] = []
    for axis in required_axes:
        claim_label = _force_label(axis, claim_force.get(axis))
        evidence_label = _force_label(axis, evidence_force.get(axis))
        claim_rank = _rank(axis, claim_force.get(axis))
        evidence_rank = _rank(axis, evidence_force.get(axis))
        gap = max(0, claim_rank - evidence_rank)
        rows.append(
            {
                "axis": axis,
                "claim_force": claim_label,
                "evidence_force": evidence_label,
                "claim_rank": claim_rank,
                "evidence_rank": evidence_rank,
                "force_gap": gap,
                "calibrated": gap == 0,
                "axis_row_hash": hash_payload(
                    {
                        "axis": axis,
                        "claim_force": claim_label,
                        "evidence_force": evidence_label,
                        "claim_rank": claim_rank,
                        "evidence_rank": evidence_rank,
                        "force_gap": gap,
                    }
                ),
            }
        )
    return rows


def _claim_force_rows(
    calibration_input: dict[str, Any], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    required_axes = tuple(policy["required_axes"])
    for index, claim in enumerate(calibration_input.get("claim_rows", [])):
        axes = _axis_rows(claim, required_axes)
        violation_axes = [row["axis"] for row in axes if not row["calibrated"]]
        support_score = _float(claim.get("support_score"), 0.0)
        confidence = _float(claim.get("confidence"), support_score)
        footer_status = str(claim.get("footer_status") or "").strip().lower()
        settlement_action = (
            str(claim.get("settlement_action") or "").strip().lower()
        )
        calibrated = (
            not violation_axes
            and support_score >= policy["min_support_score"]
            and confidence >= policy["min_confidence"]
        )
        direct_payout_requested = bool(claim.get("direct_payout", False)) or (
            settlement_action in PASSING_SETTLEMENT_ACTIONS
        )
        verified_footer_requested = footer_status in PASSING_FOOTER_STATUSES
        safe_action_for_overclaim = (
            settlement_action in SAFE_OVERCLAIM_ACTIONS
            or footer_status in {"warning", "failed", "review"}
            or not direct_payout_requested
        )
        claim_id = str(claim.get("claim_id") or f"claim:{index}")
        claim_hash = str(
            claim.get("claim_hash")
            or hash_payload(str(claim.get("claim_text") or claim_id))
        )
        evidence_hash = str(
            claim.get("evidence_hash")
            or hash_payload(str(claim.get("evidence_text") or claim_id))
        )
        row = {
            "claim_id": claim_id,
            "source_id": str(claim.get("source_id") or ""),
            "source_label": str(claim.get("source_label") or ""),
            "claim_hash": claim_hash,
            "evidence_hash": evidence_hash,
            "claim_span_hash": str(claim.get("claim_span_hash") or claim_hash),
            "evidence_span_hash": str(claim.get("evidence_span_hash") or evidence_hash),
            "support_score": round(support_score, 8),
            "confidence": round(confidence, 8),
            "axis_rows": axes,
            "violation_axes": violation_axes,
            "max_force_gap": max((axis["force_gap"] for axis in axes), default=0),
            "calibrated": calibrated,
            "verified_footer_requested": verified_footer_requested,
            "direct_payout_requested": direct_payout_requested,
            "safe_action_for_overclaim": safe_action_for_overclaim,
            "footer_status": footer_status or ("verified" if calibrated else "warning"),
            "settlement_action": settlement_action
            or ("direct_payout_allowed" if calibrated else "warrant_review_escrow"),
            "decision": "calibrated" if calibrated else "over_warranted_review",
        }
        row["claim_force_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _force_raise_rows(
    calibration_input: dict[str, Any], claim_ids: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, challenge in enumerate(calibration_input.get("force_raise_rows", [])):
        axis = str(challenge.get("axis") or "").strip().lower()
        claim_id = str(challenge.get("claim_id") or "")
        rejected = bool(challenge.get("rejected", False))
        expected_rejected = bool(challenge.get("expected_rejected", True))
        row = {
            "challenge_id": str(challenge.get("challenge_id") or f"force-raise:{index}"),
            "claim_id": claim_id,
            "axis": axis,
            "claim_exists": claim_id in claim_ids,
            "raised_claim_force": _force_label(axis, challenge.get("raised_claim_force")),
            "raised_claim_rank": _rank(axis, challenge.get("raised_claim_force")),
            "evidence_force": _force_label(axis, challenge.get("evidence_force")),
            "evidence_rank": _rank(axis, challenge.get("evidence_force")),
            "expected_rejected": expected_rejected,
            "rejected": rejected,
            "control_passed": expected_rejected and rejected and axis in REQUIRED_AXES,
            "challenge_hash": str(
                challenge.get("challenge_hash")
                or hash_payload(str(challenge.get("challenge_text") or index))
            ),
        }
        row["force_raise_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _visible_footer_claim_rows(calibration_input: dict[str, Any]) -> list[dict[str, Any]]:
    contract = calibration_input.get("citation_footer_contract", {})
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(contract.get("claims", [])):
        source_label = str(claim.get("source_label", ""))
        claim_hash = str(claim.get("claim_hash", ""))
        span_prefix = str(claim.get("evidence_span_prefix", ""))
        row = {
            "claim_index": int(claim.get("claim_index", index + 1) or index + 1),
            "source_label": source_label,
            "claim_hash": claim_hash,
            "evidence_span_prefix": span_prefix,
            "display_anchor": str(claim.get("display_anchor", "")),
            "confidence_level": str(claim.get("confidence_level", "")),
            "confidence_score": round(_float(claim.get("confidence_score"), 0.0), 8),
            "visible_claim_key": hash_payload(
                {
                    "source_label": source_label,
                    "claim_hash": claim_hash,
                    "evidence_span_prefix": span_prefix,
                }
            ),
        }
        row["visible_footer_claim_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _claim_matches_visible_footer(
    force_row: dict[str, Any], footer_claim: dict[str, Any]
) -> bool:
    if force_row.get("source_label") != footer_claim.get("source_label"):
        return False
    footer_claim_hash = str(footer_claim.get("claim_hash", ""))
    if footer_claim_hash and force_row.get("claim_hash") != footer_claim_hash:
        return False
    span_prefix = str(footer_claim.get("evidence_span_prefix", ""))
    if not span_prefix:
        return True
    return any(
        str(force_row.get(field, "")).startswith(span_prefix)
        for field in ("evidence_span_hash", "claim_span_hash", "claim_hash", "evidence_hash")
    )


def _footer_claim_coverage_rows(
    *,
    footer_claim_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for footer_claim in footer_claim_rows:
        matches = [
            row for row in claim_rows if _claim_matches_visible_footer(row, footer_claim)
        ]
        matched_claim_ids = [str(row.get("claim_id", "")) for row in matches]
        matched_calibrated = bool(matches) and all(
            bool(row.get("calibrated")) for row in matches
        )
        matched_verified_footer = bool(matches) and all(
            bool(row.get("verified_footer_requested")) for row in matches
        )
        public = {
            "visible_claim_key": footer_claim["visible_claim_key"],
            "claim_index": footer_claim["claim_index"],
            "source_label": footer_claim["source_label"],
            "claim_hash": footer_claim["claim_hash"],
            "evidence_span_prefix": footer_claim["evidence_span_prefix"],
            "footer_claim_verified": footer_claim["confidence_level"] == "verified",
            "covered_by_force_row": bool(matches),
            "matched_claim_ids": matched_claim_ids,
            "matched_calibrated": matched_calibrated,
            "matched_verified_footer": matched_verified_footer,
            "matched_force_row_hashes": [
                str(row.get("claim_force_row_hash", "")) for row in matches
            ],
        }
        public["footer_claim_coverage_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _verified_force_rows_absent_from_footer(
    *,
    footer_claim_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[str]:
    if not footer_claim_rows:
        return []
    absent = []
    for row in claim_rows:
        if not row.get("verified_footer_requested"):
            continue
        if not any(_claim_matches_visible_footer(row, claim) for claim in footer_claim_rows):
            absent.append(str(row.get("claim_id", "")))
    return absent


def _artifact_bindings(calibration_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for key in REQUIRED_ARTIFACT_BINDINGS:
        artifact = calibration_input.get(key)
        bindings[key] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(
                (artifact or {}).get("audit_version")
                or (artifact or {}).get("report_version")
                or (artifact or {}).get("receipt_version")
                or (artifact or {}).get("contract_version")
                or (artifact or {}).get("footer_version")
                or ""
            ),
        }
    return bindings


def _root(rows: list[dict[str, Any]], field: str) -> str:
    return hash_payload([row.get(field, "") for row in rows])


def make_evidence_force_calibration_report(
    calibration_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L119 audit over claim wording force and source warrant."""

    created_at = created_at or now_iso()
    policy = _policy(calibration_input)
    claim_rows = _claim_force_rows(calibration_input, policy)
    force_raise_rows = _force_raise_rows(
        calibration_input, {row["claim_id"] for row in claim_rows}
    )
    visible_footer_claim_rows = _visible_footer_claim_rows(calibration_input)
    footer_claim_coverage_rows = _footer_claim_coverage_rows(
        footer_claim_rows=visible_footer_claim_rows,
        claim_rows=claim_rows,
    )
    bindings = _artifact_bindings(calibration_input)
    missing_axes = [
        {"claim_id": row["claim_id"], "missing_axes": []}
        for row in claim_rows
        if len(row["axis_rows"]) != len(policy["required_axes"])
    ]
    over_warranted = [row for row in claim_rows if not row["calibrated"]]
    unsupported_controls = [
        row for row in force_raise_rows if not row["control_passed"]
    ]
    missing_artifacts = [
        key
        for key, value in bindings.items()
        if not value["present"] or not value["hash_reproducible"]
    ]
    uncovered_visible_footer_claims = [
        row["visible_claim_key"]
        for row in footer_claim_coverage_rows
        if not row["covered_by_force_row"]
    ]
    uncalibrated_verified_footer_claims = [
        row["visible_claim_key"]
        for row in footer_claim_coverage_rows
        if row["footer_claim_verified"] and not row["matched_calibrated"]
    ]
    verified_force_claims_absent_from_footer = _verified_force_rows_absent_from_footer(
        footer_claim_rows=visible_footer_claim_rows,
        claim_rows=claim_rows,
    )
    public_stub: dict[str, Any] = {
        "calibration_version": EVIDENCE_FORCE_CALIBRATION_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "policy": policy,
        "artifact_bindings": bindings,
        "claim_force_rows": claim_rows,
        "visible_footer_claim_rows": visible_footer_claim_rows,
        "footer_claim_coverage_rows": footer_claim_coverage_rows,
        "force_raise_rows": force_raise_rows,
        "coverage_gaps": {
            "missing_axis_rows": missing_axes,
            "over_warranted_claim_ids": [row["claim_id"] for row in over_warranted],
            "failed_force_raise_control_ids": [
                row["challenge_id"] for row in unsupported_controls
            ],
            "missing_or_unreproducible_artifacts": missing_artifacts,
            "uncovered_visible_footer_claims": uncovered_visible_footer_claims,
            "uncalibrated_verified_footer_claims": uncalibrated_verified_footer_claims,
            "verified_force_claims_absent_from_footer": (
                verified_force_claims_absent_from_footer
            ),
        },
        "commitments": {
            "claim_force_root": _root(claim_rows, "claim_force_row_hash"),
            "visible_footer_claim_root": _root(
                visible_footer_claim_rows, "visible_footer_claim_row_hash"
            ),
            "footer_claim_coverage_root": _root(
                footer_claim_coverage_rows, "footer_claim_coverage_row_hash"
            ),
            "force_raise_root": _root(force_raise_rows, "force_raise_row_hash"),
            "artifact_binding_root": hash_payload(bindings),
            "schema": EVIDENCE_FORCE_CALIBRATION_SCHEMA,
        },
        "schemas": {
            "evidence_force_calibration": EVIDENCE_FORCE_CALIBRATION_SCHEMA,
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "evidence_sufficiency_report": "docs/schemas/evidence_sufficiency_report.schema.json",
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_payment_account_disclosed": False,
            "public_report_uses_hashes_scores_force_labels_and_actions": True,
        },
    }
    checks = {
        "claim_rows_present": bool(claim_rows),
        "all_required_axes_present": not missing_axes,
        "all_claims_calibrated_to_evidence_force": not over_warranted,
        "support_scores_meet_policy": all(
            row["support_score"] >= policy["min_support_score"]
            and row["confidence"] >= policy["min_confidence"]
            for row in claim_rows
        ),
        "verified_footers_only_for_calibrated_claims": all(
            row["calibrated"] or not row["verified_footer_requested"]
            for row in claim_rows
        ),
        "direct_settlement_only_for_calibrated_claims": all(
            row["calibrated"] or not row["direct_payout_requested"]
            for row in claim_rows
        ),
        "over_warranted_claims_blocked_or_escrowed": all(
            row["calibrated"] or row["safe_action_for_overclaim"] for row in claim_rows
        ),
        "all_visible_footer_claims_have_force_rows": (
            not uncovered_visible_footer_claims
        ),
        "visible_verified_footer_claims_are_force_calibrated": (
            not uncalibrated_verified_footer_claims
        ),
        "verified_force_claims_bind_visible_footer_claims": (
            not verified_force_claims_absent_from_footer
        ),
        "force_raise_controls_rejected": (
            bool(force_raise_rows) and not unsupported_controls
            if policy["require_force_raise_controls"]
            else True
        ),
        "artifact_bindings_reproducible": not missing_artifacts,
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_stub
        ),
        "private_replay_strings_absent": _private_strings_absent(
            public_stub, calibration_input
        ),
    }
    status = "ready" if all(checks.values()) else "failed"
    report = {
        **public_stub,
        "checks": checks,
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "claim_count": len(claim_rows),
            "visible_footer_claim_count": len(visible_footer_claim_rows),
            "footer_claim_coverage_count": sum(
                1 for row in footer_claim_coverage_rows if row["covered_by_force_row"]
            ),
            "uncovered_visible_footer_claim_count": len(
                uncovered_visible_footer_claims
            ),
            "uncalibrated_verified_footer_claim_count": len(
                uncalibrated_verified_footer_claims
            ),
            "calibrated_claim_count": sum(1 for row in claim_rows if row["calibrated"]),
            "over_warranted_claim_count": len(over_warranted),
            "force_raise_control_count": len(force_raise_rows),
            "failed_force_raise_control_count": len(unsupported_controls),
            "max_force_gap": max(
                (row["max_force_gap"] for row in claim_rows), default=0
            ),
            "verified_footer_claim_count": sum(
                1 for row in claim_rows if row["verified_footer_requested"]
            ),
            "direct_payout_claim_count": sum(
                1 for row in claim_rows if row["direct_payout_requested"]
            ),
        },
    }
    report["evidence_force_calibration_hash"] = hash_payload(_hashable_report(report))
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


def validate_evidence_force_calibration_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L119 evidence-force report."""

    errors: list[str] = []
    required = (
        "calibration_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "claim_force_rows",
        "visible_footer_claim_rows",
        "footer_claim_coverage_rows",
        "force_raise_rows",
        "coverage_gaps",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "evidence_force_calibration_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence force calibration field: {key}")
    if report.get("calibration_version") != EVIDENCE_FORCE_CALIBRATION_VERSION:
        errors.append("evidence force calibration version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence force target certification level is unsupported")
    if "evidence_force_calibration" not in report.get("schemas", {}):
        errors.append("missing evidence force calibration schema")
    if _contains_private_fields(report):
        errors.append("evidence force calibration report contains private field")
    for index, row in enumerate(report.get("claim_force_rows", [])):
        for key in (
            "claim_id",
            "claim_hash",
            "evidence_hash",
            "axis_rows",
            "calibrated",
            "claim_force_row_hash",
        ):
            if key not in row:
                errors.append(f"claim force row {index} missing {key}")
    return errors


def verify_evidence_force_calibration_report(
    report: dict[str, Any],
    *,
    calibration_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L119 evidence-force report against its private replay input."""

    errors = validate_evidence_force_calibration_shape(report)
    if hash_payload(_hashable_report(report)) != report.get(
        "evidence_force_calibration_hash"
    ):
        errors.append("evidence force calibration hash is not reproducible")
    expected = make_evidence_force_calibration_report(
        calibration_input,
        issuer=report.get("issuer") or DEFAULT_ISSUER,
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "claim_force_rows",
        "visible_footer_claim_rows",
        "footer_claim_coverage_rows",
        "force_raise_rows",
        "coverage_gaps",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence force calibration {key} does not match inputs")
    if expected.get("evidence_force_calibration_hash") != report.get(
        "evidence_force_calibration_hash"
    ):
        errors.append("evidence force calibration hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("evidence force calibration status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"evidence force calibration check failed: {check}")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence force calibration is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence force calibration signature is invalid")
    return errors
