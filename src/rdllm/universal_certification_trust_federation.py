"""Universal certification trust federation.

The L161 layer turns a provider-local L160 proof pack into a portable,
third-party-verifiable trust object. It binds certification authorities,
conformance labs, trust marks, verifiable credentials, transparency inclusion,
status/revocation, and relying-party policy before any provider can make an
external RDLLM conformance claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_VERSION = (
    "rdllm-universal-certification-trust-federation/v1"
)
UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_SCHEMA = (
    "docs/schemas/universal_certification_trust_federation.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L161"
MINIMUM_INVOCATION_ENFORCEMENT_LEVEL = "RDLLM-L160"
MINIMUM_NEGOTIATION_LEVEL = "RDLLM-L159"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-certification-trust-federation.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "trust_registry",
    "universal_negotiated_invocation_enforcement",
    "universal_attribution_negotiation_handshake",
    "universal_provider_drift_sentinel",
    "universal_provider_adapter_harness",
)

REQUIRED_FEDERATION_ROLES = (
    "trust_anchor",
    "accreditation_authority",
    "certification_authority",
    "conformance_lab",
    "provider_subject",
    "relying_party",
    "creator_representative",
    "regulator_observer",
)

REQUIRED_TRUST_MARKS = (
    "rdllm_l160_conformance",
    "source_footer_attribution",
    "invocation_enforcement",
    "creator_settlement",
    "privacy_redaction",
    "negative_fixture_fail_closed",
    "transparency_publication",
    "revocation_status",
)

REQUIRED_CREDENTIAL_CLAIMS = (
    "issuer_id_hash",
    "subject_provider_hash",
    "accreditation_scope_hash",
    "certification_report_hash",
    "certification_attestation_hash",
    "assurance_bundle_hash",
    "highest_level",
    "status_list_hash",
    "trust_chain_root_hash",
    "trust_mark_root_hash",
    "scitt_inclusion_hash",
    "verification_method_hash",
    "expiry_hash",
)

REQUIRED_TRANSPARENCY_CHANNELS = (
    "scitt_statement",
    "vc_data_model",
    "openid_federation_entity_statement",
    "trust_mark",
    "status_list",
    "public_discovery_manifest",
    "relying_party_policy",
)

REQUIRED_NEGATIVE_FEDERATION_FAILURES = (
    "self_signed_without_trust_anchor",
    "expired_trust_mark",
    "revoked_credential_status",
    "wrong_provider_subject",
    "stale_certification_report_hash",
    "missing_scitt_inclusion",
    "split_view_trust_anchor",
    "overbroad_scope",
    "private_payload_leak",
    "unaccredited_conformance_lab",
)

DECLARED_HASH_FIELDS = (
    "universal_certification_trust_federation_hash",
    "universal_negotiated_invocation_enforcement_hash",
    "universal_attribution_negotiation_handshake_hash",
    "universal_provider_drift_sentinel_hash",
    "universal_provider_adapter_harness_hash",
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


def load_universal_certification_trust_federation_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L161 certification trust federation."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_federation(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_certification_trust_federation_hash", "signature"}
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
    public_payload: dict[str, Any], federation_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in federation_input.get("private_strings", [])
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


def _policy(federation_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(federation_input.get("certification_trust_federation_policy", {}))
    return {
        "profile": "rdllm-universal-certification-trust-federation-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_invocation_enforcement_level": MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
        "minimum_negotiation_level": MINIMUM_NEGOTIATION_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_federation_roles": list(
            policy.get("required_federation_roles", REQUIRED_FEDERATION_ROLES)
        ),
        "required_trust_marks": list(
            policy.get("required_trust_marks", REQUIRED_TRUST_MARKS)
        ),
        "required_credential_claims": list(
            policy.get("required_credential_claims", REQUIRED_CREDENTIAL_CLAIMS)
        ),
        "required_transparency_channels": list(
            policy.get(
                "required_transparency_channels", REQUIRED_TRANSPARENCY_CHANNELS
            )
        ),
        "required_negative_federation_failures": list(
            policy.get(
                "required_negative_federation_failures",
                REQUIRED_NEGATIVE_FEDERATION_FAILURES,
            )
        ),
        "on_untrusted_certification": "reject_conformance_claim_hold_settlement_and_publish_status",
        "on_revoked_status": "revoke_trust_mark_reject_reliance_and_hold_settlement",
        "on_private_text_leak": "block_publication",
    }


def _component_input_map(federation_input: dict[str, Any], key: str) -> dict[str, Any]:
    value = federation_input.get(key, {})
    return value if isinstance(value, dict) else {}


def _artifact_bindings(
    federation_input: dict[str, Any], required_artifacts: list[str]
) -> dict[str, Any]:
    rows = []
    for name in required_artifacts:
        artifact = federation_input.get(name)
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
        "bindings": rows,
        "binding_root": merkle_root([row["artifact_binding_hash"] for row in rows]),
    }


def _federation_role_rows(
    federation_input: dict[str, Any], required_roles: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(federation_input, "federation_role_rows")
    rows = []
    for role in required_roles:
        raw = dict(row_map.get(role, {}))
        row = {
            "role": role,
            "entity_id_hash": str(raw.get("entity_id_hash", "")),
            "jwks_thumbprint_hash": str(raw.get("jwks_thumbprint_hash", "")),
            "metadata_policy_hash": str(raw.get("metadata_policy_hash", "")),
            "trust_anchor_hash": str(raw.get("trust_anchor_hash", "")),
            "status_endpoint_hash": str(raw.get("status_endpoint_hash", "")),
            "role_authorized": raw.get("role_authorized") is True,
            "public_metadata_safe": raw.get("public_metadata_safe") is True,
        }
        row["ready"] = (
            all(
                row[field]
                for field in (
                    "entity_id_hash",
                    "jwks_thumbprint_hash",
                    "metadata_policy_hash",
                    "trust_anchor_hash",
                    "status_endpoint_hash",
                )
            )
            and row["role_authorized"]
            and row["public_metadata_safe"]
        )
        row["role_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["role_hash"] for row in rows]),
    }


def _trust_mark_rows(
    federation_input: dict[str, Any], required_marks: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(federation_input, "trust_mark_rows")
    rows = []
    for mark in required_marks:
        raw = dict(row_map.get(mark, {}))
        row = {
            "trust_mark": mark,
            "trust_mark_hash": str(raw.get("trust_mark_hash", "")),
            "issuer_chain_hash": str(raw.get("issuer_chain_hash", "")),
            "subject_hash": str(raw.get("subject_hash", "")),
            "scope_hash": str(raw.get("scope_hash", "")),
            "expires_at_hash": str(raw.get("expires_at_hash", "")),
            "status_hash": str(raw.get("status_hash", "")),
            "accreditation_hash": str(raw.get("accreditation_hash", "")),
            "issued_by_accredited_authority": (
                raw.get("issued_by_accredited_authority") is True
            ),
            "matches_policy": raw.get("matches_policy") is True,
            "not_expired": raw.get("not_expired") is True,
            "not_revoked": raw.get("not_revoked") is True,
            "public_projection_safe": raw.get("public_projection_safe") is True,
        }
        row["ready"] = (
            all(
                row[field]
                for field in (
                    "trust_mark_hash",
                    "issuer_chain_hash",
                    "subject_hash",
                    "scope_hash",
                    "expires_at_hash",
                    "status_hash",
                    "accreditation_hash",
                )
            )
            and row["issued_by_accredited_authority"]
            and row["matches_policy"]
            and row["not_expired"]
            and row["not_revoked"]
            and row["public_projection_safe"]
        )
        row["trust_mark_row_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["trust_mark_row_hash"] for row in rows]),
    }


def _credential_claim_rows(
    federation_input: dict[str, Any], required_claims: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(federation_input, "credential_claim_rows")
    rows = []
    for claim in required_claims:
        raw = dict(row_map.get(claim, {}))
        row = {
            "claim": claim,
            "claim_path_hash": str(raw.get("claim_path_hash", "")),
            "credential_hash": str(raw.get("credential_hash", "")),
            "proof_hash": str(raw.get("proof_hash", "")),
            "subject_binding_hash": str(raw.get("subject_binding_hash", "")),
            "required_in_vc": raw.get("required_in_vc") is True,
            "required_in_trust_mark": raw.get("required_in_trust_mark") is True,
            "privacy_preserving": raw.get("privacy_preserving") is True,
        }
        row["ready"] = (
            all(
                row[field]
                for field in (
                    "claim_path_hash",
                    "credential_hash",
                    "proof_hash",
                    "subject_binding_hash",
                )
            )
            and row["required_in_vc"]
            and row["required_in_trust_mark"]
            and row["privacy_preserving"]
        )
        row["credential_claim_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["credential_claim_hash"] for row in rows]),
    }


def _transparency_channel_rows(
    federation_input: dict[str, Any], required_channels: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(federation_input, "transparency_channel_rows")
    rows = []
    for channel in required_channels:
        raw = dict(row_map.get(channel, {}))
        row = {
            "channel": channel,
            "statement_hash": str(raw.get("statement_hash", "")),
            "inclusion_proof_hash": str(raw.get("inclusion_proof_hash", "")),
            "log_root_hash": str(raw.get("log_root_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "published": raw.get("published") is True,
            "inclusion_verified": raw.get("inclusion_verified") is True,
            "consistency_verified": raw.get("consistency_verified") is True,
            "public_projection_safe": raw.get("public_projection_safe") is True,
        }
        row["ready"] = (
            all(
                row[field]
                for field in (
                    "statement_hash",
                    "inclusion_proof_hash",
                    "log_root_hash",
                    "verifier_command",
                )
            )
            and row["published"]
            and row["inclusion_verified"]
            and row["consistency_verified"]
            and row["public_projection_safe"]
        )
        row["transparency_channel_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["transparency_channel_hash"] for row in rows]),
    }


def _negative_federation_rows(
    federation_input: dict[str, Any], required_failures: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(federation_input, "negative_federation_rows")
    rows = []
    for case_id in required_failures:
        raw = dict(row_map.get(case_id, {}))
        row = {
            "case_id": case_id,
            "fixture_hash": str(raw.get("fixture_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "expected_reject": raw.get("expected_reject") is True,
            "observed_reject": raw.get("observed_reject") is True,
            "trust_mark_revoked": raw.get("trust_mark_revoked") is True,
            "relying_party_blocked": raw.get("relying_party_blocked") is True,
            "settlement_held": raw.get("settlement_held") is True,
        }
        row["ready"] = (
            bool(row["fixture_hash"])
            and bool(row["verifier_command"])
            and row["expected_reject"]
            and row["observed_reject"]
            and row["relying_party_blocked"]
            and row["settlement_held"]
        )
        row["negative_federation_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["negative_federation_hash"] for row in rows]),
    }


def _artifact_summary(federation_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = federation_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_certification_trust_federation(
    federation_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L161 universal certification trust federation artifact."""

    created_at = created_at or now_iso()
    policy = _policy(federation_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_roles = [str(name) for name in policy["required_federation_roles"]]
    required_marks = [str(name) for name in policy["required_trust_marks"]]
    required_claims = [str(name) for name in policy["required_credential_claims"]]
    required_channels = [str(name) for name in policy["required_transparency_channels"]]
    required_failures = [
        str(name) for name in policy["required_negative_federation_failures"]
    ]

    artifact_bindings = _artifact_bindings(federation_input, required_artifacts)
    role_rows = _federation_role_rows(federation_input, required_roles)
    trust_mark_rows = _trust_mark_rows(federation_input, required_marks)
    credential_rows = _credential_claim_rows(federation_input, required_claims)
    transparency_rows = _transparency_channel_rows(
        federation_input, required_channels
    )
    negative_rows = _negative_federation_rows(federation_input, required_failures)

    certification_summary = _artifact_summary(federation_input, "certification_report")
    attestation_summary = _artifact_summary(
        federation_input, "certification_attestation"
    )
    invocation_summary = _artifact_summary(
        federation_input, "universal_negotiated_invocation_enforcement"
    )
    negotiation_summary = _artifact_summary(
        federation_input, "universal_attribution_negotiation_handshake"
    )
    provider_card = federation_input.get("provider_attribution_card", {})
    integration_profile = federation_input.get("integration_profile", {})
    discovery_manifest = federation_input.get("discovery_manifest", {})
    assurance_bundle = federation_input.get("assurance_bundle", {})

    core_artifacts_ready = all(
        row["present"] and row["hash_reproducible"]
        for row in artifact_bindings["bindings"]
    )
    public_projection = {
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "federation_role_rows": role_rows,
        "trust_mark_rows": trust_mark_rows,
        "credential_claim_rows": credential_rows,
        "transparency_channel_rows": transparency_rows,
        "negative_federation_rows": negative_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_level_at_least_l160": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level", ""),
                MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
            )
        ),
        "certification_attestation_bound_l160_or_higher": (
            _level_at_least(
                attestation_summary.get("attested_highest_level", ""),
                MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
            )
            or _level_at_least(
                attestation_summary.get("highest_level", ""),
                MINIMUM_INVOCATION_ENFORCEMENT_LEVEL,
            )
        ),
        "invocation_enforcement_ready_l160": (
            invocation_summary.get("status") == "ready"
            and invocation_summary.get("target_certification_level")
            == MINIMUM_INVOCATION_ENFORCEMENT_LEVEL
        ),
        "negotiation_handshake_ready_l159": (
            negotiation_summary.get("status") == "ready"
            and negotiation_summary.get("target_certification_level")
            == MINIMUM_NEGOTIATION_LEVEL
        ),
        "provider_card_declares_certification_trust_federation": (
            provider_card.get("public_disclosure_surfaces", {}).get(
                "universal_certification_trust_federation"
            )
            is True
            and provider_card.get("supported_evidence_channels", {}).get(
                "universal_certification_trust_federation"
            )
            is True
        ),
        "integration_profile_declares_certification_trust_federation": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_certification_trust_federation"
            )
            is True
            and "universal_certification_trust_federation"
            in integration_profile.get("schemas", {})
        ),
        "discovery_manifest_exposes_certification_trust_federation_path": (
            discovery_manifest.get("discovery", {}).get(
                "universal_certification_trust_federation_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "assurance_bundle_ready": (
            assurance_bundle.get("assurance_version") == "rdllm-assurance-bundle/v1"
            and int(assurance_bundle.get("summary", {}).get("artifact_count", 0) or 0)
            > 0
        ),
        "all_federation_roles_authorized": (
            role_rows["ready_count"] == role_rows["row_count"]
        ),
        "all_trust_marks_valid": (
            trust_mark_rows["ready_count"] == trust_mark_rows["row_count"]
        ),
        "all_credential_claims_bound": (
            credential_rows["ready_count"] == credential_rows["row_count"]
        ),
        "all_transparency_channels_verified": (
            transparency_rows["ready_count"] == transparency_rows["row_count"]
        ),
        "negative_federation_fixtures_reject": (
            negative_rows["ready_count"] == negative_rows["row_count"]
        ),
        "public_projection_omits_private_payloads": (
            not private_findings
            and _private_strings_absent(public_projection, federation_input)
        ),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    federation_decision = {
        "universal_certification_trust_federation_authorized": not failure_modes,
        "failure_modes": failure_modes,
        "on_failure": "reject_conformance_claim_hold_settlement_and_publish_status",
        "conformance_claim_without_trust_chain_allowed": False,
        "relying_party_acceptance_without_valid_status_allowed": False,
        "provider_self_certification_sufficient": False,
    }

    report = {
        "universal_certification_trust_federation_version": (
            UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_VERSION
        ),
        "schema": UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_SCHEMA,
        "issuer": issuer,
        "created_at": created_at,
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "federation_role_rows": role_rows,
        "trust_mark_rows": trust_mark_rows,
        "credential_claim_rows": credential_rows,
        "transparency_channel_rows": transparency_rows,
        "negative_federation_rows": negative_rows,
        "checks": checks,
        "federation_decision": federation_decision,
        "privacy": {
            "public_artifact_uses_hashes_only": True,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "credential_subject_payload_disclosed": False,
            "trust_chain_private_metadata_disclosed": False,
            "private_field_count": len(private_findings),
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_SCHEMA,
            "create": "universal-certification-trust-federation",
            "verify": "verify-universal-certification-trust-federation",
        },
        "summary": {
            "status": (
                "ready"
                if federation_decision[
                    "universal_certification_trust_federation_authorized"
                ]
                else "blocked"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_invocation_enforcement_level": (
                MINIMUM_INVOCATION_ENFORCEMENT_LEVEL
            ),
            "minimum_negotiation_level": MINIMUM_NEGOTIATION_LEVEL,
            "federation_role_count": role_rows["row_count"],
            "ready_federation_role_count": role_rows["ready_count"],
            "trust_mark_count": trust_mark_rows["row_count"],
            "ready_trust_mark_count": trust_mark_rows["ready_count"],
            "credential_claim_count": credential_rows["row_count"],
            "ready_credential_claim_count": credential_rows["ready_count"],
            "transparency_channel_count": transparency_rows["row_count"],
            "ready_transparency_channel_count": transparency_rows["ready_count"],
            "negative_federation_failure_count": negative_rows["row_count"],
            "ready_negative_federation_failure_count": negative_rows["ready_count"],
            "core_artifact_count": len(required_artifacts),
            "failure_mode_count": len(failure_modes),
            "federated_certification_required": True,
            "trust_anchor_required": True,
            "revocation_status_required": True,
            "third_party_conformance_supported": True,
            "offline_verification_supported": True,
            "privacy_preserved": checks["public_projection_omits_private_payloads"],
        },
    }
    report["universal_certification_trust_federation_hash"] = hash_payload(
        _hashable_federation(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(
                report["universal_certification_trust_federation_hash"],
                signing_secret,
            )
            if signing_secret
            else ""
        ),
    }
    return report


def validate_universal_certification_trust_federation_shape(
    report: dict[str, Any],
) -> list[str]:
    """Validate required public fields for an L161 trust federation artifact."""

    errors: list[str] = []
    required = (
        "universal_certification_trust_federation_version",
        "schema",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "federation_role_rows",
        "trust_mark_rows",
        "credential_claim_rows",
        "transparency_channel_rows",
        "negative_federation_rows",
        "checks",
        "federation_decision",
        "privacy",
        "well_known",
        "summary",
        "universal_certification_trust_federation_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal certification trust federation field: {key}")
    if errors:
        return errors
    if (
        report.get("universal_certification_trust_federation_version")
        != UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_VERSION
    ):
        errors.append("universal certification trust federation version is unsupported")
    if report.get("schema") != UNIVERSAL_CERTIFICATION_TRUST_FEDERATION_SCHEMA:
        errors.append("universal certification trust federation schema is unsupported")
    summary = report.get("summary", {})
    if summary.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal certification trust federation target level is not RDLLM-L161")
    if (
        summary.get("minimum_invocation_enforcement_level")
        != MINIMUM_INVOCATION_ENFORCEMENT_LEVEL
    ):
        errors.append("universal certification trust federation minimum invocation level is not RDLLM-L160")
    if summary.get("minimum_negotiation_level") != MINIMUM_NEGOTIATION_LEVEL:
        errors.append("universal certification trust federation minimum negotiation level is not RDLLM-L159")
    if report.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal certification trust federation well-known path is incorrect")
    return errors


def verify_universal_certification_trust_federation(
    report: dict[str, Any],
    *,
    federation_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L161 trust federation artifact against private replay input."""

    errors = validate_universal_certification_trust_federation_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_federation(report))
    if expected_hash != report.get("universal_certification_trust_federation_hash"):
        errors.append("universal certification trust federation hash is not reproducible")

    expected = make_universal_certification_trust_federation(
        federation_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "federation_role_rows",
        "trust_mark_rows",
        "credential_claim_rows",
        "transparency_channel_rows",
        "negative_federation_rows",
        "checks",
        "federation_decision",
        "privacy",
        "well_known",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(
                f"universal certification trust federation {key} does not match input"
            )
    if (
        expected.get("universal_certification_trust_federation_hash")
        != report.get("universal_certification_trust_federation_hash")
    ):
        errors.append("universal certification trust federation hash does not match input")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal certification trust federation status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal certification trust federation check failed: {check}")

    private_findings = _contains_private_fields(report)
    if private_findings:
        errors.append(
            "universal certification trust federation exposes private field(s): "
            + ", ".join(private_findings[:5])
        )
    if not _private_strings_absent(report, federation_input):
        errors.append("universal certification trust federation leaked private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(
            report.get("universal_certification_trust_federation_hash", ""),
            signing_secret,
        )
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal certification trust federation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal certification trust federation signature is invalid")

    return errors
