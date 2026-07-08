"""OpenTelemetry-aligned trace exchange for RDLLM attribution events."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import (
    TRACE_EXCHANGE_VERSION,
    canonical_json,
    hash_payload,
    validate_receipt_shape,
)
from rdllm.text import stable_hash

OTEL_GENAI_SEMCONV = "https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/"
TRACE_SCHEMA_URL = "https://rdllm.local/schemas/trace_exchange/v1"
SOURCE_BOUNDARY_PROFILE_VERSION = "rdllm-source-boundary-profile/v1"


def make_trace_exchange(
    event: UsageEvent | None = None,
    *,
    receipt: dict[str, Any] | None = None,
    provider_name: str = "rdllm.reference",
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Create a portable trace that binds accessed sources to citations and claims."""

    if receipt is not None:
        receipt_errors = validate_receipt_shape(receipt)
        if receipt_errors:
            raise ValueError(f"invalid attribution receipt: {receipt_errors}")
        payload = receipt["payload"]
        receipt_hash = receipt["receipt_hash"]
    elif event is not None:
        payload = _payload_from_event(event)
        receipt_hash = ""
    else:
        raise ValueError("event or receipt is required")

    event_payload = payload["event"]
    model = payload.get("model", {})
    grounding = payload.get("grounding", {})
    root_span_id = _span_id(event_payload["event_id"], "generation")
    resolved_trace_id = trace_id or stable_hash(f"trace:{event_payload['event_hash']}")[:32]

    spans = [
        _generation_span(
            resolved_trace_id,
            root_span_id,
            payload,
            receipt_hash=receipt_hash,
            provider_name=provider_name,
        )
    ]
    for access in grounding.get("source_accesses", []):
        spans.append(
            _source_access_span(
                resolved_trace_id,
                root_span_id,
                event_payload["event_id"],
                access,
                provider_name=provider_name,
                model=model,
            )
        )
    for source in grounding.get("sources", []):
        spans.append(
            _citation_span(
                resolved_trace_id,
                root_span_id,
                event_payload["event_id"],
                source,
            )
        )
    for index, claim in enumerate(grounding.get("claims", []), start=1):
        spans.append(
            _claim_span(
                resolved_trace_id,
                root_span_id,
                event_payload["event_id"],
                index,
                claim,
            )
        )

    trace = {
        "trace_exchange_version": TRACE_EXCHANGE_VERSION,
        "schema_url": TRACE_SCHEMA_URL,
        "otel_semconv": OTEL_GENAI_SEMCONV,
        "trace_id": resolved_trace_id,
        "event_id": event_payload["event_id"],
        "event_hash": event_payload["event_hash"],
        "receipt_hash": receipt_hash,
        "provider": {
            "name": provider_name,
            "model_id": model.get("id", ""),
            "model_version": model.get("version", ""),
            "route_id": model.get("route_id", ""),
        },
        "summary": {
            "source_access_count": len(grounding.get("source_accesses", [])),
            "visible_source_count": len(grounding.get("sources", [])),
            "claim_count": len(grounding.get("claims", [])),
            "attribution_gap_verdict": grounding.get("attribution_gap", {}).get(
                "verdict", ""
            ),
            "source_access_trace_hash": hash_payload(
                grounding.get("source_accesses", [])
            ),
            "source_reference_trace_hash": hash_payload(grounding.get("sources", [])),
            "claim_support_trace_hash": hash_payload(grounding.get("claims", [])),
        },
        "spans": spans,
    }
    trace["trace_hash"] = stable_hash(canonical_json(_hashable_trace(trace)))
    return trace


def verify_trace_exchange(
    trace: dict[str, Any],
    *,
    event: UsageEvent | None = None,
    receipt: dict[str, Any] | None = None,
) -> list[str]:
    """Verify a trace exchange against an event and/or attribution receipt."""

    errors = _validate_trace_shape(trace)
    if errors:
        return errors

    expected_hash = stable_hash(canonical_json(_hashable_trace(trace)))
    if trace.get("trace_hash") != expected_hash:
        errors.append("trace hash is not reproducible")

    if receipt is not None:
        receipt_errors = validate_receipt_shape(receipt)
        errors.extend(f"receipt: {error}" for error in receipt_errors)
        if not receipt_errors:
            payload = receipt["payload"]
            errors.extend(_verify_trace_against_payload(trace, payload))
            if trace.get("receipt_hash") != receipt.get("receipt_hash"):
                errors.append("trace receipt_hash does not match receipt")
            telemetry = payload.get("telemetry", {})
            if telemetry.get("trace_exchange_version") != TRACE_EXCHANGE_VERSION:
                errors.append("receipt trace exchange version is unsupported")
            if telemetry.get("source_access_trace_hash") != trace.get("summary", {}).get(
                "source_access_trace_hash"
            ):
                errors.append("trace source-access hash does not match receipt")
            if telemetry.get("source_reference_trace_hash") != trace.get(
                "summary", {}
            ).get("source_reference_trace_hash"):
                errors.append("trace source-reference hash does not match receipt")
            if telemetry.get("claim_support_trace_hash") != trace.get("summary", {}).get(
                "claim_support_trace_hash"
            ):
                errors.append("trace claim-support hash does not match receipt")

    if event is not None:
        errors.extend(_verify_trace_against_payload(trace, _payload_from_event(event)))

    return errors


