"""Externally signed deployment evidence for production-readiness decisions."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse

from rdllm.receipts import canonical_json, hash_payload, now_iso
from rdllm.signing import sign_bytes, verify_bytes


ATTESTATION_SCHEMA = "rdllm-deployment-attestation/v1"
TRUST_STORE_SCHEMA = "rdllm-deployment-trust-store/v1"
REQUIRED_PRODUCTION_ATTESTATIONS = {
    "audit_log_integrity",
    "backup_restore",
    "public_surface_health",
    "receipt_public_key",
    "runtime_controls",
    "security_assessment",
}
PAYMENT_PROCESSOR_ATTESTATION = "payment_processor"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def make_deployment_attestation(
    *,
    attestation_type: str,
    issuer: str,
    subject: str,
    deployment_id: str,
    evidence_uri: str,
    evidence_sha256: str,
    expires_at: str,
    private_key_pem: str | bytes,
    key_id: str,
    issued_at: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": ATTESTATION_SCHEMA,
        "attestation_type": attestation_type,
        "issuer": issuer,
        "subject": subject,
        "deployment_id": deployment_id,
        "evidence_uri": evidence_uri,
        "evidence_sha256": evidence_sha256,
        "issued_at": issued_at or now_iso(),
        "expires_at": expires_at,
    }
    return {
        "payload": payload,
        "attestation_hash": hash_payload(payload),
        "signature": sign_bytes(
            canonical_json(payload).encode("utf-8"),
            private_key_pem=private_key_pem,
            key_id=key_id,
            issuer=issuer,
        ),
    }


def verify_deployment_attestations(
    attestations: Any,
    *,
    deployment_id: str,
    operator_name: str,
    trust_store: dict[str, Any] | None,
    direct_payout_requested: bool,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    now = checked_at or datetime.now(timezone.utc)
    trust_rows = (
        trust_store.get("keys", [])
        if isinstance(trust_store, dict)
        and trust_store.get("schema") == TRUST_STORE_SCHEMA
        else []
    )
    trusted_keys = {
        str(row.get("key_id", "")): row
        for row in trust_rows
        if isinstance(row, dict) and row.get("key_id")
    }
    rows: list[dict[str, Any]] = []
    verified_types: set[str] = set()
    for index, attestation in enumerate(
        attestations if isinstance(attestations, list) else []
    ):
        errors: list[str] = []
        if not isinstance(attestation, dict):
            rows.append(
                {
                    "attestation_index": index,
                    "attestation_type": "",
                    "status": "failed",
                    "errors": ["attestation must be an object"],
                }
            )
            continue
        payload = attestation.get("payload", {})
        signature = attestation.get("signature", {})
        attestation_type = str(payload.get("attestation_type", ""))
        key_id = str(signature.get("key_id", ""))
        trusted = trusted_keys.get(key_id)
        if payload.get("schema") != ATTESTATION_SCHEMA:
            errors.append("attestation schema is unsupported")
        if payload.get("deployment_id") != deployment_id:
            errors.append("attestation deployment_id does not match the profile")
        if payload.get("subject") != operator_name:
            errors.append("attestation subject does not match the operator")
        if not SHA256_PATTERN.fullmatch(str(payload.get("evidence_sha256", ""))):
            errors.append("evidence_sha256 must be 64 lowercase hex characters")
        evidence_uri = str(payload.get("evidence_uri", ""))
        if urlparse(evidence_uri).scheme != "https":
            errors.append("evidence_uri must use HTTPS")
        issued_at = _parse_time(payload.get("issued_at"))
        expires_at = _parse_time(payload.get("expires_at"))
        if issued_at is None or issued_at > now:
            errors.append("issued_at is invalid or in the future")
        if expires_at is None or expires_at <= now:
            errors.append("attestation is expired or expires_at is invalid")
        if attestation.get("attestation_hash") != hash_payload(payload):
            errors.append("attestation hash is not reproducible")
        if trusted is None:
            errors.append("attestation key is not present in the external trust store")
        else:
            if trusted.get("issuer") != payload.get("issuer"):
                errors.append("attestation issuer does not match the trusted key")
            allowed_types = trusted.get("allowed_attestation_types", [])
            if attestation_type not in allowed_types:
                errors.append("trusted key is not allowed for this attestation type")
            public_key = trusted.get("public_key_pem", "")
            if not isinstance(public_key, str) or not public_key:
                errors.append("trusted key has no public_key_pem")
            else:
                errors.extend(
                    verify_bytes(
                        canonical_json(payload).encode("utf-8"),
                        signature,
                        public_key_pem_value=public_key,
                        expected_key_id=key_id,
                    )
                )
        status = "verified" if not errors else "failed"
        if status == "verified":
            verified_types.add(attestation_type)
        rows.append(
            {
                "attestation_index": index,
                "attestation_type": attestation_type,
                "issuer": str(payload.get("issuer", "")),
                "key_id": key_id,
                "evidence_uri": evidence_uri,
                "evidence_sha256": str(payload.get("evidence_sha256", "")),
                "expires_at": str(payload.get("expires_at", "")),
                "status": status,
                "errors": errors,
            }
        )
    required = set(REQUIRED_PRODUCTION_ATTESTATIONS)
    if direct_payout_requested:
        required.add(PAYMENT_PROCESSOR_ATTESTATION)
    missing = sorted(required - verified_types)
    return {
        "schema": "rdllm-deployment-attestation-verification/v1",
        "status": "verified" if not missing else "unverified",
        "trust_store_loaded": bool(trusted_keys),
        "required_attestation_types": sorted(required),
        "verified_attestation_types": sorted(verified_types),
        "missing_attestation_types": missing,
        "verified_attestation_count": len(verified_types & required),
        "required_attestation_count": len(required),
        "rows": rows,
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _create_command(args: argparse.Namespace) -> int:
    profile = _load_json(args.profile)
    deployment = profile.get("deployment", {})
    evidence_sha256 = hashlib.sha256(args.evidence.read_bytes()).hexdigest()
    attestation = make_deployment_attestation(
        attestation_type=args.attestation_type,
        issuer=args.issuer,
        subject=str(deployment.get("operator_name", "")),
        deployment_id=str(deployment.get("deployment_id", "")),
        evidence_uri=args.evidence_uri,
        evidence_sha256=evidence_sha256,
        expires_at=args.expires_at,
        private_key_pem=args.private_key.read_bytes(),
        key_id=args.key_id,
    )
    _write_json(args.output, attestation)
    print("deployment_attestation_create status: passed")
    print(f"attestation: {args.output.resolve()}")
    print(f"evidence_sha256: {evidence_sha256}")
    return 0


def _attach_command(args: argparse.Namespace) -> int:
    profile = _load_json(args.profile)
    attestation = _load_json(args.attestation)
    rows = profile.setdefault("external_attestations", [])
    if not isinstance(rows, list):
        print("profile.external_attestations must be an array", file=sys.stderr)
        return 2
    attestation_hash = attestation.get("attestation_hash")
    rows[:] = [
        row
        for row in rows
        if not isinstance(row, dict) or row.get("attestation_hash") != attestation_hash
    ]
    rows.append(attestation)
    _write_json(args.output, profile)
    print("deployment_attestation_attach status: passed")
    print(f"profile: {args.output.resolve()}")
    print(f"attestation_count: {len(rows)}")
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    profile = _load_json(args.profile)
    deployment = profile.get("deployment", {})
    settlement = profile.get("settlement_controls", {})
    verification = verify_deployment_attestations(
        profile.get("external_attestations", []),
        deployment_id=str(deployment.get("deployment_id", "")),
        operator_name=str(deployment.get("operator_name", "")),
        trust_store=_load_json(args.trust_store),
        direct_payout_requested=settlement.get("direct_payout_enabled") is True,
    )
    if args.json:
        print(json.dumps(verification, indent=2))
    else:
        print(f"deployment_attestation_verify status: {verification['status']}")
        print(
            "verified: "
            f"{verification['verified_attestation_count']}/"
            f"{verification['required_attestation_count']}"
        )
        if verification["missing_attestation_types"]:
            print("missing: " + ", ".join(verification["missing_attestation_types"]))
    return 0 if verification["status"] == "verified" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Sign one external evidence item.")
    create.add_argument("--profile", type=Path, required=True)
    create.add_argument(
        "--attestation-type",
        choices=sorted(REQUIRED_PRODUCTION_ATTESTATIONS | {PAYMENT_PROCESSOR_ATTESTATION}),
        required=True,
    )
    create.add_argument("--issuer", required=True)
    create.add_argument("--key-id", required=True)
    create.add_argument("--private-key", type=Path, required=True)
    create.add_argument("--evidence", type=Path, required=True)
    create.add_argument("--evidence-uri", required=True)
    create.add_argument("--expires-at", required=True)
    create.add_argument("--output", type=Path, required=True)
    create.set_defaults(func=_create_command)

    attach = subparsers.add_parser(
        "attach", help="Attach a signed attestation to a copied profile."
    )
    attach.add_argument("--profile", type=Path, required=True)
    attach.add_argument("--attestation", type=Path, required=True)
    attach.add_argument("--output", type=Path, required=True)
    attach.set_defaults(func=_attach_command)

    verify = subparsers.add_parser(
        "verify", help="Verify all profile attestations against an external trust store."
    )
    verify.add_argument("--profile", type=Path, required=True)
    verify.add_argument("--trust-store", type=Path, required=True)
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=_verify_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"deployment attestation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
