"""Source-origin lineage gates for synthetic-source royalty laundering.

This layer sits after warranted source footers. It prevents a verified footer
from becoming a royalty siphon when a cited source is synthetic, undisclosed, or
unknown-origin content. Human-origin sources can be paid directly. Synthetic
sources can be paid only through declared upstream lineage rows. Everything else
is routed to origin-review escrow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

SOURCE_ORIGIN_LINEAGE_VERSION = "rdllm-source-origin-lineage/v1"
SOURCE_ORIGIN_LINEAGE_SCHEMA = "docs/schemas/source_origin_lineage.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L121"
MINIMUM_INPUT_LEVEL = "RDLLM-L120"

ORIGIN_CLASSES = {
    "human_original",
    "synthetic_with_lineage",
    "synthetic_unattributed",
    "unknown",
}

DECLARED_HASH_FIELDS = (
    "source_origin_lineage_hash",
    "warranted_source_footer_hash",
    "grounded_source_footer_hash",
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
    "answer_text",
    "claim_text",
    "evidence_text",
    "source_text",
    "document_text",
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


def load_source_origin_lineage_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L121 source-origin lineage report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"source_origin_lineage_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], lineage_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in lineage_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _artifact_bindings(lineage_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "warranted_source_footer": lineage_input.get("warranted_source_footer"),
        "grounded_source_footer": lineage_input.get("grounded_source_footer"),
        "source_authenticity_report": lineage_input.get("source_authenticity_report"),
        "creator_license_contract": lineage_input.get("creator_license_contract"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("lineage_version")
            or (artifact or {}).get("footer_version")
            or (artifact or {}).get("version")
            or (artifact or {}).get("report_version")
            or (artifact or {}).get("contract_version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _source_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("label", "")),
        str(row.get("work_id", "")),
        str(row.get("chunk_id", "")),
    )


def _authenticity_rows_by_key(report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("source_authenticity_rows", []):
        key = _source_key(row)
        if any(key):
            rows[key] = row
    return rows


def _lineage_attestations_by_key(
    lineage_input: dict[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in lineage_input.get("origin_attestations", []):
        key = _source_key(row)
        if any(key):
            rows[key] = row
    return rows


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalised_upstream_rows(
    source: dict[str, Any],
    attestation: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, upstream in enumerate(attestation.get("upstream_sources", []), start=1):
        share = round(_float(upstream.get("upstream_share")), 8)
        row = {
            "source_label": str(source.get("label", "")),
            "upstream_index": index,
            "upstream_creator_id": str(upstream.get("upstream_creator_id", "")),
            "upstream_work_id": str(upstream.get("upstream_work_id", "")),
            "upstream_content_hash": str(upstream.get("upstream_content_hash", "")),
            "upstream_license_status": str(upstream.get("license_status", "")),
            "attribution_required": upstream.get("attribution_required") is not False,
            "royalty_required": upstream.get("royalty_required") is not False,
            "upstream_share": share,
            "upstream_lineage_hash": str(upstream.get("upstream_lineage_hash", "")),
        }
        row["upstream_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _origin_class(
    attestation: dict[str, Any],
    authenticity: dict[str, Any],
) -> str:
    declared = str(attestation.get("origin_class", "")).strip()
    if declared in ORIGIN_CLASSES:
        return declared
    if authenticity.get("synthetic_source") is True or authenticity.get("ai_generated_disclosed") is True:
        return "synthetic_unattributed"
    if authenticity.get("human_origin_attested") is True:
        return "human_original"
    return "unknown"


def _lineage_status(origin_class: str, attestation: dict[str, Any], upstream_rows: list[dict[str, Any]]) -> str:
    signed = (
        attestation.get("attestation_signature_verified") is True
        and attestation.get("attestation_issuer_trusted") is True
    )
    if origin_class == "human_original":
        return "human_origin_clear" if signed else "human_origin_unverified"
    if origin_class == "synthetic_with_lineage":
        upstream_ok = bool(upstream_rows) and all(
            row["upstream_creator_id"]
            and row["upstream_work_id"]
            and row["upstream_license_status"] == "active"
            and row["upstream_share"] > 0
            for row in upstream_rows
        )
        share_sum = round(sum(row["upstream_share"] for row in upstream_rows), 8)
        if signed and upstream_ok and 0 < share_sum <= 1.0:
            return "synthetic_lineage_clear"
        return "synthetic_lineage_incomplete"
    if origin_class == "synthetic_unattributed":
        return "synthetic_unattributed"
    return "unknown_origin"


def _settlement_action(lineage_status: str) -> str:
    if lineage_status == "human_origin_clear":
        return "direct_source_creator_payout"
    if lineage_status == "synthetic_lineage_clear":
        return "split_payout_to_upstream_creators"
    return "origin_review_escrow"


def _source_origin_rows(lineage_input: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warranted = lineage_input.get("warranted_source_footer", {})
    authenticity_by_key = _authenticity_rows_by_key(
        lineage_input.get("source_authenticity_report", {})
    )
    attestations_by_key = _lineage_attestations_by_key(lineage_input)
    source_rows: list[dict[str, Any]] = []
    upstream_rows: list[dict[str, Any]] = []

    for source in warranted.get("source_rows", []):
        key = _source_key(source)
        authenticity = authenticity_by_key.get(key, {})
        attestation = attestations_by_key.get(key, {})
        origin_class = _origin_class(attestation, authenticity)
        upstream = _normalised_upstream_rows(source, attestation)
        status = _lineage_status(origin_class, attestation, upstream)
        action = _settlement_action(status)
        upstream_share = round(sum(row["upstream_share"] for row in upstream), 8)
        direct_source_share = 1.0 if action == "direct_source_creator_payout" else 0.0
        escrow_share = 1.0 if action == "origin_review_escrow" else 0.0
        row = {
            "display_order": int(source.get("display_order", 0) or 0),
            "label": str(source.get("label", "")),
            "display_label": str(source.get("display_label", "")),
            "title": str(source.get("title", "")),
            "creator_id": str(source.get("creator_id", "")),
            "work_id": key[1],
            "chunk_id": key[2],
            "source_uri": str(source.get("source_uri", "")),
            "content_hash_prefix": str(source.get("content_hash_prefix", "")),
            "warranted_source_row_hash": str(source.get("warranted_source_row_hash", "")),
            "source_authenticity_hash": str(authenticity.get("source_authenticity_hash", "")),
            "origin_class": origin_class,
            "origin_attestation_hash": str(attestation.get("origin_attestation_hash", "")),
            "origin_attestation_issuer": str(attestation.get("origin_attestation_issuer", "")),
            "attestation_signature_verified": attestation.get("attestation_signature_verified") is True,
            "attestation_issuer_trusted": attestation.get("attestation_issuer_trusted") is True,
            "synthetic_generation_disclosed": attestation.get("synthetic_generation_disclosed") is True,
            "upstream_creator_count": len(upstream),
            "upstream_share_sum": upstream_share,
            "direct_source_creator_share": direct_source_share,
            "origin_review_escrow_share": escrow_share,
            "lineage_status": status,
            "source_creator_direct_payout_allowed": (
                action == "direct_source_creator_payout"
            ),
            "lineage_settlement_allowed": action != "origin_review_escrow",
            "direct_payout_allowed": action == "direct_source_creator_payout",
            "settlement_action": action,
            "footer_origin_label": (
                f"{source.get('display_label', '')} origin={origin_class}; "
                f"lineage={status}; settlement={action}"
            ),
        }
        row["source_origin_row_hash"] = hash_payload(row)
        source_rows.append(row)
        upstream_rows.extend(upstream)
    return source_rows, upstream_rows


def _checks(
    *,
    lineage_input: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    source_origin_rows: list[dict[str, Any]],
    upstream_rows: list[dict[str, Any]],
    public_report_stub: dict[str, Any],
) -> dict[str, bool]:
    warranted = lineage_input.get("warranted_source_footer", {})
    grounded = lineage_input.get("grounded_source_footer", {})
    authenticity = lineage_input.get("source_authenticity_report", {})
    visible_count = int(warranted.get("summary", {}).get("visible_source_count", 0) or 0)
    synthetic_rows = [
        row for row in source_origin_rows if row["origin_class"].startswith("synthetic")
    ]
    escrow_rows = [
        row for row in source_origin_rows if row["settlement_action"] == "origin_review_escrow"
    ]
    return {
        "artifact_hashes_reproducible": all(
            value["present"] and value["hash_reproducible"] for value in bindings.values()
        ),
        "warranted_source_footer_ready_l120": (
            warranted.get("summary", {}).get("status") == "ready"
            and warranted.get("summary", {}).get("target_certification_level") == "RDLLM-L120"
            and all(warranted.get("checks", {}).values())
        ),
        "grounded_source_footer_ready": (
            grounded.get("summary", {}).get("status") == "ready"
            and all(grounded.get("checks", {}).values())
        ),
        "source_authenticity_verified_or_escrowed": authenticity.get("summary", {}).get(
            "status"
        )
        in {"verified", "warning", "failed"},
        "origin_rows_cover_visible_sources": (
            bool(source_origin_rows)
            and len(source_origin_rows) == visible_count
            and all(row["label"] for row in source_origin_rows)
        ),
        "synthetic_sources_have_upstream_lineage_or_escrow": all(
            (
                row["lineage_status"] == "synthetic_lineage_clear"
                and row["upstream_creator_count"] > 0
                and row["settlement_action"] == "split_payout_to_upstream_creators"
            )
            or row["settlement_action"] == "origin_review_escrow"
            for row in synthetic_rows
        ),
        "unknown_or_unattributed_sources_escrowed": all(
            row["settlement_action"] == "origin_review_escrow"
            for row in source_origin_rows
            if row["origin_class"] in {"unknown", "synthetic_unattributed"}
        ),
        "direct_payout_requires_clear_origin": all(
            row["lineage_status"] in {"human_origin_clear", "synthetic_lineage_clear"}
            for row in source_origin_rows
            if row["lineage_settlement_allowed"]
        ),
        "lineage_shares_conserve_source_value": all(
            round(
                row["direct_source_creator_share"]
                + row["origin_review_escrow_share"]
                + (
                    row["upstream_share_sum"]
                    if row["settlement_action"] == "split_payout_to_upstream_creators"
                    else 0.0
                ),
                8,
            )
            == 1.0
            for row in source_origin_rows
        ),
        "upstream_rows_are_license_active": all(
            row["upstream_license_status"] == "active"
            and row["upstream_creator_id"]
            and row["upstream_work_id"]
            and row["upstream_share"] > 0
            for row in upstream_rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report_stub)
            and _private_strings_absent(public_report_stub, lineage_input)
        ),
        "escrow_rows_are_publicly_labeled": all(
            "origin_review_escrow" in row["footer_origin_label"] for row in escrow_rows
        ),
    }


def make_source_origin_lineage_report(
    lineage_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public L121 source-origin lineage report."""

    created_at = created_at or now_iso()
    bindings = _artifact_bindings(lineage_input)
    source_origin_rows, upstream_rows = _source_origin_rows(lineage_input)
    footer_display = {
        "profile": "rdllm-visible-source-origin-footer/v1",
        "line_count": len(source_origin_rows),
        "origin_lines": [row["footer_origin_label"] for row in source_origin_rows],
        "source_origin_root": hash_payload(
            [row["source_origin_row_hash"] for row in source_origin_rows]
        ),
        "upstream_lineage_root": hash_payload(
            [row["upstream_row_hash"] for row in upstream_rows]
        ),
    }
    footer_display["footer_hash"] = hash_payload(footer_display)
    public_stub = {
        "source_origin_rows": source_origin_rows,
        "upstream_royalty_rows": upstream_rows,
        "footer_display": footer_display,
    }
    checks = _checks(
        lineage_input=lineage_input,
        bindings=bindings,
        source_origin_rows=source_origin_rows,
        upstream_rows=upstream_rows,
        public_report_stub=public_stub,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "failed"
    report = {
        "lineage_version": SOURCE_ORIGIN_LINEAGE_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "policy": {
            "profile": "rdllm-source-origin-lineage-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "synthetic_sources_require_upstream_lineage": True,
            "unknown_origin_direct_payout_allowed": False,
            "unattributed_synthetic_direct_payout_allowed": False,
            "origin_review_escrow_required": True,
            "raw_source_text_disclosure_allowed": False,
        },
        "artifact_bindings": bindings,
        "source_origin_rows": source_origin_rows,
        "upstream_royalty_rows": upstream_rows,
        "footer_display": footer_display,
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "unknown_origin_source_labels": [
                row["label"] for row in source_origin_rows if row["origin_class"] == "unknown"
            ],
            "synthetic_unattributed_source_labels": [
                row["label"]
                for row in source_origin_rows
                if row["origin_class"] == "synthetic_unattributed"
            ],
            "origin_review_escrow_source_labels": [
                row["label"]
                for row in source_origin_rows
                if row["settlement_action"] == "origin_review_escrow"
            ],
        },
        "commitments": {
            "source_origin_root": footer_display["source_origin_root"],
            "upstream_lineage_root": footer_display["upstream_lineage_root"],
            "footer_display_hash": footer_display["footer_hash"],
            "artifact_binding_root": hash_payload(bindings),
            "schema": SOURCE_ORIGIN_LINEAGE_SCHEMA,
        },
        "privacy": {
            "origin_labels_disclosed": True,
            "upstream_creator_ids_disclosed": True,
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "payment_account_disclosed": False,
            "public_report_uses_hashes_labels_and_share_commitments": True,
        },
        "schemas": {
            "source_origin_lineage": SOURCE_ORIGIN_LINEAGE_SCHEMA,
            "warranted_source_footer": "docs/schemas/warranted_source_footer.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "source_authenticity_report": "docs/schemas/source_authenticity_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "visible_source_count": len(source_origin_rows),
            "human_original_source_count": sum(
                1 for row in source_origin_rows if row["origin_class"] == "human_original"
            ),
            "synthetic_with_lineage_source_count": sum(
                1
                for row in source_origin_rows
                if row["origin_class"] == "synthetic_with_lineage"
            ),
            "synthetic_unattributed_source_count": sum(
                1
                for row in source_origin_rows
                if row["origin_class"] == "synthetic_unattributed"
            ),
            "unknown_origin_source_count": sum(
                1 for row in source_origin_rows if row["origin_class"] == "unknown"
            ),
            "direct_payout_source_count": sum(
                1
                for row in source_origin_rows
                if row["settlement_action"] == "direct_source_creator_payout"
            ),
            "lineage_settlement_source_count": sum(
                1 for row in source_origin_rows if row["lineage_settlement_allowed"]
            ),
            "origin_review_escrow_source_count": sum(
                1
                for row in source_origin_rows
                if row["settlement_action"] == "origin_review_escrow"
            ),
            "upstream_royalty_row_count": len(upstream_rows),
            "failed_check_count": len(failed),
            "synthetic_laundering_guard_supported": True,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["source_origin_lineage_hash"] = hash_payload(_hashable_report(report))
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


def validate_source_origin_lineage_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L121 source-origin lineage report."""

    errors: list[str] = []
    required = (
        "lineage_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "source_origin_rows",
        "upstream_royalty_rows",
        "footer_display",
        "checks",
        "coverage_gaps",
        "commitments",
        "privacy",
        "schemas",
        "summary",
        "source_origin_lineage_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source origin lineage field: {key}")
    if report.get("lineage_version") != SOURCE_ORIGIN_LINEAGE_VERSION:
        errors.append("source origin lineage version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source origin lineage target level is not RDLLM-L121")
    if "source_origin_lineage" not in report.get("schemas", {}):
        errors.append("missing source origin lineage schema")
    if _contains_private_fields(report):
        errors.append("source origin lineage report contains private field")
    for index, row in enumerate(report.get("source_origin_rows", [])):
        for key in (
            "label",
            "work_id",
            "chunk_id",
            "origin_class",
            "lineage_status",
            "settlement_action",
            "source_origin_row_hash",
        ):
            if key not in row:
                errors.append(f"source origin row {index} missing {key}")
        if row.get("origin_class") not in ORIGIN_CLASSES:
            errors.append(f"source origin row {index} has unsupported origin_class")
    return errors


def verify_source_origin_lineage_report(
    report: dict[str, Any],
    *,
    lineage_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L121 source-origin lineage report by replaying private inputs."""

    errors = validate_source_origin_lineage_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("source_origin_lineage_hash"):
        errors.append("source origin lineage hash is not reproducible")
    expected = make_source_origin_lineage_report(
        lineage_input,
        issuer=report.get("issuer") or DEFAULT_ISSUER,
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "source_origin_rows",
        "upstream_royalty_rows",
        "footer_display",
        "checks",
        "coverage_gaps",
        "commitments",
        "privacy",
        "schemas",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source origin lineage {key} does not match inputs")
    if expected.get("source_origin_lineage_hash") != report.get(
        "source_origin_lineage_hash"
    ):
        errors.append("source origin lineage hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("source origin lineage status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"source origin lineage check failed: {check}")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source origin lineage is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source origin lineage signature is invalid")
    return errors
