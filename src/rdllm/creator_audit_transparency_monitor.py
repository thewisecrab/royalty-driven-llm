"""Creator-side monitoring for transparent creator audit federations.

L112 proves that a single creator audit federation answer was published into
append-only transparency logs. L113 turns those logs into a creator/auditor
monitor: scan logs for a query commitment, report newly observed appearances,
and fail closed on split views or contradictory answers for the same provider
set without exposing raw query, prompt, answer, source, license, or payment text.
"""

from __future__ import annotations

from typing import Any

from rdllm.creator_attribution_audit_federation_transparency import (
    CREATOR_AUDIT_FEDERATION_TRANSPARENCY_LOG_VERSION,
    CREATOR_AUDIT_FEDERATION_TRANSPARENCY_VERSION,
    validate_creator_audit_federation_transparency_shape,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

CREATOR_AUDIT_TRANSPARENCY_MONITOR_VERSION = (
    "rdllm-creator-audit-transparency-monitor/v1"
)
CREATOR_AUDIT_TRANSPARENCY_MONITOR_SCHEMA = (
    "docs/schemas/creator_audit_transparency_monitor.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L113"
MINIMUM_INPUT_LEVEL = "RDLLM-L112"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer",
    "answer_text",
    "source",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "notice_text",
    "license_text",
    "creator_id",
    "creator_ids",
    "work_id",
    "work_ids",
    "source_label",
    "source_labels",
    "query_terms",
    "raw_query",
    "private_query",
    "feedback_text",
    "critique_text",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
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
        if key not in {"creator_audit_transparency_monitor_hash", "signature"}
    }


def _hashable_l112_report(report: dict[str, Any]) -> dict[str, Any]:
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


def _private_strings_absent(report: dict[str, Any], private_strings: list[str]) -> bool:
    report_json = canonical_json(report)
    return all(not value or value not in report_json for value in private_strings)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return sorted(
            {
                str(item)
                for item in value
                if isinstance(item, (str, int, float)) and str(item)
            }
        )
    return []


def _query_commitment(monitor_query: dict[str, Any]) -> dict[str, Any]:
    commitment = {
        "query_hashes": _strings(monitor_query.get("query_hashes")),
        "provider_set_hashes": _strings(monitor_query.get("provider_set_hashes")),
        "expected_federation_hashes": _strings(
            monitor_query.get("expected_federation_hashes")
        ),
        "expected_participant_index_hashes": _strings(
            monitor_query.get("expected_participant_index_hashes")
        ),
        "expected_provider_ids": _strings(monitor_query.get("expected_provider_ids")),
        "raw_query_terms_disclosed": False,
        "raw_creator_or_work_identifiers_disclosed": False,
    }
    commitment["query_commitment_hash"] = hash_payload(commitment)
    return commitment


def _entry_row(log_id: str, entry: dict[str, Any], index: int) -> dict[str, Any]:
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
    return row


def _log_snapshot_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for log_id, log in transparency_logs:
        entries = list(log.get("entries", []))
        entry_rows = [
            _entry_row(log_id, entry, index)
            for index, entry in enumerate(entries)
            if isinstance(entry, dict)
        ]
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
                entry["entry_hash_reproducible"] for entry in entry_rows
            ),
            "entries_have_required_hashes": all(
                entry["entry_has_required_hashes"] for entry in entry_rows
            ),
            "entry_count": len(entry_rows),
            "entry_root": merkle_root([entry["entry_row_hash"] for entry in entry_rows]),
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


def _matches_commitment(entry: dict[str, Any], commitment: dict[str, Any]) -> bool:
    query_hash = str(entry.get("query_hash", ""))
    provider_set_hash = str(entry.get("provider_set_hash", ""))
    provider_id = str(entry.get("provider_id", ""))
    query_hashes = set(commitment["query_hashes"])
    provider_set_hashes = set(commitment["provider_set_hashes"])
    expected_provider_ids = set(commitment["expected_provider_ids"])
    if not query_hashes or query_hash not in query_hashes:
        return False
    if provider_set_hashes and provider_set_hash not in provider_set_hashes:
        return False
    if expected_provider_ids and provider_id and provider_id not in expected_provider_ids:
        return False
    return True


