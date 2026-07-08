"""Persistent memory provenance receipts.

This layer treats assistant, agent, and model memory cells as derived artifacts.
If an answer relies on persistent memory, the memory write must preserve source
labels, upstream proof hashes, license/retention policy, and downstream royalty
obligations; the later answer must carry those labels back into the verified
footer before rendering.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.artifact_refs import resolve_artifact_refs
from rdllm.client_attribution_enforcement import (
    verify_client_attribution_enforcement_receipt,
)
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.source_footer_delivery import verify_source_footer_delivery_receipt
from rdllm.text import stable_hash

PERSISTENT_MEMORY_PROVENANCE_VERSION = "rdllm-persistent-memory-provenance/v1"
PERSISTENT_MEMORY_PROVENANCE_SCHEMA = (
    "docs/schemas/persistent_memory_provenance.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L106"
MINIMUM_CLIENT_LEVEL = "RDLLM-L105"

DECLARED_HASH_FIELDS = (
    "persistent_memory_provenance_hash",
    "client_enforcement_hash",
    "source_footer_delivery_hash",
    "foundation_profile_hash",
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
    "memory_text",
    "raw_memory_text",
    "memory_value",
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


def load_persistent_memory_provenance_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a persistent memory provenance receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"persistent_memory_provenance_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if isinstance(metadata, dict) and "foundation_profile_hash" in artifact:
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("-1")


def _source_labels_from_delivery(delivery: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(row.get("label", ""))
            for row in delivery.get("source_delivery_rows", [])
            if row.get("label")
        }
    )


def _client_source_labels(client_receipt: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(label)
            for label in client_receipt.get("client_decision", {}).get(
                "source_labels", []
            )
            if str(label)
        }
    )


def _client_rendered_output_hash(client_receipt: dict[str, Any]) -> str:
    return str(
        client_receipt.get("client_decision", {}).get("rendered_output_hash")
        or client_receipt.get("artifact_bindings", {}).get("rendered_output_hash")
        or ""
    )


def _memory_text_hash(entry: dict[str, Any]) -> str:
    if entry.get("memory_hash"):
        return str(entry["memory_hash"])
    return stable_hash(str(entry.get("memory_text", "")))


def _origin_hashes(entry: dict[str, Any]) -> list[str]:
    hashes = []
    for artifact in entry.get("origin_artifacts", []):
        if isinstance(artifact, dict):
            value = artifact.get("artifact_hash")
            if value:
                hashes.append(str(value))
    return sorted(set(hashes))


def _memory_entry_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for entry in sorted(
        receipt_input.get("memory_entries", []),
        key=lambda item: (
            str(item.get("memory_id", "")),
            int(item.get("version", 0) or 0),
            int(item.get("sequence", 0) or 0),
        ),
    ):
        source_labels = sorted({str(label) for label in entry.get("source_labels", [])})
        retention_policy = entry.get("retention_policy", {})
        row = {
            "memory_id": str(entry.get("memory_id", "")),
            "version": int(entry.get("version", 0) or 0),
            "operation": str(entry.get("operation", "write")),
            "sequence": int(entry.get("sequence", 0) or 0),
            "memory_type": str(entry.get("memory_type", "persistent_memory")),
            "memory_text_hash": _memory_text_hash(entry),
            "parent_memory_text_hash": str(entry.get("parent_memory_hash", "")),
            "source_labels": source_labels,
            "origin_artifact_hashes": _origin_hashes(entry),
            "license_terms_hash": str(entry.get("license_terms_hash", "")),
            "retention_policy_hash": hash_payload(retention_policy),
            "retention_basis": str(retention_policy.get("basis", "")),
            "expires_at": str(retention_policy.get("expires_at", "")),
            "allowed_use_count": len(entry.get("allowed_uses", [])),
            "royalty_obligation_count": len(entry.get("royalty_obligations", [])),
            "delete_tombstone_hash": str(entry.get("delete_tombstone_hash", "")),
        }
        row["memory_entry_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _royalty_obligation_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for entry in sorted(
        receipt_input.get("memory_entries", []),
        key=lambda item: (
            str(item.get("memory_id", "")),
            int(item.get("version", 0) or 0),
        ),
    ):
        for obligation in sorted(
            entry.get("royalty_obligations", []),
            key=lambda item: (
                str(item.get("source_label", "")),
                str(item.get("creator_id", "")),
                str(item.get("work_id", "")),
            ),
        ):
            row = {
                "memory_id": str(entry.get("memory_id", "")),
                "memory_version": int(entry.get("version", 0) or 0),
                "source_label": str(obligation.get("source_label", "")),
                "creator_id": str(obligation.get("creator_id", "")),
                "work_id": str(obligation.get("work_id", "")),
                "share": str(obligation.get("share", "0")),
                "settlement_state": str(
                    obligation.get("settlement_state", "direct")
                ),
                "obligation_hash": hash_payload(obligation),
            }
            row["royalty_row_hash"] = hash_payload(row)
            rows.append(row)
    return rows


def _memory_read_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    client = receipt_input.get("client_attribution_enforcement", {})
    client_hash = _declared_hash(client)
    client_output_hash = _client_rendered_output_hash(client)
    rows = []
    for read in sorted(
        receipt_input.get("memory_reads", []),
        key=lambda item: (
            int(item.get("sequence", 0) or 0),
            str(item.get("read_id", "")),
        ),
    ):
        row = {
            "read_id": str(read.get("read_id", "")),
            "memory_id": str(read.get("memory_id", "")),
            "memory_version": int(read.get("memory_version", 0) or 0),
            "sequence": int(read.get("sequence", 0) or 0),
            "rendered_output_hash": str(
                read.get("rendered_output_hash") or client_output_hash
            ),
            "client_enforcement_hash": str(
                read.get("client_enforcement_hash") or client_hash
            ),
            "source_labels_carried": sorted(
                {str(label) for label in read.get("source_labels_carried", [])}
            ),
            "visible_source_labels": sorted(
                {str(label) for label in read.get("visible_source_labels", [])}
            ),
            "usage_purpose": str(read.get("usage_purpose", "answer_generation")),
        }
        row["memory_read_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    source_footer_delivery = receipt_input.get("source_footer_delivery")
    client_receipt = receipt_input.get("client_attribution_enforcement")
    foundation_profile = receipt_input.get("foundation_api_profile")
    memory_entries = receipt_input.get("memory_entries", [])
    memory_reads = receipt_input.get("memory_reads", [])
    return {
        "source_footer_delivery_hash": _declared_hash(source_footer_delivery),
        "source_footer_delivery_hash_reproducible": _artifact_hash_is_reproducible(
            source_footer_delivery
        ),
        "client_enforcement_hash": _declared_hash(client_receipt),
        "client_enforcement_hash_reproducible": _artifact_hash_is_reproducible(
            client_receipt
        ),
        "foundation_profile_hash": _declared_hash(foundation_profile),
        "foundation_profile_hash_reproducible": _artifact_hash_is_reproducible(
            foundation_profile
        )
        if foundation_profile
        else True,
        "memory_entry_root": hash_payload(_memory_entry_rows(receipt_input)),
        "memory_read_root": hash_payload(_memory_read_rows(receipt_input)),
        "royalty_obligation_root": hash_payload(
            _royalty_obligation_rows(receipt_input)
        ),
        "memory_entry_input_hash": hash_payload(memory_entries),
        "memory_read_input_hash": hash_payload(memory_reads),
        "rendered_output_hash": _client_rendered_output_hash(client_receipt),
    }


def _base_checks(
    *,
    receipt_input: dict[str, Any],
    memory_entries: list[dict[str, Any]],
    memory_reads: list[dict[str, Any]],
    royalty_rows: list[dict[str, Any]],
    artifact_bindings: dict[str, Any],
    source_footer_errors: list[str],
    client_errors: list[str],
) -> dict[str, bool]:
    delivery = receipt_input.get("source_footer_delivery", {})
    client_receipt = receipt_input.get("client_attribution_enforcement", {})
    delivered_labels = set(_source_labels_from_delivery(delivery))
    client_labels = set(_client_source_labels(client_receipt))
    client_hash = _declared_hash(client_receipt)
    rendered_output_hash = _client_rendered_output_hash(client_receipt)
    entry_by_key = {
        (row["memory_id"], row["version"]): row
        for row in memory_entries
        if row["operation"] != "delete"
    }

    source_labels_by_memory = {
        row["memory_id"]: set(row["source_labels"])
        for row in memory_entries
        if row["operation"] != "delete"
    }
    delete_sequence = {
        row["memory_id"]: row["sequence"]
        for row in memory_entries
        if row["operation"] == "delete" and row["delete_tombstone_hash"]
    }

    obligations_by_memory_label = {
        (row["memory_id"], row["source_label"]): row for row in royalty_rows
    }
    obligation_coverage = all(
        (entry["memory_id"], label) in obligations_by_memory_label
        for entry in memory_entries
        if entry["operation"] != "delete"
        for label in entry["source_labels"]
    )
    memory_ids = {
        row["memory_id"] for row in memory_entries if row["operation"] != "delete"
    }
    shares_conserved = True
    for memory_id in memory_ids:
        total = sum(
            (
                _as_decimal(row["share"])
                for row in royalty_rows
                if row["memory_id"] == memory_id
            ),
            Decimal("0"),
        )
        if total != Decimal("1.0") and total != Decimal("1"):
            shares_conserved = False
            break

    read_binds_output = all(
        row["client_enforcement_hash"] == client_hash
        and row["rendered_output_hash"] == rendered_output_hash
        for row in memory_reads
    )
    read_labels_visible = all(
        (
            source_labels_by_memory.get(row["memory_id"], set())
            <= set(row["source_labels_carried"])
            and source_labels_by_memory.get(row["memory_id"], set())
            <= set(row["visible_source_labels"])
            and set(row["visible_source_labels"]) <= (delivered_labels | client_labels)
        )
        for row in memory_reads
    )
    deleted_not_reused = all(
        not (
            row["memory_id"] in delete_sequence
            and row["sequence"] > delete_sequence[row["memory_id"]]
        )
        for row in memory_reads
    )

    return {
        "source_footer_delivery_verified": not source_footer_errors,
        "client_attribution_enforcement_verified": not client_errors
        and client_receipt.get("client_decision", {}).get(
            "may_render_attributed_answer"
        )
        is True,
        "artifact_hashes_reproducible": artifact_bindings[
            "source_footer_delivery_hash_reproducible"
        ]
        and artifact_bindings["client_enforcement_hash_reproducible"]
        and artifact_bindings["foundation_profile_hash_reproducible"],
        "memory_entries_have_origin_sources": bool(memory_entries)
        and all(
            row["operation"] in {"write", "update", "delete"}
            and (
                row["operation"] == "delete"
                or (row["source_labels"] and row["origin_artifact_hashes"])
            )
            for row in memory_entries
        ),
        "memory_origin_labels_match_delivered_footer": all(
            set(row["source_labels"]) <= delivered_labels
            for row in memory_entries
            if row["operation"] != "delete"
        ),
        "memory_entries_have_license_and_retention_policy": all(
            row["operation"] == "delete"
            or (
                bool(row["license_terms_hash"])
                and bool(row["retention_basis"])
                and row["allowed_use_count"] > 0
            )
            for row in memory_entries
        ),
        "memory_royalty_obligations_cover_sources": bool(royalty_rows)
        and obligation_coverage
        and shares_conserved,
        "memory_reads_bind_to_client_rendered_output": bool(memory_reads)
        and all((row["memory_id"], row["memory_version"]) in entry_by_key for row in memory_reads)
        and read_binds_output,
        "memory_read_labels_visible_in_footer": read_labels_visible,
        "deleted_memory_not_reused": deleted_not_reused,
        "private_memory_text_not_disclosed": not _contains_private_fields(
            receipt_input.get("public_overrides", {})
        ),
    }


def _policy_summary(receipt_input: dict[str, Any]) -> dict[str, Any]:
    policy = receipt_input.get("memory_policy", {})
    return {
        "policy_id": str(policy.get("policy_id", "memory-policy:default")),
        "requires_source_provenance": policy.get("requires_source_provenance")
        is True,
        "requires_license_terms": policy.get("requires_license_terms") is True,
        "requires_royalty_carry_forward": policy.get(
            "requires_royalty_carry_forward"
        )
        is True,
        "requires_delete_tombstones": policy.get("requires_delete_tombstones")
        is True,
        "policy_hash": hash_payload(policy),
    }


def make_persistent_memory_provenance_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public receipt for persistent memory source carry-forward."""

    receipt_input = resolve_artifact_refs(receipt_input)
    source_footer_errors = verify_source_footer_delivery_receipt(
        receipt_input.get("source_footer_delivery", {}),
        receipt_input.get("source_footer_delivery_input", {}),
        signing_secret=signing_secret,
    )
    client_errors = verify_client_attribution_enforcement_receipt(
        receipt_input.get("client_attribution_enforcement", {}),
        receipt_input.get("client_attribution_input", {}),
        signing_secret=signing_secret,
    )
    memory_entries = _memory_entry_rows(receipt_input)
    memory_reads = _memory_read_rows(receipt_input)
    royalty_rows = _royalty_obligation_rows(receipt_input)
    artifact_bindings = _artifact_bindings(receipt_input)
    checks = _base_checks(
        receipt_input=receipt_input,
        memory_entries=memory_entries,
        memory_reads=memory_reads,
        royalty_rows=royalty_rows,
        artifact_bindings=artifact_bindings,
        source_footer_errors=source_footer_errors,
        client_errors=client_errors,
    )
    policy = _policy_summary(receipt_input)
    checks["memory_policy_is_fail_closed"] = (
        policy["requires_source_provenance"]
        and policy["requires_license_terms"]
        and policy["requires_royalty_carry_forward"]
        and policy["requires_delete_tombstones"]
    )

    receipt: dict[str, Any] = {
        "version": PERSISTENT_MEMORY_PROVENANCE_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get(
                    "case_id", "case:persistent-memory-provenance"
                )
            ),
            "status": "ready" if all(checks.values()) else "blocked",
        },
        "memory_system": {
            "system_id": str(
                receipt_input.get("memory_system", {}).get(
                    "system_id", "memory:unknown"
                )
            ),
            "system_version": str(
                receipt_input.get("memory_system", {}).get("system_version", "")
            ),
            "scope": str(
                receipt_input.get("memory_system", {}).get(
                    "scope", "assistant_persistent_memory"
                )
            ),
            "minimum_client_level": MINIMUM_CLIENT_LEVEL,
        },
        "artifact_bindings": artifact_bindings,
        "memory_policy": policy,
        "memory_entries": memory_entries,
        "memory_reads": memory_reads,
        "royalty_obligations": royalty_rows,
        "verification_errors": {
            "source_footer_delivery": len(source_footer_errors),
            "client_attribution_enforcement": len(client_errors),
        },
        "checks": checks,
        "privacy": {
            "memory_text_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "payment_data_disclosed": False,
            "memory_receipt_uses_hashes_labels_and_policy_refs": True,
        },
        "schemas": {
            "persistent_memory_provenance": PERSISTENT_MEMORY_PROVENANCE_SCHEMA,
            "client_attribution_enforcement": "docs/schemas/client_attribution_enforcement.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
    }
    checks["private_memory_text_not_disclosed"] = (
        checks["private_memory_text_not_disclosed"]
        and _private_strings_absent(receipt, receipt_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    receipt["case"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    receipt["summary"] = {
        "status": receipt["case"]["status"],
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_client_level": MINIMUM_CLIENT_LEVEL,
        "memory_entry_count": len(memory_entries),
        "memory_read_count": len(memory_reads),
        "source_label_count": len(
            sorted(
                {
                    label
                    for row in memory_entries
                    for label in row.get("source_labels", [])
                }
            )
        ),
        "royalty_obligation_count": len(royalty_rows),
        "failed_check_count": failed_check_count,
        "memory_provenance_ready": failed_check_count == 0,
        "privacy_preserved": checks["private_memory_text_not_disclosed"],
    }
    receipt["persistent_memory_provenance_hash"] = hash_payload(
        _hashable_receipt(receipt)
    )
    signature = (
        sign_payload(_hashable_receipt(receipt), signing_secret)
        if signing_secret
        else ""
    )
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": signature,
    }
    return receipt


def validate_persistent_memory_provenance_shape(
    receipt: dict[str, Any]
) -> list[str]:
    """Validate the public shape of a persistent memory provenance receipt."""

    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "memory_system",
        "artifact_bindings",
        "memory_policy",
        "memory_entries",
        "memory_reads",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "persistent_memory_provenance_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing persistent memory provenance field: {key}")
    if errors:
        return errors
    if receipt.get("version") != PERSISTENT_MEMORY_PROVENANCE_VERSION:
        errors.append("persistent memory provenance version is unsupported")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("persistent memory provenance target level is not RDLLM-L106")
    if "persistent_memory_provenance" not in receipt.get("schemas", {}):
        errors.append("missing persistent memory provenance schema")
    if not isinstance(receipt.get("memory_entries"), list):
        errors.append("persistent memory entries must be a list")
    if not isinstance(receipt.get("memory_reads"), list):
        errors.append("persistent memory reads must be a list")
    return errors


def verify_persistent_memory_provenance_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a persistent memory provenance receipt against private replay input."""

    errors = validate_persistent_memory_provenance_shape(receipt)
    expected = make_persistent_memory_provenance_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "memory_system",
        "artifact_bindings",
        "memory_policy",
        "memory_entries",
        "memory_reads",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if receipt.get(key) != expected.get(key):
            errors.append(f"persistent memory provenance {key} mismatch")
    if receipt.get("persistent_memory_provenance_hash") != expected.get(
        "persistent_memory_provenance_hash"
    ):
        errors.append("persistent memory provenance hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get(
        "value"
    ):
        errors.append("persistent memory provenance signature mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("persistent memory provenance has failing checks")
    return errors
