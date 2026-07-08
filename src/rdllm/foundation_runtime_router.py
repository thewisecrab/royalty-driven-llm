"""Universal runtime router receipts for foundation-model provider stacks.

L127 proves that one native provider response can normalize into the RDLLM proof
contract. This L128 layer proves the routing decision around that response: every
candidate provider route is adapter-backed, conformance-backed, hash-committed,
and fail-closed so fallback or model-router logic cannot bypass attribution.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from rdllm.provider_family_registry import (
    canonical_provider_families,
    canonical_provider_family,
    unmapped_provider_families,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

FOUNDATION_RUNTIME_ROUTER_VERSION = "rdllm-foundation-runtime-router/v1"
FOUNDATION_RUNTIME_ROUTER_SCHEMA = (
    "docs/schemas/foundation_runtime_router.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L128"
MINIMUM_INPUT_LEVEL = "RDLLM-L127"

REQUIRED_PROVIDER_FAMILIES = (
    "openai_responses",
    "anthropic_messages",
    "google_gemini",
    "meta_llama",
    "mistral_chat",
    "cohere_chat",
    "xai_grok",
    "amazon_bedrock_converse",
    "azure_openai_responses",
    "openai_compatible_chat",
)

ALLOWED_NON_RELEASE_DECISIONS = {"block_display", "not_selected", "skip"}

DECLARED_HASH_FIELDS = (
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "foundation_profile_hash",
    "citation_url_health_hash",
    "source_footer_delivery_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_router_payload",
    "raw_native_response",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "raw_license_token",
    "license_server_secret",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_foundation_runtime_router_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L128 runtime-router receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"foundation_runtime_router_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if (
        isinstance(metadata, dict)
        and artifact.get("foundation_profile_hash")
        and "header_values" in metadata
    ):
        metadata = deepcopy(metadata)
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in PRIVATE_FIELD_NAMES or _contains_private_fields(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(
    report: dict[str, Any],
    router_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in router_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: str) -> int:
    if not level.startswith("RDLLM-L"):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _policy(router_input: dict[str, Any]) -> dict[str, Any]:
    policy = router_input.get("routing_policy", {})
    required_families = policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
    return {
        "profile": "rdllm-foundation-runtime-router-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "minimum_route_attribution_level": str(
            policy.get("minimum_route_attribution_level", MINIMUM_INPUT_LEVEL)
        ),
        "required_provider_families": [str(item) for item in required_families],
        "canonical_required_provider_families": list(
            canonical_provider_families(required_families)
        ),
        "selected_route_id": str(
            router_input.get("selected_route_id")
            or policy.get("selected_route_id", "")
        ),
        "selection_policy": str(
            policy.get("selection_policy", "highest_verified_rdllm_route")
        ),
        "on_unverified_route": "block_display",
        "on_fallback_route_failure": "block_display",
        "raw_router_payload_disclosure_allowed": False,
    }


def _artifact_bindings(router_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "foundation_runtime_adapter": router_input.get("foundation_runtime_adapter"),
        "foundation_provider_conformance": router_input.get(
            "foundation_provider_conformance"
        ),
        "composite_foundation_adapter": router_input.get(
            "composite_foundation_adapter"
        ),
        "foundation_api_profile": router_input.get("foundation_api_profile"),
        "discovery_manifest": router_input.get("discovery_manifest"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("runtime_router_version")
            or (artifact or {}).get("runtime_adapter_version")
            or (artifact or {}).get("conformance_version")
            or (artifact or {}).get("adapter_version")
            or (artifact or {}).get("profile_version")
            or (artifact or {}).get("manifest_version")
            or (artifact or {}).get("version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _candidate_routes(router_input: dict[str, Any]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for route in router_input.get("candidate_routes", []):
        routes.append(
            {
                "route_id": str(route.get("route_id", "")),
                "route_role": str(route.get("route_role", "")),
                "provider_id": str(route.get("provider_id", "")),
                "provider_family": str(route.get("provider_family", "")),
                "canonical_provider_family": canonical_provider_family(
                    route.get("provider_family", "")
                ),
                "native_api_version": str(route.get("native_api_version", "")),
                "native_model": str(route.get("native_model", "")),
                "provider_adapter_row_hash": str(
                    route.get("provider_adapter_row_hash", "")
                ),
                "foundation_provider_conformance_row_hash": str(
                    route.get("foundation_provider_conformance_row_hash", "")
                ),
                "runtime_adapter_hash": str(route.get("runtime_adapter_hash", "")),
                "minimum_attribution_level": str(
                    route.get("minimum_attribution_level", MINIMUM_INPUT_LEVEL)
                ),
                "fallback_decision": str(route.get("fallback_decision", "")),
                "runtime_release_authorized": bool(
                    route.get("runtime_release_authorized", False)
                ),
                "fail_closed_on_error": bool(route.get("fail_closed_on_error", False)),
                "selection_score_hash": str(route.get("selection_score_hash", "")),
                "health_check_hash": str(route.get("health_check_hash", "")),
                "route_decision_hash": str(route.get("route_decision_hash", "")),
                "observed_failure_modes": [
                    str(item) for item in route.get("observed_failure_modes", [])
                ],
            }
        )
    return routes


def _row_by_family(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("provider_family", "")): row for row in rows}


def _selected_route(
    policy: dict[str, Any],
    routes: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_route_id = policy["selected_route_id"]
    for route in routes:
        if route["route_id"] == selected_route_id:
            return route
    return {}


def _unsupported_route_families(
    routes: list[dict[str, Any]],
    adapter_rows: dict[str, dict[str, Any]],
    conformance_rows: dict[str, dict[str, Any]],
) -> list[str]:
    unsupported: list[str] = []
    for route in routes:
        family = route["provider_family"]
        if family not in adapter_rows or family not in conformance_rows:
            unsupported.append(family)
    return sorted(set(unsupported))


def _checks(
    *,
    router_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    routes: list[dict[str, Any]],
    selected_route: dict[str, Any],
) -> dict[str, bool]:
    runtime_adapter = router_input.get("foundation_runtime_adapter", {})
    composite_adapter = router_input.get("composite_foundation_adapter", {})
    provider_conformance = router_input.get("foundation_provider_conformance", {})
    adapter_rows = _row_by_family(composite_adapter.get("provider_adapter_rows", []))
    conformance_rows = _row_by_family(
        provider_conformance.get("provider_conformance_rows", [])
    )
    required_families = set(policy["required_provider_families"])
    route_families = {route["provider_family"] for route in routes}
    runtime_native = runtime_adapter.get("native_response_observation", {})
    selected_route_count = sum(
        1
        for route in routes
        if route["route_id"] == policy["selected_route_id"]
        or route["route_role"] == "selected"
    )
    selected_runtime_hash = _declared_hash(runtime_adapter)
    unsupported_families = _unsupported_route_families(
        routes, adapter_rows, conformance_rows
    )
    raw_provider_families = [
        *policy["required_provider_families"],
        *(route["provider_family"] for route in routes),
    ]
    public_report = {
        "candidate_routes": routes,
        "selected_route_id": policy["selected_route_id"],
        "selected_runtime_adapter_hash": selected_runtime_hash,
    }
    return {
        "artifact_hashes_reproducible": all(
            binding["present"] and binding["hash_reproducible"]
            for binding in artifact_bindings.values()
        ),
        "foundation_runtime_adapter_released_l127": (
            runtime_adapter.get("summary", {}).get("status") == "released"
            and runtime_adapter.get("summary", {}).get("target_certification_level")
            == MINIMUM_INPUT_LEVEL
            and runtime_adapter.get("runtime_decision", {}).get("release_authorized")
            is True
        ),
        "required_provider_families_declared": required_families
        == set(REQUIRED_PROVIDER_FAMILIES),
        "provider_families_map_to_canonical_taxonomy": not unmapped_provider_families(
            raw_provider_families
        ),
        "candidate_routes_cover_required_families": required_families.issubset(
            route_families
        ),
        "candidate_routes_supported_by_adapter_and_conformance": not unsupported_families
        and all(
            route["provider_adapter_row_hash"]
            == adapter_rows.get(route["provider_family"], {}).get(
                "provider_adapter_row_hash", ""
            )
            and route["foundation_provider_conformance_row_hash"]
            == conformance_rows.get(route["provider_family"], {}).get(
                "foundation_provider_conformance_row_hash", ""
            )
            and conformance_rows.get(route["provider_family"], {}).get(
                "provider_adapter_row_hash", ""
            )
            == route["provider_adapter_row_hash"]
            for route in routes
        ),
        "selected_route_declared_once": bool(selected_route)
        and selected_route_count == 1
        and selected_route.get("route_role") == "selected",
        "selected_route_matches_runtime_adapter": (
            bool(selected_route)
            and selected_route.get("runtime_adapter_hash") == selected_runtime_hash
            and selected_route.get("provider_id") == runtime_native.get("provider_id")
            and selected_route.get("provider_family")
            == runtime_native.get("provider_family")
            and selected_route.get("native_api_version")
            == runtime_native.get("native_api_version")
            and selected_route.get("native_model") == runtime_native.get("native_model")
        ),
        "selected_route_release_authorized": (
            bool(selected_route)
            and selected_route.get("fallback_decision") == "release"
            and selected_route.get("runtime_release_authorized") is True
        ),
        "non_selected_routes_not_released": all(
            route["fallback_decision"] in ALLOWED_NON_RELEASE_DECISIONS
            and route["runtime_release_authorized"] is False
            for route in routes
            if route["route_id"] != policy["selected_route_id"]
        ),
        "fallback_paths_fail_closed": all(
            route["fail_closed_on_error"] is True
            and (
                route["route_id"] == policy["selected_route_id"]
                or route["fallback_decision"] in ALLOWED_NON_RELEASE_DECISIONS
            )
            for route in routes
        ),
        "route_scores_and_health_are_committed": all(
            route["selection_score_hash"]
            and route["health_check_hash"]
            and route["route_decision_hash"]
            for route in routes
        ),
        "routes_meet_minimum_attribution_level": all(
            _level_number(route["minimum_attribution_level"])
            >= _level_number(policy["minimum_route_attribution_level"])
            for route in routes
        ),
        "router_observation_hash_present": bool(
            router_input.get("router_observation_hash")
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, router_input)
        ),
    }


def _failure_modes(checks: dict[str, bool]) -> list[str]:
    mapping = {
        "foundation_runtime_adapter_released_l127": "runtime_adapter_failure",
        "provider_families_map_to_canonical_taxonomy": "provider_family_taxonomy_gap",
        "candidate_routes_cover_required_families": "provider_route_coverage_failure",
        "candidate_routes_supported_by_adapter_and_conformance": "provider_route_conformance_failure",
        "selected_route_declared_once": "selected_route_mismatch",
        "selected_route_matches_runtime_adapter": "selected_route_mismatch",
        "selected_route_release_authorized": "selected_route_not_authorized",
        "non_selected_routes_not_released": "fallback_bypass",
        "fallback_paths_fail_closed": "fallback_bypass",
        "route_scores_and_health_are_committed": "uncommitted_route_decision",
        "routes_meet_minimum_attribution_level": "route_attribution_downgrade",
        "router_observation_hash_present": "missing_router_observation",
        "private_text_not_disclosed": "private_text_leak",
    }
    return sorted(
        {
            mode
            for check, mode in mapping.items()
            if checks.get(check) is not True
        }
    )


def make_foundation_runtime_router_report(
    router_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L128 universal provider-router receipt."""

    policy = _policy(router_input)
    artifact_bindings = _artifact_bindings(router_input)
    routes = _candidate_routes(router_input)
    selected_route = _selected_route(policy, routes)
    checks = _checks(
        router_input=router_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        routes=routes,
        selected_route=selected_route,
    )
    failed = [key for key, value in checks.items() if value is not True]
    blocked = bool(failed)
    failure_modes = _failure_modes(checks)
    runtime_adapter = router_input.get("foundation_runtime_adapter", {})
    normalized_contract = runtime_adapter.get("normalized_rdllm_contract", {})
    route_hashes = [
        {
            "route_id": route["route_id"],
            "provider_family": route["provider_family"],
            "canonical_provider_family": route["canonical_provider_family"],
            "route_hash": hash_payload(route),
        }
        for route in routes
    ]
    missing_required = sorted(
        set(policy["required_provider_families"])
        - {route["provider_family"] for route in routes}
    )
    report: dict[str, Any] = {
        "runtime_router_version": FOUNDATION_RUNTIME_ROUTER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "routing_policy": policy,
        "artifact_bindings": artifact_bindings,
        "candidate_route_bindings": route_hashes,
        "selected_route_binding": {
            "route_id": selected_route.get("route_id", ""),
            "provider_id": selected_route.get("provider_id", ""),
            "provider_family": selected_route.get("provider_family", ""),
            "canonical_provider_family": canonical_provider_family(
                selected_route.get("provider_family", "")
            ),
            "native_api_version": selected_route.get("native_api_version", ""),
            "native_model": selected_route.get("native_model", ""),
            "foundation_runtime_adapter_hash": selected_route.get(
                "runtime_adapter_hash", ""
            ),
            "route_decision_hash": selected_route.get("route_decision_hash", ""),
        },
        "normalized_universal_contract": {
            "profile": "rdllm-universal-foundation-runtime-routing/v1",
            "foundation_runtime_adapter_hash": _declared_hash(runtime_adapter),
            "foundation_provider_conformance_hash": _declared_hash(
                router_input.get("foundation_provider_conformance")
            ),
            "composite_foundation_adapter_hash": _declared_hash(
                router_input.get("composite_foundation_adapter")
            ),
            "foundation_profile_hash": _declared_hash(
                router_input.get("foundation_api_profile")
            ),
            "discovery_manifest_hash": _declared_hash(
                router_input.get("discovery_manifest")
            ),
            "response_envelope_hash": str(
                normalized_contract.get("response_envelope_hash", "")
            ),
            "source_footer_delivery_hash": str(
                normalized_contract.get("source_footer_delivery_hash", "")
            ),
            "citation_url_health_hash": str(
                normalized_contract.get("citation_url_health_hash", "")
            ),
        },
        "router_decision": {
            "decision": "block_display" if blocked else "release",
            "release_authorized": not blocked,
            "selected_route_id": policy["selected_route_id"],
            "selected_provider_family": selected_route.get("provider_family", ""),
            "canonical_selected_provider_family": canonical_provider_family(
                selected_route.get("provider_family", "")
            ),
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "safe_output_policy": (
                "suppress_all_provider_payloads"
                if blocked
                else "emit_selected_rdllm_runtime_contract"
            ),
        },
        "checks": checks,
        "coverage_gaps": {
            "missing_required_provider_families": missing_required,
            "unmapped_provider_families": list(
                unmapped_provider_families(
                    [
                        *policy["required_provider_families"],
                        *(route["provider_family"] for route in routes),
                    ]
                )
            ),
            "unsupported_route_families": _unsupported_route_families(
                routes,
                _row_by_family(
                    router_input.get("composite_foundation_adapter", {}).get(
                        "provider_adapter_rows", []
                    )
                ),
                _row_by_family(
                    router_input.get("foundation_provider_conformance", {}).get(
                        "provider_conformance_rows", []
                    )
                ),
            ),
            "released_non_selected_routes": [
                route["route_id"]
                for route in routes
                if route["route_id"] != policy["selected_route_id"]
                and route["fallback_decision"] == "release"
            ],
            "failed_checks": failed,
            "failure_modes": failure_modes,
        },
        "commitments": {
            "candidate_route_root": hash_payload(route_hashes),
            "router_observation_hash": str(
                router_input.get("router_observation_hash", "")
            ),
            "selected_runtime_adapter_hash": _declared_hash(runtime_adapter),
            "schema": FOUNDATION_RUNTIME_ROUTER_SCHEMA,
        },
        "schemas": {
            "foundation_runtime_router": FOUNDATION_RUNTIME_ROUTER_SCHEMA,
            "foundation_runtime_adapter": "docs/schemas/foundation_runtime_adapter.schema.json",
            "foundation_provider_conformance": "docs/schemas/foundation_provider_conformance.schema.json",
            "composite_foundation_adapter": "docs/schemas/composite_foundation_adapter.schema.json",
            "foundation_api_profile": "docs/schemas/foundation_attribution_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
        },
        "privacy": {
            "raw_router_payload_disclosed": False,
            "raw_native_response_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "hash_only_candidate_routes": True,
        },
        "summary": {
            "status": "blocked" if blocked else "released",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "candidate_route_count": len(routes),
            "required_provider_family_count": len(policy["required_provider_families"]),
            "covered_provider_family_count": len(
                {route["provider_family"] for route in routes}
            ),
            "covered_canonical_provider_family_count": len(
                canonical_provider_families(route["provider_family"] for route in routes)
            ),
            "selected_provider_family": selected_route.get("provider_family", ""),
            "canonical_selected_provider_family": canonical_provider_family(
                selected_route.get("provider_family", "")
            ),
            "failed_check_count": len(failed),
            "failure_mode_count": len(failure_modes),
            "router_release_authorized": not blocked,
            "fail_closed_router_supported": checks["fallback_paths_fail_closed"],
            "universal_foundation_routing_supported": not blocked,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["foundation_runtime_router_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_foundation_runtime_router_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "runtime_router_version",
        "issuer",
        "created_at",
        "routing_policy",
        "artifact_bindings",
        "candidate_route_bindings",
        "selected_route_binding",
        "normalized_universal_contract",
        "router_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "foundation_runtime_router_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing foundation runtime router field: {key}")
    if errors:
        return errors
    if report.get("runtime_router_version") != FOUNDATION_RUNTIME_ROUTER_VERSION:
        errors.append("foundation runtime router version is unsupported")
    if (
        report.get("schemas", {}).get("foundation_runtime_router")
        != FOUNDATION_RUNTIME_ROUTER_SCHEMA
    ):
        errors.append("foundation runtime router schema is not declared")
    if not isinstance(report.get("candidate_route_bindings"), list):
        errors.append("foundation runtime router candidate routes are not a list")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("foundation runtime router target level is not RDLLM-L128")
    return errors


def verify_foundation_runtime_router_report(
    report: dict[str, Any],
    *,
    router_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L128 universal provider-router receipt against replay inputs."""

    errors = validate_foundation_runtime_router_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "foundation_runtime_router_hash"
    ):
        errors.append("foundation runtime router hash is not reproducible")

    expected = make_foundation_runtime_router_report(
        router_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "routing_policy",
        "artifact_bindings",
        "candidate_route_bindings",
        "selected_route_binding",
        "normalized_universal_contract",
        "router_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"foundation runtime router {key} does not match inputs")
    if expected.get("foundation_runtime_router_hash") != report.get(
        "foundation_runtime_router_hash"
    ):
        errors.append("foundation runtime router hash does not match inputs")

    if report.get("summary", {}).get("status") not in {"released", "blocked"}:
        errors.append("foundation runtime router status is unsupported")
    decision = report.get("router_decision", {})
    if report.get("summary", {}).get("status") == "blocked":
        if decision.get("decision") != "block_display" or decision.get("release_authorized"):
            errors.append("foundation runtime router blocked report is not fail-closed")
    else:
        if decision.get("decision") != "release" or not decision.get("release_authorized"):
            errors.append("foundation runtime router released report is not releasable")

    if _contains_private_fields(report):
        errors.append("foundation runtime router exposes private field names")
    if not _private_strings_absent(report, router_input):
        errors.append("foundation runtime router exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("foundation runtime router is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("foundation runtime router signature is invalid")

    return errors
