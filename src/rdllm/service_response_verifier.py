"""Verify saved RDLLM service attribution responses."""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any

from rdllm.answer_citations import (
    answer_link_uris,
    answer_citation_markers,
    claim_citation_keys,
    model_reliance_claim_markers,
    resolved_answer_link_uris,
    resolved_answer_citation_markers,
    source_citation_keys,
    unresolved_answer_link_uris,
    unresolved_answer_citation_markers,
)
from rdllm.claim_warrant import CLAIM_WARRANT_PROFILE, claim_warrant_report
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
from rdllm.text import split_sentences, stable_hash, tokenize


DATA_PACKAGE = "rdllm.data"
RESPONSE_SCHEMA_RESOURCE = ("schemas", "service_attribution_response.schema.json")
RESPONSE_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "service_response_verification.schema.json",
)
RESPONSE_SCHEMA = "rdllm-service-attribution-response/v1"
FOOTER_SCHEMA = "rdllm-service-source-footer/v1"
DISPLAY_SCHEMA = "rdllm-service-display/v1"
VERIFICATION_SCHEMA = "rdllm-service-response-verification/v1"
SOURCE_GROUNDING_ACCEPTANCE_SCHEMA = (
    "rdllm-service-source-grounding-acceptance/v1"
)
DISPLAY_READY_GROUNDING_VERDICTS = {"verified"}
MINIMUM_DISPLAY_SOURCE_COUNT = 1
MINIMUM_DISPLAY_SUPPORTED_CLAIM_COUNT = 1
MINIMUM_DISPLAY_SUPPORT_SCORE = 0.75
MONEY_QUANT = Decimal("0.000001")
SOURCE_USAGE_METRIC_NAMES = list(SOURCE_USAGE_METRIC_METHODS)
SOURCE_IDENTITY_STRING_FIELDS = (
    "title",
    "creator_id",
    "creator_name",
    "work_id",
    "chunk_id",
    "source_uri",
    "license",
    "license_uri",
    "content_hash",
)
SOURCE_IDENTITY_SCORE_FIELDS = (
    "retrieval_score",
    "text_match_score",
    "output_support",
    "citation_score",
)
SOURCE_IDENTITY_DECIMAL_FIELDS = ("contribution_weight", "payout")
TEMPORAL_CLAIM_PATTERN = re.compile(
    r"\b("
    r"as of|currently|current|latest|recent|recently|today|tonight|now|"
    r"this week|this month|this year|up to date|up-to-date|newly|"
    r"last week|last month|last year"
    r")\b",
    re.IGNORECASE,
)
SOURCE_TEMPORAL_FIELDS = (
    "retrieved_at",
    "fetched_at",
    "published_at",
    "last_modified_at",
    "valid_from",
    "valid_until",
    "effective_at",
    "source_version_hash",
)


def _answer_claim_units(answer_text: str) -> list[str]:
    claims: list[str] = []
    for line in answer_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Royalty-aware answer:") or line.startswith(
            "The strongest registered sources say:"
        ):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        for sentence in split_sentences(line):
            sentence = re.sub(r"^\[[A-Z]\d+\]\s*-?\s*", "", sentence.strip())
            sentence = re.sub(r"\s*\[[A-Z]\d+\]\s*$", "", sentence).strip()
            if tokenize(sentence):
                claims.append(sentence)
    return claims


def _counter_difference(left: Counter[str], right: Counter[str]) -> list[str]:
    return sorted((left - right).elements())


