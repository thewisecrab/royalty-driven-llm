"""Independent watchtower challenge settlement gates for RDLLM."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash
from rdllm.transparency import merkle_root

WATCHTOWER_CHALLENGE_SETTLEMENT_VERSION = (
    "rdllm-watchtower-challenge-settlement-report/v1"
)
WATCHTOWER_CHALLENGE_SETTLEMENT_SCHEMA = (
    "docs/schemas/watchtower_challenge_settlement_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L74"
DEFAULT_WATCHTOWER_ROLE = "independent_watchtower"
DEFAULT_REQUIRED_QUORUM = 2
DEFAULT_SLASH_FRACTION = Decimal("0.10")
DEFAULT_BOUNTY_FRACTION = Decimal("0.50")

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
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
    "private_key_material",
}

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "watchtower_report_hash",
    "attestation_hash",
    "graph_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "manifest_hash",
    "bundle_hash",
    "envelope_hash",
    "receipt_hash",
    "event_hash",
)


def _money(value: Decimal | str | int | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.000001")))


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"watchtower_report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _artifact_binding(name: str, artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    row["binding_hash"] = hash_payload(row)
    return row


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


def _principal_key_hash(principal_id: str, role: str, secret: str) -> str:
    if role == "witness":
        return stable_hash(f"rdllm-witness-key:{principal_id}:{secret}")
    return stable_hash(f"rdllm-signing-key:{principal_id}:{role}:{secret}")


def _watchtower_subject(
    *,
    receipt_transparency_consistency_report: dict[str, Any],
    verifier_accountability_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    receipt_summary = receipt_transparency_consistency_report.get("summary", {})
    receipt_gate = receipt_transparency_consistency_report.get("settlement_gate", {})
    verifier_summary = verifier_accountability_report.get("summary", {})
    subject = {
        "receipt_transparency_consistency_report_hash": _declared_hash(
            receipt_transparency_consistency_report
        ),
        "verifier_accountability_report_hash": _declared_hash(
            verifier_accountability_report
        ),
        "trust_registry_hash": _declared_hash(trust_registry),
        "provider_card_hash": _declared_hash(provider_card),
        "certification_report_hash": _declared_hash(certification_report),
        "receipt_status": str(receipt_summary.get("status", "")),
        "receipt_target_certification_level": str(
            receipt_summary.get("target_certification_level", "")
        ),
        "receipt_settlement_decision": str(
            receipt_summary.get("settlement_decision", "")
        ),
        "receipt_direct_settlement_ready": bool(
            receipt_summary.get("direct_settlement_ready", False)
        ),
        "receipt_required_count": int(
            receipt_summary.get("required_receipt_count", 0) or 0
        ),
        "receipt_missing_count": int(
            receipt_summary.get("missing_receipt_count", 0) or 0
        ),
        "receipt_append_only_violation_count": int(
            receipt_summary.get("append_only_violation_count", 0) or 0
        ),
        "receipt_split_view_conflict_count": int(
            receipt_summary.get("split_view_conflict_count", 0) or 0
        ),
        "receipt_gate_decision": str(receipt_gate.get("decision", "")),
        "verifier_accountability_status": str(verifier_summary.get("status", "")),
        "verifier_accountability_blocking_challenge_count": int(
            verifier_summary.get("blocking_challenge_count", 0) or 0
        ),
        "certification_highest_level": str(
            certification_report.get("summary", {}).get("highest_level", "")
        ),
    }
    subject["subject_hash"] = hash_payload(subject)
    return subject


def _active_watchtower_rows(
    trust_registry: dict[str, Any],
    *,
    watchtower_secrets: dict[str, str],
    watchtower_role: str,
) -> list[dict[str, Any]]:
    revoked_hashes = {
        str(row.get("key_hash", ""))
        for row in trust_registry.get("revoked_keys", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for principal in trust_registry.get("principals", []):
        if not isinstance(principal, dict):
            continue
        principal_id = str(principal.get("principal_id", ""))
        role = str(principal.get("role", ""))
        if role != watchtower_role:
            continue
        secret = watchtower_secrets.get(principal_id, "")
        derived_key_hash = _principal_key_hash(principal_id, role, secret) if secret else ""
        registry_key_hash = str(principal.get("key_hash", ""))
        row = {
            "watchtower_id": principal_id,
            "role": role,
            "key_id": str(principal.get("key_id", "")),
            "registry_key_hash": registry_key_hash,
            "derived_key_hash": derived_key_hash,
            "status": str(principal.get("status", "")),
            "secret_available_to_reference_verifier": bool(secret),
            "key_hash_matches_registry": bool(secret)
            and derived_key_hash == registry_key_hash,
            "revoked_key_used": registry_key_hash in revoked_hashes,
            "active_registered_watchtower": (
                principal.get("status") == "active"
                and bool(secret)
                and derived_key_hash == registry_key_hash
                and registry_key_hash not in revoked_hashes
            ),
        }
        row["watchtower_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["watchtower_id"])


def _attestation_payload(
    subject: dict[str, Any],
    *,
    watchtower_id: str,
    watchtower_role: str,
    watchtower_secret: str,
    observed_at: str,
) -> dict[str, Any]:
    return {
        "watchtower_id": watchtower_id,
        "watchtower_role": watchtower_role,
        "watchtower_key_hash": _principal_key_hash(
            watchtower_id,
            watchtower_role,
            watchtower_secret,
        ),
        "observed_at": observed_at,
        "subject_hash": subject["subject_hash"],
        "receipt_transparency_consistency_report_hash": subject[
            "receipt_transparency_consistency_report_hash"
        ],
        "receipt_settlement_decision": subject["receipt_settlement_decision"],
        "receipt_required_count": subject["receipt_required_count"],
        "receipt_missing_count": subject["receipt_missing_count"],
        "receipt_split_view_conflict_count": subject[
            "receipt_split_view_conflict_count"
        ],
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
    watchtower_id: str,
    watchtower_role: str,
    watchtower_secret: str,
    observed_at: str,
) -> dict[str, Any]:
    payload = _attestation_payload(
        subject,
        watchtower_id=watchtower_id,
        watchtower_role=watchtower_role,
        watchtower_secret=watchtower_secret,
        observed_at=observed_at,
    )
    attestation = {
        **payload,
        "signature_algorithm": "HMAC-SHA256",
        "signature": sign_payload(payload, watchtower_secret),
    }
    attestation["attestation_hash"] = hash_payload(_hashable_attestation(attestation))
    return attestation


def _automatic_challenges(
    subject: dict[str, Any],
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    challenges: list[dict[str, Any]] = []
    if (
        subject["receipt_status"] != "ready"
        or not subject["receipt_direct_settlement_ready"]
        or subject["receipt_missing_count"] > 0
        or subject["receipt_append_only_violation_count"] > 0
        or subject["receipt_split_view_conflict_count"] > 0
    ):
        challenges.append(
            {
                "challenge_id": "auto-receipt-transparency-defect",
                "opened_by": "watchtower:auto",
                "target_type": "receipt_transparency_consistency_report",
                "target_id": subject["receipt_transparency_consistency_report_hash"],
                "status": "accepted",
                "reason_code": "receipt_log_consistency_or_inclusion_failure",
                "evidence_hash": subject["subject_hash"],
                "opened_at": created_at,
                "resolved_at": created_at,
                "blocking": True,
                "slash_targets": [],
                "challenged_amount": "0.000000",
                "currency": "USD",
            }
        )
    if subject["verifier_accountability_blocking_challenge_count"] > 0:
        challenges.append(
            {
                "challenge_id": "auto-verifier-accountability-open-challenge",
                "opened_by": "watchtower:auto",
                "target_type": "verifier_accountability_report",
                "target_id": subject["verifier_accountability_report_hash"],
                "status": "open",
                "reason_code": "upstream_verifier_accountability_challenge_open",
                "evidence_hash": subject["subject_hash"],
                "opened_at": created_at,
                "resolved_at": "",
                "blocking": True,
                "slash_targets": [],
                "challenged_amount": "0.000000",
                "currency": "USD",
            }
        )
    return challenges


def _normalise_challenge_rows(
    challenge_rows: list[dict[str, Any]] | None,
    *,
    subject: dict[str, Any],
    created_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_rows = [*(challenge_rows or []), *_automatic_challenges(subject, created_at=created_at)]
    for index, challenge in enumerate(raw_rows, start=1):
        slash_targets = sorted(str(item) for item in challenge.get("slash_targets", []))
        row = {
            "challenge_id": str(
                challenge.get("challenge_id") or f"watchtower-challenge-{index}"
            ),
            "opened_by": str(challenge.get("opened_by") or ""),
            "target_type": str(challenge.get("target_type") or "provider_surface"),
            "target_id": str(challenge.get("target_id") or ""),
            "status": str(challenge.get("status") or "open"),
            "reason_code": str(challenge.get("reason_code") or "unspecified"),
            "evidence_hash": str(challenge.get("evidence_hash") or subject["subject_hash"]),
            "opened_at": str(challenge.get("opened_at") or created_at),
            "resolved_at": str(challenge.get("resolved_at") or ""),
            "blocking": bool(challenge.get("blocking", True)),
            "slash_targets": slash_targets,
            "challenged_amount": _money(challenge.get("challenged_amount", "0")),
            "currency": str(challenge.get("currency") or "USD"),
        }
        row["challenge_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["challenge_id"])


def _bond_rows_by_verifier(
    verifier_accountability_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("verifier_id", "")): row
        for row in verifier_accountability_report.get("bond_rows", [])
        if isinstance(row, dict)
    }


def _slashing_rows(
    challenge_rows: list[dict[str, Any]],
    *,
    verifier_accountability_report: dict[str, Any],
) -> list[dict[str, Any]]:
    bond_by_id = _bond_rows_by_verifier(verifier_accountability_report)
    rows: list[dict[str, Any]] = []
    for challenge in challenge_rows:
        if not challenge.get("blocking"):
            continue
        if challenge.get("status") not in {"open", "accepted"}:
            continue
        targets = list(challenge.get("slash_targets", []))
        if not targets and challenge.get("target_type") == "verifier":
            targets = [str(challenge.get("target_id", ""))]
        for target in targets:
            bond = bond_by_id.get(target, {})
            bond_amount = _decimal(bond.get("bond_amount", "0"))
            challenged_amount = _decimal(challenge.get("challenged_amount", "0"))
            default_slash = (bond_amount * DEFAULT_SLASH_FRACTION).quantize(
                Decimal("0.000001")
            )
            slash_amount = challenged_amount if challenged_amount > 0 else default_slash
            if bond_amount > 0:
                slash_amount = min(slash_amount, bond_amount)
            if challenge.get("status") != "accepted":
                slash_amount = Decimal("0")
            row = {
                "challenge_id": challenge["challenge_id"],
                "slash_target": target,
                "target_type": "verifier",
                "bond_id": str(bond.get("bond_id", "")),
                "bond_amount": _money(bond_amount),
                "slash_amount": _money(slash_amount),
                "currency": str(bond.get("bond_currency", "USD")),
                "slash_status": (
                    "slash_ready"
                    if challenge.get("status") == "accepted"
                    and bool(bond)
                    and bool(bond.get("slashable", False))
                    else "challenge_open"
                    if challenge.get("status") == "open"
                    else "not_slashable"
                ),
                "evidence_hash": challenge["evidence_hash"],
            }
            row["slashing_row_hash"] = hash_payload(row)
            rows.append(row)
    return sorted(rows, key=lambda row: (row["challenge_id"], row["slash_target"]))


def _bounty_rows(slashing_rows: list[dict[str, Any]], challenge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    challenge_by_id = {row["challenge_id"]: row for row in challenge_rows}
    rows: list[dict[str, Any]] = []
    for slash in slashing_rows:
        if slash.get("slash_status") != "slash_ready":
            continue
        challenge = challenge_by_id.get(str(slash.get("challenge_id", "")), {})
        bounty_amount = (_decimal(slash.get("slash_amount", "0")) * DEFAULT_BOUNTY_FRACTION).quantize(
            Decimal("0.000001")
        )
        row = {
            "challenge_id": slash["challenge_id"],
            "opened_by": str(challenge.get("opened_by", "")),
            "bounty_source": "verifier_bond_slash",
            "bounty_amount": _money(bounty_amount),
            "currency": str(slash.get("currency", "USD")),
            "bounty_status": "payable",
            "slashing_row_hash": slash["slashing_row_hash"],
        }
        row["bounty_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["challenge_id"], row["opened_by"]))


def _settlement_rows(
    receipt_transparency_consistency_report: dict[str, Any],
    *,
    direct_settlement_ready: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in receipt_transparency_consistency_report.get("settlement_rows", []):
        prior_payout = _decimal(source.get("payout", "0"))
        prior_escrow = _decimal(source.get("escrow_amount", "0"))
        settlement_value = prior_payout + prior_escrow
        payout = settlement_value if direct_settlement_ready and settlement_value > 0 else Decimal("0")
        escrow_amount = Decimal("0") if direct_settlement_ready else settlement_value
        row = {
            "creator_id": str(source.get("creator_id", "")),
            "work_id": str(source.get("work_id", "")),
            "prior_settlement_decision": str(source.get("settlement_decision", "")),
            "settlement_decision": "accepted"
            if direct_settlement_ready
            else "watchtower_challenge_escrow",
            "payout": _money(payout),
            "escrow_amount": _money(escrow_amount),
            "contribution_weight": float(source.get("contribution_weight", 0.0) or 0.0),
        }
        row["settlement_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_watchtower_challenge_settlement_report(
    *,
    receipt_transparency_consistency_report: dict[str, Any],
    verifier_accountability_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    watchtower_secrets: dict[str, str],
    challenge_rows: list[dict[str, Any]] | None = None,
    required_quorum: int | None = None,
    watchtower_role: str = DEFAULT_WATCHTOWER_ROLE,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an independent watchtower gate over L73 usage receipt settlement."""

    timestamp = created_at or now_iso()
    quorum = required_quorum if required_quorum is not None else DEFAULT_REQUIRED_QUORUM
    subject = _watchtower_subject(
        receipt_transparency_consistency_report=receipt_transparency_consistency_report,
        verifier_accountability_report=verifier_accountability_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    watchtower_rows = _active_watchtower_rows(
        trust_registry,
        watchtower_secrets=watchtower_secrets,
        watchtower_role=watchtower_role,
    )
    active_ids = {
        row["watchtower_id"]
        for row in watchtower_rows
        if row["active_registered_watchtower"]
    }
    attestations = [
        _make_attestation(
            subject,
            watchtower_id=watchtower_id,
            watchtower_role=watchtower_role,
            watchtower_secret=watchtower_secrets[watchtower_id],
            observed_at=timestamp,
        )
        for watchtower_id in sorted(active_ids)
    ]
    challenge_rows_normalized = _normalise_challenge_rows(
        challenge_rows,
        subject=subject,
        created_at=timestamp,
    )
    blocking_challenges = [
        row
        for row in challenge_rows_normalized
        if row["blocking"] and row["status"] in {"open", "accepted"}
    ]
    slashing_rows = _slashing_rows(
        challenge_rows_normalized,
        verifier_accountability_report=verifier_accountability_report,
    )
    bounty_rows = _bounty_rows(slashing_rows, challenge_rows_normalized)
    artifact_bindings = [
        _artifact_binding(
            "receipt_transparency_consistency_report",
            "rdllm-receipt-transparency-consistency-report/v1",
            receipt_transparency_consistency_report,
        ),
        _artifact_binding(
            "verifier_accountability_report",
            "rdllm-verifier-accountability-report/v1",
            verifier_accountability_report,
        ),
        _artifact_binding(
            "trust_registry",
            "rdllm-trust-registry/v1",
            trust_registry,
        ),
        _artifact_binding(
            "provider_attribution_card",
            "rdllm-provider-attribution-card/v1",
            provider_card,
        ),
        _artifact_binding(
            "certification_report",
            "rdllm-certification/v1",
            certification_report,
        ),
    ]
    public_fields = {
        "subject": subject,
        "watchtower_registry_rows": watchtower_rows,
        "watchtower_attestations": attestations,
        "challenge_rows": challenge_rows_normalized,
        "slashing_rows": slashing_rows,
        "bounty_rows": bounty_rows,
        "artifact_bindings": artifact_bindings,
    }
    private_fields = _contains_private_fields(public_fields)
    checks = {
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings
        ),
        "receipt_transparency_consistency_ready": subject["receipt_status"] == "ready"
        and subject["receipt_target_certification_level"] == "RDLLM-L73"
        and subject["receipt_direct_settlement_ready"] is True,
        "verifier_accountability_ready": subject["verifier_accountability_status"]
        == "ready",
        "watchtower_subject_present": bool(subject["subject_hash"]),
        "watchtower_registry_entries_active": bool(watchtower_rows)
        and all(row["active_registered_watchtower"] for row in watchtower_rows),
        "watchtower_quorum_policy_nonzero": quorum > 0,
        "watchtower_quorum_met": len(attestations) >= quorum,
        "watchtower_signatures_valid": True,
        "no_open_or_accepted_blocking_challenges": not blocking_challenges,
        "slashing_rows_hash_reproducible": all(
            hash_payload({key: value for key, value in row.items() if key != "slashing_row_hash"})
            == row["slashing_row_hash"]
            for row in slashing_rows
        ),
        "provider_declares_watchtower_challenge_surface": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("watchtower_challenge_settlement_report")
        is True,
        "provider_declares_watchtower_challenge_channel": provider_card.get(
            "supported_evidence_channels", {}
        ).get("watchtower_challenge_settlement")
        is True,
        "certification_level_at_least_l73": _level_number(
            str(certification_report.get("summary", {}).get("highest_level", ""))
        )
        >= 73,
        "public_report_has_no_private_field_names": not private_fields,
    }
    direct_settlement_ready = all(checks.values())
    settlement_rows = _settlement_rows(
        receipt_transparency_consistency_report,
        direct_settlement_ready=direct_settlement_ready,
    )
    payout_total = sum(
        _decimal(row.get("payout", "0")) for row in settlement_rows
    )
    escrow_total = sum(
        _decimal(row.get("escrow_amount", "0")) for row in settlement_rows
    )
    upstream_pool = sum(
        _decimal(row.get("payout", "0")) + _decimal(row.get("escrow_amount", "0"))
        for row in receipt_transparency_consistency_report.get("settlement_rows", [])
    )
    checks["creator_pool_conserved_or_escrowed"] = payout_total + escrow_total == upstream_pool
    direct_settlement_ready = all(checks.values())
    if not direct_settlement_ready:
        settlement_rows = _settlement_rows(
            receipt_transparency_consistency_report,
            direct_settlement_ready=False,
        )
        payout_total = Decimal("0")
        escrow_total = sum(
            _decimal(row.get("escrow_amount", "0")) for row in settlement_rows
        )

    report = {
        "report_version": WATCHTOWER_CHALLENGE_SETTLEMENT_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": "rdllm-watchtower-challenge-settlement-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "watchtower_role": watchtower_role,
            "required_watchtower_quorum": quorum,
            "direct_settlement_requires": [
                "ready_receipt_transparency_consistency_report",
                "active_registered_independent_watchtower_quorum",
                "watchtower_subject_attestations",
                "no_open_or_accepted_blocking_challenges",
                "creator_pool_conservation",
            ],
            "challenge_statuses_that_block_direct_settlement": ["open", "accepted"],
            "failure_route": "watchtower_challenge_escrow",
            "accepted_challenge_slashing_fraction": _money(DEFAULT_SLASH_FRACTION),
            "accepted_challenge_bounty_fraction": _money(DEFAULT_BOUNTY_FRACTION),
        },
        "artifact_bindings": {
            "artifact_count": len(artifact_bindings),
            "artifact_binding_root": merkle_root(
                [row["binding_hash"] for row in artifact_bindings]
            ),
            "bindings": artifact_bindings,
            "receipt_transparency_consistency_report_hash": artifact_bindings[0][
                "declared_hash"
            ],
            "verifier_accountability_report_hash": artifact_bindings[1][
                "declared_hash"
            ],
            "trust_registry_hash": artifact_bindings[2]["declared_hash"],
            "provider_card_hash": artifact_bindings[3]["declared_hash"],
            "certification_report_hash": artifact_bindings[4]["declared_hash"],
        },
        "watchtower_subject": subject,
        "watchtower_registry_rows": watchtower_rows,
        "watchtower_attestations": attestations,
        "watchtower_quorum": {
            "required_quorum": quorum,
            "registered_watchtower_count": len(watchtower_rows),
            "active_watchtower_count": len(active_ids),
            "attestation_count": len(attestations),
            "attesting_watchtower_ids": sorted(
                attestation["watchtower_id"] for attestation in attestations
            ),
            "quorum_met": len(attestations) >= quorum,
        },
        "challenge_rows": challenge_rows_normalized,
        "slashing_evidence_rows": slashing_rows,
        "bounty_rows": bounty_rows,
        "settlement_gate": {
            "decision": "watchtower_challenge_settlement_ready"
            if direct_settlement_ready
            else "watchtower_challenge_escrow",
            "direct_settlement_ready": direct_settlement_ready,
            "blocking_challenge_count": len(blocking_challenges),
            "open_challenge_count": len(
                [row for row in blocking_challenges if row["status"] == "open"]
            ),
            "accepted_challenge_count": len(
                [row for row in blocking_challenges if row["status"] == "accepted"]
            ),
            "slash_ready_count": len(
                [row for row in slashing_rows if row["slash_status"] == "slash_ready"]
            ),
        },
        "settlement_rows": settlement_rows,
        "commitments": {
            "watchtower_subject_hash": subject["subject_hash"],
            "watchtower_registry_root": merkle_root(
                [row["watchtower_row_hash"] for row in watchtower_rows]
            ),
            "watchtower_attestation_root": merkle_root(
                [row["attestation_hash"] for row in attestations]
            ),
            "challenge_row_root": merkle_root(
                [row["challenge_row_hash"] for row in challenge_rows_normalized]
            ),
            "slashing_evidence_root": merkle_root(
                [row["slashing_row_hash"] for row in slashing_rows]
            ),
            "bounty_row_root": merkle_root(
                [row["bounty_row_hash"] for row in bounty_rows]
            ),
            "settlement_row_root": merkle_root(
                [row["settlement_row_hash"] for row in settlement_rows]
            ),
        },
        "checks": checks,
        "schemas": {
            "watchtower_challenge_settlement_report": WATCHTOWER_CHALLENGE_SETTLEMENT_SCHEMA,
            "receipt_transparency_consistency_report": "docs/schemas/receipt_transparency_consistency_report.schema.json",
            "verifier_accountability_report": "docs/schemas/verifier_accountability_report.schema.json",
            "trust_registry": "docs/schemas/trust_registry.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "ready" if direct_settlement_ready else "escrow",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "watchtower_subject_hash": subject["subject_hash"],
            "required_watchtower_quorum": quorum,
            "registered_watchtower_count": len(watchtower_rows),
            "active_watchtower_count": len(active_ids),
            "attestation_count": len(attestations),
            "blocking_challenge_count": len(blocking_challenges),
            "open_challenge_count": len(
                [row for row in blocking_challenges if row["status"] == "open"]
            ),
            "accepted_challenge_count": len(
                [row for row in blocking_challenges if row["status"] == "accepted"]
            ),
            "slash_ready_count": len(
                [row for row in slashing_rows if row["slash_status"] == "slash_ready"]
            ),
            "bounty_row_count": len(bounty_rows),
            "settlement_decision": "watchtower_challenge_settlement_ready"
            if direct_settlement_ready
            else "watchtower_challenge_escrow",
            "direct_settlement_ready": direct_settlement_ready,
            "settlement_row_count": len(settlement_rows),
            "payout_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
            "creator_pool_conserved_or_escrowed": checks[
                "creator_pool_conserved_or_escrowed"
            ],
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "receipt_payload_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "watchtower_report_uses_hashes_attestations_challenges_and_roots": True,
        },
    }
    report["watchtower_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_watchtower_challenge_settlement_report_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "watchtower_subject",
        "watchtower_registry_rows",
        "watchtower_attestations",
        "watchtower_quorum",
        "challenge_rows",
        "slashing_evidence_rows",
        "bounty_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "watchtower_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing watchtower challenge settlement field: {key}")
    if errors:
        return errors
    if report.get("report_version") != WATCHTOWER_CHALLENGE_SETTLEMENT_VERSION:
        errors.append("watchtower challenge settlement version is unsupported")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("watchtower challenge settlement target level is invalid")
    for key in (
        "subject_hash",
        "receipt_transparency_consistency_report_hash",
        "receipt_status",
        "receipt_settlement_decision",
    ):
        if key not in report.get("watchtower_subject", {}):
            errors.append(f"missing watchtower subject field: {key}")
    for row in report.get("watchtower_attestations", []):
        for key in (
            "watchtower_id",
            "watchtower_key_hash",
            "subject_hash",
            "signature",
            "attestation_hash",
        ):
            if key not in row:
                errors.append(f"missing watchtower attestation field: {key}")
    for row in report.get("challenge_rows", []):
        for key in (
            "challenge_id",
            "status",
            "reason_code",
            "evidence_hash",
            "blocking",
            "challenge_row_hash",
        ):
            if key not in row:
                errors.append(f"missing watchtower challenge field: {key}")
    if "watchtower_challenge_settlement_report" not in report.get("schemas", {}):
        errors.append("missing watchtower challenge settlement schema")
    return errors


def verify_watchtower_challenge_settlement_report(
    report: dict[str, Any],
    *,
    receipt_transparency_consistency_report: dict[str, Any],
    verifier_accountability_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    watchtower_secrets: dict[str, str],
    challenge_rows: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a watchtower challenge settlement report against public artifacts."""

    errors = validate_watchtower_challenge_settlement_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("watchtower_report_hash"):
        errors.append("watchtower challenge settlement hash is not reproducible")

    expected = make_watchtower_challenge_settlement_report(
        receipt_transparency_consistency_report=receipt_transparency_consistency_report,
        verifier_accountability_report=verifier_accountability_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        watchtower_secrets=watchtower_secrets,
        challenge_rows=challenge_rows,
        required_quorum=int(report.get("policy", {}).get("required_watchtower_quorum", 0)),
        watchtower_role=str(
            report.get("policy", {}).get("watchtower_role", DEFAULT_WATCHTOWER_ROLE)
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "watchtower_subject",
        "watchtower_registry_rows",
        "watchtower_attestations",
        "watchtower_quorum",
        "challenge_rows",
        "slashing_evidence_rows",
        "bounty_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"watchtower challenge settlement {key} does not match replay")
    if expected.get("watchtower_report_hash") != report.get("watchtower_report_hash"):
        errors.append("watchtower challenge settlement hash does not match replay")

    secret_by_id = dict(watchtower_secrets)
    subject = report.get("watchtower_subject", {})
    for attestation in report.get("watchtower_attestations", []):
        watchtower_id = str(attestation.get("watchtower_id", ""))
        secret = secret_by_id.get(watchtower_id)
        if not secret:
            errors.append(f"unknown watchtower attestation signer: {watchtower_id}")
            continue
        payload = _attestation_payload(
            subject,
            watchtower_id=watchtower_id,
            watchtower_role=str(attestation.get("watchtower_role", DEFAULT_WATCHTOWER_ROLE)),
            watchtower_secret=secret,
            observed_at=str(attestation.get("observed_at", "")),
        )
        if payload["watchtower_key_hash"] != attestation.get("watchtower_key_hash"):
            errors.append(f"watchtower key hash is invalid: {watchtower_id}")
        if sign_payload(payload, secret) != attestation.get("signature"):
            errors.append(f"watchtower signature is invalid: {watchtower_id}")
        if hash_payload(_hashable_attestation(attestation)) != attestation.get(
            "attestation_hash"
        ):
            errors.append(f"watchtower attestation hash is invalid: {watchtower_id}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("watchtower challenge settlement report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("watchtower challenge settlement signature is invalid")
    return errors
