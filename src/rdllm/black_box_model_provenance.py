"""Black-box provenance challenges for undisclosed derivative models."""

from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

BLACK_BOX_MODEL_PROVENANCE_VERSION = "rdllm-black-box-model-provenance/v1"
BLACK_BOX_MODEL_PROVENANCE_SCHEMA = (
    "docs/schemas/black_box_model_provenance_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L92"
DEFAULT_PROVENANCE_CHALLENGE_RATE = Decimal("0.10")
DEFAULT_CONFIDENCE_LEVEL = Decimal("0.95")
DEFAULT_MIN_EFFECT = Decimal("0.10")
DEFAULT_MIN_CHALLENGE_COUNT = 3
DEFAULT_WATERMARK_THRESHOLD = Decimal("0.80")
DEFAULT_FINGERPRINT_THRESHOLD = Decimal("0.80")
MONEY_QUANT = Decimal("0.000001")
WEIGHT_QUANT = Decimal("0.00000001")
SCORE_QUANT = Decimal("0.000001")
PRIVATE_TEXT_FIELDS = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "response_text",
    "source_text",
    "training_text",
    "document_text",
}


def _decimal(value: Decimal | str | float | int | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal | str | float | int | None) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _score(value: Decimal | str | float | int | None) -> str:
    return str(_clamp(_decimal(value)).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP))


def _weight(value: Decimal | str | float | int | None) -> str:
    return str(_decimal(value).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP))


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _public_source_row(row: dict[str, Any]) -> dict[str, Any]:
    public = {
        "creator_id": str(row.get("creator_id", "")),
        "creator_name": str(row.get("creator_name", "")),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": str(row.get("chunk_id", "")),
        "source_label": str(row.get("source_label", row.get("label", ""))),
        "content_hash": str(row.get("content_hash", "")),
        "source_uri_hash": stable_hash(str(row.get("source_uri", "")))
        if row.get("source_uri")
        else "",
        "license_status": str(row.get("license_status", "active")),
        "allowed_uses": sorted(str(item) for item in row.get("allowed_uses", [])),
        "derivative_model_use_allowed": bool(
            row.get("derivative_model_use_allowed", row.get("training_allowed", True))
        ),
        "contribution_weight": _weight(
            row.get("contribution_weight", row.get("normalized_weight", "1"))
        ),
        "source_evidence_hash": str(
            row.get("source_evidence_hash", row.get("answer_card_source_entry_hash", ""))
        ),
    }
    public["source_row_hash"] = str(row.get("source_row_hash") or hash_payload(public))
    return public


def _source_row_hash_valid(row: dict[str, Any]) -> bool:
    if not row.get("source_row_hash"):
        return True
    candidate = dict(row)
    declared = str(candidate.pop("source_row_hash", ""))
    return declared == hash_payload(candidate)


def _source_derivative_allowed(row: dict[str, Any]) -> bool:
    allowed_uses = set(str(item) for item in row.get("allowed_uses", []))
    return (
        row.get("license_status", "active") == "active"
        and bool(row.get("derivative_model_use_allowed", row.get("training_allowed", True)))
        and (
            "model_derivative" in allowed_uses
            or "distillation" in allowed_uses
            or "training" in allowed_uses
            or "attribution_required_derivative" in allowed_uses
        )
    )


def _candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_model_id", candidate.get("model_id", "")))


def _candidate_label(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_label", candidate.get("label", _candidate_id(candidate))))


def _component_score(row: dict[str, Any]) -> Decimal:
    if row.get("overall_score") is not None:
        return _clamp(_decimal(row.get("overall_score")))
    fields = (
        "output_similarity_score",
        "behavior_similarity_score",
        "refusal_vector_similarity",
        "watermark_score",
        "protected_probe_score",
    )
    values = [_clamp(_decimal(row[field])) for field in fields if row.get(field) is not None]
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _challenge_candidate_rows(
    challenge: dict[str, Any], candidate_id: str
) -> list[dict[str, Any]]:
    rows = challenge.get("candidate_scores", [])
    if isinstance(rows, dict):
        row = rows.get(candidate_id)
        return [row] if isinstance(row, dict) else []
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("candidate_model_id", row.get("model_id", ""))) == candidate_id
    ]


