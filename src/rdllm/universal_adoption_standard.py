"""Universal RDLLM adoption standard package.

The L138 layer turns a ready L137 deployment passport into an implementer-facing
standard package. It is the artifact a foundation-model provider, gateway,
enterprise buyer, SDK maintainer, auditor, or clearinghouse can use to decide
whether an RDLLM claim is complete enough to adopt without private negotiation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.composite_foundation_adapter import DEFAULT_PROVIDER_FAMILIES
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_ADOPTION_STANDARD_VERSION = "rdllm-universal-adoption-standard/v1"
UNIVERSAL_ADOPTION_STANDARD_SCHEMA = (
    "docs/schemas/universal_adoption_standard.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L138"
MINIMUM_INPUT_LEVEL = "RDLLM-L137"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-adoption-standard.json"

REQUIRED_CORE_ARTIFACTS = (
    "universal_rdllm_passport",
    "conformance_vector_pack",
    "integration_profile",
    "discovery_manifest",
    "provider_attribution_card",
    "certification_report",
    "attribution_exchange",
    "federation_handshake",
    "trust_registry",
)

REQUIRED_IMPLEMENTER_ROLES = (
    "foundation_model_provider",
    "model_gateway_or_broker",
    "enterprise_customer_client",
    "response_renderer",
    "creator_registry_or_cmo",
    "independent_auditor_or_watchtower",
    "clearinghouse_or_payment_rail",
)

REQUIRED_SDK_SURFACES = (
    "well_known_discovery",
    "universal_passport",
    "universal_adoption_standard",
    "response_envelope",
    "source_footer_renderer",
    "content_credential_export",
    "invocation_guard_middleware",
    "provider_meter_reconciliation",
    "conformance_vector_runner",
    "offline_verifier_bundle",
)

REQUIRED_PROCUREMENT_GATES = (
    "no_l137_passport_no_rdllm_claim",
    "all_provider_families_covered",
    "all_native_calls_guarded_and_witnessed",
    "visible_source_footer_required",
    "content_credential_required_for_export",
    "conformance_vectors_must_pass",
    "public_discovery_and_verifiers_required",
    "creator_challenge_and_clearing_required",
    "private_text_must_not_enter_public_proofs",
)

REQUIRED_STANDARD_REFERENCES = (
    "c2pa_content_credentials",
    "w3c_vc_data_integrity",
    "opentelemetry_genai",
    "model_context_protocol",
    "scitt_transparency",
    "iso_20022_remittance",
    "odrl_croissant_spdx_rights",
)

REQUIRED_PUBLIC_SURFACES = (
    "universal_adoption_standard",
    "universal_rdllm_passport",
    "conformance_vector_pack",
    "integration_profile",
    "discovery_manifest",
    "provider_attribution_card",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-rdllm-passport",
    "verify-conformance-vector-pack",
    "verify-integration-profile",
    "verify-discovery-manifest",
    "verify-attribution-exchange",
    "verify-federation-handshake",
    "verify-trust-registry",
    "verify-universal-adoption-standard",
)

DECLARED_HASH_FIELDS = (
    "universal_adoption_standard_hash",
    "universal_rdllm_passport_hash",
    "vector_pack_hash",
    "exchange_hash",
    "handshake_hash",
    "trust_registry_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "envelope_hash",
    "statement_hash",
    "receipt_hash",
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
    "raw_answer_text",
    "rendered_output",
    "copied_output",
    "source_text",
    "training_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
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
    "license_server_secret",
    "raw_license_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_adoption_standard_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L138 universal adoption standard."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_adoption_standard_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], standard_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in standard_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_version(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for key, value in artifact.items():
        if key.endswith("_version") and isinstance(value, str):
            return value
    return ""


def _policy(standard_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(standard_input.get("standard_policy", {}))
    return {
        "profile": "rdllm-universal-adoption-standard-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", DEFAULT_PROVIDER_FAMILIES)
        ),
        "required_implementer_roles": list(
            policy.get("required_implementer_roles", REQUIRED_IMPLEMENTER_ROLES)
        ),
        "required_sdk_surfaces": list(
            policy.get("required_sdk_surfaces", REQUIRED_SDK_SURFACES)
        ),
        "required_procurement_gates": list(
            policy.get("required_procurement_gates", REQUIRED_PROCUREMENT_GATES)
        ),
        "required_standard_references": list(
            policy.get("required_standard_references", REQUIRED_STANDARD_REFERENCES)
        ),
        "required_public_surfaces": list(
            policy.get("required_public_surfaces", REQUIRED_PUBLIC_SURFACES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_l137_passport": "reject_rdllm_compatibility_claim",
        "on_missing_provider_family": "reject_universal_provider_claim",
        "on_missing_sdk_surface": "block_standard_publication",
        "on_failed_procurement_gate": "block_procurement_approval",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(standard_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = standard_input.get(name)
        if not isinstance(artifact, dict):
            artifact = None
        row = {
            "name": name,
            "version": _artifact_version(artifact),
            "declared_hash": _declared_hash(artifact),
            "payload_hash": hash_payload(artifact) if artifact else "",
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "status": _artifact_status(artifact),
            "target_level": _artifact_target_level(artifact),
            "present": bool(artifact),
        }
        row["artifact_binding_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": merkle_root(
            [row["artifact_binding_hash"] for row in rows]
        ),
        "bindings": rows,
    }


def _provider_family_rows(
    standard_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    passport = standard_input.get("universal_rdllm_passport", {})
    rows_by_family = {
        str(row.get("provider_family", "")): row
        for row in passport.get("provider_family_rows", [])
        if isinstance(row, dict)
    }
    rows = []
    for family in sorted(required_families):
        passport_row = rows_by_family.get(family, {})
        row = {
            "provider_family": family,
            "provider_id": str(passport_row.get("provider_id", "")),
            "native_api_version": str(passport_row.get("native_api_version", "")),
            "covered_by_adapter": passport_row.get("covered_by_adapter") is True,
            "covered_by_conformance": passport_row.get("covered_by_conformance") is True,
            "covered_by_contract": passport_row.get("covered_by_contract") is True,
            "fail_closed_backed": passport_row.get("fail_closed_backed") is True,
            "official_documentation_refs": list(
                passport_row.get("official_documentation_refs", [])
            ),
            "passport_provider_family_row_hash": str(
                passport_row.get("passport_provider_family_row_hash", "")
            ),
        }
        row["standard_provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _role_requirements(role: str) -> tuple[list[str], list[str]]:
    mapping = {
        "foundation_model_provider": (
            [
                "universal_passport",
                "invocation_guard_middleware",
                "provider_meter_reconciliation",
                "content_credential_export",
            ],
            [
                "verify-universal-rdllm-passport",
                "verify-universal-adoption-standard",
            ],
        ),
        "model_gateway_or_broker": (
            [
                "well_known_discovery",
                "invocation_guard_middleware",
                "provider_meter_reconciliation",
                "offline_verifier_bundle",
            ],
            [
                "verify-federation-handshake",
                "verify-universal-rdllm-passport",
            ],
        ),
        "enterprise_customer_client": (
            ["well_known_discovery", "response_envelope", "offline_verifier_bundle"],
            ["verify-discovery-manifest", "verify-universal-adoption-standard"],
        ),
        "response_renderer": (
            ["source_footer_renderer", "content_credential_export"],
            ["verify-universal-rdllm-passport"],
        ),
        "creator_registry_or_cmo": (
            ["well_known_discovery", "offline_verifier_bundle"],
            ["verify-attribution-exchange", "verify-trust-registry"],
        ),
        "independent_auditor_or_watchtower": (
            ["conformance_vector_runner", "offline_verifier_bundle"],
            ["verify-conformance-vector-pack", "verify-universal-adoption-standard"],
        ),
        "clearinghouse_or_payment_rail": (
            ["well_known_discovery", "offline_verifier_bundle"],
            ["verify-attribution-exchange", "verify-universal-rdllm-passport"],
        ),
    }
    return mapping.get(role, ([], []))


def _sdk_surface_rows(
    standard_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    integration = standard_input.get("integration_profile", {})
    discovery = standard_input.get("discovery_manifest", {})
    passport = standard_input.get("universal_rdllm_passport", {})
    conformance = standard_input.get("conformance_vector_pack", {})
    public_surfaces = integration.get("public_surfaces", {})
    schemas = integration.get("schemas", {})
    verifier_commands = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    discovery_paths = discovery.get("discovery", {})
    endpoints = {
        str(endpoint.get("name", ""))
        for endpoint in integration.get("api_contract", {}).get("endpoints", [])
        if isinstance(endpoint, dict)
    }
    surface_specs = {
        "well_known_discovery": bool(discovery_paths)
        and _artifact_status(discovery) == "ready",
        "universal_passport": _artifact_status(passport) == "ready",
        "universal_adoption_standard": public_surfaces.get(
            "universal_adoption_standard"
        )
        is True
        and discovery_paths.get("universal_adoption_standard_path")
        == DEFAULT_WELL_KNOWN_PATH
        and "universal_adoption_standard" in schemas,
        "response_envelope": public_surfaces.get("response_envelope") is True
        and "response_envelope" in schemas,
        "source_footer_renderer": public_surfaces.get("citation_footer_contract")
        is True
        and public_surfaces.get("source_footer_delivery") is True,
        "content_credential_export": public_surfaces.get(
            "universal_content_credential"
        )
        is True,
        "invocation_guard_middleware": public_surfaces.get("universal_invocation_guard")
        is True,
        "provider_meter_reconciliation": public_surfaces.get(
            "universal_invocation_coverage"
        )
        is True,
        "conformance_vector_runner": _artifact_status(conformance) == "ready"
        and "verify-conformance-vector-pack" in verifier_commands,
        "offline_verifier_bundle": integration.get("verifier_contract", {}).get(
            "offline_verification_supported"
        )
        is True
        and "verify-universal-adoption-standard" in verifier_commands,
    }
    rows = []
    for surface in sorted(required_surfaces):
        row = {
            "surface": surface,
            "ready": surface_specs.get(surface) is True,
            "schema_declared": surface in schemas
            or surface
            in {
                "well_known_discovery",
                "source_footer_renderer",
                "provider_meter_reconciliation",
                "offline_verifier_bundle",
            },
            "endpoint_declared": surface in endpoints
            or surface
            in {
                "well_known_discovery",
                "source_footer_renderer",
                "provider_meter_reconciliation",
                "offline_verifier_bundle",
            },
            "required": True,
        }
        row["sdk_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _role_rows(
    required_roles: list[str],
    sdk_rows: list[dict[str, Any]],
    verifier_commands: set[str],
) -> list[dict[str, Any]]:
    ready_surfaces = {
        str(row.get("surface", ""))
        for row in sdk_rows
        if row.get("ready") is True
    }
    rows = []
    for role in sorted(required_roles):
        surfaces, commands = _role_requirements(role)
        row = {
            "role": role,
            "required_sdk_surfaces": surfaces,
            "required_verifier_commands": commands,
            "sdk_surfaces_ready": set(surfaces).issubset(ready_surfaces),
            "verifier_commands_ready": set(commands).issubset(verifier_commands),
            "required": True,
        }
        row["ready"] = row["sdk_surfaces_ready"] and row["verifier_commands_ready"]
        row["implementer_role_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standards_mapping_rows(required_refs: list[str]) -> list[dict[str, Any]]:
    mapping = {
        "c2pa_content_credentials": (
            "https://spec.c2pa.org/",
            "content credentials bind exported AI assets to RDLLM proof handles",
            ["universal_content_credential", "universal_rdllm_passport"],
        ),
        "w3c_vc_data_integrity": (
            "https://www.w3.org/TR/vc-data-integrity/",
            "portable signed proof objects use replayable hash commitments",
            ["universal_rdllm_passport", "universal_adoption_standard"],
        ),
        "opentelemetry_genai": (
            "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "native provider calls bind to GenAI telemetry, coverage, and witnesses",
            ["universal_invocation_coverage", "universal_invocation_witness"],
        ),
        "model_context_protocol": (
            "https://modelcontextprotocol.io/specification/2025-06-18",
            "provider-neutral discovery and verifier commands can be exposed as resources and tools",
            ["discovery_manifest", "integration_profile"],
        ),
        "scitt_transparency": (
            "https://datatracker.ietf.org/wg/scitt/about/",
            "publication and witness proofs provide transparency-log style consistency",
            ["publication_monitor", "publication_witness", "trust_registry"],
        ),
        "iso_20022_remittance": (
            "https://www.iso20022.org/iso-20022-message-definitions",
            "cleared creator obligations can map to structured remittance instructions",
            ["clearinghouse_report", "remittance_report", "payment_execution_report"],
        ),
        "odrl_croissant_spdx_rights": (
            "https://www.w3.org/TR/odrl-model/",
            "rights, corpus metadata, and software/license duties remain machine-readable",
            ["creator_license_contract", "training_content_summary", "code_attribution_report"],
        ),
    }
    rows = []
    for reference in sorted(required_refs):
        url, control, artifacts = mapping.get(reference, ("", "", []))
        row = {
            "reference": reference,
            "reference_url": url,
            "control": control,
            "evidence_artifacts": artifacts,
            "mapped": bool(url and control and artifacts),
            "required": True,
        }
        row["standard_mapping_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _procurement_gate_rows(
    standard_input: dict[str, Any],
    required_gates: list[str],
    provider_rows: list[dict[str, Any]],
    sdk_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    passport = standard_input.get("universal_rdllm_passport", {})
    conformance = standard_input.get("conformance_vector_pack", {})
    exchange = standard_input.get("attribution_exchange", {})
    federation = standard_input.get("federation_handshake", {})
    provider_card = standard_input.get("provider_attribution_card", {})
    credential_hash = _summary(passport).get("universal_content_credential_hash", "")
    sdk_ready = {row["surface"]: row["ready"] for row in sdk_rows}
    gate_values = {
        "no_l137_passport_no_rdllm_claim": _artifact_status(passport) == "ready"
        and _artifact_target_level(passport) == "RDLLM-L137",
        "all_provider_families_covered": all(
            row["covered_by_adapter"]
            and row["covered_by_conformance"]
            and row["covered_by_contract"]
            and row["fail_closed_backed"]
            for row in provider_rows
        ),
        "all_native_calls_guarded_and_witnessed": bool(
            _summary(passport).get("universal_content_credential_hash")
        )
        and bool(credential_hash),
        "visible_source_footer_required": sdk_ready.get("source_footer_renderer")
        is True,
        "content_credential_required_for_export": sdk_ready.get(
            "content_credential_export"
        )
        is True,
        "conformance_vectors_must_pass": _artifact_status(conformance) == "ready"
        and _summary(conformance).get("test_vector_count", 0) > 0
        and _summary(conformance).get("negative_mutation_count", 0) > 0,
        "public_discovery_and_verifiers_required": sdk_ready.get(
            "well_known_discovery"
        )
        is True
        and sdk_ready.get("offline_verifier_bundle") is True,
        "creator_challenge_and_clearing_required": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("attribution_challenge")
        is True
        and provider_card.get("public_disclosure_surfaces", {}).get(
            "clearinghouse_report"
        )
        is True
        and _artifact_status(exchange) == "ready"
        and _artifact_status(federation) == "ready",
        "private_text_must_not_enter_public_proofs": True,
    }
    rows = []
    for gate in sorted(required_gates):
        row = {
            "gate": gate,
            "passed": gate_values.get(gate) is True,
            "required": True,
            "failure_action": "block_procurement_approval",
        }
        row["procurement_gate_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _public_surface_rows(
    standard_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    provider = standard_input.get("provider_attribution_card", {})
    integration = standard_input.get("integration_profile", {})
    discovery = standard_input.get("discovery_manifest", {})
    provider_surfaces = provider.get("public_disclosure_surfaces", {})
    integration_surfaces = integration.get("public_surfaces", {})
    schemas = integration.get("schemas", {})
    paths = discovery.get("discovery", {})
    rows = []
    for surface in sorted(required_surfaces):
        path = str(paths.get(f"{surface}_path", ""))
        if surface == "provider_attribution_card" and not path:
            path = str(paths.get("provider_card_path", ""))
        if surface == "discovery_manifest" and not path:
            path = "/.well-known/rdllm.json"
        row = {
            "surface": surface,
            "provider_disclosure_declared": provider_surfaces.get(surface) is True,
            "integration_surface_declared": integration_surfaces.get(surface) is True,
            "schema_declared": surface in schemas
            or surface in {"provider_attribution_card", "discovery_manifest"},
            "discovery_path": path,
            "discovery_path_declared": bool(path),
            "required": True,
        }
        row["published"] = (
            row["provider_disclosure_declared"]
            and row["integration_surface_declared"]
            and row["discovery_path_declared"]
        )
        if surface == "universal_adoption_standard":
            row["published"] = row["published"] and path == DEFAULT_WELL_KNOWN_PATH
        row["public_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_adoption_standard(
    standard_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L138 implementer-facing RDLLM adoption standard."""

    created_at = created_at or now_iso()
    policy = _policy(standard_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_roles = [str(name) for name in policy["required_implementer_roles"]]
    required_sdk = [str(name) for name in policy["required_sdk_surfaces"]]
    required_gates = [str(name) for name in policy["required_procurement_gates"]]
    required_refs = [str(name) for name in policy["required_standard_references"]]
    required_surfaces = [str(name) for name in policy["required_public_surfaces"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    passport = standard_input.get("universal_rdllm_passport", {})
    conformance = standard_input.get("conformance_vector_pack", {})
    integration = standard_input.get("integration_profile", {})
    discovery = standard_input.get("discovery_manifest", {})
    certification = standard_input.get("certification_report", {})
    exchange = standard_input.get("attribution_exchange", {})
    federation = standard_input.get("federation_handshake", {})
    registry = standard_input.get("trust_registry", {})

    artifact_bindings = _artifact_bindings(standard_input, required_artifacts)
    provider_rows = _provider_family_rows(standard_input, required_families)
    sdk_rows = _sdk_surface_rows(standard_input, required_sdk)
    verifier_commands = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    role_rows = _role_rows(required_roles, sdk_rows, verifier_commands)
    procurement_rows = _procurement_gate_rows(
        standard_input, required_gates, provider_rows, sdk_rows
    )
    standards_rows = _standards_mapping_rows(required_refs)
    public_rows = _public_surface_rows(standard_input, required_surfaces)

    private_findings = _contains_private_fields(
        {
            "artifact_bindings": artifact_bindings,
            "provider_family_rows": provider_rows,
            "sdk_surface_rows": sdk_rows,
            "implementer_role_rows": role_rows,
            "procurement_gate_rows": procurement_rows,
            "standards_mapping_rows": standards_rows,
            "public_surface_rows": public_rows,
        }
    )

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "certification_level_at_least_l137": (
            _summary(certification).get("status") == "passed"
            and _level_at_least(_summary(certification).get("highest_level", ""), "RDLLM-L137")
        ),
        "universal_passport_ready_l137": (
            _artifact_status(passport) == "ready"
            and _artifact_target_level(passport) == "RDLLM-L137"
            and _summary(passport).get("offline_verification_supported") is True
            and _summary(passport).get("privacy_preserved") is True
        ),
        "conformance_vector_pack_ready": (
            _artifact_status(conformance) == "ready"
            and _summary(conformance).get("offline_verification_supported") is True
            and _summary(conformance).get("test_vector_count", 0) > 0
            and _summary(conformance).get("negative_mutation_count", 0) > 0
        ),
        "attribution_exchange_and_federation_ready": (
            _artifact_status(exchange) == "ready"
            and _artifact_status(federation) == "ready"
        ),
        "trust_registry_ready": _artifact_status(registry) == "ready",
        "all_provider_families_standardized": all(
            row["covered_by_adapter"]
            and row["covered_by_conformance"]
            and row["covered_by_contract"]
            and row["fail_closed_backed"]
            and bool(row["official_documentation_refs"])
            for row in provider_rows
        ),
        "sdk_surfaces_complete": all(row["ready"] for row in sdk_rows),
        "implementer_roles_complete": all(row["ready"] for row in role_rows),
        "procurement_gates_pass": all(row["passed"] for row in procurement_rows),
        "standards_mappings_complete": all(row["mapped"] for row in standards_rows),
        "public_standard_surfaces_published": all(row["published"] for row in public_rows),
        "public_verifier_commands_declared": set(required_commands).issubset(
            verifier_commands
        ),
        "discovery_manifest_exposes_standard_path": discovery.get("discovery", {}).get(
            "universal_adoption_standard_path"
        )
        == DEFAULT_WELL_KNOWN_PATH,
        "offline_verification_supported": (
            integration.get("verifier_contract", {}).get(
                "offline_verification_supported"
            )
            is True
            and _summary(discovery).get("offline_verification_supported") is True
            and _summary(passport).get("offline_verification_supported") is True
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        {
            "artifact_bindings": artifact_bindings,
            "provider_family_rows": provider_rows,
            "sdk_surface_rows": sdk_rows,
            "implementer_role_rows": role_rows,
            "procurement_gate_rows": procurement_rows,
            "standards_mapping_rows": standards_rows,
            "public_surface_rows": public_rows,
        },
        standard_input,
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "required_standard_artifact_missing",
        "artifact_hashes_reproducible": "artifact_hash_not_reproducible",
        "certification_level_at_least_l137": "certification_level_too_low",
        "universal_passport_ready_l137": "universal_passport_missing_or_blocked",
        "conformance_vector_pack_ready": "conformance_vectors_missing_or_failed",
        "attribution_exchange_and_federation_ready": "exchange_or_federation_not_ready",
        "trust_registry_ready": "trust_registry_not_ready",
        "all_provider_families_standardized": "provider_family_standardization_gap",
        "sdk_surfaces_complete": "sdk_surface_missing",
        "implementer_roles_complete": "implementer_role_not_covered",
        "procurement_gates_pass": "procurement_gate_failed",
        "standards_mappings_complete": "standards_mapping_missing",
        "public_standard_surfaces_published": "public_standard_surface_missing",
        "public_verifier_commands_declared": "verifier_command_missing",
        "discovery_manifest_exposes_standard_path": "discovery_standard_path_missing",
        "offline_verification_supported": "offline_verification_not_supported",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["standard_provider_family_row_hash"] for row in provider_rows]
        ),
        "sdk_surface_root": merkle_root(
            [row["sdk_surface_row_hash"] for row in sdk_rows]
        ),
        "implementer_role_root": merkle_root(
            [row["implementer_role_row_hash"] for row in role_rows]
        ),
        "procurement_gate_root": merkle_root(
            [row["procurement_gate_row_hash"] for row in procurement_rows]
        ),
        "standards_mapping_root": merkle_root(
            [row["standard_mapping_row_hash"] for row in standards_rows]
        ),
        "public_surface_root": merkle_root(
            [row["public_surface_row_hash"] for row in public_rows]
        ),
        "universal_rdllm_passport_hash": _declared_hash(passport),
        "conformance_vector_pack_hash": _declared_hash(conformance),
        "integration_profile_hash": _declared_hash(integration),
        "discovery_manifest_hash": _declared_hash(discovery),
    }
    commitments["standard_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "standard_version": UNIVERSAL_ADOPTION_STANDARD_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "standard_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "sdk_surface_rows": sdk_rows,
        "implementer_role_rows": role_rows,
        "procurement_gate_rows": procurement_rows,
        "standards_mapping_rows": standards_rows,
        "public_surface_rows": public_rows,
        "commitments": commitments,
        "checks": checks,
        "standard_decision": {
            "decision": "publish_universal_adoption_standard"
            if ready
            else "block_universal_adoption_standard",
            "publication_authorized": ready,
            "procurement_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "publish_l138_standard_and_l137_passport"
            if ready
            else "block_standard_publication",
        },
        "schemas": {
            "universal_adoption_standard": UNIVERSAL_ADOPTION_STANDARD_SCHEMA,
            "universal_rdllm_passport": "docs/schemas/universal_rdllm_passport.schema.json",
            "conformance_vector_pack": "docs/schemas/conformance_vector_pack.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_output_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "private_payment_details_disclosed": False,
            "hash_only_standard_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_rows),
            "sdk_surface_count": len(sdk_rows),
            "implementer_role_count": len(role_rows),
            "procurement_gate_count": len(procurement_rows),
            "standards_mapping_count": len(standards_rows),
            "public_surface_count": len(public_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "offline_verification_supported": checks[
                "offline_verification_supported"
            ],
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_rdllm_passport_hash": _declared_hash(passport),
            "conformance_vector_pack_hash": _declared_hash(conformance),
            "standard_commitment_hash": commitments["standard_commitment_hash"],
        },
    }
    report["universal_adoption_standard_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_adoption_standard_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "standard_version",
        "issuer",
        "created_at",
        "standard_policy",
        "artifact_bindings",
        "provider_family_rows",
        "sdk_surface_rows",
        "implementer_role_rows",
        "procurement_gate_rows",
        "standards_mapping_rows",
        "public_surface_rows",
        "commitments",
        "checks",
        "standard_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_adoption_standard_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal adoption standard field: {key}")
    if errors:
        return errors
    if report.get("standard_version") != UNIVERSAL_ADOPTION_STANDARD_VERSION:
        errors.append("universal adoption standard version is unsupported")
    if (
        report.get("schemas", {}).get("universal_adoption_standard")
        != UNIVERSAL_ADOPTION_STANDARD_SCHEMA
    ):
        errors.append("universal adoption standard schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal adoption standard target level is not RDLLM-L138")
    for finding in _contains_private_fields(report):
        errors.append(f"universal adoption standard contains private field: {finding}")
    return errors


def verify_universal_adoption_standard(
    report: dict[str, Any],
    *,
    standard_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L138 universal adoption standard by replaying its inputs."""

    errors = validate_universal_adoption_standard_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_adoption_standard_hash"):
        errors.append("universal adoption standard hash is not reproducible")

    expected = make_universal_adoption_standard(
        standard_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "standard_policy",
        "artifact_bindings",
        "provider_family_rows",
        "sdk_surface_rows",
        "implementer_role_rows",
        "procurement_gate_rows",
        "standards_mapping_rows",
        "public_surface_rows",
        "commitments",
        "checks",
        "standard_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal adoption standard {key} does not match replay")
    if expected.get("universal_adoption_standard_hash") != report.get(
        "universal_adoption_standard_hash"
    ):
        errors.append("universal adoption standard hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal adoption standard status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal adoption standard check failed: {check}")

    if not _private_strings_absent(report, standard_input):
        errors.append("universal adoption standard leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal adoption standard is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal adoption standard signature is invalid")

    return errors
