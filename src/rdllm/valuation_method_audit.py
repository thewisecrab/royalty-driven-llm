"""Audits for residual-corpus valuation methods."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

VALUATION_METHOD_AUDIT_VERSION = "rdllm-valuation-method-audit/v1"
VALUATION_METHOD_AUDIT_SCHEMA = "docs/schemas/valuation_method_audit.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L96"
SCORE_QUANT = Decimal("0.00000001")

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "response_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
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

DECLARED_HASH_FIELDS = (
    "report_hash",
    "summary_hash",
    "contract_hash",
    "attestation_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "graph_hash",
    "trust_registry_hash",
)

DEFAULT_REQUIRED_CASE_TYPES = (
    "known_contributor",
    "hard_antidocument",
    "duplicate_guard",
    "confidence_calibration",
    "rights_denied_escrow",
    "score_stability",
)


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _score(value: Any) -> str:
    return str(_decimal(value).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP))


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


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact)) if artifact else ""


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _policy(audit_input: dict[str, Any]) -> dict[str, Any]:
    configured = dict(audit_input.get("benchmark_policy", {}))
    return {
        "required_case_types": list(
            configured.get("required_case_types", DEFAULT_REQUIRED_CASE_TYPES)
        ),
        "max_mean_absolute_error": str(
            _decimal(configured.get("max_mean_absolute_error", "0.05000000"))
        ),
        "minimum_rank_agreement": str(
            _decimal(configured.get("minimum_rank_agreement", "0.80000000"))
        ),
        "max_antidocument_score": str(
            _decimal(configured.get("max_antidocument_score", "0.01000000"))
        ),
        "max_duplicate_group_share": str(
            _decimal(configured.get("max_duplicate_group_share", "0.55000000"))
        ),
        "max_stability_delta": str(
            _decimal(configured.get("max_stability_delta", "0.05000000"))
        ),
        "minimum_payable_confidence": str(
            _decimal(configured.get("minimum_payable_confidence", "0.50000000"))
        ),
        "minimum_positive_score": str(
            _decimal(configured.get("minimum_positive_score", "0.05000000"))
        ),
        "require_method_commitments": bool(
            configured.get("require_method_commitments", True)
        ),
        "require_privacy_proof_commitment": bool(
            configured.get("require_privacy_proof_commitment", True)
        ),
        "require_residual_scope_separation": bool(
            configured.get("require_residual_scope_separation", True)
        ),
    }


def _residual_indexes(
    residual_report: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str], set[str]]:
    valuation_by_work = {
        str(row.get("work_id", "")): row
        for row in residual_report.get("valuation_rows", [])
    }
    payable_works = {
        str(row.get("work_id", ""))
        for row in residual_report.get("payable_rows", [])
    }
    escrow_works = {
        str(row.get("work_id", ""))
        for row in residual_report.get("escrow_rows", [])
        if row.get("work_id")
    }
    return valuation_by_work, payable_works, escrow_works


def _actual_decision(work_id: str, payable_works: set[str], escrow_works: set[str]) -> str:
    if work_id in payable_works:
        return "payable"
    if work_id in escrow_works:
        return "escrow"
    return "not_payable"


def _method_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "method_id": str(row.get("method_id", f"method:{index}")),
        "method_family": str(row.get("method_family", row.get("method_id", ""))),
        "method_version": str(row.get("method_version", "")),
        "valuation_code_hash": str(row.get("valuation_code_hash", "")),
        "training_value_evidence_root": str(
            row.get("training_value_evidence_root", "")
        ),
        "benchmark_suite_hash": str(row.get("benchmark_suite_hash", "")),
        "privacy_proof_hash": str(row.get("privacy_proof_hash", "")),
        "proof_system": str(row.get("proof_system", "hash_commitment")),
        "zero_knowledge_valuation_supported": bool(
            row.get("zero_knowledge_valuation_supported", False)
        ),
        "zero_knowledge_proof_hash": str(row.get("zero_knowledge_proof_hash", "")),
        "external_implementation_reference_hash": str(
            row.get("external_implementation_reference_hash", "")
        ),
    }
    public["method_commitment_complete"] = bool(
        public["valuation_code_hash"]
        and public["training_value_evidence_root"]
        and public["benchmark_suite_hash"]
    )
    public["privacy_commitment_complete"] = bool(public["privacy_proof_hash"])
    public["zk_or_hash_verifiability_declared"] = bool(
        public["privacy_proof_hash"]
        or (
            public["zero_knowledge_valuation_supported"]
            and public["zero_knowledge_proof_hash"]
        )
    )
    public["method_row_hash"] = hash_payload(public)
    return public


def _benchmark_case_rows(
    audit_input: dict[str, Any],
    residual_report: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    valuation_by_work, payable_works, escrow_works = _residual_indexes(residual_report)
    min_confidence = _decimal(policy["minimum_payable_confidence"])
    min_positive = _decimal(policy["minimum_positive_score"])
    max_antidocument_score = _decimal(policy["max_antidocument_score"])
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(audit_input.get("benchmark_rows", []), start=1):
        work_id = str(row.get("work_id", ""))
        valuation = valuation_by_work.get(work_id, {})
        observed_score = _decimal(
            valuation.get("valuation_score", row.get("observed_score", "0"))
        )
        confidence = _decimal(
            valuation.get("confidence_score", row.get("confidence_score", "0"))
        )
        expected_score = _decimal(row.get("expected_score", observed_score))
        expected_decision = str(row.get("expected_decision", "payable"))
        actual_decision = _actual_decision(work_id, payable_works, escrow_works)
        case_type = str(row.get("case_type", "known_contributor"))
        rank_expected = int(row.get("rank_expected", 0) or 0)
        rank_observed = int(row.get("rank_observed", rank_expected) or 0)
        checks = {
            "evidence_hash_present": bool(row.get("evidence_hash"))
            or bool(valuation.get("valuation_evidence_hash")),
            "score_error_within_threshold": abs(observed_score - expected_score)
            <= _decimal(policy["max_mean_absolute_error"]),
            "rank_matches_expected": (
                rank_expected == 0 or rank_observed == rank_expected
            ),
            "decision_matches_expected": actual_decision == expected_decision
            or (expected_decision == "not_payable" and actual_decision != "payable"),
            "confidence_policy_consistent": (
                confidence >= min_confidence
                if expected_decision == "payable"
                else actual_decision != "payable"
            ),
            "known_contributor_payable": True,
            "hard_antidocument_rejected": True,
        }
        if case_type == "known_contributor":
            checks["known_contributor_payable"] = (
                actual_decision == "payable"
                and observed_score >= min_positive
                and confidence >= min_confidence
            )
        if case_type == "hard_antidocument":
            checks["hard_antidocument_rejected"] = (
                actual_decision != "payable"
                and observed_score <= max_antidocument_score
            )
        public = {
            "benchmark_case_id": str(row.get("benchmark_case_id", f"benchmark:{index}")),
            "case_type": case_type,
            "work_id": work_id,
            "method_id": str(
                row.get("method_id")
                or valuation.get("valuation_method")
                or "unknown_method"
            ),
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "expected_score": _score(expected_score),
            "observed_score": _score(observed_score),
            "score_abs_error": _score(abs(observed_score - expected_score)),
            "confidence_score": _score(confidence),
            "rank_expected": rank_expected,
            "rank_observed": rank_observed,
            "duplicate_group_id": str(row.get("duplicate_group_id", "")),
            "stability_group_id": str(row.get("stability_group_id", "")),
            "evidence_hash": str(
                row.get("evidence_hash")
                or valuation.get("valuation_evidence_hash", "")
            ),
            "valuation_row_hash": str(valuation.get("valuation_row_hash", "")),
            "checks": checks,
        }
        public["benchmark_case_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _duplicate_group_rows(
    benchmark_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in benchmark_rows:
        group_id = row.get("duplicate_group_id")
        if group_id:
            groups.setdefault(str(group_id), []).append(row)
    max_group_share = _decimal(policy["max_duplicate_group_share"])
    rows: list[dict[str, Any]] = []
    for group_id, group_rows in sorted(groups.items()):
        observed_total = sum(_decimal(row["observed_score"]) for row in group_rows)
        expected_total = sum(_decimal(row["expected_score"]) for row in group_rows)
        public = {
            "duplicate_group_id": group_id,
            "case_count": len(group_rows),
            "observed_score_total": _score(observed_total),
            "expected_score_total": _score(expected_total),
            "max_duplicate_group_share": _score(max_group_share),
            "duplicate_inflation_guard_passed": observed_total <= max_group_share,
            "member_case_hashes": [row["benchmark_case_hash"] for row in group_rows],
        }
        public["duplicate_group_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _stability_group_rows(
    benchmark_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in benchmark_rows:
        group_id = row.get("stability_group_id")
        if group_id:
            groups.setdefault(str(group_id), []).append(row)
    max_delta = _decimal(policy["max_stability_delta"])
    rows: list[dict[str, Any]] = []
    for group_id, group_rows in sorted(groups.items()):
        scores = [_decimal(row["observed_score"]) for row in group_rows]
        delta = max(scores) - min(scores) if scores else Decimal("0")
        public = {
            "stability_group_id": group_id,
            "case_count": len(group_rows),
            "score_delta": _score(delta),
            "max_stability_delta": _score(max_delta),
            "stability_guard_passed": delta <= max_delta,
            "member_case_hashes": [row["benchmark_case_hash"] for row in group_rows],
        }
        public["stability_group_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _scorecard(
    benchmark_rows: list[dict[str, Any]],
    duplicate_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    case_count = len(benchmark_rows)
    mean_abs_error = (
        sum(_decimal(row["score_abs_error"]) for row in benchmark_rows) / Decimal(case_count)
        if case_count
        else Decimal("0")
    )
    rank_agreement = (
        sum(1 for row in benchmark_rows if row["checks"]["rank_matches_expected"])
        / case_count
        if case_count
        else 0
    )
    case_types = sorted({row["case_type"] for row in benchmark_rows})
    return {
        "benchmark_case_count": case_count,
        "case_types_covered": case_types,
        "mean_absolute_error": _score(mean_abs_error),
        "max_mean_absolute_error": _score(policy["max_mean_absolute_error"]),
        "rank_agreement": _score(rank_agreement),
        "minimum_rank_agreement": _score(policy["minimum_rank_agreement"]),
        "failed_case_count": sum(
            1 for row in benchmark_rows if not all(row["checks"].values())
        ),
        "duplicate_group_count": len(duplicate_rows),
        "duplicate_group_failure_count": sum(
            1 for row in duplicate_rows if not row["duplicate_inflation_guard_passed"]
        ),
        "stability_group_count": len(stability_rows),
        "stability_group_failure_count": sum(
            1 for row in stability_rows if not row["stability_guard_passed"]
        ),
    }


def load_valuation_method_audit_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_valuation_method_audit_report(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed audit for a residual-corpus valuation method."""

    residual_report = dict(audit_input.get("residual_corpus_royalty_report", {}))
    policy = _policy(audit_input)
    method_rows = [
        _method_row(row, index)
        for index, row in enumerate(audit_input.get("method_cards", []), start=1)
    ]
    method_ids = {row["method_id"] for row in method_rows}
    residual_methods = {
        str(row.get("valuation_method", ""))
        for row in residual_report.get("valuation_rows", [])
        if row.get("valuation_method")
    }
    benchmark_rows = _benchmark_case_rows(audit_input, residual_report, policy)
    duplicate_rows = _duplicate_group_rows(benchmark_rows, policy)
    stability_rows = _stability_group_rows(benchmark_rows, policy)
    scorecard = _scorecard(benchmark_rows, duplicate_rows, stability_rows, policy)
    required_types = set(policy["required_case_types"])
    covered_types = set(scorecard["case_types_covered"])
    residual_scope = residual_report.get("scope", {})
    checks = {
        "residual_report_hash_reproducible": _artifact_hash_is_reproducible(
            residual_report
        ),
        "residual_report_ready_l95": residual_report.get("summary", {}).get("status")
        == "ready"
        and residual_report.get("summary", {}).get("target_certification_level")
        == "RDLLM-L95",
        "residual_scope_separates_visible_and_diffuse_value": (
            bool(residual_scope.get("does_not_replace_user_visible_citations"))
            and bool(residual_scope.get("does_not_double_count_direct_answer_attribution"))
        )
        if policy["require_residual_scope_separation"]
        else True,
        "required_benchmark_case_types_covered": required_types.issubset(covered_types),
        "benchmark_accuracy_within_threshold": _decimal(
            scorecard["mean_absolute_error"]
        )
        <= _decimal(policy["max_mean_absolute_error"]),
        "rank_agreement_within_threshold": _decimal(scorecard["rank_agreement"])
        >= _decimal(policy["minimum_rank_agreement"]),
        "all_benchmark_cases_pass": scorecard["failed_case_count"] == 0,
        "anti_documents_rejected": all(
            row["checks"]["hard_antidocument_rejected"]
            for row in benchmark_rows
            if row["case_type"] == "hard_antidocument"
        ),
        "duplicate_inflation_guard_passed": all(
            row["duplicate_inflation_guard_passed"] for row in duplicate_rows
        )
        and bool(duplicate_rows),
        "confidence_calibration_passed": all(
            row["checks"]["confidence_policy_consistent"] for row in benchmark_rows
        ),
        "score_stability_passed": all(
            row["stability_guard_passed"] for row in stability_rows
        )
        and bool(stability_rows),
        "valuation_methods_cover_residual_rows": bool(residual_methods)
        and residual_methods.issubset(method_ids),
        "valuation_methods_have_commitments": (
            all(row["method_commitment_complete"] for row in method_rows)
            and bool(method_rows)
        )
        if policy["require_method_commitments"]
        else True,
        "privacy_proof_commitments_present": all(
            row["privacy_commitment_complete"]
            and row["zk_or_hash_verifiability_declared"]
            for row in method_rows
        )
        if policy["require_privacy_proof_commitment"]
        else True,
        "private_text_not_disclosed": True,
    }
    status = "ready" if all(checks.values()) else "needs_review"
    report = {
        "version": VALUATION_METHOD_AUDIT_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(audit_input.get("case_id", "valuation-method-audit")),
            "status": status,
        },
        "policy": policy,
        "subject": {
            "residual_corpus_royalty_report_hash": _declared_hash(residual_report),
            "residual_corpus_royalty_version": str(residual_report.get("version", "")),
            "residual_corpus_royalty_status": str(
                residual_report.get("summary", {}).get("status", "")
            ),
            "valuation_row_count": int(
                residual_report.get("summary", {}).get("valuation_row_count", 0) or 0
            ),
            "valuation_methods_used": sorted(residual_methods),
            "valuation_methods_audited": sorted(method_ids),
            "target_input_level": "RDLLM-L95",
        },
        "method_rows": method_rows,
        "benchmark_case_rows": benchmark_rows,
        "duplicate_group_rows": duplicate_rows,
        "stability_group_rows": stability_rows,
        "scorecard": scorecard,
        "checks": checks,
        "privacy": {
            "raw_training_text_disclosed": False,
            "raw_prompt_disclosed": False,
            "raw_output_disclosed": False,
            "raw_validation_dataset_disclosed": False,
            "raw_customer_records_disclosed": False,
            "public_report_uses_hash_commitments": True,
        },
        "schemas": {
            "valuation_method_audit": VALUATION_METHOD_AUDIT_SCHEMA,
            "residual_corpus_royalty_report": (
                "docs/schemas/residual_corpus_royalty_report.schema.json"
            ),
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "benchmark_case_count": scorecard["benchmark_case_count"],
            "case_type_count": len(scorecard["case_types_covered"]),
            "mean_absolute_error": scorecard["mean_absolute_error"],
            "rank_agreement": scorecard["rank_agreement"],
            "failed_case_count": scorecard["failed_case_count"],
            "method_count": len(method_rows),
            "valuation_method_audited": checks["all_benchmark_cases_pass"]
            and checks["valuation_methods_have_commitments"],
            "valuation_methods_cover_residual_rows": checks[
                "valuation_methods_cover_residual_rows"
            ],
            "residual_report_bound": checks["residual_report_hash_reproducible"],
            "anti_gaming_guards_passed": checks["anti_documents_rejected"]
            and checks["duplicate_inflation_guard_passed"]
            and checks["score_stability_passed"],
            "privacy_verifiability_supported": checks[
                "privacy_proof_commitments_present"
            ],
        },
    }
    if _contains_private_fields(report):
        report["checks"]["private_text_not_disclosed"] = False
        report["case"]["status"] = "needs_review"
        report["summary"]["status"] = "needs_review"
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


