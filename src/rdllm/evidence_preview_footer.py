"""Evidence-preview footers for user-visible grounded answers.

This layer turns a hash-only grounded footer into a human-inspectable footer by
publishing short, permissioned evidence snippets for each visible verified claim.
It binds those snippets to L120 warrant rows and L121 source-origin rows so the
footer is useful to readers without exposing full source text, prompts, or
private reasoning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash
from rdllm.transparency import merkle_root

EVIDENCE_PREVIEW_FOOTER_VERSION = "rdllm-evidence-preview-footer/v1"
EVIDENCE_PREVIEW_FOOTER_SCHEMA = "docs/schemas/evidence_preview_footer.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L122"
MINIMUM_INPUT_LEVEL = "RDLLM-L121"

DEFAULT_MAX_EXCERPT_WORDS = 40
DEFAULT_MAX_EXCERPT_CHARS = 320

ALLOWED_EXCERPT_LICENSE_STATUSES = {
    "licensed_excerpt",
    "public_domain",
    "cc_by",
    "cc_by_sa",
    "creator_permitted",
    "fair_use_excerpt",
    "platform_preview_allowed",
}

DECLARED_HASH_FIELDS = (
    "evidence_preview_footer_hash",
    "source_origin_lineage_hash",
    "warranted_source_footer_hash",
    "grounded_source_footer_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "report_hash",
    "contract_hash",
    "footer_hash",
    "receipt_hash",
    "envelope_hash",
    "card_hash",
    "summary_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_answer_text",
    "claim_text",
    "raw_claim",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "bank_account",
    "account_number",
    "tax_id",
    "secret",
    "private_key",
    "raw_license_token",
}


def load_evidence_preview_footer_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L122 evidence-preview footer."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"evidence_preview_footer_hash", "signature"}
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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in PRIVATE_FIELD_NAMES or _contains_private_fields(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(report: dict[str, Any], preview_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in preview_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _policy(preview_input: dict[str, Any]) -> dict[str, Any]:
    policy = preview_input.get("policy", {})
    return {
        "profile": "rdllm-evidence-preview-footer-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "max_excerpt_words": int(
            policy.get("max_excerpt_words", DEFAULT_MAX_EXCERPT_WORDS) or DEFAULT_MAX_EXCERPT_WORDS
        ),
        "max_excerpt_chars": int(
            policy.get("max_excerpt_chars", DEFAULT_MAX_EXCERPT_CHARS) or DEFAULT_MAX_EXCERPT_CHARS
        ),
        "allowed_excerpt_license_statuses": sorted(
            str(item)
            for item in policy.get(
                "allowed_excerpt_license_statuses",
                ALLOWED_EXCERPT_LICENSE_STATUSES,
            )
        ),
        "verified_claims_require_preview": bool(
            policy.get("verified_claims_require_preview", True)
        ),
        "public_source_uri_required": bool(policy.get("public_source_uri_required", True)),
        "origin_and_settlement_labels_required": bool(
            policy.get("origin_and_settlement_labels_required", True)
        ),
        "raw_full_source_text_disclosure_allowed": False,
    }


def _artifact_bindings(preview_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "source_origin_lineage": preview_input.get("source_origin_lineage"),
        "warranted_source_footer": preview_input.get("warranted_source_footer"),
        "grounded_source_footer": preview_input.get("grounded_source_footer"),
        "source_freshness_audit": preview_input.get("source_freshness_audit"),
        "deep_research_citation_audit": preview_input.get("deep_research_citation_audit"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("preview_version")
            or (artifact or {}).get("lineage_version")
            or (artifact or {}).get("footer_version")
            or (artifact or {}).get("audit_version")
            or (artifact or {}).get("report_version")
            or (artifact or {}).get("version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _warrant_rows_by_key(report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("claim_warrant_rows", []):
        key = (
            str(row.get("source_label", "")),
            str(row.get("claim_hash", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        if all(key):
            rows[key] = row
    return rows


def _origin_rows_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("label", "")): row
        for row in report.get("source_origin_rows", [])
        if row.get("label")
    }


def _grounded_source_rows_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("label", "")): row
        for row in report.get("footer_rows", [])
        if row.get("label")
    }


def _claim_regions_by_key(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("source_label", "")), str(row.get("evidence_span_prefix", ""))): row
        for row in report.get("claim_rows", [])
        if row.get("source_label") and row.get("evidence_span_prefix")
    }


def _preview_inputs_by_key(preview_input: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in preview_input.get("evidence_previews", []):
        key = (
            str(row.get("source_label", row.get("label", ""))),
            str(row.get("claim_hash", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        if all(key):
            rows[key] = row
    return rows


def _source_preview_rows(
    *,
    source_origin_lineage: dict[str, Any],
    grounded_source_footer: dict[str, Any],
) -> list[dict[str, Any]]:
    origin_by_label = _origin_rows_by_label(source_origin_lineage)
    grounded_by_label = _grounded_source_rows_by_label(grounded_source_footer)
    labels = sorted(
        origin_by_label,
        key=lambda label: int(origin_by_label[label].get("display_order", 0) or 0),
    )
    rows: list[dict[str, Any]] = []
    for label in labels:
        origin = origin_by_label[label]
        grounded = grounded_by_label.get(label, {})
        public = {
            "display_order": int(origin.get("display_order", 0) or 0),
            "label": label,
            "display_label": str(origin.get("display_label") or grounded.get("display_label") or f"[{label}]"),
            "title": str(origin.get("title") or grounded.get("title", "")),
            "creator_id": str(origin.get("creator_id") or grounded.get("creator_id", "")),
            "work_id": str(origin.get("work_id") or grounded.get("work_id", "")),
            "chunk_id": str(origin.get("chunk_id") or grounded.get("chunk_id", "")),
            "source_uri": str(origin.get("source_uri") or grounded.get("source_uri", "")),
            "content_hash_prefix": str(
                origin.get("content_hash_prefix") or grounded.get("content_hash_prefix", "")
            ),
            "origin_class": str(origin.get("origin_class", "")),
            "lineage_status": str(origin.get("lineage_status", "")),
            "settlement_action": str(origin.get("settlement_action", "")),
            "source_origin_row_hash": str(origin.get("source_origin_row_hash", "")),
            "warranted_source_row_hash": str(origin.get("warranted_source_row_hash", "")),
            "source_creator_direct_payout_allowed": bool(
                origin.get("source_creator_direct_payout_allowed", False)
            ),
            "lineage_settlement_allowed": bool(origin.get("lineage_settlement_allowed", False)),
            "origin_review_escrow_share": float(origin.get("origin_review_escrow_share", 0.0) or 0.0),
        }
        public["display_line"] = (
            f"{public['display_label']} {public['title']} "
            f"origin={public['origin_class']}; warrant=calibrated; "
            f"settlement={public['settlement_action']}; source={public['source_uri']}"
        )
        public["source_preview_row_hash"] = hash_payload(
            {key: value for key, value in public.items() if key != "source_preview_row_hash"}
        )
        rows.append(public)
    return rows


def _claim_preview_rows(
    *,
    preview_input: dict[str, Any],
    policy: dict[str, Any],
    warranted_source_footer: dict[str, Any],
    grounded_source_footer: dict[str, Any],
) -> list[dict[str, Any]]:
    warrant_by_key = _warrant_rows_by_key(warranted_source_footer)
    preview_by_key = _preview_inputs_by_key(preview_input)
    region_by_key = _claim_regions_by_key(grounded_source_footer)
    rows: list[dict[str, Any]] = []
    for index, key in enumerate(sorted(warrant_by_key), start=1):
        source_label, claim_hash, span_prefix = key
        warrant = warrant_by_key[key]
        preview = preview_by_key.get(key, {})
        region = region_by_key.get((source_label, span_prefix), {})
        excerpt_text = str(preview.get("excerpt_text", ""))
        excerpt_hash = stable_hash(excerpt_text) if excerpt_text else ""
        license_status = str(preview.get("excerpt_license_status", "")).strip()
        location = {
            "page": int(preview.get("page", region.get("page", 0)) or 0),
            "line_start": int(preview.get("line_start", region.get("line_start", 0)) or 0),
            "line_end": int(preview.get("line_end", region.get("line_end", 0)) or 0),
            "start_char": int(preview.get("start_char", region.get("start_char", 0)) or 0),
            "end_char": int(preview.get("end_char", region.get("end_char", 0)) or 0),
            "location_hash": str(preview.get("location_hash", region.get("location_hash", ""))),
        }
        axis_labels = [
            f"{axis.get('axis')}={axis.get('evidence_force')}"
            for axis in warrant.get("axis_rows", [])
            if axis.get("axis") and axis.get("evidence_force")
        ]
        public = {
            "display_order": index,
            "source_label": source_label,
            "display_anchor": str(warrant.get("display_anchor", "")),
            "claim_hash": claim_hash,
            "evidence_span_prefix": span_prefix,
            "excerpt_text": excerpt_text,
            "excerpt_hash": excerpt_hash,
            "declared_excerpt_hash": str(preview.get("excerpt_hash") or excerpt_hash),
            "excerpt_word_count": _word_count(excerpt_text),
            "excerpt_char_count": len(excerpt_text),
            "excerpt_permission": preview.get("excerpt_permission") is True,
            "excerpt_license_status": license_status,
            "source_uri": str(preview.get("source_uri", "")),
            "title": str(preview.get("title", "")),
            "retrieved_at": str(preview.get("retrieved_at", "")),
            "location": location,
            "warrant_status": str(warrant.get("warrant_status", "")),
            "support_score": float(warrant.get("support_score", 0.0) or 0.0),
            "confidence": float(warrant.get("confidence", 0.0) or 0.0),
            "axis_summary": axis_labels,
            "claim_warrant_row_hash": str(warrant.get("claim_warrant_row_hash", "")),
            "source_row_hash": str(preview.get("source_row_hash", "")),
            "snippet_within_word_limit": _word_count(excerpt_text)
            <= int(policy["max_excerpt_words"]),
            "snippet_within_char_limit": len(excerpt_text)
            <= int(policy["max_excerpt_chars"]),
            "excerpt_hash_reproducible": (
                not preview.get("excerpt_hash") or str(preview.get("excerpt_hash")) == excerpt_hash
            ),
            "excerpt_license_allowed": license_status
            in set(policy["allowed_excerpt_license_statuses"]),
        }
        public["display_line"] = (
            f"[{source_label}:span={span_prefix}] Evidence: \"{excerpt_text}\" "
            f"warrant={public['warrant_status']}; "
            f"support={public['support_score']:.2f}; claim_hash={claim_hash[:12]}"
        )
        public["claim_preview_row_hash"] = hash_payload(
            {key: value for key, value in public.items() if key != "claim_preview_row_hash"}
        )
        rows.append(public)
    return rows


def _checks(
    *,
    preview_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    source_origin_lineage: dict[str, Any],
    warranted_source_footer: dict[str, Any],
    grounded_source_footer: dict[str, Any],
) -> dict[str, bool]:
    source_labels = {row["label"] for row in source_rows}
    claim_labels = {row["source_label"] for row in claim_rows}
    preview_by_key = _preview_inputs_by_key(preview_input)
    warrant_by_key = _warrant_rows_by_key(warranted_source_footer)
    public_report = {"source_preview_rows": source_rows, "claim_preview_rows": claim_rows}
    return {
        "artifact_hashes_reproducible": all(
            row["present"] and row["hash_reproducible"]
            for key, row in artifact_bindings.items()
            if key
            in {
                "source_origin_lineage",
                "warranted_source_footer",
                "grounded_source_footer",
            }
        ),
        "source_origin_lineage_ready_l121": (
            source_origin_lineage.get("summary", {}).get("status") == "ready"
            and source_origin_lineage.get("summary", {}).get("target_certification_level")
            == "RDLLM-L121"
        ),
        "warranted_source_footer_ready_l120": (
            warranted_source_footer.get("summary", {}).get("status") == "ready"
            and warranted_source_footer.get("summary", {}).get("target_certification_level")
            == "RDLLM-L120"
        ),
        "grounded_source_footer_ready": (
            grounded_source_footer.get("summary", {}).get("status") == "ready"
        ),
        "preview_rows_cover_visible_warranted_claims": (
            not policy["verified_claims_require_preview"]
            or set(warrant_by_key).issubset(set(preview_by_key))
        ),
        "preview_rows_reference_visible_sources": claim_labels.issubset(source_labels),
        "snippets_present_for_verified_claims": all(
            bool(row["excerpt_text"]) for row in claim_rows if row["warrant_status"] == "calibrated"
        ),
        "snippets_within_policy_limit": all(
            row["snippet_within_word_limit"] and row["snippet_within_char_limit"]
            for row in claim_rows
        ),
        "snippet_hashes_reproducible": all(
            row["excerpt_hash_reproducible"] and row["excerpt_hash"] == row["declared_excerpt_hash"]
            for row in claim_rows
        ),
        "snippets_have_public_excerpt_permission": all(
            row["excerpt_permission"] and row["excerpt_license_allowed"] for row in claim_rows
        ),
        "public_source_uris_present": (
            not policy["public_source_uri_required"]
            or all(row["source_uri"] for row in source_rows)
        )
        and all(row["source_uri"] for row in claim_rows),
        "origin_and_settlement_labels_present": (
            not policy["origin_and_settlement_labels_required"]
            or all(row["origin_class"] and row["settlement_action"] for row in source_rows)
        ),
        "non_direct_sources_are_labeled": all(
            row["settlement_action"] == "direct_source_creator_payout"
            or "settlement=" in row["display_line"]
            for row in source_rows
        ),
        "proof_handles_present": all(
            row["claim_warrant_row_hash"] and row["excerpt_hash"] for row in claim_rows
        )
        and all(row["source_origin_row_hash"] for row in source_rows),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, preview_input)
        ),
    }


def make_evidence_preview_footer(
    preview_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a user-visible evidence-preview footer with short source snippets."""

    policy = _policy(preview_input)
    artifact_bindings = _artifact_bindings(preview_input)
    source_origin_lineage = preview_input.get("source_origin_lineage", {})
    warranted_source_footer = preview_input.get("warranted_source_footer", {})
    grounded_source_footer = preview_input.get("grounded_source_footer", {})
    source_rows = _source_preview_rows(
        source_origin_lineage=source_origin_lineage,
        grounded_source_footer=grounded_source_footer,
    )
    claim_rows = _claim_preview_rows(
        preview_input=preview_input,
        policy=policy,
        warranted_source_footer=warranted_source_footer,
        grounded_source_footer=grounded_source_footer,
    )
    checks = _checks(
        preview_input=preview_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        source_rows=source_rows,
        claim_rows=claim_rows,
        source_origin_lineage=source_origin_lineage,
        warranted_source_footer=warranted_source_footer,
        grounded_source_footer=grounded_source_footer,
    )
    failed = [key for key, value in checks.items() if value is not True]
    source_display_lines = [row["display_line"] for row in source_rows]
    claim_display_lines = [row["display_line"] for row in claim_rows]
    report: dict[str, Any] = {
        "preview_version": EVIDENCE_PREVIEW_FOOTER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "footer_display": {
            "profile": "rdllm-human-inspectable-evidence-footer/v1",
            "source_line_count": len(source_display_lines),
            "claim_line_count": len(claim_display_lines),
            "source_lines": source_display_lines,
            "claim_lines": claim_display_lines,
            "source_preview_root": merkle_root(
                [row["source_preview_row_hash"] for row in source_rows]
            ),
            "claim_preview_root": merkle_root(
                [row["claim_preview_row_hash"] for row in claim_rows]
            ),
        },
        "source_preview_rows": source_rows,
        "claim_preview_rows": claim_rows,
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "missing_preview_claim_keys": [
                "|".join(key)
                for key in sorted(
                    set(_warrant_rows_by_key(warranted_source_footer))
                    - set(_preview_inputs_by_key(preview_input))
                )
            ],
            "overlong_excerpt_claim_hashes": [
                row["claim_hash"]
                for row in claim_rows
                if not row["snippet_within_word_limit"] or not row["snippet_within_char_limit"]
            ],
            "unlicensed_excerpt_claim_hashes": [
                row["claim_hash"]
                for row in claim_rows
                if not row["excerpt_permission"] or not row["excerpt_license_allowed"]
            ],
        },
        "commitments": {
            "artifact_binding_root": merkle_root(
                [row["declared_hash"] for row in artifact_bindings.values() if row["declared_hash"]]
            ),
            "source_preview_root": merkle_root(
                [row["source_preview_row_hash"] for row in source_rows]
            ),
            "claim_preview_root": merkle_root(
                [row["claim_preview_row_hash"] for row in claim_rows]
            ),
            "footer_display_hash": hash_payload(
                {"source_lines": source_display_lines, "claim_lines": claim_display_lines}
            ),
            "schema": EVIDENCE_PREVIEW_FOOTER_SCHEMA,
        },
        "schemas": {
            "evidence_preview_footer": EVIDENCE_PREVIEW_FOOTER_SCHEMA,
            "source_origin_lineage": "docs/schemas/source_origin_lineage.schema.json",
            "warranted_source_footer": "docs/schemas/warranted_source_footer.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "deep_research_citation_audit": "docs/schemas/deep_research_citation_audit.schema.json",
        },
        "privacy": {
            "short_evidence_excerpt_text_disclosed": True,
            "raw_full_source_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "payment_account_disclosed": False,
            "excerpt_word_limit": policy["max_excerpt_words"],
            "excerpt_char_limit": policy["max_excerpt_chars"],
        },
        "summary": {
            "status": "ready" if not failed else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "visible_source_count": len(source_rows),
            "claim_preview_count": len(claim_rows),
            "excerpt_word_limit": policy["max_excerpt_words"],
            "excerpt_char_limit": policy["max_excerpt_chars"],
            "permissioned_excerpt_count": sum(
                1
                for row in claim_rows
                if row["excerpt_permission"] and row["excerpt_license_allowed"]
            ),
            "failed_check_count": len(failed),
            "human_inspectable_footer_supported": True,
            "source_preview_text_supported": checks["snippets_present_for_verified_claims"],
            "footer_grounding_confidence_supported": checks["proof_handles_present"],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["evidence_preview_footer_hash"] = hash_payload(_hashable_report(report))
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


def validate_evidence_preview_footer_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "preview_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "footer_display",
        "source_preview_rows",
        "claim_preview_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "evidence_preview_footer_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence preview footer field: {key}")
    if errors:
        return errors
    if report.get("preview_version") != EVIDENCE_PREVIEW_FOOTER_VERSION:
        errors.append("evidence preview footer version is unsupported")
    if report.get("schemas", {}).get("evidence_preview_footer") != EVIDENCE_PREVIEW_FOOTER_SCHEMA:
        errors.append("evidence preview footer schema is not declared")
    for row in report.get("source_preview_rows", []):
        for key in (
            "label",
            "title",
            "source_uri",
            "origin_class",
            "settlement_action",
            "display_line",
            "source_preview_row_hash",
        ):
            if key not in row:
                errors.append(f"missing source preview row field: {key}")
    for row in report.get("claim_preview_rows", []):
        for key in (
            "source_label",
            "claim_hash",
            "evidence_span_prefix",
            "excerpt_text",
            "excerpt_hash",
            "excerpt_word_count",
            "excerpt_permission",
            "excerpt_license_status",
            "display_line",
            "claim_preview_row_hash",
        ):
            if key not in row:
                errors.append(f"missing claim preview row field: {key}")
    return errors


def verify_evidence_preview_footer(
    report: dict[str, Any],
    *,
    preview_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an evidence-preview footer against its private replay inputs."""

    errors = validate_evidence_preview_footer_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get("evidence_preview_footer_hash"):
        errors.append("evidence preview footer hash is not reproducible")

    expected = make_evidence_preview_footer(
        preview_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "footer_display",
        "source_preview_rows",
        "claim_preview_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence preview footer {key} does not match inputs")
    if expected.get("evidence_preview_footer_hash") != report.get("evidence_preview_footer_hash"):
        errors.append("evidence preview footer hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("evidence preview footer status is not ready")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence preview footer target level is not RDLLM-L122")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"evidence preview footer check failed: {check}")

    if _contains_private_fields(report):
        errors.append("evidence preview footer exposes private field names")
    if not _private_strings_absent(report, preview_input):
        errors.append("evidence preview footer exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence preview footer is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence preview footer signature is invalid")

    return errors
