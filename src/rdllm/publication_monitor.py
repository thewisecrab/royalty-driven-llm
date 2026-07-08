"""Append-only publication monitoring for RDLLM public proof surfaces."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

PUBLICATION_MONITOR_VERSION = "rdllm-publication-monitor/v1"
PUBLICATION_MONITOR_SCHEMA = "docs/schemas/publication_monitor.schema.json"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "graph_hash",
    "attestation_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "gate_hash",
    "contract_hash",
    "capsule_hash",
    "handshake_hash",
    "vector_pack_hash",
    "exchange_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "package_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

REQUIRED_MONITORED_ARTIFACTS = (
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "response_envelope",
    "assurance_bundle",
    "proof_dependency_graph",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}


def _hashable_monitor(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"publication_monitor_hash", "signature"}
    }


def _declared_hash(payload: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(payload)


def _artifact_hash_is_reproducible(payload: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if payload.get(field):
            if field == "receipt_hash" and isinstance(payload.get("payload"), dict):
                return hash_payload(payload["payload"]) == payload[field]
            hashable = {
                key: value
                for key, value in payload.items()
                if key not in {field, "signature"}
            }
            if field == "capsule_hash":
                surfaces = hashable.get("portable_surfaces")
                if isinstance(surfaces, dict):
                    surfaces = deepcopy(surfaces)
                    headers = surfaces.get("http_headers")
                    if isinstance(headers, dict):
                        headers.pop("RDLLM-Capsule-Hash", None)
                    hashable["portable_surfaces"] = surfaces
            return hash_payload(hashable) == payload[field]
    return True


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


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _artifact_entry(name: str, artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _certification_level(artifacts: list[tuple[str, str, dict[str, Any]]]) -> str:
    for name, _, payload in artifacts:
        if name == "certification_report":
            return str(payload.get("summary", {}).get("highest_level", ""))
    return ""


def _snapshot(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    snapshot_index: int,
) -> dict[str, Any]:
    entries = [
        _artifact_entry(name, artifact_type, payload)
        for name, artifact_type, payload in sorted(artifacts, key=lambda item: item[0])
    ]
    leaves = [entry["entry_hash"] for entry in entries]
    proofs = {
        entry["name"]: inclusion_proof(leaves, index)
        for index, entry in enumerate(entries)
    } if leaves else {}
    snapshot = {
        "snapshot_index": snapshot_index,
        "artifact_count": len(entries),
        "artifact_root": merkle_root(leaves),
        "certification_level": _certification_level(artifacts),
        "artifacts": entries,
        "inclusion_proofs": proofs,
    }
    snapshot["snapshot_hash"] = hash_payload(snapshot)
    return snapshot


def _checkpoint(
    snapshot: dict[str, Any],
    *,
    previous_checkpoint_hash: str,
    created_at: str,
) -> dict[str, Any]:
    checkpoint = {
        "checkpoint_index": snapshot["snapshot_index"],
        "created_at": created_at,
        "artifact_root": snapshot["artifact_root"],
        "snapshot_hash": snapshot["snapshot_hash"],
        "artifact_count": snapshot["artifact_count"],
        "certification_level": snapshot["certification_level"],
        "previous_checkpoint_hash": previous_checkpoint_hash,
    }
    checkpoint["checkpoint_hash"] = hash_payload(checkpoint)
    return checkpoint


def _checkpoint_chain_valid(checkpoints: list[dict[str, Any]]) -> bool:
    previous_hash = ""
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint.get("checkpoint_index") != index:
            return False
        if checkpoint.get("previous_checkpoint_hash") != previous_hash:
            return False
        expected = {
            key: value
            for key, value in checkpoint.items()
            if key != "checkpoint_hash"
        }
        if hash_payload(expected) != checkpoint.get("checkpoint_hash"):
            return False
        previous_hash = str(checkpoint.get("checkpoint_hash", ""))
    return True


def _snapshot_by_name(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry.get("name", ""): entry
        for entry in snapshot.get("artifacts", [])
        if isinstance(entry, dict)
    }


def _diff(previous_snapshot: dict[str, Any] | None, current_snapshot: dict[str, Any]) -> dict[str, Any]:
    current = _snapshot_by_name(current_snapshot)
    previous = _snapshot_by_name(previous_snapshot or {})
    current_names = set(current)
    previous_names = set(previous)
    added = sorted(current_names - previous_names)
    removed = sorted(previous_names - current_names)
    changed = sorted(
        name
        for name in current_names & previous_names
        if current[name].get("declared_hash") != previous[name].get("declared_hash")
        or current[name].get("payload_hash") != previous[name].get("payload_hash")
    )
    unchanged = sorted((current_names & previous_names) - set(changed))
    previous_level = str((previous_snapshot or {}).get("certification_level", ""))
    current_level = str(current_snapshot.get("certification_level", ""))
    removed_required = sorted(set(REQUIRED_MONITORED_ARTIFACTS) & set(removed))
    return {
        "added_artifacts": added,
        "removed_artifacts": removed,
        "changed_artifacts": changed,
        "unchanged_artifacts": unchanged,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "unchanged_count": len(unchanged),
        "previous_certification_level": previous_level,
        "current_certification_level": current_level,
        "certification_regressed": (
            bool(previous_level)
            and _level_number(current_level) < _level_number(previous_level)
        ),
        "removed_required_artifacts": removed_required,
        "removed_required_artifact_count": len(removed_required),
    }


def make_publication_monitor_report(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    previous_report: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed append-only monitor over public RDLLM artifact snapshots."""

    timestamp = created_at or now_iso()
    previous_history = list((previous_report or {}).get("checkpoint_history", []))
    previous_snapshot = (previous_report or {}).get("current_snapshot")
    snapshot = _snapshot(artifacts, snapshot_index=len(previous_history))
    previous_checkpoint_hash = (
        str(previous_history[-1].get("checkpoint_hash", ""))
        if previous_history
        else ""
    )
    checkpoint = _checkpoint(
        snapshot,
        previous_checkpoint_hash=previous_checkpoint_hash,
        created_at=timestamp,
    )
    checkpoint_history = [*previous_history, checkpoint]
    diff = _diff(previous_snapshot, snapshot)
    artifact_names = {entry["name"] for entry in snapshot["artifacts"]}
    private_fields = _contains_private_fields(
        {
            "current_snapshot": snapshot,
            "checkpoint_history": checkpoint_history,
            "diff": diff,
        }
    )
    checks = {
        "required_artifacts_present": set(REQUIRED_MONITORED_ARTIFACTS).issubset(
            artifact_names
        ),
        "artifact_names_unique": len(artifact_names) == len(snapshot["artifacts"]),
        "artifact_hashes_reproducible": all(
            entry.get("hash_reproducible") is True
            for entry in snapshot["artifacts"]
        ),
        "snapshot_inclusion_proofs_valid": all(
            verify_inclusion(proof)
            for proof in snapshot.get("inclusion_proofs", {}).values()
        ),
        "checkpoint_history_append_only": (
            not previous_report
            or previous_history == previous_report.get("checkpoint_history", [])
        ),
        "checkpoint_chain_valid": _checkpoint_chain_valid(checkpoint_history),
        "certification_not_regressed": diff["certification_regressed"] is False,
        "required_artifacts_not_removed": diff["removed_required_artifact_count"] == 0,
        "private_input_fields_absent": not private_fields,
    }
    report = {
        "monitor_version": PUBLICATION_MONITOR_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "monitor_profile": {
            "append_only_checkpoints": True,
            "merkle_snapshot_roots": True,
            "signed_checkpoint_history": True,
            "artifact_payloads_redacted": True,
            "certification_regression_blocking": True,
        },
        "required_artifacts": list(REQUIRED_MONITORED_ARTIFACTS),
        "current_snapshot": snapshot,
        "checkpoint_history": checkpoint_history,
        "diff": diff,
        "checks": checks,
        "commitments": {
            "current_artifact_root": snapshot["artifact_root"],
            "current_snapshot_hash": snapshot["snapshot_hash"],
            "latest_checkpoint_hash": checkpoint["checkpoint_hash"],
            "schema": PUBLICATION_MONITOR_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L49",
            "monitor_mode": "append" if previous_report else "genesis",
            "checkpoint_count": len(checkpoint_history),
            "current_checkpoint_index": checkpoint["checkpoint_index"],
            "artifact_count": snapshot["artifact_count"],
            "current_certification_level": snapshot["certification_level"],
            "changed_artifact_count": diff["changed_count"],
            "removed_artifact_count": diff["removed_count"],
            "added_artifact_count": diff["added_count"],
            "private_input_field_count": len(private_fields),
        },
        "privacy": {
            "artifact_payloads_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "monitor_uses_hashes_checkpoints_and_diff_metadata": True,
        },
    }
    report["publication_monitor_hash"] = hash_payload(_hashable_monitor(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_monitor(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_publication_monitor_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "monitor_version",
        "issuer",
        "created_at",
        "monitor_profile",
        "required_artifacts",
        "current_snapshot",
        "checkpoint_history",
        "diff",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "publication_monitor_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing publication monitor field: {key}")
    if errors:
        return errors
    if report.get("monitor_version") != PUBLICATION_MONITOR_VERSION:
        errors.append("publication monitor version is unsupported")
    for entry in report.get("current_snapshot", {}).get("artifacts", []):
        for key in (
            "name",
            "artifact_type",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "entry_hash",
        ):
            if key not in entry:
                errors.append(f"missing publication monitor artifact field: {key}")
    return errors


def verify_publication_monitor_report(
    report: dict[str, Any],
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    previous_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a publication monitor report against current artifacts and prior state."""

    errors = validate_publication_monitor_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_monitor(report))
    if expected_hash != report.get("publication_monitor_hash"):
        errors.append("publication monitor hash is not reproducible")

    if report.get("summary", {}).get("monitor_mode") == "append" and previous_report is None:
        errors.append("previous publication monitor report is required for append verification")

    expected = make_publication_monitor_report(
        artifacts,
        previous_report=previous_report,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "monitor_profile",
        "required_artifacts",
        "current_snapshot",
        "checkpoint_history",
        "diff",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"publication monitor {key} does not match artifacts")
    if expected.get("publication_monitor_hash") != report.get("publication_monitor_hash"):
        errors.append("publication monitor hash does not match artifacts")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("publication monitor status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"publication monitor check failed: {check}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_monitor(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("publication monitor is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("publication monitor signature is invalid")

    return errors
