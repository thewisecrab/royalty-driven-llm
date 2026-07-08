"""Universal distribution reliance passports.

The L172 layer proves that a grounded L171 response remains attributable after
it leaves the original chat surface. It binds copied, exported, embedded,
relayed, screenshotted, and downstream-ingested artifacts to the original source
footer, status resolver, content credential, reuse meter, and settlement
carry-forward obligation before third parties may rely on the distributed copy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_VERSION = (
    "rdllm-universal-distribution-reliance-passport/v1"
)
UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_SCHEMA = (
    "docs/schemas/universal_distribution_reliance_passport.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L172"
MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL = "RDLLM-L171"
MINIMUM_CONTENT_CREDENTIAL_LEVEL = "RDLLM-L136"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-distribution-reliance-passport.json"
)

REQUIRED_DISTRIBUTION_SURFACES = (
    "clipboard_copy",
    "markdown_export",
    "html_export",
    "pdf_export",
    "image_screenshot",
    "c2pa_content_credential",
    "api_relay",
    "web_embed",
    "email_share",
    "social_share",
    "downstream_rag_ingestion",
    "marketplace_dataset_export",
)

REQUIRED_PORTABLE_BINDINGS = (
    "l171_receipt_hash",
    "visible_footer_hash",
    "source_locator_manifest_hash",
    "content_credential_hash",
    "status_resolver_hash",
    "revocation_snapshot_hash",
    "reuse_meter_hash",
    "copy_export_meter_hash",
    "downstream_reuse_meter_hash",
    "settlement_carry_forward_hash",
    "auditor_export_hash",
)

REQUIRED_STATUS_CHANNELS = (
    "well_known_status_resolver",
    "content_credential_manifest",
    "source_locator_resolver",
    "citation_url_health_resolver",
    "revocation_and_correction_feed",
    "creator_settlement_status_api",
    "independent_audit_export",
)

REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES = (
    "missing_l171_receipt",
    "stale_l171_receipt",
    "footer_stripped_on_copy",
    "citation_locator_removed",
    "content_credential_missing",
    "status_resolver_unreachable",
    "revocation_snapshot_stale",
    "downstream_reuse_unmetered",
    "settlement_obligation_dropped",
    "credential_manifest_mismatch",
    "screenshot_without_source_overlay",
    "pdf_export_without_footer",
    "api_relay_without_receipt",
    "marketplace_export_without_license",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_distribution_reliance_passport_hash",
    "universal_source_grounded_response_receipt_hash",
    "universal_content_credential_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "evidence_locator_manifest_hash",
    "citation_url_health_hash",
    "universal_reliance_correction_ledger_hash",
    "revenue_allocation_hash",
    "finance_ledger_attestation_hash",
    "distribution_surface_hash",
    "artifact_body_hash",
    "l171_receipt_hash",
    "visible_footer_hash",
    "source_locator_manifest_hash",
    "content_credential_hash",
    "status_resolver_hash",
    "revocation_snapshot_hash",
    "reuse_meter_hash",
    "copy_export_meter_hash",
    "downstream_reuse_meter_hash",
    "settlement_carry_forward_hash",
    "auditor_export_hash",
    "binding_hash",
    "subject_hash",
    "binding_target_hash",
    "proof_graph_hash",
    "resolver_hash",
    "channel_hash",
    "endpoint_hash",
    "discovery_manifest_hash",
    "last_observed_root_hash",
    "verifier_hash",
    "fixture_hash",
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
    "copied_output",
    "rendered_output",
    "distributed_output",
    "screenshot_pixels",
    "pdf_body",
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


def load_universal_distribution_reliance_passport_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L172 distribution reliance passport."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_passport(passport: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in passport.items()
        if key not in {"universal_distribution_reliance_passport_hash", "signature"}
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
    passport_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in passport_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _source_grounded_response_ready(receipt: dict[str, Any] | None) -> bool:
    if not isinstance(receipt, dict):
        return False
    summary = _summary(receipt)
    decision = receipt.get("response_release_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("source_grounded_response_ready") is True
        and decision.get("final_answer_release_allowed") is True
        and decision.get("user_footer_display_allowed") is True
        and decision.get("source_reliance_allowed") is True
        and decision.get("citation_reliance_allowed") is True
        and decision.get("copy_export_allowed") is True
        and decision.get("creator_settlement_allowed") is True
    )


def _content_credential_ready(credential: dict[str, Any] | None) -> bool:
    if not isinstance(credential, dict):
        return False
    summary = _summary(credential)
    decision = credential.get("credential_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_CONTENT_CREDENTIAL_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("all_required_bindings_present") is True
        and decision.get("decision") == "publish_universal_content_credential"
        and not decision.get("failure_modes", [])
    )


def _distribution_surface_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "distribution_surface_hash",
        "artifact_body_hash",
        "l171_receipt_hash",
        "visible_footer_hash",
        "source_locator_manifest_hash",
        "status_resolver_hash",
        "content_credential_hash",
        "reuse_meter_hash",
        "settlement_carry_forward_hash",
        "verifier_hash",
    )
    required_flags = (
        "surface_exported",
        "attribution_visible_or_embedded",
        "l171_receipt_bound",
        "source_locators_preserved",
        "status_resolver_reachable",
        "revocation_checked",
        "reuse_metered",
        "settlement_obligation_preserved",
        "fail_closed_if_stripped",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _portable_binding_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "binding_hash",
        "subject_hash",
        "l171_receipt_hash",
        "binding_target_hash",
        "proof_graph_hash",
        "resolver_hash",
        "verifier_hash",
    )
    required_flags = (
        "publicly_verifiable",
        "tamper_evident",
        "survives_copy_or_transform",
        "resolves_to_current_status",
        "binds_settlement_obligation",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _status_channel_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "channel_hash",
        "endpoint_hash",
        "discovery_manifest_hash",
        "last_observed_root_hash",
        "verifier_hash",
    )
    required_flags = (
        "endpoint_published",
        "current_status_resolves",
        "revocation_status_included",
        "correction_status_included",
        "settlement_status_included",
        "no_split_view_observed",
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
            "distribution_blocked",
            "third_party_reliance_blocked",
            "downstream_reuse_blocked",
            "settlement_carry_forward_held",
            "public_status_marked_failed",
        )
    )


def _row_map(passport_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = passport_input.get(key, {})
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


def make_universal_distribution_reliance_passport(
    passport_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L172 universal distribution reliance passport."""

    source_receipt = passport_input.get("universal_source_grounded_response_receipt")
    content_credential = passport_input.get("universal_content_credential")
    surface_rows = _row_map(passport_input, "distribution_surface_rows")
    binding_rows = _row_map(passport_input, "portable_binding_rows")
    channel_rows = _row_map(passport_input, "status_channel_rows")
    negative_rows = _row_map(passport_input, "negative_distribution_rows")

    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_DISTRIBUTION_SURFACES,
        _distribution_surface_ready,
    )
    missing_bindings, incomplete_bindings = _complete_rows(
        binding_rows,
        REQUIRED_PORTABLE_BINDINGS,
        _portable_binding_ready,
    )
    missing_channels, incomplete_channels = _complete_rows(
        channel_rows,
        REQUIRED_STATUS_CHANNELS,
        _status_channel_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES,
        _negative_failure_ready,
    )

    checks = {
        "source_grounded_response_receipt_bound": _artifact_hash_is_reproducible(
            source_receipt if isinstance(source_receipt, dict) else None
        ),
        "source_grounded_response_receipt_l171_ready": (
            _source_grounded_response_ready(
                source_receipt if isinstance(source_receipt, dict) else None
            )
        ),
        "content_credential_bound": _artifact_hash_is_reproducible(
            content_credential if isinstance(content_credential, dict) else None
        ),
        "content_credential_ready": _content_credential_ready(
            content_credential if isinstance(content_credential, dict) else None
        ),
        "distribution_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "portable_binding_rows_complete": not missing_bindings
        and not incomplete_bindings,
        "status_channel_rows_complete": not missing_channels
        and not incomplete_channels,
        "negative_distribution_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "distribution_reliance_passport_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    surface_root = merkle_root([
        hash_payload({"name": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_DISTRIBUTION_SURFACES
    ])
    binding_root = merkle_root([
        hash_payload({"name": name, "row": binding_rows.get(name, {})})
        for name in REQUIRED_PORTABLE_BINDINGS
    ])
    channel_root = merkle_root([
        hash_payload({"name": name, "row": channel_rows.get(name, {})})
        for name in REQUIRED_STATUS_CHANNELS
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
    ])

    public = {
        "universal_distribution_reliance_passport_version": (
            UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_VERSION
        ),
        "schema": UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-distribution-reliance-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "minimum_content_credential_level": MINIMUM_CONTENT_CREDENTIAL_LEVEL,
            "source_footer_must_survive_distribution": True,
            "status_resolver_required_for_third_party_reliance": True,
            "content_credential_required_for_exported_artifacts": True,
            "downstream_reuse_meter_required": True,
            "settlement_obligation_carry_forward_required": True,
            "private_payloads_forbidden_in_public_passport": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_VERSION,
        },
        "source_grounded_response_binding": {
            "present": isinstance(source_receipt, dict),
            "artifact_hash": _declared_hash(
                source_receipt if isinstance(source_receipt, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    source_receipt if isinstance(source_receipt, dict) else None
                )
            ),
            "hash_reproducible": checks["source_grounded_response_receipt_bound"],
            "status": _summary(
                source_receipt if isinstance(source_receipt, dict) else None
            ).get("status", ""),
            "level": _summary(
                source_receipt if isinstance(source_receipt, dict) else None
            ).get("target_certification_level", ""),
        },
        "content_credential_binding": {
            "present": isinstance(content_credential, dict),
            "artifact_hash": _declared_hash(
                content_credential if isinstance(content_credential, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    content_credential if isinstance(content_credential, dict) else None
                )
            ),
            "hash_reproducible": checks["content_credential_bound"],
            "status": _summary(
                content_credential if isinstance(content_credential, dict) else None
            ).get("status", ""),
            "level": _summary(
                content_credential if isinstance(content_credential, dict) else None
            ).get("target_certification_level", ""),
        },
        "distribution_surface_rows": surface_rows,
        "portable_binding_rows": binding_rows,
        "status_channel_rows": channel_rows,
        "negative_distribution_rows": negative_rows,
        "evidence_roots": {
            "distribution_surface_root": surface_root,
            "portable_binding_root": binding_root,
            "status_channel_root": channel_root,
            "negative_distribution_root": negative_root,
        },
        "checks": checks,
        "distribution_reliance_decision": {
            "distribution_reliance_ready": ready,
            "copy_distribution_allowed": ready,
            "export_distribution_allowed": ready,
            "third_party_reliance_allowed": ready,
            "api_relay_allowed": ready,
            "downstream_rag_ingestion_allowed": ready,
            "content_credential_export_allowed": ready,
            "settlement_carry_forward_allowed": ready,
            "stripped_outputs_blocked": ready,
            "failure_modes": failure_modes,
            "missing_distribution_surfaces": missing_surfaces,
            "incomplete_distribution_surfaces": incomplete_surfaces,
            "missing_portable_bindings": missing_bindings,
            "incomplete_portable_bindings": incomplete_bindings,
            "missing_status_channels": missing_channels,
            "incomplete_status_channels": incomplete_channels,
            "missing_negative_failures": missing_negative,
            "incomplete_negative_failures": incomplete_negative,
        },
        "distribution_coverage": {
            "required_distribution_surface_count": len(
                REQUIRED_DISTRIBUTION_SURFACES
            ),
            "ready_distribution_surface_count": len(REQUIRED_DISTRIBUTION_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "required_portable_binding_count": len(REQUIRED_PORTABLE_BINDINGS),
            "ready_portable_binding_count": len(REQUIRED_PORTABLE_BINDINGS)
            - len(missing_bindings)
            - len(incomplete_bindings),
            "required_status_channel_count": len(REQUIRED_STATUS_CHANNELS),
            "ready_status_channel_count": len(REQUIRED_STATUS_CHANNELS)
            - len(missing_channels)
            - len(incomplete_channels),
        },
        "privacy": {
            "private_payload_fields": [],
            "private_strings_absent": True,
            "private_payloads_excluded": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_source_grounded_response_level": (
                MINIMUM_SOURCE_GROUNDED_RESPONSE_LEVEL
            ),
            "minimum_content_credential_level": MINIMUM_CONTENT_CREDENTIAL_LEVEL,
            "distribution_surface_count": len(REQUIRED_DISTRIBUTION_SURFACES),
            "ready_distribution_surface_count": len(REQUIRED_DISTRIBUTION_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "portable_binding_count": len(REQUIRED_PORTABLE_BINDINGS),
            "ready_portable_binding_count": len(REQUIRED_PORTABLE_BINDINGS)
            - len(missing_bindings)
            - len(incomplete_bindings),
            "status_channel_count": len(REQUIRED_STATUS_CHANNELS),
            "ready_status_channel_count": len(REQUIRED_STATUS_CHANNELS)
            - len(missing_channels)
            - len(incomplete_channels),
            "negative_distribution_failure_count": len(
                REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
            ),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_distribution_reliance_passport": signing_secret is not None,
        },
    }
    public["privacy"]["private_payload_fields"] = _contains_private_fields(public)
    public["privacy"]["private_strings_absent"] = _private_strings_absent(
        public,
        passport_input,
    )
    public["privacy"]["private_payloads_excluded"] = (
        not public["privacy"]["private_payload_fields"]
        and public["privacy"]["private_strings_absent"]
    )
    if not public["privacy"]["private_payloads_excluded"]:
        public["checks"]["private_payloads_excluded"] = False
        public["distribution_reliance_decision"]["distribution_reliance_ready"] = False
        public["distribution_reliance_decision"]["copy_distribution_allowed"] = False
        public["distribution_reliance_decision"]["export_distribution_allowed"] = False
        public["distribution_reliance_decision"]["third_party_reliance_allowed"] = False
        public["distribution_reliance_decision"]["api_relay_allowed"] = False
        public["distribution_reliance_decision"][
            "downstream_rag_ingestion_allowed"
        ] = False
        public["distribution_reliance_decision"][
            "content_credential_export_allowed"
        ] = False
        public["distribution_reliance_decision"][
            "settlement_carry_forward_allowed"
        ] = False
        public["distribution_reliance_decision"]["stripped_outputs_blocked"] = False
        if "private_payloads_excluded" not in public["distribution_reliance_decision"][
            "failure_modes"
        ]:
            public["distribution_reliance_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["distribution_reliance_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_distribution_reliance_passport_hash"] = hash_payload(
        _hashable_passport(public)
    )
    if signing_secret:
        public["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_passport(public), signing_secret),
        }
    return public


def validate_universal_distribution_reliance_passport_shape(
    passport: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L172 distribution passport."""

    errors: list[str] = []
    required = (
        "universal_distribution_reliance_passport_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "source_grounded_response_binding",
        "content_credential_binding",
        "distribution_surface_rows",
        "portable_binding_rows",
        "status_channel_rows",
        "negative_distribution_rows",
        "evidence_roots",
        "checks",
        "distribution_reliance_decision",
        "distribution_coverage",
        "privacy",
        "summary",
        "universal_distribution_reliance_passport_hash",
    )
    for key in required:
        if key not in passport:
            errors.append(f"missing distribution reliance passport field: {key}")
    if passport.get("universal_distribution_reliance_passport_version") != (
        UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_VERSION
    ):
        errors.append("unexpected universal_distribution_reliance_passport_version")
    if passport.get("schema") != UNIVERSAL_DISTRIBUTION_RELIANCE_PASSPORT_SCHEMA:
        errors.append("unexpected distribution reliance passport schema")
    for name in REQUIRED_DISTRIBUTION_SURFACES:
        if name not in passport.get("distribution_surface_rows", {}):
            errors.append(f"missing distribution surface row: {name}")
    for name in REQUIRED_PORTABLE_BINDINGS:
        if name not in passport.get("portable_binding_rows", {}):
            errors.append(f"missing portable binding row: {name}")
    for name in REQUIRED_STATUS_CHANNELS:
        if name not in passport.get("status_channel_rows", {}):
            errors.append(f"missing status channel row: {name}")
    for name in REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES:
        if name not in passport.get("negative_distribution_rows", {}):
            errors.append(f"missing negative distribution row: {name}")
    for check in (
        "source_grounded_response_receipt_bound",
        "source_grounded_response_receipt_l171_ready",
        "content_credential_bound",
        "content_credential_ready",
        "distribution_surface_rows_complete",
        "portable_binding_rows_complete",
        "status_channel_rows_complete",
        "negative_distribution_fixtures_reject",
        "distribution_reliance_passport_signed",
    ):
        if check not in passport.get("checks", {}):
            errors.append(f"missing distribution reliance check: {check}")
    return errors


def verify_universal_distribution_reliance_passport(
    passport_input: dict[str, Any],
    passport: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L172 distribution reliance passport against replay input."""

    errors = validate_universal_distribution_reliance_passport_shape(passport)
    expected_hash = hash_payload(_hashable_passport(passport))
    if passport.get("universal_distribution_reliance_passport_hash") != expected_hash:
        errors.append("universal_distribution_reliance_passport_hash mismatch")
    private_fields = _contains_private_fields(passport)
    if private_fields:
        errors.append(
            "distribution reliance passport exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(passport, passport_input):
        errors.append("distribution reliance passport exposes private input strings")
    replayed = make_universal_distribution_reliance_passport(
        passport_input,
        issuer=passport.get("issuer", DEFAULT_ISSUER),
        created_at=passport.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_distribution_reliance_passport_hash") != passport.get(
        "universal_distribution_reliance_passport_hash"
    ):
        errors.append("distribution reliance passport does not match replay inputs")
    if passport.get("summary", {}).get("status") != "ready":
        errors.append("distribution reliance passport is not ready")
    if passport.get("distribution_reliance_decision", {}).get(
        "distribution_reliance_ready"
    ) is not True:
        errors.append("distribution reliance decision is not ready")
    if passport.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("distribution reliance passport privacy is not preserved")
    if signing_secret:
        signature = passport.get("signature", {})
        expected_signature = sign_payload(_hashable_passport(passport), signing_secret)
        if not signature:
            errors.append("distribution reliance passport is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("distribution reliance passport signature is invalid")
    return errors
