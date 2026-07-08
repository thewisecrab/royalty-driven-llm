"""Universal source-footer enforcement contracts.

The L177 layer binds the dynamic L176 model/provider registry to the L171
source-grounded response receipt. A route cannot claim universal RDLLM support
unless every declared model route enforces source discovery, source verification,
claim support, visible footer rendering, no-source abstention, copy/export
preservation, and settlement hold rules before a response is released.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.transparency import merkle_root

UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_VERSION = (
    "rdllm-universal-source-footer-enforcement-contract/v1"
)
UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_SCHEMA = (
    "docs/schemas/universal_source_footer_enforcement_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L177"
MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL = "RDLLM-L176"
MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL = "RDLLM-L171"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-source-footer-enforcement-contract.json"
)

REQUIRED_ENFORCEMENT_STAGES = (
    "source_discovery",
    "retrieval_trace_capture",
    "claim_decomposition",
    "evidence_span_binding",
    "source_identity_resolution",
    "citation_metadata_verification",
    "claim_support_scoring",
    "counterevidence_scan",
    "no_source_abstention",
    "footer_rendering",
    "copy_export_preservation",
    "settlement_hold_binding",
)

REQUIRED_SOURCE_TYPES = (
    "retrieval_document",
    "web_source",
    "tool_observation",
    "licensed_corpus_work",
    "creator_work",
    "code_repository",
    "media_asset",
    "conversation_memory",
    "persistent_memory",
    "parametric_memory",
    "post_training_signal",
    "no_source_abstention",
)

REQUIRED_FOOTER_ROW_FIELDS = (
    "source_label",
    "source_title",
    "creator_or_publisher",
    "source_uri_or_locator",
    "source_type",
    "evidence_span_hash",
    "claim_hashes",
    "retrieval_or_memory_trace_hash",
    "confidence_label",
    "freshness_timestamp_hash",
    "license_or_rights_status_hash",
    "attribution_reason",
    "settlement_state",
)

REQUIRED_RESPONSE_SURFACES = (
    "api_json",
    "markdown_footer",
    "html_footer",
    "streaming_final",
    "tool_result",
    "batch_output",
    "copy_export",
    "content_credential",
)

REQUIRED_NEGATIVE_FOOTER_FAILURES = (
    "missing_l176_registry",
    "missing_l171_response_receipt",
    "route_without_footer_gate",
    "source_discovered_not_displayed",
    "claim_without_footer_row",
    "right_answer_wrong_source",
    "fabricated_citation",
    "unavailable_source_locator",
    "citation_metadata_mismatch",
    "retrieval_trace_not_bound",
    "parametric_claim_without_disclosure",
    "low_confidence_source_not_labelled",
    "counterevidence_ignored",
    "no_source_abstention_missing",
    "streaming_final_strips_footer",
    "copy_export_strips_footer",
    "settlement_released_without_footer",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_source_footer_enforcement_contract_hash",
    "universal_model_provider_registry_hash",
    "universal_source_grounded_response_receipt_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_live_attribution_proof_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "citation_reliance_receipt_hash",
    "citation_url_health_hash",
    "source_confidence_hash",
    "source_availability_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "model_route_hash",
    "model_identity_hash",
    "route_enforcement_hash",
    "footer_enforcement_hash",
    "footer_renderer_hash",
    "footer_field_hash",
    "source_type_hash",
    "source_identity_hash",
    "source_verifier_hash",
    "evidence_span_hash",
    "claim_hash",
    "retrieval_trace_hash",
    "memory_trace_hash",
    "answer_release_gate_hash",
    "no_source_abstention_hash",
    "settlement_hold_hash",
    "telemetry_span_hash",
    "conformance_verifier_hash",
    "fixture_hash",
    "verifier_hash",
    "schema_hash",
    "policy_hash",
    "report_hash",
    "receipt_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "answer_text",
    "raw_answer_text",
    "output",
    "output_text",
    "raw_output",
    "raw_model_output",
    "claim_text",
    "sentence_text",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "retrieval_payload",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "streaming_transcript",
    "customer_id",
    "customer_email",
    "tenant_id",
    "billing_record",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "authorization",
    "access_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_source_footer_enforcement_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L177 source-footer enforcement contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_source_footer_enforcement_contract_hash", "signature"}
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
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _model_provider_registry_ready(registry: dict[str, Any] | None) -> bool:
    if not isinstance(registry, dict):
        return False
    summary = _summary(registry)
    decision = registry.get("registry_decision", {})
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
        and isinstance(decision, dict)
        and decision.get("universal_model_provider_registry_ready") is True
        and decision.get("source_footer_required_for_all_routes") is True
        and decision.get("unregistered_routes_blocked") is True
    )


def _source_grounded_response_ready(receipt: dict[str, Any] | None) -> bool:
    if not isinstance(receipt, dict):
        return False
    summary = _summary(receipt)
    decision = receipt.get("response_release_decision", {})
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
        and isinstance(decision, dict)
        and decision.get("source_grounded_response_ready") is True
        and decision.get("final_answer_release_allowed") is True
        and decision.get("user_footer_display_allowed") is True
        and decision.get("source_reliance_allowed") is True
        and decision.get("citation_reliance_allowed") is True
    )


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _bool(value: Any) -> bool:
    return value is True


def _row_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(key, {})
    if not isinstance(rows, dict):
        return {}
    return {
        str(name): row
        for name, row in rows.items()
        if isinstance(row, dict)
    }


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate: Callable[[dict[str, Any]], bool],
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [name for name in required if name in rows and not predicate(rows[name])]
    return missing, incomplete


def _stage_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("stage_hash")),
            _string(row.get("policy_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("enabled")),
            _bool(row.get("telemetry_bound")),
            _bool(row.get("auditable")),
            _bool(row.get("fail_closed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _source_type_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("source_type_hash")),
            _string(row.get("identity_resolver_hash")),
            _string(row.get("locator_verifier_hash")),
            _string(row.get("rights_policy_hash")),
            _string(row.get("confidence_policy_hash")),
            _bool(row.get("discoverable")),
            _bool(row.get("citable_or_abstainable")),
            _bool(row.get("visible_footer_allowed")),
            _bool(row.get("machine_readable_source_allowed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _footer_field_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("footer_field_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("render_verifier_hash")),
            _bool(row.get("field_required")),
            _bool(row.get("rendered_when_applicable")),
            _bool(row.get("machine_readable")),
            _bool(row.get("privacy_safe")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _surface_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("surface_hash")),
            _string(row.get("footer_renderer_hash")),
            _string(row.get("verifier_hash")),
            _string(row.get("copy_export_hash")),
            _bool(row.get("footer_visible")),
            _bool(row.get("machine_readable_sources_visible")),
            _bool(row.get("final_response_gate_enabled")),
            _bool(row.get("copy_export_preserves_footer")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _route_enforcement_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "provider_namespace",
        "model_route_class",
        "model_identity_hash",
        "registry_route_hash",
        "route_enforcement_hash",
        "source_grounded_response_receipt_hash",
        "answer_release_gate_hash",
        "footer_renderer_hash",
        "source_verifier_hash",
        "no_source_abstention_hash",
        "settlement_hold_hash",
        "telemetry_span_hash",
        "conformance_verifier_hash",
    )
    required_bools = (
        "route_registered_l176",
        "source_grounded_response_l171_bound",
        "answer_release_gate_enabled",
        "footer_injection_enabled",
        "machine_readable_sources_emitted",
        "claim_source_support_required",
        "unsupported_claims_refused",
        "posthoc_citations_rejected",
        "no_source_abstention_enabled",
        "copy_export_preserves_sources",
        "settlement_hold_enforced",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("answer_release_blocked")),
            _bool(row.get("footer_reliance_blocked")),
            _bool(row.get("source_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _registry_routes(registry: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(registry, dict):
        return []
    rows = registry.get("declared_model_routes", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _route_id(row: dict[str, Any], fallback: str) -> str:
    return _string(row.get("route_id")) or fallback


def _route_enforcement_coverage(
    registry_routes: list[dict[str, Any]],
    enforcement_rows: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    expected_route_ids = [
        _route_id(row, f"route:{index}") for index, row in enumerate(registry_routes)
    ]
    expected = set(expected_route_ids)
    observed = set(enforcement_rows)
    missing = sorted(expected - observed)
    orphan = sorted(observed - expected)
    incomplete = sorted(
        route_id
        for route_id in expected & observed
        if not _route_enforcement_ready(enforcement_rows[route_id])
    )
    mismatched = []
    registry_by_id = {
        _route_id(row, f"route:{index}"): row
        for index, row in enumerate(registry_routes)
    }
    for route_id in expected & observed:
        registry_row = registry_by_id.get(route_id, {})
        enforcement = enforcement_rows.get(route_id, {})
        if (
            enforcement.get("provider_namespace")
            != registry_row.get("provider_namespace")
            or enforcement.get("model_route_class")
            != registry_row.get("model_route_class")
            or enforcement.get("model_identity_hash")
            != registry_row.get("model_identity_hash")
        ):
            mismatched.append(route_id)
    return missing, incomplete, orphan, sorted(mismatched)


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            if key_str in PRIVATE_FIELD_NAMES:
                found.append(next_path)
            found.extend(_contains_private_fields(nested, next_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_contains_private_fields(nested, f"{path}[{index}]"))
    return found


def _private_strings_absent(public: Any, private_input: dict[str, Any]) -> bool:
    private_strings = private_input.get("private_strings", [])
    if not isinstance(private_strings, list):
        return True
    rendered = canonical_json(public)
    return all(
        not isinstance(value, str) or not value or value not in rendered
        for value in private_strings
    )


def _public_route_rows(
    route_rows: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    public: dict[str, dict[str, Any]] = {}
    for route_id in sorted(route_rows):
        row = route_rows[route_id]
        public[route_id] = {
            "route_id": _string(row.get("route_id")) or route_id,
            "provider_namespace": _string(row.get("provider_namespace")),
            "model_route_class": _string(row.get("model_route_class")),
            "model_identity_hash": _string(row.get("model_identity_hash")),
            "registry_route_hash": _string(row.get("registry_route_hash")),
            "route_enforcement_hash": _string(row.get("route_enforcement_hash")),
            "source_grounded_response_receipt_hash": _string(
                row.get("source_grounded_response_receipt_hash")
            ),
            "answer_release_gate_hash": _string(row.get("answer_release_gate_hash")),
            "footer_renderer_hash": _string(row.get("footer_renderer_hash")),
            "source_verifier_hash": _string(row.get("source_verifier_hash")),
            "no_source_abstention_hash": _string(
                row.get("no_source_abstention_hash")
            ),
            "settlement_hold_hash": _string(row.get("settlement_hold_hash")),
            "telemetry_span_hash": _string(row.get("telemetry_span_hash")),
            "conformance_verifier_hash": _string(
                row.get("conformance_verifier_hash")
            ),
            "route_registered_l176": _bool(row.get("route_registered_l176")),
            "source_grounded_response_l171_bound": _bool(
                row.get("source_grounded_response_l171_bound")
            ),
            "answer_release_gate_enabled": _bool(
                row.get("answer_release_gate_enabled")
            ),
            "footer_injection_enabled": _bool(row.get("footer_injection_enabled")),
            "machine_readable_sources_emitted": _bool(
                row.get("machine_readable_sources_emitted")
            ),
            "claim_source_support_required": _bool(
                row.get("claim_source_support_required")
            ),
            "unsupported_claims_refused": _bool(row.get("unsupported_claims_refused")),
            "posthoc_citations_rejected": _bool(row.get("posthoc_citations_rejected")),
            "no_source_abstention_enabled": _bool(
                row.get("no_source_abstention_enabled")
            ),
            "copy_export_preserves_sources": _bool(
                row.get("copy_export_preserves_sources")
            ),
            "settlement_hold_enforced": _bool(row.get("settlement_hold_enforced")),
            "no_private_payloads": _bool(row.get("no_private_payloads")),
        }
    return public


def make_universal_source_footer_enforcement_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L177 contract proving source footers are enforced for all routes."""

    registry = contract_input.get("universal_model_provider_registry")
    response_receipt = contract_input.get("universal_source_grounded_response_receipt")
    stage_rows = _row_map(contract_input, "enforcement_stage_rows")
    source_type_rows = _row_map(contract_input, "source_type_rows")
    footer_field_rows = _row_map(contract_input, "footer_row_field_rows")
    surface_rows = _row_map(contract_input, "response_surface_rows")
    route_rows = _row_map(contract_input, "route_enforcement_rows")
    negative_rows = _row_map(contract_input, "negative_footer_rows")
    declared_routes = _registry_routes(registry if isinstance(registry, dict) else None)

    missing_stages, incomplete_stages = _complete_rows(
        stage_rows,
        REQUIRED_ENFORCEMENT_STAGES,
        _stage_row_ready,
    )
    missing_source_types, incomplete_source_types = _complete_rows(
        source_type_rows,
        REQUIRED_SOURCE_TYPES,
        _source_type_row_ready,
    )
    missing_footer_fields, incomplete_footer_fields = _complete_rows(
        footer_field_rows,
        REQUIRED_FOOTER_ROW_FIELDS,
        _footer_field_row_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_RESPONSE_SURFACES,
        _surface_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_FOOTER_FAILURES,
        _negative_row_ready,
    )
    (
        missing_route_enforcements,
        incomplete_route_enforcements,
        orphan_route_enforcements,
        mismatched_route_enforcements,
    ) = _route_enforcement_coverage(declared_routes, route_rows)

    checks = {
        "model_provider_registry_bound": _artifact_hash_is_reproducible(
            registry if isinstance(registry, dict) else None
        ),
        "model_provider_registry_l176_ready": _model_provider_registry_ready(
            registry if isinstance(registry, dict) else None
        ),
        "source_grounded_response_receipt_bound": _artifact_hash_is_reproducible(
            response_receipt if isinstance(response_receipt, dict) else None
        ),
        "source_grounded_response_receipt_l171_ready": (
            _source_grounded_response_ready(
                response_receipt if isinstance(response_receipt, dict) else None
            )
        ),
        "enforcement_stage_rows_complete": not missing_stages
        and not incomplete_stages,
        "source_type_rows_complete": not missing_source_types
        and not incomplete_source_types,
        "footer_row_field_rows_complete": not missing_footer_fields
        and not incomplete_footer_fields,
        "response_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "all_registry_routes_have_footer_enforcement": bool(declared_routes)
        and not missing_route_enforcements
        and not incomplete_route_enforcements
        and not orphan_route_enforcements
        and not mismatched_route_enforcements,
        "negative_footer_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    stage_root = merkle_root([
        hash_payload({"name": name, "row": stage_rows.get(name, {})})
        for name in REQUIRED_ENFORCEMENT_STAGES
    ])
    source_type_root = merkle_root([
        hash_payload({"name": name, "row": source_type_rows.get(name, {})})
        for name in REQUIRED_SOURCE_TYPES
    ])
    footer_field_root = merkle_root([
        hash_payload({"name": name, "row": footer_field_rows.get(name, {})})
        for name in REQUIRED_FOOTER_ROW_FIELDS
    ])
    surface_root = merkle_root([
        hash_payload({"name": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_RESPONSE_SURFACES
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_rows.get(route_id, {})})
        for route_id in sorted({_route_id(row, f"route:{i}") for i, row in enumerate(declared_routes)})
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_FOOTER_FAILURES
    ])

    public = {
        "universal_source_footer_enforcement_contract_version": (
            UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-source-footer-enforcement-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "source_payment_is_not_substitute_for_visible_attribution": True,
            "source_footer_required_before_response_release": True,
            "claim_support_required_before_footer_row": True,
            "posthoc_citations_forbidden": True,
            "no_source_abstention_required": True,
            "machine_readable_sources_required": True,
            "private_payloads_forbidden_in_public_contract": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_VERSION,
        },
        "model_provider_registry_binding": {
            "present": isinstance(registry, dict),
            "artifact_hash": _declared_hash(registry if isinstance(registry, dict) else None),
            "payload_hash": hash_payload(
                _hashable_artifact(registry if isinstance(registry, dict) else None)
            ),
            "hash_reproducible": checks["model_provider_registry_bound"],
            "status": _summary(registry if isinstance(registry, dict) else None).get(
                "status", ""
            ),
            "level": _summary(registry if isinstance(registry, dict) else None).get(
                "target_certification_level", ""
            ),
            "declared_model_route_count": len(declared_routes),
        },
        "source_grounded_response_binding": {
            "present": isinstance(response_receipt, dict),
            "artifact_hash": _declared_hash(
                response_receipt if isinstance(response_receipt, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    response_receipt if isinstance(response_receipt, dict) else None
                )
            ),
            "hash_reproducible": checks["source_grounded_response_receipt_bound"],
            "status": _summary(
                response_receipt if isinstance(response_receipt, dict) else None
            ).get("status", ""),
            "level": _summary(
                response_receipt if isinstance(response_receipt, dict) else None
            ).get("target_certification_level", ""),
        },
        "enforcement_stage_rows": {
            name: stage_rows.get(name, {}) for name in REQUIRED_ENFORCEMENT_STAGES
        },
        "source_type_rows": {
            name: source_type_rows.get(name, {}) for name in REQUIRED_SOURCE_TYPES
        },
        "footer_row_field_rows": {
            name: footer_field_rows.get(name, {})
            for name in REQUIRED_FOOTER_ROW_FIELDS
        },
        "response_surface_rows": {
            name: surface_rows.get(name, {}) for name in REQUIRED_RESPONSE_SURFACES
        },
        "route_enforcement_rows": _public_route_rows(route_rows),
        "negative_footer_rows": {
            name: negative_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_FOOTER_FAILURES
        },
        "evidence_roots": {
            "enforcement_stage_root": stage_root,
            "source_type_root": source_type_root,
            "footer_row_field_root": footer_field_root,
            "response_surface_root": surface_root,
            "route_enforcement_root": route_root,
            "negative_footer_root": negative_root,
            "combined_footer_enforcement_root": merkle_root(
                [
                    stage_root,
                    source_type_root,
                    footer_field_root,
                    surface_root,
                    route_root,
                    negative_root,
                ]
            ),
        },
        "checks": checks,
        "footer_enforcement_decision": {
            "universal_source_footer_enforcement_ready": ready,
            "final_answer_release_allowed": ready,
            "visible_source_footer_required": True,
            "user_confidence_footer_allowed": ready,
            "machine_readable_sources_required": True,
            "unsupported_claims_blocked": ready,
            "posthoc_citations_blocked": True,
            "no_source_abstention_required": True,
            "copy_export_allowed": ready,
            "creator_settlement_allowed": ready,
            "source_payment_without_attribution_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "missing_enforcement_stages": missing_stages,
            "incomplete_enforcement_stages": incomplete_stages,
            "missing_source_types": missing_source_types,
            "incomplete_source_types": incomplete_source_types,
            "missing_footer_row_fields": missing_footer_fields,
            "incomplete_footer_row_fields": incomplete_footer_fields,
            "missing_response_surfaces": missing_surfaces,
            "incomplete_response_surfaces": incomplete_surfaces,
            "missing_route_enforcements": missing_route_enforcements,
            "incomplete_route_enforcements": incomplete_route_enforcements,
            "orphan_route_enforcements": orphan_route_enforcements,
            "mismatched_route_enforcements": mismatched_route_enforcements,
            "missing_negative_footer_failures": missing_negative,
            "incomplete_negative_footer_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_source_text_excluded": True,
            "public_contract_uses_hashes_locators_and_labels": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "enforcement_stage_count": len(REQUIRED_ENFORCEMENT_STAGES),
            "ready_enforcement_stage_count": len(REQUIRED_ENFORCEMENT_STAGES)
            - len(missing_stages)
            - len(incomplete_stages),
            "source_type_count": len(REQUIRED_SOURCE_TYPES),
            "ready_source_type_count": len(REQUIRED_SOURCE_TYPES)
            - len(missing_source_types)
            - len(incomplete_source_types),
            "footer_row_field_count": len(REQUIRED_FOOTER_ROW_FIELDS),
            "ready_footer_row_field_count": len(REQUIRED_FOOTER_ROW_FIELDS)
            - len(missing_footer_fields)
            - len(incomplete_footer_fields),
            "response_surface_count": len(REQUIRED_RESPONSE_SURFACES),
            "ready_response_surface_count": len(REQUIRED_RESPONSE_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "declared_model_route_count": len(declared_routes),
            "ready_route_enforcement_count": len(declared_routes)
            - len(missing_route_enforcements)
            - len(incomplete_route_enforcements)
            - len(mismatched_route_enforcements),
            "negative_footer_failure_count": len(REQUIRED_NEGATIVE_FOOTER_FAILURES),
            "ready_negative_footer_failure_count": (
                len(REQUIRED_NEGATIVE_FOOTER_FAILURES)
                - len(missing_negative)
                - len(incomplete_negative)
            ),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_source_footer_enforcement_contract": signing_secret is not None,
        },
    }

    private_fields = _contains_private_fields(public)
    private_strings_absent = _private_strings_absent(public, contract_input)
    public["privacy"]["private_payloads_excluded"] = (
        not private_fields and private_strings_absent
    )
    public["privacy"]["private_payload_fields"] = private_fields
    public["privacy"]["private_strings_absent"] = private_strings_absent
    if not public["privacy"]["private_payloads_excluded"]:
        if "private_payloads_excluded" not in public["footer_enforcement_decision"][
            "failure_modes"
        ]:
            public["footer_enforcement_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["footer_enforcement_decision"][
            "universal_source_footer_enforcement_ready"
        ] = False
        public["footer_enforcement_decision"]["final_answer_release_allowed"] = False
        public["footer_enforcement_decision"]["user_confidence_footer_allowed"] = False
        public["footer_enforcement_decision"]["copy_export_allowed"] = False
        public["footer_enforcement_decision"]["creator_settlement_allowed"] = False
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["footer_enforcement_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_source_footer_enforcement_contract_hash"] = hash_payload(
        _hashable_contract(public)
    )
    public["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_contract(public), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return public


def validate_universal_source_footer_enforcement_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L177 footer enforcement contract."""

    errors: list[str] = []
    required = (
        "universal_source_footer_enforcement_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "model_provider_registry_binding",
        "source_grounded_response_binding",
        "enforcement_stage_rows",
        "source_type_rows",
        "footer_row_field_rows",
        "response_surface_rows",
        "route_enforcement_rows",
        "negative_footer_rows",
        "evidence_roots",
        "checks",
        "footer_enforcement_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_source_footer_enforcement_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing source footer enforcement field: {key}")
    if contract.get("universal_source_footer_enforcement_contract_version") != (
        UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_source_footer_enforcement_contract_version")
    if contract.get("schema") != UNIVERSAL_SOURCE_FOOTER_ENFORCEMENT_CONTRACT_SCHEMA:
        errors.append("unexpected source footer enforcement schema")
    for name in REQUIRED_ENFORCEMENT_STAGES:
        if name not in contract.get("enforcement_stage_rows", {}):
            errors.append(f"missing enforcement stage row: {name}")
    for name in REQUIRED_SOURCE_TYPES:
        if name not in contract.get("source_type_rows", {}):
            errors.append(f"missing source type row: {name}")
    for name in REQUIRED_FOOTER_ROW_FIELDS:
        if name not in contract.get("footer_row_field_rows", {}):
            errors.append(f"missing footer row field row: {name}")
    for name in REQUIRED_RESPONSE_SURFACES:
        if name not in contract.get("response_surface_rows", {}):
            errors.append(f"missing response surface row: {name}")
    for name in REQUIRED_NEGATIVE_FOOTER_FAILURES:
        if name not in contract.get("negative_footer_rows", {}):
            errors.append(f"missing negative footer row: {name}")
    for check in (
        "model_provider_registry_bound",
        "model_provider_registry_l176_ready",
        "source_grounded_response_receipt_bound",
        "source_grounded_response_receipt_l171_ready",
        "enforcement_stage_rows_complete",
        "source_type_rows_complete",
        "footer_row_field_rows_complete",
        "response_surface_rows_complete",
        "all_registry_routes_have_footer_enforcement",
        "negative_footer_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing source footer enforcement check: {check}")
    return errors


def verify_universal_source_footer_enforcement_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L177 footer enforcement contract against replay input."""

    errors = validate_universal_source_footer_enforcement_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_source_footer_enforcement_contract_hash") != expected_hash:
        errors.append("universal_source_footer_enforcement_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "source footer enforcement contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("source footer enforcement contract exposes private input strings")
    replayed = make_universal_source_footer_enforcement_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_source_footer_enforcement_contract_hash") != contract.get(
        "universal_source_footer_enforcement_contract_hash"
    ):
        errors.append("source footer enforcement contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("source footer enforcement contract is not ready")
    if (
        contract.get("footer_enforcement_decision", {}).get(
            "universal_source_footer_enforcement_ready"
        )
        is not True
    ):
        errors.append("source footer enforcement decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("source footer enforcement privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("source footer enforcement contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source footer enforcement contract signature is invalid")
    return errors
