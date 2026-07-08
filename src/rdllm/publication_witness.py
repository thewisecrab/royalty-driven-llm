"""Witness cosigning for RDLLM publication-monitor checkpoints."""

from __future__ import annotations

from typing import Any

from rdllm.publication_monitor import validate_publication_monitor_shape
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash
from rdllm.transparency import merkle_root, verify_inclusion

PUBLICATION_WITNESS_VERSION = "rdllm-publication-witness/v1"
PUBLICATION_WITNESS_SCHEMA = "docs/schemas/publication_witness.schema.json"

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


def _hashable_witness_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"publication_witness_hash", "signature"}
    }


def _hashable_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in checkpoint.items()
        if key != "checkpoint_hash"
    }


def _hashable_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in snapshot.items()
        if key != "snapshot_hash"
    }


def _checkpoint_chain_valid(checkpoints: list[dict[str, Any]]) -> bool:
    previous_hash = ""
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint.get("checkpoint_index") != index:
            return False
        if checkpoint.get("previous_checkpoint_hash") != previous_hash:
            return False
        if hash_payload(_hashable_checkpoint(checkpoint)) != checkpoint.get(
            "checkpoint_hash"
        ):
            return False
        previous_hash = str(checkpoint.get("checkpoint_hash", ""))
    return True


def _monitor_hashable(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"publication_monitor_hash", "signature"}
    }


def _monitor_self_errors(report: dict[str, Any]) -> list[str]:
    errors = validate_publication_monitor_shape(report)
    if errors:
        return errors
    if hash_payload(_monitor_hashable(report)) != report.get("publication_monitor_hash"):
        errors.append("publication monitor hash is not reproducible")
    history = report.get("checkpoint_history", [])
    if not isinstance(history, list) or not history:
        errors.append("publication monitor checkpoint history is empty")
        return errors
    if not _checkpoint_chain_valid(history):
        errors.append("publication monitor checkpoint chain is invalid")
    latest = history[-1]
    commitments = report.get("commitments", {})
    snapshot = report.get("current_snapshot", {})
    if latest.get("checkpoint_hash") != commitments.get("latest_checkpoint_hash"):
        errors.append("publication monitor latest checkpoint commitment drifted")
    if latest.get("snapshot_hash") != commitments.get("current_snapshot_hash"):
        errors.append("publication monitor snapshot commitment drifted")
    if latest.get("artifact_root") != commitments.get("current_artifact_root"):
        errors.append("publication monitor artifact-root commitment drifted")
    if hash_payload(_hashable_snapshot(snapshot)) != snapshot.get("snapshot_hash"):
        errors.append("publication monitor current snapshot hash is not reproducible")
    if latest.get("snapshot_hash") != snapshot.get("snapshot_hash"):
        errors.append("publication monitor latest checkpoint does not bind current snapshot")
    if not all(
        verify_inclusion(proof)
        for proof in snapshot.get("inclusion_proofs", {}).values()
        if isinstance(proof, dict)
    ):
        errors.append("publication monitor snapshot inclusion proof is invalid")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("publication monitor status is not ready")
    return errors


def _monitor_subject(report: dict[str, Any]) -> dict[str, Any]:
    checkpoint = report.get("checkpoint_history", [{}])[-1]
    subject = {
        "issuer": report.get("issuer", ""),
        "monitor_hash": report.get("publication_monitor_hash", ""),
        "monitor_created_at": report.get("created_at", ""),
        "checkpoint_index": checkpoint.get("checkpoint_index", -1),
        "checkpoint_hash": checkpoint.get("checkpoint_hash", ""),
        "previous_checkpoint_hash": checkpoint.get("previous_checkpoint_hash", ""),
        "snapshot_hash": checkpoint.get("snapshot_hash", ""),
        "artifact_root": checkpoint.get("artifact_root", ""),
        "artifact_count": checkpoint.get("artifact_count", 0),
        "certification_level": checkpoint.get("certification_level", ""),
        "monitor_status": report.get("summary", {}).get("status", ""),
    }
    subject["subject_hash"] = hash_payload(subject)
    return subject


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


def _witness_key_hash(witness_id: str, witness_secret: str) -> str:
    return stable_hash(f"rdllm-witness-key:{witness_id}:{witness_secret}")


