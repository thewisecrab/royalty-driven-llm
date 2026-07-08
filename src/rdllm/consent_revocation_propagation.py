"""Consent and revocation propagation audits.

Static rights checks are not enough for foundation-model attribution. Creator
consent, opt-outs, license terms, access leases, and downstream rights signals
change over time. This module creates a replayable public report proving that a
rights change reached every serving, attribution, memory, exchange, and settlement
surface before the source could be used or directly paid again.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

CONSENT_REVOCATION_PROPAGATION_VERSION = (
    "rdllm-consent-revocation-propagation/v1"
)
CONSENT_REVOCATION_PROPAGATION_SCHEMA = (
    "docs/schemas/consent_revocation_propagation.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L118"
MINIMUM_INPUT_LEVEL = "RDLLM-L117"

DEFAULT_MAX_PROPAGATION_SECONDS = 3600
DEFAULT_REQUIRED_SURFACES = (
    "retrieval_index",
    "source_access_lease",
    "license_transaction",
    "grounded_source_footer",
    "source_footer_delivery",
    "response_release_gate",
    "persistent_memory",
    "private_reasoning",
    "post_training_signal",
    "attribution_exchange",
    "creator_audit_federation",
    "settlement",
)
PROPAGATED_STATUSES = {"propagated", "complete", "completed", "ready", "accepted"}
SAFE_ACTIONS = {
    "blocked",
    "denylisted",
    "purged",
    "quarantined",
    "expired",
    "escrowed",
    "license_state_updated",
    "footer_state_updated",
    "notice_delivered",
    "downstream_notified",
}
SAFE_FUTURE_OUTCOMES = {
    "blocked",
    "denied",
    "escrowed",
    "rights_conflict_escrow",
    "revocation_escrow",
    "not_selected",
}
DIRECT_SETTLEMENT_ACTIONS = {"direct_payout", "pay", "paid", "payable", "settled"}
ACK_STATUSES = {"acknowledged", "accepted", "received", "complete", "completed"}

DECLARED_HASH_FIELDS = (
    "consent_revocation_propagation_hash",
    "royalty_abuse_audit_hash",
    "source_freshness_audit_hash",
    "protocol_ingestion_report_hash",
    "license_transaction_receipt_hash",
    "lease_report_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "persistent_memory_provenance_hash",
    "private_reasoning_attribution_hash",
    "post_training_signal_provenance_hash",
    "exchange_hash",
    "creator_attribution_audit_federation_hash",
    "contract_hash",
    "report_hash",
    "receipt_hash",
    "card_hash",
    "envelope_hash",
    "manifest_hash",
    "graph_hash",
    "bundle_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_model_output",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "raw_license_token",
    "raw_notice_text",
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

REQUIRED_ARTIFACT_BINDINGS = (
    "rights_remediation_report",
    "creator_license_contract",
    "source_access_lease_report",
    "license_transaction_receipt",
    "grounded_source_footer",
    "source_footer_delivery",
    "persistent_memory_provenance",
    "private_reasoning_attribution",
    "post_training_signal_provenance",
    "attribution_exchange",
    "royalty_abuse_audit",
)


def load_consent_revocation_propagation_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L118 propagation audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"consent_revocation_propagation_hash", "signature"}
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
    report: dict[str, Any], propagation_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in propagation_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _seconds_between(start: Any, end: Any) -> int | None:
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if start_dt is None or end_dt is None:
        return None
    return int((end_dt - start_dt).total_seconds())


def _after_or_at(left: Any, right: Any) -> bool:
    left_dt = _parse_iso(left)
    right_dt = _parse_iso(right)
    if left_dt is None or right_dt is None:
        return False
    return left_dt >= right_dt


def _before(left: Any, right: Any) -> bool:
    left_dt = _parse_iso(left)
    right_dt = _parse_iso(right)
    if left_dt is None or right_dt is None:
        return False
    return left_dt < right_dt


def _policy(propagation_input: dict[str, Any]) -> dict[str, Any]:
    configured = dict(propagation_input.get("policy", {}))
    required_surfaces = configured.get("required_surfaces", DEFAULT_REQUIRED_SURFACES)
    return {
        "max_propagation_seconds": int(
            configured.get(
                "max_propagation_seconds", DEFAULT_MAX_PROPAGATION_SECONDS
            )
            or DEFAULT_MAX_PROPAGATION_SECONDS
        ),
        "required_surfaces": sorted(str(surface) for surface in required_surfaces),
        "require_downstream_acknowledgements": bool(
            configured.get("require_downstream_acknowledgements", True)
        ),
        "require_future_use_block_or_escrow": bool(
            configured.get("require_future_use_block_or_escrow", True)
        ),
        "require_historical_event_preservation": bool(
            configured.get("require_historical_event_preservation", True)
        ),
    }


def _event_link_hash(row: dict[str, Any]) -> str:
    return hash_payload(
        {
            "event_id": str(row.get("event_id", "")),
            "work_id": str(row.get("work_id", "")),
            "source_id": str(row.get("source_id", "")),
            "content_hash": str(row.get("content_hash", "")),
        }
    )


def _rights_event_rows(propagation_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(propagation_input.get("rights_events", []), start=1):
        if not isinstance(event, dict):
            continue
        raw = {
            "event_id": str(event.get("event_id") or f"rights_event_{index}"),
            "event_type": str(
                event.get("event_type")
                or event.get("change_type")
                or "rights_change"
            ).lower(),
            "effective_at": str(
                event.get("effective_at") or event.get("revoked_at") or ""
            ),
            "observed_at": str(event.get("observed_at") or event.get("created_at") or ""),
            "source_id": str(event.get("source_id") or event.get("label") or ""),
            "work_id": str(event.get("work_id") or ""),
            "creator_id_hash": str(
                event.get("creator_id_hash")
                or hash_payload(str(event.get("creator_id") or ""))
            ),
            "source_uri": str(event.get("source_uri") or ""),
            "content_hash": str(event.get("content_hash") or ""),
            "previous_policy_hash": str(event.get("previous_policy_hash") or ""),
            "updated_policy_hash": str(event.get("updated_policy_hash") or ""),
            "external_rights_signal_hash": str(
                event.get("external_rights_signal_hash") or ""
            ),
        }
        downstream = [
            str(item)
            for item in (
                event.get("downstream_provider_hashes")
                or event.get("downstream_provider_ids")
                or []
            )
            if str(item)
        ]
        row = {
            "event_id": raw["event_id"],
            "event_type": raw["event_type"],
            "effective_at": raw["effective_at"],
            "observed_at": raw["observed_at"],
            "source_id": raw["source_id"],
            "work_id_hash": hash_payload(raw["work_id"]),
            "creator_id_hash": raw["creator_id_hash"],
            "source_uri_hash": hash_payload(raw["source_uri"]),
            "content_hash": raw["content_hash"],
            "previous_policy_hash": raw["previous_policy_hash"],
            "updated_policy_hash": raw["updated_policy_hash"],
            "external_rights_signal_hash": raw["external_rights_signal_hash"],
            "downstream_provider_hashes": sorted(hash_payload(item) for item in downstream),
            "event_link_hash": _event_link_hash(raw),
            "rights_event_hash": str(
                event.get("rights_event_hash")
                or event.get("revocation_event_hash")
                or ""
            ),
            "effective_time_present": _parse_iso(raw["effective_at"]) is not None,
            "policy_hash_changed_or_revoked": (
                raw["event_type"] in {"revocation", "opt_out", "lease_expiry"}
                or (
                    bool(raw["previous_policy_hash"])
                    and bool(raw["updated_policy_hash"])
                    and raw["previous_policy_hash"] != raw["updated_policy_hash"]
                )
            ),
        }
        row["rights_event_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["event_id"])


def _rights_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["event_id"]): row for row in rows}


def _propagation_rows(
    propagation_input: dict[str, Any],
    rights_by_event: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    max_seconds = int(policy["max_propagation_seconds"])
    for index, item in enumerate(
        propagation_input.get("propagation_rows", []), start=1
    ):
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        event = rights_by_event.get(event_id, {})
        completed_at = str(
            item.get("completed_at")
            or item.get("propagated_at")
            or item.get("acknowledged_at")
            or ""
        )
        latency = _seconds_between(event.get("effective_at"), completed_at)
        action = str(item.get("action") or item.get("propagation_action") or "").lower()
        status = str(item.get("status") or "").lower()
        propagated = status in PROPAGATED_STATUSES and action in SAFE_ACTIONS
        row = {
            "propagation_id": str(
                item.get("propagation_id") or f"propagation_{index}"
            ),
            "event_id": event_id,
            "surface": str(item.get("surface") or ""),
            "surface_instance_hash": hash_payload(str(item.get("surface_instance") or "")),
            "action": action,
            "status": status,
            "completed_at": completed_at,
            "latency_seconds": latency if latency is not None else -1,
            "within_sla": latency is not None and 0 <= latency <= max_seconds,
            "evidence_hash": str(item.get("evidence_hash") or ""),
            "propagated": propagated,
        }
        row["propagation_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["event_id"], row["surface"], row["propagation_id"]))


def _future_use_rows(
    propagation_input: dict[str, Any],
    rights_by_event: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(propagation_input.get("future_use_rows", []), start=1):
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        event = rights_by_event.get(event_id, {})
        used_at = str(item.get("used_at") or item.get("attempted_at") or "")
        action = str(item.get("settlement_action") or item.get("action") or "").lower()
        outcome = str(item.get("outcome") or item.get("decision") or "").lower()
        direct_payout = bool(item.get("direct_payout")) or action in DIRECT_SETTLEMENT_ACTIONS
        source_selected = bool(
            item.get("source_selected")
            or item.get("retrieved")
            or item.get("footer_visible")
            or item.get("used")
        )
        after_effective = _after_or_at(used_at, event.get("effective_at"))
        safe_outcome = outcome in SAFE_FUTURE_OUTCOMES or (
            "escrow" in action and not direct_payout
        )
        row = {
            "future_use_id": str(item.get("future_use_id") or f"future_use_{index}"),
            "event_id": event_id,
            "used_at": used_at,
            "use_type": str(item.get("use_type") or "generation"),
            "source_id": str(item.get("source_id") or event.get("source_id") or ""),
            "work_id_hash": hash_payload(str(item.get("work_id") or "")),
            "after_effective_time": after_effective,
            "outcome": outcome,
            "settlement_action": action,
            "source_selected": source_selected,
            "direct_payout": direct_payout,
            "escrowed": "escrow" in outcome or "escrow" in action or bool(item.get("escrowed")),
            "footer_license_state": str(item.get("footer_license_state") or ""),
            "blocked_or_escrowed_after_revocation": (
                not after_effective
                or (
                    safe_outcome
                    and not direct_payout
                    and not source_selected
                    and str(item.get("footer_license_state") or "").lower()
                    in {"", "revoked", "expired", "denied", "blocked", "opted_out"}
                )
            ),
        }
        row["future_use_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["event_id"], row["future_use_id"]))


def _historical_event_rows(
    propagation_input: dict[str, Any],
    rights_by_event: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(
        propagation_input.get("historical_event_rows", []), start=1
    ):
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        event = rights_by_event.get(event_id, {})
        used_at = str(item.get("used_at") or item.get("event_time") or "")
        row = {
            "historical_id": str(item.get("historical_id") or f"historical_{index}"),
            "event_id": event_id,
            "usage_event_hash": str(item.get("usage_event_hash") or item.get("event_hash") or ""),
            "used_at": used_at,
            "before_effective_time": _before(used_at, event.get("effective_at")),
            "historical_event_preserved": bool(item.get("historical_event_preserved")),
            "rewritten": bool(item.get("rewritten")),
            "settlement_state": str(item.get("settlement_state") or "preserved"),
        }
        row["historical_event_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["event_id"], row["historical_id"]))


def _expected_downstream_provider_hashes(
    propagation_input: dict[str, Any],
    rights_rows: list[dict[str, Any]],
) -> dict[str, set[str]]:
    global_expected = {
        hash_payload(str(item))
        for item in propagation_input.get("expected_downstream_provider_ids", [])
        if str(item)
    } | {
        str(item)
        for item in propagation_input.get("expected_downstream_provider_hashes", [])
        if str(item)
    }
    expected: dict[str, set[str]] = {}
    for row in rights_rows:
        event_expected = set(row.get("downstream_provider_hashes", [])) | global_expected
        expected[str(row["event_id"])] = {item for item in event_expected if item}
    return expected


def _downstream_notice_rows(
    propagation_input: dict[str, Any],
    rights_by_event: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    max_seconds = int(policy["max_propagation_seconds"])
    for index, item in enumerate(
        propagation_input.get("downstream_notice_rows", []), start=1
    ):
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        event = rights_by_event.get(event_id, {})
        provider = str(item.get("downstream_provider_id") or "")
        provider_hash = str(item.get("downstream_provider_hash") or hash_payload(provider))
        notice_sent_at = str(item.get("notice_sent_at") or item.get("sent_at") or "")
        acknowledged_at = str(
            item.get("acknowledged_at") or item.get("ack_at") or ""
        )
        notice_latency = _seconds_between(event.get("effective_at"), notice_sent_at)
        ack_latency = _seconds_between(event.get("effective_at"), acknowledged_at)
        status = str(item.get("status") or "").lower()
        row = {
            "notice_id": str(item.get("notice_id") or f"notice_{index}"),
            "event_id": event_id,
            "downstream_provider_hash": provider_hash,
            "notice_sent_at": notice_sent_at,
            "acknowledged_at": acknowledged_at,
            "status": status,
            "notice_latency_seconds": notice_latency if notice_latency is not None else -1,
            "ack_latency_seconds": ack_latency if ack_latency is not None else -1,
            "notice_within_sla": notice_latency is not None
            and 0 <= notice_latency <= max_seconds,
            "ack_within_sla": ack_latency is not None
            and 0 <= ack_latency <= max_seconds,
            "acknowledgement_hash": str(
                item.get("acknowledgement_hash") or item.get("ack_hash") or ""
            ),
            "acknowledged": status in ACK_STATUSES
            and bool(item.get("acknowledgement_hash") or item.get("ack_hash")),
        }
        row["downstream_notice_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(
        rows, key=lambda row: (row["event_id"], row["downstream_provider_hash"])
    )


def _artifact_bindings(propagation_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "rights_remediation_report": propagation_input.get("rights_remediation_report"),
        "creator_license_contract": propagation_input.get("creator_license_contract"),
        "source_access_lease_report": propagation_input.get("source_access_lease_report"),
        "content_protocol_ingestion_report": propagation_input.get(
            "content_protocol_ingestion_report"
        ),
        "license_transaction_receipt": propagation_input.get(
            "license_transaction_receipt"
        ),
        "grounded_source_footer": propagation_input.get("grounded_source_footer"),
        "source_footer_delivery": propagation_input.get("source_footer_delivery"),
        "persistent_memory_provenance": propagation_input.get(
            "persistent_memory_provenance"
        ),
        "private_reasoning_attribution": propagation_input.get(
            "private_reasoning_attribution"
        ),
        "post_training_signal_provenance": propagation_input.get(
            "post_training_signal_provenance"
        ),
        "attribution_exchange": propagation_input.get("attribution_exchange"),
        "creator_attribution_audit_federation": propagation_input.get(
            "creator_attribution_audit_federation"
        ),
        "royalty_abuse_audit": propagation_input.get("royalty_abuse_audit"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        if artifact is None:
            continue
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(artifact)
    return bindings


def _required_artifact_bindings_present(propagation_input: dict[str, Any]) -> bool:
    return all(
        isinstance(propagation_input.get(name), dict)
        for name in REQUIRED_ARTIFACT_BINDINGS
    )


def make_consent_revocation_propagation_report(
    propagation_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L118 audit over dynamic rights propagation."""

    policy = _policy(propagation_input)
    rights_rows = _rights_event_rows(propagation_input)
    rights_by_event = _rights_index(rights_rows)
    propagation_rows = _propagation_rows(propagation_input, rights_by_event, policy)
    future_rows = _future_use_rows(propagation_input, rights_by_event)
    historical_rows = _historical_event_rows(propagation_input, rights_by_event)
    downstream_rows = _downstream_notice_rows(
        propagation_input, rights_by_event, policy
    )
    expected_downstream = _expected_downstream_provider_hashes(
        propagation_input, rights_rows
    )
    propagation_by_event: dict[str, set[str]] = {
        event_id: set() for event_id in rights_by_event
    }
    for row in propagation_rows:
        if row["propagated"] and row["within_sla"]:
            propagation_by_event.setdefault(str(row["event_id"]), set()).add(
                str(row["surface"])
            )
    expected_provider_rows = {
        (event_id, provider_hash)
        for event_id, providers in expected_downstream.items()
        for provider_hash in providers
    }
    acknowledged_provider_rows = {
        (str(row["event_id"]), str(row["downstream_provider_hash"]))
        for row in downstream_rows
        if row["acknowledged"] and row["ack_within_sla"]
    }
    missing_surface_rows = [
        {
            "event_id": event_id,
            "missing_surfaces": sorted(
                set(policy["required_surfaces"])
                - propagation_by_event.get(event_id, set())
            ),
        }
        for event_id in sorted(rights_by_event)
    ]
    missing_surface_rows = [
        row for row in missing_surface_rows if row["missing_surfaces"]
    ]
    public_payload = {
        "rights_event_rows": rights_rows,
        "propagation_rows": propagation_rows,
        "future_use_rows": future_rows,
        "historical_event_rows": historical_rows,
        "downstream_notice_rows": downstream_rows,
    }
    artifact_bindings = _artifact_bindings(propagation_input)
    checks = {
        "rights_change_events_present": bool(rights_rows),
        "rights_events_have_effective_times": all(
            row["effective_time_present"] for row in rights_rows
        ),
        "rights_events_have_policy_change_or_revocation": all(
            row["policy_hash_changed_or_revoked"] for row in rights_rows
        ),
        "every_required_surface_propagated_within_sla": not missing_surface_rows,
        "every_propagation_row_has_evidence": all(
            row["evidence_hash"] for row in propagation_rows
        )
        and bool(propagation_rows),
        "future_uses_after_revocation_blocked_or_escrowed": (
            not policy["require_future_use_block_or_escrow"]
            or all(row["blocked_or_escrowed_after_revocation"] for row in future_rows)
        ),
        "historical_events_preserved_without_rewrite": (
            not policy["require_historical_event_preservation"]
            or all(
                row["before_effective_time"]
                and row["historical_event_preserved"]
                and not row["rewritten"]
                and bool(row["usage_event_hash"])
                for row in historical_rows
            )
        ),
        "downstream_acknowledgements_complete": (
            not policy["require_downstream_acknowledgements"]
            or expected_provider_rows.issubset(acknowledged_provider_rows)
        ),
        "artifact_bindings_hash_reproducible": all(
            value is True
            for key, value in artifact_bindings.items()
            if key.endswith("_hash_reproducible")
        ),
        "required_artifact_bindings_present": _required_artifact_bindings_present(
            propagation_input
        ),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_payload
        ),
    }
    report: dict[str, Any] = {
        "propagation_version": CONSENT_REVOCATION_PROPAGATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-consent-revocation-propagation-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "max_propagation_seconds": policy["max_propagation_seconds"],
            "required_surfaces": policy["required_surfaces"],
            "future_revoked_use_action": "deny_or_route_to_rights_conflict_escrow",
            "historical_event_policy": "preserve_event_hashes_without_rewrite",
            "downstream_notice_policy": "send_and_acknowledge_before_future_use",
        },
        "artifact_bindings": artifact_bindings,
        "rights_event_rows": rights_rows,
        "propagation_rows": propagation_rows,
        "future_use_rows": future_rows,
        "historical_event_rows": historical_rows,
        "downstream_notice_rows": downstream_rows,
        "coverage_gaps": {
            "missing_surface_rows": missing_surface_rows,
            "missing_downstream_acknowledgements": sorted(
                [
                    {
                        "event_id": event_id,
                        "downstream_provider_hash": provider_hash,
                    }
                    for event_id, provider_hash in (
                        expected_provider_rows - acknowledged_provider_rows
                    )
                ],
                key=lambda row: (
                    row["event_id"],
                    row["downstream_provider_hash"],
                ),
            ),
        },
        "checks": checks,
        "commitments": {
            "rights_event_root": hash_payload(
                [row["rights_event_row_hash"] for row in rights_rows]
            ),
            "propagation_root": hash_payload(
                [row["propagation_row_hash"] for row in propagation_rows]
            ),
            "future_use_root": hash_payload(
                [row["future_use_row_hash"] for row in future_rows]
            ),
            "historical_event_root": hash_payload(
                [row["historical_event_row_hash"] for row in historical_rows]
            ),
            "downstream_notice_root": hash_payload(
                [row["downstream_notice_row_hash"] for row in downstream_rows]
            ),
            "schema": CONSENT_REVOCATION_PROPAGATION_SCHEMA,
        },
        "schemas": {
            "consent_revocation_propagation": CONSENT_REVOCATION_PROPAGATION_SCHEMA,
            "rights_remediation_report": "docs/schemas/rights_remediation_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "source_access_lease_report": "docs/schemas/source_access_lease_report.schema.json",
            "license_transaction_receipt": "docs/schemas/license_transaction_receipt.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "royalty_abuse_audit": "docs/schemas/royalty_abuse_audit.schema.json",
        },
        "summary": {
            "status": "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "rights_event_count": len(rights_rows),
            "propagation_row_count": len(propagation_rows),
            "future_use_row_count": len(future_rows),
            "historical_event_count": len(historical_rows),
            "downstream_notice_count": len(downstream_rows),
            "missing_surface_event_count": len(missing_surface_rows),
            "missing_downstream_acknowledgement_count": len(
                expected_provider_rows - acknowledged_provider_rows
            ),
            "max_observed_latency_seconds": max(
                [row["latency_seconds"] for row in propagation_rows]
                + [row["ack_latency_seconds"] for row in downstream_rows],
                default=0,
            ),
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_creator_identity_disclosed": False,
            "raw_payment_account_disclosed": False,
            "public_report_uses_hashes_times_states_and_surface_names": True,
        },
    }
    report["checks"]["private_strings_absent"] = _private_strings_absent(
        report, propagation_input
    )
    report["summary"]["status"] = "ready" if all(report["checks"].values()) else "failed"
    report["consent_revocation_propagation_hash"] = hash_payload(
        _hashable_report(report)
    )
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


