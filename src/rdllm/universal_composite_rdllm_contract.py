"""Universal composite RDLLM contract.

The L167 layer is the single top-level RDLLM contract surface. Earlier layers
prove installability, model-release binding, and per-response live attribution.
This layer composes them into one verifier decision that foundation-model
providers, routers, local runtimes, enterprise gateways, creator registries,
auditors, clearinghouses, regulators, SDKs, and buyers can use without
reconstructing the whole proof chain themselves.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_VERSION = (
    "rdllm-universal-composite-rdllm-contract/v1"
)
UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_SCHEMA = (
    "docs/schemas/universal_composite_rdllm_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L167"
MINIMUM_MODEL_RELEASE_LEVEL = "RDLLM-L166"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-composite-rdllm-contract.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph_post_release",
    "trust_registry",
    "universal_foundation_model_release_passport",
    "universal_live_attribution_proof",
    "universal_reference_implementation_distribution",
    "universal_industry_adoption_root",
    "universal_foundation_provider_adoption_pack",
    "universal_certification_trust_federation",
    "universal_composite_rdllm_profile",
    "universal_runtime_conformance_receipt",
    "universal_claim_provenance_envelope",
    "universal_provider_wire_protocol",
    "universal_grounded_reliance_contract",
    "universal_reliance_correction_ledger",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_CONTRACT_ROLES = (
    "foundation_model_provider",
    "model_gateway_or_router",
    "local_open_weight_runtime",
    "enterprise_proxy",
    "rag_retrieval_provider",
    "agent_tool_or_mcp_server",
    "client_renderer",
    "creator_registry_or_cmo",
    "auditor_or_certifier",
    "clearinghouse_or_payment_rail",
    "regulator_or_public_buyer",
    "downstream_developer",
)

REQUIRED_CANONICAL_API_SURFACES = (
    "model_release_passport_lookup",
    "preflight_negotiation",
    "guarded_invocation",
    "streaming_attribution",
    "response_envelope",
    "source_footer_render",
    "live_attribution_verification",
    "copied_output_status",
    "creator_query_audit",
    "settlement_metering",
    "revocation_status",
    "regulator_export",
)

REQUIRED_DECISION_GATES = (
    "no_composite_contract_no_rdllm_claim",
    "no_passport_no_model_claim",
    "no_live_proof_no_answer_release",
    "no_route_adapter_no_invocation",
    "no_footer_no_reliance",
    "no_identity_no_citation",
    "no_license_or_escrow_no_settlement",
    "no_revocation_check_no_serving",
    "no_public_graph_no_procurement",
    "no_audit_route_no_compliance",
    "no_private_payload_in_public_proof",
    "no_copied_status_no_repost_reliance",
)

REQUIRED_STANDARD_BINDINGS = (
    "openapi_contract",
    "model_context_protocol",
    "opentelemetry_genai",
    "c2pa_content_credentials",
    "scitt_transparency_statements",
    "w3c_verifiable_credentials",
    "slsa_in_toto_supply_chain",
    "openssf_model_signing",
    "eu_gpai_transparency",
    "nist_ai_rmf_genai_profile",
)

REQUIRED_NEGATIVE_COMPOSITE_FAILURES = (
    "provider_claim_without_l167_contract",
    "model_release_passport_missing",
    "post_release_graph_omits_l166",
    "unsupported_foundation_provider_route",
    "aggregator_strips_upstream_attribution",
    "local_runtime_bypasses_invocation_guard",
    "sdk_strips_footer_or_proof",
    "settlement_without_composite_contract",
    "revoked_model_or_source_still_served",
    "creator_audit_route_missing",
    "regulator_export_unverifiable",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_composite_rdllm_contract_hash",
    "universal_foundation_model_release_passport_hash",
    "universal_live_attribution_proof_hash",
    "universal_reference_implementation_distribution_hash",
    "universal_industry_adoption_root_hash",
    "universal_foundation_provider_adoption_pack_hash",
    "universal_certification_trust_federation_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_provider_wire_protocol_hash",
    "universal_grounded_reliance_contract_hash",
    "universal_reliance_correction_ledger_hash",
    "revenue_allocation_hash",
    "finance_ledger_attestation_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "graph_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "envelope_hash",
    "event_hash",
    "package_hash",
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
    "training_record",
    "raw_training_record",
    "dataset_sample",
    "reward_text",
    "preference_text",
    "distillation_output",
    "synthetic_record",
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


def load_universal_composite_rdllm_contract_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L167 composite RDLLM contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_composite_rdllm_contract_hash", "signature"}
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


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    for key in ("target_certification_level", "highest_level", "attested_highest_level"):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    certification = artifact.get("certification") if isinstance(artifact, dict) else None
    if isinstance(certification, dict):
        value = certification.get("highest_level")
        if isinstance(value, str):
            return value
    return ""


def _artifact_binding(name: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    declared = _declared_hash(artifact)
    return {
        "artifact": name,
        "present": isinstance(artifact, dict) and bool(artifact),
        "artifact_hash": declared,
        "payload_hash": hash_payload(_hashable_artifact(artifact)),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": str(_summary(artifact).get("status", "")),
        "level": _artifact_level(artifact),
    }


def _artifact_bindings(contract_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: _artifact_binding(
            name,
            contract_input.get(name)
            if isinstance(contract_input.get(name), dict)
            else None,
        )
        for name in REQUIRED_CORE_ARTIFACTS
    }


def _row_map(contract_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = contract_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


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


def _private_strings_absent(public_payload: dict[str, Any], contract_input: dict[str, Any]) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in contract_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _role_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "role_hash",
        "obligation_hash",
        "verifier_hash",
        "settlement_hold_hash",
        "public_endpoint_hash",
    )
    required_flags = (
        "role_supported",
        "obligations_bound",
        "verifier_available",
        "fail_closed",
        "settlement_hold_bound",
        "private_payloads_excluded",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _api_surface_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "endpoint_hash",
        "schema_hash",
        "verifier_hash",
        "telemetry_hash",
        "policy_hash",
    )
    required_flags = (
        "surface_available",
        "machine_readable",
        "versioned",
        "fail_closed",
        "settlement_bound",
        "private_payloads_excluded",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _decision_gate_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "policy_hash",
        "precondition_hash",
        "enforcement_hash",
        "negative_fixture_hash",
    )
    required_flags = (
        "precondition_checked",
        "enforcement_available",
        "violation_blocks_release",
        "settlement_held_on_failure",
        "public_status_available",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _standard_binding_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("mapping_hash", "schema_hash", "test_vector_hash", "export_hash")
    required_flags = (
        "mapped",
        "test_vector_available",
        "public_or_auditor_accessible",
        "contract_bound",
        "drift_review_bound",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return bool(row.get("fixture_hash")) and all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "rdllm_claim_blocked",
            "invocation_blocked",
            "response_release_blocked",
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


def _certification_l166_ready(certification_report: dict[str, Any] | None) -> bool:
    summary = _summary(certification_report)
    levels = (
        certification_report.get("levels", {})
        if isinstance(certification_report, dict)
        else {}
    )
    l166 = levels.get(MINIMUM_MODEL_RELEASE_LEVEL, {}) if isinstance(levels, dict) else {}
    return (
        summary.get("status") == "passed"
        and _level_at_least(summary.get("highest_level", ""), MINIMUM_MODEL_RELEASE_LEVEL)
        and isinstance(l166, dict)
        and l166.get("passed") is True
    )


def _model_release_passport_l166_ready(passport: dict[str, Any] | None) -> bool:
    if not isinstance(passport, dict):
        return False
    decision = passport.get("release_decision", {})
    return (
        _summary(passport).get("status") == "ready"
        and _level_at_least(
            _summary(passport).get("target_certification_level", ""),
            MINIMUM_MODEL_RELEASE_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("model_release_passport_ready") is True
        and decision.get("provider_invocation_allowed") is True
    )


def _post_release_graph_contains_l164_l166(graph: dict[str, Any] | None) -> bool:
    if not isinstance(graph, dict) or _summary(graph).get("status") != "ready":
        return False
    artifact_names = {
        str(row.get("name", ""))
        for row in graph.get("artifacts", [])
        if isinstance(row, dict)
    }
    return {
        "universal_reference_implementation_distribution",
        "universal_live_attribution_proof",
        "universal_foundation_model_release_passport",
    }.issubset(artifact_names)


def make_universal_composite_rdllm_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L167 universal composite RDLLM contract."""

    artifact_bindings = _artifact_bindings(contract_input)
    role_rows = _row_map(contract_input, "contract_role_rows")
    api_rows = _row_map(contract_input, "canonical_api_surface_rows")
    gate_rows = _row_map(contract_input, "decision_gate_rows")
    standard_rows = _row_map(contract_input, "standard_binding_rows")
    negative_rows = _row_map(contract_input, "negative_composite_rows")

    missing_roles, incomplete_roles = _complete_rows(
        role_rows, REQUIRED_CONTRACT_ROLES, _role_row_ready
    )
    missing_apis, incomplete_apis = _complete_rows(
        api_rows, REQUIRED_CANONICAL_API_SURFACES, _api_surface_ready
    )
    missing_gates, incomplete_gates = _complete_rows(
        gate_rows, REQUIRED_DECISION_GATES, _decision_gate_ready
    )
    missing_standards, incomplete_standards = _complete_rows(
        standard_rows, REQUIRED_STANDARD_BINDINGS, _standard_binding_ready
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows, REQUIRED_NEGATIVE_COMPOSITE_FAILURES, _negative_failure_ready
    )

    checks = {
        "core_artifacts_bound": all(
            binding["present"] and binding["hash_reproducible"]
            for binding in artifact_bindings.values()
        ),
        "certification_l166_or_higher_passed": _certification_l166_ready(
            contract_input.get("certification_report")
        ),
        "model_release_passport_l166_ready": _model_release_passport_l166_ready(
            contract_input.get("universal_foundation_model_release_passport")
        ),
        "post_release_graph_contains_l164_l166": _post_release_graph_contains_l164_l166(
            contract_input.get("proof_dependency_graph_post_release")
        ),
        "contract_roles_complete": not missing_roles and not incomplete_roles,
        "canonical_api_surfaces_complete": not missing_apis and not incomplete_apis,
        "decision_gates_complete": not missing_gates and not incomplete_gates,
        "standard_bindings_complete": not missing_standards and not incomplete_standards,
        "settlement_and_revocation_publicly_bound": (
            "no_license_or_escrow_no_settlement" in gate_rows
            and "no_revocation_check_no_serving" in gate_rows
            and _decision_gate_ready(gate_rows.get("no_license_or_escrow_no_settlement", {}))
            and _decision_gate_ready(gate_rows.get("no_revocation_check_no_serving", {}))
            and artifact_bindings["revenue_allocation_report"]["present"]
            and artifact_bindings["finance_ledger_attestation"]["present"]
            and artifact_bindings["universal_reliance_correction_ledger"]["present"]
        ),
        "negative_composite_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "composite_contract_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    contract_without_privacy: dict[str, Any] = {
        "universal_composite_rdllm_contract_version": (
            UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-composite-rdllm-contract-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_release_level": MINIMUM_MODEL_RELEASE_LEVEL,
            "single_composite_contract_required": True,
            "model_claim_requires_contract": True,
            "provider_invocation_requires_contract": True,
            "answer_release_requires_live_attribution": True,
            "creator_settlement_requires_contract": True,
            "procurement_reliance_requires_post_release_graph": True,
            "private_payloads_forbidden_in_public_contract": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "contract_role_rows": {
            role: role_rows.get(role, {}) for role in REQUIRED_CONTRACT_ROLES
        },
        "canonical_api_surface_rows": {
            surface: api_rows.get(surface, {})
            for surface in REQUIRED_CANONICAL_API_SURFACES
        },
        "decision_gate_rows": {
            gate: gate_rows.get(gate, {}) for gate in REQUIRED_DECISION_GATES
        },
        "standard_binding_rows": {
            standard: standard_rows.get(standard, {})
            for standard in REQUIRED_STANDARD_BINDINGS
        },
        "negative_composite_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_COMPOSITE_FAILURES
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root(
                [
                    hash_payload({"name": name, "binding": binding})
                    for name, binding in artifact_bindings.items()
                ]
            ),
            "contract_role_root": merkle_root(
                [
                    hash_payload({"role": role, "row": role_rows.get(role, {})})
                    for role in REQUIRED_CONTRACT_ROLES
                ]
            ),
            "canonical_api_surface_root": merkle_root(
                [
                    hash_payload({"surface": surface, "row": api_rows.get(surface, {})})
                    for surface in REQUIRED_CANONICAL_API_SURFACES
                ]
            ),
            "decision_gate_root": merkle_root(
                [
                    hash_payload({"gate": gate, "row": gate_rows.get(gate, {})})
                    for gate in REQUIRED_DECISION_GATES
                ]
            ),
            "standard_binding_root": merkle_root(
                [
                    hash_payload(
                        {"standard": standard, "row": standard_rows.get(standard, {})}
                    )
                    for standard in REQUIRED_STANDARD_BINDINGS
                ]
            ),
            "negative_composite_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_COMPOSITE_FAILURES
                ]
            ),
        },
        "checks": checks,
        "contract_decision": {
            "composite_rdllm_contract_ready": not failure_modes,
            "universal_rdllm_claim_allowed": not failure_modes,
            "foundation_model_invocation_allowed": not failure_modes,
            "response_release_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_release_allowed": not failure_modes,
            "procurement_reliance_allowed": not failure_modes,
            "failure_modes": failure_modes,
            "missing_roles": missing_roles,
            "incomplete_roles": incomplete_roles,
            "missing_api_surfaces": missing_apis,
            "incomplete_api_surfaces": incomplete_apis,
            "missing_decision_gates": missing_gates,
            "incomplete_decision_gates": incomplete_gates,
            "missing_standard_bindings": missing_standards,
            "incomplete_standard_bindings": incomplete_standards,
            "missing_negative_composite_failures": missing_negative,
            "incomplete_negative_composite_failures": incomplete_negative,
        },
        "standards_and_research": {
            "eu_gpai_code_of_practice": "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai",
            "nist_ai_rmf": "https://www.nist.gov/itl/ai-risk-management-framework",
            "openssf_model_signing": "https://openssf.org/blog/2025/06/05/model-signing-is-here/",
            "openapi": "https://spec.openapis.org/oas/latest.html",
            "model_context_protocol": "https://modelcontextprotocol.io/",
            "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "c2pa": "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html",
            "scitt": "https://scitt.io/",
            "slsa": "https://slsa.dev/spec/latest/",
            "in_toto": "https://in-toto.io/",
        },
    }

    private_field_paths = _contains_private_fields(contract_without_privacy)
    private_strings_absent = _private_strings_absent(
        contract_without_privacy, contract_input
    )
    contract = {
        **contract_without_privacy,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_answer_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_training_text_disclosed": False,
            "raw_customer_record_disclosed": False,
            "private_field_paths": private_field_paths,
            "private_fields_absent": not private_field_paths,
            "private_strings_absent": private_strings_absent,
            "public_rows_are_hash_status_policy_and_endpoint_only": True,
        },
    }
    if private_field_paths or not private_strings_absent:
        contract["checks"]["private_fields_absent"] = not private_field_paths
        contract["checks"]["private_strings_absent"] = private_strings_absent
        for name in ("private_fields_absent", "private_strings_absent"):
            if not contract["checks"][name] and name not in failure_modes:
                failure_modes.append(name)

    contract["summary"] = {
        "status": "ready" if not failure_modes else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_model_release_level": MINIMUM_MODEL_RELEASE_LEVEL,
        "core_artifact_count": len(REQUIRED_CORE_ARTIFACTS),
        "contract_role_count": len(REQUIRED_CONTRACT_ROLES),
        "canonical_api_surface_count": len(REQUIRED_CANONICAL_API_SURFACES),
        "decision_gate_count": len(REQUIRED_DECISION_GATES),
        "standard_binding_count": len(REQUIRED_STANDARD_BINDINGS),
        "negative_composite_failure_count": len(REQUIRED_NEGATIVE_COMPOSITE_FAILURES),
        "failure_mode_count": len(failure_modes),
        "signed_composite_contract": bool(signing_secret),
        "privacy_preserved": not private_field_paths and private_strings_absent,
    }
    contract["universal_composite_rdllm_contract_hash"] = hash_payload(
        _hashable_contract(contract)
    )
    if signing_secret:
        contract["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_contract(contract), signing_secret),
        }
    return contract


