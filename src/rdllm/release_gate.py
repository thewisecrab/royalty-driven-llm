"""Emit-time response release gates for RDLLM model outputs."""

from __future__ import annotations

from typing import Any

from rdllm.answer_card import validate_answer_provenance_card_shape
from rdllm.answer_coverage import (
    validate_answer_claim_coverage_report_shape,
    verify_answer_claim_coverage_report,
)
from rdllm.attribution_capsule import validate_attribution_capsule_shape
from rdllm.context_closure import (
    validate_generation_context_closure_report_shape,
    verify_generation_context_closure_report,
)
from rdllm.license_contract import verify_creator_license_contract_public
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_availability import validate_source_availability_report_shape
from rdllm.source_authenticity import validate_source_authenticity_report_shape
from rdllm.source_boundary import (
    validate_source_boundary_report_shape,
    verify_source_boundary_report,
)
from rdllm.evidence_sufficiency import validate_evidence_sufficiency_report_shape
from rdllm.counterevidence import validate_counterevidence_report_shape
from rdllm.source_verification import validate_source_verification_report_shape

RELEASE_GATE_VERSION = "rdllm-response-release-gate/v1"
RELEASE_GATE_SCHEMA = "docs/schemas/release_gate.schema.json"
MINIMUM_CERTIFICATION_LEVEL = "RDLLM-L34"
FULL_GROUNDING_CLOSURE_LEVEL = "RDLLM-L57"
ANSWER_COVERAGE_LEVEL = "RDLLM-L59"
GENERATION_CONTEXT_CLOSURE_LEVEL = "RDLLM-L60"
SOURCE_BOUNDARY_LEVEL = "RDLLM-L61"
SOURCE_AUTHENTICITY_LEVEL = "RDLLM-L64"


