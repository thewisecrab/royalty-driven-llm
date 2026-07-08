"""Model-lineage attribution for distilled or fine-tuned downstream models."""

from __future__ import annotations

import json
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

MODEL_LINEAGE_ATTRIBUTION_VERSION = "rdllm-model-lineage-attribution/v1"
MODEL_LINEAGE_ATTRIBUTION_SCHEMA = (
    "docs/schemas/model_lineage_attribution_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L91"
DEFAULT_MODEL_LINEAGE_RATE = Decimal("0.20")
MONEY_QUANT = Decimal("0.000001")
WEIGHT_QUANT = Decimal("0.00000001")

DISTILLATION_METHODS = {
    "distillation",
    "teacher_distillation",
    "on_policy_distillation",
    "synthetic_distillation",
    "rlvr_distillation",
}


def _decimal(value: Decimal | str | float | int | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal | str | float | int | None) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _weight(value: Decimal | str | float | int | None) -> str:
    return str(_decimal(value).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP))


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
        if key
        not in {
            "summary_hash",
            "report_hash",
            "card_hash",
            "envelope_hash",
            "capsule_hash",
            "signature",
        }
    }


def _declared_artifact_hash(artifact: dict[str, Any]) -> str:
    for field in ("summary_hash", "report_hash", "card_hash", "envelope_hash", "capsule_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_artifact_hash(artifact)
    return hash_payload(_hashable_artifact(artifact)) == declared


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
        "training_allowed": bool(row.get("training_allowed", True)),
        "contribution_weight": _weight(row.get("contribution_weight", row.get("normalized_weight", "1"))),
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


def _source_training_allowed(row: dict[str, Any]) -> bool:
    allowed_uses = set(str(item) for item in row.get("allowed_uses", []))
    return (
        row.get("license_status", "active") == "active"
        and bool(row.get("training_allowed", True))
        and ("training" in allowed_uses or "distillation" in allowed_uses)
    )


def _training_method(training_run: dict[str, Any], item: dict[str, Any]) -> str:
    return str(item.get("training_method", training_run.get("method", ""))).lower()


def _requires_teacher_evidence(method: str, item: dict[str, Any]) -> bool:
    return (
        method in DISTILLATION_METHODS
        or "distill" in method
        or bool(item.get("teacher_model_id"))
    )


def _has_teacher_evidence(item: dict[str, Any]) -> bool:
    return bool(
        item.get("teacher_distribution_root")
        or item.get("teacher_logits_hash")
        or item.get("teacher_output_hash")
        or item.get("teacher_trace_hash")
    )


def _training_item_public_row(
    item: dict[str, Any],
    training_run: dict[str, Any],
    *,
    duplicate: bool,
) -> dict[str, Any]:
    method = _training_method(training_run, item)
    source_rows = [_public_source_row(row) for row in item.get("source_rows", [])]
    synthetic_generated = bool(item.get("synthetic_generated", item.get("synthetic", False)))
    synthetic_disclosed = bool(
        item.get(
            "synthetic_disclosed",
            training_run.get("synthetic_data_disclosed", False),
        )
    )
    teacher_required = _requires_teacher_evidence(method, item)
    teacher_evidence_present = (not teacher_required) or _has_teacher_evidence(item)
    license_allowed = bool(source_rows) and all(_source_training_allowed(row) for row in source_rows)
    source_hashes_valid = all(_source_row_hash_valid(row) for row in source_rows)
    positive_weight = _decimal(item.get("training_weight", "1")) > 0
    lineage_enabled = bool(training_run.get("lineage_tracking_enabled", True))
    artifact_hash = str(item.get("artifact_hash", ""))
    item_hash = str(item.get("item_hash", ""))
    hidden_synthetic = synthetic_generated and not synthetic_disclosed

    if duplicate:
        decision = "duplicate_training_item_held"
    elif not positive_weight or not item_hash or not artifact_hash:
        decision = "model_lineage_invalid_training_item"
    elif hidden_synthetic:
        decision = "model_lineage_hidden_synthetic_failed"
    elif not lineage_enabled:
        decision = "model_lineage_tracking_missing_failed"
    elif not teacher_evidence_present:
        decision = "model_lineage_teacher_evidence_missing_failed"
    elif not source_rows:
        decision = "model_lineage_unattributed_escrow"
    elif not license_allowed or not source_hashes_valid:
        decision = "model_lineage_rights_escrow"
    else:
        decision = "accepted_model_lineage"

    row = {
        "item_id": str(item.get("item_id", "")),
        "item_hash": item_hash,
        "artifact_type": str(item.get("artifact_type", "")),
        "artifact_hash": artifact_hash,
        "training_method": method,
        "training_weight": _weight(item.get("training_weight", "1")),
        "teacher_model_id_hash": stable_hash(str(item.get("teacher_model_id", "")))
        if item.get("teacher_model_id")
        else "",
        "teacher_distribution_root": str(item.get("teacher_distribution_root", "")),
        "teacher_output_hash": str(item.get("teacher_output_hash", "")),
        "synthetic_generated": synthetic_generated,
        "synthetic_disclosed": synthetic_disclosed,
        "source_row_count": len(source_rows),
        "source_rows": source_rows,
        "checks": {
            "positive_training_weight": positive_weight,
            "lineage_tracking_enabled": lineage_enabled,
            "artifact_hash_present": bool(artifact_hash),
            "item_hash_present": bool(item_hash),
            "synthetic_source_disclosed": not hidden_synthetic,
            "teacher_evidence_present": teacher_evidence_present,
            "source_rows_present": bool(source_rows),
            "source_training_rights_valid": license_allowed,
            "source_row_hashes_valid": source_hashes_valid,
            "duplicate_not_overpaid": not duplicate,
        },
        "decision": decision,
    }
    row["training_item_row_hash"] = hash_payload(
        {key: value for key, value in row.items() if key != "training_item_row_hash"}
    )
    return row


def _deduplicated_training_rows(
    model_input: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    training_run = model_input.get("training_run", {})
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    for item in model_input.get("training_items", []):
        dedupe_key = str(item.get("artifact_hash") or item.get("item_hash") or item.get("item_id", ""))
        duplicate = bool(dedupe_key and dedupe_key in seen)
        if dedupe_key:
            seen.add(dedupe_key)
        row = _training_item_public_row(item, training_run, duplicate=duplicate)
        rows.append(row)
        if duplicate:
            duplicate_rows.append(row)
    return rows, duplicate_rows


def _item_pool_rows(
    rows: list[dict[str, Any]],
    *,
    model_lineage_pool: Decimal,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unique_rows = [
        row
        for row in rows
        if row["decision"] != "duplicate_training_item_held"
        and _decimal(row["training_weight"]) > 0
    ]
    total_weight = sum((_decimal(row["training_weight"]) for row in unique_rows), Decimal("0"))
    accepted_rows: list[dict[str, Any]] = []
    escrow_rows: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    for index, row in enumerate(unique_rows):
        if total_weight <= 0:
            item_pool = Decimal("0")
        elif index == len(unique_rows) - 1:
            item_pool = model_lineage_pool - paid_so_far
        else:
            item_pool = (model_lineage_pool * _decimal(row["training_weight"]) / total_weight).quantize(
                MONEY_QUANT,
                rounding=ROUND_HALF_UP,
            )
            paid_so_far += item_pool
        item_payload = {
            "item_id": row["item_id"],
            "item_hash": row["item_hash"],
            "artifact_hash": row["artifact_hash"],
            "decision": row["decision"],
            "share_of_model_lineage_pool": _weight(
                _decimal(row["training_weight"]) / total_weight if total_weight > 0 else 0
            ),
            "item_pool": _money(item_pool),
            "training_item_row_hash": row["training_item_row_hash"],
        }
        item_payload["item_pool_hash"] = hash_payload(item_payload)
        if row["decision"] == "accepted_model_lineage":
            accepted_rows.append(item_payload)
        else:
            escrow = {
                **item_payload,
                "escrow_id": f"escrow:model-lineage:{row['item_id'] or index + 1}",
                "escrow_reason": row["decision"],
                "recipient_creator_id": "creator:model_lineage_escrow",
                "work_id": "escrow:model_lineage",
                "payout": item_payload["item_pool"],
            }
            escrow["escrow_hash"] = hash_payload(escrow)
            escrow_rows.append(escrow)
    return accepted_rows, escrow_rows


def _settlement_obligations(
    *,
    training_rows: list[dict[str, Any]],
    item_pool_rows: list[dict[str, Any]],
    usage: dict[str, Any],
    student_model: dict[str, Any],
) -> list[dict[str, Any]]:
    rows_by_hash = {row["training_item_row_hash"]: row for row in training_rows}
    obligations: list[dict[str, Any]] = []
    for item_index, item_pool in enumerate(item_pool_rows):
        training_row = rows_by_hash.get(item_pool["training_item_row_hash"], {})
        sources = training_row.get("source_rows", [])
        total_source_weight = sum(
            (_decimal(source.get("contribution_weight", "0")) for source in sources),
            Decimal("0"),
        )
        paid_so_far = Decimal("0")
        item_pool_amount = _decimal(item_pool["item_pool"])
        for source_index, source in enumerate(sources):
            source_share = (
                _decimal(source.get("contribution_weight", "0")) / total_source_weight
                if total_source_weight > 0
                else Decimal("0")
            )
            if source_index == len(sources) - 1:
                payout = item_pool_amount - paid_so_far
            else:
                payout = (item_pool_amount * source_share).quantize(
                    MONEY_QUANT,
                    rounding=ROUND_HALF_UP,
                )
                paid_so_far += payout
            obligation = {
                "obligation_id": f"model-lineage:{usage.get('event_id', 'event')}:{item_index + 1}:{source_index + 1}",
                "basis": "downstream_model_usage_inherits_training_lineage",
                "recipient_creator_id": source["creator_id"],
                "recipient_creator_name": source["creator_name"],
                "work_id": source["work_id"],
                "chunk_id": source["chunk_id"],
                "source_row_hash": source["source_row_hash"],
                "training_item_row_hash": training_row.get("training_item_row_hash", ""),
                "student_model_id": str(student_model.get("model_id", "")),
                "student_model_version": str(student_model.get("model_version", "")),
                "usage_event_id": str(usage.get("event_id", "")),
                "usage_event_hash": str(usage.get("event_hash", "")),
                "share_of_item_pool": _weight(source_share),
                "payout": _money(payout),
            }
            obligation["obligation_hash"] = hash_payload(obligation)
            obligations.append(obligation)
    return obligations


def _lineage_footer_rows(obligations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    totals: defaultdict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for obligation in obligations:
        key = (
            obligation["recipient_creator_id"],
            obligation["work_id"],
            obligation["chunk_id"],
        )
        if key not in grouped:
            grouped[key] = {
                "creator_id": obligation["recipient_creator_id"],
                "creator_name": obligation["recipient_creator_name"],
                "work_id": obligation["work_id"],
                "chunk_id": obligation["chunk_id"],
                "basis": "model_lineage_training_inheritance",
                "source_row_hash": obligation["source_row_hash"],
            }
        totals[key] += _decimal(obligation["payout"])
    footer_rows = []
    for key, row in sorted(grouped.items()):
        payload = dict(row)
        payload["payout"] = _money(totals[key])
        payload["footer_row_hash"] = hash_payload(payload)
        footer_rows.append(payload)
    return footer_rows


def _private_strings(model_input: dict[str, Any]) -> list[str]:
    values = [str(item) for item in model_input.get("private_strings", [])]
    for item in model_input.get("training_items", []):
        for key in ("raw_text", "prompt", "output", "training_example", "teacher_output"):
            if item.get(key):
                values.append(str(item[key]))
        for source in item.get("source_rows", []):
            for key in ("source_text", "quote", "evidence_text"):
                if source.get(key):
                    values.append(str(source[key]))
    usage = model_input.get("student_usage", {})
    for key in ("prompt", "output", "answer_text"):
        if usage.get(key):
            values.append(str(usage[key]))
    return [value for value in values if len(value) >= 16]


def load_model_lineage_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_model_lineage_attribution_report(
    model_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = Decimal("0.55"),
    model_lineage_rate: Decimal | str | float = DEFAULT_MODEL_LINEAGE_RATE,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report for royalties inherited through model training lineage."""

    gross = _decimal(gross_revenue)
    pool_rate = _decimal(creator_pool_rate)
    lineage_rate = _decimal(model_lineage_rate)
    if pool_rate < 0 or pool_rate > 1:
        raise ValueError("creator_pool_rate must be between 0 and 1")
    if lineage_rate < 0 or lineage_rate > 1:
        raise ValueError("model_lineage_rate must be between 0 and 1")

    student_model = dict(model_input.get("student_model", {}))
    training_run = dict(model_input.get("training_run", {}))
    training_summary = deepcopy(model_input.get("training_content_summary", {}))
    usage = dict(model_input.get("student_usage", {}))
    creator_pool = _decimal(usage.get("creator_pool"), default=str(gross * pool_rate))
    model_lineage_pool = (creator_pool * lineage_rate).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    residual_pool = creator_pool - model_lineage_pool

    training_rows, duplicate_rows = _deduplicated_training_rows(model_input)
    accepted_item_pools, escrow_rows = _item_pool_rows(
        training_rows,
        model_lineage_pool=model_lineage_pool,
    )
    obligations = _settlement_obligations(
        training_rows=training_rows,
        item_pool_rows=accepted_item_pools,
        usage=usage,
        student_model=student_model,
    )
    footer_rows = _lineage_footer_rows(obligations)
    direct_total = sum((_decimal(row["payout"]) for row in obligations), Decimal("0"))
    escrow_total = sum((_decimal(row["payout"]) for row in escrow_rows), Decimal("0"))
    hidden_synthetic_rows = [
        row for row in training_rows if row["decision"] == "model_lineage_hidden_synthetic_failed"
    ]
    missing_teacher_rows = [
        row
        for row in training_rows
        if row["decision"] == "model_lineage_teacher_evidence_missing_failed"
    ]
    checks = {
        "student_model_bound": bool(student_model.get("model_id"))
        and bool(student_model.get("model_version")),
        "training_run_bound": bool(training_run.get("run_id"))
        and bool(training_run.get("method")),
        "training_summary_hash_reproducible": _artifact_hash_reproducible(training_summary),
        "training_lineage_declared": bool(training_run.get("lineage_tracking_enabled", True)),
        "all_synthetic_training_disclosed": not hidden_synthetic_rows,
        "distillation_evidence_bound": not missing_teacher_rows,
        "duplicate_training_items_not_overpaid": all(
            row["decision"] == "duplicate_training_item_held" for row in duplicate_rows
        ),
        "accepted_training_items_present": bool(accepted_item_pools),
        "direct_payout_or_escrow_conserved": direct_total + escrow_total
        == model_lineage_pool,
        "creator_pool_conserved": creator_pool == model_lineage_pool + residual_pool,
        "footer_rows_present_for_direct_payout": bool(footer_rows)
        if direct_total > 0
        else True,
        "no_private_text_disclosed": True,
    }
    report = {
        "report_version": MODEL_LINEAGE_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "student_model": {
            "provider": str(student_model.get("provider", "")),
            "model_id": str(student_model.get("model_id", "")),
            "model_version": str(student_model.get("model_version", "")),
            "base_model_id": str(student_model.get("base_model_id", "")),
            "model_card_hash": str(student_model.get("model_card_hash", "")),
        },
        "training_run": {
            "run_id": str(training_run.get("run_id", "")),
            "method": str(training_run.get("method", "")),
            "stage": str(training_run.get("stage", "")),
            "dataset_hash": str(training_run.get("dataset_hash", "")),
            "lineage_tracking_enabled": bool(
                training_run.get("lineage_tracking_enabled", True)
            ),
            "synthetic_data_disclosed": bool(
                training_run.get("synthetic_data_disclosed", False)
            ),
            "training_content_summary_hash": _declared_artifact_hash(training_summary)
            if training_summary
            else "",
        },
        "student_usage": {
            "event_id": str(usage.get("event_id", "")),
            "event_hash": str(usage.get("event_hash", "")),
            "usage_hash": hash_payload(
                {
                    key: value
                    for key, value in usage.items()
                    if key not in {"prompt", "output", "answer_text"}
                }
            ),
            "creator_pool": _money(creator_pool),
        },
        "model_lineage_policy": {
            "profile": MODEL_LINEAGE_ATTRIBUTION_VERSION,
            "model_lineage_rate": str(lineage_rate),
            "trigger": "student_model_trained_or_distilled_from_attributed_outputs_or_synthetic_data",
            "distillation_and_fine_tuning_cannot_extinguish_upstream_royalties": True,
            "synthetic_training_must_be_disclosed": True,
            "duplicate_training_artifacts_do_not_inflate_credit": True,
            "future_usage_pool_split": "model_lineage_pool_then_residual_local_pool",
        },
        "training_items": training_rows,
        "accepted_training_item_pools": accepted_item_pools,
        "usage_settlement_obligations": obligations,
        "escrow_rows": escrow_rows,
        "model_lineage_footer_rows": footer_rows,
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool_rate": str(pool_rate),
            "creator_pool": _money(creator_pool),
            "model_lineage_pool": _money(model_lineage_pool),
            "residual_pool": _money(residual_pool),
            "direct_payout_total": _money(direct_total),
            "escrow_total": _money(escrow_total),
        },
        "checks": checks,
        "commitments": {
            "student_model_hash": hash_payload(student_model),
            "training_run_hash": hash_payload(training_run),
            "training_summary_hash": _declared_artifact_hash(training_summary)
            if training_summary
            else "",
            "student_usage_hash": hash_payload(
                {
                    key: value
                    for key, value in usage.items()
                    if key not in {"prompt", "output", "answer_text"}
                }
            ),
            "training_item_root": hash_payload(training_rows),
            "accepted_item_pool_root": hash_payload(accepted_item_pools),
            "obligation_root": hash_payload(obligations),
            "escrow_root": hash_payload(escrow_rows),
            "footer_root": hash_payload(footer_rows),
            "policy_hash": hash_payload(
                {
                    "profile": MODEL_LINEAGE_ATTRIBUTION_VERSION,
                    "model_lineage_rate": str(lineage_rate),
                }
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "student_model_id": str(student_model.get("model_id", "")),
            "training_item_count": len(training_rows),
            "accepted_training_item_count": len(accepted_item_pools),
            "duplicate_training_item_count": len(duplicate_rows),
            "hidden_synthetic_failure_count": len(hidden_synthetic_rows),
            "missing_teacher_evidence_count": len(missing_teacher_rows),
            "escrow_item_count": len(escrow_rows),
            "settlement_obligation_count": len(obligations),
            "footer_row_count": len(footer_rows),
            "creator_pool_conserved": checks["creator_pool_conserved"],
            "model_lineage_pool_conserved": checks[
                "direct_payout_or_escrow_conserved"
            ],
            "model_lineage_pool": _money(model_lineage_pool),
        },
        "privacy": {
            "training_text_disclosed": False,
            "teacher_output_text_disclosed": False,
            "student_prompt_text_disclosed": False,
            "student_output_text_disclosed": False,
            "source_text_disclosed": False,
            "public_report_uses_hashes_source_ids_and_model_metadata": True,
        },
        "schemas": {
            "model_lineage_attribution_report": MODEL_LINEAGE_ATTRIBUTION_SCHEMA
        },
    }
    report_json = canonical_json(report)
    leaked = [value for value in _private_strings(model_input) if value in report_json]
    if leaked:
        report["checks"]["no_private_text_disclosed"] = False
        report["summary"]["status"] = "failed"
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


def validate_model_lineage_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "student_model",
        "training_run",
        "student_usage",
        "model_lineage_policy",
        "training_items",
        "accepted_training_item_pools",
        "usage_settlement_obligations",
        "escrow_rows",
        "model_lineage_footer_rows",
        "economics",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing model-lineage attribution report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != MODEL_LINEAGE_ATTRIBUTION_VERSION:
        errors.append("model-lineage attribution report version is unsupported")
    for key in ("model_id", "model_version"):
        if key not in report.get("student_model", {}):
            errors.append(f"missing student model field: {key}")
    for key in ("run_id", "method", "training_content_summary_hash"):
        if key not in report.get("training_run", {}):
            errors.append(f"missing model-lineage training run field: {key}")
    for key in ("model_lineage_rate", "synthetic_training_must_be_disclosed"):
        if key not in report.get("model_lineage_policy", {}):
            errors.append(f"missing model-lineage policy field: {key}")
    for key in ("training_item_root", "obligation_root", "policy_hash"):
        if key not in report.get("commitments", {}):
            errors.append(f"missing model-lineage commitment: {key}")
    if "model_lineage_attribution_report" not in report.get("schemas", {}):
        errors.append("missing model-lineage attribution schema")
    return errors


def verify_model_lineage_attribution_report(
    report: dict[str, Any],
    model_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a model-lineage attribution report against private training evidence."""

    errors = validate_model_lineage_attribution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("model-lineage attribution report hash is not reproducible")

    expected = make_model_lineage_attribution_report(
        model_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=report.get("economics", {}).get("creator_pool_rate", "0.55"),
        model_lineage_rate=report.get("model_lineage_policy", {}).get(
            "model_lineage_rate", DEFAULT_MODEL_LINEAGE_RATE
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "student_model",
        "training_run",
        "student_usage",
        "model_lineage_policy",
        "training_items",
        "accepted_training_item_pools",
        "usage_settlement_obligations",
        "escrow_rows",
        "model_lineage_footer_rows",
        "economics",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"model-lineage attribution report {key} does not match evidence")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("model-lineage attribution report hash does not match evidence")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("model-lineage attribution report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"model-lineage attribution check failed: {check}")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("model-lineage attribution target level is incorrect")

    report_json = canonical_json(report)
    for private in _private_strings(model_input):
        if private in report_json:
            errors.append("model-lineage attribution report discloses private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("model-lineage attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("model-lineage attribution report signature is invalid")

    return errors
