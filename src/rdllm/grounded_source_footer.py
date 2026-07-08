"""User-facing grounded source footer receipts.

This layer turns the public proof stack into a compact answer-footer object.  It
does not decide attribution by itself; it proves that the footer a user sees is
backed by source confidence, availability, exact region binding, citation
reliance, and license-transaction evidence.
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

GROUNDED_SOURCE_FOOTER_VERSION = "rdllm-grounded-source-footer/v1"
GROUNDED_SOURCE_FOOTER_SCHEMA = (
    "docs/schemas/grounded_source_footer.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L102"

DECLARED_HASH_FIELDS = (
    "grounded_source_footer_hash",
    "citation_reliance_receipt_hash",
    "license_transaction_receipt_hash",
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
    "raw_license_token",
    "license_server_secret",
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


def load_grounded_source_footer_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a grounded source footer receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"grounded_source_footer_hash", "signature"}
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


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "citation_footer_contract": receipt_input.get("citation_footer_contract"),
        "rendered_attribution_audit": receipt_input.get("rendered_attribution_audit"),
        "source_confidence_report": receipt_input.get("source_confidence_report"),
        "source_availability_report": receipt_input.get("source_availability_report"),
        "evidence_region_binding_report": receipt_input.get(
            "evidence_region_binding_report"
        ),
        "citation_reliance_receipt": receipt_input.get("citation_reliance_receipt"),
        "license_transaction_receipt": receipt_input.get("license_transaction_receipt"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(
            artifact
        )
    return bindings


def _by_label(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("label", row.get("source_label", ""))): row for row in rows}


def _source_confidence_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("sources", [])
    by_label = _by_label(rows)
    for row in report.get("footer", {}).get("rows", []):
        label = str(row.get("label", ""))
        if label and label not in by_label:
            by_label[label] = row
    return by_label


def _availability_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _by_label(report.get("sources", []))


def _reliance_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _by_label(report.get("source_reliance_rows", []))


def _license_coverage_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _by_label(report.get("coverage_rows", []))


def _region_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {}
    for row in report.get("source_region_rows", []):
        region_id = str(row.get("region_id", ""))
        if region_id:
            rows[region_id] = row
    return rows


def _claim_region_rows(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = {}
    for row in report.get("claim_region_rows", []):
        key = (str(row.get("source_label", "")), str(row.get("evidence_span_prefix", "")))
        rows[key] = row
    return rows


def _rendered_audit_labels(report: dict[str, Any]) -> set[str]:
    parsed = report.get("parsed_markdown", {})
    return {
        str(row.get("label", row.get("source_label", "")))
        for row in parsed.get("source_footer_rows", [])
        if row.get("label") or row.get("source_label")
    }


def _rendered_claim_keys(report: dict[str, Any]) -> set[tuple[str, str]]:
    parsed = report.get("parsed_markdown", {})
    return {
        (
            str(row.get("source_label", "")),
            str(row.get("evidence_span_prefix", "")),
        )
        for row in parsed.get("claim_evidence_rows", [])
        if row.get("source_label") and row.get("evidence_span_prefix")
    }


def _source_rationale(
    *,
    source: dict[str, Any],
    confidence_row: dict[str, Any],
    availability_row: dict[str, Any],
    reliance_row: dict[str, Any],
    license_row: dict[str, Any],
    supported_claim_count: int,
) -> dict[str, Any]:
    source_confidence_verified = bool(
        confidence_row
        and confidence_row.get("confidence_level") == "verified"
        and bool(confidence_row.get("checks"))
        and all(confidence_row.get("checks", {}).values())
    )
    source_available = bool(
        availability_row
        and availability_row.get("content_hash_matches_registry", False)
        and (
            availability_row.get("inspectable", False)
            or availability_row.get("reachable", False)
            or availability_row.get("archived", False)
        )
    )
    claim_span_coverage = bool(
        availability_row and availability_row.get("claim_span_coverage", False)
    )
    reliance_covered = bool(
        reliance_row and reliance_row.get("covered_for_faithful_reliance", False)
    )
    license_covered = bool(
        license_row and license_row.get("covered_for_license_transaction", False)
    )
    direct_settlement = (
        source.get("royalty_status") == "active"
        and license_row.get("direct_settlement", True) is not False
        and not license_row.get("escrowed", False)
    )
    if (
        source_confidence_verified
        and source_available
        and claim_span_coverage
        and reliance_covered
        and license_covered
        and supported_claim_count > 0
    ):
        reason_code = "verified_claim_support_identity_reliance_license"
    elif supported_claim_count > 0:
        reason_code = "claim_support_visible_but_verification_incomplete"
    else:
        reason_code = "source_listed_for_review"
    rationale = {
        "reason_code": reason_code,
        "claim_support": "supported_claims_present" if supported_claim_count > 0 else "no_supported_claims",
        "source_identity": "verified" if source_confidence_verified else "needs_review",
        "source_availability": "inspectable" if source_available else "unavailable",
        "evidence_span_coverage": "covered" if claim_span_coverage else "missing",
        "faithful_reliance": "covered" if reliance_covered else "missing",
        "license_transaction": "covered" if license_covered else "missing",
        "settlement": "direct" if direct_settlement else "escrow_or_hold",
        "confidence_level": str(
            confidence_row.get("confidence_level", source.get("confidence_level", ""))
        ),
        "confidence_score": float(
            confidence_row.get("confidence_score", source.get("confidence_score", 0))
            or 0
        ),
        "supported_claim_count": supported_claim_count,
        "content_hash_prefix": str(
            source.get(
                "content_hash_prefix",
                confidence_row.get("content_hash_prefix", ""),
            )
        ),
    }
    rationale["source_rationale_hash"] = hash_payload(rationale)
    return rationale


def _footer_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    contract = receipt_input.get("citation_footer_contract", {})
    confidence = _source_confidence_by_label(
        receipt_input.get("source_confidence_report", {})
    )
    availability = _availability_by_label(
        receipt_input.get("source_availability_report", {})
    )
    reliance = _reliance_by_label(receipt_input.get("citation_reliance_receipt", {}))
    license_coverage = _license_coverage_by_label(
        receipt_input.get("license_transaction_receipt", {})
    )
    rendered_labels = _rendered_audit_labels(
        receipt_input.get("rendered_attribution_audit", {})
    )

    rows = []
    for index, source in enumerate(contract.get("sources", []), start=1):
        label = str(source.get("label", ""))
        confidence_row = confidence.get(label, {})
        availability_row = availability.get(label, {})
        reliance_row = reliance.get(label, {})
        license_row = license_coverage.get(label, {})
        supported_claim_count = int(
            source.get(
                "supported_claim_count",
                confidence_row.get("supported_claim_count", 0),
            )
            or 0
        )
        source_rationale = _source_rationale(
            source=source,
            confidence_row=confidence_row,
            availability_row=availability_row,
            reliance_row=reliance_row,
            license_row=license_row,
            supported_claim_count=supported_claim_count,
        )
        public = {
            "display_order": int(source.get("display_order", index)),
            "label": label,
            "display_label": str(source.get("display_label", f"[{label}]")),
            "title": str(source.get("title", "")),
            "creator_id": str(source.get("creator_id", confidence_row.get("creator_id", ""))),
            "creator_name": str(
                source.get("creator_name", confidence_row.get("creator_name", ""))
            ),
            "work_id": str(source.get("work_id", confidence_row.get("work_id", ""))),
            "chunk_id": str(source.get("chunk_id", confidence_row.get("chunk_id", ""))),
            "source_uri": str(
                source.get("source_uri", confidence_row.get("source_uri", ""))
            ),
            "content_hash_prefix": str(
                source.get(
                    "content_hash_prefix",
                    confidence_row.get("content_hash_prefix", ""),
                )
            ),
            "confidence_level": str(
                confidence_row.get(
                    "confidence_level", source.get("confidence_level", "")
                )
            ),
            "confidence_score": float(
                confidence_row.get("confidence_score", source.get("confidence_score", 0))
                or 0
            ),
            "supported_claim_count": supported_claim_count,
            "license_status": str(source.get("license_status", "")),
            "royalty_status": str(source.get("royalty_status", "")),
            "source_rationale": source_rationale,
            "source_rationale_hash": source_rationale["source_rationale_hash"],
            "rendered_in_footer": label in rendered_labels,
            "source_confidence_verified": bool(
                confidence_row
                and confidence_row.get("confidence_level") == "verified"
                and bool(confidence_row.get("checks"))
                and all(confidence_row.get("checks", {}).values())
            ),
            "source_available": bool(
                availability_row
                and availability_row.get("content_hash_matches_registry", False)
                and (
                    availability_row.get("inspectable", False)
                    or availability_row.get("reachable", False)
                    or availability_row.get("archived", False)
                )
            ),
            "claim_span_coverage": bool(
                availability_row and availability_row.get("claim_span_coverage", False)
            ),
            "citation_reliance_covered": bool(
                reliance_row and reliance_row.get("covered_for_faithful_reliance", False)
            ),
            "license_transaction_covered": bool(
                license_row and license_row.get("covered_for_license_transaction", False)
            ),
            "selected_license_transaction_id": str(
                license_row.get("selected_transaction_id", "")
            ),
            "availability_row_hash": str(availability_row.get("availability_row_hash", "")),
            "source_confidence_hash": str(
                confidence_row.get("source_confidence_hash", "")
            ),
            "source_reliance_row_hash": str(
                reliance_row.get("source_reliance_row_hash", "")
            ),
            "license_transaction_coverage_row_hash": str(
                license_row.get("coverage_row_hash", "")
            ),
        }
        public["footer_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _claim_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    contract = receipt_input.get("citation_footer_contract", {})
    claim_region = _claim_region_rows(
        receipt_input.get("evidence_region_binding_report", {})
    )
    region_rows = _region_rows(receipt_input.get("evidence_region_binding_report", {}))
    rendered_claims = _rendered_claim_keys(
        receipt_input.get("rendered_attribution_audit", {})
    )
    rows = []
    for claim in contract.get("claims", []):
        label = str(claim.get("source_label", ""))
        span_prefix = str(claim.get("evidence_span_prefix", ""))
        region_link = claim_region.get((label, span_prefix), {})
        region = region_rows.get(str(region_link.get("region_id", "")), {})
        public = {
            "claim_index": int(claim.get("claim_index", 0) or 0),
            "claim_hash": str(claim.get("claim_hash", "")),
            "source_label": label,
            "display_anchor": str(claim.get("display_anchor", "")),
            "evidence_span_prefix": span_prefix,
            "confidence_level": str(claim.get("confidence_level", "")),
            "confidence_score": float(claim.get("confidence_score", 0) or 0),
            "rendered_claim_evidence_present": (label, span_prefix) in rendered_claims,
            "region_id": str(region_link.get("region_id", "")),
            "region_verified": bool(region_link.get("verified", False)),
            "region_type": str(region.get("region_type", "")),
            "page": int(region.get("page", 0) or 0),
            "line_start": int(region.get("line_start", 0) or 0),
            "line_end": int(region.get("line_end", 0) or 0),
            "start_char": int(region.get("start_char", 0) or 0),
            "end_char": int(region.get("end_char", 0) or 0),
            "public_location": bool(region.get("public_location", False)),
            "location_hash": str(region.get("location_hash", "")),
            "region_hash": str(region_link.get("region_hash", region.get("region_hash", ""))),
        }
        public["claim_footer_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _proof_rows(
    artifact_bindings: dict[str, Any],
    footer_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for row in footer_rows:
        claim_count = sum(1 for claim in claim_rows if claim["source_label"] == row["label"])
        public = {
            "label": row["label"],
            "work_id": row["work_id"],
            "source_uri": row["source_uri"],
            "claim_count": claim_count,
            "proof_hashes": {
                "citation_footer_contract_hash": artifact_bindings.get(
                    "citation_footer_contract_hash", ""
                ),
                "rendered_attribution_audit_hash": artifact_bindings.get(
                    "rendered_attribution_audit_hash", ""
                ),
                "source_confidence_report_hash": artifact_bindings.get(
                    "source_confidence_report_hash", ""
                ),
                "source_availability_report_hash": artifact_bindings.get(
                    "source_availability_report_hash", ""
                ),
                "evidence_region_binding_report_hash": artifact_bindings.get(
                    "evidence_region_binding_report_hash", ""
                ),
                "citation_reliance_receipt_hash": artifact_bindings.get(
                    "citation_reliance_receipt_hash", ""
                ),
                "license_transaction_receipt_hash": artifact_bindings.get(
                    "license_transaction_receipt_hash", ""
                ),
            },
            "verification_endpoint": "/v1/rdllm/grounded-source-footers",
            "well_known_path": "/.well-known/rdllm/grounded-source-footer.json",
            "verifier_command": "verify-grounded-source-footer",
        }
        public["proof_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _checks(
    *,
    receipt_input: dict[str, Any],
    artifact_bindings: dict[str, Any],
    footer_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    proof_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    source_confidence = receipt_input.get("source_confidence_report", {})
    rendered_audit = receipt_input.get("rendered_attribution_audit", {})
    region_report = receipt_input.get("evidence_region_binding_report", {})
    footer_labels = {row["label"] for row in footer_rows}
    claim_labels = {row["source_label"] for row in claim_rows}
    public_report = {
        "footer_rows": footer_rows,
        "claim_rows": claim_rows,
        "proof_rows": proof_rows,
    }
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "visible_footer_source_count_positive": bool(footer_rows),
        "rendered_footer_matches_contract": all(
            row["rendered_in_footer"] for row in footer_rows
        )
        and rendered_audit.get("summary", {}).get("status") == "ready",
        "source_confidence_verified": (
            source_confidence.get("summary", {}).get("hallucination_issue_count", 0)
            == 0
            and all(row["source_confidence_verified"] for row in footer_rows)
        ),
        "source_availability_inspectable": all(
            row["source_available"] and row["claim_span_coverage"]
            for row in footer_rows
        ),
        "claim_regions_publicly_bound": (
            bool(claim_rows)
            and all(
                row["region_verified"]
                and row["public_location"]
                and bool(row["location_hash"])
                and row["rendered_claim_evidence_present"]
                for row in claim_rows
            )
            and region_report.get("summary", {}).get("status") == "ready"
        ),
        "footer_claims_have_source_rows": claim_labels.issubset(footer_labels),
        "footer_rows_have_claims": all(
            any(claim["source_label"] == row["label"] for claim in claim_rows)
            and row["supported_claim_count"] > 0
            for row in footer_rows
        ),
        "citation_reliance_covers_visible_sources": all(
            row["citation_reliance_covered"] for row in footer_rows
        ),
        "license_transactions_cover_visible_sources": all(
            row["license_transaction_covered"] for row in footer_rows
        ),
        "footer_rows_explain_source_selection": bool(footer_rows)
        and all(
            row.get("source_rationale", {}).get("reason_code")
            and row.get("source_rationale_hash")
            == row.get("source_rationale", {}).get("source_rationale_hash")
            for row in footer_rows
        ),
        "proof_handles_present": all(
            all(value for value in row["proof_hashes"].values()) for row in proof_rows
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, receipt_input)
        ),
    }


def make_grounded_source_footer(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a compact user-facing grounded source footer receipt."""

    artifact_bindings = _artifact_bindings(receipt_input)
    footer_rows = _footer_rows(receipt_input)
    claim_rows = _claim_rows(receipt_input)
    proof_rows = _proof_rows(artifact_bindings, footer_rows, claim_rows)
    checks = _checks(
        receipt_input=receipt_input,
        artifact_bindings=artifact_bindings,
        footer_rows=footer_rows,
        claim_rows=claim_rows,
        proof_rows=proof_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    footer_contract = receipt_input.get("citation_footer_contract", {})
    rendered_footer = footer_contract.get("rendered_footer", {})
    receipt = {
        "version": GROUNDED_SOURCE_FOOTER_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(receipt_input.get("case_id", "case:grounded-source-footer")),
            "status": status,
        },
        "artifact_bindings": artifact_bindings,
        "footer_display": {
            "profile": str(rendered_footer.get("profile", "")),
            "footer_hash": str(rendered_footer.get("footer_hash", "")),
            "source_line_count": int(rendered_footer.get("source_line_count", 0) or 0),
            "claim_line_count": int(rendered_footer.get("claim_line_count", 0) or 0),
            "source_label_order": [
                str(label) for label in rendered_footer.get("source_label_order", [])
            ],
        },
        "footer_rows": footer_rows,
        "claim_rows": claim_rows,
        "proof_rows": proof_rows,
        "checks": checks,
        "privacy": {
            "footer_text_disclosed": False,
            "prompt_disclosed": False,
            "output_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_proof_handles": True,
        },
        "schemas": {
            "grounded_source_footer": GROUNDED_SOURCE_FOOTER_SCHEMA,
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
            "source_confidence_report": "docs/schemas/source_confidence_report.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "evidence_region_binding_report": "docs/schemas/evidence_region_binding_report.schema.json",
            "citation_reliance_receipt": "docs/schemas/citation_reliance_receipt.schema.json",
            "license_transaction_receipt": "docs/schemas/license_transaction_receipt.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "visible_source_count": len(footer_rows),
            "claim_row_count": len(claim_rows),
            "proof_row_count": len(proof_rows),
            "verified_source_count": sum(
                1
                for row in footer_rows
                if row["source_confidence_verified"]
                and row["source_available"]
                and row["citation_reliance_covered"]
                and row["license_transaction_covered"]
            ),
            "public_region_bound_claim_count": sum(
                1 for row in claim_rows if row["region_verified"] and row["public_location"]
            ),
            "failed_check_count": len(failed),
            "user_grounded_footer_supported": True,
            "footer_hallucination_resistance_supported": checks[
                "source_confidence_verified"
            ],
            "license_aware_footer_supported": checks[
                "license_transactions_cover_visible_sources"
            ],
            "source_selection_rationale_supported": checks[
                "footer_rows_explain_source_selection"
            ],
            "source_rationale_count": sum(
                1 for row in footer_rows if row.get("source_rationale", {}).get("reason_code")
            ),
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    receipt["grounded_source_footer_hash"] = hash_payload(_hashable_report(receipt))
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


def validate_grounded_source_footer_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "artifact_bindings",
        "footer_display",
        "footer_rows",
        "claim_rows",
        "proof_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "grounded_source_footer_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing grounded source footer field: {key}")
    if receipt.get("version") != GROUNDED_SOURCE_FOOTER_VERSION:
        errors.append("grounded source footer version is unsupported")
    if "grounded_source_footer" not in receipt.get("schemas", {}):
        errors.append("missing grounded source footer schema")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("grounded source footer target level is not RDLLM-L102")
    for index, row in enumerate(receipt.get("footer_rows", [])):
        for key in (
            "label",
            "source_uri",
            "confidence_level",
            "source_confidence_verified",
            "source_available",
            "citation_reliance_covered",
            "license_transaction_covered",
            "source_rationale",
            "source_rationale_hash",
            "footer_row_hash",
        ):
            if key not in row:
                errors.append(f"grounded source footer row {index} missing {key}")
    for index, row in enumerate(receipt.get("claim_rows", [])):
        for key in (
            "claim_index",
            "source_label",
            "evidence_span_prefix",
            "region_verified",
            "public_location",
            "claim_footer_row_hash",
        ):
            if key not in row:
                errors.append(f"grounded source footer claim row {index} missing {key}")
    return errors


def verify_grounded_source_footer(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a grounded source footer receipt by replaying private inputs."""

    errors = validate_grounded_source_footer_shape(receipt)
    expected = make_grounded_source_footer(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    if receipt.get("grounded_source_footer_hash") != expected.get(
        "grounded_source_footer_hash"
    ):
        errors.append("grounded source footer hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("grounded source footer signature mismatch")
    if receipt.get("checks") != expected.get("checks"):
        errors.append("grounded source footer checks mismatch")
    if receipt.get("summary") != expected.get("summary"):
        errors.append("grounded source footer summary mismatch")
    if receipt.get("footer_rows") != expected.get("footer_rows"):
        errors.append("grounded source footer rows mismatch")
    if receipt.get("claim_rows") != expected.get("claim_rows"):
        errors.append("grounded source footer claim rows mismatch")
    if receipt.get("proof_rows") != expected.get("proof_rows"):
        errors.append("grounded source footer proof rows mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("grounded source footer has failing checks")
    return errors
