"""Deep-research citation audit reports.

Long-form AI answers can contain convincing citation strings while the cited
pages are unreachable, irrelevant, or only weakly supportive. This module turns
rendered text citations into replayable evidence: every public marker must
resolve to a materialized source row, every claim row must cite resolved sources,
and source rows must clear link, relevance, and factual-support checks.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

DEEP_RESEARCH_CITATION_AUDIT_VERSION = "rdllm-deep-research-citation-audit/v1"
DEEP_RESEARCH_CITATION_AUDIT_SCHEMA = (
    "docs/schemas/deep_research_citation_audit.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L115"
MINIMUM_INPUT_LEVEL = "RDLLM-L103"
DEFAULT_MIN_RELEVANCE_SCORE = 0.70
DEFAULT_MIN_FACTUAL_SUPPORT_SCORE = 0.70
LINK_OK_STATUSES = {"accessible", "archived", "mirrored", "available"}
SUPPORTED_STATUSES = {"supported", "verified", "entailed"}

DECLARED_HASH_FIELDS = (
    "deep_research_citation_audit_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "rendered_attribution_audit_hash",
    "claim_source_attribution_hash",
    "source_availability_hash",
    "source_confidence_hash",
    "report_hash",
    "card_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_output",
    "answer_text",
    "output_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "raw_license_token",
    "license_server_secret",
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

MARKER_RE = re.compile(r"\[(?P<label>[A-Za-z0-9_.:-]{1,64})\](?!\()")
REFERENCE_DEF_RE = re.compile(r"^\[(?P<label>[A-Za-z0-9_.:-]{1,64})\]:\s+(?P<uri>\S+)", re.MULTILINE)


def load_deep_research_citation_audit_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a deep-research citation audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"deep_research_citation_audit_hash", "signature"}
    }


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


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(report: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _rendered_text(audit_input: dict[str, Any]) -> str:
    return str(
        audit_input.get("rendered_text")
        or audit_input.get("answer_text")
        or audit_input.get("output_text")
        or ""
    )


def _normalise_label(label: Any) -> str:
    return str(label or "").strip().strip("[]")


def _source_label(row: dict[str, Any], index: int) -> str:
    return _normalise_label(row.get("label") or row.get("source_label") or f"S{index + 1}")


def _reference_definitions(rendered_text: str) -> dict[str, str]:
    return {
        _normalise_label(match.group("label")): match.group("uri")
        for match in REFERENCE_DEF_RE.finditer(rendered_text)
    }


def _citation_markers(rendered_text: str, source_labels: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    references = _reference_definitions(rendered_text)
    for index, match in enumerate(MARKER_RE.finditer(rendered_text), start=1):
        label = _normalise_label(match.group("label"))
        after = rendered_text[match.end() : match.end() + 1]
        if after == ":":
            continue
        marker_type = "source_label" if label in source_labels else "unresolved"
        if label in references:
            marker_type = "reference_definition"
        before = rendered_text[max(0, match.start() - 80) : match.start()]
        after_context = rendered_text[match.end() : match.end() + 80]
        row = {
            "occurrence": index,
            "label": label,
            "marker": match.group(0),
            "marker_type": marker_type,
            "char_start": match.start(),
            "char_end": match.end(),
            "context_hash": stable_hash(before + match.group(0) + after_context),
            "resolved": label in source_labels,
        }
        row["marker_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _public_source_rows(audit_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(audit_input.get("source_rows", [])):
        if not isinstance(source, dict):
            continue
        label = _source_label(source, index)
        retrieval_status = str(
            source.get("retrieval_status")
            or source.get("availability_status")
            or source.get("link_status")
            or ""
        ).lower()
        content_hash = str(
            source.get("content_hash")
            or source.get("snapshot_hash")
            or stable_hash(str(source.get("source_excerpt", "")))
        )
        row = {
            "label": label,
            "title": str(source.get("title") or source.get("source_title") or ""),
            "source_uri": str(source.get("source_uri") or source.get("url") or ""),
            "archive_uri": str(source.get("archive_uri") or ""),
            "content_hash": content_hash,
            "retrieval_status": retrieval_status,
            "retrieved_at": str(source.get("retrieved_at") or source.get("fetched_at") or ""),
            "license_status": str(source.get("license_status") or source.get("rights_status") or ""),
            "claim_count_declared": int(source.get("claim_count", 0) or 0),
            "link_materialized": retrieval_status in LINK_OK_STATUSES,
        }
        row["source_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["label"])


def _artifact_bindings(audit_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "source_footer_delivery": audit_input.get("source_footer_delivery"),
        "grounded_source_footer": audit_input.get("grounded_source_footer"),
        "rendered_attribution_audit": audit_input.get("rendered_attribution_audit"),
        "claim_source_attribution_report": audit_input.get("claim_source_attribution_report"),
        "source_availability_report": audit_input.get("source_availability_report"),
        "source_confidence_report": audit_input.get("source_confidence_report"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        if artifact is None:
            continue
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(artifact)
    return bindings


def _float(row: dict[str, Any], key: str) -> float:
    try:
        return max(0.0, min(1.0, float(row.get(key, 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _claim_support_rows(
    audit_input: dict[str, Any],
    source_by_label: dict[str, dict[str, Any]],
    *,
    min_relevance_score: float,
    min_factual_support_score: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(audit_input.get("claim_rows", [])):
        if not isinstance(claim, dict):
            continue
        labels = [
            _normalise_label(label)
            for label in claim.get("citation_labels", claim.get("source_labels", []))
            if _normalise_label(label)
        ]
        relevance = _float(claim, "relevance_score")
        factual = _float(claim, "factual_support_score")
        support_status = str(claim.get("support_status") or claim.get("verdict") or "").lower()
        resolved_labels = [label for label in labels if label in source_by_label]
        row = {
            "claim_id": str(claim.get("claim_id") or f"claim_{index + 1}"),
            "claim_hash": str(claim.get("claim_hash") or stable_hash(str(claim.get("claim_text", "")))),
            "citation_labels": sorted(labels),
            "resolved_citation_labels": sorted(resolved_labels),
            "unresolved_citation_labels": sorted(set(labels) - set(resolved_labels)),
            "support_status": support_status,
            "relevance_score": relevance,
            "factual_support_score": factual,
            "evidence_span_hash": str(claim.get("evidence_span_hash") or ""),
            "source_quote_hash": str(claim.get("source_quote_hash") or claim.get("quote_hash") or ""),
            "claim_has_citation": bool(labels),
            "all_citations_resolved": bool(labels) and len(labels) == len(resolved_labels),
            "relevance_threshold_met": relevance >= min_relevance_score,
            "factual_support_threshold_met": factual >= min_factual_support_score,
            "support_status_accepted": support_status in SUPPORTED_STATUSES,
            "evidence_hashes_present": bool(
                str(claim.get("evidence_span_hash") or "")
                and str(claim.get("source_quote_hash") or claim.get("quote_hash") or "")
            ),
        }
        row["claim_supported"] = (
            row["claim_has_citation"]
            and row["all_citations_resolved"]
            and row["relevance_threshold_met"]
            and row["factual_support_threshold_met"]
            and row["support_status_accepted"]
            and row["evidence_hashes_present"]
        )
        row["claim_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["claim_id"])


def _footer_rows(
    source_rows: list[dict[str, Any]],
    marker_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    marker_counts = Counter(row["label"] for row in marker_rows if row.get("resolved"))
    claim_counts: dict[str, int] = defaultdict(int)
    support_scores: dict[str, list[float]] = defaultdict(list)
    for claim in claim_rows:
        for label in claim["resolved_citation_labels"]:
            claim_counts[label] += 1
            support_scores[label].append(
                min(claim["relevance_score"], claim["factual_support_score"])
            )
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(source_rows, start=1):
        label = source["label"]
        scores = support_scores.get(label, [])
        row = {
            "display_order": index,
            "label": label,
            "title": source["title"],
            "source_uri": source["source_uri"],
            "content_hash": source["content_hash"],
            "source_row_hash": source["source_row_hash"],
            "visible_marker_count": int(marker_counts.get(label, 0)),
            "supported_claim_count": int(claim_counts.get(label, 0)),
            "minimum_claim_support_score": round(min(scores), 8) if scores else 0.0,
            "link_materialized": source["link_materialized"],
        }
        row["footer_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_deep_research_citation_audit_report(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L115 citation audit for rendered long-form answers."""

    rendered_text = _rendered_text(audit_input)
    source_rows = _public_source_rows(audit_input)
    source_by_label = {row["label"]: row for row in source_rows}
    policy = audit_input.get("policy", {})
    min_relevance_score = float(
        policy.get("min_relevance_score", DEFAULT_MIN_RELEVANCE_SCORE)
    )
    min_factual_support_score = float(
        policy.get("min_factual_support_score", DEFAULT_MIN_FACTUAL_SUPPORT_SCORE)
    )
    marker_rows = _citation_markers(rendered_text, set(source_by_label))
    claim_rows = _claim_support_rows(
        audit_input,
        source_by_label,
        min_relevance_score=min_relevance_score,
        min_factual_support_score=min_factual_support_score,
    )
    footer_rows = _footer_rows(source_rows, marker_rows, claim_rows)
    marker_labels = {row["label"] for row in marker_rows if row.get("resolved")}
    claim_labels = {
        label
        for row in claim_rows
        for label in row.get("resolved_citation_labels", [])
    }
    citation_labels = marker_labels | claim_labels
    public_payload = {
        "source_rows": source_rows,
        "citation_marker_rows": marker_rows,
        "claim_support_rows": claim_rows,
        "footer_rows": footer_rows,
    }
    checks = {
        "rendered_text_hash_present": bool(rendered_text),
        "source_rows_present": bool(source_rows),
        "citation_markers_present": bool(marker_rows),
        "claim_rows_present": bool(claim_rows),
        "every_marker_resolves_to_materialized_source": all(
            row["resolved"] for row in marker_rows
        ),
        "every_claim_has_resolved_citations": all(
            row["claim_has_citation"] and row["all_citations_resolved"]
            for row in claim_rows
        ),
        "every_claim_is_factually_supported": all(
            row["claim_supported"] for row in claim_rows
        ),
        "every_cited_source_link_materialized": all(
            source_by_label[label]["link_materialized"]
            for label in citation_labels
            if label in source_by_label
        ),
        "footer_rows_cover_all_cited_sources": citation_labels.issubset(
            {row["label"] for row in footer_rows}
        ),
        "artifact_bindings_hash_reproducible": all(
            value is True
            for key, value in _artifact_bindings(audit_input).items()
            if key.endswith("_hash_reproducible")
        ),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_payload
        ),
    }
    report: dict[str, Any] = {
        "audit_version": DEEP_RESEARCH_CITATION_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-deep-research-citation-audit-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "citation_markers_must_resolve": True,
            "source_links_must_be_materialized": True,
            "claim_support_must_clear_thresholds": True,
            "min_relevance_score": min_relevance_score,
            "min_factual_support_score": min_factual_support_score,
        },
        "answer_binding": {
            "answer_id_hash": hash_payload(str(audit_input.get("answer_id", ""))),
            "rendered_text_hash": stable_hash(rendered_text),
            "rendered_text_length": len(rendered_text),
            "citation_marker_count": len(marker_rows),
            "claim_count": len(claim_rows),
            "source_count": len(source_rows),
        },
        "artifact_bindings": _artifact_bindings(audit_input),
        "source_rows": source_rows,
        "citation_marker_rows": marker_rows,
        "claim_support_rows": claim_rows,
        "footer_rows": footer_rows,
        "checks": checks,
        "commitments": {
            "source_row_root": hash_payload([row["source_row_hash"] for row in source_rows]),
            "citation_marker_root": hash_payload([row["marker_hash"] for row in marker_rows]),
            "claim_support_root": hash_payload([row["claim_row_hash"] for row in claim_rows]),
            "footer_row_root": hash_payload([row["footer_row_hash"] for row in footer_rows]),
            "schema": DEEP_RESEARCH_CITATION_AUDIT_SCHEMA,
        },
        "schemas": {
            "deep_research_citation_audit": DEEP_RESEARCH_CITATION_AUDIT_SCHEMA,
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "claim_source_attribution_report": "docs/schemas/claim_source_attribution_report.schema.json",
        },
        "summary": {
            "status": "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "source_count": len(source_rows),
            "citation_marker_count": len(marker_rows),
            "resolved_citation_marker_count": sum(1 for row in marker_rows if row["resolved"]),
            "claim_count": len(claim_rows),
            "supported_claim_count": sum(1 for row in claim_rows if row["claim_supported"]),
            "verified_source_count": sum(1 for row in source_rows if row["link_materialized"]),
            "footer_source_count": len(footer_rows),
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "payment_text_disclosed": False,
            "public_report_uses_hashes_scores_uris_and_titles": True,
        },
    }
    report["checks"]["private_strings_absent"] = _private_strings_absent(report, audit_input)
    report["summary"]["status"] = "ready" if all(report["checks"].values()) else "failed"
    report["deep_research_citation_audit_hash"] = hash_payload(_hashable_report(report))
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


