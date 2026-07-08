"""Generation-context closure reports for RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.answer_coverage import (
    validate_answer_claim_coverage_report_shape,
)
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.source_verification import validate_source_verification_report_shape
from rdllm.telemetry import verify_trace_exchange

GENERATION_CONTEXT_CLOSURE_VERSION = "rdllm-generation-context-closure-report/v1"
GENERATION_CONTEXT_CLOSURE_SCHEMA = (
    "docs/schemas/generation_context_closure_report.schema.json"
)
GENERATION_CONTEXT_POLICY_VERSION = "rdllm-generation-context-closure-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L60"

CONTEXT_ACCESS_USES = {"retrieval", "generation_context"}


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
            "access_type": str(attrs.get("rdllm.source.access_type", "")),
            "use": str(attrs.get("rdllm.source.use", "")),
            "decision_status": str(attrs.get("rdllm.decision.status", "")),
            "policy_allowed": attrs.get("rdllm.policy.allowed") is True,
            "registry_allowed": attrs.get("rdllm.registry.allowed") is True,
            "rank": int(attrs.get("rdllm.source.rank", 0) or 0),
        }
    return rows


def _source_claims(source_verification_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in source_verification_report.get("claims", [])
        if claim.get("supported") is True and claim.get("materialized") is True
    ]


def _answer_covered_claim_indexes(
    answer_claim_coverage_report: dict[str, Any] | None,
) -> set[int]:
    return {
        int(row.get("matched_claim_index", 0) or 0)
        for row in (answer_claim_coverage_report or {}).get("answer_units", [])
        if row.get("requires_support") is True and row.get("covered") is True
    }


def derive_generation_context_blocks(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Derive a redacted context manifest from source-access trace spans.

    Real deployments should capture equivalent rows at the serving gateway before
    the model call. The reference implementation derives them from trace spans so
    the closure verifier can be exercised with the local proof pack.
    """

    accesses = _trace_accesses(trace_exchange)
    claims_by_chunk: dict[str, list[dict[str, Any]]] = {}
    for claim in _source_claims(source_verification_report):
        claims_by_chunk.setdefault(str(claim.get("chunk_id", "")), []).append(claim)

    blocks: list[dict[str, Any]] = []
    for access_id, access in sorted(
        accesses.items(),
        key=lambda item: (item[1]["rank"], item[0]),
    ):
        if access["decision_status"] != "allowed":
            continue
        if access["use"] not in CONTEXT_ACCESS_USES:
            continue
        chunk_claims = claims_by_chunk.get(access["chunk_id"], [])
        row = {
            "context_block_id": f"ctx:{access_id}",
            "block_index": len(blocks) + 1,
            "source_access_id": access_id,
            "source_access_span_id": access["span_id"],
            "chunk_id": access["chunk_id"],
            "work_id": access["work_id"],
            "creator_id": access["creator_id"],
            "content_hash": access["content_hash"],
            "access_type": access["access_type"],
            "use": access["use"],
            "decision_status": access["decision_status"],
            "policy_allowed": access["policy_allowed"],
            "registry_allowed": access["registry_allowed"],
            "context_text_hash": "",
            "included_claim_hashes": sorted(
                str(claim.get("claim_hash", "")) for claim in chunk_claims
            ),
            "included_evidence_span_hashes": sorted(
                str(claim.get("evidence_span_hash", "")) for claim in chunk_claims
            ),
        }
        row["context_block_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "context_block_hash"}
        )
        blocks.append(row)
    return blocks


