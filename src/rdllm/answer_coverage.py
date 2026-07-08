"""Answer-surface claim coverage reports for RDLLM responses."""

from __future__ import annotations

import re
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import split_sentences, stable_hash, tokenize

ANSWER_COVERAGE_VERSION = "rdllm-answer-claim-coverage-report/v1"
ANSWER_COVERAGE_SCHEMA = "docs/schemas/answer_claim_coverage_report.schema.json"
ANSWER_COVERAGE_POLICY_VERSION = "rdllm-answer-claim-coverage-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L59"

SOURCE_SECTION_HEADINGS = {"sources", "claim evidence"}
MIN_SUPPORT_TOKENS = 3


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in (
        "contract_hash",
        "report_hash",
        "card_hash",
        "envelope_hash",
        "receipt_hash",
    ):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_bindings(
    *,
    answer_card: dict[str, Any] | None,
    source_verification_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "answer_card_hash": _declared_hash(answer_card),
        "source_verification_report_hash": _declared_hash(source_verification_report),
        "evidence_sufficiency_report_hash": _declared_hash(evidence_sufficiency_report),
        "counterevidence_report_hash": _declared_hash(counterevidence_report),
        "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
        "answer_card_bound": bool(answer_card),
        "source_verification_bound": bool(source_verification_report),
        "evidence_sufficiency_bound": bool(evidence_sufficiency_report),
        "counterevidence_bound": bool(counterevidence_report),
        "citation_footer_bound": bool(citation_footer_contract),
    }


