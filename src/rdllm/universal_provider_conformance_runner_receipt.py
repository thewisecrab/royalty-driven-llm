"""Universal provider conformance runner receipt.

The L169 layer turns the L168 provider binding matrix into executed evidence.
Provider families cannot rely on static mapping rows alone: an official runner
must replay fixture suites against each native route, publish result hashes, bind
fresh run attestations, and prove negative canaries failed closed before route
adoption, source-footer reliance, or creator settlement is accepted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.provider_family_registry import CANONICAL_PROVIDER_FAMILIES
from rdllm.transparency import merkle_root

UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_VERSION = (
    "rdllm-universal-provider-conformance-runner-receipt/v1"
)
UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_SCHEMA = (
    "docs/schemas/universal_provider_conformance_runner_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L169"
MINIMUM_PROVIDER_BINDING_LEVEL = "RDLLM-L168"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-conformance-runner-receipt.json"
)

REQUIRED_PROVIDER_FAMILIES = CANONICAL_PROVIDER_FAMILIES

REQUIRED_FIXTURE_SUITES = (
    "sync_generation",
    "streaming_generation",
    "tool_calls",
    "retrieval_or_grounding",
    "response_envelope",
    "source_footer",
    "live_attribution_proof",
    "telemetry_spans",
    "settlement_meter",
    "revocation_status",
    "copy_export_status",
    "auditor_export",
    "negative_canaries",
)

REQUIRED_RUNNER_STAGES = (
    "official_fixture_manifest_loaded",
    "runner_image_verified",
    "provider_identity_verified",
    "provider_binding_matrix_loaded",
    "native_sdk_contract_loaded",
    "sync_generation_replayed",
    "streaming_generation_replayed",
    "tool_call_replayed",
    "retrieval_grounding_replayed",
    "response_envelope_replayed",
    "source_footer_replayed",
    "live_attribution_replayed",
    "telemetry_meter_replayed",
    "revocation_refusal_replayed",
    "copy_export_replayed",
    "settlement_audit_replayed",
    "negative_canaries_replayed",
    "public_result_published",
)

REQUIRED_NEGATIVE_RUNNER_FAILURES = (
    "stale_fixture_pack",
    "unsigned_runner_image",
    "binding_matrix_missing",
    "provider_route_skipped",
    "mocked_native_response",
    "missing_streaming_transcript",
    "unverified_tool_call_trace",
    "citation_locator_mismatch",
    "telemetry_meter_mismatch",
    "revocation_not_replayed",
    "settlement_not_replayed",
    "failing_negative_canary_accepted",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_conformance_runner_receipt_hash",
    "universal_foundation_provider_binding_matrix_hash",
    "universal_composite_rdllm_contract_hash",
    "runner_receipt_hash",
    "receipt_hash",
    "attestation_hash",
    "report_hash",
    "manifest_hash",
    "fixture_pack_hash",
    "result_log_hash",
    "route_run_hash",
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
    "streaming_transcript",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
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


def load_universal_provider_conformance_runner_receipt_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L169 conformance runner receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"universal_provider_conformance_runner_receipt_hash", "signature"}
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


def _private_strings_absent(public_payload: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _provider_binding_matrix_l168_ready(matrix: dict[str, Any] | None) -> bool:
    if not isinstance(matrix, dict):
        return False
    summary = _summary(matrix)
    decision = matrix.get("provider_binding_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PROVIDER_BINDING_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("provider_binding_matrix_ready") is True
        and decision.get("universal_provider_adoption_claim_allowed") is True
        and decision.get("bound_provider_invocation_allowed") is True
        and decision.get("creator_settlement_allowed_for_bound_providers") is True
    )


def _fixture_suite_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "suite_hash",
        "fixture_hash",
        "transcript_hash",
        "expected_result_hash",
        "observed_result_hash",
        "verifier_hash",
    )
    required_flags = (
        "executed",
        "passed",
        "l168_bound",
        "public_or_auditor_accessible",
        "fail_closed_on_error",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _stage_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("stage_hash", "evidence_hash", "verifier_hash")
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True
        for flag in (
            "executed",
            "passed",
            "public_or_auditor_accessible",
            "fail_closed_on_error",
        )
    )


def _provider_run_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "run_hash",
        "provider_binding_hash",
        "runner_image_digest",
        "fixture_pack_hash",
        "native_transcript_hash",
        "result_log_hash",
        "public_result_hash",
        "attestation_hash",
        "verifier_hash",
    )
    required_flags = (
        "provider_identity_verified",
        "binding_matrix_matched",
        "runner_image_verified",
        "official_fixtures_executed",
        "all_fixture_suites_passed",
        "negative_canaries_rejected",
        "fresh_within_sla",
        "public_result_published",
        "fail_closed",
        "private_payloads_excluded",
    )
    if not all(str(row.get(field, "")) for field in required_hashes):
        return False
    if not all(row.get(flag) is True for flag in required_flags):
        return False
    suites = row.get("fixture_suite_results", {})
    if not isinstance(suites, dict):
        return False
    if not all(suites.get(suite) == "passed" for suite in REQUIRED_FIXTURE_SUITES):
        return False
    return True


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return bool(row.get("fixture_hash")) and all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "provider_claim_blocked",
            "invocation_blocked",
            "response_release_blocked",
            "source_footer_reliance_blocked",
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


def _row_map(receipt_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = receipt_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


def make_universal_provider_conformance_runner_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L169 provider conformance runner receipt."""

    binding_matrix = receipt_input.get("universal_foundation_provider_binding_matrix")
    fixture_rows = _row_map(receipt_input, "fixture_suite_rows")
    stage_rows = _row_map(receipt_input, "runner_stage_rows")
    provider_rows = _row_map(receipt_input, "provider_run_rows")
    negative_rows = _row_map(receipt_input, "negative_runner_rows")

    missing_suites, incomplete_suites = _complete_rows(
        fixture_rows, REQUIRED_FIXTURE_SUITES, _fixture_suite_ready
    )
    missing_stages, incomplete_stages = _complete_rows(
        stage_rows, REQUIRED_RUNNER_STAGES, _stage_ready
    )
    missing_providers, incomplete_providers = _complete_rows(
        provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_run_ready
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows, REQUIRED_NEGATIVE_RUNNER_FAILURES, _negative_failure_ready
    )

    provider_suite_coverage = {
        provider: sorted(
            suite
            for suite in REQUIRED_FIXTURE_SUITES
            if provider_rows.get(provider, {})
            .get("fixture_suite_results", {})
            .get(suite)
            == "passed"
        )
        for provider in REQUIRED_PROVIDER_FAMILIES
    }
    runner_stage_coverage = sorted(
        stage
        for stage in REQUIRED_RUNNER_STAGES
        if _stage_ready(stage_rows.get(stage, {}))
    )

    checks = {
        "provider_binding_matrix_bound": _artifact_hash_is_reproducible(
            binding_matrix if isinstance(binding_matrix, dict) else None
        ),
        "provider_binding_matrix_l168_ready": _provider_binding_matrix_l168_ready(
            binding_matrix if isinstance(binding_matrix, dict) else None
        ),
        "provider_run_rows_complete": not missing_providers
        and not incomplete_providers,
        "fixture_suite_rows_complete": not missing_suites and not incomplete_suites,
        "runner_stage_rows_complete": not missing_stages and not incomplete_stages,
        "provider_fixture_suite_coverage_complete": all(
            len(provider_suite_coverage.get(provider, [])) == len(REQUIRED_FIXTURE_SUITES)
            for provider in REQUIRED_PROVIDER_FAMILIES
        ),
        "negative_runner_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "conformance_runner_receipt_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    receipt_without_privacy: dict[str, Any] = {
        "universal_provider_conformance_runner_receipt_version": (
            UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_VERSION
        ),
        "schema": UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-provider-conformance-runner-receipt-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_binding_level": MINIMUM_PROVIDER_BINDING_LEVEL,
            "official_runner_required": True,
            "fresh_provider_run_required": True,
            "per_provider_fixture_replay_required": True,
            "negative_canary_replay_required": True,
            "public_result_publication_required": True,
            "private_payloads_forbidden_in_public_receipt": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_VERSION,
        },
        "provider_binding_matrix_binding": {
            "present": isinstance(binding_matrix, dict) and bool(binding_matrix),
            "artifact_hash": _declared_hash(
                binding_matrix if isinstance(binding_matrix, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    binding_matrix if isinstance(binding_matrix, dict) else None
                )
            ),
            "hash_reproducible": _artifact_hash_is_reproducible(
                binding_matrix if isinstance(binding_matrix, dict) else None
            ),
            "status": str(_summary(binding_matrix).get("status", "")),
            "level": str(_summary(binding_matrix).get("target_certification_level", "")),
        },
        "fixture_suite_rows": {
            suite: fixture_rows.get(suite, {}) for suite in REQUIRED_FIXTURE_SUITES
        },
        "runner_stage_rows": {
            stage: stage_rows.get(stage, {}) for stage in REQUIRED_RUNNER_STAGES
        },
        "provider_run_rows": {
            provider: provider_rows.get(provider, {})
            for provider in REQUIRED_PROVIDER_FAMILIES
        },
        "negative_runner_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_RUNNER_FAILURES
        },
        "evidence_roots": {
            "fixture_suite_root": merkle_root(
                [
                    hash_payload({"suite": suite, "row": fixture_rows.get(suite, {})})
                    for suite in REQUIRED_FIXTURE_SUITES
                ]
            ),
            "provider_run_root": merkle_root(
                [
                    hash_payload(
                        {"provider": provider, "row": provider_rows.get(provider, {})}
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                ]
            ),
            "runner_stage_root": merkle_root(
                [
                    hash_payload({"stage": stage, "row": stage_rows.get(stage, {})})
                    for stage in REQUIRED_RUNNER_STAGES
                ]
            ),
            "negative_runner_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_RUNNER_FAILURES
                ]
            ),
        },
        "checks": checks,
        "conformance_runner_decision": {
            "conformance_runner_receipt_ready": not failure_modes,
            "provider_onboarding_allowed": not failure_modes,
            "public_provider_adoption_claim_allowed": not failure_modes,
            "bound_route_invocation_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_allowed_for_replayed_routes": not failure_modes,
            "procurement_reliance_allowed": not failure_modes,
            "unreplayed_provider_routes_blocked": True,
            "failure_modes": failure_modes,
            "missing_fixture_suites": missing_suites,
            "incomplete_fixture_suites": incomplete_suites,
            "missing_runner_stages": missing_stages,
            "incomplete_runner_stages": incomplete_stages,
            "missing_provider_runs": missing_providers,
            "incomplete_provider_runs": incomplete_providers,
            "missing_negative_runner_failures": missing_negative,
            "incomplete_negative_runner_failures": incomplete_negative,
        },
        "runner_coverage": {
            "required_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_run_count": sum(
                1
                for provider in REQUIRED_PROVIDER_FAMILIES
                if _provider_run_ready(provider_rows.get(provider, {}))
            ),
            "required_fixture_suite_count": len(REQUIRED_FIXTURE_SUITES),
            "required_runner_stage_count": len(REQUIRED_RUNNER_STAGES),
            "ready_runner_stage_count": len(runner_stage_coverage),
            "provider_suite_coverage": provider_suite_coverage,
            "runner_stage_coverage": runner_stage_coverage,
        },
        "standards_and_research": {
            "attestation_promotion_gate": (
                "LLM supply-chain attestation work motivates promotion gates that "
                "check claim evidence before release."
            ),
            "test_result_attestation": (
                "in-toto/SLSA-style attestations motivate signed test-result "
                "predicates for runner outputs."
            ),
            "api_and_agent_replay": (
                "API and agent conformance work motivates replayable sync, "
                "streaming, tool, citation, and telemetry fixtures."
            ),
        },
    }
    privacy = {
        "private_payload_fields": _contains_private_fields(receipt_without_privacy),
        "private_strings_absent": _private_strings_absent(
            receipt_without_privacy, receipt_input
        ),
    }
    receipt = {
        **receipt_without_privacy,
        "privacy": {
            **privacy,
            "private_payloads_excluded": not privacy["private_payload_fields"]
            and privacy["private_strings_absent"],
        },
    }
    receipt["summary"] = {
        "status": "ready"
        if not failure_modes and receipt["privacy"]["private_payloads_excluded"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_provider_binding_level": MINIMUM_PROVIDER_BINDING_LEVEL,
        "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
        "ready_provider_run_count": receipt["runner_coverage"][
            "ready_provider_run_count"
        ],
        "fixture_suite_count": len(REQUIRED_FIXTURE_SUITES),
        "runner_stage_count": len(REQUIRED_RUNNER_STAGES),
        "ready_runner_stage_count": receipt["runner_coverage"][
            "ready_runner_stage_count"
        ],
        "negative_runner_failure_count": len(REQUIRED_NEGATIVE_RUNNER_FAILURES),
        "failure_mode_count": len(failure_modes),
        "privacy_preserved": receipt["privacy"]["private_payloads_excluded"],
        "signed_conformance_runner_receipt": bool(signing_secret),
    }
    receipt["universal_provider_conformance_runner_receipt_hash"] = hash_payload(
        _hashable_receipt(receipt)
    )
    if signing_secret:
        receipt["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_receipt(receipt), signing_secret),
        }
    return receipt


def validate_universal_provider_conformance_runner_receipt_shape(
    receipt: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L169 receipt."""

    errors: list[str] = []
    required = (
        "universal_provider_conformance_runner_receipt_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "provider_binding_matrix_binding",
        "fixture_suite_rows",
        "runner_stage_rows",
        "provider_run_rows",
        "negative_runner_rows",
        "evidence_roots",
        "checks",
        "conformance_runner_decision",
        "runner_coverage",
        "privacy",
        "summary",
        "universal_provider_conformance_runner_receipt_hash",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing {key}")
    if receipt.get("universal_provider_conformance_runner_receipt_version") != (
        UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_VERSION
    ):
        errors.append("unexpected universal_provider_conformance_runner_receipt_version")
    if receipt.get("schema") != UNIVERSAL_PROVIDER_CONFORMANCE_RUNNER_RECEIPT_SCHEMA:
        errors.append("unexpected schema")
    if _contains_private_fields(receipt):
        errors.append("public receipt contains private field names")
    fixture_rows = receipt.get("fixture_suite_rows", {})
    if not isinstance(fixture_rows, dict):
        errors.append("fixture_suite_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            fixture_rows, REQUIRED_FIXTURE_SUITES, _fixture_suite_ready
        )
        errors.extend(f"missing fixture suite {name}" for name in missing)
        errors.extend(f"incomplete fixture suite {name}" for name in incomplete)
    provider_rows = receipt.get("provider_run_rows", {})
    if not isinstance(provider_rows, dict):
        errors.append("provider_run_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_run_ready
        )
        errors.extend(f"missing provider run {name}" for name in missing)
        errors.extend(f"incomplete provider run {name}" for name in incomplete)
    stage_rows = receipt.get("runner_stage_rows", {})
    if not isinstance(stage_rows, dict):
        errors.append("runner_stage_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            stage_rows, REQUIRED_RUNNER_STAGES, _stage_ready
        )
        errors.extend(f"missing runner stage {name}" for name in missing)
        errors.extend(f"incomplete runner stage {name}" for name in incomplete)
    negative_rows = receipt.get("negative_runner_rows", {})
    if not isinstance(negative_rows, dict):
        errors.append("negative_runner_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            negative_rows, REQUIRED_NEGATIVE_RUNNER_FAILURES, _negative_failure_ready
        )
        errors.extend(f"missing negative runner fixture {name}" for name in missing)
        errors.extend(f"incomplete negative runner fixture {name}" for name in incomplete)
    return errors


def verify_universal_provider_conformance_runner_receipt(
    receipt_input: dict[str, Any],
    receipt: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L169 conformance runner receipt against replay input."""

    errors = validate_universal_provider_conformance_runner_receipt_shape(receipt)
    expected_hash = hash_payload(_hashable_receipt(receipt))
    if receipt.get("universal_provider_conformance_runner_receipt_hash") != expected_hash:
        errors.append("universal_provider_conformance_runner_receipt_hash mismatch")
    if signing_secret and "signature" not in receipt:
        errors.append("missing signature")
    if signing_secret:
        signature = receipt.get("signature", {})
        expected_signature = sign_payload(_hashable_receipt(receipt), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")
    replayed = make_universal_provider_conformance_runner_receipt(
        receipt_input,
        issuer=receipt.get("issuer", DEFAULT_ISSUER),
        created_at=receipt.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_provider_conformance_runner_receipt_hash") != receipt.get(
        "universal_provider_conformance_runner_receipt_hash"
    ):
        errors.append("replay hash mismatch")
    if replayed.get("summary", {}).get("status") != receipt.get("summary", {}).get("status"):
        errors.append("replay status mismatch")
    if receipt.get("summary", {}).get("status") != "ready":
        errors.append("conformance runner receipt is not ready")
    if receipt.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("private payloads are not excluded")
    return errors
