"""Conversation-level attribution continuity ledgers for RDLLM sessions."""

from __future__ import annotations

from typing import Any

from rdllm.proof_carrying_response import verify_proof_carrying_response
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.serving_gateway import verify_serving_gateway_report
from rdllm.streaming_attribution import verify_streaming_attribution_manifest
from rdllm.text import stable_hash

CONVERSATION_ATTRIBUTION_VERSION = "rdllm-conversation-attribution-ledger/v1"
CONVERSATION_ATTRIBUTION_SCHEMA = (
    "docs/schemas/conversation_attribution_ledger.schema.json"
)
MINIMUM_STREAMING_LEVEL = "RDLLM-L65"
MINIMUM_PROOF_LEVEL = "RDLLM-L37"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L66"


def _hashable_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key not in {"conversation_ledger_hash", "signature"}
    }


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _proof_level(proof_response: dict[str, Any]) -> str:
    return str(
        proof_response.get("embedded_artifacts", {})
        .get("certification_report", {})
        .get("summary", {})
        .get("highest_level", "")
    )


def _provider_surface_declared(proof_response: dict[str, Any]) -> bool:
    provider_card = (
        proof_response.get("embedded_artifacts", {})
        .get("provider_attribution_card", {})
    )
    return (
        provider_card.get("public_disclosure_surfaces", {})
        .get("conversation_attribution_ledger")
        is True
    )


def _source_section(output: str) -> str:
    start = output.find("\nSources\n")
    if start < 0 and output.startswith("Sources\n"):
        start = 0
    if start < 0:
        return ""
    end = output.find("\nGrounding:", start)
    if end < 0:
        end = output.find("\nClaim Evidence", start)
    if end < 0:
        end = len(output)
    return output[start:end].strip()


def _answer_sources(proof_response: dict[str, Any]) -> list[dict[str, Any]]:
    envelope = (
        proof_response.get("embedded_artifacts", {})
        .get("response_envelope", {})
    )
    card = envelope.get("embedded_artifacts", {}).get("answer_provenance_card", {})
    sources = card.get("sources", [])
    return [source for source in sources if isinstance(source, dict)]


