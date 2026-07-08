"""Calibrated attribution-confidence reports for RDLLM responses."""

from __future__ import annotations

import math
from typing import Any

from rdllm.decision_provenance import verify_decision_provenance_report
from rdllm.evidence_sufficiency import validate_evidence_sufficiency_report_shape
from rdllm.provenance_eval import validate_provenance_evaluation_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_confidence import validate_source_confidence_report_shape

CALIBRATED_ATTRIBUTION_VERSION = "rdllm-calibrated-attribution-confidence/v1"
CALIBRATED_ATTRIBUTION_SCHEMA = "docs/schemas/calibrated_attribution_report.schema.json"
CALIBRATION_POLICY_VERSION = "rdllm-calibrated-attribution-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L63"
MIN_CALIBRATION_CASES = 5
MIN_CLAIM_LOWER_BOUND = 0.50
MIN_FOOTER_LOWER_BOUND = 0.50
MIN_PAYOUT_LOWER_BOUND = 0.20
PRODUCTION_RECOMMENDED_LOWER_BOUND = 0.90

DECLARED_HASH_FIELDS = (
    "report_hash",
    "envelope_hash",
    "card_hash",
    "contract_hash",
    "receipt_hash",
    "trace_hash",
    "capsule_hash",
    "gate_hash",
    "summary_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "hidden_state",
    "token_logits",
    "private_trace",
    "customer_email",
    "bank_account",
    "account_number",
    "tax_id",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
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
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _rate(summary: dict[str, Any], key: str) -> float:
    try:
        return max(0.0, min(1.0, float(summary.get(key, 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _wilson_lower_bound(successes: int, total: int, *, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    phat = successes / total
    denom = 1 + (z * z / total)
    centre = phat + (z * z / (2 * total))
    margin = z * math.sqrt((phat * (1 - phat) + (z * z / (4 * total))) / total)
    return round(max(0.0, (centre - margin) / denom), 8)


def _bound_row(name: str, observed_rate: float, sample_count: int) -> dict[str, Any]:
    successes = int(round(observed_rate * sample_count))
    row = {
        "metric": name,
        "observed_rate": round(observed_rate, 8),
        "sample_count": sample_count,
        "success_count": successes,
        "method": "wilson_lower_bound_95",
        "lower_bound": _wilson_lower_bound(successes, sample_count),
    }
    row["bound_hash"] = hash_payload(row)
    return row


def _calibration_evidence(provenance_evaluation_report: dict[str, Any]) -> dict[str, Any]:
    summary = provenance_evaluation_report.get("summary", {})
    sample_count = int(summary.get("case_count", 0) or 0)
    rows = [
        _bound_row("top1_accuracy", _rate(summary, "top1_accuracy"), sample_count),
        _bound_row("decoy_resistance_rate", _rate(summary, "decoy_resistance_rate"), sample_count),
        _bound_row("grounding_verified_rate", _rate(summary, "grounding_verified_rate"), sample_count),
        _bound_row("escrow_accuracy", _rate(summary, "escrow_accuracy"), sample_count),
        _bound_row("mean_expected_recall", _rate(summary, "mean_expected_recall"), sample_count),
        _bound_row("mean_paid_source_precision", _rate(summary, "mean_paid_source_precision"), sample_count),
    ]
    by_metric = {row["metric"]: row for row in rows}
    claim_lower = min(
        by_metric["top1_accuracy"]["lower_bound"],
        by_metric["decoy_resistance_rate"]["lower_bound"],
        by_metric["grounding_verified_rate"]["lower_bound"],
        by_metric["mean_expected_recall"]["lower_bound"],
    )
    footer_lower = min(
        by_metric["top1_accuracy"]["lower_bound"],
        by_metric["grounding_verified_rate"]["lower_bound"],
        by_metric["mean_expected_recall"]["lower_bound"],
    )
    payout_lower = min(
        by_metric["mean_paid_source_precision"]["lower_bound"],
        by_metric["escrow_accuracy"]["lower_bound"],
        by_metric["mean_expected_recall"]["lower_bound"],
    )
    evidence = {
        "benchmark_profile": provenance_evaluation_report.get("benchmark", {}).get("profile", ""),
        "benchmark_case_count": sample_count,
        "benchmark_case_root": provenance_evaluation_report.get("benchmark", {}).get("case_root", ""),
        "calibration_method": "binomial_wilson_lower_bound_95_over_benchmark_rates",
        "metric_bounds": rows,
        "global_lower_bounds": {
            "claim_grounding_lower_bound": round(claim_lower, 8),
            "footer_attribution_lower_bound": round(footer_lower, 8),
            "payout_participation_lower_bound": round(payout_lower, 8),
        },
        "production_recommended_lower_bound": PRODUCTION_RECOMMENDED_LOWER_BOUND,
    }
    evidence["calibration_evidence_hash"] = hash_payload(evidence)
    return evidence


def _claim_sufficiency_by_index(
    evidence_sufficiency_report: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for claim in evidence_sufficiency_report.get("claims", []):
        index = int(claim.get("claim_index", 0) or 0)
        if index:
            rows[index] = claim
    return rows


def _decision_ids(decision_provenance_report: dict[str, Any], decision_type: str) -> set[str]:
    return {
        str(node.get("node_id", ""))
        for node in decision_provenance_report.get("decision_nodes", [])
        if node.get("decision_type") == decision_type
    }


def _source_confidence_by_label(source_confidence_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("label", "")): row
        for row in source_confidence_report.get("sources", [])
        if row.get("label")
    }


def _claim_rows(
    *,
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    decision_provenance_report: dict[str, Any],
    calibration_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    sufficiency_by_index = _claim_sufficiency_by_index(evidence_sufficiency_report)
    claim_decision_ids = _decision_ids(decision_provenance_report, "claim_grounding")
    claim_global = float(calibration_evidence["global_lower_bounds"]["claim_grounding_lower_bound"])
    rows: list[dict[str, Any]] = []
    for claim in source_confidence_report.get("claims", []):
        index = int(claim.get("claim_index", 0) or 0)
        sufficiency = sufficiency_by_index.get(index, {})
        decision_id = f"claim_decision:{index}"
        confidence_score = float(claim.get("confidence_score", 0.0) or 0.0)
        support_score = float(claim.get("support_score", 0.0) or 0.0)
        top_support = float(sufficiency.get("top_support_score", support_score) or 0.0)
        decoy_margin = float(sufficiency.get("decoy_margin", 0.0) or 0.0)
        decoy_score = min(1.0, max(0.0, decoy_margin / max(0.000001, float(sufficiency.get("minimum_decoy_margin", 0.15) or 0.15))))
        decision_present = decision_id in claim_decision_ids
        raw_confidence = min(
            confidence_score,
            support_score,
            top_support,
            decoy_score,
            1.0 if sufficiency.get("sufficient") is True else 0.0,
            1.0 if decision_present else 0.0,
        )
        calibrated = round(min(raw_confidence, claim_global), 8)
        row = {
            "claim_index": index,
            "claim_hash": claim.get("claim_hash", ""),
            "source_label": claim.get("source_label", ""),
            "evidence_span_prefix": claim.get("evidence_span_prefix", ""),
            "decision_node_id": decision_id,
            "decision_node_present": decision_present,
            "confidence_report_score": round(confidence_score, 8),
            "claim_support_score": round(support_score, 8),
            "top_support_score": round(top_support, 8),
            "decoy_margin": round(decoy_margin, 8),
            "evidence_sufficient": sufficiency.get("sufficient") is True,
            "raw_evidence_confidence": round(raw_confidence, 8),
            "global_claim_lower_bound": round(claim_global, 8),
            "calibrated_lower_bound": calibrated,
            "release_mode": (
                "claim_release_supported"
                if calibrated >= MIN_CLAIM_LOWER_BOUND
                else "hold_for_review"
            ),
        }
        row["claim_calibration_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _source_rows(
    *,
    source_confidence_report: dict[str, Any],
    decision_provenance_report: dict[str, Any],
    calibration_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    footer_decision_ids = _decision_ids(decision_provenance_report, "visible_attribution_footer")
    payout_decision_ids = _decision_ids(decision_provenance_report, "royalty_participation")
    footer_global = float(calibration_evidence["global_lower_bounds"]["footer_attribution_lower_bound"])
    payout_global = float(calibration_evidence["global_lower_bounds"]["payout_participation_lower_bound"])
    rows: list[dict[str, Any]] = []
    for source in source_confidence_report.get("sources", []):
        label = str(source.get("label", ""))
        footer_decision_id = f"footer_decision:{label}"
        payout_decision_id = f"payout_decision:{label}"
        confidence_score = float(source.get("confidence_score", 0.0) or 0.0)
        source_verified = source.get("confidence_level") == "verified"
        footer_present = footer_decision_id in footer_decision_ids
        payout_present = payout_decision_id in payout_decision_ids
        raw_footer = min(confidence_score, 1.0 if source_verified else 0.0, 1.0 if footer_present else 0.0)
        raw_payout = min(confidence_score, 1.0 if source_verified else 0.0, 1.0 if payout_present else 0.0)
        footer_bound = round(min(raw_footer, footer_global), 8)
        payout_bound = round(min(raw_payout, payout_global), 8)
        row = {
            "label": label,
            "work_id": source.get("work_id", ""),
            "creator_id": source.get("creator_id", ""),
            "content_hash_prefix": source.get("content_hash_prefix", ""),
            "footer_decision_node_id": footer_decision_id,
            "footer_decision_node_present": footer_present,
            "payout_decision_node_id": payout_decision_id,
            "payout_decision_node_present": payout_present,
            "confidence_report_score": round(confidence_score, 8),
            "source_confidence_level": source.get("confidence_level", ""),
            "raw_footer_confidence": round(raw_footer, 8),
            "raw_payout_confidence": round(raw_payout, 8),
            "global_footer_lower_bound": round(footer_global, 8),
            "global_payout_lower_bound": round(payout_global, 8),
            "calibrated_footer_lower_bound": footer_bound,
            "calibrated_payout_lower_bound": payout_bound,
            "footer_mode": (
                "display_as_calibrated"
                if footer_bound >= MIN_FOOTER_LOWER_BOUND
                else "display_with_warning_or_hold"
            ),
            "payout_mode": (
                "pay_with_calibrated_uncertainty"
                if payout_bound >= MIN_PAYOUT_LOWER_BOUND
                else "escrow_until_more_calibration"
            ),
        }
        row["source_calibration_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _artifact_status(
    *,
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    provenance_evaluation_report: dict[str, Any],
    decision_provenance_report: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    signing_secret: str | None,
) -> dict[str, Any]:
    decision_errors = verify_decision_provenance_report(
        decision_provenance_report,
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        signing_secret=signing_secret,
    )
    return {
        "response_envelope_verified": not verify_response_envelope(
            response_envelope,
            signing_secret=signing_secret,
        ),
        "source_confidence_shape_valid": not validate_source_confidence_report_shape(
            source_confidence_report
        ),
        "source_confidence_status_verified": source_confidence_report.get("summary", {}).get("status") == "verified",
        "evidence_sufficiency_shape_valid": not validate_evidence_sufficiency_report_shape(
            evidence_sufficiency_report
        ),
        "evidence_sufficiency_status_verified": evidence_sufficiency_report.get("summary", {}).get("status") == "verified",
        "provenance_evaluation_shape_valid": not validate_provenance_evaluation_shape(
            provenance_evaluation_report
        ),
        "provenance_evaluation_status_passed": provenance_evaluation_report.get("summary", {}).get("status") == "passed",
        "decision_provenance_verified": not decision_errors,
        "decision_provenance_errors": decision_errors,
        "response_envelope_hash_reproducible": _artifact_hash_is_reproducible(response_envelope),
        "source_confidence_hash_reproducible": _artifact_hash_is_reproducible(source_confidence_report),
        "evidence_sufficiency_hash_reproducible": _artifact_hash_is_reproducible(evidence_sufficiency_report),
        "provenance_evaluation_hash_reproducible": _artifact_hash_is_reproducible(provenance_evaluation_report),
        "decision_provenance_hash_reproducible": _artifact_hash_is_reproducible(decision_provenance_report),
    }


def make_calibrated_attribution_report(
    *,
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    provenance_evaluation_report: dict[str, Any],
    decision_provenance_report: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed confidence-calibration report for visible attribution."""

    calibration_evidence = _calibration_evidence(provenance_evaluation_report)
    claim_rows = _claim_rows(
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        decision_provenance_report=decision_provenance_report,
        calibration_evidence=calibration_evidence,
    )
    source_rows = _source_rows(
        source_confidence_report=source_confidence_report,
        decision_provenance_report=decision_provenance_report,
        calibration_evidence=calibration_evidence,
    )
    artifact_status = _artifact_status(
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        provenance_evaluation_report=provenance_evaluation_report,
        decision_provenance_report=decision_provenance_report,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        signing_secret=signing_secret,
    )
    private_field_paths = _contains_private_fields(
        {
            "calibration_evidence": calibration_evidence,
            "claims": claim_rows,
            "sources": source_rows,
        }
    )
    checks = {
        "artifact_statuses_verified": all(
            value is True
            for key, value in artifact_status.items()
            if key != "decision_provenance_errors"
        ),
        "calibration_case_count_meets_floor": (
            calibration_evidence["benchmark_case_count"] >= MIN_CALIBRATION_CASES
        ),
        "all_claims_have_calibrated_lower_bounds": all(
            row["calibrated_lower_bound"] >= MIN_CLAIM_LOWER_BOUND
            for row in claim_rows
        ),
        "all_visible_sources_have_calibrated_footer_bounds": all(
            row["calibrated_footer_lower_bound"] >= MIN_FOOTER_LOWER_BOUND
            for row in source_rows
        ),
        "all_payout_rows_have_calibrated_bounds_or_escrow": all(
            (
                row["calibrated_payout_lower_bound"] >= MIN_PAYOUT_LOWER_BOUND
                or row["payout_mode"] == "escrow_until_more_calibration"
            )
            for row in source_rows
        ),
        "decision_provenance_bound": artifact_status["decision_provenance_verified"],
        "private_fields_absent": not private_field_paths,
    }
    issue_list = []
    if private_field_paths:
        issue_list.append(
            {
                "issue_type": "private_field_leak",
                "severity": "high",
                "paths": private_field_paths,
            }
        )
    for row in claim_rows:
        if row["calibrated_lower_bound"] < MIN_CLAIM_LOWER_BOUND:
            issue_list.append(
                {
                    "issue_type": "claim_calibration_below_floor",
                    "severity": "high",
                    "claim_index": row["claim_index"],
                    "calibrated_lower_bound": row["calibrated_lower_bound"],
                }
            )
    for row in source_rows:
        if row["calibrated_footer_lower_bound"] < MIN_FOOTER_LOWER_BOUND:
            issue_list.append(
                {
                    "issue_type": "footer_calibration_below_floor",
                    "severity": "high",
                    "source_label": row["label"],
                    "calibrated_lower_bound": row["calibrated_footer_lower_bound"],
                }
            )
        if row["calibrated_payout_lower_bound"] < MIN_PAYOUT_LOWER_BOUND:
            issue_list.append(
                {
                    "issue_type": "payout_calibration_escrow",
                    "severity": "medium",
                    "source_label": row["label"],
                    "calibrated_lower_bound": row["calibrated_payout_lower_bound"],
                }
            )
    status = "verified" if all(checks.values()) and not issue_list else "failed"
    report = {
        "report_version": CALIBRATED_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": source_confidence_report.get("event", {}).get("event_id", ""),
            "event_hash": source_confidence_report.get("event", {}).get("event_hash", ""),
            "rendered_output_hash": source_confidence_report.get("event", {}).get(
                "rendered_output_hash",
                "",
            ),
            "response_envelope_hash": _declared_hash(response_envelope),
            "source_confidence_report_hash": _declared_hash(source_confidence_report),
            "evidence_sufficiency_report_hash": _declared_hash(evidence_sufficiency_report),
            "provenance_evaluation_report_hash": _declared_hash(provenance_evaluation_report),
            "decision_provenance_report_hash": _declared_hash(decision_provenance_report),
        },
        "policy": {
            "policy_version": CALIBRATION_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_calibration_cases": MIN_CALIBRATION_CASES,
            "minimum_claim_lower_bound": MIN_CLAIM_LOWER_BOUND,
            "minimum_footer_lower_bound": MIN_FOOTER_LOWER_BOUND,
            "minimum_payout_lower_bound": MIN_PAYOUT_LOWER_BOUND,
            "production_recommended_lower_bound": PRODUCTION_RECOMMENDED_LOWER_BOUND,
            "requires_claim_footer_payout_bounds": True,
            "requires_decision_provenance_binding": True,
        },
        "artifact_status": artifact_status,
        "calibration_evidence": calibration_evidence,
        "claims": claim_rows,
        "sources": source_rows,
        "checks": checks,
        "issues": issue_list,
        "commitments": {
            "claim_calibration_root": hash_payload(claim_rows),
            "source_calibration_root": hash_payload(source_rows),
            "calibration_evidence_hash": calibration_evidence["calibration_evidence_hash"],
            "artifact_status_hash": hash_payload(artifact_status),
            "issue_root": hash_payload(issue_list),
            "schema": CALIBRATED_ATTRIBUTION_SCHEMA,
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "claim_count": len(claim_rows),
            "source_count": len(source_rows),
            "calibration_case_count": calibration_evidence["benchmark_case_count"],
            "issue_count": len(issue_list),
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "minimum_claim_lower_bound_observed": (
                min(row["calibrated_lower_bound"] for row in claim_rows)
                if claim_rows
                else 1.0
            ),
            "minimum_footer_lower_bound_observed": (
                min(row["calibrated_footer_lower_bound"] for row in source_rows)
                if source_rows
                else 1.0
            ),
            "minimum_payout_lower_bound_observed": (
                min(row["calibrated_payout_lower_bound"] for row in source_rows)
                if source_rows
                else 1.0
            ),
            "uncertainty_disclosure_required": True,
        },
        "schemas": {
            "calibrated_attribution_report": CALIBRATED_ATTRIBUTION_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_confidence_report": "docs/schemas/source_confidence_report.schema.json",
            "evidence_sufficiency_report": "docs/schemas/evidence_sufficiency_report.schema.json",
            "provenance_evaluation_report": "docs/schemas/provenance_evaluation_report.schema.json",
            "decision_provenance_report": "docs/schemas/decision_provenance_report.schema.json",
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payout_account_disclosed": False,
            "report_uses_hashes_bounds_scores_and_decision_ids": True,
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


def validate_calibrated_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "artifact_status",
        "calibration_evidence",
        "claims",
        "sources",
        "checks",
        "issues",
        "commitments",
        "summary",
        "schemas",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing calibrated attribution report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CALIBRATED_ATTRIBUTION_VERSION:
        errors.append("calibrated attribution report version is unsupported")
    if report.get("policy", {}).get("policy_version") != CALIBRATION_POLICY_VERSION:
        errors.append("calibrated attribution policy version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("calibrated attribution target certification level is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "response_envelope_hash",
        "source_confidence_report_hash",
        "evidence_sufficiency_report_hash",
        "provenance_evaluation_report_hash",
        "decision_provenance_report_hash",
    ):
        if key not in report.get("event", {}):
            errors.append(f"missing calibrated attribution event field: {key}")
    for claim in report.get("claims", []):
        for key in (
            "claim_index",
            "claim_hash",
            "source_label",
            "calibrated_lower_bound",
            "release_mode",
            "claim_calibration_hash",
        ):
            if key not in claim:
                errors.append(f"missing calibrated attribution claim field: {key}")
    for source in report.get("sources", []):
        for key in (
            "label",
            "work_id",
            "calibrated_footer_lower_bound",
            "calibrated_payout_lower_bound",
            "footer_mode",
            "payout_mode",
            "source_calibration_hash",
        ):
            if key not in source:
                errors.append(f"missing calibrated attribution source field: {key}")
    if "calibrated_attribution_report" not in report.get("schemas", {}):
        errors.append("missing calibrated attribution schema")
    return errors


def verify_calibrated_attribution_report(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    provenance_evaluation_report: dict[str, Any],
    decision_provenance_report: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify calibrated attribution confidence against public proof artifacts."""

    errors = validate_calibrated_attribution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("calibrated attribution report hash is not reproducible")

    expected = make_calibrated_attribution_report(
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        provenance_evaluation_report=provenance_evaluation_report,
        decision_provenance_report=decision_provenance_report,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "policy",
        "artifact_status",
        "calibration_evidence",
        "claims",
        "sources",
        "checks",
        "issues",
        "commitments",
        "summary",
        "schemas",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"calibrated attribution report {key} does not match artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("calibrated attribution report hash does not match artifacts")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("calibrated attribution report status is not verified")
    if report.get("summary", {}).get("issue_count") != 0:
        errors.append("calibrated attribution report contains issues")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"calibrated attribution check failed: {check}")

    rendered = canonical_json(report)
    for private_literal in (
        "source text",
        "evidence text",
        "hidden state",
        "bank account",
    ):
        if private_literal in rendered:
            errors.append(f"calibrated attribution report exposes private literal {private_literal}")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("calibrated attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("calibrated attribution report signature is invalid")
    return errors
