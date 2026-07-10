"""Verifiable attribution receipts for AI usage events."""

from __future__ import annotations

import hmac
import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from rdllm.models import UsageEvent
from rdllm.signing import ED25519_ALGORITHM, sign_bytes, verify_bytes
from rdllm.text import stable_hash

PROTOCOL_VERSION = "rdllm-attribution-receipt/v1"
SELECTIVE_DISCLOSURE_VERSION = "rdllm-selective-disclosure/v1"
TRACE_EXCHANGE_VERSION = "rdllm-trace-exchange/v1"
OTEL_GENAI_SEMCONV = "https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/"
DEFAULT_ISSUER = "rdllm-local-demo"
DISCLOSURE_ROOT_PATH = "/privacy/disclosure_root"
DISCLOSURE_SALTS_PATH = "/privacy/disclosure_salts"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def hash_payload(data: Any) -> str:
    return stable_hash(canonical_json(data))


def _parent(left: str, right: str) -> str:
    return stable_hash(f"disclosure-node:{left}:{right}")


def _merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return stable_hash("disclosure-empty")
    level = leaves[:]
    while len(level) > 1:
        next_level: list[str] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_parent(left, right))
        level = next_level
    return level[0]


def _escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _leaf_hash(path: str, value: Any, salt: str = "") -> str:
    return stable_hash(f"disclosure-leaf:{path}\0{salt}\0{canonical_json(value)}")


