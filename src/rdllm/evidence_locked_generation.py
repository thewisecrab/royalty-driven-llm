"""Evidence-locked generation reports for RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

EVIDENCE_LOCKED_GENERATION_VERSION = "rdllm-evidence-locked-generation/v1"
EVIDENCE_LOCKED_GENERATION_SCHEMA = (
    "docs/schemas/evidence_locked_generation.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L82"

DECLARED_HASH_FIELDS = (
    "report_hash",
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


def _footer_rows_by_label(
    rendered_attribution_audit: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("label", "")): row
        for row in rendered_attribution_audit.get("parsed_markdown", {}).get(
            "source_footer_rows", []
        )
        if row.get("label")
    }


def _claim_evidence_rows_by_index(
    rendered_attribution_audit: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    return {
        int(row.get("claim_index", 0) or 0): row
        for row in rendered_attribution_audit.get("parsed_markdown", {}).get(
            "claim_evidence_rows", []
        )
        if row.get("claim_index")
    }


def _body_marker_labels(rendered_attribution_audit: dict[str, Any]) -> set[str]:
    return {
        str(row.get("label", ""))
        for row in rendered_attribution_audit.get("parsed_markdown", {}).get(
            "source_marker_rows", []
        )
        if row.get("label")
    }


def _context_rows_by_claim(
    generation_context_closure_report: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    return {
        int(row.get("claim_index", 0) or 0): row
        for row in generation_context_closure_report.get("claim_context_rows", [])
        if row.get("claim_index")
    }


def _prefix_matches(value: str, prefix: str) -> bool:
    return bool(value and prefix and value.startswith(prefix))


def _lock_rows(
    *,
    answer_claim_coverage_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
    rendered_attribution_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    footer_by_label = _footer_rows_by_label(rendered_attribution_audit)
    claim_evidence_by_index = _claim_evidence_rows_by_index(rendered_attribution_audit)
    body_labels = _body_marker_labels(rendered_attribution_audit)
    context_by_claim = _context_rows_by_claim(generation_context_closure_report)
    rows: list[dict[str, Any]] = []

    for unit in answer_claim_coverage_report.get("answer_units", []):
        if unit.get("requires_support") is not True:
            continue
        claim_index = int(unit.get("matched_claim_index", 0) or 0)
        source_label = str(unit.get("matched_source_label", ""))
        evidence_prefix = str(unit.get("matched_evidence_span_prefix", ""))
        context = context_by_claim.get(claim_index, {})
        footer = footer_by_label.get(source_label, {})
        rendered_claim = claim_evidence_by_index.get(claim_index, {})
        footer_prefixes = [str(value) for value in footer.get("evidence_span_prefixes", [])]
        context_evidence_hash = str(context.get("evidence_span_hash", ""))
        row = {
            "unit_index": int(unit.get("unit_index", 0) or 0),
            "unit_hash": str(unit.get("unit_hash", "")),
            "unit_text_hash": str(unit.get("text_hash", "")),
            "claim_index": claim_index,
            "claim_hash": str(context.get("claim_hash", unit.get("text_hash", ""))),
            "source_label": source_label,
            "evidence_span_prefix": evidence_prefix,
            "matched_context_block_id": str(
                context.get("matched_context_block_id", "")
            ),
            "matched_source_access_id": str(
                context.get("matched_source_access_id", "")
            ),
            "work_id": str(context.get("work_id", "")),
            "chunk_id": str(context.get("chunk_id", "")),
            "content_hash": str(context.get("content_hash", "")),
            "context_closed": context.get("context_closed") is True,
            "retrieval_context_allowed": (
                context.get("retrieval_context_allowed") is True
            ),
            "answer_surface_covered": unit.get("covered") is True
            and context.get("answer_surface_covered") is True,
            "footer_source_visible": bool(footer),
            "footer_evidence_prefix_bound": evidence_prefix in footer_prefixes,
            "body_source_marker_visible": source_label in body_labels,
            "rendered_claim_evidence_bound": (
                rendered_claim.get("source_label") == source_label
                and rendered_claim.get("evidence_span_prefix") == evidence_prefix
            ),
            "context_evidence_prefix_bound": _prefix_matches(
                context_evidence_hash,
                evidence_prefix,
            ),
        }
        row["lock_satisfied"] = all(
            row[key]
            for key in (
                "context_closed",
                "retrieval_context_allowed",
                "answer_surface_covered",
                "footer_source_visible",
                "footer_evidence_prefix_bound",
                "body_source_marker_visible",
                "rendered_claim_evidence_bound",
                "context_evidence_prefix_bound",
            )
        )
        row["lock_row_hash"] = hash_payload(row)
        rows.append(row)

    return sorted(rows, key=lambda row: (row["unit_index"], row["claim_index"]))


def make_evidence_locked_generation_report(
    *,
    response_envelope: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    rendered_attribution_audit: dict[str, Any],
    training_memory_provenance: dict[str, Any],
    lock_created_at: str | None = None,
    generation_started_at: str | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report proving generation committed to evidence before emission."""

    response = response_envelope.get("response", {})
    created = created_at or now_iso()
    lock_created = lock_created_at or created
    generation_started = generation_started_at or created
    rows = _lock_rows(
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        rendered_attribution_audit=rendered_attribution_audit,
    )
    support_required_count = int(
        answer_claim_coverage_report.get("summary", {}).get(
            "support_required_unit_count",
            0,
        )
        or 0
    )
    footer_labels = set(_footer_rows_by_label(rendered_attribution_audit))
    locked_labels = {str(row["source_label"]) for row in rows if row["lock_satisfied"]}
    checks = {
        "lock_created_before_generation": lock_created <= generation_started,
        "response_envelope_verified": response_envelope.get("summary", {}).get("status")
        == "verified",
        "rendered_output_hash_matches_coverage": answer_claim_coverage_report.get(
            "event", {}
        ).get("rendered_output_hash")
        == response.get("rendered_output_hash"),
        "rendered_output_hash_matches_audit": rendered_attribution_audit.get(
            "displayed_response", {}
        ).get("rendered_output_hash")
        == response.get("rendered_output_hash"),
        "answer_claim_coverage_verified": answer_claim_coverage_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and answer_claim_coverage_report.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L59",
        "generation_context_closure_verified": generation_context_closure_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and generation_context_closure_report.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L60",
        "citation_footer_contract_verified": citation_footer_contract.get(
            "summary", {}
        ).get("status")
        == "verified",
        "rendered_attribution_audit_ready": rendered_attribution_audit.get(
            "summary", {}
        ).get("status")
        == "ready"
        and rendered_attribution_audit.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L80",
        "training_memory_provenance_ready": training_memory_provenance.get(
            "summary", {}
        ).get("status")
        == "ready"
        and training_memory_provenance.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L81"
        and int(
            training_memory_provenance.get("summary", {}).get(
                "hidden_memory_span_count",
                0,
            )
            or 0
        )
        == 0,
        "every_support_required_unit_locked": len(rows) == support_required_count
        and all(row["lock_satisfied"] for row in rows),
        "every_footer_source_has_lock": footer_labels.issubset(locked_labels),
        "input_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                response_envelope,
                answer_claim_coverage_report,
                generation_context_closure_report,
                citation_footer_contract,
                rendered_attribution_audit,
                training_memory_provenance,
            )
        ),
    }
    report = {
        "report_version": EVIDENCE_LOCKED_GENERATION_VERSION,
        "issuer": issuer,
        "created_at": created,
        "lock_policy": {
            "profile": "rdllm-evidence-locked-generation-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L81",
            "pre_generation_lock_required": True,
            "post_hoc_citation_rationalization_blocked": True,
            "raw_answer_text_forbidden": True,
            "raw_source_text_forbidden": True,
            "raw_context_text_forbidden": True,
        },
        "generation_window": {
            "lock_created_at": lock_created,
            "generation_started_at": generation_started,
            "lock_root": hash_payload(rows),
            "lock_count": len(rows),
        },
        "response": {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "source_labels": list(response.get("source_labels", [])),
        },
        "artifact_bindings": {
            "response_envelope_hash": _declared_hash(response_envelope),
            "answer_claim_coverage_report_hash": _declared_hash(
                answer_claim_coverage_report
            ),
            "generation_context_closure_report_hash": _declared_hash(
                generation_context_closure_report
            ),
            "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
            "rendered_attribution_audit_hash": _declared_hash(
                rendered_attribution_audit
            ),
            "training_memory_provenance_hash": _declared_hash(
                training_memory_provenance
            ),
        },
        "evidence_lock_rows": rows,
        "checks": checks,
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "support_required_unit_count": support_required_count,
            "evidence_lock_count": len(rows),
            "satisfied_lock_count": sum(1 for row in rows if row["lock_satisfied"]),
            "footer_source_count": len(footer_labels),
            "locked_footer_source_count": len(footer_labels & locked_labels),
            "post_hoc_rationalization_blocked": all(checks.values()),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "context_text_disclosed": False,
            "prompt_text_disclosed": False,
            "claim_text_disclosed": False,
            "stores_hashes_ids_and_counts_not_text": True,
        },
        "schemas": {
            "evidence_locked_generation": EVIDENCE_LOCKED_GENERATION_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "answer_claim_coverage_report": "docs/schemas/answer_claim_coverage_report.schema.json",
            "generation_context_closure_report": "docs/schemas/generation_context_closure_report.schema.json",
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "training_memory_provenance": "docs/schemas/training_memory_provenance.schema.json",
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


def validate_evidence_locked_generation_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "lock_policy",
        "generation_window",
        "response",
        "artifact_bindings",
        "evidence_lock_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence locked generation field: {key}")
    if errors:
        return errors
    if report.get("report_version") != EVIDENCE_LOCKED_GENERATION_VERSION:
        errors.append("evidence locked generation version is unsupported")
    if report.get("lock_policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence locked generation target certification level is unsupported")
    for key in (
        "lock_created_at",
        "generation_started_at",
        "lock_root",
        "lock_count",
    ):
        if key not in report.get("generation_window", {}):
            errors.append(f"missing evidence lock window field: {key}")
    for key in (
        "response_envelope_hash",
        "answer_claim_coverage_report_hash",
        "generation_context_closure_report_hash",
        "citation_footer_contract_hash",
        "rendered_attribution_audit_hash",
        "training_memory_provenance_hash",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing evidence locked generation binding: {key}")
    if "evidence_locked_generation" not in report.get("schemas", {}):
        errors.append("missing evidence locked generation schema")
    return errors


def verify_evidence_locked_generation_report(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    rendered_attribution_audit: dict[str, Any],
    training_memory_provenance: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an evidence-locked generation report against public proof inputs."""

    errors = validate_evidence_locked_generation_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("evidence locked generation hash is not reproducible")
    expected = make_evidence_locked_generation_report(
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        citation_footer_contract=citation_footer_contract,
        rendered_attribution_audit=rendered_attribution_audit,
        training_memory_provenance=training_memory_provenance,
        lock_created_at=report.get("generation_window", {}).get(
            "lock_created_at",
            "",
        ),
        generation_started_at=report.get("generation_window", {}).get(
            "generation_started_at",
            "",
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "lock_policy",
        "generation_window",
        "response",
        "artifact_bindings",
        "evidence_lock_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence locked generation {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("evidence locked generation hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("evidence locked generation status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"evidence locked generation check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence locked generation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence locked generation signature is invalid")
    return errors
