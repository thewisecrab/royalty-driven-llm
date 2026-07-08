"""Universal foundation provider binding matrix.

The L168 layer binds the L167 composite RDLLM contract to concrete foundation
provider families and runtime route shapes. L167 proves the universal contract is
valid; this layer proves OpenAI-compatible, Anthropic, Google, cloud, router,
local-runtime, RAG, and MCP/agent surfaces actually map their native APIs,
streams, tool calls, source footers, telemetry, revocation checks, and settlement
meters into that contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.provider_family_registry import CANONICAL_PROVIDER_FAMILIES
from rdllm.transparency import merkle_root

UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_VERSION = (
    "rdllm-universal-foundation-provider-binding-matrix/v1"
)
UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_SCHEMA = (
    "docs/schemas/universal_foundation_provider_binding_matrix.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L168"
MINIMUM_COMPOSITE_CONTRACT_LEVEL = "RDLLM-L167"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-foundation-provider-binding-matrix.json"
)

REQUIRED_PROVIDER_FAMILIES = CANONICAL_PROVIDER_FAMILIES

REQUIRED_BINDING_DOMAINS = (
    "identity_and_model_alias_resolution",
    "auth_and_tenant_boundary",
    "request_preflight_negotiation",
    "native_request_mapping",
    "streaming_chunk_mapping",
    "tool_call_and_mcp_mapping",
    "retrieval_and_citation_mapping",
    "response_envelope_mapping",
    "source_footer_rendering",
    "live_attribution_proof_mapping",
    "telemetry_and_meter_mapping",
    "revocation_and_refusal_mapping",
    "copy_export_status_mapping",
    "creator_audit_and_settlement_mapping",
    "negative_canary_execution",
    "public_verifier_publication",
)

REQUIRED_NATIVE_CAPABILITIES = (
    "sync_generation",
    "streaming_generation",
    "tool_calls",
    "retrieval_or_grounding",
    "response_envelope",
    "source_footer",
    "live_attribution_proof",
    "telemetry_spans",
    "settlement_meter",
    "revocation_status",
    "copy_export_status",
    "auditor_export",
)

REQUIRED_NEGATIVE_PROVIDER_FAILURES = (
    "provider_family_not_listed",
    "model_alias_drift",
    "native_route_unbound_to_l167",
    "streaming_chunk_without_footer_binding",
    "tool_call_loses_source_context",
    "retrieval_adapter_drops_locator",
    "sdk_response_shape_mismatch",
    "cloud_gateway_rewrites_response",
    "local_runtime_without_attestation",
    "fallback_model_without_passport",
    "telemetry_or_meter_gap",
    "settlement_provider_mismatch",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_foundation_provider_binding_matrix_hash",
    "universal_composite_rdllm_contract_hash",
    "universal_foundation_model_release_passport_hash",
    "universal_live_attribution_proof_hash",
    "universal_provider_wire_protocol_hash",
    "universal_runtime_conformance_receipt_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "graph_hash",
    "contract_hash",
    "receipt_hash",
    "envelope_hash",
    "distribution_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "training_text",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "authorization",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_foundation_provider_binding_matrix_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L168 provider binding matrix."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_matrix(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in matrix.items()
        if key not in {"universal_foundation_provider_binding_matrix_hash", "signature"}
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


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _level_number(level: Any) -> int | None:
    if not isinstance(level, str) or not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: Any, minimum: str) -> bool:
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


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


def _private_strings_absent(public_payload: dict[str, Any], matrix_input: dict[str, Any]) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in matrix_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _composite_contract_l167_ready(contract: dict[str, Any] | None) -> bool:
    if not isinstance(contract, dict):
        return False
    summary = _summary(contract)
    decision = contract.get("contract_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_COMPOSITE_CONTRACT_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("composite_rdllm_contract_ready") is True
        and decision.get("universal_rdllm_claim_allowed") is True
        and decision.get("foundation_model_invocation_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("creator_settlement_release_allowed") is True
    )


def _domain_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("domain_hash", "fixture_hash", "verifier_hash", "drift_hash")
    required_flags = ("mapped", "tested", "l167_bound", "fail_closed")
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _provider_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "provider_binding_hash",
        "native_api_contract_hash",
        "adapter_hash",
        "conformance_fixture_hash",
        "drift_canary_hash",
        "telemetry_mapping_hash",
        "settlement_meter_hash",
        "revocation_status_hash",
        "public_verifier_hash",
    )
    required_flags = (
        "provider_family_supported",
        "native_api_bound_to_l167",
        "all_required_capabilities_supported",
        "domain_bindings_complete",
        "fail_closed",
        "private_payloads_excluded",
    )
    if not all(str(row.get(field, "")) for field in required_hashes):
        return False
    if not all(row.get(flag) is True for flag in required_flags):
        return False
    capabilities = row.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return False
    if not all(capabilities.get(name) is True for name in REQUIRED_NATIVE_CAPABILITIES):
        return False
    domain_rows = row.get("domain_bindings", {})
    if not isinstance(domain_rows, dict):
        return False
    return all(
        domain in domain_rows and _domain_row_ready(domain_rows.get(domain, {}))
        for domain in REQUIRED_BINDING_DOMAINS
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return bool(row.get("fixture_hash")) and all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "provider_claim_blocked",
            "invocation_blocked",
            "response_release_blocked",
            "source_footer_reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    )


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate: Any,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name
        for name in required
        if name in rows and not predicate(rows.get(name, {}))
    ]
    return missing, incomplete


def _row_map(matrix_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = matrix_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


def make_universal_foundation_provider_binding_matrix(
    matrix_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L168 universal foundation provider binding matrix."""

    composite_contract = matrix_input.get("universal_composite_rdllm_contract")
    provider_rows = _row_map(matrix_input, "provider_binding_rows")
    negative_rows = _row_map(matrix_input, "negative_provider_binding_rows")

    missing_providers, incomplete_providers = _complete_rows(
        provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_row_ready
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows, REQUIRED_NEGATIVE_PROVIDER_FAILURES, _negative_failure_ready
    )

    covered_domains = {
        provider: sorted(
            domain
            for domain in REQUIRED_BINDING_DOMAINS
            if isinstance(provider_rows.get(provider, {}).get("domain_bindings", {}), dict)
            and _domain_row_ready(
                provider_rows.get(provider, {})
                .get("domain_bindings", {})
                .get(domain, {})
            )
        )
        for provider in REQUIRED_PROVIDER_FAMILIES
    }
    covered_capabilities = {
        provider: sorted(
            capability
            for capability in REQUIRED_NATIVE_CAPABILITIES
            if provider_rows.get(provider, {}).get("capabilities", {}).get(capability)
            is True
        )
        for provider in REQUIRED_PROVIDER_FAMILIES
    }

    checks = {
        "composite_contract_bound": _artifact_hash_is_reproducible(
            composite_contract if isinstance(composite_contract, dict) else None
        ),
        "composite_contract_l167_ready": _composite_contract_l167_ready(
            composite_contract if isinstance(composite_contract, dict) else None
        ),
        "provider_families_complete": not missing_providers
        and not incomplete_providers,
        "provider_domain_bindings_complete": all(
            len(covered_domains.get(provider, [])) == len(REQUIRED_BINDING_DOMAINS)
            for provider in REQUIRED_PROVIDER_FAMILIES
        ),
        "native_capabilities_complete": all(
            len(covered_capabilities.get(provider, []))
            == len(REQUIRED_NATIVE_CAPABILITIES)
            for provider in REQUIRED_PROVIDER_FAMILIES
        ),
        "negative_provider_binding_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "provider_binding_matrix_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    matrix_without_privacy: dict[str, Any] = {
        "universal_foundation_provider_binding_matrix_version": (
            UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_VERSION
        ),
        "schema": UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-foundation-provider-binding-matrix-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_composite_contract_level": MINIMUM_COMPOSITE_CONTRACT_LEVEL,
            "named_provider_bindings_required": True,
            "native_api_mapping_required": True,
            "provider_claim_requires_binding_matrix": True,
            "unbound_provider_invocation_blocked": True,
            "source_footer_reliance_requires_provider_binding": True,
            "creator_settlement_requires_provider_binding": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_VERSION,
        },
        "composite_contract_binding": {
            "present": isinstance(composite_contract, dict) and bool(composite_contract),
            "artifact_hash": _declared_hash(
                composite_contract if isinstance(composite_contract, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    composite_contract if isinstance(composite_contract, dict) else None
                )
            ),
            "hash_reproducible": _artifact_hash_is_reproducible(
                composite_contract if isinstance(composite_contract, dict) else None
            ),
            "status": str(_summary(composite_contract).get("status", "")),
            "level": str(
                _summary(composite_contract).get("target_certification_level", "")
            ),
        },
        "provider_binding_rows": {
            provider: provider_rows.get(provider, {})
            for provider in REQUIRED_PROVIDER_FAMILIES
        },
        "negative_provider_binding_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_PROVIDER_FAILURES
        },
        "evidence_roots": {
            "provider_binding_root": merkle_root(
                [
                    hash_payload(
                        {"provider": provider, "row": provider_rows.get(provider, {})}
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                ]
            ),
            "domain_binding_root": merkle_root(
                [
                    hash_payload(
                        {
                            "provider": provider,
                            "domain": domain,
                            "row": provider_rows.get(provider, {})
                            .get("domain_bindings", {})
                            .get(domain, {}),
                        }
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                    for domain in REQUIRED_BINDING_DOMAINS
                ]
            ),
            "capability_root": merkle_root(
                [
                    hash_payload(
                        {
                            "provider": provider,
                            "capability": capability,
                            "enabled": provider_rows.get(provider, {})
                            .get("capabilities", {})
                            .get(capability)
                            is True,
                        }
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                    for capability in REQUIRED_NATIVE_CAPABILITIES
                ]
            ),
            "negative_provider_binding_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_PROVIDER_FAILURES
                ]
            ),
        },
        "checks": checks,
        "provider_binding_decision": {
            "provider_binding_matrix_ready": not failure_modes,
            "universal_provider_adoption_claim_allowed": not failure_modes,
            "bound_provider_invocation_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "cross_provider_procurement_allowed": not failure_modes,
            "creator_settlement_allowed_for_bound_providers": not failure_modes,
            "unbound_provider_claims_blocked": True,
            "failure_modes": failure_modes,
            "missing_provider_families": missing_providers,
            "incomplete_provider_families": incomplete_providers,
            "missing_negative_provider_failures": missing_negative,
            "incomplete_negative_provider_failures": incomplete_negative,
        },
        "provider_coverage": {
            "required_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_family_count": sum(
                1
                for provider in REQUIRED_PROVIDER_FAMILIES
                if _provider_row_ready(provider_rows.get(provider, {}))
            ),
            "required_binding_domain_count": len(REQUIRED_BINDING_DOMAINS),
            "required_native_capability_count": len(REQUIRED_NATIVE_CAPABILITIES),
            "covered_domains": covered_domains,
            "covered_capabilities": covered_capabilities,
        },
        "standards_and_research": {
            "model_documentation_fragmentation": (
                "AI Transparency Atlas identifies inconsistent model documentation "
                "across providers; this matrix turns provider-specific documentation "
                "into machine-verifiable route bindings."
            ),
            "citation_reliability": (
                "Cited but Not Verified and PaperTrail motivate native citation, "
                "locator, claim-evidence, and footer checks per provider route."
            ),
            "open_foundation_model_value_participation": (
                "Recent TDM and foundation-model scholarship motivates downstream "
                "licensing and value-participation hooks at provider and fine-tune "
                "routes."
            ),
        },
    }
    privacy = {
        "private_payload_fields": _contains_private_fields(matrix_without_privacy),
        "private_strings_absent": _private_strings_absent(
            matrix_without_privacy, matrix_input
        ),
    }
    matrix = {
        **matrix_without_privacy,
        "privacy": {
            **privacy,
            "private_payloads_excluded": not privacy["private_payload_fields"]
            and privacy["private_strings_absent"],
        },
    }
    matrix["summary"] = {
        "status": "ready"
        if not failure_modes and matrix["privacy"]["private_payloads_excluded"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_composite_contract_level": MINIMUM_COMPOSITE_CONTRACT_LEVEL,
        "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
        "ready_provider_family_count": matrix["provider_coverage"][
            "ready_provider_family_count"
        ],
        "binding_domain_count": len(REQUIRED_BINDING_DOMAINS),
        "native_capability_count": len(REQUIRED_NATIVE_CAPABILITIES),
        "negative_provider_failure_count": len(REQUIRED_NEGATIVE_PROVIDER_FAILURES),
        "failure_mode_count": len(failure_modes),
        "privacy_preserved": matrix["privacy"]["private_payloads_excluded"],
        "signed_provider_binding_matrix": bool(signing_secret),
    }
    matrix["universal_foundation_provider_binding_matrix_hash"] = hash_payload(
        _hashable_matrix(matrix)
    )
    if signing_secret:
        matrix["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_matrix(matrix), signing_secret),
        }
    return matrix


def validate_universal_foundation_provider_binding_matrix_shape(
    matrix: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L168 matrix."""

    errors: list[str] = []
    required = (
        "universal_foundation_provider_binding_matrix_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "composite_contract_binding",
        "provider_binding_rows",
        "negative_provider_binding_rows",
        "evidence_roots",
        "checks",
        "provider_binding_decision",
        "provider_coverage",
        "privacy",
        "summary",
        "universal_foundation_provider_binding_matrix_hash",
    )
    for key in required:
        if key not in matrix:
            errors.append(f"missing {key}")
    if matrix.get("universal_foundation_provider_binding_matrix_version") != (
        UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_VERSION
    ):
        errors.append("unexpected universal_foundation_provider_binding_matrix_version")
    if matrix.get("schema") != UNIVERSAL_FOUNDATION_PROVIDER_BINDING_MATRIX_SCHEMA:
        errors.append("unexpected schema")
    if _contains_private_fields(matrix):
        errors.append("public matrix contains private field names")
    provider_rows = matrix.get("provider_binding_rows", {})
    if not isinstance(provider_rows, dict):
        errors.append("provider_binding_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_row_ready
        )
        errors.extend(f"missing provider binding {name}" for name in missing)
        errors.extend(f"incomplete provider binding {name}" for name in incomplete)
    negative_rows = matrix.get("negative_provider_binding_rows", {})
    if not isinstance(negative_rows, dict):
        errors.append("negative_provider_binding_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            negative_rows, REQUIRED_NEGATIVE_PROVIDER_FAILURES, _negative_failure_ready
        )
        errors.extend(f"missing negative provider fixture {name}" for name in missing)
        errors.extend(f"incomplete negative provider fixture {name}" for name in incomplete)
    return errors


def verify_universal_foundation_provider_binding_matrix(
    matrix_input: dict[str, Any],
    matrix: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L168 provider binding matrix against replay input."""

    errors = validate_universal_foundation_provider_binding_matrix_shape(matrix)
    expected_hash = hash_payload(_hashable_matrix(matrix))
    if matrix.get("universal_foundation_provider_binding_matrix_hash") != expected_hash:
        errors.append("universal_foundation_provider_binding_matrix_hash mismatch")
    if signing_secret and "signature" not in matrix:
        errors.append("missing signature")
    if signing_secret:
        signature = matrix.get("signature", {})
        expected_signature = sign_payload(_hashable_matrix(matrix), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")

    replayed = make_universal_foundation_provider_binding_matrix(
        matrix_input,
        issuer=matrix.get("issuer", DEFAULT_ISSUER),
        created_at=matrix.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_foundation_provider_binding_matrix_hash") != matrix.get(
        "universal_foundation_provider_binding_matrix_hash"
    ):
        errors.append("replay hash mismatch")
    if replayed.get("summary", {}).get("status") != matrix.get("summary", {}).get("status"):
        errors.append("replay status mismatch")
    if matrix.get("summary", {}).get("status") != "ready":
        errors.append("provider binding matrix is not ready")
    if matrix.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("private payloads are not excluded")
    return errors
