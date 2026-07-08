"""Provider-neutral adapters for composite RDLLM adoption.

This layer turns RDLLM from a reference API into a universal foundation-model
contract. It proves that native OpenAI-, Anthropic-, Google-, Meta-, Mistral-,
Cohere-, xAI-, Bedrock-, Azure OpenAI-, or OpenAI-compatible responses map into
the same RDLLM response envelope, footer, URL-health, and verification metadata
without exposing raw prompts or source text.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

COMPOSITE_FOUNDATION_ADAPTER_VERSION = "rdllm-composite-foundation-adapter/v1"
COMPOSITE_FOUNDATION_ADAPTER_SCHEMA = (
    "docs/schemas/composite_foundation_adapter.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L125"
MINIMUM_INPUT_LEVEL = "RDLLM-L124"

DEFAULT_PROVIDER_FAMILIES = (
    "openai_responses",
    "anthropic_messages",
    "google_gemini",
    "meta_llama",
    "mistral_chat",
    "cohere_chat",
    "xai_grok",
    "amazon_bedrock_converse",
    "azure_openai_responses",
    "openai_compatible_chat",
)

DECLARED_HASH_FIELDS = (
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


def load_composite_foundation_adapter_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L125 composite adapter report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"composite_foundation_adapter_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], adapter_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in adapter_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(adapter_input: dict[str, Any]) -> dict[str, Any]:
    policy = adapter_input.get("policy", {})
    return {
        "profile": "rdllm-composite-foundation-adapter-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_provider_families": list(
            policy.get("required_provider_families", DEFAULT_PROVIDER_FAMILIES)
        ),
        "native_output_hash_match_required": bool(
            policy.get("native_output_hash_match_required", True)
        ),
        "required_metadata_maps_headers": bool(
            policy.get("required_metadata_maps_headers", True)
        ),
        "required_json_maps_fields": bool(policy.get("required_json_maps_fields", True)),
        "citation_and_tool_paths_required": bool(
            policy.get("citation_and_tool_paths_required", True)
        ),
        "streaming_final_event_hashes_required": bool(
            policy.get("streaming_final_event_hashes_required", True)
        ),
        "fail_closed_on_adapter_failure": bool(
            policy.get("fail_closed_on_adapter_failure", True)
        ),
        "raw_native_response_disclosure_allowed": False,
        "raw_prompt_or_source_text_disclosure_allowed": False,
    }


def _foundation_required_headers(foundation_api_profile: dict[str, Any]) -> list[str]:
    return list(
        foundation_api_profile.get("response_metadata_contract", {}).get(
            "required_http_headers", []
        )
    )


def _foundation_required_json_fields(foundation_api_profile: dict[str, Any]) -> list[str]:
    return list(
        foundation_api_profile.get("response_metadata_contract", {}).get(
            "required_json_fields", []
        )
    )


def _artifact_bindings(adapter_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "foundation_api_profile": adapter_input.get("foundation_api_profile"),
        "response_envelope": adapter_input.get("response_envelope"),
        "source_footer_delivery": adapter_input.get("source_footer_delivery"),
        "citation_url_health": adapter_input.get("citation_url_health"),
        "discovery_manifest": adapter_input.get("discovery_manifest"),
        "integration_profile": adapter_input.get("integration_profile"),
        "provider_attribution_card": adapter_input.get("provider_card"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("adapter_version")
            or (artifact or {}).get("version")
            or (artifact or {}).get("url_health_version")
            or (artifact or {}).get("delivery_version")
            or (artifact or {}).get("envelope_version")
            or (artifact or {}).get("manifest_version")
            or (artifact or {}).get("profile_version")
            or (artifact or {}).get("card_version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _metadata_maps_all(required: list[str], mapping: dict[str, Any]) -> bool:
    return all(bool(mapping.get(item)) for item in required)


def _native_rows(
    *,
    adapter_input: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    response_envelope = adapter_input.get("response_envelope", {})
    foundation_api_profile = adapter_input.get("foundation_api_profile", {})
    citation_url_health = adapter_input.get("citation_url_health", {})
    response = response_envelope.get("response", {})
    rendered_hash = str(response.get("rendered_output_hash", ""))
    required_headers = _foundation_required_headers(foundation_api_profile)
    required_json_fields = _foundation_required_json_fields(foundation_api_profile)
    rows: list[dict[str, Any]] = []
    for index, mapping in enumerate(adapter_input.get("provider_adapter_mappings", []), start=1):
        header_mappings = {
            str(key): str(value)
            for key, value in mapping.get("header_mappings", {}).items()
        }
        json_field_mappings = {
            str(key): str(value)
            for key, value in mapping.get("json_field_mappings", {}).items()
        }
        stream_hashes = {
            str(key): str(value)
            for key, value in mapping.get("stream_final_event_hashes", {}).items()
        }
        citation_paths = [str(item) for item in mapping.get("citation_mapping_paths", [])]
        tool_paths = [str(item) for item in mapping.get("tool_mapping_paths", [])]
        native_output_hash = str(mapping.get("native_output_hash", ""))
        public = {
            "display_order": index,
            "provider_id": str(mapping.get("provider_id", "")),
            "provider_family": str(mapping.get("provider_family", "")),
            "native_api_version": str(mapping.get("native_api_version", "")),
            "native_response_id": str(mapping.get("native_response_id", "")),
            "native_model": str(mapping.get("native_model", "")),
            "native_status": str(mapping.get("native_status", "")),
            "native_created_at": str(mapping.get("native_created_at", "")),
            "rdllm_event_id": str(mapping.get("rdllm_event_id", response.get("event_id", ""))),
            "rdllm_response_envelope_hash": str(
                mapping.get(
                    "rdllm_response_envelope_hash",
                    response_envelope.get("envelope_hash", ""),
                )
            ),
            "foundation_profile_hash": str(
                mapping.get(
                    "foundation_profile_hash",
                    foundation_api_profile.get("foundation_profile_hash", ""),
                )
            ),
            "citation_url_health_hash": str(
                mapping.get(
                    "citation_url_health_hash",
                    citation_url_health.get("citation_url_health_hash", ""),
                )
            ),
            "rendered_output_hash": rendered_hash,
            "native_output_hash": native_output_hash,
            "native_output_hash_matches_rdllm": native_output_hash == rendered_hash,
            "native_output_path": str(mapping.get("native_output_path", "")),
            "header_mappings": header_mappings,
            "json_field_mappings": json_field_mappings,
            "citation_mapping_paths": citation_paths,
            "tool_mapping_paths": tool_paths,
            "stream_final_event_hashes": stream_hashes,
            "required_headers_mapped": _metadata_maps_all(required_headers, header_mappings),
            "required_json_fields_mapped": _metadata_maps_all(
                required_json_fields, json_field_mappings
            ),
            "citation_paths_declared": bool(citation_paths),
            "tool_paths_declared": bool(tool_paths),
            "stream_final_event_binds_hashes": (
                stream_hashes.get("RDLLM-Response-Envelope-Hash")
                == response_envelope.get("envelope_hash", "")
                and stream_hashes.get("RDLLM-Foundation-Profile-Hash")
                == foundation_api_profile.get("foundation_profile_hash", "")
                and stream_hashes.get("RDLLM-Citation-URL-Health-Hash")
                == citation_url_health.get("citation_url_health_hash", "")
            ),
            "failure_policy": {
                "on_missing_rdllm_metadata": str(
                    mapping.get("failure_policy", {}).get(
                        "on_missing_rdllm_metadata", "block_display"
                    )
                ),
                "on_hash_mismatch": str(
                    mapping.get("failure_policy", {}).get(
                        "on_hash_mismatch", "block_display"
                    )
                ),
                "on_unverified_citation": str(
                    mapping.get("failure_policy", {}).get(
                        "on_unverified_citation", "block_display"
                    )
                ),
            },
            "native_response_shape_hash": str(mapping.get("native_response_shape_hash", "")),
        }
        public["fail_closed_policy_declared"] = all(
            value in {"block_display", "refuse", "label_unattributed"}
            for value in public["failure_policy"].values()
        )
        public["provider_adapter_row_hash"] = hash_payload(
            {key: value for key, value in public.items() if key != "provider_adapter_row_hash"}
        )
        rows.append(public)
    return rows


def _checks(
    *,
    adapter_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, bool]:
    foundation_api_profile = adapter_input.get("foundation_api_profile", {})
    response_envelope = adapter_input.get("response_envelope", {})
    citation_url_health = adapter_input.get("citation_url_health", {})
    required_families = set(policy["required_provider_families"])
    observed_families = {row["provider_family"] for row in rows}
    public_report = {
        "artifact_bindings": artifact_bindings,
        "provider_adapter_rows": rows,
    }
    return {
        "artifact_hashes_reproducible": (
            artifact_bindings["foundation_api_profile"]["present"]
            and artifact_bindings["foundation_api_profile"]["hash_reproducible"]
            and artifact_bindings["response_envelope"]["present"]
            and artifact_bindings["response_envelope"]["hash_reproducible"]
            and artifact_bindings["citation_url_health"]["present"]
            and artifact_bindings["citation_url_health"]["hash_reproducible"]
        ),
        "foundation_api_profile_ready_l104": (
            foundation_api_profile.get("summary", {}).get("status") == "ready"
            and foundation_api_profile.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L104"
        ),
        "citation_url_health_ready_l124": (
            citation_url_health.get("summary", {}).get("status") == "ready"
            and citation_url_health.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L124"
        ),
        "response_envelope_hash_reproducible": _artifact_hash_is_reproducible(
            response_envelope
        ),
        "adapter_rows_cover_required_provider_families": required_families.issubset(
            observed_families
        ),
        "adapter_rows_have_native_identity": all(
            row["provider_id"]
            and row["provider_family"]
            and row["native_response_id"]
            and row["native_model"]
            for row in rows
        ),
        "adapter_rows_bind_response_envelope": all(
            row["rdllm_response_envelope_hash"]
            == response_envelope.get("envelope_hash", "")
            for row in rows
        ),
        "adapter_rows_bind_foundation_profile": all(
            row["foundation_profile_hash"]
            == foundation_api_profile.get("foundation_profile_hash", "")
            for row in rows
        ),
        "adapter_rows_bind_citation_url_health": all(
            row["citation_url_health_hash"]
            == citation_url_health.get("citation_url_health_hash", "")
            for row in rows
        ),
        "native_output_hashes_match_rdllm": (
            not policy["native_output_hash_match_required"]
            or all(row["native_output_hash_matches_rdllm"] for row in rows)
        ),
        "required_headers_mapped": (
            not policy["required_metadata_maps_headers"]
            or all(row["required_headers_mapped"] for row in rows)
        ),
        "required_json_fields_mapped": (
            not policy["required_json_maps_fields"]
            or all(row["required_json_fields_mapped"] for row in rows)
        ),
        "native_citation_and_tool_paths_declared": (
            not policy["citation_and_tool_paths_required"]
            or all(
                row["citation_paths_declared"] and row["tool_paths_declared"]
                for row in rows
            )
        ),
        "streaming_final_events_bind_rdllm_hashes": (
            not policy["streaming_final_event_hashes_required"]
            or all(row["stream_final_event_binds_hashes"] for row in rows)
        ),
        "failure_policy_blocks_display": (
            not policy["fail_closed_on_adapter_failure"]
            or all(row["fail_closed_policy_declared"] for row in rows)
        ),
        "adapter_row_hashes_present": all(
            row["provider_adapter_row_hash"] for row in rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, adapter_input)
        ),
    }


def make_composite_foundation_adapter_report(
    adapter_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L125 provider-neutral adapter report."""

    policy = _policy(adapter_input)
    artifact_bindings = _artifact_bindings(adapter_input)
    rows = _native_rows(adapter_input=adapter_input, policy=policy)
    checks = _checks(
        adapter_input=adapter_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        rows=rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    required_families = set(policy["required_provider_families"])
    observed_families = {row["provider_family"] for row in rows}
    report: dict[str, Any] = {
        "adapter_version": COMPOSITE_FOUNDATION_ADAPTER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_adapter_rows": rows,
        "composite_contract": {
            "profile": "rdllm-universal-foundation-model-contract/v1",
            "provider_families": sorted(observed_families),
            "required_provider_families": sorted(required_families),
            "portable_response_object": "rdllm-response-envelope/v1",
            "portable_attribution_footer": "rdllm-source-footer-delivery/v1",
            "portable_url_health": "rdllm-citation-url-health/v1",
            "adapter_row_root": merkle_root(
                [row["provider_adapter_row_hash"] for row in rows]
            ),
            "adoption_target": "foundation-model-provider-neutral",
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "missing_provider_families": sorted(required_families - observed_families),
            "native_output_hash_mismatch_providers": [
                row["provider_id"]
                for row in rows
                if not row["native_output_hash_matches_rdllm"]
            ],
            "missing_header_mapping_providers": [
                row["provider_id"] for row in rows if not row["required_headers_mapped"]
            ],
            "missing_json_mapping_providers": [
                row["provider_id"] for row in rows if not row["required_json_fields_mapped"]
            ],
            "missing_stream_binding_providers": [
                row["provider_id"]
                for row in rows
                if not row["stream_final_event_binds_hashes"]
            ],
            "non_fail_closed_providers": [
                row["provider_id"] for row in rows if not row["fail_closed_policy_declared"]
            ],
        },
        "commitments": {
            "artifact_binding_root": merkle_root(
                [
                    row["declared_hash"]
                    for row in artifact_bindings.values()
                    if row["declared_hash"]
                ]
            ),
            "adapter_row_root": merkle_root(
                [row["provider_adapter_row_hash"] for row in rows]
            ),
            "provider_family_root": hash_payload(sorted(observed_families)),
            "schema": COMPOSITE_FOUNDATION_ADAPTER_SCHEMA,
        },
        "schemas": {
            "composite_foundation_adapter": COMPOSITE_FOUNDATION_ADAPTER_SCHEMA,
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
            "raw_tool_output_disclosed": False,
            "hash_only_native_output_commitments": True,
        },
        "summary": {
            "status": "ready" if not failed else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_adapter_count": len(rows),
            "required_provider_family_count": len(required_families),
            "covered_provider_family_count": len(observed_families & required_families),
            "failed_check_count": len(failed),
            "universal_foundation_model_contract_supported": checks[
                "adapter_rows_cover_required_provider_families"
            ],
            "native_response_hash_binding_supported": checks[
                "native_output_hashes_match_rdllm"
            ],
            "provider_neutral_metadata_supported": checks[
                "required_headers_mapped"
            ]
            and checks["required_json_fields_mapped"],
            "streaming_adapter_supported": checks[
                "streaming_final_events_bind_rdllm_hashes"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["composite_foundation_adapter_hash"] = hash_payload(_hashable_report(report))
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


def validate_composite_foundation_adapter_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "adapter_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "provider_adapter_rows",
        "composite_contract",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "composite_foundation_adapter_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing composite foundation adapter field: {key}")
    if errors:
        return errors
    if report.get("adapter_version") != COMPOSITE_FOUNDATION_ADAPTER_VERSION:
        errors.append("composite foundation adapter version is unsupported")
    if (
        report.get("schemas", {}).get("composite_foundation_adapter")
        != COMPOSITE_FOUNDATION_ADAPTER_SCHEMA
    ):
        errors.append("composite foundation adapter schema is not declared")
    for row in report.get("provider_adapter_rows", []):
        for key in (
            "provider_id",
            "provider_family",
            "native_response_id",
            "native_model",
            "rdllm_response_envelope_hash",
            "foundation_profile_hash",
            "citation_url_health_hash",
            "native_output_hash",
            "rendered_output_hash",
            "provider_adapter_row_hash",
        ):
            if key not in row:
                errors.append(f"missing composite adapter row field: {key}")
    return errors


def verify_composite_foundation_adapter_report(
    report: dict[str, Any],
    *,
    adapter_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L125 composite adapter report against replay inputs."""

    errors = validate_composite_foundation_adapter_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "composite_foundation_adapter_hash"
    ):
        errors.append("composite foundation adapter hash is not reproducible")

    expected = make_composite_foundation_adapter_report(
        adapter_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "provider_adapter_rows",
        "composite_contract",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"composite foundation adapter {key} does not match inputs")
    if expected.get("composite_foundation_adapter_hash") != report.get(
        "composite_foundation_adapter_hash"
    ):
        errors.append("composite foundation adapter hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("composite foundation adapter status is not ready")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("composite foundation adapter target level is not RDLLM-L125")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"composite foundation adapter check failed: {check}")

    if _contains_private_fields(report):
        errors.append("composite foundation adapter exposes private field names")
    if not _private_strings_absent(report, adapter_input):
        errors.append("composite foundation adapter exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("composite foundation adapter is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("composite foundation adapter signature is invalid")

    return errors
