"""Faithful citation reliance receipts for grounded LLM responses.

This layer closes the post-hoc bibliography gap: a response can show correct
sources while the model actually relied on different context, prior memory, or
unsupported generation.  The receipt binds user-visible footer rows to
pre-generation evidence locks, claim-source replay, causal utility trials,
source-access leases, and external content-protocol ingestion before direct
settlement is trusted.
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

CITATION_RELIANCE_RECEIPT_VERSION = "rdllm-citation-reliance-receipt/v1"
CITATION_RELIANCE_RECEIPT_SCHEMA = (
    "docs/schemas/citation_reliance_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L100"

DECLARED_HASH_FIELDS = (
    "citation_reliance_receipt_hash",
    "protocol_ingestion_report_hash",
    "lease_report_hash",
    "binding_report_hash",
    "report_hash",
    "contract_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
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
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "raw_notice_text",
    "raw_protocol_payload",
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

DIRECT_STATUSES = {"direct", "accepted", "payable", "paid", "settled"}
ESCROW_STATUSES = {
    "escrow",
    "held",
    "rights_conflict_escrow",
    "source_access_lease_escrow",
    "content_protocol_escrow",
    "license_escrow",
}


def load_citation_reliance_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a citation reliance receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"citation_reliance_receipt_hash", "signature"}
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
        return True
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(report: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _policy(receipt_input: dict[str, Any]) -> dict[str, bool]:
    configured = dict(receipt_input.get("policy", {}))
    return {
        "require_rendered_footer_rows": bool(
            configured.get("require_rendered_footer_rows", True)
        ),
        "require_pre_generation_evidence_locks": bool(
            configured.get("require_pre_generation_evidence_locks", True)
        ),
        "require_claim_source_replay": bool(
            configured.get("require_claim_source_replay", True)
        ),
        "require_causal_utility": bool(configured.get("require_causal_utility", True)),
        "require_current_turn_trace": bool(
            configured.get("require_current_turn_trace", True)
        ),
        "require_access_lease_and_protocol_for_direct_sources": bool(
            configured.get("require_access_lease_and_protocol_for_direct_sources", True)
        ),
        "require_no_paid_hidden_sources": bool(
            configured.get("require_no_paid_hidden_sources", True)
        ),
    }


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "row_hash",
            "source_reliance_row_hash",
            "claim_reliance_row_hash",
        }
    }


def _source_id(row: dict[str, Any]) -> str:
    return str(row.get("source_id") or row.get("chunk_id") or "")


def _label_from_claim_id(claim_id: str, claim_index: Any) -> str:
    if str(claim_index).isdigit():
        return str(claim_index)
    suffix = str(claim_id).rsplit("_", 1)[-1]
    return suffix if suffix.isdigit() else ""


def _visible_footer_rows(rendered_audit: dict[str, Any], claim_source_report: dict[str, Any]) -> list[dict[str, Any]]:
    parsed_rows = (
        rendered_audit.get("parsed_markdown", {}).get("source_footer_rows", [])
        if rendered_audit
        else []
    )
    claim_rows = claim_source_report.get("footer", {}).get("source_rows", [])
    by_label = {str(row.get("label", "")): row for row in claim_rows if row.get("label")}
    rows = []
    raw_rows = parsed_rows or claim_rows
    for index, row in enumerate(raw_rows, start=1):
        label = str(row.get("label", f"S{index}"))
        enriched = by_label.get(label, {})
        source_id = str(
            row.get("source_id")
            or row.get("chunk_id")
            or enriched.get("source_id")
            or enriched.get("chunk_id")
            or ""
        )
        content_hash = str(enriched.get("content_hash", ""))
        if not content_hash and row.get("content_hash"):
            content_hash = str(row.get("content_hash"))
        if not content_hash and row.get("content_hash_prefix"):
            content_hash = str(row.get("content_hash_prefix"))
        public = {
            "source_label": label,
            "source_id": source_id,
            "work_id": str(row.get("work_id") or enriched.get("work_id") or ""),
            "chunk_id": str(row.get("chunk_id") or enriched.get("chunk_id") or source_id),
            "source_uri": str(row.get("source_uri") or enriched.get("source_uri") or ""),
            "content_hash_prefix": str(
                row.get("content_hash_prefix")
                or content_hash[:16]
                or enriched.get("content_hash_prefix", "")
            ),
            "creator_id": str(enriched.get("creator_id", "")),
            "footer_row_hash": str(
                row.get("source_footer_row_hash") or row.get("footer_row_hash") or ""
            ),
        }
        public["source_reliance_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _marker_counts(rendered_audit: dict[str, Any]) -> dict[str, int]:
    rows = rendered_audit.get("parsed_markdown", {}).get("source_marker_rows", [])
    return {
        str(row.get("label", "")): int(row.get("body_occurrence_count", 0) or 0)
        for row in rows
    }


def _rendered_claim_rows(rendered_audit: dict[str, Any]) -> list[dict[str, Any]]:
    return rendered_audit.get("parsed_markdown", {}).get("claim_evidence_rows", [])


def _claim_source_rows(claim_source_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = claim_source_report.get("footer", {}).get("claim_rows", [])
    if rows:
        return rows
    return claim_source_report.get("claims", [])


def _utility_rows(evidence_utility_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = evidence_utility_report.get("utility_attribution", [])
    if isinstance(rows, list):
        return rows
    return []


def _trace_current_source_ids(evidence_utility_report: dict[str, Any]) -> set[str]:
    trace = evidence_utility_report.get("retrieval_trace", {})
    return {str(item) for item in trace.get("current_turn_source_ids", [])}


def _lock_rows(evidence_locked_report: dict[str, Any]) -> list[dict[str, Any]]:
    return evidence_locked_report.get("evidence_lock_rows", [])


def _source_access_coverage(source_access_lease_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_usage_id", "")): row
        for row in source_access_lease_report.get("coverage_rows", [])
        if row.get("source_usage_id")
    }


def _source_usage_rows(source_access_lease_report: dict[str, Any]) -> list[dict[str, Any]]:
    return source_access_lease_report.get("source_usage_rows", [])


def _protocol_coverage(content_protocol_ingestion_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_usage_id", "")): row
        for row in content_protocol_ingestion_report.get("coverage_rows", [])
        if row.get("source_usage_id")
    }


def _is_escrow(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    route = str(row.get("escrow_account", row.get("settlement_route", "")))
    return status in ESCROW_STATUSES or route.endswith("escrow") or "escrow" in route


def _is_direct(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    return bool(row.get("direct_settlement", False)) or (
        status in DIRECT_STATUSES and not _is_escrow(row)
    )


def _matching_usage_rows(source: dict[str, Any], usage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in usage_rows
        if (
            str(row.get("source_label", "")) == source["source_label"]
            or str(row.get("chunk_id", "")) == source["chunk_id"]
            or str(row.get("source_uri", "")) == source["source_uri"]
        )
    ]


def _source_reliance_rows(
    *,
    visible_sources: list[dict[str, Any]],
    evidence_locked_report: dict[str, Any],
    claim_source_report: dict[str, Any],
    evidence_utility_report: dict[str, Any],
    rendered_audit: dict[str, Any],
    source_access_lease_report: dict[str, Any],
    content_protocol_ingestion_report: dict[str, Any],
) -> list[dict[str, Any]]:
    markers = _marker_counts(rendered_audit)
    locks = _lock_rows(evidence_locked_report)
    utility_rows = _utility_rows(evidence_utility_report)
    claim_rows = _claim_source_rows(claim_source_report)
    current_sources = _trace_current_source_ids(evidence_utility_report)
    usage_rows = _source_usage_rows(source_access_lease_report)
    lease_coverage = _source_access_coverage(source_access_lease_report)
    protocol_coverage = _protocol_coverage(content_protocol_ingestion_report)
    rows = []
    for source in visible_sources:
        matching_locks = [
            row
            for row in locks
            if str(row.get("source_label", "")) == source["source_label"]
            or str(row.get("chunk_id", "")) == source["chunk_id"]
        ]
        source_claim_rows = [
            row
            for row in claim_rows
            if str(row.get("label", "")) == source["source_label"]
            or str(row.get("top_source_id", "")) == source["source_id"]
            or source["source_id"] in {str(item) for item in row.get("accepted_source_ids", [])}
        ]
        source_utility_rows = [
            row
            for row in utility_rows
            if str(row.get("source_id", "")) == source["source_id"]
            and bool(row.get("accepted", False))
        ]
        matching_usage = _matching_usage_rows(source, usage_rows)
        direct_usage = [row for row in matching_usage if _is_direct(row)]
        covered_usage = [
            row
            for row in matching_usage
            if lease_coverage.get(str(row.get("source_usage_id", "")), {}).get(
                "covered_for_direct_settlement", False
            )
            or (
                not _is_direct(row)
                and lease_coverage.get(str(row.get("source_usage_id", "")), {}).get(
                    "denied_or_unleased_escrowed", False
                )
            )
        ]
        protocol_rows = [
            protocol_coverage.get(str(row.get("source_usage_id", "")), {})
            for row in matching_usage
        ]
        protocol_covered = bool(
            protocol_rows
            and all(
                row.get("covered_for_protocol_ingestion", False)
                or row.get("missing_or_denied_protocol_escrowed", False)
                for row in protocol_rows
            )
        )
        public = {
            **source,
            "body_occurrence_count": markers.get(source["source_label"], 0),
            "evidence_lock_count": len(matching_locks),
            "satisfied_lock_count": sum(
                1 for row in matching_locks if row.get("lock_satisfied", False)
            ),
            "rendered_claim_count": len(source_claim_rows),
            "causal_utility_count": len(source_utility_rows),
            "current_turn_trace_present": (
                source["source_id"] in current_sources
                or source["chunk_id"] in current_sources
                or not current_sources
            ),
            "source_usage_count": len(matching_usage),
            "direct_settlement_count": len(direct_usage),
            "source_access_covered": bool(covered_usage),
            "content_protocol_covered": protocol_covered,
            "covered_for_faithful_reliance": bool(
                markers.get(source["source_label"], 0) > 0
                and any(row.get("lock_satisfied", False) for row in matching_locks)
                and source_claim_rows
                and source_utility_rows
                and (source["source_id"] in current_sources or source["chunk_id"] in current_sources or not current_sources)
                and (not direct_usage or (covered_usage and protocol_covered))
            ),
        }
        public["source_reliance_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _claim_reliance_rows(
    *,
    claim_source_report: dict[str, Any],
    evidence_locked_report: dict[str, Any],
    evidence_utility_report: dict[str, Any],
    rendered_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    claim_rows = _claim_source_rows(claim_source_report)
    locks = _lock_rows(evidence_locked_report)
    utility_rows = _utility_rows(evidence_utility_report)
    rendered_rows = _rendered_claim_rows(rendered_audit)
    rows = []
    for index, claim in enumerate(claim_rows, start=1):
        claim_id = str(claim.get("claim_id", f"claim_{index}"))
        claim_hash = str(claim.get("claim_hash", ""))
        source_label = str(claim.get("label", ""))
        source_id = str(
            claim.get("top_source_id")
            or next(iter(claim.get("accepted_source_ids", [])), "")
        )
        label_index = _label_from_claim_id(claim_id, index)
        matching_locks = [
            row
            for row in locks
            if (claim_hash and str(row.get("claim_hash", "")) == claim_hash)
            or (
                source_label
                and str(row.get("source_label", "")) == source_label
                and str(row.get("claim_index", "")) == label_index
            )
        ]
        matching_rendered = [
            row
            for row in rendered_rows
            if (
                source_label
                and str(row.get("source_label", "")) == source_label
                and (
                    str(row.get("evidence_span_prefix", ""))
                    == claim_hash[:12]
                    or str(row.get("claim_index", "")) == label_index
                )
            )
        ]
        matching_utility = [
            row
            for row in utility_rows
            if str(row.get("claim_id", "")) == claim_id
            and (
                str(row.get("source_id", "")) == source_id
                or not source_id
            )
            and bool(row.get("accepted", False))
        ]
        public = {
            "claim_id": claim_id,
            "claim_hash": claim_hash,
            "source_label": source_label,
            "source_id": source_id,
            "claim_source_decision": str(claim.get("decision", claim.get("status", ""))),
            "rendered_claim_evidence_present": bool(matching_rendered),
            "evidence_lock_count": len(matching_locks),
            "satisfied_lock_count": sum(
                1 for row in matching_locks if row.get("lock_satisfied", False)
            ),
            "causal_utility_count": len(matching_utility),
            "covered_for_faithful_reliance": bool(
                str(claim.get("decision", claim.get("status", "")))
                in {"grounded", "causally_grounded", "accepted"}
                and matching_rendered
                and any(row.get("lock_satisfied", False) for row in matching_locks)
                and matching_utility
            ),
        }
        public["claim_reliance_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "evidence_locked_generation_report": receipt_input.get(
            "evidence_locked_generation_report"
        ),
        "claim_source_attribution_report": receipt_input.get(
            "claim_source_attribution_report"
        ),
        "evidence_utility_attribution_report": receipt_input.get(
            "evidence_utility_attribution_report"
        ),
        "rendered_attribution_audit": receipt_input.get("rendered_attribution_audit"),
        "source_access_lease_report": receipt_input.get("source_access_lease_report"),
        "content_protocol_ingestion_report": receipt_input.get(
            "content_protocol_ingestion_report"
        ),
        "citation_footer_contract": receipt_input.get("citation_footer_contract"),
        "answer_claim_coverage_report": receipt_input.get(
            "answer_claim_coverage_report"
        ),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(
            artifact
        )
    return bindings


def _checks(
    *,
    receipt_input: dict[str, Any],
    policy: dict[str, bool],
    artifact_bindings: dict[str, Any],
    visible_sources: list[dict[str, Any]],
    source_reliance_rows: list[dict[str, Any]],
    claim_reliance_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    evidence_locked_report = receipt_input.get("evidence_locked_generation_report", {})
    rendered_audit = receipt_input.get("rendered_attribution_audit", {})
    claim_source_report = receipt_input.get("claim_source_attribution_report", {})
    evidence_utility_report = receipt_input.get("evidence_utility_attribution_report", {})
    source_access_lease_report = receipt_input.get("source_access_lease_report", {})
    content_protocol_ingestion_report = receipt_input.get(
        "content_protocol_ingestion_report", {}
    )
    direct_usage = [
        row
        for row in _source_usage_rows(source_access_lease_report)
        if _is_direct(row)
    ]
    visible_labels = {row["source_label"] for row in visible_sources}
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "rendered_footer_rows_present": (
            not policy["require_rendered_footer_rows"] or bool(visible_sources)
        ),
        "rendered_attribution_audit_ready": rendered_audit.get("summary", {}).get(
            "status"
        )
        in {"ready", "verified"}
        and rendered_audit.get("checks", {}).get(
            "rendered_markdown_attribution_verified", True
        )
        is True,
        "evidence_locks_precede_generation": (
            not policy["require_pre_generation_evidence_locks"]
            or (
                evidence_locked_report.get("checks", {}).get(
                    "lock_created_before_generation", True
                )
                is True
                and evidence_locked_report.get("checks", {}).get(
                    "every_footer_source_has_lock", True
                )
                is True
            )
        ),
        "every_visible_source_has_satisfied_lock": (
            not policy["require_pre_generation_evidence_locks"]
            or all(row["satisfied_lock_count"] > 0 for row in source_reliance_rows)
        ),
        "every_visible_source_has_claim_source_replay": (
            not policy["require_claim_source_replay"]
            or all(row["rendered_claim_count"] > 0 for row in source_reliance_rows)
        ),
        "every_visible_source_has_causal_utility": (
            not policy["require_causal_utility"]
            or all(row["causal_utility_count"] > 0 for row in source_reliance_rows)
        ),
        "every_grounded_claim_has_reliance_proof": (
            not policy["require_claim_source_replay"]
            or all(row["covered_for_faithful_reliance"] for row in claim_reliance_rows)
        ),
        "visible_sources_are_in_current_turn_trace": (
            not policy["require_current_turn_trace"]
            or all(row["current_turn_trace_present"] for row in source_reliance_rows)
        ),
        "source_access_and_protocol_cover_direct_sources": (
            not policy["require_access_lease_and_protocol_for_direct_sources"]
            or all(
                row["direct_settlement_count"] == 0
                or (row["source_access_covered"] and row["content_protocol_covered"])
                for row in source_reliance_rows
            )
        ),
        "no_paid_source_without_visible_footer": (
            not policy["require_no_paid_hidden_sources"]
            or all(str(row.get("source_label", "")) in visible_labels for row in direct_usage)
        ),
        "claim_source_report_ready": claim_source_report.get("summary", {}).get("status")
        in {"ready", "verified"},
        "evidence_utility_report_ready": evidence_utility_report.get("summary", {}).get(
            "status"
        )
        in {"ready", "verified"},
        "source_access_lease_ready": source_access_lease_report.get("summary", {}).get(
            "status"
        )
        in {"ready", "verified"},
        "content_protocol_ingestion_ready": content_protocol_ingestion_report.get(
            "summary", {}
        ).get("status")
        in {"ready", "verified"},
        "private_text_not_disclosed": (
            not _contains_private_fields(
                {
                    "visible_sources": visible_sources,
                    "source_reliance_rows": source_reliance_rows,
                    "claim_reliance_rows": claim_reliance_rows,
                }
            )
            and _private_strings_absent(
                {
                    "visible_sources": visible_sources,
                    "source_reliance_rows": source_reliance_rows,
                    "claim_reliance_rows": claim_reliance_rows,
                },
                receipt_input,
            )
        ),
        "direct_source_count_positive": bool(direct_usage),
    }


def make_citation_reliance_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable receipt proving footer sources were actually relied on."""

    policy = _policy(receipt_input)
    evidence_locked_report = receipt_input.get("evidence_locked_generation_report", {})
    claim_source_report = receipt_input.get("claim_source_attribution_report", {})
    evidence_utility_report = receipt_input.get("evidence_utility_attribution_report", {})
    rendered_audit = receipt_input.get("rendered_attribution_audit", {})
    source_access_lease_report = receipt_input.get("source_access_lease_report", {})
    content_protocol_ingestion_report = receipt_input.get(
        "content_protocol_ingestion_report", {}
    )
    visible_sources = _visible_footer_rows(rendered_audit, claim_source_report)
    source_reliance_rows = _source_reliance_rows(
        visible_sources=visible_sources,
        evidence_locked_report=evidence_locked_report,
        claim_source_report=claim_source_report,
        evidence_utility_report=evidence_utility_report,
        rendered_audit=rendered_audit,
        source_access_lease_report=source_access_lease_report,
        content_protocol_ingestion_report=content_protocol_ingestion_report,
    )
    claim_reliance_rows = _claim_reliance_rows(
        claim_source_report=claim_source_report,
        evidence_locked_report=evidence_locked_report,
        evidence_utility_report=evidence_utility_report,
        rendered_audit=rendered_audit,
    )
    artifact_bindings = _artifact_bindings(receipt_input)
    checks = _checks(
        receipt_input=receipt_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        visible_sources=visible_sources,
        source_reliance_rows=source_reliance_rows,
        claim_reliance_rows=claim_reliance_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    receipt = {
        "version": CITATION_RELIANCE_RECEIPT_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get("case_id", "case:citation-reliance-receipt")
            ),
            "status": status,
        },
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "visible_source_rows": visible_sources,
        "source_reliance_rows": source_reliance_rows,
        "claim_reliance_rows": claim_reliance_rows,
        "checks": checks,
        "privacy": {
            "prompt_disclosed": False,
            "output_disclosed": False,
            "source_text_disclosed": False,
            "raw_trace_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_reliance_proof": True,
        },
        "schemas": {
            "citation_reliance_receipt": CITATION_RELIANCE_RECEIPT_SCHEMA,
            "evidence_locked_generation": "docs/schemas/evidence_locked_generation.schema.json",
            "claim_source_attribution_report": "docs/schemas/claim_source_attribution_report.schema.json",
            "evidence_utility_attribution_report": "docs/schemas/evidence_utility_attribution_report.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "source_access_lease_report": "docs/schemas/source_access_lease_report.schema.json",
            "content_protocol_ingestion_report": "docs/schemas/content_protocol_ingestion_report.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "visible_source_count": len(visible_sources),
            "source_reliance_row_count": len(source_reliance_rows),
            "claim_reliance_row_count": len(claim_reliance_rows),
            "faithfully_covered_source_count": sum(
                1 for row in source_reliance_rows if row["covered_for_faithful_reliance"]
            ),
            "faithfully_covered_claim_count": sum(
                1 for row in claim_reliance_rows if row["covered_for_faithful_reliance"]
            ),
            "failed_check_count": len(failed),
            "post_hoc_citation_blocked": checks[
                "every_visible_source_has_satisfied_lock"
            ]
            and checks["visible_sources_are_in_current_turn_trace"],
            "footer_grounding_reliance_supported": True,
            "direct_settlement_reliance_supported": checks[
                "source_access_and_protocol_cover_direct_sources"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    receipt["citation_reliance_receipt_hash"] = hash_payload(_hashable_report(receipt))
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_citation_reliance_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "policy",
        "artifact_bindings",
        "visible_source_rows",
        "source_reliance_rows",
        "claim_reliance_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "citation_reliance_receipt_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing citation reliance receipt field: {key}")
    if receipt.get("version") != CITATION_RELIANCE_RECEIPT_VERSION:
        errors.append("citation reliance receipt version is unsupported")
    if "citation_reliance_receipt" not in receipt.get("schemas", {}):
        errors.append("missing citation reliance receipt schema")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("citation reliance receipt target level is not RDLLM-L100")
    for index, row in enumerate(receipt.get("source_reliance_rows", [])):
        for key in (
            "source_label",
            "source_id",
            "body_occurrence_count",
            "satisfied_lock_count",
            "causal_utility_count",
            "source_access_covered",
            "content_protocol_covered",
            "covered_for_faithful_reliance",
            "source_reliance_row_hash",
        ):
            if key not in row:
                errors.append(f"citation source reliance row {index} missing {key}")
    for index, row in enumerate(receipt.get("claim_reliance_rows", [])):
        for key in (
            "claim_id",
            "source_label",
            "rendered_claim_evidence_present",
            "satisfied_lock_count",
            "causal_utility_count",
            "covered_for_faithful_reliance",
            "claim_reliance_row_hash",
        ):
            if key not in row:
                errors.append(f"citation claim reliance row {index} missing {key}")
    return errors


def verify_citation_reliance_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a citation reliance receipt by replaying private inputs."""

    errors = validate_citation_reliance_receipt_shape(receipt)
    expected = make_citation_reliance_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    if receipt.get("citation_reliance_receipt_hash") != expected.get(
        "citation_reliance_receipt_hash"
    ):
        errors.append("citation reliance receipt hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("citation reliance receipt signature mismatch")
    if receipt.get("checks") != expected.get("checks"):
        errors.append("citation reliance receipt checks mismatch")
    if receipt.get("summary") != expected.get("summary"):
        errors.append("citation reliance receipt summary mismatch")
    if receipt.get("source_reliance_rows") != expected.get("source_reliance_rows"):
        errors.append("citation reliance receipt source rows mismatch")
    if receipt.get("claim_reliance_rows") != expected.get("claim_reliance_rows"):
        errors.append("citation reliance receipt claim rows mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("citation reliance receipt has failing checks")
    return errors