def _hashable_gate(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in gate.items()
        if key not in {"gate_hash", "signature"}
    }


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _certification_summary(certification_report: dict[str, Any]) -> dict[str, Any]:
    summary = certification_report.get("summary", {})
    return {
        "report_hash": certification_report.get("report_hash", ""),
        "status": summary.get("status", ""),
        "highest_level": summary.get("highest_level", ""),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
    }


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _report_hash_is_reproducible(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    return hash_payload(_hashable_report(report)) == report.get("report_hash", "")


def _requires_level(certification_report: dict[str, Any], minimum_level: str) -> bool:
    return _level_number(_certification_summary(certification_report)["highest_level"]) >= _level_number(minimum_level)


def _release_mode(answer_card: dict[str, Any]) -> str:
    grounding = answer_card.get("grounding", {})
    quality_verdict = grounding.get("quality_verdict", "")
    grounding_status = grounding.get("status", "")
    policy_status = grounding.get("policy_status", "")
    registry_status = grounding.get("registry_status", "")
    attribution_gap = grounding.get("attribution_gap_verdict", "")
    unsupported = int(grounding.get("unsupported_claim_count", 0) or 0)
    if (
        quality_verdict == "verified"
        and grounding_status == "grounded"
        and unsupported == 0
    ):
        return "grounded_answer"
    if quality_verdict == "blocked_by_policy" and policy_status == "blocked":
        return "rights_block_notice"
    if quality_verdict == "blocked_by_registry" and registry_status == "disputed":
        return "registry_dispute_notice"
    if quality_verdict == "unattributed" and attribution_gap == "closed":
        return "unattributed_escrow_notice"
    return "hold_for_revision"


def _gate_policy() -> dict[str, Any]:
    return {
        "policy_version": "rdllm-emit-gate-strict/v1",
        "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
        "full_grounding_closure_level": FULL_GROUNDING_CLOSURE_LEVEL,
        "allowed_release_modes": [
            "grounded_answer",
            "rights_block_notice",
            "registry_dispute_notice",
            "unattributed_escrow_notice",
        ],
        "unsupported_claims_allowed": 0,
        "minimum_grounded_quality_score": 0.95,
        "requires_response_envelope_verification": True,
        "requires_source_materialization": True,
        "requires_footer_claim_span_coverage": True,
        "requires_capsule_delivery_contract": True,
        "requires_creator_license_contract": True,
        "requires_public_provider_surface": True,
        "requires_source_availability_for_l55": True,
        "requires_evidence_sufficiency_for_l56": True,
        "requires_counterevidence_for_l57": True,
        "requires_answer_claim_coverage_for_l59": True,
        "requires_generation_context_closure_for_l60": True,
        "requires_source_boundary_for_l61": True,
        "requires_source_authenticity_for_l64": True,
    }


def _source_terms_cover_answer_sources(
    answer_card: dict[str, Any],
    creator_license_contract: dict[str, Any],
) -> bool:
    terms = {
        str(term.get("work_id", "")): term
        for term in creator_license_contract.get("terms", [])
    }
    for source in answer_card.get("sources", []):
        work_id = str(source.get("work_id", ""))
        if not work_id:
            return False
        term = terms.get(work_id)
        if not term:
            return False
        if term.get("consent_status") != "active" or term.get("revoked") is True:
            return False
        if "generation" not in set(term.get("allowed_uses", [])):
            return False
        if term.get("content_hash") != source.get("content_hash"):
            return False
        if term.get("requires_attribution") is not True:
            return False
        if term.get("requires_royalty") is not True:
            return False
        duties = term.get("duties", {})
        if duties.get("attribution_required") is not True:
            return False
        if duties.get("royalty_required") is not True:
            return False
    return True


def _subject(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    creator_license_contract: dict[str, Any],
    answer_card: dict[str, Any],
    source_report: dict[str, Any],
) -> dict[str, Any]:
    response = response_envelope.get("response", {})
    artifacts = response_envelope.get("embedded_artifacts", {})
    grounding = answer_card.get("grounding", {})
    return {
        "event_id": response.get("event_id", ""),
        "event_hash": response.get("event_hash", ""),
        "rendered_output_hash": response.get("rendered_output_hash", ""),
        "envelope_hash": response_envelope.get("envelope_hash", ""),
        "capsule_hash": attribution_capsule.get("capsule_hash", ""),
        "creator_license_contract_hash": creator_license_contract.get(
            "contract_hash", ""
        ),
        "answer_card_hash": answer_card.get("card_hash", ""),
        "source_verification_report_hash": source_report.get("report_hash", ""),
        "source_availability_report_hash": artifacts.get(
            "source_availability_report",
            {},
        ).get("report_hash", ""),
        "evidence_sufficiency_report_hash": artifacts.get(
            "evidence_sufficiency_report",
            {},
        ).get("report_hash", ""),
        "counterevidence_report_hash": artifacts.get(
            "counterevidence_report",
            {},
        ).get("report_hash", ""),
        "answer_claim_coverage_report_hash": artifacts.get(
            "answer_claim_coverage_report",
            {},
        ).get("report_hash", ""),
        "generation_context_closure_report_hash": artifacts.get(
            "generation_context_closure_report",
            {},
        ).get("report_hash", ""),
        "source_boundary_report_hash": artifacts.get(
            "source_boundary_report",
            {},
        ).get("report_hash", ""),
        "source_authenticity_report_hash": artifacts.get(
            "source_authenticity_report",
            {},
        ).get("report_hash", ""),
        "quality_verdict": grounding.get("quality_verdict", ""),
        "quality_score": grounding.get("quality_score", 0.0),
        "grounding_status": grounding.get("status", ""),
        "unsupported_claim_count": int(
            grounding.get("unsupported_claim_count", 0) or 0
        ),
        "source_count": int(response_envelope.get("summary", {}).get("source_count", 0) or 0),
        "claim_count": int(response_envelope.get("summary", {}).get("claim_count", 0) or 0),
    }


def _event_matches_response(report: dict[str, Any] | None, response: dict[str, Any]) -> bool:
    if not report:
        return False
    event = report.get("event", {})
    return (
        event.get("event_hash") == response.get("event_hash", "")
        and event.get("rendered_output_hash")
        == response.get("rendered_output_hash", "")
        and event.get("answer_hash") == response.get("answer_hash", "")
    )


def _late_grounding_bound(
    *,
    response_envelope: dict[str, Any],
    answer_card: dict[str, Any],
    source_report: dict[str, Any],
    source_availability_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
) -> bool:
    citation_footer_contract = response_envelope.get("embedded_artifacts", {}).get(
        "citation_footer_contract",
        {},
    )
    if not source_availability_report:
        return False
    availability_bindings = source_availability_report.get("artifact_bindings", {})
    if (
        availability_bindings.get("answer_card_hash") != answer_card.get("card_hash", "")
        or availability_bindings.get("source_verification_report_hash")
        != source_report.get("report_hash", "")
        or availability_bindings.get("citation_footer_contract_hash")
        != citation_footer_contract.get("contract_hash", "")
    ):
        return False
    if not evidence_sufficiency_report:
        return False
    sufficiency_bindings = evidence_sufficiency_report.get("artifact_bindings", {})
    if (
        sufficiency_bindings.get("answer_card_hash") != answer_card.get("card_hash", "")
        or sufficiency_bindings.get("source_verification_report_hash")
        != source_report.get("report_hash", "")
        or sufficiency_bindings.get("source_availability_report_hash")
        != source_availability_report.get("report_hash", "")
        or sufficiency_bindings.get("citation_footer_contract_hash")
        != citation_footer_contract.get("contract_hash", "")
    ):
        return False
    if not counterevidence_report:
        return False
    counter_bindings = counterevidence_report.get("artifact_bindings", {})
    return (
        counter_bindings.get("answer_card_hash") == answer_card.get("card_hash", "")
        and counter_bindings.get("source_verification_report_hash")
        == source_report.get("report_hash", "")
        and counter_bindings.get("source_availability_report_hash")
        == source_availability_report.get("report_hash", "")
        and counter_bindings.get("evidence_sufficiency_report_hash")
        == evidence_sufficiency_report.get("report_hash", "")
        and counter_bindings.get("citation_footer_contract_hash")
        == citation_footer_contract.get("contract_hash", "")
    )


def _source_availability_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
) -> bool:
    return (
        bool(report)
        and not validate_source_availability_report_shape(report)
        and _report_hash_is_reproducible(report)
        and _event_matches_response(report, response)
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get("all_public_sources_inspectable") is True
        and not report.get("issues")
    )


