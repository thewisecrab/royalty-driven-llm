"""Rendered Markdown attribution audits for user-visible RDLLM answers."""

from __future__ import annotations

import re
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

RENDERED_ATTRIBUTION_AUDIT_VERSION = "rdllm-rendered-attribution-audit/v1"
RENDERED_ATTRIBUTION_AUDIT_SCHEMA = (
    "docs/schemas/rendered_attribution_audit.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L80"

SOURCE_MARKER_RE = re.compile(r"(?<![A-Za-z0-9])\[(S[0-9]+)\](?![:A-Za-z0-9])")
FOOTER_SOURCE_RE = re.compile(
    r"^\[(S[0-9]+)\]\s+(?P<title>.*?);\s+chunk=(?P<chunk>[^;]+);\s+"
    r"uri=(?P<uri>[^;]+);\s+(?:claims=(?P<claims>[0-9]+);\s+)?"
    r"(?:confidence=(?P<confidence>[^;]+);\s+)?support=(?P<support>[0-9.]+);\s+"
    r"text_match=(?P<text_match>[0-9.]+);\s+"
    r"(?:why=(?P<why>[^;]+);\s+)?(?:payout=(?P<payout>[^;]+);\s+)?"
    r"hash=(?P<hash>[a-f0-9]+)\."
)
CLAIM_EVIDENCE_RE = re.compile(
    r"^\[C(?P<claim_index>[0-9]+)\]\s+(?P<label>S[0-9]+);\s+"
    r"(?:claim_hash=(?P<claim_hash>[a-f0-9]{12});\s+)?"
    r"(?:support=(?P<support>[0-9.]+);\s+)?"
    r"span=(?P<span>[a-f0-9]{12});\s+chars=(?P<start>[0-9]+)-(?P<end>[0-9]+)\."
)
SPAN_LIST_RE = re.compile(r"span_hashes=(?P<spans>[a-f0-9,]+)")

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


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.endswith("_hash")}


def _line_hash(line: str) -> str:
    return stable_hash(line)


def _section_lines(rendered_output: str) -> dict[str, list[str]]:
    lines = rendered_output.splitlines()
    sources_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "Sources"),
        len(lines),
    )
    claim_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "Claim Evidence"),
        len(lines),
    )
    return {
        "answer_body": lines[:sources_index],
        "source_footer": lines[sources_index + 1 : claim_index]
        if sources_index < len(lines)
        else [],
        "claim_evidence": lines[claim_index + 1 :] if claim_index < len(lines) else [],
    }


def _labels_in_lines(lines: list[str]) -> list[str]:
    labels: list[str] = []
    for line in lines:
        labels.extend(SOURCE_MARKER_RE.findall(line))
    return labels


def _source_marker_rows(body_lines: list[str]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    first_hashes: dict[str, str] = {}
    for line in body_lines:
        for label in SOURCE_MARKER_RE.findall(line):
            counts[label] = counts.get(label, 0) + 1
            first_hashes.setdefault(label, _line_hash(line))
    rows = []
    for label in sorted(counts, key=lambda value: int(value[1:])):
        row = {
            "label": label,
            "body_occurrence_count": counts[label],
            "first_body_line_hash": first_hashes.get(label, ""),
        }
        row["marker_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _source_footer_rows(source_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    current_label = ""
    for line in source_lines:
        stripped = line.strip()
        if not stripped:
            continue
        source_match = FOOTER_SOURCE_RE.match(stripped)
        if source_match:
            current_label = source_match.group(1)
            row = {
                "label": current_label,
                "title_hash": hash_payload(source_match.group("title")),
                "chunk_id": source_match.group("chunk"),
                "source_uri": source_match.group("uri"),
                "claim_count": int(source_match.group("claims") or 0),
                "confidence_level": source_match.group("confidence") or "",
                "support": source_match.group("support"),
                "text_match": source_match.group("text_match"),
                "source_rationale_code": source_match.group("why") or "",
                "payout_present": bool(source_match.group("payout")),
                "content_hash_prefix": source_match.group("hash"),
                "evidence_span_prefixes": [],
                "footer_line_hash": _line_hash(stripped),
            }
            row["source_footer_row_hash"] = hash_payload(row)
            rows.append(row)
            continue
        span_match = SPAN_LIST_RE.search(stripped)
        if span_match and current_label:
            rows[-1]["evidence_span_prefixes"] = sorted(
                span
                for span in span_match.group("spans").split(",")
                if re.fullmatch(r"[a-f0-9]{12}", span)
            )
            rows[-1]["source_footer_row_hash"] = hash_payload(rows[-1])
            continue
        if stripped.startswith("[S"):
            warnings.append(f"unparsed source footer line hash={_line_hash(stripped)}")
    return rows, warnings


def _claim_evidence_rows(claim_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for line in claim_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("Grounding:"):
            continue
        match = CLAIM_EVIDENCE_RE.match(stripped)
        if not match:
            if stripped.startswith("[C"):
                warnings.append(f"unparsed claim evidence line hash={_line_hash(stripped)}")
            continue
        row = {
            "claim_index": int(match.group("claim_index")),
            "source_label": match.group("label"),
            "claim_hash_prefix": match.group("claim_hash") or "",
            "support": match.group("support") or "",
            "evidence_span_prefix": match.group("span"),
            "start_char": int(match.group("start")),
            "end_char": int(match.group("end")),
            "claim_evidence_line_hash": _line_hash(stripped),
        }
        row["claim_evidence_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows, warnings


def _label_set(rows: list[dict[str, Any]], field: str = "label") -> set[str]:
    return {str(row.get(field, "")) for row in rows if row.get(field)}


def _coverage_pairs(answer_claim_coverage_report: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (
            str(row.get("matched_source_label", "")),
            str(row.get("matched_evidence_span_prefix", "")),
        )
        for row in answer_claim_coverage_report.get("answer_units", [])
        if row.get("requires_support") and row.get("covered")
    }


def _claim_pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(row.get("source_label", "")), str(row.get("evidence_span_prefix", "")))
        for row in rows
    }


def _footer_span_pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(row.get("label", "")), str(span))
        for row in rows
        for span in row.get("evidence_span_prefixes", [])
    }


