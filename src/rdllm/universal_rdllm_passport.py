"""Universal RDLLM deployment passport.

The L137 layer is the provider/deployment-level adoption object. L136 proves a
single released asset can carry portable source, payout, provenance, and
invocation evidence; L137 proves the whole provider or gateway deployment
publishes one offline-verifiable passport binding those proofs, verifier
commands, public discovery surfaces, and universal foundation-model conformance.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from rdllm.composite_foundation_adapter import DEFAULT_PROVIDER_FAMILIES
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_RDLLM_PASSPORT_VERSION = "rdllm-universal-rdllm-passport/v1"
UNIVERSAL_RDLLM_PASSPORT_SCHEMA = "docs/schemas/universal_rdllm_passport.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L137"
MINIMUM_INPUT_LEVEL = "RDLLM-L136"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-rdllm-passport.json"

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "training_content_summary",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "universal_composition_receipt",
    "universal_composition_settlement",
    "universal_foundation_model_contract",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "universal_content_credential",
)

REQUIRED_PUBLIC_SURFACES = (
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "universal_foundation_model_contract",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "universal_content_credential",
    "universal_rdllm_passport",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-certification-attestation",
    "verify-integration-profile",
    "verify-discovery-manifest",
    "verify-assurance-bundle",
    "verify-proof-dependency-graph",
    "verify-composite-foundation-adapter",
    "verify-foundation-provider-conformance",
    "verify-foundation-runtime-adapter",
    "verify-foundation-runtime-router",
    "verify-foundation-model-deployment-attestation",
    "verify-universal-composition-receipt",
    "verify-universal-composition-settlement",
    "verify-universal-foundation-model-contract",
    "verify-universal-invocation-guard",
    "verify-universal-invocation-coverage",
    "verify-universal-invocation-witness",
    "verify-universal-content-credential",
    "verify-universal-rdllm-passport",
)

DECLARED_HASH_FIELDS = (
    "universal_rdllm_passport_hash",
    "universal_content_credential_hash",
    "universal_invocation_witness_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "universal_foundation_model_contract_hash",
    "universal_composition_settlement_hash",
    "universal_composition_receipt_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "proof_response_hash",
    "gateway_report_hash",
    "gate_hash",
    "capsule_hash",
    "handshake_hash",
    "vector_pack_hash",
    "exchange_hash",
    "binding_report_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "citation_url_health_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
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


def load_universal_rdllm_passport_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L137 universal RDLLM passport."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_rdllm_passport_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], passport_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in passport_input.get("private_strings", [])
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


def _policy(passport_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(passport_input.get("passport_policy", {}))
    return {
        "profile": "rdllm-universal-passport-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", DEFAULT_PROVIDER_FAMILIES)
        ),
        "required_public_surfaces": list(
            policy.get("required_public_surfaces", REQUIRED_PUBLIC_SURFACES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_provider_family": "block_passport_publication",
        "on_missing_public_surface": "block_passport_publication",
        "on_unverifiable_artifact_hash": "block_passport_publication",
        "on_missing_l136_content_credential": "block_passport_publication",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(
    passport_input: dict[str, Any], required_artifacts: list[str]
) -> dict[str, Any]:
    rows = []
    for name in required_artifacts:
        artifact = passport_input.get(name)
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


def _artifact_binding_by_name(artifact_bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name", "")): row
        for row in artifact_bindings.get("bindings", [])
        if isinstance(row, dict)
    }


def _provider_family_rows(
    passport_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    composite = passport_input.get("composite_foundation_adapter", {})
    conformance = passport_input.get("foundation_provider_conformance", {})
    contract = passport_input.get("universal_foundation_model_contract", {})

    adapter_by_family = {
        str(row.get("provider_family", "")): row
        for row in composite.get("provider_adapter_rows", [])
        if isinstance(row, dict)
    }
    conformance_by_family = {
        str(row.get("provider_family", "")): row
        for row in conformance.get("provider_conformance_rows", [])
        if isinstance(row, dict)
    }
    contract_by_family = {
        str(row.get("provider_family", "")): row
        for row in contract.get("provider_family_rows", [])
        if isinstance(row, dict)
    }

    rows: list[dict[str, Any]] = []
    for family in sorted(required_families):
        adapter = adapter_by_family.get(family, {})
        conformance_row = conformance_by_family.get(family, {})
        contract_row = contract_by_family.get(family, {})
        row = {
            "provider_family": family,
            "provider_id": str(
                adapter.get("provider_id")
                or conformance_row.get("provider_id")
                or contract_row.get("provider_id")
                or ""
            ),
            "native_api_version": str(
                adapter.get("native_api_version")
                or conformance_row.get("native_api_version")
                or contract_row.get("native_api_version")
                or ""
            ),
            "native_model_hash": hash_payload(
                {
                    "native_model": str(
                        adapter.get("native_model")
                        or conformance_row.get("native_model")
                        or contract_row.get("native_model")
                        or ""
                    )
                }
            ),
            "provider_adapter_row_hash": str(
                adapter.get("provider_adapter_row_hash", "")
            ),
            "foundation_provider_conformance_row_hash": str(
                conformance_row.get("foundation_provider_conformance_row_hash", "")
            ),
            "universal_provider_contract_row_hash": str(
                contract_row.get("universal_provider_contract_row_hash", "")
            ),
            "route_hash": str(contract_row.get("route_hash", "")),
            "official_documentation_refs": list(
                conformance_row.get("official_documentation_refs", [])
                or contract_row.get("official_documentation_refs", [])
            ),
            "capability_count": int(
                contract_row.get("capability_count")
                or len(
                    [
                        key
                        for key, value in conformance_row.get("capabilities", {}).items()
                        if key and value is True
                    ]
                )
            ),
            "negative_fixture_count": int(
                contract_row.get("negative_fixture_count")
                or len(conformance_row.get("negative_fixture_hashes", {}))
            ),
            "covered_by_adapter": bool(adapter),
            "covered_by_conformance": bool(conformance_row),
            "covered_by_contract": bool(contract_row),
            "fail_closed_backed": bool(
                contract_row.get("fail_closed_backed")
                or (
                    conformance_row.get("negative_fixture_hashes")
                    and conformance_row.get("failure_policy")
                )
            ),
        }
        row["passport_provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _catalog_names(discovery_manifest: dict[str, Any]) -> set[str]:
    return {
        str(row.get("name", ""))
        for row in discovery_manifest.get("artifact_catalog", [])
        if isinstance(row, dict)
    }


def _adoption_surface_rows(
    passport_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    provider_card = passport_input.get("provider_attribution_card", {})
    integration = passport_input.get("integration_profile", {})
    discovery = passport_input.get("discovery_manifest", {})
    provider_surfaces = provider_card.get("public_disclosure_surfaces", {})
    provider_channels = provider_card.get("supported_evidence_channels", {})
    integration_surfaces = integration.get("public_surfaces", {})
    schemas = integration.get("schemas", {})
    paths = discovery.get("discovery", {})
    catalog = _catalog_names(discovery)

    rows = []
    for surface in sorted(required_surfaces):
        path = str(paths.get(f"{surface}_path", ""))
        if not path and surface == "provider_attribution_card":
            path = str(paths.get("provider_card_path", ""))
        if not path and surface == "discovery_manifest":
            path = "/.well-known/rdllm.json"
        row = {
            "surface": surface,
            "provider_disclosure_declared": provider_surfaces.get(surface) is True,
            "provider_evidence_channel_declared": provider_channels.get(surface) is True,
            "integration_surface_declared": integration_surfaces.get(surface) is True,
            "schema_declared": surface in schemas or surface == "universal_rdllm_passport",
            "discovery_path": path,
            "discovery_path_declared": bool(path),
            "discovery_catalog_published": surface in catalog,
            "well_known_path": DEFAULT_WELL_KNOWN_PATH
            if surface == "universal_rdllm_passport"
            else path,
            "required": True,
        }
        row["published"] = (
            row["provider_disclosure_declared"]
            and row["integration_surface_declared"]
            and row["discovery_path_declared"]
        )
        if surface == "universal_rdllm_passport":
            row["published"] = row["published"] and path == DEFAULT_WELL_KNOWN_PATH
        row["adoption_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    passport_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    integration = passport_input.get("integration_profile", {})
    profile_commands = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    rows = []
    for command in sorted(required_commands):
        row = {
            "command": command,
            "declared_by_integration_profile": command in profile_commands,
            "offline_replay_command": command.startswith("verify-")
            or command == "conformance",
            "required": True,
        }
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _core_proof_rows(artifact_bindings: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for binding in artifact_bindings.get("bindings", []):
        row = {
            "name": binding["name"],
            "declared_hash": binding["declared_hash"],
            "hash_reproducible": binding["hash_reproducible"],
            "status": binding["status"],
            "target_level": binding["target_level"],
            "present": binding["present"],
        }
        row["core_proof_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _research_alignment_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "reference_id": "arxiv:2508.15396",
            "reference_url": "https://arxiv.org/abs/2508.15396",
            "control": "unified evidence-based text generation taxonomy",
            "passport_binding": "source footers, claim coverage, and answer provenance are required core proofs",
        },
        {
            "reference_id": "arxiv:2507.04480",
            "reference_url": "https://arxiv.org/abs/2507.04480",
            "control": "document-level source attribution under redundancy and synergy",
            "passport_binding": "provider passport binds attribution rows and payout rows instead of only final citations",
        },
        {
            "reference_id": "arxiv:2510.17853",
            "reference_url": "https://arxiv.org/abs/2510.17853",
            "control": "citation attribution alignment",
            "passport_binding": "visible citation/source footers must be backed by replayable evidence and URL health",
        },
        {
            "reference_id": "arxiv:2605.05687",
            "reference_url": "https://arxiv.org/abs/2605.05687",
            "control": "pinpoint provenance and anti-document robustness",
            "passport_binding": "training-memory, pinpoint provenance, and L136 content credential proofs are hash-bound",
        },
        {
            "reference_id": "c2pa:2.2",
            "reference_url": "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html",
            "control": "content credential validation and durable asset provenance",
            "passport_binding": "L136 content credential is required and points to public RDLLM verification surfaces",
        },
        {
            "reference_id": "w3c:vc-data-integrity-1.0",
            "reference_url": "https://www.w3.org/TR/vc-data-integrity/",
            "control": "cryptographic integrity for portable constrained documents",
            "passport_binding": "passport, credential, graph, and bundle hashes are replayed without network dependency",
        },
        {
            "reference_id": "opentelemetry:gen-ai-semconv",
            "reference_url": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "control": "GenAI trace interoperability",
            "passport_binding": "runtime, invocation coverage, and witness proofs bind provider calls to public traces",
        },
        {
            "reference_id": "mcp:2025-06-18",
            "reference_url": "https://modelcontextprotocol.io/specification/2025-06-18",
            "control": "composable context, resources, tools, and host integrations",
            "passport_binding": "provider-neutral public surfaces and verifier commands are exposed as one integration entry point",
        },
    ]
    for row in rows:
        row["research_alignment_row_hash"] = hash_payload(row)
    return rows


def _interoperability_profile(
    passport_input: dict[str, Any],
    provider_family_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    credential = passport_input.get("universal_content_credential", {})
    discovery = passport_input.get("discovery_manifest", {})
    integration = passport_input.get("integration_profile", {})
    return {
        "profile": "rdllm-universal-interoperability-profile/v1",
        "provider_family_count": len(provider_family_rows),
        "supported_provider_families": [
            row["provider_family"]
            for row in provider_family_rows
            if row["covered_by_adapter"]
            and row["covered_by_conformance"]
            and row["covered_by_contract"]
        ],
        "well_known_passport_path": DEFAULT_WELL_KNOWN_PATH,
        "well_known_discovery_path": "/.well-known/rdllm.json",
        "content_credential_path": "/.well-known/rdllm/universal-content-credential.json",
        "c2pa_compatible_content_credentials": True,
        "w3c_verifiable_credential_compatible_signatures": True,
        "scitt_statement_subject_compatible_hashes": True,
        "mcp_resource_compatible_public_paths": True,
        "opentelemetry_genai_trace_binding": True,
        "offline_verification_supported": bool(
            integration.get("verifier_contract", {}).get(
                "offline_verification_supported"
            )
        )
        and bool(_summary(discovery).get("offline_verification_supported"))
        and bool(_summary(credential).get("offline_verification_supported")),
    }


def make_universal_rdllm_passport(
    passport_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L137 deployment passport for universal RDLLM adoption."""

    created_at = created_at or now_iso()
    policy = _policy(passport_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_surfaces = [str(name) for name in policy["required_public_surfaces"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    artifact_bindings = _artifact_bindings(passport_input, required_artifacts)
    bindings_by_name = _artifact_binding_by_name(artifact_bindings)
    provider_rows = _provider_family_rows(passport_input, required_families)
    adoption_rows = _adoption_surface_rows(passport_input, required_surfaces)
    verifier_rows = _verifier_command_rows(passport_input, required_commands)
    core_rows = _core_proof_rows(artifact_bindings)
    research_rows = _research_alignment_rows()
    interoperability = _interoperability_profile(passport_input, provider_rows)

    certification = passport_input.get("certification_report", {})
    certification_attestation = passport_input.get("certification_attestation", {})
    integration = passport_input.get("integration_profile", {})
    provider_card = passport_input.get("provider_attribution_card", {})
    discovery = passport_input.get("discovery_manifest", {})
    assurance = passport_input.get("assurance_bundle", {})
    graph = passport_input.get("proof_dependency_graph", {})
    composite = passport_input.get("composite_foundation_adapter", {})
    conformance = passport_input.get("foundation_provider_conformance", {})
    runtime_adapter = passport_input.get("foundation_runtime_adapter", {})
    router = passport_input.get("foundation_runtime_router", {})
    deployment = passport_input.get("foundation_model_deployment_attestation", {})
    composition = passport_input.get("universal_composition_receipt", {})
    settlement = passport_input.get("universal_composition_settlement", {})
    contract = passport_input.get("universal_foundation_model_contract", {})
    guard = passport_input.get("universal_invocation_guard", {})
    coverage = passport_input.get("universal_invocation_coverage", {})
    witness = passport_input.get("universal_invocation_witness", {})
    credential = passport_input.get("universal_content_credential", {})

    assurance_types = set(_summary(assurance).get("artifact_types", []))
    directly_bound_types = {
        name
        for name in required_artifacts
        if bindings_by_name.get(name, {}).get("present")
        and bindings_by_name.get(name, {}).get("hash_reproducible")
    }
    graph_summary = _summary(graph)
    credential_summary = _summary(credential)
    credential_checks = credential.get("checks", {})
    observed_families = {
        row["provider_family"]
        for row in provider_rows
        if row["covered_by_adapter"]
        and row["covered_by_conformance"]
        and row["covered_by_contract"]
        and row["fail_closed_backed"]
    }

    private_findings = _contains_private_fields(
        {
            "artifact_bindings": artifact_bindings,
            "provider_family_rows": provider_rows,
            "adoption_surface_rows": adoption_rows,
            "verifier_command_rows": verifier_rows,
            "core_proof_rows": core_rows,
            "research_alignment_rows": research_rows,
            "interoperability_profile": interoperability,
        }
    )

    checks = {
        "required_core_artifacts_present": all(
            bindings_by_name[name]["present"] for name in required_artifacts
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "certification_level_at_least_l136": (
            _summary(certification).get("status") == "passed"
            and _level_at_least(_summary(certification).get("highest_level", ""), "RDLLM-L136")
        ),
        "certification_attests_l136_report": (
            _artifact_status(certification_attestation) == "attested"
            and _level_at_least(
                _summary(certification_attestation).get("attested_highest_level", ""),
                "RDLLM-L136",
            )
        ),
        "provider_card_declares_passport": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("universal_rdllm_passport")
        is True
        and provider_card.get("supported_evidence_channels", {}).get(
            "universal_rdllm_passport"
        )
        is True,
        "integration_profile_declares_passport_surface": integration.get(
            "public_surfaces", {}
        ).get("universal_rdllm_passport")
        is True
        and "universal_rdllm_passport" in integration.get("schemas", {}),
        "discovery_manifest_exposes_passport_path": discovery.get("discovery", {}).get(
            "universal_rdllm_passport_path"
        )
        == DEFAULT_WELL_KNOWN_PATH,
        "discovery_manifest_publishes_l136_or_better": (
            _artifact_status(discovery) == "ready"
            and _level_at_least(_summary(discovery).get("highest_level", ""), "RDLLM-L136")
        ),
        "proof_dependency_graph_ready_and_acyclic": (
            _artifact_status(graph) == "ready"
            and _level_at_least(
                graph_summary.get("target_certification_level", ""), "RDLLM-L136"
            )
            and int(graph_summary.get("cycle_node_count", 1)) == 0
            and int(graph_summary.get("unknown_dependency_count", 1)) == 0
        ),
        "assurance_bundle_includes_l136_chain": (
            _summary(assurance).get("artifact_count", 0) >= 1
            and {
                "certification_report",
                "integration_profile",
                "provider_attribution_card",
                "universal_invocation_guard",
                "universal_invocation_coverage",
                "universal_invocation_witness",
                "universal_content_credential",
            }
            <= (assurance_types | directly_bound_types)
        ),
        "provider_families_cover_required_set": set(required_families).issubset(
            observed_families
        ),
        "foundation_adapter_conformance_and_contract_ready": (
            _artifact_status(composite) == "ready"
            and _level_at_least(_artifact_target_level(composite), "RDLLM-L125")
            and _artifact_status(conformance) == "ready"
            and _level_at_least(_artifact_target_level(conformance), "RDLLM-L126")
            and _artifact_status(contract) == "ready"
            and _level_at_least(_artifact_target_level(contract), "RDLLM-L132")
        ),
        "runtime_chain_released": (
            _artifact_status(runtime_adapter) == "released"
            and _level_at_least(_artifact_target_level(runtime_adapter), "RDLLM-L127")
            and _artifact_status(router) == "released"
            and _level_at_least(_artifact_target_level(router), "RDLLM-L128")
            and _artifact_status(deployment) == "released"
            and _level_at_least(_artifact_target_level(deployment), "RDLLM-L129")
        ),
        "composition_and_settlement_ready": (
            _artifact_status(composition) == "released"
            and _level_at_least(_artifact_target_level(composition), "RDLLM-L130")
            and _artifact_status(settlement) == "ready"
            and _level_at_least(_artifact_target_level(settlement), "RDLLM-L131")
        ),
        "invocation_guard_coverage_witness_ready": (
            _artifact_status(guard) == "ready"
            and _level_at_least(_artifact_target_level(guard), "RDLLM-L133")
            and _artifact_status(coverage) == "ready"
            and _level_at_least(_artifact_target_level(coverage), "RDLLM-L134")
            and _artifact_status(witness) == "ready"
            and _level_at_least(_artifact_target_level(witness), "RDLLM-L135")
            and _summary(witness).get("nonrepudiation_complete") is True
        ),
        "universal_content_credential_ready_l136": (
            _artifact_status(credential) == "ready"
            and _level_at_least(_artifact_target_level(credential), "RDLLM-L136")
            and credential_summary.get("source_count", 0) > 0
            and credential_summary.get("payout_row_count", 0) > 0
            and credential_summary.get("provider_invocation_count", 0) > 0
        ),
        "content_credential_binds_sources_payouts_and_invocations": all(
            credential_checks.get(check) is True
            for check in (
                "sources_bound_to_visible_footer",
                "payout_rows_cover_sources",
                "provider_invocations_are_nonrepudiable",
                "content_credentials_bind_subject",
                "durable_signals_cover_content",
            )
        ),
        "public_adoption_surfaces_published": all(row["published"] for row in adoption_rows),
        "public_verifier_commands_declared": all(
            row["declared_by_integration_profile"] for row in verifier_rows
        ),
        "research_controls_mapped_to_mechanism": all(
            row["reference_url"] and row["passport_binding"] for row in research_rows
        ),
        "offline_verification_supported": interoperability["offline_verification_supported"],
        "public_report_has_no_private_field_names": not private_findings,
    }

    checks["private_strings_absent"] = _private_strings_absent(
        {
            "artifact_bindings": artifact_bindings,
            "provider_family_rows": provider_rows,
            "adoption_surface_rows": adoption_rows,
            "verifier_command_rows": verifier_rows,
            "core_proof_rows": core_rows,
            "research_alignment_rows": research_rows,
            "interoperability_profile": interoperability,
        },
        passport_input,
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "required_core_artifact_missing",
        "artifact_hashes_reproducible": "artifact_hash_not_reproducible",
        "certification_level_at_least_l136": "certification_level_too_low",
        "certification_attests_l136_report": "certification_attestation_missing_or_stale",
        "provider_card_declares_passport": "provider_card_passport_surface_missing",
        "integration_profile_declares_passport_surface": "integration_passport_surface_missing",
        "discovery_manifest_exposes_passport_path": "discovery_passport_path_missing",
        "discovery_manifest_publishes_l136_or_better": "discovery_manifest_level_too_low",
        "proof_dependency_graph_ready_and_acyclic": "proof_dependency_graph_not_replayable",
        "assurance_bundle_includes_l136_chain": "assurance_bundle_missing_l136_chain",
        "provider_families_cover_required_set": "provider_family_coverage_failure",
        "foundation_adapter_conformance_and_contract_ready": "foundation_contract_not_ready",
        "runtime_chain_released": "runtime_chain_not_released",
        "composition_and_settlement_ready": "composition_settlement_not_ready",
        "invocation_guard_coverage_witness_ready": "invocation_nonrepudiation_not_ready",
        "universal_content_credential_ready_l136": "universal_content_credential_missing_or_blocked",
        "content_credential_binds_sources_payouts_and_invocations": "content_credential_binding_incomplete",
        "public_adoption_surfaces_published": "public_adoption_surface_missing",
        "public_verifier_commands_declared": "verifier_command_missing",
        "research_controls_mapped_to_mechanism": "research_control_mapping_missing",
        "offline_verification_supported": "offline_verification_not_supported",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["passport_provider_family_row_hash"] for row in provider_rows]
        ),
        "adoption_surface_root": merkle_root(
            [row["adoption_surface_row_hash"] for row in adoption_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_rows]
        ),
        "core_proof_root": merkle_root(
            [row["core_proof_row_hash"] for row in core_rows]
        ),
        "research_alignment_root": merkle_root(
            [row["research_alignment_row_hash"] for row in research_rows]
        ),
        "universal_content_credential_hash": _declared_hash(credential),
        "universal_foundation_model_contract_hash": _declared_hash(contract),
        "proof_dependency_graph_hash": _declared_hash(graph),
        "assurance_bundle_hash": _declared_hash(assurance),
    }
    commitments["passport_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "passport_version": UNIVERSAL_RDLLM_PASSPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "passport_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "adoption_surface_rows": adoption_rows,
        "verifier_command_rows": verifier_rows,
        "core_proof_rows": core_rows,
        "research_alignment_rows": research_rows,
        "interoperability_profile": interoperability,
        "commitments": commitments,
        "checks": checks,
        "passport_decision": {
            "decision": "publish_universal_rdllm_passport"
            if ready
            else "block_universal_rdllm_passport",
            "release_authorized": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "emit_l137_passport_and_source_footer"
            if ready
            else "block_passport_publication",
        },
        "schemas": {
            "universal_rdllm_passport": UNIVERSAL_RDLLM_PASSPORT_SCHEMA,
            "universal_content_credential": "docs/schemas/universal_content_credential.schema.json",
            "universal_foundation_model_contract": "docs/schemas/universal_foundation_model_contract.schema.json",
            "proof_dependency_graph": "docs/schemas/proof_dependency_graph.schema.json",
            "assurance_bundle": "docs/schemas/assurance_bundle.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_output_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "private_payment_details_disclosed": False,
            "hash_only_provider_and_creator_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_rows),
            "covered_provider_family_count": len(observed_families & set(required_families)),
            "required_provider_family_count": len(required_families),
            "core_artifact_count": len(core_rows),
            "public_surface_count": len(adoption_rows),
            "verifier_command_count": len(verifier_rows),
            "research_control_count": len(research_rows),
            "universal_content_credential_hash": _declared_hash(credential),
            "universal_foundation_model_contract_hash": _declared_hash(contract),
            "proof_dependency_graph_hash": _declared_hash(graph),
            "assurance_bundle_hash": _declared_hash(assurance),
            "passport_commitment_hash": commitments["passport_commitment_hash"],
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "offline_verification_supported": interoperability[
                "offline_verification_supported"
            ],
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
        },
    }
    report["universal_rdllm_passport_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_rdllm_passport_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "passport_version",
        "issuer",
        "created_at",
        "passport_policy",
        "artifact_bindings",
        "provider_family_rows",
        "adoption_surface_rows",
        "verifier_command_rows",
        "core_proof_rows",
        "research_alignment_rows",
        "interoperability_profile",
        "commitments",
        "checks",
        "passport_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_rdllm_passport_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal RDLLM passport field: {key}")
    if errors:
        return errors
    if report.get("passport_version") != UNIVERSAL_RDLLM_PASSPORT_VERSION:
        errors.append("universal RDLLM passport version is unsupported")
    if (
        report.get("schemas", {}).get("universal_rdllm_passport")
        != UNIVERSAL_RDLLM_PASSPORT_SCHEMA
    ):
        errors.append("universal RDLLM passport schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal RDLLM passport target level is not RDLLM-L137")
    for finding in _contains_private_fields(report):
        errors.append(f"universal RDLLM passport contains private field: {finding}")
    return errors


def verify_universal_rdllm_passport(
    report: dict[str, Any],
    *,
    passport_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L137 universal RDLLM passport by replaying its inputs."""

    errors = validate_universal_rdllm_passport_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_rdllm_passport_hash"):
        errors.append("universal RDLLM passport hash is not reproducible")

    expected = make_universal_rdllm_passport(
        passport_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "passport_policy",
        "artifact_bindings",
        "provider_family_rows",
        "adoption_surface_rows",
        "verifier_command_rows",
        "core_proof_rows",
        "research_alignment_rows",
        "interoperability_profile",
        "commitments",
        "checks",
        "passport_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal RDLLM passport {key} does not match replay")
    if expected.get("universal_rdllm_passport_hash") != report.get(
        "universal_rdllm_passport_hash"
    ):
        errors.append("universal RDLLM passport hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal RDLLM passport status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal RDLLM passport check failed: {check}")

    if not _private_strings_absent(report, passport_input):
        errors.append("universal RDLLM passport leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal RDLLM passport is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal RDLLM passport signature is invalid")

    return errors
