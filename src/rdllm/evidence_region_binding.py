"""Evidence-region binding reports for user-visible citation footers.

This layer closes the gap between "the answer cites source S1" and "the cited
claim is actually supported by this exact source location."  The public report
stores source metadata, page/line/char/bbox coordinates, and hash commitments,
but never raw prompt, answer, source, or evidence text.
"""

from __future__ import annotations

import json
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

EVIDENCE_REGION_BINDING_VERSION = "rdllm-evidence-region-binding/v1"
EVIDENCE_REGION_BINDING_SCHEMA = (
    "docs/schemas/evidence_region_binding_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L97"

DECLARED_HASH_FIELDS = (
    "binding_report_hash",
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

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "response_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "region_text",
    "quote",
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

TEXT_REGION_TYPES = {"text_span", "table_cell"}
VISUAL_REGION_TYPES = {"visual_bbox", "image_bbox", "pdf_bbox", "video_region"}
TEMPORAL_REGION_TYPES = {"audio_segment", "video_segment"}


def load_evidence_region_binding_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay an evidence-region binding report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"binding_report_hash", "signature"}
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
    return hash_payload(_hashable_artifact(artifact)) if artifact else ""


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(report: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(audit_input: dict[str, Any]) -> dict[str, Any]:
    configured = dict(audit_input.get("policy", {}))
    return {
        "require_public_location": bool(
            configured.get("require_public_location", True)
        ),
        "require_region_hash": bool(configured.get("require_region_hash", True)),
        "require_wrong_region_controls": bool(
            configured.get("require_wrong_region_controls", True)
        ),
        "require_all_rendered_claim_spans_bound": bool(
            configured.get("require_all_rendered_claim_spans_bound", True)
        ),
        "require_all_footer_span_prefixes_bound": bool(
            configured.get("require_all_footer_span_prefixes_bound", True)
        ),
        "require_rendered_audit_ready": bool(
            configured.get("require_rendered_audit_ready", True)
        ),
        "require_claim_source_report_ready": bool(
            configured.get("require_claim_source_report_ready", True)
        ),
        "minimum_region_coverage": str(
            configured.get("minimum_region_coverage", "1.0")
        ),
    }


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_or_zero(value: Any) -> float:
    try:
        return round(float(value or 0.0), 6)
    except (TypeError, ValueError):
        return 0.0


def _bbox(row: dict[str, Any]) -> dict[str, float]:
    value = row.get("bbox", {})
    if not isinstance(value, dict):
        value = {}
    return {
        "x": _float_or_zero(value.get("x", row.get("x", 0.0))),
        "y": _float_or_zero(value.get("y", row.get("y", 0.0))),
        "width": _float_or_zero(value.get("width", row.get("width", 0.0))),
        "height": _float_or_zero(value.get("height", row.get("height", 0.0))),
    }


def _region_text_hash(region: dict[str, Any]) -> str:
    return str(
        region.get("region_text_hash")
        or region.get("evidence_hash")
        or stable_hash(str(region.get("region_text", "")))
    )


def _region_public_location(row: dict[str, Any]) -> bool:
    region_type = str(row.get("region_type", "text_span"))
    page = _int_or_zero(row.get("page"))
    line_start = _int_or_zero(row.get("line_start"))
    line_end = _int_or_zero(row.get("line_end"))
    start_char = _int_or_zero(row.get("start_char"))
    end_char = _int_or_zero(row.get("end_char"))
    bbox = row.get("bbox", {})

    if region_type in TEXT_REGION_TYPES:
        return bool(
            page > 0
            or (line_start > 0 and line_end >= line_start)
            or (end_char > start_char)
        )
    if region_type in VISUAL_REGION_TYPES:
        return page > 0 and bbox.get("width", 0.0) > 0 and bbox.get("height", 0.0) > 0
    if region_type in TEMPORAL_REGION_TYPES:
        start = _float_or_zero(row.get("start_seconds"))
        end = _float_or_zero(row.get("end_seconds"))
        return end > start
    return bool(page > 0 or end_char > start_char)


def _source_region_rows(
    audit_input: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for source_index, source in enumerate(
        audit_input.get("source_snapshots", []), start=1
    ):
        source_id = str(source.get("source_id") or f"source:{source_index}")
        source_label = str(source.get("source_label") or source.get("label") or "")
        source_version_hash = str(
            source.get("source_version_hash")
            or source.get("snapshot_hash")
            or stable_hash(str(source.get("content", "")))
        )
        content_hash = str(
            source.get("content_hash") or stable_hash(str(source.get("content", "")))
        )
        regions = source.get("regions", [])
        for region_index, region in enumerate(regions, start=1):
            region_id = str(region.get("region_id") or f"region:{region_index}")
            region_type = str(region.get("region_type", "text_span"))
            bbox = _bbox(region)
            public = {
                "source_id": source_id,
                "source_label": source_label,
                "work_id": str(source.get("work_id", "")),
                "chunk_id": str(source.get("chunk_id", "")),
                "source_uri": str(source.get("source_uri", "")),
                "content_hash": content_hash,
                "source_version_hash": source_version_hash,
                "region_id": region_id,
                "region_type": region_type,
                "page": _int_or_zero(region.get("page")),
                "section_hash": stable_hash(str(region.get("section", ""))),
                "line_start": _int_or_zero(region.get("line_start")),
                "line_end": _int_or_zero(region.get("line_end")),
                "start_char": _int_or_zero(region.get("start_char")),
                "end_char": _int_or_zero(region.get("end_char")),
                "start_seconds": _float_or_zero(region.get("start_seconds")),
                "end_seconds": _float_or_zero(region.get("end_seconds")),
                "bbox": bbox,
                "bbox_hash": hash_payload(bbox),
                "evidence_span_prefixes": sorted(
                    str(prefix)
                    for prefix in region.get("evidence_span_prefixes", [])
                    if str(prefix)
                ),
                "claim_ids": sorted(
                    str(claim_id)
                    for claim_id in region.get("claim_ids", [])
                    if str(claim_id)
                ),
                "region_text_hash": _region_text_hash(region),
            }
            public["public_location"] = _region_public_location(public)
            public["location_hash"] = hash_payload(
                {
                    "source_id": public["source_id"],
                    "source_label": public["source_label"],
                    "region_id": public["region_id"],
                    "region_type": public["region_type"],
                    "page": public["page"],
                    "section_hash": public["section_hash"],
                    "line_start": public["line_start"],
                    "line_end": public["line_end"],
                    "start_char": public["start_char"],
                    "end_char": public["end_char"],
                    "start_seconds": public["start_seconds"],
                    "end_seconds": public["end_seconds"],
                    "bbox_hash": public["bbox_hash"],
                }
            )
            public["region_hash"] = hash_payload(public)
            rows.append(public)
            index[region_id] = public
    return rows, index


def _rendered_claim_rows(
    rendered_attribution_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    return list(
        rendered_attribution_audit.get("parsed_markdown", {}).get(
            "claim_evidence_rows", []
        )
    )


def _rendered_claim_pairs(rendered_attribution_audit: dict[str, Any]) -> set[tuple[int, str, str]]:
    return {
        (
            _int_or_zero(row.get("claim_index")),
            str(row.get("source_label", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        for row in _rendered_claim_rows(rendered_attribution_audit)
    }


def _rendered_claim_row_index(
    rendered_attribution_audit: dict[str, Any],
) -> dict[tuple[int, str, str], dict[str, Any]]:
    return {
        (
            _int_or_zero(row.get("claim_index")),
            str(row.get("source_label", "")),
            str(row.get("evidence_span_prefix", "")),
        ): row
        for row in _rendered_claim_rows(rendered_attribution_audit)
    }


def _footer_span_pairs(rendered_attribution_audit: dict[str, Any]) -> set[tuple[str, str]]:
    rows = rendered_attribution_audit.get("parsed_markdown", {}).get(
        "source_footer_rows", []
    )
    return {
        (str(row.get("label", "")), str(span))
        for row in rows
        for span in row.get("evidence_span_prefixes", [])
    }


def _claim_source_claims(
    claim_source_attribution_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("claim_id", "")): row
        for row in claim_source_attribution_report.get("claims", [])
        if row.get("claim_id")
    }


def _source_label_index(
    source_region_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in source_region_rows:
        label = str(row.get("source_label", ""))
        if label and label not in index:
            index[label] = row
    return index


def _link_region_checks(
    link: dict[str, Any],
    *,
    region_index: dict[str, dict[str, Any]],
    rendered_index: dict[tuple[int, str, str], dict[str, Any]],
    claim_source_claims: dict[str, dict[str, Any]],
    require_claim_id: bool = True,
) -> tuple[dict[str, bool], dict[str, Any]]:
    claim_index = _int_or_zero(link.get("claim_index"))
    source_label = str(link.get("source_label", ""))
    evidence_span_prefix = str(link.get("evidence_span_prefix", ""))
    region_id = str(link.get("region_id", ""))
    claim_id = str(link.get("claim_id", ""))
    source_id = str(link.get("source_id", ""))
    chunk_id = str(link.get("chunk_id", ""))
    rendered_row = rendered_index.get((claim_index, source_label, evidence_span_prefix))
    region = region_index.get(region_id)
    claim_source_row = claim_source_claims.get(claim_id)
    evidence_hash = str(link.get("evidence_hash", ""))

    checks = {
        "region_exists": region is not None,
        "rendered_claim_span_exists": rendered_row is not None,
        "source_label_matches_region": bool(
            region and source_label == str(region.get("source_label", ""))
        ),
        "source_id_matches_region": bool(
            region and (not source_id or source_id == str(region.get("source_id", "")))
        ),
        "chunk_id_matches_region": bool(
            region and (not chunk_id or chunk_id == str(region.get("chunk_id", "")))
        ),
        "evidence_prefix_in_region": bool(
            region
            and evidence_span_prefix
            and evidence_span_prefix in region.get("evidence_span_prefixes", [])
        ),
        "region_location_actionable": bool(
            region and region.get("public_location") is True
        ),
        "claim_id_matches_region": (
            bool(region and claim_id and claim_id in region.get("claim_ids", []))
            if require_claim_id
            else True
        ),
        "claim_source_report_has_claim": claim_source_row is not None,
        "claim_source_report_grounded": bool(
            claim_source_row and claim_source_row.get("decision") == "grounded"
        ),
        "claim_source_report_accepts_source": bool(
            claim_source_row
            and (
                not source_id
                or source_id
                in {str(item) for item in claim_source_row.get("accepted_source_ids", [])}
            )
        ),
        "rendered_char_range_matches": bool(
            rendered_row
            and (
                not link.get("start_char")
                or _int_or_zero(link.get("start_char"))
                == _int_or_zero(rendered_row.get("start_char"))
            )
            and (
                not link.get("end_char")
                or _int_or_zero(link.get("end_char"))
                == _int_or_zero(rendered_row.get("end_char"))
            )
        ),
        "evidence_hash_matches_region": bool(
            region
            and (
                not evidence_hash
                or evidence_hash == str(region.get("region_text_hash", ""))
            )
        ),
    }
    public = {
        "claim_id": claim_id,
        "claim_index": claim_index,
        "source_label": source_label,
        "source_id": source_id,
        "chunk_id": chunk_id,
        "evidence_span_prefix": evidence_span_prefix,
        "region_id": region_id,
        "expected_support": bool(link.get("expected_support", True)),
        "evidence_hash": evidence_hash,
        "rendered_claim_evidence_row_hash": str(
            (rendered_row or {}).get("claim_evidence_row_hash", "")
        ),
        "region_hash": str((region or {}).get("region_hash", "")),
        "location_hash": str((region or {}).get("location_hash", "")),
        "checks": checks,
    }
    public["link_hash"] = hash_payload(public)
    return checks, public


def _claim_region_rows(
    audit_input: dict[str, Any],
    *,
    region_index: dict[str, dict[str, Any]],
    rendered_index: dict[tuple[int, str, str], dict[str, Any]],
    claim_source_claims: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in audit_input.get("claim_region_links", []):
        _, row = _link_region_checks(
            dict(link),
            region_index=region_index,
            rendered_index=rendered_index,
            claim_source_claims=claim_source_claims,
            require_claim_id=True,
        )
        row["verified"] = all(row["checks"].values()) and row["expected_support"]
        row["link_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "link_hash"}
        )
        rows.append(row)
    return rows


def _wrong_region_control_rows(
    audit_input: dict[str, Any],
    *,
    region_index: dict[str, dict[str, Any]],
    rendered_index: dict[tuple[int, str, str], dict[str, Any]],
    claim_source_claims: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, control in enumerate(
        audit_input.get("negative_region_links", []), start=1
    ):
        checks, row = _link_region_checks(
            dict(control),
            region_index=region_index,
            rendered_index=rendered_index,
            claim_source_claims=claim_source_claims,
            require_claim_id=True,
        )
        would_bind = all(checks.values())
        row.update(
            {
                "control_id": str(control.get("control_id", f"wrong-region:{index}")),
                "expected_rejected": bool(control.get("expected_rejected", True)),
                "would_bind_if_accepted": would_bind,
                "rejected": bool(control.get("expected_rejected", True))
                and not would_bind,
            }
        )
        row["control_hash"] = hash_payload(
            {key: value for key, value in row.items() if key not in {"link_hash", "control_hash"}}
        )
        rows.append(row)
    return rows


def _region_coverage(
    claim_region_rows: list[dict[str, Any]],
    rendered_pairs: set[tuple[int, str, str]],
) -> float:
    if not rendered_pairs:
        return 1.0 if not claim_region_rows else 0.0
    bound_pairs = {
        (
            _int_or_zero(row.get("claim_index")),
            str(row.get("source_label", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        for row in claim_region_rows
        if row.get("verified") is True
    }
    return round(len(bound_pairs & rendered_pairs) / len(rendered_pairs), 8)


def _footer_coverage(
    claim_region_rows: list[dict[str, Any]],
    footer_pairs: set[tuple[str, str]],
) -> float:
    if not footer_pairs:
        return 1.0 if not claim_region_rows else 0.0
    bound_pairs = {
        (str(row.get("source_label", "")), str(row.get("evidence_span_prefix", "")))
        for row in claim_region_rows
        if row.get("verified") is True
    }
    return round(len(bound_pairs & footer_pairs) / len(footer_pairs), 8)


def make_evidence_region_binding_report(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report binding rendered citations to exact source regions."""

    response_envelope = dict(audit_input.get("response_envelope", {}))
    rendered_audit = dict(audit_input.get("rendered_attribution_audit", {}))
    claim_source_report = dict(audit_input.get("claim_source_attribution_report", {}))
    citation_footer_contract = dict(audit_input.get("citation_footer_contract", {}))
    policy = _policy(audit_input)
    source_region_rows, region_index = _source_region_rows(audit_input)
    rendered_index = _rendered_claim_row_index(rendered_audit)
    rendered_pairs = _rendered_claim_pairs(rendered_audit)
    footer_pairs = _footer_span_pairs(rendered_audit)
    claim_source_claims = _claim_source_claims(claim_source_report)
    claim_rows = _claim_region_rows(
        audit_input,
        region_index=region_index,
        rendered_index=rendered_index,
        claim_source_claims=claim_source_claims,
    )
    wrong_region_rows = _wrong_region_control_rows(
        audit_input,
        region_index=region_index,
        rendered_index=rendered_index,
        claim_source_claims=claim_source_claims,
    )
    region_coverage = _region_coverage(claim_rows, rendered_pairs)
    footer_coverage = _footer_coverage(claim_rows, footer_pairs)
    required_coverage = float(policy["minimum_region_coverage"])
    bound_pairs = {
        (
            _int_or_zero(row.get("claim_index")),
            str(row.get("source_label", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        for row in claim_rows
        if row.get("verified") is True
    }
    bound_footer_pairs = {
        (str(row.get("source_label", "")), str(row.get("evidence_span_prefix", "")))
        for row in claim_rows
        if row.get("verified") is True
    }
    source_labels = _source_label_index(source_region_rows)
    checks = {
        "response_envelope_hash_reproducible": _artifact_hash_is_reproducible(
            response_envelope
        ),
        "rendered_attribution_audit_hash_reproducible": _artifact_hash_is_reproducible(
            rendered_audit
        ),
        "claim_source_attribution_hash_reproducible": _artifact_hash_is_reproducible(
            claim_source_report
        ),
        "citation_footer_contract_hash_reproducible": _artifact_hash_is_reproducible(
            citation_footer_contract
        ),
        "rendered_attribution_audit_ready": (
            rendered_audit.get("summary", {}).get("status") == "ready"
            and rendered_audit.get("summary", {}).get("target_certification_level")
            == "RDLLM-L80"
        )
        if policy["require_rendered_audit_ready"]
        else True,
        "claim_source_report_ready": (
            claim_source_report.get("summary", {}).get("status") == "ready"
            and claim_source_report.get("summary", {}).get("target_certification_level")
            == "RDLLM-L87"
        )
        if policy["require_claim_source_report_ready"]
        else True,
        "citation_footer_contract_verified": citation_footer_contract.get(
            "summary", {}
        ).get("status")
        in {"verified", "ready"},
        "source_snapshots_have_content_hashes": all(
            row.get("content_hash") and row.get("source_version_hash")
            for row in source_region_rows
        )
        and bool(source_region_rows),
        "region_hashes_reproducible": all(
            hash_payload({key: value for key, value in row.items() if key != "region_hash"})
            == row.get("region_hash")
            for row in source_region_rows
        )
        if policy["require_region_hash"]
        else True,
        "every_region_has_public_location": all(
            row.get("public_location") is True for row in source_region_rows
        )
        if policy["require_public_location"]
        else True,
        "all_claim_region_links_verified": all(row.get("verified") is True for row in claim_rows)
        and bool(claim_rows),
        "every_rendered_claim_span_bound": rendered_pairs <= bound_pairs
        if policy["require_all_rendered_claim_spans_bound"]
        else True,
        "every_footer_span_prefix_bound": footer_pairs <= bound_footer_pairs
        if policy["require_all_footer_span_prefixes_bound"]
        else True,
        "minimum_region_coverage_met": region_coverage >= required_coverage,
        "minimum_footer_span_coverage_met": footer_coverage >= required_coverage,
        "wrong_region_controls_rejected": all(
            row.get("rejected") is True for row in wrong_region_rows
        )
        and (bool(wrong_region_rows) if policy["require_wrong_region_controls"] else True),
        "source_labels_have_region_rows": all(
            label in source_labels
            for _, label, _ in rendered_pairs
        ),
        "private_text_not_disclosed": True,
    }
    report = {
        "version": EVIDENCE_REGION_BINDING_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(audit_input.get("case_id", "evidence-region-binding")),
            "status": "ready" if all(checks.values()) else "needs_review",
        },
        "policy": policy,
        "artifact_bindings": {
            "response_envelope_hash": _declared_hash(response_envelope),
            "rendered_attribution_audit_hash": _declared_hash(rendered_audit),
            "claim_source_attribution_report_hash": _declared_hash(
                claim_source_report
            ),
            "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
        },
        "source_region_rows": source_region_rows,
        "claim_region_rows": claim_rows,
        "wrong_region_control_rows": wrong_region_rows,
        "coverage": {
            "rendered_claim_span_count": len(rendered_pairs),
            "bound_rendered_claim_span_count": len(bound_pairs & rendered_pairs),
            "rendered_claim_region_coverage": region_coverage,
            "footer_span_prefix_count": len(footer_pairs),
            "bound_footer_span_prefix_count": len(bound_footer_pairs & footer_pairs),
            "footer_span_region_coverage": footer_coverage,
        },
        "checks": checks,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "raw_region_text_disclosed": False,
            "public_report_uses_hashes_and_locations": True,
        },
        "schemas": {
            "evidence_region_binding_report": EVIDENCE_REGION_BINDING_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "claim_source_attribution_report": "docs/schemas/claim_source_attribution_report.schema.json",
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "needs_review",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_region_count": len(source_region_rows),
            "claim_region_link_count": len(claim_rows),
            "wrong_region_control_count": len(wrong_region_rows),
            "rendered_claim_span_count": len(rendered_pairs),
            "bound_rendered_claim_span_count": len(bound_pairs & rendered_pairs),
            "rendered_claim_region_coverage": region_coverage,
            "footer_span_region_coverage": footer_coverage,
            "failed_check_count": sum(1 for passed in checks.values() if not passed),
            "public_location_binding_supported": checks[
                "all_claim_region_links_verified"
            ]
            and checks["every_rendered_claim_span_bound"],
            "anti_wrong_region_controls_passed": checks[
                "wrong_region_controls_rejected"
            ],
            "privacy_preserved": True,
        },
    }
    private_ok = (
        not _contains_private_fields(report)
        and _private_strings_absent(report, audit_input)
    )
    report["checks"]["private_text_not_disclosed"] = private_ok
    report["summary"]["privacy_preserved"] = private_ok
    report["summary"]["failed_check_count"] = sum(
        1 for passed in report["checks"].values() if not passed
    )
    report["case"]["status"] = (
        "ready" if all(report["checks"].values()) else "needs_review"
    )
    report["summary"]["status"] = report["case"]["status"]
    report["summary"]["public_location_binding_supported"] = (
        report["checks"]["all_claim_region_links_verified"]
        and report["checks"]["every_rendered_claim_span_bound"]
        and report["checks"]["every_region_has_public_location"]
    )
    report["binding_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_evidence_region_binding_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "policy",
        "artifact_bindings",
        "source_region_rows",
        "claim_region_rows",
        "wrong_region_control_rows",
        "coverage",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "binding_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence-region binding field: {key}")
    if errors:
        return errors
    if report.get("version") != EVIDENCE_REGION_BINDING_VERSION:
        errors.append("evidence-region binding version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence-region binding target level is incorrect")
    if "evidence_region_binding_report" not in report.get("schemas", {}):
        errors.append("missing evidence-region binding schema")
    for key in (
        "response_envelope_hash",
        "rendered_attribution_audit_hash",
        "claim_source_attribution_report_hash",
        "citation_footer_contract_hash",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing evidence-region artifact binding: {key}")
    for row in report.get("source_region_rows", []):
        for key in (
            "source_id",
            "source_label",
            "chunk_id",
            "content_hash",
            "region_id",
            "region_type",
            "location_hash",
            "region_text_hash",
            "region_hash",
        ):
            if key not in row:
                errors.append(f"missing source-region row field: {key}")
    for row in report.get("claim_region_rows", []):
        for key in (
            "claim_id",
            "claim_index",
            "source_label",
            "evidence_span_prefix",
            "region_id",
            "checks",
            "verified",
            "link_hash",
        ):
            if key not in row:
                errors.append(f"missing claim-region row field: {key}")
    return errors


def verify_evidence_region_binding_report(
    report: dict[str, Any],
    audit_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an evidence-region binding report against private source snapshots."""

    errors = validate_evidence_region_binding_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("binding_report_hash", ""):
        errors.append("evidence-region binding report hash is not reproducible")
    expected = make_evidence_region_binding_report(
        audit_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "policy",
        "artifact_bindings",
        "source_region_rows",
        "claim_region_rows",
        "wrong_region_control_rows",
        "coverage",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence-region binding {key} does not match inputs")
    if expected.get("binding_report_hash") != report.get("binding_report_hash"):
        errors.append("evidence-region binding hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("evidence-region binding status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"evidence-region binding check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence-region binding report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence-region binding signature is invalid")
    return errors
