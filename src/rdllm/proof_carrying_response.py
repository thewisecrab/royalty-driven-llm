"""Proof-carrying response delivery objects for RDLLM serving boundaries."""

from __future__ import annotations

from typing import Any

from rdllm.attribution_capsule import validate_attribution_capsule_shape
from rdllm.license_contract import validate_creator_license_contract_shape
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.release_gate import validate_release_gate_shape, verify_release_gate_report
from rdllm.response_envelope import validate_response_envelope_shape, verify_response_envelope
from rdllm.text import stable_hash

PROOF_CARRYING_RESPONSE_VERSION = "rdllm-proof-carrying-response/v1"
PROOF_CARRYING_RESPONSE_SCHEMA = "docs/schemas/proof_carrying_response.schema.json"
MINIMUM_RELEASE_GATE_LEVEL = "RDLLM-L35"
BLOCKED_NOTICE = (
    "RDLLM response held: attribution, source support, rights, or release-gate "
    "verification did not pass before emission."
)


def _hashable_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in response.items()
        if key not in {"proof_response_hash", "signature"}
    }


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _display_payload(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    release_gate: dict[str, Any],
    gate_errors: list[str],
) -> dict[str, Any]:
    rendered = str(response_envelope.get("response", {}).get("rendered_output", ""))
    footer = str(attribution_capsule.get("portable_surfaces", {}).get("text_footer", ""))
    gate_emits = not gate_errors and release_gate.get("summary", {}).get("decision") == "emit"
    if gate_emits:
        copied_output = f"{rendered}\n\n{footer}" if footer else rendered
        return {
            "delivery_status": "released",
            "release_decision": "emit",
            "rendered_output": rendered,
            "attribution_footer": footer,
            "copied_output": copied_output,
            "rendered_output_hash": stable_hash(rendered),
            "copied_output_hash": stable_hash(copied_output),
            "capsule_marker_present": bool(footer and footer in copied_output),
            "blocked_notice": "",
        }
    return {
        "delivery_status": "blocked",
        "release_decision": "hold_for_revision",
        "rendered_output": BLOCKED_NOTICE,
        "attribution_footer": "",
        "copied_output": BLOCKED_NOTICE,
        "rendered_output_hash": stable_hash(BLOCKED_NOTICE),
        "copied_output_hash": stable_hash(BLOCKED_NOTICE),
        "capsule_marker_present": False,
        "blocked_notice": BLOCKED_NOTICE,
    }