def _generation_span(
    trace_id: str,
    span_id: str,
    payload: dict[str, Any],
    *,
    receipt_hash: str,
    provider_name: str,
) -> dict[str, Any]:
    event = payload["event"]
    model = payload.get("model", {})
    return {
        "name": "gen_ai.generate",
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": "",
        "kind": "CLIENT",
        "attributes": {
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": provider_name,
            "gen_ai.request.model": model.get("id", ""),
            "gen_ai.response.model": model.get("id", ""),
            "rdllm.span.kind": "generation",
            "rdllm.event.id": event["event_id"],
            "rdllm.event.hash": event["event_hash"],
            "rdllm.prompt.hash": event["prompt_hash"],
            "rdllm.answer.hash": event["answer_hash"],
            "rdllm.rendered_output.hash": event["rendered_output_hash"],
            "rdllm.receipt.hash": receipt_hash,
            "rdllm.attribution_gap.verdict": payload.get("grounding", {})
            .get("attribution_gap", {})
            .get("verdict", ""),
        },
    }


def _source_access_span(
    trace_id: str,
    parent_span_id: str,
    event_id: str,
    access: dict[str, Any],
    *,
    provider_name: str,
    model: dict[str, Any],
) -> dict[str, Any]:
    boundary_packet = {
        "profile": SOURCE_BOUNDARY_PROFILE_VERSION,
        "role": "evidence",
        "access_id": access["access_id"],
        "chunk_id": access["chunk_id"],
        "work_id": access["work_id"],
        "content_hash": access["content_hash"],
        "use": access.get("use", ""),
        "control_channel": False,
        "instruction_channel": False,
        "can_modify_attribution": False,
        "can_modify_payout": False,
        "content_hash_bound": True,
    }
    document = {
        "id": access["chunk_id"],
        "score": access.get("score", 0),
        "metadata": {
            "work_id": access.get("work_id", ""),
            "creator_id": access.get("creator_id", ""),
            "source_uri": access.get("source_uri", ""),
            "content_hash": access.get("content_hash", ""),
            "decision_status": access.get("decision_status", ""),
        },
    }
    return {
        "name": f"gen_ai.{access.get('access_type', 'source_access')}",
        "trace_id": trace_id,
        "span_id": _span_id(event_id, f"access:{access['access_id']}"),
        "parent_span_id": parent_span_id,
        "kind": "INTERNAL",
        "attributes": {
            "gen_ai.operation.name": access.get("access_type", "source_access"),
            "gen_ai.provider.name": provider_name,
            "gen_ai.request.model": model.get("id", ""),
            "gen_ai.data_source.id": stable_hash(
                access.get("source_uri") or access.get("work_id", "")
            )[:24],
            "gen_ai.retrieval.documents": [document],
            "rdllm.span.kind": "source_access",
            "rdllm.source.access_id": access["access_id"],
            "rdllm.source.access_type": access.get("access_type", ""),
            "rdllm.source.use": access.get("use", ""),
            "rdllm.source.chunk_id": access["chunk_id"],
            "rdllm.source.work_id": access["work_id"],
            "rdllm.source.creator_id": access["creator_id"],
            "rdllm.source.uri": access.get("source_uri", ""),
            "rdllm.source.content_hash": access["content_hash"],
            "rdllm.source.score": access.get("score", 0),
            "rdllm.source.rank": access.get("rank", 0),
            "rdllm.policy.allowed": access.get("policy_allowed", True),
            "rdllm.registry.allowed": access.get("registry_allowed", True),
            "rdllm.decision.status": access.get("decision_status", ""),
            "rdllm.matched_text.hash": access.get("matched_text_hash", ""),
            "rdllm.source.boundary.profile": SOURCE_BOUNDARY_PROFILE_VERSION,
            "rdllm.source.boundary.role": "evidence",
            "rdllm.source.boundary.control_channel": False,
            "rdllm.source.boundary.instruction_channel": False,
            "rdllm.source.boundary.can_modify_attribution": False,
            "rdllm.source.boundary.can_modify_payout": False,
            "rdllm.source.boundary.content_hash_bound": True,
            "rdllm.source.boundary.packet_hash": hash_payload(boundary_packet),
        },
    }


