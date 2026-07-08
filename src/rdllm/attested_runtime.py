"""Runtime attestation for attribution-enforcing model serving paths."""

from __future__ import annotations

from typing import Any

from rdllm.live_emission_transparency import (
    validate_live_emission_transparency_shape,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

ATTESTED_RUNTIME_VERSION = "rdllm-attested-attribution-runtime/v1"
ATTESTED_RUNTIME_QUOTE_VERSION = "rdllm-runtime-attestation-quote/v1"
ATTESTED_RUNTIME_SCHEMA = "docs/schemas/attested_runtime.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L86"
MINIMUM_INPUT_LEVEL = "RDLLM-L85"

REQUIRED_RUNTIME_CAPABILITIES = (
    "evidence_lock_enforced_before_generation",
    "release_gate_enforced_before_delivery",
    "serving_gateway_bound_to_proof_response",
    "streaming_chunks_bound_to_gateway_output",
    "live_witness_required_before_release",
    "live_transparency_required_before_release",
    "source_footer_required_for_supported_claims",
    "creator_pool_conservation_enforced",
    "private_text_redaction_enforced",
)

ACCEPTED_PLATFORM_TYPES = {
    "rdllm-conformance-tee",
    "intel-tdx",
    "intel-sgx",
    "amd-sev-snp",
    "arm-cca",
    "nvidia-h100-confidential-computing",
    "zkml-audit-sampler",
    "hybrid-tee-zkml",
}

DECLARED_HASH_FIELDS = (
    "attested_runtime_hash",
    "live_emission_transparency_hash",
    "live_witness_hash",
    "proof_response_hash",
    "gateway_report_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "chunk_text",
    "raw_model_output",
    "customer_id",
    "customer_email",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "attestor_secret",
    "signing_secret",
    "private_key",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"attested_runtime_hash", "signature"}
    }


