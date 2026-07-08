"""Private creator watch tokens for L113 transparency monitors.

L113 monitors transparency logs, but its query hashes can still become stable
public lookup keys. L114 produces a redacted creator-side watch receipt: the
creator or an authorized auditor verifies it with the private watch secret and
the L113 monitor, while the public artifact exposes only keyed watch tokens,
counts, roots, and monitor bindings.
"""

from __future__ import annotations

import hmac
from hashlib import sha256
from typing import Any

from rdllm.creator_audit_transparency_monitor import (
    CREATOR_AUDIT_TRANSPARENCY_MONITOR_VERSION,
    validate_creator_audit_transparency_monitor_shape,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

CREATOR_AUDIT_PRIVATE_WATCH_VERSION = "rdllm-creator-audit-private-watch/v1"
CREATOR_AUDIT_PRIVATE_WATCH_SCHEMA = (
    "docs/schemas/creator_audit_private_watch.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L114"
MINIMUM_INPUT_LEVEL = "RDLLM-L113"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "answer",
    "answer_text",
    "output",
    "output_text",
    "source",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "notice_text",
    "license_text",
    "creator_id",
    "creator_ids",
    "work_id",
    "work_ids",
    "source_label",
    "source_labels",
    "query_hash",
    "query_hashes",
    "provider_set_hash",
    "provider_set_hashes",
    "subject_hash",
    "federation_hash",
    "participant_index_hash",
    "entry_hash",
    "raw_query",
    "private_query",
    "watch_secret",
    "secret",
    "signing_secret",
    "private_key",
    "customer_id",
    "customer_email",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"creator_audit_private_watch_hash", "signature"}
    }


def _hashable_monitor(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"creator_audit_transparency_monitor_hash", "signature"}
    }


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return sorted(
            {
                str(item)
                for item in value
                if isinstance(item, (str, int, float)) and str(item)
            }
        )
    return []


def _private_strings_absent(report: dict[str, Any], private_strings: list[str]) -> bool:
    report_json = canonical_json(report)
    return all(not value or value not in report_json for value in private_strings)


def _watch_secret(watch_input: dict[str, Any]) -> str:
    return str(watch_input.get("watch_secret", ""))


def _watch_key_hash(watch_input: dict[str, Any]) -> str:
    secret = _watch_secret(watch_input)
    return hash_payload(
        {
            "purpose": "rdllm-creator-private-watch-key/v1",
            "watch_id": str(watch_input.get("watch_id", "")),
            "secret": secret,
        }
    )


def _watch_token(secret: str, purpose: str, value: Any, *, context: str) -> str:
    message = canonical_json(
        {
            "context": context,
            "purpose": purpose,
            "value": value,
        }
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, sha256).hexdigest()


def _monitor_hash_reproducible(monitor_report: dict[str, Any]) -> bool:
    declared = str(monitor_report.get("creator_audit_transparency_monitor_hash", ""))
    return bool(declared) and hash_payload(_hashable_monitor(monitor_report)) == declared


def _redacted_monitor_binding(monitor_report: dict[str, Any]) -> dict[str, Any]:
    summary = monitor_report.get("summary", {})
    binding = {
        "monitor_version": str(monitor_report.get("monitor_version", "")),
        "monitor_hash": str(
            monitor_report.get("creator_audit_transparency_monitor_hash", "")
        ),
        "monitor_payload_hash": hash_payload(monitor_report),
        "monitor_hash_reproducible": _monitor_hash_reproducible(monitor_report),
        "monitor_status": str(summary.get("status", "")),
        "monitor_target_level": str(summary.get("target_certification_level", "")),
        "query_identifier_count": int(summary.get("query_hash_count", 0) or 0),
        "provider_set_identifier_count": int(
            summary.get("provider_set_hash_count", 0) or 0
        ),
        "matching_observation_count": int(
            summary.get("matching_observation_count", 0) or 0
        ),
        "new_observation_count": int(summary.get("new_observation_count", 0) or 0),
        "conflict_count": int(summary.get("conflict_count", 0) or 0),
        "append_only_violation_count": int(
            summary.get("append_only_violation_count", 0) or 0
        ),
    }
    binding["monitor_binding_hash"] = hash_payload(binding)
    return binding


