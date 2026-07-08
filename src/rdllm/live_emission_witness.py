"""Live emission witness quorum reports for RDLLM streaming responses."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

LIVE_EMISSION_WITNESS_VERSION = "rdllm-live-emission-witness/v1"
LIVE_EMISSION_WITNESS_SCHEMA = "docs/schemas/live_emission_witness.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L84"
MINIMUM_INPUT_LEVEL = "RDLLM-L83"
POLICY_VERSION = "rdllm-live-emission-witness-policy/v1"
DEFAULT_REQUIRED_QUORUM = 2
DEFAULT_MINIMUM_INDEPENDENT_ORGANIZATIONS = 2

DECLARED_HASH_FIELDS = (
    "live_witness_hash",
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

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "chunk_text",
    "raw_model_output",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}

REQUIRED_ATTESTATION_CHECKS = (
    "subject_hash_matches",
    "emission_enforcement_ready",
    "streaming_manifest_committed",
    "chunk_chain_committed",
    "witness_observed_in_phase_window",
    "raw_chunk_text_absent",
)


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"live_witness_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    return {
        key: value
        for key, value in (artifact or {}).items()
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


def _witness_key_hash(witness_id: str, witness_secret: str) -> str:
    return stable_hash(f"rdllm-live-emission-witness-key:{witness_id}:{witness_secret}")


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _normalise_witness_specs(
    witness_specs: list[dict[str, Any]] | None,
    *,
    witnesses: list[tuple[str, str]],
    preflight_observed_at: str,
    completion_observed_at: str,
) -> list[dict[str, Any]]:
    if witness_specs is None:
        specs = [
            {
                "witness_id": witness_id,
                "organization_id": f"org:{witness_id}",
                "role": "live_emission_boundary_witness",
                "trust_tier": "independent",
                "preflight_observed_at": preflight_observed_at,
                "completion_observed_at": completion_observed_at,
                "replay_verdict": "accepted",
            }
            for witness_id, _secret in witnesses
        ]
    else:
        specs = witness_specs

    rows: list[dict[str, Any]] = []
    for spec in specs:
        witness_id = str(spec.get("witness_id", "")).strip()
        if not witness_id:
            continue
        rows.append(
            {
                "witness_id": witness_id,
                "organization_id": str(
                    spec.get("organization_id") or f"org:{witness_id}"
                ),
                "role": str(spec.get("role") or "live_emission_boundary_witness"),
                "trust_tier": str(spec.get("trust_tier") or "independent"),
                "preflight_observed_at": str(
                    spec.get("preflight_observed_at") or preflight_observed_at
                ),
                "completion_observed_at": str(
                    spec.get("completion_observed_at") or completion_observed_at
                ),
                "replay_verdict": str(spec.get("replay_verdict") or "accepted"),
            }
        )
    return sorted(rows, key=lambda row: row["witness_id"])


def _emission_unit_root(report: dict[str, Any]) -> str:
    return hash_payload(
        [
            row.get("emission_row_hash", "")
            for row in report.get("emission_unit_rows", [])
        ]
    )


def _chunk_subject_rows(
    *,
    emission_evidence_enforcement: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    emission_hash = _declared_hash(emission_evidence_enforcement)
    stream_hash = _declared_hash(streaming_attribution_manifest)
    rows: list[dict[str, Any]] = []
    for chunk in streaming_attribution_manifest.get("stream_chunks", []):
        subject = {
            "chunk_index": int(chunk.get("chunk_index", 0) or 0),
            "stream_phase": str(chunk.get("stream_phase", "")),
            "char_start": int(chunk.get("char_start", 0) or 0),
            "char_end": int(chunk.get("char_end", 0) or 0),
            "char_length": int(chunk.get("char_length", 0) or 0),
            "byte_length": int(chunk.get("byte_length", 0) or 0),
            "chunk_hash": str(chunk.get("chunk_hash", "")),
            "chunk_row_hash": str(chunk.get("row_hash", "")),
            "chain_hash": str(chunk.get("chain_hash", "")),
            "previous_chain_hash": str(chunk.get("previous_chain_hash", "")),
            "emission_evidence_enforcement_hash": emission_hash,
            "streaming_manifest_hash": stream_hash,
            "chunk_admission_requires_witness_quorum": True,
        }
        subject["chunk_subject_hash"] = hash_payload(subject)
        rows.append(subject)
    return sorted(rows, key=lambda row: row["chunk_index"])


def _preflight_subject(
    *,
    emission_evidence_enforcement: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
) -> dict[str, Any]:
    bindings = emission_evidence_enforcement.get("artifact_bindings", {})
    timing = emission_evidence_enforcement.get("emission_timing", {})
    summary = emission_evidence_enforcement.get("summary", {})
    subject = {
        "subject_type": "rdllm-live-emission-preflight/v1",
        "emission_evidence_enforcement_hash": _declared_hash(
            emission_evidence_enforcement
        ),
        "streaming_manifest_hash": _declared_hash(streaming_attribution_manifest),
        "response_envelope_hash": bindings.get("response_envelope_hash", ""),
        "answer_claim_coverage_report_hash": bindings.get(
            "answer_claim_coverage_report_hash", ""
        ),
        "evidence_locked_generation_hash": bindings.get(
            "evidence_locked_generation_hash", ""
        ),
        "proof_response_hash": bindings.get("proof_carrying_response_hash", ""),
        "gateway_report_hash": bindings.get("serving_gateway_report_hash", ""),
        "lock_created_at": timing.get("lock_created_at", ""),
        "generation_started_at": timing.get("generation_started_at", ""),
        "stream_started_at": timing.get("stream_started_at", ""),
        "support_required_unit_count": int(
            summary.get("support_required_unit_count", 0) or 0
        ),
        "authorized_emission_unit_count": int(
            summary.get("authorized_emission_unit_count", 0) or 0
        ),
        "emission_unit_root": _emission_unit_root(emission_evidence_enforcement),
    }
    subject["subject_hash"] = hash_payload(subject)
    return subject


def _completion_subject(
    *,
    emission_evidence_enforcement: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
    chunk_subject_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    stream_summary = streaming_attribution_manifest.get("summary", {})
    stream_timing = streaming_attribution_manifest.get("stream_timing", {})
    subject = {
        "subject_type": "rdllm-live-emission-completion/v1",
        "emission_evidence_enforcement_hash": _declared_hash(
            emission_evidence_enforcement
        ),
        "streaming_manifest_hash": _declared_hash(streaming_attribution_manifest),
        "streamed_output_hash": stream_summary.get("streamed_output_hash", ""),
        "final_chain_hash": stream_summary.get("final_chain_hash", ""),
        "chunk_count": int(stream_summary.get("chunk_count", 0) or 0),
        "stream_completed_at": stream_timing.get("stream_completed_at", ""),
        "chunk_subject_root": hash_payload(
            [row["chunk_subject_hash"] for row in chunk_subject_rows]
        ),
        "chunk_row_root": hash_payload(
            [row.get("chunk_row_hash", "") for row in chunk_subject_rows]
        ),
    }
    subject["subject_hash"] = hash_payload(subject)
    return subject


def _attestation_payload(
    *,
    phase: str,
    subject: dict[str, Any],
    witness_id: str,
    organization_id: str,
    role: str,
    trust_tier: str,
    observed_at: str,
    replay_verdict: str,
    checks: dict[str, bool],
    witness_key_hash: str,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "witness_id": witness_id,
        "organization_id": organization_id,
        "role": role,
        "trust_tier": trust_tier,
        "observed_at": observed_at,
        "policy": POLICY_VERSION,
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "subject_hash": subject["subject_hash"],
        "emission_evidence_enforcement_hash": subject[
            "emission_evidence_enforcement_hash"
        ],
        "streaming_manifest_hash": subject["streaming_manifest_hash"],
        "replay_verdict": replay_verdict,
        "checks": checks,
        "witness_key_hash": witness_key_hash,
    }


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key != "attestation_hash"
    }


def _make_attestation(
    *,
    phase: str,
    subject: dict[str, Any],
    witness_spec: dict[str, Any],
    witness_secret: str,
    stream_started_at: str,
    stream_completed_at: str,
    emission_ready: bool,
    stream_committed: bool,
    chunk_chain_committed: bool,
    private_fields_absent: bool,
) -> dict[str, Any]:
    observed_at = (
        witness_spec["preflight_observed_at"]
        if phase == "preflight"
        else witness_spec["completion_observed_at"]
    )
    timing_valid = (
        observed_at <= stream_started_at
        if phase == "preflight"
        else observed_at >= stream_completed_at
    )
    checks = {
        "subject_hash_matches": bool(subject.get("subject_hash")),
        "emission_enforcement_ready": emission_ready,
        "streaming_manifest_committed": stream_committed,
        "chunk_chain_committed": chunk_chain_committed,
        "witness_observed_in_phase_window": timing_valid,
        "raw_chunk_text_absent": private_fields_absent,
    }
    witness_id = witness_spec["witness_id"]
    key_hash = _witness_key_hash(witness_id, witness_secret) if witness_secret else ""
    payload = _attestation_payload(
        phase=phase,
        subject=subject,
        witness_id=witness_id,
        organization_id=witness_spec["organization_id"],
        role=witness_spec["role"],
        trust_tier=witness_spec["trust_tier"],
        observed_at=observed_at,
        replay_verdict=witness_spec["replay_verdict"],
        checks=checks,
        witness_key_hash=key_hash,
    )
    row = {
        **payload,
        "signature_algorithm": "HMAC-SHA256" if witness_secret else "UNSIGNED",
        "signature": sign_payload(payload, witness_secret) if witness_secret else "",
    }
    row["attestation_hash"] = hash_payload(_hashable_attestation(row))
    return row


def _row_signature_valid(
    row: dict[str, Any],
    *,
    subjects: dict[str, dict[str, Any]],
    witness_secrets: dict[str, str],
) -> bool:
    witness_id = str(row.get("witness_id", ""))
    secret = witness_secrets.get(witness_id)
    subject = subjects.get(str(row.get("subject_hash", "")))
    if not secret or not subject:
        return False
    checks = {
        key: bool(value)
        for key, value in row.get("checks", {}).items()
        if key in REQUIRED_ATTESTATION_CHECKS
    }
    payload = _attestation_payload(
        phase=str(row.get("phase", "")),
        subject=subject,
        witness_id=witness_id,
        organization_id=str(row.get("organization_id", "")),
        role=str(row.get("role", "")),
        trust_tier=str(row.get("trust_tier", "")),
        observed_at=str(row.get("observed_at", "")),
        replay_verdict=str(row.get("replay_verdict", "")),
        checks=checks,
        witness_key_hash=_witness_key_hash(witness_id, secret),
    )
    return (
        row.get("signature_algorithm") == "HMAC-SHA256"
        and row.get("witness_key_hash") == _witness_key_hash(witness_id, secret)
        and row.get("signature") == sign_payload(payload, secret)
        and row.get("attestation_hash") == hash_payload(_hashable_attestation(row))
    )


def _phase_quorum(
    *,
    phase: str,
    rows: list[dict[str, Any]],
    subject_hash: str,
    subjects: dict[str, dict[str, Any]],
    witness_secrets: dict[str, str],
    required_quorum: int,
    minimum_independent_organizations: int,
) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        signature_valid = _row_signature_valid(
            row,
            subjects=subjects,
            witness_secrets=witness_secrets,
        )
        checks_pass = all(
            row.get("checks", {}).get(check) is True
            for check in REQUIRED_ATTESTATION_CHECKS
        )
        subject_matches = row.get("subject_hash") == subject_hash
        verdict = row.get("replay_verdict")
        if signature_valid and checks_pass and subject_matches and verdict == "accepted":
            accepted.append(row)
        elif signature_valid and verdict in {"rejected", "disputed"}:
            rejected.append(row)
        else:
            invalid.append(row)
    organizations = {
        str(row.get("organization_id", ""))
        for row in accepted
        if row.get("organization_id")
    }
    return {
        "phase": phase,
        "accepted_witness_count": len(accepted),
        "rejected_or_disputed_witness_count": len(rejected),
        "invalid_witness_count": len(invalid),
        "independent_organization_count": len(organizations),
        "accepted_witness_ids": sorted(str(row["witness_id"]) for row in accepted),
        "accepted_organization_ids": sorted(organizations),
        "quorum_met": len(accepted) >= required_quorum,
        "organization_quorum_met": len(organizations)
        >= minimum_independent_organizations,
        "no_disagreement": not rejected,
    }


def make_live_emission_witness_report(
    *,
    emission_evidence_enforcement: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
    witnesses: list[tuple[str, str]],
    witness_specs: list[dict[str, Any]] | None = None,
    required_quorum: int = DEFAULT_REQUIRED_QUORUM,
    minimum_independent_organizations: int = DEFAULT_MINIMUM_INDEPENDENT_ORGANIZATIONS,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a witness report proving live preflight and completion stream checks."""

    timestamp = created_at or now_iso()
    witness_secret_map = dict(witnesses)
    stream_timing = streaming_attribution_manifest.get("stream_timing", {})
    stream_summary = streaming_attribution_manifest.get("summary", {})
    stream_started_at = str(stream_timing.get("stream_started_at", timestamp))
    stream_completed_at = str(stream_timing.get("stream_completed_at", timestamp))
    specs = _normalise_witness_specs(
        witness_specs,
        witnesses=witnesses,
        preflight_observed_at=stream_started_at,
        completion_observed_at=stream_completed_at,
    )
    chunk_rows = _chunk_subject_rows(
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
    )
    preflight_subject = _preflight_subject(
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
    )
    completion_subject = _completion_subject(
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
        chunk_subject_rows=chunk_rows,
    )
    private_fields = _contains_private_fields(
        {
            "preflight_subject": preflight_subject,
            "completion_subject": completion_subject,
            "chunk_subject_rows": chunk_rows,
        }
    )
    emission_summary = emission_evidence_enforcement.get("summary", {})
    emission_ready = (
        emission_summary.get("status") == "ready"
        and emission_summary.get("target_certification_level") == MINIMUM_INPUT_LEVEL
        and emission_summary.get("serving_emission_enforced") is True
    )
    stream_committed = stream_summary.get("status") == "committed"
    chunk_chain_committed = (
        len(chunk_rows) == int(stream_summary.get("chunk_count", 0) or 0)
        and bool(chunk_rows)
    )
    attestations = [
        _make_attestation(
            phase=phase,
            subject=preflight_subject if phase == "preflight" else completion_subject,
            witness_spec=spec,
            witness_secret=witness_secret_map.get(spec["witness_id"], ""),
            stream_started_at=stream_started_at,
            stream_completed_at=stream_completed_at,
            emission_ready=emission_ready,
            stream_committed=stream_committed,
            chunk_chain_committed=chunk_chain_committed,
            private_fields_absent=not private_fields,
        )
        for spec in specs
        for phase in ("preflight", "completion")
    ]
    subjects = {
        preflight_subject["subject_hash"]: preflight_subject,
        completion_subject["subject_hash"]: completion_subject,
    }
    preflight_quorum = _phase_quorum(
        phase="preflight",
        rows=attestations,
        subject_hash=preflight_subject["subject_hash"],
        subjects=subjects,
        witness_secrets=witness_secret_map,
        required_quorum=required_quorum,
        minimum_independent_organizations=minimum_independent_organizations,
    )
    completion_quorum = _phase_quorum(
        phase="completion",
        rows=attestations,
        subject_hash=completion_subject["subject_hash"],
        subjects=subjects,
        witness_secrets=witness_secret_map,
        required_quorum=required_quorum,
        minimum_independent_organizations=minimum_independent_organizations,
    )
    artifact_bindings = {
        "emission_evidence_enforcement_hash": _declared_hash(
            emission_evidence_enforcement
        ),
        "streaming_attribution_manifest_hash": _declared_hash(
            streaming_attribution_manifest
        ),
        "proof_response_hash": emission_evidence_enforcement.get(
            "emission_subject", {}
        ).get("proof_response_hash", ""),
        "gateway_report_hash": emission_evidence_enforcement.get(
            "emission_subject", {}
        ).get("gateway_report_hash", ""),
        "final_chain_hash": stream_summary.get("final_chain_hash", ""),
    }
    checks = {
        "emission_evidence_enforcement_ready": emission_ready,
        "streaming_manifest_committed": stream_committed,
        "streaming_manifest_hash_matches_l83": artifact_bindings[
            "streaming_attribution_manifest_hash"
        ]
        == emission_evidence_enforcement.get("artifact_bindings", {}).get(
            "streaming_attribution_manifest_hash", ""
        ),
        "final_chain_hash_matches_l83": artifact_bindings["final_chain_hash"]
        == emission_summary.get("final_chain_hash", ""),
        "chunk_subjects_cover_stream_chunks": chunk_chain_committed,
        "preflight_witness_quorum_met": preflight_quorum["quorum_met"],
        "preflight_organization_quorum_met": preflight_quorum[
            "organization_quorum_met"
        ],
        "completion_witness_quorum_met": completion_quorum["quorum_met"],
        "completion_organization_quorum_met": completion_quorum[
            "organization_quorum_met"
        ],
        "no_witness_disagreement": preflight_quorum["no_disagreement"]
        and completion_quorum["no_disagreement"],
        "all_attestation_signatures_valid": all(
            _row_signature_valid(
                row,
                subjects=subjects,
                witness_secrets=witness_secret_map,
            )
            for row in attestations
        ),
        "input_hashes_reproducible": _artifact_hash_is_reproducible(
            emission_evidence_enforcement
        )
        and _artifact_hash_is_reproducible(streaming_attribution_manifest),
        "private_input_fields_absent": not private_fields,
    }
    report = {
        "witness_version": LIVE_EMISSION_WITNESS_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "witness_policy": {
            "policy_version": POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "required_quorum": required_quorum,
            "minimum_independent_organizations": minimum_independent_organizations,
            "preflight_quorum_required_before_first_chunk": True,
            "completion_quorum_required_after_final_chain": True,
            "raw_chunk_text_forbidden": True,
        },
        "artifact_bindings": artifact_bindings,
        "preflight_subject": preflight_subject,
        "completion_subject": completion_subject,
        "chunk_subject_rows": chunk_rows,
        "witness_attestations": sorted(
            attestations,
            key=lambda row: (row["phase"], row["subject_hash"], row["witness_id"]),
        ),
        "witness_quorum": {
            "preflight": preflight_quorum,
            "completion": completion_quorum,
        },
        "checks": checks,
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "witness_count": len(specs),
            "required_quorum": required_quorum,
            "minimum_independent_organizations": minimum_independent_organizations,
            "preflight_accepted_witness_count": preflight_quorum[
                "accepted_witness_count"
            ],
            "completion_accepted_witness_count": completion_quorum[
                "accepted_witness_count"
            ],
            "chunk_subject_count": len(chunk_rows),
            "final_chain_hash": artifact_bindings["final_chain_hash"],
            "live_emission_witnessed": all(checks.values()),
        },
        "privacy": {
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "context_text_disclosed": False,
            "prompt_text_disclosed": False,
            "claim_text_disclosed": False,
            "stream_chunk_text_disclosed": False,
            "stores_hashes_ids_counts_signatures_and_booleans_not_text": True,
        },
        "schemas": {
            "live_emission_witness": LIVE_EMISSION_WITNESS_SCHEMA,
            "emission_evidence_enforcement": "docs/schemas/emission_evidence_enforcement.schema.json",
            "streaming_attribution_manifest": "docs/schemas/streaming_attribution_manifest.schema.json",
        },
    }
    report["live_witness_hash"] = hash_payload(_hashable_report(report))
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