def _evidence_sufficiency_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
) -> bool:
    return (
        bool(report)
        and not validate_evidence_sufficiency_report_shape(report)
        and _report_hash_is_reproducible(report)
        and _event_matches_response(report, response)
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get(
            "all_claims_have_minimal_sufficient_evidence"
        )
        is True
        and not report.get("issues")
    )


def _counterevidence_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
) -> bool:
    return (
        bool(report)
        and not validate_counterevidence_report_shape(report)
        and _report_hash_is_reproducible(report)
        and _event_matches_response(report, response)
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get("all_claims_counterevidence_adjudicated")
        is True
        and int(
            report.get("summary", {}).get("unaddressed_counterevidence_count", 0)
            or 0
        )
        == 0
        and not report.get("issues")
    )


def _answer_coverage_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
    *,
    answer_card: dict[str, Any],
    source_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    signing_secret: str | None,
) -> bool:
    return (
        bool(report)
        and not validate_answer_claim_coverage_report_shape(report)
        and not verify_answer_claim_coverage_report(
            report,
            rendered_output=str(response.get("rendered_output", "")),
            event_id=str(response.get("event_id", "")),
            event_hash=str(response.get("event_hash", "")),
            answer_hash=str(response.get("answer_hash", "")),
            answer_card=answer_card,
            source_verification_report=source_report,
            evidence_sufficiency_report=evidence_sufficiency_report,
            counterevidence_report=counterevidence_report,
            citation_footer_contract=citation_footer_contract,
            signing_secret=signing_secret,
        )
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get("all_answer_claims_covered") is True
        and not report.get("issues")
    )


