"""Universal claim-evidence footer verification contracts.

The L184 layer turns source footers from "a cited source exists" into "this
source supports this exact claim." L183 normalizes provider-native source
annotations into RDLLM footer rows. L184 verifies claim decomposition, citation
parsing, source accessibility, intent-purpose alignment, source suitability,
answer-source fidelity, factual support, and footer preservation before a user
or settlement record may rely on the displayed sources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_VERSION = (
    "rdllm-universal-claim-evidence-footer-verification-contract/v1"
)
UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_SCHEMA = (
    "docs/schemas/universal_claim_evidence_footer_verification_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L184"
MINIMUM_NATIVE_SOURCE_ANNOTATION_LEVEL = "RDLLM-L183"
MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL = "RDLLM-L180"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-claim-evidence-footer-verification-contract.json"
)

REQUIRED_VERIFICATION_DIMENSIONS = (
    "citation_existence",
    "source_accessibility",
    "source_materialization",
    "claim_decomposition",
    "inline_citation_ast_parsing",
    "intent_purpose_alignment",
    "source_suitability",
    "answer_source_fidelity",
    "factual_support",
    "relevance_to_claim",
    "omission_and_overclaim_scan",
    "footer_rendering_preservation",
)

REQUIRED_VERIFIED_FOOTER_FIELDS = (
    "footer_source_label",
    "source_title_hash",
    "source_creator_or_publisher_hash",
    "source_uri_or_locator_hash",
    "source_access_status",
    "source_type_or_domain",
    "claim_hash",
    "claim_span_hash",
    "evidence_span_hash",
    "intent_purpose_alignment_score_hash",
    "source_suitability_score_hash",
    "answer_source_fidelity_score_hash",
    "support_verdict",
    "confidence_label",
    "rdllm_footer_row_hash",
)

REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES = (
    "nonexistent_citation_identifier",
    "link_works_but_source_does_not_support_claim",
    "correct_answer_wrong_source",
    "real_source_domain_inappropriate",
    "intent_purpose_mismatch",
    "source_says_opinion_answer_states_fact",
    "hedged_source_answer_removes_qualifier",
    "source_contradicts_claim",
    "tangential_source_misattributed",
    "retrieval_context_not_cited_in_footer",
    "cited_source_not_retrieved_or_materialized",
    "deep_research_markdown_citation_unparsed",
    "streaming_final_omits_source_footer",
    "provider_annotation_not_mapped_to_claim",
    "claim_without_citation_or_abstention",
    "citation_added_posthoc",
    "footer_source_omitted_from_settlement",
    "private_source_text_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_claim_evidence_footer_verification_contract_hash",
    "universal_native_source_annotation_contract_hash",
    "universal_verified_source_footer_contract_hash",
    "dimension_hash",
    "rubric_hash",
    "field_hash",
    "claim_evidence_hash",
    "native_annotation_hash",
    "footer_row_hash",
    "verified_footer_hash",
    "claim_hash",
    "claim_span_hash",
    "evidence_span_hash",
    "source_identity_hash",
    "source_access_hash",
    "intent_purpose_alignment_hash",
    "source_suitability_hash",
    "answer_source_fidelity_hash",
    "support_verdict_hash",
    "verifier_hash",
    "fixture_hash",
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
    "citation_text",
    "cited_text",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "retrieval_payload",
    "tool_payload",
    "reasoning",
    "chain_of_thought",
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

PUBLIC_ROW_KEY_ALLOWLISTS = {
    "verification_dimension_rows": set(REQUIRED_VERIFICATION_DIMENSIONS),
    "verified_footer_field_rows": set(REQUIRED_VERIFIED_FOOTER_FIELDS),
    "negative_claim_evidence_rows": set(REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES),
}


def load_universal_claim_evidence_footer_verification_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L184 claim-evidence footer contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key
        not in {
            "universal_claim_evidence_footer_verification_contract_hash",
            "signature",
        }
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


def _l183_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("native_source_annotation_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_NATIVE_SOURCE_ANNOTATION_LEVEL
        and decision.get("universal_native_source_annotation_ready") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("response_release_allowed") is True
    )


def _l180_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("source_footer_reliance_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
        and decision.get("universal_verified_source_footer_ready") is True
        and (
            decision.get("source_footer_reliance_allowed") is True
            or decision.get("user_source_footer_reliance_allowed") is True
        )
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


def _dimension_row_ready(row: dict[str, Any]) -> bool:
    required_strings = ("dimension_hash", "rubric_hash", "verifier_hash")
    required_bools = (
        "measured",
        "threshold_met",
        "claim_level",
        "source_level",
        "footer_gate",
        "negative_fixture_covered",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _field_row_ready(row: dict[str, Any]) -> bool:
    required_strings = ("field_hash", "schema_hash", "renderer_hash")
    required_bools = (
        "field_required",
        "claim_bound",
        "source_bound",
        "footer_visible_or_machine_readable",
        "privacy_safe",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_claim_evidence_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "claim_evidence_hash",
        "native_annotation_hash",
        "footer_row_hash",
        "claim_hash",
        "evidence_span_hash",
        "verifier_hash",
    )
    required_bools = (
        "claim_decomposed",
        "citation_ast_parsed",
        "cited_content_materialized",
        "source_supports_claim",
        "intent_purpose_aligned",
        "source_suitable",
        "answer_source_fidelity_passed",
        "footer_row_projected",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _verified_footer_source_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "source_label",
        "source_identity_hash",
        "source_access_hash",
        "claim_hash",
        "evidence_span_hash",
        "intent_purpose_alignment_hash",
        "source_suitability_hash",
        "answer_source_fidelity_hash",
        "support_verdict_hash",
        "footer_row_hash",
        "verifier_hash",
        "support_verdict",
        "confidence_label",
    )
    required_bools = (
        "source_exists_or_archived",
        "access_checked",
        "metadata_matches",
        "claim_hashes_bound",
        "evidence_span_bound",
        "support_verdict_verified",
        "footer_visible",
        "source_suitability_verified",
        "answer_source_fidelity_verified",
        "no_private_payloads",
    )
    return (
        all(_string(row.get(field)) for field in required_strings)
        and row.get("support_verdict") == "supported"
        and all(_bool(row.get(field)) for field in required_bools)
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("creator_settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _l183_route_ids(native_source_annotation: dict[str, Any] | None) -> list[str]:
    if not isinstance(native_source_annotation, dict):
        return []
    rows = native_source_annotation.get("route_annotation_rows", {})
    if isinstance(rows, dict) and rows:
        return sorted(str(route_id) for route_id in rows)
    coverage = native_source_annotation.get("coverage", {})
    if isinstance(coverage, dict):
        route_ids = coverage.get("l182_route_ids", [])
        if isinstance(route_ids, list):
            return sorted(str(route_id) for route_id in route_ids if route_id)
    return []


def _route_rows_complete(
    rows: dict[str, dict[str, Any]],
    required_route_ids: list[str],
) -> tuple[list[str], list[str], list[str]]:
    missing = [route_id for route_id in required_route_ids if route_id not in rows]
    incomplete = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and not _route_claim_evidence_row_ready(rows[route_id])
    ]
    mismatched = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and rows[route_id].get("route_id") != route_id
    ]
    if not required_route_ids:
        missing.append("at_least_one_l183_route")
    return missing, incomplete, mismatched


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
        if not _verified_footer_source_row_ready(row):
            incomplete_labels.append(label)
        if row.get("source_label") != label:
            mismatched_labels.append(label)
    if not rows:
        missing_labels.append("at_least_one_verified_footer_source_row")
    return missing_labels, incomplete_labels, mismatched_labels


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            allowlisted_row_keys = PUBLIC_ROW_KEY_ALLOWLISTS.get(path, set())
            if key_str in PRIVATE_FIELD_NAMES and key_str not in allowlisted_row_keys:
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


def make_universal_claim_evidence_footer_verification_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L184 universal claim-evidence footer verification contract."""

    native_source_annotation = contract_input.get(
        "universal_native_source_annotation_contract"
    )
    verified_source_footer = contract_input.get(
        "universal_verified_source_footer_contract"
    )
    dimension_rows = _row_map(contract_input, "verification_dimension_rows")
    field_rows = _row_map(contract_input, "verified_footer_field_rows")
    route_rows = _row_map(contract_input, "route_claim_evidence_rows")
    footer_rows = _row_map(contract_input, "verified_footer_source_rows")
    negative_rows = _row_map(contract_input, "negative_claim_evidence_rows")

    missing_dimensions, incomplete_dimensions = _complete_rows(
        dimension_rows,
        REQUIRED_VERIFICATION_DIMENSIONS,
        _dimension_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        field_rows,
        REQUIRED_VERIFIED_FOOTER_FIELDS,
        _field_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES,
        _negative_row_ready,
    )
    required_route_ids = _l183_route_ids(
        native_source_annotation
        if isinstance(native_source_annotation, dict)
        else None
    )
    missing_routes, incomplete_routes, mismatched_routes = _route_rows_complete(
        route_rows, required_route_ids
    )
    missing_footer_rows, incomplete_footer_rows, mismatched_footer_rows = (
        _verified_footer_rows_complete(footer_rows)
    )

    l183_ready = _l183_ready(
        native_source_annotation
        if isinstance(native_source_annotation, dict)
        else None
    )
    l180_ready = _l180_ready(
        verified_source_footer
        if isinstance(verified_source_footer, dict)
        else None
    )
    checks = {
        "native_source_annotation_l183_ready": l183_ready
        and _artifact_hash_is_reproducible(
            native_source_annotation
            if isinstance(native_source_annotation, dict)
            else None
        ),
        "verified_source_footer_l180_ready": l180_ready
        and _artifact_hash_is_reproducible(
            verified_source_footer
            if isinstance(verified_source_footer, dict)
            else None
        ),
        "verification_dimension_rows_complete": not missing_dimensions
        and not incomplete_dimensions,
        "verified_footer_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "route_claim_evidence_rows_complete": (
            not missing_routes
            and not incomplete_routes
            and not mismatched_routes
        ),
        "verified_footer_source_rows_complete": (
            not missing_footer_rows
            and not incomplete_footer_rows
            and not mismatched_footer_rows
        ),
        "negative_claim_evidence_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    dimension_root = merkle_root([
        hash_payload({"dimension": name, "row": dimension_rows.get(name, {})})
        for name in REQUIRED_VERIFICATION_DIMENSIONS
    ])
    field_root = merkle_root([
        hash_payload({"verified_footer_field": name, "row": field_rows.get(name, {})})
        for name in REQUIRED_VERIFIED_FOOTER_FIELDS
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_rows.get(route_id, {})})
        for route_id in required_route_ids
    ])
    footer_root = merkle_root([
        hash_payload({"source_label": label, "row": footer_rows[label]})
        for label in sorted(footer_rows)
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES
    ])

    public = {
        "universal_claim_evidence_footer_verification_contract_version": (
            UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-claim-evidence-footer-verification-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_native_source_annotation_level": (
                MINIMUM_NATIVE_SOURCE_ANNOTATION_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "citations_must_be_parsed_as_structured_objects": True,
            "cited_content_must_be_materialized": True,
            "footer_sources_must_support_specific_claims": True,
            "source_suitability_and_intent_alignment_required": True,
            "answer_source_fidelity_required": True,
            "unsupported_or_misleading_footer_sources_fail_closed": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": (
                UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_VERSION
            ),
        },
        "artifact_bindings": {
            "universal_native_source_annotation_contract": _artifact_binding(
                native_source_annotation
                if isinstance(native_source_annotation, dict)
                else None,
                minimum_level=MINIMUM_NATIVE_SOURCE_ANNOTATION_LEVEL,
                ready=l183_ready,
            ),
            "universal_verified_source_footer_contract": _artifact_binding(
                verified_source_footer
                if isinstance(verified_source_footer, dict)
                else None,
                minimum_level=MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL,
                ready=l180_ready,
            ),
        },
        "verification_dimension_rows": {
            name: dimension_rows.get(name, {})
            for name in REQUIRED_VERIFICATION_DIMENSIONS
        },
        "verified_footer_field_rows": {
            name: field_rows.get(name, {})
            for name in REQUIRED_VERIFIED_FOOTER_FIELDS
        },
        "route_claim_evidence_rows": {
            route_id: route_rows.get(route_id, {}) for route_id in required_route_ids
        },
        "verified_footer_source_rows": {
            label: footer_rows[label] for label in sorted(footer_rows)
        },
        "negative_claim_evidence_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES
        },
        "evidence_roots": {
            "verification_dimension_root": dimension_root,
            "verified_footer_field_root": field_root,
            "route_claim_evidence_root": route_root,
            "verified_footer_source_root": footer_root,
            "negative_claim_evidence_root": negative_root,
            "combined_claim_evidence_footer_root": merkle_root(
                [dimension_root, field_root, route_root, footer_root, negative_root]
            ),
        },
        "checks": checks,
        "claim_evidence_footer_decision": {
            "universal_claim_evidence_footer_verification_ready": ready,
            "source_footer_reliance_allowed": ready,
            "response_release_allowed": ready,
            "creator_settlement_allowed": ready,
            "citation_existence_verified": ready,
            "source_suitability_verified": ready,
            "answer_source_fidelity_verified": ready,
            "unsupported_claim_blocked": True,
            "misleading_citation_blocked": True,
            "fabricated_citation_blocked": True,
            "posthoc_citation_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "l183_route_ids": required_route_ids,
            "missing_verification_dimensions": missing_dimensions,
            "incomplete_verification_dimensions": incomplete_dimensions,
            "missing_verified_footer_fields": missing_fields,
            "incomplete_verified_footer_fields": incomplete_fields,
            "missing_route_claim_evidence_rows": missing_routes,
            "incomplete_route_claim_evidence_rows": incomplete_routes,
            "mismatched_route_claim_evidence_rows": mismatched_routes,
            "missing_verified_footer_source_rows": missing_footer_rows,
            "incomplete_verified_footer_source_rows": incomplete_footer_rows,
            "mismatched_verified_footer_source_rows": mismatched_footer_rows,
            "missing_negative_claim_evidence_failures": missing_negative,
            "incomplete_negative_claim_evidence_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_source_text_excluded": True,
            "private_provider_annotations_excluded": True,
            "public_contract_uses_hashes_verdicts_routes_and_footer_rows": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_native_source_annotation_level": (
                MINIMUM_NATIVE_SOURCE_ANNOTATION_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "verification_dimension_count": len(REQUIRED_VERIFICATION_DIMENSIONS),
            "ready_verification_dimension_count": len(REQUIRED_VERIFICATION_DIMENSIONS)
            - len(missing_dimensions)
            - len(incomplete_dimensions),
            "verified_footer_field_count": len(REQUIRED_VERIFIED_FOOTER_FIELDS),
            "ready_verified_footer_field_count": len(REQUIRED_VERIFIED_FOOTER_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "l183_route_count": len(required_route_ids),
            "ready_route_claim_evidence_count": len(required_route_ids)
            - len(missing_routes)
            - len(incomplete_routes)
            - len(mismatched_routes),
            "verified_footer_source_count": len(footer_rows),
            "ready_verified_footer_source_count": len(footer_rows)
            - len(incomplete_footer_rows)
            - len(mismatched_footer_rows),
            "negative_claim_evidence_failure_count": len(
                REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES
            ),
            "ready_negative_claim_evidence_failure_count": len(
                REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_claim_evidence_footer_contract": signing_secret is not None,
        },
    }
    public["universal_claim_evidence_footer_verification_contract_hash"] = hash_payload(
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


def validate_universal_claim_evidence_footer_verification_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L184 footer contract."""

    errors: list[str] = []
    required = (
        "universal_claim_evidence_footer_verification_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "verification_dimension_rows",
        "verified_footer_field_rows",
        "route_claim_evidence_rows",
        "verified_footer_source_rows",
        "negative_claim_evidence_rows",
        "evidence_roots",
        "checks",
        "claim_evidence_footer_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_claim_evidence_footer_verification_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing claim-evidence footer field: {key}")
    if contract.get(
        "universal_claim_evidence_footer_verification_contract_version"
    ) != UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_VERSION:
        errors.append(
            "unexpected universal_claim_evidence_footer_verification_contract_version"
        )
    if (
        contract.get("schema")
        != UNIVERSAL_CLAIM_EVIDENCE_FOOTER_VERIFICATION_CONTRACT_SCHEMA
    ):
        errors.append("unexpected claim-evidence footer schema")
    for dimension in REQUIRED_VERIFICATION_DIMENSIONS:
        if dimension not in contract.get("verification_dimension_rows", {}):
            errors.append(f"missing verification dimension row: {dimension}")
    for field in REQUIRED_VERIFIED_FOOTER_FIELDS:
        if field not in contract.get("verified_footer_field_rows", {}):
            errors.append(f"missing verified footer field row: {field}")
    for failure in REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES:
        if failure not in contract.get("negative_claim_evidence_rows", {}):
            errors.append(f"missing negative claim-evidence row: {failure}")
    for check in (
        "native_source_annotation_l183_ready",
        "verified_source_footer_l180_ready",
        "verification_dimension_rows_complete",
        "verified_footer_field_rows_complete",
        "route_claim_evidence_rows_complete",
        "verified_footer_source_rows_complete",
        "negative_claim_evidence_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing claim-evidence footer check: {check}")
    return errors


def verify_universal_claim_evidence_footer_verification_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L184 claim-evidence footer contract against replay input."""

    errors = validate_universal_claim_evidence_footer_verification_contract_shape(
        contract
    )
    expected_hash = hash_payload(_hashable_contract(contract))
    if (
        contract.get("universal_claim_evidence_footer_verification_contract_hash")
        != expected_hash
    ):
        errors.append(
            "universal_claim_evidence_footer_verification_contract_hash mismatch"
        )
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "claim-evidence footer contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("claim-evidence footer contract exposes private input strings")
    replayed = make_universal_claim_evidence_footer_verification_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get(
        "universal_claim_evidence_footer_verification_contract_hash"
    ) != contract.get("universal_claim_evidence_footer_verification_contract_hash"):
        errors.append("claim-evidence footer contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("claim-evidence footer contract is not ready")
    if (
        contract.get("claim_evidence_footer_decision", {}).get(
            "universal_claim_evidence_footer_verification_ready"
        )
        is not True
    ):
        errors.append("claim-evidence footer decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("claim-evidence footer privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("claim-evidence footer contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("claim-evidence footer contract signature is invalid")
    return errors
