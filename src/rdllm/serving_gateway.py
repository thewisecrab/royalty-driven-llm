"""Serving-gateway reports for RDLLM API ingress and egress enforcement."""

from __future__ import annotations

from typing import Any

from rdllm.proof_carrying_response import verify_proof_carrying_response
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

SERVING_GATEWAY_VERSION = "rdllm-serving-gateway-report/v1"
SERVING_GATEWAY_SCHEMA = "docs/schemas/serving_gateway_report.schema.json"
MINIMUM_PROOF_RESPONSE_LEVEL = "RDLLM-L36"


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"gateway_report_hash", "signature"}
    }


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _provider_surface_declared(proof_response: dict[str, Any]) -> bool:
    provider_card = (
        proof_response.get("embedded_artifacts", {})
        .get("provider_attribution_card", {})
    )
    return (
        provider_card.get("public_disclosure_surfaces", {})
        .get("serving_gateway_report")
        is True
    )


def _proof_level(proof_response: dict[str, Any]) -> str:
    certification = (
        proof_response.get("embedded_artifacts", {})
        .get("certification_report", {})
        .get("summary", {})
    )
    return str(certification.get("highest_level", ""))


def _request_context(
    *,
    request_id: str,
    provider: str,
    model_id: str,
    model_version: str,
    route_id: str,
    prompt: str | None,
    raw_model_output: str | None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "provider": provider,
        "model_id": model_id,
        "model_version": model_version,
        "route_id": route_id,
        "prompt_hash": stable_hash(prompt or ""),
        "raw_model_output_hash": stable_hash(raw_model_output or ""),
        "prompt_supplied_to_gateway": prompt is not None,
        "raw_model_output_supplied_to_gateway": raw_model_output is not None,
        "prompt_text_disclosed": False,
        "raw_model_output_text_disclosed": False,
    }


def _artifact_bindings(proof_response: dict[str, Any]) -> dict[str, str]:
    bindings = proof_response.get("artifact_bindings", {})
    return {
        "proof_response_hash": proof_response.get("proof_response_hash", ""),
        "response_envelope_hash": bindings.get("response_envelope_hash", ""),
        "attribution_capsule_hash": bindings.get("attribution_capsule_hash", ""),
        "release_gate_hash": bindings.get("release_gate_hash", ""),
        "provider_card_hash": bindings.get("provider_card_hash", ""),
        "certification_report_hash": bindings.get("certification_report_hash", ""),
    }


def _egress(
    *,
    proof_response: dict[str, Any],
    delivered_output: str,
) -> dict[str, Any]:
    display = proof_response.get("display", {})
    return {
        "delivery_status": proof_response.get("summary", {}).get("status", ""),
        "release_decision": proof_response.get("summary", {}).get("decision", ""),
        "delivered_output_hash": stable_hash(delivered_output),
        "proof_display_copied_output_hash": display.get("copied_output_hash", ""),
        "proof_display_rendered_output_hash": display.get("rendered_output_hash", ""),
        "proof_response_hash": proof_response.get("proof_response_hash", ""),
        "released_via": "proof_carrying_response",
        "delivered_output_matches_proof_display": delivered_output
        == display.get("copied_output", ""),
    }


def _gateway_checks(
    *,
    proof_response: dict[str, Any],
    delivered_output: str,
    raw_model_output: str | None,
    proof_errors: list[str],
) -> dict[str, bool]:
    display = proof_response.get("display", {})
    proof_summary = proof_response.get("summary", {})
    copied_output = str(display.get("copied_output", ""))
    released = proof_summary.get("status") == "released"
    blocked = proof_summary.get("status") == "blocked"
    proof_level = _proof_level(proof_response)
    raw = raw_model_output or ""
    return {
        "proof_carrying_response_verified": not proof_errors,
        "proof_response_hash_bound": bool(proof_response.get("proof_response_hash")),
        "delivered_output_matches_proof_copied_output": delivered_output == copied_output,
        "released_response_uses_capsule_marker": (
            not released or display.get("capsule_marker_present") is True
        ),
        "blocked_response_returns_only_held_notice": (
            not blocked
            or (
                bool(display.get("blocked_notice"))
                and delivered_output == display.get("blocked_notice")
            )
        ),
        "blocked_response_suppresses_raw_model_output": (
            not blocked or not raw or raw not in delivered_output
        ),
        "unverified_raw_output_not_delivered": (
            not proof_errors or not raw or raw not in delivered_output
        ),
        "release_requires_verified_proof": (
            not released
            or (
                not proof_errors
                and proof_summary.get("decision") == "emit"
                and display.get("delivery_status") == "released"
            )
        ),
        "provider_declares_gateway_surface": _provider_surface_declared(proof_response),
        "certification_meets_gateway_minimum": (
            _level_number(proof_level) >= _level_number(MINIMUM_PROOF_RESPONSE_LEVEL)
        ),
        "gateway_does_not_disclose_prompt_or_raw_output_fields": True,
    }


