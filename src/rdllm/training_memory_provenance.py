"""Training-memory provenance audits for rendered RDLLM answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import (
    longest_common_token_sequence,
    ngram_containment,
    stable_hash,
    tokenize,
)

TRAINING_MEMORY_PROVENANCE_VERSION = "rdllm-training-memory-provenance/v1"
TRAINING_MEMORY_PROVENANCE_SCHEMA = (
    "docs/schemas/training_memory_provenance.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L81"
DEFAULT_MIN_MATCH_TOKENS = 8

DECLARED_HASH_FIELDS = (
    "report_hash",
    "summary_hash",
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


def load_training_memory_snapshots(path: str | Path) -> list[dict[str, Any]]:
    """Load registered source snapshots for training-memory provenance audits."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("snapshots", [])]


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
    if not any(artifact.get(field) for field in DECLARED_HASH_FIELDS):
        return True
    return hash_payload(_hashable_artifact(artifact)) == _declared_hash(artifact)


def _body_text(snapshot: dict[str, Any]) -> str:
    for key in ("body_text", "source_text", "content"):
        value = snapshot.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _answer_body(rendered_output: str) -> str:
    lines = rendered_output.splitlines()
    sources_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "Sources"),
        len(lines),
    )
    return "\n".join(lines[:sources_index]).strip()


def _snapshot_commitment(snapshot: dict[str, Any]) -> dict[str, Any]:
    body = _body_text(snapshot)
    declared_hash = str(snapshot.get("content_hash", ""))
    body_hash = stable_hash(body) if body else str(snapshot.get("body_hash", ""))
    content_hash = declared_hash or body_hash
    row = {
        "work_id": str(snapshot.get("work_id", "")),
        "chunk_id": str(snapshot.get("chunk_id", "")),
        "source_uri": str(snapshot.get("source_uri", "")),
        "canonical_uri": str(
            snapshot.get("canonical_uri", snapshot.get("source_uri", ""))
        ),
        "archived_uri": str(snapshot.get("archived_uri", "")),
        "retrieved_at": str(snapshot.get("retrieved_at", "")),
        "content_hash": content_hash,
        "body_hash": body_hash,
        "declared_content_hash_matches_body": (
            not body or not declared_hash or declared_hash == body_hash
        ),
        "token_count": len(tokenize(body)),
    }
    row["snapshot_commitment_hash"] = hash_payload(row)
    return row


