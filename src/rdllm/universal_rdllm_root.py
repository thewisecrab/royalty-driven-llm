"""Universal RDLLM root-of-trust artifact.

The L146 layer is the single composite proof a foundation-model provider,
gateway, enterprise buyer, creator registry, auditor, or regulator can start
from. It binds certification, attestation, public discovery, integration,
assurance, proof graph, source-footer delivery, training-to-serving continuity,
confidential auditability, runtime authority, and settlement posture into one
offline-verifiable root without embedding private prompts, source text, customer
logs, model internals, or payment details.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_RDLLM_ROOT_VERSION = "rdllm-universal-rdllm-root/v1"
UNIVERSAL_RDLLM_ROOT_SCHEMA = "docs/schemas/universal_rdllm_root.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L146"
MINIMUM_INPUT_LEVEL = "RDLLM-L145"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-rdllm-root.json"

REQUIRED_ROOT_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_training_serving_contract",
    "universal_confidential_attribution_audit",
    "universal_attribution_authority_control_plane",
    "universal_context_provenance_bridge",
    "universal_citation_verification_contract",
    "universal_grounded_reuse_contract",
    "source_footer_delivery",
    "proof_carrying_response",
    "response_envelope",
    "trust_registry",
    "foundation_model_deployment_attestation",
    "foundation_runtime_router",
    "foundation_runtime_adapter",
    "composite_foundation_adapter",
    "foundation_api_profile",
    "agent_tool_attribution_ledger",
    "persistent_memory_provenance",
    "private_reasoning_attribution",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google",
    "meta",
    "mistral",
    "cohere",
    "xai",
    "deepseek",
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_COMPOSITE_SURFACES = (
    "certification",
    "identity_and_trust",
    "provider_api",
    "agent_runtime",
    "context_and_retrieval",
    "citation_footer",
    "training_to_serving",
    "confidential_audit",
    "authority_control",
    "settlement_publication",
)

REQUIRED_FAILURE_CASES = (
    "missing_l145_authority_root",
    "certification_below_l145",
    "attestation_report_hash_mismatch",
    "discovery_missing_root_path",
    "proof_graph_cycle",
    "assurance_missing_l145",
    "integration_missing_root_surface",
    "provider_card_missing_root_support",
    "l143_l144_hash_mismatch",
    "l144_l145_hash_mismatch",
    "private_field_leak",
    "unsupported_provider_family",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-certification-attestation",
    "verify-provider-card",
    "verify-integration-profile",
    "verify-discovery-manifest",
    "verify-assurance-bundle",
    "verify-proof-dependency-graph",
    "verify-universal-training-serving-contract",
    "verify-universal-confidential-attribution-audit",
    "verify-universal-attribution-authority-control-plane",
    "verify-trust-registry",
    "verify-universal-rdllm-root",
)

DECLARED_HASH_FIELDS = (
    "universal_rdllm_root_hash",
    "universal_attribution_authority_control_plane_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "universal_context_provenance_bridge_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_profile_hash",
    "composite_foundation_adapter_hash",
    "tool_ledger_hash",
    "agent_tool_attribution_ledger_hash",
    "persistent_memory_provenance_hash",
    "private_reasoning_attribution_hash",
    "source_footer_delivery_hash",
    "proof_response_hash",
    "envelope_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "contract_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_query",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "raw_training_record",
    "training_text",
    "dataset_sample",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "reward_text",
    "preference_text",
    "critique_text",
    "hidden_state",
    "activation",
    "gradient",
    "model_weight",
    "model_weights",
    "model_parameters",
    "serving_log",
    "customer_log",
    "billing_record",
    "customer_id",
    "customer_email",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "raw_root_payload",
    "root_private_key",
    "authority_secret",
    "raw_artifact",
    "private_settlement_record",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_rdllm_root_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L146 universal RDLLM root."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_rdllm_root_hash", "signature"}
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
    if isinstance(metadata, dict) and "foundation_profile_hash" in artifact:
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
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
    if artifact.get("receipt_hash") and isinstance(artifact.get("payload"), dict):
        return artifact["receipt_hash"] == hash_payload(artifact["payload"])
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


def _private_strings_absent(report: dict[str, Any], root_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in root_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


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


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _component_input_map(root_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = root_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("provider_family")
                or row.get("composite_surface")
                or row.get("case_id")
                or row.get("command")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _root_obligation_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("provider_family", "")), str(row.get("composite_surface", "")))


def _policy(root_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(root_input.get("root_policy", {}))
    return {
        "profile": "rdllm-universal-root-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_root_artifacts": list(
            policy.get("required_root_artifacts", REQUIRED_ROOT_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_composite_surfaces": list(
            policy.get("required_composite_surfaces", REQUIRED_COMPOSITE_SURFACES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_l145_authority": "block_root_publication",
        "on_unverifiable_hash": "block_root_publication",
        "on_missing_public_surface": "block_root_publication",
        "on_private_payload_leak": "block_publication",
        "settlement_policy": "source_footer_and_creator_settlement_may_be_claimed_only_when_root_verifies",
    }


def _artifact_bindings(root_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = root_input.get(name)
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


def _binding_by_name(artifact_bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name", "")): row
        for row in artifact_bindings.get("bindings", [])
        if isinstance(row, dict)
    }


def _provider_family_rows(
    root_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(root_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "root_registry_hash": str(item.get("root_registry_hash", "")),
            "provider_public_key_hash": str(item.get("provider_public_key_hash", "")),
            "deployment_root_hash": str(item.get("deployment_root_hash", "")),
            "authority_control_hash": str(item.get("authority_control_hash", "")),
            "settlement_authority_hash": str(item.get("settlement_authority_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_universal_rdllm_root": item.get("supports_universal_rdllm_root") is True,
            "supports_public_verification": item.get("supports_public_verification") is True,
            "supports_cross_provider_attribution": item.get("supports_cross_provider_attribution") is True,
            "supports_creator_query": item.get("supports_creator_query") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["root_registry_hash"])
            and bool(row["provider_public_key_hash"])
            and bool(row["deployment_root_hash"])
            and bool(row["authority_control_hash"])
            and bool(row["settlement_authority_hash"])
            and row["public_verifier_command"] == "verify-universal-rdllm-root"
            and row["supports_universal_rdllm_root"]
            and row["supports_public_verification"]
            and row["supports_cross_provider_attribution"]
            and row["supports_creator_query"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _composite_surface_rows(
    root_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    surface_map = _component_input_map(root_input, "composite_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = surface_map.get(surface, {})
        row = {
            "composite_surface": surface,
            "surface_root_hash": str(item.get("surface_root_hash", "")),
            "api_contract_hash": str(item.get("api_contract_hash", "")),
            "schema_hash": str(item.get("schema_hash", "")),
            "well_known_path": str(item.get("well_known_path", "")),
            "challenge_fixture_hash": str(item.get("challenge_fixture_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["surface_root_hash"])
            and bool(row["api_contract_hash"])
            and bool(row["schema_hash"])
            and bool(row["well_known_path"])
            and bool(row["challenge_fixture_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["composite_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _root_obligation_rows(
    root_input: dict[str, Any],
    required_families: list[str],
    required_surfaces: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        root_input.get("root_obligation_rows", []),
        key=lambda row: (
            str(row.get("provider_family", "")) if isinstance(row, dict) else "",
            str(row.get("composite_surface", "")) if isinstance(row, dict) else "",
        ),
    ):
        if not isinstance(item, dict):
            continue
        row = {
            "provider_family": str(item.get("provider_family", "")),
            "composite_surface": str(item.get("composite_surface", "")),
            "root_binding_hash": str(item.get("root_binding_hash", "")),
            "artifact_set_hash": str(item.get("artifact_set_hash", "")),
            "verifier_set_hash": str(item.get("verifier_set_hash", "")),
            "policy_hash": str(item.get("policy_hash", "")),
            "publication_hash": str(item.get("publication_hash", "")),
            "challenge_hash": str(item.get("challenge_hash", "")),
            "fail_closed_fixture_hash": str(item.get("fail_closed_fixture_hash", "")),
            "l145_authority_hash": str(item.get("l145_authority_hash", "")),
            "certification_bound": item.get("certification_bound") is True,
            "discovery_bound": item.get("discovery_bound") is True,
            "integration_bound": item.get("integration_bound") is True,
            "proof_graph_bound": item.get("proof_graph_bound") is True,
            "assurance_bound": item.get("assurance_bound") is True,
            "authority_control_bound": item.get("authority_control_bound") is True,
            "source_footer_bound": item.get("source_footer_bound") is True,
            "settlement_bound": item.get("settlement_bound") is True,
            "verifier_command_bound": item.get("verifier_command_bound") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["required"] = (
            row["provider_family"] in required_families
            and row["composite_surface"] in required_surfaces
        )
        row["ready"] = (
            row["required"]
            and bool(row["root_binding_hash"])
            and bool(row["artifact_set_hash"])
            and bool(row["verifier_set_hash"])
            and bool(row["policy_hash"])
            and bool(row["publication_hash"])
            and bool(row["challenge_hash"])
            and bool(row["fail_closed_fixture_hash"])
            and bool(row["l145_authority_hash"])
            and row["certification_bound"]
            and row["discovery_bound"]
            and row["integration_bound"]
            and row["proof_graph_bound"]
            and row["assurance_bound"]
            and row["authority_control_bound"]
            and row["source_footer_bound"]
            and row["settlement_bound"]
            and row["verifier_command_bound"]
            and row["fail_closed"]
        )
        row["root_obligation_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    root_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(root_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = case_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
            "required": True,
        }
        row["passed"] = (
            bool(row["fixture_hash"])
            and row["verifier_command"] == "verify-universal-rdllm-root"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    root_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    declared = {str(command) for command in root_input.get("verifier_commands", [])}
    integration = root_input.get("integration_profile", {})
    discovery = root_input.get("discovery_manifest", {})
    declared |= set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    declared |= set(discovery.get("verification", {}).get("reference_cli_commands", []))
    rows = []
    for command in sorted(required_commands):
        row = {"command": command, "declared": command in declared, "required": True}
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _research_alignment_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "reference_id": "arxiv:2605.17169",
            "reference_url": "https://arxiv.org/abs/2605.17169",
            "control": "explicit provenance and responsibility attribution for agentic AI",
            "root_binding": "runtime authority, agent/tool use, and settlement decisions are root-bound before release",
        },
        {
            "reference_id": "arxiv:2604.05467",
            "reference_url": "https://arxiv.org/abs/2604.05467",
            "control": "intervention-based utility of retrieved evidence",
            "root_binding": "source-footers and payout eligibility must bind causal evidence utility artifacts",
        },
        {
            "reference_id": "arxiv:2510.17853",
            "reference_url": "https://arxiv.org/abs/2510.17853",
            "control": "faithful citation attribution alignment",
            "root_binding": "visible citations require citation-verification and grounded-reuse contracts",
        },
        {
            "reference_id": "frontiers:10.3389/fcomp.2026.1735919",
            "reference_url": "https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2026.1735919/full",
            "control": "AI bill of materials and lifecycle assurance",
            "root_binding": "root artifact binds attribution BOM, proof graph, assurance, and lifecycle contracts",
        },
        {
            "reference_id": "ietf:rfc9943",
            "reference_url": "https://www.rfc-editor.org/rfc/rfc9943.html",
            "control": "transparent supply-chain statements and attestations",
            "root_binding": "public hashes, verifier commands, and proof graph are published as challengeable statements",
        },
        {
            "reference_id": "w3c:vc-data-integrity-1.0",
            "reference_url": "https://www.w3.org/TR/vc-data-integrity/",
            "control": "cryptographic integrity for verifiable documents",
            "root_binding": "root, certification attestation, and public credentials verify by signature and hash replay",
        },
        {
            "reference_id": "c2pa:2.4",
            "reference_url": "https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html",
            "control": "content credentials with hard bindings and AI/ML asset types",
            "root_binding": "content credentials are treated as one surface of the root, not the whole attribution system",
        },
        {
            "reference_id": "ssrn:6761318",
            "reference_url": "https://ssrn.com/abstract=6761318",
            "control": "creator data licensing and compensation market design",
            "root_binding": "root distinguishes public attribution confidence from settlement authorization and escrow posture",
        },
    ]
    for row in rows:
        row["research_alignment_row_hash"] = hash_payload(row)
    return rows


def _certification_report_hash(report: dict[str, Any]) -> str:
    return str(report.get("report_hash") or hash_payload(_hashable_artifact(report)))


def _attestation_binds_report(
    attestation: dict[str, Any], certification_report: dict[str, Any]
) -> bool:
    report_hash = _certification_report_hash(certification_report)
    return (
        bool(report_hash)
        and attestation.get("subject", {}).get("certification_report_hash") == report_hash
        and attestation.get("commitments", {}).get("certification_report_hash")
        == report_hash
        and attestation.get("certification_summary", {}).get("status") == "passed"
        and _level_at_least(
            attestation.get("certification_summary", {}).get("highest_level", ""),
            MINIMUM_INPUT_LEVEL,
        )
    )


def make_universal_rdllm_root(
    root_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L146 universal RDLLM root-of-trust report."""

    created_at = created_at or now_iso()
    policy = _policy(root_input)
    required_artifacts = [str(name) for name in policy["required_root_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_surfaces = [str(name) for name in policy["required_composite_surfaces"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    artifact_bindings = _artifact_bindings(root_input, required_artifacts)
    bindings_by_name = _binding_by_name(artifact_bindings)
    provider_rows = _provider_family_rows(root_input, required_families)
    surface_rows = _composite_surface_rows(root_input, required_surfaces)
    obligation_rows = _root_obligation_rows(root_input, required_families, required_surfaces)
    failure_rows = _failure_case_rows(root_input, required_cases)
    verifier_rows = _verifier_command_rows(root_input, required_commands)
    research_rows = _research_alignment_rows()

    certification = root_input.get("certification_report", {})
    attestation = root_input.get("certification_attestation", {})
    provider_card = root_input.get("provider_attribution_card", {})
    integration = root_input.get("integration_profile", {})
    discovery = root_input.get("discovery_manifest", {})
    assurance = root_input.get("assurance_bundle", {})
    graph = root_input.get("proof_dependency_graph", {})
    l143 = root_input.get("universal_training_serving_contract", {})
    l144 = root_input.get("universal_confidential_attribution_audit", {})
    l145 = root_input.get("universal_attribution_authority_control_plane", {})

    required_matrix = {
        (provider_family, surface)
        for provider_family in required_families
        for surface in required_surfaces
    }
    observed_matrix = {_root_obligation_key(row) for row in obligation_rows}
    assurance_types = set(_summary(assurance).get("artifact_types", []))

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "composite_surface_rows": surface_rows,
        "root_obligation_rows": obligation_rows,
        "failure_case_rows": failure_rows,
        "verifier_command_rows": verifier_rows,
        "research_alignment_rows": research_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    integration_commands = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    checks = {
        "required_root_artifacts_present": all(
            bindings_by_name.get(name, {}).get("present") is True
            for name in required_artifacts
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "certification_passed_l145": (
            _summary(certification).get("status") == "passed"
            and _level_at_least(_summary(certification).get("highest_level", ""), MINIMUM_INPUT_LEVEL)
        ),
        "certification_attestation_binds_report_l145": _attestation_binds_report(
            attestation, certification
        )
        and _artifact_status(attestation) in {"attested", "ready"},
        "training_serving_ready_l143": (
            _artifact_status(l143) == "ready"
            and _level_at_least(_artifact_target_level(l143), "RDLLM-L143")
        ),
        "confidential_audit_ready_l144": (
            _artifact_status(l144) == "ready"
            and _level_at_least(_artifact_target_level(l144), "RDLLM-L144")
            and _summary(l144).get("privacy_preserved") is True
        ),
        "authority_control_ready_l145": (
            _artifact_status(l145) == "ready"
            and _level_at_least(_artifact_target_level(l145), "RDLLM-L145")
            and _summary(l145).get("privacy_preserved") is True
        ),
        "l143_l144_hash_chain_bound": (
            _summary(l144).get("universal_training_serving_contract_hash")
            == _declared_hash(l143)
        ),
        "l144_l145_hash_chain_bound": (
            _summary(l145).get("universal_confidential_attribution_audit_hash")
            == _declared_hash(l144)
        ),
        "integration_profile_ready_and_exposes_root": (
            _artifact_status(integration) == "ready"
            and integration.get("public_surfaces", {}).get("universal_rdllm_root") is True
            and "universal_rdllm_root" in integration.get("schemas", {})
            and "verify-universal-rdllm-root" in integration_commands
        ),
        "provider_card_exposes_root_support": (
            provider_card.get("public_disclosure_surfaces", {}).get("universal_rdllm_root")
            is True
            and provider_card.get("supported_evidence_channels", {}).get(
                "universal_rdllm_root"
            )
            is True
            and provider_card.get("rights_and_settlement", {}).get(
                "universal_rdllm_root_supported"
            )
            is True
            and provider_card.get("rights_and_settlement", {}).get(
                "single_composite_rdllm_root_supported"
            )
            is True
        ),
        "discovery_manifest_exposes_root_path": discovery.get("discovery", {}).get(
            "universal_rdllm_root_path"
        )
        == DEFAULT_WELL_KNOWN_PATH,
        "assurance_bundle_includes_l145": (
            "universal_attribution_authority_control_plane" in assurance_types
        ),
        "proof_graph_ready_l145_acyclic": (
            _artifact_status(graph) == "ready"
            and _level_at_least(_summary(graph).get("target_certification_level", ""), "RDLLM-L145")
            and int(_summary(graph).get("cycle_node_count", 1)) == 0
            and int(_summary(graph).get("unknown_dependency_count", 1)) == 0
        ),
        "provider_family_coverage_complete": all(row["ready"] for row in provider_rows),
        "composite_surface_coverage_complete": all(row["ready"] for row in surface_rows),
        "root_obligation_matrix_complete": (
            bool(required_matrix) and required_matrix <= observed_matrix
        ),
        "root_obligations_ready": bool(obligation_rows)
        and all(row["ready"] for row in obligation_rows),
        "public_verifier_commands_declared": all(row["declared"] for row in verifier_rows),
        "failure_cases_fail_closed": all(row["passed"] for row in failure_rows),
        "research_controls_mapped_to_mechanism": all(
            row["reference_url"] and row["root_binding"] for row in research_rows
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(public_projection, root_input)

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_root_artifacts_present": "root_artifact_missing",
        "artifact_hashes_reproducible": "root_artifact_hash_not_reproducible",
        "certification_passed_l145": "root_certification_below_l145",
        "certification_attestation_binds_report_l145": "root_attestation_mismatch",
        "training_serving_ready_l143": "root_l143_not_ready",
        "confidential_audit_ready_l144": "root_l144_not_ready",
        "authority_control_ready_l145": "root_l145_not_ready",
        "l143_l144_hash_chain_bound": "root_l143_l144_hash_mismatch",
        "l144_l145_hash_chain_bound": "root_l144_l145_hash_mismatch",
        "integration_profile_ready_and_exposes_root": "root_integration_surface_missing",
        "provider_card_exposes_root_support": "root_provider_card_surface_missing",
        "discovery_manifest_exposes_root_path": "root_discovery_path_missing",
        "assurance_bundle_includes_l145": "root_assurance_missing_l145",
        "proof_graph_ready_l145_acyclic": "root_proof_graph_not_ready",
        "provider_family_coverage_complete": "root_provider_family_gap",
        "composite_surface_coverage_complete": "root_surface_gap",
        "root_obligation_matrix_complete": "root_obligation_matrix_gap",
        "root_obligations_ready": "root_obligation_gate_failed",
        "public_verifier_commands_declared": "root_verifier_command_missing",
        "failure_cases_fail_closed": "root_negative_case_not_blocked",
        "research_controls_mapped_to_mechanism": "root_research_mapping_missing",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["provider_family_row_hash"] for row in provider_rows]
        ),
        "composite_surface_root": merkle_root(
            [row["composite_surface_row_hash"] for row in surface_rows]
        ),
        "root_obligation_root": merkle_root(
            [row["root_obligation_row_hash"] for row in obligation_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_rows]
        ),
        "research_alignment_root": merkle_root(
            [row["research_alignment_row_hash"] for row in research_rows]
        ),
        "certification_report_hash": _declared_hash(certification),
        "certification_attestation_hash": _declared_hash(attestation),
        "universal_training_serving_contract_hash": _declared_hash(l143),
        "universal_confidential_attribution_audit_hash": _declared_hash(l144),
        "universal_attribution_authority_control_plane_hash": _declared_hash(l145),
        "assurance_bundle_hash": _declared_hash(assurance),
        "proof_dependency_graph_hash": _declared_hash(graph),
        "discovery_manifest_hash": _declared_hash(discovery),
        "integration_profile_hash": _declared_hash(integration),
        "provider_attribution_card_hash": _declared_hash(provider_card),
    }
    commitments["root_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "root_version": UNIVERSAL_RDLLM_ROOT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "root_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "composite_surface_rows": surface_rows,
        "root_obligation_rows": obligation_rows,
        "failure_case_rows": failure_rows,
        "verifier_command_rows": verifier_rows,
        "research_alignment_rows": research_rows,
        "commitments": commitments,
        "checks": checks,
        "root_decision": {
            "decision": "publish_universal_rdllm_root"
            if ready
            else "block_universal_rdllm_root",
            "publication_authorized": ready,
            "attribution_footer_authorized": ready,
            "creator_settlement_authorized": ready,
            "customer_confidence_footer_enabled": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "emit_only_outputs_whose_source_footer_settlement_and_provider_runtime_are_bound_to_the_universal_rdllm_root"
            if ready
            else "block_root_publication_and_preserve_challenge_evidence",
        },
        "schemas": {
            "universal_rdllm_root": UNIVERSAL_RDLLM_ROOT_SCHEMA,
            "certification_report": "docs/schemas/certification_report.schema.json",
            "certification_attestation": "docs/schemas/certification_attestation.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "assurance_bundle": "docs/schemas/assurance_bundle.schema.json",
            "proof_dependency_graph": "docs/schemas/proof_dependency_graph.schema.json",
            "universal_attribution_authority_control_plane": "docs/schemas/universal_attribution_authority_control_plane.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_training_text_disclosed": False,
            "raw_tool_payload_disclosed": False,
            "raw_memory_payload_disclosed": False,
            "raw_customer_or_billing_logs_disclosed": False,
            "model_weights_or_hidden_states_disclosed": False,
            "payment_details_disclosed": False,
            "hash_only_root_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "root_artifact_count": len(artifact_bindings["bindings"]),
            "provider_family_count": len(provider_rows),
            "composite_surface_count": len(surface_rows),
            "root_obligation_count": len(obligation_rows),
            "required_obligation_count": len(required_matrix),
            "failure_case_count": len(failure_rows),
            "verifier_command_count": len(verifier_rows),
            "research_control_count": len(research_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "certification_report_hash": _declared_hash(certification),
            "universal_training_serving_contract_hash": _declared_hash(l143),
            "universal_confidential_attribution_audit_hash": _declared_hash(l144),
            "universal_attribution_authority_control_plane_hash": _declared_hash(l145),
            "assurance_bundle_hash": _declared_hash(assurance),
            "proof_dependency_graph_hash": _declared_hash(graph),
            "root_commitment_hash": commitments["root_commitment_hash"],
            "offline_verification_supported": True,
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
        },
    }
    report["universal_rdllm_root_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_rdllm_root_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "root_version",
        "issuer",
        "created_at",
        "root_policy",
        "artifact_bindings",
        "provider_family_rows",
        "composite_surface_rows",
        "root_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "research_alignment_rows",
        "commitments",
        "checks",
        "root_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_rdllm_root_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal RDLLM root field: {key}")
    if errors:
        return errors
    if report.get("root_version") != UNIVERSAL_RDLLM_ROOT_VERSION:
        errors.append("universal RDLLM root version is unsupported")
    if (
        report.get("schemas", {}).get("universal_rdllm_root")
        != UNIVERSAL_RDLLM_ROOT_SCHEMA
    ):
        errors.append("universal RDLLM root schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal RDLLM root target level is not RDLLM-L146")
    for finding in _contains_private_fields(report):
        errors.append(f"universal RDLLM root contains private field: {finding}")
    return errors


def verify_universal_rdllm_root(
    report: dict[str, Any],
    *,
    root_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L146 universal RDLLM root by replaying public inputs."""

    errors = validate_universal_rdllm_root_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_rdllm_root_hash"):
        errors.append("universal RDLLM root hash is not reproducible")

    expected = make_universal_rdllm_root(
        root_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "root_policy",
        "artifact_bindings",
        "provider_family_rows",
        "composite_surface_rows",
        "root_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "research_alignment_rows",
        "commitments",
        "checks",
        "root_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal RDLLM root {key} does not match replay")
    if expected.get("universal_rdllm_root_hash") != report.get(
        "universal_rdllm_root_hash"
    ):
        errors.append("universal RDLLM root hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal RDLLM root status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal RDLLM root check failed: {check}")

    if not _private_strings_absent(report, root_input):
        errors.append("universal RDLLM root leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal RDLLM root is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal RDLLM root signature is invalid")

    return errors