def _strip_source_marker(text: str) -> str:
    text = re.sub(r"^\[[A-Z]\d+\]\s*-?\s*", "", text.strip())
    text = re.sub(r"\s*\[[A-Z]\d+\]\s*$", "", text)
    text = re.sub(r"\s*\[[A-Z]\d+\]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_structured_footer_line(line: str, section: str) -> bool:
    if section == "sources":
        return (
            bool(re.match(r"^\[[A-Z]\d+\]\s", line))
            or line.startswith("Evidence:")
            or line.startswith("Grounding:")
        )
    if section == "claim evidence":
        return bool(re.match(r"^\[[A-Z]\d+\]\s", line))
    return False


def _answer_body_lines(rendered_output: str) -> list[str]:
    lines: list[str] = []
    section = "answer"
    for raw_line in rendered_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower() in SOURCE_SECTION_HEADINGS:
            section = line.lower()
            continue
        if section != "answer" and _is_structured_footer_line(line, section):
            continue
        lines.append(line)
    return lines


def _is_framing_line(line: str) -> bool:
    lower = line.lower()
    return (
        line.endswith(":")
        or lower.startswith("for the prompt")
        or lower.startswith("this response is blocked by rights policy")
        or lower.startswith("this response is held by ownership registry policy")
    )


def _answer_units(rendered_output: str) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for line in _answer_body_lines(rendered_output):
        if _is_framing_line(line):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        for sentence in split_sentences(line):
            normalized = _strip_source_marker(sentence)
            tokens = tokenize(normalized)
            if not tokens:
                continue
            requires_support = len(tokens) >= MIN_SUPPORT_TOKENS
            row = {
                "unit_index": len(units) + 1,
                "text_hash": stable_hash(normalized),
                "token_count": len(tokens),
                "source_markers": sorted(set(re.findall(r"\[([A-Z]\d+)\]", sentence))),
                "requires_support": requires_support,
            }
            row["unit_hash"] = hash_payload(row)
            units.append(row)
    return units


def _supported_claims_by_hash(
    source_verification_report: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for claim in (source_verification_report or {}).get("claims", []):
        claim_hash = str(claim.get("claim_hash", ""))
        if (
            claim_hash
            and claim.get("supported") is True
            and claim.get("materialized") is True
        ):
            rows[claim_hash] = claim
    return rows


def _evidence_sufficiency_hashes(
    evidence_sufficiency_report: dict[str, Any] | None,
) -> set[str]:
    return {
        str(claim.get("claim_hash", ""))
        for claim in (evidence_sufficiency_report or {}).get("claims", [])
        if claim.get("sufficient") is True and claim.get("claim_hash")
    }


def _counterevidence_free_hashes(
    counterevidence_report: dict[str, Any] | None,
) -> set[str]:
    return {
        str(claim.get("claim_hash", ""))
        for claim in (counterevidence_report or {}).get("claims", [])
        if claim.get("counterevidence_free") is True and claim.get("claim_hash")
    }


def _coverage_rows(
    *,
    rendered_output: str,
    source_verification_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    supported = _supported_claims_by_hash(source_verification_report)
    sufficient_hashes = _evidence_sufficiency_hashes(evidence_sufficiency_report)
    counterevidence_free_hashes = _counterevidence_free_hashes(counterevidence_report)
    rows: list[dict[str, Any]] = []
    for unit in _answer_units(rendered_output):
        claim = supported.get(str(unit["text_hash"]), {})
        requires_support = bool(unit["requires_support"])
        covered = (
            not requires_support
            or (
                bool(claim)
                and (
                    not evidence_sufficiency_report
                    or unit["text_hash"] in sufficient_hashes
                )
                and (
                    not counterevidence_report
                    or unit["text_hash"] in counterevidence_free_hashes
                )
            )
        )
        row = dict(unit)
        row.update(
            {
                "matched_claim_index": int(claim.get("claim_index", 0) or 0),
                "matched_source_label": str(claim.get("source_label", "")),
                "matched_evidence_span_prefix": str(
                    claim.get("evidence_span_prefix", "")
                ),
                "source_claim_materialized": bool(claim),
                "evidence_sufficient": (
                    not evidence_sufficiency_report
                    or unit["text_hash"] in sufficient_hashes
                ),
                "counterevidence_free": (
                    not counterevidence_report
                    or unit["text_hash"] in counterevidence_free_hashes
                ),
                "covered": covered,
            }
        )
        row["coverage_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "unit_hash"}
        )
        rows.append(row)
    return rows


def _issues(rows: list[dict[str, Any]], bindings: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for row in rows:
        if row["requires_support"] and not row["covered"]:
            issues.append(f"answer unit U{row['unit_index']} is not covered by a verified claim")
    for name in ("answer_card", "source_verification"):
        if bindings.get(f"{name}_bound") is not True:
            issues.append(f"{name.replace('_', ' ')} is not bound")
    return issues


def make_answer_claim_coverage_report(
    *,
    rendered_output: str,
    event_id: str,
    event_hash: str,
    answer_hash: str,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any] | None = None,
    counterevidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public proof that every factual answer sentence has a claim row."""

    rows = _coverage_rows(
        rendered_output=rendered_output,
        source_verification_report=source_verification_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
    )
    bindings = _artifact_bindings(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
    )
    issue_list = _issues(rows, bindings)
    support_required_count = sum(1 for row in rows if row["requires_support"])
    covered_count = sum(
        1 for row in rows if row["requires_support"] and row["covered"]
    )
    report = {
        "report_version": ANSWER_COVERAGE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": ANSWER_COVERAGE_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_sections_excluded": sorted(SOURCE_SECTION_HEADINGS),
            "minimum_support_tokens": MIN_SUPPORT_TOKENS,
            "requires_source_materialization": True,
            "requires_evidence_sufficiency_when_present": True,
            "requires_counterevidence_free_when_present": True,
        },
        "event": {
            "event_id": event_id,
            "event_hash": event_hash,
            "rendered_output_hash": stable_hash(rendered_output),
            "answer_hash": answer_hash,
        },
        "artifact_bindings": bindings,
        "answer_units": rows,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "answer_unit_count": len(rows),
            "support_required_unit_count": support_required_count,
            "covered_unit_count": covered_count,
            "unsupported_unit_count": support_required_count - covered_count,
            "non_claim_unit_count": len(rows) - support_required_count,
            "all_answer_claims_covered": support_required_count == covered_count,
            "issue_count": len(issue_list),
        },
        "commitments": {
            "answer_unit_root": hash_payload(rows),
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
            "rendered_output_hash": stable_hash(rendered_output),
        },
        "schemas": {
            "answer_claim_coverage_report": ANSWER_COVERAGE_SCHEMA,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "report_uses_public_output_hashes_only": True,
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


def validate_answer_claim_coverage_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "answer_units",
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
            errors.append(f"missing answer coverage field: {key}")
    if errors:
        return errors
    if report.get("report_version") != ANSWER_COVERAGE_VERSION:
        errors.append("answer coverage report version is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing answer coverage event field: {key}")
    for key in (
        "answer_card_hash",
        "source_verification_report_hash",
        "answer_card_bound",
        "source_verification_bound",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing answer coverage artifact binding: {key}")
    for row in report.get("answer_units", []):
        for key in (
            "unit_index",
            "text_hash",
            "token_count",
            "requires_support",
            "matched_claim_index",
            "source_claim_materialized",
            "covered",
            "coverage_hash",
        ):
            if key not in row:
                errors.append(f"missing answer coverage unit field: {key}")
    return errors


def verify_answer_claim_coverage_report(
    report: dict[str, Any],
    *,
    rendered_output: str,
    event_id: str,
    event_hash: str,
    answer_hash: str,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any] | None = None,
    counterevidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify answer-surface claim coverage from public response artifacts."""

    errors = validate_answer_claim_coverage_report_shape(report)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("answer coverage report hash is not reproducible")
    expected = make_answer_claim_coverage_report(
        rendered_output=rendered_output,
        event_id=event_id,
        event_hash=event_hash,
        answer_hash=answer_hash,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "answer_units",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"answer coverage report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("answer coverage report hash does not match replay")
    if report.get("summary", {}).get("status") != "verified":
        errors.append("answer coverage report status is not verified")
    if report.get("summary", {}).get("all_answer_claims_covered") is not True:
        errors.append("answer coverage report has uncovered answer claims")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("answer coverage report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("answer coverage report signature is invalid")
    return errors
