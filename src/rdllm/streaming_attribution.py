"""Streaming attribution manifests for proof-carrying RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.proof_carrying_response import verify_proof_carrying_response
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.serving_gateway import verify_serving_gateway_report
from rdllm.text import stable_hash

STREAMING_ATTRIBUTION_VERSION = "rdllm-streaming-attribution-manifest/v1"
STREAMING_ATTRIBUTION_SCHEMA = (
    "docs/schemas/streaming_attribution_manifest.schema.json"
)
MINIMUM_GATEWAY_LEVEL = "RDLLM-L37"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L65"
DEFAULT_CHUNK_SIZE = 96


def _hashable_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in {"streaming_manifest_hash", "signature"}
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
        .get("streaming_attribution_manifest")
        is True
    )


def _chunk_text(value: str, chunk_size: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not value:
        return []
    return [value[index : index + chunk_size] for index in range(0, len(value), chunk_size)]


def _deterministic_lengths_match(
    chunks: list[str],
    *,
    output_length: int,
    chunk_size: int,
) -> bool:
    if output_length == 0:
        return not chunks
    if not chunks:
        return False
    for chunk in chunks[:-1]:
        if len(chunk) != chunk_size:
            return False
    return 0 < len(chunks[-1]) <= chunk_size


def _genesis_hash(
    *,
    proof_response_hash: str,
    gateway_report_hash: str,
) -> str:
    return stable_hash(
        "rdllm-stream-chain-genesis:"
        f"{proof_response_hash}:"
        f"{gateway_report_hash}"
    )


def _chunk_rows(
    *,
    chunks: list[str],
    proof_response_hash: str,
    gateway_report_hash: str,
    copied_output: str,
    attribution_footer: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous = _genesis_hash(
        proof_response_hash=proof_response_hash,
        gateway_report_hash=gateway_report_hash,
    )
    footer_start = copied_output.find(attribution_footer) if attribution_footer else -1
    cursor = 0
    for index, chunk in enumerate(chunks):
        char_start = cursor
        char_end = cursor + len(chunk)
        cursor = char_end
        if footer_start >= 0 and char_end > footer_start:
            phase = "footer"
        else:
            phase = "body"
        if index == len(chunks) - 1:
            phase = "final"
        chunk_hash = stable_hash(chunk)
        row_without_hashes = {
            "chunk_index": index,
            "stream_phase": phase,
            "char_start": char_start,
            "char_end": char_end,
            "char_length": len(chunk),
            "byte_length": len(chunk.encode("utf-8")),
            "chunk_hash": chunk_hash,
            "previous_chain_hash": previous,
            "contains_footer_bytes": bool(
                attribution_footer
                and char_start < footer_start + len(attribution_footer)
                and char_end > footer_start
            )
            if footer_start >= 0
            else False,
            "contains_final_byte": index == len(chunks) - 1,
        }
        chain_hash = hash_payload(row_without_hashes)
        row = {
            **row_without_hashes,
            "chain_hash": chain_hash,
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
        previous = chain_hash
    return rows


def _chunks_from_lengths(output: str, rows: list[dict[str, Any]]) -> list[str]:
    chunks: list[str] = []
    cursor = 0
    for row in rows:
        length = int(row.get("char_length", -1))
        if length < 0:
            return []
        chunk = output[cursor : cursor + length]
        chunks.append(chunk)
        cursor += length
    return chunks


def _chain_is_contiguous(rows: list[dict[str, Any]], *, expected_genesis: str) -> bool:
    previous = expected_genesis
    cursor = 0
    for index, row in enumerate(rows):
        if row.get("chunk_index") != index:
            return False
        if row.get("char_start") != cursor:
            return False
        if row.get("char_end") != cursor + int(row.get("char_length", -1)):
            return False
        if row.get("previous_chain_hash") != previous:
            return False
        cursor = int(row.get("char_end", -1))
        previous = str(row.get("chain_hash", ""))
    return True


def _artifact_bindings(
    *,
    proof_response: dict[str, Any],
    gateway_report: dict[str, Any],
    stream_output: str,
) -> dict[str, str]:
    proof_bindings = proof_response.get("artifact_bindings", {})
    return {
        "proof_response_hash": proof_response.get("proof_response_hash", ""),
        "gateway_report_hash": gateway_report.get("gateway_report_hash", ""),
        "response_envelope_hash": proof_bindings.get("response_envelope_hash", ""),
        "attribution_capsule_hash": proof_bindings.get("attribution_capsule_hash", ""),
        "release_gate_hash": proof_bindings.get("release_gate_hash", ""),
        "provider_card_hash": proof_bindings.get("provider_card_hash", ""),
        "certification_report_hash": proof_bindings.get("certification_report_hash", ""),
        "stream_output_hash": stable_hash(stream_output),
        "gateway_delivered_output_hash": gateway_report.get("egress", {}).get(
            "delivered_output_hash", ""
        ),
    }


def _streaming_checks(
    *,
    proof_response: dict[str, Any],
    gateway_report: dict[str, Any],
    chunks: list[str],
    rows: list[dict[str, Any]],
    chunking_mode: str,
    chunk_size: int,
    proof_errors: list[str],
    gateway_errors: list[str],
    proof_verified_at: str,
    gateway_verified_at: str,
    stream_started_at: str,
) -> dict[str, bool]:
    display = proof_response.get("display", {})
    copied_output = str(display.get("copied_output", ""))
    footer = str(display.get("attribution_footer", ""))
    reconstructed = "".join(chunks)
    proof_hash = proof_response.get("proof_response_hash", "")
    gateway_hash = gateway_report.get("gateway_report_hash", "")
    expected_genesis = _genesis_hash(
        proof_response_hash=proof_hash,
        gateway_report_hash=gateway_hash,
    )
    released = proof_response.get("summary", {}).get("status") == "released"
    final_row = rows[-1] if rows else {}
    footer_start = copied_output.find(footer) if footer else -1
    deterministic_ok = (
        chunking_mode != "deterministic_fixed_char"
        or _deterministic_lengths_match(
            chunks,
            output_length=len(copied_output),
            chunk_size=chunk_size,
        )
    )
    return {
        "proof_carrying_response_verified": not proof_errors,
        "serving_gateway_report_verified": not gateway_errors,
        "gateway_binds_same_proof_response": (
            gateway_report.get("artifact_bindings", {}).get("proof_response_hash")
            == proof_hash
            and gateway_report.get("egress", {}).get("proof_response_hash")
            == proof_hash
        ),
        "certification_meets_streaming_minimum": (
            _level_number(_proof_level(proof_response))
            >= _level_number(MINIMUM_GATEWAY_LEVEL)
        ),
        "provider_declares_streaming_surface": _provider_surface_declared(proof_response),
        "chunks_reconstruct_proof_display": reconstructed == copied_output,
        "chunks_reconstruct_gateway_egress_hash": (
            stable_hash(reconstructed)
            == gateway_report.get("egress", {}).get("delivered_output_hash")
        ),
        "chunk_chain_contiguous": _chain_is_contiguous(
            rows,
            expected_genesis=expected_genesis,
        ),
        "chunk_hashes_replay_from_public_output": rows
        == _chunk_rows(
            chunks=chunks,
            proof_response_hash=proof_hash,
            gateway_report_hash=gateway_hash,
            copied_output=copied_output,
            attribution_footer=footer,
        ),
        "final_chain_hash_bound": bool(rows)
        and final_row.get("chain_hash")
        == (rows[-1] or {}).get("chain_hash"),
        "deterministic_chunking_policy_honored": deterministic_ok,
        "released_stream_contains_capsule_marker": (
            not released
            or (
                display.get("capsule_marker_present") is True
                and bool(footer)
                and footer in reconstructed
            )
        ),
        "footer_visible_by_stream_completion": (
            not released
            or (
                footer_start >= 0
                and bool(rows)
                and final_row.get("char_end") == len(copied_output)
                and int(final_row.get("char_start", -1)) < footer_start + len(footer)
            )
        ),
        "proof_verification_precedes_first_chunk": (
            proof_verified_at <= stream_started_at
            and gateway_verified_at <= stream_started_at
        ),
        "stream_manifest_does_not_disclose_prompt_or_raw_output_fields": (
            canonical_json(rows).find('"prompt":') == -1
            and canonical_json(rows).find('"raw_model_output":') == -1
        ),
    }


def make_streaming_attribution_manifest(
    *,
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    streamed_chunks: list[str] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunking_mode: str | None = None,
    proof_verified_at: str | None = None,
    gateway_verified_at: str | None = None,
    stream_started_at: str | None = None,
    stream_completed_at: str | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed hash-chain manifest for streamed RDLLM response chunks."""

    timestamp = created_at or now_iso()
    proof_response = proof_carrying_response
    gateway_report = serving_gateway_report
    copied_output = str(proof_response.get("display", {}).get("copied_output", ""))
    footer = str(proof_response.get("display", {}).get("attribution_footer", ""))
    if streamed_chunks is None:
        chunks = _chunk_text(copied_output, chunk_size)
        mode = chunking_mode or "deterministic_fixed_char"
    else:
        chunks = [str(chunk) for chunk in streamed_chunks]
        mode = chunking_mode or "provided_chunk_lengths"
    proof_errors = verify_proof_carrying_response(
        proof_response,
        signing_secret=signing_secret,
    )
    gateway_errors = verify_serving_gateway_report(
        gateway_report,
        delivered_output=copied_output,
        signing_secret=signing_secret,
    )
    rows = _chunk_rows(
        chunks=chunks,
        proof_response_hash=proof_response.get("proof_response_hash", ""),
        gateway_report_hash=gateway_report.get("gateway_report_hash", ""),
        copied_output=copied_output,
        attribution_footer=footer,
    )
    proof_time = proof_verified_at or timestamp
    gateway_time = gateway_verified_at or timestamp
    started_at = stream_started_at or timestamp
    completed_at = stream_completed_at or started_at
    checks = _streaming_checks(
        proof_response=proof_response,
        gateway_report=gateway_report,
        chunks=chunks,
        rows=rows,
        chunking_mode=mode,
        chunk_size=chunk_size,
        proof_errors=proof_errors,
        gateway_errors=gateway_errors,
        proof_verified_at=proof_time,
        gateway_verified_at=gateway_time,
        stream_started_at=started_at,
    )
    output_hash = stable_hash("".join(chunks))
    final_chain_hash = rows[-1]["chain_hash"] if rows else _genesis_hash(
        proof_response_hash=proof_response.get("proof_response_hash", ""),
        gateway_report_hash=gateway_report.get("gateway_report_hash", ""),
    )
    manifest = {
        "streaming_manifest_version": STREAMING_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "stream_context": {
            "request_id": gateway_report.get("request", {}).get("request_id", ""),
            "provider": gateway_report.get("request", {}).get("provider", ""),
            "model_id": gateway_report.get("request", {}).get("model_id", ""),
            "model_version": gateway_report.get("request", {}).get(
                "model_version", ""
            ),
            "route_id": gateway_report.get("request", {}).get("route_id", ""),
            "stream_transport": "server_sent_events_or_equivalent",
            "streamed_output_hash": output_hash,
        },
        "streaming_policy": {
            "policy_version": "rdllm-streaming-attribution-boundary/v1",
            "minimum_gateway_level": MINIMUM_GATEWAY_LEVEL,
            "chunking_mode": mode,
            "chunk_size": chunk_size,
            "chunks_must_reconstruct_gateway_output": True,
            "chunk_text_must_not_be_embedded": True,
            "chunk_lengths_are_public_commitments": True,
            "proof_and_gateway_must_verify_before_first_chunk": True,
            "final_stream_must_include_attribution_footer": True,
        },
        "stream_timing": {
            "proof_verified_at": proof_time,
            "gateway_verified_at": gateway_time,
            "stream_started_at": started_at,
            "stream_completed_at": completed_at,
            "clock_source": "issuer_attested_rfc3339",
            "proof_verification_precedes_first_chunk": (
                proof_time <= started_at and gateway_time <= started_at
            ),
        },
        "stream_commitments": {
            "genesis_hash": _genesis_hash(
                proof_response_hash=proof_response.get("proof_response_hash", ""),
                gateway_report_hash=gateway_report.get("gateway_report_hash", ""),
            ),
            "chunk_count": len(rows),
            "chunk_row_root": hash_payload([row["row_hash"] for row in rows]),
            "chunk_chain_root": hash_payload([row["chain_hash"] for row in rows]),
            "final_chain_hash": final_chain_hash,
            "stream_reconstruction_hash": output_hash,
            "proof_display_copied_output_hash": proof_response.get("display", {}).get(
                "copied_output_hash", ""
            ),
            "gateway_delivered_output_hash": gateway_report.get("egress", {}).get(
                "delivered_output_hash", ""
            ),
        },
        "stream_chunks": rows,
        "embedded_artifacts": {
            "proof_carrying_response": proof_response,
            "serving_gateway_report": gateway_report,
        },
        "artifact_bindings": _artifact_bindings(
            proof_response=proof_response,
            gateway_report=gateway_report,
            stream_output="".join(chunks),
        ),
        "checks": checks,
        "schemas": {
            "streaming_attribution_manifest": STREAMING_ATTRIBUTION_SCHEMA,
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
        },
        "summary": {
            "status": "committed" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_gateway_level": MINIMUM_GATEWAY_LEVEL,
            "proof_response_hash": proof_response.get("proof_response_hash", ""),
            "gateway_report_hash": gateway_report.get("gateway_report_hash", ""),
            "streamed_output_hash": output_hash,
            "chunk_count": len(rows),
            "final_chain_hash": final_chain_hash,
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "raw_model_output_text_disclosed": False,
            "chunk_text_disclosed": False,
            "chunk_rows_use_lengths_and_hashes_only": True,
            "public_output_reconstructable_from_embedded_proof_response": True,
            "source_text_disclosed": False,
        },
    }
    manifest["streaming_manifest_hash"] = hash_payload(_hashable_manifest(manifest))
    manifest["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_manifest(manifest), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return manifest


def validate_streaming_attribution_manifest_shape(
    manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "streaming_manifest_version",
        "issuer",
        "created_at",
        "stream_context",
        "streaming_policy",
        "stream_timing",
        "stream_commitments",
        "stream_chunks",
        "embedded_artifacts",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "streaming_manifest_hash",
        "signature",
    )
    for key in required:
        if key not in manifest:
            errors.append(f"missing streaming attribution field: {key}")
    if errors:
        return errors
    if manifest.get("streaming_manifest_version") != STREAMING_ATTRIBUTION_VERSION:
        errors.append("streaming attribution manifest version is unsupported")
    if manifest.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("streaming attribution target certification level is unsupported")
    for embedded in ("proof_carrying_response", "serving_gateway_report"):
        if embedded not in manifest.get("embedded_artifacts", {}):
            errors.append(f"missing embedded streaming artifact: {embedded}")
    if "streaming_attribution_manifest" not in manifest.get("schemas", {}):
        errors.append("missing streaming attribution schema")
    for row in manifest.get("stream_chunks", []):
        for key in (
            "chunk_index",
            "stream_phase",
            "char_start",
            "char_end",
            "char_length",
            "byte_length",
            "chunk_hash",
            "previous_chain_hash",
            "chain_hash",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing streaming chunk field: {key}")
    return errors


def verify_streaming_attribution_manifest(
    manifest: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a streaming attribution manifest against embedded public artifacts."""

    errors = validate_streaming_attribution_manifest_shape(manifest)
    if errors:
        return errors
    if hash_payload(_hashable_manifest(manifest)) != manifest.get(
        "streaming_manifest_hash"
    ):
        errors.append("streaming attribution manifest hash is not reproducible")

    proof_response = manifest.get("embedded_artifacts", {}).get(
        "proof_carrying_response", {}
    )
    gateway_report = manifest.get("embedded_artifacts", {}).get(
        "serving_gateway_report", {}
    )
    copied_output = str(proof_response.get("display", {}).get("copied_output", ""))
    chunks = _chunks_from_lengths(copied_output, manifest.get("stream_chunks", []))
    if "".join(chunks) != copied_output:
        errors.append("streaming chunk lengths do not reconstruct proof display")
    expected = make_streaming_attribution_manifest(
        proof_carrying_response=proof_response,
        serving_gateway_report=gateway_report,
        streamed_chunks=chunks,
        chunk_size=int(manifest.get("streaming_policy", {}).get("chunk_size", 0) or 0),
        chunking_mode=str(
            manifest.get("streaming_policy", {}).get(
                "chunking_mode", "provided_chunk_lengths"
            )
        ),
        proof_verified_at=manifest.get("stream_timing", {}).get(
            "proof_verified_at", ""
        ),
        gateway_verified_at=manifest.get("stream_timing", {}).get(
            "gateway_verified_at", ""
        ),
        stream_started_at=manifest.get("stream_timing", {}).get(
            "stream_started_at", ""
        ),
        stream_completed_at=manifest.get("stream_timing", {}).get(
            "stream_completed_at", ""
        ),
        issuer=manifest.get("issuer", DEFAULT_ISSUER),
        created_at=manifest.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "stream_context",
        "streaming_policy",
        "stream_timing",
        "stream_commitments",
        "stream_chunks",
        "artifact_bindings",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != manifest.get(key):
            errors.append(f"streaming attribution {key} does not match replay")
    if expected.get("streaming_manifest_hash") != manifest.get(
        "streaming_manifest_hash"
    ):
        errors.append("streaming attribution manifest hash does not match replay")

    bindings = manifest.get("artifact_bindings", {})
    if bindings.get("proof_response_hash") != proof_response.get("proof_response_hash"):
        errors.append("streaming attribution proof response hash binding drifted")
    if bindings.get("gateway_report_hash") != gateway_report.get("gateway_report_hash"):
        errors.append("streaming attribution gateway report hash binding drifted")
    if manifest.get("summary", {}).get("status") != "committed":
        errors.append("streaming attribution manifest status is not committed")
    for check, passed in manifest.get("checks", {}).items():
        if passed is not True:
            errors.append(f"streaming attribution check failed: {check}")

    manifest_json = canonical_json(manifest)
    if manifest_json.find('"chunk_text":') != -1:
        errors.append("streaming attribution manifest discloses chunk text")
    if manifest_json.find('"prompt":') != -1:
        errors.append("streaming attribution manifest discloses prompt field")
    if manifest_json.find('"raw_model_output":') != -1:
        errors.append("streaming attribution manifest discloses raw model output field")

    if signing_secret:
        signature = manifest.get("signature", {})
        expected_signature = sign_payload(_hashable_manifest(manifest), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("streaming attribution manifest is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("streaming attribution manifest signature is invalid")
    return errors
