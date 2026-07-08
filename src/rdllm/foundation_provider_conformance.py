"""Provider conformance matrix for attribution-capable foundation APIs.

This layer turns a provider-neutral adapter claim into a public conformance
claim. It proves that each supported foundation-model API family has replayed
fixtures for synchronous answers, streaming, tools, citations or grounding,
URL-health binding, structured proof fields, and fail-closed behavior.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from rdllm.composite_foundation_adapter import (
    DEFAULT_PROVIDER_FAMILIES as COMPOSITE_PROVIDER_FAMILIES,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

FOUNDATION_PROVIDER_CONFORMANCE_VERSION = (
    "rdllm-foundation-provider-conformance/v1"
)
FOUNDATION_PROVIDER_CONFORMANCE_SCHEMA = (
    "docs/schemas/foundation_provider_conformance.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L126"
MINIMUM_INPUT_LEVEL = "RDLLM-L125"

DEFAULT_REQUIRED_CAPABILITIES = (
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

DEFAULT_REQUIRED_NEGATIVE_FIXTURES = (
    "missing_required_header",
    "native_output_hash_mismatch",
    "unverified_citation_url",
    "unsupported_claim_footer",
    "stream_final_hash_drift",
    "private_text_leak",
)

DEFAULT_REQUIRED_ARTIFACTS = (
    "response_envelope",
    "source_footer_delivery",
    "citation_url_health",
    "foundation_api_profile",
    "composite_foundation_adapter",
)

DECLARED_HASH_FIELDS = (
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "foundation_profile_hash",
    "citation_url_health_hash",
    "source_footer_delivery_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "vector_pack_hash",
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


def load_foundation_provider_conformance_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L126 provider conformance report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"foundation_provider_conformance_hash", "signature"}
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
    conformance_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in conformance_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(conformance_input: dict[str, Any]) -> dict[str, Any]:
    policy = conformance_input.get("policy", {})
    return {
        "profile": "rdllm-foundation-provider-conformance-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_provider_families": list(
            policy.get("required_provider_families", COMPOSITE_PROVIDER_FAMILIES)
        ),
        "required_capabilities": list(
            policy.get("required_capabilities", DEFAULT_REQUIRED_CAPABILITIES)
        ),
        "required_negative_fixtures": list(
            policy.get(
                "required_negative_fixtures", DEFAULT_REQUIRED_NEGATIVE_FIXTURES
            )
        ),
        "required_rdllm_artifacts": list(
            policy.get("required_rdllm_artifacts", DEFAULT_REQUIRED_ARTIFACTS)
        ),
        "official_documentation_required": bool(
            policy.get("official_documentation_required", True)
        ),
        "adapter_row_backing_required": bool(
            policy.get("adapter_row_backing_required", True)
        ),
        "hash_only_fixture_commitments_required": bool(
            policy.get("hash_only_fixture_commitments_required", True)
        ),
        "fail_closed_on_conformance_failure": bool(
            policy.get("fail_closed_on_conformance_failure", True)
        ),
        "claim_support_and_footer_required": bool(
            policy.get("claim_support_and_footer_required", True)
        ),
        "parametric_memory_fallback_required": bool(
            policy.get("parametric_memory_fallback_required", True)
        ),
        "raw_prompt_or_source_text_disclosure_allowed": False,
    }


def _artifact_bindings(conformance_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "composite_foundation_adapter": conformance_input.get(
            "composite_foundation_adapter"
        ),
        "foundation_api_profile": conformance_input.get("foundation_api_profile"),
        "citation_url_health": conformance_input.get("citation_url_health"),
        "source_footer_delivery": conformance_input.get("source_footer_delivery"),
        "integration_profile": conformance_input.get("integration_profile"),
        "discovery_manifest": conformance_input.get("discovery_manifest"),
        "provider_attribution_card": conformance_input.get("provider_card"),
        "conformance_vector_pack": conformance_input.get("conformance_vector_pack"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("conformance_version")
            or (artifact or {}).get("adapter_version")
            or (artifact or {}).get("version")
            or (artifact or {}).get("url_health_version")
            or (artifact or {}).get("delivery_version")
            or (artifact or {}).get("manifest_version")
            or (artifact or {}).get("profile_version")
            or (artifact or {}).get("card_version")
            or (artifact or {}).get("vector_pack_version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": (
                True if artifact is None else _artifact_hash_is_reproducible(artifact)
            ),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _adapter_rows_by_family(
    composite_foundation_adapter: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in composite_foundation_adapter.get("provider_adapter_rows", []):
        family = str(row.get("provider_family", ""))
        if family:
            rows[family] = row
    return rows


def _hash_map(value: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(item)
        for key, item in value.items()
        if str(item).strip()
    }


def _failure_policy(row: dict[str, Any]) -> dict[str, str]:
    policy = row.get("failure_policy", {})
    return {
        str(key): str(value)
        for key, value in policy.items()
        if str(key).strip() and str(value).strip()
    }


def _conformance_rows(
    *,
    conformance_input: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    adapter_rows = _adapter_rows_by_family(
        conformance_input.get("composite_foundation_adapter", {})
    )
    required_capabilities = tuple(policy["required_capabilities"])
    rows: list[dict[str, Any]] = []
    for index, source_row in enumerate(
        conformance_input.get("provider_capability_rows", []), start=1
    ):
        family = str(source_row.get("provider_family", ""))
        adapter_row = adapter_rows.get(family, {})
        capabilities = {
            capability: bool(source_row.get("capabilities", {}).get(capability))
            for capability in required_capabilities
        }
        positive_hashes = _hash_map(source_row.get("positive_fixture_hashes", {}))
        negative_hashes = _hash_map(source_row.get("negative_fixture_hashes", {}))
        rdllm_artifacts = [
            str(item)
            for item in source_row.get("rdllm_artifacts_supported", [])
            if str(item).strip()
        ]
        official_refs = [
            str(item)
            for item in source_row.get("official_documentation_refs", [])
            if str(item).strip()
        ]
        failure_policy = _failure_policy(source_row)
        public = {
            "display_order": index,
            "provider_id": str(source_row.get("provider_id", "")),
            "provider_family": family,
            "native_api_version": str(source_row.get("native_api_version", "")),
            "native_model": str(source_row.get("native_model", "")),
            "certification_profile": str(
                source_row.get(
                    "certification_profile",
                    "rdllm-provider-attribution-conformance/v1",
                )
            ),
            "provider_adapter_row_hash": str(
                source_row.get(
                    "provider_adapter_row_hash",
                    adapter_row.get("provider_adapter_row_hash", ""),
                )
            ),
            "adapter_row_hash_matches_composite": str(
                source_row.get(
                    "provider_adapter_row_hash",
                    adapter_row.get("provider_adapter_row_hash", ""),
                )
            )
            == str(adapter_row.get("provider_adapter_row_hash", "")),
            "capabilities": capabilities,
            "positive_fixture_hashes": positive_hashes,
            "negative_fixture_hashes": negative_hashes,
            "rdllm_artifacts_supported": rdllm_artifacts,
            "official_documentation_refs": official_refs,
            "failure_policy": failure_policy,
            "conformance_vector_pack_hash": str(
                source_row.get(
                    "conformance_vector_pack_hash",
                    _declared_hash(conformance_input.get("conformance_vector_pack")),
                )
            ),
        }
        public["capability_coverage_count"] = sum(
            1 for enabled in capabilities.values() if enabled
        )
        public["positive_fixture_coverage_count"] = sum(
            1 for capability in required_capabilities if positive_hashes.get(capability)
        )
        public["negative_fixture_coverage_count"] = sum(
            1
            for failure_mode in policy["required_negative_fixtures"]
            if negative_hashes.get(failure_mode)
        )
        public["fail_closed_policy_declared"] = all(
            failure_policy.get(failure_mode) in {"block_display", "refuse", "escalate"}
            for failure_mode in policy["required_negative_fixtures"]
        )
        public["foundation_provider_conformance_row_hash"] = hash_payload(
            {
                key: value
                for key, value in public.items()
                if key != "foundation_provider_conformance_row_hash"
            }
        )
        rows.append(public)
    return rows


def _checks(
    *,
    conformance_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, bool]:
    composite_adapter = conformance_input.get("composite_foundation_adapter", {})
    required_families = set(policy["required_provider_families"])
    observed_families = {row["provider_family"] for row in rows}
    required_capabilities = set(policy["required_capabilities"])
    required_negative = set(policy["required_negative_fixtures"])
    required_artifacts = set(policy["required_rdllm_artifacts"])
    public_report = {
        "artifact_bindings": artifact_bindings,
        "provider_conformance_rows": rows,
    }
    required_artifact_bindings = (
        "composite_foundation_adapter",
        "foundation_api_profile",
        "citation_url_health",
        "source_footer_delivery",
        "integration_profile",
        "discovery_manifest",
        "provider_attribution_card",
    )
    return {
        "artifact_hashes_reproducible": all(
            artifact_bindings[name]["present"]
            and artifact_bindings[name]["hash_reproducible"]
            for name in required_artifact_bindings
        )
        and artifact_bindings["conformance_vector_pack"]["hash_reproducible"],
        "composite_adapter_ready_l125": (
            composite_adapter.get("summary", {}).get("status") == "ready"
            and composite_adapter.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L125"
        ),
        "provider_rows_cover_required_provider_families": required_families.issubset(
            observed_families
        ),
        "provider_rows_backed_by_composite_adapter": (
            not policy["adapter_row_backing_required"]
            or all(
                row["provider_adapter_row_hash"]
                and row["adapter_row_hash_matches_composite"]
                for row in rows
            )
        ),
        "required_capabilities_declared": all(
            required_capabilities.issubset(
                {
                    capability
                    for capability, enabled in row["capabilities"].items()
                    if enabled
                }
            )
            for row in rows
        ),
        "positive_fixtures_cover_required_capabilities": (
            not policy["hash_only_fixture_commitments_required"]
            or all(
                required_capabilities.issubset(
                    set(row["positive_fixture_hashes"].keys())
                )
                for row in rows
            )
        ),
        "negative_fixtures_cover_fail_closed_modes": (
            not policy["hash_only_fixture_commitments_required"]
            or all(
                required_negative.issubset(set(row["negative_fixture_hashes"].keys()))
                for row in rows
            )
        ),
        "official_documentation_declared": (
            not policy["official_documentation_required"]
            or all(row["official_documentation_refs"] for row in rows)
        ),
        "required_rdllm_artifacts_supported": all(
            required_artifacts.issubset(set(row["rdllm_artifacts_supported"]))
            for row in rows
        ),
        "streaming_tool_and_citation_modes_bound": all(
            row["capabilities"].get("streaming_response")
            and row["capabilities"].get("tool_calling")
            and row["capabilities"].get("citation_or_grounding")
            and row["capabilities"].get("url_health_binding")
            for row in rows
        ),
        "claim_support_footer_bound": (
            not policy["claim_support_and_footer_required"]
            or all(row["capabilities"].get("claim_support_footer") for row in rows)
        ),
        "parametric_memory_fallback_bound": (
            not policy["parametric_memory_fallback_required"]
            or all(
                row["capabilities"].get("parametric_memory_fallback")
                for row in rows
            )
        ),
        "structured_proof_fields_bound": all(
            row["capabilities"].get("structured_proof_fields") for row in rows
        ),
        "fail_closed_policy_declared": (
            not policy["fail_closed_on_conformance_failure"]
            or all(row["fail_closed_policy_declared"] for row in rows)
        ),
        "conformance_row_hashes_present": all(
            row["foundation_provider_conformance_row_hash"] for row in rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, conformance_input)
        ),
    }


def make_foundation_provider_conformance_report(
    conformance_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L126 provider conformance matrix report."""

    policy = _policy(conformance_input)
    artifact_bindings = _artifact_bindings(conformance_input)
    rows = _conformance_rows(conformance_input=conformance_input, policy=policy)
    checks = _checks(
        conformance_input=conformance_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        rows=rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    required_families = set(policy["required_provider_families"])
    observed_families = {row["provider_family"] for row in rows}
    required_capabilities = set(policy["required_capabilities"])
    required_negative = set(policy["required_negative_fixtures"])
    report: dict[str, Any] = {
        "conformance_version": FOUNDATION_PROVIDER_CONFORMANCE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_conformance_rows": rows,
        "conformance_matrix": {
            "profile": "rdllm-universal-foundation-provider-conformance/v1",
            "provider_families": sorted(observed_families),
            "required_provider_families": sorted(required_families),
            "required_capabilities": sorted(required_capabilities),
            "required_negative_fixtures": sorted(required_negative),
            "row_root": merkle_root(
                [
                    row["foundation_provider_conformance_row_hash"]
                    for row in rows
                ]
            ),
            "positive_fixture_root": merkle_root(
                [
                    row["positive_fixture_hashes"][fixture_name]
                    for row in rows
                    for fixture_name in sorted(row["positive_fixture_hashes"])
                ]
            ),
            "negative_fixture_root": merkle_root(
                [
                    row["negative_fixture_hashes"][fixture_name]
                    for row in rows
                    for fixture_name in sorted(row["negative_fixture_hashes"])
                ]
            ),
            "adoption_target": "provider-public-attribution-conformance",
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "missing_provider_families": sorted(required_families - observed_families),
            "providers_missing_capabilities": [
                row["provider_id"]
                for row in rows
                if not required_capabilities.issubset(
                    {
                        capability
                        for capability, enabled in row["capabilities"].items()
                        if enabled
                    }
                )
            ],
            "providers_missing_positive_fixtures": [
                row["provider_id"]
                for row in rows
                if not required_capabilities.issubset(
                    set(row["positive_fixture_hashes"].keys())
                )
            ],
            "providers_missing_negative_fixtures": [
                row["provider_id"]
                for row in rows
                if not required_negative.issubset(
                    set(row["negative_fixture_hashes"].keys())
                )
            ],
            "providers_missing_adapter_backing": [
                row["provider_id"]
                for row in rows
                if not row["adapter_row_hash_matches_composite"]
            ],
            "providers_missing_official_docs": [
                row["provider_id"]
                for row in rows
                if not row["official_documentation_refs"]
            ],
            "providers_missing_fail_closed_policy": [
                row["provider_id"]
                for row in rows
                if not row["fail_closed_policy_declared"]
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
            "provider_conformance_row_root": merkle_root(
                [
                    row["foundation_provider_conformance_row_hash"]
                    for row in rows
                ]
            ),
            "provider_family_root": hash_payload(sorted(observed_families)),
            "capability_root": hash_payload(sorted(required_capabilities)),
            "negative_fixture_root": hash_payload(sorted(required_negative)),
            "schema": FOUNDATION_PROVIDER_CONFORMANCE_SCHEMA,
        },
        "schemas": {
            "foundation_provider_conformance": FOUNDATION_PROVIDER_CONFORMANCE_SCHEMA,
            "composite_foundation_adapter": "docs/schemas/composite_foundation_adapter.schema.json",
            "foundation_api_profile": "docs/schemas/foundation_attribution_profile.schema.json",
            "citation_url_health": "docs/schemas/citation_url_health.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
        "privacy": {
            "raw_fixture_payloads_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "hash_only_fixture_commitments": True,
        },
        "summary": {
            "status": "ready" if not failed else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_conformance_row_count": len(rows),
            "required_provider_family_count": len(required_families),
            "covered_provider_family_count": len(
                observed_families & required_families
            ),
            "required_capability_count": len(required_capabilities),
            "required_negative_fixture_count": len(required_negative),
            "failed_check_count": len(failed),
            "universal_provider_conformance_supported": checks[
                "provider_rows_cover_required_provider_families"
            ]
            and checks["required_capabilities_declared"],
            "grounded_footer_attribution_supported": checks[
                "claim_support_footer_bound"
            ],
            "parametric_memory_fallback_supported": checks[
                "parametric_memory_fallback_bound"
            ],
            "hash_only_conformance_fixtures_supported": checks[
                "positive_fixtures_cover_required_capabilities"
            ]
            and checks["negative_fixtures_cover_fail_closed_modes"],
            "fail_closed_conformance_supported": checks[
                "fail_closed_policy_declared"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["foundation_provider_conformance_hash"] = hash_payload(
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


def validate_foundation_provider_conformance_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "conformance_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "provider_conformance_rows",
        "conformance_matrix",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "foundation_provider_conformance_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing foundation provider conformance field: {key}")
    if errors:
        return errors
    if report.get("conformance_version") != FOUNDATION_PROVIDER_CONFORMANCE_VERSION:
        errors.append("foundation provider conformance version is unsupported")
    if (
        report.get("schemas", {}).get("foundation_provider_conformance")
        != FOUNDATION_PROVIDER_CONFORMANCE_SCHEMA
    ):
        errors.append("foundation provider conformance schema is not declared")
    for row in report.get("provider_conformance_rows", []):
        for key in (
            "provider_id",
            "provider_family",
            "native_api_version",
            "native_model",
            "provider_adapter_row_hash",
            "capabilities",
            "positive_fixture_hashes",
            "negative_fixture_hashes",
            "rdllm_artifacts_supported",
            "official_documentation_refs",
            "failure_policy",
            "foundation_provider_conformance_row_hash",
        ):
            if key not in row:
                errors.append(f"missing provider conformance row field: {key}")
    return errors


def verify_foundation_provider_conformance_report(
    report: dict[str, Any],
    *,
    conformance_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L126 provider conformance report against replay inputs."""

    errors = validate_foundation_provider_conformance_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "foundation_provider_conformance_hash"
    ):
        errors.append("foundation provider conformance hash is not reproducible")

    expected = make_foundation_provider_conformance_report(
        conformance_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "provider_conformance_rows",
        "conformance_matrix",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"foundation provider conformance {key} does not match inputs")
    if expected.get("foundation_provider_conformance_hash") != report.get(
        "foundation_provider_conformance_hash"
    ):
        errors.append("foundation provider conformance hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("foundation provider conformance status is not ready")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("foundation provider conformance target level is not RDLLM-L126")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"foundation provider conformance check failed: {check}")

    if _contains_private_fields(report):
        errors.append("foundation provider conformance exposes private field names")
    if not _private_strings_absent(report, conformance_input):
        errors.append("foundation provider conformance exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("foundation provider conformance is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("foundation provider conformance signature is invalid")

    return errors