def validate_deep_research_citation_audit_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L115 citation audit."""

    errors: list[str] = []
    required = (
        "audit_version",
        "issuer",
        "created_at",
        "policy",
        "answer_binding",
        "artifact_bindings",
        "source_rows",
        "citation_marker_rows",
        "claim_support_rows",
        "footer_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "deep_research_citation_audit_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing deep research citation audit field: {key}")
    if errors:
        return errors
    if report.get("audit_version") != DEEP_RESEARCH_CITATION_AUDIT_VERSION:
        errors.append("deep research citation audit version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("deep research citation audit target certification level is unsupported")
    if "deep_research_citation_audit" not in report.get("schemas", {}):
        errors.append("missing deep research citation audit schema")
    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append("deep research citation audit contains private field")
    return errors


def verify_deep_research_citation_audit_report(
    report: dict[str, Any],
    *,
    audit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L115 citation audit against its private replay input."""

    errors = validate_deep_research_citation_audit_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "deep_research_citation_audit_hash"
    ):
        errors.append("deep research citation audit hash is not reproducible")
    expected = make_deep_research_citation_audit_report(
        audit_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "answer_binding",
        "artifact_bindings",
        "source_rows",
        "citation_marker_rows",
        "claim_support_rows",
        "footer_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"deep research citation audit {key} does not match inputs")
    if expected.get("deep_research_citation_audit_hash") != report.get(
        "deep_research_citation_audit_hash"
    ):
        errors.append("deep research citation audit hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("deep research citation audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"deep research citation audit check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("deep research citation audit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("deep research citation audit signature is invalid")
    return errors