def _generation_context_closure_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
    *,
    trace_exchange: dict[str, Any] | None,
    source_report: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any] | None,
    answer_card: dict[str, Any],
    signing_secret: str | None,
) -> bool:
    return (
        bool(report)
        and bool(trace_exchange)
        and not validate_generation_context_closure_report_shape(report)
        and not verify_generation_context_closure_report(
            report,
            trace_exchange=trace_exchange or {},
            source_verification_report=source_report,
            answer_claim_coverage_report=answer_claim_coverage_report,
            signing_secret=signing_secret,
        )
        and _event_matches_response(report, response)
        and report.get("event", {}).get("trace_hash")
        == answer_card.get("event", {}).get("trace_hash", "")
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get(
            "all_supported_claims_in_generation_context"
        )
        is True
        and not report.get("issues")
    )


def _source_boundary_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
    *,
    trace_exchange: dict[str, Any] | None,
    source_report: dict[str, Any],
    generation_context_closure_report: dict[str, Any] | None,
    answer_claim_coverage_report: dict[str, Any] | None,
    answer_card: dict[str, Any],
    signing_secret: str | None,
) -> bool:
    return (
        bool(report)
        and bool(trace_exchange)
        and bool(generation_context_closure_report)
        and not validate_source_boundary_report_shape(report)
        and not verify_source_boundary_report(
            report,
            trace_exchange=trace_exchange or {},
            source_verification_report=source_report,
            generation_context_closure_report=generation_context_closure_report
            or {},
            answer_claim_coverage_report=answer_claim_coverage_report,
            signing_secret=signing_secret,
        )
        and _event_matches_response(report, response)
        and report.get("event", {}).get("trace_hash")
        == answer_card.get("event", {}).get("trace_hash", "")
        and report.get("event", {}).get("generation_context_closure_report_hash")
        == (generation_context_closure_report or {}).get("report_hash", "")
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get("all_context_blocks_boundary_isolated")
        is True
        and not report.get("issues")
    )


def _source_authenticity_release_verified(
    report: dict[str, Any] | None,
    response: dict[str, Any],
    *,
    source_availability_report: dict[str, Any] | None,
    source_boundary_report: dict[str, Any] | None,
    creator_license_contract: dict[str, Any],
) -> bool:
    return (
        bool(report)
        and not validate_source_authenticity_report_shape(report)
        and _report_hash_is_reproducible(report)
        and _event_matches_response(report, response)
        and report.get("event", {}).get("source_availability_report_hash")
        == (source_availability_report or {}).get("report_hash", "")
        and report.get("event", {}).get("source_boundary_report_hash")
        == (source_boundary_report or {}).get("report_hash", "")
        and report.get("event", {}).get("creator_license_contract_hash")
        == creator_license_contract.get("contract_hash", "")
        and report.get("summary", {}).get("status") == "verified"
        and report.get("summary", {}).get("all_sources_authentic") is True
        and int(report.get("summary", {}).get("escrow_recommended_count", 0) or 0)
        == 0
        and not report.get("issues")
    )


