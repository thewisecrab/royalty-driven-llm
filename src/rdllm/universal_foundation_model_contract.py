"""Universal foundation-model RDLLM contract.

This L132 layer is the provider-neutral adoption gate. It proves that the same
RDLLM attribution, grounding, routing, composition, and settlement contract works
across supported foundation-model API families, and that the actual displayed
answer is backed by the L127-L131 runtime chain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.composite_foundation_adapter import DEFAULT_PROVIDER_FAMILIES
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_FOUNDATION_MODEL_CONTRACT_VERSION = (
    "rdllm-universal-foundation-model-contract/v1"
)
UNIVERSAL_FOUNDATION_MODEL_CONTRACT_SCHEMA = (
    "docs/schemas/universal_foundation_model_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L132"
MINIMUM_INPUT_LEVEL = "RDLLM-L131"

REQUIRED_CHAIN_ARTIFACTS = (
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "proof_dependency_graph",
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "universal_composition_receipt",
    "universal_composition_settlement",
)

REQUIRED_PUBLIC_SURFACES = (
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "universal_composition_receipt",
    "universal_composition_settlement",
)

DECLARED_HASH_FIELDS = (
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
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "envelope_hash",
    "trace_hash",
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
    "source_text",
    "training_text",
    "document_text",
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
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_foundation_model_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay inputs for an L132 universal foundation-model contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_foundation_model_contract_hash", "signature"}
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
    contract_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in contract_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: Any) -> int | None:
    if not isinstance(level, str) or not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: Any, minimum: str) -> bool:
    level_num = _level_number(level)
    minimum_num = _level_number(minimum)
    return level_num is not None and minimum_num is not None and level_num >= minimum_num


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(summary.get("target_certification_level") or summary.get("highest_level") or "")


def _artifact_binding(name: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    version = ""
    if artifact:
        for key, value in artifact.items():
            if key.endswith("_version") and isinstance(value, str):
                version = value
                break
    return {
        "name": name,
        "version": version,
        "declared_hash": _declared_hash(artifact),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": _artifact_status(artifact),
        "target_level": _artifact_target_level(artifact),
        "present": bool(artifact),
    }


def _policy(contract_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(contract_input.get("contract_policy", {}))
    return {
        "profile": "rdllm-universal-foundation-model-contract-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_provider_families": list(
            policy.get("required_provider_families", DEFAULT_PROVIDER_FAMILIES)
        ),
        "required_chain_artifacts": list(
            policy.get("required_chain_artifacts", REQUIRED_CHAIN_ARTIFACTS)
        ),
        "required_public_surfaces": list(
            policy.get("required_public_surfaces", REQUIRED_PUBLIC_SURFACES)
        ),
        "minimum_discovery_level": str(
            policy.get("minimum_discovery_level", MINIMUM_INPUT_LEVEL)
        ),
        "minimum_proof_graph_level": str(
            policy.get("minimum_proof_graph_level", MINIMUM_INPUT_LEVEL)
        ),
        "on_missing_provider_family": "block_model_release",
        "on_missing_public_surface": "block_model_release",
        "on_unreleased_runtime_chain": "block_model_release",
        "on_unsettled_composition": "block_model_release",
        "on_private_text_leak": "block_publication",
    }


def _artifact_inputs(contract_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: contract_input.get(name, {})
        for name in REQUIRED_CHAIN_ARTIFACTS
        if isinstance(contract_input.get(name, {}), dict)
    }


def _provider_family_rows(
    contract_input: dict[str, Any],
    required_families: list[str],
) -> list[dict[str, Any]]:
    composite = contract_input.get("composite_foundation_adapter", {})
    conformance = contract_input.get("foundation_provider_conformance", {})
    router = contract_input.get("foundation_runtime_router", {})

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
    route_by_family = {
        str(row.get("provider_family", "")): row
        for row in router.get("candidate_route_bindings", [])
        if isinstance(row, dict)
    }

    rows: list[dict[str, Any]] = []
    for family in sorted(required_families):
        adapter = adapter_by_family.get(family, {})
        conformance_row = conformance_by_family.get(family, {})
        route = route_by_family.get(family, {})
        row = {
            "provider_family": family,
            "provider_id": str(
                adapter.get("provider_id")
                or conformance_row.get("provider_id")
                or route.get("provider_id")
                or ""
            ),
            "native_api_version": str(
                adapter.get("native_api_version")
                or conformance_row.get("native_api_version")
                or ""
            ),
            "native_model": str(
                adapter.get("native_model") or conformance_row.get("native_model") or ""
            ),
            "provider_adapter_row_hash": str(
                adapter.get("provider_adapter_row_hash", "")
            ),
            "foundation_provider_conformance_row_hash": str(
                conformance_row.get("foundation_provider_conformance_row_hash", "")
            ),
            "route_id": str(route.get("route_id", "")),
            "route_hash": str(route.get("route_hash", "")),
            "official_documentation_refs": list(
                conformance_row.get("official_documentation_refs", [])
            ),
            "capability_count": len(
                [
                    key
                    for key, value in conformance_row.get("capabilities", {}).items()
                    if value is True
                ]
            ),
            "negative_fixture_count": len(
                conformance_row.get("negative_fixture_hashes", {})
            ),
            "covered_by_adapter": bool(adapter),
            "covered_by_conformance": bool(conformance_row),
            "covered_by_router": bool(route),
            "fail_closed_backed": bool(
                conformance_row.get("negative_fixture_hashes")
                and conformance_row.get("failure_policy")
            ),
        }
        row["universal_provider_contract_row_hash"] = hash_payload(
            {
                key: value
                for key, value in row.items()
                if key != "universal_provider_contract_row_hash"
            }
        )
        rows.append(row)
    return rows


def _selected_route_binding(contract_input: dict[str, Any]) -> dict[str, Any]:
    runtime_adapter = contract_input.get("foundation_runtime_adapter", {})
    router = contract_input.get("foundation_runtime_router", {})
    deployment = contract_input.get("foundation_model_deployment_attestation", {})
    selected_route = router.get("selected_route_binding", {})
    return {
        "selected_route_id": str(selected_route.get("route_id", "")),
        "selected_provider_family": str(selected_route.get("provider_family", "")),
        "runtime_adapter_provider_family": str(
            _summary(runtime_adapter).get("provider_family", "")
        ),
        "deployment_provider_family": str(_summary(deployment).get("provider_family", "")),
        "foundation_runtime_adapter_hash": _declared_hash(runtime_adapter),
        "foundation_runtime_router_hash": _declared_hash(router),
        "foundation_model_deployment_attestation_hash": _declared_hash(deployment),
        "runtime_release_authorized": bool(
            _summary(runtime_adapter).get("runtime_release_authorized")
        ),
        "router_release_authorized": bool(
            _summary(router).get("router_release_authorized")
        ),
        "deployment_release_authorized": bool(
            _summary(deployment).get("deployment_release_authorized")
        ),
    }


def _public_surface_binding(contract_input: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    integration = contract_input.get("integration_profile", {})
    discovery = contract_input.get("discovery_manifest", {})
    proof_graph = contract_input.get("proof_dependency_graph", {})
    surfaces = integration.get("public_surfaces", {})
    discovery_paths = discovery.get("discovery", {})
    catalog_names = {
        str(entry.get("name"))
        for entry in discovery.get("artifact_catalog", [])
        if isinstance(entry, dict)
    }
    required_surfaces = list(policy["required_public_surfaces"])
    missing_integration = [
        surface for surface in required_surfaces if surfaces.get(surface) is not True
    ]
    missing_discovery = [
        surface
        for surface in required_surfaces
        if surface not in catalog_names and not discovery_paths.get(f"{surface}_path")
    ]
    return {
        "integration_profile_hash": _declared_hash(integration),
        "discovery_manifest_hash": _declared_hash(discovery),
        "proof_dependency_graph_hash": _declared_hash(proof_graph),
        "integration_status": _artifact_status(integration),
        "discovery_status": _artifact_status(discovery),
        "proof_graph_status": _artifact_status(proof_graph),
        "discovery_highest_level": str(_summary(discovery).get("highest_level", "")),
        "proof_graph_target_level": str(
            _summary(proof_graph).get("target_certification_level", "")
        ),
        "required_public_surfaces": required_surfaces,
        "missing_integration_surfaces": missing_integration,
        "missing_discovery_surfaces": missing_discovery,
        "public_surface_binding_hash": hash_payload(
            {
                "integration_profile_hash": _declared_hash(integration),
                "discovery_manifest_hash": _declared_hash(discovery),
                "proof_dependency_graph_hash": _declared_hash(proof_graph),
                "required_public_surfaces": required_surfaces,
                "missing_integration_surfaces": missing_integration,
                "missing_discovery_surfaces": missing_discovery,
            }
        ),
    }


def make_universal_foundation_model_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a verifiable L132 universal foundation-model RDLLM contract."""

    created_at = created_at or now_iso()
    policy = _policy(contract_input)
    required_families = [str(family) for family in policy["required_provider_families"]]
    artifacts = _artifact_inputs(contract_input)
    artifact_bindings = {
        name: _artifact_binding(name, artifacts.get(name))
        for name in policy["required_chain_artifacts"]
    }
    provider_family_rows = _provider_family_rows(contract_input, required_families)
    selected_route = _selected_route_binding(contract_input)
    public_surface = _public_surface_binding(contract_input, policy)

    settlement = contract_input.get("universal_composition_settlement", {})
    composition = contract_input.get("universal_composition_receipt", {})
    router = contract_input.get("foundation_runtime_router", {})
    conformance = contract_input.get("foundation_provider_conformance", {})
    composite = contract_input.get("composite_foundation_adapter", {})
    proof_graph = contract_input.get("proof_dependency_graph", {})
    discovery = contract_input.get("discovery_manifest", {})

    observed_families = {
        row["provider_family"]
        for row in provider_family_rows
        if row["covered_by_adapter"]
        and row["covered_by_conformance"]
        and row["covered_by_router"]
    }
    selected_families = {
        selected_route["selected_provider_family"],
        selected_route["runtime_adapter_provider_family"],
        selected_route["deployment_provider_family"],
    }

    checks = {
        "required_artifacts_present": all(
            artifact_bindings[name]["present"] for name in policy["required_chain_artifacts"]
        ),
        "artifact_hashes_reproducible": all(
            binding["hash_reproducible"] for binding in artifact_bindings.values()
        ),
        "provider_families_cover_required_set": set(required_families).issubset(
            observed_families
        ),
        "composite_adapter_ready_l125": _artifact_status(composite) == "ready"
        and _level_at_least(_artifact_target_level(composite), "RDLLM-L125"),
        "provider_conformance_ready_l126": _artifact_status(conformance) == "ready"
        and _level_at_least(_artifact_target_level(conformance), "RDLLM-L126"),
        "runtime_router_released_l128": _artifact_status(router) == "released"
        and _level_at_least(_artifact_target_level(router), "RDLLM-L128"),
        "router_covers_all_provider_families": bool(
            _summary(router).get("universal_foundation_routing_supported")
        )
        and int(_summary(router).get("covered_provider_family_count", 0))
        >= len(required_families),
        "fail_closed_router_policy": bool(
            router.get("checks", {}).get("fallback_paths_fail_closed")
        )
        and bool(router.get("checks", {}).get("non_selected_routes_not_released")),
        "selected_route_binds_runtime_and_deployment": len(
            {family for family in selected_families if family}
        )
        == 1
        and all(
            [
                selected_route["runtime_release_authorized"],
                selected_route["router_release_authorized"],
                selected_route["deployment_release_authorized"],
            ]
        ),
        "universal_composition_released_l130": _artifact_status(composition)
        == "released"
        and _level_at_least(_artifact_target_level(composition), "RDLLM-L130"),
        "universal_composition_settlement_ready_l131": _artifact_status(settlement)
        == "ready"
        and _level_at_least(_artifact_target_level(settlement), "RDLLM-L131")
        and bool(_summary(settlement).get("composition_settlement_authorized")),
        "source_footer_to_settlement_bound": bool(
            _summary(settlement).get("source_footer_binding_preserved")
        )
        and bool(_summary(composition).get("source_footer_obligations_preserved")),
        "creator_pool_conserved": str(_summary(settlement).get("settled_total", ""))
        == str(_summary(settlement).get("creator_pool", "")),
        "discovery_profile_and_graph_publish_contract": _artifact_status(
            contract_input.get("integration_profile", {})
        )
        == "ready"
        and _artifact_status(discovery) == "ready"
        and _artifact_status(proof_graph) == "ready"
        and _level_at_least(
            _summary(discovery).get("highest_level", ""), policy["minimum_discovery_level"]
        )
        and _level_at_least(
            _summary(proof_graph).get("target_certification_level", ""),
            policy["minimum_proof_graph_level"],
        ),
        "required_public_surfaces_published": not public_surface[
            "missing_integration_surfaces"
        ]
        and not public_surface["missing_discovery_surfaces"],
        "private_text_not_disclosed": True,
    }
    checks["private_text_not_disclosed"] = (
        not _contains_private_fields(
            {
                "artifact_bindings": artifact_bindings,
                "provider_family_rows": provider_family_rows,
                "selected_route": selected_route,
                "public_surface": public_surface,
            }
        )
    )

    failure_modes_by_check = {
        "required_artifacts_present": "required_artifact_missing",
        "artifact_hashes_reproducible": "artifact_hash_not_reproducible",
        "provider_families_cover_required_set": "provider_family_coverage_failure",
        "composite_adapter_ready_l125": "composite_adapter_not_ready",
        "provider_conformance_ready_l126": "provider_conformance_not_ready",
        "runtime_router_released_l128": "runtime_router_not_released",
        "router_covers_all_provider_families": "router_provider_coverage_failure",
        "fail_closed_router_policy": "fail_closed_policy_missing",
        "selected_route_binds_runtime_and_deployment": "selected_route_not_bound",
        "universal_composition_released_l130": "universal_composition_not_released",
        "universal_composition_settlement_ready_l131": "l131_settlement_not_ready",
        "source_footer_to_settlement_bound": "source_footer_settlement_mismatch",
        "creator_pool_conserved": "creator_pool_not_conserved",
        "discovery_profile_and_graph_publish_contract": "public_contract_not_ready",
        "required_public_surfaces_published": "public_contract_surface_missing",
        "private_text_not_disclosed": "private_text_leak",
    }
    failed_checks = [key for key, passed in checks.items() if not passed]
    failure_modes = [failure_modes_by_check[key] for key in failed_checks]
    contract_ready = not failed_checks

    coverage_gaps = {
        "missing_provider_families": sorted(set(required_families) - observed_families),
        "missing_integration_surfaces": public_surface["missing_integration_surfaces"],
        "missing_discovery_surfaces": public_surface["missing_discovery_surfaces"],
        "failed_checks": failed_checks,
    }
    commitments = {
        "artifact_binding_root": merkle_root(
            [hash_payload(binding) for binding in artifact_bindings.values()]
        ),
        "provider_family_root": merkle_root(
            [
                row["universal_provider_contract_row_hash"]
                for row in provider_family_rows
            ]
        ),
        "public_surface_binding_hash": public_surface["public_surface_binding_hash"],
        "selected_route_binding_hash": hash_payload(selected_route),
        "l131_settlement_hash": _declared_hash(settlement),
    }
    universal_contract_binding = {
        "profile": "rdllm-universal-foundation-model-contract-binding/v1",
        "provider_family_root": commitments["provider_family_root"],
        "artifact_binding_root": commitments["artifact_binding_root"],
        "selected_route_binding_hash": commitments["selected_route_binding_hash"],
        "public_surface_binding_hash": commitments["public_surface_binding_hash"],
        "foundation_provider_conformance_hash": _declared_hash(conformance),
        "foundation_runtime_router_hash": _declared_hash(router),
        "universal_composition_receipt_hash": _declared_hash(composition),
        "universal_composition_settlement_hash": _declared_hash(settlement),
        "discovery_manifest_hash": _declared_hash(discovery),
        "proof_dependency_graph_hash": _declared_hash(proof_graph),
    }
    universal_contract_binding["contract_binding_hash"] = hash_payload(
        universal_contract_binding
    )

    report = {
        "contract_version": UNIVERSAL_FOUNDATION_MODEL_CONTRACT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "contract_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "selected_route_binding": selected_route,
        "public_surface_binding": public_surface,
        "universal_contract_binding": universal_contract_binding,
        "contract_decision": {
            "decision": "release_universal_contract" if contract_ready else "block_universal_contract",
            "release_authorized": contract_ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "emit_only_l132_universal_rdllm_contract"
            if contract_ready
            else "block_foundation_model_release",
        },
        "checks": checks,
        "coverage_gaps": coverage_gaps,
        "commitments": commitments,
        "schemas": {
            "universal_foundation_model_contract": UNIVERSAL_FOUNDATION_MODEL_CONTRACT_SCHEMA,
            "universal_composition_settlement": "docs/schemas/universal_composition_settlement.schema.json",
            "foundation_provider_conformance": "docs/schemas/foundation_provider_conformance.schema.json",
            "foundation_runtime_router": "docs/schemas/foundation_runtime_router.schema.json",
        },
        "privacy": {
            "private_text_fields_excluded": True,
            "hash_only_provider_fixtures": True,
            "raw_prompts_outputs_sources_excluded": True,
            "private_strings_absent": True,
        },
        "summary": {
            "status": "ready" if contract_ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "required_provider_family_count": len(required_families),
            "covered_provider_family_count": len(observed_families & set(required_families)),
            "provider_family_row_count": len(provider_family_rows),
            "selected_provider_family": selected_route["selected_provider_family"],
            "foundation_chain_release_authorized": contract_ready,
            "universal_contract_release_authorized": contract_ready,
            "l131_settlement_hash": _declared_hash(settlement),
            "source_footer_to_settlement_bound": checks[
                "source_footer_to_settlement_bound"
            ],
            "creator_pool_conserved": checks["creator_pool_conserved"],
            "privacy_preserved": True,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
        },
    }
    report["privacy"]["private_strings_absent"] = _private_strings_absent(
        report, contract_input
    )
    report["checks"]["private_text_not_disclosed"] = (
        report["checks"]["private_text_not_disclosed"]
        and report["privacy"]["private_strings_absent"]
    )
    if not report["checks"]["private_text_not_disclosed"]:
        if "private_text_not_disclosed" not in report["contract_decision"]["failed_checks"]:
            report["contract_decision"]["failed_checks"].append(
                "private_text_not_disclosed"
            )
            report["contract_decision"]["failure_modes"].append("private_text_leak")
        report["contract_decision"]["decision"] = "block_universal_contract"
        report["contract_decision"]["release_authorized"] = False
        report["summary"]["status"] = "blocked"
        report["summary"]["foundation_chain_release_authorized"] = False
        report["summary"]["universal_contract_release_authorized"] = False
        report["summary"]["privacy_preserved"] = False
        report["summary"]["failed_check_count"] = len(
            report["contract_decision"]["failed_checks"]
        )
        report["summary"]["failure_mode_count"] = len(
            report["contract_decision"]["failure_modes"]
        )

    report["universal_foundation_model_contract_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = sign_payload(
        report["universal_foundation_model_contract_hash"], signing_secret
    )
    return report


