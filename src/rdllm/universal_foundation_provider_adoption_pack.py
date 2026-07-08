"""Universal foundation provider adoption pack.

The L162 layer turns the L161 certified proof chain into one implementation
package a foundation-model provider, SDK, gateway, client, auditor, or regulator
can adopt without relying on provider-local conventions. It binds provider-family
coverage, standard exports, runtime gates, and negative fixtures to the same
source-footer, invocation, certification, and settlement chain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_VERSION = (
    "rdllm-universal-foundation-provider-adoption-pack/v1"
)
UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_SCHEMA = (
    "docs/schemas/universal_foundation_provider_adoption_pack.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L162"
MINIMUM_CERTIFICATION_TRUST_LEVEL = "RDLLM-L161"
MINIMUM_INVOCATION_ENFORCEMENT_LEVEL = "RDLLM-L160"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-foundation-provider-adoption-pack.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "trust_registry",
    "universal_certification_trust_federation",
    "universal_negotiated_invocation_enforcement",
    "universal_attribution_negotiation_handshake",
    "universal_provider_drift_sentinel",
    "universal_provider_adapter_harness",
    "universal_foundation_adoption_kernel",
    "universal_composite_rdllm_profile",
    "universal_rdllm_root",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "universal_content_credential",
    "response_envelope",
    "source_footer_delivery",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai_responses_api",
    "anthropic_messages_api",
    "google_gemini_vertex",
    "azure_openai",
    "aws_bedrock_converse",
    "meta_llama_open_weights",
    "mistral_api",
    "cohere_command",
    "xai_grok",
    "deepseek_api",
    "openrouter_compatible",
    "local_open_weight_runtime",
    "enterprise_gateway_proxy",
)

REQUIRED_STANDARD_EXPORTS = (
    "json_schema_bundle",
    "openapi_discovery",
    "sdk_middleware_contract",
    "otel_genai_mapping",
    "mcp_tool_resource_contract",
    "c2pa_content_credential_assertion",
    "w3c_vc_data_integrity_credential",
    "scitt_transparency_statement",
    "openid_federation_entity_statement",
    "payment_settlement_rail_profile",
    "creator_challenge_dispute_api",
    "provider_procurement_checklist",
)

REQUIRED_ADOPTION_GATES = (
    "pre_generation_negotiation_gate",
    "provider_adapter_gate",
    "drift_revocation_gate",
    "invocation_receipt_gate",
    "source_footer_render_gate",
    "claim_evidence_materialization_gate",
    "copied_output_status_gate",
    "telemetry_trace_export_gate",
    "certification_trust_gate",
    "settlement_release_gate",
    "creator_audit_query_gate",
    "regulator_export_gate",
)

REQUIRED_NEGATIVE_ADOPTION_FAILURES = (
    "unsupported_provider_family",
    "missing_adapter_fixture",
    "stale_provider_sdk",
    "unnegotiated_direct_call",
    "stream_without_footer_lock",
    "mcp_tool_without_source_locator",
    "retrieval_without_evidence_regions",
    "copied_output_without_status",
    "missing_otel_trace",
    "invalid_certification_trust_chain",
    "settlement_without_invocation_receipt",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_foundation_provider_adoption_pack_hash",
    "universal_certification_trust_federation_hash",
    "universal_negotiated_invocation_enforcement_hash",
    "universal_attribution_negotiation_handshake_hash",
    "universal_provider_drift_sentinel_hash",
    "universal_provider_adapter_harness_hash",
    "universal_foundation_adoption_kernel_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_rdllm_root_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_content_credential_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "graph_hash",
    "summary_hash",
    "envelope_hash",
    "receipt_hash",
    "event_hash",
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
    "tool_payload",
    "raw_tool_output",
    "memory_value",
    "raw_memory",
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


def load_universal_foundation_provider_adoption_pack_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L162 adoption pack."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_pack(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in pack.items()
        if key not in {"universal_foundation_provider_adoption_pack_hash", "signature"}
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


def _private_strings_absent(
    public_payload: dict[str, Any], pack_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in pack_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _level_number(level: str) -> int:
    try:
        return int(str(level).rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _provider_declares_pack(provider_card: dict[str, Any]) -> bool:
    return bool(
        provider_card.get("supported_evidence_channels", {}).get(
            "universal_foundation_provider_adoption_pack"
        )
        and provider_card.get("public_disclosure_surfaces", {}).get(
            "universal_foundation_provider_adoption_pack"
        )
    )


def _integration_declares_pack(integration_profile: dict[str, Any]) -> bool:
    return bool(
        integration_profile.get("public_surfaces", {}).get(
            "universal_foundation_provider_adoption_pack"
        )
        and integration_profile.get("schemas", {}).get(
            "universal_foundation_provider_adoption_pack"
        )
        == UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_SCHEMA
    )


def _discovery_declares_pack(discovery_manifest: dict[str, Any]) -> bool:
    return bool(
        discovery_manifest.get("discovery", {}).get(
            "universal_foundation_provider_adoption_pack_path"
        )
        == DEFAULT_WELL_KNOWN_PATH
        and discovery_manifest.get("schemas", {}).get(
            "universal_foundation_provider_adoption_pack"
        )
        == UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_SCHEMA
    )


def _is_ready_artifact(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    status = _artifact_status(artifact)
    if status:
        return status in {"ready", "passed", "attested", "ok"}
    summary = _summary(artifact)
    if summary:
        return not bool(summary.get("failed_check_count", 0))
    return _artifact_hash_is_reproducible(artifact)


def _row_map(pack_input: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    rows = pack_input.get(name, {})
    return rows if isinstance(rows, dict) else {}


def _row_has_hashes(row: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(bool(str(row.get(field, "")).strip()) for field in fields)


def _provider_family_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(
        row,
        (
            "native_route_hash",
            "adapter_profile_hash",
            "negotiation_profile_hash",
            "invocation_enforcement_hash",
            "certification_federation_hash",
            "source_footer_profile_hash",
            "settlement_meter_hash",
            "telemetry_mapping_hash",
            "status_endpoint_hash",
            "public_docs_hash",
        ),
    ) and all(
        bool(row.get(field))
        for field in (
            "adapter_verified",
            "drift_sentinel_green",
            "negotiation_required",
            "invocation_enforced",
            "certification_federated",
            "source_footer_required",
            "settlement_metered",
            "telemetry_exportable",
            "revocation_checked",
            "public_discovery_available",
        )
    )


def _standard_export_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(
        row,
        (
            "export_hash",
            "schema_hash",
            "publication_path_hash",
            "compatibility_hash",
            "version_hash",
        ),
    ) and all(
        bool(row.get(field))
        for field in (
            "implemented",
            "published",
            "verifier_available",
            "privacy_preserving",
        )
    )


def _adoption_gate_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(
        row,
        (
            "gate_hash",
            "input_contract_hash",
            "output_contract_hash",
            "failure_policy_hash",
            "owner_role_hash",
        ),
    ) and all(
        bool(row.get(field))
        for field in (
            "blocks_on_failure",
            "settlement_hold_on_failure",
            "audit_visible",
            "public_status_safe",
        )
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(row, ("fixture_hash",)) and all(
        bool(row.get(field))
        for field in (
            "expected_reject",
            "observed_reject",
            "display_blocked",
            "settlement_held",
            "provider_route_revoked",
        )
    )


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name
        for name in required
        if name in rows and not predicate(rows.get(name, {}))
    ]
    return missing, incomplete


def _artifact_bindings(pack_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CORE_ARTIFACTS:
        artifact = pack_input.get(name)
        artifact_dict = artifact if isinstance(artifact, dict) else None
        bindings[name] = {
            "artifact_hash": _declared_hash(artifact_dict),
            "payload_hash": hash_payload(_hashable_artifact(artifact_dict)),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact_dict),
            "status": _artifact_status(artifact_dict),
            "level": _artifact_level(artifact_dict),
            "present": bool(artifact_dict),
        }
    return bindings


def make_universal_foundation_provider_adoption_pack(
    pack_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L162 provider-neutral adoption pack."""

    certification_report = pack_input.get("certification_report")
    certification_attestation = pack_input.get("certification_attestation")
    provider_card = pack_input.get("provider_attribution_card")
    integration_profile = pack_input.get("integration_profile")
    discovery_manifest = pack_input.get("discovery_manifest")
    l161 = pack_input.get("universal_certification_trust_federation")
    proof_graph = pack_input.get("proof_dependency_graph")

    artifact_bindings = _artifact_bindings(pack_input)
    provider_family_rows = _row_map(pack_input, "provider_family_rows")
    standard_export_rows = _row_map(pack_input, "standard_export_rows")
    adoption_gate_rows = _row_map(pack_input, "adoption_gate_rows")
    negative_adoption_rows = _row_map(pack_input, "negative_adoption_rows")

    missing_families, incomplete_families = _complete_rows(
        provider_family_rows, REQUIRED_PROVIDER_FAMILIES, _provider_family_ready
    )
    missing_exports, incomplete_exports = _complete_rows(
        standard_export_rows, REQUIRED_STANDARD_EXPORTS, _standard_export_ready
    )
    missing_gates, incomplete_gates = _complete_rows(
        adoption_gate_rows, REQUIRED_ADOPTION_GATES, _adoption_gate_ready
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_adoption_rows,
        REQUIRED_NEGATIVE_ADOPTION_FAILURES,
        _negative_failure_ready,
    )

    ready_core = [
        name
        for name, binding in artifact_bindings.items()
        if binding["present"] and binding["hash_reproducible"]
    ]
    core_artifacts_bound = len(ready_core) == len(REQUIRED_CORE_ARTIFACTS)
    core_artifacts_ready = all(
        _is_ready_artifact(pack_input.get(name))
        for name in REQUIRED_CORE_ARTIFACTS
        if name
        not in {
            "revenue_allocation_report",
            "finance_ledger_attestation",
            "response_envelope",
            "source_footer_delivery",
        }
    )
    certification_level_sufficient = _level_number(
        str(_summary(certification_report).get("highest_level", ""))
    ) >= _level_number(MINIMUM_CERTIFICATION_TRUST_LEVEL)
    attestation_level_sufficient = _level_number(
        str(_summary(certification_attestation).get("attested_highest_level", ""))
    ) >= _level_number(MINIMUM_CERTIFICATION_TRUST_LEVEL)
    l161_ready = bool(
        isinstance(l161, dict)
        and _summary(l161).get("status") == "ready"
        and _summary(l161).get("target_certification_level")
        == MINIMUM_CERTIFICATION_TRUST_LEVEL
    )
    proof_graph_l161_bound = bool(
        isinstance(proof_graph, dict)
        and _summary(proof_graph).get("status") == "ready"
        and _level_number(str(_summary(proof_graph).get("target_certification_level", "")))
        >= _level_number(MINIMUM_CERTIFICATION_TRUST_LEVEL)
    )
    provider_pack_declared = isinstance(provider_card, dict) and _provider_declares_pack(
        provider_card
    )
    integration_pack_declared = isinstance(
        integration_profile, dict
    ) and _integration_declares_pack(integration_profile)
    discovery_pack_declared = isinstance(
        discovery_manifest, dict
    ) and _discovery_declares_pack(discovery_manifest)

    checks = {
        "core_artifacts_bound": core_artifacts_bound,
        "core_artifacts_ready": core_artifacts_ready,
        "certification_level_sufficient": certification_level_sufficient,
        "attestation_level_sufficient": attestation_level_sufficient,
        "l161_trust_federation_ready": l161_ready,
        "proof_graph_binds_l161_or_higher": proof_graph_l161_bound,
        "provider_card_declares_adoption_pack": provider_pack_declared,
        "integration_profile_declares_adoption_pack": integration_pack_declared,
        "discovery_manifest_declares_adoption_pack": discovery_pack_declared,
        "all_provider_families_adoptable": not missing_families
        and not incomplete_families,
        "all_standard_exports_published": not missing_exports and not incomplete_exports,
        "all_adoption_gates_fail_closed": not missing_gates and not incomplete_gates,
        "negative_adoption_fixtures_reject": not missing_negative
        and not incomplete_negative,
    }

    failure_modes = [name for name, passed in checks.items() if not passed]
    provider_family_root = merkle_root([
        hash_payload({"name": name, "row": provider_family_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_FAMILIES
    ])
    standard_export_root = merkle_root([
        hash_payload({"name": name, "row": standard_export_rows.get(name, {})})
        for name in REQUIRED_STANDARD_EXPORTS
    ])
    adoption_gate_root = merkle_root([
        hash_payload({"name": name, "row": adoption_gate_rows.get(name, {})})
        for name in REQUIRED_ADOPTION_GATES
    ])
    negative_adoption_root = merkle_root([
        hash_payload({"name": name, "row": negative_adoption_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_ADOPTION_FAILURES
    ])

    pack: dict[str, Any] = {
        "universal_foundation_provider_adoption_pack_version": (
            UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_VERSION
        ),
        "schema": UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-foundation-provider-adoption-pack-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_certification_trust_level": MINIMUM_CERTIFICATION_TRUST_LEVEL,
            "minimum_invocation_enforcement_level": MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
            "provider_neutral_adoption_required": True,
            "self_certification_sufficient": False,
            "source_footer_required": True,
            "creator_settlement_required": True,
            "telemetry_export_required": True,
            "negative_fixture_fail_closed_required": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": {
            name: provider_family_rows.get(name, {})
            for name in REQUIRED_PROVIDER_FAMILIES
        },
        "standard_export_rows": {
            name: standard_export_rows.get(name, {})
            for name in REQUIRED_STANDARD_EXPORTS
        },
        "adoption_gate_rows": {
            name: adoption_gate_rows.get(name, {})
            for name in REQUIRED_ADOPTION_GATES
        },
        "negative_adoption_rows": {
            name: negative_adoption_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_ADOPTION_FAILURES
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root([
                hash_payload({"name": name, "binding": binding})
                for name, binding in artifact_bindings.items()
            ]),
            "provider_family_root": provider_family_root,
            "standard_export_root": standard_export_root,
            "adoption_gate_root": adoption_gate_root,
            "negative_adoption_root": negative_adoption_root,
        },
        "adoption_decision": {
            "provider_neutral_adoption_ready": not failure_modes,
            "foundation_provider_self_assertion_sufficient": False,
            "failure_modes": failure_modes,
            "missing_provider_families": missing_families,
            "incomplete_provider_families": incomplete_families,
            "missing_standard_exports": missing_exports,
            "incomplete_standard_exports": incomplete_exports,
            "missing_adoption_gates": missing_gates,
            "incomplete_adoption_gates": incomplete_gates,
            "missing_negative_adoption_failures": missing_negative,
            "incomplete_negative_adoption_failures": incomplete_negative,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payloads_disclosed": False,
            "tool_payloads_disclosed": False,
            "payment_account_details_disclosed": False,
            "public_pack_uses_hashes_and_status_rows": True,
        },
        "checks": checks,
    }
    public_probe = dict(pack)
    private_field_findings = _contains_private_fields(public_probe)
    checks["private_fields_absent"] = not private_field_findings
    checks["private_strings_absent"] = _private_strings_absent(public_probe, pack_input)
    if not checks["private_fields_absent"] or not checks["private_strings_absent"]:
        failure_modes = [name for name, passed in checks.items() if not passed]
        pack["adoption_decision"]["failure_modes"] = failure_modes
        pack["adoption_decision"]["provider_neutral_adoption_ready"] = False

    pack["summary"] = {
        "status": "ready"
        if pack["adoption_decision"]["provider_neutral_adoption_ready"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_certification_trust_level": MINIMUM_CERTIFICATION_TRUST_LEVEL,
        "minimum_invocation_enforcement_level": MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
        "core_artifact_count": len(REQUIRED_CORE_ARTIFACTS),
        "bound_core_artifact_count": len(ready_core),
        "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
        "ready_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES)
        - len(missing_families)
        - len(incomplete_families),
        "standard_export_count": len(REQUIRED_STANDARD_EXPORTS),
        "ready_standard_export_count": len(REQUIRED_STANDARD_EXPORTS)
        - len(missing_exports)
        - len(incomplete_exports),
        "adoption_gate_count": len(REQUIRED_ADOPTION_GATES),
        "ready_adoption_gate_count": len(REQUIRED_ADOPTION_GATES)
        - len(missing_gates)
        - len(incomplete_gates),
        "negative_adoption_failure_count": len(REQUIRED_NEGATIVE_ADOPTION_FAILURES),
        "ready_negative_adoption_failure_count": len(
            REQUIRED_NEGATIVE_ADOPTION_FAILURES
        )
        - len(missing_negative)
        - len(incomplete_negative),
        "failure_mode_count": len(pack["adoption_decision"]["failure_modes"]),
        "offline_verification_supported": True,
        "privacy_preserved": checks["private_fields_absent"]
        and checks["private_strings_absent"],
        "provider_neutral_adoption_supported": True,
        "standard_export_required": True,
        "telemetry_export_required": True,
        "source_footer_reliance_required": True,
        "creator_settlement_release_guarded": True,
    }
    pack["universal_foundation_provider_adoption_pack_hash"] = hash_payload(
        _hashable_pack(pack)
    )
    pack["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(
                pack["universal_foundation_provider_adoption_pack_hash"],
                signing_secret,
            )
            if signing_secret
            else ""
        ),
    }
    return pack


def validate_universal_foundation_provider_adoption_pack_shape(
    pack: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L162 adoption pack."""

    errors: list[str] = []
    if (
        pack.get("universal_foundation_provider_adoption_pack_version")
        != UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_VERSION
    ):
        errors.append("universal foundation provider adoption pack version is unsupported")
    if pack.get("schema") != UNIVERSAL_FOUNDATION_PROVIDER_ADOPTION_PACK_SCHEMA:
        errors.append("universal foundation provider adoption pack schema is unsupported")
    if pack.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal foundation provider adoption pack target level is not RDLLM-L162")
    if pack.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal foundation provider adoption pack well-known path is invalid")
    for section in (
        "artifact_bindings",
        "provider_family_rows",
        "standard_export_rows",
        "adoption_gate_rows",
        "negative_adoption_rows",
        "adoption_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if not isinstance(pack.get(section), dict):
            errors.append(f"universal foundation provider adoption pack missing {section}")
    for family in REQUIRED_PROVIDER_FAMILIES:
        if family not in pack.get("provider_family_rows", {}):
            errors.append(f"universal foundation provider adoption pack missing provider family {family}")
    for export in REQUIRED_STANDARD_EXPORTS:
        if export not in pack.get("standard_export_rows", {}):
            errors.append(f"universal foundation provider adoption pack missing standard export {export}")
    for gate in REQUIRED_ADOPTION_GATES:
        if gate not in pack.get("adoption_gate_rows", {}):
            errors.append(f"universal foundation provider adoption pack missing adoption gate {gate}")
    for failure in REQUIRED_NEGATIVE_ADOPTION_FAILURES:
        if failure not in pack.get("negative_adoption_rows", {}):
            errors.append(
                f"universal foundation provider adoption pack missing negative failure {failure}"
            )
    if pack.get("adoption_decision", {}).get("foundation_provider_self_assertion_sufficient"):
        errors.append("universal foundation provider adoption pack permits self assertion")
    if _contains_private_fields(pack):
        errors.append("universal foundation provider adoption pack exposes a private field")
    return errors


def verify_universal_foundation_provider_adoption_pack(
    pack: dict[str, Any],
    *,
    pack_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify an L162 adoption pack."""

    errors = validate_universal_foundation_provider_adoption_pack_shape(pack)
    expected_hash = hash_payload(_hashable_pack(pack))
    if expected_hash != pack.get("universal_foundation_provider_adoption_pack_hash"):
        errors.append("universal foundation provider adoption pack hash is not reproducible")

    expected = make_universal_foundation_provider_adoption_pack(
        pack_input,
        issuer=str(pack.get("issuer", DEFAULT_ISSUER)),
        created_at=str(pack.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "artifact_bindings",
        "provider_family_rows",
        "standard_export_rows",
        "adoption_gate_rows",
        "negative_adoption_rows",
        "evidence_roots",
        "adoption_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if pack.get(key) != expected.get(key):
            errors.append(f"universal foundation provider adoption pack {key} does not match replay input")
    if pack.get("universal_foundation_provider_adoption_pack_hash") != expected.get(
        "universal_foundation_provider_adoption_pack_hash"
    ):
        errors.append("universal foundation provider adoption pack hash does not match replay input")
    if pack.get("signature") != expected.get("signature"):
        errors.append("universal foundation provider adoption pack signature is invalid")
    if pack.get("summary", {}).get("status") != "ready":
        errors.append("universal foundation provider adoption pack status is not ready")
    for check, passed in pack.get("checks", {}).items():
        if not passed:
            errors.append(f"universal foundation provider adoption pack check failed: {check}")
    if _contains_private_fields(pack):
        errors.append("universal foundation provider adoption pack exposes a private field")
    if not _private_strings_absent(pack, pack_input):
        errors.append("universal foundation provider adoption pack exposes private input text")
    return errors