def _citation_span(
    trace_id: str,
    parent_span_id: str,
    event_id: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": "rdllm.citation",
        "trace_id": trace_id,
        "span_id": _span_id(event_id, f"citation:{source['label']}"),
        "parent_span_id": parent_span_id,
        "kind": "INTERNAL",
        "attributes": {
            "rdllm.span.kind": "citation",
            "rdllm.source.label": source["label"],
            "rdllm.source.chunk_id": source["chunk_id"],
            "rdllm.source.work_id": source["work_id"],
            "rdllm.source.creator_id": source["creator_id"],
            "rdllm.source.uri": source.get("source_uri", ""),
            "rdllm.source.content_hash": source["content_hash"],
            "rdllm.source.contribution_weight": source.get(
                "contribution_weight", "0"
            ),
            "rdllm.source.evidence_span_hashes": source.get(
                "evidence_span_hashes", []
            ),
        },
    }


def _claim_span(
    trace_id: str,
    parent_span_id: str,
    event_id: str,
    index: int,
    claim: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": "rdllm.claim_support",
        "trace_id": trace_id,
        "span_id": _span_id(event_id, f"claim:{index}"),
        "parent_span_id": parent_span_id,
        "kind": "INTERNAL",
        "attributes": {
            "rdllm.span.kind": "claim_support",
            "rdllm.claim.index": index,
            "rdllm.claim.hash": stable_hash(claim.get("claim", "")),
            "rdllm.claim.supported": claim.get("supported", False),
            "rdllm.claim.support_score": claim.get("support_score", 0),
            "rdllm.claim.source_label": claim.get("source_label", ""),
            "rdllm.claim.work_id": claim.get("work_id", ""),
            "rdllm.claim.chunk_id": claim.get("chunk_id", ""),
            "rdllm.claim.evidence_span_hash": claim.get("evidence_span_hash", ""),
            "rdllm.claim.evidence_start_char": claim.get("evidence_start_char", -1),
            "rdllm.claim.evidence_end_char": claim.get("evidence_end_char", -1),
        },
    }