def _attestation_payload(
    subject: dict[str, Any],
    *,
    witness_id: str,
    witness_secret: str,
    observed_at: str,
) -> dict[str, Any]:
    return {
        "witness_id": witness_id,
        "witness_key_hash": _witness_key_hash(witness_id, witness_secret),
        "observed_at": observed_at,
        "subject_hash": subject["subject_hash"],
        "monitor_hash": subject["monitor_hash"],
        "checkpoint_index": subject["checkpoint_index"],
        "checkpoint_hash": subject["checkpoint_hash"],
        "artifact_root": subject["artifact_root"],
    }


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key != "attestation_hash"
    }


def _make_attestation(
    subject: dict[str, Any],
    *,
    witness_id: str,
    witness_secret: str,
    observed_at: str,
) -> dict[str, Any]:
    payload = _attestation_payload(
        subject,
        witness_id=witness_id,
        witness_secret=witness_secret,
        observed_at=observed_at,
    )
    attestation = {
        **payload,
        "signature_algorithm": "HMAC-SHA256",
        "signature": sign_payload(payload, witness_secret),
    }
    attestation["attestation_hash"] = hash_payload(_hashable_attestation(attestation))
    return attestation


def _equivocation_groups(subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for subject in subjects:
        grouped.setdefault(
            (str(subject.get("issuer", "")), int(subject.get("checkpoint_index", -1))),
            [],
        ).append(subject)
    conflicts: list[dict[str, Any]] = []
    for (issuer, checkpoint_index), rows in grouped.items():
        hashes = {row.get("checkpoint_hash", "") for row in rows}
        roots = {row.get("artifact_root", "") for row in rows}
        snapshots = {row.get("snapshot_hash", "") for row in rows}
        if len(hashes) > 1 or len(roots) > 1 or len(snapshots) > 1:
            conflicts.append(
                {
                    "issuer": issuer,
                    "checkpoint_index": checkpoint_index,
                    "checkpoint_hashes": sorted(hashes),
                    "artifact_roots": sorted(roots),
                    "snapshot_hashes": sorted(snapshots),
                    "subject_hashes": sorted(row["subject_hash"] for row in rows),
                }
            )
    return conflicts


def _quorum_by_subject(
    attestations: list[dict[str, Any]],
) -> dict[str, list[str]]:
    quorum: dict[str, set[str]] = {}
    for attestation in attestations:
        quorum.setdefault(str(attestation.get("subject_hash", "")), set()).add(
            str(attestation.get("witness_id", ""))
        )
    return {key: sorted(value) for key, value in quorum.items()}


def make_publication_witness_report(
    publication_monitors: list[dict[str, Any]],
    *,
    witnesses: list[tuple[str, str]],
    required_quorum: int | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a witness quorum report over publication-monitor checkpoints."""

    timestamp = created_at or now_iso()
    witness_rows = sorted(witnesses, key=lambda item: item[0])
    quorum = required_quorum if required_quorum is not None else min(2, len(witness_rows))
    subject_pairs = sorted(
        [(_monitor_subject(report), report) for report in publication_monitors],
        key=lambda item: (
            item[0]["issuer"],
            item[0]["checkpoint_index"],
            item[0]["subject_hash"],
        ),
    )
    subjects = [subject for subject, _report in subject_pairs]
    monitor_errors = {
        subject["monitor_hash"]: _monitor_self_errors(report)
        for subject, report in subject_pairs
    }
    attestations = [
        _make_attestation(
            subject,
            witness_id=witness_id,
            witness_secret=witness_secret,
            observed_at=timestamp,
        )
        for subject in subjects
        for witness_id, witness_secret in witness_rows
    ]
    attestations = sorted(
        attestations,
        key=lambda item: (item["subject_hash"], item["witness_id"]),
    )
    quorum_map = _quorum_by_subject(attestations)
    equivocations = _equivocation_groups(subjects)
    private_fields = _contains_private_fields(
        {
            "subjects": subjects,
            "witness_attestations": attestations,
            "equivocation": equivocations,
        }
    )
    subject_hashes = [subject["subject_hash"] for subject in subjects]
    attestation_hashes = [
        attestation["attestation_hash"] for attestation in attestations
    ]
    checks = {
        "publication_monitors_self_consistent": all(
            not errors for errors in monitor_errors.values()
        ),
        "checkpoint_subjects_present": bool(subjects),
        "witness_quorum_policy_nonzero": quorum > 0 and len(witness_rows) >= quorum,
        "witness_quorum_met": all(
            len(quorum_map.get(subject["subject_hash"], [])) >= quorum
            for subject in subjects
        ),
        "witness_signatures_valid": True,
        "equivocation_absent": not equivocations,
        "private_input_fields_absent": not private_fields,
    }
    report = {
        "witness_version": PUBLICATION_WITNESS_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "witness_policy": {
            "required_quorum": quorum,
            "witness_count": len(witness_rows),
            "split_view_detection": True,
            "checkpoint_cosignatures_required": True,
            "public_payloads_redacted": True,
        },
        "checkpoint_subjects": subjects,
        "monitor_errors": monitor_errors,
        "witness_attestations": attestations,
        "witness_quorum": quorum_map,
        "equivocation": {
            "conflict_count": len(equivocations),
            "conflicts": equivocations,
        },
        "checks": checks,
        "commitments": {
            "subject_root": merkle_root(subject_hashes),
            "attestation_root": merkle_root(attestation_hashes),
            "schema": PUBLICATION_WITNESS_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L50",
            "monitor_count": len(publication_monitors),
            "checkpoint_subject_count": len(subjects),
            "witness_count": len(witness_rows),
            "required_quorum": quorum,
            "equivocation_count": len(equivocations),
            "private_input_field_count": len(private_fields),
        },
        "privacy": {
            "publication_monitor_payloads_embedded": False,
            "artifact_payloads_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "witness_report_uses_checkpoint_hashes_and_cosignatures": True,
        },
    }
    report["publication_witness_hash"] = hash_payload(
        _hashable_witness_report(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_witness_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_publication_witness_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "witness_version",
        "issuer",
        "created_at",
        "witness_policy",
        "checkpoint_subjects",
        "monitor_errors",
        "witness_attestations",
        "witness_quorum",
        "equivocation",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "publication_witness_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing publication witness field: {key}")
    if errors:
        return errors
    if report.get("witness_version") != PUBLICATION_WITNESS_VERSION:
        errors.append("publication witness version is unsupported")
    for subject in report.get("checkpoint_subjects", []):
        for key in (
            "issuer",
            "monitor_hash",
            "checkpoint_index",
            "checkpoint_hash",
            "artifact_root",
            "subject_hash",
        ):
            if key not in subject:
                errors.append(f"missing publication witness subject field: {key}")
    for attestation in report.get("witness_attestations", []):
        for key in (
            "witness_id",
            "witness_key_hash",
            "subject_hash",
            "checkpoint_hash",
            "signature",
            "attestation_hash",
        ):
            if key not in attestation:
                errors.append(f"missing publication witness attestation field: {key}")
    return errors


def verify_publication_witness_report(
    report: dict[str, Any],
    publication_monitors: list[dict[str, Any]],
    *,
    witnesses: list[tuple[str, str]],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a publication witness report against monitor checkpoints."""

    errors = validate_publication_witness_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_witness_report(report))
    if expected_hash != report.get("publication_witness_hash"):
        errors.append("publication witness hash is not reproducible")

    expected = make_publication_witness_report(
        publication_monitors,
        witnesses=witnesses,
        required_quorum=int(report.get("witness_policy", {}).get("required_quorum", 0)),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "witness_policy",
        "checkpoint_subjects",
        "monitor_errors",
        "witness_attestations",
        "witness_quorum",
        "equivocation",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"publication witness {key} does not match monitors")
    if expected.get("publication_witness_hash") != report.get("publication_witness_hash"):
        errors.append("publication witness hash does not match monitors")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("publication witness status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"publication witness check failed: {check}")

    witness_secrets = dict(witnesses)
    subjects = {
        subject["subject_hash"]: subject
        for subject in report.get("checkpoint_subjects", [])
        if isinstance(subject, dict)
    }
    for attestation in report.get("witness_attestations", []):
        witness_id = str(attestation.get("witness_id", ""))
        secret = witness_secrets.get(witness_id)
        subject = subjects.get(str(attestation.get("subject_hash", "")))
        if not secret:
            errors.append(f"unknown publication witness: {witness_id}")
            continue
        if subject is None:
            errors.append("publication witness attestation subject is unknown")
            continue
        payload = _attestation_payload(
            subject,
            witness_id=witness_id,
            witness_secret=secret,
            observed_at=str(attestation.get("observed_at", "")),
        )
        if _witness_key_hash(witness_id, secret) != attestation.get("witness_key_hash"):
            errors.append(f"publication witness key hash is invalid for {witness_id}")
        if sign_payload(payload, secret) != attestation.get("signature"):
            errors.append(f"publication witness signature is invalid for {witness_id}")
        if hash_payload(_hashable_attestation(attestation)) != attestation.get(
            "attestation_hash"
        ):
            errors.append(f"publication witness attestation hash is invalid for {witness_id}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_witness_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("publication witness report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("publication witness report signature is invalid")

    return errors
