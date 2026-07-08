"""Universal foundation-model release passport.

The L166 layer makes RDLLM model-version scoped. Earlier layers prove that the
RDLLM stack can be installed and that a concrete answer has live attribution.
This layer binds a named foundation-model release to those proofs so a provider
cannot claim RDLLM compatibility for a model, route, SDK, gateway, or deployment
unless the model identity, training and post-training lineage, source-footer
contract, live attribution proof, revocation path, and settlement meters are all
bound before release.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_VERSION = (
    "rdllm-universal-foundation-model-release-passport/v1"
)
UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_SCHEMA = (
    "docs/schemas/universal_foundation_model_release_passport.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L166"
MINIMUM_LIVE_ATTRIBUTION_LEVEL = "RDLLM-L165"
MINIMUM_REFERENCE_DISTRIBUTION_LEVEL = "RDLLM-L164"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-foundation-model-release-passport.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "proof_dependency_graph",
    "trust_registry",
    "universal_reference_implementation_distribution",
    "universal_live_attribution_proof",
    "universal_foundation_model_contract",
    "universal_training_serving_contract",
    "universal_composite_rdllm_profile",
    "universal_runtime_conformance_receipt",
    "universal_provider_wire_protocol",
    "universal_grounded_reliance_contract",
    "universal_reliance_correction_ledger",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_PROVIDER_RELEASE_ROUTES = (
    "openai_responses_api",
    "anthropic_messages_api",
    "google_gemini_generate_content",
    "meta_llama_stack",
    "mistral_chat_api",
    "cohere_chat_api",
    "xai_grok_api",
    "deepseek_chat_api",
    "azure_openai_responses",
    "aws_bedrock_converse",
    "openrouter_chat_completions",
    "local_openai_compatible_runtime",
    "open_weight_runtime",
    "enterprise_gateway_proxy",
)

REQUIRED_RELEASE_LIFECYCLE_DOMAINS = (
    "model_identity",
    "training_content_transparency",
    "copyright_and_tdm_policy",
    "post_training_lineage",
    "distillation_and_synthetic_data",
    "adapter_and_fine_tune_deltas",
    "evaluation_and_safety",
    "live_attribution_enforcement",
    "source_footer_delivery",
    "royalty_settlement",
    "revocation_and_correction",
    "downstream_developer_documentation",
)

REQUIRED_COMPLIANCE_MAPPINGS = (
    "eu_ai_act_gpai_transparency",
    "nist_ai_rmf_genai_profile",
    "model_cards_and_downstream_docs",
    "openssf_model_signing",
    "slsa_in_toto_supply_chain",
    "c2pa_content_credentials",
    "scitt_transparency_statements",
    "opentelemetry_genai",
    "aibom_cyclonedx_spdx",
    "w3c_verifiable_credentials",
)

REQUIRED_NEGATIVE_RELEASE_FAILURES = (
    "unregistered_model_version",
    "model_hash_or_attestation_mismatch",
    "missing_training_summary",
    "copyright_policy_unbound",
    "tdm_opt_out_not_enforced",
    "post_training_lineage_gap",
    "unsupported_provider_route",
    "route_without_live_attribution",
    "sdk_or_gateway_strips_release_passport",
    "revoked_model_release_still_served",
    "settlement_without_model_passport",
    "private_training_or_customer_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_foundation_model_release_passport_hash",
    "universal_live_attribution_proof_hash",
    "universal_reference_implementation_distribution_hash",
    "universal_foundation_model_contract_hash",
    "universal_training_serving_contract_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_provider_wire_protocol_hash",
    "universal_grounded_reliance_contract_hash",
    "universal_reliance_correction_ledger_hash",
    "revenue_allocation_hash",
    "finance_ledger_attestation_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "graph_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "envelope_hash",
    "event_hash",
    "package_hash",
    "distribution_hash",
    "model_release_hash",
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
    "training_text",
    "training_record",
    "raw_training_record",
    "dataset_sample",
    "fine_tune_example",
    "reward_text",
    "preference_text",
    "distillation_output",
    "synthetic_record",
    "adapter_delta_raw",
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


def load_universal_foundation_model_release_passport_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L166 model-release passport."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_passport(passport: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in passport.items()
        if key not in {"universal_foundation_model_release_passport_hash", "signature"}
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


def _artifact_bindings(passport_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: _artifact_binding(
            name,
            passport_input.get(name)
            if isinstance(passport_input.get(name), dict)
            else None,
        )
        for name in REQUIRED_CORE_ARTIFACTS
    }


def _row_map(passport_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = passport_input.get(key, {})
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


def _private_strings_absent(
    public_payload: dict[str, Any],
    passport_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in passport_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _release_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "provider_subject_hash",
        "model_identity_hash",
        "model_artifact_or_attestation_hash",
        "model_signing_hash",
        "training_summary_hash",
        "copyright_policy_hash",
        "tdm_reservation_policy_hash",
        "post_training_lineage_hash",
        "live_attribution_proof_hash",
        "settlement_contract_hash",
        "revocation_status_hash",
        "downstream_documentation_hash",
    )
    required_flags = (
        "model_id_bound",
        "provider_subject_verified",
        "model_version_bound",
        "signed_model_or_closed_weight_attested",
        "training_content_summary_published",
        "copyright_policy_bound",
        "tdm_opt_out_policy_enforced",
        "post_training_lineage_bound",
        "live_attribution_required_for_all_outputs",
        "downstream_docs_available",
        "settlement_policy_bound",
        "revocation_policy_bound",
        "private_payloads_excluded",
    )
    return (
        str(row.get("provider_family", ""))
        and str(row.get("model_id", ""))
        and str(row.get("model_version", ""))
        and str(row.get("release_status", "")) == "ready"
        and all(str(row.get(field, "")) for field in required_hashes)
        and all(row.get(flag) is True for flag in required_flags)
    )


def _route_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "route_contract_hash",
        "adapter_hash",
        "telemetry_hash",
        "source_footer_hash",
        "live_proof_hash",
        "settlement_meter_hash",
        "refusal_path_hash",
    )
    required_flags = (
        "route_supported",
        "adapter_verified",
        "live_attribution_enforced",
        "streaming_and_batch_covered",
        "copy_export_covered",
        "fallback_routes_blocked",
        "settlement_meter_bound",
        "private_payloads_excluded",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _lifecycle_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("control_hash", "evidence_hash", "verifier_hash", "policy_hash")
    required_flags = (
        "control_supported",
        "evidence_bound",
        "verifier_available",
        "release_gate_bound",
        "failure_holds_release",
        "private_payloads_excluded",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _compliance_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("mapping_hash", "evidence_hash", "control_owner_hash", "export_hash")
    required_flags = (
        "mapped",
        "machine_readable",
        "public_or_auditor_accessible",
        "release_gate_bound",
        "drift_review_bound",
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
            "model_release_blocked",
            "invocation_blocked",
            "footer_reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    )


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


def _certification_l165_ready(certification_report: dict[str, Any] | None) -> bool:
    summary = _summary(certification_report)
    levels = (
        certification_report.get("levels", {})
        if isinstance(certification_report, dict)
        else {}
    )
    l165 = levels.get(MINIMUM_LIVE_ATTRIBUTION_LEVEL, {}) if isinstance(levels, dict) else {}
    return (
        summary.get("status") == "passed"
        and _level_at_least(summary.get("highest_level", ""), MINIMUM_LIVE_ATTRIBUTION_LEVEL)
        and isinstance(l165, dict)
        and l165.get("passed") is True
    )


def _live_attribution_l165_ready(proof: dict[str, Any] | None) -> bool:
    if not isinstance(proof, dict):
        return False
    return (
        _summary(proof).get("status") == "ready"
        and _level_at_least(
            _summary(proof).get("target_certification_level", ""),
            MINIMUM_LIVE_ATTRIBUTION_LEVEL,
        )
        and proof.get("attribution_decision", {}).get("live_attribution_ready") is True
        and proof.get("attribution_decision", {}).get("response_release_allowed") is True
    )


def _reference_distribution_l164_ready(distribution: dict[str, Any] | None) -> bool:
    if not isinstance(distribution, dict):
        return False
    return (
        _summary(distribution).get("status") == "ready"
        and _level_at_least(
            _summary(distribution).get("target_certification_level", ""),
            MINIMUM_REFERENCE_DISTRIBUTION_LEVEL,
        )
        and distribution.get("distribution_decision", {}).get(
            "reference_distribution_ready"
        )
        is True
    )


def make_universal_foundation_model_release_passport(
    passport_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L166 model-version release passport."""

    artifact_bindings = _artifact_bindings(passport_input)
    model_release_rows = _row_map(passport_input, "model_release_rows")
    route_rows = _row_map(passport_input, "provider_route_rows")
    lifecycle_rows = _row_map(passport_input, "release_lifecycle_rows")
    compliance_rows = _row_map(passport_input, "compliance_mapping_rows")
    negative_rows = _row_map(passport_input, "negative_model_release_rows")

    missing_routes, incomplete_routes = _complete_rows(
        route_rows,
        REQUIRED_PROVIDER_RELEASE_ROUTES,
        _route_row_ready,
    )
    missing_lifecycle, incomplete_lifecycle = _complete_rows(
        lifecycle_rows,
        REQUIRED_RELEASE_LIFECYCLE_DOMAINS,
        _lifecycle_row_ready,
    )
    missing_compliance, incomplete_compliance = _complete_rows(
        compliance_rows,
        REQUIRED_COMPLIANCE_MAPPINGS,
        _compliance_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_RELEASE_FAILURES,
        _negative_failure_ready,
    )

    ready_release_rows = {
        name: row for name, row in model_release_rows.items() if _release_row_ready(row)
    }
    model_identity_hashes = [
        str(row.get("model_identity_hash", ""))
        for row in model_release_rows.values()
        if str(row.get("model_identity_hash", ""))
    ]
    release_claims_bound = all(
        str(row.get("model_id", ""))
        and str(row.get("model_version", ""))
        and row.get("model_id_bound") is True
        and row.get("model_version_bound") is True
        for row in model_release_rows.values()
    ) and bool(model_release_rows)
    settlement_and_revocation_bound = all(
        row.get("settlement_policy_bound") is True
        and row.get("revocation_policy_bound") is True
        and str(row.get("settlement_contract_hash", ""))
        and str(row.get("revocation_status_hash", ""))
        for row in model_release_rows.values()
    ) and bool(model_release_rows)

    checks = {
        "core_artifacts_bound": all(
            binding["present"] and binding["hash_reproducible"]
            for binding in artifact_bindings.values()
        ),
        "certification_l165_or_higher_passed": _certification_l165_ready(
            passport_input.get("certification_report")
        ),
        "reference_distribution_l164_ready": _reference_distribution_l164_ready(
            passport_input.get("universal_reference_implementation_distribution")
        ),
        "live_attribution_l165_ready": _live_attribution_l165_ready(
            passport_input.get("universal_live_attribution_proof")
        ),
        "model_release_rows_ready": bool(model_release_rows)
        and len(ready_release_rows) == len(model_release_rows),
        "model_identity_unique": bool(model_identity_hashes)
        and len(model_identity_hashes) == len(set(model_identity_hashes)),
        "release_claims_bound_to_model_versions": release_claims_bound,
        "provider_route_coverage_complete": not missing_routes
        and not incomplete_routes,
        "release_lifecycle_controls_complete": not missing_lifecycle
        and not incomplete_lifecycle,
        "compliance_mappings_complete": not missing_compliance
        and not incomplete_compliance,
        "settlement_and_revocation_bound": settlement_and_revocation_bound,
        "negative_model_release_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "model_release_passport_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    passport_without_privacy: dict[str, Any] = {
        "universal_foundation_model_release_passport_version": (
            UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_VERSION
        ),
        "schema": UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-foundation-model-release-passport-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_live_attribution_level": MINIMUM_LIVE_ATTRIBUTION_LEVEL,
            "minimum_reference_distribution_level": (
                MINIMUM_REFERENCE_DISTRIBUTION_LEVEL
            ),
            "model_release_claim_requires_passport": True,
            "provider_invocation_requires_passport": True,
            "source_footer_reliance_requires_live_passport": True,
            "creator_settlement_requires_model_release_binding": True,
            "training_summary_and_copyright_policy_required": True,
            "closed_weight_models_require_attested_model_identity": True,
            "unsupported_provider_routes_fail_closed": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "model_release_rows": dict(sorted(model_release_rows.items())),
        "provider_route_rows": {
            route: route_rows.get(route, {})
            for route in REQUIRED_PROVIDER_RELEASE_ROUTES
        },
        "release_lifecycle_rows": {
            domain: lifecycle_rows.get(domain, {})
            for domain in REQUIRED_RELEASE_LIFECYCLE_DOMAINS
        },
        "compliance_mapping_rows": {
            mapping: compliance_rows.get(mapping, {})
            for mapping in REQUIRED_COMPLIANCE_MAPPINGS
        },
        "negative_model_release_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_RELEASE_FAILURES
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root(
                [
                    hash_payload({"name": name, "binding": binding})
                    for name, binding in artifact_bindings.items()
                ]
            ),
            "model_release_root": merkle_root(
                [
                    hash_payload({"name": name, "row": row})
                    for name, row in sorted(model_release_rows.items())
                ]
            ),
            "provider_route_root": merkle_root(
                [
                    hash_payload({"route": route, "row": route_rows.get(route, {})})
                    for route in REQUIRED_PROVIDER_RELEASE_ROUTES
                ]
            ),
            "release_lifecycle_root": merkle_root(
                [
                    hash_payload(
                        {"domain": domain, "row": lifecycle_rows.get(domain, {})}
                    )
                    for domain in REQUIRED_RELEASE_LIFECYCLE_DOMAINS
                ]
            ),
            "compliance_mapping_root": merkle_root(
                [
                    hash_payload(
                        {"mapping": mapping, "row": compliance_rows.get(mapping, {})}
                    )
                    for mapping in REQUIRED_COMPLIANCE_MAPPINGS
                ]
            ),
            "negative_model_release_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_RELEASE_FAILURES
                ]
            ),
        },
        "checks": checks,
        "release_decision": {
            "model_release_passport_ready": not failure_modes,
            "model_release_claim_allowed": not failure_modes,
            "provider_invocation_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_release_allowed": not failure_modes,
            "failure_modes": failure_modes,
            "missing_provider_routes": missing_routes,
            "incomplete_provider_routes": incomplete_routes,
            "missing_lifecycle_domains": missing_lifecycle,
            "incomplete_lifecycle_domains": incomplete_lifecycle,
            "missing_compliance_mappings": missing_compliance,
            "incomplete_compliance_mappings": incomplete_compliance,
            "missing_negative_release_failures": missing_negative,
            "incomplete_negative_release_failures": incomplete_negative,
        },
        "standards_and_research": {
            "eu_gpai_code_of_practice": "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai",
            "nist_ai_rmf_generative_ai_profile": "https://www.nist.gov/itl/ai-risk-management-framework",
            "openssf_model_signing": "https://openssf.org/blog/2025/06/05/model-signing-is-here/",
            "slsa": "https://slsa.dev/spec/latest/",
            "in_toto": "https://in-toto.io/",
            "c2pa": "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html",
            "scitt": "https://scitt.io/",
            "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "model_cards": "https://arxiv.org/abs/1810.03993",
            "data_sheets_for_datasets": "https://arxiv.org/abs/1803.09010",
            "data_attribution_for_diffusion_models": "https://arxiv.org/abs/2311.00500",
        },
    }

    private_field_paths = _contains_private_fields(passport_without_privacy)
    private_strings_absent = _private_strings_absent(
        passport_without_privacy, passport_input
    )
    passport = {
        **passport_without_privacy,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_answer_disclosed": False,
            "raw_training_text_disclosed": False,
            "raw_customer_record_disclosed": False,
            "private_field_paths": private_field_paths,
            "private_fields_absent": not private_field_paths,
            "private_strings_absent": private_strings_absent,
            "public_rows_are_hash_status_and_policy_only": True,
        },
    }
    if private_field_paths or not private_strings_absent:
        passport["checks"]["private_fields_absent"] = not private_field_paths
        passport["checks"]["private_strings_absent"] = private_strings_absent
        for name in ("private_fields_absent", "private_strings_absent"):
            if not passport["checks"][name] and name not in failure_modes:
                failure_modes.append(name)

    passport["summary"] = {
        "status": "ready" if not failure_modes else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_live_attribution_level": MINIMUM_LIVE_ATTRIBUTION_LEVEL,
        "minimum_reference_distribution_level": MINIMUM_REFERENCE_DISTRIBUTION_LEVEL,
        "model_release_count": len(model_release_rows),
        "ready_model_release_count": len(ready_release_rows),
        "provider_route_count": len(REQUIRED_PROVIDER_RELEASE_ROUTES),
        "release_lifecycle_domain_count": len(REQUIRED_RELEASE_LIFECYCLE_DOMAINS),
        "compliance_mapping_count": len(REQUIRED_COMPLIANCE_MAPPINGS),
        "negative_release_failure_count": len(REQUIRED_NEGATIVE_RELEASE_FAILURES),
        "failure_mode_count": len(failure_modes),
        "signed_model_release_passport": bool(signing_secret),
        "privacy_preserved": not private_field_paths and private_strings_absent,
    }
    passport["universal_foundation_model_release_passport_hash"] = hash_payload(
        _hashable_passport(passport)
    )
    if signing_secret:
        passport["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_passport(passport), signing_secret),
        }
    return passport