def _verify_trace_against_payload(
    trace: dict[str, Any],
    payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    event = payload["event"]
    grounding = payload.get("grounding", {})
    if trace.get("event_id") != event["event_id"]:
        errors.append("trace event_id does not match payload")
    if trace.get("event_hash") != event["event_hash"]:
        errors.append("trace event_hash does not match payload")

    root_spans = _spans_by_kind(trace, "generation")
    if len(root_spans) != 1:
        errors.append("trace must contain exactly one generation span")
    elif root_spans[0].get("attributes", {}).get("rdllm.event.hash") != event[
        "event_hash"
    ]:
        errors.append("generation span event hash does not match payload")

    expected_accesses = {
        access["access_id"]: access for access in grounding.get("source_accesses", [])
    }
    actual_accesses = {
        span.get("attributes", {}).get("rdllm.source.access_id"): span
        for span in _spans_by_kind(trace, "source_access")
    }
    if set(actual_accesses) != set(expected_accesses):
        errors.append("trace source-access span set does not match payload")
    for access_id, access in expected_accesses.items():
        span = actual_accesses.get(access_id)
        if not span:
            continue
        attributes = span.get("attributes", {})
        for attr, key in (
            ("rdllm.source.chunk_id", "chunk_id"),
            ("rdllm.source.work_id", "work_id"),
            ("rdllm.source.creator_id", "creator_id"),
            ("rdllm.source.content_hash", "content_hash"),
            ("rdllm.decision.status", "decision_status"),
        ):
            if attributes.get(attr) != access.get(key):
                errors.append(f"trace source-access {key} mismatch for {access_id}")
        if round(float(attributes.get("rdllm.source.score", 0)), 8) != round(
            float(access.get("score", 0)), 8
        ):
            errors.append(f"trace source-access score mismatch for {access_id}")

    expected_citations = {
        source["label"]: source for source in grounding.get("sources", [])
    }
    actual_citations = {
        span.get("attributes", {}).get("rdllm.source.label"): span
        for span in _spans_by_kind(trace, "citation")
    }
    if set(actual_citations) != set(expected_citations):
        errors.append("trace citation span set does not match payload")
    for label, source in expected_citations.items():
        span = actual_citations.get(label)
        if not span:
            continue
        attributes = span.get("attributes", {})
        if attributes.get("rdllm.source.chunk_id") != source["chunk_id"]:
            errors.append(f"trace citation chunk mismatch for {label}")
        if attributes.get("rdllm.source.content_hash") != source["content_hash"]:
            errors.append(f"trace citation content hash mismatch for {label}")

    expected_claims = grounding.get("claims", [])
    actual_claims = _spans_by_kind(trace, "claim_support")
    if len(actual_claims) != len(expected_claims):
        errors.append("trace claim-support span count does not match payload")
    for index, claim in enumerate(expected_claims, start=1):
        span = next(
            (
                item
                for item in actual_claims
                if item.get("attributes", {}).get("rdllm.claim.index") == index
            ),
            None,
        )
        if not span:
            continue
        attributes = span.get("attributes", {})
        if attributes.get("rdllm.claim.hash") != stable_hash(claim.get("claim", "")):
            errors.append(f"trace claim hash mismatch for claim {index}")
        if attributes.get("rdllm.claim.evidence_span_hash") != claim.get(
            "evidence_span_hash", ""
        ):
            errors.append(f"trace evidence span mismatch for claim {index}")

    summary = trace.get("summary", {})
    if summary.get("source_access_count") != len(grounding.get("source_accesses", [])):
        errors.append("trace source-access count does not match payload")
    if summary.get("visible_source_count") != len(grounding.get("sources", [])):
        errors.append("trace visible-source count does not match payload")
    if summary.get("claim_count") != len(grounding.get("claims", [])):
        errors.append("trace claim count does not match payload")
    if summary.get("source_access_trace_hash") != hash_payload(
        grounding.get("source_accesses", [])
    ):
        errors.append("trace source-access summary hash does not match payload")
    if summary.get("source_reference_trace_hash") != hash_payload(
        grounding.get("sources", [])
    ):
        errors.append("trace source-reference summary hash does not match payload")
    if summary.get("claim_support_trace_hash") != hash_payload(
        grounding.get("claims", [])
    ):
        errors.append("trace claim-support summary hash does not match payload")
    return errors


def _validate_trace_shape(trace: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "trace_exchange_version",
        "trace_id",
        "event_id",
        "event_hash",
        "provider",
        "summary",
        "spans",
        "trace_hash",
    )
    for key in required:
        if key not in trace:
            errors.append(f"missing trace field: {key}")
    if errors:
        return errors
    if trace.get("trace_exchange_version") != TRACE_EXCHANGE_VERSION:
        errors.append("trace exchange version is unsupported")
    if not isinstance(trace.get("spans"), list):
        errors.append("trace spans must be a list")
    return errors


def _spans_by_kind(trace: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [
        span
        for span in trace.get("spans", [])
        if span.get("attributes", {}).get("rdllm.span.kind") == kind
    ]


def _payload_from_event(event: UsageEvent) -> dict[str, Any]:
    source_accesses = [access.to_dict() for access in event.source_accesses]
    sources = [source.to_dict() for source in event.source_references]
    claims = [claim.to_dict() for claim in event.claim_support]
    return {
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "prompt_hash": stable_hash(event.prompt),
            "answer_hash": stable_hash(event.answer_text or event.output),
            "rendered_output_hash": stable_hash(event.output),
        },
        "model": {
            "id": "model:unspecified",
            "version": "unknown",
            "route_id": "route:default",
        },
        "grounding": {
            "attribution_gap": event.attribution_gap,
            "source_accesses": source_accesses,
            "sources": sources,
            "claims": claims,
        },
        "telemetry": {
            "trace_exchange_version": TRACE_EXCHANGE_VERSION,
            "source_access_trace_hash": hash_payload(source_accesses),
            "source_reference_trace_hash": hash_payload(sources),
            "claim_support_trace_hash": hash_payload(claims),
        },
    }


def _span_id(event_id: str, name: str) -> str:
    return stable_hash(f"span:{event_id}:{name}")[:16]


def _hashable_trace(trace: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in trace.items() if key != "trace_hash"}