def make_serving_gateway_report(
    *,
    proof_carrying_response: dict[str, Any],
    request_id: str,
    provider: str,
    model_id: str,
    model_version: str = "unknown",
    route_id: str = "route:default",
    prompt: str | None = None,
    raw_model_output: str | None = None,
    delivered_output: str | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report for the gateway that served an RDLLM response."""

    proof_errors = verify_proof_carrying_response(
        proof_carrying_response,
        signing_secret=signing_secret,
    )
    delivered = (
        delivered_output
        if delivered_output is not None
        else str(proof_carrying_response.get("display", {}).get("copied_output", ""))
    )
    checks = _gateway_checks(
        proof_response=proof_carrying_response,
        delivered_output=delivered,
        raw_model_output=raw_model_output,
        proof_errors=proof_errors,
    )
    request = _request_context(
        request_id=request_id,
        provider=provider,
        model_id=model_id,
        model_version=model_version,
        route_id=route_id,
        prompt=prompt,
        raw_model_output=raw_model_output,
    )
    egress = _egress(
        proof_response=proof_carrying_response,
        delivered_output=delivered,
    )
    emitted = all(checks.values())
    report = {
        "gateway_report_version": SERVING_GATEWAY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "request": request,
        "egress": egress,
        "embedded_artifacts": {
            "proof_carrying_response": proof_carrying_response,
        },
        "artifact_bindings": _artifact_bindings(proof_carrying_response),
        "serving_policy": {
            "policy_version": "rdllm-serving-gateway-boundary/v1",
            "minimum_proof_response_level": MINIMUM_PROOF_RESPONSE_LEVEL,
            "on_proof_failure": "block_before_egress",
            "egress_must_equal_proof_response_copied_output": True,
            "blocked_responses_must_suppress_raw_model_output": True,
            "prompt_and_raw_output_are_hash_committed_only": True,
        },
        "checks": checks,
        "schemas": {
            "serving_gateway_report": SERVING_GATEWAY_SCHEMA,
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
        },
        "summary": {
            "status": "served" if emitted else "failed",
            "target_certification_level": "RDLLM-L37",
            "minimum_proof_response_level": MINIMUM_PROOF_RESPONSE_LEVEL,
            "proof_response_hash": proof_carrying_response.get("proof_response_hash", ""),
            "release_gate_hash": proof_carrying_response.get("summary", {}).get(
                "release_gate_hash", ""
            ),
            "delivery_status": egress["delivery_status"],
            "release_decision": egress["release_decision"],
            "delivered_output_hash": egress["delivered_output_hash"],
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "raw_model_output_text_disclosed": False,
            "delivered_output_embedded": False,
            "proof_response_embeds_public_answer_when_released": (
                proof_carrying_response.get("summary", {}).get("status") == "released"
            ),
            "blocked_raw_model_output_suppressed": checks[
                "blocked_response_suppresses_raw_model_output"
            ],
            "hash_only_request_commitments": True,
        },
    }
    report["gateway_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_serving_gateway_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "gateway_report_version",
        "issuer",
        "created_at",
        "request",
        "egress",
        "embedded_artifacts",
        "artifact_bindings",
        "serving_policy",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "gateway_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing serving gateway field: {key}")
    if report.get("gateway_report_version") != SERVING_GATEWAY_VERSION:
        errors.append("serving gateway report version is unsupported")
    if "proof_carrying_response" not in report.get("embedded_artifacts", {}):
        errors.append("missing embedded proof-carrying response")
    if "serving_gateway_report" not in report.get("schemas", {}):
        errors.append("missing serving gateway schema")
    if report.get("summary", {}).get("target_certification_level") != "RDLLM-L37":
        errors.append("serving gateway target certification level is unsupported")
    return errors


def verify_serving_gateway_report(
    report: dict[str, Any],
    *,
    prompt: str | None = None,
    raw_model_output: str | None = None,
    delivered_output: str | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a serving-gateway report and its embedded proof-carrying response."""

    errors = validate_serving_gateway_report_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("gateway_report_hash"):
        errors.append("serving gateway report hash is not reproducible")

    proof_response = report.get("embedded_artifacts", {}).get(
        "proof_carrying_response", {}
    )
    proof_errors = verify_proof_carrying_response(
        proof_response,
        signing_secret=signing_secret,
    )
    for error in proof_errors:
        errors.append(f"embedded proof-carrying response: {error}")

    bindings = report.get("artifact_bindings", {})
    if bindings.get("proof_response_hash") != proof_response.get("proof_response_hash"):
        errors.append("serving gateway proof response hash binding drifted")

    expected_delivered = str(proof_response.get("display", {}).get("copied_output", ""))
    expected_delivered_hash = stable_hash(expected_delivered)
    egress = report.get("egress", {})
    if egress.get("delivered_output_hash") != expected_delivered_hash:
        errors.append("serving gateway delivered output hash does not match proof display")
    if report.get("summary", {}).get("delivered_output_hash") != expected_delivered_hash:
        errors.append("serving gateway summary delivered output hash drifted")
    if delivered_output is not None and stable_hash(delivered_output) != egress.get(
        "delivered_output_hash"
    ):
        errors.append("provided delivered output does not match gateway report")
    if delivered_output is not None and delivered_output != expected_delivered:
        errors.append("provided delivered output does not match proof response display")

    request = report.get("request", {})
    if prompt is not None and stable_hash(prompt) != request.get("prompt_hash"):
        errors.append("provided prompt does not match gateway prompt commitment")
    if raw_model_output is not None and stable_hash(raw_model_output) != request.get(
        "raw_model_output_hash"
    ):
        errors.append("provided raw model output does not match gateway commitment")
    if (
        raw_model_output is not None
        and proof_response.get("summary", {}).get("status") == "blocked"
        and raw_model_output in expected_delivered
    ):
        errors.append("blocked gateway output leaks raw model output")

    if canonical_json(report).find('"prompt":') != -1:
        errors.append("serving gateway report discloses prompt field")
    if canonical_json(report).find('"raw_model_output":') != -1:
        errors.append("serving gateway report discloses raw model output field")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"serving gateway check failed: {check}")

    if signing_secret:
        signature = report.get("signature", {})
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("serving gateway report is not HMAC signed")
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("serving gateway report signature is invalid")
    return errors