def load_response_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*RESPONSE_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_response_verification_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(
        *RESPONSE_VERIFICATION_SCHEMA_RESOURCE
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def event_hash_from_event(event: dict[str, Any]) -> str:
    payload = {
        "prompt": event.get("prompt", ""),
        "answer_text": event.get("answer_text", event.get("output", "")),
        "output": event.get("output", ""),
        "gross_revenue": str(
            Decimal(str(event.get("gross_revenue", "0"))).quantize(MONEY_QUANT)
        ),
        "creator_pool": str(event.get("creator_pool", "")),
        "shares": event.get("royalty_shares", []),
        "source_references": event.get("source_references", []),
        "claim_support": event.get("claim_support", []),
        "grounding_report": event.get("grounding_report", {}),
        "grounding_quality": event.get("grounding_quality", {}),
        "attribution_gap": event.get("attribution_gap", {}),
        "generation_evidence": event.get("generation_evidence", {}),
        "settlement_decision": event.get("settlement_decision", {}),
        "policy_decisions": event.get("policy_decisions", []),
        "registry_decisions": event.get("registry_decisions", []),
    }
    encoded = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_object(value: Any) -> bool:
    return isinstance(value, dict)


def _hash_without_hash_field(row: dict[str, Any], field: str) -> str:
    return canonical_hash({key: value for key, value in row.items() if key != field})


def _source_verification_handle(event: dict[str, Any], row: dict[str, Any]) -> str:
    return (
        "rdllm://verify/source-footer/"
        f"{event.get('event_id', '')}/"
        f"{row.get('label', '')}/"
        f"{str(row.get('content_hash', ''))[:12]}"
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _round_float(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 8)


def _int_or_zero(value: Any) -> int:
    try:
        if isinstance(value, bool):
            return 0
        return max(0, int(value))
    except Exception:
        return 0


def _source_row_has_usage_metrics(row: dict[str, Any]) -> bool:
    output_support = _float_or_none(row.get("output_support"))
    text_match = _float_or_none(row.get("text_match_score"))
    contribution_weight = _decimal_or_none(row.get("contribution_weight"))
    payout = _decimal_or_none(row.get("payout"))
    return (
        output_support is not None
        and 0.0 <= output_support <= 1.0
        and text_match is not None
        and 0.0 <= text_match <= 1.0
        and contribution_weight is not None
        and payout is not None
    )


def _source_row_renders_usage_metrics(
    row: dict[str, Any],
    footer_text: str,
) -> bool:
    prefix = (
        f"{row.get('display_label', '')} {row.get('title', '')} - "
        f"{row.get('creator_name', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(prefix)),
        "",
    )
    return all(f"{name}=" in rendered_line for name in SOURCE_USAGE_METRIC_NAMES)


def _source_row_has_usage_metric_provenance(row: dict[str, Any]) -> bool:
    if row.get("usage_metric_profile") != SOURCE_USAGE_METRIC_PROFILE:
        return False
    if row.get("usage_metric_scope") != SOURCE_USAGE_METRIC_SCOPE:
        return False
    return all(
        row.get(field) == SOURCE_USAGE_METRIC_METHODS[metric]
        for metric, field in SOURCE_USAGE_METRIC_METHOD_FIELDS.items()
    )


def _source_row_renders_usage_metric_provenance(
    row: dict[str, Any],
    footer_text: str,
) -> bool:
    prefix = (
        f"{row.get('display_label', '')} {row.get('title', '')} - "
        f"{row.get('creator_name', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(prefix)),
        "",
    )
    method_tokens = [
        f"{metric}:{SOURCE_USAGE_METRIC_METHODS[metric]}"
        for metric in SOURCE_USAGE_METRIC_NAMES
    ]
    return (
        bool(rendered_line)
        and f"metrics={SOURCE_USAGE_METRIC_PROFILE}; " in rendered_line
        and f"scope={SOURCE_USAGE_METRIC_SCOPE}; " in rendered_line
        and "methods=" in rendered_line
        and all(token in rendered_line for token in method_tokens)
    )


def _source_row_renders_locator(
    row: dict[str, Any],
    footer_text: str,
) -> bool:
    prefix = (
        f"{row.get('display_label', '')} {row.get('title', '')} - "
        f"{row.get('creator_name', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(prefix)),
        "",
    )
    content_hash = str(row.get("content_hash", ""))
    content_hash_prefix = str(row.get("content_hash_prefix", ""))
    source_uri = str(row.get("source_uri", ""))
    verification_handle = str(row.get("verification_handle", ""))
    return (
        bool(rendered_line)
        and bool(source_uri)
        and bool(verification_handle)
        and bool(content_hash)
        and bool(content_hash_prefix)
        and content_hash_prefix == content_hash[:12]
        and f"uri={source_uri}; " in rendered_line
        and f"verify={verification_handle}; " in rendered_line
        and f"hash={content_hash_prefix}." in rendered_line
    )


def _event_source_references_by_label(
    event: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    references = event.get("source_references", [])
    if not isinstance(references, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for reference in references:
        if not isinstance(reference, dict):
            continue
        label = reference.get("label")
        if isinstance(label, str) and label and label not in result:
            result[label] = reference
    return result


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def _score_matches(row_value: Any, reference_value: Any) -> bool:
    row_score = _float_or_none(row_value)
    reference_score = _float_or_none(reference_value)
    if row_score is None or reference_score is None:
        return False
    return round(row_score, 8) == round(reference_score, 8)


def _decimal_matches(row_value: Any, reference_value: Any) -> bool:
    row_decimal = _decimal_or_none(row_value)
    reference_decimal = _decimal_or_none(reference_value)
    return (
        row_decimal is not None
        and reference_decimal is not None
        and row_decimal == reference_decimal
    )


def _source_row_matches_event_reference(
    row: dict[str, Any],
    source_references_by_label: dict[str, dict[str, Any]],
) -> bool:
    reference = source_references_by_label.get(str(row.get("label", "")))
    if not reference:
        return False
    for field in SOURCE_IDENTITY_STRING_FIELDS:
        if str(row.get(field, "")) != str(reference.get(field, "")):
            return False
    for field in SOURCE_IDENTITY_SCORE_FIELDS:
        if not _score_matches(row.get(field), reference.get(field)):
            return False
    for field in SOURCE_IDENTITY_DECIMAL_FIELDS:
        if not _decimal_matches(row.get(field), reference.get(field)):
            return False
    return (
        row.get("evidence_preview") == reference.get("quote")
        and _string_list(row.get("evidence_span_hashes"))
        == _string_list(reference.get("evidence_span_hashes"))
    )


def _temporal_claim_markers(answer_text: str) -> list[str]:
    return sorted(
        {
            match.group(1).lower().replace("-", " ")
            for match in TEMPORAL_CLAIM_PATTERN.finditer(answer_text)
        }
    )


def _source_row_has_temporal_metadata(row: dict[str, Any]) -> bool:
    return any(str(row.get(field, "")).strip() for field in SOURCE_TEMPORAL_FIELDS)


def _claim_row_has_valid_evidence(row: dict[str, Any]) -> bool:
    span_hash = str(row.get("evidence_span_hash", ""))
    evidence_preview = row.get("evidence_preview")
    start_char = row.get("evidence_start_char")
    end_char = row.get("evidence_end_char")
    support_score = _float_or_none(row.get("support_score"))
    return (
        row.get("supported") is True
        and bool(row.get("source_label"))
        and bool(row.get("work_id"))
        and bool(row.get("chunk_id"))
        and support_score is not None
        and 0.0 <= support_score <= 1.0
        and bool(span_hash)
        and row.get("evidence_span_hash_prefix") == span_hash[:12]
        and isinstance(evidence_preview, str)
        and bool(evidence_preview)
        and stable_hash(evidence_preview) == span_hash
        and isinstance(start_char, int)
        and not isinstance(start_char, bool)
        and isinstance(end_char, int)
        and not isinstance(end_char, bool)
        and start_char >= 0
        and end_char >= start_char
    )


def _rendered_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ",".join(str(item) for item in value)


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


def _claim_row_renders_warrant_strength(
    row: dict[str, Any],
    footer_text: str,
) -> bool:
    line_prefix = (
        f"[C{row.get('claim_index')}] {row.get('source_label', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(line_prefix)),
        "",
    )
    return (
        bool(rendered_line)
        and (
            f"warrant={row.get('warrant_strength_status', '')}; "
            in rendered_line
        )
        and (
            f"force={_rendered_list(row.get('claim_force_flags', []))}; "
            in rendered_line
        )
        and (
            f"missing={_rendered_list(row.get('warrant_mismatch_flags', []))}; "
            in rendered_line
        )
        and f"profile={row.get('claim_warrant_profile', '')}. " in rendered_line
        and f"Claim: {row.get('claim_preview', '')} " in rendered_line
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


def _claim_row_renders_source_disagreement(
    row: dict[str, Any],
    footer_text: str,
) -> bool:
    line_prefix = (
        f"[C{row.get('claim_index')}] {row.get('source_label', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(line_prefix)),
        "",
    )
    return (
        bool(rendered_line)
        and (
            f"disagreement={row.get('source_disagreement_status', '')}; "
            in rendered_line
        )
        and (
            f"agreements={_rendered_list(row.get('agreement_source_labels', []))}; "
            in rendered_line
        )
        and (
            f"conflicts={_rendered_list(row.get('disagreement_source_labels', []))}; "
            in rendered_line
        )
        and (
            "disagreement_profile="
            f"{row.get('source_disagreement_profile', '')}. "
        )
        in rendered_line
    )


def _claim_row_renders_evidence(row: dict[str, Any], footer_text: str) -> bool:
    line_prefix = (
        f"[C{row.get('claim_index')}] {row.get('source_label', '')}; "
    )
    rendered_line = next(
        (line for line in footer_text.splitlines() if line.startswith(line_prefix)),
        "",
    )
    support_score = _float_or_none(row.get("support_score"))
    support_text = (
        f"support={support_score:.3f}; " if support_score is not None else ""
    )
    return (
        bool(rendered_line)
        and f"claim_hash={row.get('claim_hash_prefix', '')}; " in rendered_line
        and (not support_text or support_text in rendered_line)
        and f"span={row.get('evidence_span_hash_prefix', '')}; " in rendered_line
        and (
            f"chars={row.get('evidence_start_char')}-"
            f"{row.get('evidence_end_char')}. "
        )
        in rendered_line
        and f"Claim: {row.get('claim_preview', '')} " in rendered_line
        and f"Evidence: {row.get('evidence_preview', '')}" in rendered_line
    )


def _claim_row_matches_source_row(
    row: dict[str, Any],
    source_rows_by_label: dict[str, dict[str, Any]],
) -> bool:
    source_row = source_rows_by_label.get(str(row.get("source_label", "")))
    return bool(
        source_row
        and row.get("supported") is True
        and row.get("work_id") == source_row.get("work_id")
        and row.get("chunk_id") == source_row.get("chunk_id")
    )


def _unresolved_answer_citation_markers(
    answer_text: str,
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[str]:
    source_labels = [str(row.get("label", "")) for row in source_rows]
    supported_claim_indexes = [
        row.get("claim_index") for row in claim_rows if row.get("supported") is True
    ]
    allowed = source_citation_keys(source_labels) | claim_citation_keys(
        supported_claim_indexes
    )
    return unresolved_answer_citation_markers(answer_text, allowed)


def _resolved_answer_citation_markers(
    answer_text: str,
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[str]:
    source_labels = [str(row.get("label", "")) for row in source_rows]
    supported_claim_indexes = [
        row.get("claim_index") for row in claim_rows if row.get("supported") is True
    ]
    allowed = source_citation_keys(source_labels) | claim_citation_keys(
        supported_claim_indexes
    )
    return resolved_answer_citation_markers(answer_text, allowed)


def _empty_source_grounding_acceptance(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SOURCE_GROUNDING_ACCEPTANCE_SCHEMA,
        "status": "failed",
        "errors": errors,
        "policy": {
            "minimum_source_count": MINIMUM_DISPLAY_SOURCE_COUNT,
            "minimum_supported_claim_count": MINIMUM_DISPLAY_SUPPORTED_CLAIM_COUNT,
            "minimum_support_score": MINIMUM_DISPLAY_SUPPORT_SCORE,
            "required_render_policy": "answer_plus_verified_source_footer",
            "unresolved_inline_citation_markers_blocked": True,
            "source_usage_metrics_required": True,
            "claim_evidence_rows_required": True,
            "claim_source_closure_required": True,
            "source_locators_required": True,
            "attribution_gap_closed_required": True,
            "source_identity_binding_required": True,
            "temporal_claims_require_source_freshness_metadata": True,
            "answer_source_links_must_match_footer_sources": True,
            "answer_claim_rows_must_cover_answer_text": True,
            "model_internal_reliance_claims_blocked": True,
            "source_usage_metric_provenance_required": True,
            "claim_warrant_strength_required": True,
            "claim_source_disagreement_required": True,
        },
        "source_count": 0,
        "verified_source_count": 0,
        "source_uri_count": 0,
        "verification_handle_count": 0,
        "source_locator_count": 0,
        "source_identity_count": 0,
        "source_temporal_metadata_count": 0,
        "source_usage_metric_names": SOURCE_USAGE_METRIC_NAMES,
        "source_usage_metric_profile": SOURCE_USAGE_METRIC_PROFILE,
        "source_usage_metric_scope": SOURCE_USAGE_METRIC_SCOPE,
        "source_usage_metric_methods": SOURCE_USAGE_METRIC_METHODS,
        "source_usage_metric_row_count": 0,
        "source_usage_metric_provenance_count": 0,
        "answer_citation_markers": [],
        "resolved_answer_citation_markers": [],
        "unresolved_answer_citation_markers": [],
        "answer_link_uris": [],
        "resolved_answer_link_uris": [],
        "unresolved_answer_link_uris": [],
        "answer_citation_marker_count": 0,
        "resolved_answer_citation_marker_count": 0,
        "answer_link_uri_count": 0,
        "resolved_answer_link_uri_count": 0,
        "unresolved_answer_link_uri_count": 0,
        "temporal_claim_markers": [],
        "temporal_claim_marker_count": 0,
        "answer_claim_unit_count": 0,
        "answer_claim_row_coverage_count": 0,
        "uncovered_answer_claim_hashes": [],
        "extra_claim_row_hashes": [],
        "model_reliance_claim_markers": [],
        "model_reliance_claim_marker_count": 0,
        "claim_count": 0,
        "supported_claim_count": 0,
        "unsupported_claim_count": 0,
        "claim_evidence_row_count": 0,
        "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
        "claim_warrant_strength_count": 0,
        "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
        "claim_source_disagreement_count": 0,
        "claim_source_closure_count": 0,
        "minimum_support_score": 0.0,
        "average_support_score": 0.0,
        "royalty_share_count": 0,
        "royalty_covered_source_count": 0,
        "attribution_gap_verdict": "",
        "attribution_gap_accessed_source_count": 0,
        "attribution_gap_allowed_accessed_source_count": 0,
        "attribution_gap_credited_source_count": 0,
        "attribution_gap_consumed_without_credit_count": 0,
        "attribution_gap_cited_without_access_count": 0,
        "attribution_gap_paid_hidden_count": 0,
        "source_materialization_status": "failed",
        "fact_support_status": "failed",
        "royalty_attribution_status": "failed",
        "attribution_gap_status": "failed",
        "display_binding_status": "failed",
        "citation_marker_status": "failed",
        "source_usage_metric_status": "failed",
        "source_usage_metric_provenance_status": "failed",
        "source_identity_status": "failed",
        "temporal_grounding_status": "failed",
        "answer_link_status": "failed",
        "answer_claim_coverage_status": "failed",
        "model_reliance_claim_status": "failed",
        "claim_evidence_status": "failed",
        "claim_warrant_strength_status": "failed",
        "claim_source_disagreement_status": "failed",
        "claim_source_closure_status": "failed",
        "source_locator_status": "failed",
        "display_footer_bound": False,
        "display_rendered_with_footer": False,
        "footer_contains_source_section": False,
        "footer_contains_claim_evidence": False,
    }


def _source_grounding_acceptance(
    *,
    footer: dict[str, Any],
    display: dict[str, Any],
    event: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    source_rows = [
        row for row in footer.get("source_rows", []) if isinstance(row, dict)
    ]
    claim_rows = [
        row for row in footer.get("claim_rows", []) if isinstance(row, dict)
    ]
    supported_claim_rows = [row for row in claim_rows if row.get("supported") is True]
    unsupported_claim_rows = [
        row for row in claim_rows if row.get("supported") is not True
    ]
    support_scores = []
    for row in supported_claim_rows:
        try:
            support_scores.append(float(row.get("support_score", 0.0)))
        except Exception:
            support_scores.append(0.0)

    source_count = len(source_rows)
    source_rows_by_label = {
        str(row.get("label", "")): row for row in source_rows if row.get("label")
    }
    source_row_uris = {
        str(row.get("source_uri", ""))
        for row in source_rows
        if row.get("confidence") == "verified" and row.get("source_uri")
    }
    source_references_by_label = _event_source_references_by_label(event)
    verified_source_count = sum(
        1 for row in source_rows if row.get("confidence") == "verified"
    )
    source_uri_count = sum(1 for row in source_rows if row.get("source_uri"))
    verification_handle_count = sum(
        1 for row in source_rows if row.get("verification_handle")
    )
    paid_chunk_ids = {
        str(row.get("chunk_id", ""))
        for row in event.get("royalty_shares", [])
        if isinstance(row, dict)
        and not str(row.get("chunk_id", "")).startswith("escrow:")
        and (_decimal_or_none(row.get("payout", "0")) or Decimal("0")) > 0
    }
    royalty_covered_source_count = sum(
        1
        for row in source_rows
        if str(row.get("chunk_id", "")) in paid_chunk_ids
        and (_decimal_or_none(row.get("payout", "0")) or Decimal("0")) > 0
    )
    attribution_gap = event.get("attribution_gap", {})
    if not isinstance(attribution_gap, dict):
        attribution_gap = {}
    attribution_gap_summary = attribution_gap.get("summary", {})
    if not isinstance(attribution_gap_summary, dict):
        attribution_gap_summary = {}
    attribution_gap_verdict = str(attribution_gap.get("verdict", ""))
    attribution_gap_accessed_source_count = _int_or_zero(
        attribution_gap_summary.get("accessed_source_count", 0)
    )
    attribution_gap_allowed_accessed_source_count = _int_or_zero(
        attribution_gap_summary.get("allowed_accessed_source_count", 0)
    )
    attribution_gap_credited_source_count = _int_or_zero(
        attribution_gap_summary.get("credited_source_count", 0)
    )
    attribution_gap_consumed_without_credit_count = _int_or_zero(
        attribution_gap_summary.get("consumed_without_credit_count", 0)
    )
    attribution_gap_cited_without_access_count = _int_or_zero(
        attribution_gap_summary.get("cited_without_access_count", 0)
    )
    attribution_gap_paid_hidden_count = _int_or_zero(
        attribution_gap_summary.get("paid_hidden_count", 0)
    )
    attribution_gap_closed = (
        attribution_gap_verdict == "closed"
        and attribution_gap_consumed_without_credit_count == 0
        and attribution_gap_cited_without_access_count == 0
        and attribution_gap_paid_hidden_count == 0
    )
    minimum_support = min(support_scores) if support_scores else 0.0
    average_support = (
        sum(support_scores) / len(support_scores) if support_scores else 0.0
    )
    footer_text = str(footer.get("rendered_text", ""))
    display_text = str(display.get("rendered_text", ""))
    answer_text = str(event.get("answer_text", event.get("output", "")))
    source_locator_count = sum(
        1 for row in source_rows if _source_row_renders_locator(row, footer_text)
    )
    source_identity_count = sum(
        1
        for row in source_rows
        if _source_row_matches_event_reference(row, source_references_by_label)
    )
    source_temporal_metadata_count = sum(
        1 for row in source_rows if _source_row_has_temporal_metadata(row)
    )
    answer_markers = answer_citation_markers(answer_text)
    answer_links = answer_link_uris(answer_text)
    model_reliance_markers = model_reliance_claim_markers(answer_text)
    answer_claim_units = _answer_claim_units(answer_text)
    answer_claim_hashes = [stable_hash(unit) for unit in answer_claim_units]
    claim_row_hashes = [
        str(row.get("claim_hash", "")) for row in claim_rows if row.get("claim_hash")
    ]
    answer_claim_counter = Counter(answer_claim_hashes)
    claim_row_counter = Counter(claim_row_hashes)
    uncovered_answer_claim_hashes = _counter_difference(
        answer_claim_counter,
        claim_row_counter,
    )
    extra_claim_row_hashes = _counter_difference(
        claim_row_counter,
        answer_claim_counter,
    )
    answer_claim_row_coverage_count = sum(
        (answer_claim_counter & claim_row_counter).values()
    )
    temporal_claim_markers = _temporal_claim_markers(answer_text)
    resolved_answer_markers = _resolved_answer_citation_markers(
        answer_text,
        source_rows,
        claim_rows,
    )
    unresolved_answer_citation_markers = _unresolved_answer_citation_markers(
        answer_text,
        source_rows,
        claim_rows,
    )
    resolved_answer_links = resolved_answer_link_uris(
        answer_text,
        source_row_uris,
    )
    unresolved_answer_links = unresolved_answer_link_uris(
        answer_text,
        source_row_uris,
    )

    display_footer_bound = bool(
        footer.get("footer_hash")
        and display.get("source_footer_hash") == footer.get("footer_hash")
        and summary.get("source_footer_hash") == footer.get("footer_hash")
    )
    display_rendered_with_footer = bool(
        footer_text
        and footer_text in display_text
        and display_text.startswith(answer_text.rstrip())
    )
    footer_contains_source_section = "Sources" in footer_text
    footer_contains_claim_evidence = "Claim Evidence" in footer_text
    source_usage_metric_row_count = sum(
        1
        for row in source_rows
        if _source_row_has_usage_metrics(row)
        and _source_row_renders_usage_metrics(row, footer_text)
    )
    source_usage_metric_provenance_count = sum(
        1
        for row in source_rows
        if _source_row_has_usage_metric_provenance(row)
        and _source_row_renders_usage_metric_provenance(row, footer_text)
    )
    claim_evidence_row_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_has_valid_evidence(row)
        and _claim_row_renders_evidence(row, footer_text)
    )
    claim_warrant_strength_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_has_valid_warrant_strength(row)
        and _claim_row_renders_warrant_strength(row, footer_text)
    )
    claim_source_disagreement_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_has_valid_source_disagreement(row, source_rows)
        and _claim_row_renders_source_disagreement(row, footer_text)
    )
    claim_source_closure_count = sum(
        1
        for row in supported_claim_rows
        if _claim_row_matches_source_row(row, source_rows_by_label)
    )

    errors: list[str] = []
    if source_count < MINIMUM_DISPLAY_SOURCE_COUNT:
        errors.append("source_materialization: no visible source rows")
    if verified_source_count != source_count:
        errors.append("source_materialization: not every source row is verified")
    if source_uri_count != source_count:
        errors.append("source_materialization: not every source row has a source URI")
    if verification_handle_count != source_count:
        errors.append(
            "source_materialization: not every source row has a verification handle"
        )
    if source_locator_count != source_count:
        errors.append(
            "source_locator: not every visible source row exposes uri, verify, "
            "and hash locators"
        )
    if source_identity_count != source_count:
        errors.append(
            "source_identity: not every visible source row matches event source "
            "reference identity"
        )
    if temporal_claim_markers and source_temporal_metadata_count != source_count:
        errors.append(
            "temporal_grounding: temporal answer claims require source freshness "
            "metadata"
        )

    if len(supported_claim_rows) < MINIMUM_DISPLAY_SUPPORTED_CLAIM_COUNT:
        errors.append("fact_support: no supported claim rows")
    if unsupported_claim_rows:
        errors.append("fact_support: unsupported claim rows are present")
    if support_scores and minimum_support < MINIMUM_DISPLAY_SUPPORT_SCORE:
        errors.append(
            "fact_support: minimum support score below "
            f"{MINIMUM_DISPLAY_SUPPORT_SCORE:.2f}"
        )

    if royalty_covered_source_count != source_count:
        errors.append(
            "royalty_attribution: not every visible source has a matching "
            "non-escrow royalty share"
        )
    if not attribution_gap_closed:
        errors.append(
            "attribution_gap: accessed, visible, and paid source coverage is "
            "not closed"
        )

    if display.get("render_policy") != "answer_plus_verified_source_footer":
        errors.append("display_binding: render policy is not source-footer preserving")
    if not display_footer_bound:
        errors.append("display_binding: display is not bound to source footer hash")
    if not display_rendered_with_footer:
        errors.append("display_binding: rendered answer does not include source footer")
    if not footer_contains_source_section:
        errors.append("display_binding: footer does not contain Sources section")
    if not footer_contains_claim_evidence:
        errors.append("display_binding: footer does not contain Claim Evidence section")
    if unresolved_answer_citation_markers:
        errors.append(
            "answer_citations: unresolved inline citation markers "
            f"{', '.join(unresolved_answer_citation_markers)}"
        )
    if unresolved_answer_links:
        errors.append(
            "answer_links: unverified answer source links "
            f"{', '.join(unresolved_answer_links)}"
        )
    if not answer_claim_hashes:
        errors.append("answer_claim_coverage: answer text exposes no claim units")
    elif uncovered_answer_claim_hashes or extra_claim_row_hashes:
        errors.append(
            "answer_claim_coverage: answer text claims do not match footer "
            "claim rows"
        )
    if model_reliance_markers:
        errors.append(
            "answer_model_reliance: unverified model-internal reliance claims "
            f"{', '.join(model_reliance_markers)}"
        )
    if source_usage_metric_row_count != source_count:
        errors.append(
            "source_usage: not every visible source row exposes support, "
            "text_match, weight, and payout"
        )
    if source_usage_metric_provenance_count != source_count:
        errors.append(
            "source_usage_metric_provenance: not every visible source row exposes "
            "metric profile, scope, and methods"
        )
    if claim_evidence_row_count != len(supported_claim_rows):
        errors.append(
            "claim_evidence: not every supported claim exposes a visible "
            "evidence span"
        )
    if claim_warrant_strength_count != len(supported_claim_rows):
        errors.append(
            "claim_warrant_strength: not every supported claim passes "
            "evidence-force calibration"
        )
    if claim_source_disagreement_count != len(supported_claim_rows):
        errors.append(
            "claim_source_disagreement: not every supported claim is free of "
            "visible source disagreement"
        )
    if claim_source_closure_count != len(supported_claim_rows):
        errors.append(
            "claim_source_closure: not every supported claim binds to the "
            "visible source row work and chunk"
        )

    return {
        "schema": SOURCE_GROUNDING_ACCEPTANCE_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "policy": {
            "minimum_source_count": MINIMUM_DISPLAY_SOURCE_COUNT,
            "minimum_supported_claim_count": MINIMUM_DISPLAY_SUPPORTED_CLAIM_COUNT,
            "minimum_support_score": MINIMUM_DISPLAY_SUPPORT_SCORE,
            "required_render_policy": "answer_plus_verified_source_footer",
            "unresolved_inline_citation_markers_blocked": True,
            "source_usage_metrics_required": True,
            "claim_evidence_rows_required": True,
            "claim_source_closure_required": True,
            "source_locators_required": True,
            "attribution_gap_closed_required": True,
            "source_identity_binding_required": True,
            "temporal_claims_require_source_freshness_metadata": True,
            "answer_source_links_must_match_footer_sources": True,
            "answer_claim_rows_must_cover_answer_text": True,
            "model_internal_reliance_claims_blocked": True,
            "source_usage_metric_provenance_required": True,
            "claim_warrant_strength_required": True,
            "claim_source_disagreement_required": True,
        },
        "source_count": source_count,
        "verified_source_count": verified_source_count,
        "source_uri_count": source_uri_count,
        "verification_handle_count": verification_handle_count,
        "source_locator_count": source_locator_count,
        "source_identity_count": source_identity_count,
        "source_temporal_metadata_count": source_temporal_metadata_count,
        "source_usage_metric_names": SOURCE_USAGE_METRIC_NAMES,
        "source_usage_metric_profile": SOURCE_USAGE_METRIC_PROFILE,
        "source_usage_metric_scope": SOURCE_USAGE_METRIC_SCOPE,
        "source_usage_metric_methods": SOURCE_USAGE_METRIC_METHODS,
        "source_usage_metric_row_count": source_usage_metric_row_count,
        "source_usage_metric_provenance_count": (
            source_usage_metric_provenance_count
        ),
        "answer_citation_markers": answer_markers,
        "resolved_answer_citation_markers": resolved_answer_markers,
        "unresolved_answer_citation_markers": unresolved_answer_citation_markers,
        "answer_link_uris": answer_links,
        "resolved_answer_link_uris": resolved_answer_links,
        "unresolved_answer_link_uris": unresolved_answer_links,
        "answer_citation_marker_count": len(answer_markers),
        "resolved_answer_citation_marker_count": len(resolved_answer_markers),
        "answer_link_uri_count": len(answer_links),
        "resolved_answer_link_uri_count": len(resolved_answer_links),
        "unresolved_answer_link_uri_count": len(unresolved_answer_links),
        "temporal_claim_markers": temporal_claim_markers,
        "temporal_claim_marker_count": len(temporal_claim_markers),
        "answer_claim_unit_count": len(answer_claim_hashes),
        "answer_claim_row_coverage_count": answer_claim_row_coverage_count,
        "uncovered_answer_claim_hashes": uncovered_answer_claim_hashes,
        "extra_claim_row_hashes": extra_claim_row_hashes,
        "model_reliance_claim_markers": model_reliance_markers,
        "model_reliance_claim_marker_count": len(model_reliance_markers),
        "claim_count": len(claim_rows),
        "supported_claim_count": len(supported_claim_rows),
        "unsupported_claim_count": len(unsupported_claim_rows),
        "claim_evidence_row_count": claim_evidence_row_count,
        "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
        "claim_warrant_strength_count": claim_warrant_strength_count,
        "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
        "claim_source_disagreement_count": claim_source_disagreement_count,
        "claim_source_closure_count": claim_source_closure_count,
        "minimum_support_score": _round_float(minimum_support),
        "average_support_score": _round_float(average_support),
        "royalty_share_count": len(event.get("royalty_shares", [])),
        "royalty_covered_source_count": royalty_covered_source_count,
        "attribution_gap_verdict": attribution_gap_verdict,
        "attribution_gap_accessed_source_count": (
            attribution_gap_accessed_source_count
        ),
        "attribution_gap_allowed_accessed_source_count": (
            attribution_gap_allowed_accessed_source_count
        ),
        "attribution_gap_credited_source_count": (
            attribution_gap_credited_source_count
        ),
        "attribution_gap_consumed_without_credit_count": (
            attribution_gap_consumed_without_credit_count
        ),
        "attribution_gap_cited_without_access_count": (
            attribution_gap_cited_without_access_count
        ),
        "attribution_gap_paid_hidden_count": attribution_gap_paid_hidden_count,
        "source_materialization_status": (
            "passed"
            if source_count >= MINIMUM_DISPLAY_SOURCE_COUNT
            and verified_source_count == source_count
            and source_uri_count == source_count
            and verification_handle_count == source_count
            else "failed"
        ),
        "source_locator_status": (
            "passed"
            if source_count > 0 and source_locator_count == source_count
            else "failed"
        ),
        "source_identity_status": (
            "passed"
            if source_count > 0 and source_identity_count == source_count
            else "failed"
        ),
        "temporal_grounding_status": (
            "passed"
            if not temporal_claim_markers
            or (source_count > 0 and source_temporal_metadata_count == source_count)
            else "failed"
        ),
        "fact_support_status": (
            "passed"
            if len(supported_claim_rows) >= MINIMUM_DISPLAY_SUPPORTED_CLAIM_COUNT
            and not unsupported_claim_rows
            and minimum_support >= MINIMUM_DISPLAY_SUPPORT_SCORE
            else "failed"
        ),
        "royalty_attribution_status": (
            "passed" if royalty_covered_source_count == source_count else "failed"
        ),
        "attribution_gap_status": "passed" if attribution_gap_closed else "failed",
        "display_binding_status": (
            "passed"
            if display.get("render_policy") == "answer_plus_verified_source_footer"
            and display_footer_bound
            and display_rendered_with_footer
            and footer_contains_source_section
            and footer_contains_claim_evidence
            else "failed"
        ),
        "citation_marker_status": (
            "passed" if not unresolved_answer_citation_markers else "failed"
        ),
        "answer_link_status": "passed" if not unresolved_answer_links else "failed",
        "answer_claim_coverage_status": (
            "passed"
            if answer_claim_hashes
            and not uncovered_answer_claim_hashes
            and not extra_claim_row_hashes
            else "failed"
        ),
        "model_reliance_claim_status": (
            "passed" if not model_reliance_markers else "failed"
        ),
        "source_usage_metric_status": (
            "passed"
            if source_count > 0 and source_usage_metric_row_count == source_count
            else "failed"
        ),
        "source_usage_metric_provenance_status": (
            "passed"
            if source_count > 0
            and source_usage_metric_provenance_count == source_count
            else "failed"
        ),
        "claim_evidence_status": (
            "passed"
            if supported_claim_rows
            and claim_evidence_row_count == len(supported_claim_rows)
            else "failed"
        ),
        "claim_warrant_strength_status": (
            "passed"
            if supported_claim_rows
            and claim_warrant_strength_count == len(supported_claim_rows)
            else "failed"
        ),
        "claim_source_disagreement_status": (
            "passed"
            if supported_claim_rows
            and claim_source_disagreement_count == len(supported_claim_rows)
            else "failed"
        ),
        "claim_source_closure_status": (
            "passed"
            if supported_claim_rows
            and claim_source_closure_count == len(supported_claim_rows)
            else "failed"
        ),
        "display_footer_bound": display_footer_bound,
        "display_rendered_with_footer": display_rendered_with_footer,
        "footer_contains_source_section": footer_contains_source_section,
        "footer_contains_claim_evidence": footer_contains_claim_evidence,
    }


def _render_footer_text(footer: dict[str, Any], event: dict[str, Any]) -> str:
    return render_source_footer_text(
        source_rows=[
            row for row in footer.get("source_rows", []) if isinstance(row, dict)
        ],
        claim_rows=[
            row for row in footer.get("claim_rows", []) if isinstance(row, dict)
        ],
        grounding_report=event.get("grounding_report", {}),
    )


def _render_display_text(footer: dict[str, Any], event: dict[str, Any]) -> str:
    answer_text = str(event.get("answer_text", event.get("output", "")))
    return f"{answer_text.rstrip()}\n\n{footer.get('rendered_text', '')}"


def _display_text_result(
    *,
    display_text: str | None,
    expected_display_text: str,
    display_text_path: str = "",
) -> tuple[dict[str, str], list[str]]:
    if display_text is None:
        return {
            "display_text_status": "not_checked",
            "display_text_hash": "",
            "display_text_path": display_text_path,
        }, []

    errors: list[str] = []
    if display_text != expected_display_text:
        errors.append("display_text: does not match answer plus footer")
        footer_start = expected_display_text.split("\n\n", 1)[-1]
        if footer_start and footer_start not in display_text:
            errors.append("display_text: missing source footer")
        if "rdllm://verify/source-footer/" not in display_text:
            errors.append("display_text: missing source verification handles")
    return {
        "display_text_status": "passed" if not errors else "failed",
        "display_text_hash": canonical_hash(display_text),
        "display_text_path": display_text_path,
    }, errors


def _shape_errors(response: Any) -> list[str]:
    if not _is_object(response):
        return ["<root>: expected object"]
    errors: list[str] = []
    required = {
        "schema",
        "status",
        "summary",
        "source_footer",
        "display",
        "audit_errors",
        "event",
    }
    for field in sorted(required - set(response)):
        errors.append(f"<root>.{field}: missing required field")
    if response.get("schema") != RESPONSE_SCHEMA:
        errors.append(f"<root>.schema: expected {RESPONSE_SCHEMA!r}")
    if response.get("status") not in {"ready", "blocked"}:
        errors.append("<root>.status: expected ready or blocked")
    if not isinstance(response.get("summary"), dict):
        errors.append("<root>.summary: expected object")
    if not isinstance(response.get("source_footer"), dict):
        errors.append("<root>.source_footer: expected object")
    if not isinstance(response.get("audit_errors"), list):
        errors.append("<root>.audit_errors: expected array")
    if not isinstance(response.get("event"), dict):
        errors.append("<root>.event: expected object")
    return errors


def verify_service_response(
    response: dict[str, Any],
    *,
    display_text: str | None = None,
    display_text_path: str = "",
) -> dict[str, Any]:
    errors = _shape_errors(response)
    if errors:
        display_text_fields, _display_text_errors = _display_text_result(
            display_text=display_text,
            expected_display_text="",
            display_text_path=display_text_path,
        )
        return {
            "schema": VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": errors,
            "response_status": "unknown",
            "production_display_ready": False,
            "display_text_status": display_text_fields["display_text_status"],
            "display_text_hash": display_text_fields["display_text_hash"],
            "display_text_path": display_text_fields["display_text_path"],
            "source_grounding_acceptance": _empty_source_grounding_acceptance(
                ["response shape is invalid"]
            ),
            "event_id": "",
            "event_hash": "",
            "footer_hash": "",
            "display_hash": "",
            "source_count": 0,
            "claim_count": 0,
            "grounding_verdict": "",
            "attribution_gap_verdict": "",
        }

    summary = response["summary"]
    footer = response["source_footer"]
    display = response["display"]
    event = response["event"]

    if footer.get("schema") != FOOTER_SCHEMA:
        errors.append(f"source_footer.schema: expected {FOOTER_SCHEMA!r}")
    if not isinstance(display, dict):
        errors.append("display: expected object")
        display = {}
    elif display.get("schema") != DISPLAY_SCHEMA:
        errors.append(f"display.schema: expected {DISPLAY_SCHEMA!r}")
    if response["status"] == "ready" and response["audit_errors"]:
        errors.append("status: ready response has audit errors")
    if response["status"] == "blocked" and not response["audit_errors"]:
        errors.append("status: blocked response has no audit errors")

    source_rows = footer.get("source_rows", [])
    claim_rows = footer.get("claim_rows", [])
    if not isinstance(source_rows, list):
        errors.append("source_footer.source_rows: expected array")
        source_rows = []
    if not isinstance(claim_rows, list):
        errors.append("source_footer.claim_rows: expected array")
        claim_rows = []

    source_rows_by_label: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, row in enumerate(source_rows):
        if not isinstance(row, dict):
            errors.append(f"source_footer.source_rows[{index}]: expected object")
            continue
        label = row.get("label")
        if isinstance(label, str) and label:
            if label in source_rows_by_label:
                errors.append(
                    f"source_footer.source_rows[{index}].label: duplicate source label"
                )
            else:
                source_rows_by_label[label] = (index, row)
            if row.get("display_label") != f"[{label}]":
                errors.append(
                    f"source_footer.source_rows[{index}].display_label: "
                    "does not match label"
                )
        expected = _hash_without_hash_field(row, "row_hash")
        if row.get("row_hash") != expected:
            errors.append(f"source_footer.source_rows[{index}].row_hash: mismatch")
        content_hash = str(row.get("content_hash", ""))
        if row.get("content_hash_prefix") != content_hash[:12]:
            errors.append(
                f"source_footer.source_rows[{index}].content_hash_prefix: mismatch"
            )
        if row.get("verification_handle") != _source_verification_handle(event, row):
            errors.append(
                f"source_footer.source_rows[{index}].verification_handle: mismatch"
            )

    source_labels = set(source_rows_by_label)
    supported_claims_by_label: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, row in enumerate(claim_rows):
        if not isinstance(row, dict):
            errors.append(f"source_footer.claim_rows[{index}]: expected object")
            continue
        expected = _hash_without_hash_field(row, "row_hash")
        if row.get("row_hash") != expected:
            errors.append(f"source_footer.claim_rows[{index}].row_hash: mismatch")
        claim_hash = str(row.get("claim_hash", ""))
        claim_preview = row.get("claim_preview")
        if not isinstance(claim_preview, str) or not claim_preview:
            errors.append(f"source_footer.claim_rows[{index}].claim_preview: missing")
        elif stable_hash(claim_preview) != claim_hash:
            errors.append(
                f"source_footer.claim_rows[{index}].claim_hash: "
                "does not match claim preview"
            )
        if row.get("claim_hash_prefix") != claim_hash[:12]:
            errors.append(f"source_footer.claim_rows[{index}].claim_hash_prefix: mismatch")
        expected_warrant = claim_warrant_report(
            claim=claim_preview if isinstance(claim_preview, str) else "",
            evidence=str(row.get("evidence_preview", "")),
            supported=row.get("supported") is True,
        )
        for field, expected_value in expected_warrant.items():
            if row.get(field) != expected_value:
                errors.append(
                    f"source_footer.claim_rows[{index}].{field}: mismatch"
                )
        expected_disagreement = claim_source_disagreement_report(
            claim=claim_preview if isinstance(claim_preview, str) else "",
            source_label=str(row.get("source_label", "")),
            source_rows=source_rows,
            supported=row.get("supported") is True,
        )
        for field, expected_value in expected_disagreement.items():
            if row.get(field) != expected_value:
                errors.append(
                    f"source_footer.claim_rows[{index}].{field}: mismatch"
                )
        span_hash = str(row.get("evidence_span_hash", ""))
        if row.get("evidence_span_hash_prefix") != span_hash[:12]:
            errors.append(
                f"source_footer.claim_rows[{index}].evidence_span_hash_prefix: mismatch"
            )
        if row.get("supported") and row.get("source_label") not in source_labels:
            errors.append(
                f"source_footer.claim_rows[{index}].source_label: missing source row"
            )
        if row.get("supported"):
            label = row.get("source_label")
            if isinstance(label, str) and label:
                supported_claims_by_label.setdefault(label, []).append((index, row))
                source_row = source_rows_by_label.get(label, (None, {}))[1]
                if (
                    source_row
                    and (
                        row.get("work_id") != source_row.get("work_id")
                        or row.get("chunk_id") != source_row.get("chunk_id")
                    )
                ):
                    errors.append(
                        f"source_footer.claim_rows[{index}].source_binding: "
                        "does not match source row work and chunk"
                    )
            if not row.get("work_id"):
                errors.append(f"source_footer.claim_rows[{index}].work_id: missing")
            if not row.get("chunk_id"):
                errors.append(f"source_footer.claim_rows[{index}].chunk_id: missing")
            if not row.get("evidence_span_hash"):
                errors.append(
                    f"source_footer.claim_rows[{index}].evidence_span_hash: missing"
                )
            evidence_preview = row.get("evidence_preview")
            if not isinstance(evidence_preview, str) or not evidence_preview:
                errors.append(
                    f"source_footer.claim_rows[{index}].evidence_preview: missing"
                )
            elif span_hash and stable_hash(evidence_preview) != span_hash:
                errors.append(
                    f"source_footer.claim_rows[{index}].evidence_span_hash: "
                    "does not match evidence preview"
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
                errors.append(
                    f"source_footer.claim_rows[{index}].evidence_span: "
                    "invalid character offsets"
                )

    for label, (index, row) in source_rows_by_label.items():
        supported_rows = supported_claims_by_label.get(label, [])
        expected_supported_count = len(supported_rows)
        if row.get("supported_claim_count") != expected_supported_count:
            errors.append(
                f"source_footer.source_rows[{index}].supported_claim_count: "
                "does not match supported claim rows"
            )
        support_scores: list[float] = []
        for claim_index, claim in supported_rows:
            try:
                support_scores.append(float(claim.get("support_score", 0.0)))
            except Exception:
                errors.append(
                    f"source_footer.claim_rows[{claim_index}].support_score: "
                    "expected number"
                )
                support_scores.append(0.0)
        expected_minimum_support = (
            round(min(support_scores), 8)
            if support_scores
            else 0.0
        )
        if row.get("minimum_support_score") != expected_minimum_support:
            errors.append(
                f"source_footer.source_rows[{index}].minimum_support_score: "
                "does not match supported claim rows"
            )
        expected_span_hashes = sorted(
            {
                str(claim.get("evidence_span_hash", ""))
                for _, claim in supported_rows
                if claim.get("evidence_span_hash")
            }
        )
        span_hashes = row.get("evidence_span_hashes", [])
        if isinstance(span_hashes, list):
            observed_span_hashes = sorted(str(value) for value in span_hashes)
        else:
            errors.append(
                f"source_footer.source_rows[{index}].evidence_span_hashes: "
                "expected array"
            )
            observed_span_hashes = []
        if observed_span_hashes != expected_span_hashes:
            errors.append(
                f"source_footer.source_rows[{index}].evidence_span_hashes: "
                "does not match supported claim rows"
            )
        payout = _decimal_or_none(row.get("payout", "0"))
        if payout is None:
            errors.append(f"source_footer.source_rows[{index}].payout: invalid decimal")
            payout = Decimal("0")
        settlement_eligible = event.get("settlement_decision", {}).get(
            "eligible_for_settlement_instruction"
        ) is True
        expected_settlement = (
            "allocated_not_executed"
            if payout > Decimal("0") and settlement_eligible
            else "candidate_held_for_review"
            if payout > Decimal("0")
            else "not_allocated"
        )
        if row.get("settlement_status") != expected_settlement:
            errors.append(
                f"source_footer.source_rows[{index}].settlement_status: "
                "does not match payout"
            )
        expected_why = (
            "verified_context_bound_claim_support_identity_rights_royalty"
            if row.get("confidence") == "verified"
            and payout > Decimal("0")
            and settlement_eligible
            else "post_hoc_candidate_needs_review"
            if row.get("confidence") == "verified" and payout > Decimal("0")
            else "claim_support_needs_review"
        )
        if row.get("why") != expected_why:
            errors.append(
                f"source_footer.source_rows[{index}].why: "
                "does not match confidence and payout"
            )
        if row.get("confidence") == "verified":
            if expected_supported_count <= 0:
                errors.append(
                    f"source_footer.source_rows[{index}].confidence: "
                    "verified source has no supported claims"
                )
            if expected_minimum_support < 0.75:
                errors.append(
                    f"source_footer.source_rows[{index}].confidence: "
                    "verified source has low claim support"
                )
            for field in (
                "source_uri",
                "content_hash",
                "verification_handle",
                "evidence_preview",
            ):
                if not row.get(field):
                    errors.append(
                        f"source_footer.source_rows[{index}].confidence: "
                        f"verified source missing {field}"
                    )

    footer_hash = canonical_hash(
        {key: value for key, value in footer.items() if key != "footer_hash"}
    )
    if footer.get("footer_hash") != footer_hash:
        errors.append("source_footer.footer_hash: mismatch")
    if footer.get("source_count") != len(source_rows):
        errors.append("source_footer.source_count: does not match source rows")
    if footer.get("claim_count") != len(claim_rows):
        errors.append("source_footer.claim_count: does not match claim rows")
    try:
        rendered_text = _render_footer_text(footer, event)
    except Exception as exc:
        errors.append(f"source_footer.rendered_text: failed to recompute: {exc}")
    else:
        if footer.get("rendered_text") != rendered_text:
            errors.append("source_footer.rendered_text: does not match footer rows")

    event_hash = ""
    try:
        event_hash = event_hash_from_event(event)
    except Exception as exc:
        errors.append(f"event.event_hash: failed to recompute: {exc}")
    if event_hash and event.get("event_hash") != event_hash:
        errors.append("event.event_hash: mismatch")
    expected_event_id = f"evt_{event.get('event_hash', '')[:16]}"
    if event.get("event_id") != expected_event_id:
        errors.append("event.event_id: does not match event hash")

    bindings = (
        ("summary.event_id", summary.get("event_id"), event.get("event_id")),
        ("summary.event_hash", summary.get("event_hash"), event.get("event_hash")),
        ("source_footer.event_id", footer.get("event_id"), event.get("event_id")),
        ("source_footer.event_hash", footer.get("event_hash"), event.get("event_hash")),
        (
            "summary.source_footer_hash",
            summary.get("source_footer_hash"),
            footer.get("footer_hash"),
        ),
        (
            "summary.display_hash",
            summary.get("display_hash"),
            display.get("rendered_text_hash"),
        ),
        ("summary.source_count", summary.get("source_count"), len(source_rows)),
        (
            "summary.royalty_share_count",
            summary.get("royalty_share_count"),
            len(event.get("royalty_shares", [])),
        ),
    )
    for label, actual, expected in bindings:
        if actual != expected:
            errors.append(f"{label}: binding mismatch")

    public_verifier = footer.get("public_verifier", {})
    if not isinstance(public_verifier, dict):
        errors.append("source_footer.public_verifier: expected object")
        public_verifier = {}
    grounding_verdict = event.get("grounding_quality", {}).get("verdict", "")
    attribution_gap_verdict = event.get("attribution_gap", {}).get("verdict", "")
    if (
        response["status"] == "ready"
        and grounding_verdict not in DISPLAY_READY_GROUNDING_VERDICTS
    ):
        errors.append("status: ready response has non-display-safe grounding verdict")
    if (
        grounding_verdict not in DISPLAY_READY_GROUNDING_VERDICTS
        and not any(
            isinstance(error, str) and error.startswith("grounding_quality:")
            for error in response["audit_errors"]
        )
    ):
        errors.append("audit_errors: missing grounding display gate error")
    if summary.get("grounding_verdict") != grounding_verdict:
        errors.append("summary.grounding_verdict: binding mismatch")
    if summary.get("attribution_gap_verdict") != attribution_gap_verdict:
        errors.append("summary.attribution_gap_verdict: binding mismatch")
    if public_verifier.get("event_hash") != event.get("event_hash"):
        errors.append("source_footer.public_verifier.event_hash: binding mismatch")
    if public_verifier.get("grounding_verdict") != grounding_verdict:
        errors.append(
            "source_footer.public_verifier.grounding_verdict: binding mismatch"
        )
    if public_verifier.get("attribution_gap_verdict") != attribution_gap_verdict:
        errors.append(
            "source_footer.public_verifier.attribution_gap_verdict: binding mismatch"
        )
    if public_verifier.get("generation_evidence_mode") != event.get(
        "generation_evidence", {}
    ).get("mode"):
        errors.append(
            "source_footer.public_verifier.generation_evidence_mode: binding mismatch"
        )
    if public_verifier.get("settlement_status") != event.get(
        "settlement_decision", {}
    ).get("status"):
        errors.append("source_footer.public_verifier.settlement_status: binding mismatch")
    if public_verifier.get("settlement_instruction_eligible") != event.get(
        "settlement_decision", {}
    ).get("eligible_for_settlement_instruction"):
        errors.append(
            "source_footer.public_verifier.settlement_instruction_eligible: binding mismatch"
        )

    display_bindings = (
        ("display.status", display.get("status"), response["status"]),
        ("display.event_id", display.get("event_id"), event.get("event_id")),
        ("display.event_hash", display.get("event_hash"), event.get("event_hash")),
        (
            "display.source_footer_hash",
            display.get("source_footer_hash"),
            footer.get("footer_hash"),
        ),
        (
            "display.answer_text_hash",
            display.get("answer_text_hash"),
            canonical_hash(str(event.get("answer_text", event.get("output", "")))),
        ),
    )
    for label, actual, expected in display_bindings:
        if actual != expected:
            errors.append(f"{label}: binding mismatch")
    if display.get("render_policy") != "answer_plus_verified_source_footer":
        errors.append(
            "display.render_policy: expected answer_plus_verified_source_footer"
        )
    expected_display_text = _render_display_text(footer, event)
    if display.get("rendered_text") != expected_display_text:
        errors.append("display.rendered_text: does not match answer plus footer")
    if display.get("rendered_text_hash") != canonical_hash(expected_display_text):
        errors.append("display.rendered_text_hash: mismatch")
    display_text_fields, display_text_errors = _display_text_result(
        display_text=display_text,
        expected_display_text=expected_display_text,
        display_text_path=display_text_path,
    )
    errors.extend(display_text_errors)

    source_grounding_acceptance = _source_grounding_acceptance(
        footer=footer,
        display=display,
        event=event,
        summary=summary,
    )
    source_grounding_ready = source_grounding_acceptance.get("status") == "passed"
    if response["status"] == "ready" and not source_grounding_ready:
        errors.append(
            "source_grounding_acceptance: ready response does not meet grounded "
            "source display profile"
        )

    verification_passed = not errors
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "passed" if verification_passed else "failed",
        "errors": errors,
        "response_status": str(response.get("status", "")),
        "production_display_ready": bool(
            verification_passed
            and response.get("status") == "ready"
            and grounding_verdict in DISPLAY_READY_GROUNDING_VERDICTS
            and source_grounding_ready
        ),
        "display_text_status": display_text_fields["display_text_status"],
        "display_text_hash": display_text_fields["display_text_hash"],
        "display_text_path": display_text_fields["display_text_path"],
        "source_grounding_acceptance": source_grounding_acceptance,
        "event_id": str(event.get("event_id", "")),
        "event_hash": str(event.get("event_hash", "")),
        "footer_hash": str(footer.get("footer_hash", "")),
        "display_hash": str(display.get("rendered_text_hash", "")),
        "source_count": len(source_rows),
        "claim_count": len(claim_rows),
        "grounding_verdict": str(summary.get("grounding_verdict", "")),
        "attribution_gap_verdict": str(summary.get("attribution_gap_verdict", "")),
    }


def render_text(report: dict[str, Any]) -> str:
    acceptance = report.get("source_grounding_acceptance", {})
    if not isinstance(acceptance, dict):
        acceptance = {}
    lines = [
        f"service_response_verification status: {report['status']}",
        f"response_status: {report.get('response_status', 'unknown')}",
        "production_display_ready: "
        f"{json.dumps(bool(report.get('production_display_ready', False)))}",
        "source_grounding_acceptance: "
        f"{acceptance.get('status', 'unknown')}",
        "source_grounding_supported_claims: "
        f"{acceptance.get('supported_claim_count', 0)}",
        "claim_evidence_rows: "
        f"{acceptance.get('claim_evidence_row_count', 0)}/"
        f"{acceptance.get('supported_claim_count', 0)} supported claims",
        "claim_evidence_status: "
        f"{acceptance.get('claim_evidence_status', 'unknown')}",
        "claim_warrant_strength: "
        f"{acceptance.get('claim_warrant_strength_count', 0)}/"
        f"{acceptance.get('supported_claim_count', 0)} supported claims",
        "claim_warrant_strength_status: "
        f"{acceptance.get('claim_warrant_strength_status', 'unknown')}",
        "claim_warrant_profile: "
        f"{acceptance.get('claim_warrant_profile', '')}",
        "claim_source_disagreement: "
        f"{acceptance.get('claim_source_disagreement_count', 0)}/"
        f"{acceptance.get('supported_claim_count', 0)} supported claims",
        "claim_source_disagreement_status: "
        f"{acceptance.get('claim_source_disagreement_status', 'unknown')}",
        "source_disagreement_profile: "
        f"{acceptance.get('source_disagreement_profile', '')}",
        "claim_source_closure_rows: "
        f"{acceptance.get('claim_source_closure_count', 0)}/"
        f"{acceptance.get('supported_claim_count', 0)} supported claims",
        "claim_source_closure_status: "
        f"{acceptance.get('claim_source_closure_status', 'unknown')}",
        "answer_claim_coverage: "
        f"{acceptance.get('answer_claim_row_coverage_count', 0)}/"
        f"{acceptance.get('answer_claim_unit_count', 0)} answer claims",
        "answer_claim_coverage_status: "
        f"{acceptance.get('answer_claim_coverage_status', 'unknown')}",
        "model_reliance_claim_status: "
        f"{acceptance.get('model_reliance_claim_status', 'unknown')}",
        "model_reliance_claim_markers: "
        f"{', '.join(acceptance.get('model_reliance_claim_markers', []))}",
        "source_grounding_minimum_support: "
        f"{acceptance.get('minimum_support_score', 0.0)}",
        "source_grounding_royalty_covered_sources: "
        f"{acceptance.get('royalty_covered_source_count', 0)}",
        "attribution_gap_status: "
        f"{acceptance.get('attribution_gap_status', 'unknown')}",
        "attribution_gap_verdict: "
        f"{acceptance.get('attribution_gap_verdict', '')}",
        "attribution_gap_coverage: "
        f"accessed={acceptance.get('attribution_gap_accessed_source_count', 0)} "
        f"credited={acceptance.get('attribution_gap_credited_source_count', 0)} "
        "consumed_without_credit="
        f"{acceptance.get('attribution_gap_consumed_without_credit_count', 0)} "
        "cited_without_access="
        f"{acceptance.get('attribution_gap_cited_without_access_count', 0)} "
        f"paid_hidden={acceptance.get('attribution_gap_paid_hidden_count', 0)}",
        "source_locators: "
        f"{acceptance.get('source_locator_count', 0)}/"
        f"{acceptance.get('source_count', 0)} rows",
        "source_locator_status: "
        f"{acceptance.get('source_locator_status', 'unknown')}",
        "source_identity: "
        f"{acceptance.get('source_identity_count', 0)}/"
        f"{acceptance.get('source_count', 0)} rows",
        "source_identity_status: "
        f"{acceptance.get('source_identity_status', 'unknown')}",
        "temporal_claim_markers: "
        f"{', '.join(acceptance.get('temporal_claim_markers', []))}",
        "temporal_grounding_status: "
        f"{acceptance.get('temporal_grounding_status', 'unknown')}",
        "source_usage_metrics: "
        f"{acceptance.get('source_usage_metric_row_count', 0)}/"
        f"{acceptance.get('source_count', 0)} rows",
        "source_usage_metric_status: "
        f"{acceptance.get('source_usage_metric_status', 'unknown')}",
        "source_usage_metric_provenance: "
        f"{acceptance.get('source_usage_metric_provenance_count', 0)}/"
        f"{acceptance.get('source_count', 0)} rows",
        "source_usage_metric_provenance_status: "
        f"{acceptance.get('source_usage_metric_provenance_status', 'unknown')}",
        "source_usage_metric_profile: "
        f"{acceptance.get('source_usage_metric_profile', '')}",
        "source_usage_metric_scope: "
        f"{acceptance.get('source_usage_metric_scope', '')}",
        "answer_citation_markers: "
        f"{acceptance.get('resolved_answer_citation_marker_count', 0)}/"
        f"{acceptance.get('answer_citation_marker_count', 0)} resolved",
        "answer_citation_marker_status: "
        f"{acceptance.get('citation_marker_status', 'unknown')}",
        "answer_citation_marker_list: "
        f"{', '.join(acceptance.get('answer_citation_markers', []))}",
        "unresolved_answer_citation_markers: "
        f"{', '.join(acceptance.get('unresolved_answer_citation_markers', []))}",
        "answer_link_uris: "
        f"{acceptance.get('resolved_answer_link_uri_count', 0)}/"
        f"{acceptance.get('answer_link_uri_count', 0)} resolved",
        "answer_link_status: "
        f"{acceptance.get('answer_link_status', 'unknown')}",
        "answer_link_uri_list: "
        f"{', '.join(acceptance.get('answer_link_uris', []))}",
        "unresolved_answer_link_uris: "
        f"{', '.join(acceptance.get('unresolved_answer_link_uris', []))}",
        "display_text_status: "
        f"{report.get('display_text_status', 'not_checked')}",
        "display_text_hash: "
        f"{report.get('display_text_hash', '')}",
        "display_text_path: "
        f"{report.get('display_text_path', '')}",
        f"event_id: {report['event_id']}",
        f"event_hash: {report['event_hash']}",
        f"footer_hash: {report['footer_hash']}",
        f"display_hash: {report['display_hash']}",
        f"source_count: {report['source_count']}",
        f"claim_count: {report['claim_count']}",
        f"grounding_verdict: {report['grounding_verdict']}",
        f"attribution_gap_verdict: {report['attribution_gap_verdict']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    if acceptance.get("errors"):
        lines.append("source_grounding_acceptance_errors:")
        lines.extend(f"- {error}" for error in acceptance["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument(
        "--display-text",
        type=Path,
        help="Optional copied/exported answer text to verify against display.rendered_text.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    display_text: str | None = None
    display_text_path = str(args.display_text) if args.display_text else ""
    if args.display_text:
        try:
            display_text = args.display_text.read_text(encoding="utf-8")
        except Exception as exc:
            report = {
                "schema": VERIFICATION_SCHEMA,
                "status": "failed",
                "errors": [f"display_text: failed to read text: {exc}"],
                "response_status": "unknown",
                "production_display_ready": False,
                "display_text_status": "failed",
                "display_text_hash": "",
                "display_text_path": display_text_path,
                "source_grounding_acceptance": _empty_source_grounding_acceptance(
                    ["display text read failed"]
                ),
                "event_id": "",
                "event_hash": "",
                "footer_hash": "",
                "display_hash": "",
                "source_count": 0,
                "claim_count": 0,
                "grounding_verdict": "",
                "attribution_gap_verdict": "",
            }
            print(
                json.dumps(report, indent=2, sort_keys=True)
                if args.json
                else render_text(report)
            )
            return 1

    try:
        response = load_json(args.response)
    except Exception as exc:
        report = {
            "schema": VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": [f"response: failed to read JSON: {exc}"],
            "response_status": "unknown",
            "production_display_ready": False,
            "display_text_status": "not_checked"
            if display_text is None
            else "failed",
            "display_text_hash": ""
            if display_text is None
            else canonical_hash(display_text),
            "display_text_path": display_text_path,
            "source_grounding_acceptance": _empty_source_grounding_acceptance(
                ["response read failed"]
            ),
            "event_id": "",
            "event_hash": "",
            "footer_hash": "",
            "display_hash": "",
            "source_count": 0,
            "claim_count": 0,
            "grounding_verdict": "",
            "attribution_gap_verdict": "",
        }
    else:
        report = verify_service_response(
            response,
            display_text=display_text,
            display_text_path=display_text_path,
        )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