def make_rendered_attribution_audit(
    *,
    response_envelope: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    source_availability_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    counterevidence_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Audit the exact rendered Markdown attribution surface without storing raw text."""

    response = response_envelope.get("response", {})
    rendered_output = str(response.get("rendered_output", ""))
    sections = _section_lines(rendered_output)
    source_marker_rows = _source_marker_rows(sections["answer_body"])
    source_footer_rows, source_warnings = _source_footer_rows(sections["source_footer"])
    claim_evidence_rows, claim_warnings = _claim_evidence_rows(
        sections["claim_evidence"]
    )
    body_labels = _label_set(source_marker_rows)
    footer_labels = _label_set(source_footer_rows)
    contract_labels = _label_set(citation_footer_contract.get("sources", []))
    envelope_labels = set(str(label) for label in response.get("source_labels", []))
    claim_pairs = _claim_pairs(claim_evidence_rows)
    footer_pairs = _footer_span_pairs(source_footer_rows)
    coverage_pairs = _coverage_pairs(answer_claim_coverage_report)
    availability_labels = _label_set(source_availability_report.get("sources", []))
    checks = {
        "rendered_output_hash_matches_response": response.get("rendered_output_hash")
        == stable_hash(rendered_output),
        "markdown_sources_section_present": bool(sections["source_footer"]),
        "markdown_claim_evidence_section_present": bool(sections["claim_evidence"]),
        "markdown_parser_has_no_warnings": not source_warnings and not claim_warnings,
        "body_citations_match_response_labels": body_labels == envelope_labels,
        "footer_sources_match_body_citations": footer_labels == body_labels,
        "footer_sources_match_contract_sources": footer_labels == contract_labels,
        "all_footer_rows_have_uri_and_content_hash": all(
            row.get("source_uri") and row.get("content_hash_prefix")
            for row in source_footer_rows
        ),
        "all_footer_rows_explain_source_selection": all(
            row.get("source_rationale_code") for row in source_footer_rows
        ),
        "claim_evidence_rows_cover_answer_claims": coverage_pairs <= claim_pairs,
        "claim_evidence_rows_bind_footer_spans": claim_pairs <= footer_pairs,
        "citation_footer_contract_verified": citation_footer_contract.get(
            "summary", {}
        ).get("status")
        == "verified",
        "source_availability_verified": source_availability_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and availability_labels >= footer_labels,
        "evidence_sufficiency_verified": evidence_sufficiency_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and evidence_sufficiency_report.get("summary", {}).get(
            "all_claims_have_minimal_sufficient_evidence"
        )
        is True,
        "counterevidence_adjudicated": counterevidence_report.get("summary", {}).get(
            "status"
        )
        == "verified"
        and counterevidence_report.get("summary", {}).get(
            "all_claims_counterevidence_adjudicated"
        )
        is True,
        "answer_claim_coverage_verified": answer_claim_coverage_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and answer_claim_coverage_report.get("summary", {}).get(
            "all_answer_claims_covered"
        )
        is True,
        "input_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                response_envelope,
                citation_footer_contract,
                source_availability_report,
                evidence_sufficiency_report,
                counterevidence_report,
                answer_claim_coverage_report,
            )
        ),
    }
    report = {
        "report_version": RENDERED_ATTRIBUTION_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "audit_policy": {
            "profile": "rdllm-rendered-markdown-attribution-audit/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L79",
            "parser": "deterministic-regex-markdown-source-footer-v1",
            "raw_answer_text_forbidden": True,
            "raw_source_text_forbidden": True,
            "every_inline_source_marker_must_bind_footer_source": True,
            "every_claim_span_must_bind_coverage_and_footer": True,
            "every_footer_source_must_explain_source_selection": True,
        },
        "displayed_response": {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "answer_body_hash": hash_payload(sections["answer_body"]),
            "source_footer_hash": hash_payload(sections["source_footer"]),
            "claim_evidence_hash": hash_payload(sections["claim_evidence"]),
            "line_count": len(rendered_output.splitlines()),
        },
        "parsed_markdown": {
            "source_marker_rows": source_marker_rows,
            "source_footer_rows": source_footer_rows,
            "claim_evidence_rows": claim_evidence_rows,
            "parse_warning_hashes": source_warnings + claim_warnings,
            "body_source_label_root": hash_payload(sorted(body_labels)),
            "footer_source_label_root": hash_payload(sorted(footer_labels)),
            "claim_span_root": hash_payload(sorted(claim_pairs)),
        },
        "artifact_bindings": {
            "response_envelope_hash": _declared_hash(response_envelope),
            "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
            "source_availability_report_hash": _declared_hash(
                source_availability_report
            ),
            "evidence_sufficiency_report_hash": _declared_hash(
                evidence_sufficiency_report
            ),
            "counterevidence_report_hash": _declared_hash(counterevidence_report),
            "answer_claim_coverage_report_hash": _declared_hash(
                answer_claim_coverage_report
            ),
        },
        "checks": checks,
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "body_citation_label_count": len(body_labels),
            "footer_source_count": len(source_footer_rows),
            "claim_evidence_row_count": len(claim_evidence_rows),
            "covered_claim_pair_count": len(coverage_pairs),
            "parse_warning_count": len(source_warnings) + len(claim_warnings),
            "rendered_markdown_attribution_verified": all(checks.values()),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "prompt_text_disclosed": False,
            "claim_text_disclosed": False,
            "stores_line_hashes_not_lines": True,
            "stores_source_metadata_not_source_text": True,
        },
        "schemas": {
            "rendered_attribution_audit": RENDERED_ATTRIBUTION_AUDIT_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "evidence_sufficiency_report": "docs/schemas/evidence_sufficiency_report.schema.json",
            "counterevidence_report": "docs/schemas/counterevidence_report.schema.json",
            "answer_claim_coverage_report": "docs/schemas/answer_claim_coverage_report.schema.json",
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


def validate_rendered_attribution_audit_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "audit_policy",
        "displayed_response",
        "parsed_markdown",
        "artifact_bindings",
        "checks",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing rendered attribution audit field: {key}")
    if errors:
        return errors
    if report.get("report_version") != RENDERED_ATTRIBUTION_AUDIT_VERSION:
        errors.append("rendered attribution audit version is unsupported")
    if report.get("audit_policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("rendered attribution audit target certification level is unsupported")
    for key in (
        "response_envelope_hash",
        "citation_footer_contract_hash",
        "source_availability_report_hash",
        "evidence_sufficiency_report_hash",
        "counterevidence_report_hash",
        "answer_claim_coverage_report_hash",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing rendered attribution artifact binding: {key}")
    for key in (
        "status",
        "target_certification_level",
        "body_citation_label_count",
        "footer_source_count",
        "claim_evidence_row_count",
        "covered_claim_pair_count",
        "parse_warning_count",
        "rendered_markdown_attribution_verified",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing rendered attribution summary field: {key}")
    if "rendered_attribution_audit" not in report.get("schemas", {}):
        errors.append("missing rendered attribution audit schema")
    return errors


def verify_rendered_attribution_audit(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    source_availability_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    counterevidence_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a rendered attribution audit against the displayed response proof pack."""

    errors = validate_rendered_attribution_audit_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("rendered attribution audit hash is not reproducible")
    expected = make_rendered_attribution_audit(
        response_envelope=response_envelope,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "audit_policy",
        "displayed_response",
        "parsed_markdown",
        "artifact_bindings",
        "checks",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"rendered attribution audit {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("rendered attribution audit hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("rendered attribution audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"rendered attribution audit check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("rendered attribution audit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("rendered attribution audit signature is invalid")
    return errors