def _baseline_scores(challenges: list[dict[str, Any]]) -> list[Decimal]:
    scores: list[Decimal] = []
    for challenge in challenges:
        for value in challenge.get("baseline_similarity_scores", []):
            scores.append(_clamp(_decimal(value)))
        for row in challenge.get("baseline_scores", []):
            if isinstance(row, dict):
                scores.append(_component_score(row))
            else:
                scores.append(_clamp(_decimal(row)))
    return scores


def _empirical_p_value(candidate_mean: Decimal, baseline_scores: list[Decimal]) -> Decimal:
    if not baseline_scores:
        return Decimal("1")
    exceedances = sum(1 for score in baseline_scores if score >= candidate_mean)
    return (Decimal(exceedances) + Decimal("1")) / (Decimal(len(baseline_scores)) + Decimal("1"))


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _challenge_rows(
    challenges: list[dict[str, Any]], candidate_ids: set[str]
) -> list[dict[str, Any]]:
    rows = []
    for challenge in challenges:
        score_count = 0
        for candidate_id in candidate_ids:
            score_count += len(_challenge_candidate_rows(challenge, candidate_id))
        rows.append(
            {
                "challenge_id": str(challenge.get("challenge_id", "")),
                "prompt_hash": str(
                    challenge.get("prompt_hash")
                    or stable_hash(str(challenge.get("prompt_text", "")))
                ),
                "challenged_output_hash": str(
                    challenge.get("challenged_output_hash")
                    or stable_hash(str(challenge.get("output_text", "")))
                ),
                "query_commitment_hash": str(
                    challenge.get("query_commitment_hash")
                    or hash_payload(
                        {
                            "challenge_id": str(challenge.get("challenge_id", "")),
                            "prompt_hash": str(
                                challenge.get("prompt_hash")
                                or stable_hash(str(challenge.get("prompt_text", "")))
                            ),
                            "challenged_output_hash": str(
                                challenge.get("challenged_output_hash")
                                or stable_hash(str(challenge.get("output_text", "")))
                            ),
                        }
                    )
                ),
                "evidence_hash": str(
                    challenge.get("evidence_hash")
                    or challenge.get("transcript_hash")
                    or challenge.get("api_trace_hash", "")
                ),
                "baseline_score_count": len(challenge.get("baseline_similarity_scores", []))
                + len(challenge.get("baseline_scores", [])),
                "candidate_score_count": score_count,
            }
        )
    return rows


