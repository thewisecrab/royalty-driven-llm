"""Creator-facing attribution audit index.

This layer lets a creator or auditor ask "where did this creator/work/hash appear?"
across response footers, delivery receipts, model-release BOMs, post-training
signals, training lineage, access leases, license transactions, and payout
receipts. The public artifact is queryable and replayable, but it only exposes
labels, IDs, hashes, statuses, and proof handles rather than raw prompt, answer,
source, feedback, notice, license, or payment text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

CREATOR_ATTRIBUTION_AUDIT_INDEX_VERSION = (
    "rdllm-creator-attribution-audit-index/v1"
)
CREATOR_ATTRIBUTION_AUDIT_INDEX_SCHEMA = (
    "docs/schemas/creator_attribution_audit_index.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L110"
MINIMUM_CERTIFICATION_LEVEL = "RDLLM-L109"

DECLARED_HASH_FIELDS = (
    "creator_attribution_audit_index_hash",
    "attribution_bom_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "post_training_signal_provenance_hash",
    "lease_report_hash",
    "license_transaction_receipt_hash",
    "citation_reliance_receipt_hash",
    "graph_hash",
    "card_hash",
    "summary_hash",
    "report_hash",
    "receipt_hash",
    "contract_hash",
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
    "quote",
    "notice_text",
    "license_text",
    "feedback_text",
    "critique_text",
    "reward_explanation_text",
    "verifier_rationale",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
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


def load_creator_attribution_audit_index_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a creator attribution audit index."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _level_number(level: str) -> int:
    try:
        return int(str(level).rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_index(index: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in index.items()
        if key not in {"creator_attribution_audit_index_hash", "signature"}
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


def _private_strings_absent(index: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(index)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _query(audit_input: dict[str, Any]) -> dict[str, set[str]]:
    query = audit_input.get("query", {})
    return {
        "creator_ids": {str(item) for item in query.get("creator_ids", []) if item},
        "work_ids": {str(item) for item in query.get("work_ids", []) if item},
        "chunk_ids": {str(item) for item in query.get("chunk_ids", []) if item},
        "content_hashes": {
            str(item) for item in query.get("content_hashes", []) if item
        },
        "source_labels": {
            str(item) for item in query.get("source_labels", []) if item
        },
    }


def _query_commitment(audit_input: dict[str, Any]) -> dict[str, Any]:
    query = audit_input.get("query", {})
    return {
        "query_hash": hash_payload(query),
        "creator_id_count": len(query.get("creator_ids", [])),
        "work_id_count": len(query.get("work_ids", [])),
        "chunk_id_count": len(query.get("chunk_ids", [])),
        "content_hash_count": len(query.get("content_hashes", [])),
        "source_label_count": len(query.get("source_labels", [])),
        "raw_query_terms_disclosed": False,
    }


def _row_matches(row: dict[str, Any], query: dict[str, set[str]]) -> bool:
    content_hash = str(row.get("content_hash", ""))
    content_hash_prefix = str(row.get("content_hash_prefix", ""))
    return any(
        (
            str(row.get("creator_id", "")) in query["creator_ids"],
            str(row.get("recipient_creator_id", "")) in query["creator_ids"],
            str(row.get("work_id", "")) in query["work_ids"],
            str(row.get("chunk_id", "")) in query["chunk_ids"],
            content_hash in query["content_hashes"],
            bool(content_hash_prefix)
            and any(
                full_hash.startswith(content_hash_prefix)
                for full_hash in query["content_hashes"]
            ),
            str(row.get("source_label", row.get("label", "")))
            in query["source_labels"],
        )
    )


def _safe_hash_prefix(value: Any, length: int = 16) -> str:
    text = str(value or "")
    return text[:length] if text else ""


def _surface_row(
    *,
    artifact_name: str,
    artifact_type: str,
    artifact: dict[str, Any] | None,
    surface: str,
    source_label: str = "",
    creator_id: str = "",
    work_id: str = "",
    chunk_id: str = "",
    content_hash: str = "",
    content_hash_prefix: str = "",
    evidence_hash: str = "",
    visibility_state: str = "",
    settlement_state: str = "",
    notice_hash: str = "",
    license_terms_hash: str = "",
) -> dict[str, Any]:
    row = {
        "surface": surface,
        "artifact_name": artifact_name,
        "artifact_type": artifact_type,
        "artifact_hash": _declared_hash(artifact),
        "source_label": source_label,
        "creator_id": creator_id,
        "work_id": work_id,
        "chunk_id": chunk_id,
        "content_hash_prefix": content_hash_prefix or _safe_hash_prefix(content_hash),
        "evidence_hash": evidence_hash,
        "visibility_state": visibility_state,
        "settlement_state": settlement_state,
        "notice_hash": notice_hash,
        "license_terms_hash": license_terms_hash,
        "source_label_namespace": f"{artifact_name}:{surface}",
    }
    row["surface_row_hash"] = hash_payload(row)
    return row


def _props(component: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for prop in component.get("properties", []):
        if isinstance(prop, dict):
            result[str(prop.get("name", ""))] = str(prop.get("value", ""))
    return result


def _artifact_bindings(audit_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "certification_report": audit_input.get("certification_report"),
        "provider_attribution_card": audit_input.get("provider_attribution_card"),
        "attribution_bom": audit_input.get("attribution_bom"),
        "proof_dependency_graph": audit_input.get("proof_dependency_graph"),
        "grounded_source_footer": audit_input.get("grounded_source_footer"),
        "source_footer_delivery": audit_input.get("source_footer_delivery"),
        "post_training_signal_provenance": audit_input.get(
            "post_training_signal_provenance"
        ),
        "model_lineage_attribution_report": audit_input.get(
            "model_lineage_attribution_report"
        ),
        "creator_payout_receipt_report": audit_input.get(
            "creator_payout_receipt_report"
        ),
        "training_content_summary": audit_input.get("training_content_summary"),
        "source_access_lease_report": audit_input.get("source_access_lease_report"),
        "license_transaction_receipt": audit_input.get(
            "license_transaction_receipt"
        ),
        "citation_reliance_receipt": audit_input.get("citation_reliance_receipt"),
    }
    return {
        name: {
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        }
        for name, artifact in artifacts.items()
        if artifact
    }


def _collect_abom_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("attribution_bom", {})
    rows: list[dict[str, Any]] = []
    for component in artifact.get("components", []):
        if component.get("type") != "data":
            continue
        props = _props(component)
        row = {
            "source_label": props.get("rdllm:source_label", ""),
            "creator_id": props.get("rdllm:creator_id", ""),
            "work_id": props.get("rdllm:work_id", ""),
            "chunk_id": props.get("rdllm:chunk_id", ""),
            "content_hash": props.get("rdllm:content_hash", ""),
            "notice_hash": props.get("rdllm:notice_hash", ""),
            "license_terms_hash": props.get("rdllm:license_terms_hash", ""),
            "settlement_state": props.get("rdllm:settlement_state", ""),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="attribution_bom",
                    artifact_type="attribution_bom",
                    artifact=artifact,
                    surface="model_release_abom_source_component",
                    evidence_hash=component.get("hashes", [{}])[0].get("content", ""),
                    visibility_state="model_release_public",
                    **row,
                )
            )
    return rows


def _collect_footer_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("grounded_source_footer", {})
    rows: list[dict[str, Any]] = []
    for source in artifact.get("footer_rows", []):
        row = {
            "source_label": str(source.get("label", "")),
            "creator_id": str(source.get("creator_id", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "content_hash_prefix": str(source.get("content_hash_prefix", "")),
            "settlement_state": str(source.get("royalty_status", "")),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="grounded_source_footer",
                    artifact_type="grounded_source_footer",
                    artifact=artifact,
                    surface="user_visible_grounded_footer",
                    evidence_hash=str(source.get("footer_row_hash", "")),
                    visibility_state=(
                        "rendered"
                        if source.get("rendered_in_footer") is True
                        else "not_rendered"
                    ),
                    **row,
                )
            )
    return rows


def _collect_delivery_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("source_footer_delivery", {})
    rows: list[dict[str, Any]] = []
    for source in artifact.get("source_delivery_rows", []):
        row = {
            "source_label": str(source.get("label", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "settlement_state": (
                "license_transaction_covered"
                if source.get("license_transaction_covered") is True
                else "uncovered"
            ),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="source_footer_delivery",
                    artifact_type="source_footer_delivery",
                    artifact=artifact,
                    surface="client_delivered_footer",
                    evidence_hash=str(source.get("source_delivery_row_hash", "")),
                    visibility_state=(
                        "delivered"
                        if source.get("label_visible_in_delivered_output") is True
                        else "not_delivered"
                    ),
                    **row,
                )
            )
    return rows


def _collect_citation_reliance_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("citation_reliance_receipt", {})
    rows: list[dict[str, Any]] = []
    for source in artifact.get("source_reliance_rows", []):
        row = {
            "source_label": str(source.get("source_label", "")),
            "creator_id": str(source.get("creator_id", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "content_hash_prefix": str(source.get("content_hash_prefix", "")),
            "settlement_state": (
                "direct"
                if int(source.get("direct_settlement_count", 0) or 0) > 0
                else "unknown"
            ),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="citation_reliance_receipt",
                    artifact_type="citation_reliance_receipt",
                    artifact=artifact,
                    surface="claim_citation_reliance",
                    evidence_hash=str(source.get("source_reliance_row_hash", "")),
                    visibility_state="claim_reliance_public",
                    **row,
                )
            )
    return rows


def _collect_source_access_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("source_access_lease_report", {})
    rows: list[dict[str, Any]] = []
    for source in artifact.get("source_usage_rows", []):
        row = {
            "source_label": str(source.get("source_label", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "content_hash": str(source.get("content_hash", "")),
            "settlement_state": str(source.get("settlement_status", "")),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="source_access_lease_report",
                    artifact_type="source_access_lease_report",
                    artifact=artifact,
                    surface="pre_use_source_access",
                    evidence_hash=str(source.get("usage_row_hash", "")),
                    visibility_state=str(source.get("usage_purpose", "")),
                    **row,
                )
            )
    for lease in artifact.get("lease_rows", []):
        row = {
            "creator_id": str(lease.get("creator_id", "")),
            "work_id": str(lease.get("work_id", "")),
            "chunk_id": str(lease.get("chunk_id", "")),
            "content_hash": str(lease.get("content_hash", "")),
            "settlement_state": "active" if lease.get("revoked") is not True else "revoked",
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="source_access_lease_report",
                    artifact_type="source_access_lease_report",
                    artifact=artifact,
                    surface="source_issued_access_lease",
                    evidence_hash=str(lease.get("lease_row_hash", "")),
                    visibility_state=str(lease.get("access_method", "")),
                    **row,
                )
            )
    return rows


def _collect_license_transaction_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("license_transaction_receipt", {})
    rows: list[dict[str, Any]] = []
    for coverage in artifact.get("coverage_rows", []):
        row = {
            "source_label": str(coverage.get("source_label", "")),
            "work_id": str(coverage.get("work_id", "")),
            "chunk_id": str(coverage.get("chunk_id", "")),
            "settlement_state": (
                "transaction_accepted"
                if coverage.get("transaction_accepted") is True
                else "missing_or_invalid"
            ),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="license_transaction_receipt",
                    artifact_type="license_transaction_receipt",
                    artifact=artifact,
                    surface="license_transaction_coverage",
                    evidence_hash=str(coverage.get("coverage_row_hash", "")),
                    visibility_state=str(coverage.get("selected_transaction_id", "")),
                    **row,
                )
            )
    return rows


def _collect_post_training_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("post_training_signal_provenance", {})
    obligation_by_label = {
        str(row.get("source_label", "")): row
        for row in artifact.get("royalty_obligations", [])
        if row.get("source_label")
    }
    rows: list[dict[str, Any]] = []
    for signal in artifact.get("post_training_signals", []):
        for label in signal.get("source_labels", []):
            obligation = obligation_by_label.get(str(label), {})
            row = {
                "source_label": str(label),
                "creator_id": str(obligation.get("creator_id", "")),
                "work_id": str(obligation.get("work_id", "")),
                "settlement_state": str(obligation.get("settlement_state", "")),
                "license_terms_hash": str(signal.get("license_terms_hash", "")),
            }
            if _row_matches(row, query):
                rows.append(
                    _surface_row(
                        artifact_name="post_training_signal_provenance",
                        artifact_type="post_training_signal_provenance",
                        artifact=artifact,
                        surface="post_training_signal_source",
                        evidence_hash=str(signal.get("signal_row_hash", "")),
                        visibility_state=str(signal.get("post_training_stage", "")),
                        **row,
                    )
                )
    return rows


def _collect_model_lineage_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("model_lineage_attribution_report", {})
    rows: list[dict[str, Any]] = []
    for item in artifact.get("training_items", []):
        for source in item.get("source_rows", []):
            row = {
                "source_label": str(source.get("source_label", "")),
                "creator_id": str(source.get("creator_id", "")),
                "work_id": str(source.get("work_id", "")),
                "chunk_id": str(source.get("chunk_id", "")),
                "content_hash": str(source.get("content_hash", "")),
                "settlement_state": str(item.get("decision", "")),
            }
            if _row_matches(row, query):
                rows.append(
                    _surface_row(
                        artifact_name="model_lineage_attribution_report",
                        artifact_type="model_lineage_attribution_report",
                        artifact=artifact,
                        surface="model_lineage_training_source",
                        evidence_hash=str(source.get("source_row_hash", "")),
                        visibility_state=str(item.get("training_method", "")),
                        **row,
                    )
                )
    for obligation in artifact.get("usage_settlement_obligations", []):
        row = {
            "creator_id": str(obligation.get("recipient_creator_id", "")),
            "work_id": str(obligation.get("work_id", "")),
            "chunk_id": str(obligation.get("chunk_id", "")),
            "settlement_state": "model_lineage_obligation",
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="model_lineage_attribution_report",
                    artifact_type="model_lineage_attribution_report",
                    artifact=artifact,
                    surface="model_lineage_settlement_obligation",
                    evidence_hash=str(obligation.get("obligation_hash", "")),
                    visibility_state=str(obligation.get("basis", "")),
                    **row,
                )
            )
    return rows


def _collect_payout_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("creator_payout_receipt_report", {})
    rows: list[dict[str, Any]] = []
    for payout in artifact.get("creator_payout_rows", []):
        chunk_ids = payout.get("chunk_ids", [])
        row = {
            "creator_id": str(payout.get("recipient_creator_id", "")),
            "recipient_creator_id": str(payout.get("recipient_creator_id", "")),
            "work_id": str(payout.get("work_id", "")),
            "chunk_id": str(chunk_ids[0] if chunk_ids else ""),
            "settlement_state": str(payout.get("creator_visible_status", "")),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="creator_payout_receipt_report",
                    artifact_type="creator_payout_receipt_report",
                    artifact=artifact,
                    surface="creator_visible_payout_receipt",
                    evidence_hash=str(payout.get("creator_receipt_row_hash", "")),
                    visibility_state=str(payout.get("execution_status", "")),
                    **{key: value for key, value in row.items() if key != "recipient_creator_id"},
                )
            )
    return rows


def _collect_training_summary_rows(audit_input: dict[str, Any], query: dict[str, set[str]]) -> list[dict[str, Any]]:
    artifact = audit_input.get("training_content_summary", {})
    rows: list[dict[str, Any]] = []
    for cohort in artifact.get("training_content", {}).get("cohorts", []):
        row = {
            "creator_id": str(cohort.get("creator_id", "")),
            "work_id": str(cohort.get("work_id", "")),
            "content_hash": str(cohort.get("content_hash", "")),
            "settlement_state": (
                "training_allowed"
                if cohort.get("training_allowed") is True
                else "training_blocked"
            ),
        }
        if _row_matches(row, query):
            rows.append(
                _surface_row(
                    artifact_name="training_content_summary",
                    artifact_type="training_content_summary",
                    artifact=artifact,
                    surface="training_content_summary_cohort",
                    evidence_hash=str(cohort.get("training_value_root", "")),
                    visibility_state=str(cohort.get("content_category", "")),
                    license_terms_hash=str(cohort.get("license", "")),
                    **row,
                )
            )
    return rows


def _surface_rows(audit_input: dict[str, Any]) -> list[dict[str, Any]]:
    query = _query(audit_input)
    rows: list[dict[str, Any]] = []
    for collector in (
        _collect_abom_rows,
        _collect_footer_rows,
        _collect_delivery_rows,
        _collect_citation_reliance_rows,
        _collect_source_access_rows,
        _collect_license_transaction_rows,
        _collect_post_training_rows,
        _collect_model_lineage_rows,
        _collect_payout_rows,
        _collect_training_summary_rows,
    ):
        rows.extend(collector(audit_input, query))
    return sorted(
        rows,
        key=lambda row: (
            row["artifact_name"],
            row["surface"],
            row.get("creator_id", ""),
            row.get("work_id", ""),
            row.get("source_label", ""),
            row["surface_row_hash"],
        ),
    )


def _creator_work_rows(surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    creator_by_work = {
        str(row.get("work_id", "")): str(row.get("creator_id", ""))
        for row in surface_rows
        if row.get("work_id") and row.get("creator_id")
    }
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in surface_rows:
        work_id = str(row.get("work_id", ""))
        creator_id = str(row.get("creator_id", "")) or creator_by_work.get(work_id, "")
        key = (
            creator_id,
            work_id,
            str(row.get("chunk_id", "")),
        )
        grouped.setdefault(key, []).append(row)
    result: list[dict[str, Any]] = []
    for (creator_id, work_id, chunk_id), rows in sorted(grouped.items()):
        surfaces = sorted({row["surface"] for row in rows})
        artifact_names = sorted({row["artifact_name"] for row in rows})
        settlement_states = sorted(
            {row["settlement_state"] for row in rows if row.get("settlement_state")}
        )
        content_hash_prefixes = sorted(
            {row["content_hash_prefix"] for row in rows if row.get("content_hash_prefix")}
        )
        row = {
            "creator_id": creator_id,
            "work_id": work_id,
            "chunk_id": chunk_id,
            "content_hash_prefixes": content_hash_prefixes,
            "content_hash_prefix_root": hash_payload(content_hash_prefixes),
            "surface_count": len(surfaces),
            "surfaces": surfaces,
            "artifact_names": artifact_names,
            "settlement_states": settlement_states,
            "footer_visible": any(
                source.get("surface") == "user_visible_grounded_footer"
                for source in rows
            ),
            "model_release_bound": any(
                source.get("surface") == "model_release_abom_source_component"
                for source in rows
            ),
            "post_training_bound": any(
                source.get("surface") == "post_training_signal_source"
                for source in rows
            ),
            "payout_or_obligation_bound": any(
                source.get("surface")
                in {
                    "creator_visible_payout_receipt",
                    "model_lineage_settlement_obligation",
                    "post_training_signal_source",
                    "license_transaction_coverage",
                    "pre_use_source_access",
                    "model_release_abom_source_component",
                }
                for source in rows
            ),
        }
        row["creator_work_row_hash"] = hash_payload(row)
        result.append(row)
    return result


def _non_inclusion_rows(audit_input: dict[str, Any], surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query = audit_input.get("query", {})
    matched = {
        "creator_ids": {row.get("creator_id", "") for row in surface_rows},
        "work_ids": {row.get("work_id", "") for row in surface_rows},
        "chunk_ids": {row.get("chunk_id", "") for row in surface_rows},
        "source_labels": {row.get("source_label", "") for row in surface_rows},
    }
    rows: list[dict[str, Any]] = []
    for term_type in ("creator_ids", "work_ids", "chunk_ids", "source_labels"):
        for term in query.get(term_type, []):
            if str(term) not in matched.get(term_type, set()):
                row = {
                    "term_type": term_type,
                    "term_hash": hash_payload(str(term)),
                    "matched": False,
                }
                row["non_inclusion_row_hash"] = hash_payload(row)
                rows.append(row)
    content_prefixes = {row.get("content_hash_prefix", "") for row in surface_rows}
    for term in query.get("content_hashes", []):
        if not any(str(term).startswith(prefix) and prefix for prefix in content_prefixes):
            row = {
                "term_type": "content_hashes",
                "term_hash": hash_payload(str(term)),
                "matched": False,
            }
            row["non_inclusion_row_hash"] = hash_payload(row)
            rows.append(row)
    return rows


def _base_checks(
    *,
    audit_input: dict[str, Any],
    surface_rows: list[dict[str, Any]],
    creator_work_rows: list[dict[str, Any]],
    artifact_bindings: dict[str, Any],
) -> dict[str, bool]:
    certification = audit_input.get("certification_report", {})
    certification_summary = certification.get("summary", {})
    attribution_bom = audit_input.get("attribution_bom", {})
    provider_card = audit_input.get("provider_attribution_card", {})
    footer_labels = {
        (row.get("work_id", ""), row.get("source_label", ""))
        for row in surface_rows
        if row.get("surface") == "user_visible_grounded_footer"
    }
    delivery_labels = {
        (row.get("work_id", ""), row.get("source_label", ""))
        for row in surface_rows
        if row.get("surface") == "client_delivered_footer"
    }
    post_training_labels = {
        row.get("source_label", "")
        for row in surface_rows
        if row.get("surface") == "post_training_signal_source"
    }
    post_training_obligation_labels = {
        str(row.get("source_label", ""))
        for row in audit_input.get("post_training_signal_provenance", {}).get(
            "royalty_obligations", []
        )
    }
    abom_rows = [
        row
        for row in surface_rows
        if row.get("surface") == "model_release_abom_source_component"
    ]

    return {
        "certification_report_verified_l109_or_higher": certification_summary.get("status") == "passed"
        and _level_number(str(certification_summary.get("highest_level", ""))) >= 109,
        "provider_card_declares_creator_audit_surface": provider_card.get("certification", {}).get("highest_level") == certification_summary.get("highest_level")
        and provider_card.get("supported_evidence_channels", {}).get("attribution_bom") is True
        and provider_card.get("supported_evidence_channels", {}).get("creator_attribution_audit_index") is True
        and provider_card.get("public_disclosure_surfaces", {}).get("creator_attribution_audit_index") is True,
        "attribution_bom_ready_and_hash_reproducible": attribution_bom.get("summary", {}).get("target_certification_level") == "RDLLM-L109"
        and attribution_bom.get("summary", {}).get("status") == "ready"
        and _artifact_hash_is_reproducible(attribution_bom),
        "query_commitment_present": bool(audit_input.get("query"))
        and bool(_query_commitment(audit_input).get("query_hash")),
        "creator_query_matches_public_rows": bool(surface_rows),
        "matched_rows_have_artifact_bindings": bool(artifact_bindings)
        and all(row.get("artifact_hash") for row in surface_rows),
        "source_identity_namespaced_by_artifact": all(
            row.get("source_label_namespace") and row.get("artifact_name")
            for row in surface_rows
        ),
        "abom_rows_have_notice_and_license_hashes": all(
            row.get("notice_hash") and row.get("license_terms_hash")
            for row in abom_rows
        ),
        "visible_footer_rows_have_delivery_proof": footer_labels.issubset(delivery_labels),
        "post_training_rows_have_royalty_obligations": post_training_labels.issubset(
            post_training_obligation_labels
        ),
        "payout_or_obligation_rows_cover_matched_works": bool(creator_work_rows)
        and all(row.get("payout_or_obligation_bound") is True for row in creator_work_rows),
        "notices_and_private_text_not_disclosed": not _contains_private_fields(
            audit_input.get("public_overrides", {})
        ),
    }


def make_creator_attribution_audit_index(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed creator-facing attribution audit index."""

    issued_at = issued_at or now_iso()
    surface_rows = _surface_rows(audit_input)
    creator_work_rows = _creator_work_rows(surface_rows)
    non_inclusion_rows = _non_inclusion_rows(audit_input, surface_rows)
    artifact_bindings = _artifact_bindings(audit_input)
    checks = _base_checks(
        audit_input=audit_input,
        surface_rows=surface_rows,
        creator_work_rows=creator_work_rows,
        artifact_bindings=artifact_bindings,
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    index: dict[str, Any] = {
        "version": CREATOR_ATTRIBUTION_AUDIT_INDEX_VERSION,
        "issued_at": issued_at,
        "issuer": issuer,
        "case": {
            "case_id": str(audit_input.get("case_id", "case:creator-attribution-audit-index")),
            "query_commitment": _query_commitment(audit_input),
            "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
        },
        "artifact_bindings": artifact_bindings,
        "creator_work_rows": creator_work_rows,
        "surface_rows": surface_rows,
        "non_inclusion_rows": non_inclusion_rows,
        "commitments": {
            "creator_work_root": hash_payload(
                [row["creator_work_row_hash"] for row in creator_work_rows]
            ),
            "surface_row_root": hash_payload(
                [row["surface_row_hash"] for row in surface_rows]
            ),
            "non_inclusion_root": hash_payload(
                [row["non_inclusion_row_hash"] for row in non_inclusion_rows]
            ),
            "artifact_binding_root": hash_payload(artifact_bindings),
        },
        "checks": checks,
        "privacy": {
            "raw_query_terms_disclosed": False,
            "raw_prompt_disclosed": False,
            "raw_answer_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_feedback_text_disclosed": False,
            "raw_notice_text_disclosed": False,
            "raw_license_text_disclosed": False,
            "raw_payment_data_disclosed": False,
            "index_uses_hashes_labels_statuses_and_proof_handles": True,
        },
        "schemas": {
            "creator_attribution_audit_index": CREATOR_ATTRIBUTION_AUDIT_INDEX_SCHEMA,
            "attribution_bom": "docs/schemas/attribution_bom.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "post_training_signal_provenance": "docs/schemas/post_training_signal_provenance.schema.json",
        },
        "summary": {
            "status": "ready" if failed_check_count == 0 else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
            "creator_work_count": len(creator_work_rows),
            "surface_row_count": len(surface_rows),
            "artifact_binding_count": len(artifact_bindings),
            "non_inclusion_row_count": len(non_inclusion_rows),
            "failed_check_count": failed_check_count,
            "creator_audit_index_ready": failed_check_count == 0,
            "privacy_preserved": checks["notices_and_private_text_not_disclosed"],
        },
    }
    checks["notices_and_private_text_not_disclosed"] = (
        checks["notices_and_private_text_not_disclosed"]
        and _private_strings_absent(index, audit_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    index["summary"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    index["summary"]["failed_check_count"] = failed_check_count
    index["summary"]["creator_audit_index_ready"] = failed_check_count == 0
    index["summary"]["privacy_preserved"] = checks["notices_and_private_text_not_disclosed"]
    index["creator_attribution_audit_index_hash"] = hash_payload(_hashable_index(index))
    index["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_index(index), signing_secret) if signing_secret else ""
        ),
    }
    return index


def validate_creator_attribution_audit_index_shape(index: dict[str, Any]) -> list[str]:
    """Validate the public shape of a creator attribution audit index."""

    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "artifact_bindings",
        "creator_work_rows",
        "surface_rows",
        "non_inclusion_rows",
        "commitments",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "creator_attribution_audit_index_hash",
        "signature",
    )
    for key in required:
        if key not in index:
            errors.append(f"missing creator attribution audit index field: {key}")
    if errors:
        return errors
    if index.get("version") != CREATOR_ATTRIBUTION_AUDIT_INDEX_VERSION:
        errors.append("creator attribution audit index version is unsupported")
    if index.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("creator attribution audit index target level is not RDLLM-L110")
    if (
        "creator_attribution_audit_index"
        not in index.get("schemas", {})
    ):
        errors.append("missing creator attribution audit index schema")
    if not isinstance(index.get("surface_rows"), list):
        errors.append("creator attribution audit index surface_rows must be a list")
    if _contains_private_fields(index):
        errors.append("creator attribution audit index contains private field")
    return errors


def verify_creator_attribution_audit_index(
    index: dict[str, Any],
    audit_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a creator attribution audit index against replay inputs."""

    errors = validate_creator_attribution_audit_index_shape(index)
    expected = make_creator_attribution_audit_index(
        audit_input,
        issuer=str(index.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(index.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "version",
        "case",
        "artifact_bindings",
        "creator_work_rows",
        "surface_rows",
        "non_inclusion_rows",
        "commitments",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if index.get(key) != expected.get(key):
            errors.append(f"creator attribution audit index {key} mismatch")
    if index.get("creator_attribution_audit_index_hash") != expected.get(
        "creator_attribution_audit_index_hash"
    ):
        errors.append("creator attribution audit index hash mismatch")
    if index.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("creator attribution audit index signature mismatch")
    if any(value is not True for value in index.get("checks", {}).values()):
        errors.append("creator attribution audit index has failing checks")
    return errors
