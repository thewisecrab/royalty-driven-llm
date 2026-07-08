"""Serving-time emission enforcement reports for RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

EMISSION_ENFORCEMENT_VERSION = "rdllm-emission-evidence-enforcement/v1"
EMISSION_ENFORCEMENT_SCHEMA = (
    "docs/schemas/emission_evidence_enforcement.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L83"
MINIMUM_INPUT_LEVEL = "RDLLM-L82"

DECLARED_HASH_FIELDS = (
    "streaming_manifest_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "report_hash",
    "contract_hash",
    "envelope_hash",
    "card_hash",
    "bundle_hash",
    "manifest_hash",
    "profile_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
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
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return hash_payload(_hashable_artifact(artifact)) == value
    return True


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _certification_level(proof_carrying_response: dict[str, Any]) -> str:
    return str(
        proof_carrying_response.get("embedded_artifacts", {})
        .get("certification_report", {})
        .get("summary", {})
        .get("highest_level", "")
    )


def _locked_rows_by_unit(
    evidence_locked_generation: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("unit_hash", "")): row
        for row in evidence_locked_generation.get("evidence_lock_rows", [])
        if row.get("unit_hash")
    }


def _emission_unit_rows(
    *,
    answer_claim_coverage_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    locks = _locked_rows_by_unit(evidence_locked_generation)
    rows: list[dict[str, Any]] = []
    proof_hash = _declared_hash(proof_carrying_response)
    gateway_hash = _declared_hash(serving_gateway_report)
    stream_hash = _declared_hash(streaming_attribution_manifest)
    stream_summary = streaming_attribution_manifest.get("summary", {})
    stream_bound = stream_summary.get("status") == "committed"
    for unit in answer_claim_coverage_report.get("answer_units", []):
        if unit.get("requires_support") is not True:
            continue
        unit_hash = str(unit.get("unit_hash", ""))
        lock = locks.get(unit_hash, {})
        row = {
            "unit_index": int(unit.get("unit_index", 0) or 0),
            "unit_hash": unit_hash,
            "unit_text_hash": str(unit.get("text_hash", "")),
            "claim_index": int(unit.get("matched_claim_index", 0) or 0),
            "source_label": str(unit.get("matched_source_label", "")),
            "evidence_span_prefix": str(unit.get("matched_evidence_span_prefix", "")),
            "evidence_lock_row_hash": str(lock.get("lock_row_hash", "")),
            "proof_response_hash": proof_hash,
            "gateway_report_hash": gateway_hash,
            "streaming_manifest_hash": stream_hash,
            "answer_unit_covered": unit.get("covered") is True,
            "matching_lock_found": bool(lock),
            "matching_lock_satisfied": lock.get("lock_satisfied") is True,
            "unit_text_hash_matches_lock": str(unit.get("text_hash", ""))
            == str(lock.get("unit_text_hash", "")),
            "source_label_matches_lock": str(unit.get("matched_source_label", ""))
            == str(lock.get("source_label", "")),
            "evidence_prefix_matches_lock": str(
                unit.get("matched_evidence_span_prefix", "")
            )
            == str(lock.get("evidence_span_prefix", "")),
            "stream_chain_bound": stream_bound,
        }
        row["emission_authorized"] = all(
            row[key]
            for key in (
                "answer_unit_covered",
                "matching_lock_found",
                "matching_lock_satisfied",
                "unit_text_hash_matches_lock",
                "source_label_matches_lock",
                "evidence_prefix_matches_lock",
                "stream_chain_bound",
            )
        )
        row["emission_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["unit_index"], row["claim_index"]))


def _artifact_bindings(
    *,
    response_envelope: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
) -> dict[str, str]:
    return {
        "response_envelope_hash": _declared_hash(response_envelope),
        "answer_claim_coverage_report_hash": _declared_hash(
            answer_claim_coverage_report
        ),
        "evidence_locked_generation_hash": _declared_hash(
            evidence_locked_generation
        ),
        "proof_carrying_response_hash": _declared_hash(proof_carrying_response),
        "serving_gateway_report_hash": _declared_hash(serving_gateway_report),
        "streaming_attribution_manifest_hash": _declared_hash(
            streaming_attribution_manifest
        ),
    }


def make_emission_evidence_enforcement_report(
    *,
    response_envelope: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report proving emitted output used satisfied pre-generation locks."""

    response = response_envelope.get("response", {})
    proof_display = proof_carrying_response.get("display", {})
    gateway_egress = serving_gateway_report.get("egress", {})
    stream_summary = streaming_attribution_manifest.get("summary", {})
    stream_context = streaming_attribution_manifest.get("stream_context", {})
    stream_timing = streaming_attribution_manifest.get("stream_timing", {})
    lock_window = evidence_locked_generation.get("generation_window", {})
    rows = _emission_unit_rows(
        answer_claim_coverage_report=answer_claim_coverage_report,
        evidence_locked_generation=evidence_locked_generation,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
    )
    support_required_count = int(
        answer_claim_coverage_report.get("summary", {}).get(
            "support_required_unit_count",
            0,
        )
        or 0
    )
    stream_output_hashes = {
        proof_display.get("copied_output_hash", ""),
        gateway_egress.get("delivered_output_hash", ""),
        stream_summary.get("streamed_output_hash", ""),
        stream_context.get("streamed_output_hash", ""),
        streaming_attribution_manifest.get("artifact_bindings", {}).get(
            "stream_output_hash",
            "",
        ),
    }
    stream_output_hashes.discard("")
    checks = {
        "certification_level_reaches_l82": _level_number(
            _certification_level(proof_carrying_response)
        )
        >= _level_number(MINIMUM_INPUT_LEVEL),
        "response_envelope_verified": response_envelope.get("summary", {}).get(
            "status"
        )
        == "verified",
        "answer_claim_coverage_verified": answer_claim_coverage_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and answer_claim_coverage_report.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L59",
        "evidence_locked_generation_ready": evidence_locked_generation.get(
            "summary", {}
        ).get("status")
        == "ready"
        and evidence_locked_generation.get("summary", {}).get(
            "target_certification_level"
        )
        == MINIMUM_INPUT_LEVEL,
        "proof_carrying_response_released": proof_carrying_response.get(
            "summary", {}
        ).get("status")
        == "released"
        and proof_carrying_response.get("summary", {}).get("decision") == "emit",
        "serving_gateway_served": serving_gateway_report.get("summary", {}).get(
            "status"
        )
        == "served",
        "streaming_manifest_committed": stream_summary.get("status") == "committed",
        "rendered_output_hash_bound_across_envelope_lock_and_proof": (
            response.get("rendered_output_hash")
            == evidence_locked_generation.get("response", {}).get(
                "rendered_output_hash"
            )
            == proof_display.get("rendered_output_hash")
        ),
        "stream_output_hash_bound_across_proof_gateway_and_stream": (
            len(stream_output_hashes) == 1
        ),
        "proof_response_hash_bound_to_gateway_and_stream": (
            _declared_hash(proof_carrying_response)
            == serving_gateway_report.get("artifact_bindings", {}).get(
                "proof_response_hash"
            )
            == gateway_egress.get("proof_response_hash")
            == stream_summary.get("proof_response_hash")
            == streaming_attribution_manifest.get("artifact_bindings", {}).get(
                "proof_response_hash"
            )
        ),
        "gateway_report_hash_bound_to_stream": (
            _declared_hash(serving_gateway_report)
            == stream_summary.get("gateway_report_hash")
            == streaming_attribution_manifest.get("artifact_bindings", {}).get(
                "gateway_report_hash"
            )
        ),
        "proof_and_gateway_verified_before_first_chunk": stream_timing.get(
            "proof_verification_precedes_first_chunk"
        )
        is True,
        "evidence_lock_precedes_generation_and_stream": (
            str(lock_window.get("lock_created_at", ""))
            <= str(lock_window.get("generation_started_at", ""))
            <= str(stream_timing.get("stream_started_at", ""))
        ),
        "all_support_units_have_satisfied_locks": len(rows)
        == support_required_count
        and all(row["emission_authorized"] for row in rows),
        "stream_chunks_replayable_and_contiguous": all(
            streaming_attribution_manifest.get("checks", {}).get(check) is True
            for check in (
                "chunk_chain_contiguous",
                "chunk_hashes_replay_from_public_output",
                "chunks_reconstruct_proof_display",
                "chunks_reconstruct_gateway_egress_hash",
            )
        ),
        "input_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                response_envelope,
                answer_claim_coverage_report,
                evidence_locked_generation,
                proof_carrying_response,
                serving_gateway_report,
                streaming_attribution_manifest,
            )
        ),
    }
    report = {
        "report_version": EMISSION_ENFORCEMENT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "emission_policy": {
            "profile": "rdllm-emission-evidence-enforcement-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "block_chunk_without_satisfied_evidence_lock": True,
            "streaming_gateway_and_proof_response_must_bind_same_output": True,
            "raw_answer_text_forbidden": True,
            "raw_source_text_forbidden": True,
            "raw_context_text_forbidden": True,
        },
        "artifact_bindings": _artifact_bindings(
            response_envelope=response_envelope,
            answer_claim_coverage_report=answer_claim_coverage_report,
            evidence_locked_generation=evidence_locked_generation,
            proof_carrying_response=proof_carrying_response,
            serving_gateway_report=serving_gateway_report,
            streaming_attribution_manifest=streaming_attribution_manifest,
        ),
        "emission_subject": {
            "event_id": response.get("event_id", ""),
            "event_hash": response.get("event_hash", ""),
            "rendered_output_hash": response.get("rendered_output_hash", ""),
            "copied_output_hash": proof_display.get("copied_output_hash", ""),
            "streamed_output_hash": stream_summary.get("streamed_output_hash", ""),
            "proof_response_hash": _declared_hash(proof_carrying_response),
            "gateway_report_hash": _declared_hash(serving_gateway_report),
            "streaming_manifest_hash": _declared_hash(
                streaming_attribution_manifest
            ),
        },
        "emission_timing": {
            "lock_created_at": lock_window.get("lock_created_at", ""),
            "generation_started_at": lock_window.get("generation_started_at", ""),
            "proof_verified_at": stream_timing.get("proof_verified_at", ""),
            "gateway_verified_at": stream_timing.get("gateway_verified_at", ""),
            "stream_started_at": stream_timing.get("stream_started_at", ""),
            "stream_completed_at": stream_timing.get("stream_completed_at", ""),
        },
        "emission_unit_rows": rows,
        "checks": checks,
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "support_required_unit_count": support_required_count,
            "emission_unit_count": len(rows),
            "authorized_emission_unit_count": sum(
                1 for row in rows if row["emission_authorized"]
            ),
            "streamed_chunk_count": int(stream_summary.get("chunk_count", 0) or 0),
            "final_chain_hash": stream_summary.get("final_chain_hash", ""),
            "serving_emission_enforced": all(checks.values()),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "context_text_disclosed": False,
            "prompt_text_disclosed": False,
            "claim_text_disclosed": False,
            "stream_chunk_text_disclosed": False,
            "stores_hashes_ids_counts_and_booleans_not_text": True,
        },
        "schemas": {
            "emission_evidence_enforcement": EMISSION_ENFORCEMENT_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "answer_claim_coverage_report": "docs/schemas/answer_claim_coverage_report.schema.json",
            "evidence_locked_generation": "docs/schemas/evidence_locked_generation.schema.json",
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
            "streaming_attribution_manifest": "docs/schemas/streaming_attribution_manifest.schema.json",
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


def validate_emission_evidence_enforcement_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "emission_policy",
        "artifact_bindings",
        "emission_subject",
        "emission_timing",
        "emission_unit_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing emission enforcement field: {key}")
    if errors:
        return errors
    if report.get("report_version") != EMISSION_ENFORCEMENT_VERSION:
        errors.append("emission enforcement version is unsupported")
    if (
        report.get("emission_policy", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("emission enforcement target certification level is unsupported")
    for key in (
        "response_envelope_hash",
        "answer_claim_coverage_report_hash",
        "evidence_locked_generation_hash",
        "proof_carrying_response_hash",
        "serving_gateway_report_hash",
        "streaming_attribution_manifest_hash",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing emission enforcement binding: {key}")
    if "emission_evidence_enforcement" not in report.get("schemas", {}):
        errors.append("missing emission enforcement schema")
    return errors


def verify_emission_evidence_enforcement_report(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    answer_claim_coverage_report: dict[str, Any],
    evidence_locked_generation: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an emission enforcement report against serving proof inputs."""

    errors = validate_emission_evidence_enforcement_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("emission enforcement hash is not reproducible")
    expected = make_emission_evidence_enforcement_report(
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        evidence_locked_generation=evidence_locked_generation,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "emission_policy",
        "artifact_bindings",
        "emission_subject",
        "emission_timing",
        "emission_unit_rows",
        "checks",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"emission enforcement {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("emission enforcement hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("emission enforcement status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"emission enforcement check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("emission enforcement is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("emission enforcement signature is invalid")
    return errors