def _visible_footer_by_chunk(
    rendered_attribution_audit: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = (
        rendered_attribution_audit.get("parsed_markdown", {})
        .get("source_footer_rows", [])
    )
    return {
        str(row.get("chunk_id", "")): row
        for row in rows
        if row.get("chunk_id")
    }


def _visible_footer_by_uri(
    rendered_attribution_audit: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = (
        rendered_attribution_audit.get("parsed_markdown", {})
        .get("source_footer_rows", [])
    )
    return {
        str(row.get("source_uri", "")): row
        for row in rows
        if row.get("source_uri")
    }


def _license_terms_by_work(
    creator_license_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(term.get("work_id", "")): term
        for term in creator_license_contract.get("terms", [])
        if term.get("work_id")
    }


def _training_cohorts_by_work(
    training_content_summary: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(cohort.get("work_id", "")): cohort
        for cohort in training_content_summary.get("training_content", {}).get(
            "cohorts", []
        )
        if cohort.get("work_id")
    }


def _memory_span_rows(
    *,
    answer_body: str,
    source_snapshots: list[dict[str, Any]],
    rendered_attribution_audit: dict[str, Any],
    creator_license_contract: dict[str, Any],
    training_content_summary: dict[str, Any],
    min_match_tokens: int,
) -> list[dict[str, Any]]:
    answer_tokens = tokenize(answer_body)
    visible_by_chunk = _visible_footer_by_chunk(rendered_attribution_audit)
    visible_by_uri = _visible_footer_by_uri(rendered_attribution_audit)
    terms_by_work = _license_terms_by_work(creator_license_contract)
    cohorts_by_work = _training_cohorts_by_work(training_content_summary)
    rows: list[dict[str, Any]] = []

    for snapshot in source_snapshots:
        source_text = _body_text(snapshot)
        source_tokens = tokenize(source_text)
        if not source_tokens or not answer_tokens:
            continue
        longest_length, longest_tokens = longest_common_token_sequence(
            source_tokens,
            answer_tokens,
        )
        if longest_length < min_match_tokens:
            continue
        chunk_id = str(snapshot.get("chunk_id", ""))
        source_uri = str(snapshot.get("source_uri", ""))
        work_id = str(snapshot.get("work_id", ""))
        visible_row = visible_by_chunk.get(chunk_id) or visible_by_uri.get(source_uri)
        term = terms_by_work.get(work_id, {})
        cohort = cohorts_by_work.get(work_id, {})
        allowed_uses = set(str(use) for use in term.get("allowed_uses", []))
        training_allowed = cohort.get("training_allowed") is True and (
            "training" in allowed_uses or not allowed_uses
        )
        generation_allowed = "generation" in allowed_uses or not allowed_uses
        display_allowed = "display" in allowed_uses or not allowed_uses
        visible = bool(visible_row)
        attribution_required = (
            term.get("requires_attribution") is True
            or term.get("duties", {}).get("attribution_required") is True
        )
        royalty_required = (
            term.get("requires_royalty") is True
            or term.get("duties", {}).get("royalty_required") is True
        )
        content_hash = str(snapshot.get("content_hash") or stable_hash(source_text))
        row = {
            "work_id": work_id,
            "chunk_id": chunk_id,
            "creator_id": str(snapshot.get("creator_id") or term.get("creator_id", "")),
            "source_uri": source_uri,
            "content_hash": content_hash,
            "visible_source_label": str(visible_row.get("label", "")) if visible else "",
            "matched_sequence_hash": stable_hash(" ".join(longest_tokens)),
            "matched_token_count": longest_length,
            "source_token_count": len(source_tokens),
            "answer_token_count": len(answer_tokens),
            "source_token_coverage": round(longest_length / len(source_tokens), 8),
            "answer_token_coverage": round(longest_length / len(answer_tokens), 8),
            "ngram_containment": round(
                ngram_containment(
                    source_tokens,
                    answer_tokens,
                    size=min(5, max(1, min_match_tokens)),
                ),
                8,
            ),
            "visible_attribution_bound": visible,
            "training_allowed": training_allowed,
            "generation_allowed": generation_allowed,
            "display_allowed": display_allowed,
            "attribution_required": attribution_required,
            "royalty_required": royalty_required,
            "content_hash_in_training_summary": (
                cohort.get("content_hash") == content_hash
            ),
            "content_hash_in_license_contract": term.get("content_hash") == content_hash,
            "remediation_status": (
                "visible_attributed"
                if visible
                else "unattributed_memory_escrow_required"
            ),
        }
        row["memory_span_row_hash"] = hash_payload(row)
        rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row["work_id"]),
            str(row["chunk_id"]),
            str(row["matched_sequence_hash"]),
        )
    )
    return rows


