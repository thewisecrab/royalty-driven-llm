"""Universal verified source-footer reliance contracts.

The L180 layer turns user-facing source footers into a live-route reliance
contract. Earlier layers prove source-grounded responses, footer enforcement,
citation verification, and runtime route binding. L180 requires the exact
footer a user sees to bind all of those proofs before a response, copied output,
or settlement record may imply that the answer is grounded in its displayed
sources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_VERSION = (
    "rdllm-universal-verified-source-footer-contract/v1"
)
UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_SCHEMA = (
    "docs/schemas/universal_verified_source_footer_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L180"
MINIMUM_CITATION_VERIFICATION_LEVEL = "RDLLM-L141"
MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL = "RDLLM-L171"
MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL = "RDLLM-L177"
MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL = "RDLLM-L179"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-verified-source-footer-contract.json"
)

REQUIRED_FOOTER_VERIFICATION_STAGES = (
    "source_materialization",
    "locator_health_check",
    "metadata_fidelity_check",
    "claim_decomposition",
    "claim_source_alignment",
    "factual_support_check",
    "relevance_check",
    "evidence_utility_check",
    "citation_rendering_check",
    "copy_export_preservation",
    "attribution_omission_scan",
    "post_release_replay",
)

REQUIRED_VERIFIED_FOOTER_FIELDS = (
    "source_label",
    "source_title",
    "creator_or_publisher",
    "source_uri_or_locator",
    "source_type",
    "source_content_hash",
    "evidence_span_hash",
    "claim_hashes",
    "link_health_status",
    "relevance_score",
    "factual_support_score",
    "confidence_label",
    "attribution_reason",
    "license_or_rights_status",
    "settlement_state",
)

REQUIRED_FOOTER_RESPONSE_SURFACES = (
    "api_json",
    "markdown_footer",
    "html_footer",
    "streaming_final",
    "tool_result",
    "batch_output",
    "copy_export",
    "content_credential",
    "research_report_markdown",
    "auditor_export",
)

REQUIRED_SUPPORT_DIMENSIONS = (
    "link_works",
    "source_materialized",
    "metadata_matches_source",
    "relevant_content",
    "factual_support",
    "claim_span_matches_footer",
    "runtime_route_matches_footer",
    "footer_visible_and_preserved",
)

REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES = (
    "link_works_but_fact_not_supported",
    "relevant_source_wrong_claim",
    "fabricated_citation_identifier",
    "metadata_drift",
    "inaccessible_or_never_seen_locator",
    "cited_source_not_materialized",
    "answer_claim_no_footer_source",
    "source_used_but_omitted_from_footer",
    "footer_added_posthoc",
    "no_source_abstention_missing",
    "low_confidence_source_hidden",
    "copy_export_strips_footer",
    "streaming_final_strips_footer",
    "runtime_route_footer_mismatch",
    "settlement_without_verified_footer",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_verified_source_footer_contract_hash",
    "universal_runtime_route_binding_contract_hash",
    "universal_source_footer_enforcement_contract_hash",
    "universal_source_grounded_response_receipt_hash",
    "universal_citation_verification_contract_hash",
    "deep_research_citation_audit_hash",
    "citation_url_health_hash",
    "source_availability_report_hash",
    "source_confidence_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "citation_footer_contract_hash",
    "rendered_attribution_audit_hash",
    "evidence_utility_attribution_hash",
    "footer_row_hash",
    "claim_row_hash",
    "source_row_hash",
    "surface_hash",
    "stage_hash",
    "dimension_hash",
    "fixture_hash",
    "verifier_hash",
    "report_hash",
    "receipt_hash",
    "contract_hash",
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
    "output_text",
    "raw_output",
    "raw_model_output",
    "rendered_output",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "claim_text",
    "raw_claim",
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
    "api_key",
    "access_token",
    "refresh_token",
    "oauth_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_verified_source_footer_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L180 verified source-footer contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_verified_source_footer_contract_hash", "signature"}
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


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_binding(
    artifact: dict[str, Any] | None,
    *,
    minimum_level: str,
    ready: bool,
) -> dict[str, Any]:
    return {
        "present": isinstance(artifact, dict),
        "artifact_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(_hashable_artifact(artifact)),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": _summary(artifact).get("status", ""),
        "level": _artifact_level(artifact),
        "minimum_level": minimum_level,
        "ready": ready,
    }


def _runtime_route_binding_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("runtime_route_binding_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL
        and decision.get("universal_runtime_route_binding_ready") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("response_release_allowed") is True
    )


def _source_footer_enforcement_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("footer_enforcement_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
        and decision.get("universal_source_footer_enforcement_ready") is True
        and decision.get("final_answer_release_allowed") is True
        and decision.get("user_confidence_footer_allowed") is True
    )


def _source_grounded_response_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("response_release_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
        and decision.get("source_grounded_response_ready") is True
        and decision.get("user_footer_display_allowed") is True
        and decision.get("citation_reliance_allowed") is True
    )


def _citation_verification_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("citation_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_CITATION_VERIFICATION_LEVEL
        and decision.get("verified_footer_release_approved") is True
        and decision.get("citation_reliance_approved") is True
    )


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _bool(value: Any) -> bool:
    return value is True


def _row_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(key, {})
    if not isinstance(rows, dict):
        return {}
    return {str(name): row for name, row in rows.items() if isinstance(row, dict)}


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate,
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
            _bool(row.get("footer_reliance_gate")),
            _bool(row.get("fail_closed")),
            _bool(row.get("auditable")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _field_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("field_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("renderer_hash")),
            _bool(row.get("field_required")),
            _bool(row.get("user_visible_or_machine_readable")),
            _bool(row.get("claim_bound")),
            _bool(row.get("source_bound")),
            _bool(row.get("privacy_safe")),
        )
    )


def _surface_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("surface_hash")),
            _string(row.get("footer_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("exact_footer_required")),
            _bool(row.get("citation_markers_preserved")),
            _bool(row.get("source_rows_preserved")),
            _bool(row.get("claim_rows_preserved")),
            _bool(row.get("copy_or_stream_preserved")),
            _bool(row.get("fail_closed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _support_dimension_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("dimension_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("measured")),
            _bool(row.get("threshold_met")),
            _bool(row.get("claim_level")),
            _bool(row.get("footer_level")),
            _bool(row.get("negative_fixture_covered")),
        )
    )


def _footer_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "source_label",
        "footer_row_hash",
        "source_identity_hash",
        "locator_health_hash",
        "metadata_fidelity_hash",
        "claim_support_hash",
        "evidence_span_hash",
        "rendered_footer_hash",
        "runtime_route_binding_hash",
        "verifier_hash",
    )
    required_bools = (
        "source_materialized",
        "locator_live_or_archived",
        "metadata_matches",
        "relevant_to_claims",
        "factually_supports_claims",
        "claim_hashes_bound",
        "evidence_span_bound",
        "visible_in_footer",
        "copy_export_preserved",
        "route_binding_matched",
        "settlement_state_visible",
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
            _bool(row.get("footer_reliance_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("copy_export_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _verified_footer_rows_complete(
    rows: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    missing_labels: list[str] = []
    incomplete_labels: list[str] = []
    mismatched_labels: list[str] = []
    for label, row in rows.items():
        if not label:
            missing_labels.append(label)
            continue
        if not _footer_row_ready(row):
            incomplete_labels.append(label)
        if row.get("source_label") != label:
            mismatched_labels.append(label)
    if not rows:
        missing_labels.append("at_least_one_verified_source_footer_row")
    return missing_labels, incomplete_labels, mismatched_labels


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


def make_universal_verified_source_footer_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L180 verified source-footer reliance contract."""

    runtime_route_binding = contract_input.get("universal_runtime_route_binding_contract")
    source_footer_enforcement = contract_input.get(
        "universal_source_footer_enforcement_contract"
    )
    source_grounded_response = contract_input.get(
        "universal_source_grounded_response_receipt"
    )
    citation_verification = contract_input.get(
        "universal_citation_verification_contract"
    )
    stage_rows = _row_map(contract_input, "footer_verification_stage_rows")
    field_rows = _row_map(contract_input, "verified_footer_field_rows")
    surface_rows = _row_map(contract_input, "footer_response_surface_rows")
    dimension_rows = _row_map(contract_input, "support_dimension_rows")
    footer_rows = _row_map(contract_input, "verified_footer_rows")
    negative_rows = _row_map(contract_input, "negative_footer_reliance_rows")

    missing_stages, incomplete_stages = _complete_rows(
        stage_rows,
        REQUIRED_FOOTER_VERIFICATION_STAGES,
        _stage_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        field_rows,
        REQUIRED_VERIFIED_FOOTER_FIELDS,
        _field_row_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_FOOTER_RESPONSE_SURFACES,
        _surface_row_ready,
    )
    missing_dimensions, incomplete_dimensions = _complete_rows(
        dimension_rows,
        REQUIRED_SUPPORT_DIMENSIONS,
        _support_dimension_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES,
        _negative_row_ready,
    )
    missing_footer_rows, incomplete_footer_rows, mismatched_footer_rows = (
        _verified_footer_rows_complete(footer_rows)
    )

    runtime_ready = _runtime_route_binding_ready(
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None
    )
    enforcement_ready = _source_footer_enforcement_ready(
        source_footer_enforcement
        if isinstance(source_footer_enforcement, dict)
        else None
    )
    response_ready = _source_grounded_response_ready(
        source_grounded_response if isinstance(source_grounded_response, dict) else None
    )
    citation_ready = _citation_verification_ready(
        citation_verification if isinstance(citation_verification, dict) else None
    )

    checks = {
        "runtime_route_binding_l179_ready": runtime_ready
        and _artifact_hash_is_reproducible(
            runtime_route_binding if isinstance(runtime_route_binding, dict) else None
        ),
        "source_footer_enforcement_l177_ready": enforcement_ready
        and _artifact_hash_is_reproducible(
            source_footer_enforcement
            if isinstance(source_footer_enforcement, dict)
            else None
        ),
        "source_grounded_response_l171_ready": response_ready
        and _artifact_hash_is_reproducible(
            source_grounded_response
            if isinstance(source_grounded_response, dict)
            else None
        ),
        "citation_verification_l141_ready": citation_ready
        and _artifact_hash_is_reproducible(
            citation_verification if isinstance(citation_verification, dict) else None
        ),
        "footer_verification_stage_rows_complete": not missing_stages
        and not incomplete_stages,
        "verified_footer_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "footer_response_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "support_dimension_rows_complete": not missing_dimensions
        and not incomplete_dimensions,
        "verified_footer_rows_complete": not missing_footer_rows
        and not incomplete_footer_rows
        and not mismatched_footer_rows,
        "negative_footer_reliance_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    stage_root = merkle_root([
        hash_payload({"stage": stage, "row": stage_rows.get(stage, {})})
        for stage in REQUIRED_FOOTER_VERIFICATION_STAGES
    ])
    field_root = merkle_root([
        hash_payload({"field": field, "row": field_rows.get(field, {})})
        for field in REQUIRED_VERIFIED_FOOTER_FIELDS
    ])
    surface_root = merkle_root([
        hash_payload({"surface": surface, "row": surface_rows.get(surface, {})})
        for surface in REQUIRED_FOOTER_RESPONSE_SURFACES
    ])
    dimension_root = merkle_root([
        hash_payload({"dimension": dimension, "row": dimension_rows.get(dimension, {})})
        for dimension in REQUIRED_SUPPORT_DIMENSIONS
    ])
    footer_root = merkle_root([
        hash_payload({"source_label": label, "row": footer_rows[label]})
        for label in sorted(footer_rows)
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES
    ])

    public = {
        "universal_verified_source_footer_contract_version": (
            UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-verified-source-footer-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "minimum_source_footer_enforcement_level": (
                MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
            ),
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "minimum_citation_verification_level": (
                MINIMUM_CITATION_VERIFICATION_LEVEL
            ),
            "link_health_relevance_and_fact_support_required": True,
            "footer_rows_must_be_visible_and_machine_readable": True,
            "used_sources_must_be_displayed_or_escrowed": True,
            "posthoc_footer_reliance_blocked": True,
            "copy_export_must_preserve_footer": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_runtime_route_binding_contract": _artifact_binding(
                runtime_route_binding
                if isinstance(runtime_route_binding, dict)
                else None,
                minimum_level=MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
                ready=runtime_ready,
            ),
            "universal_source_footer_enforcement_contract": _artifact_binding(
                source_footer_enforcement
                if isinstance(source_footer_enforcement, dict)
                else None,
                minimum_level=MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL,
                ready=enforcement_ready,
            ),
            "universal_source_grounded_response_receipt": _artifact_binding(
                source_grounded_response
                if isinstance(source_grounded_response, dict)
                else None,
                minimum_level=MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL,
                ready=response_ready,
            ),
            "universal_citation_verification_contract": _artifact_binding(
                citation_verification
                if isinstance(citation_verification, dict)
                else None,
                minimum_level=MINIMUM_CITATION_VERIFICATION_LEVEL,
                ready=citation_ready,
            ),
        },
        "footer_verification_stage_rows": {
            stage: stage_rows.get(stage, {})
            for stage in REQUIRED_FOOTER_VERIFICATION_STAGES
        },
        "verified_footer_field_rows": {
            field: field_rows.get(field, {})
            for field in REQUIRED_VERIFIED_FOOTER_FIELDS
        },
        "footer_response_surface_rows": {
            surface: surface_rows.get(surface, {})
            for surface in REQUIRED_FOOTER_RESPONSE_SURFACES
        },
        "support_dimension_rows": {
            dimension: dimension_rows.get(dimension, {})
            for dimension in REQUIRED_SUPPORT_DIMENSIONS
        },
        "verified_footer_rows": {
            label: footer_rows[label] for label in sorted(footer_rows)
        },
        "negative_footer_reliance_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES
        },
        "evidence_roots": {
            "footer_verification_stage_root": stage_root,
            "verified_footer_field_root": field_root,
            "footer_response_surface_root": surface_root,
            "support_dimension_root": dimension_root,
            "verified_footer_root": footer_root,
            "negative_footer_reliance_root": negative_root,
            "combined_verified_source_footer_root": merkle_root(
                [
                    stage_root,
                    field_root,
                    surface_root,
                    dimension_root,
                    footer_root,
                    negative_root,
                ]
            ),
        },
        "checks": checks,
        "source_footer_reliance_decision": {
            "universal_verified_source_footer_ready": ready,
            "response_release_allowed": ready,
            "user_source_footer_reliance_allowed": ready,
            "claim_source_reliance_allowed": ready,
            "copy_export_allowed": ready,
            "creator_settlement_allowed": ready,
            "fabricated_or_unsupported_sources_blocked": True,
            "used_but_omitted_sources_blocked_or_escrowed": True,
            "posthoc_footer_reliance_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "missing_footer_verification_stages": missing_stages,
            "incomplete_footer_verification_stages": incomplete_stages,
            "missing_verified_footer_fields": missing_fields,
            "incomplete_verified_footer_fields": incomplete_fields,
            "missing_footer_response_surfaces": missing_surfaces,
            "incomplete_footer_response_surfaces": incomplete_surfaces,
            "missing_support_dimensions": missing_dimensions,
            "incomplete_support_dimensions": incomplete_dimensions,
            "missing_verified_footer_rows": missing_footer_rows,
            "incomplete_verified_footer_rows": incomplete_footer_rows,
            "mismatched_verified_footer_rows": mismatched_footer_rows,
            "missing_negative_footer_reliance_failures": missing_negative,
            "incomplete_negative_footer_reliance_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_source_text_excluded": True,
            "private_evidence_text_excluded": True,
            "public_contract_uses_hashes_labels_locators_and_scores": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "minimum_source_footer_enforcement_level": (
                MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
            ),
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "minimum_citation_verification_level": (
                MINIMUM_CITATION_VERIFICATION_LEVEL
            ),
            "footer_verification_stage_count": len(
                REQUIRED_FOOTER_VERIFICATION_STAGES
            ),
            "ready_footer_verification_stage_count": len(
                REQUIRED_FOOTER_VERIFICATION_STAGES
            )
            - len(missing_stages)
            - len(incomplete_stages),
            "verified_footer_field_count": len(REQUIRED_VERIFIED_FOOTER_FIELDS),
            "ready_verified_footer_field_count": len(REQUIRED_VERIFIED_FOOTER_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "footer_response_surface_count": len(REQUIRED_FOOTER_RESPONSE_SURFACES),
            "ready_footer_response_surface_count": len(
                REQUIRED_FOOTER_RESPONSE_SURFACES
            )
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "support_dimension_count": len(REQUIRED_SUPPORT_DIMENSIONS),
            "ready_support_dimension_count": len(REQUIRED_SUPPORT_DIMENSIONS)
            - len(missing_dimensions)
            - len(incomplete_dimensions),
            "verified_footer_row_count": len(footer_rows),
            "ready_verified_footer_row_count": len(footer_rows)
            - len(incomplete_footer_rows)
            - len(mismatched_footer_rows),
            "negative_footer_reliance_failure_count": len(
                REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES
            ),
            "ready_negative_footer_reliance_failure_count": len(
                REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_verified_source_footer_contract": signing_secret is not None,
        },
    }
    public["universal_verified_source_footer_contract_hash"] = hash_payload(
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


def validate_universal_verified_source_footer_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L180 footer reliance contract."""

    errors: list[str] = []
    required = (
        "universal_verified_source_footer_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "footer_verification_stage_rows",
        "verified_footer_field_rows",
        "footer_response_surface_rows",
        "support_dimension_rows",
        "verified_footer_rows",
        "negative_footer_reliance_rows",
        "evidence_roots",
        "checks",
        "source_footer_reliance_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_verified_source_footer_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing verified source footer field: {key}")
    if contract.get("universal_verified_source_footer_contract_version") != (
        UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_verified_source_footer_contract_version")
    if contract.get("schema") != UNIVERSAL_VERIFIED_SOURCE_FOOTER_CONTRACT_SCHEMA:
        errors.append("unexpected verified source footer schema")
    for stage in REQUIRED_FOOTER_VERIFICATION_STAGES:
        if stage not in contract.get("footer_verification_stage_rows", {}):
            errors.append(f"missing footer verification stage row: {stage}")
    for field in REQUIRED_VERIFIED_FOOTER_FIELDS:
        if field not in contract.get("verified_footer_field_rows", {}):
            errors.append(f"missing verified footer field row: {field}")
    for surface in REQUIRED_FOOTER_RESPONSE_SURFACES:
        if surface not in contract.get("footer_response_surface_rows", {}):
            errors.append(f"missing footer response surface row: {surface}")
    for dimension in REQUIRED_SUPPORT_DIMENSIONS:
        if dimension not in contract.get("support_dimension_rows", {}):
            errors.append(f"missing support dimension row: {dimension}")
    for failure in REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES:
        if failure not in contract.get("negative_footer_reliance_rows", {}):
            errors.append(f"missing negative footer reliance row: {failure}")
    for check in (
        "runtime_route_binding_l179_ready",
        "source_footer_enforcement_l177_ready",
        "source_grounded_response_l171_ready",
        "citation_verification_l141_ready",
        "footer_verification_stage_rows_complete",
        "verified_footer_field_rows_complete",
        "footer_response_surface_rows_complete",
        "support_dimension_rows_complete",
        "verified_footer_rows_complete",
        "negative_footer_reliance_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing verified source footer check: {check}")
    return errors


def verify_universal_verified_source_footer_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L180 footer reliance contract against replay input."""

    errors = validate_universal_verified_source_footer_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_verified_source_footer_contract_hash") != expected_hash:
        errors.append("universal_verified_source_footer_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "verified source footer contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("verified source footer contract exposes private input strings")
    replayed = make_universal_verified_source_footer_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_verified_source_footer_contract_hash") != contract.get(
        "universal_verified_source_footer_contract_hash"
    ):
        errors.append("verified source footer contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("verified source footer contract is not ready")
    if (
        contract.get("source_footer_reliance_decision", {}).get(
            "universal_verified_source_footer_ready"
        )
        is not True
    ):
        errors.append("verified source footer decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("verified source footer privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("verified source footer contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("verified source footer contract signature is invalid")
    return errors