def validate_universal_foundation_model_contract_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = [
        "contract_version",
        "issuer",
        "created_at",
        "contract_policy",
        "artifact_bindings",
        "provider_family_rows",
        "selected_route_binding",
        "public_surface_binding",
        "universal_contract_binding",
        "contract_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_foundation_model_contract_hash",
        "signature",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing universal foundation model contract field: {key}")
    if report.get("contract_version") != UNIVERSAL_FOUNDATION_MODEL_CONTRACT_VERSION:
        errors.append("universal foundation model contract version is unsupported")
    if (
        report.get("schemas", {}).get("universal_foundation_model_contract")
        != UNIVERSAL_FOUNDATION_MODEL_CONTRACT_SCHEMA
    ):
        errors.append("universal foundation model contract schema is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal foundation model contract target level is not RDLLM-L132")
    if not isinstance(report.get("provider_family_rows"), list):
        errors.append("universal foundation model contract provider family rows are not a list")
    if _contains_private_fields(report):
        errors.append("universal foundation model contract exposes private field names")
    return errors


def verify_universal_foundation_model_contract(
    report: dict[str, Any],
    *,
    contract_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L132 universal foundation-model contract by replaying inputs."""

    errors = validate_universal_foundation_model_contract_shape(report)
    declared_hash = report.get("universal_foundation_model_contract_hash")
    if declared_hash != hash_payload(_hashable_report(report)):
        errors.append("universal foundation model contract hash is not reproducible")
    expected = make_universal_foundation_model_contract(
        contract_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    if expected.get("universal_foundation_model_contract_hash") != report.get(
        "universal_foundation_model_contract_hash"
    ):
        errors.append("universal foundation model contract hash does not match inputs")
    if expected.get("contract_decision") != report.get("contract_decision"):
        errors.append("universal foundation model contract decision does not match inputs")
    if expected.get("provider_family_rows") != report.get("provider_family_rows"):
        errors.append("universal foundation model contract provider rows do not match inputs")
    if expected.get("signature") != report.get("signature"):
        errors.append("universal foundation model contract signature is invalid")
    if not _private_strings_absent(report, contract_input):
        errors.append("universal foundation model contract leaks private replay strings")
    return errors