def _normalise_context_blocks(context_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, block in enumerate(context_blocks, start=1):
        row = {
            "context_block_id": str(
                block.get("context_block_id", f"ctx:{index}")
            ),
            "block_index": int(block.get("block_index", index) or index),
            "source_access_id": str(block.get("source_access_id", "")),
            "source_access_span_id": str(block.get("source_access_span_id", "")),
            "chunk_id": str(block.get("chunk_id", "")),
            "work_id": str(block.get("work_id", "")),
            "creator_id": str(block.get("creator_id", "")),
            "content_hash": str(block.get("content_hash", "")),
            "access_type": str(block.get("access_type", "")),
            "use": str(block.get("use", "")),
            "decision_status": str(block.get("decision_status", "")),
            "policy_allowed": block.get("policy_allowed") is True,
            "registry_allowed": block.get("registry_allowed") is True,
            "context_text_hash": str(block.get("context_text_hash", "")),
            "included_claim_hashes": sorted(
                str(value) for value in block.get("included_claim_hashes", [])
            ),
            "included_evidence_span_hashes": sorted(
                str(value)
                for value in block.get("included_evidence_span_hashes", [])
            ),
        }
        row["context_block_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["block_index"], row["context_block_id"]))


def _artifact_bindings(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "trace_exchange_hash": _declared_hash(trace_exchange),
        "source_verification_report_hash": _declared_hash(
            source_verification_report
        ),
        "answer_claim_coverage_report_hash": _declared_hash(
            answer_claim_coverage_report
        ),
        "trace_exchange_bound": bool(trace_exchange),
        "source_verification_bound": bool(source_verification_report),
        "answer_claim_coverage_bound": bool(answer_claim_coverage_report),
    }


def _claim_context_rows(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None,
    context_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accesses = _trace_accesses(trace_exchange)
    content_hash_by_chunk = {
        str(source.get("chunk_id", "")): str(source.get("content_hash", ""))
        for source in source_verification_report.get("sources", [])
    }
    blocks_by_chunk = {}
    for block in context_blocks:
        blocks_by_chunk.setdefault(str(block.get("chunk_id", "")), []).append(block)
    covered_indexes = _answer_covered_claim_indexes(answer_claim_coverage_report)
    rows: list[dict[str, Any]] = []
    for claim in _source_claims(source_verification_report):
        claim_index = int(claim.get("claim_index", 0) or 0)
        claim_hash = str(claim.get("claim_hash", ""))
        evidence_hash = str(claim.get("evidence_span_hash", ""))
        claim_content_hash = content_hash_by_chunk.get(
            str(claim.get("chunk_id", "")),
            str(claim.get("content_hash", "")),
        )
        matched_block: dict[str, Any] = {}
        for block in blocks_by_chunk.get(str(claim.get("chunk_id", "")), []):
            if (
                evidence_hash
                and evidence_hash in block.get("included_evidence_span_hashes", [])
                and claim_hash in block.get("included_claim_hashes", [])
            ):
                matched_block = block
                break
        access = accesses.get(str(matched_block.get("source_access_id", "")), {})
        access_in_trace = bool(access)
        retrieval_context_allowed = (
            access_in_trace
            and access.get("decision_status") == "allowed"
            and access.get("policy_allowed") is True
            and access.get("registry_allowed") is True
            and access.get("use") in CONTEXT_ACCESS_USES
            and access.get("chunk_id") == claim.get("chunk_id")
            and access.get("content_hash") == claim_content_hash
        )
        answer_surface_covered = (
            not answer_claim_coverage_report or claim_index in covered_indexes
        )
        row = {
            "claim_index": claim_index,
            "claim_hash": claim_hash,
            "source_label": str(claim.get("source_label", "")),
            "chunk_id": str(claim.get("chunk_id", "")),
            "work_id": str(claim.get("work_id", "")),
            "content_hash": claim_content_hash,
            "evidence_span_hash": evidence_hash,
            "matched_context_block_id": str(
                matched_block.get("context_block_id", "")
            ),
            "matched_source_access_id": str(
                matched_block.get("source_access_id", "")
            ),
            "source_access_in_trace": access_in_trace,
            "retrieval_context_allowed": retrieval_context_allowed,
            "evidence_span_in_context": bool(matched_block),
            "answer_surface_covered": answer_surface_covered,
        }
        row["context_closed"] = (
            row["source_access_in_trace"]
            and row["retrieval_context_allowed"]
            and row["evidence_span_in_context"]
            and row["answer_surface_covered"]
        )
        row["claim_context_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(
    *,
    claim_rows: list[dict[str, Any]],
    bindings: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    for row in claim_rows:
        if row["context_closed"] is not True:
            issues.append(
                f"claim C{row['claim_index']} is not closed over generation context"
            )
    for name in ("trace_exchange", "source_verification", "answer_claim_coverage"):
        if bindings.get(f"{name}_bound") is not True:
            issues.append(f"{name.replace('_', ' ')} is not bound")
    return issues


def make_generation_context_closure_report(
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None,
    context_blocks: list[dict[str, Any]] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public proof that verified claims were in generation context."""

    blocks = _normalise_context_blocks(
        context_blocks
        if context_blocks is not None
        else derive_generation_context_blocks(
            trace_exchange=trace_exchange,
            source_verification_report=source_verification_report,
        )
    )
    bindings = _artifact_bindings(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
    )
    claim_rows = _claim_context_rows(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        context_blocks=blocks,
    )
    issue_list = _issues(claim_rows=claim_rows, bindings=bindings)
    event = source_verification_report.get("event", {})
    report = {
        "report_version": GENERATION_CONTEXT_CLOSURE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": GENERATION_CONTEXT_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "requires_pre_generation_context_manifest": True,
            "requires_trace_source_access": True,
            "requires_answer_claim_coverage": True,
            "allowed_context_uses": sorted(CONTEXT_ACCESS_USES),
        },
        "event": {
            "event_id": event.get("event_id", ""),
            "event_hash": event.get("event_hash", ""),
            "rendered_output_hash": event.get("rendered_output_hash", ""),
            "answer_hash": event.get("answer_hash", ""),
            "trace_hash": trace_exchange.get("trace_hash", ""),
        },
        "artifact_bindings": bindings,
        "context_blocks": blocks,
        "claim_context_rows": claim_rows,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "context_block_count": len(blocks),
            "supported_claim_count": len(claim_rows),
            "context_closed_claim_count": sum(
                1 for row in claim_rows if row["context_closed"]
            ),
            "missing_context_claim_count": sum(
                1 for row in claim_rows if not row["context_closed"]
            ),
            "all_supported_claims_in_generation_context": all(
                row["context_closed"] for row in claim_rows
            )
            if claim_rows
            else True,
            "issue_count": len(issue_list),
        },
        "commitments": {
            "context_block_root": hash_payload(blocks),
            "claim_context_root": hash_payload(claim_rows),
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
        },
        "schemas": {
            "generation_context_closure_report": GENERATION_CONTEXT_CLOSURE_SCHEMA,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "context_text_disclosed": False,
            "report_uses_hashes_and_trace_ids": True,
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


def validate_generation_context_closure_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "context_blocks",
        "claim_context_rows",
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
            errors.append(f"missing generation context closure field: {key}")
    if errors:
        return errors
    if report.get("report_version") != GENERATION_CONTEXT_CLOSURE_VERSION:
        errors.append("generation context closure report version is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing generation context closure event field: {key}")
    for row in report.get("context_blocks", []):
        for key in (
            "context_block_id",
            "source_access_id",
            "chunk_id",
            "content_hash",
            "included_evidence_span_hashes",
            "context_block_hash",
        ):
            if key not in row:
                errors.append(f"missing generation context block field: {key}")
    for row in report.get("claim_context_rows", []):
        for key in (
            "claim_index",
            "claim_hash",
            "evidence_span_hash",
            "matched_context_block_id",
            "source_access_in_trace",
            "retrieval_context_allowed",
            "evidence_span_in_context",
            "answer_surface_covered",
            "context_closed",
            "claim_context_hash",
        ):
            if key not in row:
                errors.append(f"missing generation claim context field: {key}")
    return errors


def verify_generation_context_closure_report(
    report: dict[str, Any],
    *,
    trace_exchange: dict[str, Any],
    source_verification_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None,
    context_blocks: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify generation-context closure against public trace and proof artifacts."""

    errors = validate_generation_context_closure_report_shape(report)
    if errors:
        return errors
    if verify_trace_exchange(trace_exchange):
        errors.append("generation context trace exchange is not self-verifying")
    errors.extend(
        f"source verification report: {error}"
        for error in validate_source_verification_report_shape(
            source_verification_report
        )
    )
    if answer_claim_coverage_report:
        errors.extend(
            f"answer coverage report: {error}"
            for error in validate_answer_claim_coverage_report_shape(
                answer_claim_coverage_report
            )
        )
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("generation context closure report hash is not reproducible")
    expected = make_generation_context_closure_report(
        trace_exchange=trace_exchange,
        source_verification_report=source_verification_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        context_blocks=context_blocks
        if context_blocks is not None
        else report.get("context_blocks", []),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "context_blocks",
        "claim_context_rows",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"generation context closure {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("generation context closure report hash does not match replay")
    summary = report.get("summary", {})
    if summary.get("status") != "verified":
        errors.append("generation context closure report status is not verified")
    if summary.get("all_supported_claims_in_generation_context") is not True:
        errors.append("generation context closure has claims outside context")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("generation context closure report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("generation context closure report signature is invalid")
    return errors