def _checks(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    answer_card: dict[str, Any],
    source_report: dict[str, Any],
    signing_secret: str | None,
) -> dict[str, bool]:
    envelope_errors = verify_response_envelope(
        response_envelope,
        signing_secret=signing_secret,
    )
    license_contract_errors = verify_creator_license_contract_public(
        creator_license_contract,
        signing_secret=signing_secret,
    )
    capsule_shape_errors = validate_attribution_capsule_shape(attribution_capsule)
    answer_card_errors = validate_answer_provenance_card_shape(answer_card)
    source_report_errors = validate_source_verification_report_shape(source_report)
    provider_card_errors = validate_provider_card_shape(provider_card)
    envelope_verification = response_envelope.get("verification", {})
    source_summary = source_report.get("summary", {})
    grounding = answer_card.get("grounding", {})
    artifacts = response_envelope.get("embedded_artifacts", {})
    response = response_envelope.get("response", {})
    source_availability_report = artifacts.get("source_availability_report")
    evidence_sufficiency_report = artifacts.get("evidence_sufficiency_report")
    counterevidence_report = artifacts.get("counterevidence_report")
    answer_claim_coverage_report = artifacts.get("answer_claim_coverage_report")
    trace_exchange = artifacts.get("trace_exchange")
    generation_context_closure_report = artifacts.get(
        "generation_context_closure_report"
    )
    source_boundary_report = artifacts.get("source_boundary_report")
    source_authenticity_report = artifacts.get("source_authenticity_report")
    citation_footer_contract = artifacts.get("citation_footer_contract")
    capsule_surfaces = attribution_capsule.get("portable_surfaces", {})
    delivery_contract = capsule_surfaces.get("delivery_contract", {})
    output_hash = response_envelope.get("response", {}).get("rendered_output_hash", "")
    certification = _certification_summary(certification_report)
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    mode = _release_mode(answer_card)
    policy = _gate_policy()
    quality_score = float(grounding.get("quality_score", 0.0) or 0.0)
    source_availability_required = _requires_level(certification_report, "RDLLM-L55")
    evidence_sufficiency_required = _requires_level(certification_report, "RDLLM-L56")
    counterevidence_required = _requires_level(certification_report, "RDLLM-L57")
    answer_coverage_required = _requires_level(certification_report, ANSWER_COVERAGE_LEVEL)
    context_closure_required = _requires_level(
        certification_report,
        GENERATION_CONTEXT_CLOSURE_LEVEL,
    )
    source_boundary_required = _requires_level(
        certification_report,
        SOURCE_BOUNDARY_LEVEL,
    )
    source_authenticity_required = _requires_level(
        certification_report,
        SOURCE_AUTHENTICITY_LEVEL,
    )
    source_availability_verified = _source_availability_release_verified(
        source_availability_report,
        response,
    )
    evidence_sufficiency_verified = _evidence_sufficiency_release_verified(
        evidence_sufficiency_report,
        response,
    )
    counterevidence_verified = _counterevidence_release_verified(
        counterevidence_report,
        response,
    )
    answer_coverage_verified = _answer_coverage_release_verified(
        answer_claim_coverage_report,
        response,
        answer_card=answer_card,
        source_report=source_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
        signing_secret=signing_secret,
    )
    context_closure_verified = _generation_context_closure_release_verified(
        generation_context_closure_report,
        response,
        trace_exchange=trace_exchange,
        source_report=source_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        answer_card=answer_card,
        signing_secret=signing_secret,
    )
    source_boundary_verified = _source_boundary_release_verified(
        source_boundary_report,
        response,
        trace_exchange=trace_exchange,
        source_report=source_report,
        generation_context_closure_report=generation_context_closure_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        answer_card=answer_card,
        signing_secret=signing_secret,
    )
    source_authenticity_verified = _source_authenticity_release_verified(
        source_authenticity_report,
        response,
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
    )
    return {
        "response_envelope_verified": not envelope_errors
        and response_envelope.get("summary", {}).get("status") == "verified",
        "answer_card_shape_valid": not answer_card_errors,
        "source_verification_shape_valid": not source_report_errors,
        "provider_card_shape_valid": not provider_card_errors,
        "attribution_capsule_shape_valid": not capsule_shape_errors,
        "creator_license_contract_verified": not license_contract_errors
        and creator_license_contract.get("summary", {}).get("status") == "ready",
        "source_terms_cover_answer_sources": _source_terms_cover_answer_sources(
            answer_card,
            creator_license_contract,
        ),
        "release_mode_allowed": mode in policy["allowed_release_modes"],
        "grounded_quality_sufficient": (
            mode != "grounded_answer"
            or quality_score >= policy["minimum_grounded_quality_score"]
        ),
        "no_unsupported_claims": int(
            grounding.get("unsupported_claim_count", 0) or 0
        )
        <= policy["unsupported_claims_allowed"],
        "source_materialization_verified": source_summary.get("status") == "verified"
        and source_summary.get("all_sources_materialized") is True
        and source_summary.get("all_supported_claims_materialized") is True,
        "source_availability_release_verified": (
            source_availability_verified or not source_availability_required
        ),
        "evidence_sufficiency_release_verified": (
            evidence_sufficiency_verified or not evidence_sufficiency_required
        ),
        "counterevidence_release_verified": (
            counterevidence_verified or not counterevidence_required
        ),
        "response_envelope_binds_late_grounding_reports": (
            _late_grounding_bound(
                response_envelope=response_envelope,
                answer_card=answer_card,
                source_report=source_report,
                source_availability_report=source_availability_report,
                evidence_sufficiency_report=evidence_sufficiency_report,
                counterevidence_report=counterevidence_report,
            )
            or not counterevidence_required
        ),
        "answer_claim_coverage_release_verified": (
            answer_coverage_verified or not answer_coverage_required
        ),
        "generation_context_closure_release_verified": (
            context_closure_verified or not context_closure_required
        ),
        "source_boundary_release_verified": (
            source_boundary_verified or not source_boundary_required
        ),
        "source_authenticity_release_verified": (
            source_authenticity_verified or not source_authenticity_required
        ),
        "footer_sources_verified": (
            envelope_verification.get("footer_source_labels_match_answer_card") is True
        ),
        "footer_claim_spans_verified": (
            envelope_verification.get("footer_span_prefixes_cover_answer_card") is True
        ),
        "capsule_binds_response_output": attribution_capsule.get("subject", {}).get(
            "rendered_output_hash"
        )
        == output_hash,
        "capsule_delivery_contract_verified": (
            delivery_contract.get("contract_version") == "rdllm-delivered-output/v1"
            and delivery_contract.get("body_hash") == output_hash
            and bool(delivery_contract.get("footer_marker_hash"))
        ),
        "provider_declares_release_gate_surface": public_surfaces.get(
            "response_release_gate"
        )
        is True,
        "certification_meets_gate_minimum": certification.get("status") == "passed"
        and _level_number(str(certification.get("highest_level", "")))
        >= _level_number(MINIMUM_CERTIFICATION_LEVEL),
        "private_text_not_disclosed_by_gate": True,
    }


