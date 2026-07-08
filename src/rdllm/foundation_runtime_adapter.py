"""Runtime adapter receipts for native foundation-model responses.

The L125 adapter and L126 conformance matrix prove that provider families can
carry RDLLM metadata. This layer makes that proof executable for a concrete
native response: the response either normalizes into the RDLLM proof contract or
it fails closed before display.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

FOUNDATION_RUNTIME_ADAPTER_VERSION = "rdllm-foundation-runtime-adapter/v1"
FOUNDATION_RUNTIME_ADAPTER_SCHEMA = (
    "docs/schemas/foundation_runtime_adapter.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L127"
MINIMUM_INPUT_LEVEL = "RDLLM-L126"

REQUIRED_NEGATIVE_MODES = (
    "missing_required_header",
    "native_output_hash_mismatch",
    "unverified_citation_url",
    "unsupported_claim_footer",
    "stream_final_hash_drift",
    "private_text_leak",
)

DECLARED_HASH_FIELDS = (
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "foundation_profile_hash",
    "citation_url_health_hash",
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


def load_foundation_runtime_adapter_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L127 runtime adapter receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"foundation_runtime_adapter_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if (
        isinstance(metadata, dict)
        and artifact.get("foundation_profile_hash")
        and "header_values" in metadata
    ):
        metadata = deepcopy(metadata)
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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
    adapter_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in adapter_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: str) -> int:
    if not level.startswith("RDLLM-L"):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _policy(adapter_input: dict[str, Any]) -> dict[str, Any]:
    policy = adapter_input.get("policy", {})
    return {
        "profile": "rdllm-foundation-runtime-adapter-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "minimum_attribution_level": str(
            policy.get("minimum_attribution_level", "RDLLM-L126")
        ),
        "required_negative_modes": list(
            policy.get("required_negative_modes", REQUIRED_NEGATIVE_MODES)
        ),
        "on_runtime_adapter_failure": "block_display",
        "native_response_payload_disclosure_allowed": False,
        "raw_prompt_or_source_text_disclosure_allowed": False,
    }


def _artifact_bindings(adapter_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "foundation_provider_conformance": adapter_input.get(
            "foundation_provider_conformance"
        ),
        "composite_foundation_adapter": adapter_input.get(
            "composite_foundation_adapter"
        ),
        "foundation_api_profile": adapter_input.get("foundation_api_profile"),
        "response_envelope": adapter_input.get("response_envelope"),
        "source_footer_delivery": adapter_input.get("source_footer_delivery"),
        "citation_url_health": adapter_input.get("citation_url_health"),
        "discovery_manifest": adapter_input.get("discovery_manifest"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("runtime_adapter_version")
            or (artifact or {}).get("conformance_version")
            or (artifact or {}).get("adapter_version")
            or (artifact or {}).get("version")
            or (artifact or {}).get("url_health_version")
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


def _row_by_family(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("provider_family", "")): row for row in rows}


def _native_response(adapter_input: dict[str, Any]) -> dict[str, Any]:
    native = adapter_input.get("native_response", {})
    return {
        "provider_id": str(native.get("provider_id", "")),
        "provider_family": str(native.get("provider_family", "")),
        "native_api_version": str(native.get("native_api_version", "")),
        "native_response_id": str(native.get("native_response_id", "")),
        "native_model": str(native.get("native_model", "")),
        "native_status": str(native.get("native_status", "")),
        "native_created_at": str(native.get("native_created_at", "")),
        "native_output_hash": str(native.get("native_output_hash", "")),
        "headers": {
            str(key): str(value) for key, value in native.get("headers", {}).items()
        },
        "json_proof_hashes": {
            str(key): str(value)
            for key, value in native.get("json_proof_hashes", {}).items()
        },
        "citation_path_observations": {
            str(key): bool(value)
            for key, value in native.get("citation_path_observations", {}).items()
        },
        "tool_path_observations": {
            str(key): bool(value)
            for key, value in native.get("tool_path_observations", {}).items()
        },
        "stream_final_event_hashes": {
            str(key): str(value)
            for key, value in native.get("stream_final_event_hashes", {}).items()
        },
        "claim_support_footer_hash": str(native.get("claim_support_footer_hash", "")),
        "runtime_observation_hash": str(native.get("runtime_observation_hash", "")),
    }


def _response_envelope_hash(response_envelope: dict[str, Any]) -> str:
    return str(response_envelope.get("envelope_hash", ""))


def _rendered_output_hash(response_envelope: dict[str, Any]) -> str:
    return str(response_envelope.get("response", {}).get("rendered_output_hash", ""))


def _source_footer_delivery_hash(source_footer_delivery: dict[str, Any]) -> str:
    return str(source_footer_delivery.get("source_footer_delivery_hash", ""))


def _citation_url_health_hash(citation_url_health: dict[str, Any]) -> str:
    return str(citation_url_health.get("citation_url_health_hash", ""))


def _foundation_profile_hash(foundation_api_profile: dict[str, Any]) -> str:
    return str(foundation_api_profile.get("foundation_profile_hash", ""))


def _discovery_manifest_hash(discovery_manifest: dict[str, Any]) -> str:
    return str(discovery_manifest.get("manifest_hash", ""))


def _expected_header_values(adapter_input: dict[str, Any]) -> dict[str, str]:
    profile_values = dict(
        adapter_input.get("foundation_api_profile", {})
        .get("response_metadata_contract", {})
        .get("header_values", {})
    )
    profile_values["RDLLM-Foundation-Profile-Hash"] = _foundation_profile_hash(
        adapter_input.get("foundation_api_profile", {})
    )
    profile_values["RDLLM-Discovery-Manifest-Hash"] = _discovery_manifest_hash(
        adapter_input.get("discovery_manifest", {})
    )
    profile_values["RDLLM-Response-Envelope-Hash"] = _response_envelope_hash(
        adapter_input.get("response_envelope", {})
    )
    profile_values["RDLLM-Source-Footer-Delivery-Hash"] = _source_footer_delivery_hash(
        adapter_input.get("source_footer_delivery", {})
    )
    return {str(key): str(value) for key, value in profile_values.items()}


def _adapter_and_conformance_rows(
    adapter_input: dict[str, Any],
    native: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    family = native["provider_family"]
    adapter_rows = _row_by_family(
        adapter_input.get("composite_foundation_adapter", {}).get(
            "provider_adapter_rows", []
        )
    )
    conformance_rows = _row_by_family(
        adapter_input.get("foundation_provider_conformance", {}).get(
            "provider_conformance_rows", []
        )
    )
    return adapter_rows.get(family, {}), conformance_rows.get(family, {})


def _checks(
    *,
    adapter_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    native: dict[str, Any],
    adapter_row: dict[str, Any],
    conformance_row: dict[str, Any],
) -> dict[str, bool]:
    foundation_profile = adapter_input.get("foundation_api_profile", {})
    response_envelope = adapter_input.get("response_envelope", {})
    source_footer_delivery = adapter_input.get("source_footer_delivery", {})
    citation_url_health = adapter_input.get("citation_url_health", {})
    composite_adapter = adapter_input.get("composite_foundation_adapter", {})
    provider_conformance = adapter_input.get("foundation_provider_conformance", {})
    required_headers = list(
        foundation_profile.get("response_metadata_contract", {}).get(
            "required_http_headers", []
        )
    )
    required_json_fields = list(
        foundation_profile.get("response_metadata_contract", {}).get(
            "required_json_fields", []
        )
    )
    expected_headers = _expected_header_values(adapter_input)
    native_headers = native["headers"]
    native_json_hashes = native["json_proof_hashes"]
    required_negative_modes = set(policy["required_negative_modes"])
    conformance_negative_modes = set(
        conformance_row.get("negative_fixture_hashes", {}).keys()
    )
    public_report = {
        "native_response_observation": native,
        "adapter_row_hash": adapter_row.get("provider_adapter_row_hash", ""),
        "conformance_row_hash": conformance_row.get(
            "foundation_provider_conformance_row_hash", ""
        ),
    }
    stream_hashes = native["stream_final_event_hashes"]
    url_summary = citation_url_health.get("summary", {})
    unverified_url_count = int(url_summary.get("unverified_url_count", 0) or 0)
    return {
        "artifact_hashes_reproducible": all(
            binding["present"] and binding["hash_reproducible"]
            for binding in artifact_bindings.values()
        ),
        "foundation_provider_conformance_ready_l126": (
            provider_conformance.get("summary", {}).get("status") == "ready"
            and provider_conformance.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L126"
        ),
        "composite_foundation_adapter_ready_l125": (
            composite_adapter.get("summary", {}).get("status") == "ready"
            and composite_adapter.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L125"
        ),
        "provider_family_supported": bool(adapter_row) and bool(conformance_row),
        "native_provider_identity_matches_adapter": (
            bool(adapter_row)
            and native["provider_id"] == adapter_row.get("provider_id", "")
            and native["provider_family"] == adapter_row.get("provider_family", "")
            and native["native_api_version"]
            == adapter_row.get("native_api_version", "")
            and native["native_model"] == adapter_row.get("native_model", "")
        ),
        "native_output_hash_matches_response_envelope": (
            native["native_output_hash"] == _rendered_output_hash(response_envelope)
        ),
        "required_headers_present": all(
            bool(native_headers.get(header)) for header in required_headers
        ),
        "required_header_values_bind_artifacts": all(
            header == "RDLLM-Attribution-Level"
            or not expected_headers.get(header)
            or native_headers.get(header) == expected_headers.get(header)
            for header in required_headers
        ),
        "runtime_attribution_level_meets_minimum": (
            _level_number(native_headers.get("RDLLM-Attribution-Level", ""))
            >= _level_number(policy["minimum_attribution_level"])
        ),
        "required_json_proof_fields_present": all(
            bool(native_json_hashes.get(field)) for field in required_json_fields
        ),
        "json_proof_fields_bind_embedded_artifacts": (
            native_json_hashes.get("embedded_artifacts.response_envelope")
            == _response_envelope_hash(response_envelope)
            and native_json_hashes.get("embedded_artifacts.source_footer_delivery")
            == _source_footer_delivery_hash(source_footer_delivery)
            and native_json_hashes.get("verification.foundation_attribution_profile")
            == _foundation_profile_hash(foundation_profile)
        ),
        "citation_paths_observed": all(
            native["citation_path_observations"].get(path) is True
            for path in adapter_row.get("citation_mapping_paths", [])
        ),
        "tool_paths_observed": all(
            native["tool_path_observations"].get(path) is True
            for path in adapter_row.get("tool_mapping_paths", [])
        ),
        "stream_final_event_hashes_bind_artifacts": (
            stream_hashes.get("RDLLM-Response-Envelope-Hash")
            == _response_envelope_hash(response_envelope)
            and stream_hashes.get("RDLLM-Foundation-Profile-Hash")
            == _foundation_profile_hash(foundation_profile)
            and stream_hashes.get("RDLLM-Citation-URL-Health-Hash")
            == _citation_url_health_hash(citation_url_health)
            and stream_hashes.get("RDLLM-Source-Footer-Delivery-Hash")
            == _source_footer_delivery_hash(source_footer_delivery)
        ),
        "citation_url_health_ready_and_verified": (
            url_summary.get("status") == "ready" and unverified_url_count == 0
        ),
        "claim_support_footer_bound": (
            native["claim_support_footer_hash"]
            == _source_footer_delivery_hash(source_footer_delivery)
            and source_footer_delivery.get("summary", {}).get("status") == "ready"
        ),
        "conformance_row_backs_adapter_row": (
            bool(conformance_row)
            and bool(adapter_row)
            and conformance_row.get("provider_adapter_row_hash", "")
            == adapter_row.get("provider_adapter_row_hash", "")
            and conformance_row.get("adapter_row_hash_matches_composite") is True
        ),
        "conformance_capabilities_cover_runtime_modes": all(
            conformance_row.get("capabilities", {}).get(capability) is True
            for capability in (
                "sync_response",
                "streaming_response",
                "tool_calling",
                "citation_or_grounding",
                "url_health_binding",
                "structured_proof_fields",
                "claim_support_footer",
                "parametric_memory_fallback",
                "fail_closed_errors",
            )
        ),
        "negative_modes_have_fail_closed_fixtures": required_negative_modes.issubset(
            conformance_negative_modes
        ),
        "runtime_observation_hash_present": bool(native["runtime_observation_hash"]),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, adapter_input)
        ),
    }


def _failure_modes(checks: dict[str, bool]) -> list[str]:
    mapping = {
        "required_headers_present": "missing_required_header",
        "required_header_values_bind_artifacts": "missing_required_header",
        "native_output_hash_matches_response_envelope": "native_output_hash_mismatch",
        "citation_url_health_ready_and_verified": "unverified_citation_url",
        "claim_support_footer_bound": "unsupported_claim_footer",
        "stream_final_event_hashes_bind_artifacts": "stream_final_hash_drift",
        "private_text_not_disclosed": "private_text_leak",
    }
    modes = [
        mode
        for check, mode in mapping.items()
        if checks.get(check) is not True
    ]
    if any(
        checks.get(check) is not True
        for check in (
            "foundation_provider_conformance_ready_l126",
            "composite_foundation_adapter_ready_l125",
            "provider_family_supported",
            "conformance_row_backs_adapter_row",
            "conformance_capabilities_cover_runtime_modes",
            "negative_modes_have_fail_closed_fixtures",
        )
    ):
        modes.append("provider_conformance_failure")
    return sorted(set(modes))


def make_foundation_runtime_adapter_report(
    adapter_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L127 runtime adapter receipt for one native provider response."""

    policy = _policy(adapter_input)
    artifact_bindings = _artifact_bindings(adapter_input)
    native = _native_response(adapter_input)
    adapter_row, conformance_row = _adapter_and_conformance_rows(adapter_input, native)
    checks = _checks(
        adapter_input=adapter_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        native=native,
        adapter_row=adapter_row,
        conformance_row=conformance_row,
    )
    failed = [key for key, value in checks.items() if value is not True]
    blocked = bool(failed)
    failure_modes = _failure_modes(checks)
    response_envelope = adapter_input.get("response_envelope", {})
    source_footer_delivery = adapter_input.get("source_footer_delivery", {})
    citation_url_health = adapter_input.get("citation_url_health", {})
    foundation_api_profile = adapter_input.get("foundation_api_profile", {})
    report: dict[str, Any] = {
        "runtime_adapter_version": FOUNDATION_RUNTIME_ADAPTER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "native_response_observation": native,
        "adapter_binding": {
            "provider_adapter_row_hash": adapter_row.get(
                "provider_adapter_row_hash", ""
            ),
            "provider_family": adapter_row.get("provider_family", ""),
            "native_output_path": adapter_row.get("native_output_path", ""),
            "citation_mapping_paths": adapter_row.get("citation_mapping_paths", []),
            "tool_mapping_paths": adapter_row.get("tool_mapping_paths", []),
        },
        "conformance_binding": {
            "foundation_provider_conformance_row_hash": conformance_row.get(
                "foundation_provider_conformance_row_hash", ""
            ),
            "provider_adapter_row_hash": conformance_row.get(
                "provider_adapter_row_hash", ""
            ),
            "capabilities": conformance_row.get("capabilities", {}),
            "negative_fixture_hashes": conformance_row.get(
                "negative_fixture_hashes", {}
            ),
        },
        "normalized_rdllm_contract": {
            "profile": "rdllm-native-response-runtime-normalization/v1",
            "response_envelope_hash": _response_envelope_hash(response_envelope),
            "rendered_output_hash": _rendered_output_hash(response_envelope),
            "source_footer_delivery_hash": _source_footer_delivery_hash(
                source_footer_delivery
            ),
            "citation_url_health_hash": _citation_url_health_hash(citation_url_health),
            "foundation_profile_hash": _foundation_profile_hash(
                foundation_api_profile
            ),
            "foundation_provider_conformance_hash": _declared_hash(
                adapter_input.get("foundation_provider_conformance")
            ),
            "native_output_hash": native["native_output_hash"],
        },
        "runtime_decision": {
            "decision": "block_display" if blocked else "release",
            "release_authorized": not blocked,
            "failure_modes": failure_modes,
            "failed_checks": failed,
            "safe_output_policy": (
                "suppress_native_payload" if blocked else "emit_rdllm_proof_contract"
            ),
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "missing_headers": [
                header
                for header in foundation_api_profile.get(
                    "response_metadata_contract", {}
                ).get("required_http_headers", [])
                if not native["headers"].get(header)
            ],
            "missing_json_proof_fields": [
                field
                for field in foundation_api_profile.get(
                    "response_metadata_contract", {}
                ).get("required_json_fields", [])
                if not native["json_proof_hashes"].get(field)
            ],
            "missing_citation_paths": [
                path
                for path in adapter_row.get("citation_mapping_paths", [])
                if native["citation_path_observations"].get(path) is not True
            ],
            "missing_tool_paths": [
                path
                for path in adapter_row.get("tool_mapping_paths", [])
                if native["tool_path_observations"].get(path) is not True
            ],
        },
        "commitments": {
            "native_response_observation_hash": hash_payload(native),
            "adapter_row_hash": adapter_row.get("provider_adapter_row_hash", ""),
            "conformance_row_hash": conformance_row.get(
                "foundation_provider_conformance_row_hash", ""
            ),
            "schema": FOUNDATION_RUNTIME_ADAPTER_SCHEMA,
        },
        "schemas": {
            "foundation_runtime_adapter": FOUNDATION_RUNTIME_ADAPTER_SCHEMA,
            "foundation_provider_conformance": "docs/schemas/foundation_provider_conformance.schema.json",
            "composite_foundation_adapter": "docs/schemas/composite_foundation_adapter.schema.json",
            "foundation_api_profile": "docs/schemas/foundation_attribution_profile.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "citation_url_health": "docs/schemas/citation_url_health.schema.json",
        },
        "privacy": {
            "raw_native_response_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "hash_only_native_response_observation": True,
        },
        "summary": {
            "status": "blocked" if blocked else "released",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family": native["provider_family"],
            "provider_id": native["provider_id"],
            "failed_check_count": len(failed),
            "failure_mode_count": len(failure_modes),
            "runtime_release_authorized": not blocked,
            "fail_closed_runtime_adapter_supported": blocked or not failed,
            "native_response_normalized_to_rdllm": not blocked,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["foundation_runtime_adapter_hash"] = hash_payload(_hashable_report(report))
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


def validate_foundation_runtime_adapter_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "runtime_adapter_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "native_response_observation",
        "adapter_binding",
        "conformance_binding",
        "normalized_rdllm_contract",
        "runtime_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "foundation_runtime_adapter_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing foundation runtime adapter field: {key}")
    if errors:
        return errors
    if report.get("runtime_adapter_version") != FOUNDATION_RUNTIME_ADAPTER_VERSION:
        errors.append("foundation runtime adapter version is unsupported")
    if (
        report.get("schemas", {}).get("foundation_runtime_adapter")
        != FOUNDATION_RUNTIME_ADAPTER_SCHEMA
    ):
        errors.append("foundation runtime adapter schema is not declared")
    for key in (
        "provider_id",
        "provider_family",
        "native_api_version",
        "native_response_id",
        "native_model",
        "native_output_hash",
        "headers",
        "json_proof_hashes",
        "stream_final_event_hashes",
    ):
        if key not in report.get("native_response_observation", {}):
            errors.append(f"missing native response observation field: {key}")
    return errors


def verify_foundation_runtime_adapter_report(
    report: dict[str, Any],
    *,
    adapter_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L127 runtime adapter receipt against replay inputs."""

    errors = validate_foundation_runtime_adapter_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "foundation_runtime_adapter_hash"
    ):
        errors.append("foundation runtime adapter hash is not reproducible")

    expected = make_foundation_runtime_adapter_report(
        adapter_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "native_response_observation",
        "adapter_binding",
        "conformance_binding",
        "normalized_rdllm_contract",
        "runtime_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"foundation runtime adapter {key} does not match inputs")
    if expected.get("foundation_runtime_adapter_hash") != report.get(
        "foundation_runtime_adapter_hash"
    ):
        errors.append("foundation runtime adapter hash does not match inputs")

    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("foundation runtime adapter target level is not RDLLM-L127")
    if report.get("summary", {}).get("status") not in {"released", "blocked"}:
        errors.append("foundation runtime adapter status is unsupported")
    decision = report.get("runtime_decision", {})
    if report.get("summary", {}).get("status") == "blocked":
        if decision.get("decision") != "block_display" or decision.get("release_authorized"):
            errors.append("foundation runtime adapter blocked report is not fail-closed")
    else:
        if decision.get("decision") != "release" or not decision.get("release_authorized"):
            errors.append("foundation runtime adapter released report is not releasable")

    if _contains_private_fields(report):
        errors.append("foundation runtime adapter exposes private field names")
    if not _private_strings_absent(report, adapter_input):
        errors.append("foundation runtime adapter exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("foundation runtime adapter is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("foundation runtime adapter signature is invalid")

    return errors