def _candidate_evidence_row(
    candidate: dict[str, Any],
    challenges: list[dict[str, Any]],
    baseline_scores: list[Decimal],
    *,
    candidate_count: int,
    min_challenge_count: int,
    min_effect: Decimal,
    alpha: Decimal,
    watermark_threshold: Decimal,
    fingerprint_threshold: Decimal,
) -> dict[str, Any]:
    candidate_id = _candidate_id(candidate)
    score_rows = []
    scores = []
    watermark_support_count = 0
    fingerprint_support_count = 0
    for challenge in challenges:
        rows = _challenge_candidate_rows(challenge, candidate_id)
        if not rows:
            continue
        best_row = max(rows, key=_component_score)
        score_value = _component_score(best_row)
        scores.append(score_value)
        watermark_score = _clamp(_decimal(best_row.get("watermark_score", "0")))
        fingerprint_score = _clamp(
            _decimal(
                best_row.get(
                    "refusal_vector_similarity",
                    best_row.get("behavior_fingerprint_score", "0"),
                )
            )
        )
        watermark_positive = bool(
            watermark_score >= watermark_threshold
            and best_row.get("watermark_key_attested", True)
        )
        fingerprint_positive = fingerprint_score >= fingerprint_threshold
        watermark_support_count += int(watermark_positive)
        fingerprint_support_count += int(fingerprint_positive)
        score_rows.append(
            {
                "challenge_id": str(challenge.get("challenge_id", "")),
                "prompt_hash": str(
                    challenge.get("prompt_hash")
                    or stable_hash(str(challenge.get("prompt_text", "")))
                ),
                "challenged_output_hash": str(
                    challenge.get("challenged_output_hash")
                    or stable_hash(str(challenge.get("output_text", "")))
                ),
                "overall_score": _score(score_value),
                "output_similarity_score": _score(best_row.get("output_similarity_score", score_value)),
                "behavior_similarity_score": _score(
                    best_row.get("behavior_similarity_score", score_value)
                ),
                "refusal_vector_similarity": _score(
                    best_row.get("refusal_vector_similarity", "0")
                ),
                "watermark_score": _score(best_row.get("watermark_score", "0")),
                "watermark_key_attested": bool(
                    best_row.get("watermark_key_attested", False)
                ),
            }
        )

    candidate_mean = _mean(scores)
    baseline_mean = _mean(baseline_scores)
    effect = max(Decimal("0"), candidate_mean - baseline_mean)
    empirical_p = _empirical_p_value(candidate_mean, baseline_scores)
    adjusted_p = min(Decimal("1"), empirical_p * Decimal(max(candidate_count, 1)))
    sufficient_samples = len(scores) >= min_challenge_count
    statistical_detection = (
        sufficient_samples and effect >= min_effect and adjusted_p <= alpha
    )
    watermark_detection = (
        sufficient_samples
        and watermark_support_count >= max(2, min_challenge_count // 2)
        and effect >= min_effect
    )
    fingerprint_detection = (
        sufficient_samples
        and fingerprint_support_count >= max(2, min_challenge_count // 2)
        and effect >= min_effect
    )
    included = statistical_detection or watermark_detection or fingerprint_detection
    if included:
        decision = "model_provenance_set_member"
    elif not sufficient_samples:
        decision = "candidate_insufficient_black_box_samples"
    else:
        decision = "candidate_excluded_by_black_box_test"

    source_rows = [_public_source_row(row) for row in candidate.get("source_rows", [])]
    return {
        "candidate_model_id_hash": stable_hash(candidate_id),
        "candidate_label": _candidate_label(candidate),
        "candidate_model_hash": str(candidate.get("candidate_model_hash", "")),
        "candidate_family_hash": stable_hash(str(candidate.get("model_family", "")))
        if candidate.get("model_family")
        else "",
        "owner_id": str(candidate.get("owner_id", "")),
        "declared_by_challenged_model": bool(
            candidate.get("declared_by_challenged_model", False)
        ),
        "disclosed_lineage_report_hash": str(
            candidate.get("disclosed_lineage_report_hash", "")
        ),
        "source_rows": source_rows,
        "source_row_count": len(source_rows),
        "score_count": len(scores),
        "mean_candidate_score": _score(candidate_mean),
        "mean_baseline_score": _score(baseline_mean),
        "effect_over_baseline": _score(effect),
        "empirical_p_value": _score(empirical_p),
        "multiple_testing_adjusted_p_value": _score(adjusted_p),
        "watermark_support_count": watermark_support_count,
        "fingerprint_support_count": fingerprint_support_count,
        "score_rows": score_rows,
        "checks": {
            "minimum_challenge_count_met": sufficient_samples,
            "baseline_distribution_present": bool(baseline_scores),
            "multiple_testing_control_applied": True,
            "statistical_threshold_met": statistical_detection,
            "watermark_threshold_met": watermark_detection,
            "fingerprint_threshold_met": fingerprint_detection,
            "source_rows_hash_valid": all(
                _source_row_hash_valid(row) for row in candidate.get("source_rows", [])
            ),
        },
        "decision": decision,
    }


def _allocate_settlement(
    provenance_rows: list[dict[str, Any]],
    *,
    creator_pool: Decimal,
    provenance_challenge_rate: Decimal,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Decimal, Decimal]:
    unresolved = [
        row
        for row in provenance_rows
        if not row["declared_by_challenged_model"]
        and not row.get("disclosed_lineage_report_hash")
    ]
    challenge_pool = (
        creator_pool * provenance_challenge_rate if unresolved else Decimal("0")
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    if not unresolved:
        return [], [], challenge_pool, creator_pool - challenge_pool

    total_signal = sum(
        _decimal(row["effect_over_baseline"]) for row in unresolved
    ) or Decimal("1")
    obligations: list[dict[str, Any]] = []
    escrow_rows: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    for candidate_index, row in enumerate(unresolved):
        if candidate_index == len(unresolved) - 1:
            candidate_pool = challenge_pool - paid_so_far
        else:
            candidate_pool = (
                challenge_pool
                * _decimal(row["effect_over_baseline"])
                / total_signal
            ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            paid_so_far += candidate_pool

        source_rows = row.get("source_rows", [])
        valid_sources = [
            source for source in source_rows if _source_derivative_allowed(source)
        ]
        if not valid_sources:
            escrow_rows.append(
                {
                    "escrow_id": f"escrow:black-box-model-provenance:{candidate_index + 1}",
                    "candidate_model_id_hash": row["candidate_model_id_hash"],
                    "recipient_creator_id": "creator:black_box_model_provenance_escrow",
                    "amount": _money(candidate_pool),
                    "reason": "candidate_source_rights_missing_or_revoked",
                }
            )
            continue
        total_weight = sum(
            _decimal(source.get("contribution_weight", "1")) for source in valid_sources
        ) or Decimal("1")
        source_paid = Decimal("0")
        for source_index, source in enumerate(valid_sources):
            if source_index == len(valid_sources) - 1:
                amount = candidate_pool - source_paid
            else:
                amount = (
                    candidate_pool
                    * _decimal(source.get("contribution_weight", "1"))
                    / total_weight
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
                source_paid += amount
            obligations.append(
                {
                    "obligation_id": (
                        f"black-box-model-provenance:{candidate_index + 1}:{source_index + 1}"
                    ),
                    "candidate_model_id_hash": row["candidate_model_id_hash"],
                    "recipient_creator_id": source["creator_id"],
                    "creator_name": source["creator_name"],
                    "work_id": source["work_id"],
                    "chunk_id": source["chunk_id"],
                    "source_row_hash": source["source_row_hash"],
                    "basis": "undisclosed_derivative_model_black_box_provenance",
                    "amount": _money(amount),
                }
            )
    return obligations, escrow_rows, challenge_pool, creator_pool - challenge_pool


def _contains_private_text_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_TEXT_FIELDS:
                return True
            if _contains_private_text_field(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_text_field(child) for child in value)
    return False


def load_black_box_model_provenance_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_black_box_model_provenance_report(
    audit_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = Decimal("0.55"),
    provenance_challenge_rate: Decimal | str | float = DEFAULT_PROVENANCE_CHALLENGE_RATE,
    confidence_level: Decimal | str | float = DEFAULT_CONFIDENCE_LEVEL,
    min_effect: Decimal | str | float = DEFAULT_MIN_EFFECT,
    min_challenge_count: int = DEFAULT_MIN_CHALLENGE_COUNT,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public report for black-box derivative-model provenance tests."""

    challenged_model = dict(audit_input.get("challenged_model", {}))
    candidates = [dict(row) for row in audit_input.get("candidate_models", [])]
    challenges = [dict(row) for row in audit_input.get("challenge_set", [])]
    candidate_ids = {_candidate_id(candidate) for candidate in candidates}
    baseline = _baseline_scores(challenges)
    confidence = _decimal(confidence_level)
    if confidence <= 0 or confidence >= 1:
        raise ValueError("confidence_level must be between 0 and 1")
    alpha = Decimal("1") - confidence
    gross = _decimal(gross_revenue)
    pool_rate = _decimal(creator_pool_rate)
    if gross < 0:
        raise ValueError("gross_revenue must be non-negative")
    if pool_rate < 0 or pool_rate > 1:
        raise ValueError("creator_pool_rate must be between 0 and 1")
    challenge_rate = _decimal(provenance_challenge_rate)
    if challenge_rate < 0 or challenge_rate > 1:
        raise ValueError("provenance_challenge_rate must be between 0 and 1")
    minimum_effect = _decimal(min_effect)
    creator_pool = (gross * pool_rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    challenge_rows = _challenge_rows(challenges, candidate_ids)
    evidence_rows = [
        _candidate_evidence_row(
            candidate,
            challenges,
            baseline,
            candidate_count=len(candidates),
            min_challenge_count=min_challenge_count,
            min_effect=minimum_effect,
            alpha=alpha,
            watermark_threshold=DEFAULT_WATERMARK_THRESHOLD,
            fingerprint_threshold=DEFAULT_FINGERPRINT_THRESHOLD,
        )
        for candidate in candidates
    ]
    provenance_set = [
        row for row in evidence_rows if row["decision"] == "model_provenance_set_member"
    ]
    obligations, escrow_rows, challenge_pool, residual_pool = _allocate_settlement(
        provenance_set,
        creator_pool=creator_pool,
        provenance_challenge_rate=challenge_rate,
    )
    obligation_total = sum(_decimal(row["amount"]) for row in obligations)
    escrow_total = sum(_decimal(row["amount"]) for row in escrow_rows)
    unresolved_count = sum(
        1
        for row in provenance_set
        if not row["declared_by_challenged_model"]
        and not row.get("disclosed_lineage_report_hash")
    )
    minimum_challenges_ok = len(challenge_rows) >= min_challenge_count
    baseline_ok = len(baseline) >= min_challenge_count
    candidate_scores_ok = all(
        row["score_count"] >= min_challenge_count
        for row in evidence_rows
        if row["decision"] == "model_provenance_set_member"
    )
    confidence_ok = all(
        _decimal(row["multiple_testing_adjusted_p_value"]) <= alpha
        or row["watermark_support_count"] >= max(2, min_challenge_count // 2)
        or row["fingerprint_support_count"] >= max(2, min_challenge_count // 2)
        for row in provenance_set
    )
    checks = {
        "minimum_black_box_challenge_count_met": minimum_challenges_ok,
        "baseline_distribution_present": baseline_ok,
        "candidate_scores_present": bool(evidence_rows),
        "model_provenance_set_constructed": bool(provenance_set),
        "multiple_testing_control_applied": True,
        "provenance_set_confidence_level_met": confidence_ok,
        "candidate_member_sample_counts_met": candidate_scores_ok,
        "undisclosed_derivative_challenge_settled_or_escrowed": (
            unresolved_count == 0
            or (obligation_total + escrow_total == challenge_pool and challenge_pool > 0)
        ),
        "creator_pool_conserved": creator_pool == challenge_pool + residual_pool,
        "black_box_private_text_not_disclosed": True,
    }
    status = "ready" if all(checks.values()) else "needs_review"
    if not provenance_set and minimum_challenges_ok and baseline_ok and bool(evidence_rows):
        status = "ready_no_derivative_signal"
    if unresolved_count:
        challenge_decision = "undisclosed_derivative_challenge_ready"
    elif provenance_set:
        challenge_decision = "declared_or_authorized_provenance_confirmed"
    else:
        challenge_decision = "no_derivative_signal"

    footer_rows = []
    for row in provenance_set:
        for source in row.get("source_rows", []):
            footer_rows.append(
                {
                    "candidate_model_id_hash": row["candidate_model_id_hash"],
                    "candidate_label": row["candidate_label"],
                    "confidence_level": str(confidence),
                    "source_row_hash": source["source_row_hash"],
                    "creator_id": source["creator_id"],
                    "creator_name": source["creator_name"],
                    "work_id": source["work_id"],
                    "chunk_id": source["chunk_id"],
                    "source_label": source["source_label"],
                    "basis": "black_box_model_provenance_footer",
                }
            )

    report = {
        "version": BLACK_BOX_MODEL_PROVENANCE_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "audit": {
            "audit_id": str(audit_input.get("audit_id", "")),
            "auditor_id": str(audit_input.get("auditor_id", "")),
            "method": "black_box_model_provenance_set",
            "confidence_level": str(confidence),
            "alpha": str(alpha),
            "minimum_effect_over_baseline": _score(minimum_effect),
            "minimum_challenge_count": int(min_challenge_count),
        },
        "challenged_model": {
            "model_id_hash": stable_hash(str(challenged_model.get("model_id", ""))),
            "provider_id": str(challenged_model.get("provider_id", "")),
            "endpoint_hash": stable_hash(str(challenged_model.get("endpoint", "")))
            if challenged_model.get("endpoint")
            else "",
            "declared_model_lineage_report_hash": str(
                challenged_model.get("declared_model_lineage_report_hash", "")
            ),
        },
        "challenge_rows": challenge_rows,
        "candidate_evidence": evidence_rows,
        "model_provenance_set": provenance_set,
        "model_provenance_footer_rows": footer_rows,
        "settlement_obligations": obligations,
        "escrow_rows": escrow_rows,
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool_rate": str(pool_rate),
            "creator_pool": _money(creator_pool),
            "provenance_challenge_rate": str(challenge_rate),
            "provenance_challenge_pool": _money(challenge_pool),
            "residual_creator_pool": _money(residual_pool),
            "settlement_obligation_total": _money(obligation_total),
            "escrow_total": _money(escrow_total),
        },
        "checks": checks,
        "privacy": {
            "prompt_text_disclosed": False,
            "output_text_disclosed": False,
            "source_text_disclosed": False,
            "report_uses_hashes_and_scores_only": True,
        },
        "schemas": {
            "black_box_model_provenance_report": BLACK_BOX_MODEL_PROVENANCE_SCHEMA
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "challenged_model_hash": stable_hash(str(challenged_model.get("model_id", ""))),
            "challenge_decision": challenge_decision,
            "challenge_count": len(challenge_rows),
            "candidate_model_count": len(evidence_rows),
            "baseline_score_count": len(baseline),
            "model_provenance_set_count": len(provenance_set),
            "undisclosed_candidate_count": unresolved_count,
            "footer_row_count": len(footer_rows),
            "settlement_obligation_count": len(obligations),
            "escrow_row_count": len(escrow_rows),
            "provenance_challenge_pool": _money(challenge_pool),
            "creator_pool_conserved": checks["creator_pool_conserved"],
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


def validate_black_box_model_provenance_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "audit",
        "challenged_model",
        "challenge_rows",
        "candidate_evidence",
        "model_provenance_set",
        "model_provenance_footer_rows",
        "settlement_obligations",
        "escrow_rows",
        "economics",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing black-box model provenance report field: {key}")
    if report.get("version") != BLACK_BOX_MODEL_PROVENANCE_VERSION:
        errors.append("black-box model provenance report version is unsupported")
    for key in ("confidence_level", "minimum_challenge_count", "alpha"):
        if key not in report.get("audit", {}):
            errors.append(f"missing black-box model provenance audit field: {key}")
    if "black_box_model_provenance_report" not in report.get("schemas", {}):
        errors.append("missing black-box model provenance schema")
    return errors


def verify_black_box_model_provenance_report(
    report: dict[str, Any],
    audit_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a black-box model provenance report against private challenge evidence."""

    errors = validate_black_box_model_provenance_report_shape(report)
    report_hash = report.get("report_hash", "")
    if hash_payload(_hashable_report(report)) != report_hash:
        errors.append("black-box model provenance report hash is not reproducible")

    expected = make_black_box_model_provenance_report(
        audit_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=report.get("economics", {}).get("creator_pool_rate", "0.55"),
        provenance_challenge_rate=report.get("economics", {}).get(
            "provenance_challenge_rate", DEFAULT_PROVENANCE_CHALLENGE_RATE
        ),
        confidence_level=report.get("audit", {}).get(
            "confidence_level", DEFAULT_CONFIDENCE_LEVEL
        ),
        min_effect=report.get("audit", {}).get(
            "minimum_effect_over_baseline", DEFAULT_MIN_EFFECT
        ),
        min_challenge_count=int(
            report.get("audit", {}).get(
                "minimum_challenge_count", DEFAULT_MIN_CHALLENGE_COUNT
            )
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at"),
        signing_secret=signing_secret,
    )
    comparable_keys = (
        "audit",
        "challenged_model",
        "challenge_rows",
        "candidate_evidence",
        "model_provenance_set",
        "model_provenance_footer_rows",
        "settlement_obligations",
        "escrow_rows",
        "economics",
        "checks",
        "privacy",
        "schemas",
        "summary",
    )
    for key in comparable_keys:
        if report.get(key) != expected.get(key):
            errors.append(f"black-box model provenance report {key} does not match evidence")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("black-box model provenance report hash does not match evidence")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("black-box model provenance target level is incorrect")
    if report.get("summary", {}).get("status") not in {"ready", "ready_no_derivative_signal"}:
        errors.append("black-box model provenance report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if not passed and check != "model_provenance_set_constructed":
            errors.append(f"black-box model provenance check failed: {check}")
    if _contains_private_text_field(report):
        errors.append("black-box model provenance report discloses private text")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("black-box model provenance report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("black-box model provenance report signature is invalid")
    return errors