def make_release_gate_report(
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed emit-time release decision for an RDLLM response."""

    artifacts = response_envelope.get("embedded_artifacts", {})
    answer_card = artifacts.get("answer_provenance_card", {})
    source_report = artifacts.get("source_verification_report", {})
    policy = _gate_policy()
    checks = _checks(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        answer_card=answer_card,
        source_report=source_report,
        signing_secret=signing_secret,
    )
    mode = _release_mode(answer_card)
    decision = (
        "emit"
        if mode in policy["allowed_release_modes"] and all(checks.values())
        else "hold_for_revision"
    )
    artifact_bindings = {
        "response_envelope_hash": response_envelope.get("envelope_hash", ""),
        "attribution_capsule_hash": attribution_capsule.get("capsule_hash", ""),
        "creator_license_contract_hash": creator_license_contract.get(
            "contract_hash", ""
        ),
        "provider_card_hash": provider_card.get("card_hash", ""),
        "certification_report_hash": certification_report.get("report_hash", ""),
        "answer_card_hash": answer_card.get("card_hash", ""),
        "source_verification_report_hash": source_report.get("report_hash", ""),
        "source_availability_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("source_availability_report", {})
            .get("report_hash", "")
        ),
        "evidence_sufficiency_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("evidence_sufficiency_report", {})
            .get("report_hash", "")
        ),
        "counterevidence_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("counterevidence_report", {})
            .get("report_hash", "")
        ),
        "answer_claim_coverage_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("answer_claim_coverage_report", {})
            .get("report_hash", "")
        ),
        "generation_context_closure_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("generation_context_closure_report", {})
            .get("report_hash", "")
        ),
        "source_boundary_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("source_boundary_report", {})
            .get("report_hash", "")
        ),
        "source_authenticity_report_hash": (
            response_envelope.get("embedded_artifacts", {})
            .get("source_authenticity_report", {})
            .get("report_hash", "")
        ),
    }
    subject = _subject(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        answer_card=answer_card,
        source_report=source_report,
    )
    gate = {
        "gate_version": RELEASE_GATE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "subject": subject,
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "checks": checks,
        "schemas": {
            "response_release_gate": RELEASE_GATE_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
            "answer_provenance_card": "docs/schemas/answer_provenance_card.schema.json",
            "source_verification_report": "docs/schemas/source_verification_report.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "evidence_sufficiency_report": "docs/schemas/evidence_sufficiency_report.schema.json",
            "counterevidence_report": "docs/schemas/counterevidence_report.schema.json",
            "answer_claim_coverage_report": "docs/schemas/answer_claim_coverage_report.schema.json",
            "generation_context_closure_report": "docs/schemas/generation_context_closure_report.schema.json",
            "source_boundary_report": "docs/schemas/source_boundary_report.schema.json",
            "source_authenticity_report": "docs/schemas/source_authenticity_report.schema.json",
        },
        "summary": {
            "decision": decision,
            "release_mode": mode,
            "target_certification_level": "RDLLM-L35",
            "minimum_upstream_level": MINIMUM_CERTIFICATION_LEVEL,
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed_by_gate": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "hidden_state_disclosed": False,
            "gate_uses_hashes_scores_and_decisions": True,
        },
    }
    gate["gate_hash"] = hash_payload(_hashable_gate(gate))
    gate["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_gate(gate), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return gate


def validate_release_gate_shape(gate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "gate_version",
        "issuer",
        "created_at",
        "subject",
        "policy",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "gate_hash",
        "signature",
    )
    for key in required:
        if key not in gate:
            errors.append(f"missing release gate field: {key}")
    if errors:
        return errors
    if gate.get("gate_version") != RELEASE_GATE_VERSION:
        errors.append("release gate version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "envelope_hash",
        "capsule_hash",
        "creator_license_contract_hash",
        "answer_card_hash",
        "source_verification_report_hash",
    ):
        if key not in gate.get("subject", {}):
            errors.append(f"missing release gate subject field: {key}")
    if "response_release_gate" not in gate.get("schemas", {}):
        errors.append("missing release gate schema")
    return errors


def verify_release_gate_report(
    gate: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    attribution_capsule: dict[str, Any],
    creator_license_contract: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a response release gate against public RDLLM artifacts."""

    errors = validate_release_gate_shape(gate)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_gate(gate))
    if expected_hash != gate.get("gate_hash"):
        errors.append("release gate hash is not reproducible")

    expected = make_release_gate_report(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=gate.get("issuer", DEFAULT_ISSUER),
        created_at=gate.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "subject",
        "policy",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != gate.get(key):
            errors.append(f"release gate {key} does not match artifacts")
    if expected.get("gate_hash") != gate.get("gate_hash"):
        errors.append("release gate hash does not match artifacts")
    if gate.get("summary", {}).get("decision") != "emit":
        errors.append("release gate decision is not emit")
    for check, passed in gate.get("checks", {}).items():
        if passed is not True:
            errors.append(f"release gate check failed: {check}")

    gate_json = canonical_json(gate)
    for field in ("prompt", "output", "source_text", "matched_text", "hidden_state"):
        if f'"{field}"' in gate_json:
            errors.append(f"release gate discloses private {field} field")

    signature = gate.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_gate(gate), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("release gate is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("release gate signature is invalid")

    return errors