def _observation_rows(
    transparency_logs: list[tuple[str, dict[str, Any]]],
    commitment: dict[str, Any],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for log_id, log in transparency_logs:
        entries = [dict(entry) for entry in log.get("entries", [])]
        leaves = [str(entry.get("entry_hash", "")) for entry in entries]
        for index, entry in enumerate(entries):
            if not _matches_commitment(entry, commitment):
                continue
            proof = inclusion_proof(leaves, index)
            row = {
                "log_id": log_id,
                "entry_index": index,
                "entry_type": str(entry.get("entry_type", "")),
                "subject_hash": str(entry.get("subject_hash", "")),
                "subject_payload_hash": str(entry.get("subject_payload_hash", "")),
                "federation_hash": str(entry.get("federation_hash", "")),
                "query_hash": str(entry.get("query_hash", "")),
                "provider_set_hash": str(entry.get("provider_set_hash", "")),
                "provider_id": str(entry.get("provider_id", "")),
                "participant_index_hash": str(entry.get("participant_index_hash", "")),
                "entry_hash": str(entry.get("entry_hash", "")),
                "log_root": str(log.get("root", "")),
                "tree_size": len(entries),
                "entry_hash_reproducible": hash_payload(_hashable_log_entry(entry))
                == entry.get("entry_hash"),
                "inclusion_proof": proof,
                "inclusion_proof_valid": verify_inclusion(proof),
            }
            row["observation_hash"] = hash_payload(
                {key: value for key, value in row.items() if key != "inclusion_proof"}
            )
            observations.append(row)
    return sorted(
        observations,
        key=lambda row: (
            row["query_hash"],
            row["provider_set_hash"],
            row["entry_type"],
            row["provider_id"],
            row["subject_hash"],
            row["log_id"],
            row["entry_index"],
        ),
    )


def _transparency_report_rows(
    reports: list[dict[str, Any]],
    commitment: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, report in enumerate(reports):
        shape_errors = validate_creator_audit_federation_transparency_shape(report)
        declared_hash = str(
            report.get("creator_attribution_audit_federation_transparency_hash", "")
        )
        computed_hash = hash_payload(_hashable_l112_report(report))
        artifact_bindings = report.get("artifact_bindings", {})
        query_hash = str(artifact_bindings.get("query_hash", ""))
        provider_set_hash = str(artifact_bindings.get("provider_set_hash", ""))
        report_checks = report.get("checks", {})
        row = {
            "report_index": index,
            "report_version": str(report.get("report_version", "")),
            "transparency_report_hash": declared_hash,
            "transparency_report_payload_hash": hash_payload(report),
            "transparency_report_hash_reproducible": bool(declared_hash)
            and declared_hash == computed_hash,
            "shape_valid": not shape_errors,
            "status": str(report.get("summary", {}).get("status", "")),
            "target_certification_level": str(
                report.get("summary", {}).get("target_certification_level", "")
            ),
            "query_hash": query_hash,
            "provider_set_hash": provider_set_hash,
            "federation_hash": str(
                artifact_bindings.get("creator_attribution_audit_federation_hash", "")
            ),
            "subject_count": int(report.get("summary", {}).get("subject_count", 0) or 0),
            "required_subject_count": int(
                report.get("summary", {}).get("required_subject_count", 0) or 0
            ),
            "missing_subject_count": int(
                report.get("summary", {}).get("missing_subject_count", 0) or 0
            ),
            "split_view_conflict_count": int(
                report.get("summary", {}).get("split_view_conflict_count", 0) or 0
            ),
            "append_only_violation_count": int(
                report.get("summary", {}).get("append_only_violation_count", 0) or 0
            ),
            "checks_all_pass": bool(report_checks) and all(
                value is True for value in report_checks.values()
            ),
            "matches_monitor_query": query_hash in set(commitment["query_hashes"])
            and (
                not commitment["provider_set_hashes"]
                or provider_set_hash in set(commitment["provider_set_hashes"])
            ),
            "shape_error_count": len(shape_errors),
        }
        row["transparency_report_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _conflict_rows(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    federations_by_query: dict[tuple[str, str], set[str]] = {}
    indexes_by_provider_query: dict[tuple[str, str], set[str]] = {}
    for row in observations:
        if row["entry_type"] == "rdllm-creator-attribution-audit-federation/v1":
            federations_by_query.setdefault(
                (row["query_hash"], row["provider_set_hash"]),
                set(),
            ).add(row["subject_hash"])
        if row["entry_type"] == "rdllm-creator-attribution-audit-index/v1":
            indexes_by_provider_query.setdefault(
                (row["provider_id"], row["query_hash"]),
                set(),
            ).add(row["subject_hash"])
    for (query_hash, provider_set_hash), federation_hashes in federations_by_query.items():
        if len(federation_hashes) > 1:
            conflict = {
                "conflict_type": "same_query_provider_set_multiple_federations",
                "query_hash": query_hash,
                "provider_set_hash": provider_set_hash,
                "federation_hashes": sorted(federation_hashes),
            }
            conflict["conflict_hash"] = hash_payload(conflict)
            conflicts.append(conflict)
    for (provider_id, query_hash), index_hashes in indexes_by_provider_query.items():
        if len(index_hashes) > 1:
            conflict = {
                "conflict_type": "provider_query_multiple_index_hashes",
                "provider_id": provider_id,
                "query_hash": query_hash,
                "index_hashes": sorted(index_hashes),
            }
            conflict["conflict_hash"] = hash_payload(conflict)
            conflicts.append(conflict)
    return sorted(conflicts, key=lambda row: row["conflict_hash"])


def _previous_monitor_hash_reproducible(previous_report: dict[str, Any] | None) -> bool:
    if not previous_report:
        return True
    return hash_payload(_hashable_report(previous_report)) == previous_report.get(
        "creator_audit_transparency_monitor_hash"
    )


def make_creator_audit_transparency_monitor_report(
    *,
    monitor_query: dict[str, Any],
    transparency_reports: list[dict[str, Any]],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    previous_report: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L113 creator/auditor monitor over L112 transparency logs."""

    timestamp = created_at or now_iso()
    private_strings = _strings(monitor_query.get("private_strings"))
    commitment = _query_commitment(monitor_query)
    report_rows = _transparency_report_rows(transparency_reports, commitment)
    snapshots = _log_snapshot_rows(transparency_logs)
    append_only = _append_only_rows(transparency_logs)
    observations = _observation_rows(transparency_logs, commitment)
    conflicts = _conflict_rows(observations)
    previous_observation_hashes = {
        str(row.get("observation_hash", ""))
        for row in (previous_report or {}).get("observation_rows", [])
        if isinstance(row, dict)
    }
    current_observation_hashes = {
        str(row.get("observation_hash", "")) for row in observations
    }
    new_observations = [
        row
        for row in observations
        if row["observation_hash"] not in previous_observation_hashes
    ]
    removed_previous = sorted(previous_observation_hashes - current_observation_hashes)
    observed_federations = {
        row["subject_hash"]
        for row in observations
        if row["entry_type"] == "rdllm-creator-attribution-audit-federation/v1"
    }
    observed_participant_indexes = {
        row["subject_hash"]
        for row in observations
        if row["entry_type"] == "rdllm-creator-attribution-audit-index/v1"
    }
    missing_expected_federations = sorted(
        set(commitment["expected_federation_hashes"]) - observed_federations
    )
    missing_expected_indexes = sorted(
        set(commitment["expected_participant_index_hashes"])
        - observed_participant_indexes
    )
    previous_commitment_hash = str(
        (previous_report or {})
        .get("monitor_query", {})
        .get("query_commitment_hash", "")
    )
    public_fields = {
        "monitor_query": commitment,
        "transparency_report_rows": report_rows,
        "log_snapshot_rows": snapshots,
        "append_only_consistency_rows": append_only,
        "observation_rows": [
            {key: value for key, value in row.items() if key != "inclusion_proof"}
            for row in observations
        ],
        "conflict_rows": conflicts,
    }
    checks = {
        "monitor_query_commitment_present": bool(commitment["query_hashes"]),
        "monitor_query_has_no_private_field_names": not _contains_private_fields(
            {
                key: value
                for key, value in monitor_query.items()
                if key != "private_strings"
            }
        ),
        "l112_transparency_reports_present": bool(transparency_reports),
        "l112_transparency_report_versions_supported": all(
            row["report_version"] == CREATOR_AUDIT_FEDERATION_TRANSPARENCY_VERSION
            for row in report_rows
        ),
        "l112_transparency_report_shapes_valid": all(
            row["shape_valid"] for row in report_rows
        ),
        "l112_transparency_report_hashes_reproducible": all(
            row["transparency_report_hash_reproducible"] for row in report_rows
        ),
        "l112_transparency_reports_ready": all(
            row["status"] == "ready"
            and row["target_certification_level"] == MINIMUM_INPUT_LEVEL
            and row["checks_all_pass"]
            for row in report_rows
        ),
        "l112_transparency_reports_match_monitor_query": all(
            row["matches_monitor_query"] for row in report_rows
        ),
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
        "matching_observations_present": bool(observations),
        "matching_observation_entry_hashes_reproducible": all(
            row["entry_hash_reproducible"] for row in observations
        ),
        "matching_observation_inclusion_proofs_valid": all(
            row["inclusion_proof_valid"] for row in observations
        ),
        "expected_federation_hashes_seen": not missing_expected_federations,
        "expected_participant_index_hashes_seen": not missing_expected_indexes,
        "append_only_prefix_consistency": all(
            row["prefix_consistent"] for row in append_only
        ),
        "same_query_equivocation_absent": not any(
            row["conflict_type"] == "same_query_provider_set_multiple_federations"
            for row in conflicts
        ),
        "provider_index_equivocation_absent": not any(
            row["conflict_type"] == "provider_query_multiple_index_hashes"
            for row in conflicts
        ),
        "previous_monitor_hash_reproducible": _previous_monitor_hash_reproducible(
            previous_report
        ),
        "monitor_query_matches_previous": (
            not previous_report
            or previous_commitment_hash == commitment["query_commitment_hash"]
        ),
        "monitor_observations_append_only_with_previous": not removed_previous,
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_fields
        ),
    }
    ready = all(checks.values())
    report: dict[str, Any] = {
        "monitor_version": CREATOR_AUDIT_TRANSPARENCY_MONITOR_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-creator-audit-transparency-monitor-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "requires_l112_transparency_reports": True,
            "requires_append_only_log_monitoring": True,
            "requires_inclusion_proofs_for_matching_entries": True,
            "requires_query_equivocation_absence": True,
            "requires_append_only_monitor_continuity": True,
            "raw_creator_query_terms_prohibited": True,
        },
        "monitor_query": commitment,
        "transparency_report_rows": report_rows,
        "log_snapshot_rows": snapshots,
        "append_only_consistency_rows": append_only,
        "observation_rows": observations,
        "new_observation_rows": new_observations,
        "conflict_rows": conflicts,
        "continuity": {
            "monitor_mode": "append" if previous_report else "genesis",
            "previous_monitor_hash": str(
                (previous_report or {}).get(
                    "creator_audit_transparency_monitor_hash", ""
                )
            ),
            "previous_query_commitment_hash": previous_commitment_hash,
            "previous_observation_count": len(previous_observation_hashes),
            "current_observation_count": len(current_observation_hashes),
            "new_observation_count": len(new_observations),
            "removed_previous_observation_hashes": removed_previous,
            "removed_previous_observation_count": len(removed_previous),
        },
        "checks": checks,
        "commitments": {
            "query_commitment_hash": commitment["query_commitment_hash"],
            "transparency_report_root": merkle_root(
                [row["transparency_report_row_hash"] for row in report_rows]
            ),
            "log_snapshot_root": merkle_root(
                [row["snapshot_hash"] for row in snapshots]
            ),
            "append_only_consistency_root": merkle_root(
                [row["consistency_hash"] for row in append_only]
            ),
            "observation_root": merkle_root(
                [row["observation_hash"] for row in observations]
            ),
            "new_observation_root": merkle_root(
                [row["observation_hash"] for row in new_observations]
            ),
            "conflict_root": merkle_root(
                [row["conflict_hash"] for row in conflicts]
            ),
            "schema": CREATOR_AUDIT_TRANSPARENCY_MONITOR_SCHEMA,
        },
        "schemas": {
            "creator_audit_transparency_monitor": CREATOR_AUDIT_TRANSPARENCY_MONITOR_SCHEMA,
            "creator_attribution_audit_federation_transparency": "docs/schemas/creator_attribution_audit_federation_transparency.schema.json",
            "creator_attribution_audit_federation": "docs/schemas/creator_attribution_audit_federation.schema.json",
            "creator_attribution_audit_index": "docs/schemas/creator_attribution_audit_index.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "monitor_mode": "append" if previous_report else "genesis",
            "query_hash_count": len(commitment["query_hashes"]),
            "provider_set_hash_count": len(commitment["provider_set_hashes"]),
            "transparency_report_count": len(transparency_reports),
            "transparency_log_count": len(transparency_logs),
            "matching_observation_count": len(observations),
            "new_observation_count": len(new_observations),
            "federation_observation_count": len(observed_federations),
            "participant_index_observation_count": len(observed_participant_indexes),
            "append_only_violation_count": len(
                [
                    row
                    for row in append_only
                    if row["decision"] == "append_only_violation"
                ]
            ),
            "conflict_count": len(conflicts),
            "missing_expected_federation_count": len(missing_expected_federations),
            "missing_expected_participant_index_count": len(missing_expected_indexes),
        },
        "privacy": {
            "query_terms_disclosed": False,
            "creator_identifiers_disclosed": False,
            "work_identifiers_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "notice_text_disclosed": False,
            "license_text_disclosed": False,
            "payment_text_disclosed": False,
            "stores_hashes_log_roots_inclusion_proofs_counts_and_diffs_not_text": True,
        },
    }
    checks["private_strings_absent"] = _private_strings_absent(report, private_strings)
    report["summary"]["status"] = "ready" if all(checks.values()) else "failed"
    report["creator_audit_transparency_monitor_hash"] = hash_payload(
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


def validate_creator_audit_transparency_monitor_shape(
    report: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L113 creator transparency monitor."""

    errors: list[str] = []
    required = (
        "monitor_version",
        "issuer",
        "created_at",
        "policy",
        "monitor_query",
        "transparency_report_rows",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "observation_rows",
        "new_observation_rows",
        "conflict_rows",
        "continuity",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "creator_audit_transparency_monitor_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing creator audit transparency monitor field: {key}")
    if errors:
        return errors
    if report.get("monitor_version") != CREATOR_AUDIT_TRANSPARENCY_MONITOR_VERSION:
        errors.append("creator audit transparency monitor version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append(
            "creator audit transparency monitor target certification level is unsupported"
        )
    if "creator_audit_transparency_monitor" not in report.get("schemas", {}):
        errors.append("missing creator audit transparency monitor schema")
    if _contains_private_fields(report):
        errors.append("creator audit transparency monitor contains private field")
    for row in report.get("observation_rows", []):
        for key in (
            "log_id",
            "entry_index",
            "entry_type",
            "subject_hash",
            "query_hash",
            "provider_set_hash",
            "entry_hash",
            "observation_hash",
            "inclusion_proof_valid",
        ):
            if key not in row:
                errors.append(
                    f"missing creator audit transparency monitor observation field: {key}"
                )
    return errors


def verify_creator_audit_transparency_monitor_report(
    report: dict[str, Any],
    *,
    monitor_query: dict[str, Any],
    transparency_reports: list[dict[str, Any]],
    transparency_logs: list[tuple[str, dict[str, Any]]],
    previous_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L113 monitor against L112 reports, log snapshots, and prior state."""

    errors = validate_creator_audit_transparency_monitor_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "creator_audit_transparency_monitor_hash"
    ):
        errors.append("creator audit transparency monitor hash is not reproducible")
    if report.get("summary", {}).get("monitor_mode") == "append" and previous_report is None:
        errors.append("previous creator audit transparency monitor is required")
    expected = make_creator_audit_transparency_monitor_report(
        monitor_query=monitor_query,
        transparency_reports=transparency_reports,
        transparency_logs=transparency_logs,
        previous_report=previous_report,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "monitor_query",
        "transparency_report_rows",
        "log_snapshot_rows",
        "append_only_consistency_rows",
        "observation_rows",
        "new_observation_rows",
        "conflict_rows",
        "continuity",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"creator audit transparency monitor {key} does not match inputs")
    if expected.get("creator_audit_transparency_monitor_hash") != report.get(
        "creator_audit_transparency_monitor_hash"
    ):
        errors.append("creator audit transparency monitor hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("creator audit transparency monitor status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"creator audit transparency monitor check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("creator audit transparency monitor report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append(
                "creator audit transparency monitor report signature is invalid"
            )
    return errors