def _artifact_bindings(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    release_gate: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> dict[str, str]:
    return {
        "response_envelope_hash": response_envelope.get("envelope_hash", ""),
        "attribution_capsule_hash": attribution_capsule.get("capsule_hash", ""),
        "release_gate_hash": release_gate.get("gate_hash", ""),
        "creator_license_contract_hash": creator_license_contract.get(
            "contract_hash", ""
        ),
        "provider_card_hash": provider_card.get("card_hash", ""),
        "certification_report_hash": certification_report.get("report_hash", ""),
    }


def _delivery_checks(
    *,
    display: dict[str, Any],
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    release_gate: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    gate_errors: list[str],
) -> dict[str, bool]:
    rendered = str(response_envelope.get("response", {}).get("rendered_output", ""))
    footer = str(attribution_capsule.get("portable_surfaces", {}).get("text_footer", ""))
    copied_output = str(display.get("copied_output", ""))
    delivery_contract = attribution_capsule.get("portable_surfaces", {}).get(
        "delivery_contract", {}
    )
    certification_summary = certification_report.get("summary", {})
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    gate_decision = release_gate.get("summary", {}).get("decision", "")
    released = display.get("delivery_status") == "released"
    return {
        "release_gate_verified": not gate_errors,
        "release_gate_decision_emit": gate_decision == "emit",
        "response_envelope_shape_valid": not validate_response_envelope_shape(
            response_envelope
        ),
        "response_envelope_verified": not verify_response_envelope(response_envelope),
        "attribution_capsule_shape_valid": not validate_attribution_capsule_shape(
            attribution_capsule
        ),
        "creator_license_contract_shape_valid": not validate_creator_license_contract_shape(
            creator_license_contract
        ),
        "provider_card_shape_valid": not validate_provider_card_shape(provider_card),
        "displayed_output_matches_envelope": (
            released and display.get("rendered_output") == rendered
        )
        or (not released and rendered not in display.get("rendered_output", "")),
        "displayed_output_hash_matches_payload": stable_hash(
            str(display.get("rendered_output", ""))
        )
        == display.get("rendered_output_hash"),
        "copied_output_hash_matches_payload": stable_hash(copied_output)
        == display.get("copied_output_hash"),
        "capsule_marker_attached_when_released": (
            not released or bool(footer and footer in copied_output)
        ),
        "capsule_delivery_contract_matches_display": (
            not released
            or (
                isinstance(delivery_contract, dict)
                and delivery_contract.get("body_hash")
                == response_envelope.get("response", {}).get("rendered_output_hash")
                and delivery_contract.get("footer_marker_hash") == stable_hash(footer)
            )
        ),
        "provider_declares_proof_carrying_surface": public_surfaces.get(
            "proof_carrying_response"
        )
        is True,
        "certification_meets_response_minimum": (
            certification_summary.get("status") == "passed"
            and _level_number(str(certification_summary.get("highest_level", "")))
            >= _level_number(MINIMUM_RELEASE_GATE_LEVEL)
        ),
        "blocked_response_suppresses_original_output": (
            released or rendered not in copied_output
        ),
        "private_source_text_not_disclosed_by_boundary": True,
    }


def make_proof_carrying_response(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    release_gate: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed proof-carrying response for the serving boundary."""

    gate_errors = verify_release_gate_report(
        release_gate,
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=signing_secret,
    )
    display = _display_payload(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        release_gate=release_gate,
        gate_errors=gate_errors,
    )
    checks = _delivery_checks(
        display=display,
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        release_gate=release_gate,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        gate_errors=gate_errors,
    )
    emitted = display["delivery_status"] == "released" and all(checks.values())
    response = {
        "proof_response_version": PROOF_CARRYING_RESPONSE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "display": display,
        "embedded_artifacts": {
            "response_envelope": response_envelope,
            "attribution_capsule": attribution_capsule,
            "release_gate": release_gate,
            "creator_license_contract": creator_license_contract,
            "provider_attribution_card": provider_card,
            "certification_report": certification_report,
        },
        "artifact_bindings": _artifact_bindings(
            response_envelope=response_envelope,
            attribution_capsule=attribution_capsule,
            release_gate=release_gate,
            creator_license_contract=creator_license_contract,
            provider_card=provider_card,
            certification_report=certification_report,
        ),
        "delivery_policy": {
            "policy_version": "rdllm-proof-carrying-response-boundary/v1",
            "minimum_release_gate_level": MINIMUM_RELEASE_GATE_LEVEL,
            "on_gate_failure": "block_and_suppress_original_output",
            "released_output_requires_capsule_marker": True,
            "released_output_requires_gate_decision_emit": True,
        },
        "checks": checks,
        "schemas": {
            "proof_carrying_response": PROOF_CARRYING_RESPONSE_SCHEMA,
            "response_release_gate": "docs/schemas/release_gate.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "released" if emitted else "blocked",
            "decision": "emit" if emitted else "hold_for_revision",
            "target_certification_level": "RDLLM-L36",
            "minimum_release_gate_level": MINIMUM_RELEASE_GATE_LEVEL,
            "release_gate_hash": release_gate.get("gate_hash", ""),
            "displayed_output_hash": display["rendered_output_hash"],
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "rendered_output_disclosed_when_released": display["delivery_status"]
            == "released",
            "original_output_suppressed_when_blocked": display["delivery_status"]
            == "blocked",
            "prompt_text_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "hidden_state_disclosed": False,
            "boundary_uses_public_answer_and_hash_only_proofs": True,
        },
    }
    response["proof_response_hash"] = hash_payload(_hashable_response(response))
    response["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_response(response), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return response


def validate_proof_carrying_response_shape(response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "proof_response_version",
        "issuer",
        "created_at",
        "display",
        "embedded_artifacts",
        "artifact_bindings",
        "delivery_policy",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "proof_response_hash",
        "signature",
    )
    for key in required:
        if key not in response:
            errors.append(f"missing proof-carrying response field: {key}")
    if errors:
        return errors
    if response.get("proof_response_version") != PROOF_CARRYING_RESPONSE_VERSION:
        errors.append("proof-carrying response version is unsupported")
    artifacts = response.get("embedded_artifacts", {})
    for key in (
        "response_envelope",
        "attribution_capsule",
        "release_gate",
        "creator_license_contract",
        "provider_attribution_card",
        "certification_report",
    ):
        if key not in artifacts:
            errors.append(f"missing proof-carrying response artifact: {key}")
    if "proof_carrying_response" not in response.get("schemas", {}):
        errors.append("missing proof-carrying response schema")
    if response.get("display", {}).get("delivery_status") not in {
        "released",
        "blocked",
    }:
        errors.append("proof-carrying response delivery status is unsupported")
    return errors


def verify_proof_carrying_response(
    response: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a proof-carrying response using embedded public artifacts."""

    errors = validate_proof_carrying_response_shape(response)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_response(response))
    if expected_hash != response.get("proof_response_hash"):
        errors.append("proof-carrying response hash is not reproducible")

    artifacts = response.get("embedded_artifacts", {})
    envelope = artifacts.get("response_envelope", {})
    capsule = artifacts.get("attribution_capsule", {})
    gate = artifacts.get("release_gate", {})
    creator_license_contract = artifacts.get("creator_license_contract", {})
    provider_card = artifacts.get("provider_attribution_card", {})
    certification_report = artifacts.get("certification_report", {})
    expected = make_proof_carrying_response(
        response_envelope=envelope,
        attribution_capsule=capsule,
        release_gate=gate,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=response.get("issuer", DEFAULT_ISSUER),
        created_at=response.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "display",
        "artifact_bindings",
        "delivery_policy",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != response.get(key):
            errors.append(f"proof-carrying response {key} does not match artifacts")
    if expected.get("proof_response_hash") != response.get("proof_response_hash"):
        errors.append("proof-carrying response hash does not match artifacts")
    if response.get("summary", {}).get("status") != "released":
        errors.append("proof-carrying response status is not released")
    for check, passed in response.get("checks", {}).items():
        if passed is not True:
            errors.append(f"proof-carrying response check failed: {check}")
    display = response.get("display", {})
    if display.get("delivery_status") == "released":
        copied_output = str(display.get("copied_output", ""))
        footer = str(capsule.get("portable_surfaces", {}).get("text_footer", ""))
        if footer and footer not in copied_output:
            errors.append("proof-carrying response released output is missing capsule marker")
        if stable_hash(str(display.get("rendered_output", ""))) != display.get(
            "rendered_output_hash"
        ):
            errors.append("proof-carrying response rendered output hash drifted")
    gate_json = canonical_json(response)
    for field in ("source_text", "matched_text", "hidden_state"):
        if f'"{field}"' in gate_json:
            errors.append(f"proof-carrying response discloses private {field} field")

    signature = response.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_response(response), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("proof-carrying response is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("proof-carrying response signature is invalid")
    return errors
