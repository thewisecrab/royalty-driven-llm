"""Agent and tool-call attribution ledgers for RDLLM evidence trajectories."""

from __future__ import annotations

from typing import Any

from rdllm.conversation_attribution import verify_conversation_attribution_ledger
from rdllm.proof_carrying_response import verify_proof_carrying_response
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.telemetry import verify_trace_exchange
from rdllm.text import stable_hash

AGENT_TOOL_ATTRIBUTION_VERSION = "rdllm-agent-tool-attribution-ledger/v1"
AGENT_TOOL_ATTRIBUTION_SCHEMA = (
    "docs/schemas/agent_tool_attribution_ledger.schema.json"
)
MINIMUM_CONVERSATION_LEVEL = "RDLLM-L66"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L67"


def _hashable_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key not in {"tool_ledger_hash", "signature"}
    }


def _provider_surface_declared(proof_response: dict[str, Any]) -> bool:
    provider_card = (
        proof_response.get("embedded_artifacts", {})
        .get("provider_attribution_card", {})
    )
    return (
        provider_card.get("public_disclosure_surfaces", {})
        .get("agent_tool_attribution_ledger")
        is True
    )


def _answer_card(proof_response: dict[str, Any]) -> dict[str, Any]:
    envelope = (
        proof_response.get("embedded_artifacts", {})
        .get("response_envelope", {})
    )
    card = envelope.get("embedded_artifacts", {}).get("answer_provenance_card", {})
    return card if isinstance(card, dict) else {}


def _event(proof_response: dict[str, Any], trace_exchange: dict[str, Any]) -> dict[str, str]:
    envelope = (
        proof_response.get("embedded_artifacts", {})
        .get("response_envelope", {})
    )
    response = envelope.get("response", {})
    return {
        "event_id": str(response.get("event_id", "")),
        "event_hash": str(response.get("event_hash", "")),
        "rendered_output_hash": str(response.get("rendered_output_hash", "")),
        "trace_event_id": str(trace_exchange.get("event_id", "")),
        "trace_event_hash": str(trace_exchange.get("event_hash", "")),
        "trace_hash": str(trace_exchange.get("trace_hash", "")),
        "proof_response_hash": str(proof_response.get("proof_response_hash", "")),
    }


