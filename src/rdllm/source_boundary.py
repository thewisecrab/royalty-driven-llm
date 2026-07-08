"""Source-boundary integrity reports for RDLLM generation context."""

from __future__ import annotations

from typing import Any

from rdllm.context_closure import (
    validate_generation_context_closure_report_shape,
    verify_generation_context_closure_report,
)
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.source_verification import validate_source_verification_report_shape
from rdllm.telemetry import verify_trace_exchange

SOURCE_BOUNDARY_REPORT_VERSION = "rdllm-source-boundary-report/v1"
SOURCE_BOUNDARY_SCHEMA = "docs/schemas/source_boundary_report.schema.json"
SOURCE_BOUNDARY_PROFILE_VERSION = "rdllm-source-boundary-profile/v1"
SOURCE_BOUNDARY_POLICY_VERSION = "rdllm-source-boundary-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L61"


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in ("trace_hash", "report_hash", "card_hash", "contract_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _trace_accesses(trace_exchange: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for span in trace_exchange.get("spans", []):
        attrs = span.get("attributes", {})
        if attrs.get("rdllm.span.kind") != "source_access":
            continue
        access_id = str(attrs.get("rdllm.source.access_id", ""))
        if not access_id:
            continue
        rows[access_id] = {
            "source_access_id": access_id,
            "span_id": str(span.get("span_id", "")),
            "chunk_id": str(attrs.get("rdllm.source.chunk_id", "")),
            "work_id": str(attrs.get("rdllm.source.work_id", "")),
            "creator_id": str(attrs.get("rdllm.source.creator_id", "")),
            "content_hash": str(attrs.get("rdllm.source.content_hash", "")),
            "use": str(attrs.get("rdllm.source.use", "")),
            "boundary_profile": str(
                attrs.get("rdllm.source.boundary.profile", "")
            ),
            "boundary_role": str(attrs.get("rdllm.source.boundary.role", "")),
            "boundary_control_channel": attrs.get(
                "rdllm.source.boundary.control_channel"
            )
            is True,
            "boundary_instruction_channel": attrs.get(
                "rdllm.source.boundary.instruction_channel"
            )
            is True,
            "boundary_can_modify_attribution": attrs.get(
                "rdllm.source.boundary.can_modify_attribution"
            )
            is True,
            "boundary_can_modify_payout": attrs.get(
                "rdllm.source.boundary.can_modify_payout"
            )
            is True,
            "boundary_content_hash_bound": attrs.get(
                "rdllm.source.boundary.content_hash_bound"
            )
            is True,
            "boundary_packet_hash": str(
                attrs.get("rdllm.source.boundary.packet_hash", "")
            ),
        }
    return rows


def _source_content_hash_by_chunk(
    source_verification_report: dict[str, Any],
) -> dict[str, str]:
    return {
        str(source.get("chunk_id", "")): str(source.get("content_hash", ""))
        for source in source_verification_report.get("sources", [])
    }


def _expected_packet_hash(access: dict[str, Any]) -> str:
    return hash_payload(
        {
            "profile": SOURCE_BOUNDARY_PROFILE_VERSION,
            "role": "evidence",
            "access_id": access.get("source_access_id", ""),
            "chunk_id": access.get("chunk_id", ""),
            "work_id": access.get("work_id", ""),
            "content_hash": access.get("content_hash", ""),
            "use": access.get("use", ""),
            "control_channel": False,
            "instruction_channel": False,
            "can_modify_attribution": False,
            "can_modify_payout": False,
            "content_hash_bound": True,
        }
    )


def _artifact_bindings(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
) -> dict[str, Any]:
    context_event = generation_context_closure_report.get("event", {})
    source_event = source_verification_report.get("event", {})
    return {
        "trace_exchange_hash": _declared_hash(trace_exchange),
        "source_verification_report_hash": _declared_hash(
            source_verification_report
        ),
        "generation_context_closure_report_hash": _declared_hash(
            generation_context_closure_report
        ),
        "trace_exchange_bound": bool(trace_exchange),
        "source_verification_bound": bool(source_verification_report),
        "generation_context_closure_bound": bool(
            generation_context_closure_report
        ),
        "context_event_matches_source_report": (
            context_event.get("event_hash") == source_event.get("event_hash")
            and context_event.get("rendered_output_hash")
            == source_event.get("rendered_output_hash")
            and context_event.get("answer_hash") == source_event.get("answer_hash")
        ),
        "context_trace_matches_trace_exchange": (
            context_event.get("trace_hash") == trace_exchange.get("trace_hash", "")
        ),
    }


def _boundary_rows(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
) -> list[dict[str, Any]]:
    accesses = _trace_accesses(trace_exchange)
    content_hash_by_chunk = _source_content_hash_by_chunk(source_verification_report)
    rows: list[dict[str, Any]] = []
    for block in sorted(
        generation_context_closure_report.get("context_blocks", []),
        key=lambda row: (
            int(row.get("block_index", 0) or 0),
            str(row.get("context_block_id", "")),
        ),
    ):
        access = accesses.get(str(block.get("source_access_id", "")), {})
        access_in_trace = bool(access)
        source_content_hash = content_hash_by_chunk.get(
            str(block.get("chunk_id", "")),
            "",
        )
        evidence_role_declared = (
            access_in_trace
            and access.get("boundary_profile") == SOURCE_BOUNDARY_PROFILE_VERSION
            and access.get("boundary_role") == "evidence"
        )
        control_channel_blocked = (
            access_in_trace and access.get("boundary_control_channel") is False
        )
        instruction_channel_blocked = (
            access_in_trace and access.get("boundary_instruction_channel") is False
        )
        source_cannot_modify_attribution = (
            access_in_trace
            and access.get("boundary_can_modify_attribution") is False
        )
        source_cannot_modify_payout = (
            access_in_trace and access.get("boundary_can_modify_payout") is False
        )
        content_hash_bound = (
            access_in_trace and access.get("boundary_content_hash_bound") is True
        )
        content_hash_matches_context = (
            access_in_trace
            and access.get("content_hash") == block.get("content_hash")
            and (
                not source_content_hash
                or source_content_hash == block.get("content_hash")
            )
        )
        span_matches_context = (
            access_in_trace
            and access.get("span_id") == block.get("source_access_span_id")
            and access.get("chunk_id") == block.get("chunk_id")
            and access.get("work_id") == block.get("work_id")
            and access.get("creator_id") == block.get("creator_id")
        )
        packet_hash_matches_profile = (
            access_in_trace
            and access.get("boundary_packet_hash") == _expected_packet_hash(access)
        )
        row = {
            "context_block_id": str(block.get("context_block_id", "")),
            "context_block_hash": str(block.get("context_block_hash", "")),
            "source_access_id": str(block.get("source_access_id", "")),
            "source_access_span_id": str(block.get("source_access_span_id", "")),
            "chunk_id": str(block.get("chunk_id", "")),
            "work_id": str(block.get("work_id", "")),
            "creator_id": str(block.get("creator_id", "")),
            "content_hash": str(block.get("content_hash", "")),
            "source_access_in_trace": access_in_trace,
            "span_matches_context": span_matches_context,
            "boundary_profile": str(access.get("boundary_profile", "")),
            "source_role": str(access.get("boundary_role", "")),
            "evidence_role_declared": evidence_role_declared,
            "control_channel_blocked": control_channel_blocked,
            "instruction_channel_blocked": instruction_channel_blocked,
            "source_cannot_modify_attribution": source_cannot_modify_attribution,
            "source_cannot_modify_payout": source_cannot_modify_payout,
            "content_hash_bound": content_hash_bound,
            "content_hash_matches_context": content_hash_matches_context,
            "packet_hash_matches_profile": packet_hash_matches_profile,
        }
        row["source_boundary_closed"] = all(
            row[key] is True
            for key in (
                "source_access_in_trace",
                "span_matches_context",
                "evidence_role_declared",
                "control_channel_blocked",
                "instruction_channel_blocked",
                "source_cannot_modify_attribution",
                "source_cannot_modify_payout",
                "content_hash_bound",
                "content_hash_matches_context",
                "packet_hash_matches_profile",
            )
        )
        row["source_boundary_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(
    *,
    rows: list[dict[str, Any]],
    bindings: dict[str, Any],
    source_verification_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    for row in rows:
        if row["source_boundary_closed"] is not True:
            issues.append(
                f"context block {row['context_block_id']} is not source-boundary isolated"
            )
    for name in (
        "trace_exchange",
        "source_verification",
        "generation_context_closure",
    ):
        if bindings.get(f"{name}_bound") is not True:
            issues.append(f"{name.replace('_', ' ')} is not bound")
    if bindings.get("context_event_matches_source_report") is not True:
        issues.append("generation context closure event does not match source report")
    if bindings.get("context_trace_matches_trace_exchange") is not True:
        issues.append("generation context closure trace does not match trace exchange")
    if source_verification_report.get("summary", {}).get("status") != "verified":
        issues.append("source verification report is not verified")
    if generation_context_closure_report.get("summary", {}).get("status") != "verified":
        issues.append("generation context closure report is not verified")
    if generation_context_closure_report.get("summary", {}).get(
        "all_supported_claims_in_generation_context"
    ) is not True:
        issues.append("generation context closure has claims outside context")
    return issues


def make_source_boundary_report(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public proof that generation-context sources were evidence-only."""

    rows = _boundary_rows(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        generation_context_closure_report=generation_context_closure_report,
    )
    bindings = _artifact_bindings(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        generation_context_closure_report=generation_context_closure_report,
    )
    issue_list = _issues(
        rows=rows,
        bindings=bindings,
        source_verification_report=source_verification_report,
        generation_context_closure_report=generation_context_closure_report,
    )
    event = source_verification_report.get("event", {})
    report = {
        "report_version": SOURCE_BOUNDARY_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": SOURCE_BOUNDARY_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_boundary_profile": SOURCE_BOUNDARY_PROFILE_VERSION,
            "requires_source_data_instruction_separation": True,
            "requires_evidence_only_source_role": True,
            "blocks_source_control_channel": True,
            "blocks_source_instruction_channel": True,
            "blocks_source_attribution_mutation": True,
            "blocks_source_payout_mutation": True,
            "requires_content_hash_bound_packets": True,
        },
        "event": {
            "event_id": event.get("event_id", ""),
            "event_hash": event.get("event_hash", ""),
            "rendered_output_hash": event.get("rendered_output_hash", ""),
            "answer_hash": event.get("answer_hash", ""),
            "trace_hash": trace_exchange.get("trace_hash", ""),
            "generation_context_closure_report_hash": (
                generation_context_closure_report or {}
            ).get("report_hash", ""),
        },
        "artifact_bindings": bindings,
        "source_boundary_rows": rows,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "context_block_count": len(rows),
            "boundary_closed_block_count": sum(
                1 for row in rows if row["source_boundary_closed"]
            ),
            "boundary_violation_count": sum(
                1 for row in rows if not row["source_boundary_closed"]
            ),
            "all_context_blocks_boundary_isolated": all(
                row["source_boundary_closed"] for row in rows
            )
            if rows
            else True,
            "issue_count": len(issue_list),
        },
        "commitments": {
            "source_boundary_root": hash_payload(rows),
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
        },
        "schemas": {
            "source_boundary_report": SOURCE_BOUNDARY_SCHEMA,
            "generation_context_closure_report": (
                "docs/schemas/generation_context_closure_report.schema.json"
            ),
            "trace_exchange": "docs/schemas/trace_exchange.schema.json",
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "context_text_disclosed": False,
            "report_uses_hashes_trace_ids_and_boundary_booleans": True,
        },
        "issues": issue_list,
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


def validate_source_boundary_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "source_boundary_rows",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source boundary field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SOURCE_BOUNDARY_REPORT_VERSION:
        errors.append("source boundary report version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "answer_hash",
        "trace_hash",
        "generation_context_closure_report_hash",
    ):
        if key not in report.get("event", {}):
            errors.append(f"missing source boundary event field: {key}")
    for row in report.get("source_boundary_rows", []):
        for key in (
            "context_block_id",
            "context_block_hash",
            "source_access_id",
            "source_access_span_id",
            "chunk_id",
            "work_id",
            "content_hash",
            "source_access_in_trace",
            "span_matches_context",
            "boundary_profile",
            "source_role",
            "evidence_role_declared",
            "control_channel_blocked",
            "instruction_channel_blocked",
            "source_cannot_modify_attribution",
            "source_cannot_modify_payout",
            "content_hash_bound",
            "content_hash_matches_context",
            "packet_hash_matches_profile",
            "source_boundary_closed",
            "source_boundary_hash",
        ):
            if key not in row:
                errors.append(f"missing source boundary row field: {key}")
    return errors


def verify_source_boundary_report(
    report: dict[str, Any],
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify source-boundary isolation against trace and context artifacts."""

    errors = validate_source_boundary_report_shape(report)
    if errors:
        return errors
    if verify_trace_exchange(trace_exchange):
        errors.append("source boundary trace exchange is not self-verifying")
    errors.extend(
        f"source verification report: {error}"
        for error in validate_source_verification_report_shape(
            source_verification_report
        )
    )
    errors.extend(
        f"generation context closure report: {error}"
        for error in validate_generation_context_closure_report_shape(
            generation_context_closure_report
        )
    )
    if answer_claim_coverage_report is not None:
        errors.extend(
            f"generation context closure: {error}"
            for error in verify_generation_context_closure_report(
                generation_context_closure_report,
                trace_exchange=trace_exchange,
                source_verification_report=source_verification_report,
                answer_claim_coverage_report=answer_claim_coverage_report,
                signing_secret=signing_secret,
            )
        )
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("source boundary report hash is not reproducible")
    expected = make_source_boundary_report(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        generation_context_closure_report=generation_context_closure_report,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "source_boundary_rows",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source boundary {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("source boundary report hash does not match replay")
    summary = report.get("summary", {})
    if summary.get("status") != "verified":
        errors.append("source boundary report status is not verified")
    if summary.get("all_context_blocks_boundary_isolated") is not True:
        errors.append("source boundary has non-isolated context blocks")
    if report.get("issues"):
        errors.append("source boundary report contains issues")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source boundary report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source boundary report signature is invalid")
    return errors
