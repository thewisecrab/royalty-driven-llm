"""Universal live attribution proof.

The L165 layer is the response-time proof that an answer's visible source
footer reflects actual source reliance. It binds source identity, rendered
footer rows, claim support, operational influence, factual confidence,
knowledge-source classification, and settlement participation before a provider
can treat a response as attributed or release creator royalties.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_LIVE_ATTRIBUTION_PROOF_VERSION = "rdllm-universal-live-attribution-proof/v1"
UNIVERSAL_LIVE_ATTRIBUTION_PROOF_SCHEMA = (
    "docs/schemas/universal_live_attribution_proof.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L165"
MINIMUM_REFERENCE_DISTRIBUTION_LEVEL = "RDLLM-L164"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-live-attribution-proof.json"

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "universal_reference_implementation_distribution",
    "response_envelope",
    "universal_claim_provenance_envelope",
    "grounded_source_footer",
    "source_footer_delivery",
    "citation_reliance_receipt",
    "claim_source_attribution_report",
    "evidence_utility_attribution_report",
    "parametric_memory_attribution_report",
    "source_confidence_report",
    "source_availability_report",
    "citation_identity_report",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_KNOWLEDGE_SOURCE_MODES = (
    "current_turn_retrieval",
    "tool_observation",
    "conversation_memory",
    "persistent_memory",
    "parametric_memory",
    "post_training_signal",
    "residual_corpus_value",
    "no_source_abstention",
)

REQUIRED_FOOTER_SURFACES = (
    "api_json",
    "markdown",
    "html",
    "streaming_final",
    "copy_export",
)

REQUIRED_NEGATIVE_LIVE_FAILURES = (
    "decorative_citation_without_influence",
    "right_answer_wrong_source",
    "fabricated_source_identity",
    "hidden_payable_source",
    "low_confidence_source_released",
    "unsupported_parametric_memory_claim",
    "attribution_suppression",
    "stale_or_unavailable_source_released",
    "posthoc_footer_added_after_generation",
    "provider_strips_live_proof",
    "settlement_released_without_live_proof",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_live_attribution_proof_hash",
    "universal_reference_implementation_distribution_hash",
    "universal_industry_adoption_root_hash",
    "universal_foundation_provider_adoption_pack_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "citation_reliance_receipt_hash",
    "claim_source_attribution_hash",
    "claim_source_attribution_report_hash",
    "evidence_utility_attribution_hash",
    "evidence_utility_attribution_report_hash",
    "parametric_memory_attribution_hash",
    "parametric_memory_attribution_report_hash",
    "citation_identity_hash",
    "source_confidence_hash",
    "source_availability_hash",
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "source_access_lease_hash",
    "binding_report_hash",
    "lease_report_hash",
    "protocol_ingestion_report_hash",
    "revenue_allocation_hash",
    "finance_ledger_attestation_hash",
    "trust_registry_hash",
    "attestation_hash",
    "graph_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "envelope_hash",
    "event_hash",
    "package_hash",
    "distribution_hash",
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


def load_universal_live_attribution_proof_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L165 live attribution proof."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_proof(proof: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in proof.items()
        if key not in {"universal_live_attribution_proof_hash", "signature"}
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
    if artifact.get("receipt_hash") and isinstance(artifact.get("payload"), dict):
        return declared == hash_payload(artifact["payload"])
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _level_number(level: str) -> int | None:
    if not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: str, minimum: str) -> bool:
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    for key in ("target_certification_level", "highest_level", "attested_highest_level"):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    certification = artifact.get("certification") if isinstance(artifact, dict) else None
    if isinstance(certification, dict):
        value = certification.get("highest_level")
        if isinstance(value, str):
            return value
    return ""


def _artifact_binding(name: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    declared = _declared_hash(artifact)
    return {
        "artifact": name,
        "present": isinstance(artifact, dict) and bool(artifact),
        "artifact_hash": declared,
        "payload_hash": hash_payload(_hashable_artifact(artifact)),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": str(_summary(artifact).get("status", "")),
        "level": _artifact_level(artifact),
    }


def _artifact_bindings(proof_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: _artifact_binding(
            name,
            proof_input.get(name) if isinstance(proof_input.get(name), dict) else None,
        )
        for name in REQUIRED_CORE_ARTIFACTS
    }


def _row_map(proof_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = proof_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


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


def _private_strings_absent(public_payload: dict[str, Any], proof_input: dict[str, Any]) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in proof_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _float(row: dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _live_source_ready(row: dict[str, Any], *, min_confidence: float, min_utility: float) -> bool:
    required_hashes = (
        "source_hash",
        "footer_row_hash",
        "claim_provenance_hash",
        "influence_hash",
        "source_identity_hash",
        "confidence_hash",
        "settlement_hash",
    )
    required_flags = (
        "visible_in_footer",
        "identity_verified",
        "claim_support_verified",
        "current_turn_or_memory_path_verified",
        "causal_utility_verified",
        "factual_confidence_accepted",
        "license_or_escrow_resolved",
        "settlement_weight_bound",
        "private_payloads_excluded",
    )
    mode = str(row.get("knowledge_source_mode", ""))
    return (
        mode in REQUIRED_KNOWLEDGE_SOURCE_MODES
        and all(str(row.get(field, "")) for field in required_hashes)
        and all(row.get(flag) is True for flag in required_flags)
        and _float(row, "factual_confidence") >= min_confidence
        and _float(row, "utility_score") >= min_utility
        and _float(row, "attribution_weight") > 0.0
    )


def _knowledge_mode_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "classifier_hash",
        "calibration_hash",
        "evidence_path_hash",
        "negative_control_hash",
    )
    required_flags = (
        "mode_supported",
        "classifier_calibrated",
        "negative_control_passed",
        "footer_policy_enforced",
        "settlement_policy_bound",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _footer_surface_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "surface_hash",
        "rendered_footer_hash",
        "live_proof_binding_hash",
        "copy_export_hash",
    )
    required_flags = (
        "source_footer_visible",
        "live_proof_hash_embedded",
        "claim_markers_preserved",
        "source_order_preserved",
        "verification_link_available",
        "copy_export_preserves_footer",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "response_blocked",
            "footer_reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    ) and bool(row.get("fixture_hash"))


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


def _hidden_payable_count(proof_input: dict[str, Any]) -> int:
    value = proof_input.get("hidden_payable_source_count", 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _suppression_count(proof_input: dict[str, Any]) -> int:
    explicit = proof_input.get("attribution_suppression_count")
    if explicit is not None:
        try:
            return int(explicit or 0)
        except (TypeError, ValueError):
            return 0
    confidence = proof_input.get("source_confidence_report", {})
    summary = confidence.get("summary", {}) if isinstance(confidence, dict) else {}
    taxonomy = confidence.get("hallucination_taxonomy", {}) if isinstance(confidence, dict) else {}
    for container in (summary, taxonomy):
        if "attribution_suppression_count" in container:
            try:
                return int(container.get("attribution_suppression_count", 0) or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def make_universal_live_attribution_proof(
    proof_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L165 universal live attribution proof."""

    policy_input = proof_input.get("policy", {})
    min_confidence = float(policy_input.get("minimum_factual_confidence", 0.72))
    min_utility = float(policy_input.get("minimum_utility_score", 0.35))

    artifact_bindings = _artifact_bindings(proof_input)
    live_source_rows = _row_map(proof_input, "live_source_rows")
    knowledge_mode_rows = _row_map(proof_input, "knowledge_source_mode_rows")
    footer_surface_rows = _row_map(proof_input, "footer_surface_rows")
    negative_live_rows = _row_map(proof_input, "negative_live_attribution_rows")

    missing_modes, incomplete_modes = _complete_rows(
        knowledge_mode_rows,
        REQUIRED_KNOWLEDGE_SOURCE_MODES,
        _knowledge_mode_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        footer_surface_rows,
        REQUIRED_FOOTER_SURFACES,
        _footer_surface_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_live_rows,
        REQUIRED_NEGATIVE_LIVE_FAILURES,
        _negative_failure_ready,
    )

    core_artifacts_bound = all(
        binding["present"] and binding["hash_reproducible"]
        for binding in artifact_bindings.values()
    )
    reference_distribution = proof_input.get("universal_reference_implementation_distribution")
    reference_distribution_l164_ready = bool(
        isinstance(reference_distribution, dict)
        and _summary(reference_distribution).get("status") == "ready"
        and _level_at_least(
            str(_summary(reference_distribution).get("target_certification_level", "")),
            MINIMUM_REFERENCE_DISTRIBUTION_LEVEL,
        )
        and reference_distribution.get("distribution_decision", {}).get(
            "reference_distribution_ready"
        )
        is True
    )
    ready_source_rows = {
        name: row
        for name, row in live_source_rows.items()
        if _live_source_ready(row, min_confidence=min_confidence, min_utility=min_utility)
    }
    all_live_sources_attributed = bool(live_source_rows) and len(ready_source_rows) == len(
        live_source_rows
    )
    no_decorative_citations = all(
        row.get("visible_in_footer") is True
        and row.get("causal_utility_verified") is True
        and row.get("claim_support_verified") is True
        for row in live_source_rows.values()
    ) and bool(live_source_rows)
    no_hidden_payable_sources = _hidden_payable_count(proof_input) == 0
    factual_confidence_gate_passed = all(
        _float(row, "factual_confidence") >= min_confidence
        for row in live_source_rows.values()
    ) and bool(live_source_rows)
    knowledge_source_modes_covered = not missing_modes and not incomplete_modes
    footer_surfaces_preserve_live_proof = not missing_surfaces and not incomplete_surfaces
    settlement_participation_bound = all(
        row.get("settlement_weight_bound") is True
        and str(row.get("settlement_hash", ""))
        and _float(row, "settlement_weight") >= 0.0
        for row in live_source_rows.values()
    ) and bool(live_source_rows)
    attribution_suppression_absent = _suppression_count(proof_input) == 0
    negative_live_fixtures_reject = not missing_negative and not incomplete_negative

    checks = {
        "core_artifacts_bound": core_artifacts_bound,
        "reference_distribution_l164_ready": reference_distribution_l164_ready,
        "all_live_sources_attributed": all_live_sources_attributed,
        "no_decorative_citations": no_decorative_citations,
        "no_hidden_payable_sources": no_hidden_payable_sources,
        "factual_confidence_gate_passed": factual_confidence_gate_passed,
        "knowledge_source_modes_covered": knowledge_source_modes_covered,
        "footer_surfaces_preserve_live_proof": footer_surfaces_preserve_live_proof,
        "settlement_participation_bound": settlement_participation_bound,
        "attribution_suppression_absent": attribution_suppression_absent,
        "negative_live_fixtures_reject": negative_live_fixtures_reject,
        "live_attribution_proof_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    proof_without_privacy: dict[str, Any] = {
        "universal_live_attribution_proof_version": (
            UNIVERSAL_LIVE_ATTRIBUTION_PROOF_VERSION
        ),
        "schema": UNIVERSAL_LIVE_ATTRIBUTION_PROOF_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-live-attribution-proof-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_reference_distribution_level": (
                MINIMUM_REFERENCE_DISTRIBUTION_LEVEL
            ),
            "minimum_factual_confidence": min_confidence,
            "minimum_utility_score": min_utility,
            "posthoc_citation_sufficient": False,
            "answer_accuracy_without_source_attribution_sufficient": False,
            "source_footer_required_before_release": True,
            "creator_settlement_requires_live_proof": True,
            "knowledge_source_classification_required": True,
            "attribution_suppression_blocks_release": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_LIVE_ATTRIBUTION_PROOF_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "live_source_rows": dict(sorted(live_source_rows.items())),
        "knowledge_source_mode_rows": {
            mode: knowledge_mode_rows.get(mode, {})
            for mode in REQUIRED_KNOWLEDGE_SOURCE_MODES
        },
        "footer_surface_rows": {
            surface: footer_surface_rows.get(surface, {})
            for surface in REQUIRED_FOOTER_SURFACES
        },
        "negative_live_attribution_rows": {
            failure: negative_live_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_LIVE_FAILURES
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root(
                [
                    hash_payload({"name": name, "binding": binding})
                    for name, binding in artifact_bindings.items()
                ]
            ),
            "live_source_root": merkle_root(
                [
                    hash_payload({"name": name, "row": row})
                    for name, row in sorted(live_source_rows.items())
                ]
            ),
            "knowledge_source_mode_root": merkle_root(
                [
                    hash_payload({"mode": mode, "row": knowledge_mode_rows.get(mode, {})})
                    for mode in REQUIRED_KNOWLEDGE_SOURCE_MODES
                ]
            ),
            "footer_surface_root": merkle_root(
                [
                    hash_payload(
                        {"surface": surface, "row": footer_surface_rows.get(surface, {})}
                    )
                    for surface in REQUIRED_FOOTER_SURFACES
                ]
            ),
            "negative_live_attribution_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_live_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_LIVE_FAILURES
                ]
            ),
        },
        "checks": checks,
        "attribution_decision": {
            "live_attribution_ready": not failure_modes,
            "response_release_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_release_allowed": not failure_modes,
            "posthoc_footer_only_rejected": True,
            "failure_modes": failure_modes,
            "missing_knowledge_source_modes": missing_modes,
            "incomplete_knowledge_source_modes": incomplete_modes,
            "missing_footer_surfaces": missing_surfaces,
            "incomplete_footer_surfaces": incomplete_surfaces,
            "missing_negative_live_failures": missing_negative,
            "incomplete_negative_live_failures": incomplete_negative,
            "hidden_payable_source_count": _hidden_payable_count(proof_input),
            "attribution_suppression_count": _suppression_count(proof_input),
        },
        "standards_and_research": {
            "source_attribution_in_rag": "https://arxiv.org/abs/2507.04480",
            "cue_r_evidence_utility": "https://arxiv.org/abs/2604.05467",
            "knowledge_source_attribution_probe": "https://arxiv.org/abs/2602.22787",
            "factual_confidence_prediction": "https://arxiv.org/abs/2605.05244",
            "citation_attribution_alignment": "https://arxiv.org/abs/2510.17853",
            "attribution_bias_suppression": "https://arxiv.org/abs/2604.05224",
            "false_citation_negative_control": "https://arxiv.org/abs/2602.11167",
            "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "c2pa": "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html",
            "scitt": "https://scitt.io/",
        },
    }

    private_field_paths = _contains_private_fields(proof_without_privacy)
    private_strings_absent = _private_strings_absent(proof_without_privacy, proof_input)
    proof = {
        **proof_without_privacy,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_answer_disclosed": False,
            "raw_source_text_disclosed": False,
            "private_field_paths": private_field_paths,
            "private_fields_absent": not private_field_paths,
            "private_strings_absent": private_strings_absent,
            "public_rows_are_hash_and_status_only": True,
        },
    }
    if private_field_paths or not private_strings_absent:
        proof["checks"]["private_fields_absent"] = not private_field_paths
        proof["checks"]["private_strings_absent"] = private_strings_absent
        for name in ("private_fields_absent", "private_strings_absent"):
            if not proof["checks"][name] and name not in failure_modes:
                failure_modes.append(name)

    proof["summary"] = {
        "status": "ready" if not failure_modes else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_reference_distribution_level": MINIMUM_REFERENCE_DISTRIBUTION_LEVEL,
        "live_source_count": len(live_source_rows),
        "ready_live_source_count": len(ready_source_rows),
        "knowledge_source_mode_count": len(REQUIRED_KNOWLEDGE_SOURCE_MODES),
        "footer_surface_count": len(REQUIRED_FOOTER_SURFACES),
        "negative_live_failure_count": len(REQUIRED_NEGATIVE_LIVE_FAILURES),
        "failure_mode_count": len(failure_modes),
        "signed_live_attribution_proof": bool(signing_secret),
        "privacy_preserved": not private_field_paths and private_strings_absent,
    }
    proof["universal_live_attribution_proof_hash"] = hash_payload(
        _hashable_proof(proof)
    )
    if signing_secret:
        proof["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_proof(proof), signing_secret),
        }
    return proof


