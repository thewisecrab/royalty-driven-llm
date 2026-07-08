"""Exact evidence locators for human-inspectable source footers.

This layer sits after evidence-preview footers. L122 proves that a short,
permissioned snippet can be shown to the reader; L123 proves that the reader or
auditor can resolve that snippet to an exact source location or immutable
snapshot without exposing full source text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

EVIDENCE_LOCATOR_MANIFEST_VERSION = "rdllm-evidence-locator-manifest/v1"
EVIDENCE_LOCATOR_MANIFEST_SCHEMA = "docs/schemas/evidence_locator_manifest.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L123"
MINIMUM_INPUT_LEVEL = "RDLLM-L122"

ALLOWED_LOCATOR_TYPES = {
    "text_fragment",
    "canonical_url",
    "page_line",
    "byte_range",
    "timecode",
    "bbox",
    "snapshot",
    "doi",
    "content_hash",
}

ALLOWED_RESOLVER_STATUSES = {
    "resolved",
    "resolver_verified",
    "snapshot_verified",
    "offline_snapshot_verified",
}

DECLARED_HASH_FIELDS = (
    "evidence_locator_manifest_hash",
    "evidence_preview_footer_hash",
    "evidence_region_binding_hash",
    "source_availability_report_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "report_hash",
    "audit_hash",
    "manifest_hash",
    "footer_hash",
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


def load_evidence_locator_manifest_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L123 evidence-locator manifest."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"evidence_locator_manifest_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], locator_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in locator_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(locator_input: dict[str, Any]) -> dict[str, Any]:
    policy = locator_input.get("policy", {})
    return {
        "profile": "rdllm-evidence-locator-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "every_preview_claim_requires_locator": bool(
            policy.get("every_preview_claim_requires_locator", True)
        ),
        "exact_passage_locator_required": bool(
            policy.get("exact_passage_locator_required", True)
        ),
        "public_locator_url_required": bool(policy.get("public_locator_url_required", True)),
        "snapshot_or_text_fragment_required": bool(
            policy.get("snapshot_or_text_fragment_required", True)
        ),
        "allowed_locator_types": sorted(
            str(item) for item in policy.get("allowed_locator_types", ALLOWED_LOCATOR_TYPES)
        ),
        "allowed_resolver_statuses": sorted(
            str(item)
            for item in policy.get(
                "allowed_resolver_statuses", ALLOWED_RESOLVER_STATUSES
            )
        ),
        "raw_full_source_text_disclosure_allowed": False,
        "raw_excerpt_text_redisclosure_allowed": False,
    }


def _artifact_bindings(locator_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "evidence_preview_footer": locator_input.get("evidence_preview_footer"),
        "evidence_region_binding": locator_input.get("evidence_region_binding"),
        "source_availability_report": locator_input.get("source_availability_report"),
        "source_freshness_audit": locator_input.get("source_freshness_audit"),
        "deep_research_citation_audit": locator_input.get(
            "deep_research_citation_audit"
        ),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("locator_version")
            or (artifact or {}).get("preview_version")
            or (artifact or {}).get("binding_version")
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


def _preview_rows_by_key(report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("claim_preview_rows", []):
        key = (
            str(row.get("source_label", "")),
            str(row.get("claim_hash", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        if all(key):
            rows[key] = row
    return rows


def _locator_inputs_by_key(locator_input: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in locator_input.get("source_locators", []):
        key = (
            str(row.get("source_label", row.get("label", ""))),
            str(row.get("claim_hash", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        if all(key):
            rows[key] = row
    return rows


def _public_url_valid(url: str, locator_type: str) -> bool:
    if locator_type == "doi":
        return url.startswith("doi:") or "doi.org/" in url
    if locator_type == "content_hash":
        return url.startswith(("urn:", "ipfs://", "ar://")) or len(url) >= 16
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https", "ipfs", "ar", "urn"}


def _has_text_fragment(locator_url: str, row: dict[str, Any]) -> bool:
    return "#:~:text=" in locator_url or bool(row.get("text_fragment_hash"))


def _locator_rows(
    *,
    locator_input: dict[str, Any],
    policy: dict[str, Any],
    evidence_preview_footer: dict[str, Any],
) -> list[dict[str, Any]]:
    preview_by_key = _preview_rows_by_key(evidence_preview_footer)
    locator_by_key = _locator_inputs_by_key(locator_input)
    rows: list[dict[str, Any]] = []
    allowed_types = set(policy["allowed_locator_types"])
    allowed_statuses = set(policy["allowed_resolver_statuses"])
    for index, key in enumerate(sorted(preview_by_key), start=1):
        source_label, claim_hash, span_prefix = key
        preview = preview_by_key[key]
        locator = locator_by_key.get(key, {})
        locator_type = str(locator.get("locator_type", "")).strip()
        locator_url = str(locator.get("locator_url", "")).strip()
        source_uri = str(locator.get("source_uri", preview.get("source_uri", ""))).strip()
        resolver_status = str(locator.get("resolver_status", "")).strip()
        snapshot_hash = str(locator.get("snapshot_hash", "")).strip()
        text_fragment_hash = str(locator.get("text_fragment_hash", "")).strip()
        preview_row_hash = str(preview.get("claim_preview_row_hash", ""))
        declared_preview_row_hash = str(locator.get("claim_preview_row_hash", preview_row_hash))
        declared_excerpt_hash = str(locator.get("excerpt_hash", preview.get("excerpt_hash", "")))
        public = {
            "display_order": index,
            "source_label": source_label,
            "claim_hash": claim_hash,
            "evidence_span_prefix": span_prefix,
            "display_anchor": str(preview.get("display_anchor", "")),
            "source_uri": source_uri,
            "preview_source_uri": str(preview.get("source_uri", "")),
            "locator_type": locator_type,
            "locator_url": locator_url,
            "resolver_status": resolver_status,
            "resolved_at": str(locator.get("resolved_at", "")),
            "snapshot_hash": snapshot_hash,
            "snapshot_uri": str(locator.get("snapshot_uri", "")),
            "content_hash_prefix": str(locator.get("content_hash_prefix", "")),
            "text_fragment_hash": text_fragment_hash,
            "region_hash": str(
                locator.get(
                    "region_hash",
                    (preview.get("location") or {}).get("location_hash", ""),
                )
            ),
            "claim_preview_row_hash": preview_row_hash,
            "declared_claim_preview_row_hash": declared_preview_row_hash,
            "excerpt_hash": str(preview.get("excerpt_hash", "")),
            "declared_excerpt_hash": declared_excerpt_hash,
            "exact_passage_locator": locator.get("exact_passage_locator") is True,
            "locator_type_supported": locator_type in allowed_types,
            "locator_url_public": bool(locator_url) and _public_url_valid(
                locator_url, locator_type
            ),
            "resolver_status_allowed": resolver_status in allowed_statuses,
            "source_uri_matches_preview": source_uri == str(preview.get("source_uri", "")),
            "preview_row_hash_bound": declared_preview_row_hash == preview_row_hash,
            "excerpt_hash_bound": declared_excerpt_hash == str(preview.get("excerpt_hash", "")),
        }
        public["snapshot_or_text_fragment_bound"] = bool(snapshot_hash) or _has_text_fragment(
            locator_url, public
        )
        public["display_line"] = (
            f"[{source_label}:span={span_prefix}] Locate evidence: {locator_url} "
            f"type={locator_type}; resolver={resolver_status}; "
            f"snapshot={snapshot_hash[:12]}; proof={preview_row_hash[:12]}"
        )
        public["evidence_locator_row_hash"] = hash_payload(
            {key: value for key, value in public.items() if key != "evidence_locator_row_hash"}
        )
        rows.append(public)
    return rows


def _checks(
    *,
    locator_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    evidence_preview_footer: dict[str, Any],
    locator_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    preview_keys = set(_preview_rows_by_key(evidence_preview_footer))
    locator_keys = set(_locator_inputs_by_key(locator_input))
    public_report = {"evidence_locator_rows": locator_rows}
    return {
        "artifact_hashes_reproducible": (
            artifact_bindings["evidence_preview_footer"]["present"]
            and artifact_bindings["evidence_preview_footer"]["hash_reproducible"]
            and all(
                row["hash_reproducible"]
                for name, row in artifact_bindings.items()
                if name != "evidence_preview_footer" and row["present"]
            )
        ),
        "evidence_preview_footer_ready_l122": (
            evidence_preview_footer.get("summary", {}).get("status") == "ready"
            and evidence_preview_footer.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L122"
        ),
        "locator_rows_cover_preview_claims": (
            not policy["every_preview_claim_requires_locator"]
            or preview_keys.issubset(locator_keys)
        ),
        "locator_rows_reference_preview_claims": all(
            (
                row["source_label"],
                row["claim_hash"],
                row["evidence_span_prefix"],
            )
            in preview_keys
            for row in locator_rows
        ),
        "exact_passage_locators_present": (
            not policy["exact_passage_locator_required"]
            or all(row["exact_passage_locator"] for row in locator_rows)
        ),
        "public_locator_urls_present": (
            not policy["public_locator_url_required"]
            or all(row["locator_url_public"] for row in locator_rows)
        ),
        "locator_types_supported": all(
            row["locator_type_supported"] for row in locator_rows
        ),
        "resolver_statuses_allowed": all(
            row["resolver_status_allowed"] for row in locator_rows
        ),
        "source_uris_match_preview": all(
            row["source_uri_matches_preview"] for row in locator_rows
        ),
        "preview_hashes_bound": all(
            row["preview_row_hash_bound"] and row["excerpt_hash_bound"]
            for row in locator_rows
        ),
        "snapshot_or_text_fragment_bound": (
            not policy["snapshot_or_text_fragment_required"]
            or all(row["snapshot_or_text_fragment_bound"] for row in locator_rows)
        ),
        "locator_hashes_present": all(
            row["evidence_locator_row_hash"] and row["claim_preview_row_hash"]
            for row in locator_rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, locator_input)
        ),
    }


def make_evidence_locator_manifest(
    locator_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L123 manifest that resolves each preview snippet to source evidence."""

    policy = _policy(locator_input)
    artifact_bindings = _artifact_bindings(locator_input)
    evidence_preview_footer = locator_input.get("evidence_preview_footer", {})
    locator_rows = _locator_rows(
        locator_input=locator_input,
        policy=policy,
        evidence_preview_footer=evidence_preview_footer,
    )
    checks = _checks(
        locator_input=locator_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        evidence_preview_footer=evidence_preview_footer,
        locator_rows=locator_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    locator_lines = [row["display_line"] for row in locator_rows]
    report: dict[str, Any] = {
        "locator_version": EVIDENCE_LOCATOR_MANIFEST_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "footer_locator_display": {
            "profile": "rdllm-exact-evidence-locator-footer/v1",
            "locator_line_count": len(locator_lines),
            "locator_lines": locator_lines,
            "locator_root": merkle_root(
                [row["evidence_locator_row_hash"] for row in locator_rows]
            ),
        },
        "evidence_locator_rows": locator_rows,
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "missing_locator_claim_keys": [
                "|".join(key)
                for key in sorted(
                    set(_preview_rows_by_key(evidence_preview_footer))
                    - set(_locator_inputs_by_key(locator_input))
                )
            ],
            "unsupported_locator_claim_hashes": [
                row["claim_hash"] for row in locator_rows if not row["locator_type_supported"]
            ],
            "unresolved_locator_claim_hashes": [
                row["claim_hash"] for row in locator_rows if not row["resolver_status_allowed"]
            ],
            "missing_exact_locator_claim_hashes": [
                row["claim_hash"] for row in locator_rows if not row["exact_passage_locator"]
            ],
            "unbound_snapshot_claim_hashes": [
                row["claim_hash"]
                for row in locator_rows
                if not row["snapshot_or_text_fragment_bound"]
            ],
            "source_uri_mismatch_claim_hashes": [
                row["claim_hash"] for row in locator_rows if not row["source_uri_matches_preview"]
            ],
        },
        "commitments": {
            "artifact_binding_root": merkle_root(
                [
                    row["declared_hash"]
                    for row in artifact_bindings.values()
                    if row["declared_hash"]
                ]
            ),
            "locator_root": merkle_root(
                [row["evidence_locator_row_hash"] for row in locator_rows]
            ),
            "footer_locator_display_hash": hash_payload(locator_lines),
            "schema": EVIDENCE_LOCATOR_MANIFEST_SCHEMA,
        },
        "schemas": {
            "evidence_locator_manifest": EVIDENCE_LOCATOR_MANIFEST_SCHEMA,
            "evidence_preview_footer": "docs/schemas/evidence_preview_footer.schema.json",
            "evidence_region_binding": "docs/schemas/evidence_region_binding_report.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "deep_research_citation_audit": "docs/schemas/deep_research_citation_audit.schema.json",
        },
        "privacy": {
            "raw_full_source_text_disclosed": False,
            "raw_excerpt_text_redisclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "payment_account_disclosed": False,
            "public_locator_urls_disclosed": True,
            "snapshot_hashes_disclosed": True,
        },
        "summary": {
            "status": "ready" if not failed else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "preview_claim_count": len(_preview_rows_by_key(evidence_preview_footer)),
            "locator_count": len(locator_rows),
            "exact_locator_count": sum(
                1 for row in locator_rows if row["exact_passage_locator"]
            ),
            "snapshot_or_text_fragment_count": sum(
                1 for row in locator_rows if row["snapshot_or_text_fragment_bound"]
            ),
            "failed_check_count": len(failed),
            "click_through_evidence_supported": checks["public_locator_urls_present"],
            "exact_passage_resolution_supported": checks[
                "exact_passage_locators_present"
            ],
            "snapshot_fallback_supported": any(
                bool(row["snapshot_hash"]) for row in locator_rows
            ),
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["evidence_locator_manifest_hash"] = hash_payload(_hashable_report(report))
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


def validate_evidence_locator_manifest_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "locator_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "footer_locator_display",
        "evidence_locator_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "evidence_locator_manifest_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence locator manifest field: {key}")
    if errors:
        return errors
    if report.get("locator_version") != EVIDENCE_LOCATOR_MANIFEST_VERSION:
        errors.append("evidence locator manifest version is unsupported")
    if (
        report.get("schemas", {}).get("evidence_locator_manifest")
        != EVIDENCE_LOCATOR_MANIFEST_SCHEMA
    ):
        errors.append("evidence locator manifest schema is not declared")
    for row in report.get("evidence_locator_rows", []):
        for key in (
            "source_label",
            "claim_hash",
            "evidence_span_prefix",
            "source_uri",
            "locator_type",
            "locator_url",
            "resolver_status",
            "claim_preview_row_hash",
            "display_line",
            "evidence_locator_row_hash",
        ):
            if key not in row:
                errors.append(f"missing evidence locator row field: {key}")
    return errors


def verify_evidence_locator_manifest(
    report: dict[str, Any],
    *,
    locator_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L123 evidence-locator manifest against private replay inputs."""

    errors = validate_evidence_locator_manifest_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "evidence_locator_manifest_hash"
    ):
        errors.append("evidence locator manifest hash is not reproducible")

    expected = make_evidence_locator_manifest(
        locator_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "footer_locator_display",
        "evidence_locator_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence locator manifest {key} does not match inputs")
    if expected.get("evidence_locator_manifest_hash") != report.get(
        "evidence_locator_manifest_hash"
    ):
        errors.append("evidence locator manifest hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("evidence locator manifest status is not ready")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence locator manifest target level is not RDLLM-L123")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"evidence locator manifest check failed: {check}")

    if _contains_private_fields(report):
        errors.append("evidence locator manifest exposes private field names")
    if not _private_strings_absent(report, locator_input):
        errors.append("evidence locator manifest exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence locator manifest is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence locator manifest signature is invalid")

    return errors
