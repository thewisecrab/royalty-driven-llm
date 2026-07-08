"""Receipt transparency-log consistency checks for settlement gating."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

RECEIPT_TRANSPARENCY_CONSISTENCY_VERSION = (
    "rdllm-receipt-transparency-consistency-report/v1"
)
RECEIPT_TRANSPARENCY_CONSISTENCY_SCHEMA = (
    "docs/schemas/receipt_transparency_consistency_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L73"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "attestation_hash",
    "graph_hash",
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


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
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
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
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


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _entry_rows(log_id: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        row = {
            "log_id": log_id,
            "entry_index": int(entry.get("index", index)),
            "receipt_hash": str(entry.get("receipt_hash", "")),
            "payload_hash": str(entry.get("payload_hash", "")),
            "receipt_envelope_hash": str(entry.get("receipt_envelope_hash", "")),
            "entry_index_matches_position": entry.get("index") == index,
            "entry_has_required_hashes": all(
                bool(entry.get(field))
                for field in (
                    "receipt_hash",
                    "payload_hash",
                    "receipt_envelope_hash",
                )
            ),
        }
        row["entry_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _snapshot_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        leaves = [str(entry.get("receipt_hash", "")) for entry in entries]
        entry_rows = _entry_rows(log_id, entries)
        computed_root = merkle_root(leaves)
        declared_root = str(log.get("root", ""))
        row = {
            "log_id": log_id,
            "log_version": str(log.get("log_version", "")),
            "declared_tree_size": int(log.get("tree_size", 0) or 0),
            "computed_tree_size": len(entries),
            "declared_root": declared_root,
            "computed_root": computed_root,
            "tree_size_matches_entries": int(log.get("tree_size", 0) or 0)
            == len(entries),
            "root_matches_entries": declared_root == computed_root,
            "entries_are_sequential": all(
                entry.get("index") == index for index, entry in enumerate(entries)
            ),
            "entries_have_required_hashes": all(
                row["entry_has_required_hashes"] for row in entry_rows
            ),
            "entry_count": len(entry_rows),
            "entry_root": merkle_root([row["entry_hash"] for row in entry_rows]),
        }
        row["snapshot_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda item: (item["computed_tree_size"], item["log_id"]))


def _append_only_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    indexed = sorted(
        [
            (
                log_id,
                [dict(entry) for entry in log.get("entries", [])],
                str(log.get("root", "")),
            )
            for log_id, log in transparency_logs
        ],
        key=lambda item: (len(item[1]), item[0]),
    )
    rows: list[dict[str, Any]] = []
    for previous_index, (prev_id, previous_entries, previous_root) in enumerate(indexed):
        for curr_id, current_entries, current_root in indexed[previous_index + 1 :]:
            if len(previous_entries) > len(current_entries):
                continue
            prefix_consistent = current_entries[: len(previous_entries)] == previous_entries
            row = {
                "previous_log_id": prev_id,
                "current_log_id": curr_id,
                "previous_tree_size": len(previous_entries),
                "current_tree_size": len(current_entries),
                "previous_root": previous_root,
                "current_root": current_root,
                "prefix_consistent": prefix_consistent,
                "decision": "consistent_prefix"
                if prefix_consistent
                else "append_only_violation",
            }
            row["consistency_hash"] = hash_payload(row)
            rows.append(row)
    return rows


def _split_view_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_size: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    receipt_positions: dict[str, dict[int, list[str]]] = {}
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        tree_size = len(entries)
        by_size.setdefault(tree_size, []).append((log_id, log))
        for index, entry in enumerate(entries):
            receipt_hash = str(entry.get("receipt_hash", ""))
            if receipt_hash:
                receipt_positions.setdefault(receipt_hash, {}).setdefault(index, []).append(
                    log_id
                )
    for tree_size, logs in by_size.items():
        roots = {str(log.get("root", "")) for _, log in logs}
        if len(roots) > 1:
            row = {
                "conflict_type": "same_tree_size_different_roots",
                "tree_size": tree_size,
                "log_ids": sorted(log_id for log_id, _ in logs),
                "roots": sorted(roots),
            }
            row["conflict_hash"] = hash_payload(row)
            rows.append(row)
    for receipt_hash, positions in receipt_positions.items():
        if len(positions) > 1:
            row = {
                "conflict_type": "receipt_hash_at_multiple_indexes",
                "receipt_hash": receipt_hash,
                "positions": [
                    {"entry_index": index, "log_ids": sorted(log_ids)}
                    for index, log_ids in sorted(positions.items())
                ],
            }
            row["conflict_hash"] = hash_payload(row)
            rows.append(row)
    return sorted(rows, key=lambda item: item["conflict_hash"])


def _latest_log(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, Any]] | None:
    if not transparency_logs:
        return None
    return max(
        transparency_logs,
        key=lambda item: (len(item[1].get("entries", [])), item[0]),
    )


def _receipt_hash(receipt: dict[str, Any]) -> str:
    value = receipt.get("receipt_hash")
    if isinstance(value, str) and value:
        return value
    payload = receipt.get("payload")
    if isinstance(payload, dict):
        return hash_payload(payload)
    return hash_payload(receipt)


def _receipt_rows(
    receipts: list[dict[str, Any]],
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    latest = _latest_log(transparency_logs)
    if latest is None:
        return []
    latest_id, latest_log = latest
    entries = list(latest_log.get("entries", []))
    leaves = [str(entry.get("receipt_hash", "")) for entry in entries]
    by_hash = {
        str(entry.get("receipt_hash", "")): (index, entry)
        for index, entry in enumerate(entries)
    }
    rows: list[dict[str, Any]] = []
    for receipt in receipts:
        receipt_hash = _receipt_hash(receipt)
        match = by_hash.get(receipt_hash)
        present = match is not None
        proof: dict[str, Any] | None = None
        payload_hash_matches = True
        envelope_hash_matches = True
        entry_index = -1
        if present and match is not None:
            entry_index, entry = match
            proof = inclusion_proof(leaves, entry_index)
            if isinstance(receipt.get("payload"), dict):
                payload_hash_matches = (
                    hash_payload(receipt["payload"]) == entry.get("payload_hash")
                )
                envelope_hash_matches = (
                    stable_hash(canonical_json(receipt))
                    == entry.get("receipt_envelope_hash")
                )
        row = {
            "receipt_hash": receipt_hash,
            "latest_log_id": latest_id,
            "latest_tree_size": len(entries),
            "present": present,
            "entry_index": entry_index,
            "payload_hash_matches": payload_hash_matches,
            "receipt_envelope_hash_matches": envelope_hash_matches,
            "inclusion_proof": proof or {},
            "inclusion_proof_valid": bool(proof) and verify_inclusion(proof),
        }
        row["receipt_row_hash"] = hash_payload(
            {
                key: value
                for key, value in row.items()
                if key != "inclusion_proof"
            }
        )
        rows.append(row)
    return rows


def _settlement_rows(
    verifier_accountability_report: dict[str, Any],
    *,
    direct_settlement_ready: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in verifier_accountability_report.get("settlement_rows", []):
        payout = Decimal(str(source.get("payout", "0") or "0"))
        escrow = Decimal(str(source.get("escrow_amount", "0") or "0"))
        amount = payout + escrow
        row = {
            "creator_id": str(source.get("creator_id", "")),
            "work_id": str(source.get("work_id", "")),
            "contribution_weight": float(source.get("contribution_weight", 0.0) or 0.0),
            "prior_settlement_decision": str(source.get("settlement_decision", "")),
            "payout": _money(amount if direct_settlement_ready else Decimal("0")),
            "escrow_amount": _money(Decimal("0") if direct_settlement_ready else amount),
            "settlement_decision": "accepted"
            if direct_settlement_ready
            else "receipt_transparency_consistency_escrow",
        }
        row["settlement_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_receipt_transparency_consistency_report(
    *,
    transparency_logs: list[tuple[str, dict[str, Any]]],
    receipts: list[dict[str, Any]],
    verifier_accountability_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a receipt-log consistency report that gates direct settlement."""

    timestamp = created_at or now_iso()
    snapshots = _snapshot_rows(transparency_logs)
    append_only = _append_only_rows(transparency_logs)
    split_views = _split_view_rows(transparency_logs)
    required_receipts = _receipt_rows(receipts, transparency_logs)
    artifact_bindings = [
        _artifact_binding(
            "verifier_accountability_report",
            "rdllm-verifier-accountability-report/v1",
            verifier_accountability_report,
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
    transparency_bindings = [
        {
            "log_id": log_id,
            "payload_hash": hash_payload(log),
            "declared_root": str(log.get("root", "")),
            "tree_size": int(log.get("tree_size", 0) or 0),
            "entry_count": len(log.get("entries", [])),
        }
        for log_id, log in transparency_logs
    ]
    for binding in transparency_bindings:
        binding["binding_hash"] = hash_payload(binding)
    public_fields = {
        "snapshots": snapshots,
        "append_only": append_only,
        "split_views": split_views,
        "required_receipts": [
            {key: value for key, value in row.items() if key != "inclusion_proof"}
            for row in required_receipts
        ],
        "artifact_bindings": artifact_bindings,
        "transparency_bindings": transparency_bindings,
    }
    private_fields = _contains_private_fields(public_fields)
    checks = {
        "transparency_snapshots_present": bool(snapshots),
        "transparency_tree_sizes_match": all(
            row["tree_size_matches_entries"] for row in snapshots
        ),
        "transparency_log_roots_reproducible": all(
            row["root_matches_entries"] for row in snapshots
        ),
        "transparency_log_entries_sequential": all(
            row["entries_are_sequential"] for row in snapshots
        ),
        "transparency_log_entries_have_required_hashes": all(
            row["entries_have_required_hashes"] for row in snapshots
        ),
        "append_only_prefix_consistency": all(
            row["prefix_consistent"] for row in append_only
        ),
        "split_view_absent": not split_views,
        "required_receipts_declared": bool(required_receipts),
        "required_receipts_in_latest_snapshot": all(
            row["present"] for row in required_receipts
        ),
        "required_receipt_inclusion_proofs_valid": all(
            row["inclusion_proof_valid"] for row in required_receipts
        ),
        "receipt_payload_hashes_match_log_entries": all(
            row["payload_hash_matches"] for row in required_receipts
        ),
        "receipt_envelope_hashes_match_log_entries": all(
            row["receipt_envelope_hash_matches"] for row in required_receipts
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings
        ),
        "verifier_accountability_ready": verifier_accountability_report.get(
            "summary", {}
        ).get("status")
        == "ready",
        "verifier_accountability_target_l72": verifier_accountability_report.get(
            "summary", {}
        ).get("target_certification_level")
        == "RDLLM-L72",
        "provider_declares_receipt_transparency_consistency_surface": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("receipt_transparency_consistency_report")
        is True,
        "provider_declares_receipt_transparency_consistency_channel": provider_card.get(
            "supported_evidence_channels", {}
        ).get("receipt_transparency_consistency")
        is True,
        "certification_level_at_least_l72": _level_number(
            str(certification_report.get("summary", {}).get("highest_level", ""))
        )
        >= 72,
        "public_report_has_no_private_field_names": not private_fields,
    }
    direct_settlement_ready = all(checks.values())
    settlement_rows = _settlement_rows(
        verifier_accountability_report,
        direct_settlement_ready=direct_settlement_ready,
    )
    payout_total = sum(
        Decimal(str(row.get("payout", "0") or "0")) for row in settlement_rows
    )
    escrow_total = sum(
        Decimal(str(row.get("escrow_amount", "0") or "0")) for row in settlement_rows
    )
    creator_pool = payout_total + escrow_total
    checks["creator_pool_conserved_or_escrowed"] = creator_pool == sum(
        Decimal(str(row.get("payout", "0") or "0"))
        + Decimal(str(row.get("escrow_amount", "0") or "0"))
        for row in verifier_accountability_report.get("settlement_rows", [])
    )
    direct_settlement_ready = all(checks.values())
    if not direct_settlement_ready:
        settlement_rows = _settlement_rows(
            verifier_accountability_report,
            direct_settlement_ready=False,
        )
        payout_total = Decimal("0")
        escrow_total = sum(
            Decimal(str(row.get("escrow_amount", "0") or "0"))
            for row in settlement_rows
        )
    report = {
        "report_version": RECEIPT_TRANSPARENCY_CONSISTENCY_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-receipt-transparency-consistency-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "direct_settlement_requires": [
                "append_only_receipt_log_snapshots",
                "no_split_view_roots",
                "required_receipt_inclusion_proofs",
                "receipt_payload_and_envelope_hash_match",
                "ready_bonded_verifier_accountability_report",
            ],
            "failure_route": "receipt_transparency_consistency_escrow",
        },
        "artifact_bindings": {
            "artifact_count": len(artifact_bindings),
            "bindings": artifact_bindings,
            "artifact_binding_root": merkle_root(
                [row["binding_hash"] for row in artifact_bindings]
            ),
            "transparency_log_binding_root": merkle_root(
                [row["binding_hash"] for row in transparency_bindings]
            ),
            "verifier_accountability_report_hash": artifact_bindings[0][
                "declared_hash"
            ],
            "provider_card_hash": artifact_bindings[1]["declared_hash"],
            "certification_report_hash": artifact_bindings[2]["declared_hash"],
        },
        "transparency_log_bindings": transparency_bindings,
        "log_snapshot_rows": snapshots,
        "append_only_consistency_rows": append_only,
        "split_view_conflict_rows": split_views,
        "required_receipt_rows": required_receipts,
        "settlement_gate": {
            "decision": "receipt_transparency_consistency_ready"
            if direct_settlement_ready
            else "receipt_transparency_consistency_escrow",
            "direct_settlement_ready": direct_settlement_ready,
            "split_view_conflict_count": len(split_views),
            "append_only_violation_count": len(
                [
                    row
                    for row in append_only
                    if row["decision"] == "append_only_violation"
                ]
            ),
            "missing_receipt_count": len(
                [row for row in required_receipts if not row["present"]]
            ),
        },
        "settlement_rows": settlement_rows,
        "commitments": {
            "log_snapshot_root": merkle_root(
                [row["snapshot_hash"] for row in snapshots]
            ),
            "append_only_consistency_root": merkle_root(
                [row["consistency_hash"] for row in append_only]
            ),
            "split_view_conflict_root": merkle_root(
                [row["conflict_hash"] for row in split_views]
            ),
            "required_receipt_root": merkle_root(
                [row["receipt_row_hash"] for row in required_receipts]
            ),
            "settlement_row_root": merkle_root(
                [row["settlement_row_hash"] for row in settlement_rows]
            ),
        },
        "checks": checks,
        "schemas": {
            "receipt_transparency_consistency_report": RECEIPT_TRANSPARENCY_CONSISTENCY_SCHEMA,
            "verifier_accountability_report": "docs/schemas/verifier_accountability_report.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "ready" if direct_settlement_ready else "escrow",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "transparency_snapshot_count": len(snapshots),
            "latest_tree_size": max(
                [row["computed_tree_size"] for row in snapshots], default=0
            ),
            "required_receipt_count": len(required_receipts),
            "missing_receipt_count": len(
                [row for row in required_receipts if not row["present"]]
            ),
            "append_only_violation_count": len(
                [
                    row
                    for row in append_only
                    if row["decision"] == "append_only_violation"
                ]
            ),
            "split_view_conflict_count": len(split_views),
            "settlement_decision": "receipt_transparency_consistency_ready"
            if direct_settlement_ready
            else "receipt_transparency_consistency_escrow",
            "direct_settlement_ready": direct_settlement_ready,
            "settlement_row_count": len(settlement_rows),
            "payout_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
            "creator_pool_conserved_or_escrowed": checks[
                "creator_pool_conserved_or_escrowed"
            ],
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "receipt_payload_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "report_uses_hashes_roots_and_inclusion_proofs": True,
        },
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
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


def validate_receipt_transparency_consistency_report_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "split_view_conflict_rows",
        "required_receipt_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing receipt transparency consistency field: {key}")
    if errors:
        return errors
    if report.get("report_version") != RECEIPT_TRANSPARENCY_CONSISTENCY_VERSION:
        errors.append("receipt transparency consistency version is unsupported")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("receipt transparency consistency target level is invalid")
    for row in report.get("log_snapshot_rows", []):
        for key in (
            "log_id",
            "declared_tree_size",
            "computed_tree_size",
            "declared_root",
            "computed_root",
            "snapshot_hash",
        ):
            if key not in row:
                errors.append(f"missing receipt transparency snapshot field: {key}")
    for row in report.get("required_receipt_rows", []):
        for key in (
            "receipt_hash",
            "present",
            "inclusion_proof_valid",
            "receipt_row_hash",
        ):
            if key not in row:
                errors.append(f"missing receipt transparency receipt field: {key}")
    if "receipt_transparency_consistency_report" not in report.get("schemas", {}):
        errors.append("missing receipt transparency consistency schema")
    return errors


def verify_receipt_transparency_consistency_report(
    report: dict[str, Any],
    *,
    transparency_logs: list[tuple[str, dict[str, Any]]],
    receipts: list[dict[str, Any]],
    verifier_accountability_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a receipt transparency consistency report against public logs."""

    errors = validate_receipt_transparency_consistency_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("receipt transparency consistency hash is not reproducible")

    expected = make_receipt_transparency_consistency_report(
        transparency_logs=transparency_logs,
        receipts=receipts,
        verifier_accountability_report=verifier_accountability_report,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "split_view_conflict_rows",
        "required_receipt_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(
                f"receipt transparency consistency {key} does not match replay"
            )
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("receipt transparency consistency hash does not match replay")

    for row in report.get("required_receipt_rows", []):
        proof = row.get("inclusion_proof")
        if row.get("present") and (not isinstance(proof, dict) or not verify_inclusion(proof)):
            errors.append(
                f"receipt transparency inclusion proof invalid for {row.get('receipt_hash', '')}"
            )
    for check, passed in report.get("checks", {}).items():
        if passed is not True and report.get("summary", {}).get("status") == "ready":
            errors.append(f"receipt transparency consistency check failed: {check}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("receipt transparency consistency report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("receipt transparency consistency report signature is invalid")

    return errors
