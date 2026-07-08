"""Portable response envelopes for RDLLM API responses."""

from __future__ import annotations

from typing import Any

from rdllm.answer_card import validate_answer_provenance_card_shape
from rdllm.answer_coverage import (
    validate_answer_claim_coverage_report_shape,
    verify_answer_claim_coverage_report,
)
from rdllm.conformance import source_labels_in_output, span_hash_prefixes_in_output
from rdllm.context_closure import (
    validate_generation_context_closure_report_shape,
    verify_generation_context_closure_report,
)
from rdllm.models import UsageEvent
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.source_confidence import (
    validate_source_confidence_report_shape,
    verify_source_confidence_report,
)
from rdllm.counterevidence import validate_counterevidence_report_shape
from rdllm.evidence_sufficiency import validate_evidence_sufficiency_report_shape
from rdllm.source_availability import validate_source_availability_report_shape
from rdllm.source_authenticity import validate_source_authenticity_report_shape
from rdllm.source_boundary import (
    validate_source_boundary_report_shape,
    verify_source_boundary_report,
)
from rdllm.source_verification import validate_source_verification_report_shape
from rdllm.text import stable_hash

RESPONSE_ENVELOPE_VERSION = "rdllm-response-envelope/v1"


def _hashable_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.items()
        if key not in {"envelope_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key
        not in {
            "card_hash",
            "report_hash",
            "receipt_hash",
            "summary_hash",
            "bundle_hash",
            "contract_hash",
            "trace_hash",
            "statement_hash",
            "signature",
        }
    }


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in (
        "card_hash",
        "report_hash",
        "summary_hash",
        "bundle_hash",
        "contract_hash",
        "trace_hash",
        "receipt_hash",
        "statement_hash",
    ):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_declared_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in (
        "card_hash",
        "report_hash",
        "summary_hash",
        "bundle_hash",
        "contract_hash",
        "trace_hash",
        "statement_hash",
    ):
        if artifact.get(field):
            if field == "trace_hash":
                return (
                    hash_payload(
                        {
                            key: value
                            for key, value in artifact.items()
                            if key not in {"trace_hash", "signature"}
                        }
                    )
                    == artifact[field]
                )
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    if artifact.get("receipt_hash") and artifact.get("payload"):
        return hash_payload(artifact["payload"]) == artifact["receipt_hash"]
    return True