def validate_valuation_method_audit_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "case",
        "policy",
        "subject",
        "method_rows",
        "benchmark_case_rows",
        "duplicate_group_rows",
        "stability_group_rows",
        "scorecard",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing valuation method audit field: {key}")
    if report.get("version") != VALUATION_METHOD_AUDIT_VERSION:
        errors.append("valuation method audit version is unsupported")
    if "valuation_method_audit" not in report.get("schemas", {}):
        errors.append("missing valuation method audit schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("valuation method audit target level is incorrect")
    return errors


def verify_valuation_method_audit_report(
    report: dict[str, Any],
    audit_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a valuation method audit report against benchmark evidence."""

    errors = validate_valuation_method_audit_report_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("report_hash", ""):
        errors.append("valuation method audit report hash is not reproducible")
    expected = make_valuation_method_audit_report(
        audit_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at"),
        signing_secret=signing_secret,
    )
    comparable_keys = (
        "case",
        "policy",
        "subject",
        "method_rows",
        "benchmark_case_rows",
        "duplicate_group_rows",
        "stability_group_rows",
        "scorecard",
        "checks",
        "privacy",
        "schemas",
        "summary",
    )
    for key in comparable_keys:
        if report.get(key) != expected.get(key):
            errors.append(f"valuation method audit {key} does not match evidence")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("valuation method audit report hash does not match evidence")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("valuation method audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if not passed:
            errors.append(f"valuation method audit check failed: {check}")
    if _contains_private_fields(report) or any(
        private and private in canonical_json(report)
        for private in audit_input.get("private_strings", [])
    ):
        errors.append("valuation method audit report discloses private text")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("valuation method audit report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("valuation method audit report signature is invalid")
    return errors