def validate_universal_foundation_model_release_passport_shape(
    passport: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L166 model-release passport."""

    errors: list[str] = []
    required = (
        "universal_foundation_model_release_passport_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "model_release_rows",
        "provider_route_rows",
        "release_lifecycle_rows",
        "compliance_mapping_rows",
        "negative_model_release_rows",
        "evidence_roots",
        "checks",
        "release_decision",
        "privacy",
        "summary",
        "universal_foundation_model_release_passport_hash",
    )
    for field in required:
        if field not in passport:
            errors.append(f"missing field: {field}")
    if passport.get("universal_foundation_model_release_passport_version") != (
        UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_VERSION
    ):
        errors.append("unexpected universal_foundation_model_release_passport_version")
    if passport.get("schema") != UNIVERSAL_FOUNDATION_MODEL_RELEASE_PASSPORT_SCHEMA:
        errors.append("unexpected schema")
    if passport.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("unexpected well_known path")
    if passport.get("policy", {}).get("target_certification_level") != (
        TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("unexpected target certification level")
    if passport.get("summary", {}).get("target_certification_level") != (
        TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("summary target certification level mismatch")
    for collection in (
        "artifact_bindings",
        "model_release_rows",
        "provider_route_rows",
        "release_lifecycle_rows",
        "compliance_mapping_rows",
        "negative_model_release_rows",
    ):
        if collection in passport and not isinstance(passport.get(collection), dict):
            errors.append(f"{collection} must be an object")
    return errors


def verify_universal_foundation_model_release_passport(
    passport: dict[str, Any],
    *,
    passport_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L166 model-release passport against private replay inputs."""

    errors = validate_universal_foundation_model_release_passport_shape(passport)
    expected_hash = hash_payload(_hashable_passport(passport))
    if passport.get("universal_foundation_model_release_passport_hash") != expected_hash:
        errors.append("universal_foundation_model_release_passport_hash mismatch")
    if signing_secret:
        signature = passport.get("signature", {})
        expected_signature = sign_payload(_hashable_passport(passport), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")
    private_fields = _contains_private_fields(passport)
    if private_fields:
        errors.append(f"private field leaked: {private_fields[0]}")
    if not _private_strings_absent(passport, passport_input):
        errors.append("private replay string leaked")

    replayed = make_universal_foundation_model_release_passport(
        passport_input,
        issuer=passport.get("issuer", DEFAULT_ISSUER),
        created_at=passport.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_foundation_model_release_passport_hash") != passport.get(
        "universal_foundation_model_release_passport_hash"
    ):
        errors.append("replayed model release passport hash mismatch")
    for field in ("checks", "summary", "release_decision", "evidence_roots"):
        if replayed.get(field) != passport.get(field):
            errors.append(f"replayed {field} mismatch")
    if passport.get("summary", {}).get("status") != "ready":
        errors.append("model release passport is not ready")
    if passport.get("release_decision", {}).get("model_release_passport_ready") is not True:
        errors.append("model release decision not ready")
    if passport.get("checks", {}).get("model_release_passport_signed") is not True:
        errors.append("model release passport is unsigned")
    return errors
