"""Universal provider drift sentinel.

The L158 layer keeps L157 from becoming stale. L157 proves provider-native
fixtures normalize into one RDLLM response contract at certification time; L158
proves that provider API, SDK, model-alias, streaming, gateway, citation, and
settlement drift are continuously replayed, detected, and revoked before a route
continues to display grounded answers or settle creator royalties.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root
from rdllm.universal_foundation_adoption_kernel import REQUIRED_PROVIDER_FAMILIES

UNIVERSAL_PROVIDER_DRIFT_SENTINEL_VERSION = (
    "rdllm-universal-provider-drift-sentinel/v1"
)
UNIVERSAL_PROVIDER_DRIFT_SENTINEL_SCHEMA = (
    "docs/schemas/universal_provider_drift_sentinel.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L158"
MINIMUM_HARNESS_LEVEL = "RDLLM-L157"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-drift-sentinel.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "universal_provider_adapter_harness",
    "universal_foundation_adoption_kernel",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "response_envelope",
    "citation_url_health",
    "source_freshness_audit",
    "evidence_locator_manifest",
    "warranted_source_footer",
    "trust_registry",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
)

REQUIRED_DRIFT_SURFACES = (
    "provider_api_schema",
    "model_alias_resolution",
    "response_shape",
    "streaming_event_schema",
    "tool_call_schema",
    "retrieval_context_schema",
    "batch_callback_schema",
    "webhook_schema",
    "copy_export_schema",
    "sdk_metadata_contract",
    "gateway_transform_contract",
    "telemetry_semconv",
    "citation_locator_resolution",
    "source_footer_rendering",
    "settlement_metering",
    "policy_status_resolver",
)

REQUIRED_CANARY_CADENCES = (
    "pre_release",
    "hourly_canary",
    "daily_schema_snapshot",
    "weekly_negative_rotation",
    "incident_triggered_replay",
)

REQUIRED_SENTINEL_FIELDS = (
    "baseline_hash",
    "observed_hash",
    "adapter_harness_hash",
    "canary_trace_hash",
    "response_contract_hash",
    "drift_score_hash",
    "remediation_status_hash",
    "revocation_status_hash",
    "witness_hash",
    "provider_notice_hash",
    "rollback_plan_hash",
    "customer_notice_hash",
)

REQUIRED_DRIFT_FAILURES = (
    "silent_response_shape_change",
    "streaming_footer_regression",
    "model_alias_substitution",
    "provider_api_version_unpinned",
    "sdk_drops_metadata",
    "gateway_transform_strips_footer",
    "stale_citation_locator",
    "settlement_meter_drift",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_drift_sentinel_hash",
    "universal_provider_adapter_harness_hash",
    "universal_foundation_adoption_kernel_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "citation_url_health_hash",
    "source_freshness_audit_hash",
    "evidence_locator_manifest_hash",
    "warranted_source_footer_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "contract_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "envelope_hash",
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


def load_universal_provider_drift_sentinel_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L158 provider drift sentinel."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_sentinel(sentinel: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sentinel.items()
        if key not in {"universal_provider_drift_sentinel_hash", "signature"}
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
    public_payload: dict[str, Any], sentinel_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in sentinel_input.get("private_strings", [])
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


def _policy(sentinel_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(sentinel_input.get("drift_sentinel_policy", {}))
    return {
        "profile": "rdllm-universal-provider-drift-sentinel-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_harness_level": MINIMUM_HARNESS_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_drift_surfaces": list(
            policy.get("required_drift_surfaces", REQUIRED_DRIFT_SURFACES)
        ),
        "required_canary_cadences": list(
            policy.get("required_canary_cadences", REQUIRED_CANARY_CADENCES)
        ),
        "required_sentinel_fields": list(
            policy.get("required_sentinel_fields", REQUIRED_SENTINEL_FIELDS)
        ),
        "required_drift_failures": list(
            policy.get("required_drift_failures", REQUIRED_DRIFT_FAILURES)
        ),
        "on_provider_drift": "revoke_grounded_display_and_hold_settlement",
        "on_missing_canary": "block_provider_route",
        "on_private_text_leak": "block_publication",
    }


def _component_input_map(sentinel_input: dict[str, Any], key: str) -> dict[str, Any]:
    value = sentinel_input.get(key, {})
    return value if isinstance(value, dict) else {}


def _artifact_bindings(
    sentinel_input: dict[str, Any], required_artifacts: list[str]
) -> dict[str, Any]:
    rows = []
    for name in required_artifacts:
        artifact = sentinel_input.get(name)
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
    root = merkle_root([row["artifact_binding_hash"] for row in rows])
    return {"bindings": rows, "binding_root": root}


def _drift_surface_rows(
    sentinel_input: dict[str, Any],
    required_families: list[str],
    required_surfaces: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(sentinel_input, "drift_surface_rows")
    rows = []
    for family in required_families:
        for surface in required_surfaces:
            raw = dict(row_map.get(f"{family}:{surface}", {}))
            drift_status = str(raw.get("drift_status", ""))
            row = {
                "provider_family": family,
                "drift_surface": surface,
                "baseline_hash": str(raw.get("baseline_hash", "")),
                "observed_hash": str(raw.get("observed_hash", "")),
                "monitor_hash": str(raw.get("monitor_hash", "")),
                "adapter_harness_hash": str(raw.get("adapter_harness_hash", "")),
                "status_resolver_hash": str(raw.get("status_resolver_hash", "")),
                "drift_status": drift_status,
                "drift_score_hash": str(raw.get("drift_score_hash", "")),
                "last_observed_at": str(raw.get("last_observed_at", "")),
                "ready": (
                    bool(raw.get("baseline_hash"))
                    and bool(raw.get("observed_hash"))
                    and bool(raw.get("monitor_hash"))
                    and bool(raw.get("adapter_harness_hash"))
                    and drift_status in {"stable", "approved_change"}
                ),
            }
            row["surface_hash"] = hash_payload(row)
            rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["surface_hash"] for row in rows]),
    }


def _canary_replay_rows(
    sentinel_input: dict[str, Any],
    required_families: list[str],
    required_cadences: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(sentinel_input, "canary_replay_rows")
    rows = []
    for family in required_families:
        for cadence in required_cadences:
            raw = dict(row_map.get(f"{family}:{cadence}", {}))
            row = {
                "provider_family": family,
                "cadence": cadence,
                "canary_trace_hash": str(raw.get("canary_trace_hash", "")),
                "fixture_pack_hash": str(raw.get("fixture_pack_hash", "")),
                "response_contract_hash": str(raw.get("response_contract_hash", "")),
                "source_footer_hash": str(raw.get("source_footer_hash", "")),
                "claim_provenance_hash": str(raw.get("claim_provenance_hash", "")),
                "settlement_meter_hash": str(raw.get("settlement_meter_hash", "")),
                "telemetry_trace_hash": str(raw.get("telemetry_trace_hash", "")),
                "copy_status_link_hash": str(raw.get("copy_status_link_hash", "")),
                "passed": raw.get("passed") is True,
                "private_payload_absent": raw.get("private_payload_absent") is True,
            }
            row["ready"] = (
                row["passed"]
                and row["private_payload_absent"]
                and all(
                    row[field]
                    for field in (
                        "canary_trace_hash",
                        "fixture_pack_hash",
                        "response_contract_hash",
                        "source_footer_hash",
                        "claim_provenance_hash",
                        "settlement_meter_hash",
                        "telemetry_trace_hash",
                        "copy_status_link_hash",
                    )
                )
            )
            row["canary_hash"] = hash_payload(row)
            rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["canary_hash"] for row in rows]),
    }


def _sentinel_field_rows(
    sentinel_input: dict[str, Any],
    required_fields: list[str],
    required_families: list[str],
    required_surfaces: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(sentinel_input, "sentinel_field_rows")
    rows = []
    provider_count = len(required_families)
    surface_count = len(required_surfaces)
    for field in required_fields:
        raw = dict(row_map.get(field, {}))
        row = {
            "field": field,
            "field_path_hash": str(raw.get("field_path_hash", "")),
            "covered_provider_family_count": int(
                raw.get("covered_provider_family_count", 0)
            ),
            "covered_surface_count": int(raw.get("covered_surface_count", 0)),
            "public_projection_safe": raw.get("public_projection_safe") is True,
        }
        row["ready"] = (
            bool(row["field_path_hash"])
            and row["covered_provider_family_count"] >= provider_count
            and row["covered_surface_count"] >= surface_count
            and row["public_projection_safe"]
        )
        row["field_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["field_hash"] for row in rows]),
    }


def _negative_drift_rows(
    sentinel_input: dict[str, Any], required_failures: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(sentinel_input, "negative_drift_rows")
    rows = []
    for case_id in required_failures:
        raw = dict(row_map.get(case_id, {}))
        row = {
            "case_id": case_id,
            "fixture_hash": str(raw.get("fixture_hash", "")),
            "drift_detected": raw.get("drift_detected") is True,
            "route_revoked": raw.get("route_revoked") is True,
            "settlement_held": raw.get("settlement_held") is True,
            "customer_notice_hash": str(raw.get("customer_notice_hash", "")),
            "creator_notice_hash": str(raw.get("creator_notice_hash", "")),
            "remediation_status_hash": str(raw.get("remediation_status_hash", "")),
        }
        row["ready"] = (
            row["drift_detected"]
            and row["route_revoked"]
            and row["settlement_held"]
            and bool(row["fixture_hash"])
            and bool(row["customer_notice_hash"])
            and bool(row["creator_notice_hash"])
            and bool(row["remediation_status_hash"])
        )
        row["negative_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["negative_hash"] for row in rows]),
    }


def _artifact_summary(sentinel_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = sentinel_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_provider_drift_sentinel(
    sentinel_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L158 drift sentinel for provider-wide RDLLM adoption."""

    created_at = created_at or now_iso()
    policy = _policy(sentinel_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_surfaces = [str(name) for name in policy["required_drift_surfaces"]]
    required_cadences = [str(name) for name in policy["required_canary_cadences"]]
    required_fields = [str(name) for name in policy["required_sentinel_fields"]]
    required_failures = [str(name) for name in policy["required_drift_failures"]]

    artifact_bindings = _artifact_bindings(sentinel_input, required_artifacts)
    drift_surfaces = _drift_surface_rows(
        sentinel_input, required_families, required_surfaces
    )
    canary_replays = _canary_replay_rows(
        sentinel_input, required_families, required_cadences
    )
    field_rows = _sentinel_field_rows(
        sentinel_input, required_fields, required_families, required_surfaces
    )
    negative_rows = _negative_drift_rows(sentinel_input, required_failures)

    certification_summary = _artifact_summary(sentinel_input, "certification_report")
    provider_card = sentinel_input.get("provider_attribution_card", {})
    integration_profile = sentinel_input.get("integration_profile", {})
    discovery_manifest = sentinel_input.get("discovery_manifest", {})
    harness_summary = _artifact_summary(
        sentinel_input, "universal_provider_adapter_harness"
    )

    core_artifacts_ready = all(
        row["present"] and row["hash_reproducible"]
        for row in artifact_bindings["bindings"]
    )
    public_projection = {
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "drift_surfaces": drift_surfaces,
        "canary_replays": canary_replays,
        "sentinel_field_rows": field_rows,
        "negative_drift_rows": negative_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_level_at_least_l157": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level", ""),
                MINIMUM_HARNESS_LEVEL,
            )
        ),
        "provider_card_declares_drift_sentinel": (
            provider_card.get("public_disclosure_surfaces", {}).get(
                "universal_provider_drift_sentinel"
            )
            is True
            and provider_card.get("supported_evidence_channels", {}).get(
                "universal_provider_drift_sentinel"
            )
            is True
        ),
        "integration_profile_declares_drift_sentinel": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_provider_drift_sentinel"
            )
            is True
            and "universal_provider_drift_sentinel"
            in integration_profile.get("schemas", {})
        ),
        "discovery_manifest_exposes_drift_sentinel_path": (
            discovery_manifest.get("discovery", {}).get(
                "universal_provider_drift_sentinel_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "adapter_harness_ready_l157": (
            harness_summary.get("status") == "ready"
            and harness_summary.get("target_certification_level")
            == MINIMUM_HARNESS_LEVEL
        ),
        "all_provider_drift_surfaces_monitored": (
            drift_surfaces["ready_count"] == drift_surfaces["row_count"]
        ),
        "all_provider_canaries_replayed": (
            canary_replays["ready_count"] == canary_replays["row_count"]
        ),
        "sentinel_fields_cover_all_surfaces": (
            field_rows["ready_count"] == field_rows["row_count"]
        ),
        "negative_drift_fixtures_fail_closed": (
            negative_rows["ready_count"] == negative_rows["row_count"]
        ),
        "public_projection_omits_private_payloads": (
            not private_findings
            and _private_strings_absent(public_projection, sentinel_input)
        ),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    sentinel_decision = {
        "universal_provider_drift_sentinel_authorized": not failure_modes,
        "failure_modes": failure_modes,
        "on_failure": "revoke_grounded_display_hold_settlement_and_publish_status",
        "revocation_required_for": [
            "source_footer_display",
            "claim_provenance_trust",
            "copy_status_reliance",
            "creator_settlement_release",
            "customer_procurement_claim",
        ],
    }

    sentinel = {
        "universal_provider_drift_sentinel_version": UNIVERSAL_PROVIDER_DRIFT_SENTINEL_VERSION,
        "schema": UNIVERSAL_PROVIDER_DRIFT_SENTINEL_SCHEMA,
        "issuer": issuer,
        "created_at": created_at,
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "drift_surface_rows": drift_surfaces,
        "canary_replay_rows": canary_replays,
        "sentinel_field_rows": field_rows,
        "negative_drift_rows": negative_rows,
        "checks": checks,
        "sentinel_decision": sentinel_decision,
        "privacy": {
            "public_artifact_uses_hashes_only": True,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payload_disclosed": False,
            "private_field_count": len(private_findings),
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_PROVIDER_DRIFT_SENTINEL_SCHEMA,
            "create": "universal-provider-drift-sentinel",
            "verify": "verify-universal-provider-drift-sentinel",
        },
        "summary": {
            "status": (
                "ready"
                if sentinel_decision["universal_provider_drift_sentinel_authorized"]
                else "blocked"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_harness_level": MINIMUM_HARNESS_LEVEL,
            "provider_family_count": len(required_families),
            "drift_surface_count": len(required_surfaces),
            "provider_surface_count": drift_surfaces["row_count"],
            "ready_provider_surface_count": drift_surfaces["ready_count"],
            "canary_cadence_count": len(required_cadences),
            "canary_replay_count": canary_replays["row_count"],
            "ready_canary_replay_count": canary_replays["ready_count"],
            "sentinel_field_count": field_rows["row_count"],
            "ready_sentinel_field_count": field_rows["ready_count"],
            "negative_drift_fixture_count": negative_rows["row_count"],
            "ready_negative_drift_fixture_count": negative_rows["ready_count"],
            "core_artifact_count": len(required_artifacts),
            "failure_mode_count": len(failure_modes),
            "continuous_drift_monitoring_supported": True,
            "automatic_revocation_supported": True,
            "settlement_hold_on_drift_required": True,
            "offline_verification_supported": True,
            "privacy_preserved": checks["public_projection_omits_private_payloads"],
        },
    }
    sentinel["universal_provider_drift_sentinel_hash"] = hash_payload(
        _hashable_sentinel(sentinel)
    )
    sentinel["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(sentinel["universal_provider_drift_sentinel_hash"], signing_secret)
            if signing_secret
            else ""
        ),
    }
    return sentinel


def validate_universal_provider_drift_sentinel_shape(
    sentinel: dict[str, Any],
) -> list[str]:
    """Validate required public fields for an L158 drift sentinel."""

    errors: list[str] = []
    required = (
        "universal_provider_drift_sentinel_version",
        "schema",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "drift_surface_rows",
        "canary_replay_rows",
        "sentinel_field_rows",
        "negative_drift_rows",
        "checks",
        "sentinel_decision",
        "privacy",
        "well_known",
        "summary",
        "universal_provider_drift_sentinel_hash",
        "signature",
    )
    for key in required:
        if key not in sentinel:
            errors.append(f"missing universal provider drift sentinel field: {key}")
    if errors:
        return errors
    if (
        sentinel.get("universal_provider_drift_sentinel_version")
        != UNIVERSAL_PROVIDER_DRIFT_SENTINEL_VERSION
    ):
        errors.append("universal provider drift sentinel version is unsupported")
    if sentinel.get("schema") != UNIVERSAL_PROVIDER_DRIFT_SENTINEL_SCHEMA:
        errors.append("universal provider drift sentinel schema is unsupported")
    summary = sentinel.get("summary", {})
    if summary.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal provider drift sentinel target level is not RDLLM-L158")
    if summary.get("minimum_harness_level") != MINIMUM_HARNESS_LEVEL:
        errors.append("universal provider drift sentinel minimum harness level is not RDLLM-L157")
    if sentinel.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal provider drift sentinel well-known path is incorrect")
    return errors


def verify_universal_provider_drift_sentinel(
    sentinel: dict[str, Any],
    *,
    sentinel_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L158 drift sentinel against private replay input."""

    errors = validate_universal_provider_drift_sentinel_shape(sentinel)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_sentinel(sentinel))
    if expected_hash != sentinel.get("universal_provider_drift_sentinel_hash"):
        errors.append("universal provider drift sentinel hash is not reproducible")

    expected = make_universal_provider_drift_sentinel(
        sentinel_input,
        issuer=sentinel.get("issuer", DEFAULT_ISSUER),
        created_at=sentinel.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "drift_surface_rows",
        "canary_replay_rows",
        "sentinel_field_rows",
        "negative_drift_rows",
        "checks",
        "sentinel_decision",
        "privacy",
        "well_known",
        "summary",
    ):
        if expected.get(key) != sentinel.get(key):
            errors.append(f"universal provider drift sentinel {key} does not match input")
    if (
        expected.get("universal_provider_drift_sentinel_hash")
        != sentinel.get("universal_provider_drift_sentinel_hash")
    ):
        errors.append("universal provider drift sentinel hash does not match input")

    if sentinel.get("summary", {}).get("status") != "ready":
        errors.append("universal provider drift sentinel status is not ready")
    for check, passed in sentinel.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal provider drift sentinel check failed: {check}")

    private_findings = _contains_private_fields(sentinel)
    if private_findings:
        errors.append(
            "universal provider drift sentinel exposes private field(s): "
            + ", ".join(private_findings[:5])
        )
    if not _private_strings_absent(sentinel, sentinel_input):
        errors.append("universal provider drift sentinel leaked private replay text")

    signature = sentinel.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(
            sentinel.get("universal_provider_drift_sentinel_hash", ""),
            signing_secret,
        )
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal provider drift sentinel is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal provider drift sentinel signature is invalid")

    return errors