def _spans_by_kind(trace_exchange: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [
        span
        for span in trace_exchange.get("spans", [])
        if span.get("attributes", {}).get("rdllm.span.kind") == kind
    ]


def _answer_sources(proof_response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        source
        for source in _answer_card(proof_response).get("sources", [])
        if isinstance(source, dict)
    ]


def _source_obligation_core(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "obligation_type": "source_attribution_and_creator_pool_royalty",
        "label": str(source.get("label", "")),
        "work_id": str(source.get("work_id", "")),
        "chunk_id": str(source.get("chunk_id", "")),
        "creator_id": str(source.get("creator_id", "")),
        "creator_name": str(source.get("creator_name", "")),
        "source_uri": str(source.get("source_uri", "")),
        "content_hash": str(source.get("content_hash", "")),
        "source_entry_hash": str(source.get("source_entry_hash", "")),
        "license": str(source.get("license", "")),
        "contribution_weight": str(source.get("contribution_weight", "")),
    }


def _obligation_hash(source: dict[str, Any]) -> str:
    return hash_payload(_source_obligation_core(source))


def _sources_by_chunk(proof_response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(source.get("chunk_id", "")): source for source in _answer_sources(proof_response)}


def _sources_by_label(proof_response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(source.get("label", "")): source for source in _answer_sources(proof_response)}


def _claim_rows(trace_exchange: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for span in _spans_by_kind(trace_exchange, "claim_support"):
        attrs = span.get("attributes", {})
        row = {
            "claim_index": int(attrs.get("rdllm.claim.index", 0) or 0),
            "claim_hash": str(attrs.get("rdllm.claim.hash", "")),
            "source_label": str(attrs.get("rdllm.claim.source_label", "")),
            "work_id": str(attrs.get("rdllm.claim.work_id", "")),
            "chunk_id": str(attrs.get("rdllm.claim.chunk_id", "")),
            "evidence_span_hash": str(
                attrs.get("rdllm.claim.evidence_span_hash", "")
            ),
            "supported": attrs.get("rdllm.claim.supported") is True,
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["claim_index"])


def _tool_type(access_type: str, source_uri: str) -> str:
    if source_uri.startswith("http://") or source_uri.startswith("https://"):
        return "web_search"
    if source_uri.startswith("file://"):
        return "file_search"
    if access_type in {"text_match", "retrieval"}:
        return "retrieval"
    return access_type or "tool_call"


def _conversation_obligations(conversation_ledger: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for turn in conversation_ledger.get("conversation_turns", [])
        for value in turn.get("continuing_obligation_hashes", [])
    }


def _tool_rows(
    *,
    proof_response: dict[str, Any],
    trace_exchange: dict[str, Any],
    conversation_ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    sources_by_chunk = _sources_by_chunk(proof_response)
    claims = _claim_rows(trace_exchange)
    conversation_obligations = _conversation_obligations(conversation_ledger)
    rows: list[dict[str, Any]] = []
    for index, span in enumerate(_spans_by_kind(trace_exchange, "source_access")):
        attrs = span.get("attributes", {})
        chunk_id = str(attrs.get("rdllm.source.chunk_id", ""))
        source = sources_by_chunk.get(chunk_id, {})
        source_uri = str(attrs.get("rdllm.source.uri", ""))
        access_id = str(attrs.get("rdllm.source.access_id", ""))
        access_type = str(attrs.get("rdllm.source.access_type", ""))
        obligation_hash = _obligation_hash(source) if source else ""
        related_claims = [
            claim
            for claim in claims
            if claim.get("chunk_id") == chunk_id
            or claim.get("source_label") == source.get("label", "")
        ]
        observation = {
            "source_access_id": access_id,
            "span_id": str(span.get("span_id", "")),
            "chunk_id": chunk_id,
            "work_id": str(attrs.get("rdllm.source.work_id", "")),
            "creator_id": str(attrs.get("rdllm.source.creator_id", "")),
            "source_uri": source_uri,
            "content_hash": str(attrs.get("rdllm.source.content_hash", "")),
            "decision_status": str(attrs.get("rdllm.decision.status", "")),
        }
        row = {
            "tool_call_index": index,
            "tool_call_id": f"tool:{access_id}",
            "tool_type": _tool_type(access_type, source_uri),
            "tool_name": access_type or "source_access",
            "tool_span_id": str(span.get("span_id", "")),
            "parent_generation_span_id": str(span.get("parent_span_id", "")),
            "input_commitment_hash": stable_hash(
                f"tool-input:{trace_exchange.get('event_hash', '')}:{access_id}"
            ),
            "observation_hash": hash_payload(observation),
            "source_access_id": access_id,
            "source_chunk_id": chunk_id,
            "source_work_id": str(attrs.get("rdllm.source.work_id", "")),
            "source_creator_id": str(attrs.get("rdllm.source.creator_id", "")),
            "source_uri_hash": stable_hash(source_uri),
            "content_hash": str(attrs.get("rdllm.source.content_hash", "")),
            "decision_status": str(attrs.get("rdllm.decision.status", "")),
            "visible_source_label": str(source.get("label", "")),
            "source_entry_hash": str(source.get("source_entry_hash", "")),
            "source_obligation_hash": obligation_hash,
            "claim_indexes": [claim["claim_index"] for claim in related_claims],
            "claim_hashes": [claim["claim_hash"] for claim in related_claims],
            "evidence_span_hashes": [
                claim["evidence_span_hash"]
                for claim in related_claims
                if claim.get("evidence_span_hash")
            ],
            "support_relation": "quotation_compression_or_inference"
            if related_claims
            else "unused_or_candidate_evidence",
            "tool_trace_span_bound": bool(span.get("span_id") and access_id),
            "tool_output_has_visible_source_row": bool(source),
            "tool_output_has_claim_support": bool(related_claims),
            "tool_output_has_obligation": bool(obligation_hash),
            "tool_obligation_in_conversation_ledger": (
                not conversation_obligations or obligation_hash in conversation_obligations
            ),
            "raw_tool_output_text_embedded": False,
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _artifact_bindings(
    *,
    proof_response: dict[str, Any],
    trace_exchange: dict[str, Any],
    conversation_ledger: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "proof_response_hash": proof_response.get("proof_response_hash", ""),
        "trace_exchange_hash": trace_exchange.get("trace_hash", ""),
        "conversation_ledger_hash": conversation_ledger.get(
            "conversation_ledger_hash", ""
        ),
        "tool_row_root": hash_payload([row["row_hash"] for row in rows]),
        "tool_observation_root": hash_payload(
            [row["observation_hash"] for row in rows]
        ),
        "source_obligation_root": hash_payload(
            sorted(
                {
                    row["source_obligation_hash"]
                    for row in rows
                    if row.get("source_obligation_hash")
                }
            )
        ),
        "claim_support_root": hash_payload(
            [row["claim_hashes"] for row in rows if row.get("claim_hashes")]
        ),
    }


def _checks(
    *,
    proof_response: dict[str, Any],
    trace_exchange: dict[str, Any],
    conversation_ledger: dict[str, Any],
    rows: list[dict[str, Any]],
    proof_errors: list[str],
    trace_errors: list[str],
    conversation_errors: list[str],
) -> dict[str, bool]:
    event = _event(proof_response, trace_exchange)
    answer_sources = _answer_sources(proof_response)
    source_labels = {str(source.get("label", "")) for source in answer_sources}
    row_labels = {row.get("visible_source_label", "") for row in rows}
    claims = _claim_rows(trace_exchange)
    row_claims = {
        int(index)
        for row in rows
        for index in row.get("claim_indexes", [])
    }
    visible_source_rows = [row for row in rows if row.get("visible_source_label")]
    return {
        "proof_carrying_response_verified": not proof_errors,
        "trace_exchange_hash_verified": not trace_errors,
        "conversation_ledger_verified": not conversation_errors,
        "trace_event_matches_proof_response": (
            bool(event["event_hash"])
            and event["event_hash"] == event["trace_event_hash"]
            and event["event_id"] == event["trace_event_id"]
        ),
        "tool_rows_cover_trace_source_access_spans": len(rows)
        == len(_spans_by_kind(trace_exchange, "source_access")),
        "tool_rows_cover_visible_answer_sources": source_labels.issubset(row_labels),
        "tool_rows_cover_supported_claims": {
            claim["claim_index"] for claim in claims if claim.get("supported")
        }.issubset(row_claims),
        "tool_observations_bind_source_obligations": all(
            row.get("tool_output_has_obligation") is True for row in visible_source_rows
        ),
        "tool_obligations_bound_to_conversation_ledger": all(
            row.get("tool_obligation_in_conversation_ledger") is True
            for row in visible_source_rows
        ),
        "tool_observations_have_claim_support_or_candidate_status": all(
            row.get("tool_output_has_claim_support") is True
            or row.get("support_relation") == "unused_or_candidate_evidence"
            for row in rows
        ),
        "provider_declares_agent_tool_surface": _provider_surface_declared(
            proof_response
        ),
        "certification_meets_tool_minimum": (
            conversation_ledger.get("summary", {}).get("status") == "continued"
            and conversation_ledger.get("summary", {}).get(
                "target_certification_level"
            )
            == MINIMUM_CONVERSATION_LEVEL
        ),
        "tool_ledger_rows_do_not_embed_private_or_raw_tool_text": (
            canonical_json(rows).find('"prompt":') == -1
            and canonical_json(rows).find('"raw_model_output":') == -1
            and canonical_json(rows).find('"tool_output_text":') == -1
            and all(row.get("raw_tool_output_text_embedded") is False for row in rows)
        ),
    }


def make_agent_tool_attribution_ledger(
    *,
    proof_carrying_response: dict[str, Any],
    trace_exchange: dict[str, Any],
    conversation_attribution_ledger: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed ledger binding tool observations to sources and claims."""

    timestamp = created_at or now_iso()
    proof_response = proof_carrying_response
    conversation_ledger = conversation_attribution_ledger
    rows = _tool_rows(
        proof_response=proof_response,
        trace_exchange=trace_exchange,
        conversation_ledger=conversation_ledger,
    )
    proof_errors = verify_proof_carrying_response(
        proof_response,
        signing_secret=signing_secret,
    )
    trace_errors = verify_trace_exchange(trace_exchange)
    conversation_errors = verify_conversation_attribution_ledger(
        conversation_ledger,
        signing_secret=signing_secret,
    )
    checks = _checks(
        proof_response=proof_response,
        trace_exchange=trace_exchange,
        conversation_ledger=conversation_ledger,
        rows=rows,
        proof_errors=proof_errors,
        trace_errors=trace_errors,
        conversation_errors=conversation_errors,
    )
    event = _event(proof_response, trace_exchange)
    ledger = {
        "tool_ledger_version": AGENT_TOOL_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "event": event,
        "tool_policy": {
            "policy_version": "rdllm-agent-tool-attribution-policy/v1",
            "minimum_conversation_level": MINIMUM_CONVERSATION_LEVEL,
            "tool_observations_must_bind_trace_spans": True,
            "visible_sources_must_bind_tool_observations": True,
            "supported_claims_must_bind_tool_observations": True,
            "tool_obligations_must_reach_conversation_ledger": True,
            "raw_tool_outputs_must_not_be_publicly_embedded": True,
        },
        "tool_calls": rows,
        "embedded_artifacts": {
            "proof_carrying_response": proof_response,
            "trace_exchange": trace_exchange,
            "conversation_attribution_ledger": conversation_ledger,
        },
        "artifact_bindings": _artifact_bindings(
            proof_response=proof_response,
            trace_exchange=trace_exchange,
            conversation_ledger=conversation_ledger,
            rows=rows,
        ),
        "checks": checks,
        "schemas": {
            "agent_tool_attribution_ledger": AGENT_TOOL_ATTRIBUTION_SCHEMA,
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "trace_exchange": "docs/schemas/trace_exchange.schema.json",
            "conversation_attribution_ledger": "docs/schemas/conversation_attribution_ledger.schema.json",
        },
        "summary": {
            "status": "bound" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_conversation_level": MINIMUM_CONVERSATION_LEVEL,
            "tool_call_count": len(rows),
            "visible_source_count": len(_answer_sources(proof_response)),
            "claim_count": len(_claim_rows(trace_exchange)),
            "tool_row_root": hash_payload([row["row_hash"] for row in rows]),
            "source_obligation_root": _artifact_bindings(
                proof_response=proof_response,
                trace_exchange=trace_exchange,
                conversation_ledger=conversation_ledger,
                rows=rows,
            )["source_obligation_root"],
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed_by_tool_rows": False,
            "raw_model_output_text_disclosed_by_tool_rows": False,
            "raw_tool_output_text_disclosed_by_tool_rows": False,
            "tool_inputs_are_hash_commitments": True,
            "tool_outputs_are_observation_hashes_and_source_metadata": True,
        },
    }
    ledger["tool_ledger_hash"] = hash_payload(_hashable_ledger(ledger))
    ledger["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_ledger(ledger), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return ledger


def validate_agent_tool_attribution_ledger_shape(
    ledger: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "tool_ledger_version",
        "issuer",
        "created_at",
        "event",
        "tool_policy",
        "tool_calls",
        "embedded_artifacts",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "tool_ledger_hash",
        "signature",
    )
    for key in required:
        if key not in ledger:
            errors.append(f"missing agent tool attribution field: {key}")
    if errors:
        return errors
    if ledger.get("tool_ledger_version") != AGENT_TOOL_ATTRIBUTION_VERSION:
        errors.append("agent tool attribution ledger version is unsupported")
    if ledger.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("agent tool attribution target certification level is unsupported")
    for embedded in (
        "proof_carrying_response",
        "trace_exchange",
        "conversation_attribution_ledger",
    ):
        if embedded not in ledger.get("embedded_artifacts", {}):
            errors.append(f"missing embedded agent tool artifact: {embedded}")
    if "agent_tool_attribution_ledger" not in ledger.get("schemas", {}):
        errors.append("missing agent tool attribution schema")
    for row in ledger.get("tool_calls", []):
        for key in (
            "tool_call_index",
            "tool_call_id",
            "tool_type",
            "tool_span_id",
            "input_commitment_hash",
            "observation_hash",
            "source_access_id",
            "source_chunk_id",
            "content_hash",
            "visible_source_label",
            "source_obligation_hash",
            "claim_indexes",
            "evidence_span_hashes",
            "tool_trace_span_bound",
            "tool_output_has_visible_source_row",
            "tool_output_has_claim_support",
            "tool_output_has_obligation",
            "tool_obligation_in_conversation_ledger",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing agent tool row field: {key}")
    return errors


def verify_agent_tool_attribution_ledger(
    ledger: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a tool attribution ledger against embedded public artifacts."""

    errors = validate_agent_tool_attribution_ledger_shape(ledger)
    if errors:
        return errors
    if hash_payload(_hashable_ledger(ledger)) != ledger.get("tool_ledger_hash"):
        errors.append("agent tool attribution ledger hash is not reproducible")

    embedded = ledger.get("embedded_artifacts", {})
    proof_response = embedded.get("proof_carrying_response", {})
    trace_exchange = embedded.get("trace_exchange", {})
    conversation_ledger = embedded.get("conversation_attribution_ledger", {})
    expected = make_agent_tool_attribution_ledger(
        proof_carrying_response=proof_response,
        trace_exchange=trace_exchange,
        conversation_attribution_ledger=conversation_ledger,
        issuer=ledger.get("issuer", DEFAULT_ISSUER),
        created_at=ledger.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "tool_policy",
        "tool_calls",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != ledger.get(key):
            errors.append(f"agent tool attribution {key} does not match replay")
    if expected.get("tool_ledger_hash") != ledger.get("tool_ledger_hash"):
        errors.append("agent tool attribution ledger hash does not match replay")

    if ledger.get("summary", {}).get("status") != "bound":
        errors.append("agent tool attribution ledger status is not bound")
    for check, passed in ledger.get("checks", {}).items():
        if passed is not True:
            errors.append(f"agent tool attribution check failed: {check}")

    rows_json = canonical_json(ledger.get("tool_calls", []))
    if rows_json.find('"prompt":') != -1:
        errors.append("agent tool attribution rows disclose prompt field")
    if rows_json.find('"raw_model_output":') != -1:
        errors.append("agent tool attribution rows disclose raw model output field")
    if rows_json.find('"tool_output_text":') != -1:
        errors.append("agent tool attribution rows disclose raw tool output text")

    if signing_secret:
        signature = ledger.get("signature", {})
        expected_signature = sign_payload(_hashable_ledger(ledger), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("agent tool attribution ledger is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("agent tool attribution ledger signature is invalid")
    return errors
