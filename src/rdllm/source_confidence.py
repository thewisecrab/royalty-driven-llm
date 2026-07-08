"""Public source-confidence reports for RDLLM answer footers."""

from __future__ import annotations

from typing import Any

from rdllm.license_contract import verify_creator_license_contract_public
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

SOURCE_CONFIDENCE_VERSION = "rdllm-source-confidence-report/v1"
SOURCE_CONFIDENCE_SCHEMA = "docs/schemas/source_confidence_report.schema.json"
SUPPORT_SCORE_FLOOR = 0.75


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in ("card_hash", "report_hash", "contract_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _hash_reproducible(artifact: dict[str, Any], declared_field: str) -> bool:
    declared = artifact.get(declared_field, "")
    if not declared:
        return False
    return hash_payload(
        {key: value for key, value in artifact.items() if key not in {declared_field, "signature"}}
    ) == declared


def _contract_terms_by_work(contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not contract:
        return {}
    return {
        str(term.get("work_id", "")): term
        for term in contract.get("terms", [])
        if term.get("work_id")
    }


def _score(checks: dict[str, bool]) -> float:
    if not checks:
        return 0.0
    return round(sum(1 for value in checks.values() if value) / len(checks), 8)


def _level(score: float, *, all_required: bool) -> str:
    if all_required and score == 1.0:
        return "verified"
    if score >= 0.75:
        return "warning"
    return "failed"


def _source_rows(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    creator_license_contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    source_report_by_label = {
        str(source.get("label", "")): source
        for source in source_verification_report.get("sources", [])
    }
    terms_by_work = _contract_terms_by_work(creator_license_contract)
    footer_labels = set(answer_card.get("footer_checks", {}).get("source_labels", []))
    rows: list[dict[str, Any]] = []
    for source in answer_card.get("sources", []):
        label = str(source.get("label", ""))
        report_source = source_report_by_label.get(label, {})
        term = terms_by_work.get(str(source.get("work_id", "")), {})
        checks = {
            "source_label_visible_in_footer": label in footer_labels,
            "source_materialized": report_source.get("materialized") is True,
            "registered_chunk_found": report_source.get("registered_chunk_found") is True,
            "content_hash_matches_registry": report_source.get("content_hash_matches_registry") is True,
            "content_hash_reproducible": report_source.get("content_hash_reproducible") is True,
            "metadata_matches_registry": all(
                report_source.get(key) is True
                for key in (
                    "work_identity_matches_registry",
                    "creator_matches_registry",
                    "title_matches_registry",
                    "source_uri_matches_registry",
                    "license_matches_registry",
                )
            ),
            "quote_present_in_registered_chunk": report_source.get("quote_present_in_registered_chunk") is True,
            "active_license_term": bool(term) and term.get("revoked") is False and term.get("consent_status") == "active",
            "generation_allowed_by_license": "generation" in term.get("allowed_uses", []),
            "content_hash_covered_by_license": bool(term) and term.get("content_hash") == source.get("content_hash"),
            "attribution_duty_present": term.get("duties", {}).get("attribution_required") is True,
            "royalty_duty_present": term.get("duties", {}).get("royalty_required") is True,
        }
        score = _score(checks)
        all_required = all(checks.values())
        row = {
            "label": label,
            "title": source.get("title", ""),
            "creator_id": source.get("creator_id", ""),
            "creator_name": source.get("creator_name", ""),
            "work_id": source.get("work_id", ""),
            "chunk_id": source.get("chunk_id", ""),
            "source_uri": source.get("source_uri", ""),
            "license": source.get("license", ""),
            "content_hash": source.get("content_hash", ""),
            "content_hash_prefix": str(source.get("content_hash", ""))[:12],
            "evidence_span_hash_count": len(source.get("evidence_span_hashes", [])),
            "support_score": source.get("support_score", 0.0),
            "retrieval_score": source.get("retrieval_score", 0.0),
            "text_match_score": source.get("text_match_score", 0.0),
            "contribution_weight": source.get("contribution_weight", ""),
            "confidence_score": score,
            "confidence_level": _level(score, all_required=all_required),
            "checks": checks,
        }
        row["source_confidence_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _claim_rows(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    report_by_index = {
        int(claim.get("claim_index", 0)): claim
        for claim in source_verification_report.get("claims", [])
    }
    source_level_by_label = {
        str(source["label"]): str(source["confidence_level"])
        for source in source_rows
    }
    rows: list[dict[str, Any]] = []
    for claim in answer_card.get("claims", []):
        index = int(claim.get("claim_index", 0))
        report_claim = report_by_index.get(index, {})
        support_score = float(claim.get("support_score", 0.0) or 0.0)
        source_level = source_level_by_label.get(str(claim.get("source_label", "")), "failed")
        checks = {
            "claim_supported": claim.get("supported") is True,
            "support_score_meets_floor": support_score >= SUPPORT_SCORE_FLOOR,
            "claim_materialized": report_claim.get("materialized") is True,
            "source_label_resolves": report_claim.get("source_label_resolves") is True,
            "source_chunk_matches_claim": report_claim.get("source_chunk_matches_claim") is True,
            "evidence_hash_reproducible": report_claim.get("evidence_hash_reproducible") is True,
            "evidence_span_in_registered_chunk": report_claim.get("evidence_span_in_registered_chunk") is True,
            "visible_footer_source_label": report_claim.get("visible_footer_source_label") is True,
            "visible_footer_span_prefix": report_claim.get("visible_footer_span_prefix") is True,
            "source_confidence_not_failed": source_level != "failed",
        }
        score = _score(checks)
        all_required = all(checks.values())
        row = {
            "claim_index": index,
            "claim_hash": claim.get("claim_hash", ""),
            "source_label": claim.get("source_label", ""),
            "work_id": claim.get("work_id", ""),
            "chunk_id": claim.get("chunk_id", ""),
            "support_score": round(support_score, 8),
            "evidence_span_hash": claim.get("evidence_span_hash", ""),
            "evidence_span_prefix": claim.get("evidence_span_prefix", ""),
            "source_confidence_level": source_level,
            "confidence_score": score,
            "confidence_level": _level(score, all_required=all_required),
            "checks": checks,
        }
        row["claim_confidence_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _taxonomy(source_rows: list[dict[str, Any]], claim_rows: list[dict[str, Any]]) -> dict[str, Any]:
    fabricated_sources = [
        source["label"]
        for source in source_rows
        if not source["checks"]["registered_chunk_found"]
    ]
    metadata_mismatches = [
        source["label"]
        for source in source_rows
        if not source["checks"]["metadata_matches_registry"]
    ]
    hash_mismatches = [
        source["label"]
        for source in source_rows
        if not (
            source["checks"]["content_hash_matches_registry"]
            and source["checks"]["content_hash_reproducible"]
        )
    ]
    footer_omissions = [
        source["label"]
        for source in source_rows
        if not source["checks"]["source_label_visible_in_footer"]
    ]
    attribution_suppression = [
        source["label"]
        for source in source_rows
        if (
            source["checks"]["registered_chunk_found"]
            and source["checks"]["source_materialized"]
            and not source["checks"]["source_label_visible_in_footer"]
        )
    ]
    license_gaps = [
        source["label"]
        for source in source_rows
        if not (
            source["checks"]["active_license_term"]
            and source["checks"]["generation_allowed_by_license"]
            and source["checks"]["content_hash_covered_by_license"]
            and source["checks"]["attribution_duty_present"]
            and source["checks"]["royalty_duty_present"]
        )
    ]
    unsupported_claims = [
        claim["claim_index"]
        for claim in claim_rows
        if not (
            claim["checks"]["claim_supported"]
            and claim["checks"]["support_score_meets_floor"]
        )
    ]
    evidence_span_gaps = [
        claim["claim_index"]
        for claim in claim_rows
        if not (
            claim["checks"]["evidence_hash_reproducible"]
            and claim["checks"]["evidence_span_in_registered_chunk"]
            and claim["checks"]["visible_footer_span_prefix"]
        )
    ]
    failed_sources = [
        source["label"] for source in source_rows if source["confidence_level"] == "failed"
    ]
    failed_claims = [
        claim["claim_index"] for claim in claim_rows if claim["confidence_level"] == "failed"
    ]
    return {
        "fabricated_source_labels": fabricated_sources,
        "metadata_mismatch_source_labels": metadata_mismatches,
        "hash_mismatch_source_labels": hash_mismatches,
        "footer_omission_source_labels": footer_omissions,
        "attribution_suppression_source_labels": attribution_suppression,
        "license_gap_source_labels": license_gaps,
        "unsupported_claim_indexes": unsupported_claims,
        "evidence_span_gap_claim_indexes": evidence_span_gaps,
        "failed_source_labels": failed_sources,
        "failed_claim_indexes": failed_claims,
        "fabricated_source_count": len(fabricated_sources),
        "metadata_mismatch_count": len(metadata_mismatches),
        "hash_mismatch_count": len(hash_mismatches),
        "footer_omission_count": len(footer_omissions),
        "attribution_suppression_count": len(attribution_suppression),
        "license_gap_count": len(license_gaps),
        "unsupported_claim_count": len(unsupported_claims),
        "evidence_span_gap_count": len(evidence_span_gaps),
        "failed_source_count": len(failed_sources),
        "failed_claim_count": len(failed_claims),
    }


def _footer_rows(source_rows: list[dict[str, Any]], claim_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claim_counts: dict[str, int] = {}
    for claim in claim_rows:
        label = str(claim.get("source_label", ""))
        claim_counts[label] = claim_counts.get(label, 0) + 1
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        row = {
            "label": source["label"],
            "title": source["title"],
            "creator_name": source["creator_name"],
            "work_id": source["work_id"],
            "source_uri": source["source_uri"],
            "confidence_level": source["confidence_level"],
            "confidence_score": source["confidence_score"],
            "supported_claim_count": claim_counts.get(str(source["label"]), 0),
            "content_hash_prefix": source["content_hash_prefix"],
        }
        row["footer_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _artifact_status(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    creator_license_contract: dict[str, Any] | None,
    signing_secret: str | None,
) -> dict[str, Any]:
    contract_errors = (
        verify_creator_license_contract_public(
            creator_license_contract,
            signing_secret=signing_secret,
        )
        if creator_license_contract
        else ["creator license contract missing"]
    )
    return {
        "answer_card_hash_reproducible": _hash_reproducible(answer_card, "card_hash"),
        "source_verification_hash_reproducible": _hash_reproducible(
            source_verification_report,
            "report_hash",
        ),
        "source_verification_status_verified": source_verification_report.get("summary", {}).get("status") == "verified",
        "creator_license_contract_verified": not contract_errors,
        "creator_license_contract_errors": contract_errors,
    }


def make_source_confidence_report(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    creator_license_contract: dict[str, Any] | None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public, user-facing confidence report for answer source footers."""

    source_rows = _source_rows(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        creator_license_contract=creator_license_contract,
    )
    claim_rows = _claim_rows(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_rows=source_rows,
    )
    taxonomy = _taxonomy(source_rows, claim_rows)
    footer_rows = _footer_rows(source_rows, claim_rows)
    artifact_status = _artifact_status(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        creator_license_contract=creator_license_contract,
        signing_secret=signing_secret,
    )
    source_scores = [float(row["confidence_score"]) for row in source_rows]
    claim_scores = [float(row["confidence_score"]) for row in claim_rows]
    all_artifacts_verified = (
        artifact_status["answer_card_hash_reproducible"]
        and artifact_status["source_verification_hash_reproducible"]
        and artifact_status["source_verification_status_verified"]
        and artifact_status["creator_license_contract_verified"]
    )
    all_rows_verified = all(row["confidence_level"] == "verified" for row in source_rows + claim_rows)
    status = "verified" if all_artifacts_verified and all_rows_verified else "warning"
    if taxonomy["failed_source_count"] or taxonomy["failed_claim_count"]:
        status = "failed"
    report = {
        "report_version": SOURCE_CONFIDENCE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": answer_card.get("event", {}).get("event_id", ""),
            "event_hash": answer_card.get("event", {}).get("event_hash", ""),
            "rendered_output_hash": answer_card.get("event", {}).get(
                "rendered_output_hash",
                "",
            ),
            "answer_card_hash": answer_card.get("card_hash", ""),
            "source_verification_report_hash": source_verification_report.get(
                "report_hash",
                "",
            ),
            "creator_license_contract_hash": (
                creator_license_contract or {}
            ).get("contract_hash", ""),
        },
        "artifact_status": artifact_status,
        "sources": source_rows,
        "claims": claim_rows,
        "footer": {
            "profile": "rdllm-source-confidence-footer/v1",
            "rows": footer_rows,
            "row_count": len(footer_rows),
        },
        "hallucination_taxonomy": taxonomy,
        "commitments": {
            "source_confidence_root": hash_payload(source_rows),
            "claim_confidence_root": hash_payload(claim_rows),
            "footer_confidence_root": hash_payload(footer_rows),
            "taxonomy_hash": hash_payload(taxonomy),
            "answer_card_hash": _declared_hash(answer_card),
            "source_verification_report_hash": _declared_hash(source_verification_report),
            "creator_license_contract_hash": (
                _declared_hash(creator_license_contract)
                if creator_license_contract
                else ""
            ),
        },
        "summary": {
            "status": status,
            "source_count": len(source_rows),
            "claim_count": len(claim_rows),
            "verified_source_count": sum(1 for row in source_rows if row["confidence_level"] == "verified"),
            "verified_claim_count": sum(1 for row in claim_rows if row["confidence_level"] == "verified"),
            "minimum_source_confidence": min(source_scores) if source_scores else 1.0,
            "minimum_claim_confidence": min(claim_scores) if claim_scores else 1.0,
            "average_source_confidence": round(sum(source_scores) / len(source_scores), 8) if source_scores else 1.0,
            "average_claim_confidence": round(sum(claim_scores) / len(claim_scores), 8) if claim_scores else 1.0,
            "support_score_floor": SUPPORT_SCORE_FLOOR,
            "hallucination_issue_count": (
                taxonomy["fabricated_source_count"]
                + taxonomy["metadata_mismatch_count"]
                + taxonomy["hash_mismatch_count"]
                + taxonomy["footer_omission_count"]
                + taxonomy["attribution_suppression_count"]
                + taxonomy["license_gap_count"]
                + taxonomy["unsupported_claim_count"]
                + taxonomy["evidence_span_gap_count"]
            ),
            "public_footer_verification_supported": True,
        },
        "schemas": {
            "source_confidence_report": SOURCE_CONFIDENCE_SCHEMA,
            "answer_provenance_card": "docs/schemas/answer_provenance_card.schema.json",
            "source_verification_report": "docs/schemas/source_verification_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "source_quote_text_disclosed": False,
            "claim_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "payout_account_disclosed": False,
            "report_uses_hashes_metadata_booleans_and_scores": True,
        },
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
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


def validate_source_confidence_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "artifact_status",
        "sources",
        "claims",
        "footer",
        "hallucination_taxonomy",
        "commitments",
        "summary",
        "schemas",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source confidence report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SOURCE_CONFIDENCE_VERSION:
        errors.append("source confidence report version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "answer_card_hash",
        "source_verification_report_hash",
        "creator_license_contract_hash",
    ):
        if key not in report.get("event", {}):
            errors.append(f"missing source confidence event field: {key}")
    for source in report.get("sources", []):
        for key in ("label", "work_id", "confidence_score", "confidence_level", "checks", "source_confidence_hash"):
            if key not in source:
                errors.append(f"missing source confidence source field: {key}")
    for claim in report.get("claims", []):
        for key in ("claim_index", "claim_hash", "source_label", "confidence_score", "confidence_level", "checks", "claim_confidence_hash"):
            if key not in claim:
                errors.append(f"missing source confidence claim field: {key}")
    if "source_confidence_report" not in report.get("schemas", {}):
        errors.append("missing source confidence schema")
    return errors


def verify_source_confidence_report(
    report: dict[str, Any],
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    creator_license_contract: dict[str, Any] | None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a source-confidence report using only public RDLLM artifacts."""

    errors = validate_source_confidence_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("source confidence report hash is not reproducible")

    expected = make_source_confidence_report(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        creator_license_contract=creator_license_contract,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "artifact_status",
        "sources",
        "claims",
        "footer",
        "hallucination_taxonomy",
        "commitments",
        "summary",
        "schemas",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source confidence report {key} does not match public artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("source confidence report hash does not match public artifacts")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("source confidence report status is not verified")
    if report.get("summary", {}).get("hallucination_issue_count") != 0:
        errors.append("source confidence report contains hallucination issues")
    if report.get("artifact_status", {}).get("creator_license_contract_verified") is not True:
        errors.append("source confidence report creator license contract is not verified")

    rendered = canonical_json(report)
    forbidden_keys = (
        "source quote text",
        "claim evidence text",
    )
    for forbidden in forbidden_keys:
        if forbidden in rendered:
            errors.append("source confidence report leaks private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source confidence report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source confidence report signature is invalid")
    return errors
