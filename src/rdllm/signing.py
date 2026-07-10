"""Public-key signatures for RDLLM proof artifacts."""

from __future__ import annotations

import base64
import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


ED25519_ALGORITHM = "Ed25519"


def _as_bytes(value: str | bytes) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def _encode_signature(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_signature(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def load_private_key(value: str | bytes) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(_as_bytes(value), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("signing key must be an Ed25519 private key")
    return key


def load_public_key(value: str | bytes) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(_as_bytes(value))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("verification key must be an Ed25519 public key")
    return key


def generate_ed25519_keypair() -> tuple[str, str]:
    """Generate a PEM key pair for an operator-managed key store."""

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private_pem, public_pem


def public_key_fingerprint(public_key_pem_value: str | bytes) -> str:
    """Return a stable SHA-256 fingerprint for an Ed25519 public key."""

    public_key = load_public_key(public_key_pem_value)
    encoded = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _write_key(path: Path, value: str, *, mode: int, force: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
    descriptor = os.open(path, flags, mode)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            descriptor = -1
            handle.write(value)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an operator-managed Ed25519 key pair."
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default=Path("rdllm-ed25519-private.pem"),
        help="private key output (created with mode 0600)",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=Path("rdllm-ed25519-public.pem"),
        help="public key output (created with mode 0644)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace existing key files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    private_path = args.private_key.expanduser().resolve()
    public_path = args.public_key.expanduser().resolve()
    if private_path == public_path:
        print("private and public key paths must differ", file=sys.stderr)
        return 2
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_pem, public_pem = generate_ed25519_keypair()
    try:
        _write_key(private_path, private_pem, mode=0o600, force=args.force)
        try:
            _write_key(public_path, public_pem, mode=0o644, force=args.force)
        except Exception:
            private_path.unlink(missing_ok=True)
            raise
    except FileExistsError as exc:
        print(f"refusing to replace existing key: {exc.filename}", file=sys.stderr)
        return 2
    print("rdllm_keygen status: passed")
    print(f"private_key: {private_path}")
    print(f"public_key: {public_path}")
    print(f"public_key_fingerprint: {public_key_fingerprint(public_pem)}")
    print("Store the private key in a secrets manager; publish only the public key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def public_key_pem(private_key_pem: str | bytes) -> str:
    private_key = load_private_key(private_key_pem)
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def sign_bytes(
    payload: bytes,
    *,
    private_key_pem: str | bytes,
    key_id: str,
    issuer: str,
) -> dict[str, Any]:
    if not key_id.strip():
        raise ValueError("key_id is required for a public signature")
    return {
        "algorithm": ED25519_ALGORITHM,
        "key_id": key_id,
        "issuer": issuer,
        "value": _encode_signature(load_private_key(private_key_pem).sign(payload)),
        "security_level": "publicly_verifiable",
    }


def verify_bytes(
    payload: bytes,
    signature: dict[str, Any],
    *,
    public_key_pem_value: str | bytes,
    expected_key_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if signature.get("algorithm") != ED25519_ALGORITHM:
        return ["signature algorithm is not Ed25519"]
    key_id = str(signature.get("key_id", ""))
    if not key_id:
        errors.append("signature key_id is missing")
    if expected_key_id is not None and key_id != expected_key_id:
        errors.append("signature key_id does not match the trusted key")
    value = signature.get("value")
    if not isinstance(value, str) or not value:
        errors.append("signature value is missing")
        return errors
    try:
        decoded = _decode_signature(value)
    except (ValueError, TypeError):
        errors.append("signature value is not valid base64url")
        return errors
    try:
        load_public_key(public_key_pem_value).verify(decoded, payload)
    except InvalidSignature:
        errors.append("signature is invalid")
    except (TypeError, ValueError) as exc:
        errors.append(f"verification key is invalid: {exc}")
    return errors
