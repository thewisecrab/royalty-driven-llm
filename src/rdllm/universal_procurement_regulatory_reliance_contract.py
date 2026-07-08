"""Universal procurement and regulatory reliance contracts.

The L174 layer turns the L173 adversarial provenance quorum into an adoption
object that buyers, marketplaces, routers, regulators, creator collectives, and
payment processors can require before accepting a provider's attribution claim.
It is deliberately contractual as well as technical: if terms, procurement
gates, regulator exports, source footers, or settlement remedies do not bind to
the L173 quorum, reliance fails closed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_VERSION = (
    "rdllm-universal-procurement-regulatory-reliance-contract/v1"
)
UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_SCHEMA = (
    "docs/schemas/universal_procurement_regulatory_reliance_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L174"
MINIMUM_ADVERSARIAL_PROVENANCE_LEVEL = "RDLLM-L173"
MINIMUM_INDUSTRY_ADOPTION_ROOT_LEVEL = "RDLLM-L163"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-procurement-regulatory-reliance-contract.json"
)

REQUIRED_ADOPTION_ROLES = (
    "foundation_model_provider",
    "api_gateway_or_router",
    "cloud_marketplace",
    "enterprise_customer",
    "application_developer",
    "auditor_or_lab",
    "regulator_or_court",
    "creator_collective",
    "payment_processor",
    "end_user_surface",
)

REQUIRED_CONTRACTUAL_CONTROLS = (
    "conformance_claim_binding",
    "model_version_binding",
    "source_footer_display_duty",
    "machine_readable_source_duty",
    "distribution_survival_duty",
    "adversarial_quorum_duty",
    "audit_right",
    "regulator_export",
    "creator_challenge_route",
    "settlement_hold_and_remedy",
    "revocation_and_correction_sla",
    "procurement_sla",
    "marketplace_delisting",
)

REQUIRED_JURISDICTION_MAPPINGS = (
    "copyright_and_ai_training_disclosure",
    "eu_ai_act_gpai_summary",
    "us_copyright_record",
    "uk_tdm_reservation",
    "data_protection_privacy",
    "consumer_deception_disclosure",
    "accessibility_and_machine_readability",
    "payment_and_tax_reporting",
)

REQUIRED_NEGATIVE_PROCUREMENT_FAILURES = (
    "unbound_conformance_claim",
    "terms_override_creator_payment",
    "model_version_substitution",
    "router_bypass",
    "marketplace_listing_without_proof",
    "missing_audit_right",
    "missing_regulator_export",
    "revoked_trust_root_accepted",
    "settlement_hold_unenforceable",
    "creator_challenge_unroutable",
    "jurisdiction_mapping_missing",
    "sla_missing_or_unmeasured",
    "source_footer_removed_in_terms",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_procurement_regulatory_reliance_contract_hash",
    "universal_adversarial_provenance_quorum_hash",
    "universal_industry_adoption_root_hash",
    "universal_distribution_reliance_passport_hash",
    "universal_source_grounded_response_receipt_hash",
    "provider_attribution_card_hash",
    "integration_profile_hash",
    "discovery_manifest_hash",
    "assurance_bundle_hash",
    "proof_dependency_graph_hash",
    "role_hash",
    "contract_hash",
    "l173_quorum_hash",
    "authority_hash",
    "endpoint_hash",
    "control_hash",
    "obligation_hash",
    "evidence_hash",
    "enforcement_hash",
    "remedy_hash",
    "jurisdiction_hash",
    "mapping_hash",
    "evidence_export_hash",
    "fixture_hash",
    "route_trace_hash",
    "verifier_hash",
    "trace_hash",
    "span_hash",
    "receipt_hash",
    "attestation_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
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
    "copied_output",
    "rendered_output",
    "distributed_output",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "contract_terms_text",
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


def load_universal_procurement_regulatory_reliance_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L174 procurement reliance contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key
        not in {
            "universal_procurement_regulatory_reliance_contract_hash",
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
    contract_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in contract_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _adversarial_quorum_ready(quorum: dict[str, Any] | None) -> bool:
    if not isinstance(quorum, dict):
        return False
    summary = _summary(quorum)
    decision = quorum.get("adversarial_quorum_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_ADVERSARIAL_PROVENANCE_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("adversarial_provenance_quorum_ready") is True
        and decision.get("high_stakes_reliance_allowed") is True
        and decision.get("third_party_distribution_reliance_allowed") is True
        and decision.get("creator_settlement_release_allowed") is True
        and not decision.get("failure_modes", [])
    )


def _industry_adoption_root_ready(root: dict[str, Any] | None) -> bool:
    if not isinstance(root, dict):
        return False
    summary = _summary(root)
    decision = root.get("adoption_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_INDUSTRY_ADOPTION_ROOT_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("industry_adoption_root_ready") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("creator_settlement_release_allowed") is True
        and not decision.get("failure_modes", [])
    )


def _role_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "role_hash",
        "contract_hash",
        "l173_quorum_hash",
        "authority_hash",
        "endpoint_hash",
        "verifier_hash",
    )
    required_flags = (
        "accepts_rdllm_standard",
        "binds_l173_quorum",
        "publishes_well_known_contract",
        "blocks_unbound_claims",
        "preserves_footer_or_machine_readable_sources",
        "supports_creator_challenge",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _control_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "control_hash",
        "obligation_hash",
        "evidence_hash",
        "enforcement_hash",
        "remedy_hash",
        "verifier_hash",
    )
    required_flags = (
        "obligation_binding",
        "measurable_sla",
        "audit_evidence_exported",
        "breach_blocks_reliance",
        "settlement_or_display_remedy",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _jurisdiction_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "jurisdiction_hash",
        "obligation_hash",
        "mapping_hash",
        "evidence_export_hash",
        "verifier_hash",
    )
    required_flags = (
        "maps_to_provider_duty",
        "maps_to_customer_duty",
        "regulator_readable",
        "creator_readable",
        "footer_and_machine_readable_attribution_supported",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "fixture_hash",
        "route_trace_hash",
        "contract_hash",
        "verifier_hash",
    )
    required_flags = (
        "expected_reject",
        "observed_reject",
        "procurement_blocked",
        "marketplace_delisted",
        "regulator_warning_emitted",
        "settlement_held",
        "creator_challenge_routed",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _row_map(contract_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = contract_input.get(key, {})
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


def make_universal_procurement_regulatory_reliance_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L174 universal procurement and regulatory reliance contract."""

    adversarial_quorum = contract_input.get("universal_adversarial_provenance_quorum")
    industry_root = contract_input.get("universal_industry_adoption_root")
    role_rows = _row_map(contract_input, "adoption_role_rows")
    control_rows = _row_map(contract_input, "contractual_control_rows")
    jurisdiction_rows = _row_map(contract_input, "jurisdiction_mapping_rows")
    negative_rows = _row_map(contract_input, "negative_procurement_rows")

    missing_roles, incomplete_roles = _complete_rows(
        role_rows,
        REQUIRED_ADOPTION_ROLES,
        _role_row_ready,
    )
    missing_controls, incomplete_controls = _complete_rows(
        control_rows,
        REQUIRED_CONTRACTUAL_CONTROLS,
        _control_row_ready,
    )
    missing_jurisdictions, incomplete_jurisdictions = _complete_rows(
        jurisdiction_rows,
        REQUIRED_JURISDICTION_MAPPINGS,
        _jurisdiction_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_PROCUREMENT_FAILURES,
        _negative_row_ready,
    )

    checks = {
        "adversarial_provenance_quorum_bound": _artifact_hash_is_reproducible(
            adversarial_quorum if isinstance(adversarial_quorum, dict) else None
        ),
        "adversarial_provenance_quorum_l173_ready": _adversarial_quorum_ready(
            adversarial_quorum if isinstance(adversarial_quorum, dict) else None
        ),
        "industry_adoption_root_bound": _artifact_hash_is_reproducible(
            industry_root if isinstance(industry_root, dict) else None
        ),
        "industry_adoption_root_l163_ready": _industry_adoption_root_ready(
            industry_root if isinstance(industry_root, dict) else None
        ),
        "adoption_role_rows_complete": not missing_roles and not incomplete_roles,
        "contractual_control_rows_complete": not missing_controls
        and not incomplete_controls,
        "jurisdiction_mapping_rows_complete": not missing_jurisdictions
        and not incomplete_jurisdictions,
        "negative_procurement_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "procurement_reliance_contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    role_root = merkle_root([
        hash_payload({"name": name, "row": role_rows.get(name, {})})
        for name in REQUIRED_ADOPTION_ROLES
    ])
    control_root = merkle_root([
        hash_payload({"name": name, "row": control_rows.get(name, {})})
        for name in REQUIRED_CONTRACTUAL_CONTROLS
    ])
    jurisdiction_root = merkle_root([
        hash_payload({"name": name, "row": jurisdiction_rows.get(name, {})})
        for name in REQUIRED_JURISDICTION_MAPPINGS
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
    ])

    public = {
        "universal_procurement_regulatory_reliance_contract_version": (
            UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-procurement-regulatory-reliance-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_adversarial_provenance_level": (
                MINIMUM_ADVERSARIAL_PROVENANCE_LEVEL
            ),
            "minimum_industry_adoption_root_level": (
                MINIMUM_INDUSTRY_ADOPTION_ROOT_LEVEL
            ),
            "provider_terms_must_not_override_creator_payment": True,
            "source_footer_and_machine_readable_attribution_survive_distribution": True,
            "marketplace_listing_requires_current_l173_quorum": True,
            "regulator_export_required": True,
            "creator_challenge_route_required": True,
            "settlement_hold_required_on_contract_breach": True,
            "private_payloads_forbidden_in_public_contract": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_VERSION,
        },
        "adversarial_quorum_binding": {
            "present": isinstance(adversarial_quorum, dict),
            "artifact_hash": _declared_hash(
                adversarial_quorum if isinstance(adversarial_quorum, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    adversarial_quorum if isinstance(adversarial_quorum, dict) else None
                )
            ),
            "hash_reproducible": checks["adversarial_provenance_quorum_bound"],
            "status": _summary(
                adversarial_quorum if isinstance(adversarial_quorum, dict) else None
            ).get("status", ""),
            "level": _summary(
                adversarial_quorum if isinstance(adversarial_quorum, dict) else None
            ).get("target_certification_level", ""),
        },
        "industry_root_binding": {
            "present": isinstance(industry_root, dict),
            "artifact_hash": _declared_hash(
                industry_root if isinstance(industry_root, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    industry_root if isinstance(industry_root, dict) else None
                )
            ),
            "hash_reproducible": checks["industry_adoption_root_bound"],
            "status": _summary(
                industry_root if isinstance(industry_root, dict) else None
            ).get("status", ""),
            "level": _summary(
                industry_root if isinstance(industry_root, dict) else None
            ).get("target_certification_level", ""),
        },
        "adoption_role_rows": role_rows,
        "contractual_control_rows": control_rows,
        "jurisdiction_mapping_rows": jurisdiction_rows,
        "negative_procurement_rows": negative_rows,
        "evidence_roots": {
            "adoption_role_root": role_root,
            "contractual_control_root": control_root,
            "jurisdiction_mapping_root": jurisdiction_root,
            "negative_procurement_root": negative_root,
        },
        "checks": checks,
        "procurement_reliance_decision": {
            "procurement_reliance_ready": ready,
            "provider_conformance_claim_allowed": ready,
            "marketplace_listing_allowed": ready,
            "enterprise_procurement_allowed": ready,
            "regulator_reliance_allowed": ready,
            "creator_collective_reliance_allowed": ready,
            "settlement_contract_enforceable": ready,
            "source_footer_contract_enforceable": ready,
            "noncompliant_routes_blocked": ready,
            "failure_modes": failure_modes,
            "missing_adoption_roles": missing_roles,
            "incomplete_adoption_roles": incomplete_roles,
            "missing_contractual_controls": missing_controls,
            "incomplete_contractual_controls": incomplete_controls,
            "missing_jurisdiction_mappings": missing_jurisdictions,
            "incomplete_jurisdiction_mappings": incomplete_jurisdictions,
            "missing_negative_procurement_failures": missing_negative,
            "incomplete_negative_procurement_failures": incomplete_negative,
        },
        "contract_coverage": {
            "required_adoption_role_count": len(REQUIRED_ADOPTION_ROLES),
            "ready_adoption_role_count": len(REQUIRED_ADOPTION_ROLES)
            - len(missing_roles)
            - len(incomplete_roles),
            "required_contractual_control_count": len(REQUIRED_CONTRACTUAL_CONTROLS),
            "ready_contractual_control_count": len(REQUIRED_CONTRACTUAL_CONTROLS)
            - len(missing_controls)
            - len(incomplete_controls),
            "required_jurisdiction_mapping_count": len(REQUIRED_JURISDICTION_MAPPINGS),
            "ready_jurisdiction_mapping_count": len(REQUIRED_JURISDICTION_MAPPINGS)
            - len(missing_jurisdictions)
            - len(incomplete_jurisdictions),
            "required_negative_procurement_failure_count": len(
                REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
            ),
            "ready_negative_procurement_failure_count": len(
                REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
        },
        "privacy": {
            "private_payload_fields": [],
            "private_strings_absent": True,
            "private_payloads_excluded": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_adversarial_provenance_level": (
                MINIMUM_ADVERSARIAL_PROVENANCE_LEVEL
            ),
            "minimum_industry_adoption_root_level": (
                MINIMUM_INDUSTRY_ADOPTION_ROOT_LEVEL
            ),
            "adoption_role_count": len(REQUIRED_ADOPTION_ROLES),
            "ready_adoption_role_count": len(REQUIRED_ADOPTION_ROLES)
            - len(missing_roles)
            - len(incomplete_roles),
            "contractual_control_count": len(REQUIRED_CONTRACTUAL_CONTROLS),
            "ready_contractual_control_count": len(REQUIRED_CONTRACTUAL_CONTROLS)
            - len(missing_controls)
            - len(incomplete_controls),
            "jurisdiction_mapping_count": len(REQUIRED_JURISDICTION_MAPPINGS),
            "ready_jurisdiction_mapping_count": len(REQUIRED_JURISDICTION_MAPPINGS)
            - len(missing_jurisdictions)
            - len(incomplete_jurisdictions),
            "negative_procurement_failure_count": len(
                REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
            ),
            "ready_negative_procurement_failure_count": len(
                REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_procurement_reliance_contract": signing_secret is not None,
        },
    }
    public["privacy"]["private_payload_fields"] = _contains_private_fields(public)
    public["privacy"]["private_strings_absent"] = _private_strings_absent(
        public,
        contract_input,
    )
    public["privacy"]["private_payloads_excluded"] = (
        not public["privacy"]["private_payload_fields"]
        and public["privacy"]["private_strings_absent"]
    )
    if not public["privacy"]["private_payloads_excluded"]:
        public["checks"]["private_payloads_excluded"] = False
        for decision in (
            "procurement_reliance_ready",
            "provider_conformance_claim_allowed",
            "marketplace_listing_allowed",
            "enterprise_procurement_allowed",
            "regulator_reliance_allowed",
            "creator_collective_reliance_allowed",
            "settlement_contract_enforceable",
            "source_footer_contract_enforceable",
            "noncompliant_routes_blocked",
        ):
            public["procurement_reliance_decision"][decision] = False
        if "private_payloads_excluded" not in public[
            "procurement_reliance_decision"
        ]["failure_modes"]:
            public["procurement_reliance_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["procurement_reliance_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_procurement_regulatory_reliance_contract_hash"] = hash_payload(
        _hashable_contract(public)
    )
    if signing_secret:
        public["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_contract(public), signing_secret),
        }
    return public


def validate_universal_procurement_regulatory_reliance_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L174 reliance contract."""

    errors: list[str] = []
    required = (
        "universal_procurement_regulatory_reliance_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "adversarial_quorum_binding",
        "industry_root_binding",
        "adoption_role_rows",
        "contractual_control_rows",
        "jurisdiction_mapping_rows",
        "negative_procurement_rows",
        "evidence_roots",
        "checks",
        "procurement_reliance_decision",
        "contract_coverage",
        "privacy",
        "summary",
        "universal_procurement_regulatory_reliance_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing procurement reliance contract field: {key}")
    if contract.get("universal_procurement_regulatory_reliance_contract_version") != (
        UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_VERSION
    ):
        errors.append(
            "unexpected universal_procurement_regulatory_reliance_contract_version"
        )
    if contract.get("schema") != (
        UNIVERSAL_PROCUREMENT_REGULATORY_RELIANCE_CONTRACT_SCHEMA
    ):
        errors.append("unexpected procurement reliance contract schema")
    for name in REQUIRED_ADOPTION_ROLES:
        if name not in contract.get("adoption_role_rows", {}):
            errors.append(f"missing adoption role row: {name}")
    for name in REQUIRED_CONTRACTUAL_CONTROLS:
        if name not in contract.get("contractual_control_rows", {}):
            errors.append(f"missing contractual control row: {name}")
    for name in REQUIRED_JURISDICTION_MAPPINGS:
        if name not in contract.get("jurisdiction_mapping_rows", {}):
            errors.append(f"missing jurisdiction mapping row: {name}")
    for name in REQUIRED_NEGATIVE_PROCUREMENT_FAILURES:
        if name not in contract.get("negative_procurement_rows", {}):
            errors.append(f"missing negative procurement row: {name}")
    for check in (
        "adversarial_provenance_quorum_bound",
        "adversarial_provenance_quorum_l173_ready",
        "industry_adoption_root_bound",
        "industry_adoption_root_l163_ready",
        "adoption_role_rows_complete",
        "contractual_control_rows_complete",
        "jurisdiction_mapping_rows_complete",
        "negative_procurement_fixtures_reject",
        "procurement_reliance_contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing procurement reliance contract check: {check}")
    return errors


def verify_universal_procurement_regulatory_reliance_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L174 reliance contract against replay input."""

    errors = validate_universal_procurement_regulatory_reliance_contract_shape(
        contract
    )
    expected_hash = hash_payload(_hashable_contract(contract))
    if (
        contract.get("universal_procurement_regulatory_reliance_contract_hash")
        != expected_hash
    ):
        errors.append(
            "universal_procurement_regulatory_reliance_contract_hash mismatch"
        )
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "procurement reliance contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("procurement reliance contract exposes private input strings")
    replayed = make_universal_procurement_regulatory_reliance_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get(
        "universal_procurement_regulatory_reliance_contract_hash"
    ) != contract.get("universal_procurement_regulatory_reliance_contract_hash"):
        errors.append("procurement reliance contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("procurement reliance contract is not ready")
    if contract.get("procurement_reliance_decision", {}).get(
        "procurement_reliance_ready"
    ) is not True:
        errors.append("procurement reliance contract decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("procurement reliance contract privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("procurement reliance contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("procurement reliance contract signature is invalid")
    return errors
