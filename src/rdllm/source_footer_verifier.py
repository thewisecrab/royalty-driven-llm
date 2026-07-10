"""Verify public RDLLM source footer artifacts and copied display text."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

from rdllm.claim_warrant import CLAIM_WARRANT_PROFILE, claim_warrant_report
from rdllm.service_response_verifier import canonical_hash
from rdllm.source_disagreement import (
    SOURCE_DISAGREEMENT_PROFILE,
    claim_source_disagreement_report,
)
from rdllm.source_footer_rendering import render_source_footer_text
from rdllm.source_usage_metrics import (
    SOURCE_USAGE_METRIC_METHOD_FIELDS,
    SOURCE_USAGE_METRIC_METHODS,
    SOURCE_USAGE_METRIC_PROFILE,
    SOURCE_USAGE_METRIC_SCOPE,
)
from rdllm.text import stable_hash


DATA_PACKAGE = "rdllm.data"
SOURCE_FOOTER_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "service_source_footer_verification.schema.json",
)
FOOTER_SCHEMA = "rdllm-service-source-footer/v1"
VERIFICATION_SCHEMA = "rdllm-service-source-footer-verification/v1"
MONEY_ZERO = Decimal("0")
GROUNDING_LINE = re.compile(
    r"^Grounding: (?P<supported>\d+)/(?P<total>\d+) claims supported; "
    r"status=(?P<status>[a-z_]+)\.$"
)


def load_source_footer_verification_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(
        *SOURCE_FOOTER_VERIFICATION_SCHEMA_RESOURCE
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _hash_without_hash_field(row: dict[str, Any], field: str) -> str:
    return canonical_hash({key: value for key, value in row.items() if key != field})


def _decimal_or_none(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _source_verification_handle(
    *,
    event_id: str,
    label: str,
    content_hash: str,
) -> str:
    return f"rdllm://verify/source-footer/{event_id}/{label}/{content_hash[:12]}"


def _source_row_has_usage_metric_provenance(row: dict[str, Any]) -> bool:
    if row.get("usage_metric_profile") != SOURCE_USAGE_METRIC_PROFILE:
        return False
    if row.get("usage_metric_scope") != SOURCE_USAGE_METRIC_SCOPE:
        return False
    return all(
        row.get(field) == SOURCE_USAGE_METRIC_METHODS[metric]
        for metric, field in SOURCE_USAGE_METRIC_METHOD_FIELDS.items()
    )


def _claim_row_has_valid_warrant_strength(row: dict[str, Any]) -> bool:
    claim_preview = row.get("claim_preview")
    evidence_preview = row.get("evidence_preview")
    if not isinstance(claim_preview, str) or not claim_preview:
        return False
    if stable_hash(claim_preview) != row.get("claim_hash"):
        return False
    if not isinstance(evidence_preview, str):
        return False
    expected = claim_warrant_report(
        claim=claim_preview,
        evidence=evidence_preview,
        supported=row.get("supported") is True,
    )
    return (
        row.get("claim_warrant_profile") == expected["claim_warrant_profile"]
        and row.get("claim_force_flags") == expected["claim_force_flags"]
        and row.get("evidence_force_flags") == expected["evidence_force_flags"]
        and row.get("warrant_mismatch_flags") == expected["warrant_mismatch_flags"]
        and row.get("warrant_strength_status")
        == expected["warrant_strength_status"]
        and row.get("warrant_strength_status") == "passed"
    )


def _claim_row_has_valid_source_disagreement(
    row: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> bool:
    claim_preview = row.get("claim_preview")
    if not isinstance(claim_preview, str) or not claim_preview:
        return False
    expected = claim_source_disagreement_report(
        claim=claim_preview,
        source_label=str(row.get("source_label", "")),
        source_rows=source_rows,
        supported=row.get("supported") is True,
    )
    return (
        row.get("source_disagreement_profile")
        == expected["source_disagreement_profile"]
        and row.get("agreement_source_labels")
        == expected["agreement_source_labels"]
        and row.get("disagreement_source_labels")
        == expected["disagreement_source_labels"]
        and row.get("source_disagreement_status")
        == expected["source_disagreement_status"]
        and row.get("source_disagreement_status") == "passed"
    )


def _expected_public_footer_body_lines(footer: dict[str, Any]) -> list[str]:
    source_rows = [
        row for row in footer.get("source_rows", []) if isinstance(row, dict)
    ]
    claim_rows = [row for row in footer.get("claim_rows", []) if isinstance(row, dict)]
    return render_source_footer_text(
        source_rows=source_rows,
        claim_rows=claim_rows,
        grounding_report={},
    ).splitlines()[:-1]


def _display_text_result(
    *,
    footer: dict[str, Any],
    display_text: str | None,
    display_text_path: str,
) -> tuple[str, str, list[str]]:
    if display_text is None:
        return "not_checked", "", []

    errors: list[str] = []
    footer_text = str(footer.get("rendered_text", ""))
    if footer_text not in display_text:
        errors.append("display_text: missing exact source footer")
    handles = [
        str(row.get("verification_handle", ""))
        for row in footer.get("source_rows", [])
        if isinstance(row, dict)
    ]
    missing_handles = [handle for handle in handles if handle and handle not in display_text]
    if missing_handles:
        errors.append("display_text: missing source verification handles")
    return (
        "passed" if not errors else "failed",
        canonical_hash(display_text),
        errors,
    )


def _shape_errors(footer: Any) -> list[str]:
    if not isinstance(footer, dict):
        return ["<root>: expected object"]
    errors: list[str] = []
    required = {
        "schema",
        "status",
        "event_id",
        "event_hash",
        "source_count",
        "claim_count",
        "source_rows",
        "claim_rows",
        "rendered_text",
        "public_verifier",
        "footer_hash",
    }
    for field in sorted(required - set(footer)):
        errors.append(f"<root>.{field}: missing required field")
    if footer.get("schema") != FOOTER_SCHEMA:
        errors.append(f"<root>.schema: expected {FOOTER_SCHEMA!r}")
    if not isinstance(footer.get("event_id", ""), str) or not footer.get("event_id"):
        errors.append("<root>.event_id: expected non-empty string")
    if not _is_hash(footer.get("event_hash")):
        errors.append("<root>.event_hash: expected SHA-256 hex string")
    if not _is_hash(footer.get("footer_hash")):
        errors.append("<root>.footer_hash: expected SHA-256 hex string")
    if not isinstance(footer.get("source_rows"), list):
        errors.append("<root>.source_rows: expected array")
    if not isinstance(footer.get("claim_rows"), list):
        errors.append("<root>.claim_rows: expected array")
    if not isinstance(footer.get("public_verifier"), dict):
        errors.append("<root>.public_verifier: expected object")
    return errors


def verify_source_footer(
    footer: dict[str, Any],
    *,
    display_text: str | None = None,
    display_text_path: str = "",
) -> dict[str, Any]:
    errors = _shape_errors(footer)
    if not isinstance(footer, dict):
        return {
            "schema": VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": errors,
            "footer_status": "unknown",
            "event_id": "",
            "event_hash": "",
            "footer_hash": "",
            "display_text_status": "not_checked" if display_text is None else "failed",
            "display_text_hash": "" if display_text is None else canonical_hash(display_text),
            "display_text_path": display_text_path,
            "source_count": 0,
            "claim_count": 0,
            "verified_source_count": 0,
            "supported_claim_count": 0,
            "verification_handle_count": 0,
            "source_usage_metric_profile": SOURCE_USAGE_METRIC_PROFILE,
            "source_usage_metric_scope": SOURCE_USAGE_METRIC_SCOPE,
            "source_usage_metric_methods": SOURCE_USAGE_METRIC_METHODS,
            "source_usage_metric_provenance_count": 0,
            "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
            "claim_warrant_strength_count": 0,
            "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
            "claim_source_disagreement_count": 0,
            "public_footer_ready": False,
            "copied_display_footer_ready": False,
            "row_hash_status": "failed",
            "claim_hash_status": "failed",
            "handle_status": "failed",
            "source_usage_metric_provenance_status": "failed",
            "claim_warrant_strength_status": "failed",
            "claim_source_disagreement_status": "failed",
            "rendered_footer_status": "failed",
            "public_verifier_status": "failed",
        }

    source_rows = [
        row for row in footer.get("source_rows", []) if isinstance(row, dict)
    ]
    claim_rows = [row for row in footer.get("claim_rows", []) if isinstance(row, dict)]
    supported_claim_rows = [row for row in claim_rows if row.get("supported") is True]
    verified_source_count = sum(
        1 for row in source_rows if row.get("confidence") == "verified"
    )
    verification_handle_count = sum(
        1 for row in source_rows if row.get("verification_handle")
    )
    source_usage_metric_provenance_count = sum(
        1 for row in source_rows if _source_row_has_usage_metric_provenance(row)
    )
    claim_warrant_strength_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_has_valid_warrant_strength(row)
    )
    claim_source_disagreement_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_has_valid_source_disagreement(row, source_rows)
    )
    event_id = str(footer.get("event_id", ""))
    event_hash = str(footer.get("event_hash", ""))

    if _is_hash(event_hash) and event_id != f"evt_{event_hash[:16]}":
        errors.append("event_id: does not match event hash")
    if footer.get("source_count") != len(source_rows):
        errors.append("source_count: does not match source rows")
    if footer.get("claim_count") != len(claim_rows):
        errors.append("claim_count: does not match claim rows")
    if len(source_rows) != len(footer.get("source_rows", [])):
        errors.append("source_rows: expected object items")
    if len(claim_rows) != len(footer.get("claim_rows", [])):
        errors.append("claim_rows: expected object items")

    row_hash_errors: list[str] = []
    claim_hash_errors: list[str] = []
    handle_errors: list[str] = []

    source_rows_by_label: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, row in enumerate(source_rows):
        label = row.get("label")
        if isinstance(label, str) and label:
            if label in source_rows_by_label:
                handle_errors.append(f"source_rows[{index}].label: duplicate")
            else:
                source_rows_by_label[label] = (index, row)
            if row.get("display_label") != f"[{label}]":
                handle_errors.append(f"source_rows[{index}].display_label: mismatch")
        expected_row_hash = _hash_without_hash_field(row, "row_hash")
        if row.get("row_hash") != expected_row_hash:
            row_hash_errors.append(f"source_rows[{index}].row_hash: mismatch")
        content_hash = str(row.get("content_hash", ""))
        if row.get("content_hash_prefix") != content_hash[:12]:
            row_hash_errors.append(f"source_rows[{index}].content_hash_prefix: mismatch")
        expected_handle = _source_verification_handle(
            event_id=event_id,
            label=str(label or ""),
            content_hash=content_hash,
        )
        if row.get("verification_handle") != expected_handle:
            handle_errors.append(f"source_rows[{index}].verification_handle: mismatch")

    supported_claims_by_label: dict[str, list[dict[str, Any]]] = {}
    source_labels = set(source_rows_by_label)
    for index, row in enumerate(claim_rows):
        expected_row_hash = _hash_without_hash_field(row, "row_hash")
        if row.get("row_hash") != expected_row_hash:
            claim_hash_errors.append(f"claim_rows[{index}].row_hash: mismatch")
        claim_hash = str(row.get("claim_hash", ""))
        claim_preview = row.get("claim_preview")
        if not isinstance(claim_preview, str) or not claim_preview:
            claim_hash_errors.append(f"claim_rows[{index}].claim_preview: missing")
        elif stable_hash(claim_preview) != claim_hash:
            claim_hash_errors.append(f"claim_rows[{index}].claim_hash: mismatch")
        if row.get("claim_hash_prefix") != claim_hash[:12]:
            claim_hash_errors.append(f"claim_rows[{index}].claim_hash_prefix: mismatch")
        expected_warrant = claim_warrant_report(
            claim=claim_preview if isinstance(claim_preview, str) else "",
            evidence=str(row.get("evidence_preview", "")),
            supported=row.get("supported") is True,
        )
        for field, expected_value in expected_warrant.items():
            if row.get(field) != expected_value:
                claim_hash_errors.append(f"claim_rows[{index}].{field}: mismatch")
        expected_disagreement = claim_source_disagreement_report(
            claim=claim_preview if isinstance(claim_preview, str) else "",
            source_label=str(row.get("source_label", "")),
            source_rows=source_rows,
            supported=row.get("supported") is True,
        )
        for field, expected_value in expected_disagreement.items():
            if row.get(field) != expected_value:
                claim_hash_errors.append(f"claim_rows[{index}].{field}: mismatch")
        span_hash = str(row.get("evidence_span_hash", ""))
        if row.get("evidence_span_hash_prefix") != span_hash[:12]:
            claim_hash_errors.append(
                f"claim_rows[{index}].evidence_span_hash_prefix: mismatch"
            )
        evidence_preview = row.get("evidence_preview")
        if row.get("supported"):
            label = row.get("source_label")
            if label not in source_labels:
                claim_hash_errors.append(f"claim_rows[{index}].source_label: missing")
            elif isinstance(label, str):
                supported_claims_by_label.setdefault(label, []).append(row)
            if not isinstance(evidence_preview, str) or not evidence_preview:
                claim_hash_errors.append(f"claim_rows[{index}].evidence_preview: missing")
            elif span_hash and stable_hash(evidence_preview) != span_hash:
                claim_hash_errors.append(
                    f"claim_rows[{index}].evidence_span_hash: mismatch"
                )
            start_char = row.get("evidence_start_char")
            end_char = row.get("evidence_end_char")
            if (
                not isinstance(start_char, int)
                or isinstance(start_char, bool)
                or not isinstance(end_char, int)
                or isinstance(end_char, bool)
                or start_char < 0
                or end_char < start_char
            ):
                claim_hash_errors.append(f"claim_rows[{index}].evidence_span: invalid")

    for label, (index, row) in source_rows_by_label.items():
        supported_rows = supported_claims_by_label.get(label, [])
        support_scores: list[float] = []
        for claim in supported_rows:
            try:
                support_scores.append(float(claim.get("support_score", 0.0)))
            except Exception:
                support_scores.append(0.0)
                claim_hash_errors.append("claim_rows.support_score: expected number")
        expected_supported_count = len(supported_rows)
        expected_minimum_support = (
            round(min(support_scores), 8) if support_scores else 0.0
        )
        expected_span_hashes = sorted(
            str(claim.get("evidence_span_hash", ""))
            for claim in supported_rows
            if claim.get("evidence_span_hash")
        )
        observed_span_hashes = row.get("evidence_span_hashes", [])
        if isinstance(observed_span_hashes, list):
            observed_span_hashes = sorted(str(value) for value in observed_span_hashes)
        else:
            observed_span_hashes = []
            row_hash_errors.append(f"source_rows[{index}].evidence_span_hashes: expected array")
        if row.get("supported_claim_count") != expected_supported_count:
            row_hash_errors.append(
                f"source_rows[{index}].supported_claim_count: mismatch"
            )
        if row.get("minimum_support_score") != expected_minimum_support:
            row_hash_errors.append(
                f"source_rows[{index}].minimum_support_score: mismatch"
            )
        if observed_span_hashes != expected_span_hashes:
            row_hash_errors.append(
                f"source_rows[{index}].evidence_span_hashes: mismatch"
            )
        payout = _decimal_or_none(row.get("payout", "0")) or MONEY_ZERO
        settlement_eligible = footer.get("public_verifier", {}).get(
            "settlement_instruction_eligible"
        ) is True
        expected_settlement = (
            "allocated_not_executed"
            if payout > 0 and settlement_eligible
            else "candidate_held_for_review"
            if payout > 0
            else "not_allocated"
        )
        if row.get("settlement_status") != expected_settlement:
            row_hash_errors.append(f"source_rows[{index}].settlement_status: mismatch")
        expected_why = (
            "verified_context_bound_claim_support_identity_rights_royalty"
            if row.get("confidence") == "verified"
            and payout > 0
            and settlement_eligible
            else "post_hoc_candidate_needs_review"
            if row.get("confidence") == "verified" and payout > 0
            else "claim_support_needs_review"
        )
        if row.get("why") != expected_why:
            row_hash_errors.append(f"source_rows[{index}].why: mismatch")
        if row.get("confidence") == "verified":
            for field in ("source_uri", "content_hash", "verification_handle", "evidence_preview"):
                if not row.get(field):
                    row_hash_errors.append(
                        f"source_rows[{index}].confidence: missing {field}"
                    )

    footer_hash = canonical_hash(
        {key: value for key, value in footer.items() if key != "footer_hash"}
    )
    if footer.get("footer_hash") != footer_hash:
        errors.append("footer_hash: mismatch")

    public_verifier = footer.get("public_verifier", {})
    if not isinstance(public_verifier, dict):
        public_verifier = {}
    public_verifier_errors: list[str] = []
    if public_verifier.get("event_hash") != event_hash:
        public_verifier_errors.append("public_verifier.event_hash: mismatch")
    grounding_verdict = public_verifier.get("grounding_verdict", "")
    if not isinstance(grounding_verdict, str):
        public_verifier_errors.append("public_verifier.grounding_verdict: expected string")
    elif grounding_verdict != footer.get("status"):
        public_verifier_errors.append(
            "public_verifier.grounding_verdict: does not match footer status"
        )
    attribution_gap_verdict = public_verifier.get("attribution_gap_verdict", "")
    if not isinstance(attribution_gap_verdict, str):
        public_verifier_errors.append(
            "public_verifier.attribution_gap_verdict: expected string"
        )
    if not isinstance(public_verifier.get("generation_evidence_mode"), str):
        public_verifier_errors.append(
            "public_verifier.generation_evidence_mode: expected string"
        )
    if not isinstance(public_verifier.get("settlement_status"), str):
        public_verifier_errors.append(
            "public_verifier.settlement_status: expected string"
        )
    if not isinstance(public_verifier.get("settlement_instruction_eligible"), bool):
        public_verifier_errors.append(
            "public_verifier.settlement_instruction_eligible: expected boolean"
        )

    rendered_errors: list[str] = []
    rendered_text = str(footer.get("rendered_text", ""))
    rendered_lines = rendered_text.splitlines()
    expected_body_lines = _expected_public_footer_body_lines(footer)
    if len(rendered_lines) != len(expected_body_lines) + 1:
        rendered_errors.append("rendered_text: unexpected line count")
    elif rendered_lines[:-1] != expected_body_lines:
        rendered_errors.append("rendered_text: public footer rows do not match")
    if rendered_lines:
        match = GROUNDING_LINE.match(rendered_lines[-1])
        if not match:
            rendered_errors.append("rendered_text: invalid grounding summary line")
        else:
            if int(match.group("supported")) != len(supported_claim_rows):
                rendered_errors.append("rendered_text: supported claim count mismatch")
            if int(match.group("total")) != len(claim_rows):
                rendered_errors.append("rendered_text: total claim count mismatch")
    else:
        rendered_errors.append("rendered_text: missing")

    display_text_status, display_text_hash, display_errors = _display_text_result(
        footer=footer,
        display_text=display_text,
        display_text_path=display_text_path,
    )
    readiness_errors: list[str] = []
    if footer.get("status") != "verified":
        readiness_errors.append("footer_status: expected verified")
    if len(source_rows) < 1:
        readiness_errors.append("source_rows: expected at least one source")
    elif verified_source_count != len(source_rows):
        readiness_errors.append("source_rows: all source rows must be verified")
    if len(supported_claim_rows) < 1:
        readiness_errors.append("claim_rows: expected at least one supported claim")
    if verification_handle_count != len(source_rows):
        readiness_errors.append(
            "source_rows: every source row must include a verification handle"
        )
    if source_usage_metric_provenance_count != len(source_rows):
        readiness_errors.append(
            "source_rows: every source row must include source usage metric "
            "profile, scope, and methods"
        )
    if claim_warrant_strength_count != len(supported_claim_rows):
        readiness_errors.append(
            "claim_rows: every supported claim must pass evidence-force "
            "calibration"
        )
    if claim_source_disagreement_count != len(supported_claim_rows):
        readiness_errors.append(
            "claim_rows: every supported claim must be free of visible source "
            "disagreement"
        )
    errors.extend(row_hash_errors)
    errors.extend(claim_hash_errors)
    errors.extend(handle_errors)
    errors.extend(public_verifier_errors)
    errors.extend(rendered_errors)
    errors.extend(display_errors)
    errors.extend(readiness_errors)

    row_hash_status = "passed" if not row_hash_errors else "failed"
    claim_hash_status = "passed" if not claim_hash_errors else "failed"
    handle_status = "passed" if not handle_errors else "failed"
    source_usage_metric_provenance_status = (
        "passed"
        if source_rows and source_usage_metric_provenance_count == len(source_rows)
        else "failed"
    )
    claim_warrant_strength_status = (
        "passed"
        if supported_claim_rows
        and claim_warrant_strength_count == len(supported_claim_rows)
        else "failed"
    )
    claim_source_disagreement_status = (
        "passed"
        if supported_claim_rows
        and claim_source_disagreement_count == len(supported_claim_rows)
        else "failed"
    )
    rendered_footer_status = "passed" if not rendered_errors else "failed"
    public_verifier_status = "passed" if not public_verifier_errors else "failed"
    public_footer_ready = bool(
        not errors
        and footer.get("status") == "verified"
        and len(source_rows) >= 1
        and verified_source_count == len(source_rows)
        and len(supported_claim_rows) >= 1
        and verification_handle_count == len(source_rows)
        and source_usage_metric_provenance_status == "passed"
        and claim_warrant_strength_status == "passed"
        and claim_source_disagreement_status == "passed"
    )
    copied_display_footer_ready = bool(
        public_footer_ready and display_text_status == "passed"
    )

    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "footer_status": str(footer.get("status", "unknown")),
        "event_id": event_id,
        "event_hash": event_hash,
        "footer_hash": str(footer.get("footer_hash", "")),
        "display_text_status": display_text_status,
        "display_text_hash": display_text_hash,
        "display_text_path": display_text_path,
        "source_count": len(source_rows),
        "claim_count": len(claim_rows),
        "verified_source_count": verified_source_count,
        "supported_claim_count": len(supported_claim_rows),
        "verification_handle_count": verification_handle_count,
        "source_usage_metric_profile": SOURCE_USAGE_METRIC_PROFILE,
        "source_usage_metric_scope": SOURCE_USAGE_METRIC_SCOPE,
        "source_usage_metric_methods": SOURCE_USAGE_METRIC_METHODS,
        "source_usage_metric_provenance_count": (
            source_usage_metric_provenance_count
        ),
        "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
        "claim_warrant_strength_count": claim_warrant_strength_count,
        "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
        "claim_source_disagreement_count": claim_source_disagreement_count,
        "public_footer_ready": public_footer_ready,
        "copied_display_footer_ready": copied_display_footer_ready,
        "row_hash_status": row_hash_status,
        "claim_hash_status": claim_hash_status,
        "handle_status": handle_status,
        "source_usage_metric_provenance_status": (
            source_usage_metric_provenance_status
        ),
        "claim_warrant_strength_status": claim_warrant_strength_status,
        "claim_source_disagreement_status": claim_source_disagreement_status,
        "rendered_footer_status": rendered_footer_status,
        "public_verifier_status": public_verifier_status,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"service_source_footer_verification status: {report['status']}",
        f"footer_status: {report.get('footer_status', 'unknown')}",
        f"public_footer_ready: {json.dumps(bool(report.get('public_footer_ready', False)))}",
        "copied_display_footer_ready: "
        f"{json.dumps(bool(report.get('copied_display_footer_ready', False)))}",
        f"display_text_status: {report.get('display_text_status', 'not_checked')}",
        f"display_text_hash: {report.get('display_text_hash', '')}",
        f"display_text_path: {report.get('display_text_path', '')}",
        f"event_id: {report.get('event_id', '')}",
        f"event_hash: {report.get('event_hash', '')}",
        f"footer_hash: {report.get('footer_hash', '')}",
        f"source_count: {report.get('source_count', 0)}",
        f"claim_count: {report.get('claim_count', 0)}",
        f"verified_source_count: {report.get('verified_source_count', 0)}",
        f"supported_claim_count: {report.get('supported_claim_count', 0)}",
        f"verification_handle_count: {report.get('verification_handle_count', 0)}",
        "source_usage_metric_provenance_count: "
        f"{report.get('source_usage_metric_provenance_count', 0)}",
        "source_usage_metric_provenance_status: "
        f"{report.get('source_usage_metric_provenance_status', 'unknown')}",
        "claim_warrant_strength_count: "
        f"{report.get('claim_warrant_strength_count', 0)}",
        "claim_warrant_strength_status: "
        f"{report.get('claim_warrant_strength_status', 'unknown')}",
        f"claim_warrant_profile: {report.get('claim_warrant_profile', '')}",
        "claim_source_disagreement_count: "
        f"{report.get('claim_source_disagreement_count', 0)}",
        "claim_source_disagreement_status: "
        f"{report.get('claim_source_disagreement_status', 'unknown')}",
        f"source_disagreement_profile: {report.get('source_disagreement_profile', '')}",
        f"row_hash_status: {report.get('row_hash_status', 'unknown')}",
        f"claim_hash_status: {report.get('claim_hash_status', 'unknown')}",
        f"handle_status: {report.get('handle_status', 'unknown')}",
        f"rendered_footer_status: {report.get('rendered_footer_status', 'unknown')}",
        f"public_verifier_status: {report.get('public_verifier_status', 'unknown')}",
    ]
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footer", type=Path, required=True)
    parser.add_argument(
        "--display-text",
        type=Path,
        help="Optional copied/exported answer text that should contain this footer.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    display_text: str | None = None
    display_text_path = str(args.display_text) if args.display_text else ""
    if args.display_text:
        try:
            display_text = args.display_text.read_text(encoding="utf-8")
        except Exception as exc:
            report = verify_source_footer(
                {},
                display_text="",
                display_text_path=display_text_path,
            )
            report["errors"] = [f"display_text: failed to read text: {exc}"]
            report["display_text_status"] = "failed"
            print(
                json.dumps(report, indent=2, sort_keys=True)
                if args.json
                else render_text(report)
            )
            return 1

    try:
        footer = load_json(args.footer)
    except Exception as exc:
        report = verify_source_footer(
            {},
            display_text=display_text,
            display_text_path=display_text_path,
        )
        report["errors"] = [f"footer: failed to read JSON: {exc}"]
        print(
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_text(report)
        )
        return 1

    report = verify_source_footer(
        footer,
        display_text=display_text,
        display_text_path=display_text_path,
    )
    print(
        json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