def _query_token_rows(
    monitor_report: dict[str, Any],
    *,
    secret: str,
    context: str,
) -> list[dict[str, Any]]:
    monitor_query = monitor_report.get("monitor_query", {})
    rows: list[dict[str, Any]] = []
    for field, purpose in (
        ("query_hashes", "query"),
        ("provider_set_hashes", "provider-set"),
        ("expected_federation_hashes", "expected-federation"),
        ("expected_participant_index_hashes", "expected-participant-index"),
        ("expected_provider_ids", "expected-provider"),
    ):
        for index, value in enumerate(_strings(monitor_query.get(field))):
            row = {
                "token_type": purpose,
                "token_index": index,
                "watch_token": _watch_token(secret, purpose, value, context=context),
            }
            row["token_row_hash"] = hash_payload(row)
            rows.append(row)
    return sorted(rows, key=lambda row: (row["token_type"], row["watch_token"]))


def _observation_token_rows(
    monitor_report: dict[str, Any],
    *,
    secret: str,
    context: str,
) -> list[dict[str, Any]]:
    new_hashes = {
        str(row.get("observation_hash", ""))
        for row in monitor_report.get("new_observation_rows", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for index, observation in enumerate(monitor_report.get("observation_rows", [])):
        if not isinstance(observation, dict):
            continue
        value = {
            "observation_hash": str(observation.get("observation_hash", "")),
            "entry_type": str(observation.get("entry_type", "")),
            "log_id": str(observation.get("log_id", "")),
            "entry_index": int(observation.get("entry_index", 0) or 0),
        }
        row = {
            "sequence": index,
            "watch_token": _watch_token(
                secret,
                "observation",
                value,
                context=context,
            ),
            "inclusion_proof_valid": observation.get("inclusion_proof_valid") is True,
            "new_observation": str(observation.get("observation_hash", ""))
            in new_hashes,
        }
        row["token_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _raw_identifiers(monitor_report: dict[str, Any], watch_input: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    monitor_query = monitor_report.get("monitor_query", {})
    for field in (
        "query_hashes",
        "provider_set_hashes",
        "expected_federation_hashes",
        "expected_participant_index_hashes",
        "expected_provider_ids",
    ):
        values.update(_strings(monitor_query.get(field)))
    for row in monitor_report.get("observation_rows", []):
        if isinstance(row, dict):
            for field in (
                "query_hash",
                "provider_set_hash",
                "subject_hash",
                "federation_hash",
                "participant_index_hash",
                "entry_hash",
                "provider_id",
            ):
                value = str(row.get(field, ""))
                if value:
                    values.add(value)
    values.update(_strings(watch_input.get("private_strings")))
    values.add(_watch_secret(watch_input))
    return sorted(value for value in values if value)


def _identifiers_absent(report: dict[str, Any], identifiers: list[str]) -> bool:
    report_json = canonical_json(report)
    return all(value not in report_json for value in identifiers)


def make_creator_audit_private_watch_report(
    *,
    watch_input: dict[str, Any],
    monitor_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L114 redacted watch receipt over an L113 monitor."""

    timestamp = created_at or now_iso()
    secret = _watch_secret(watch_input)
    context = str(watch_input.get("watch_context", "rdllm-creator-private-watch"))
    private_strings = _strings(watch_input.get("private_strings"))
    monitor_shape_errors = validate_creator_audit_transparency_monitor_shape(
        monitor_report
    )
    monitor_binding = _redacted_monitor_binding(monitor_report)
    query_tokens = _query_token_rows(monitor_report, secret=secret, context=context)
    observation_tokens = _observation_token_rows(
        monitor_report,
        secret=secret,
        context=context,
    )
    all_tokens = [row["watch_token"] for row in query_tokens + observation_tokens]
    public_fields = {
        "monitor_binding": monitor_binding,
        "query_token_rows": query_tokens,
        "observation_token_rows": observation_tokens,
    }
    report: dict[str, Any] = {
        "watch_version": CREATOR_AUDIT_PRIVATE_WATCH_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-creator-audit-private-watch-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "requires_l113_monitor": True,
            "requires_private_watch_secret": True,
            "requires_keyed_watch_tokens": True,
            "raw_query_identifiers_prohibited": True,
            "raw_subject_identifiers_prohibited": True,
            "oprf_upgrade_path": "RFC9497 VOPRF or POPRF",
        },
        "watch_binding": {
            "watch_id_hash": hash_payload(str(watch_input.get("watch_id", ""))),
            "watch_key_hash": _watch_key_hash(watch_input),
            "watch_context_hash": hash_payload(context),
            "token_scheme": "rdllm-hmac-watch-token/v1",
            "recommended_production_scheme": "RFC9497 VOPRF/POPRF",
        },
        "monitor_binding": monitor_binding,
        "query_token_rows": query_tokens,
        "observation_token_rows": observation_tokens,
        "checks": {},
        "commitments": {
            "monitor_binding_hash": monitor_binding["monitor_binding_hash"],
            "query_token_root": merkle_root(
                [row["token_row_hash"] for row in query_tokens]
            ),
            "observation_token_root": merkle_root(
                [row["token_row_hash"] for row in observation_tokens]
            ),
            "schema": CREATOR_AUDIT_PRIVATE_WATCH_SCHEMA,
        },
        "schemas": {
            "creator_audit_private_watch": CREATOR_AUDIT_PRIVATE_WATCH_SCHEMA,
            "creator_audit_transparency_monitor": "docs/schemas/creator_audit_transparency_monitor.schema.json",
        },
        "summary": {
            "status": "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "monitor_status": monitor_binding["monitor_status"],
            "query_token_count": len(query_tokens),
            "observation_token_count": len(observation_tokens),
            "new_observation_token_count": len(
                [row for row in observation_tokens if row["new_observation"]]
            ),
            "matching_observation_count": monitor_binding[
                "matching_observation_count"
            ],
            "conflict_count": monitor_binding["conflict_count"],
        },
        "privacy": {
            "stable_query_identifiers_disclosed": False,
            "stable_subject_identifiers_disclosed": False,
            "provider_ids_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "notice_text_disclosed": False,
            "license_text_disclosed": False,
            "payment_text_disclosed": False,
            "watch_secret_disclosed": False,
            "public_artifact_uses_keyed_tokens_counts_roots_and_monitor_hashes": True,
        },
    }
    raw_identifiers = _raw_identifiers(monitor_report, watch_input)
    checks = {
        "l113_monitor_shape_valid": not monitor_shape_errors,
        "l113_monitor_hash_reproducible": monitor_binding[
            "monitor_hash_reproducible"
        ],
        "l113_monitor_ready": monitor_binding["monitor_version"]
        == CREATOR_AUDIT_TRANSPARENCY_MONITOR_VERSION
        and monitor_binding["monitor_status"] == "ready"
        and monitor_binding["monitor_target_level"] == MINIMUM_INPUT_LEVEL,
        "l113_monitor_has_no_conflicts": monitor_binding["conflict_count"] == 0
        and monitor_binding["append_only_violation_count"] == 0,
        "watch_secret_present": bool(secret),
        "watch_key_commitment_present": bool(
            report["watch_binding"]["watch_key_hash"]
        ),
        "query_tokens_present": bool(query_tokens),
        "observation_tokens_present": bool(observation_tokens),
        "all_observation_tokens_have_valid_inclusion": all(
            row["inclusion_proof_valid"] for row in observation_tokens
        ),
        "tokens_unique": len(all_tokens) == len(set(all_tokens)),
        "raw_identifiers_absent": _identifiers_absent(report, raw_identifiers),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_fields
        ),
    }
    report["checks"] = checks
    report["summary"]["status"] = "ready" if all(checks.values()) else "failed"
    report["summary"]["raw_identifier_count_checked"] = len(raw_identifiers)
    checks["private_strings_absent"] = _private_strings_absent(report, private_strings)
    report["summary"]["status"] = "ready" if all(checks.values()) else "failed"
    report["creator_audit_private_watch_hash"] = hash_payload(_hashable_report(report))
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


def validate_creator_audit_private_watch_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L114 private watch report."""

    errors: list[str] = []
    required = (
        "watch_version",
        "issuer",
        "created_at",
        "policy",
        "watch_binding",
        "monitor_binding",
        "query_token_rows",
        "observation_token_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "creator_audit_private_watch_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing creator audit private watch field: {key}")
    if errors:
        return errors
    if report.get("watch_version") != CREATOR_AUDIT_PRIVATE_WATCH_VERSION:
        errors.append("creator audit private watch version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("creator audit private watch target certification level is unsupported")
    if "creator_audit_private_watch" not in report.get("schemas", {}):
        errors.append("missing creator audit private watch schema")
    if _contains_private_fields(report):
        errors.append("creator audit private watch contains private field")
    return errors


def verify_creator_audit_private_watch_report(
    report: dict[str, Any],
    *,
    watch_input: dict[str, Any],
    monitor_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L114 private watch report against an L113 monitor and watch secret."""

    errors = validate_creator_audit_private_watch_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "creator_audit_private_watch_hash"
    ):
        errors.append("creator audit private watch hash is not reproducible")
    expected = make_creator_audit_private_watch_report(
        watch_input=watch_input,
        monitor_report=monitor_report,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "watch_binding",
        "monitor_binding",
        "query_token_rows",
        "observation_token_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"creator audit private watch {key} does not match inputs")
    if expected.get("creator_audit_private_watch_hash") != report.get(
        "creator_audit_private_watch_hash"
    ):
        errors.append("creator audit private watch hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("creator audit private watch status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"creator audit private watch check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("creator audit private watch report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("creator audit private watch report signature is invalid")
    return errors
