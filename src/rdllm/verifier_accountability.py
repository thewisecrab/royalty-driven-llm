"""Bonded verifier accountability reports for RDLLM settlement gates."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

VERIFIER_ACCOUNTABILITY_VERSION = "rdllm-verifier-accountability-report/v1"
VERIFIER_ACCOUNTABILITY_SCHEMA = (
    "docs/schemas/verifier_accountability_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L72"
POLICY_VERSION = "rdllm-bonded-verifier-accountability-policy/v1"
DEFAULT_MINIMUM_BOND_AMOUNT = Decimal("1000.00")
DEFAULT_BOND_CURRENCY = "USD"

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
    "profile_hash",
    "card_hash",
    "report_hash",
    "attestation_hash",
    "manifest_hash",
    "bundle_hash",
    "graph_hash",
    "envelope_hash",
    "receipt_hash",
    "event_hash",
)


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


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
        if key not in {"report_hash", "signature"}
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


def _artifact_binding(
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    row["binding_hash"] = hash_payload(row)
    return row


def _artifact_bindings(
    *,
    verifier_quorum_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    rows = sorted(
        [
            _artifact_binding(
                "verifier_quorum_report",
                "rdllm-verifier-quorum-report/v1",
                verifier_quorum_report,
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
        ],
        key=lambda row: row["name"],
    )
    by_name = {row["name"]: row for row in rows}
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": hash_payload(rows),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in rows
        ),
        "verifier_quorum_report_hash": by_name["verifier_quorum_report"][
            "declared_hash"
        ],
        "trust_registry_hash": by_name["trust_registry"]["declared_hash"],
        "provider_card_hash": by_name["provider_attribution_card"]["declared_hash"],
        "certification_report_hash": by_name["certification_report"][
            "declared_hash"
        ],
        "bindings": rows,
    }


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


def _verifier_key_hash(verifier_id: str, verifier_secret: str) -> str:
    return stable_hash(f"rdllm-verifier-key:{verifier_id}:{verifier_secret}")


def _accepted_verifier_rows(verifier_quorum_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in verifier_quorum_report.get("verifier_rows", []):
        if row.get("replay_verdict") != "accepted":
            continue
        checks = row.get("checks", {})
        if not isinstance(checks, dict) or not all(bool(value) for value in checks.values()):
            continue
        rows.append(
            {
                "verifier_id": str(row.get("verifier_id", "")),
                "organization_id": str(row.get("organization_id", "")),
                "role": str(row.get("role", "")),
                "trust_tier": str(row.get("trust_tier", "")),
                "verifier_key_hash": str(row.get("verifier_key_hash", "")),
                "attestation_hash": str(row.get("attestation_hash", "")),
                "artifact_binding_root": str(row.get("artifact_binding_root", "")),
                "replay_verdict": str(row.get("replay_verdict", "")),
            }
        )
    return sorted(rows, key=lambda item: item["verifier_id"])


def _registry_rows(
    trust_registry: dict[str, Any],
    accepted_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accepted_ids = {row["verifier_id"] for row in accepted_rows}
    accepted_key_hashes = {row["verifier_key_hash"] for row in accepted_rows}
    revoked_hashes = {
        str(row.get("key_hash", ""))
        for row in trust_registry.get("revoked_keys", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for principal in trust_registry.get("principals", []):
        if not isinstance(principal, dict):
            continue
        key_hashes = {
            str(principal.get("key_hash", "")),
            str(principal.get("verifier_key_hash", "")),
        }
        for item in principal.get("alternate_key_hashes", []):
            key_hashes.add(str(item))
        verifier_id = str(principal.get("principal_id", ""))
        if verifier_id not in accepted_ids and not (accepted_key_hashes & key_hashes):
            continue
        row = {
            "verifier_id": verifier_id,
            "role": str(principal.get("role", "")),
            "key_id": str(principal.get("key_id", "")),
            "registry_key_hash": str(principal.get("key_hash", "")),
            "verifier_key_hash": str(principal.get("verifier_key_hash", "")),
            "status": str(principal.get("status", "")),
            "key_hash_matches_verifier_attestation": bool(
                accepted_key_hashes & key_hashes
            ),
            "revoked_key_used": bool(key_hashes & revoked_hashes),
        }
        row["registry_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["verifier_id"])


def _default_bond_specs(
    accepted_rows: list[dict[str, Any]],
    *,
    minimum_bond_amount: Decimal,
    created_at: str,
) -> list[dict[str, Any]]:
    return [
        {
            "verifier_id": row["verifier_id"],
            "organization_id": row["organization_id"],
            "bond_id": stable_hash(f"rdllm-verifier-bond:{row['verifier_id']}")[:24],
            "bond_amount": _money(minimum_bond_amount),
            "bond_currency": DEFAULT_BOND_CURRENCY,
            "bond_escrow_account_hash": stable_hash(
                f"rdllm-verifier-bond-escrow:{row['verifier_id']}"
            ),
            "valid_from": created_at,
            "valid_until": "9999-12-31T23:59:59Z",
            "conflict_disclosure_hash": stable_hash(
                f"rdllm-conflict-disclosure:none:{row['verifier_id']}"
            ),
            "conflict_status": "none_declared",
            "active": True,
            "slashable": True,
            "duties": [
                "replay_public_artifact_hashes",
                "verify_citation_footer_and_claim_support",
                "verify_consensus_payout_conservation",
                "disclose_conflicts",
                "accept_slashing_for_bad_or_conflicted_attestation",
            ],
        }
        for row in accepted_rows
    ]


def _normalise_bond_specs(
    bond_specs: list[dict[str, Any]] | None,
    *,
    accepted_rows: list[dict[str, Any]],
    minimum_bond_amount: Decimal,
    created_at: str,
) -> list[dict[str, Any]]:
    specs = bond_specs
    if specs is None:
        specs = _default_bond_specs(
            accepted_rows,
            minimum_bond_amount=minimum_bond_amount,
            created_at=created_at,
        )
    rows: list[dict[str, Any]] = []
    accepted_by_id = {row["verifier_id"]: row for row in accepted_rows}
    for spec in specs:
        verifier_id = str(spec.get("verifier_id", "")).strip()
        if not verifier_id:
            continue
        accepted = accepted_by_id.get(verifier_id, {})
        row = {
            "verifier_id": verifier_id,
            "organization_id": str(
                spec.get("organization_id") or accepted.get("organization_id", "")
            ),
            "bond_id": str(
                spec.get("bond_id")
                or stable_hash(f"rdllm-verifier-bond:{verifier_id}")[:24]
            ),
            "bond_amount": _money(_decimal(spec.get("bond_amount", minimum_bond_amount))),
            "bond_currency": str(spec.get("bond_currency") or DEFAULT_BOND_CURRENCY),
            "bond_escrow_account_hash": str(
                spec.get("bond_escrow_account_hash")
                or stable_hash(f"rdllm-verifier-bond-escrow:{verifier_id}")
            ),
            "valid_from": str(spec.get("valid_from") or created_at),
            "valid_until": str(spec.get("valid_until") or "9999-12-31T23:59:59Z"),
            "conflict_disclosure_hash": str(
                spec.get("conflict_disclosure_hash")
                or stable_hash(f"rdllm-conflict-disclosure:none:{verifier_id}")
            ),
            "conflict_status": str(spec.get("conflict_status") or "none_declared"),
            "active": bool(spec.get("active", True)),
            "slashable": bool(spec.get("slashable", True)),
            "duties": list(spec.get("duties") or [
                "replay_public_artifact_hashes",
                "verify_citation_footer_and_claim_support",
                "verify_consensus_payout_conservation",
                "disclose_conflicts",
                "accept_slashing_for_bad_or_conflicted_attestation",
            ]),
        }
        row["bond_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["verifier_id"])


def _normalise_challenge_rows(
    challenge_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, challenge in enumerate(challenge_rows or [], start=1):
        row = {
            "challenge_id": str(
                challenge.get("challenge_id")
                or f"verifier-accountability-challenge-{index}"
            ),
            "verifier_id": str(challenge.get("verifier_id", "")),
            "status": str(challenge.get("status") or "open"),
            "reason_code": str(challenge.get("reason_code") or "unspecified"),
            "evidence_hash": str(challenge.get("evidence_hash") or ""),
            "opened_at": str(challenge.get("opened_at") or ""),
            "resolved_at": str(challenge.get("resolved_at") or ""),
            "blocking": bool(challenge.get("blocking", True)),
        }
        row["challenge_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["challenge_id"])


def _settlement_rows(
    verifier_quorum_report: dict[str, Any],
    *,
    accountability_ready: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in verifier_quorum_report.get("settlement_rows", []):
        prior_payout = _decimal(source.get("payout", "0"))
        prior_escrow = _decimal(source.get("escrow_amount", "0"))
        settlement_value = prior_payout + prior_escrow
        if accountability_ready and prior_payout > 0:
            payout = prior_payout
            escrow_amount = Decimal("0")
            decision = str(source.get("settlement_decision", "accepted"))
        else:
            payout = Decimal("0")
            escrow_amount = settlement_value
            decision = "bonded_verifier_accountability_escrow"
        row = {
            "creator_id": str(source.get("creator_id", "")),
            "work_id": str(source.get("work_id", "")),
            "prior_settlement_decision": str(source.get("settlement_decision", "")),
            "settlement_decision": decision,
            "consensus_payout": str(source.get("consensus_payout", "0.000000")),
            "payout": _money(payout),
            "escrow_amount": _money(escrow_amount),
            "contribution_weight": float(source.get("contribution_weight", 0.0) or 0.0),
        }
        row["settlement_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _bond_specs_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "verifier_id": row.get("verifier_id", ""),
            "organization_id": row.get("organization_id", ""),
            "bond_id": row.get("bond_id", ""),
            "bond_amount": row.get("bond_amount", ""),
            "bond_currency": row.get("bond_currency", ""),
            "bond_escrow_account_hash": row.get("bond_escrow_account_hash", ""),
            "valid_from": row.get("valid_from", ""),
            "valid_until": row.get("valid_until", ""),
            "conflict_disclosure_hash": row.get("conflict_disclosure_hash", ""),
            "conflict_status": row.get("conflict_status", ""),
            "active": row.get("active", False),
            "slashable": row.get("slashable", False),
            "duties": row.get("duties", []),
        }
        for row in report.get("bond_rows", [])
    ]


def make_verifier_accountability_report(
    *,
    verifier_quorum_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    bond_specs: list[dict[str, Any]] | None = None,
    challenge_rows: list[dict[str, Any]] | None = None,
    minimum_bond_amount: Decimal | str | float = DEFAULT_MINIMUM_BOND_AMOUNT,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public settlement gate for bonded, slashable verifier accountability."""

    timestamp = created_at or now_iso()
    minimum_bond = _decimal(minimum_bond_amount)
    bindings = _artifact_bindings(
        verifier_quorum_report=verifier_quorum_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    accepted_rows = _accepted_verifier_rows(verifier_quorum_report)
    registry_rows = _registry_rows(trust_registry, accepted_rows)
    bond_rows = _normalise_bond_specs(
        bond_specs,
        accepted_rows=accepted_rows,
        minimum_bond_amount=minimum_bond,
        created_at=timestamp,
    )
    challenges = _normalise_challenge_rows(challenge_rows)
    accepted_ids = {row["verifier_id"] for row in accepted_rows}
    registry_ids = {
        row["verifier_id"]
        for row in registry_rows
        if row["status"] == "active" and row["key_hash_matches_verifier_attestation"]
    }
    bond_by_id = {row["verifier_id"]: row for row in bond_rows}
    blocking_challenges = [
        row
        for row in challenges
        if row["blocking"] and row["status"] in {"open", "accepted", "pending"}
    ]
    conflict_bond_rows = [
        row
        for row in bond_rows
        if row["conflict_status"] not in {"none_declared", "cleared"}
    ]
    verifier_quorum_ready = (
        verifier_quorum_report.get("summary", {}).get("status") == "ready"
        and verifier_quorum_report.get("summary", {}).get("direct_settlement_ready")
        is True
    )
    checks = {
        "verifier_quorum_ready": verifier_quorum_ready,
        "verifier_quorum_target_l71": verifier_quorum_report.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L71",
        "trust_registry_ready": trust_registry.get("summary", {}).get("status")
        == "ready",
        "provider_declares_verifier_accountability_surface": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("verifier_accountability_report")
        is True,
        "provider_declares_bonded_verifier_accountability_channel": provider_card.get(
            "supported_evidence_channels", {}
        ).get("bonded_verifier_accountability")
        is True,
        "certification_level_at_least_l71": _level_number(
            str(certification_report.get("summary", {}).get("highest_level", ""))
        )
        >= 71,
        "accepted_verifiers_have_active_registry_entries": bool(accepted_ids)
        and accepted_ids.issubset(registry_ids),
        "accepted_verifier_key_hashes_match_registry": all(
            row["key_hash_matches_verifier_attestation"] for row in registry_rows
        )
        and accepted_ids.issubset(registry_ids),
        "registry_keys_not_revoked": not any(
            row["revoked_key_used"] for row in registry_rows
        ),
        "accepted_verifiers_have_active_bonds": bool(accepted_ids)
        and all(
            verifier_id in bond_by_id and bond_by_id[verifier_id]["active"]
            for verifier_id in accepted_ids
        ),
        "bond_coverage_meets_policy": bool(accepted_ids)
        and all(
            _decimal(bond_by_id.get(verifier_id, {}).get("bond_amount", "0"))
            >= minimum_bond
            for verifier_id in accepted_ids
        ),
        "bond_rows_are_slashable": bool(accepted_ids)
        and all(
            bond_by_id.get(verifier_id, {}).get("slashable") is True
            for verifier_id in accepted_ids
        ),
        "conflict_disclosures_present": bool(accepted_ids)
        and all(
            bool(bond_by_id.get(verifier_id, {}).get("conflict_disclosure_hash"))
            for verifier_id in accepted_ids
        ),
        "no_blocking_conflicts": not conflict_bond_rows,
        "no_open_accountability_challenges": not blocking_challenges,
        "artifact_hashes_reproducible": bindings["artifact_hashes_reproducible"],
    }
    accountability_ready = all(checks.values())
    settlement_rows = _settlement_rows(
        verifier_quorum_report,
        accountability_ready=accountability_ready,
    )
    payout_total = sum((_decimal(row["payout"]) for row in settlement_rows), Decimal("0"))
    escrow_total = sum(
        (_decimal(row["escrow_amount"]) for row in settlement_rows), Decimal("0")
    )
    upstream_total = sum(
        (
            _decimal(row.get("payout", "0")) + _decimal(row.get("escrow_amount", "0"))
            for row in verifier_quorum_report.get("settlement_rows", [])
        ),
        Decimal("0"),
    )
    checks["creator_pool_conserved_or_escrowed"] = (
        _money(payout_total + escrow_total) == _money(upstream_total)
    )
    checks["public_report_has_no_private_field_names"] = not _contains_private_fields(
        {
            "artifact_bindings": bindings,
            "accepted_verifier_rows": accepted_rows,
            "registry_rows": registry_rows,
            "bond_rows": bond_rows,
            "challenge_rows": challenges,
            "settlement_rows": settlement_rows,
        }
    )
    accountability_ready = all(checks.values())
    settlement_decision = (
        "bonded_verifier_settlement_ready"
        if accountability_ready
        else "bonded_verifier_accountability_escrow"
    )
    escrow_reasons = [
        check for check, passed in checks.items() if passed is not True
    ]
    slashing_evidence_rows = [
        {
            "verifier_id": row["verifier_id"],
            "challenge_id": row["challenge_id"],
            "reason_code": row["reason_code"],
            "evidence_hash": row["evidence_hash"],
            "slash_status": (
                "slash_ready" if row["status"] == "accepted" else "challenge_open"
            ),
        }
        for row in blocking_challenges
    ]
    for row in slashing_evidence_rows:
        row["slashing_evidence_hash"] = hash_payload(row)

    report = {
        "report_version": VERIFIER_ACCOUNTABILITY_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_bond_amount": _money(minimum_bond),
            "bond_currency": DEFAULT_BOND_CURRENCY,
            "direct_settlement_requires": [
                "accepted_verifier_quorum",
                "active_trust_registry_entries",
                "non_revoked_verifier_keys",
                "active_slashable_bonds",
                "conflict_disclosures",
                "no_open_accountability_challenges",
            ],
            "failure_route": "bonded_verifier_accountability_escrow",
        },
        "artifact_bindings": bindings,
        "accepted_verifier_rows": accepted_rows,
        "registry_rows": registry_rows,
        "bond_rows": bond_rows,
        "challenge_rows": challenges,
        "slashing_policy": {
            "slashable_events": [
                "bad_artifact_replay_attestation",
                "undisclosed_conflict_of_interest",
                "revoked_or_unregistered_key_use",
                "accepted_challenge_against_verifier_attestation",
            ],
            "evidence_required": [
                "verifier_attestation_hash",
                "registry_row_hash",
                "bond_row_hash",
                "challenge_evidence_hash",
            ],
            "slashing_evidence_root": hash_payload(slashing_evidence_rows),
        },
        "slashing_evidence_rows": slashing_evidence_rows,
        "settlement_gate": {
            "decision": settlement_decision,
            "direct_settlement_ready": accountability_ready,
            "escrow_reasons": escrow_reasons,
            "accepted_verifier_count": len(accepted_rows),
            "registry_verified_verifier_count": len(registry_ids & accepted_ids),
            "bonded_verifier_count": len(
                [
                    verifier_id
                    for verifier_id in accepted_ids
                    if verifier_id in bond_by_id
                    and bond_by_id[verifier_id]["active"]
                    and bond_by_id[verifier_id]["slashable"]
                ]
            ),
            "blocking_challenge_count": len(blocking_challenges),
            "blocking_conflict_count": len(conflict_bond_rows),
        },
        "settlement_rows": settlement_rows,
        "commitments": {
            "schema": VERIFIER_ACCOUNTABILITY_SCHEMA,
            "artifact_binding_root": bindings["artifact_binding_root"],
            "accepted_verifier_root": hash_payload(accepted_rows),
            "registry_row_root": hash_payload(registry_rows),
            "bond_row_root": hash_payload(bond_rows),
            "challenge_row_root": hash_payload(challenges),
            "slashing_evidence_root": hash_payload(slashing_evidence_rows),
            "settlement_row_root": hash_payload(settlement_rows),
        },
        "checks": checks,
        "schemas": {
            "verifier_accountability_report": VERIFIER_ACCOUNTABILITY_SCHEMA,
            "verifier_quorum_report": "docs/schemas/verifier_quorum_report.schema.json",
            "trust_registry": "docs/schemas/trust_registry.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "ready" if accountability_ready else "escrow",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "accepted_verifier_count": len(accepted_rows),
            "registry_verified_verifier_count": len(registry_ids & accepted_ids),
            "bonded_verifier_count": len(
                [
                    verifier_id
                    for verifier_id in accepted_ids
                    if verifier_id in bond_by_id
                    and bond_by_id[verifier_id]["active"]
                    and bond_by_id[verifier_id]["slashable"]
                ]
            ),
            "minimum_bond_amount": _money(minimum_bond),
            "blocking_challenge_count": len(blocking_challenges),
            "blocking_conflict_count": len(conflict_bond_rows),
            "settlement_decision": settlement_decision,
            "direct_settlement_ready": accountability_ready,
            "settlement_row_count": len(settlement_rows),
            "payout_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
            "creator_pool_conserved_or_escrowed": checks[
                "creator_pool_conserved_or_escrowed"
            ],
            "offline_verification_supported": True,
        },
        "privacy": {
            "private_prompt_disclosed": False,
            "private_response_disclosed": False,
            "private_source_text_disclosed": False,
            "private_finance_payload_disclosed": False,
            "verifier_private_notes_disclosed": False,
            "raw_bond_account_disclosed": False,
            "report_uses_hashes_bonds_conflict_status_and_challenge_status": True,
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


def validate_verifier_accountability_report_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "accepted_verifier_rows",
        "registry_rows",
        "bond_rows",
        "challenge_rows",
        "slashing_policy",
        "slashing_evidence_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing verifier accountability field: {key}")
    if errors:
        return errors
    if report.get("report_version") != VERIFIER_ACCOUNTABILITY_VERSION:
        errors.append("verifier accountability report version is unsupported")
    if report.get("policy", {}).get("profile") != POLICY_VERSION:
        errors.append("verifier accountability policy is unsupported")
    if (
        report.get("policy", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("verifier accountability target certification level is unsupported")
    for key in (
        "verifier_quorum_report_hash",
        "trust_registry_hash",
        "provider_card_hash",
        "certification_report_hash",
    ):
        if not report.get("artifact_bindings", {}).get(key):
            errors.append(f"missing verifier accountability artifact binding: {key}")
    for row in report.get("bond_rows", []):
        for key in (
            "verifier_id",
            "bond_id",
            "bond_amount",
            "bond_escrow_account_hash",
            "conflict_disclosure_hash",
            "active",
            "slashable",
            "bond_row_hash",
        ):
            if key not in row:
                errors.append(f"missing verifier bond row field: {key}")
    if "verifier_accountability_report" not in report.get("schemas", {}):
        errors.append("missing verifier accountability schema")
    return errors


def verify_verifier_accountability_report(
    report: dict[str, Any],
    *,
    verifier_quorum_report: dict[str, Any],
    trust_registry: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a bonded verifier accountability report against public artifacts."""

    errors = validate_verifier_accountability_report_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("verifier accountability report hash is not reproducible")

    expected = make_verifier_accountability_report(
        verifier_quorum_report=verifier_quorum_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        bond_specs=_bond_specs_from_report(report),
        challenge_rows=report.get("challenge_rows", []),
        minimum_bond_amount=report.get("policy", {}).get(
            "minimum_bond_amount", DEFAULT_MINIMUM_BOND_AMOUNT
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "accepted_verifier_rows",
        "registry_rows",
        "bond_rows",
        "challenge_rows",
        "slashing_policy",
        "slashing_evidence_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(
                f"verifier accountability {key} does not match replayed artifacts"
            )
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append(
            "verifier accountability report hash does not match replayed artifacts"
        )

    for check in (
        "artifact_hashes_reproducible",
        "creator_pool_conserved_or_escrowed",
        "public_report_has_no_private_field_names",
    ):
        if report.get("checks", {}).get(check) is not True:
            errors.append(f"verifier accountability required check failed: {check}")
    if report.get("summary", {}).get("status") == "ready":
        for check in (
            "accepted_verifiers_have_active_registry_entries",
            "accepted_verifiers_have_active_bonds",
            "bond_coverage_meets_policy",
            "bond_rows_are_slashable",
            "no_blocking_conflicts",
            "no_open_accountability_challenges",
        ):
            if report.get("checks", {}).get(check) is not True:
                errors.append(f"ready verifier accountability missing check: {check}")
    if report.get("summary", {}).get("status") not in {"ready", "escrow"}:
        errors.append("verifier accountability status is unsupported")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("verifier accountability report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("verifier accountability report signature is invalid")

    return errors