def validate_live_emission_witness_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "witness_version",
        "issuer",
        "created_at",
        "witness_policy",
        "artifact_bindings",
        "preflight_subject",
        "completion_subject",
        "chunk_subject_rows",
        "witness_attestations",
        "witness_quorum",
        "checks",
        "summary",
        "privacy",
        "schemas",
        "live_witness_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing live emission witness field: {key}")
    if errors:
        return errors
    if report.get("witness_version") != LIVE_EMISSION_WITNESS_VERSION:
        errors.append("live emission witness version is unsupported")
    if (
        report.get("witness_policy", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("live emission witness target certification level is unsupported")
    for key in (
        "emission_evidence_enforcement_hash",
        "streaming_attribution_manifest_hash",
        "proof_response_hash",
        "gateway_report_hash",
        "final_chain_hash",
    ):
        if key not in report.get("artifact_bindings", {}):
            errors.append(f"missing live emission witness binding: {key}")
    if "live_emission_witness" not in report.get("schemas", {}):
        errors.append("missing live emission witness schema")
    return errors


def _witness_specs_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    by_witness: dict[str, dict[str, Any]] = {}
    for row in report.get("witness_attestations", []):
        witness_id = str(row.get("witness_id", ""))
        if not witness_id:
            continue
        spec = by_witness.setdefault(
            witness_id,
            {
                "witness_id": witness_id,
                "organization_id": row.get("organization_id", ""),
                "role": row.get("role", ""),
                "trust_tier": row.get("trust_tier", ""),
                "replay_verdict": row.get("replay_verdict", ""),
            },
        )
        if row.get("phase") == "preflight":
            spec["preflight_observed_at"] = row.get("observed_at", "")
        elif row.get("phase") == "completion":
            spec["completion_observed_at"] = row.get("observed_at", "")
    return sorted(by_witness.values(), key=lambda item: item["witness_id"])


def verify_live_emission_witness_report(
    report: dict[str, Any],
    *,
    emission_evidence_enforcement: dict[str, Any],
    streaming_attribution_manifest: dict[str, Any],
    witnesses: list[tuple[str, str]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a live emission witness report against L83 and stream inputs."""

    errors = validate_live_emission_witness_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("live_witness_hash"):
        errors.append("live emission witness hash is not reproducible")
    expected = make_live_emission_witness_report(
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
        witnesses=witnesses,
        witness_specs=_witness_specs_from_report(report),
        required_quorum=int(report.get("witness_policy", {}).get("required_quorum", 0)),
        minimum_independent_organizations=int(
            report.get("witness_policy", {}).get(
                "minimum_independent_organizations",
                0,
            )
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "witness_policy",
        "artifact_bindings",
        "preflight_subject",
        "completion_subject",
        "chunk_subject_rows",
        "witness_attestations",
        "witness_quorum",
        "checks",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"live emission witness {key} does not match inputs")
    if expected.get("live_witness_hash") != report.get("live_witness_hash"):
        errors.append("live emission witness hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("live emission witness status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"live emission witness check failed: {check}")
    report_json = canonical_json(report)
    for private_key in ('"chunk_text":', '"prompt":', '"raw_model_output":'):
        if private_key in report_json:
            errors.append(f"live emission witness discloses private field {private_key}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("live emission witness report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("live emission witness report signature is invalid")
    return errors
