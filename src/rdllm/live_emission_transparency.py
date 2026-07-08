"""Transparency inclusion for live emission witness reports."""

from __future__ import annotations

from typing import Any

from rdllm.live_emission_witness import validate_live_emission_witness_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

LIVE_EMISSION_TRANSPARENCY_VERSION = "rdllm-live-emission-transparency/v1"
LIVE_EMISSION_TRANSPARENCY_LOG_VERSION = "rdllm-live-emission-transparency-log/v1"
LIVE_EMISSION_TRANSPARENCY_SCHEMA = (
    "docs/schemas/live_emission_transparency.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L85"
MINIMUM_INPUT_LEVEL = "RDLLM-L84"

DECLARED_HASH_FIELDS = (
    "live_emission_transparency_hash",
    "live_witness_hash",
    "report_hash",
    "streaming_manifest_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "contract_hash",
    "envelope_hash",
    "card_hash",
    "bundle_hash",
    "manifest_hash",
    "profile_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
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


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"live_emission_transparency_hash", "signature"}
    }


def _hashable_log_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "entry_hash"}


def _hashable_subject(subject: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in subject.items()
        if key not in {"subject_payload_hash", "subject_row_hash"}
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


def _subject_with_hashes(subject: dict[str, Any]) -> dict[str, Any]:
    row = dict(subject)
    row["subject_payload_hash"] = hash_payload(_hashable_subject(row))
    row["subject_row_hash"] = hash_payload(_hashable_subject(row))
    return row


def _live_subject_rows(live_emission_witness: dict[str, Any]) -> list[dict[str, Any]]:
    live_witness_hash = _declared_hash(live_emission_witness)
    attestations = list(live_emission_witness.get("witness_attestations", []))
    chunk_rows = list(live_emission_witness.get("chunk_subject_rows", []))
    report_subject = _subject_with_hashes(
        {
            "subject_type": "rdllm-live-emission-witness-report/v1",
            "subject_hash": live_witness_hash,
            "live_witness_hash": live_witness_hash,
            "witness_version": live_emission_witness.get("witness_version", ""),
            "target_certification_level": live_emission_witness.get("summary", {}).get(
                "target_certification_level", ""
            ),
            "minimum_input_level": live_emission_witness.get("summary", {}).get(
                "minimum_input_level", ""
            ),
            "preflight_subject_hash": live_emission_witness.get(
                "preflight_subject", {}
            ).get("subject_hash", ""),
            "completion_subject_hash": live_emission_witness.get(
                "completion_subject", {}
            ).get("subject_hash", ""),
            "witness_attestation_root": merkle_root(
                [str(row.get("attestation_hash", "")) for row in attestations]
            ),
            "chunk_subject_root": merkle_root(
                [str(row.get("chunk_subject_hash", "")) for row in chunk_rows]
            ),
        }
    )
    rows = [report_subject]
    for attestation in attestations:
        rows.append(
            _subject_with_hashes(
                {
                    "subject_type": "rdllm-live-emission-witness-attestation/v1",
                    "subject_hash": str(attestation.get("attestation_hash", "")),
                    "live_witness_hash": live_witness_hash,
                    "phase": str(attestation.get("phase", "")),
                    "witness_id": str(attestation.get("witness_id", "")),
                    "organization_id": str(attestation.get("organization_id", "")),
                    "witness_key_hash": str(attestation.get("witness_key_hash", "")),
                    "observed_at": str(attestation.get("observed_at", "")),
                    "preflight_or_completion_subject_hash": str(
                        attestation.get("subject_hash", "")
                    ),
                    "replay_verdict": str(attestation.get("replay_verdict", "")),
                    "signature_algorithm": str(
                        attestation.get("signature_algorithm", "")
                    ),
                }
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            row["subject_type"],
            row.get("phase", ""),
            row.get("witness_id", ""),
            row["subject_hash"],
        ),
    )


def make_live_emission_transparency_log(
    live_emission_witness: dict[str, Any],
    *,
    log_id: str = "live-emission-transparency",
    existing_entries: list[dict[str, Any]] | None = None,
    include_attestations: bool = True,
) -> dict[str, Any]:
    """Create an append-only log containing live witness report and attestation subjects."""

    entries = [dict(entry) for entry in existing_entries or []]
    subjects = _live_subject_rows(live_emission_witness)
    if not include_attestations:
        subjects = [
            subject
            for subject in subjects
            if subject["subject_type"] == "rdllm-live-emission-witness-report/v1"
        ]
    existing_subject_hashes = {
        str(entry.get("subject_hash", "")) for entry in entries if entry.get("subject_hash")
    }
    subjects = [
        subject for subject in subjects if subject["subject_hash"] not in existing_subject_hashes
    ]
    start_index = len(entries)
    for offset, subject in enumerate(subjects):
        entry = {
            "index": start_index + offset,
            "log_id": log_id,
            "entry_type": subject["subject_type"],
            "subject_hash": subject["subject_hash"],
            "subject_payload_hash": subject["subject_payload_hash"],
            "live_witness_hash": subject["live_witness_hash"],
            "phase": subject.get("phase", ""),
            "witness_id": subject.get("witness_id", ""),
        }
        entry["entry_hash"] = hash_payload(_hashable_log_entry(entry))
        entries.append(entry)
    leaves = [str(entry.get("entry_hash", "")) for entry in entries]
    return {
        "log_version": LIVE_EMISSION_TRANSPARENCY_LOG_VERSION,
        "log_id": log_id,
        "tree_size": len(entries),
        "root": merkle_root(leaves),
        "entries": entries,
    }


def _entry_rows(log_id: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        row = {
            "log_id": log_id,
            "entry_index": int(entry.get("index", index) or 0),
            "entry_type": str(entry.get("entry_type", "")),
            "subject_hash": str(entry.get("subject_hash", "")),
            "subject_payload_hash": str(entry.get("subject_payload_hash", "")),
            "entry_hash": str(entry.get("entry_hash", "")),
            "entry_index_matches_position": entry.get("index") == index,
            "entry_hash_reproducible": hash_payload(_hashable_log_entry(entry))
            == entry.get("entry_hash"),
            "entry_has_required_hashes": all(
                bool(entry.get(field))
                for field in (
                    "entry_type",
                    "subject_hash",
                    "subject_payload_hash",
                    "entry_hash",
                )
            ),
        }
        row["entry_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _snapshot_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        entry_rows = _entry_rows(log_id, entries)
        leaves = [str(entry.get("entry_hash", "")) for entry in entries]
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
            "entry_hashes_reproducible": all(
                row["entry_hash_reproducible"] for row in entry_rows
            ),
            "entries_have_required_hashes": all(
                row["entry_has_required_hashes"] for row in entry_rows
            ),
            "entry_count": len(entry_rows),
            "entry_root": merkle_root([row["entry_row_hash"] for row in entry_rows]),
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
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        by_size.setdefault(len(entries), []).append((log_id, log))
        seen: dict[str, list[int]] = {}
        for index, entry in enumerate(entries):
            subject_hash = str(entry.get("subject_hash", ""))
            if subject_hash:
                seen.setdefault(subject_hash, []).append(index)
        for subject_hash, indexes in seen.items():
            if len(indexes) > 1:
                row = {
                    "conflict_type": "subject_hash_repeated_in_log",
                    "log_id": log_id,
                    "subject_hash": subject_hash,
                    "entry_indexes": indexes,
                }
                row["conflict_hash"] = hash_payload(row)
                rows.append(row)
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


def _required_subject_rows(
    subjects: list[dict[str, Any]],
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    latest = _latest_log(transparency_logs)
    if latest is None:
        return []
    latest_id, latest_log = latest
    entries = list(latest_log.get("entries", []))
    leaves = [str(entry.get("entry_hash", "")) for entry in entries]
    by_subject = {
        str(entry.get("subject_hash", "")): (index, entry)
        for index, entry in enumerate(entries)
    }
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        subject_hash = str(subject.get("subject_hash", ""))
        match = by_subject.get(subject_hash)
        present = match is not None
        proof: dict[str, Any] | None = None
        entry_index = -1
        payload_hash_matches = False
        entry_type_matches = False
        if present and match is not None:
            entry_index, entry = match
            proof = inclusion_proof(leaves, entry_index)
            payload_hash_matches = (
                entry.get("subject_payload_hash") == subject.get("subject_payload_hash")
            )
            entry_type_matches = entry.get("entry_type") == subject.get("subject_type")
        row = {
            "subject_type": subject.get("subject_type", ""),
            "subject_hash": subject_hash,
            "subject_payload_hash": subject.get("subject_payload_hash", ""),
            "latest_log_id": latest_id,
            "latest_tree_size": len(entries),
            "present": present,
            "entry_index": entry_index,
            "entry_type_matches": entry_type_matches,
            "payload_hash_matches": payload_hash_matches,
            "inclusion_proof": proof or {},
            "inclusion_proof_valid": bool(proof) and verify_inclusion(proof),
        }
        row["required_subject_row_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "inclusion_proof"}
        )
        rows.append(row)
    return rows


def make_live_emission_transparency_report(
    *,
    live_emission_witness: dict[str, Any],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L85 report proving live witness artifacts are log-included."""

    timestamp = created_at or now_iso()
    subjects = _live_subject_rows(live_emission_witness)
    snapshots = _snapshot_rows(transparency_logs)
    append_only = _append_only_rows(transparency_logs)
    split_views = _split_view_rows(transparency_logs)
    required_subjects = _required_subject_rows(subjects, transparency_logs)
    live_shape_errors = validate_live_emission_witness_shape(live_emission_witness)
    public_fields = {
        "subjects": subjects,
        "snapshots": snapshots,
        "append_only": append_only,
        "split_views": split_views,
        "required_subjects": [
            {key: value for key, value in row.items() if key != "inclusion_proof"}
            for row in required_subjects
        ],
    }
    private_fields = _contains_private_fields(public_fields)
    checks = {
        "live_emission_witness_shape_valid": not live_shape_errors,
        "live_emission_witness_hash_reproducible": _artifact_hash_is_reproducible(
            live_emission_witness
        ),
        "live_emission_witness_ready": live_emission_witness.get("summary", {}).get(
            "status"
        )
        == "ready",
        "live_emission_witness_target_l84": live_emission_witness.get(
            "summary", {}
        ).get("target_certification_level")
        == MINIMUM_INPUT_LEVEL,
        "required_subjects_declared": bool(subjects),
        "transparency_logs_present": bool(transparency_logs),
        "transparency_log_versions_supported": all(
            row["log_version"] == LIVE_EMISSION_TRANSPARENCY_LOG_VERSION
            for row in snapshots
        ),
        "transparency_tree_sizes_match": all(
            row["tree_size_matches_entries"] for row in snapshots
        ),
        "transparency_roots_reproducible": all(
            row["root_matches_entries"] for row in snapshots
        ),
        "transparency_entries_sequential": all(
            row["entries_are_sequential"] for row in snapshots
        ),
        "transparency_entry_hashes_reproducible": all(
            row["entry_hashes_reproducible"] for row in snapshots
        ),
        "transparency_entries_have_required_hashes": all(
            row["entries_have_required_hashes"] for row in snapshots
        ),
        "append_only_prefix_consistency": all(
            row["prefix_consistent"] for row in append_only
        ),
        "split_view_absent": not split_views,
        "required_subjects_in_latest_log": bool(required_subjects)
        and all(row["present"] for row in required_subjects),
        "required_subject_inclusion_proofs_valid": bool(required_subjects)
        and all(row["inclusion_proof_valid"] for row in required_subjects),
        "required_subject_payload_hashes_match": bool(required_subjects)
        and all(row["payload_hash_matches"] for row in required_subjects),
        "required_subject_entry_types_match": bool(required_subjects)
        and all(row["entry_type_matches"] for row in required_subjects),
        "public_report_has_no_private_field_names": not private_fields,
    }
    ready = all(checks.values())
    report = {
        "report_version": LIVE_EMISSION_TRANSPARENCY_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-live-emission-transparency-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "requires_live_witness_report_inclusion": True,
            "requires_witness_attestation_inclusion": True,
            "requires_append_only_consistency": True,
            "requires_split_view_absence": True,
        },
        "artifact_bindings": {
            "live_emission_witness_hash": _declared_hash(live_emission_witness),
            "live_emission_witness_payload_hash": hash_payload(
                live_emission_witness
            ),
            "live_emission_witness_hash_reproducible": _artifact_hash_is_reproducible(
                live_emission_witness
            ),
        },
        "transparency_log_bindings": [
            {
                "log_id": log_id,
                "payload_hash": hash_payload(log),
                "declared_root": str(log.get("root", "")),
                "tree_size": int(log.get("tree_size", 0) or 0),
                "entry_count": len(log.get("entries", [])),
            }
            for log_id, log in transparency_logs
        ],
        "live_subject_rows": subjects,
        "log_snapshot_rows": snapshots,
        "append_only_consistency_rows": append_only,
        "split_view_conflict_rows": split_views,
        "required_subject_rows": required_subjects,
        "checks": checks,
        "commitments": {
            "live_subject_root": merkle_root(
                [row["subject_row_hash"] for row in subjects]
            ),
            "log_snapshot_root": merkle_root(
                [row["snapshot_hash"] for row in snapshots]
            ),
            "append_only_consistency_root": merkle_root(
                [row["consistency_hash"] for row in append_only]
            ),
            "split_view_conflict_root": merkle_root(
                [row["conflict_hash"] for row in split_views]
            ),
            "required_subject_root": merkle_root(
                [row["required_subject_row_hash"] for row in required_subjects]
            ),
        },
        "schemas": {
            "live_emission_transparency": LIVE_EMISSION_TRANSPARENCY_SCHEMA,
            "live_emission_witness": "docs/schemas/live_emission_witness.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "live_emission_transparency_included": ready,
            "live_subject_count": len(subjects),
            "required_subject_count": len(required_subjects),
            "missing_subject_count": len(
                [row for row in required_subjects if not row["present"]]
            ),
            "transparency_log_count": len(transparency_logs),
            "latest_tree_size": max(
                [row["computed_tree_size"] for row in snapshots], default=0
            ),
            "append_only_violation_count": len(
                [
                    row
                    for row in append_only
                    if row["decision"] == "append_only_violation"
                ]
            ),
            "split_view_conflict_count": len(split_views),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "context_text_disclosed": False,
            "prompt_text_disclosed": False,
            "claim_text_disclosed": False,
            "stream_chunk_text_disclosed": False,
            "stores_hashes_log_roots_inclusion_proofs_and_counts_not_text": True,
        },
    }
    for binding in report["transparency_log_bindings"]:
        binding["binding_hash"] = hash_payload(binding)
    report["commitments"]["transparency_log_binding_root"] = merkle_root(
        [row["binding_hash"] for row in report["transparency_log_bindings"]]
    )
    report["live_emission_transparency_hash"] = hash_payload(_hashable_report(report))
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


def validate_live_emission_transparency_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "live_subject_rows",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "split_view_conflict_rows",
        "required_subject_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "live_emission_transparency_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing live emission transparency field: {key}")
    if errors:
        return errors
    if report.get("report_version") != LIVE_EMISSION_TRANSPARENCY_VERSION:
        errors.append("live emission transparency version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("live emission transparency target certification level is unsupported")
    if "live_emission_transparency" not in report.get("schemas", {}):
        errors.append("missing live emission transparency schema")
    return errors


def verify_live_emission_transparency_report(
    report: dict[str, Any],
    *,
    live_emission_witness: dict[str, Any],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify live witness transparency inclusion against logs and L84 input."""

    errors = validate_live_emission_transparency_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "live_emission_transparency_hash"
    ):
        errors.append("live emission transparency hash is not reproducible")
    expected = make_live_emission_transparency_report(
        live_emission_witness=live_emission_witness,
        transparency_logs=transparency_logs,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "live_subject_rows",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "split_view_conflict_rows",
        "required_subject_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"live emission transparency {key} does not match inputs")
    if expected.get("live_emission_transparency_hash") != report.get(
        "live_emission_transparency_hash"
    ):
        errors.append("live emission transparency hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("live emission transparency status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"live emission transparency check failed: {check}")
    report_json = canonical_json(report)
    for private_key in ('"chunk_text":', '"prompt":', '"raw_model_output":'):
        if private_key in report_json:
            errors.append(
                f"live emission transparency discloses private field {private_key}"
            )
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("live emission transparency report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("live emission transparency report signature is invalid")
    return errors
