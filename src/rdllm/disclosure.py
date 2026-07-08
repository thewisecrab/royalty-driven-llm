"""Selective-disclosure packages for attribution receipts."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterable

from rdllm.receipts import (
    SELECTIVE_DISCLOSURE_VERSION,
    canonical_json,
    disclosure_root_from_leaves,
    hash_payload,
    payload_disclosure_leaves,
    payload_disclosure_root,
    public_receipt,
    verify_receipt,
)
from rdllm.text import stable_hash

PUBLIC_SOURCE_FIELDS = {
    "label",
    "creator_id",
    "work_id",
    "chunk_id",
    "source_uri",
    "content_hash",
    "contribution_weight",
}
PUBLIC_CLAIM_FIELDS = {
    "claim",
    "source_label",
    "support_score",
    "supported",
    "work_id",
    "chunk_id",
    "evidence_span_hash",
    "evidence_start_char",
    "evidence_end_char",
}
PUBLIC_PRIVACY_FIELDS = {
    "prompt_disclosed",
    "answer_disclosed",
    "source_quotes_disclosed",
    "selective_disclosure",
    "disclosure_version",
}

SOURCE_FIELD_RE = re.compile(r"^/grounding/sources/\d+/([^/]+)$")
CLAIM_FIELD_RE = re.compile(r"^/grounding/claims/\d+/([^/]+)$")


def make_selective_disclosure_package(
    receipt: dict[str, Any],
    *,
    disclose_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Create a public package that exposes citation facts and hides private fields."""

    payload = receipt["payload"]
    requested = set(disclose_paths or ())
    disclosed: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    for leaf in payload_disclosure_leaves(payload):
        if _is_disclosed_path(leaf["path"], requested):
            disclosed.append(
                {
                    "path": leaf["path"],
                    "value": leaf["value"],
                    "salt": leaf["salt"],
                    "leaf_hash": leaf["leaf_hash"],
                }
            )
        else:
            redacted.append(
                {
                    "path": leaf["path"],
                    "leaf_hash": leaf["leaf_hash"],
                }
            )

    package = {
        "disclosure_version": SELECTIVE_DISCLOSURE_VERSION,
        "receipt_hash": receipt["receipt_hash"],
        "payload_hash": hash_payload(payload),
        "payload_disclosure_root": payload["privacy"]["disclosure_root"],
        "commitment_scheme": "path-bound salted SHA-256 Merkle commitments",
        "public_receipt": public_receipt(receipt),
        "disclosed": sorted(disclosed, key=lambda item: item["path"]),
        "redacted": sorted(redacted, key=lambda item: item["path"]),
        "summary": {
            "disclosed_path_count": len(disclosed),
            "redacted_path_count": len(redacted),
            "redacted_categories": _redacted_categories(redacted),
        },
    }
    package["package_hash"] = stable_hash(canonical_json(_hashable_package(package)))
    return package