def _hashable_quote(quote: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in quote.items()
        if key not in {"quote_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    return {
        key: value
        for key, value in (artifact or {}).items()
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
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return hash_payload(_hashable_artifact(artifact)) == value
    return True


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


def make_attestor_key_hash(
    attestor_id: str,
    platform_id: str,
    attestor_secret: str,
) -> str:
    """Return the public key commitment used by the reference HMAC attestor."""

    return hash_payload(
        f"rdllm-attested-runtime-attestor:{attestor_id}:{platform_id}:{attestor_secret}"
    )


def make_runtime_measurement(
    *,
    runtime_id: str,
    source_commit_hash: str,
    container_image_hash: str,
    enforcement_binary_hash: str,
    policy_bundle_hash: str,
    model_binding_hash: str,
    verifier_bundle_hash: str,
    runtime_version: str = "rdllm-reference-runtime/2026-06",
) -> dict[str, Any]:
    """Create a deterministic runtime measurement commitment."""

    measurement = {
        "runtime_id": runtime_id,
        "runtime_version": runtime_version,
        "source_commit_hash": source_commit_hash,
        "container_image_hash": container_image_hash,
        "enforcement_binary_hash": enforcement_binary_hash,
        "policy_bundle_hash": policy_bundle_hash,
        "model_binding_hash": model_binding_hash,
        "verifier_bundle_hash": verifier_bundle_hash,
        "required_capabilities": list(REQUIRED_RUNTIME_CAPABILITIES),
    }
    measurement["measurement_hash"] = hash_payload(measurement)
    return measurement


def _subject_bindings(
    *,
    live_emission_transparency: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
) -> dict[str, Any]:
    live_bindings = live_emission_transparency.get("artifact_bindings", {})
    proof_response_hash = _declared_hash(proof_carrying_response)
    gateway_report_hash = _declared_hash(serving_gateway_report)
    evidence_lock_hash = _declared_hash(evidence_locked_generation)
    bindings = {
        "live_emission_transparency_hash": _declared_hash(
            live_emission_transparency
        ),
        "live_emission_witness_hash": str(
            live_bindings.get("live_emission_witness_hash", "")
        ),
        "proof_response_hash": proof_response_hash,
        "gateway_report_hash": gateway_report_hash,
        "evidence_locked_generation_hash": evidence_lock_hash,
        "release_gate_hash": str(
            proof_carrying_response.get("summary", {}).get("release_gate_hash", "")
            or serving_gateway_report.get("summary", {}).get("release_gate_hash", "")
        ),
        "delivered_output_hash": str(
            serving_gateway_report.get("summary", {}).get("delivered_output_hash", "")
        ),
        "live_subject_root": str(
            live_emission_transparency.get("commitments", {}).get(
                "live_subject_root", ""
            )
        ),
        "transparency_log_binding_root": str(
            live_emission_transparency.get("commitments", {}).get(
                "transparency_log_binding_root", ""
            )
        ),
    }
    bindings["subject_binding_root"] = hash_payload(
        {key: value for key, value in bindings.items() if key != "subject_binding_root"}
    )
    return bindings


def make_runtime_attestation_nonce(
    *,
    runtime_measurement: dict[str, Any],
    subject_bindings: dict[str, Any],
) -> str:
    return hash_payload(
        {
            "runtime_measurement_hash": runtime_measurement.get("measurement_hash", ""),
            "subject_binding_root": subject_bindings.get("subject_binding_root", ""),
        }
    )


def make_runtime_attestation_quote(
    *,
    runtime_measurement: dict[str, Any],
    live_emission_transparency: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    attestor_id: str,
    platform_id: str,
    attestor_secret: str,
    platform_type: str = "rdllm-conformance-tee",
    created_at: str | None = None,
    expires_at: str | None = None,
    capabilities: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Create a reference runtime attestation quote over the attribution path."""

    timestamp = created_at or now_iso()
    subject_bindings = _subject_bindings(
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
    )
    runtime_capabilities = {name: True for name in REQUIRED_RUNTIME_CAPABILITIES}
    if capabilities:
        runtime_capabilities.update(capabilities)
    quote = {
        "quote_version": ATTESTED_RUNTIME_QUOTE_VERSION,
        "attestor_id": attestor_id,
        "platform_id": platform_id,
        "platform_type": platform_type,
        "attestor_key_hash": make_attestor_key_hash(
            attestor_id, platform_id, attestor_secret
        ),
        "created_at": timestamp,
        "expires_at": expires_at or timestamp,
        "runtime_measurement": runtime_measurement,
        "subject_bindings": subject_bindings,
        "nonce": make_runtime_attestation_nonce(
            runtime_measurement=runtime_measurement,
            subject_bindings=subject_bindings,
        ),
        "capabilities": runtime_capabilities,
    }
    quote["quote_hash"] = hash_payload(_hashable_quote(quote))
    quote["signature"] = {
        "algorithm": "HMAC-SHA256",
        "attestor_id": attestor_id,
        "value": sign_payload(_hashable_quote(quote), attestor_secret),
    }
    return quote


def _trusted_attestor_rows(
    trusted_attestors: list[tuple[str, str, str] | tuple[str, str, str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in trusted_attestors:
        attestor_id, platform_id, secret = item[:3]
        platform_type = item[3] if len(item) > 3 else "rdllm-conformance-tee"
        row = {
            "attestor_id": attestor_id,
            "platform_id": platform_id,
            "platform_type": platform_type,
            "attestor_key_hash": make_attestor_key_hash(
                attestor_id, platform_id, secret
            ),
            "trusted_for": "attribution_runtime_attestation",
        }
        row["attestor_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["attestor_row_hash"])


def _quote_rows(
    *,
    quotes: list[dict[str, Any]],
    trusted_attestors: list[tuple[str, str, str] | tuple[str, str, str, str]],
    expected_runtime_measurement: dict[str, Any],
    expected_subject_bindings: dict[str, Any],
    report_created_at: str,
) -> list[dict[str, Any]]:
    secret_by_trust_key = {
        (item[0], item[1], make_attestor_key_hash(item[0], item[1], item[2])): item[2]
        for item in trusted_attestors
    }
    trusted_platform_types = {
        (item[0], item[1]): item[3] if len(item) > 3 else "rdllm-conformance-tee"
        for item in trusted_attestors
    }
    rows: list[dict[str, Any]] = []
    for quote in quotes:
        attestor_id = str(quote.get("attestor_id", ""))
        platform_id = str(quote.get("platform_id", ""))
        attestor_key_hash = str(quote.get("attestor_key_hash", ""))
        secret = secret_by_trust_key.get((attestor_id, platform_id, attestor_key_hash))
        signature = quote.get("signature", {})
        expected_signature = (
            sign_payload(_hashable_quote(quote), secret) if secret else ""
        )
        created_at = str(quote.get("created_at", ""))
        expires_at = str(quote.get("expires_at", ""))
        quote_subjects = quote.get("subject_bindings", {})
        quote_measurement = quote.get("runtime_measurement", {})
        capabilities = quote.get("capabilities", {})
        row = {
            "quote_hash": str(quote.get("quote_hash", "")),
            "attestor_id": attestor_id,
            "platform_id": platform_id,
            "platform_type": str(quote.get("platform_type", "")),
            "attestor_key_hash": attestor_key_hash,
            "attestor_is_trusted": secret is not None,
            "platform_type_is_trusted": trusted_platform_types.get(
                (attestor_id, platform_id)
            )
            == quote.get("platform_type")
            and quote.get("platform_type") in ACCEPTED_PLATFORM_TYPES,
            "quote_hash_reproducible": hash_payload(_hashable_quote(quote))
            == quote.get("quote_hash"),
            "signature_valid": bool(secret)
            and signature.get("algorithm") == "HMAC-SHA256"
            and signature.get("value") == expected_signature,
            "runtime_measurement_matches": quote_measurement
            == expected_runtime_measurement,
            "subject_bindings_match": quote_subjects == expected_subject_bindings,
            "nonce_binds_measurement_and_subjects": quote.get("nonce")
            == make_runtime_attestation_nonce(
                runtime_measurement=expected_runtime_measurement,
                subject_bindings=expected_subject_bindings,
            ),
            "freshness_window_valid": bool(created_at)
            and bool(expires_at)
            and created_at <= report_created_at <= expires_at,
            "required_capabilities_present": all(
                capabilities.get(name) is True for name in REQUIRED_RUNTIME_CAPABILITIES
            ),
            "quote_has_no_private_field_names": not _contains_private_fields(
                {
                    "runtime_measurement": quote_measurement,
                    "subject_bindings": quote_subjects,
                    "capabilities": capabilities,
                }
            ),
        }
        row["accepted"] = all(
            row[key]
            for key in (
                "attestor_is_trusted",
                "platform_type_is_trusted",
                "quote_hash_reproducible",
                "signature_valid",
                "runtime_measurement_matches",
                "subject_bindings_match",
                "nonce_binds_measurement_and_subjects",
                "freshness_window_valid",
                "required_capabilities_present",
                "quote_has_no_private_field_names",
            )
        )
        row["quote_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["quote_row_hash"])


def make_attested_runtime_report(
    *,
    live_emission_transparency: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    runtime_measurement: dict[str, Any],
    runtime_quotes: list[dict[str, Any]],
    trusted_attestors: list[tuple[str, str, str] | tuple[str, str, str, str]],
    minimum_quote_count: int = 1,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L86 report proving the attribution path ran under attested code."""

    timestamp = created_at or now_iso()
    subject_bindings = _subject_bindings(
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
    )
    trusted_rows = _trusted_attestor_rows(trusted_attestors)
    quote_rows = _quote_rows(
        quotes=runtime_quotes,
        trusted_attestors=trusted_attestors,
        expected_runtime_measurement=runtime_measurement,
        expected_subject_bindings=subject_bindings,
        report_created_at=timestamp,
    )
    live_shape_errors = validate_live_emission_transparency_shape(
        live_emission_transparency
    )
    public_fields = {
        "runtime_measurement": runtime_measurement,
        "subject_bindings": subject_bindings,
        "trusted_attestors": trusted_rows,
        "quote_rows": quote_rows,
    }
    private_fields = _contains_private_fields(public_fields)
    accepted_quote_rows = [row for row in quote_rows if row["accepted"]]
    checks = {
        "live_emission_transparency_shape_valid": not live_shape_errors,
        "live_emission_transparency_hash_reproducible": _artifact_hash_is_reproducible(
            live_emission_transparency
        ),
        "live_emission_transparency_ready": live_emission_transparency.get(
            "summary", {}
        ).get("status")
        == "ready",
        "live_emission_transparency_target_l85": live_emission_transparency.get(
            "summary", {}
        ).get("target_certification_level")
        == MINIMUM_INPUT_LEVEL,
        "runtime_measurement_hash_reproducible": hash_payload(
            {
                key: value
                for key, value in runtime_measurement.items()
                if key != "measurement_hash"
            }
        )
        == runtime_measurement.get("measurement_hash"),
        "runtime_measurement_declares_required_capabilities": set(
            runtime_measurement.get("required_capabilities", [])
        )
        >= set(REQUIRED_RUNTIME_CAPABILITIES),
        "subject_bindings_complete": all(
            bool(subject_bindings.get(key))
            for key in (
                "live_emission_transparency_hash",
                "live_emission_witness_hash",
                "proof_response_hash",
                "gateway_report_hash",
                "evidence_locked_generation_hash",
                "subject_binding_root",
            )
        ),
        "trusted_attestors_declared": bool(trusted_rows),
        "runtime_quotes_present": bool(runtime_quotes),
        "minimum_quote_count_met": len(accepted_quote_rows) >= minimum_quote_count,
        "all_quote_hashes_reproducible": bool(quote_rows)
        and all(row["quote_hash_reproducible"] for row in quote_rows),
        "accepted_quotes_bind_runtime_measurement": bool(accepted_quote_rows)
        and all(row["runtime_measurement_matches"] for row in accepted_quote_rows),
        "accepted_quotes_bind_subjects": bool(accepted_quote_rows)
        and all(row["subject_bindings_match"] for row in accepted_quote_rows),
        "accepted_quotes_have_valid_signatures": bool(accepted_quote_rows)
        and all(row["signature_valid"] for row in accepted_quote_rows),
        "accepted_quotes_are_fresh": bool(accepted_quote_rows)
        and all(row["freshness_window_valid"] for row in accepted_quote_rows),
        "accepted_quotes_have_required_capabilities": bool(accepted_quote_rows)
        and all(row["required_capabilities_present"] for row in accepted_quote_rows),
        "public_report_has_no_private_field_names": not private_fields,
    }
    ready = all(checks.values())
    report = {
        "report_version": ATTESTED_RUNTIME_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-attested-attribution-runtime-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "minimum_quote_count": minimum_quote_count,
            "accepted_platform_types": sorted(ACCEPTED_PLATFORM_TYPES),
            "required_capabilities": list(REQUIRED_RUNTIME_CAPABILITIES),
            "production_note": (
                "The reference implementation uses HMAC conformance quotes; "
                "production deployments replace them with hardware TEE, ZKML, or "
                "hybrid attestation evidence."
            ),
        },
        "artifact_bindings": {
            "live_emission_transparency_hash": _declared_hash(
                live_emission_transparency
            ),
            "proof_response_hash": _declared_hash(proof_carrying_response),
            "gateway_report_hash": _declared_hash(serving_gateway_report),
            "evidence_locked_generation_hash": _declared_hash(
                evidence_locked_generation
            ),
        },
        "runtime_measurement": runtime_measurement,
        "subject_bindings": subject_bindings,
        "trusted_attestor_rows": trusted_rows,
        "runtime_quote_rows": quote_rows,
        "checks": checks,
        "commitments": {
            "runtime_measurement_hash": runtime_measurement.get(
                "measurement_hash", ""
            ),
            "subject_binding_root": subject_bindings.get("subject_binding_root", ""),
            "trusted_attestor_root": merkle_root(
                [row["attestor_row_hash"] for row in trusted_rows]
            ),
            "runtime_quote_root": merkle_root(
                [row["quote_row_hash"] for row in quote_rows]
            ),
            "accepted_quote_root": merkle_root(
                [row["quote_row_hash"] for row in accepted_quote_rows]
            ),
        },
        "schemas": {
            "attested_runtime": ATTESTED_RUNTIME_SCHEMA,
            "live_emission_transparency": "docs/schemas/live_emission_transparency.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "runtime_attested": ready,
            "quote_count": len(runtime_quotes),
            "accepted_quote_count": len(accepted_quote_rows),
            "minimum_quote_count": minimum_quote_count,
            "trusted_attestor_count": len(trusted_rows),
            "runtime_measurement_hash": runtime_measurement.get(
                "measurement_hash", ""
            ),
            "subject_binding_root": subject_bindings.get("subject_binding_root", ""),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "stream_chunk_text_disclosed": False,
            "attestor_secret_disclosed": False,
            "stores_measurements_subject_hashes_quotes_and_roots_not_text": True,
        },
    }
    report["attested_runtime_hash"] = hash_payload(_hashable_report(report))
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


def validate_attested_runtime_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "runtime_measurement",
        "subject_bindings",
        "trusted_attestor_rows",
        "runtime_quote_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "attested_runtime_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing attested runtime field: {key}")
    if errors:
        return errors
    if report.get("report_version") != ATTESTED_RUNTIME_VERSION:
        errors.append("attested runtime version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("attested runtime target certification level is unsupported")
    if "attested_runtime" not in report.get("schemas", {}):
        errors.append("missing attested runtime schema")
    return errors


def verify_attested_runtime_report(
    report: dict[str, Any],
    *,
    live_emission_transparency: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    runtime_measurement: dict[str, Any],
    runtime_quotes: list[dict[str, Any]],
    trusted_attestors: list[tuple[str, str, str] | tuple[str, str, str, str]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L86 runtime attestation report against quotes and artifacts."""

    errors = validate_attested_runtime_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("attested_runtime_hash"):
        errors.append("attested runtime hash is not reproducible")
    expected = make_attested_runtime_report(
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
        runtime_measurement=runtime_measurement,
        runtime_quotes=runtime_quotes,
        trusted_attestors=trusted_attestors,
        minimum_quote_count=int(report.get("policy", {}).get("minimum_quote_count", 1)),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "runtime_measurement",
        "subject_bindings",
        "trusted_attestor_rows",
        "runtime_quote_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"attested runtime {key} does not match inputs")
    if expected.get("attested_runtime_hash") != report.get("attested_runtime_hash"):
        errors.append("attested runtime hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("attested runtime status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"attested runtime check failed: {check}")
    report_json = canonical_json(report)
    for private_key in ('"chunk_text":', '"prompt":', '"raw_model_output":', '"attestor_secret":'):
        if private_key in report_json:
            errors.append(f"attested runtime discloses private field {private_key}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("attested runtime report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("attested runtime report signature is invalid")
    return errors