def _walk_leaves(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if path in (DISCLOSURE_ROOT_PATH, DISCLOSURE_SALTS_PATH):
        return []
    if isinstance(value, dict):
        if not value:
            return [(path or "/", value)]
        leaves: list[tuple[str, Any]] = []
        for key in sorted(value):
            escaped_key = _escape_pointer_part(str(key))
            child_path = f"{path}/{escaped_key}" if path else f"/{escaped_key}"
            leaves.extend(_walk_leaves(value[key], child_path))
        return leaves
    if isinstance(value, list):
        if not value:
            return [(path or "/", value)]
        leaves = []
        for index, item in enumerate(value):
            child_path = f"{path}/{index}" if path else f"/{index}"
            leaves.extend(_walk_leaves(item, child_path))
        return leaves
    return [(path or "/", value)]


def payload_disclosure_leaves(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic path/value commitments for selective disclosure."""

    salts = payload.get("privacy", {}).get("disclosure_salts", {})
    return [
        {
            "path": path,
            "value": value,
            "salt": salts.get(path, ""),
            "leaf_hash": _leaf_hash(path, value, salts.get(path, "")),
        }
        for path, value in _walk_leaves(payload)
    ]


def disclosure_root_from_leaves(leaves: list[dict[str, Any]]) -> str:
    """Return the Merkle root over disclosure leaf hashes sorted by JSON path."""

    return _merkle_root(
        [
            leaf["leaf_hash"]
            for leaf in sorted(leaves, key=lambda item: item["path"])
        ]
    )


def payload_disclosure_root(payload: dict[str, Any]) -> str:
    """Return the root commitment for a full receipt payload."""

    return disclosure_root_from_leaves(payload_disclosure_leaves(payload))


def make_disclosure_salts(
    payload: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> dict[str, str]:
    """Create per-path blinding salts for SD-JWT-style private commitments."""

    event = payload.get("event", {})
    seed = stable_hash(
        "disclosure-salt-seed:"
        f"{payload.get('issuer', '')}:"
        f"{payload.get('issued_at', '')}:"
        f"{event.get('event_hash', '')}:"
        f"{signing_secret or 'unsigned'}"
    )
    return {
        path: stable_hash(f"disclosure-salt:{seed}:{path}")
        for path, _value in _walk_leaves(payload)
    }


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_json(payload).encode("utf-8"),
        sha256,
    ).hexdigest()


def make_attribution_receipt(
    event: UsageEvent,
    *,
    issuer: str = DEFAULT_ISSUER,
    model_id: str = "model:unspecified",
    model_version: str = "unknown",
    route_id: str = "route:default",
    issued_at: str | None = None,
    signing_secret: str | None = None,
    signing_private_key: str | bytes | None = None,
    signing_key_id: str = "",
) -> dict[str, Any]:
    """Build a verifiable receipt suitable for a model API response header/body."""

    if signing_secret and signing_private_key:
        raise ValueError("choose either a demo shared secret or an Ed25519 private key")

    source_accesses = [access.to_dict() for access in event.source_accesses]
    sources = [reference.to_dict() for reference in event.source_references]
    claims = [support.to_dict() for support in event.claim_support]
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "issuer": issuer,
        "issued_at": issued_at or now_iso(),
        "model": {
            "id": model_id,
            "version": model_version,
            "route_id": route_id,
        },
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "prompt_hash": stable_hash(event.prompt),
            "answer_hash": stable_hash(event.answer_text or event.output),
            "rendered_output_hash": stable_hash(event.output),
        },
        "grounding": {
            "report": event.grounding_report,
            "quality": event.grounding_quality,
            "attribution_gap": event.attribution_gap,
            "source_accesses": source_accesses,
            "sources": sources,
            "claims": claims,
        },
        "telemetry": {
            "trace_exchange_version": TRACE_EXCHANGE_VERSION,
            "otel_semconv": OTEL_GENAI_SEMCONV,
            "source_access_trace_hash": hash_payload(source_accesses),
            "source_reference_trace_hash": hash_payload(sources),
            "claim_support_trace_hash": hash_payload(claims),
        },
        "rights": {
            "policy_status": event.grounding_report.get("policy_status", "allowed"),
            "policy_denials": event.grounding_report.get("policy_denials", 0),
            "decisions": event.policy_decisions,
        },
        "registry": {
            "registry_status": event.grounding_report.get("registry_status", "clear"),
            "registry_conflicts": event.grounding_report.get("registry_conflicts", 0),
            "registry_report_hash": event.grounding_report.get(
                "registry_report_hash", ""
            ),
            "decisions": event.registry_decisions,
        },
        "economics": {
            "gross_revenue": str(event.gross_revenue),
            "creator_pool_rate": str(event.creator_pool_rate),
            "creator_pool": str(event.creator_pool),
            "shares": [share.to_dict() for share in event.royalty_shares],
        },
        "privacy": {
            "prompt_disclosed": False,
            "answer_disclosed": False,
            "source_quotes_disclosed": True,
            "disclosure_version": SELECTIVE_DISCLOSURE_VERSION,
            "disclosure_root": "",
            "disclosure_salts": {},
            "selective_disclosure": "hash commitments expose prompt/output integrity without disclosing private prompts",
        },
    }
    payload["privacy"]["disclosure_salts"] = make_disclosure_salts(
        payload,
        signing_secret=signing_secret,
    )
    payload["privacy"]["disclosure_root"] = payload_disclosure_root(payload)
    receipt_hash = hash_payload(payload)
    if signing_private_key:
        signature = sign_bytes(
            canonical_json(payload).encode("utf-8"),
            private_key_pem=signing_private_key,
            key_id=signing_key_id,
            issuer=issuer,
        )
    elif signing_secret:
        signature = {
            "algorithm": "HMAC-SHA256",
            "key_id": "",
            "issuer": issuer,
            "value": sign_payload(payload, signing_secret),
            "security_level": "demo_shared_secret",
        }
    else:
        signature = {
            "algorithm": "UNSIGNED",
            "key_id": "",
            "issuer": issuer,
            "value": "",
            "security_level": "none",
        }
    return {
        "receipt_hash": receipt_hash,
        "payload": payload,
        "signature": signature,
    }


def public_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Return a public, privacy-reduced receipt view."""

    payload = receipt["payload"]
    return {
        "receipt_hash": receipt["receipt_hash"],
        "protocol_version": payload["protocol_version"],
        "issuer": payload["issuer"],
        "issued_at": payload["issued_at"],
        "model": payload["model"],
        "event": payload["event"],
        "telemetry": payload.get("telemetry", {}),
        "grounding_report": payload["grounding"]["report"],
        "grounding_quality": payload["grounding"].get("quality", {}),
        "attribution_gap": {
            "verdict": payload["grounding"].get("attribution_gap", {}).get("verdict", ""),
            "summary": payload["grounding"].get("attribution_gap", {}).get("summary", {}),
            "report_hash": payload["grounding"].get("attribution_gap", {}).get("report_hash", ""),
        },
        "rights": {
            "policy_status": payload["rights"]["policy_status"],
            "policy_denials": payload["rights"]["policy_denials"],
        },
        "registry": {
            "registry_status": payload["registry"].get("registry_status", "clear"),
            "registry_conflicts": payload["registry"].get("registry_conflicts", 0),
            "registry_report_hash": payload["registry"].get("registry_report_hash", ""),
        },
        "sources": [
            {
                "label": source["label"],
                "creator_id": source["creator_id"],
                "work_id": source["work_id"],
                "chunk_id": source["chunk_id"],
                "source_uri": source["source_uri"],
                "content_hash": source["content_hash"],
                "contribution_weight": source["contribution_weight"],
            }
            for source in payload["grounding"]["sources"]
        ],
        "claim_support": [
            {
                "claim": claim["claim"],
                "source_label": claim["source_label"],
                "support_score": claim["support_score"],
                "supported": claim["supported"],
                "work_id": claim["work_id"],
                "chunk_id": claim["chunk_id"],
                "evidence_span_hash": claim["evidence_span_hash"],
                "evidence_start_char": claim["evidence_start_char"],
                "evidence_end_char": claim["evidence_end_char"],
            }
            for claim in payload["grounding"]["claims"]
        ],
        "privacy": {
            "prompt_disclosed": payload["privacy"].get("prompt_disclosed", False),
            "answer_disclosed": payload["privacy"].get("answer_disclosed", False),
            "source_quotes_disclosed": payload["privacy"].get(
                "source_quotes_disclosed", False
            ),
            "selective_disclosure": payload["privacy"].get(
                "selective_disclosure", ""
            ),
            "disclosure_version": payload["privacy"].get(
                "disclosure_version", ""
            ),
            "disclosure_root": payload["privacy"].get("disclosure_root", ""),
        },
        "signature": receipt["signature"],
    }


def verify_receipt(
    receipt: dict[str, Any],
    *,
    signing_secret: str | None = None,
    verification_public_key: str | bytes | None = None,
    expected_key_id: str | None = None,
    require_public_signature: bool = False,
) -> list[str]:
    errors = validate_receipt_shape(receipt)
    if errors:
        return errors
    expected_hash = hash_payload(receipt.get("payload", {}))
    if expected_hash != receipt.get("receipt_hash"):
        errors.append("receipt hash is not reproducible")

    privacy = receipt.get("payload", {}).get("privacy", {})
    disclosure_root = privacy.get("disclosure_root", "")
    if privacy.get("disclosure_version") == SELECTIVE_DISCLOSURE_VERSION:
        expected_disclosure_root = payload_disclosure_root(receipt.get("payload", {}))
        if disclosure_root != expected_disclosure_root:
            errors.append("receipt disclosure root is not reproducible")

    payload = receipt.get("payload", {})
    telemetry = payload.get("telemetry", {})
    grounding = payload.get("grounding", {})
    if telemetry.get("trace_exchange_version") == TRACE_EXCHANGE_VERSION:
        expected_source_access_hash = hash_payload(grounding.get("source_accesses", []))
        expected_source_reference_hash = hash_payload(grounding.get("sources", []))
        expected_claim_hash = hash_payload(grounding.get("claims", []))
        if telemetry.get("source_access_trace_hash") != expected_source_access_hash:
            errors.append("receipt source-access trace hash is not reproducible")
        if telemetry.get("source_reference_trace_hash") != expected_source_reference_hash:
            errors.append("receipt source-reference trace hash is not reproducible")
        if telemetry.get("claim_support_trace_hash") != expected_claim_hash:
            errors.append("receipt claim-support trace hash is not reproducible")

    signature = receipt.get("signature", {})
    algorithm = signature.get("algorithm")
    if verification_public_key is not None:
        errors.extend(
            verify_bytes(
                canonical_json(receipt.get("payload", {})).encode("utf-8"),
                signature,
                public_key_pem_value=verification_public_key,
                expected_key_id=expected_key_id,
            )
        )
    elif signing_secret:
        expected_signature = sign_payload(receipt.get("payload", {}), signing_secret)
        if algorithm != "HMAC-SHA256":
            errors.append("receipt is not HMAC signed")
        elif expected_signature != signature.get("value"):
            errors.append("receipt signature is invalid")
    if require_public_signature and algorithm != ED25519_ALGORITHM:
        errors.append("receipt requires a publicly verifiable Ed25519 signature")
    elif require_public_signature and verification_public_key is None:
        errors.append("receipt public verification key is required")
    return errors


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("receipt_hash", "payload", "signature"):
        if key not in receipt:
            errors.append(f"missing receipt field: {key}")
    if errors:
        return errors

    payload = receipt["payload"]
    required_payload = (
        "protocol_version",
        "issuer",
        "issued_at",
        "model",
        "event",
        "grounding",
        "economics",
        "rights",
        "registry",
        "telemetry",
        "privacy",
    )
    for key in required_payload:
        if key not in payload:
            errors.append(f"missing payload field: {key}")

    event = payload.get("event", {})
    for key in ("event_id", "event_hash", "prompt_hash", "answer_hash", "rendered_output_hash"):
        if key not in event:
            errors.append(f"missing event field: {key}")

    grounding = payload.get("grounding", {})
    for key in ("report", "quality", "attribution_gap", "source_accesses", "sources", "claims"):
        if key not in grounding:
            errors.append(f"missing grounding field: {key}")
    rights = payload.get("rights", {})
    for key in ("policy_status", "policy_denials", "decisions"):
        if key not in rights:
            errors.append(f"missing rights field: {key}")
    registry = payload.get("registry", {})
    for key in (
        "registry_status",
        "registry_conflicts",
        "registry_report_hash",
        "decisions",
    ):
        if key not in registry:
            errors.append(f"missing registry field: {key}")
    telemetry = payload.get("telemetry", {})
    for key in (
        "trace_exchange_version",
        "otel_semconv",
        "source_access_trace_hash",
        "source_reference_trace_hash",
        "claim_support_trace_hash",
    ):
        if key not in telemetry:
            errors.append(f"missing telemetry field: {key}")
    privacy = payload.get("privacy", {})
    for key in (
        "prompt_disclosed",
        "answer_disclosed",
        "source_quotes_disclosed",
        "selective_disclosure",
        "disclosure_version",
        "disclosure_root",
        "disclosure_salts",
    ):
        if key not in privacy:
            errors.append(f"missing privacy field: {key}")
    return errors