def verify_selective_disclosure_package(
    package: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a selective-disclosure package, optionally against a private receipt."""

    errors = _validate_package_shape(package)
    if errors:
        return errors

    expected_hash = stable_hash(canonical_json(_hashable_package(package)))
    if package.get("package_hash") != expected_hash:
        errors.append("selective disclosure package hash is not reproducible")

    leaf_errors, leaves = _validated_package_leaves(package)
    errors.extend(leaf_errors)
    root = disclosure_root_from_leaves(leaves)
    if root != package.get("payload_disclosure_root"):
        errors.append("selective disclosure root is not reproducible")

    public_errors = _verify_public_receipt_from_disclosures(package)
    errors.extend(public_errors)

    if receipt is not None:
        receipt_errors = verify_receipt(receipt, signing_secret=signing_secret)
        errors.extend(f"private receipt: {error}" for error in receipt_errors)
        if receipt.get("receipt_hash") != package.get("receipt_hash"):
            errors.append("private receipt hash does not match package")
        private_root = receipt.get("payload", {}).get("privacy", {}).get(
            "disclosure_root", ""
        )
        if private_root != package.get("payload_disclosure_root"):
            errors.append("private receipt disclosure root does not match package")
        if payload_disclosure_root(receipt.get("payload", {})) != package.get(
            "payload_disclosure_root"
        ):
            errors.append("private receipt disclosure root is not reproducible")
        private_leaves = payload_disclosure_leaves(receipt.get("payload", {}))
        if _leaf_digest(private_leaves) != _leaf_digest(leaves):
            errors.append("package leaves do not match private receipt leaves")
        if public_receipt(receipt) != package.get("public_receipt"):
            errors.append("package public receipt does not match private receipt")

    return errors


def _validate_package_shape(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "disclosure_version",
        "receipt_hash",
        "payload_hash",
        "payload_disclosure_root",
        "public_receipt",
        "disclosed",
        "redacted",
        "summary",
        "package_hash",
    )
    for key in required:
        if key not in package:
            errors.append(f"missing selective disclosure field: {key}")
    if errors:
        return errors
    if package.get("disclosure_version") != SELECTIVE_DISCLOSURE_VERSION:
        errors.append("selective disclosure version is unsupported")
    if not isinstance(package.get("disclosed"), list):
        errors.append("selective disclosure disclosed field must be a list")
    if not isinstance(package.get("redacted"), list):
        errors.append("selective disclosure redacted field must be a list")
    return errors


def _validated_package_leaves(
    package: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    leaves: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for leaf in package.get("disclosed", []):
        for key in ("path", "value", "salt", "leaf_hash"):
            if key not in leaf:
                errors.append(f"missing disclosed leaf field: {key}")
                continue
        if "path" not in leaf or "leaf_hash" not in leaf:
            continue
        if leaf["path"] in seen_paths:
            errors.append(f"duplicate disclosure path: {leaf['path']}")
        seen_paths.add(leaf["path"])
        expected = stable_hash(
            f"disclosure-leaf:{leaf['path']}\0"
            f"{leaf.get('salt', '')}\0{canonical_json(leaf.get('value'))}"
        )
        if expected != leaf["leaf_hash"]:
            errors.append(f"disclosed leaf hash mismatch: {leaf['path']}")
        leaves.append(
            {
                "path": leaf["path"],
                "salt": leaf.get("salt", ""),
                "value": leaf.get("value"),
                "leaf_hash": leaf["leaf_hash"],
            }
        )

    for leaf in package.get("redacted", []):
        for key in ("path", "leaf_hash"):
            if key not in leaf:
                errors.append(f"missing redacted leaf field: {key}")
                continue
        if "path" not in leaf or "leaf_hash" not in leaf:
            continue
        if leaf["path"] in seen_paths:
            errors.append(f"duplicate disclosure path: {leaf['path']}")
        seen_paths.add(leaf["path"])
        leaves.append({"path": leaf["path"], "leaf_hash": leaf["leaf_hash"]})

    return errors, leaves


def _verify_public_receipt_from_disclosures(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    public = package.get("public_receipt", {})
    if public.get("receipt_hash") != package.get("receipt_hash"):
        errors.append("public receipt hash does not match package")
    if "economics" in public or "grounding" in public:
        errors.append("public receipt exposes private economics or full grounding")

    partial_payload = _payload_from_disclosures(package.get("disclosed", []))
    try:
        expected_public = _expected_public_receipt(
            partial_payload,
            package,
            public.get("signature", {}),
        )
    except KeyError as exc:
        errors.append(f"public disclosure is missing required path: {exc}")
        return errors

    public_without_signature = {
        key: deepcopy(value)
        for key, value in public.items()
        if key != "signature"
    }
    expected_without_signature = {
        key: deepcopy(value)
        for key, value in expected_public.items()
        if key != "signature"
    }
    if public_without_signature.get("event") != expected_without_signature.get("event"):
        errors.append("public receipt event does not match disclosed payload")
    if public_without_signature != expected_without_signature:
        errors.append("public receipt does not match disclosed payload")
    if not isinstance(public.get("signature"), dict):
        errors.append("public receipt signature is missing")
    return errors


def _expected_public_receipt(
    payload: dict[str, Any],
    package: dict[str, Any],
    signature: dict[str, Any],
) -> dict[str, Any]:
    grounding = payload["grounding"]
    attribution_gap = grounding.get("attribution_gap", {})
    privacy = payload.get("privacy", {})
    return {
        "receipt_hash": package["receipt_hash"],
        "protocol_version": payload["protocol_version"],
        "issuer": payload["issuer"],
        "issued_at": payload["issued_at"],
        "model": payload["model"],
        "event": payload["event"],
        "telemetry": payload.get("telemetry", {}),
        "grounding_report": grounding["report"],
        "grounding_quality": grounding.get("quality", {}),
        "attribution_gap": {
            "verdict": attribution_gap.get("verdict", ""),
            "summary": attribution_gap.get("summary", {}),
            "report_hash": attribution_gap.get("report_hash", ""),
        },
        "rights": {
            "policy_status": payload["rights"]["policy_status"],
            "policy_denials": payload["rights"]["policy_denials"],
        },
        "registry": {
            "registry_status": payload["registry"].get("registry_status", "clear"),
            "registry_conflicts": payload["registry"].get("registry_conflicts", 0),
            "registry_report_hash": payload["registry"].get(
                "registry_report_hash", ""
            ),
        },
        "sources": [
            {key: source[key] for key in sorted(PUBLIC_SOURCE_FIELDS)}
            for source in grounding["sources"]
        ],
        "claim_support": [
            {key: claim[key] for key in sorted(PUBLIC_CLAIM_FIELDS)}
            for claim in grounding["claims"]
        ],
        "privacy": {
            "prompt_disclosed": privacy.get("prompt_disclosed", False),
            "answer_disclosed": privacy.get("answer_disclosed", False),
            "source_quotes_disclosed": privacy.get("source_quotes_disclosed", False),
            "selective_disclosure": privacy.get("selective_disclosure", ""),
            "disclosure_version": privacy.get("disclosure_version", ""),
            "disclosure_root": package["payload_disclosure_root"],
        },
        "signature": signature,
    }


def _payload_from_disclosures(disclosed: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for leaf in disclosed:
        _assign_path(payload, leaf["path"], leaf.get("value"))
    return payload


def _assign_path(root: dict[str, Any], path: str, value: Any) -> None:
    parts = _parse_pointer(path)
    current: Any = root
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if isinstance(current, list):
            item_index = int(part)
            while len(current) <= item_index:
                current.append(None)
            if last:
                current[item_index] = value
            else:
                next_container: list[Any] | dict[str, Any]
                if current[item_index] is None:
                    next_container = [] if parts[index + 1].isdigit() else {}
                    current[item_index] = next_container
                current = current[item_index]
            continue

        if last:
            current[part] = value
        else:
            if part not in current:
                current[part] = [] if parts[index + 1].isdigit() else {}
            current = current[part]


def _parse_pointer(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"invalid disclosure path: {path}")
    return [
        part.replace("~1", "/").replace("~0", "~")
        for part in path.strip("/").split("/")
        if part
    ]


def _is_disclosed_path(path: str, requested: set[str]) -> bool:
    if path in requested:
        return True
    if any(path.startswith(prefix.rstrip("/") + "/") for prefix in requested):
        return True
    if path in {
        "/protocol_version",
        "/issuer",
        "/issued_at",
        "/grounding/attribution_gap/verdict",
        "/grounding/attribution_gap/report_hash",
        "/rights/policy_status",
        "/rights/policy_denials",
        "/registry/registry_status",
        "/registry/registry_conflicts",
        "/registry/registry_report_hash",
    }:
        return True
    if path.startswith(("/model/", "/event/", "/grounding/report/")):
        return True
    if path.startswith("/telemetry/"):
        return True
    if path.startswith(("/grounding/quality/", "/grounding/attribution_gap/summary/")):
        return True
    if path.startswith("/grounding/attribution_gap/scores/"):
        return True
    if match := SOURCE_FIELD_RE.match(path):
        return match.group(1) in PUBLIC_SOURCE_FIELDS
    if match := CLAIM_FIELD_RE.match(path):
        return match.group(1) in PUBLIC_CLAIM_FIELDS
    if path.startswith("/privacy/"):
        field = path.removeprefix("/privacy/")
        return field in PUBLIC_PRIVACY_FIELDS
    return False


def _redacted_categories(redacted: list[dict[str, Any]]) -> dict[str, int]:
    categories = {
        "economics": 0,
        "source_accesses": 0,
        "source_quotes": 0,
        "claim_evidence_text": 0,
        "rights_decisions": 0,
        "registry_decisions": 0,
        "other": 0,
    }
    for leaf in redacted:
        path = leaf.get("path", "")
        if path.startswith("/economics/"):
            categories["economics"] += 1
        elif path.startswith("/grounding/source_accesses/"):
            categories["source_accesses"] += 1
        elif path.endswith("/quote"):
            categories["source_quotes"] += 1
        elif path.endswith("/evidence_text"):
            categories["claim_evidence_text"] += 1
        elif path.startswith("/rights/decisions/"):
            categories["rights_decisions"] += 1
        elif path.startswith("/registry/decisions/"):
            categories["registry_decisions"] += 1
        else:
            categories["other"] += 1
    return {key: value for key, value in categories.items() if value}


def _leaf_digest(leaves: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return sorted((leaf["path"], leaf["leaf_hash"]) for leaf in leaves)


def _hashable_package(package: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in package.items()
        if key != "package_hash"
    }
