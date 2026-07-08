"""Post-training signal provenance receipts.

This layer covers preference labels, reward-model scores, verifier outcomes,
RLAIF critiques, RLHF/RLVR traces, and other post-training signals. These
signals can change a foundation model without appearing as ordinary training
items or answer citations, so RDLLM treats them as provenance-bearing artifacts
with source labels, upstream proof hashes, license terms, and royalty carry-forward.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.artifact_refs import resolve_artifact_refs
from rdllm.model_lineage_attribution import verify_model_lineage_attribution_report
from rdllm.private_reasoning_attribution import (
    verify_private_reasoning_attribution_receipt,
)
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

POST_TRAINING_SIGNAL_PROVENANCE_VERSION = (
    "rdllm-post-training-signal-provenance/v1"
)
POST_TRAINING_SIGNAL_PROVENANCE_SCHEMA = (
    "docs/schemas/post_training_signal_provenance.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L108"
MINIMUM_PRIVATE_REASONING_LEVEL = "RDLLM-L107"
MINIMUM_MODEL_LINEAGE_LEVEL = "RDLLM-L91"

DECLARED_HASH_FIELDS = (
    "post_training_signal_provenance_hash",
    "private_reasoning_attribution_hash",
    "persistent_memory_provenance_hash",
    "client_enforcement_hash",
    "source_footer_delivery_hash",
    "tool_ledger_hash",
    "conversation_ledger_hash",
    "proof_response_hash",
    "report_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "preference_text",
    "feedback_text",
    "critique_text",
    "reward_explanation_text",
    "verifier_rationale",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
    "scratchpad_text",
    "hidden_trace",
    "private_trace",
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


def load_post_training_signal_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a post-training signal provenance receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"post_training_signal_provenance_hash", "signature"}
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
        return True
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(receipt: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(receipt)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("-1")


def _signal_payload_hash(signal: dict[str, Any]) -> str:
    if signal.get("signal_payload_hash"):
        return str(signal["signal_payload_hash"])
    for key in (
        "private_feedback_text",
        "feedback_text",
        "preference_text",
        "critique_text",
        "reward_explanation_text",
    ):
        if signal.get(key):
            return stable_hash(str(signal[key]))
    return ""


def _reward_commitment_hash(signal: dict[str, Any]) -> str:
    if signal.get("reward_commitment_hash"):
        return str(signal["reward_commitment_hash"])
    if "reward_value" in signal:
        return stable_hash(f"reward:{signal.get('reward_value')}")
    if signal.get("label"):
        return stable_hash(f"label:{signal.get('label')}")
    return ""


def _update_commitment_hash(signal: dict[str, Any]) -> str:
    if signal.get("update_commitment_hash"):
        return str(signal["update_commitment_hash"])
    if signal.get("optimizer_update_hash"):
        return str(signal["optimizer_update_hash"])
    if signal.get("used_for_update") is True:
        return stable_hash(f"post-training-update:{signal.get('signal_id', '')}")
    return ""


def _signal_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for signal in sorted(
        receipt_input.get("post_training_signals", []),
        key=lambda item: (
            int(item.get("sequence", 0) or 0),
            str(item.get("signal_id", "")),
        ),
    ):
        row = {
            "signal_id": str(signal.get("signal_id", "")),
            "sequence": int(signal.get("sequence", 0) or 0),
            "signal_type": str(signal.get("signal_type", "preference")),
            "post_training_stage": str(
                signal.get("post_training_stage", "alignment")
            ),
            "signal_payload_hash": _signal_payload_hash(signal),
            "reward_commitment_hash": _reward_commitment_hash(signal),
            "update_commitment_hash": _update_commitment_hash(signal),
            "input_artifact_hashes": sorted(
                {
                    str(value)
                    for value in signal.get("input_artifact_hashes", [])
                    if value
                }
            ),
            "source_labels": sorted(
                {str(label) for label in signal.get("source_labels", []) if label}
            ),
            "creator_ids": sorted(
                {str(value) for value in signal.get("creator_ids", []) if value}
            ),
            "work_ids": sorted(
                {str(value) for value in signal.get("work_ids", []) if value}
            ),
            "annotator_attestation_hash": str(
                signal.get("annotator_attestation_hash", "")
            ),
            "reward_model_id_hash": stable_hash(
                str(signal.get("reward_model_id", ""))
            )
            if signal.get("reward_model_id")
            else "",
            "verifier_id_hash": stable_hash(str(signal.get("verifier_id", "")))
            if signal.get("verifier_id")
            else "",
            "synthetic_input": signal.get("synthetic_input") is True,
            "synthetic_disclosed": signal.get("synthetic_disclosed") is True,
            "license_terms_hash": str(signal.get("license_terms_hash", "")),
            "used_for_update": signal.get("used_for_update") is True,
            "escrow_if_unattributed": signal.get("escrow_if_unattributed") is True,
            "raw_signal_text_disclosed": False,
        }
        row["signal_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _royalty_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for obligation in sorted(
        receipt_input.get("signal_royalty_obligations", []),
        key=lambda item: (
            str(item.get("source_label", "")),
            str(item.get("creator_id", "")),
            str(item.get("work_id", "")),
        ),
    ):
        row = {
            "source_label": str(obligation.get("source_label", "")),
            "creator_id": str(obligation.get("creator_id", "")),
            "work_id": str(obligation.get("work_id", "")),
            "share": str(obligation.get("share", "0")),
            "settlement_state": str(obligation.get("settlement_state", "direct")),
            "basis": str(obligation.get("basis", "post_training_signal_influence")),
            "obligation_hash": hash_payload(obligation),
        }
        row["royalty_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _private_reasoning_labels(receipt: dict[str, Any]) -> set[str]:
    return {
        str(label)
        for row in receipt.get("reasoning_steps", [])
        for label in row.get("source_labels", [])
        if label
    }


def _model_lineage_labels(report: dict[str, Any]) -> set[str]:
    return {
        str(source.get("source_label", ""))
        for row in report.get("training_items", [])
        for source in row.get("source_rows", [])
        if source.get("source_label")
    }


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    private_reasoning = receipt_input.get("private_reasoning_attribution")
    model_lineage = receipt_input.get("model_lineage_attribution_report")
    signals = receipt_input.get("post_training_signals", [])
    return {
        "private_reasoning_attribution_hash": _declared_hash(private_reasoning),
        "private_reasoning_attribution_hash_reproducible": _artifact_hash_is_reproducible(
            private_reasoning
        )
        if private_reasoning
        else True,
        "model_lineage_attribution_hash": _declared_hash(model_lineage),
        "model_lineage_attribution_hash_reproducible": _artifact_hash_is_reproducible(
            model_lineage
        )
        if model_lineage
        else True,
        "signal_row_root": hash_payload(_signal_rows(receipt_input)),
        "signal_input_hash": hash_payload(signals),
        "royalty_obligation_root": hash_payload(_royalty_rows(receipt_input)),
    }


def _known_upstream_hashes(artifact_bindings: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for key, value in artifact_bindings.items()
        if key.endswith("_hash") and isinstance(value, str) and value
    }


def _policy_summary(receipt_input: dict[str, Any]) -> dict[str, Any]:
    policy = receipt_input.get("post_training_policy", {})
    return {
        "policy_id": str(
            policy.get("policy_id", "policy:post-training-signal-provenance")
        ),
        "requires_signal_lineage": policy.get("requires_signal_lineage") is True,
        "requires_source_carry_forward": policy.get("requires_source_carry_forward")
        is True,
        "requires_reward_commitments": policy.get("requires_reward_commitments")
        is True,
        "requires_annotator_or_verifier_attestation": policy.get(
            "requires_annotator_or_verifier_attestation"
        )
        is True,
        "requires_synthetic_disclosure": policy.get(
            "requires_synthetic_disclosure"
        )
        is True,
        "requires_royalty_carry_forward": policy.get(
            "requires_royalty_carry_forward"
        )
        is True,
        "requires_model_lineage_settlement": policy.get(
            "requires_model_lineage_settlement"
        )
        is True,
        "requires_no_raw_signal_text": policy.get("requires_no_raw_signal_text")
        is True,
        "policy_hash": hash_payload(policy),
    }


def _base_checks(
    *,
    receipt_input: dict[str, Any],
    signal_rows: list[dict[str, Any]],
    royalty_rows: list[dict[str, Any]],
    artifact_bindings: dict[str, Any],
    private_reasoning_errors: list[str],
    model_lineage_errors: list[str],
) -> dict[str, bool]:
    private_reasoning = receipt_input.get("private_reasoning_attribution", {})
    model_lineage = receipt_input.get("model_lineage_attribution_report", {})
    used_labels = {
        label for row in signal_rows for label in row.get("source_labels", [])
    }
    upstream_labels = _private_reasoning_labels(private_reasoning) | _model_lineage_labels(
        model_lineage
    )
    known_hashes = _known_upstream_hashes(artifact_bindings)
    obligations_by_label = {row.get("source_label", ""): row for row in royalty_rows}
    total_share = sum((_as_decimal(row["share"]) for row in royalty_rows), Decimal("0"))

    return {
        "private_reasoning_attribution_verified": bool(private_reasoning)
        and not private_reasoning_errors
        and private_reasoning.get("summary", {}).get("target_certification_level")
        == MINIMUM_PRIVATE_REASONING_LEVEL,
        "model_lineage_attribution_verified": bool(model_lineage)
        and not model_lineage_errors
        and model_lineage.get("summary", {}).get("target_certification_level")
        == MINIMUM_MODEL_LINEAGE_LEVEL,
        "artifact_hashes_reproducible": artifact_bindings[
            "private_reasoning_attribution_hash_reproducible"
        ]
        and artifact_bindings["model_lineage_attribution_hash_reproducible"],
        "post_training_signal_rows_present": bool(signal_rows),
        "signals_have_payload_reward_and_update_commitments": bool(signal_rows)
        and all(
            row["signal_payload_hash"]
            and row["reward_commitment_hash"]
            and row["update_commitment_hash"]
            and row["used_for_update"] is True
            for row in signal_rows
        ),
        "signals_bind_upstream_artifacts": bool(signal_rows)
        and all(
            set(row["input_artifact_hashes"])
            and set(row["input_artifact_hashes"]) <= known_hashes
            for row in signal_rows
        ),
        "signal_source_labels_declared": bool(used_labels)
        and all(row["source_labels"] for row in signal_rows),
        "signal_source_labels_bound_to_upstream_provenance": used_labels <= upstream_labels,
        "signal_royalty_obligations_cover_sources": bool(royalty_rows)
        and used_labels.issubset(set(obligations_by_label))
        and total_share == Decimal("1.0"),
        "signals_have_license_terms": all(
            bool(row["license_terms_hash"]) for row in signal_rows
        ),
        "annotator_or_verifier_attestations_present": all(
            bool(row["annotator_attestation_hash"])
            or bool(row["verifier_id_hash"])
            or bool(row["reward_model_id_hash"])
            for row in signal_rows
        ),
        "synthetic_signal_inputs_disclosed": all(
            not row["synthetic_input"] or row["synthetic_disclosed"]
            for row in signal_rows
        ),
        "raw_signal_text_not_disclosed": not _contains_private_fields(
            receipt_input.get("public_overrides", {})
        ),
    }


def make_post_training_signal_provenance_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public receipt for post-training signal source carry-forward."""

    receipt_input = resolve_artifact_refs(receipt_input)
    private_reasoning_errors: list[str] = []
    if receipt_input.get("private_reasoning_attribution"):
        private_reasoning_errors = verify_private_reasoning_attribution_receipt(
            receipt_input.get("private_reasoning_attribution", {}),
            receipt_input.get("private_reasoning_input", {}),
            signing_secret=signing_secret,
        )
    model_lineage_errors: list[str] = []
    if receipt_input.get("model_lineage_attribution_report"):
        model_lineage_errors = verify_model_lineage_attribution_report(
            receipt_input.get("model_lineage_attribution_report", {}),
            receipt_input.get("model_lineage_input", {}),
            signing_secret=signing_secret,
        )
    signal_rows = _signal_rows(receipt_input)
    royalty_rows = _royalty_rows(receipt_input)
    artifact_bindings = _artifact_bindings(receipt_input)
    checks = _base_checks(
        receipt_input=receipt_input,
        signal_rows=signal_rows,
        royalty_rows=royalty_rows,
        artifact_bindings=artifact_bindings,
        private_reasoning_errors=private_reasoning_errors,
        model_lineage_errors=model_lineage_errors,
    )
    policy = _policy_summary(receipt_input)
    checks["post_training_policy_is_fail_closed"] = (
        policy["requires_signal_lineage"]
        and policy["requires_source_carry_forward"]
        and policy["requires_reward_commitments"]
        and policy["requires_annotator_or_verifier_attestation"]
        and policy["requires_synthetic_disclosure"]
        and policy["requires_royalty_carry_forward"]
        and policy["requires_model_lineage_settlement"]
        and policy["requires_no_raw_signal_text"]
    )

    receipt: dict[str, Any] = {
        "version": POST_TRAINING_SIGNAL_PROVENANCE_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get(
                    "case_id", "case:post-training-signal-provenance"
                )
            ),
            "status": "ready" if all(checks.values()) else "blocked",
        },
        "post_training_system": {
            "provider": str(
                receipt_input.get("post_training_system", {}).get("provider", "")
            ),
            "model_id": str(
                receipt_input.get("post_training_system", {}).get(
                    "model_id", "model:unknown"
                )
            ),
            "model_version": str(
                receipt_input.get("post_training_system", {}).get(
                    "model_version", ""
                )
            ),
            "run_id": str(
                receipt_input.get("post_training_system", {}).get(
                    "run_id", "posttrain:unknown"
                )
            ),
            "stage": str(
                receipt_input.get("post_training_system", {}).get(
                    "stage", "alignment"
                )
            ),
            "minimum_private_reasoning_level": MINIMUM_PRIVATE_REASONING_LEVEL,
            "minimum_model_lineage_level": MINIMUM_MODEL_LINEAGE_LEVEL,
        },
        "artifact_bindings": artifact_bindings,
        "post_training_policy": policy,
        "post_training_signals": signal_rows,
        "royalty_obligations": royalty_rows,
        "verification_errors": {
            "private_reasoning_attribution": len(private_reasoning_errors),
            "model_lineage_attribution": len(model_lineage_errors),
        },
        "checks": checks,
        "privacy": {
            "raw_signal_text_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "feedback_text_disclosed": False,
            "reward_explanation_disclosed": False,
            "payment_data_disclosed": False,
            "receipt_uses_hashes_labels_and_commitments": True,
        },
        "schemas": {
            "post_training_signal_provenance": POST_TRAINING_SIGNAL_PROVENANCE_SCHEMA,
            "private_reasoning_attribution": "docs/schemas/private_reasoning_attribution.schema.json",
            "model_lineage_attribution_report": "docs/schemas/model_lineage_attribution_report.schema.json",
        },
    }
    checks["raw_signal_text_not_disclosed"] = (
        checks["raw_signal_text_not_disclosed"]
        and _private_strings_absent(receipt, receipt_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    receipt["case"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    receipt["summary"] = {
        "status": receipt["case"]["status"],
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_private_reasoning_level": MINIMUM_PRIVATE_REASONING_LEVEL,
        "minimum_model_lineage_level": MINIMUM_MODEL_LINEAGE_LEVEL,
        "signal_count": len(signal_rows),
        "source_label_count": len(
            sorted(
                {
                    label
                    for row in signal_rows
                    for label in row.get("source_labels", [])
                }
            )
        ),
        "synthetic_signal_count": sum(1 for row in signal_rows if row["synthetic_input"]),
        "royalty_obligation_count": len(royalty_rows),
        "failed_check_count": failed_check_count,
        "post_training_signal_provenance_ready": failed_check_count == 0,
        "privacy_preserved": checks["raw_signal_text_not_disclosed"],
    }
    receipt["post_training_signal_provenance_hash"] = hash_payload(
        _hashable_receipt(receipt)
    )
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_receipt(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_post_training_signal_provenance_shape(
    receipt: dict[str, Any]
) -> list[str]:
    """Validate the public shape of a post-training signal provenance receipt."""

    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "post_training_system",
        "artifact_bindings",
        "post_training_policy",
        "post_training_signals",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "post_training_signal_provenance_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing post-training signal provenance field: {key}")
    if errors:
        return errors
    if receipt.get("version") != POST_TRAINING_SIGNAL_PROVENANCE_VERSION:
        errors.append("post-training signal provenance version is unsupported")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("post-training signal provenance target level is not RDLLM-L108")
    if "post_training_signal_provenance" not in receipt.get("schemas", {}):
        errors.append("missing post-training signal provenance schema")
    if not isinstance(receipt.get("post_training_signals"), list):
        errors.append("post-training signals must be a list")
    if _contains_private_fields(receipt):
        errors.append("post-training signal provenance receipt contains private field")
    return errors


def verify_post_training_signal_provenance_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a post-training signal provenance receipt against replay inputs."""

    errors = validate_post_training_signal_provenance_shape(receipt)
    expected = make_post_training_signal_provenance_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "post_training_system",
        "artifact_bindings",
        "post_training_policy",
        "post_training_signals",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if receipt.get(key) != expected.get(key):
            errors.append(f"post-training signal provenance {key} mismatch")
    if receipt.get("post_training_signal_provenance_hash") != expected.get(
        "post_training_signal_provenance_hash"
    ):
        errors.append("post-training signal provenance hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get(
        "value"
    ):
        errors.append("post-training signal provenance signature mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("post-training signal provenance has failing checks")
    return errors
