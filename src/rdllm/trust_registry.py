"""Public trust-root registry for RDLLM signers and witnesses."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

TRUST_REGISTRY_VERSION = "rdllm-trust-registry/v1"
TRUST_REGISTRY_SCHEMA = "docs/schemas/trust_registry.schema.json"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "attestation_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "gate_hash",
    "capsule_hash",
    "handshake_hash",
    "vector_pack_hash",
    "exchange_hash",
    "graph_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "contract_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "secret",
    "signing_secret",
    "private_key",
    "private_key_material",
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}


def _hashable_registry(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"trust_registry_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


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


def _principal_key_hash(principal_id: str, role: str, secret: str) -> str:
    if role == "witness":
        return stable_hash(f"rdllm-witness-key:{principal_id}:{secret}")
    return stable_hash(f"rdllm-signing-key:{principal_id}:{role}:{secret}")


def _verifier_key_hash(principal_id: str, secret: str) -> str:
    return stable_hash(f"rdllm-verifier-key:{principal_id}:{secret}")


def _key_id(principal_id: str, role: str, key_hash: str) -> str:
    return stable_hash(f"rdllm-key-id:{principal_id}:{role}:{key_hash}")[:24]


def _principal_entry(
    principal_id: str,
    role: str,
    secret: str,
    *,
    status: str = "active",
) -> dict[str, Any]:
    key_hash = _principal_key_hash(principal_id, role, secret)
    entry = {
        "principal_id": principal_id,
        "role": role,
        "key_id": _key_id(principal_id, role, key_hash),
        "key_type": (
            "HMAC-SHA256-reference-witness"
            if role == "witness"
            else "HMAC-SHA256-reference-signer"
        ),
        "key_hash": key_hash,
        "status": status,
        "allowed_signature_algorithms": ["HMAC-SHA256"],
        "public_key_material_disclosed": False,
    }
    if role in {"independent_attribution_verifier", "verifier"}:
        entry["verifier_key_hash"] = _verifier_key_hash(principal_id, secret)
        entry["alternate_key_hashes"] = [entry["verifier_key_hash"]]
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _active_secret_index(
    principals: list[tuple[str, str, str]],
    revoked: list[tuple[str, str, str]],
) -> dict[str, list[tuple[str, str, str, str]]]:
    revoked_hashes = {
        _principal_key_hash(principal_id, role, secret)
        for principal_id, role, secret in revoked
    }
    index: dict[str, list[tuple[str, str, str, str]]] = {}
    for principal_id, role, secret in principals:
        key_hash = _principal_key_hash(principal_id, role, secret)
        if key_hash in revoked_hashes:
            continue
        index.setdefault(principal_id, []).append((role, secret, key_hash, _key_id(principal_id, role, key_hash)))
    return index


def _artifact_binding(
    *,
    name: str,
    artifact_type: str,
    artifact: dict[str, Any],
    active_secrets: dict[str, list[tuple[str, str, str, str]]],
    revoked_hashes: set[str],
) -> dict[str, Any]:
    signature = artifact.get("signature", {})
    issuer = str(signature.get("issuer") or artifact.get("issuer") or "")
    algorithm = str(signature.get("algorithm", ""))
    signature_value = str(signature.get("value", ""))
    matched: tuple[str, str, str] | None = None
    if issuer and algorithm == "HMAC-SHA256" and signature_value:
        for role, secret, key_hash, key_id in active_secrets.get(issuer, []):
            if sign_payload(_hashable_artifact(artifact), secret) == signature_value:
                matched = (role, key_hash, key_id)
                break
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "issuer": issuer,
        "signature_algorithm": algorithm,
        "signature_present": bool(signature_value),
        "declared_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(artifact),
        "signature_verified": matched is not None,
        "signer_role": matched[0] if matched else "",
        "signing_key_hash": matched[1] if matched else "",
        "signing_key_id": matched[2] if matched else "",
        "signer_registered": bool(matched),
        "revoked_key_used": bool(matched and matched[1] in revoked_hashes),
    }
    row["binding_hash"] = hash_payload(row)
    return row


def _attestation_payload(
    subject: dict[str, Any],
    *,
    witness_id: str,
    witness_secret: str,
    observed_at: str,
) -> dict[str, Any]:
    return {
        "witness_id": witness_id,
        "witness_key_hash": _principal_key_hash(witness_id, "witness", witness_secret),
        "observed_at": observed_at,
        "subject_hash": subject["subject_hash"],
        "monitor_hash": subject["monitor_hash"],
        "checkpoint_index": subject["checkpoint_index"],
        "checkpoint_hash": subject["checkpoint_hash"],
        "artifact_root": subject["artifact_root"],
    }


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key != "attestation_hash"
    }


def _witness_bindings(
    publication_witnesses: list[dict[str, Any]],
    *,
    principal_secrets: dict[str, list[tuple[str, str, str, str]]],
    revoked_hashes: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for witness_report in publication_witnesses:
        subjects = {
            str(subject.get("subject_hash", "")): subject
            for subject in witness_report.get("checkpoint_subjects", [])
            if isinstance(subject, dict)
        }
        for attestation in witness_report.get("witness_attestations", []):
            witness_id = str(attestation.get("witness_id", ""))
            subject = subjects.get(str(attestation.get("subject_hash", "")))
            matched: tuple[str, str, str] | None = None
            key_hash_matches = False
            signature_valid = False
            attestation_hash_valid = (
                hash_payload(_hashable_attestation(attestation))
                == attestation.get("attestation_hash")
            )
            for role, secret, key_hash, key_id in principal_secrets.get(witness_id, []):
                if role != "witness" or subject is None:
                    continue
                key_hash_matches = key_hash == attestation.get("witness_key_hash")
                payload = _attestation_payload(
                    subject,
                    witness_id=witness_id,
                    witness_secret=secret,
                    observed_at=str(attestation.get("observed_at", "")),
                )
                signature_valid = sign_payload(payload, secret) == attestation.get(
                    "signature"
                )
                if key_hash_matches and signature_valid:
                    matched = (role, key_hash, key_id)
                    break
            row = {
                "witness_id": witness_id,
                "subject_hash": attestation.get("subject_hash", ""),
                "monitor_hash": attestation.get("monitor_hash", ""),
                "checkpoint_hash": attestation.get("checkpoint_hash", ""),
                "witness_registered": matched is not None,
                "witness_key_hash": matched[1] if matched else str(attestation.get("witness_key_hash", "")),
                "witness_key_id": matched[2] if matched else "",
                "witness_key_hash_matches": key_hash_matches,
                "witness_signature_valid": signature_valid,
                "attestation_hash_valid": attestation_hash_valid,
                "revoked_key_used": bool(matched and matched[1] in revoked_hashes),
            }
            row["binding_hash"] = hash_payload(row)
            rows.append(row)
    return rows


def _rotation_rows(
    rotations: list[tuple[str, str, str, str]],
    principals: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    active_hashes = {
        _principal_key_hash(principal_id, role, secret)
        for principal_id, role, secret in principals
    }
    rows: list[dict[str, Any]] = []
    for principal_id, role, previous_secret, new_secret in rotations:
        previous_key_hash = _principal_key_hash(principal_id, role, previous_secret)
        new_key_hash = _principal_key_hash(principal_id, role, new_secret)
        row = {
            "principal_id": principal_id,
            "role": role,
            "previous_key_hash": previous_key_hash,
            "new_key_hash": new_key_hash,
            "new_key_active": new_key_hash in active_hashes,
            "rotation_changes_key": previous_key_hash != new_key_hash,
        }
        row["rotation_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_trust_registry_report(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    principals: list[tuple[str, str, str]],
    publication_witnesses: list[dict[str, Any]] | None = None,
    rotations: list[tuple[str, str, str, str]] | None = None,
    revoked_keys: list[tuple[str, str, str]] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public registry for RDLLM signing and witness trust roots."""

    publication_witnesses = publication_witnesses or []
    rotations = rotations or []
    revoked_keys = revoked_keys or []
    revoked_hashes = {
        _principal_key_hash(principal_id, role, secret)
        for principal_id, role, secret in revoked_keys
    }
    principal_entries = [
        _principal_entry(principal_id, role, secret)
        for principal_id, role, secret in sorted(principals)
    ]
    revoked_entries = [
        _principal_entry(principal_id, role, secret, status="revoked")
        for principal_id, role, secret in sorted(revoked_keys)
    ]
    active_secrets = _active_secret_index(principals, revoked_keys)
    artifact_bindings = [
        _artifact_binding(
            name=name,
            artifact_type=artifact_type,
            artifact=payload,
            active_secrets=active_secrets,
            revoked_hashes=revoked_hashes,
        )
        for name, artifact_type, payload in sorted(artifacts, key=lambda item: item[0])
    ]
    witness_bindings = _witness_bindings(
        publication_witnesses,
        principal_secrets=active_secrets,
        revoked_hashes=revoked_hashes,
    )
    rotation_rows = _rotation_rows(rotations, principals)
    private_paths: list[str] = []
    checks = {
        "principals_present": bool(principal_entries),
        "key_ids_unique": len({entry["key_id"] for entry in principal_entries})
        == len(principal_entries),
        "artifact_signers_registered": all(
            binding["signer_registered"] for binding in artifact_bindings
        ),
        "artifact_signatures_verified": all(
            binding["signature_verified"] for binding in artifact_bindings
        ),
        "witness_keys_registered": all(
            binding["witness_registered"] for binding in witness_bindings
        ),
        "witness_signatures_verified": all(
            binding["witness_signature_valid"]
            and binding["attestation_hash_valid"]
            and binding["witness_key_hash_matches"]
            for binding in witness_bindings
        ),
        "revoked_keys_not_used": not any(
            binding["revoked_key_used"]
            for binding in [*artifact_bindings, *witness_bindings]
        ),
        "rotations_link_active_new_keys": all(
            row["new_key_active"] and row["rotation_changes_key"]
            for row in rotation_rows
        ),
        "private_key_material_absent": True,
    }
    report = {
        "registry_version": TRUST_REGISTRY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "trust_profile": {
            "profile": "rdllm-public-trust-registry/v1",
            "key_format": "rdllm-reference-hmac-key-hash",
            "production_mapping": [
                "RFC7517_JWKS",
                "W3C_DID_verificationMethod",
                "Sigstore_TUF_trust_root",
            ],
            "raw_key_material_disallowed": True,
            "revocation_checked": True,
            "rotation_checked": True,
            "witness_keys_bound": True,
        },
        "principals": principal_entries,
        "revoked_keys": revoked_entries,
        "key_rotations": rotation_rows,
        "artifact_bindings": artifact_bindings,
        "witness_bindings": witness_bindings,
        "checks": checks,
        "commitments": {
            "principal_root": hash_payload(principal_entries),
            "revoked_key_root": hash_payload(revoked_entries),
            "rotation_root": hash_payload(rotation_rows),
            "artifact_binding_root": hash_payload(artifact_bindings),
            "witness_binding_root": hash_payload(witness_bindings),
            "schema": TRUST_REGISTRY_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L51",
            "principal_count": len(principal_entries),
            "revoked_key_count": len(revoked_entries),
            "rotation_count": len(rotation_rows),
            "artifact_binding_count": len(artifact_bindings),
            "witness_binding_count": len(witness_bindings),
            "failed_check_count": sum(1 for value in checks.values() if value is not True),
            "private_input_field_count": len(private_paths),
        },
        "privacy": {
            "raw_key_material_disclosed": False,
            "signing_secrets_disclosed": False,
            "private_prompt_or_source_text_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "registry_uses_key_hashes_and_artifact_hashes": True,
        },
    }
    private_paths = _contains_private_fields(report)
    report["summary"]["private_input_field_count"] = len(private_paths)
    report["checks"]["private_key_material_absent"] = not private_paths
    report["summary"]["status"] = "ready" if all(report["checks"].values()) else "failed"
    report["trust_registry_hash"] = hash_payload(_hashable_registry(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_registry(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_trust_registry_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "registry_version",
        "issuer",
        "created_at",
        "trust_profile",
        "principals",
        "revoked_keys",
        "key_rotations",
        "artifact_bindings",
        "witness_bindings",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "trust_registry_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing trust registry field: {key}")
    if errors:
        return errors
    if report.get("registry_version") != TRUST_REGISTRY_VERSION:
        errors.append("trust registry version is unsupported")
    for entry in report.get("principals", []):
        for key in ("principal_id", "role", "key_id", "key_hash", "status", "entry_hash"):
            if key not in entry:
                errors.append(f"missing trust principal field: {key}")
    for binding in report.get("artifact_bindings", []):
        for key in (
            "name",
            "artifact_type",
            "issuer",
            "declared_hash",
            "payload_hash",
            "signature_verified",
            "signer_registered",
            "binding_hash",
        ):
            if key not in binding:
                errors.append(f"missing trust artifact binding field: {key}")
    for key in (
        "principals_present",
        "key_ids_unique",
        "artifact_signers_registered",
        "artifact_signatures_verified",
        "witness_keys_registered",
        "witness_signatures_verified",
        "revoked_keys_not_used",
        "rotations_link_active_new_keys",
        "private_key_material_absent",
    ):
        if key not in report.get("checks", {}):
            errors.append(f"missing trust registry check: {key}")
    return errors


def verify_trust_registry_report(
    report: dict[str, Any],
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    principals: list[tuple[str, str, str]],
    publication_witnesses: list[dict[str, Any]] | None = None,
    rotations: list[tuple[str, str, str, str]] | None = None,
    revoked_keys: list[tuple[str, str, str]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a trust registry report against artifacts and disclosed verifier keys."""

    errors = validate_trust_registry_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_registry(report))
    if expected_hash != report.get("trust_registry_hash"):
        errors.append("trust registry hash is not reproducible")

    expected = make_trust_registry_report(
        artifacts,
        principals=principals,
        publication_witnesses=publication_witnesses,
        rotations=rotations,
        revoked_keys=revoked_keys,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "trust_profile",
        "principals",
        "revoked_keys",
        "key_rotations",
        "artifact_bindings",
        "witness_bindings",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"trust registry {key} does not match inputs")
    if expected.get("trust_registry_hash") != report.get("trust_registry_hash"):
        errors.append("trust registry hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("trust registry status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"trust registry check failed: {check}")
    if _contains_private_fields(report):
        errors.append("trust registry discloses private key or payload fields")
    registry_json = canonical_json(report)
    for token in ('"secret"', '"private_key"', '"signing_secret"'):
        if token in registry_json:
            errors.append("trust registry discloses private key material")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_registry(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("trust registry is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("trust registry signature is invalid")
    return errors
