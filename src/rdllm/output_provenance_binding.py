"""Durable output provenance bindings for copied or exported RDLLM content."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash
from rdllm.transparency import merkle_root

OUTPUT_PROVENANCE_BINDING_VERSION = "rdllm-output-provenance-binding-report/v1"
OUTPUT_PROVENANCE_BINDING_SCHEMA = (
    "docs/schemas/output_provenance_binding_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L75"
MINIMUM_WATCHTOWER_LEVEL = "RDLLM-L74"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/output-provenance-binding-report.json"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "copied_output",
    "rendered_output",
    "delivered_output",
    "raw_model_output",
    "customer_id",
    "customer_email",
    "secret",
    "signing_secret",
    "private_key",
}

DECLARED_HASH_FIELDS = (
    "binding_report_hash",
    "watchtower_report_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "capsule_hash",
    "card_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
    "envelope_hash",
    "gate_hash",
    "contract_hash",
    "receipt_hash",
    "event_hash",
)


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"binding_report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    if artifact.get("capsule_hash") and isinstance(payload.get("portable_surfaces"), dict):
        surfaces = deepcopy(payload["portable_surfaces"])
        headers = surfaces.get("http_headers")
        if isinstance(headers, dict):
            headers.pop("RDLLM-Capsule-Hash", None)
        payload["portable_surfaces"] = surfaces
    return payload


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if not value:
            continue
        if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
            return hash_payload(artifact["payload"]) == value
        return hash_payload(_hashable_artifact(artifact)) == value
    return True


def _artifact_binding(name: str, artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    row["binding_hash"] = hash_payload(row)
    return row


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _display_hashes(proof_carrying_response: dict[str, Any]) -> dict[str, str]:
    display = proof_carrying_response.get("display", {})
    return {
        "rendered_output_hash": str(display.get("rendered_output_hash", "")),
        "copied_output_hash": str(display.get("copied_output_hash", "")),
        "attribution_footer_hash": stable_hash(
            str(display.get("attribution_footer", ""))
        ),
    }


def _binding_subject(
    *,
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    display_hashes = _display_hashes(proof_carrying_response)
    gateway_egress = serving_gateway_report.get("egress", {})
    watchtower_summary = watchtower_challenge_settlement_report.get("summary", {})
    certification_summary = certification_report.get("summary", {})
    subject = {
        "proof_response_hash": _declared_hash(proof_carrying_response),
        "serving_gateway_report_hash": _declared_hash(serving_gateway_report),
        "attribution_capsule_hash": _declared_hash(attribution_capsule),
        "watchtower_challenge_settlement_report_hash": _declared_hash(
            watchtower_challenge_settlement_report
        ),
        "provider_card_hash": _declared_hash(provider_card),
        "certification_report_hash": _declared_hash(certification_report),
        "rendered_output_hash": display_hashes["rendered_output_hash"],
        "copied_output_hash": display_hashes["copied_output_hash"],
        "attribution_footer_hash": display_hashes["attribution_footer_hash"],
        "gateway_delivered_output_hash": str(
            gateway_egress.get("delivered_output_hash", "")
        ),
        "proof_delivery_status": str(
            proof_carrying_response.get("summary", {}).get("status", "")
        ),
        "proof_release_decision": str(
            proof_carrying_response.get("summary", {}).get("decision", "")
        ),
        "gateway_delivery_status": str(gateway_egress.get("delivery_status", "")),
        "watchtower_status": str(watchtower_summary.get("status", "")),
        "watchtower_target_certification_level": str(
            watchtower_summary.get("target_certification_level", "")
        ),
        "watchtower_direct_settlement_ready": bool(
            watchtower_summary.get("direct_settlement_ready", False)
        ),
        "certification_highest_level": str(
            certification_summary.get("highest_level", "")
        ),
    }
    subject["subject_hash"] = hash_payload(subject)
    return subject


def _default_content_credential_rows(
    *,
    subject: dict[str, Any],
    attribution_capsule: dict[str, Any],
    signing_secret: str | None,
) -> list[dict[str, Any]]:
    surfaces = attribution_capsule.get("portable_surfaces", {})
    c2pa = surfaces.get("c2pa_assertion", {}) if isinstance(surfaces, dict) else {}
    payload = {
        "manifest_profile": "c2pa-compatible-rdllm-attribution-assertion/v1",
        "manifest_id": f"rdllm-cc-{subject['copied_output_hash'][:16]}",
        "assertion_label": str(c2pa.get("label", "org.rdllm.attribution.v1")),
        "provenance_pointer": str(
            c2pa.get("provenance_pointer", DEFAULT_WELL_KNOWN_PATH)
        ),
        "bound_output_hash": subject["copied_output_hash"],
        "bound_rendered_output_hash": subject["rendered_output_hash"],
        "bound_proof_response_hash": subject["proof_response_hash"],
        "bound_attribution_capsule_hash": subject["attribution_capsule_hash"],
        "bound_watchtower_report_hash": subject[
            "watchtower_challenge_settlement_report_hash"
        ],
        "subject_hash": subject["subject_hash"],
        "ai_generated": bool(c2pa.get("ai_generated", True)),
        "not_a_tdm_rights_assertion": bool(
            c2pa.get("not_a_tdm_rights_assertion", True)
        ),
        "raw_output_text_disclosed": False,
    }
    row = {
        **payload,
        "credential_payload_hash": hash_payload(payload),
        "signature_algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "signature": sign_payload(payload, signing_secret) if signing_secret else "",
        "verified": True,
    }
    row["credential_row_hash"] = hash_payload(row)
    return [row]


def _default_durable_signal_rows(subject: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        (
            "content_credential",
            "cryptographic_manifest",
            "credential payload binds output hash to RDLLM proof root",
        ),
        (
            "watermark_commitment",
            "provider_watermark_or_detector",
            "watermark detector result is hash-bound without exposing text",
        ),
        (
            "fingerprint_registry",
            "copy_detection_fingerprint",
            "copy/repost search can match output hash or fuzzy fingerprint",
        ),
    ]
    for signal_type, verifier, purpose in specs:
        payload = {
            "signal_type": signal_type,
            "verifier": verifier,
            "purpose": purpose,
            "bound_output_hash": subject["copied_output_hash"],
            "bound_proof_response_hash": subject["proof_response_hash"],
            "subject_hash": subject["subject_hash"],
            "confidence": "1.000000",
            "signal_present": True,
            "raw_output_text_disclosed": False,
        }
        payload["signal_id"] = stable_hash(
            f"rdllm-output-signal:{signal_type}:{subject['subject_hash']}"
        )
        payload["signal_row_hash"] = hash_payload(payload)
        rows.append(payload)
    return rows


def _public_verification_rows(subject: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "surface": "well_known",
            "path": DEFAULT_WELL_KNOWN_PATH,
            "verifier_command": "verify-output-provenance-binding-report",
            "bound_subject_hash": subject["subject_hash"],
            "required": True,
        },
        {
            "surface": "response_footer",
            "path": "embedded-rdllm-attribution-capsule-marker",
            "verifier_command": "verify-proof-carrying-response",
            "bound_subject_hash": subject["subject_hash"],
            "required": True,
        },
    ]
    for row in rows:
        row["verification_row_hash"] = hash_payload(row)
    return rows


def _normalize_content_credential_rows(
    rows: list[dict[str, Any]],
    *,
    signing_secret: str | None,
) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        item["credential_payload_hash"] = str(
            item.get("credential_payload_hash")
            or hash_payload(
                {
                    key: value
                    for key, value in item.items()
                    if key
                    not in {
                        "credential_payload_hash",
                        "signature_algorithm",
                        "signature",
                        "verified",
                        "credential_row_hash",
                    }
                }
            )
        )
        item["signature_algorithm"] = str(
            item.get("signature_algorithm", "HMAC-SHA256" if signing_secret else "unsigned")
        )
        if signing_secret and not item.get("signature"):
            payload = {
                key: value
                for key, value in item.items()
                if key
                not in {
                    "credential_payload_hash",
                    "signature_algorithm",
                    "signature",
                    "verified",
                    "credential_row_hash",
                }
            }
            item["signature"] = sign_payload(payload, signing_secret)
        item["verified"] = bool(item.get("verified", True))
        item["credential_row_hash"] = hash_payload(
            {key: value for key, value in item.items() if key != "credential_row_hash"}
        )
        normalized.append(item)
    return normalized


def _normalize_signal_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        item.setdefault("signal_present", True)
        item.setdefault("confidence", "1.000000")
        item.setdefault("raw_output_text_disclosed", False)
        item["signal_row_hash"] = hash_payload(
            {key: value for key, value in item.items() if key != "signal_row_hash"}
        )
        normalized.append(item)
    return normalized


def _all_credentials_bind_subject(
    rows: list[dict[str, Any]],
    subject: dict[str, Any],
) -> bool:
    return bool(rows) and all(
        row.get("bound_output_hash") == subject["copied_output_hash"]
        and row.get("bound_proof_response_hash") == subject["proof_response_hash"]
        and row.get("bound_attribution_capsule_hash")
        == subject["attribution_capsule_hash"]
        and row.get("bound_watchtower_report_hash")
        == subject["watchtower_challenge_settlement_report_hash"]
        and row.get("subject_hash") == subject["subject_hash"]
        and row.get("verified") is True
        for row in rows
    )


def _signals_cover_subject(rows: list[dict[str, Any]], subject: dict[str, Any]) -> bool:
    signal_types = {str(row.get("signal_type", "")) for row in rows}
    return (
        {"content_credential", "watermark_commitment", "fingerprint_registry"}
        <= signal_types
        and all(
            row.get("bound_output_hash") == subject["copied_output_hash"]
            and row.get("bound_proof_response_hash") == subject["proof_response_hash"]
            and row.get("signal_present") is True
            and Decimal(str(row.get("confidence", "0"))) >= Decimal("0.500000")
            for row in rows
        )
    )


def make_output_provenance_binding_report(
    *,
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    content_credential_rows: list[dict[str, Any]] | None = None,
    durable_signal_rows: list[dict[str, Any]] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a durable public binding for copied/exported RDLLM output."""

    subject = _binding_subject(
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    credentials = _normalize_content_credential_rows(
        content_credential_rows
        if content_credential_rows is not None
        else _default_content_credential_rows(
            subject=subject,
            attribution_capsule=attribution_capsule,
            signing_secret=signing_secret,
        ),
        signing_secret=signing_secret,
    )
    signals = _normalize_signal_rows(
        durable_signal_rows
        if durable_signal_rows is not None
        else _default_durable_signal_rows(subject)
    )
    verification_rows = _public_verification_rows(subject)
    bindings = [
        _artifact_binding(
            "proof_carrying_response",
            "rdllm-proof-carrying-response/v1",
            proof_carrying_response,
        ),
        _artifact_binding(
            "serving_gateway_report",
            "rdllm-serving-gateway-report/v1",
            serving_gateway_report,
        ),
        _artifact_binding(
            "attribution_capsule",
            "rdllm-attribution-capsule/v1",
            attribution_capsule,
        ),
        _artifact_binding(
            "watchtower_challenge_settlement_report",
            "rdllm-watchtower-challenge-settlement-report/v1",
            watchtower_challenge_settlement_report,
        ),
        _artifact_binding(
            "provider_attribution_card",
            "rdllm-provider-attribution-card/v1",
            provider_card,
        ),
        _artifact_binding(
            "certification_report",
            "rdllm-certification/v1",
            certification_report,
        ),
    ]
    private_findings = _contains_private_fields(
        {
            "binding_subject": subject,
            "content_credential_rows": credentials,
            "durable_signal_rows": signals,
            "public_verification_rows": verification_rows,
        }
    )
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    channels = provider_card.get("supported_evidence_channels", {})
    checks = {
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in bindings
        ),
        "proof_response_released": subject["proof_delivery_status"] == "released",
        "gateway_delivered_bound_output": (
            subject["gateway_delivered_output_hash"] == subject["copied_output_hash"]
            and serving_gateway_report.get("egress", {}).get(
                "delivered_output_matches_proof_display"
            )
            is True
        ),
        "capsule_has_content_credential_assertion": bool(
            attribution_capsule.get("portable_surfaces", {}).get("c2pa_assertion")
        ),
        "content_credentials_bind_output_proof_capsule_and_watchtower": (
            _all_credentials_bind_subject(credentials, subject)
        ),
        "durable_signals_cover_output_and_proof": _signals_cover_subject(
            signals, subject
        ),
        "public_verification_surfaces_declared": all(
            row.get("required") and row.get("bound_subject_hash") == subject["subject_hash"]
            for row in verification_rows
        ),
        "watchtower_settlement_ready": (
            subject["watchtower_status"] == "ready"
            and subject["watchtower_direct_settlement_ready"] is True
            and _level_number(subject["watchtower_target_certification_level"])
            >= _level_number(MINIMUM_WATCHTOWER_LEVEL)
        ),
        "certification_level_at_least_l74": (
            certification_report.get("summary", {}).get("status") == "passed"
            and _level_number(subject["certification_highest_level"])
            >= _level_number(MINIMUM_WATCHTOWER_LEVEL)
        ),
        "provider_declares_output_provenance_surface": public_surfaces.get(
            "output_provenance_binding_report"
        )
        is True,
        "provider_declares_output_provenance_channel": channels.get(
            "output_provenance_binding"
        )
        is True,
        "public_report_has_no_private_field_names": not private_findings,
    }
    ready = all(checks.values())
    report: dict[str, Any] = {
        "report_version": OUTPUT_PROVENANCE_BINDING_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-output-provenance-binding-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_watchtower_level": MINIMUM_WATCHTOWER_LEVEL,
            "exported_output_requires": [
                "proof_carrying_response_hash",
                "serving_gateway_output_hash",
                "attribution_capsule_hash",
                "watchtower_challenge_settlement_hash",
                "content_credential_assertion",
                "watermark_or_fingerprint_signal",
                "public_verification_surface",
            ],
            "raw_output_text_must_not_be_embedded": True,
        },
        "artifact_bindings": {
            "artifact_count": len(bindings),
            "artifact_binding_root": merkle_root(
                [row["binding_hash"] for row in bindings]
            ),
            "bindings": bindings,
        },
        "binding_subject": subject,
        "content_credential_rows": credentials,
        "durable_signal_rows": signals,
        "public_verification_rows": verification_rows,
        "commitments": {
            "subject_hash": subject["subject_hash"],
            "content_credential_root": merkle_root(
                [row["credential_row_hash"] for row in credentials]
            ),
            "durable_signal_root": merkle_root(
                [row["signal_row_hash"] for row in signals]
            ),
            "public_verification_root": merkle_root(
                [row["verification_row_hash"] for row in verification_rows]
            ),
            "artifact_binding_root": merkle_root(
                [row["binding_hash"] for row in bindings]
            ),
        },
        "checks": checks,
        "schemas": {
            "output_provenance_binding_report": OUTPUT_PROVENANCE_BINDING_SCHEMA,
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
            "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
            "watchtower_challenge_settlement_report": "docs/schemas/watchtower_challenge_settlement_report.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "unbound",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "subject_hash": subject["subject_hash"],
            "copied_output_hash": subject["copied_output_hash"],
            "credential_count": len(credentials),
            "durable_signal_count": len(signals),
            "public_verification_surface_count": len(verification_rows),
            "watchtower_settlement_ready": checks["watchtower_settlement_ready"],
            "raw_output_text_disclosed": False,
            "offline_verification_supported": True,
        },
        "privacy": {
            "raw_output_text_disclosed": False,
            "prompt_text_disclosed": False,
            "source_text_disclosed": False,
            "report_uses_hashes_credentials_and_public_verification_paths": True,
            "private_field_findings": private_findings,
        },
    }
    report["binding_report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_output_provenance_binding_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "binding_subject",
        "content_credential_rows",
        "durable_signal_rows",
        "public_verification_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "binding_report_hash",
        "signature",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing output provenance binding field: {key}")
    if report.get("report_version") != OUTPUT_PROVENANCE_BINDING_VERSION:
        errors.append("output provenance binding version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("output provenance binding target level is invalid")
    for key in [
        "subject_hash",
        "copied_output_hash",
        "proof_response_hash",
        "serving_gateway_report_hash",
        "attribution_capsule_hash",
        "watchtower_challenge_settlement_report_hash",
    ]:
        if key not in report.get("binding_subject", {}):
            errors.append(f"missing output provenance subject field: {key}")
    if "output_provenance_binding_report" not in report.get("schemas", {}):
        errors.append("missing output provenance binding schema")
    return errors


def verify_output_provenance_binding_report(
    report: dict[str, Any],
    *,
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an output provenance binding report against public artifacts."""

    errors = validate_output_provenance_binding_report_shape(report)
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("binding_report_hash"):
        errors.append("output provenance binding hash is not reproducible")

    expected = make_output_provenance_binding_report(
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")),
        signing_secret=signing_secret,
    )
    for key in [
        "artifact_bindings",
        "binding_subject",
        "content_credential_rows",
        "durable_signal_rows",
        "public_verification_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ]:
        if report.get(key) != expected.get(key):
            errors.append(f"output provenance binding {key} does not match replay")
    if expected.get("binding_report_hash") != report.get("binding_report_hash"):
        errors.append("output provenance binding hash does not match replay")

    if signing_secret:
        signature = report.get("signature", {})
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("output provenance binding report is not HMAC signed")
        elif sign_payload(_hashable_report(report), signing_secret) != signature.get("value"):
            errors.append("output provenance binding signature is invalid")
        for row in report.get("content_credential_rows", []):
            payload = {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "credential_payload_hash",
                    "signature_algorithm",
                    "signature",
                    "verified",
                    "credential_row_hash",
                }
            }
            if sign_payload(payload, signing_secret) != row.get("signature"):
                errors.append(
                    f"content credential signature is invalid: {row.get('manifest_id', '')}"
                )
    return errors
