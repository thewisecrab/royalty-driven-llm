"""Universal source-grounded response receipt.

The L171 layer binds a live L170 production admission to the final answer that
users see. L170 proves the provider call was admitted; L171 proves the released
response has grounded footer rows, claim-source support, citation metadata,
copy/export preservation, and settlement linkage before users, buyers, auditors,
or creators may rely on the answer or release royalties.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_VERSION = (
    "rdllm-universal-source-grounded-response-receipt/v1"
)
UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_SCHEMA = (
    "docs/schemas/universal_source_grounded_response_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L171"
MINIMUM_PRODUCTION_ADMISSION_LEVEL = "RDLLM-L170"
MINIMUM_LIVE_ATTRIBUTION_LEVEL = "RDLLM-L165"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-source-grounded-response-receipt.json"
)

REQUIRED_SOURCE_CATEGORIES = (
    "retrieval_document",
    "tool_observation",
    "web_source",
    "licensed_corpus_work",
    "conversation_memory",
    "persistent_memory",
    "parametric_memory",
    "post_training_signal",
    "code_repository",
    "media_asset",
    "human_creator_work",
    "no_source_abstention",
)

REQUIRED_CLAIM_TYPES = (
    "answer_claim",
    "factual_claim",
    "citation_claim",
    "quotation_claim",
    "summary_claim",
    "comparative_claim",
    "code_claim",
    "media_claim",
    "safety_or_policy_claim",
    "no_source_abstention_claim",
)

REQUIRED_RESPONSE_SURFACES = (
    "api_json",
    "markdown_footer",
    "html_footer",
    "streaming_final",
    "copy_export",
    "content_credential",
    "audit_export",
)

REQUIRED_SETTLEMENT_SCOPES = (
    "direct_creator_payout",
    "collective_management_pool",
    "residual_corpus_pool",
    "escrow_unattributed",
    "escrow_rights_conflict",
    "post_correction_adjustment",
)

REQUIRED_NEGATIVE_RESPONSE_FAILURES = (
    "missing_l170_admission",
    "stale_l170_admission",
    "source_footer_missing",
    "claim_without_source_support",
    "fabricated_source_identifier",
    "citation_target_unavailable",
    "citation_metadata_mismatch",
    "right_answer_wrong_source",
    "hidden_payable_source",
    "unsupported_parametric_claim",
    "low_confidence_source_released",
    "posthoc_footer_added_after_response",
    "copy_export_strips_sources",
    "settlement_without_grounded_footer",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_source_grounded_response_receipt_hash",
    "universal_production_invocation_admission_hash",
    "universal_live_attribution_proof_hash",
    "universal_provider_conformance_runner_receipt_hash",
    "universal_foundation_provider_binding_matrix_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "citation_reliance_receipt_hash",
    "claim_source_attribution_report_hash",
    "source_confidence_hash",
    "source_availability_hash",
    "revenue_allocation_hash",
    "finance_ledger_attestation_hash",
    "content_credential_hash",
    "admission_token_hash",
    "source_row_hash",
    "claim_row_hash",
    "settlement_row_hash",
    "response_surface_hash",
    "trace_hash",
    "span_hash",
    "receipt_hash",
    "attestation_hash",
    "report_hash",
    "manifest_hash",
    "envelope_hash",
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
    "claim_text",
    "sentence_text",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "streaming_transcript",
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


def load_universal_source_grounded_response_receipt_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L171 source-grounded response receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"universal_source_grounded_response_receipt_hash", "signature"}
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
    public_payload: dict[str, Any],
    receipt_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _production_admission_l170_ready(admission: dict[str, Any] | None) -> bool:
    if not isinstance(admission, dict):
        return False
    summary = _summary(admission)
    decision = admission.get("admission_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PRODUCTION_ADMISSION_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("production_invocation_admission_ready") is True
        and decision.get("live_provider_invocation_allowed") is True
        and decision.get("response_release_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("settlement_metering_allowed") is True
    )


def _live_attribution_ready(proof: dict[str, Any] | None) -> bool:
    if not isinstance(proof, dict):
        return False
    summary = _summary(proof)
    decision = proof.get("attribution_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_LIVE_ATTRIBUTION_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("live_attribution_ready") is True
        and decision.get("response_release_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("creator_settlement_release_allowed") is True
    )


def _source_category_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "source_row_hash",
        "source_identity_hash",
        "locator_hash",
        "license_hash",
        "creator_hash",
        "evidence_hash",
        "confidence_hash",
        "footer_label_hash",
        "settlement_share_hash",
        "verifier_hash",
    )
    required_flags = (
        "source_available",
        "claim_support_verified",
        "footer_visible",
        "rights_allow_display",
        "confidence_calibrated",
        "settlement_bound",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _claim_grounding_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "claim_row_hash",
        "claim_hash",
        "source_row_hash",
        "evidence_span_hash",
        "citation_locator_hash",
        "confidence_hash",
        "verifier_hash",
    )
    required_flags = (
        "supported_by_source",
        "source_visible_in_footer",
        "evidence_span_bound",
        "citation_metadata_verified",
        "unsupported_claim_blocked",
        "no_private_payloads",
    )
    return (
        row.get("claim_type") in REQUIRED_CLAIM_TYPES
        and all(str(row.get(field, "")) for field in required_hashes)
        and all(row.get(flag) is True for flag in required_flags)
    )


def _response_surface_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "response_surface_hash",
        "rendered_footer_hash",
        "admission_token_hash",
        "live_proof_hash",
        "claim_root_hash",
        "copy_export_hash",
        "verifier_hash",
    )
    required_flags = (
        "surface_rendered",
        "source_footer_visible",
        "l170_admission_bound",
        "live_proof_bound",
        "claim_rows_bound",
        "copy_export_preserves_sources",
        "fail_closed",
        "public_or_auditor_accessible",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _settlement_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "settlement_row_hash",
        "creator_hash",
        "source_row_hash",
        "license_hash",
        "usage_meter_hash",
        "allocation_hash",
        "remittance_hold_hash",
        "verifier_hash",
    )
    required_flags = (
        "source_visible_in_footer",
        "claim_support_verified",
        "l170_admission_bound",
        "footer_release_bound",
        "settlement_held_until_footer",
        "no_hidden_payable_source",
        "no_private_payloads",
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
            "response_release_blocked",
            "footer_reliance_blocked",
            "source_reliance_blocked",
            "citation_reliance_blocked",
            "copy_export_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    )


def _row_map(receipt_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = receipt_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


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


def make_universal_source_grounded_response_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L171 universal source-grounded response receipt."""

    admission = receipt_input.get("universal_production_invocation_admission")
    live_proof = receipt_input.get("universal_live_attribution_proof")
    source_rows = _row_map(receipt_input, "source_category_rows")
    claim_rows = _row_map(receipt_input, "claim_grounding_rows")
    surface_rows = _row_map(receipt_input, "response_surface_rows")
    settlement_rows = _row_map(receipt_input, "settlement_release_rows")
    negative_rows = _row_map(receipt_input, "negative_response_rows")

    missing_sources, incomplete_sources = _complete_rows(
        source_rows,
        REQUIRED_SOURCE_CATEGORIES,
        _source_category_ready,
    )
    missing_claims, incomplete_claims = _complete_rows(
        claim_rows,
        REQUIRED_CLAIM_TYPES,
        _claim_grounding_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_RESPONSE_SURFACES,
        _response_surface_ready,
    )
    missing_settlements, incomplete_settlements = _complete_rows(
        settlement_rows,
        REQUIRED_SETTLEMENT_SCOPES,
        _settlement_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_RESPONSE_FAILURES,
        _negative_failure_ready,
    )

    checks = {
        "production_invocation_admission_bound": _artifact_hash_is_reproducible(
            admission if isinstance(admission, dict) else None
        ),
        "production_invocation_admission_l170_ready": (
            _production_admission_l170_ready(admission if isinstance(admission, dict) else None)
        ),
        "live_attribution_proof_bound": _artifact_hash_is_reproducible(
            live_proof if isinstance(live_proof, dict) else None
        ),
        "live_attribution_proof_l165_ready": _live_attribution_ready(
            live_proof if isinstance(live_proof, dict) else None
        ),
        "source_category_rows_complete": not missing_sources
        and not incomplete_sources,
        "claim_grounding_rows_complete": not missing_claims and not incomplete_claims,
        "response_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "settlement_release_rows_complete": not missing_settlements
        and not incomplete_settlements,
        "negative_response_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "source_grounded_response_receipt_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    source_root = merkle_root([
        hash_payload({"name": name, "row": source_rows.get(name, {})})
        for name in REQUIRED_SOURCE_CATEGORIES
    ])
    claim_root = merkle_root([
        hash_payload({"name": name, "row": claim_rows.get(name, {})})
        for name in REQUIRED_CLAIM_TYPES
    ])
    surface_root = merkle_root([
        hash_payload({"name": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_RESPONSE_SURFACES
    ])
    settlement_root = merkle_root([
        hash_payload({"name": name, "row": settlement_rows.get(name, {})})
        for name in REQUIRED_SETTLEMENT_SCOPES
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_RESPONSE_FAILURES
    ])

    public = {
        "universal_source_grounded_response_receipt_version": (
            UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_VERSION
        ),
        "schema": UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-source-grounded-response-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_production_admission_level": MINIMUM_PRODUCTION_ADMISSION_LEVEL,
            "minimum_live_attribution_level": MINIMUM_LIVE_ATTRIBUTION_LEVEL,
            "source_footer_required_before_response_release": True,
            "claim_source_support_required": True,
            "citation_metadata_verification_required": True,
            "copy_export_source_preservation_required": True,
            "settlement_hold_required_until_grounded_footer": True,
            "private_payloads_forbidden_in_public_receipt": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_VERSION,
        },
        "production_admission_binding": {
            "present": isinstance(admission, dict),
            "artifact_hash": _declared_hash(admission if isinstance(admission, dict) else None),
            "payload_hash": hash_payload(
                _hashable_artifact(admission if isinstance(admission, dict) else None)
            ),
            "hash_reproducible": checks["production_invocation_admission_bound"],
            "status": _summary(admission if isinstance(admission, dict) else None).get(
                "status", ""
            ),
            "level": _summary(admission if isinstance(admission, dict) else None).get(
                "target_certification_level", ""
            ),
        },
        "live_attribution_binding": {
            "present": isinstance(live_proof, dict),
            "artifact_hash": _declared_hash(live_proof if isinstance(live_proof, dict) else None),
            "payload_hash": hash_payload(
                _hashable_artifact(live_proof if isinstance(live_proof, dict) else None)
            ),
            "hash_reproducible": checks["live_attribution_proof_bound"],
            "status": _summary(live_proof if isinstance(live_proof, dict) else None).get(
                "status", ""
            ),
            "level": _summary(live_proof if isinstance(live_proof, dict) else None).get(
                "target_certification_level", ""
            ),
        },
        "source_category_rows": source_rows,
        "claim_grounding_rows": claim_rows,
        "response_surface_rows": surface_rows,
        "settlement_release_rows": settlement_rows,
        "negative_response_rows": negative_rows,
        "evidence_roots": {
            "source_category_root": source_root,
            "claim_grounding_root": claim_root,
            "response_surface_root": surface_root,
            "settlement_release_root": settlement_root,
            "negative_response_root": negative_root,
        },
        "checks": checks,
        "response_release_decision": {
            "source_grounded_response_ready": ready,
            "final_answer_release_allowed": ready,
            "user_footer_display_allowed": ready,
            "source_reliance_allowed": ready,
            "citation_reliance_allowed": ready,
            "copy_export_allowed": ready,
            "creator_settlement_allowed": ready,
            "unsupported_claims_blocked": ready,
            "hidden_payable_sources_blocked": ready,
            "failure_modes": failure_modes,
            "missing_source_categories": missing_sources,
            "incomplete_source_categories": incomplete_sources,
            "missing_claim_types": missing_claims,
            "incomplete_claim_types": incomplete_claims,
            "missing_response_surfaces": missing_surfaces,
            "incomplete_response_surfaces": incomplete_surfaces,
            "missing_settlement_scopes": missing_settlements,
            "incomplete_settlement_scopes": incomplete_settlements,
            "missing_negative_failures": missing_negative,
            "incomplete_negative_failures": incomplete_negative,
        },
        "response_coverage": {
            "required_source_category_count": len(REQUIRED_SOURCE_CATEGORIES),
            "ready_source_category_count": len(REQUIRED_SOURCE_CATEGORIES)
            - len(missing_sources)
            - len(incomplete_sources),
            "required_claim_type_count": len(REQUIRED_CLAIM_TYPES),
            "ready_claim_type_count": len(REQUIRED_CLAIM_TYPES)
            - len(missing_claims)
            - len(incomplete_claims),
            "required_response_surface_count": len(REQUIRED_RESPONSE_SURFACES),
            "ready_response_surface_count": len(REQUIRED_RESPONSE_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "required_settlement_scope_count": len(REQUIRED_SETTLEMENT_SCOPES),
            "ready_settlement_scope_count": len(REQUIRED_SETTLEMENT_SCOPES)
            - len(missing_settlements)
            - len(incomplete_settlements),
        },
        "privacy": {
            "private_payload_fields": [],
            "private_strings_absent": True,
            "private_payloads_excluded": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_production_admission_level": MINIMUM_PRODUCTION_ADMISSION_LEVEL,
            "minimum_live_attribution_level": MINIMUM_LIVE_ATTRIBUTION_LEVEL,
            "source_category_count": len(REQUIRED_SOURCE_CATEGORIES),
            "ready_source_category_count": len(REQUIRED_SOURCE_CATEGORIES)
            - len(missing_sources)
            - len(incomplete_sources),
            "claim_type_count": len(REQUIRED_CLAIM_TYPES),
            "ready_claim_type_count": len(REQUIRED_CLAIM_TYPES)
            - len(missing_claims)
            - len(incomplete_claims),
            "response_surface_count": len(REQUIRED_RESPONSE_SURFACES),
            "ready_response_surface_count": len(REQUIRED_RESPONSE_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "settlement_scope_count": len(REQUIRED_SETTLEMENT_SCOPES),
            "ready_settlement_scope_count": len(REQUIRED_SETTLEMENT_SCOPES)
            - len(missing_settlements)
            - len(incomplete_settlements),
            "negative_response_failure_count": len(REQUIRED_NEGATIVE_RESPONSE_FAILURES),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_source_grounded_response_receipt": signing_secret is not None,
        },
    }
    public["privacy"]["private_payload_fields"] = _contains_private_fields(public)
    public["privacy"]["private_strings_absent"] = _private_strings_absent(
        public,
        receipt_input,
    )
    public["privacy"]["private_payloads_excluded"] = (
        not public["privacy"]["private_payload_fields"]
        and public["privacy"]["private_strings_absent"]
    )
    if not public["privacy"]["private_payloads_excluded"]:
        public["checks"]["private_payloads_excluded"] = False
        public["response_release_decision"]["source_grounded_response_ready"] = False
        public["response_release_decision"]["final_answer_release_allowed"] = False
        public["response_release_decision"]["user_footer_display_allowed"] = False
        public["response_release_decision"]["source_reliance_allowed"] = False
        public["response_release_decision"]["citation_reliance_allowed"] = False
        public["response_release_decision"]["copy_export_allowed"] = False
        public["response_release_decision"]["creator_settlement_allowed"] = False
        public["response_release_decision"]["unsupported_claims_blocked"] = False
        public["response_release_decision"]["hidden_payable_sources_blocked"] = False
        if "private_payloads_excluded" not in public["response_release_decision"]["failure_modes"]:
            public["response_release_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["response_release_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_source_grounded_response_receipt_hash"] = hash_payload(
        _hashable_receipt(public)
    )
    if signing_secret:
        public["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_receipt(public), signing_secret),
        }
    return public


def validate_universal_source_grounded_response_receipt_shape(
    receipt: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L171 response receipt."""

    errors: list[str] = []
    required = (
        "universal_source_grounded_response_receipt_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "production_admission_binding",
        "live_attribution_binding",
        "source_category_rows",
        "claim_grounding_rows",
        "response_surface_rows",
        "settlement_release_rows",
        "negative_response_rows",
        "evidence_roots",
        "checks",
        "response_release_decision",
        "response_coverage",
        "privacy",
        "summary",
        "universal_source_grounded_response_receipt_hash",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing source grounded response receipt field: {key}")
    if receipt.get("universal_source_grounded_response_receipt_version") != (
        UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_VERSION
    ):
        errors.append("unexpected universal_source_grounded_response_receipt_version")
    if receipt.get("schema") != UNIVERSAL_SOURCE_GROUNDED_RESPONSE_RECEIPT_SCHEMA:
        errors.append("unexpected source grounded response schema")
    for name in REQUIRED_SOURCE_CATEGORIES:
        if name not in receipt.get("source_category_rows", {}):
            errors.append(f"missing source category row: {name}")
    for name in REQUIRED_CLAIM_TYPES:
        if name not in receipt.get("claim_grounding_rows", {}):
            errors.append(f"missing claim grounding row: {name}")
    for name in REQUIRED_RESPONSE_SURFACES:
        if name not in receipt.get("response_surface_rows", {}):
            errors.append(f"missing response surface row: {name}")
    for name in REQUIRED_SETTLEMENT_SCOPES:
        if name not in receipt.get("settlement_release_rows", {}):
            errors.append(f"missing settlement release row: {name}")
    for name in REQUIRED_NEGATIVE_RESPONSE_FAILURES:
        if name not in receipt.get("negative_response_rows", {}):
            errors.append(f"missing negative response row: {name}")
    for check in (
        "production_invocation_admission_bound",
        "production_invocation_admission_l170_ready",
        "live_attribution_proof_bound",
        "live_attribution_proof_l165_ready",
        "source_category_rows_complete",
        "claim_grounding_rows_complete",
        "response_surface_rows_complete",
        "settlement_release_rows_complete",
        "negative_response_fixtures_reject",
        "source_grounded_response_receipt_signed",
    ):
        if check not in receipt.get("checks", {}):
            errors.append(f"missing source grounded response check: {check}")
    return errors


def verify_universal_source_grounded_response_receipt(
    receipt_input: dict[str, Any],
    receipt: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L171 response receipt against replay input."""

    errors = validate_universal_source_grounded_response_receipt_shape(receipt)
    expected_hash = hash_payload(_hashable_receipt(receipt))
    if receipt.get("universal_source_grounded_response_receipt_hash") != expected_hash:
        errors.append("universal_source_grounded_response_receipt_hash mismatch")
    if _contains_private_fields(receipt):
        errors.append(
            "source grounded response receipt exposes private fields: "
            + ", ".join(_contains_private_fields(receipt))
        )
    if not _private_strings_absent(receipt, receipt_input):
        errors.append("source grounded response receipt exposes private input strings")
    replayed = make_universal_source_grounded_response_receipt(
        receipt_input,
        issuer=receipt.get("issuer", DEFAULT_ISSUER),
        created_at=receipt.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_source_grounded_response_receipt_hash") != receipt.get(
        "universal_source_grounded_response_receipt_hash"
    ):
        errors.append("source grounded response receipt does not match replay inputs")
    if receipt.get("summary", {}).get("status") != "ready":
        errors.append("source grounded response receipt is not ready")
    if receipt.get("response_release_decision", {}).get(
        "source_grounded_response_ready"
    ) is not True:
        errors.append("source grounded response release decision is not ready")
    if receipt.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("source grounded response receipt privacy is not preserved")
    if signing_secret:
        signature = receipt.get("signature", {})
        expected_signature = sign_payload(_hashable_receipt(receipt), signing_secret)
        if not signature:
            errors.append("source grounded response receipt is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source grounded response receipt signature is invalid")
    return errors
