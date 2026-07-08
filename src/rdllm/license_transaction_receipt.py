"""License-server transaction receipts for attribution-aware source access.

This layer closes the dynamic-authorization gap.  Content protocol records and
source leases can describe allowed use, but a foundation-model provider also
needs a replayable record that a publisher or license server issued an accepted,
non-replayed transaction token for the exact source usage before access and
settlement.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

LICENSE_TRANSACTION_RECEIPT_VERSION = "rdllm-license-transaction-receipt/v1"
LICENSE_TRANSACTION_RECEIPT_SCHEMA = (
    "docs/schemas/license_transaction_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L101"

DECLARED_HASH_FIELDS = (
    "license_transaction_receipt_hash",
    "citation_reliance_receipt_hash",
    "protocol_ingestion_report_hash",
    "lease_report_hash",
    "binding_report_hash",
    "report_hash",
    "contract_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "raw_notice_text",
    "raw_protocol_payload",
    "raw_license_token",
    "license_server_secret",
    "quote",
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

DIRECT_STATUSES = {"direct", "accepted", "payable", "paid", "settled"}
ESCROW_STATUSES = {
    "escrow",
    "held",
    "rights_conflict_escrow",
    "source_access_lease_escrow",
    "content_protocol_escrow",
    "license_transaction_escrow",
    "license_escrow",
}
DENY_PAYMENT_TYPES = {"deny", "denied", "blocked", "forbidden", "none"}


def load_license_transaction_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a license transaction receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"license_transaction_receipt_hash", "signature"}
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
        return True
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"transaction_row_hash", "coverage_row_hash"}
    }


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


def _private_strings_absent(report: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _policy(receipt_input: dict[str, Any]) -> dict[str, bool]:
    configured = dict(receipt_input.get("policy", {}))
    return {
        "require_license_server_transaction_for_direct_sources": bool(
            configured.get(
                "require_license_server_transaction_for_direct_sources", True
            )
        ),
        "require_license_server_signature": bool(
            configured.get("require_license_server_signature", True)
        ),
        "require_license_ledger_inclusion": bool(
            configured.get("require_license_ledger_inclusion", True)
        ),
        "require_transaction_before_access": bool(
            configured.get("require_transaction_before_access", True)
        ),
        "require_transaction_terms_match_protocol": bool(
            configured.get("require_transaction_terms_match_protocol", True)
        ),
        "require_transaction_binds_access_log": bool(
            configured.get("require_transaction_binds_access_log", True)
        ),
        "require_reliance_receipt_for_direct_sources": bool(
            configured.get("require_reliance_receipt_for_direct_sources", True)
        ),
        "require_invalid_or_missing_transaction_escrowed": bool(
            configured.get("require_invalid_or_missing_transaction_escrowed", True)
        ),
    }


def _is_escrow(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    route = str(row.get("escrow_account", row.get("settlement_route", "")))
    return status in ESCROW_STATUSES or route.endswith("escrow") or "escrow" in route


def _is_direct(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    return bool(row.get("direct_settlement", False)) or (
        status in DIRECT_STATUSES and not _is_escrow(row)
    )


def _source_usage_rows(source_access_lease_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(
        source_access_lease_report.get("source_usage_rows", []), start=1
    ):
        public = {
            "source_usage_id": str(row.get("source_usage_id", f"use:{index}")),
            "source_label": str(row.get("source_label", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash": str(row.get("content_hash", "")),
            "usage_purpose": str(row.get("usage_purpose", "retrieval_inference")),
            "settlement_status": str(row.get("settlement_status", "direct")),
            "escrow_account": str(row.get("escrow_account", "")),
            "creator_pool_rate": str(row.get("creator_pool_rate", "")),
        }
        public["direct_settlement"] = _is_direct(public)
        public["escrowed"] = _is_escrow(public)
        rows.append(public)
    return rows


def _matches_usage(row: dict[str, Any], usage: dict[str, Any]) -> bool:
    return bool(
        (
            not row.get("source_usage_id")
            or row.get("source_usage_id") == usage.get("source_usage_id")
        )
        and (
            not row.get("work_id")
            or not usage.get("work_id")
            or row.get("work_id") == usage.get("work_id")
        )
        and (
            not row.get("chunk_id")
            or not usage.get("chunk_id")
            or row.get("chunk_id") == usage.get("chunk_id")
        )
        and (
            not row.get("source_uri")
            or not usage.get("source_uri")
            or row.get("source_uri") == usage.get("source_uri")
        )
    )


def _access_rows_by_usage(source_access_lease_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    access_rows = source_access_lease_report.get("access_log_rows", [])
    by_usage: dict[str, dict[str, Any]] = {}
    for usage in _source_usage_rows(source_access_lease_report):
        for access in access_rows:
            if _matches_usage(access, usage):
                by_usage[usage["source_usage_id"]] = access
                break
    return by_usage


def _lease_coverage(source_access_lease_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_usage_id", "")): row
        for row in source_access_lease_report.get("coverage_rows", [])
        if row.get("source_usage_id")
    }


def _protocol_coverage(content_protocol_ingestion_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_usage_id", "")): row
        for row in content_protocol_ingestion_report.get("coverage_rows", [])
        if row.get("source_usage_id")
    }


def _protocol_rows(content_protocol_ingestion_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("protocol_record_id", "")): row
        for row in content_protocol_ingestion_report.get("protocol_rows", [])
        if row.get("protocol_record_id")
    }


def _reliance_rows(citation_reliance_receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {}
    for row in citation_reliance_receipt.get("source_reliance_rows", []):
        if row.get("source_label"):
            rows[str(row.get("source_label"))] = row
        if row.get("source_id"):
            rows[str(row.get("source_id"))] = row
        if row.get("chunk_id"):
            rows[str(row.get("chunk_id"))] = row
    return rows


def _transaction_signature_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "token_payload_hash",
            "token_signature",
            "token_signature_valid",
            "license_ledger_leaf_hash",
            "license_ledger_checkpoint_hash",
            "license_ledger_inclusion_proof_hashes",
            "license_ledger_included",
            "transaction_row_hash",
        }
    }


def _transaction_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(receipt_input.get("license_transactions", []), start=1):
        public = {
            "transaction_id": str(
                row.get("transaction_id") or row.get("license_transaction_id") or f"license-tx:{index}"
            ),
            "source_usage_id": str(row.get("source_usage_id", "")),
            "access_event_id": str(row.get("access_event_id", "")),
            "protocol_record_id": str(row.get("protocol_record_id", "")),
            "license_server": str(row.get("license_server", "")),
            "provider_id": str(row.get("provider_id", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash": str(row.get("content_hash", "")),
            "usage_purpose": str(row.get("usage_purpose", "retrieval_inference")),
            "payment_type": str(row.get("payment_type", "royalty")).lower(),
            "creator_pool_rate": str(row.get("creator_pool_rate", "")),
            "minimum_creator_pool_rate": str(row.get("minimum_creator_pool_rate", "0")),
            "attribution_required": bool(row.get("attribution_required", True)),
            "royalty_required": bool(row.get("royalty_required", True)),
            "transaction_status": str(row.get("transaction_status", "accepted")).lower(),
            "requested_at": str(row.get("requested_at", "")),
            "issued_at": str(row.get("issued_at", "")),
            "accepted_at": str(row.get("accepted_at", "")),
            "valid_until": str(row.get("valid_until", "")),
            "access_nonce_hash": str(row.get("access_nonce_hash", "")),
            "metering_event_hash": str(row.get("metering_event_hash", "")),
            "token_nonce_hash": str(row.get("token_nonce_hash", "")),
            "terms_hash": str(row.get("terms_hash", "")),
            "raw_license_token_disclosed": False,
        }
        secret = str(row.get("license_server_secret", ""))
        payload = _transaction_signature_payload(public)
        public["token_payload_hash"] = str(
            row.get("token_payload_hash") or hash_payload(payload)
        )
        expected_signature = sign_payload(payload, secret) if secret else ""
        public["token_signature"] = str(
            row.get("token_signature") or expected_signature
        )
        public["token_signature_valid"] = bool(
            public["token_signature"] and (
                not secret or public["token_signature"] == expected_signature
            )
        )
        leaf_payload = {
            "transaction_id": public["transaction_id"],
            "source_usage_id": public["source_usage_id"],
            "token_payload_hash": public["token_payload_hash"],
            "token_signature": public["token_signature"],
        }
        leaf_hash = str(row.get("license_ledger_leaf_hash") or hash_payload(leaf_payload))
        proof_hashes = [
            str(item)
            for item in row.get("license_ledger_inclusion_proof_hashes", [leaf_hash])
            if str(item)
        ]
        public["license_ledger_leaf_hash"] = leaf_hash
        public["license_ledger_checkpoint_hash"] = str(
            row.get("license_ledger_checkpoint_hash")
            or hash_payload(
                {
                    "license_server": public["license_server"],
                    "leaf_hashes": sorted(set(proof_hashes)),
                }
            )
        )
        public["license_ledger_inclusion_proof_hashes"] = proof_hashes
        public["license_ledger_included"] = bool(
            public["license_ledger_checkpoint_hash"] and leaf_hash in proof_hashes
        )
        public["transaction_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _transaction_valid_for_access(transaction: dict[str, Any], access: dict[str, Any]) -> bool:
    if not transaction:
        return False
    accessed_at = str(access.get("accessed_at", ""))
    issued_at = str(transaction.get("issued_at", ""))
    accepted_at = str(transaction.get("accepted_at", ""))
    valid_until = str(transaction.get("valid_until", ""))
    if issued_at and accessed_at and issued_at > accessed_at:
        return False
    if accepted_at and accessed_at and accepted_at > accessed_at:
        return False
    if valid_until and accessed_at and accessed_at > valid_until:
        return False
    return True


def _transaction_binds_access(transaction: dict[str, Any], access: dict[str, Any]) -> bool:
    if not transaction or not access:
        return False
    return bool(
        (not transaction.get("access_event_id") or transaction.get("access_event_id") == access.get("access_event_id"))
        and (
            not transaction.get("access_nonce_hash")
            or transaction.get("access_nonce_hash") == access.get("request_nonce_hash")
        )
        and (
            not transaction.get("metering_event_hash")
            or transaction.get("metering_event_hash") == access.get("metering_event_hash")
        )
    )


def _transaction_terms_match_protocol(
    transaction: dict[str, Any],
    protocol_coverage_row: dict[str, Any],
    protocol_record: dict[str, Any],
) -> bool:
    if not transaction or not protocol_coverage_row:
        return False
    if transaction.get("transaction_status") != "accepted":
        return False
    if transaction.get("payment_type") in DENY_PAYMENT_TYPES:
        return False
    protocol_id = str(protocol_coverage_row.get("selected_protocol_record_id", ""))
    if protocol_id and transaction.get("protocol_record_id") != protocol_id:
        return False
    if _decimal(transaction.get("minimum_creator_pool_rate")) < _decimal(
        protocol_coverage_row.get("protocol_minimum_creator_pool_rate", "0")
    ):
        return False
    if bool(protocol_coverage_row.get("protocol_attribution_required", False)) and not bool(
        transaction.get("attribution_required", False)
    ):
        return False
    if bool(protocol_coverage_row.get("protocol_royalty_required", False)) and not bool(
        transaction.get("royalty_required", False)
    ):
        return False
    if protocol_record and protocol_record.get("license_server"):
        return transaction.get("license_server") == protocol_record.get("license_server")
    return True


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "source_access_lease_report": receipt_input.get("source_access_lease_report"),
        "content_protocol_ingestion_report": receipt_input.get(
            "content_protocol_ingestion_report"
        ),
        "citation_reliance_receipt": receipt_input.get("citation_reliance_receipt"),
        "creator_license_contract": receipt_input.get("creator_license_contract"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(
            artifact
        )
    return bindings


def _coverage_rows(
    *,
    usage_rows: list[dict[str, Any]],
    transaction_rows: list[dict[str, Any]],
    source_access_lease_report: dict[str, Any],
    content_protocol_ingestion_report: dict[str, Any],
    citation_reliance_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    access_rows = _access_rows_by_usage(source_access_lease_report)
    lease_coverage = _lease_coverage(source_access_lease_report)
    protocol_by_usage = _protocol_coverage(content_protocol_ingestion_report)
    protocol_by_id = _protocol_rows(content_protocol_ingestion_report)
    reliance_by_key = _reliance_rows(citation_reliance_receipt)
    rows = []
    for usage in usage_rows:
        matches = [
            row for row in transaction_rows if _matches_usage(row, usage)
        ]
        selected = next(
            (row for row in matches if row["transaction_status"] == "accepted"),
            matches[0] if matches else {},
        )
        access = access_rows.get(usage["source_usage_id"], {})
        lease_row = lease_coverage.get(usage["source_usage_id"], {})
        protocol_row = protocol_by_usage.get(usage["source_usage_id"], {})
        protocol_record = protocol_by_id.get(
            str(protocol_row.get("selected_protocol_record_id", "")), {}
        )
        reliance_row = (
            reliance_by_key.get(usage["source_label"])
            or reliance_by_key.get(usage["chunk_id"])
            or {}
        )
        accepted = bool(selected and selected.get("transaction_status") == "accepted")
        signature_valid = bool(selected and selected.get("token_signature_valid", False))
        ledger_included = bool(selected and selected.get("license_ledger_included", False))
        access_bound = _transaction_binds_access(selected, access)
        valid_window = _transaction_valid_for_access(selected, access)
        terms_match = _transaction_terms_match_protocol(
            selected, protocol_row, protocol_record
        )
        source_access_covered = bool(
            lease_row.get("covered_for_direct_settlement", False)
            or (not usage["direct_settlement"] and lease_row.get("denied_or_unleased_escrowed", False))
        )
        protocol_covered = bool(
            protocol_row.get("covered_for_protocol_ingestion", False)
            or (not usage["direct_settlement"] and protocol_row.get("missing_or_denied_protocol_escrowed", False))
        )
        reliance_covered = bool(
            reliance_row.get("covered_for_faithful_reliance", False)
            or not usage["direct_settlement"]
        )
        covered = bool(
            usage["direct_settlement"]
            and accepted
            and signature_valid
            and ledger_included
            and access_bound
            and valid_window
            and terms_match
            and source_access_covered
            and protocol_covered
            and reliance_covered
        )
        invalid_or_missing_escrowed = bool(
            not covered
            and not usage["direct_settlement"]
            and usage["escrowed"]
        )
        row = {
            "source_usage_id": usage["source_usage_id"],
            "source_label": usage["source_label"],
            "work_id": usage["work_id"],
            "chunk_id": usage["chunk_id"],
            "usage_purpose": usage["usage_purpose"],
            "direct_settlement": usage["direct_settlement"],
            "escrowed": usage["escrowed"],
            "matching_transaction_count": len(matches),
            "selected_transaction_id": str(selected.get("transaction_id", "")),
            "selected_license_server": str(selected.get("license_server", "")),
            "transaction_accepted": accepted,
            "token_signature_valid": signature_valid,
            "license_ledger_included": ledger_included,
            "transaction_terms_match_protocol": terms_match,
            "transaction_binds_access_log": access_bound,
            "transaction_valid_before_access": valid_window,
            "source_access_lease_covered": source_access_covered,
            "content_protocol_covered": protocol_covered,
            "citation_reliance_covered": reliance_covered,
            "covered_for_license_transaction": covered,
            "invalid_or_missing_transaction_escrowed": invalid_or_missing_escrowed,
        }
        row["coverage_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _checks(
    *,
    receipt_input: dict[str, Any],
    policy: dict[str, bool],
    artifact_bindings: dict[str, Any],
    transaction_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    direct_rows = [row for row in coverage_rows if row["direct_settlement"]]
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "direct_sources_have_license_transactions": (
            not policy["require_license_server_transaction_for_direct_sources"]
            or all(row["matching_transaction_count"] > 0 for row in direct_rows)
        ),
        "license_transactions_accepted": all(
            row["transaction_accepted"] for row in direct_rows
        ),
        "license_server_signatures_valid": (
            not policy["require_license_server_signature"]
            or all(row["token_signature_valid"] for row in direct_rows)
        ),
        "license_transactions_ledger_included": (
            not policy["require_license_ledger_inclusion"]
            or all(row["license_ledger_included"] for row in direct_rows)
        ),
        "license_transaction_terms_match_protocol": (
            not policy["require_transaction_terms_match_protocol"]
            or all(row["transaction_terms_match_protocol"] for row in direct_rows)
        ),
        "license_transactions_bind_access_logs": (
            not policy["require_transaction_binds_access_log"]
            or all(row["transaction_binds_access_log"] for row in direct_rows)
        ),
        "license_transactions_valid_before_access": (
            not policy["require_transaction_before_access"]
            or all(row["transaction_valid_before_access"] for row in direct_rows)
        ),
        "citation_reliance_receipt_covers_direct_sources": (
            not policy["require_reliance_receipt_for_direct_sources"]
            or all(row["citation_reliance_covered"] for row in direct_rows)
        ),
        "no_direct_settlement_without_license_transaction": all(
            row["covered_for_license_transaction"] for row in direct_rows
        ),
        "invalid_or_missing_transactions_escrowed": (
            not policy["require_invalid_or_missing_transaction_escrowed"]
            or all(
                row["direct_settlement"]
                or row["covered_for_license_transaction"]
                or row["invalid_or_missing_transaction_escrowed"]
                for row in coverage_rows
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(
                {
                    "transaction_rows": transaction_rows,
                    "coverage_rows": coverage_rows,
                }
            )
            and _private_strings_absent(
                {
                    "transaction_rows": transaction_rows,
                    "coverage_rows": coverage_rows,
                },
                receipt_input,
            )
        ),
        "direct_source_count_positive": bool(direct_rows),
    }


def make_license_transaction_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable license transaction receipt."""

    policy = _policy(receipt_input)
    source_access_lease_report = receipt_input.get("source_access_lease_report", {})
    content_protocol_ingestion_report = receipt_input.get(
        "content_protocol_ingestion_report", {}
    )
    citation_reliance_receipt = receipt_input.get("citation_reliance_receipt", {})
    usage_rows = _source_usage_rows(source_access_lease_report)
    transaction_rows = _transaction_rows(receipt_input)
    artifact_bindings = _artifact_bindings(receipt_input)
    coverage_rows = _coverage_rows(
        usage_rows=usage_rows,
        transaction_rows=transaction_rows,
        source_access_lease_report=source_access_lease_report,
        content_protocol_ingestion_report=content_protocol_ingestion_report,
        citation_reliance_receipt=citation_reliance_receipt,
    )
    checks = _checks(
        receipt_input=receipt_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        transaction_rows=transaction_rows,
        coverage_rows=coverage_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    receipt = {
        "version": LICENSE_TRANSACTION_RECEIPT_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get("case_id", "case:license-transaction-receipt")
            ),
            "status": status,
        },
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "source_usage_rows": usage_rows,
        "transaction_rows": transaction_rows,
        "coverage_rows": coverage_rows,
        "checks": checks,
        "privacy": {
            "prompt_disclosed": False,
            "output_disclosed": False,
            "source_text_disclosed": False,
            "raw_license_token_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_license_transactions": True,
        },
        "schemas": {
            "license_transaction_receipt": LICENSE_TRANSACTION_RECEIPT_SCHEMA,
            "source_access_lease_report": "docs/schemas/source_access_lease_report.schema.json",
            "content_protocol_ingestion_report": "docs/schemas/content_protocol_ingestion_report.schema.json",
            "citation_reliance_receipt": "docs/schemas/citation_reliance_receipt.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_usage_count": len(usage_rows),
            "direct_source_usage_count": sum(1 for row in usage_rows if row["direct_settlement"]),
            "license_transaction_count": len(transaction_rows),
            "coverage_row_count": len(coverage_rows),
            "covered_direct_source_count": sum(
                1 for row in coverage_rows if row["covered_for_license_transaction"]
            ),
            "escrowed_invalid_or_missing_transaction_count": sum(
                1 for row in coverage_rows if row["invalid_or_missing_transaction_escrowed"]
            ),
            "failed_check_count": len(failed),
            "license_server_transaction_supported": True,
            "license_ledger_inclusion_supported": checks[
                "license_transactions_ledger_included"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    receipt["license_transaction_receipt_hash"] = hash_payload(_hashable_report(receipt))
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_license_transaction_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "policy",
        "artifact_bindings",
        "source_usage_rows",
        "transaction_rows",
        "coverage_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "license_transaction_receipt_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing license transaction receipt field: {key}")
    if receipt.get("version") != LICENSE_TRANSACTION_RECEIPT_VERSION:
        errors.append("license transaction receipt version is unsupported")
    if "license_transaction_receipt" not in receipt.get("schemas", {}):
        errors.append("missing license transaction receipt schema")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("license transaction receipt target level is not RDLLM-L101")
    for index, row in enumerate(receipt.get("coverage_rows", [])):
        for key in (
            "source_usage_id",
            "matching_transaction_count",
            "transaction_accepted",
            "token_signature_valid",
            "license_ledger_included",
            "transaction_terms_match_protocol",
            "transaction_binds_access_log",
            "transaction_valid_before_access",
            "covered_for_license_transaction",
            "coverage_row_hash",
        ):
            if key not in row:
                errors.append(f"license transaction coverage row {index} missing {key}")
    return errors


def verify_license_transaction_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a license transaction receipt by replaying private inputs."""

    errors = validate_license_transaction_receipt_shape(receipt)
    expected = make_license_transaction_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    if receipt.get("license_transaction_receipt_hash") != expected.get(
        "license_transaction_receipt_hash"
    ):
        errors.append("license transaction receipt hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("license transaction receipt signature mismatch")
    if receipt.get("checks") != expected.get("checks"):
        errors.append("license transaction receipt checks mismatch")
    if receipt.get("summary") != expected.get("summary"):
        errors.append("license transaction receipt summary mismatch")
    if receipt.get("transaction_rows") != expected.get("transaction_rows"):
        errors.append("license transaction receipt transaction rows mismatch")
    if receipt.get("coverage_rows") != expected.get("coverage_rows"):
        errors.append("license transaction receipt coverage rows mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("license transaction receipt has failing checks")
    return errors
