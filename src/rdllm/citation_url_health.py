"""Citation URL health checks for exact evidence locators.

L123 proves that a footer preview resolves to an exact locator. L124 adds the
URL-health guard: each visible locator must be live, content-addressed, DOI
resolved, or backed by an archival snapshot, and fabricated or never-seen URLs
fail closed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

CITATION_URL_HEALTH_VERSION = "rdllm-citation-url-health/v1"
CITATION_URL_HEALTH_SCHEMA = "docs/schemas/citation_url_health.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L124"
MINIMUM_INPUT_LEVEL = "RDLLM-L123"

GOOD_HEALTH_STATUSES = {
    "live",
    "canonical_redirect",
    "archived_snapshot",
    "doi_resolved",
    "content_addressed",
}

BAD_HEALTH_STATUSES = {
    "fabricated",
    "never_seen",
    "not_found",
    "soft_404",
    "timeout",
    "unverified",
}

DECLARED_HASH_FIELDS = (
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "source_availability_report_hash",
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "report_hash",
    "audit_hash",
    "manifest_hash",
    "locator_hash",
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
    "resolver_body",
    "raw_http_body",
}


def load_citation_url_health_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L124 citation URL-health report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in report.items() if key not in {"citation_url_health_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], health_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in health_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(health_input: dict[str, Any]) -> dict[str, Any]:
    policy = health_input.get("policy", {})
    return {
        "profile": "rdllm-citation-url-health-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "every_locator_requires_url_health": bool(
            policy.get("every_locator_requires_url_health", True)
        ),
        "live_or_archived_required": bool(policy.get("live_or_archived_required", True)),
        "fabricated_url_blocked": bool(policy.get("fabricated_url_blocked", True)),
        "resolver_evidence_required": bool(
            policy.get("resolver_evidence_required", True)
        ),
        "canonical_redirect_allowed": bool(
            policy.get("canonical_redirect_allowed", True)
        ),
        "accepted_health_statuses": sorted(
            str(item) for item in policy.get("accepted_health_statuses", GOOD_HEALTH_STATUSES)
        ),
        "rejected_health_statuses": sorted(
            str(item) for item in policy.get("rejected_health_statuses", BAD_HEALTH_STATUSES)
        ),
        "raw_http_body_disclosure_allowed": False,
        "raw_source_text_disclosure_allowed": False,
    }


def _artifact_bindings(health_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "evidence_locator_manifest": health_input.get("evidence_locator_manifest"),
        "source_availability_report": health_input.get("source_availability_report"),
        "source_freshness_audit": health_input.get("source_freshness_audit"),
        "deep_research_citation_audit": health_input.get(
            "deep_research_citation_audit"
        ),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("url_health_version")
            or (artifact or {}).get("locator_version")
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


def _locator_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source_label", "")),
        str(row.get("claim_hash", "")),
        str(row.get("evidence_span_prefix", "")),
    )


def _locator_rows_by_key(manifest: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in manifest.get("evidence_locator_rows", []):
        key = _locator_key(row)
        if all(key):
            rows[key] = row
    return rows


def _health_inputs_by_key(health_input: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in health_input.get("url_health_checks", []):
        key = (
            str(row.get("source_label", row.get("label", ""))),
            str(row.get("claim_hash", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        if all(key):
            rows[key] = row
    return rows


def _url_scheme(locator_url: str) -> str:
    if locator_url.startswith("doi:") or "doi.org/" in locator_url:
        return "doi"
    return urlparse(locator_url).scheme


def _snapshot_hash(check: dict[str, Any], locator: dict[str, Any]) -> str:
    return str(
        check.get("archival_snapshot_hash")
        or check.get("archive_snapshot_hash")
        or check.get("snapshot_hash")
        or locator.get("snapshot_hash")
        or ""
    )


def _snapshot_uri(check: dict[str, Any], locator: dict[str, Any]) -> str:
    return str(
        check.get("archival_snapshot_uri")
        or check.get("archive_snapshot_uri")
        or check.get("snapshot_uri")
        or locator.get("snapshot_uri")
        or ""
    )


def _is_content_addressed(locator_url: str, locator: dict[str, Any], status: str) -> bool:
    return (
        status == "content_addressed"
        or str(locator.get("locator_type", "")) == "content_hash"
        or locator_url.startswith(("ipfs://", "ar://", "urn:"))
    )


def _classify_url(
    *,
    check: dict[str, Any],
    locator: dict[str, Any],
    health_status: str,
    locator_url: str,
    live_resolved: bool,
    archived: bool,
) -> str:
    never_seen = check.get("never_seen") is True or health_status in {
        "fabricated",
        "never_seen",
    }
    if never_seen:
        return "fabricated_or_never_seen"
    if live_resolved or health_status in {"live", "canonical_redirect", "doi_resolved"}:
        return "not_hallucinated"
    if _is_content_addressed(locator_url, locator, health_status):
        return "not_hallucinated"
    if archived or health_status == "archived_snapshot":
        return "stale_or_link_rot"
    return "unverified"


def _citation_url_health_rows(
    *,
    health_input: dict[str, Any],
    policy: dict[str, Any],
    evidence_locator_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    locator_by_key = _locator_rows_by_key(evidence_locator_manifest)
    health_by_key = _health_inputs_by_key(health_input)
    accepted = set(policy["accepted_health_statuses"])
    rejected = set(policy["rejected_health_statuses"])
    rows: list[dict[str, Any]] = []

    for index, key in enumerate(sorted(locator_by_key), start=1):
        source_label, claim_hash, span_prefix = key
        locator = locator_by_key[key]
        check = health_by_key.get(key, {})
        locator_url = str(locator.get("locator_url", "")).strip()
        declared_locator_url = str(check.get("locator_url", locator_url)).strip()
        health_status = str(check.get("health_status", "")).strip()
        live_resolved = bool(check.get("live_resolved")) or health_status in {
            "live",
            "canonical_redirect",
            "doi_resolved",
        }
        snapshot_hash = _snapshot_hash(check, locator)
        snapshot_uri = _snapshot_uri(check, locator)
        archived = bool(snapshot_hash and snapshot_uri)
        resolver_evidence_hash = str(
            check.get("resolver_evidence_hash")
            or check.get("resolver_trace_hash")
            or check.get("http_head_hash")
            or ""
        ).strip()
        classification = _classify_url(
            check=check,
            locator=locator,
            health_status=health_status,
            locator_url=locator_url,
            live_resolved=live_resolved,
            archived=archived,
        )
        content_addressed = _is_content_addressed(locator_url, locator, health_status)
        durable_evidence_bound = bool(
            resolver_evidence_hash
            or archived
            or content_addressed
            or health_status == "doi_resolved"
        )
        public = {
            "display_order": index,
            "source_label": source_label,
            "claim_hash": claim_hash,
            "evidence_span_prefix": span_prefix,
            "locator_url": locator_url,
            "declared_locator_url": declared_locator_url,
            "final_url": str(check.get("final_url", locator_url if live_resolved else "")),
            "canonical_url": str(check.get("canonical_url", "")),
            "health_status": health_status,
            "http_status": int(check.get("http_status", 0) or 0),
            "content_type": str(check.get("content_type", "")),
            "checked_at": str(check.get("checked_at", "")),
            "first_seen_at": str(check.get("first_seen_at", "")),
            "last_seen_at": str(check.get("last_seen_at", "")),
            "archive_seen_at": str(check.get("archive_seen_at", "")),
            "archival_snapshot_uri": snapshot_uri,
            "archival_snapshot_hash": snapshot_hash,
            "resolver_evidence_hash": resolver_evidence_hash,
            "url_scheme": _url_scheme(locator_url),
            "live_resolved": live_resolved,
            "content_addressed": content_addressed,
            "archived_snapshot_available": archived,
            "accepted_health_status": health_status in accepted,
            "rejected_health_status": health_status in rejected,
            "locator_url_matches": declared_locator_url == locator_url,
            "locator_row_hash": str(locator.get("evidence_locator_row_hash", "")),
            "declared_locator_row_hash": str(
                check.get(
                    "evidence_locator_row_hash",
                    locator.get("evidence_locator_row_hash", ""),
                )
            ),
            "locator_hash_bound": str(
                check.get(
                    "evidence_locator_row_hash",
                    locator.get("evidence_locator_row_hash", ""),
                )
            )
            == str(locator.get("evidence_locator_row_hash", "")),
            "durable_resolver_evidence_bound": durable_evidence_bound,
            "live_or_archived_or_content_addressed": (
                live_resolved
                or archived
                or content_addressed
                or health_status == "doi_resolved"
            ),
            "hallucination_classification": classification,
            "direct_publication_allowed": classification
            in {"not_hallucinated", "stale_or_link_rot"},
        }
        public["display_line"] = (
            f"[{source_label}:span={span_prefix}] URL health: "
            f"{public['hallucination_classification']} status={health_status}; "
            f"live={str(live_resolved).lower()}; "
            f"archive={snapshot_hash[:12]}; proof={public['locator_row_hash'][:12]}"
        )
        public["citation_url_health_row_hash"] = hash_payload(
            {key: value for key, value in public.items() if key != "citation_url_health_row_hash"}
        )
        rows.append(public)
    return rows


def _checks(
    *,
    health_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    evidence_locator_manifest: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, bool]:
    locator_keys = set(_locator_rows_by_key(evidence_locator_manifest))
    health_keys = set(_health_inputs_by_key(health_input))
    public_report = {"citation_url_health_rows": rows}
    return {
        "artifact_hashes_reproducible": (
            artifact_bindings["evidence_locator_manifest"]["present"]
            and artifact_bindings["evidence_locator_manifest"]["hash_reproducible"]
            and all(
                row["hash_reproducible"]
                for name, row in artifact_bindings.items()
                if name != "evidence_locator_manifest" and row["present"]
            )
        ),
        "evidence_locator_manifest_ready_l123": (
            evidence_locator_manifest.get("summary", {}).get("status") == "ready"
            and evidence_locator_manifest.get("summary", {}).get(
                "target_certification_level"
            )
            == "RDLLM-L123"
        ),
        "health_rows_cover_locator_rows": (
            not policy["every_locator_requires_url_health"]
            or locator_keys.issubset(health_keys)
        ),
        "health_rows_reference_locator_urls": all(
            row["locator_url_matches"] for row in rows
        ),
        "locator_hashes_bound": all(row["locator_hash_bound"] for row in rows),
        "durable_resolver_evidence_bound": (
            not policy["resolver_evidence_required"]
            or all(row["durable_resolver_evidence_bound"] for row in rows)
        ),
        "every_url_live_archived_or_content_addressed": (
            not policy["live_or_archived_required"]
            or all(row["live_or_archived_or_content_addressed"] for row in rows)
        ),
        "fabricated_or_never_seen_urls_blocked": (
            not policy["fabricated_url_blocked"]
            or all(
                row["hallucination_classification"] != "fabricated_or_never_seen"
                for row in rows
            )
        ),
        "unverified_urls_blocked": all(
            row["hallucination_classification"] != "unverified" for row in rows
        ),
        "rejected_health_statuses_absent": all(
            not row["rejected_health_status"] for row in rows
        ),
        "health_row_hashes_present": all(
            row["citation_url_health_row_hash"] and row["locator_row_hash"]
            for row in rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, health_input)
        ),
    }


def make_citation_url_health_report(
    health_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L124 report that classifies every visible locator URL."""

    policy = _policy(health_input)
    artifact_bindings = _artifact_bindings(health_input)
    evidence_locator_manifest = health_input.get("evidence_locator_manifest", {})
    rows = _citation_url_health_rows(
        health_input=health_input,
        policy=policy,
        evidence_locator_manifest=evidence_locator_manifest,
    )
    checks = _checks(
        health_input=health_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        evidence_locator_manifest=evidence_locator_manifest,
        rows=rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    display_lines = [row["display_line"] for row in rows]
    fabricated = [
        row
        for row in rows
        if row["hallucination_classification"] == "fabricated_or_never_seen"
    ]
    unverified = [
        row for row in rows if row["hallucination_classification"] == "unverified"
    ]
    report: dict[str, Any] = {
        "url_health_version": CITATION_URL_HEALTH_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "footer_url_health_display": {
            "profile": "rdllm-citation-url-health-footer/v1",
            "health_line_count": len(display_lines),
            "health_lines": display_lines,
            "health_root": merkle_root(
                [row["citation_url_health_row_hash"] for row in rows]
            ),
        },
        "citation_url_health_rows": rows,
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "missing_health_claim_keys": [
                "|".join(key) for key in sorted(set(_locator_rows_by_key(evidence_locator_manifest)) - set(_health_inputs_by_key(health_input)))
            ],
            "fabricated_or_never_seen_claim_hashes": [
                row["claim_hash"] for row in fabricated
            ],
            "unverified_claim_hashes": [row["claim_hash"] for row in unverified],
            "unarchived_unresolved_claim_hashes": [
                row["claim_hash"]
                for row in rows
                if not row["live_or_archived_or_content_addressed"]
            ],
            "locator_url_mismatch_claim_hashes": [
                row["claim_hash"] for row in rows if not row["locator_url_matches"]
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
            "url_health_root": merkle_root(
                [row["citation_url_health_row_hash"] for row in rows]
            ),
            "footer_url_health_display_hash": hash_payload(display_lines),
            "schema": CITATION_URL_HEALTH_SCHEMA,
        },
        "schemas": {
            "citation_url_health": CITATION_URL_HEALTH_SCHEMA,
            "evidence_locator_manifest": "docs/schemas/evidence_locator_manifest.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "deep_research_citation_audit": "docs/schemas/deep_research_citation_audit.schema.json",
        },
        "privacy": {
            "raw_http_body_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "public_locator_urls_disclosed": True,
            "resolver_evidence_hashes_disclosed": True,
            "archival_snapshot_hashes_disclosed": True,
        },
        "summary": {
            "status": "ready" if not failed else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "locator_count": len(_locator_rows_by_key(evidence_locator_manifest)),
            "health_row_count": len(rows),
            "live_url_count": sum(1 for row in rows if row["live_resolved"]),
            "archived_only_url_count": sum(
                1
                for row in rows
                if row["hallucination_classification"] == "stale_or_link_rot"
            ),
            "content_addressed_url_count": sum(
                1 for row in rows if row["content_addressed"]
            ),
            "fabricated_or_never_seen_url_count": len(fabricated),
            "unverified_url_count": len(unverified),
            "failed_check_count": len(failed),
            "url_hallucination_guard_supported": checks[
                "fabricated_or_never_seen_urls_blocked"
            ],
            "link_rot_snapshot_fallback_supported": any(
                row["archived_snapshot_available"] for row in rows
            ),
            "resolver_evidence_supported": checks["durable_resolver_evidence_bound"],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["citation_url_health_hash"] = hash_payload(_hashable_report(report))
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


def validate_citation_url_health_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "url_health_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "footer_url_health_display",
        "citation_url_health_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "citation_url_health_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing citation url health field: {key}")
    if errors:
        return errors
    if report.get("url_health_version") != CITATION_URL_HEALTH_VERSION:
        errors.append("citation url health version is unsupported")
    if report.get("schemas", {}).get("citation_url_health") != CITATION_URL_HEALTH_SCHEMA:
        errors.append("citation url health schema is not declared")
    for row in report.get("citation_url_health_rows", []):
        for key in (
            "source_label",
            "claim_hash",
            "evidence_span_prefix",
            "locator_url",
            "health_status",
            "hallucination_classification",
            "locator_row_hash",
            "citation_url_health_row_hash",
        ):
            if key not in row:
                errors.append(f"missing citation url health row field: {key}")
    return errors


def verify_citation_url_health_report(
    report: dict[str, Any],
    *,
    health_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L124 citation URL-health report against replay inputs."""

    errors = validate_citation_url_health_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get("citation_url_health_hash"):
        errors.append("citation url health hash is not reproducible")

    expected = make_citation_url_health_report(
        health_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "footer_url_health_display",
        "citation_url_health_rows",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"citation url health {key} does not match inputs")
    if expected.get("citation_url_health_hash") != report.get("citation_url_health_hash"):
        errors.append("citation url health hash does not match inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("citation url health status is not ready")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("citation url health target level is not RDLLM-L124")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"citation url health check failed: {check}")

    if _contains_private_fields(report):
        errors.append("citation url health exposes private field names")
    if not _private_strings_absent(report, health_input):
        errors.append("citation url health exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("citation url health is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("citation url health signature is invalid")

    return errors
