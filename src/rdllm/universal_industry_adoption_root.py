"""Universal industry adoption root.

The L163 layer is the acyclic closure over the L162 adoption pack. It gives a
foundation-model provider, gateway, regulator, buyer, or creator representative
one final public object to verify before treating an answer route as grounded,
source-footer reliable, and settlement eligible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_INDUSTRY_ADOPTION_ROOT_VERSION = "rdllm-universal-industry-adoption-root/v1"
UNIVERSAL_INDUSTRY_ADOPTION_ROOT_SCHEMA = (
    "docs/schemas/universal_industry_adoption_root.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L163"
MINIMUM_ADOPTION_PACK_LEVEL = "RDLLM-L162"
MINIMUM_TRUST_FEDERATION_LEVEL = "RDLLM-L161"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-industry-adoption-root.json"

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "trust_registry",
    "universal_foundation_provider_adoption_pack",
    "universal_certification_trust_federation",
    "universal_negotiated_invocation_enforcement",
    "response_envelope",
    "source_footer_delivery",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_PUBLICATION_ENDPOINTS = (
    "industry_adoption_root",
    "foundation_provider_adoption_pack",
    "proof_dependency_graph",
    "discovery_manifest",
    "integration_profile",
    "provider_attribution_card",
    "certification_report",
    "certification_attestation",
    "trust_registry",
    "revocation_status",
    "creator_audit_query",
    "regulator_export",
    "sdk_middleware_package",
    "openapi_discovery",
    "mcp_tool_resource_contract",
    "otel_genai_mapping",
    "c2pa_content_credential_assertion",
    "w3c_vc_trust_mark",
    "scitt_transparency_statement",
    "payment_settlement_rail_profile",
)

REQUIRED_ADOPTION_ROLES = (
    "foundation_model_provider",
    "cloud_platform_gateway",
    "enterprise_proxy",
    "open_weight_runtime",
    "agent_runtime",
    "retrieval_connector",
    "mcp_tool_server",
    "payment_settlement_processor",
    "creator_registry",
    "independent_certifier",
    "regulator_observer",
    "downstream_publisher",
)

REQUIRED_NEGATIVE_ROOT_FAILURES = (
    "missing_l162_adoption_pack",
    "stale_proof_dependency_graph",
    "root_not_in_discovery",
    "endpoint_without_verifier",
    "role_without_settlement_hold",
    "provider_route_without_l162",
    "copied_output_without_status_link",
    "creator_audit_route_missing",
    "regulator_export_missing",
    "invalid_trust_chain",
    "settlement_without_l162_root",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_industry_adoption_root_hash",
    "universal_foundation_provider_adoption_pack_hash",
    "universal_certification_trust_federation_hash",
    "universal_negotiated_invocation_enforcement_hash",
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


def load_universal_industry_adoption_root_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L163 industry adoption root."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_root(root: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in root.items()
        if key not in {"universal_industry_adoption_root_hash", "signature"}
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
    public_payload: dict[str, Any], root_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in root_input.get("private_strings", [])
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
    if not artifact:
        return ""
    summary = _summary(artifact)
    certification = artifact.get("certification", {})
    if not isinstance(certification, dict):
        certification = {}
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or certification.get("highest_level")
        or ""
    )


def _level_at_least(level: str, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _is_ready_artifact(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    status = _artifact_status(artifact)
    if status:
        return status in {"ready", "passed", "attested", "ok", "verified"}
    summary = _summary(artifact)
    if summary:
        return not bool(summary.get("failed_check_count", 0))
    return _artifact_hash_is_reproducible(artifact)


def _provider_declares_root(provider_card: dict[str, Any]) -> bool:
    return bool(
        provider_card.get("supported_evidence_channels", {}).get(
            "universal_industry_adoption_root"
        )
        and provider_card.get("public_disclosure_surfaces", {}).get(
            "universal_industry_adoption_root"
        )
    )


def _integration_declares_root(integration_profile: dict[str, Any]) -> bool:
    return bool(
        integration_profile.get("public_surfaces", {}).get(
            "universal_industry_adoption_root"
        )
        and integration_profile.get("schemas", {}).get(
            "universal_industry_adoption_root"
        )
        == UNIVERSAL_INDUSTRY_ADOPTION_ROOT_SCHEMA
    )


def _discovery_declares_root(discovery_manifest: dict[str, Any]) -> bool:
    return bool(
        discovery_manifest.get("discovery", {}).get(
            "universal_industry_adoption_root_path"
        )
        == DEFAULT_WELL_KNOWN_PATH
        and discovery_manifest.get("schemas", {}).get(
            "universal_industry_adoption_root"
        )
        == UNIVERSAL_INDUSTRY_ADOPTION_ROOT_SCHEMA
    )


def _row_map(root_input: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    rows = root_input.get(name, {})
    return rows if isinstance(rows, dict) else {}


def _row_has_hashes(row: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(bool(str(row.get(field, "")).strip()) for field in fields)


def _publication_endpoint_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(
        row,
        (
            "endpoint_hash",
            "schema_hash",
            "status_hash",
            "verifier_command_hash",
            "version_hash",
        ),
    ) and all(
        bool(row.get(field))
        for field in (
            "published",
            "verifier_available",
            "privacy_preserving",
            "revocation_status_available",
        )
    )


def _role_obligation_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(
        row,
        (
            "role_hash",
            "adoption_policy_hash",
            "responsibility_hash",
            "verifier_hash",
            "status_endpoint_hash",
        ),
    ) and all(
        bool(row.get(field))
        for field in (
            "required",
            "blocks_on_failure",
            "settlement_hold_on_failure",
            "audit_visible",
            "public_discovery_safe",
        )
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return _row_has_hashes(row, ("fixture_hash",)) and all(
        bool(row.get(field))
        for field in (
            "expected_reject",
            "observed_reject",
            "root_reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
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


def _artifact_bindings(root_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CORE_ARTIFACTS:
        artifact = root_input.get(name)
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


def _adoption_pack_binds_graph(
    adoption_pack: dict[str, Any] | None,
    proof_graph: dict[str, Any] | None,
) -> bool:
    if not isinstance(adoption_pack, dict) or not isinstance(proof_graph, dict):
        return False
    graph_hash = _declared_hash(proof_graph)
    binding = adoption_pack.get("artifact_bindings", {}).get("proof_dependency_graph", {})
    return bool(graph_hash and binding.get("artifact_hash") == graph_hash)


def make_universal_industry_adoption_root(
    root_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L163 universal industry adoption root."""

    certification_report = root_input.get("certification_report")
    certification_attestation = root_input.get("certification_attestation")
    provider_card = root_input.get("provider_attribution_card")
    integration_profile = root_input.get("integration_profile")
    discovery_manifest = root_input.get("discovery_manifest")
    proof_graph = root_input.get("proof_dependency_graph")
    adoption_pack = root_input.get("universal_foundation_provider_adoption_pack")

    artifact_bindings = _artifact_bindings(root_input)
    publication_endpoint_rows = _row_map(root_input, "publication_endpoint_rows")
    role_obligation_rows = _row_map(root_input, "role_obligation_rows")
    negative_root_rows = _row_map(root_input, "negative_root_rows")

    missing_endpoints, incomplete_endpoints = _complete_rows(
        publication_endpoint_rows,
        REQUIRED_PUBLICATION_ENDPOINTS,
        _publication_endpoint_ready,
    )
    missing_roles, incomplete_roles = _complete_rows(
        role_obligation_rows,
        REQUIRED_ADOPTION_ROLES,
        _role_obligation_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_root_rows,
        REQUIRED_NEGATIVE_ROOT_FAILURES,
        _negative_failure_ready,
    )

    core_artifacts_bound = all(
        binding["present"] and binding["hash_reproducible"]
        for binding in artifact_bindings.values()
    )
    core_artifacts_ready = all(
        _is_ready_artifact(root_input.get(name))
        for name in REQUIRED_CORE_ARTIFACTS
        if name
        not in {
            "response_envelope",
            "source_footer_delivery",
            "revenue_allocation_report",
            "finance_ledger_attestation",
        }
    )
    certification_l162 = _level_at_least(
        str(_summary(certification_report).get("highest_level", "")),
        MINIMUM_ADOPTION_PACK_LEVEL,
    )
    attestation_l162 = _level_at_least(
        str(_summary(certification_attestation).get("attested_highest_level", "")),
        MINIMUM_ADOPTION_PACK_LEVEL,
    )
    provider_l162 = _level_at_least(_artifact_level(provider_card), MINIMUM_ADOPTION_PACK_LEVEL)
    discovery_l162 = _level_at_least(
        _artifact_level(discovery_manifest), MINIMUM_ADOPTION_PACK_LEVEL
    )
    proof_graph_l162_ready = bool(
        isinstance(proof_graph, dict)
        and _summary(proof_graph).get("status") == "ready"
        and _level_at_least(
            str(_summary(proof_graph).get("target_certification_level", "")),
            MINIMUM_ADOPTION_PACK_LEVEL,
        )
    )
    adoption_pack_l162_ready = bool(
        isinstance(adoption_pack, dict)
        and _summary(adoption_pack).get("status") == "ready"
        and _summary(adoption_pack).get("target_certification_level")
        == MINIMUM_ADOPTION_PACK_LEVEL
        and adoption_pack.get("adoption_decision", {}).get(
            "provider_neutral_adoption_ready"
        )
        is True
    )
    adoption_pack_binds_current_graph = _adoption_pack_binds_graph(
        adoption_pack if isinstance(adoption_pack, dict) else None,
        proof_graph if isinstance(proof_graph, dict) else None,
    )
    provider_root_declared = isinstance(provider_card, dict) and _provider_declares_root(
        provider_card
    )
    integration_root_declared = isinstance(
        integration_profile, dict
    ) and _integration_declares_root(integration_profile)
    discovery_root_declared = isinstance(
        discovery_manifest, dict
    ) and _discovery_declares_root(discovery_manifest)

    checks = {
        "core_artifacts_bound": core_artifacts_bound,
        "core_artifacts_ready": core_artifacts_ready,
        "certification_level_at_least_l162": certification_l162,
        "attestation_level_at_least_l162": attestation_l162,
        "provider_card_level_at_least_l162": provider_l162,
        "discovery_manifest_level_at_least_l162": discovery_l162,
        "proof_graph_l162_ready": proof_graph_l162_ready,
        "adoption_pack_l162_ready": adoption_pack_l162_ready,
        "adoption_pack_binds_current_proof_graph": adoption_pack_binds_current_graph,
        "provider_card_declares_industry_root": provider_root_declared,
        "integration_profile_declares_industry_root": integration_root_declared,
        "discovery_manifest_declares_industry_root": discovery_root_declared,
        "all_publication_endpoints_verified": not missing_endpoints
        and not incomplete_endpoints,
        "all_adoption_roles_fail_closed": not missing_roles and not incomplete_roles,
        "negative_root_fixtures_reject": not missing_negative
        and not incomplete_negative,
    }

    failure_modes = [name for name, passed in checks.items() if not passed]
    publication_endpoint_root = merkle_root([
        hash_payload({"name": name, "row": publication_endpoint_rows.get(name, {})})
        for name in REQUIRED_PUBLICATION_ENDPOINTS
    ])
    role_obligation_root = merkle_root([
        hash_payload({"name": name, "row": role_obligation_rows.get(name, {})})
        for name in REQUIRED_ADOPTION_ROLES
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_root_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_ROOT_FAILURES
    ])

    root: dict[str, Any] = {
        "universal_industry_adoption_root_version": (
            UNIVERSAL_INDUSTRY_ADOPTION_ROOT_VERSION
        ),
        "schema": UNIVERSAL_INDUSTRY_ADOPTION_ROOT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-industry-adoption-root-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_adoption_pack_level": MINIMUM_ADOPTION_PACK_LEVEL,
            "minimum_trust_federation_level": MINIMUM_TRUST_FEDERATION_LEVEL,
            "provider_neutral_root_required": True,
            "self_assertion_sufficient": False,
            "two_phase_acyclic_closure_required": True,
            "source_footer_reliance_requires_root": True,
            "creator_settlement_release_requires_root": True,
            "public_endpoint_verifiers_required": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_INDUSTRY_ADOPTION_ROOT_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "publication_endpoint_rows": {
            name: publication_endpoint_rows.get(name, {})
            for name in REQUIRED_PUBLICATION_ENDPOINTS
        },
        "role_obligation_rows": {
            name: role_obligation_rows.get(name, {})
            for name in REQUIRED_ADOPTION_ROLES
        },
        "negative_root_rows": {
            name: negative_root_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_ROOT_FAILURES
        },
        "closure_model": {
            "type": "two_phase_acyclic_root",
            "proof_graph_hash": _declared_hash(proof_graph if isinstance(proof_graph, dict) else None),
            "adoption_pack_hash": _declared_hash(
                adoption_pack if isinstance(adoption_pack, dict) else None
            ),
            "adoption_pack_binds_proof_graph": adoption_pack_binds_current_graph,
            "root_binds_adoption_pack": True,
            "root_binds_publication_endpoints": True,
            "root_binds_role_obligations": True,
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root([
                hash_payload({"name": name, "binding": binding})
                for name, binding in artifact_bindings.items()
            ]),
            "publication_endpoint_root": publication_endpoint_root,
            "role_obligation_root": role_obligation_root,
            "negative_root": negative_root,
        },
        "adoption_decision": {
            "industry_adoption_root_ready": not failure_modes,
            "provider_self_assertion_sufficient": False,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_release_allowed": not failure_modes,
            "failure_modes": failure_modes,
            "missing_publication_endpoints": missing_endpoints,
            "incomplete_publication_endpoints": incomplete_endpoints,
            "missing_adoption_roles": missing_roles,
            "incomplete_adoption_roles": incomplete_roles,
            "missing_negative_root_failures": missing_negative,
            "incomplete_negative_root_failures": incomplete_negative,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payloads_disclosed": False,
            "tool_payloads_disclosed": False,
            "payment_account_details_disclosed": False,
            "public_root_uses_hashes_status_rows_and_verifier_commands": True,
        },
    }
    checks["private_fields_absent"] = not _contains_private_fields(root)
    checks["private_strings_absent"] = _private_strings_absent(root, root_input)
    root["checks"] = checks
    if not checks["private_fields_absent"] or not checks["private_strings_absent"]:
        root["adoption_decision"]["industry_adoption_root_ready"] = False
        for check in ("private_fields_absent", "private_strings_absent"):
            if not checks[check] and check not in root["adoption_decision"]["failure_modes"]:
                root["adoption_decision"]["failure_modes"].append(check)

    root["summary"] = {
        "status": "ready"
        if root["adoption_decision"]["industry_adoption_root_ready"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_adoption_pack_level": MINIMUM_ADOPTION_PACK_LEVEL,
        "minimum_trust_federation_level": MINIMUM_TRUST_FEDERATION_LEVEL,
        "core_artifact_count": len(REQUIRED_CORE_ARTIFACTS),
        "bound_core_artifact_count": sum(
            1
            for binding in artifact_bindings.values()
            if binding["present"] and binding["hash_reproducible"]
        ),
        "publication_endpoint_count": len(REQUIRED_PUBLICATION_ENDPOINTS),
        "ready_publication_endpoint_count": len(REQUIRED_PUBLICATION_ENDPOINTS)
        - len(missing_endpoints)
        - len(incomplete_endpoints),
        "adoption_role_count": len(REQUIRED_ADOPTION_ROLES),
        "ready_adoption_role_count": len(REQUIRED_ADOPTION_ROLES)
        - len(missing_roles)
        - len(incomplete_roles),
        "negative_root_failure_count": len(REQUIRED_NEGATIVE_ROOT_FAILURES),
        "ready_negative_root_failure_count": len(REQUIRED_NEGATIVE_ROOT_FAILURES)
        - len(missing_negative)
        - len(incomplete_negative),
        "failure_mode_count": len(root["adoption_decision"]["failure_modes"]),
        "two_phase_acyclic_closure": True,
        "provider_neutral_root_supported": True,
        "source_footer_reliance_allowed": root["adoption_decision"][
            "source_footer_reliance_allowed"
        ],
        "creator_settlement_release_allowed": root["adoption_decision"][
            "creator_settlement_release_allowed"
        ],
        "privacy_preserved": checks["private_fields_absent"]
        and checks["private_strings_absent"],
    }
    root["universal_industry_adoption_root_hash"] = hash_payload(_hashable_root(root))
    root["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(root["universal_industry_adoption_root_hash"], signing_secret)
            if signing_secret
            else ""
        ),
    }
    return root


