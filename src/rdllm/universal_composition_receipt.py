"""Universal composition receipts for multi-provider foundation-model answers.

L129 proves one selected foundation-model deployment. This L130 layer proves the
next deployment shape: one public answer assembled from multiple provider-native
subresponses while preserving each provider's deployment attestation, source
footer obligations, telemetry span binding, and payout conservation.
"""

from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_COMPOSITION_RECEIPT_VERSION = "rdllm-universal-composition-receipt/v1"
UNIVERSAL_COMPOSITION_RECEIPT_SCHEMA = (
    "docs/schemas/universal_composition_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L130"
MINIMUM_INPUT_LEVEL = "RDLLM-L129"

DECLARED_HASH_FIELDS = (
    "universal_composition_receipt_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "source_footer_delivery_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
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
    "raw_native_response",
    "raw_composition_payload",
    "native_response_body",
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
    "reasoning",
    "chain_of_thought",
    "raw_license_token",
    "license_server_secret",
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


def load_universal_composition_receipt_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L130 universal composition receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_composition_receipt_hash", "signature"}
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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in PRIVATE_FIELD_NAMES or _contains_private_fields(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(
    report: dict[str, Any],
    composition_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in composition_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(composition_input: dict[str, Any]) -> dict[str, Any]:
    policy = composition_input.get("composition_policy", {})
    return {
        "profile": "rdllm-universal-composition-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "minimum_segment_level": str(
            policy.get("minimum_segment_level", MINIMUM_INPUT_LEVEL)
        ),
        "provider_segment_attestation_required": bool(
            policy.get("provider_segment_attestation_required", True)
        ),
        "source_footer_preservation_required": bool(
            policy.get("source_footer_preservation_required", True)
        ),
        "telemetry_span_binding_required": bool(
            policy.get("telemetry_span_binding_required", True)
        ),
        "provider_weight_conservation_required": bool(
            policy.get("provider_weight_conservation_required", True)
        ),
        "on_unattested_segment": "block_display",
        "on_merge_hash_mismatch": "block_display",
        "on_source_footer_gap": "block_display",
        "raw_composition_payload_disclosure_allowed": False,
    }


def _artifact_bindings(
    composition_input: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    artifacts = {
        "response_envelope": composition_input.get("response_envelope"),
        "source_footer_delivery": composition_input.get("source_footer_delivery"),
        "composite_foundation_adapter": composition_input.get(
            "composite_foundation_adapter"
        ),
        "foundation_provider_conformance": composition_input.get(
            "foundation_provider_conformance"
        ),
        "foundation_runtime_router": composition_input.get("foundation_runtime_router"),
        "discovery_manifest": composition_input.get("discovery_manifest"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("composition_receipt_version")
            or (artifact or {}).get("deployment_attestation_version")
            or (artifact or {}).get("runtime_router_version")
            or (artifact or {}).get("conformance_version")
            or (artifact or {}).get("adapter_version")
            or (artifact or {}).get("delivery_version")
            or (artifact or {}).get("envelope_version")
            or (artifact or {}).get("manifest_version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _deployment_attestation_rows(
    composition_input: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, attestation in enumerate(
        composition_input.get("deployment_attestations", []),
        start=1,
    ):
        summary = attestation.get("summary", {})
        request_response = attestation.get("request_response_binding", {})
        statement = attestation.get("model_deployment_statement", {})
        row = {
            "display_order": index,
            "deployment_attestation_hash": str(
                attestation.get("foundation_model_deployment_attestation_hash", "")
            ),
            "hash_reproducible": _artifact_hash_is_reproducible(attestation),
            "status": str(summary.get("status", "")),
            "target_certification_level": str(
                summary.get("target_certification_level", "")
            ),
            "provider_id": str(summary.get("provider_id", "")),
            "provider_family": str(summary.get("provider_family", "")),
            "native_model": str(summary.get("native_model", "")),
            "deployment_id": str(summary.get("deployment_id", "")),
            "native_response_id": str(request_response.get("native_response_id", "")),
            "native_output_hash": str(request_response.get("native_output_hash", "")),
            "response_envelope_hash": str(
                request_response.get("response_envelope_hash", "")
            ),
            "request_projection_hash": str(
                request_response.get("request_projection_hash", "")
            ),
            "response_binding_hash": str(
                request_response.get("response_binding_hash", "")
            ),
            "api_boundary_attestation_hash": str(
                request_response.get("api_boundary_attestation_hash", "")
            ),
            "statement_hash": str(statement.get("statement_hash", "")),
            "deployment_release_authorized": bool(
                summary.get("deployment_release_authorized", False)
            ),
        }
        row["deployment_attestation_row_hash"] = hash_payload(
            {
                key: value
                for key, value in row.items()
                if key != "deployment_attestation_row_hash"
            }
        )
        rows.append(row)
    return rows


def _segment_rows(
    composition_input: dict[str, Any],
    source_footer_delivery: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_footer_delivery_hash = str(
        source_footer_delivery.get("source_footer_delivery_hash", "")
    )
    for index, segment in enumerate(composition_input.get("segments", []), start=1):
        row = {
            "display_order": index,
            "segment_id": str(segment.get("segment_id", "")),
            "segment_role": str(segment.get("segment_role", "")),
            "provider_id": str(segment.get("provider_id", "")),
            "provider_family": str(segment.get("provider_family", "")),
            "native_model": str(segment.get("native_model", "")),
            "deployment_id": str(segment.get("deployment_id", "")),
            "native_response_id": str(segment.get("native_response_id", "")),
            "native_output_hash": str(segment.get("native_output_hash", "")),
            "response_envelope_hash": str(segment.get("response_envelope_hash", "")),
            "source_footer_delivery_hash": str(
                segment.get(
                    "source_footer_delivery_hash",
                    source_footer_delivery_hash,
                )
            ),
            "deployment_attestation_hash": str(
                segment.get("deployment_attestation_hash", "")
            ),
            "merge_input_hash": str(segment.get("merge_input_hash", "")),
            "merge_output_span_hash": str(segment.get("merge_output_span_hash", "")),
            "provider_weight": str(segment.get("provider_weight", "0")),
            "claim_ids": [str(item) for item in segment.get("claim_ids", [])],
            "source_labels": [str(item) for item in segment.get("source_labels", [])],
        }
        row["segment_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "segment_hash"}
        )
        rows.append(row)
    return rows


def _telemetry_span_rows(composition_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, span in enumerate(
        composition_input.get("telemetry_span_bindings", []),
        start=1,
    ):
        row = {
            "display_order": index,
            "segment_id": str(span.get("segment_id", "")),
            "provider_id": str(span.get("provider_id", "")),
            "provider_family": str(span.get("provider_family", "")),
            "native_response_id": str(span.get("native_response_id", "")),
            "response_envelope_hash": str(span.get("response_envelope_hash", "")),
            "trace_id_hash": str(span.get("trace_id_hash", "")),
            "span_id_hash": str(span.get("span_id_hash", "")),
            "span_kind": str(span.get("span_kind", "")),
            "gen_ai_operation": str(span.get("gen_ai_operation", "")),
        }
        row["telemetry_span_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "telemetry_span_hash"}
        )
        rows.append(row)
    return rows


def _composition_plan(
    composition_input: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    source_footer_delivery: dict[str, Any],
    segment_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    plan = composition_input.get("composition_plan", {})
    public = {
        "composition_id": str(plan.get("composition_id", "")),
        "composition_mode": str(plan.get("composition_mode", "provider_segment_merge")),
        "merge_policy": str(plan.get("merge_policy", "hash_bound_segment_merge")),
        "final_response_envelope_hash": str(
            plan.get(
                "final_response_envelope_hash",
                response_envelope.get("envelope_hash", ""),
            )
        ),
        "final_rendered_output_hash": str(
            plan.get(
                "final_rendered_output_hash",
                response_envelope.get("response", {}).get("rendered_output_hash", ""),
            )
        ),
        "source_footer_delivery_hash": str(
            plan.get(
                "source_footer_delivery_hash",
                source_footer_delivery.get("source_footer_delivery_hash", ""),
            )
        ),
        "segment_ids": [str(row["segment_id"]) for row in segment_rows],
        "provider_families": sorted({str(row["provider_family"]) for row in segment_rows}),
        "segment_count": len(segment_rows),
        "declared_segment_root": str(
            plan.get(
                "declared_segment_root",
                merkle_root([row["segment_hash"] for row in segment_rows]),
            )
        ),
        "declared_composition_plan_hash": str(
            plan.get("declared_composition_plan_hash", "")
        ),
    }
    computed_plan_hash = hash_payload(
        {
            key: value
            for key, value in public.items()
            if key != "declared_composition_plan_hash"
        }
    )
    if not public["declared_composition_plan_hash"]:
        public["declared_composition_plan_hash"] = computed_plan_hash
    public["computed_segment_root"] = merkle_root(
        [row["segment_hash"] for row in segment_rows]
    )
    public["computed_composition_plan_hash"] = computed_plan_hash
    return public


def _segment_match_count(
    segment: dict[str, Any],
    deployment_rows: list[dict[str, Any]],
) -> int:
    return sum(
        1
        for row in deployment_rows
        if row["deployment_attestation_hash"] == segment["deployment_attestation_hash"]
        and row["provider_id"] == segment["provider_id"]
        and row["provider_family"] == segment["provider_family"]
        and row["native_model"] == segment["native_model"]
        and row["deployment_id"] == segment["deployment_id"]
        and row["native_response_id"] == segment["native_response_id"]
        and row["native_output_hash"] == segment["native_output_hash"]
        and row["response_envelope_hash"] == segment["response_envelope_hash"]
    )


def _supported_families_from_composite(
    composite_foundation_adapter: dict[str, Any],
) -> set[str]:
    return {
        str(row.get("provider_family", ""))
        for row in composite_foundation_adapter.get("provider_adapter_rows", [])
        if row.get("provider_family")
    }


def _supported_families_from_conformance(
    foundation_provider_conformance: dict[str, Any],
) -> set[str]:
    return {
        str(row.get("provider_family", ""))
        for row in foundation_provider_conformance.get("provider_conformance_rows", [])
        if row.get("provider_family")
    }


def _provider_weights_conserve_unit(segment_rows: list[dict[str, Any]]) -> bool:
    try:
        total = sum(Decimal(row["provider_weight"]) for row in segment_rows)
    except (InvalidOperation, KeyError):
        return False
    return total == Decimal("1.000000") and all(
        Decimal(row["provider_weight"]) >= Decimal("0") for row in segment_rows
    )


def _checks(
    *,
    composition_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    deployment_rows: list[dict[str, Any]],
    segment_rows: list[dict[str, Any]],
    telemetry_rows: list[dict[str, Any]],
    composition_plan: dict[str, Any],
) -> dict[str, bool]:
    response_envelope = composition_input.get("response_envelope", {})
    source_footer_delivery = composition_input.get("source_footer_delivery", {})
    composite_foundation_adapter = composition_input.get("composite_foundation_adapter", {})
    foundation_provider_conformance = composition_input.get(
        "foundation_provider_conformance", {}
    )
    segment_ids = [row["segment_id"] for row in segment_rows]
    segment_families = {row["provider_family"] for row in segment_rows}
    composite_families = _supported_families_from_composite(composite_foundation_adapter)
    conformance_families = _supported_families_from_conformance(
        foundation_provider_conformance
    )
    span_keys = {
        (
            row["segment_id"],
            row["provider_id"],
            row["provider_family"],
            row["native_response_id"],
            row["response_envelope_hash"],
        )
        for row in telemetry_rows
    }
    public_report = {
        "composition_plan": composition_plan,
        "deployment_attestation_rows": deployment_rows,
        "provider_segments": segment_rows,
        "telemetry_span_bindings": telemetry_rows,
    }
    return {
        "artifact_hashes_reproducible": (
            artifact_bindings["response_envelope"]["present"]
            and artifact_bindings["response_envelope"]["hash_reproducible"]
            and artifact_bindings["source_footer_delivery"]["present"]
            and artifact_bindings["source_footer_delivery"]["hash_reproducible"]
            and artifact_bindings["composite_foundation_adapter"]["present"]
            and artifact_bindings["composite_foundation_adapter"]["hash_reproducible"]
            and artifact_bindings["foundation_provider_conformance"]["present"]
            and artifact_bindings["foundation_provider_conformance"][
                "hash_reproducible"
            ]
        ),
        "deployment_attestations_released_l129": all(
            row["status"] == "released"
            and row["target_certification_level"] == MINIMUM_INPUT_LEVEL
            and row["deployment_release_authorized"]
            and row["hash_reproducible"]
            for row in deployment_rows
        )
        and bool(deployment_rows),
        "segment_count_positive": bool(segment_rows),
        "segment_ids_unique": len(segment_ids) == len(set(segment_ids)),
        "segment_hashes_present": all(row["segment_hash"] for row in segment_rows),
        "each_segment_has_single_matching_deployment_attestation": all(
            _segment_match_count(row, deployment_rows) == 1 for row in segment_rows
        )
        if policy["provider_segment_attestation_required"]
        else True,
        "segment_provider_families_supported_by_composite_adapter": (
            segment_families.issubset(composite_families) and bool(segment_families)
        ),
        "segment_provider_families_supported_by_conformance": (
            segment_families.issubset(conformance_families) and bool(segment_families)
        ),
        "composition_plan_hash_reproducible": (
            composition_plan["declared_composition_plan_hash"]
            == composition_plan["computed_composition_plan_hash"]
        ),
        "segment_root_matches_plan": (
            composition_plan["declared_segment_root"]
            == composition_plan["computed_segment_root"]
        ),
        "final_response_binds_response_envelope": (
            composition_plan["final_response_envelope_hash"]
            == response_envelope.get("envelope_hash", "")
            and composition_plan["final_rendered_output_hash"]
            == response_envelope.get("response", {}).get("rendered_output_hash", "")
        ),
        "source_footer_delivery_bound": (
            not policy["source_footer_preservation_required"]
            or (
                composition_plan["source_footer_delivery_hash"]
                == source_footer_delivery.get("source_footer_delivery_hash", "")
                and all(
                    row["source_footer_delivery_hash"]
                    == source_footer_delivery.get("source_footer_delivery_hash", "")
                    for row in segment_rows
                )
            )
        ),
        "provider_weights_conserve_unit": (
            not policy["provider_weight_conservation_required"]
            or _provider_weights_conserve_unit(segment_rows)
        ),
        "segment_claims_and_sources_declared": all(
            row["claim_ids"] and row["source_labels"] for row in segment_rows
        ),
        "telemetry_spans_bind_segments": (
            not policy["telemetry_span_binding_required"]
            or all(
                (
                    row["segment_id"],
                    row["provider_id"],
                    row["provider_family"],
                    row["native_response_id"],
                    row["response_envelope_hash"],
                )
                in span_keys
                for row in segment_rows
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, composition_input)
        ),
    }


def _failure_modes(checks: dict[str, bool]) -> list[str]:
    mapping = {
        "artifact_hashes_reproducible": "artifact_hash_drift",
        "deployment_attestations_released_l129": "deployment_attestation_not_released",
        "segment_count_positive": "missing_provider_segment",
        "segment_ids_unique": "duplicate_segment_id",
        "segment_hashes_present": "segment_hash_missing",
        "each_segment_has_single_matching_deployment_attestation": "segment_deployment_attestation_mismatch",
        "segment_provider_families_supported_by_composite_adapter": "provider_family_not_adapter_supported",
        "segment_provider_families_supported_by_conformance": "provider_family_not_conformance_supported",
        "composition_plan_hash_reproducible": "composition_plan_hash_drift",
        "segment_root_matches_plan": "segment_root_mismatch",
        "final_response_binds_response_envelope": "final_response_envelope_mismatch",
        "source_footer_delivery_bound": "source_footer_gap",
        "provider_weights_conserve_unit": "provider_weight_conservation_failure",
        "segment_claims_and_sources_declared": "segment_attribution_scope_missing",
        "telemetry_spans_bind_segments": "telemetry_span_binding_missing",
        "private_text_not_disclosed": "private_text_leak",
    }
    return sorted(
        {mode for check, mode in mapping.items() if checks.get(check) is not True}
    )


def make_universal_composition_receipt(
    composition_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L130 universal multi-provider composition receipt."""

    policy = _policy(composition_input)
    artifact_bindings = _artifact_bindings(composition_input)
    deployment_rows = _deployment_attestation_rows(composition_input)
    response_envelope = composition_input.get("response_envelope", {})
    source_footer_delivery = composition_input.get("source_footer_delivery", {})
    segment_rows = _segment_rows(composition_input, source_footer_delivery)
    telemetry_rows = _telemetry_span_rows(composition_input)
    composition_plan = _composition_plan(
        composition_input,
        response_envelope=response_envelope,
        source_footer_delivery=source_footer_delivery,
        segment_rows=segment_rows,
    )
    checks = _checks(
        composition_input=composition_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        deployment_rows=deployment_rows,
        segment_rows=segment_rows,
        telemetry_rows=telemetry_rows,
        composition_plan=composition_plan,
    )
    failed = [key for key, value in checks.items() if value is not True]
    blocked = bool(failed)
    failure_modes = _failure_modes(checks)
    provider_families = sorted({row["provider_family"] for row in segment_rows})
    report: dict[str, Any] = {
        "composition_receipt_version": UNIVERSAL_COMPOSITION_RECEIPT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "composition_policy": policy,
        "artifact_bindings": artifact_bindings,
        "deployment_attestation_rows": deployment_rows,
        "composition_plan": composition_plan,
        "provider_segments": segment_rows,
        "telemetry_span_bindings": telemetry_rows,
        "composition_decision": {
            "decision": "block_display" if blocked else "release",
            "release_authorized": not blocked,
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "safe_output_policy": (
                "suppress_unverified_composite_answer"
                if blocked
                else "emit_universal_attributed_composite_answer"
            ),
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "segment_ids_without_matching_attestation": [
                row["segment_id"]
                for row in segment_rows
                if _segment_match_count(row, deployment_rows) != 1
            ],
            "duplicate_segment_ids": sorted(
                {segment_id for segment_id in segment_ids if segment_ids.count(segment_id) > 1}
            )
            if (segment_ids := [row["segment_id"] for row in segment_rows])
            else [],
            "provider_families": provider_families,
        },
        "commitments": {
            "deployment_attestation_root": merkle_root(
                [row["deployment_attestation_row_hash"] for row in deployment_rows]
            ),
            "provider_segment_root": composition_plan["computed_segment_root"],
            "telemetry_span_root": merkle_root(
                [row["telemetry_span_hash"] for row in telemetry_rows]
            ),
            "composition_plan_hash": composition_plan[
                "computed_composition_plan_hash"
            ],
            "final_response_envelope_hash": composition_plan[
                "final_response_envelope_hash"
            ],
            "source_footer_delivery_hash": composition_plan[
                "source_footer_delivery_hash"
            ],
            "schema": UNIVERSAL_COMPOSITION_RECEIPT_SCHEMA,
        },
        "schemas": {
            "universal_composition_receipt": UNIVERSAL_COMPOSITION_RECEIPT_SCHEMA,
            "foundation_model_deployment_attestation": "docs/schemas/foundation_model_deployment_attestation.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "composite_foundation_adapter": "docs/schemas/composite_foundation_adapter.schema.json",
            "foundation_provider_conformance": "docs/schemas/foundation_provider_conformance.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_provider_response_disclosed": False,
            "raw_composition_payload_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "hash_only_segment_commitments": True,
        },
        "summary": {
            "status": "blocked" if blocked else "released",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "composition_id": composition_plan["composition_id"],
            "provider_segment_count": len(segment_rows),
            "provider_family_count": len(provider_families),
            "deployment_attestation_count": len(deployment_rows),
            "failed_check_count": len(failed),
            "failure_mode_count": len(failure_modes),
            "composite_answer_release_authorized": not blocked,
            "universal_multi_provider_composition_supported": checks[
                "each_segment_has_single_matching_deployment_attestation"
            ]
            and checks["provider_weights_conserve_unit"],
            "source_footer_obligations_preserved": checks["source_footer_delivery_bound"],
            "telemetry_bound": checks["telemetry_spans_bind_segments"],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["universal_composition_receipt_hash"] = hash_payload(
        _hashable_report(report)
    )
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


def validate_universal_composition_receipt_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "composition_receipt_version",
        "issuer",
        "created_at",
        "composition_policy",
        "artifact_bindings",
        "deployment_attestation_rows",
        "composition_plan",
        "provider_segments",
        "telemetry_span_bindings",
        "composition_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_composition_receipt_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal composition receipt field: {key}")
    if errors:
        return errors
    if report.get("composition_receipt_version") != UNIVERSAL_COMPOSITION_RECEIPT_VERSION:
        errors.append("universal composition receipt version is unsupported")
    if (
        report.get("schemas", {}).get("universal_composition_receipt")
        != UNIVERSAL_COMPOSITION_RECEIPT_SCHEMA
    ):
        errors.append("universal composition receipt schema is not declared")
    if not isinstance(report.get("provider_segments"), list):
        errors.append("universal composition provider segments are not a list")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("universal composition receipt target level is not RDLLM-L130")
    return errors


def verify_universal_composition_receipt(
    report: dict[str, Any],
    *,
    composition_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L130 universal composition receipt against replay inputs."""

    errors = validate_universal_composition_receipt_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "universal_composition_receipt_hash"
    ):
        errors.append("universal composition receipt hash is not reproducible")

    expected = make_universal_composition_receipt(
        composition_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "composition_policy",
        "artifact_bindings",
        "deployment_attestation_rows",
        "composition_plan",
        "provider_segments",
        "telemetry_span_bindings",
        "composition_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal composition receipt {key} does not match inputs")
    if expected.get("universal_composition_receipt_hash") != report.get(
        "universal_composition_receipt_hash"
    ):
        errors.append("universal composition receipt hash does not match inputs")

    decision = report.get("composition_decision", {})
    if report.get("summary", {}).get("status") == "blocked":
        if decision.get("decision") != "block_display" or decision.get(
            "release_authorized"
        ):
            errors.append("universal composition blocked report is not fail-closed")
    elif report.get("summary", {}).get("status") == "released":
        if decision.get("decision") != "release" or not decision.get(
            "release_authorized"
        ):
            errors.append("universal composition released report is not releasable")
    else:
        errors.append("universal composition receipt status is unsupported")

    if _contains_private_fields(report):
        errors.append("universal composition receipt exposes private field names")
    if not _private_strings_absent(report, composition_input):
        errors.append("universal composition receipt exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal composition receipt is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal composition receipt signature is invalid")

    return errors
