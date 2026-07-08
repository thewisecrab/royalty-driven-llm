"""Verifiable citation footer rendering contracts for RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.conformance import source_labels_in_output, span_hash_prefixes_in_output
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.source_confidence import verify_source_confidence_report
from rdllm.text import stable_hash

CITATION_FOOTER_VERSION = "rdllm-citation-footer-contract/v1"
CITATION_FOOTER_SCHEMA = "docs/schemas/citation_footer_contract.schema.json"


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"contract_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in (
        "envelope_hash",
        "card_hash",
        "report_hash",
        "contract_hash",
        "receipt_hash",
    ):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _hashable_row(row: dict[str, Any], hash_field: str) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != hash_field}


def _response_boundary_hash(
    *,
    response: dict[str, Any],
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_confidence_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
) -> str:
    return hash_payload(
        {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "answer_card_hash": _declared_hash(answer_card),
            "source_verification_report_hash": _declared_hash(
                source_verification_report
            ),
            "source_confidence_report_hash": _declared_hash(
                source_confidence_report
            ),
            "creator_license_contract_hash": _declared_hash(
                creator_license_contract
            ),
        }
    )


def _license_status(source: dict[str, Any]) -> str:
    checks = source.get("checks", {})
    required = (
        checks.get("active_license_term") is True
        and checks.get("generation_allowed_by_license") is True
        and checks.get("content_hash_covered_by_license") is True
        and checks.get("attribution_duty_present") is True
    )
    return "active" if required else "blocked"


def _royalty_status(source: dict[str, Any]) -> str:
    checks = source.get("checks", {})
    return "active" if checks.get("royalty_duty_present") is True else "blocked"


def _source_rationale(
    *,
    source: dict[str, Any],
    supported_claim_count: int,
    license_status: str,
    royalty_status: str,
) -> dict[str, Any]:
    checks = source.get("checks", {})
    identity_verified = all(
        checks.get(key) is True
        for key in (
            "source_materialized",
            "registered_chunk_found",
            "content_hash_matches_registry",
            "content_hash_reproducible",
            "metadata_matches_registry",
        )
    )
    claim_supported = supported_claim_count > 0
    rights_active = license_status == "active"
    royalty_active = royalty_status == "active"
    if identity_verified and claim_supported and rights_active and royalty_active:
        reason_code = "verified_claim_support_identity_rights_royalty"
    elif claim_supported and identity_verified:
        reason_code = "verified_claim_support_with_policy_gap"
    elif claim_supported:
        reason_code = "claim_support_needs_verification"
    else:
        reason_code = "source_listed_for_review"
    public = {
        "reason_code": reason_code,
        "claim_support": "supported_claims_present" if claim_supported else "no_supported_claims",
        "identity": "hash_metadata_verified" if identity_verified else "identity_needs_review",
        "rights": "license_active" if rights_active else "license_blocked",
        "royalty": "royalty_active" if royalty_active else "royalty_blocked",
        "confidence_level": str(source.get("confidence_level", "")),
        "confidence_score": float(source.get("confidence_score", 0.0) or 0.0),
        "supported_claim_count": supported_claim_count,
        "source_confidence_hash": str(source.get("source_confidence_hash", "")),
    }
    public["source_rationale_hash"] = hash_payload(public)
    return public


def _source_display_rows(source_confidence_report: dict[str, Any]) -> list[dict[str, Any]]:
    footer_rows = {
        str(row.get("label", "")): row
        for row in source_confidence_report.get("footer", {}).get("rows", [])
    }
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(source_confidence_report.get("sources", []), start=1):
        label = str(source.get("label", ""))
        footer_row = footer_rows.get(label, {})
        license_status = _license_status(source)
        royalty_status = _royalty_status(source)
        supported_claim_count = int(footer_row.get("supported_claim_count", 0) or 0)
        source_rationale = _source_rationale(
            source=source,
            supported_claim_count=supported_claim_count,
            license_status=license_status,
            royalty_status=royalty_status,
        )
        display_text = (
            f"[{label}] {source.get('title', '')} - {source.get('creator_name', '')}; "
            f"confidence={source.get('confidence_level', '')}; "
            f"claims={supported_claim_count}; "
            f"why={source_rationale['reason_code']}; "
            f"hash={source.get('content_hash_prefix', '')}; "
            f"license={license_status}; royalty={royalty_status}; "
            f"uri={source.get('source_uri', '')}"
        )
        row = {
            "display_order": index,
            "label": label,
            "display_label": f"[{label}]",
            "title": source.get("title", ""),
            "creator_id": source.get("creator_id", ""),
            "creator_name": source.get("creator_name", ""),
            "work_id": source.get("work_id", ""),
            "chunk_id": source.get("chunk_id", ""),
            "source_uri": source.get("source_uri", ""),
            "content_hash_prefix": source.get("content_hash_prefix", ""),
            "confidence_level": source.get("confidence_level", ""),
            "confidence_score": source.get("confidence_score", 0.0),
            "supported_claim_count": supported_claim_count,
            "license_status": license_status,
            "royalty_status": royalty_status,
            "source_rationale": source_rationale,
            "display_text": display_text,
            "source_confidence_hash": source.get("source_confidence_hash", ""),
            "footer_row_hash": footer_row.get("footer_row_hash", ""),
        }
        row["display_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _claim_display_rows(source_confidence_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim in source_confidence_report.get("claims", []):
        source_label = str(claim.get("source_label", ""))
        span_prefix = str(claim.get("evidence_span_prefix", ""))
        row = {
            "claim_index": int(claim.get("claim_index", 0) or 0),
            "claim_hash": claim.get("claim_hash", ""),
            "source_label": source_label,
            "display_label": f"[{source_label}]",
            "evidence_span_prefix": span_prefix,
            "display_anchor": f"[{source_label}:span={span_prefix}]",
            "support_score": claim.get("support_score", 0.0),
            "confidence_level": claim.get("confidence_level", ""),
            "confidence_score": claim.get("confidence_score", 0.0),
            "claim_confidence_hash": claim.get("claim_confidence_hash", ""),
        }
        row["claim_display_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _rendered_footer(source_rows: list[dict[str, Any]], claim_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_lines = [str(row["display_text"]) for row in source_rows]
    claim_lines = [
        (
            f"claim {row['claim_index']} -> {row['display_label']} "
            f"span={row['evidence_span_prefix']}; confidence={row['confidence_level']}"
        )
        for row in claim_rows
    ]
    footer_text = "\n".join(source_lines + claim_lines)
    footer = {
        "profile": "rdllm-verifiable-citation-footer/v1",
        "source_lines": source_lines,
        "claim_lines": claim_lines,
        "footer_text": footer_text,
        "source_label_order": [row["label"] for row in source_rows],
        "claim_span_prefixes": [row["evidence_span_prefix"] for row in claim_rows],
        "source_line_count": len(source_lines),
        "claim_line_count": len(claim_lines),
    }
    footer["footer_hash"] = hash_payload(footer)
    return footer


def _verification_summary(
    *,
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    rendered_footer: dict[str, Any],
    signing_secret: str | None,
) -> dict[str, bool]:
    response = response_envelope.get("response", {})
    rendered_output = str(response.get("rendered_output", ""))
    labels = source_labels_in_output(rendered_output)
    span_prefixes = span_hash_prefixes_in_output(rendered_output)
    artifacts = response_envelope.get("embedded_artifacts", {})
    answer_card = artifacts.get("answer_provenance_card", {})
    source_report = artifacts.get("source_verification_report", {})
    source_confidence_errors = (
        verify_source_confidence_report(
            source_confidence_report,
            answer_card=answer_card,
            source_verification_report=source_report,
            creator_license_contract=creator_license_contract,
            signing_secret=signing_secret,
        )
        if source_confidence_report and creator_license_contract
        else ["source confidence report or creator license contract missing"]
    )
    display_text = canonical_json(
        {
            "source_rows": source_rows,
            "claim_rows": claim_rows,
            "rendered_footer": rendered_footer,
        }
    )
    return {
        "rendered_output_hash_matches_response": (
            response.get("rendered_output_hash") == stable_hash(rendered_output)
        ),
        "source_labels_match_response": response.get("source_labels") == labels,
        "claim_span_prefixes_match_response": (
            response.get("claim_span_prefixes") == span_prefixes
        ),
        "footer_sources_match_rendered_output": (
            rendered_footer.get("source_label_order") == labels
        ),
        "footer_claim_spans_cover_rendered_output": all(
            prefix in rendered_footer.get("claim_span_prefixes", [])
            for prefix in span_prefixes
        ),
        "source_confidence_report_verified": not source_confidence_errors,
        "all_display_sources_verified": bool(source_rows)
        and all(row.get("confidence_level") == "verified" for row in source_rows),
        "all_display_claims_verified": bool(claim_rows)
        and all(row.get("confidence_level") == "verified" for row in claim_rows),
        "all_display_sources_have_active_license": all(
            row.get("license_status") == "active" for row in source_rows
        ),
        "all_display_sources_have_active_royalty": all(
            row.get("royalty_status") == "active" for row in source_rows
        ),
        "display_row_hashes_reproducible": all(
            hash_payload(_hashable_row(row, "display_row_hash"))
            == row.get("display_row_hash")
            for row in source_rows
        ),
        "claim_display_hashes_reproducible": all(
            hash_payload(_hashable_row(row, "claim_display_hash"))
            == row.get("claim_display_hash")
            for row in claim_rows
        ),
        "footer_hash_reproducible": (
            hash_payload(_hashable_row(rendered_footer, "footer_hash"))
            == rendered_footer.get("footer_hash")
        ),
        "no_private_answer_or_source_text_disclosed": (
            "Royalty-aware answer:" not in display_text
            and '"evidence_text"' not in display_text
            and '"quote"' not in display_text
            and '"prompt"' not in display_text
        ),
    }


def make_citation_footer_contract(
    *,
    response_envelope: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a client-renderable source footer bound to public response proofs."""

    response = response_envelope.get("response", {})
    artifacts = response_envelope.get("embedded_artifacts", {})
    answer_card = artifacts.get("answer_provenance_card", {})
    source_report = artifacts.get("source_verification_report", {})
    source_confidence_report = artifacts.get("source_confidence_report", {})
    creator_license_contract = artifacts.get("creator_license_contract", {})
    source_rows = _source_display_rows(source_confidence_report)
    claim_rows = _claim_display_rows(source_confidence_report)
    rendered_footer = _rendered_footer(source_rows, claim_rows)
    verification = _verification_summary(
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        creator_license_contract=creator_license_contract,
        source_rows=source_rows,
        claim_rows=claim_rows,
        rendered_footer=rendered_footer,
        signing_secret=signing_secret,
    )
    source_scores = [float(row.get("confidence_score", 0.0) or 0.0) for row in source_rows]
    claim_scores = [float(row.get("confidence_score", 0.0) or 0.0) for row in claim_rows]
    contract = {
        "contract_version": CITATION_FOOTER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "response_boundary_hash": _response_boundary_hash(
                response=response,
                answer_card=answer_card,
                source_verification_report=source_report,
                source_confidence_report=source_confidence_report,
                creator_license_contract=creator_license_contract,
            ),
            "answer_card_hash": _declared_hash(answer_card),
            "source_verification_report_hash": _declared_hash(source_report),
            "source_confidence_report_hash": _declared_hash(source_confidence_report),
            "creator_license_contract_hash": _declared_hash(creator_license_contract),
        },
        "display_profile": {
            "profile": "rdllm-verifiable-citation-footer/v1",
            "render_location": "answer_footer",
            "required_source_label_pattern": "[S#]",
            "required_claim_anchor_pattern": "[S#:span=<12 hex chars>]",
            "client_must_render_source_confidence": True,
            "client_must_render_license_and_royalty_status": True,
            "client_must_preserve_display_order": True,
        },
        "sources": source_rows,
        "claims": claim_rows,
        "rendered_footer": rendered_footer,
        "verification": verification,
        "commitments": {
            "response_boundary_hash": _response_boundary_hash(
                response=response,
                answer_card=answer_card,
                source_verification_report=source_report,
                source_confidence_report=source_confidence_report,
                creator_license_contract=creator_license_contract,
            ),
            "source_display_root": hash_payload(source_rows),
            "claim_display_root": hash_payload(claim_rows),
            "rendered_footer_hash": rendered_footer.get("footer_hash", ""),
            "source_confidence_report_hash": _declared_hash(source_confidence_report),
            "creator_license_contract_hash": _declared_hash(creator_license_contract),
        },
        "summary": {
            "status": "verified" if all(verification.values()) else "failed",
            "source_count": len(source_rows),
            "claim_count": len(claim_rows),
            "verified_source_count": sum(
                1 for row in source_rows if row.get("confidence_level") == "verified"
            ),
            "verified_claim_count": sum(
                1 for row in claim_rows if row.get("confidence_level") == "verified"
            ),
            "minimum_source_confidence": min(source_scores) if source_scores else 1.0,
            "minimum_claim_confidence": min(claim_scores) if claim_scores else 1.0,
            "footer_line_count": rendered_footer.get("source_line_count", 0)
            + rendered_footer.get("claim_line_count", 0),
            "display_contract_verification_supported": True,
            "source_footer_rendering_required": True,
        },
        "schemas": {
            "citation_footer_contract": CITATION_FOOTER_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_confidence_report": "docs/schemas/source_confidence_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
        },
        "privacy": {
            "footer_text_disclosed": True,
            "answer_text_disclosed": False,
            "prompt_text_disclosed": False,
            "source_text_disclosed": False,
            "source_quote_text_disclosed": False,
            "claim_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "payout_account_disclosed": False,
            "contract_uses_hashes_metadata_scores_and_statuses": True,
        },
    }
    contract["contract_hash"] = hash_payload(_hashable_contract(contract))
    contract["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_contract(contract), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return contract


def validate_citation_footer_contract_shape(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "contract_version",
        "issuer",
        "created_at",
        "event",
        "display_profile",
        "sources",
        "claims",
        "rendered_footer",
        "verification",
        "commitments",
        "summary",
        "schemas",
        "privacy",
        "contract_hash",
        "signature",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing citation footer contract field: {key}")
    if errors:
        return errors
    if contract.get("contract_version") != CITATION_FOOTER_VERSION:
        errors.append("citation footer contract version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "response_boundary_hash",
        "answer_card_hash",
        "source_verification_report_hash",
        "source_confidence_report_hash",
        "creator_license_contract_hash",
    ):
        if key not in contract.get("event", {}):
            errors.append(f"missing citation footer event field: {key}")
    for source in contract.get("sources", []):
        for key in (
            "display_order",
            "label",
            "display_label",
            "title",
            "creator_name",
            "work_id",
            "source_uri",
            "confidence_level",
            "license_status",
            "royalty_status",
            "source_rationale",
            "display_text",
            "display_row_hash",
        ):
            if key not in source:
                errors.append(f"missing citation footer source field: {key}")
    for claim in contract.get("claims", []):
        for key in (
            "claim_index",
            "source_label",
            "display_anchor",
            "evidence_span_prefix",
            "confidence_level",
            "claim_display_hash",
        ):
            if key not in claim:
                errors.append(f"missing citation footer claim field: {key}")
    if "citation_footer_contract" not in contract.get("schemas", {}):
        errors.append("missing citation footer schema")
    return errors


def verify_citation_footer_contract(
    contract: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a footer rendering contract against public response artifacts."""

    errors = validate_citation_footer_contract_shape(contract)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_contract(contract))
    if expected_hash != contract.get("contract_hash"):
        errors.append("citation footer contract hash is not reproducible")

    expected = make_citation_footer_contract(
        response_envelope=response_envelope,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "display_profile",
        "sources",
        "claims",
        "rendered_footer",
        "verification",
        "commitments",
        "summary",
        "schemas",
        "privacy",
    ):
        if expected.get(key) != contract.get(key):
            errors.append(f"citation footer contract {key} does not match response proofs")
    if expected.get("contract_hash") != contract.get("contract_hash"):
        errors.append("citation footer contract hash does not match response proofs")

    if contract.get("summary", {}).get("status") != "verified":
        errors.append("citation footer contract status is not verified")
    if not all(bool(value) for value in contract.get("verification", {}).values()):
        errors.append("citation footer contract verification checks are not all true")
    if contract.get("privacy", {}).get("answer_text_disclosed") is not False:
        errors.append("citation footer contract must not disclose answer text")
    if contract.get("privacy", {}).get("source_text_disclosed") is not False:
        errors.append("citation footer contract must not disclose source text")

    rendered = canonical_json(contract)
    for forbidden in ('"evidence_text"', '"quote"', '"prompt"', "Royalty-aware answer:"):
        if forbidden in rendered:
            errors.append("citation footer contract leaks private text")
            break

    signature = contract.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("citation footer contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("citation footer contract signature is invalid")
    return errors