def validate_universal_industry_adoption_root_shape(root: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L163 industry adoption root."""

    errors: list[str] = []
    if (
        root.get("universal_industry_adoption_root_version")
        != UNIVERSAL_INDUSTRY_ADOPTION_ROOT_VERSION
    ):
        errors.append("universal industry adoption root version is unsupported")
    if root.get("schema") != UNIVERSAL_INDUSTRY_ADOPTION_ROOT_SCHEMA:
        errors.append("universal industry adoption root schema is unsupported")
    if root.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal industry adoption root target level is not RDLLM-L163")
    if root.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal industry adoption root well-known path is invalid")
    for section in (
        "artifact_bindings",
        "publication_endpoint_rows",
        "role_obligation_rows",
        "negative_root_rows",
        "closure_model",
        "evidence_roots",
        "adoption_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if not isinstance(root.get(section), dict):
            errors.append(f"universal industry adoption root missing {section}")
    for endpoint in REQUIRED_PUBLICATION_ENDPOINTS:
        if endpoint not in root.get("publication_endpoint_rows", {}):
            errors.append(f"universal industry adoption root missing endpoint {endpoint}")
    for role in REQUIRED_ADOPTION_ROLES:
        if role not in root.get("role_obligation_rows", {}):
            errors.append(f"universal industry adoption root missing role {role}")
    for failure in REQUIRED_NEGATIVE_ROOT_FAILURES:
        if failure not in root.get("negative_root_rows", {}):
            errors.append(f"universal industry adoption root missing negative failure {failure}")
    if root.get("adoption_decision", {}).get("provider_self_assertion_sufficient"):
        errors.append("universal industry adoption root permits self assertion")
    if _contains_private_fields(root):
        errors.append("universal industry adoption root exposes a private field")
    return errors


def verify_universal_industry_adoption_root(
    root: dict[str, Any],
    *,
    root_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify an L163 industry adoption root."""

    errors = validate_universal_industry_adoption_root_shape(root)
    expected_hash = hash_payload(_hashable_root(root))
    if expected_hash != root.get("universal_industry_adoption_root_hash"):
        errors.append("universal industry adoption root hash is not reproducible")

    expected = make_universal_industry_adoption_root(
        root_input,
        issuer=str(root.get("issuer", DEFAULT_ISSUER)),
        created_at=str(root.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "artifact_bindings",
        "publication_endpoint_rows",
        "role_obligation_rows",
        "negative_root_rows",
        "closure_model",
        "evidence_roots",
        "adoption_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if root.get(key) != expected.get(key):
            errors.append(f"universal industry adoption root {key} does not match replay input")
    if root.get("universal_industry_adoption_root_hash") != expected.get(
        "universal_industry_adoption_root_hash"
    ):
        errors.append("universal industry adoption root hash does not match replay input")
    if root.get("signature") != expected.get("signature"):
        errors.append("universal industry adoption root signature is invalid")
    if root.get("summary", {}).get("status") != "ready":
        errors.append("universal industry adoption root status is not ready")
    for check, passed in root.get("checks", {}).items():
        if not passed:
            errors.append(f"universal industry adoption root check failed: {check}")
    if _contains_private_fields(root):
        errors.append("universal industry adoption root exposes a private field")
    if not _private_strings_absent(root, root_input):
        errors.append("universal industry adoption root exposes private input text")
    return errors
