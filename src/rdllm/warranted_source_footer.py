"""Visible warrant labels for force-calibrated RDLLM source footers.

This layer turns the L119 evidence-force audit into a user-facing footer
supplement. It does not expose raw claims or source text; it publishes the
force labels, claim hashes, span prefixes, and proof handles needed to verify
that each visible claim was warranted by its cited evidence.
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

WARRANTED_SOURCE_FOOTER_VERSION = "rdllm-warranted-source-footer/v1"
WARRANTED_SOURCE_FOOTER_SCHEMA = "docs/schemas/warranted_source_footer.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L120"
MINIMUM_INPUT_LEVEL = "RDLLM-L119"
REQUIRED_AXES = ("relation", "modality", "scope", "temporal", "numeric")

DECLARED_HASH_FIELDS = (
    "warranted_source_footer_hash",
    "evidence_force_calibration_hash",
    "grounded_source_footer_hash",
    "rendered_attribution_audit_hash",
    "contract_hash",
    "report_hash",
    "receipt_hash",
    "footer_hash",
    "envelope_hash",
    "card_hash",
    "summary_hash",
    "graph_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "claim_text",
    "raw_claim",
    "source_text",
    "evidence_text",
    "quote",
    "matched_text",
    "document_text",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "payment_account",
    "bank_account",
    "account_number",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_warranted_source_footer_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L120 warranted source footer."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"warranted_source_footer_hash", "signature"}
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


def _private_strings_absent(
    report: dict[str, Any], footer_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in footer_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _artifact_bindings(footer_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "evidence_force_calibration": footer_input.get("evidence_force_calibration"),
        "grounded_source_footer": footer_input.get("grounded_source_footer"),
        "citation_footer_contract": footer_input.get("citation_footer_contract"),
        "rendered_attribution_audit": footer_input.get("rendered_attribution_audit"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(
                (artifact or {}).get("calibration_version")
                or (artifact or {}).get("footer_version")
                or (artifact or {}).get("contract_version")
                or (artifact or {}).get("report_version")
                or ""
            ),
        }
    return bindings


def _footer_sources(grounded_source_footer: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in grounded_source_footer.get("footer_rows", []):
        public = {
            "display_order": int(row.get("display_order", 0) or 0),
            "label": str(row.get("label", "")),
            "display_label": str(row.get("display_label", "")),
            "title": str(row.get("title", "")),
            "creator_id": str(row.get("creator_id", "")),
            "creator_name": str(row.get("creator_name", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash_prefix": str(row.get("content_hash_prefix", "")),
            "confidence_level": str(row.get("confidence_level", "")),
            "source_confidence_verified": bool(row.get("source_confidence_verified")),
            "source_available": bool(row.get("source_available")),
            "license_status": str(row.get("license_status", "")),
            "royalty_status": str(row.get("royalty_status", "")),
            "grounded_footer_row_hash": str(row.get("footer_row_hash", "")),
        }
        public["warranted_source_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _visible_claims(calibration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("visible_claim_key", "")): row
        for row in calibration.get("visible_footer_claim_rows", [])
    }


def _force_rows_by_hash(calibration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("claim_force_row_hash", "")): row
        for row in calibration.get("claim_force_rows", [])
    }


def _axis_summary(force_row: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for axis in force_row.get("axis_rows", []):
        public = {
            "axis": str(axis.get("axis", "")),
            "claim_force": str(axis.get("claim_force", "")),
            "evidence_force": str(axis.get("evidence_force", "")),
            "claim_rank": int(axis.get("claim_rank", 0) or 0),
            "evidence_rank": int(axis.get("evidence_rank", 0) or 0),
            "calibrated": bool(axis.get("calibrated", False)),
            "force_gap": int(axis.get("force_gap", 0) or 0),
            "axis_row_hash": str(axis.get("axis_row_hash", "")),
        }
        rows.append(public)
    return rows


def _claim_warrant_rows(calibration: dict[str, Any]) -> list[dict[str, Any]]:
    visible_by_key = _visible_claims(calibration)
    force_by_hash = _force_rows_by_hash(calibration)
    rows: list[dict[str, Any]] = []
    for coverage in calibration.get("footer_claim_coverage_rows", []):
        key = str(coverage.get("visible_claim_key", ""))
        visible = visible_by_key.get(key, {})
        matched_hashes = [
            str(item) for item in coverage.get("matched_force_row_hashes", []) if item
        ]
        force_row = next(
            (force_by_hash[item] for item in matched_hashes if item in force_by_hash),
            {},
        )
        axis_rows = _axis_summary(force_row)
        calibrated = bool(coverage.get("matched_calibrated")) and bool(
            force_row.get("calibrated", False)
        )
        footer_claim_verified = bool(coverage.get("footer_claim_verified", False))
        public = {
            "visible_claim_key": key,
            "claim_index": int(
                coverage.get("claim_index", visible.get("claim_index", 0)) or 0
            ),
            "source_label": str(
                coverage.get("source_label", visible.get("source_label", ""))
            ),
            "claim_hash": str(coverage.get("claim_hash", visible.get("claim_hash", ""))),
            "evidence_span_prefix": str(
                coverage.get(
                    "evidence_span_prefix",
                    visible.get("evidence_span_prefix", ""),
                )
            ),
            "display_anchor": str(visible.get("display_anchor", "")),
            "footer_claim_verified": footer_claim_verified,
            "covered_by_force_row": bool(coverage.get("covered_by_force_row", False)),
            "matched_claim_ids": [
                str(item) for item in coverage.get("matched_claim_ids", [])
            ],
            "matched_force_row_hashes": matched_hashes,
            "calibrated": calibrated,
            "warrant_status": "calibrated" if calibrated else "not_warranted",
            "support_score": round(float(force_row.get("support_score", 0.0) or 0.0), 8),
            "confidence": round(float(force_row.get("confidence", 0.0) or 0.0), 8),
            "footer_status": str(force_row.get("footer_status", "")),
            "settlement_action": str(force_row.get("settlement_action", "")),
            "violation_axes": [
                str(axis) for axis in force_row.get("violation_axes", [])
            ],
            "axis_rows": axis_rows,
        }
        public["display_text"] = _display_text(public)
        public["claim_warrant_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _display_text(row: dict[str, Any]) -> str:
    forces = {
        str(axis.get("axis", "")): str(axis.get("claim_force", ""))
        for axis in row.get("axis_rows", [])
    }
    return (
        f"claim {row.get('claim_index')} {row.get('display_anchor')} "
        f"warrant={row.get('warrant_status')}; "
        f"relation={forces.get('relation', 'none')}; "
        f"modality={forces.get('modality', 'none')}; "
        f"scope={forces.get('scope', 'none')}; "
        f"temporal={forces.get('temporal', 'none')}; "
        f"numeric={forces.get('numeric', 'none')}; "
        f"claim_hash={str(row.get('claim_hash', ''))[:12]}"
    )


def _footer_display(claim_warrant_rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [str(row.get("display_text", "")) for row in claim_warrant_rows]
    footer = {
        "profile": "rdllm-visible-warranted-source-footer/v1",
        "line_count": len(lines),
        "warrant_lines": lines,
        "visible_claim_key_root": hash_payload(
            [row.get("visible_claim_key", "") for row in claim_warrant_rows]
        ),
        "claim_warrant_root": hash_payload(
            [row.get("claim_warrant_row_hash", "") for row in claim_warrant_rows]
        ),
    }
    footer["footer_hash"] = hash_payload(footer)
    return footer


def _checks(
    *,
    footer_input: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    source_rows: list[dict[str, Any]],
    claim_warrant_rows: list[dict[str, Any]],
    footer_display: dict[str, Any],
) -> dict[str, bool]:
    calibration = footer_input.get("evidence_force_calibration", {})
    grounded = footer_input.get("grounded_source_footer", {})
    contract = footer_input.get("citation_footer_contract", {})
    rendered = footer_input.get("rendered_attribution_audit", {})
    visible_claim_count = int(
        calibration.get("summary", {}).get("visible_footer_claim_count", 0) or 0
    )
    public_stub = {
        "source_rows": source_rows,
        "claim_warrant_rows": claim_warrant_rows,
        "footer_display": footer_display,
    }
    return {
        "artifact_hashes_reproducible": all(
            bool(value.get("hash_reproducible")) and bool(value.get("present"))
            for value in bindings.values()
        ),
        "evidence_force_calibration_ready_l119": (
            calibration.get("summary", {}).get("status") == "ready"
            and calibration.get("summary", {}).get("target_certification_level")
            == "RDLLM-L119"
            and all(calibration.get("checks", {}).values())
        ),
        "grounded_source_footer_ready": (
            grounded.get("summary", {}).get("status") == "ready"
            and all(grounded.get("checks", {}).values())
        ),
        "citation_footer_contract_verified": (
            contract.get("summary", {}).get("status") == "verified"
        ),
        "rendered_attribution_audit_ready": (
            rendered.get("summary", {}).get("status") == "ready"
            and all(rendered.get("checks", {}).values())
        ),
        "visible_footer_claims_covered_by_l119": (
            calibration.get("checks", {}).get("all_visible_footer_claims_have_force_rows")
            is True
            and calibration.get("summary", {}).get("uncovered_visible_footer_claim_count")
            == 0
        ),
        "visible_verified_claims_force_calibrated": (
            calibration.get("checks", {}).get(
                "visible_verified_footer_claims_are_force_calibrated"
            )
            is True
            and calibration.get("summary", {}).get(
                "uncalibrated_verified_footer_claim_count"
            )
            == 0
        ),
        "warrant_rows_cover_visible_footer_claims": (
            bool(claim_warrant_rows)
            and len(claim_warrant_rows) == visible_claim_count
            and all(row["covered_by_force_row"] for row in claim_warrant_rows)
        ),
        "warrant_rows_include_required_force_axes": all(
            set(REQUIRED_AXES)
            <= {str(axis.get("axis", "")) for axis in row.get("axis_rows", [])}
            for row in claim_warrant_rows
        ),
        "verified_footer_rows_show_only_calibrated_warrants": all(
            not row["footer_claim_verified"] or row["warrant_status"] == "calibrated"
            for row in claim_warrant_rows
        ),
        "source_rows_visible_and_verified": bool(source_rows)
        and all(
            row["source_confidence_verified"]
            and row["source_available"]
            and row["confidence_level"] == "verified"
            for row in source_rows
        ),
        "footer_display_hash_reproducible": (
            hash_payload(
                {
                    key: value
                    for key, value in footer_display.items()
                    if key != "footer_hash"
                }
            )
            == footer_display.get("footer_hash")
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_stub)
            and _private_strings_absent(public_stub, footer_input)
        ),
    }


def make_warranted_source_footer(
    footer_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public footer supplement with evidence-force warrant labels."""

    created_at = created_at or now_iso()
    bindings = _artifact_bindings(footer_input)
    source_rows = _footer_sources(footer_input.get("grounded_source_footer", {}))
    claim_warrant_rows = _claim_warrant_rows(
        footer_input.get("evidence_force_calibration", {})
    )
    footer_display = _footer_display(claim_warrant_rows)
    checks = _checks(
        footer_input=footer_input,
        bindings=bindings,
        source_rows=source_rows,
        claim_warrant_rows=claim_warrant_rows,
        footer_display=footer_display,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "failed"
    report = {
        "footer_version": WARRANTED_SOURCE_FOOTER_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "policy": {
            "profile": "rdllm-visible-warrant-disclosure-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "required_axes": list(REQUIRED_AXES),
            "verified_footer_requires_visible_warrant_label": True,
            "raw_claim_text_disclosure_allowed": False,
            "raw_evidence_text_disclosure_allowed": False,
        },
        "artifact_bindings": bindings,
        "source_rows": source_rows,
        "claim_warrant_rows": claim_warrant_rows,
        "footer_display": footer_display,
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "uncovered_visible_claim_keys": [
                row["visible_claim_key"]
                for row in claim_warrant_rows
                if not row["covered_by_force_row"]
            ],
            "uncalibrated_visible_claim_keys": [
                row["visible_claim_key"]
                for row in claim_warrant_rows
                if row["footer_claim_verified"] and not row["calibrated"]
            ],
        },
        "commitments": {
            "source_row_root": hash_payload(
                [row.get("warranted_source_row_hash", "") for row in source_rows]
            ),
            "claim_warrant_root": footer_display["claim_warrant_root"],
            "footer_display_hash": footer_display["footer_hash"],
            "artifact_binding_root": hash_payload(bindings),
            "schema": WARRANTED_SOURCE_FOOTER_SCHEMA,
        },
        "privacy": {
            "footer_warrant_labels_disclosed": True,
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_claim_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "payment_account_disclosed": False,
            "public_report_uses_hashes_force_labels_scores_and_statuses": True,
        },
        "schemas": {
            "warranted_source_footer": WARRANTED_SOURCE_FOOTER_SCHEMA,
            "evidence_force_calibration": "docs/schemas/evidence_force_calibration.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "citation_footer_contract": "docs/schemas/citation_footer_contract.schema.json",
            "rendered_attribution_audit": "docs/schemas/rendered_attribution_audit.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "visible_source_count": len(source_rows),
            "visible_claim_count": len(claim_warrant_rows),
            "calibrated_visible_claim_count": sum(
                1 for row in claim_warrant_rows if row["calibrated"]
            ),
            "uncovered_visible_claim_count": sum(
                1 for row in claim_warrant_rows if not row["covered_by_force_row"]
            ),
            "uncalibrated_visible_claim_count": sum(
                1
                for row in claim_warrant_rows
                if row["footer_claim_verified"] and not row["calibrated"]
            ),
            "warrant_line_count": footer_display["line_count"],
            "failed_check_count": len(failed),
            "user_visible_warrant_labels_supported": True,
            "verified_footer_warrant_disclosure_supported": checks[
                "verified_footer_rows_show_only_calibrated_warrants"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["warranted_source_footer_hash"] = hash_payload(_hashable_report(report))
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


def validate_warranted_source_footer_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L120 warranted source footer."""

    errors: list[str] = []
    required = (
        "footer_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "source_rows",
        "claim_warrant_rows",
        "footer_display",
        "checks",
        "coverage_gaps",
        "commitments",
        "privacy",
        "schemas",
        "summary",
        "warranted_source_footer_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing warranted source footer field: {key}")
    if report.get("footer_version") != WARRANTED_SOURCE_FOOTER_VERSION:
        errors.append("warranted source footer version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("warranted source footer target level is not RDLLM-L120")
    if "warranted_source_footer" not in report.get("schemas", {}):
        errors.append("missing warranted source footer schema")
    if _contains_private_fields(report):
        errors.append("warranted source footer report contains private field")
    for index, row in enumerate(report.get("claim_warrant_rows", [])):
        for key in (
            "visible_claim_key",
            "claim_index",
            "source_label",
            "claim_hash",
            "warrant_status",
            "axis_rows",
            "display_text",
            "claim_warrant_row_hash",
        ):
            if key not in row:
                errors.append(f"claim warrant row {index} missing {key}")
    return errors


def verify_warranted_source_footer(
    report: dict[str, Any],
    *,
    footer_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L120 warranted source footer by replaying private inputs."""

    errors = validate_warranted_source_footer_shape(report)
    if hash_payload(_hashable_report(report)) != report.get(
        "warranted_source_footer_hash"
    ):
        errors.append("warranted source footer hash is not reproducible")
    expected = make_warranted_source_footer(
        footer_input,
        issuer=report.get("issuer") or DEFAULT_ISSUER,
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "source_rows",
        "claim_warrant_rows",
        "footer_display",
        "checks",
        "coverage_gaps",
        "commitments",
        "privacy",
        "schemas",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"warranted source footer {key} does not match inputs")
    if expected.get("warranted_source_footer_hash") != report.get(
        "warranted_source_footer_hash"
    ):
        errors.append("warranted source footer hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("warranted source footer status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"warranted source footer check failed: {check}")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("warranted source footer is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("warranted source footer signature is invalid")
    return errors