def validate_universal_live_attribution_proof_shape(proof: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L165 live attribution proof."""

    errors: list[str] = []
    required = (
        "universal_live_attribution_proof_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "live_source_rows",
        "knowledge_source_mode_rows",
        "footer_surface_rows",
        "negative_live_attribution_rows",
        "evidence_roots",
        "checks",
        "attribution_decision",
        "privacy",
        "summary",
        "universal_live_attribution_proof_hash",
    )
    for field in required:
        if field not in proof:
            errors.append(f"missing field: {field}")
    if proof.get("universal_live_attribution_proof_version") != (
        UNIVERSAL_LIVE_ATTRIBUTION_PROOF_VERSION
    ):
        errors.append("unexpected universal_live_attribution_proof_version")
    if proof.get("schema") != UNIVERSAL_LIVE_ATTRIBUTION_PROOF_SCHEMA:
        errors.append("unexpected schema")
    if proof.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("unexpected well_known path")
    if proof.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("unexpected target certification level")
    if proof.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("summary target certification level mismatch")
    if proof.get("policy", {}).get("minimum_reference_distribution_level") != (
        MINIMUM_REFERENCE_DISTRIBUTION_LEVEL
    ):
        errors.append("minimum reference distribution level mismatch")
    for collection in (
        "artifact_bindings",
        "live_source_rows",
        "knowledge_source_mode_rows",
        "footer_surface_rows",
        "negative_live_attribution_rows",
    ):
        if collection in proof and not isinstance(proof.get(collection), dict):
            errors.append(f"{collection} must be an object")
    return errors


def verify_universal_live_attribution_proof(
    proof: dict[str, Any],
    *,
    proof_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L165 live attribution proof against private replay inputs."""

    errors = validate_universal_live_attribution_proof_shape(proof)
    expected_hash = hash_payload(_hashable_proof(proof))
    if proof.get("universal_live_attribution_proof_hash") != expected_hash:
        errors.append("universal_live_attribution_proof_hash mismatch")
    if signing_secret:
        signature = proof.get("signature", {})
        expected_signature = sign_payload(_hashable_proof(proof), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")
    private_fields = _contains_private_fields(proof)
    if private_fields:
        errors.append(f"private field leaked: {private_fields[0]}")
    if not _private_strings_absent(proof, proof_input):
        errors.append("private replay string leaked")

    replayed = make_universal_live_attribution_proof(
        proof_input,
        issuer=proof.get("issuer", DEFAULT_ISSUER),
        created_at=proof.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_live_attribution_proof_hash") != proof.get(
        "universal_live_attribution_proof_hash"
    ):
        errors.append("replayed live attribution proof hash mismatch")
    for field in ("checks", "summary", "attribution_decision", "evidence_roots"):
        if replayed.get(field) != proof.get(field):
            errors.append(f"replayed {field} mismatch")
    if proof.get("summary", {}).get("status") != "ready":
        errors.append("live attribution proof is not ready")
    if proof.get("attribution_decision", {}).get("live_attribution_ready") is not True:
        errors.append("live attribution decision not ready")
    if proof.get("checks", {}).get("live_attribution_proof_signed") is not True:
        errors.append("live attribution proof is unsigned")
    return errors
