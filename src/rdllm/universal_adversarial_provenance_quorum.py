"""Universal adversarial provenance quorums.

The L173 layer hardens distributed attribution against spoofing, stripping,
credential replay, resolver split views, proxy rewrites, and downstream RAG
poisoning. L172 proves that attribution should survive distribution; L173 proves
that multiple independent provenance signals agree under adversarial tests
before high-stakes reliance or settlement is allowed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_VERSION = (
    "rdllm-universal-adversarial-provenance-quorum/v1"
)
UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_SCHEMA = (
    "docs/schemas/universal_adversarial_provenance_quorum.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L173"
MINIMUM_DISTRIBUTION_RELIANCE_LEVEL = "RDLLM-L172"
MINIMUM_WITNESS_QUORUM_LEVEL = "RDLLM-L153"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-adversarial-provenance-quorum.json"
)

REQUIRED_PROVENANCE_SIGNALS = (
    "visible_source_footer",
    "machine_readable_footer",
    "content_credential_manifest",
    "transparency_log_inclusion",
    "witness_quorum_signature",
    "status_resolver",
    "source_locator_health",
    "copy_body_hash",
    "perceptual_fingerprint",
    "watermark_or_marker",
    "settlement_meter_commitment",
    "creator_audit_index",
)

REQUIRED_ATTACK_CLASSES = (
    "manifest_substitution",
    "signature_replay",
    "footer_spoofing",
    "locator_phishing",
    "resolver_split_view",
    "watermark_removal",
    "perceptual_near_duplicate",
    "screenshot_crop",
    "pdf_metadata_strip",
    "api_proxy_rewrite",
    "downstream_rag_poisoning",
    "credential_time_shift",
    "creator_id_impersonation",
    "settlement_meter_fork",
    "private_payload_leak",
)

REQUIRED_RELIANCE_CONTEXTS = (
    "consumer_view",
    "publisher_embed",
    "enterprise_export",
    "api_customer_relay",
    "regulator_evidence",
    "creator_audit",
    "settlement_release",
    "downstream_training_or_rag_use",
)

DECLARED_HASH_FIELDS = (
    "universal_adversarial_provenance_quorum_hash",
    "universal_distribution_reliance_passport_hash",
    "universal_accountability_witness_quorum_hash",
    "universal_source_grounded_response_receipt_hash",
    "universal_content_credential_hash",
    "publication_witness_hash",
    "receipt_transparency_consistency_report_hash",
    "proof_dependency_graph_hash",
    "signal_hash",
    "l172_passport_hash",
    "witness_quorum_hash",
    "independent_observation_hash",
    "status_resolver_hash",
    "adversarial_test_hash",
    "attack_trace_hash",
    "context_hash",
    "minimum_signal_root_hash",
    "attack_root_hash",
    "verifier_hash",
    "fixture_hash",
    "trace_hash",
    "span_hash",
    "receipt_hash",
    "attestation_hash",
    "report_hash",
    "manifest_hash",
    "envelope_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "claim_text",
    "sentence_text",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "copied_output",
    "rendered_output",
    "distributed_output",
    "screenshot_pixels",
    "pdf_body",
    "attack_payload",
    "poisoned_document_text",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "streaming_transcript",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "authorization",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_adversarial_provenance_quorum_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L173 adversarial provenance quorum."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_quorum(quorum: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in quorum.items()
        if key not in {"universal_adversarial_provenance_quorum_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
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
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _level_number(level: Any) -> int | None:
    if not isinstance(level, str) or not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: Any, minimum: str) -> bool:
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(
    public_payload: dict[str, Any],
    quorum_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in quorum_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _distribution_passport_ready(passport: dict[str, Any] | None) -> bool:
    if not isinstance(passport, dict):
        return False
    summary = _summary(passport)
    decision = passport.get("distribution_reliance_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_DISTRIBUTION_RELIANCE_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("distribution_reliance_ready") is True
        and decision.get("third_party_reliance_allowed") is True
        and decision.get("content_credential_export_allowed") is True
        and decision.get("settlement_carry_forward_allowed") is True
    )


def _witness_quorum_ready(quorum: dict[str, Any] | None) -> bool:
    if not isinstance(quorum, dict):
        return False
    summary = _summary(quorum)
    decision = quorum.get("witness_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_WITNESS_QUORUM_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("universal_accountability_witness_quorum_authorized") is True
        and decision.get("provider_publication_trusted") is True
        and decision.get("customer_acceptance_allowed") is True
        and decision.get("regulator_reliance_allowed") is True
        and decision.get("split_view_risk_accepted") is False
        and not decision.get("failure_modes", [])
    )


def _signal_row_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "signal_hash",
        "l172_passport_hash",
        "witness_quorum_hash",
        "independent_observation_hash",
        "status_resolver_hash",
        "adversarial_test_hash",
        "verifier_hash",
    )
    required_flags = (
        "signal_present",
        "signal_independent",
        "signal_matches_l172",
        "witness_observed",
        "current_status_resolves",
        "spoof_resistant",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _attack_row_ready(row: dict[str, Any]) -> bool:
    return bool(row.get("fixture_hash")) and bool(row.get("attack_trace_hash")) and all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "signal_quorum_failed_closed",
            "reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
            "no_private_payloads",
        )
    )


def _reliance_context_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "context_hash",
        "minimum_signal_root_hash",
        "attack_root_hash",
        "l172_passport_hash",
        "witness_quorum_hash",
        "verifier_hash",
    )
    required_flags = (
        "context_supported",
        "quorum_threshold_met",
        "current_status_checked",
        "high_stakes_policy_applied",
        "reliance_allowed_only_on_quorum",
        "settlement_release_bound",
        "no_private_payloads",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _row_map(quorum_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = quorum_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate: Any,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name
        for name in required
        if name in rows and not predicate(rows.get(name, {}))
    ]
    return missing, incomplete


def make_universal_adversarial_provenance_quorum(
    quorum_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L173 universal adversarial provenance quorum."""

    distribution_passport = quorum_input.get("universal_distribution_reliance_passport")
    witness_quorum = quorum_input.get("universal_accountability_witness_quorum")
    signal_rows = _row_map(quorum_input, "provenance_signal_rows")
    attack_rows = _row_map(quorum_input, "attack_resistance_rows")
    context_rows = _row_map(quorum_input, "reliance_context_rows")

    missing_signals, incomplete_signals = _complete_rows(
        signal_rows,
        REQUIRED_PROVENANCE_SIGNALS,
        _signal_row_ready,
    )
    missing_attacks, incomplete_attacks = _complete_rows(
        attack_rows,
        REQUIRED_ATTACK_CLASSES,
        _attack_row_ready,
    )
    missing_contexts, incomplete_contexts = _complete_rows(
        context_rows,
        REQUIRED_RELIANCE_CONTEXTS,
        _reliance_context_ready,
    )

    checks = {
        "distribution_reliance_passport_bound": _artifact_hash_is_reproducible(
            distribution_passport if isinstance(distribution_passport, dict) else None
        ),
        "distribution_reliance_passport_l172_ready": _distribution_passport_ready(
            distribution_passport if isinstance(distribution_passport, dict) else None
        ),
        "accountability_witness_quorum_bound": _artifact_hash_is_reproducible(
            witness_quorum if isinstance(witness_quorum, dict) else None
        ),
        "accountability_witness_quorum_l153_ready": _witness_quorum_ready(
            witness_quorum if isinstance(witness_quorum, dict) else None
        ),
        "provenance_signal_rows_complete": not missing_signals
        and not incomplete_signals,
        "attack_resistance_rows_complete": not missing_attacks
        and not incomplete_attacks,
        "reliance_context_rows_complete": not missing_contexts
        and not incomplete_contexts,
        "adversarial_provenance_quorum_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    signal_root = merkle_root([
        hash_payload({"name": name, "row": signal_rows.get(name, {})})
        for name in REQUIRED_PROVENANCE_SIGNALS
    ])
    attack_root = merkle_root([
        hash_payload({"name": name, "row": attack_rows.get(name, {})})
        for name in REQUIRED_ATTACK_CLASSES
    ])
    context_root = merkle_root([
        hash_payload({"name": name, "row": context_rows.get(name, {})})
        for name in REQUIRED_RELIANCE_CONTEXTS
    ])

    public = {
        "universal_adversarial_provenance_quorum_version": (
            UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_VERSION
        ),
        "schema": UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-adversarial-provenance-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_distribution_reliance_level": (
                MINIMUM_DISTRIBUTION_RELIANCE_LEVEL
            ),
            "minimum_witness_quorum_level": MINIMUM_WITNESS_QUORUM_LEVEL,
            "single_provenance_signal_insufficient": True,
            "independent_witness_required": True,
            "adversarial_negative_fixtures_required": True,
            "resolver_split_view_rejection_required": True,
            "settlement_hold_required_on_quorum_failure": True,
            "private_payloads_forbidden_in_public_quorum": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_VERSION,
        },
        "distribution_passport_binding": {
            "present": isinstance(distribution_passport, dict),
            "artifact_hash": _declared_hash(
                distribution_passport
                if isinstance(distribution_passport, dict)
                else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    distribution_passport
                    if isinstance(distribution_passport, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["distribution_reliance_passport_bound"],
            "status": _summary(
                distribution_passport
                if isinstance(distribution_passport, dict)
                else None
            ).get("status", ""),
            "level": _summary(
                distribution_passport
                if isinstance(distribution_passport, dict)
                else None
            ).get("target_certification_level", ""),
        },
        "witness_quorum_binding": {
            "present": isinstance(witness_quorum, dict),
            "artifact_hash": _declared_hash(
                witness_quorum if isinstance(witness_quorum, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    witness_quorum if isinstance(witness_quorum, dict) else None
                )
            ),
            "hash_reproducible": checks["accountability_witness_quorum_bound"],
            "status": _summary(
                witness_quorum if isinstance(witness_quorum, dict) else None
            ).get("status", ""),
            "level": _summary(
                witness_quorum if isinstance(witness_quorum, dict) else None
            ).get("target_certification_level", ""),
        },
        "provenance_signal_rows": signal_rows,
        "attack_resistance_rows": attack_rows,
        "reliance_context_rows": context_rows,
        "evidence_roots": {
            "provenance_signal_root": signal_root,
            "attack_resistance_root": attack_root,
            "reliance_context_root": context_root,
        },
        "checks": checks,
        "adversarial_quorum_decision": {
            "adversarial_provenance_quorum_ready": ready,
            "credential_reliance_allowed": ready,
            "footer_reliance_allowed": ready,
            "high_stakes_reliance_allowed": ready,
            "third_party_distribution_reliance_allowed": ready,
            "downstream_rag_or_training_reuse_allowed": ready,
            "creator_settlement_release_allowed": ready,
            "single_signal_reliance_blocked": ready,
            "spoofed_or_stripped_outputs_blocked": ready,
            "failure_modes": failure_modes,
            "missing_provenance_signals": missing_signals,
            "incomplete_provenance_signals": incomplete_signals,
            "missing_attack_classes": missing_attacks,
            "incomplete_attack_classes": incomplete_attacks,
            "missing_reliance_contexts": missing_contexts,
            "incomplete_reliance_contexts": incomplete_contexts,
        },
        "quorum_coverage": {
            "required_provenance_signal_count": len(REQUIRED_PROVENANCE_SIGNALS),
            "ready_provenance_signal_count": len(REQUIRED_PROVENANCE_SIGNALS)
            - len(missing_signals)
            - len(incomplete_signals),
            "required_attack_class_count": len(REQUIRED_ATTACK_CLASSES),
            "ready_attack_class_count": len(REQUIRED_ATTACK_CLASSES)
            - len(missing_attacks)
            - len(incomplete_attacks),
            "required_reliance_context_count": len(REQUIRED_RELIANCE_CONTEXTS),
            "ready_reliance_context_count": len(REQUIRED_RELIANCE_CONTEXTS)
            - len(missing_contexts)
            - len(incomplete_contexts),
        },
        "privacy": {
            "private_payload_fields": [],
            "private_strings_absent": True,
            "private_payloads_excluded": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_distribution_reliance_level": (
                MINIMUM_DISTRIBUTION_RELIANCE_LEVEL
            ),
            "minimum_witness_quorum_level": MINIMUM_WITNESS_QUORUM_LEVEL,
            "provenance_signal_count": len(REQUIRED_PROVENANCE_SIGNALS),
            "ready_provenance_signal_count": len(REQUIRED_PROVENANCE_SIGNALS)
            - len(missing_signals)
            - len(incomplete_signals),
            "attack_class_count": len(REQUIRED_ATTACK_CLASSES),
            "ready_attack_class_count": len(REQUIRED_ATTACK_CLASSES)
            - len(missing_attacks)
            - len(incomplete_attacks),
            "reliance_context_count": len(REQUIRED_RELIANCE_CONTEXTS),
            "ready_reliance_context_count": len(REQUIRED_RELIANCE_CONTEXTS)
            - len(missing_contexts)
            - len(incomplete_contexts),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_adversarial_provenance_quorum": signing_secret is not None,
        },
    }
    public["privacy"]["private_payload_fields"] = _contains_private_fields(public)
    public["privacy"]["private_strings_absent"] = _private_strings_absent(
        public,
        quorum_input,
    )
    public["privacy"]["private_payloads_excluded"] = (
        not public["privacy"]["private_payload_fields"]
        and public["privacy"]["private_strings_absent"]
    )
    if not public["privacy"]["private_payloads_excluded"]:
        public["checks"]["private_payloads_excluded"] = False
        public["adversarial_quorum_decision"][
            "adversarial_provenance_quorum_ready"
        ] = False
        public["adversarial_quorum_decision"]["credential_reliance_allowed"] = False
        public["adversarial_quorum_decision"]["footer_reliance_allowed"] = False
        public["adversarial_quorum_decision"]["high_stakes_reliance_allowed"] = False
        public["adversarial_quorum_decision"][
            "third_party_distribution_reliance_allowed"
        ] = False
        public["adversarial_quorum_decision"][
            "downstream_rag_or_training_reuse_allowed"
        ] = False
        public["adversarial_quorum_decision"][
            "creator_settlement_release_allowed"
        ] = False
        public["adversarial_quorum_decision"]["single_signal_reliance_blocked"] = False
        public["adversarial_quorum_decision"][
            "spoofed_or_stripped_outputs_blocked"
        ] = False
        if "private_payloads_excluded" not in public["adversarial_quorum_decision"][
            "failure_modes"
        ]:
            public["adversarial_quorum_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["adversarial_quorum_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_adversarial_provenance_quorum_hash"] = hash_payload(
        _hashable_quorum(public)
    )
    if signing_secret:
        public["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_quorum(public), signing_secret),
        }
    return public