def validate_universal_composite_rdllm_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L167 composite RDLLM contract."""

    errors: list[str] = []
    required = (
        "universal_composite_rdllm_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "contract_role_rows",
        "canonical_api_surface_rows",
        "decision_gate_rows",
        "standard_binding_rows",
        "negative_composite_rows",
        "evidence_roots",
        "checks",
        "contract_decision",
        "privacy",
        "summary",
        "universal_composite_rdllm_contract_hash",
    )
    for field in required:
        if field not in contract:
            errors.append(f"missing field: {field}")
    if contract.get("universal_composite_rdllm_contract_version") != (
        UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_composite_rdllm_contract_version")
    if contract.get("schema") != UNIVERSAL_COMPOSITE_RDLLM_CONTRACT_SCHEMA:
        errors.append("unexpected schema")
    if contract.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("unexpected well_known path")
    if contract.get("policy", {}).get("target_certification_level") != (
        TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("unexpected target certification level")
    if contract.get("summary", {}).get("target_certification_level") != (
        TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("summary target certification level mismatch")
    for collection in (
        "artifact_bindings",
        "contract_role_rows",
        "canonical_api_surface_rows",
        "decision_gate_rows",
        "standard_binding_rows",
        "negative_composite_rows",
    ):
        if collection in contract and not isinstance(contract.get(collection), dict):
            errors.append(f"{collection} must be an object")
    return errors


def verify_universal_composite_rdllm_contract(
    contract: dict[str, Any],
    *,
    contract_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L167 composite RDLLM contract against private replay inputs."""

    errors = validate_universal_composite_rdllm_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_composite_rdllm_contract_hash") != expected_hash:
        errors.append("universal_composite_rdllm_contract_hash mismatch")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(f"private field leaked: {private_fields[0]}")
    if not _private_strings_absent(contract, contract_input):
        errors.append("private replay string leaked")

    replayed = make_universal_composite_rdllm_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_composite_rdllm_contract_hash") != contract.get(
        "universal_composite_rdllm_contract_hash"
    ):
        errors.append("replayed composite contract hash mismatch")
    for field in ("checks", "summary", "contract_decision", "evidence_roots"):
        if replayed.get(field) != contract.get(field):
            errors.append(f"replayed {field} mismatch")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("composite RDLLM contract is not ready")
    if contract.get("contract_decision", {}).get("composite_rdllm_contract_ready") is not True:
        errors.append("composite RDLLM contract decision not ready")
    if contract.get("checks", {}).get("composite_contract_signed") is not True:
        errors.append("composite RDLLM contract is unsigned")
    return errors
