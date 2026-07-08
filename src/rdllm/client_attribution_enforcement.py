"""Client-side enforcement receipts for attributed model API responses.

The foundation API profile defines what a conforming provider must expose. This
layer proves that a relying client actually observed and enforced that contract
before rendering an attributed answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.artifact_refs import resolve_artifact_refs
from rdllm.foundation_api_profile import verify_foundation_api_profile
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_footer_delivery import verify_source_footer_delivery_receipt
from rdllm.text import stable_hash

CLIENT_ATTRIBUTION_ENFORCEMENT_VERSION = (
    "rdllm-client-attribution-enforcement/v1"
)
CLIENT_ATTRIBUTION_ENFORCEMENT_SCHEMA = (
    "docs/schemas/client_attribution_enforcement.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L105"
MINIMUM_PROFILE_LEVEL = "RDLLM-L104"

REQUIRED_CLIENT_POLICY = {
    "missing_profile": "block_display",
    "missing_or_failed_source_footer_delivery": "block_display",
    "response_hash_drift": "block_display",
}

DECLARED_HASH_FIELDS = (
    "client_enforcement_hash",
    "foundation_profile_hash",
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


def load_client_attribution_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a client attribution enforcement receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"client_enforcement_hash", "signature"}
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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(receipt: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(receipt)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _all_required_fields_present(payload: dict[str, Any], fields: list[str]) -> bool:
    for field in fields:
        value = _get_path(payload, field)
        if value is None:
            return False
        if value == "" or value == [] or value == {}:
            return False
    return True


def _source_labels_from_delivery(delivery: dict[str, Any]) -> list[str]:
    return [
        str(row.get("label", ""))
        for row in delivery.get("source_delivery_rows", [])
        if row.get("label")
    ]


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    profile = receipt_input.get("foundation_api_profile", {})
    response_payload = receipt_input.get("response_payload", {})
    embedded_envelope = _get_path(response_payload, "embedded_artifacts.response_envelope")
    embedded_delivery = _get_path(
        response_payload, "embedded_artifacts.source_footer_delivery"
    )
    embedded_profile = _get_path(
        response_payload, "verification.foundation_attribution_profile"
    )
    return {
        "foundation_api_profile_hash": _declared_hash(profile),
        "foundation_api_profile_hash_reproducible": _artifact_hash_is_reproducible(
            profile
        ),
        "embedded_foundation_api_profile_hash": _declared_hash(embedded_profile),
        "response_envelope_hash": _declared_hash(embedded_envelope),
        "response_envelope_hash_reproducible": _artifact_hash_is_reproducible(
            embedded_envelope
        ),
        "source_footer_delivery_hash": _declared_hash(embedded_delivery),
        "source_footer_delivery_hash_reproducible": _artifact_hash_is_reproducible(
            embedded_delivery
        ),
        "observed_header_hash": hash_payload(receipt_input.get("response_headers", {})),
        "observed_payload_hash": hash_payload(response_payload),
        "rendered_output_hash": stable_hash(
            str(_get_path(response_payload, "response.rendered_output") or "")
        ),
    }


def _observed_header_rows(
    expected_values: dict[str, str],
    observed_headers: dict[str, str],
) -> list[dict[str, Any]]:
    rows = []
    for header in sorted(expected_values):
        expected = expected_values[header]
        observed = str(observed_headers.get(header, ""))
        row = {
            "name": header,
            "expected_value_hash": stable_hash(str(expected)),
            "observed_value_hash": stable_hash(observed) if observed else "",
            "present": bool(observed),
            "matches_profile": observed == str(expected),
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _client_subject(receipt_input: dict[str, Any]) -> dict[str, Any]:
    client = receipt_input.get("client", {})
    profile = receipt_input.get("foundation_api_profile", {})
    response_payload = receipt_input.get("response_payload", {})
    return {
        "client_id": str(client.get("client_id", "client:unknown")),
        "client_version": str(client.get("client_version", "")),
        "client_surface": str(client.get("client_surface", "model-api-client")),
        "render_target": str(client.get("render_target", "chat")),
        "foundation_profile_hash": profile.get("foundation_profile_hash", ""),
        "response_envelope_hash": profile.get("artifact_bindings", {}).get(
            "response_envelope_hash", ""
        ),
        "source_footer_delivery_hash": profile.get("artifact_bindings", {}).get(
            "source_footer_delivery_hash", ""
        ),
        "rendered_output_hash": stable_hash(
            str(_get_path(response_payload, "response.rendered_output") or "")
        ),
    }


def _base_checks(
    *,
    receipt_input: dict[str, Any],
    artifact_bindings: dict[str, Any],
    profile_errors: list[str],
    response_errors: list[str],
    delivery_errors: list[str],
    header_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    profile = receipt_input.get("foundation_api_profile", {})
    response_headers = receipt_input.get("response_headers", {})
    response_payload = receipt_input.get("response_payload", {})
    metadata = profile.get("response_metadata_contract", {})
    required_headers = list(metadata.get("required_http_headers", []))
    required_fields = list(metadata.get("required_json_fields", []))
    header_values = metadata.get("header_values", {})
    embedded_envelope = _get_path(response_payload, "embedded_artifacts.response_envelope")
    embedded_delivery = _get_path(
        response_payload, "embedded_artifacts.source_footer_delivery"
    )
    embedded_profile = _get_path(
        response_payload, "verification.foundation_attribution_profile"
    )
    payload_source_labels = [
        str(label) for label in _get_path(response_payload, "response.source_labels") or []
    ]
    delivery_source_labels = _source_labels_from_delivery(
        embedded_delivery if isinstance(embedded_delivery, dict) else {}
    )
    verifier_commands = [
        str(command)
        for command in _get_path(response_payload, "verification.verifier_commands")
        or []
    ]
    rendered_output_hash = stable_hash(
        str(_get_path(response_payload, "response.rendered_output") or "")
    )
    envelope_rendered_hash = ""
    if isinstance(embedded_envelope, dict):
        envelope_rendered_hash = str(
            embedded_envelope.get("response", {}).get("rendered_output_hash", "")
        )
    checks = {
        "foundation_api_profile_verified": (
            not profile_errors
            and profile.get("summary", {}).get("status") == "ready"
            and profile.get("summary", {}).get("target_certification_level")
            == MINIMUM_PROFILE_LEVEL
        ),
        "observed_headers_include_required_profile_headers": all(
            bool(response_headers.get(header)) for header in required_headers
        ),
        "observed_headers_match_profile_values": all(
            row["matches_profile"] is True for row in header_rows
        )
        and bool(header_values),
        "observed_payload_has_required_json_fields": _all_required_fields_present(
            response_payload, required_fields
        ),
        "embedded_foundation_profile_matches_observed_profile": (
            artifact_bindings.get("embedded_foundation_api_profile_hash")
            == artifact_bindings.get("foundation_api_profile_hash")
        ),
        "embedded_response_envelope_verified": not response_errors
        and isinstance(embedded_envelope, dict),
        "embedded_response_envelope_matches_profile": (
            artifact_bindings.get("response_envelope_hash")
            == profile.get("artifact_bindings", {}).get("response_envelope_hash", "")
        ),
        "embedded_source_footer_delivery_verified": not delivery_errors
        and isinstance(embedded_delivery, dict)
        and embedded_delivery.get("summary", {}).get("status") == "ready",
        "embedded_source_footer_delivery_matches_profile": (
            artifact_bindings.get("source_footer_delivery_hash")
            == profile.get("artifact_bindings", {}).get(
                "source_footer_delivery_hash", ""
            )
        ),
        "rendered_output_hash_matches_envelope": (
            bool(rendered_output_hash)
            and rendered_output_hash == envelope_rendered_hash
        ),
        "source_labels_match_delivery_rows": (
            bool(payload_source_labels)
            and payload_source_labels == delivery_source_labels
        ),
        "verifier_commands_match_profile_contract": all(
            command in verifier_commands
            for command in profile.get("verification_contract", {}).get(
                "verifier_commands", []
            )
        ),
        "client_policy_is_fail_closed": all(
            profile.get("client_failure_policy", {}).get(key) == value
            for key, value in REQUIRED_CLIENT_POLICY.items()
        ),
    }
    return checks


def make_client_attribution_enforcement_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public receipt proving a client enforced L104 before rendering."""

    receipt_input = resolve_artifact_refs(receipt_input)
    profile = receipt_input.get("foundation_api_profile", {})
    profile_input = receipt_input.get("foundation_api_profile_input", {})
    response_payload = receipt_input.get("response_payload", {})
    embedded_envelope = _get_path(response_payload, "embedded_artifacts.response_envelope")
    embedded_delivery = _get_path(
        response_payload, "embedded_artifacts.source_footer_delivery"
    )
    source_footer_delivery_input = profile_input.get("source_footer_delivery_input", {})

    profile_errors = verify_foundation_api_profile(
        profile,
        profile_input,
        signing_secret=signing_secret,
    )
    response_errors = (
        verify_response_envelope(embedded_envelope, signing_secret=signing_secret)
        if isinstance(embedded_envelope, dict)
        else ["missing embedded response envelope"]
    )
    delivery_errors = (
        verify_source_footer_delivery_receipt(
            embedded_delivery,
            source_footer_delivery_input,
            signing_secret=signing_secret,
        )
        if isinstance(embedded_delivery, dict)
        else ["missing embedded source footer delivery"]
    )

    artifact_bindings = _artifact_bindings(receipt_input)
    header_rows = _observed_header_rows(
        profile.get("response_metadata_contract", {}).get("header_values", {}),
        receipt_input.get("response_headers", {}),
    )
    checks = _base_checks(
        receipt_input=receipt_input,
        artifact_bindings=artifact_bindings,
        profile_errors=profile_errors,
        response_errors=response_errors,
        delivery_errors=delivery_errors,
        header_rows=header_rows,
    )
    expected_decision = (
        "render_attributed" if all(checks.values()) else "block_unverified_attribution"
    )
    requested_decision = str(
        receipt_input.get("client_decision", {}).get("decision", expected_decision)
    )
    checks["client_render_decision_matches_enforcement"] = (
        requested_decision == expected_decision
    )

    public_privacy_probe = {
        "artifact_bindings": artifact_bindings,
        "observed_header_results": header_rows,
        "client_subject": _client_subject(receipt_input),
        "checks": checks,
    }
    checks["private_text_not_disclosed"] = (
        not _contains_private_fields(public_privacy_probe)
        and _private_strings_absent(public_privacy_probe, receipt_input)
    )

    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "blocked"
    rendered_output_hash = artifact_bindings["rendered_output_hash"]
    payload_source_labels = [
        str(label) for label in _get_path(response_payload, "response.source_labels") or []
    ]
    receipt = {
        "version": CLIENT_ATTRIBUTION_ENFORCEMENT_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(receipt_input.get("case_id", "case:client-attribution")),
            "status": status,
        },
        "client_subject": _client_subject(receipt_input),
        "artifact_bindings": artifact_bindings,
        "observed_header_results": header_rows,
        "observed_payload_commitments": {
            "payload_hash": artifact_bindings["observed_payload_hash"],
            "rendered_output_hash": rendered_output_hash,
            "source_label_count": len(payload_source_labels),
            "source_labels_hash": hash_payload(payload_source_labels),
            "required_json_field_count": len(
                profile.get("response_metadata_contract", {}).get(
                    "required_json_fields", []
                )
            ),
        },
        "client_decision": {
            "decision": expected_decision,
            "requested_decision": requested_decision,
            "may_render_attributed_answer": expected_decision == "render_attributed",
            "rendered_output_hash": rendered_output_hash,
            "source_labels": payload_source_labels,
            "failure_action": "block_display" if failed else "render_with_sources",
            "failure_reasons": failed,
        },
        "verification_errors": {
            "foundation_api_profile_error_count": len(profile_errors),
            "response_envelope_error_count": len(response_errors),
            "source_footer_delivery_error_count": len(delivery_errors),
        },
        "checks": checks,
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payment_data_disclosed": False,
            "client_receipt_uses_hashes_and_labels": True,
        },
        "schemas": {
            "client_attribution_enforcement": CLIENT_ATTRIBUTION_ENFORCEMENT_SCHEMA,
            "foundation_api_profile": "docs/schemas/foundation_attribution_profile.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_profile_level": MINIMUM_PROFILE_LEVEL,
            "required_header_count": len(header_rows),
            "required_json_field_count": len(
                profile.get("response_metadata_contract", {}).get(
                    "required_json_fields", []
                )
            ),
            "source_label_count": len(payload_source_labels),
            "failed_check_count": len(failed),
            "client_enforcement_ready": not failed,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    receipt["client_enforcement_hash"] = hash_payload(_hashable_receipt(receipt))
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_receipt(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_client_attribution_enforcement_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "client_subject",
        "artifact_bindings",
        "observed_header_results",
        "observed_payload_commitments",
        "client_decision",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "client_enforcement_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing client enforcement field: {key}")
    if errors:
        return errors
    if receipt.get("version") != CLIENT_ATTRIBUTION_ENFORCEMENT_VERSION:
        errors.append("client enforcement version is unsupported")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("client enforcement target level is not RDLLM-L105")
    if "client_attribution_enforcement" not in receipt.get("schemas", {}):
        errors.append("missing client attribution enforcement schema")
    if not isinstance(receipt.get("observed_header_results"), list):
        errors.append("client enforcement observed_header_results must be a list")
    if receipt.get("client_decision", {}).get("decision") not in {
        "render_attributed",
        "block_unverified_attribution",
    }:
        errors.append("client enforcement decision is unsupported")
    return errors


def verify_client_attribution_enforcement_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a client attribution enforcement receipt against observed inputs."""

    errors = validate_client_attribution_enforcement_shape(receipt)
    expected = make_client_attribution_enforcement_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "client_subject",
        "artifact_bindings",
        "observed_header_results",
        "observed_payload_commitments",
        "client_decision",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if receipt.get(key) != expected.get(key):
            errors.append(f"client enforcement {key} mismatch")
    if receipt.get("client_enforcement_hash") != expected.get("client_enforcement_hash"):
        errors.append("client enforcement hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("client enforcement signature mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("client enforcement has failing checks")
    return errors