def validate_universal_adversarial_provenance_quorum_shape(
    quorum: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L173 provenance quorum."""

    errors: list[str] = []
    required = (
        "universal_adversarial_provenance_quorum_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "distribution_passport_binding",
        "witness_quorum_binding",
        "provenance_signal_rows",
        "attack_resistance_rows",
        "reliance_context_rows",
        "evidence_roots",
        "checks",
        "adversarial_quorum_decision",
        "quorum_coverage",
        "privacy",
        "summary",
        "universal_adversarial_provenance_quorum_hash",
    )
    for key in required:
        if key not in quorum:
            errors.append(f"missing adversarial provenance quorum field: {key}")
    if quorum.get("universal_adversarial_provenance_quorum_version") != (
        UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_VERSION
    ):
        errors.append("unexpected universal_adversarial_provenance_quorum_version")
    if quorum.get("schema") != UNIVERSAL_ADVERSARIAL_PROVENANCE_QUORUM_SCHEMA:
        errors.append("unexpected adversarial provenance quorum schema")
    for name in REQUIRED_PROVENANCE_SIGNALS:
        if name not in quorum.get("provenance_signal_rows", {}):
            errors.append(f"missing provenance signal row: {name}")
    for name in REQUIRED_ATTACK_CLASSES:
        if name not in quorum.get("attack_resistance_rows", {}):
            errors.append(f"missing attack resistance row: {name}")
    for name in REQUIRED_RELIANCE_CONTEXTS:
        if name not in quorum.get("reliance_context_rows", {}):
            errors.append(f"missing reliance context row: {name}")
    for check in (
        "distribution_reliance_passport_bound",
        "distribution_reliance_passport_l172_ready",
        "accountability_witness_quorum_bound",
        "accountability_witness_quorum_l153_ready",
        "provenance_signal_rows_complete",
        "attack_resistance_rows_complete",
        "reliance_context_rows_complete",
        "adversarial_provenance_quorum_signed",
    ):
        if check not in quorum.get("checks", {}):
            errors.append(f"missing adversarial provenance quorum check: {check}")
    return errors


def verify_universal_adversarial_provenance_quorum(
    quorum_input: dict[str, Any],
    quorum: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L173 adversarial provenance quorum against replay input."""

    errors = validate_universal_adversarial_provenance_quorum_shape(quorum)
    expected_hash = hash_payload(_hashable_quorum(quorum))
    if quorum.get("universal_adversarial_provenance_quorum_hash") != expected_hash:
        errors.append("universal_adversarial_provenance_quorum_hash mismatch")
    private_fields = _contains_private_fields(quorum)
    if private_fields:
        errors.append(
            "adversarial provenance quorum exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(quorum, quorum_input):
        errors.append("adversarial provenance quorum exposes private input strings")
    replayed = make_universal_adversarial_provenance_quorum(
        quorum_input,
        issuer=quorum.get("issuer", DEFAULT_ISSUER),
        created_at=quorum.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_adversarial_provenance_quorum_hash") != quorum.get(
        "universal_adversarial_provenance_quorum_hash"
    ):
        errors.append("adversarial provenance quorum does not match replay inputs")
    if quorum.get("summary", {}).get("status") != "ready":
        errors.append("adversarial provenance quorum is not ready")
    if quorum.get("adversarial_quorum_decision", {}).get(
        "adversarial_provenance_quorum_ready"
    ) is not True:
        errors.append("adversarial provenance quorum decision is not ready")
    if quorum.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("adversarial provenance quorum privacy is not preserved")
    if signing_secret:
        signature = quorum.get("signature", {})
        expected_signature = sign_payload(_hashable_quorum(quorum), signing_secret)
        if not signature:
            errors.append("adversarial provenance quorum is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("adversarial provenance quorum signature is invalid")
    return errors
