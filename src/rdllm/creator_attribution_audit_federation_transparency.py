"""Transparency inclusion for cross-provider creator audit federations.

L111 answers a creator query across providers. L112 makes that answer
anti-equivocation evidence by requiring the federation result and participant
index hashes to appear in append-only transparency logs.
"""

from __future__ import annotations

from typing import Any

from rdllm.creator_attribution_audit_federation import (
    validate_creator_attribution_audit_federation_shape,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

CREATOR_AUDIT_FEDERATION_TRANSPARENCY_VERSION = (
    "rdllm-creator-attribution-audit-federation-transparency/v1"
)
CREATOR_AUDIT_FEDERATION_TRANSPARENCY_LOG_VERSION = (
    "rdllm-creator-attribution-audit-federation-transparency-log/v1"
)
CREATOR_AUDIT_FEDERATION_TRANSPARENCY_SCHEMA = (
    "docs/schemas/creator_attribution_audit_federation_transparency.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L112"
MINIMUM_INPUT_LEVEL = "RDLLM-L111"

DECLARED_HASH_FIELDS = (
    "creator_attribution_audit_federation_transparency_hash",
    "creator_attribution_audit_federation_hash",
    "creator_attribution_audit_index_hash",
    "handshake_hash",
    "exchange_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "receipt_hash",
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
    "quote",
    "notice_text",
    "license_text",
    "feedback_text",
    "critique_text",
    "reward_explanation_text",
    "verifier_rationale",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
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
        if key
        not in {
            "creator_attribution_audit_federation_transparency_hash",
            "signature",
        }
    }


def _hashable_log_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "entry_hash"}


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


def _provider_set_hash(federation_report: dict[str, Any]) -> str:
    provider_ids = sorted(
        str(row.get("provider_id", ""))
        for row in federation_report.get("participant_rows", [])
        if row.get("provider_id")
    )
    return hash_payload(provider_ids)


def _query_hash(federation_report: dict[str, Any]) -> str:
    return str(
        federation_report.get("case", {})
        .get("query_federation", {})
        .get("agreed_query_hash", "")
    )


def _subject_with_hash(row: dict[str, Any]) -> dict[str, Any]:
    subject = dict(row)
    subject["subject_payload_hash"] = hash_payload(
        {key: value for key, value in subject.items() if key != "subject_payload_hash"}
    )
    subject["subject_row_hash"] = hash_payload(subject)
    return subject


def _federation_subject_rows(
    federation_report: dict[str, Any],
) -> list[dict[str, Any]]:
    federation_hash = _declared_hash(federation_report)
    query_hash = _query_hash(federation_report)
    provider_set_hash = _provider_set_hash(federation_report)
    rows = [
        _subject_with_hash(
            {
                "subject_type": "rdllm-creator-attribution-audit-federation/v1",
                "subject_hash": federation_hash,
                "federation_hash": federation_hash,
                "query_hash": query_hash,
                "provider_set_hash": provider_set_hash,
                "provider_id": "",
                "participant_index_hash": "",
                "target_certification_level": str(
                    federation_report.get("summary", {}).get(
                        "target_certification_level", ""
                    )
                ),
                "participant_count": int(
                    federation_report.get("summary", {}).get("participant_count", 0)
                    or 0
                ),
                "provider_count": int(
                    federation_report.get("summary", {}).get("provider_count", 0) or 0
                ),
                "identity_conflict_count": int(
                    federation_report.get("summary", {}).get(
                        "identity_conflict_count", 0
                    )
                    or 0
                ),
                "participant_root": str(
                    federation_report.get("commitments", {}).get(
                        "participant_root", ""
                    )
                ),
                "federated_creator_work_root": str(
                    federation_report.get("commitments", {}).get(
                        "federated_creator_work_root", ""
                    )
                ),
            }
        )
    ]
    for participant in federation_report.get("participant_rows", []):
        index_hash = str(participant.get("creator_attribution_audit_index_hash", ""))
        rows.append(
            _subject_with_hash(
                {
                    "subject_type": "rdllm-creator-attribution-audit-index/v1",
                    "subject_hash": index_hash,
                    "federation_hash": federation_hash,
                    "query_hash": str(participant.get("query_hash", "")),
                    "provider_set_hash": provider_set_hash,
                    "provider_id": str(participant.get("provider_id", "")),
                    "participant_index_hash": index_hash,
                    "target_certification_level": str(
                        participant.get("index_target_level", "")
                    ),
                    "participant_count": 0,
                    "provider_count": 0,
                    "identity_conflict_count": 0,
                    "participant_root": "",
                    "federated_creator_work_root": "",
                }
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            row["subject_type"],
            row.get("provider_id", ""),
            row["subject_hash"],
        ),
    )


def make_creator_audit_federation_transparency_log(
    federation_report: dict[str, Any],
    *,
    log_id: str = "creator-audit-federation-transparency",
    existing_entries: list[dict[str, Any]] | None = None,
    include_participant_indexes: bool = True,
) -> dict[str, Any]:
    """Create an append-only log for an L111 creator audit federation."""

    entries = [dict(entry) for entry in existing_entries or []]
    subjects = _federation_subject_rows(federation_report)
    if not include_participant_indexes:
        subjects = [
            subject
            for subject in subjects
            if subject["subject_type"]
            == "rdllm-creator-attribution-audit-federation/v1"
        ]
    existing = {
        (str(entry.get("entry_type", "")), str(entry.get("subject_hash", "")))
        for entry in entries
    }
    subjects = [
        subject
        for subject in subjects
        if (subject["subject_type"], subject["subject_hash"]) not in existing
    ]
    start_index = len(entries)
    for offset, subject in enumerate(subjects):
        entry = {
            "index": start_index + offset,
            "log_id": log_id,
            "entry_type": subject["subject_type"],
            "subject_hash": subject["subject_hash"],
            "subject_payload_hash": subject["subject_payload_hash"],
            "federation_hash": subject["federation_hash"],
            "query_hash": subject["query_hash"],
            "provider_set_hash": subject["provider_set_hash"],
            "provider_id": subject.get("provider_id", ""),
            "participant_index_hash": subject.get("participant_index_hash", ""),
        }
        entry["entry_hash"] = hash_payload(_hashable_log_entry(entry))
        entries.append(entry)
    leaves = [str(entry.get("entry_hash", "")) for entry in entries]
    return {
        "log_version": CREATOR_AUDIT_FEDERATION_TRANSPARENCY_LOG_VERSION,
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
            "federation_hash": str(entry.get("federation_hash", "")),
            "query_hash": str(entry.get("query_hash", "")),
            "provider_set_hash": str(entry.get("provider_set_hash", "")),
            "provider_id": str(entry.get("provider_id", "")),
            "participant_index_hash": str(entry.get("participant_index_hash", "")),
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
                    "federation_hash",
                    "query_hash",
                    "provider_set_hash",
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
        row = {
            "log_id": log_id,
            "log_version": str(log.get("log_version", "")),
            "declared_tree_size": int(log.get("tree_size", 0) or 0),
            "computed_tree_size": len(entries),
            "declared_root": str(log.get("root", "")),
            "computed_root": merkle_root(leaves),
            "tree_size_matches_entries": int(log.get("tree_size", 0) or 0)
            == len(entries),
            "root_matches_entries": str(log.get("root", "")) == merkle_root(leaves),
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
    return sorted(rows, key=lambda row: (row["computed_tree_size"], row["log_id"]))


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
    federations_by_query: dict[tuple[str, str], set[str]] = {}
    indexes_by_provider_query: dict[tuple[str, str], set[str]] = {}
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        by_size.setdefault(len(entries), []).append((log_id, log))
        seen: dict[tuple[str, str], list[int]] = {}
        for index, entry in enumerate(entries):
            subject_key = (
                str(entry.get("entry_type", "")),
                str(entry.get("subject_hash", "")),
            )
            if subject_key[1]:
                seen.setdefault(subject_key, []).append(index)
            if entry.get("entry_type") == "rdllm-creator-attribution-audit-federation/v1":
                key = (
                    str(entry.get("query_hash", "")),
                    str(entry.get("provider_set_hash", "")),
                )
                federations_by_query.setdefault(key, set()).add(
                    str(entry.get("subject_hash", ""))
                )
            if entry.get("entry_type") == "rdllm-creator-attribution-audit-index/v1":
                key = (
                    str(entry.get("provider_id", "")),
                    str(entry.get("query_hash", "")),
                )
                indexes_by_provider_query.setdefault(key, set()).add(
                    str(entry.get("subject_hash", ""))
                )
        for (entry_type, subject_hash), indexes in seen.items():
            if len(indexes) > 1:
                row = {
                    "conflict_type": "subject_hash_repeated_in_log",
                    "log_id": log_id,
                    "entry_type": entry_type,
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
    for (query_hash, provider_set_hash), federation_hashes in federations_by_query.items():
        if len(federation_hashes) > 1:
            row = {
                "conflict_type": "same_query_provider_set_multiple_federations",
                "query_hash": query_hash,
                "provider_set_hash": provider_set_hash,
                "federation_hashes": sorted(federation_hashes),
            }
            row["conflict_hash"] = hash_payload(row)
            rows.append(row)
    for (provider_id, query_hash), index_hashes in indexes_by_provider_query.items():
        if len(index_hashes) > 1:
            row = {
                "conflict_type": "provider_query_multiple_index_hashes",
                "provider_id": provider_id,
                "query_hash": query_hash,
                "index_hashes": sorted(index_hashes),
            }
            row["conflict_hash"] = hash_payload(row)
            rows.append(row)
    return sorted(rows, key=lambda row: row["conflict_hash"])


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
        (str(entry.get("entry_type", "")), str(entry.get("subject_hash", ""))): (
            index,
            entry,
        )
        for index, entry in enumerate(entries)
    }
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        subject_key = (
            str(subject.get("subject_type", "")),
            str(subject.get("subject_hash", "")),
        )
        match = by_subject.get(subject_key)
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
            "subject_hash": subject.get("subject_hash", ""),
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


def make_creator_audit_federation_transparency_report(
    *,
    federation_report: dict[str, Any],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L112 report proving creator-audit federation inclusion."""

    timestamp = created_at or now_iso()
    subjects = _federation_subject_rows(federation_report)
    snapshots = _snapshot_rows(transparency_logs)
    append_only = _append_only_rows(transparency_logs)
    split_views = _split_view_rows(transparency_logs)
    required_subjects = _required_subject_rows(subjects, transparency_logs)
    federation_shape_errors = validate_creator_attribution_audit_federation_shape(
        federation_report
    )
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
    checks = {
        "creator_audit_federation_shape_valid": not federation_shape_errors,
        "creator_audit_federation_hash_reproducible": _artifact_hash_is_reproducible(
            federation_report
        ),
        "creator_audit_federation_ready": federation_report.get("summary", {}).get(
            "status"
        )
        == "ready",
        "creator_audit_federation_target_l111": federation_report.get(
            "summary", {}
        ).get("target_certification_level")
        == MINIMUM_INPUT_LEVEL,
        "creator_audit_federation_has_no_identity_conflicts": int(
            federation_report.get("summary", {}).get("identity_conflict_count", 1)
        )
        == 0,
        "required_subjects_declared": bool(subjects),
        "transparency_logs_present": bool(transparency_logs),
        "transparency_log_versions_supported": all(
            row["log_version"] == CREATOR_AUDIT_FEDERATION_TRANSPARENCY_LOG_VERSION
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
        "split_view_and_query_equivocation_absent": not split_views,
        "required_subjects_in_latest_log": bool(required_subjects)
        and all(row["present"] for row in required_subjects),
        "required_subject_inclusion_proofs_valid": bool(required_subjects)
        and all(row["inclusion_proof_valid"] for row in required_subjects),
        "required_subject_payload_hashes_match": bool(required_subjects)
        and all(row["payload_hash_matches"] for row in required_subjects),
        "required_subject_entry_types_match": bool(required_subjects)
        and all(row["entry_type_matches"] for row in required_subjects),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_fields
        ),
    }
    ready = all(checks.values())
    report: dict[str, Any] = {
        "report_version": CREATOR_AUDIT_FEDERATION_TRANSPARENCY_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-creator-audit-federation-transparency-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "requires_federation_report_inclusion": True,
            "requires_participant_index_inclusion": True,
            "requires_append_only_consistency": True,
            "requires_split_view_absence": True,
            "requires_query_equivocation_absence": True,
        },
        "artifact_bindings": {
            "creator_attribution_audit_federation_hash": _declared_hash(
                federation_report
            ),
            "creator_attribution_audit_federation_payload_hash": hash_payload(
                federation_report
            ),
            "creator_attribution_audit_federation_hash_reproducible": _artifact_hash_is_reproducible(
                federation_report
            ),
            "query_hash": _query_hash(federation_report),
            "provider_set_hash": _provider_set_hash(federation_report),
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
        "federation_subject_rows": subjects,
        "log_snapshot_rows": snapshots,
        "append_only_consistency_rows": append_only,
        "split_view_conflict_rows": split_views,
        "required_subject_rows": required_subjects,
        "checks": checks,
        "commitments": {
            "federation_subject_root": merkle_root(
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
            "creator_attribution_audit_federation_transparency": CREATOR_AUDIT_FEDERATION_TRANSPARENCY_SCHEMA,
            "creator_attribution_audit_federation": "docs/schemas/creator_attribution_audit_federation.schema.json",
            "creator_attribution_audit_index": "docs/schemas/creator_attribution_audit_index.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "creator_audit_federation_transparency_included": ready,
            "subject_count": len(subjects),
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
            "query_terms_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "notice_text_disclosed": False,
            "license_text_disclosed": False,
            "stores_hashes_log_roots_inclusion_proofs_and_counts_not_text": True,
        },
    }
    for binding in report["transparency_log_bindings"]:
        binding["binding_hash"] = hash_payload(binding)
    report["commitments"]["transparency_log_binding_root"] = merkle_root(
        [row["binding_hash"] for row in report["transparency_log_bindings"]]
    )
    report["creator_attribution_audit_federation_transparency_hash"] = hash_payload(
        _hashable_report(report)
    )
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


def validate_creator_audit_federation_transparency_shape(
    report: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L112 federation transparency report."""

    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "federation_subject_rows",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "split_view_conflict_rows",
        "required_subject_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "creator_attribution_audit_federation_transparency_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing creator audit federation transparency field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CREATOR_AUDIT_FEDERATION_TRANSPARENCY_VERSION:
        errors.append("creator audit federation transparency version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append(
            "creator audit federation transparency target certification level is unsupported"
        )
    if "creator_attribution_audit_federation_transparency" not in report.get(
        "schemas", {}
    ):
        errors.append("missing creator audit federation transparency schema")
    if _contains_private_fields(report):
        errors.append("creator audit federation transparency contains private field")
    return errors


def verify_creator_audit_federation_transparency_report(
    report: dict[str, Any],
    *,
    federation_report: dict[str, Any],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L112 report against a federation and transparency logs."""

    errors = validate_creator_audit_federation_transparency_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "creator_attribution_audit_federation_transparency_hash"
    ):
        errors.append(
            "creator audit federation transparency hash is not reproducible"
        )
    expected = make_creator_audit_federation_transparency_report(
        federation_report=federation_report,
        transparency_logs=transparency_logs,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "transparency_log_bindings",
        "federation_subject_rows",
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
            errors.append(
                f"creator audit federation transparency {key} does not match inputs"
            )
    if expected.get(
        "creator_attribution_audit_federation_transparency_hash"
    ) != report.get("creator_attribution_audit_federation_transparency_hash"):
        errors.append("creator audit federation transparency hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("creator audit federation transparency status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"creator audit federation transparency check failed: {check}")
    report_json = canonical_json(report)
    for private_key in (
        '"prompt":',
        '"prompt_text":',
        '"answer_text":',
        '"source_text":',
        '"notice_text":',
        '"license_text":',
    ):
        if private_key in report_json:
            errors.append(
                "creator audit federation transparency discloses private field "
                f"{private_key}"
            )
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("creator audit federation transparency report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("creator audit federation transparency report signature is invalid")
    return errors