def validate_consent_revocation_propagation_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L118 propagation audit."""

    errors: list[str] = []
    required = (
        "propagation_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "rights_event_rows",
        "propagation_rows",
        "future_use_rows",
        "historical_event_rows",
        "downstream_notice_rows",
        "coverage_gaps",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "consent_revocation_propagation_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing consent revocation propagation field: {key}")
    if errors:
        return errors
    if report.get("propagation_version") != CONSENT_REVOCATION_PROPAGATION_VERSION:
        errors.append("consent revocation propagation version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("consent revocation target certification level is unsupported")
    if "consent_revocation_propagation" not in report.get("schemas", {}):
        errors.append("missing consent revocation propagation schema")
    if _contains_private_fields(report):
        errors.append("consent revocation propagation report contains private field")
    return errors


def verify_consent_revocation_propagation_report(
    report: dict[str, Any],
    *,
    propagation_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L118 propagation audit against private replay input."""

    errors = validate_consent_revocation_propagation_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "consent_revocation_propagation_hash"
    ):
        errors.append("consent revocation propagation hash is not reproducible")
    expected = make_consent_revocation_propagation_report(
        propagation_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "rights_event_rows",
        "propagation_rows",
        "future_use_rows",
        "historical_event_rows",
        "downstream_notice_rows",
        "coverage_gaps",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"consent revocation propagation {key} does not match inputs")
    if expected.get("consent_revocation_propagation_hash") != report.get(
        "consent_revocation_propagation_hash"
    ):
        errors.append("consent revocation propagation hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("consent revocation propagation status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"consent revocation propagation check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("consent revocation propagation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("consent revocation propagation signature is invalid")
    return errors