def _report_hash_is_reproducible(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    return hash_payload(_hashable_report(report)) == report.get("report_hash", "")


def _required_by_certification(
    certification_report: dict[str, Any] | None,
    minimum_level: int,
) -> bool:
    return _level_number(_certification_summary(certification_report)["highest_level"]) >= minimum_level


def _report_event_matches_response(
    report: dict[str, Any] | None,
    *,
    event_hash: str,
    rendered_output_hash: str,
    answer_hash: str,
) -> bool:
    if not report:
        return False
    event = report.get("event", {})
    return (
        event.get("event_hash") == event_hash
        and event.get("rendered_output_hash") == rendered_output_hash
        and event.get("answer_hash") == answer_hash
    )


def _late_grounding_reports_bound(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_availability_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> bool:
    if not source_availability_report:
        return False
    availability_bindings = source_availability_report.get("artifact_bindings", {})
    if (
        availability_bindings.get("answer_card_hash") != answer_card.get("card_hash", "")
        or availability_bindings.get("source_verification_report_hash")
        != source_verification_report.get("report_hash", "")
        or availability_bindings.get("citation_footer_contract_hash")
        != (citation_footer_contract or {}).get("contract_hash", "")
    ):
        return False
    if not evidence_sufficiency_report:
        return False
    sufficiency_bindings = evidence_sufficiency_report.get("artifact_bindings", {})
    if (
        sufficiency_bindings.get("answer_card_hash") != answer_card.get("card_hash", "")
        or sufficiency_bindings.get("source_verification_report_hash")
        != source_verification_report.get("report_hash", "")
        or sufficiency_bindings.get("source_availability_report_hash")
        != source_availability_report.get("report_hash", "")
        or sufficiency_bindings.get("citation_footer_contract_hash")
        != (citation_footer_contract or {}).get("contract_hash", "")
    ):
        return False
    if not counterevidence_report:
        return False
    counter_bindings = counterevidence_report.get("artifact_bindings", {})
    return (
        counter_bindings.get("answer_card_hash") == answer_card.get("card_hash", "")
        and counter_bindings.get("source_verification_report_hash")
        == source_verification_report.get("report_hash", "")
        and counter_bindings.get("source_availability_report_hash")
        == source_availability_report.get("report_hash", "")
        and counter_bindings.get("evidence_sufficiency_report_hash")
        == evidence_sufficiency_report.get("report_hash", "")
        and counter_bindings.get("citation_footer_contract_hash")
        == (citation_footer_contract or {}).get("contract_hash", "")
    )


def _artifact_entry(name: str, artifact_type: str, artifact: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(artifact),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _certification_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "report_hash": "",
            "status": "",
            "highest_level": "",
            "case_count": 0,
            "passed": 0,
            "failed": 0,
        }
    summary = report.get("summary", {})
    return {
        "report_hash": report.get("report_hash", hash_payload(report)),
        "status": summary.get("status", ""),
        "highest_level": summary.get("highest_level", ""),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
    }


def _embedded_artifacts(
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
    creator_license_contract: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    source_availability_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    answer_claim_coverage_report: dict[str, Any] | None,
    trace_exchange: dict[str, Any] | None,
    generation_context_closure_report: dict[str, Any] | None,
    source_boundary_report: dict[str, Any] | None,
    source_authenticity_report: dict[str, Any] | None,
    public_receipt: dict[str, Any] | None,
    provider_card: dict[str, Any] | None,
    certification_report: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    artifacts = {
        "answer_provenance_card": answer_card,
        "source_verification_report": source_verification_report,
    }
    if source_confidence_report:
        artifacts["source_confidence_report"] = source_confidence_report
    if creator_license_contract:
        artifacts["creator_license_contract"] = creator_license_contract
    if citation_footer_contract:
        artifacts["citation_footer_contract"] = citation_footer_contract
    if source_availability_report:
        artifacts["source_availability_report"] = source_availability_report
    if evidence_sufficiency_report:
        artifacts["evidence_sufficiency_report"] = evidence_sufficiency_report
    if counterevidence_report:
        artifacts["counterevidence_report"] = counterevidence_report
    if answer_claim_coverage_report:
        artifacts["answer_claim_coverage_report"] = answer_claim_coverage_report
    if trace_exchange:
        artifacts["trace_exchange"] = trace_exchange
    if generation_context_closure_report:
        artifacts["generation_context_closure_report"] = generation_context_closure_report
    if source_boundary_report:
        artifacts["source_boundary_report"] = source_boundary_report
    if source_authenticity_report:
        artifacts["source_authenticity_report"] = source_authenticity_report
    if public_receipt:
        artifacts["public_receipt"] = public_receipt
    if provider_card:
        artifacts["provider_attribution_card"] = provider_card
    if certification_report:
        artifacts["certification_report"] = certification_report
    return artifacts


def _artifact_entries(artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _artifact_entry(name, name, artifact)
        for name, artifact in sorted(artifacts.items())
    ]


def _citation_footer_contract_matches_response(
    *,
    contract: dict[str, Any] | None,
    rendered_output: str,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
    creator_license_contract: dict[str, Any] | None,
) -> bool:
    if not contract:
        return True
    try:
        from rdllm.citation_footer import validate_citation_footer_contract_shape
    except ImportError:
        return False

    if validate_citation_footer_contract_shape(contract):
        return False
    expected_boundary = hash_payload(
        {
            "event_id": answer_card.get("event", {}).get("event_id", ""),
            "event_hash": answer_card.get("event", {}).get("event_hash", ""),
            "rendered_output_hash": stable_hash(rendered_output),
            "answer_card_hash": answer_card.get("card_hash", ""),
            "source_verification_report_hash": source_verification_report.get(
                "report_hash",
                "",
            ),
            "source_confidence_report_hash": (
                source_confidence_report or {}
            ).get("report_hash", ""),
            "creator_license_contract_hash": (
                creator_license_contract or {}
            ).get("contract_hash", ""),
        }
    )
    event = contract.get("event", {})
    return (
        event.get("rendered_output_hash") == stable_hash(rendered_output)
        and event.get("response_boundary_hash") == expected_boundary
        and event.get("answer_card_hash") == answer_card.get("card_hash", "")
        and event.get("source_verification_report_hash")
        == source_verification_report.get("report_hash", "")
        and event.get("source_confidence_report_hash")
        == (source_confidence_report or {}).get("report_hash", "")
        and event.get("creator_license_contract_hash")
        == (creator_license_contract or {}).get("contract_hash", "")
        and contract.get("summary", {}).get("status") == "verified"
        and all(bool(value) for value in contract.get("verification", {}).values())
    )


def _verification_summary(
    *,
    rendered_output: str,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
    creator_license_contract: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    source_availability_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    answer_claim_coverage_report: dict[str, Any] | None,
    trace_exchange: dict[str, Any] | None,
    generation_context_closure_report: dict[str, Any] | None,
    source_boundary_report: dict[str, Any] | None,
    source_authenticity_report: dict[str, Any] | None,
    provider_card: dict[str, Any] | None,
    certification_report: dict[str, Any] | None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    output_hash = stable_hash(rendered_output)
    labels = source_labels_in_output(rendered_output)
    span_prefixes = span_hash_prefixes_in_output(rendered_output)
    card_event = answer_card.get("event", {})
    card_footer = answer_card.get("footer_checks", {})
    report_event = source_verification_report.get("event", {})
    report_answer_card = source_verification_report.get("answer_card", {})
    report_summary = source_verification_report.get("summary", {})
    provider_surfaces = (provider_card or {}).get("public_disclosure_surfaces", {})
    certification = _certification_summary(certification_report)
    availability_required = _required_by_certification(certification_report, 55)
    sufficiency_required = _required_by_certification(certification_report, 56)
    counterevidence_required = _required_by_certification(certification_report, 57)
    answer_coverage_required = _required_by_certification(certification_report, 59)
    context_closure_required = _required_by_certification(certification_report, 60)
    source_boundary_required = _required_by_certification(certification_report, 61)
    source_authenticity_required = _required_by_certification(certification_report, 64)
    source_confidence_errors = (
        verify_source_confidence_report(
            source_confidence_report,
            answer_card=answer_card,
            source_verification_report=source_verification_report,
            creator_license_contract=creator_license_contract,
            signing_secret=signing_secret,
        )
        if source_confidence_report and creator_license_contract
        else []
    )
    response_event_hash = card_event.get("event_hash", "")
    response_answer_hash = card_event.get("answer_hash", "")
    availability_shape_errors = (
        validate_source_availability_report_shape(source_availability_report)
        if source_availability_report
        else []
    )
    sufficiency_shape_errors = (
        validate_evidence_sufficiency_report_shape(evidence_sufficiency_report)
        if evidence_sufficiency_report
        else []
    )
    counterevidence_shape_errors = (
        validate_counterevidence_report_shape(counterevidence_report)
        if counterevidence_report
        else []
    )
    answer_coverage_shape_errors = (
        validate_answer_claim_coverage_report_shape(answer_claim_coverage_report)
        if answer_claim_coverage_report
        else []
    )
    context_closure_shape_errors = (
        validate_generation_context_closure_report_shape(
            generation_context_closure_report
        )
        if generation_context_closure_report
        else []
    )
    source_boundary_shape_errors = (
        validate_source_boundary_report_shape(source_boundary_report)
        if source_boundary_report
        else []
    )
    source_authenticity_shape_errors = (
        validate_source_authenticity_report_shape(source_authenticity_report)
        if source_authenticity_report
        else []
    )
    availability_verified = (
        bool(source_availability_report)
        and not availability_shape_errors
        and _report_hash_is_reproducible(source_availability_report)
        and _report_event_matches_response(
            source_availability_report,
            event_hash=response_event_hash,
            rendered_output_hash=output_hash,
            answer_hash=response_answer_hash,
        )
        and source_availability_report.get("summary", {}).get("status") == "verified"
        and source_availability_report.get("summary", {}).get(
            "all_public_sources_inspectable"
        )
        is True
        and not source_availability_report.get("issues")
    )
    sufficiency_verified = (
        bool(evidence_sufficiency_report)
        and not sufficiency_shape_errors
        and _report_hash_is_reproducible(evidence_sufficiency_report)
        and _report_event_matches_response(
            evidence_sufficiency_report,
            event_hash=response_event_hash,
            rendered_output_hash=output_hash,
            answer_hash=response_answer_hash,
        )
        and evidence_sufficiency_report.get("summary", {}).get("status") == "verified"
        and evidence_sufficiency_report.get("summary", {}).get(
            "all_claims_have_minimal_sufficient_evidence"
        )
        is True
        and not evidence_sufficiency_report.get("issues")
    )
    counterevidence_verified = (
        bool(counterevidence_report)
        and not counterevidence_shape_errors
        and _report_hash_is_reproducible(counterevidence_report)
        and _report_event_matches_response(
            counterevidence_report,
            event_hash=response_event_hash,
            rendered_output_hash=output_hash,
            answer_hash=response_answer_hash,
        )
        and counterevidence_report.get("summary", {}).get("status") == "verified"
        and counterevidence_report.get("summary", {}).get(
            "all_claims_counterevidence_adjudicated"
        )
        is True
        and int(
            counterevidence_report.get("summary", {}).get(
                "unaddressed_counterevidence_count",
                0,
            )
            or 0
        )
        == 0
        and not counterevidence_report.get("issues")
    )
    late_grounding_bound = _late_grounding_reports_bound(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
    )
    answer_coverage_errors = (
        verify_answer_claim_coverage_report(
            answer_claim_coverage_report,
            rendered_output=rendered_output,
            event_id=card_event.get("event_id", ""),
            event_hash=response_event_hash,
            answer_hash=response_answer_hash,
            answer_card=answer_card,
            source_verification_report=source_verification_report,
            evidence_sufficiency_report=evidence_sufficiency_report,
            counterevidence_report=counterevidence_report,
            citation_footer_contract=citation_footer_contract,
            signing_secret=signing_secret,
        )
        if answer_claim_coverage_report
        else []
    )
    answer_coverage_verified = (
        bool(answer_claim_coverage_report)
        and not answer_coverage_shape_errors
        and not answer_coverage_errors
        and answer_claim_coverage_report.get("summary", {}).get("status")
        == "verified"
        and answer_claim_coverage_report.get("summary", {}).get(
            "all_answer_claims_covered"
        )
        is True
        and not answer_claim_coverage_report.get("issues")
    )
    context_closure_errors = (
        verify_generation_context_closure_report(
            generation_context_closure_report,
            trace_exchange=trace_exchange or {},
            source_verification_report=source_verification_report,
            answer_claim_coverage_report=answer_claim_coverage_report,
            signing_secret=signing_secret,
        )
        if generation_context_closure_report
        else []
    )
    context_closure_verified = (
        bool(generation_context_closure_report)
        and bool(trace_exchange)
        and not context_closure_shape_errors
        and not context_closure_errors
        and generation_context_closure_report.get("summary", {}).get("status")
        == "verified"
        and generation_context_closure_report.get("summary", {}).get(
            "all_supported_claims_in_generation_context"
        )
        is True
        and not generation_context_closure_report.get("issues")
        and generation_context_closure_report.get("event", {}).get("trace_hash")
        == card_event.get("trace_hash", "")
    )
    source_boundary_errors = (
        verify_source_boundary_report(
            source_boundary_report,
            trace_exchange=trace_exchange or {},
            source_verification_report=source_verification_report,
            generation_context_closure_report=generation_context_closure_report
            or {},
            answer_claim_coverage_report=answer_claim_coverage_report,
            signing_secret=signing_secret,
        )
        if source_boundary_report
        else []
    )
    source_boundary_verified = (
        bool(source_boundary_report)
        and bool(trace_exchange)
        and bool(generation_context_closure_report)
        and not source_boundary_shape_errors
        and not source_boundary_errors
        and _report_event_matches_response(
            source_boundary_report,
            event_hash=response_event_hash,
            rendered_output_hash=output_hash,
            answer_hash=response_answer_hash,
        )
        and source_boundary_report.get("event", {}).get("trace_hash")
        == card_event.get("trace_hash", "")
        and source_boundary_report.get("event", {}).get(
            "generation_context_closure_report_hash"
        )
        == (generation_context_closure_report or {}).get("report_hash", "")
        and source_boundary_report.get("summary", {}).get("status") == "verified"
        and source_boundary_report.get("summary", {}).get(
            "all_context_blocks_boundary_isolated"
        )
        is True
        and not source_boundary_report.get("issues")
    )
    source_authenticity_verified = (
        bool(source_authenticity_report)
        and not source_authenticity_shape_errors
        and _report_hash_is_reproducible(source_authenticity_report)
        and _report_event_matches_response(
            source_authenticity_report,
            event_hash=response_event_hash,
            rendered_output_hash=output_hash,
            answer_hash=response_answer_hash,
        )
        and source_authenticity_report.get("event", {}).get(
            "source_availability_report_hash"
        )
        == (source_availability_report or {}).get("report_hash", "")
        and source_authenticity_report.get("event", {}).get(
            "source_boundary_report_hash"
        )
        == (source_boundary_report or {}).get("report_hash", "")
        and source_authenticity_report.get("event", {}).get(
            "creator_license_contract_hash"
        )
        == (creator_license_contract or {}).get("contract_hash", "")
        and source_authenticity_report.get("summary", {}).get("status")
        == "verified"
        and source_authenticity_report.get("summary", {}).get(
            "all_sources_authentic"
        )
        is True
        and int(
            source_authenticity_report.get("summary", {}).get(
                "escrow_recommended_count",
                0,
            )
            or 0
        )
        == 0
        and not source_authenticity_report.get("issues")
    )

    return {
        "rendered_output_hash_matches_answer_card": (
            card_event.get("rendered_output_hash") == output_hash
        ),
        "rendered_output_hash_matches_source_report": (
            report_event.get("rendered_output_hash") == output_hash
        ),
        "footer_source_labels_match_answer_card": (
            card_footer.get("source_labels") == labels
            and card_footer.get("source_labels_match") is True
        ),
        "footer_span_prefixes_cover_answer_card": all(
            prefix in span_prefixes
            for prefix in card_footer.get("expected_claim_span_prefixes", [])
        )
        and card_footer.get("claim_span_prefixes_match") is True,
        "source_report_bound_to_answer_card": (
            report_answer_card.get("answer_card_hash") == answer_card.get("card_hash")
            and report_answer_card.get("answer_card_bound") is True
        ),
        "source_report_verified": report_summary.get("status") == "verified"
        and report_summary.get("all_sources_materialized") is True
        and report_summary.get("all_supported_claims_materialized") is True,
        "source_confidence_report_verified": (
            not source_confidence_report
            or (
                bool(creator_license_contract)
                and not source_confidence_errors
                and source_confidence_report.get("summary", {}).get("status")
                == "verified"
                and source_confidence_report.get("summary", {}).get(
                    "hallucination_issue_count"
                )
                == 0
            )
        ),
        "citation_footer_contract_verified": (
            _citation_footer_contract_matches_response(
                contract=citation_footer_contract,
                rendered_output=rendered_output,
                answer_card=answer_card,
                source_verification_report=source_verification_report,
                source_confidence_report=source_confidence_report,
                creator_license_contract=creator_license_contract,
            )
        ),
        "source_availability_report_verified": (
            availability_verified or not availability_required and not source_availability_report
        ),
        "evidence_sufficiency_report_verified": (
            sufficiency_verified or not sufficiency_required and not evidence_sufficiency_report
        ),
        "counterevidence_report_verified": (
            counterevidence_verified or not counterevidence_required and not counterevidence_report
        ),
        "late_grounding_reports_bound": (
            late_grounding_bound or not counterevidence_required
        ),
        "answer_claim_coverage_report_verified": (
            answer_coverage_verified
            or not answer_coverage_required
            and not answer_claim_coverage_report
        ),
        "generation_context_closure_report_verified": (
            context_closure_verified
            or not context_closure_required
            and not generation_context_closure_report
        ),
        "source_boundary_report_verified": (
            source_boundary_verified
            or not source_boundary_required
            and not source_boundary_report
        ),
        "source_authenticity_report_verified": (
            source_authenticity_verified
            or not source_authenticity_required
            and not source_authenticity_report
        ),
        "provider_discloses_response_surface": (
            not provider_card
            or (
                provider_surfaces.get("answer_provenance_card") is True
                and provider_surfaces.get("source_verification_report") is True
                and provider_surfaces.get("response_envelope") is True
                and (
                    not source_confidence_report
                    or provider_surfaces.get("source_confidence_report") is True
                )
                and (
                    not citation_footer_contract
                    or provider_surfaces.get("citation_footer_contract") is True
                )
                and (
                    not source_availability_report
                    or provider_surfaces.get("source_availability_report") is True
                )
                and (
                    not evidence_sufficiency_report
                    or provider_surfaces.get("evidence_sufficiency_report") is True
                )
                and (
                    not counterevidence_report
                    or provider_surfaces.get("counterevidence_report") is True
                )
                and (
                    not answer_claim_coverage_report
                    or provider_surfaces.get("answer_claim_coverage_report") is True
                )
                and (
                    not generation_context_closure_report
                    or provider_surfaces.get("generation_context_closure_report")
                    is True
                )
                and (
                    not source_boundary_report
                    or provider_surfaces.get("source_boundary_report") is True
                )
                and (
                    not source_authenticity_report
                    or provider_surfaces.get("source_authenticity_report") is True
                )
            )
        ),
        "certification_meets_source_materialization_level": (
            not certification_report
            or (
                certification.get("status") == "passed"
                and _level_number(str(certification.get("highest_level", ""))) >= 20
            )
        ),
    }


def make_response_envelope(
    event: UsageEvent,
    *,
    answer_card: dict[str, Any],
    source_verification_report: dict[str, Any],
    source_confidence_report: dict[str, Any] | None = None,
    creator_license_contract: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    evidence_sufficiency_report: dict[str, Any] | None = None,
    counterevidence_report: dict[str, Any] | None = None,
    answer_claim_coverage_report: dict[str, Any] | None = None,
    trace_exchange: dict[str, Any] | None = None,
    generation_context_closure_report: dict[str, Any] | None = None,
    source_boundary_report: dict[str, Any] | None = None,
    source_authenticity_report: dict[str, Any] | None = None,
    public_receipt: dict[str, Any] | None = None,
    provider_card: dict[str, Any] | None = None,
    certification_report: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Package a rendered answer and public proof artifacts for API delivery."""

    artifacts = _embedded_artifacts(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_confidence_report=source_confidence_report,
        creator_license_contract=creator_license_contract,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        trace_exchange=trace_exchange,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        public_receipt=public_receipt,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    entries = _artifact_entries(artifacts)
    labels = source_labels_in_output(event.output)
    span_prefixes = span_hash_prefixes_in_output(event.output)
    verification = _verification_summary(
        rendered_output=event.output,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_confidence_report=source_confidence_report,
        creator_license_contract=creator_license_contract,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        trace_exchange=trace_exchange,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=signing_secret,
    )
    envelope = {
        "envelope_version": RESPONSE_ENVELOPE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "response": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "rendered_output": event.output,
            "rendered_output_hash": stable_hash(event.output),
            "answer_hash": stable_hash(event.answer_text or event.output),
            "source_labels": labels,
            "claim_span_prefixes": span_prefixes,
        },
        "embedded_artifacts": artifacts,
        "artifact_index": entries,
        "certification": _certification_summary(certification_report),
        "commitments": {
            "rendered_output_hash": stable_hash(event.output),
            "footer_label_root": hash_payload(labels),
            "footer_span_root": hash_payload(span_prefixes),
            "artifact_root": hash_payload(entries),
            "answer_card_hash": answer_card.get("card_hash", ""),
            "source_verification_report_hash": source_verification_report.get(
                "report_hash", ""
            ),
            "source_confidence_report_hash": (
                source_confidence_report or {}
            ).get("report_hash", ""),
            "creator_license_contract_hash": (
                creator_license_contract or {}
            ).get("contract_hash", ""),
            "citation_footer_contract_hash": (
                citation_footer_contract or {}
            ).get("contract_hash", ""),
            "source_availability_report_hash": (
                source_availability_report or {}
            ).get("report_hash", ""),
            "evidence_sufficiency_report_hash": (
                evidence_sufficiency_report or {}
            ).get("report_hash", ""),
            "counterevidence_report_hash": (
                counterevidence_report or {}
            ).get("report_hash", ""),
            "answer_claim_coverage_report_hash": (
                answer_claim_coverage_report or {}
            ).get("report_hash", ""),
            "trace_exchange_hash": (trace_exchange or {}).get("trace_hash", ""),
            "generation_context_closure_report_hash": (
                generation_context_closure_report or {}
            ).get("report_hash", ""),
            "source_boundary_report_hash": (
                source_boundary_report or {}
            ).get("report_hash", ""),
            "source_authenticity_report_hash": (
                source_authenticity_report or {}
            ).get("report_hash", ""),
            "provider_card_hash": (provider_card or {}).get("card_hash", ""),
            "certification_report_hash": (certification_report or {}).get(
                "report_hash", ""
            ),
            "public_receipt_hash": (public_receipt or {}).get("receipt_hash", ""),
        },
        "verification": verification,
        "summary": {
            "status": "verified"
            if all(bool(value) for value in verification.values())
            else "failed",
            "public_verification_profile": "rdllm-response-envelope-public/v1",
            "artifact_count": len(entries),
            "source_count": len(
                source_verification_report.get("sources", [])
            ),
            "claim_count": len(source_verification_report.get("claims", [])),
            "visible_footer_source_count": len(labels),
            "visible_footer_span_count": len(span_prefixes),
        },
        "privacy": {
            "rendered_output_disclosed": True,
            "prompt_text_disclosed": event.prompt in event.output,
            "private_prompt_payload_disclosed": False,
            "private_ledger_disclosed": False,
            "private_source_corpus_disclosed": False,
            "full_private_receipt_disclosed": False,
            "additional_private_source_text_disclosed": False,
        },
    }
    envelope["envelope_hash"] = hash_payload(_hashable_envelope(envelope))
    envelope["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_envelope(envelope), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return envelope


def validate_response_envelope_shape(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "envelope_version",
        "issuer",
        "created_at",
        "response",
        "embedded_artifacts",
        "artifact_index",
        "certification",
        "commitments",
        "verification",
        "summary",
        "privacy",
        "envelope_hash",
        "signature",
    )
    for key in required:
        if key not in envelope:
            errors.append(f"missing response envelope field: {key}")
    if errors:
        return errors
    if envelope.get("envelope_version") != RESPONSE_ENVELOPE_VERSION:
        errors.append("response envelope version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output",
        "rendered_output_hash",
        "answer_hash",
        "source_labels",
        "claim_span_prefixes",
    ):
        if key not in envelope.get("response", {}):
            errors.append(f"missing response envelope response field: {key}")
    artifacts = envelope.get("embedded_artifacts", {})
    if "answer_provenance_card" not in artifacts:
        errors.append("response envelope is missing answer provenance card")
    if "source_verification_report" not in artifacts:
        errors.append("response envelope is missing source verification report")
    return errors


def verify_response_envelope(
    envelope: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a response envelope using only public embedded artifacts."""

    errors = validate_response_envelope_shape(envelope)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_envelope(envelope))
    if expected_hash != envelope.get("envelope_hash"):
        errors.append("response envelope hash is not reproducible")

    response = envelope.get("response", {})
    rendered_output = str(response.get("rendered_output", ""))
    output_hash = stable_hash(rendered_output)
    labels = source_labels_in_output(rendered_output)
    span_prefixes = span_hash_prefixes_in_output(rendered_output)
    if response.get("rendered_output_hash") != output_hash:
        errors.append("response envelope rendered output hash does not match output")
    if response.get("source_labels") != labels:
        errors.append("response envelope source labels do not match output")
    if response.get("claim_span_prefixes") != span_prefixes:
        errors.append("response envelope claim spans do not match output")

    artifacts = envelope.get("embedded_artifacts", {})
    answer_card = artifacts.get("answer_provenance_card", {})
    source_report = artifacts.get("source_verification_report", {})
    source_confidence_report = artifacts.get("source_confidence_report")
    creator_license_contract = artifacts.get("creator_license_contract")
    citation_footer_contract = artifacts.get("citation_footer_contract")
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
    provider_card = artifacts.get("provider_attribution_card")
    certification_report = artifacts.get("certification_report")

    errors.extend(
        f"answer card: {error}"
        for error in validate_answer_provenance_card_shape(answer_card)
    )
    errors.extend(
        f"source verification report: {error}"
        for error in validate_source_verification_report_shape(source_report)
    )
    if source_confidence_report:
        errors.extend(
            f"source confidence report: {error}"
            for error in validate_source_confidence_report_shape(
                source_confidence_report
            )
        )
    if source_availability_report:
        errors.extend(
            f"source availability report: {error}"
            for error in validate_source_availability_report_shape(
                source_availability_report
            )
        )
    if evidence_sufficiency_report:
        errors.extend(
            f"evidence sufficiency report: {error}"
            for error in validate_evidence_sufficiency_report_shape(
                evidence_sufficiency_report
            )
        )
    if counterevidence_report:
        errors.extend(
            f"counterevidence report: {error}"
            for error in validate_counterevidence_report_shape(
                counterevidence_report
            )
        )
    if answer_claim_coverage_report:
        errors.extend(
            f"answer coverage report: {error}"
            for error in validate_answer_claim_coverage_report_shape(
                answer_claim_coverage_report
            )
        )
    if generation_context_closure_report:
        errors.extend(
            f"generation context closure report: {error}"
            for error in validate_generation_context_closure_report_shape(
                generation_context_closure_report
            )
        )
    if source_boundary_report:
        errors.extend(
            f"source boundary report: {error}"
            for error in validate_source_boundary_report_shape(
                source_boundary_report
            )
        )
    if source_authenticity_report:
        errors.extend(
            f"source authenticity report: {error}"
            for error in validate_source_authenticity_report_shape(
                source_authenticity_report
            )
        )
    if citation_footer_contract:
        from rdllm.citation_footer import (
            validate_citation_footer_contract_shape,
            verify_citation_footer_contract,
        )

        errors.extend(
            f"citation footer contract: {error}"
            for error in validate_citation_footer_contract_shape(
                citation_footer_contract
            )
        )
        errors.extend(
            f"citation footer contract: {error}"
            for error in verify_citation_footer_contract(
                citation_footer_contract,
                response_envelope=envelope,
                signing_secret=signing_secret,
            )
        )
    if provider_card:
        errors.extend(
            f"provider card: {error}"
            for error in validate_provider_card_shape(provider_card)
        )

    entries = _artifact_entries(artifacts)
    if entries != envelope.get("artifact_index"):
        errors.append("response envelope artifact index does not match artifacts")
    if envelope.get("commitments", {}).get("artifact_root") != hash_payload(entries):
        errors.append("response envelope artifact root is not reproducible")
    for entry in entries:
        artifact = artifacts.get(entry["name"], {})
        if not _artifact_declared_hash_is_reproducible(artifact):
            errors.append(
                f"response envelope embedded {entry['name']} hash is not reproducible"
            )

    expected_verification = _verification_summary(
        rendered_output=rendered_output,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence_report,
        creator_license_contract=creator_license_contract,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        trace_exchange=trace_exchange,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=signing_secret,
    )
    if envelope.get("verification") != expected_verification:
        errors.append("response envelope verification summary is not reproducible")
    if not all(bool(value) for value in expected_verification.values()):
        errors.append("response envelope public verification checks are not all true")

    commitments = envelope.get("commitments", {})
    if commitments.get("rendered_output_hash") != output_hash:
        errors.append("response envelope output commitment does not match output")
    if commitments.get("footer_label_root") != hash_payload(labels):
        errors.append("response envelope footer label root is not reproducible")
    if commitments.get("footer_span_root") != hash_payload(span_prefixes):
        errors.append("response envelope footer span root is not reproducible")
    if commitments.get("answer_card_hash") != answer_card.get("card_hash", ""):
        errors.append("response envelope answer card hash does not match artifact")
    if commitments.get("source_verification_report_hash") != source_report.get(
        "report_hash", ""
    ):
        errors.append("response envelope source report hash does not match artifact")
    if source_confidence_report and commitments.get(
        "source_confidence_report_hash"
    ) != source_confidence_report.get("report_hash", ""):
        errors.append(
            "response envelope source confidence report hash does not match artifact"
        )
    if creator_license_contract and commitments.get(
        "creator_license_contract_hash"
    ) != creator_license_contract.get("contract_hash", ""):
        errors.append(
            "response envelope creator license contract hash does not match artifact"
        )
    if citation_footer_contract and commitments.get(
        "citation_footer_contract_hash"
    ) != citation_footer_contract.get("contract_hash", ""):
        errors.append(
            "response envelope citation footer contract hash does not match artifact"
        )
    if source_availability_report and commitments.get(
        "source_availability_report_hash"
    ) != source_availability_report.get("report_hash", ""):
        errors.append(
            "response envelope source availability report hash does not match artifact"
        )
    if evidence_sufficiency_report and commitments.get(
        "evidence_sufficiency_report_hash"
    ) != evidence_sufficiency_report.get("report_hash", ""):
        errors.append(
            "response envelope evidence sufficiency report hash does not match artifact"
        )
    if counterevidence_report and commitments.get(
        "counterevidence_report_hash"
    ) != counterevidence_report.get("report_hash", ""):
        errors.append(
            "response envelope counterevidence report hash does not match artifact"
        )
    if answer_claim_coverage_report and commitments.get(
        "answer_claim_coverage_report_hash"
    ) != answer_claim_coverage_report.get("report_hash", ""):
        errors.append(
            "response envelope answer claim coverage report hash does not match artifact"
        )
    if trace_exchange and commitments.get("trace_exchange_hash") != trace_exchange.get(
        "trace_hash", ""
    ):
        errors.append("response envelope trace exchange hash does not match artifact")
    if generation_context_closure_report and commitments.get(
        "generation_context_closure_report_hash"
    ) != generation_context_closure_report.get("report_hash", ""):
        errors.append(
            "response envelope generation context closure report hash does not match artifact"
        )
    if source_boundary_report and commitments.get(
        "source_boundary_report_hash"
    ) != source_boundary_report.get("report_hash", ""):
        errors.append(
            "response envelope source boundary report hash does not match artifact"
        )
    if source_authenticity_report and commitments.get(
        "source_authenticity_report_hash"
    ) != source_authenticity_report.get("report_hash", ""):
        errors.append(
            "response envelope source authenticity report hash does not match artifact"
        )

    expected_status = (
        "verified" if all(bool(value) for value in expected_verification.values()) else "failed"
    )
    if envelope.get("summary", {}).get("status") != expected_status:
        errors.append("response envelope summary status is not reproducible")
    if envelope.get("privacy", {}).get("private_prompt_payload_disclosed") is not False:
        errors.append("response envelope must not disclose private prompt payload")
    if envelope.get("privacy", {}).get("private_source_corpus_disclosed") is not False:
        errors.append("response envelope must not disclose private source corpus")

    signature = envelope.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_envelope(envelope), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("response envelope is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("response envelope signature is invalid")

    return errors