def _source_obligation_rows(proof_response: dict[str, Any]) -> list[dict[str, Any]]:
    output = str(proof_response.get("display", {}).get("copied_output", ""))
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(_answer_sources(proof_response)):
        content_hash = str(source.get("content_hash", ""))
        core = {
            "obligation_type": "source_attribution_and_creator_pool_royalty",
            "label": str(source.get("label", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "creator_id": str(source.get("creator_id", "")),
            "creator_name": str(source.get("creator_name", "")),
            "source_uri": str(source.get("source_uri", "")),
            "content_hash": content_hash,
            "source_entry_hash": str(source.get("source_entry_hash", "")),
            "license": str(source.get("license", "")),
            "contribution_weight": str(source.get("contribution_weight", "")),
        }
        visibility = {
            "label_visible": bool(core["label"] and core["label"] in output),
            "chunk_id_visible": bool(core["chunk_id"] and core["chunk_id"] in output),
            "source_uri_visible": bool(
                core["source_uri"] and core["source_uri"] in output
            ),
            "content_hash_prefix_visible": bool(
                content_hash and content_hash[:12] in output
            ),
        }
        row = {
            "source_index": index,
            **core,
            "visibility": visibility,
            "obligation_hash": hash_payload(core),
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _turn_genesis_hash(conversation_id: str) -> str:
    return stable_hash(f"rdllm-conversation-chain-genesis:{conversation_id}")


def _turn_hash_without_row_hash(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"turn_chain_hash", "row_hash"}
    }


def _row_without_row_hash(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "row_hash"}


def _artifact_hashes(turns: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "proof_response_hashes": [
            str(turn.get("proof_carrying_response", {}).get("proof_response_hash", ""))
            for turn in turns
        ],
        "gateway_report_hashes": [
            str(turn.get("serving_gateway_report", {}).get("gateway_report_hash", ""))
            for turn in turns
        ],
        "streaming_manifest_hashes": [
            str(
                turn.get("streaming_attribution_manifest", {}).get(
                    "streaming_manifest_hash", ""
                )
            )
            for turn in turns
        ],
    }


def _turn_rows(
    *,
    conversation_id: str,
    turns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior_chain_hash = _turn_genesis_hash(conversation_id)
    prior_obligations: set[str] = set()
    turn_chain_hashes: dict[str, str] = {}
    for index, turn in enumerate(turns):
        proof = turn.get("proof_carrying_response", {})
        gateway = turn.get("serving_gateway_report", {})
        stream = turn.get("streaming_attribution_manifest", {})
        turn_id = str(turn.get("turn_id") or f"turn-{index + 1}")
        if "depends_on_turn_ids" in turn:
            depends_on_turn_ids = [
                str(item) for item in turn.get("depends_on_turn_ids", [])
            ]
        elif index == 0:
            depends_on_turn_ids = []
        else:
            depends_on_turn_ids = [str(rows[-1]["turn_id"])]
        parent_hashes = [
            turn_chain_hashes.get(parent_id, "") for parent_id in depends_on_turn_ids
        ]
        source_rows = _source_obligation_rows(proof)
        active_obligations = sorted(
            row["obligation_hash"] for row in source_rows if row.get("obligation_hash")
        )
        inherited_obligations = sorted(prior_obligations)
        propagated = sorted(set(active_obligations).intersection(prior_obligations))
        missing = sorted(prior_obligations.difference(active_obligations))
        source_footer = _source_section(
            str(proof.get("display", {}).get("copied_output", ""))
        )
        row = {
            "turn_index": index,
            "turn_id": turn_id,
            "depends_on_turn_ids": depends_on_turn_ids,
            "parent_turn_chain_hashes": parent_hashes,
            "previous_turn_chain_hash": prior_chain_hash,
            "proof_response_hash": str(proof.get("proof_response_hash", "")),
            "gateway_report_hash": str(gateway.get("gateway_report_hash", "")),
            "streaming_manifest_hash": str(
                stream.get("streaming_manifest_hash", "")
            ),
            "public_output_hash": str(
                proof.get("display", {}).get("copied_output_hash", "")
            ),
            "gateway_delivered_output_hash": str(
                gateway.get("egress", {}).get("delivered_output_hash", "")
            ),
            "source_footer_hash": stable_hash(source_footer),
            "source_count": len(source_rows),
            "visible_source_rows": source_rows,
            "active_obligation_hashes": active_obligations,
            "inherited_obligation_hashes": inherited_obligations,
            "propagated_obligation_hashes": propagated,
            "missing_inherited_obligation_hashes": missing,
            "continuing_obligation_hashes": sorted(
                set(active_obligations).union(prior_obligations)
            ),
        }
        row["turn_chain_hash"] = hash_payload(_turn_hash_without_row_hash(row))
        row["row_hash"] = hash_payload(_row_without_row_hash(row))
        rows.append(row)
        turn_chain_hashes[turn_id] = row["turn_chain_hash"]
        prior_chain_hash = row["turn_chain_hash"]
        prior_obligations = set(row["continuing_obligation_hashes"])
    return rows


def _turn_checks(
    *,
    turns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    signing_secret: str | None,
) -> dict[str, bool]:
    proof_errors: list[str] = []
    gateway_errors: list[str] = []
    streaming_errors: list[str] = []
    for turn in turns:
        proof = turn.get("proof_carrying_response", {})
        gateway = turn.get("serving_gateway_report", {})
        stream = turn.get("streaming_attribution_manifest", {})
        proof_errors.extend(
            verify_proof_carrying_response(proof, signing_secret=signing_secret)
        )
        gateway_errors.extend(
            verify_serving_gateway_report(
                gateway,
                delivered_output=str(proof.get("display", {}).get("copied_output", "")),
                signing_secret=signing_secret,
            )
        )
        if stream:
            streaming_errors.extend(
                verify_streaming_attribution_manifest(
                    stream,
                    signing_secret=signing_secret,
                )
            )
        else:
            streaming_errors.append("missing streaming attribution manifest")

    known_turn_ids: set[str] = set()
    parents_precede_children = True
    for row in rows:
        parents = row.get("depends_on_turn_ids", [])
        if any(parent not in known_turn_ids for parent in parents):
            parents_precede_children = False
        known_turn_ids.add(str(row.get("turn_id", "")))

    contiguous = bool(rows)
    for index, row in enumerate(rows):
        expected = (
            rows[index - 1]["turn_chain_hash"]
            if index > 0
            else row["previous_turn_chain_hash"]
        )
        if row.get("previous_turn_chain_hash") != expected:
            contiguous = False

    all_non_initial_depend_on_prior = all(
        index == 0 or rows[index - 1]["turn_id"] in row.get("depends_on_turn_ids", [])
        for index, row in enumerate(rows)
    )
    visible_rows_ok = all(
        all(row["visibility"].values())
        for turn in rows
        for row in turn.get("visible_source_rows", [])
    )
    inherited_visible = all(
        not row.get("missing_inherited_obligation_hashes") for row in rows
    )
    proof_levels = [
        _level_number(_proof_level(turn.get("proof_carrying_response", {})))
        for turn in turns
    ]
    streams_meet_minimum = all(
        turn.get("streaming_attribution_manifest", {})
        .get("summary", {})
        .get("status")
        == "committed"
        and turn.get("streaming_attribution_manifest", {})
        .get("summary", {})
        .get("target_certification_level")
        == MINIMUM_STREAMING_LEVEL
        for turn in turns
    )
    stream_hashes_match = all(
        row.get("streaming_manifest_hash")
        == turn.get("streaming_attribution_manifest", {}).get(
            "streaming_manifest_hash", ""
        )
        for row, turn in zip(rows, turns)
    )
    gateway_hashes_match = all(
        row.get("gateway_report_hash")
        == turn.get("serving_gateway_report", {}).get("gateway_report_hash", "")
        and row.get("gateway_delivered_output_hash")
        == turn.get("serving_gateway_report", {})
        .get("egress", {})
        .get("delivered_output_hash", "")
        for row, turn in zip(rows, turns)
    )
    proof_hashes_match = all(
        row.get("proof_response_hash")
        == turn.get("proof_carrying_response", {}).get("proof_response_hash", "")
        and row.get("public_output_hash")
        == turn.get("proof_carrying_response", {})
        .get("display", {})
        .get("copied_output_hash", "")
        for row, turn in zip(rows, turns)
    )
    row_chain_hashes_match = all(
        row.get("turn_chain_hash") == hash_payload(_turn_hash_without_row_hash(row))
        and row.get("row_hash") == hash_payload(_row_without_row_hash(row))
        for row in rows
    )
    return {
        "conversation_has_multiple_turns": len(rows) >= 2,
        "proof_carrying_responses_verified": not proof_errors,
        "serving_gateway_reports_verified": not gateway_errors,
        "streaming_manifests_verified": not streaming_errors,
        "proof_hashes_match_turn_rows": proof_hashes_match,
        "gateway_hashes_match_turn_rows": gateway_hashes_match,
        "streaming_hashes_match_turn_rows": stream_hashes_match,
        "turn_chain_contiguous": contiguous,
        "turn_row_hashes_replay": row_chain_hashes_match,
        "parent_turns_precede_children": parents_precede_children,
        "all_non_initial_turns_depend_on_prior_turn": all_non_initial_depend_on_prior,
        "inherited_source_obligations_propagated": inherited_visible,
        "visible_footers_cover_active_sources": visible_rows_ok,
        "visible_footers_cover_inherited_sources": inherited_visible and visible_rows_ok,
        "provider_declares_conversation_surface": all(
            _provider_surface_declared(turn.get("proof_carrying_response", {}))
            for turn in turns
        ),
        "certification_meets_conversation_minimum": bool(proof_levels)
        and min(proof_levels) >= _level_number(MINIMUM_PROOF_LEVEL)
        and streams_meet_minimum,
        "ledger_rows_do_not_disclose_prompt_or_raw_output_fields": (
            canonical_json(rows).find('"prompt":') == -1
            and canonical_json(rows).find('"raw_model_output":') == -1
        ),
    }


def make_conversation_attribution_ledger(
    *,
    conversation_id: str,
    turns: list[dict[str, Any]],
    session_state_id: str = "session:default",
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed ledger that carries source obligations across turns."""

    timestamp = created_at or now_iso()
    normalized_turns = [
        {
            "turn_id": str(turn.get("turn_id") or f"turn-{index + 1}"),
            "depends_on_turn_ids": (
                [str(item) for item in turn.get("depends_on_turn_ids", [])]
                if "depends_on_turn_ids" in turn
                else ([] if index == 0 else [str(turns[index - 1].get("turn_id") or f"turn-{index}")])
            ),
            "proof_carrying_response": turn.get("proof_carrying_response", {}),
            "serving_gateway_report": turn.get("serving_gateway_report", {}),
            "streaming_attribution_manifest": turn.get(
                "streaming_attribution_manifest", {}
            ),
        }
        for index, turn in enumerate(turns)
    ]
    rows = _turn_rows(
        conversation_id=conversation_id,
        turns=normalized_turns,
    )
    checks = _turn_checks(
        turns=normalized_turns,
        rows=rows,
        signing_secret=signing_secret,
    )
    first_gateway = (
        normalized_turns[0].get("serving_gateway_report", {}) if normalized_turns else {}
    )
    request = first_gateway.get("request", {})
    artifact_hashes = _artifact_hashes(normalized_turns)
    all_obligations = sorted(
        {
            obligation
            for row in rows
            for obligation in row.get("continuing_obligation_hashes", [])
        }
    )
    final_chain_hash = (
        rows[-1]["turn_chain_hash"] if rows else _turn_genesis_hash(conversation_id)
    )
    ledger = {
        "conversation_ledger_version": CONVERSATION_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "conversation_context": {
            "conversation_id": conversation_id,
            "conversation_id_hash": stable_hash(conversation_id),
            "session_state_id": session_state_id,
            "session_state_hash": stable_hash(session_state_id),
            "provider": request.get("provider", ""),
            "model_id": request.get("model_id", ""),
            "model_version": request.get("model_version", ""),
            "route_id": request.get("route_id", ""),
            "turn_count": len(rows),
            "state_transport": "conversation_object_previous_response_id_or_equivalent",
        },
        "continuity_policy": {
            "policy_version": "rdllm-conversation-attribution-continuity/v1",
            "minimum_streaming_level": MINIMUM_STREAMING_LEVEL,
            "minimum_proof_level": MINIMUM_PROOF_LEVEL,
            "dependent_turns_inherit_parent_source_obligations": True,
            "all_non_initial_turns_depend_on_immediate_prior_turn": True,
            "inherited_obligations_must_be_visible_in_current_footer": True,
            "streaming_manifest_required_for_each_turn": True,
            "proof_gateway_and_stream_must_verify_before_continuation": True,
        },
        "conversation_turns": rows,
        "embedded_artifacts": {
            "turns": normalized_turns,
        },
        "artifact_bindings": {
            **artifact_hashes,
            "turn_row_root": hash_payload([row["row_hash"] for row in rows]),
            "turn_chain_root": hash_payload(
                [row["turn_chain_hash"] for row in rows]
            ),
            "final_turn_chain_hash": final_chain_hash,
            "source_obligation_root": hash_payload(all_obligations),
        },
        "checks": checks,
        "schemas": {
            "conversation_attribution_ledger": CONVERSATION_ATTRIBUTION_SCHEMA,
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
            "streaming_attribution_manifest": "docs/schemas/streaming_attribution_manifest.schema.json",
        },
        "summary": {
            "status": "continued" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_streaming_level": MINIMUM_STREAMING_LEVEL,
            "conversation_id_hash": stable_hash(conversation_id),
            "turn_count": len(rows),
            "unique_source_obligation_count": len(all_obligations),
            "final_turn_chain_hash": final_chain_hash,
            "source_obligation_root": hash_payload(all_obligations),
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed_by_ledger_rows": False,
            "raw_model_output_text_disclosed_by_ledger_rows": False,
            "source_text_disclosed_by_ledger_rows": False,
            "public_outputs_remain_inside_embedded_proof_responses": True,
            "source_obligations_are_hash_and_metadata_commitments": True,
        },
    }
    ledger["conversation_ledger_hash"] = hash_payload(_hashable_ledger(ledger))
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


def validate_conversation_attribution_ledger_shape(
    ledger: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "conversation_ledger_version",
        "issuer",
        "created_at",
        "conversation_context",
        "continuity_policy",
        "conversation_turns",
        "embedded_artifacts",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "conversation_ledger_hash",
        "signature",
    )
    for key in required:
        if key not in ledger:
            errors.append(f"missing conversation attribution field: {key}")
    if errors:
        return errors
    if ledger.get("conversation_ledger_version") != CONVERSATION_ATTRIBUTION_VERSION:
        errors.append("conversation attribution ledger version is unsupported")
    if ledger.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("conversation attribution target certification level is unsupported")
    if "turns" not in ledger.get("embedded_artifacts", {}):
        errors.append("missing embedded conversation turns")
    if "conversation_attribution_ledger" not in ledger.get("schemas", {}):
        errors.append("missing conversation attribution schema")
    for row in ledger.get("conversation_turns", []):
        for key in (
            "turn_index",
            "turn_id",
            "depends_on_turn_ids",
            "parent_turn_chain_hashes",
            "previous_turn_chain_hash",
            "proof_response_hash",
            "gateway_report_hash",
            "streaming_manifest_hash",
            "public_output_hash",
            "source_footer_hash",
            "visible_source_rows",
            "active_obligation_hashes",
            "inherited_obligation_hashes",
            "propagated_obligation_hashes",
            "missing_inherited_obligation_hashes",
            "continuing_obligation_hashes",
            "turn_chain_hash",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing conversation turn field: {key}")
    return errors


def verify_conversation_attribution_ledger(
    ledger: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a conversation attribution ledger against embedded artifacts."""

    errors = validate_conversation_attribution_ledger_shape(ledger)
    if errors:
        return errors
    if hash_payload(_hashable_ledger(ledger)) != ledger.get(
        "conversation_ledger_hash"
    ):
        errors.append("conversation attribution ledger hash is not reproducible")

    embedded_turns = ledger.get("embedded_artifacts", {}).get("turns", [])
    rows = ledger.get("conversation_turns", [])
    turns = []
    for index, embedded in enumerate(embedded_turns):
        row = rows[index] if index < len(rows) else {}
        turns.append(
            {
                "turn_id": row.get("turn_id", embedded.get("turn_id", "")),
                "depends_on_turn_ids": row.get(
                    "depends_on_turn_ids",
                    embedded.get("depends_on_turn_ids", []),
                ),
                "proof_carrying_response": embedded.get("proof_carrying_response", {}),
                "serving_gateway_report": embedded.get("serving_gateway_report", {}),
                "streaming_attribution_manifest": embedded.get(
                    "streaming_attribution_manifest", {}
                ),
            }
        )
    expected = make_conversation_attribution_ledger(
        conversation_id=str(
            ledger.get("conversation_context", {}).get("conversation_id", "")
        ),
        session_state_id=str(
            ledger.get("conversation_context", {}).get("session_state_id", "")
        ),
        turns=turns,
        issuer=ledger.get("issuer", DEFAULT_ISSUER),
        created_at=ledger.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "conversation_context",
        "continuity_policy",
        "conversation_turns",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != ledger.get(key):
            errors.append(f"conversation attribution {key} does not match replay")
    if expected.get("conversation_ledger_hash") != ledger.get(
        "conversation_ledger_hash"
    ):
        errors.append("conversation attribution ledger hash does not match replay")

    if ledger.get("summary", {}).get("status") != "continued":
        errors.append("conversation attribution ledger status is not continued")
    for check, passed in ledger.get("checks", {}).items():
        if passed is not True:
            errors.append(f"conversation attribution check failed: {check}")

    rows_json = canonical_json(ledger.get("conversation_turns", []))
    if rows_json.find('"prompt":') != -1:
        errors.append("conversation attribution rows disclose prompt field")
    if rows_json.find('"raw_model_output":') != -1:
        errors.append("conversation attribution rows disclose raw model output field")
    if rows_json.find('"source_text":') != -1:
        errors.append("conversation attribution rows disclose source text field")

    if signing_secret:
        signature = ledger.get("signature", {})
        expected_signature = sign_payload(_hashable_ledger(ledger), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("conversation attribution ledger is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("conversation attribution ledger signature is invalid")
    return errors