def make_training_memory_provenance_report(
    *,
    response_envelope: dict[str, Any],
    rendered_attribution_audit: dict[str, Any],
    creator_license_contract: dict[str, Any],
    training_content_summary: dict[str, Any],
    source_snapshots: list[dict[str, Any]],
    min_match_tokens: int = DEFAULT_MIN_MATCH_TOKENS,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Detect registered training-memory spans in the visible answer surface."""

    response = response_envelope.get("response", {})
    rendered_output = str(response.get("rendered_output", ""))
    answer_body = _answer_body(rendered_output)
    snapshot_commitments = [
        _snapshot_commitment(snapshot) for snapshot in source_snapshots
    ]
    memory_rows = _memory_span_rows(
        answer_body=answer_body,
        source_snapshots=source_snapshots,
        rendered_attribution_audit=rendered_attribution_audit,
        creator_license_contract=creator_license_contract,
        training_content_summary=training_content_summary,
        min_match_tokens=min_match_tokens,
    )
    hidden_rows = [
        row for row in memory_rows if not row.get("visible_attribution_bound")
    ]
    checks = {
        "rendered_output_hash_matches_response": response.get("rendered_output_hash")
        == stable_hash(rendered_output),
        "rendered_attribution_audit_verified": rendered_attribution_audit.get(
            "summary", {}
        ).get("status")
        == "ready"
        and rendered_attribution_audit.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L80",
        "snapshot_content_hashes_reproducible": all(
            row.get("declared_content_hash_matches_body")
            for row in snapshot_commitments
        ),
        "memory_sources_present_in_training_summary": all(
            row.get("content_hash_in_training_summary") for row in memory_rows
        ),
        "memory_sources_present_in_license_contract": all(
            row.get("content_hash_in_license_contract") for row in memory_rows
        ),
        "memory_sources_training_generation_display_allowed": all(
            row.get("training_allowed")
            and row.get("generation_allowed")
            and row.get("display_allowed")
            for row in memory_rows
        ),
        "all_memory_spans_visible_attributed": not hidden_rows,
        "input_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                response_envelope,
                rendered_attribution_audit,
                creator_license_contract,
                training_content_summary,
            )
        ),
    }
    report = {
        "report_version": TRAINING_MEMORY_PROVENANCE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "audit_policy": {
            "profile": "rdllm-training-memory-provenance-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L80",
            "min_match_tokens": min_match_tokens,
            "raw_answer_text_forbidden": True,
            "raw_source_text_forbidden": True,
            "memorized_registered_text_requires_visible_attribution": True,
            "hidden_memory_match_requires_escrow_or_block": True,
        },
        "response": {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "answer_body_hash": stable_hash(answer_body),
            "answer_body_token_count": len(tokenize(answer_body)),
        },
        "artifact_bindings": {
            "response_envelope_hash": _declared_hash(response_envelope),
            "rendered_attribution_audit_hash": _declared_hash(
                rendered_attribution_audit
            ),
            "creator_license_contract_hash": _declared_hash(creator_license_contract),
            "training_content_summary_hash": _declared_hash(training_content_summary),
            "source_snapshot_root": hash_payload(snapshot_commitments),
        },
        "source_snapshot_commitments": snapshot_commitments,
        "memorized_span_rows": memory_rows,
        "remediation_rows": [
            {
                "work_id": row["work_id"],
                "chunk_id": row["chunk_id"],
                "creator_id": row["creator_id"],
                "matched_sequence_hash": row["matched_sequence_hash"],
                "required_action": "add_visible_attribution_or_route_to_memory_escrow",
                "remediation_row_hash": hash_payload(
                    {
                        "work_id": row["work_id"],
                        "chunk_id": row["chunk_id"],
                        "creator_id": row["creator_id"],
                        "matched_sequence_hash": row["matched_sequence_hash"],
                    }
                ),
            }
            for row in hidden_rows
        ],
        "checks": checks,
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_snapshot_count": len(snapshot_commitments),
            "detected_memory_span_count": len(memory_rows),
            "visible_attributed_memory_span_count": len(memory_rows) - len(hidden_rows),
            "hidden_memory_span_count": len(hidden_rows),
            "remediation_row_count": len(hidden_rows),
            "training_memory_provenance_verified": all(checks.values()),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "prompt_text_disclosed": False,
            "matched_text_disclosed": False,
            "stores_hashes_and_counts_not_text": True,
        },
        "schemas": {
            "training_memory_provenance": TRAINING_MEMORY_PROVENANCE_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "training_content_summary": "docs/schemas/training_content_summary.schema.json",
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


def validate_training_memory_provenance_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "audit_policy",
        "response",
        "artifact_bindings",
        "source_snapshot_commitments",
        "memorized_span_rows",
        "remediation_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing training memory provenance field: {key}")
    if errors:
        return errors
    if report.get("report_version") != TRAINING_MEMORY_PROVENANCE_VERSION:
        errors.append("training memory provenance version is unsupported")
    if report.get("audit_policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("training memory provenance target certification level is unsupported")
    for key in (
        "response_envelope_hash",
        "rendered_attribution_audit_hash",
        "creator_license_contract_hash",
        "training_content_summary_hash",
        "source_snapshot_root",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing training memory artifact binding: {key}")
    for key in (
        "status",
        "target_certification_level",
        "source_snapshot_count",
        "detected_memory_span_count",
        "visible_attributed_memory_span_count",
        "hidden_memory_span_count",
        "remediation_row_count",
        "training_memory_provenance_verified",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing training memory summary field: {key}")
    if "training_memory_provenance" not in report.get("schemas", {}):
        errors.append("missing training memory provenance schema")
    return errors


def verify_training_memory_provenance_report(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    rendered_attribution_audit: dict[str, Any],
    creator_license_contract: dict[str, Any],
    training_content_summary: dict[str, Any],
    source_snapshots: list[dict[str, Any]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a training-memory provenance report against its proof inputs."""

    errors = validate_training_memory_provenance_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("training memory provenance hash is not reproducible")
    expected = make_training_memory_provenance_report(
        response_envelope=response_envelope,
        rendered_attribution_audit=rendered_attribution_audit,
        creator_license_contract=creator_license_contract,
        training_content_summary=training_content_summary,
        source_snapshots=source_snapshots,
        min_match_tokens=int(report.get("audit_policy", {}).get("min_match_tokens", 0)),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "audit_policy",
        "response",
        "artifact_bindings",
        "source_snapshot_commitments",
        "memorized_span_rows",
        "remediation_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"training memory provenance {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("training memory provenance hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("training memory provenance status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"training memory provenance check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("training memory provenance is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("training memory provenance signature is invalid")
    return errors
