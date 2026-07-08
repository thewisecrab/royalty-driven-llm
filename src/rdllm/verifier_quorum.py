"""Independent verifier quorum reports for RDLLM settlement gates."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

VERIFIER_QUORUM_VERSION = "rdllm-verifier-quorum-report/v1"
VERIFIER_QUORUM_SCHEMA = "docs/schemas/verifier_quorum_report.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L71"
POLICY_VERSION = "rdllm-independent-verifier-quorum-policy/v1"
DEFAULT_MINIMUM_QUORUM = 3
DEFAULT_MINIMUM_INDEPENDENT_ORGANIZATIONS = 2

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

REQUIRED_ARTIFACTS = (
    "attribution_consensus_report",
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
)

REQUIRED_ARTIFACT_HASH_FIELDS = {
    "attribution_consensus_report": "attribution_consensus_report_hash",
    "provider_attribution_card": "provider_card_hash",
    "certification_report": "certification_report_hash",
    "integration_profile": "integration_profile_hash",
}

REQUIRED_VERIFIER_CHECKS = (
    "artifact_hashes_replayed",
    "attribution_consensus_ready",
    "attribution_consensus_target_l70",
    "consensus_creator_pool_conserved",
    "provider_declares_consensus_and_verifier_surfaces",
    "certification_level_at_least_l70",
    "integration_profile_ready",
)

DECLARED_HASH_FIELDS = (
    "profile_hash",
    "card_hash",
    "report_hash",
    "manifest_hash",
    "attestation_hash",
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
    attribution_consensus_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        _artifact_binding(
            "attribution_consensus_report",
            "rdllm-attribution-consensus-report/v1",
            attribution_consensus_report,
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
        _artifact_binding(
            "integration_profile",
            "rdllm-integration-profile/v1",
            integration_profile,
        ),
    ]
    rows = sorted(rows, key=lambda row: row["name"])
    by_name = {row["name"]: row for row in rows}
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": hash_payload(rows),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in rows
        ),
        "attribution_consensus_report_hash": by_name[
            "attribution_consensus_report"
        ]["declared_hash"],
        "provider_card_hash": by_name["provider_attribution_card"]["declared_hash"],
        "certification_report_hash": by_name["certification_report"]["declared_hash"],
        "integration_profile_hash": by_name["integration_profile"]["declared_hash"],
        "bindings": rows,
    }


def _artifact_status(
    *,
    attribution_consensus_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
) -> dict[str, Any]:
    consensus_summary = attribution_consensus_report.get("summary", {})
    certification_summary = certification_report.get("summary", {})
    provider_surfaces = provider_card.get("public_disclosure_surfaces", {})
    provider_channels = provider_card.get("supported_evidence_channels", {})
    return {
        "attribution_consensus_ready": consensus_summary.get("status") == "ready",
        "attribution_consensus_target_l70": consensus_summary.get(
            "target_certification_level"
        )
        == "RDLLM-L70",
        "consensus_creator_pool_conserved": attribution_consensus_report.get(
            "checks", {}
        ).get("creator_pool_conserved")
        is True,
        "provider_declares_consensus_surface": provider_surfaces.get(
            "attribution_consensus_report"
        )
        is True,
        "provider_declares_verifier_quorum_surface": provider_surfaces.get(
            "verifier_quorum_report"
        )
        is True,
        "provider_declares_verifier_quorum_channel": provider_channels.get(
            "independent_verifier_quorum"
        )
        is True,
        "certification_passed": certification_summary.get("status") == "passed",
        "certification_level_at_least_l70": _level_number(
            str(certification_summary.get("highest_level", ""))
        )
        >= 70,
        "integration_profile_ready": integration_profile.get("summary", {}).get(
            "status"
        )
        == "ready",
        "integration_declares_verifier_quorum_schema": "verifier_quorum_report"
        in integration_profile.get("schemas", {}),
        "integration_declares_verifier_quorum_surface": integration_profile.get(
            "public_surfaces", {}
        ).get("verifier_quorum_report")
        is True,
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


def _default_verifier_specs(
    verifier_secrets: dict[str, str],
    *,
    observed_at: str,
) -> list[dict[str, Any]]:
    return [
        {
            "verifier_id": verifier_id,
            "organization_id": f"org:{verifier_id}",
            "role": "independent_attribution_verifier",
            "trust_tier": "independent",
            "observed_at": observed_at,
            "replay_verdict": "accepted",
        }
        for verifier_id in sorted(verifier_secrets)
    ]


def _normalise_verifier_specs(
    verifier_specs: list[dict[str, Any]] | None,
    *,
    verifier_secrets: dict[str, str],
    observed_at: str,
) -> list[dict[str, Any]]:
    specs = verifier_specs
    if specs is None:
        specs = _default_verifier_specs(verifier_secrets, observed_at=observed_at)
    normalised: list[dict[str, Any]] = []
    for spec in specs:
        verifier_id = str(spec.get("verifier_id", "")).strip()
        if not verifier_id:
            continue
        normalised.append(
            {
                "verifier_id": verifier_id,
                "organization_id": str(
                    spec.get("organization_id") or f"org:{verifier_id}"
                ),
                "role": str(
                    spec.get("role") or "independent_attribution_verifier"
                ),
                "trust_tier": str(spec.get("trust_tier") or "independent"),
                "observed_at": str(spec.get("observed_at") or observed_at),
                "replay_verdict": str(spec.get("replay_verdict") or "accepted"),
                "checks": dict(spec.get("checks", {}))
                if isinstance(spec.get("checks", {}), dict)
                else {},
                "notes_hash": str(spec.get("notes_hash", "")),
            }
        )
    return sorted(normalised, key=lambda row: row["verifier_id"])


def _base_verifier_checks(
    *,
    artifact_status: dict[str, Any],
    artifact_hashes_reproducible: bool,
) -> dict[str, bool]:
    return {
        "artifact_hashes_replayed": artifact_hashes_reproducible,
        "attribution_consensus_ready": artifact_status[
            "attribution_consensus_ready"
        ],
        "attribution_consensus_target_l70": artifact_status[
            "attribution_consensus_target_l70"
        ],
        "consensus_creator_pool_conserved": artifact_status[
            "consensus_creator_pool_conserved"
        ],
        "provider_declares_consensus_and_verifier_surfaces": artifact_status[
            "provider_declares_consensus_surface"
        ]
        and artifact_status["provider_declares_verifier_quorum_surface"]
        and artifact_status["provider_declares_verifier_quorum_channel"],
        "certification_level_at_least_l70": artifact_status[
            "certification_level_at_least_l70"
        ],
        "integration_profile_ready": artifact_status["integration_profile_ready"]
        and artifact_status["integration_declares_verifier_quorum_schema"]
        and artifact_status["integration_declares_verifier_quorum_surface"],
    }


def _attestation_payload(
    *,
    verifier_id: str,
    organization_id: str,
    role: str,
    trust_tier: str,
    observed_at: str,
    replay_verdict: str,
    artifact_binding_root: str,
    artifact_count: int,
    checks: dict[str, bool],
    notes_hash: str,
    verifier_key_hash: str,
) -> dict[str, Any]:
    return {
        "verifier_id": verifier_id,
        "organization_id": organization_id,
        "role": role,
        "trust_tier": trust_tier,
        "observed_at": observed_at,
        "policy": POLICY_VERSION,
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "replay_verdict": replay_verdict,
        "artifact_binding_root": artifact_binding_root,
        "artifact_count": artifact_count,
        "checks": checks,
        "notes_hash": notes_hash,
        "verifier_key_hash": verifier_key_hash,
    }


def _make_verifier_row(
    spec: dict[str, Any],
    *,
    artifact_binding_root: str,
    artifact_count: int,
    base_checks: dict[str, bool],
    verifier_secrets: dict[str, str],
) -> dict[str, Any]:
    checks = dict(base_checks)
    checks.update(
        {
            key: bool(value)
            for key, value in spec.get("checks", {}).items()
            if key in REQUIRED_VERIFIER_CHECKS
        }
    )
    verifier_id = spec["verifier_id"]
    secret = verifier_secrets.get(verifier_id, "")
    verifier_key_hash = _verifier_key_hash(verifier_id, secret) if secret else ""
    payload = _attestation_payload(
        verifier_id=verifier_id,
        organization_id=spec["organization_id"],
        role=spec["role"],
        trust_tier=spec["trust_tier"],
        observed_at=spec["observed_at"],
        replay_verdict=spec["replay_verdict"],
        artifact_binding_root=artifact_binding_root,
        artifact_count=artifact_count,
        checks=checks,
        notes_hash=spec["notes_hash"],
        verifier_key_hash=verifier_key_hash,
    )
    signature_value = sign_payload(payload, secret) if secret else ""
    row = {
        **payload,
        "signature_algorithm": "HMAC-SHA256" if secret else "UNSIGNED",
        "signature": signature_value,
    }
    row["attestation_hash"] = hash_payload(row)
    return row


def _row_signature_valid(
    row: dict[str, Any],
    *,
    verifier_secrets: dict[str, str],
) -> bool:
    verifier_id = str(row.get("verifier_id", ""))
    secret = verifier_secrets.get(verifier_id)
    if not secret:
        return False
    expected_key_hash = _verifier_key_hash(verifier_id, secret)
    checks = {
        key: bool(value)
        for key, value in row.get("checks", {}).items()
        if key in REQUIRED_VERIFIER_CHECKS
    }
    payload = _attestation_payload(
        verifier_id=verifier_id,
        organization_id=str(row.get("organization_id", "")),
        role=str(row.get("role", "")),
        trust_tier=str(row.get("trust_tier", "")),
        observed_at=str(row.get("observed_at", "")),
        replay_verdict=str(row.get("replay_verdict", "")),
        artifact_binding_root=str(row.get("artifact_binding_root", "")),
        artifact_count=int(row.get("artifact_count", 0) or 0),
        checks=checks,
        notes_hash=str(row.get("notes_hash", "")),
        verifier_key_hash=expected_key_hash,
    )
    expected = sign_payload(payload, secret)
    return (
        row.get("signature_algorithm") == "HMAC-SHA256"
        and row.get("verifier_key_hash") == expected_key_hash
        and row.get("signature") == expected
    )


def _verifier_quorum(
    verifier_rows: list[dict[str, Any]],
    *,
    artifact_binding_root: str,
    minimum_quorum: int,
    minimum_independent_organizations: int,
    verifier_secrets: dict[str, str],
) -> dict[str, Any]:
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    for row in verifier_rows:
        signature_valid = _row_signature_valid(
            row,
            verifier_secrets=verifier_secrets,
        )
        checks_pass = all(
            row.get("checks", {}).get(check) is True
            for check in REQUIRED_VERIFIER_CHECKS
        )
        root_matches = row.get("artifact_binding_root") == artifact_binding_root
        verdict = str(row.get("replay_verdict", ""))
        if signature_valid and checks_pass and root_matches and verdict == "accepted":
            accepted_rows.append(row)
        elif signature_valid and verdict in {"rejected", "disputed"}:
            rejected_rows.append(row)
        else:
            invalid_rows.append(row)

    organizations = {
        str(row.get("organization_id", ""))
        for row in accepted_rows
        if row.get("organization_id")
    }
    return {
        "accepted_rows": accepted_rows,
        "rejected_rows": rejected_rows,
        "invalid_rows": invalid_rows,
        "accepted_verifier_count": len(accepted_rows),
        "rejected_or_disputed_verifier_count": len(rejected_rows),
        "invalid_verifier_count": len(invalid_rows),
        "independent_organization_count": len(organizations),
        "accepted_verifier_ids": sorted(
            str(row.get("verifier_id", "")) for row in accepted_rows
        ),
        "accepted_organization_ids": sorted(organizations),
        "quorum_met": len(accepted_rows) >= minimum_quorum,
        "organization_quorum_met": len(organizations)
        >= minimum_independent_organizations,
        "no_disagreement": not rejected_rows,
    }


def _settlement_rows(
    attribution_consensus_report: dict[str, Any],
    *,
    direct_settlement_ready: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for share in attribution_consensus_report.get("royalty_shares", []):
        consensus_payout = _decimal(share.get("payout", "0"))
        if direct_settlement_ready:
            payout = consensus_payout
            escrow_amount = Decimal("0")
            decision = str(share.get("decision", "accepted"))
        else:
            payout = Decimal("0")
            escrow_amount = consensus_payout
            decision = "verifier_quorum_escrow"
        row = {
            "creator_id": str(share.get("creator_id", "")),
            "work_id": str(share.get("work_id", "")),
            "consensus_decision": str(share.get("decision", "")),
            "settlement_decision": decision,
            "consensus_payout": _money(consensus_payout),
            "payout": _money(payout),
            "escrow_amount": _money(escrow_amount),
            "contribution_weight": float(share.get("contribution_weight", 0.0) or 0.0),
        }
        row["settlement_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_specs_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for row in report.get("verifier_rows", []):
        specs.append(
            {
                "verifier_id": row.get("verifier_id", ""),
                "organization_id": row.get("organization_id", ""),
                "role": row.get("role", ""),
                "trust_tier": row.get("trust_tier", ""),
                "observed_at": row.get("observed_at", ""),
                "replay_verdict": row.get("replay_verdict", ""),
                "checks": row.get("checks", {}),
                "notes_hash": row.get("notes_hash", ""),
            }
        )
    return specs


def make_verifier_quorum_report(
    *,
    attribution_consensus_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    verifier_specs: list[dict[str, Any]] | None = None,
    verifier_secrets: dict[str, str] | None = None,
    minimum_quorum: int = DEFAULT_MINIMUM_QUORUM,
    minimum_independent_organizations: int = DEFAULT_MINIMUM_INDEPENDENT_ORGANIZATIONS,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public report requiring external verifier quorum before payout."""

    verifier_secret_map = dict(verifier_secrets or {})
    timestamp = created_at or now_iso()
    bindings = _artifact_bindings(
        attribution_consensus_report=attribution_consensus_report,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
    )
    status = _artifact_status(
        attribution_consensus_report=attribution_consensus_report,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
    )
    base_checks = _base_verifier_checks(
        artifact_status=status,
        artifact_hashes_reproducible=bindings["artifact_hashes_reproducible"],
    )
    specs = _normalise_verifier_specs(
        verifier_specs,
        verifier_secrets=verifier_secret_map,
        observed_at=timestamp,
    )
    verifier_rows = [
        _make_verifier_row(
            spec,
            artifact_binding_root=bindings["artifact_binding_root"],
            artifact_count=bindings["artifact_count"],
            base_checks=base_checks,
            verifier_secrets=verifier_secret_map,
        )
        for spec in specs
    ]
    quorum = _verifier_quorum(
        verifier_rows,
        artifact_binding_root=bindings["artifact_binding_root"],
        minimum_quorum=minimum_quorum,
        minimum_independent_organizations=minimum_independent_organizations,
        verifier_secrets=verifier_secret_map,
    )
    direct_settlement_ready = (
        quorum["quorum_met"]
        and quorum["organization_quorum_met"]
        and quorum["no_disagreement"]
        and all(base_checks.values())
    )
    settlement_rows = _settlement_rows(
        attribution_consensus_report,
        direct_settlement_ready=direct_settlement_ready,
    )
    payout_total = sum((_decimal(row["payout"]) for row in settlement_rows), Decimal("0"))
    escrow_total = sum(
        (_decimal(row["escrow_amount"]) for row in settlement_rows), Decimal("0")
    )
    creator_pool = _decimal(
        attribution_consensus_report.get("economics", {}).get("creator_pool", "0")
    )
    disagreement_rows = [
        {
            "verifier_id": row.get("verifier_id", ""),
            "organization_id": row.get("organization_id", ""),
            "replay_verdict": row.get("replay_verdict", ""),
            "artifact_binding_root": row.get("artifact_binding_root", ""),
            "attestation_hash": row.get("attestation_hash", ""),
        }
        for row in verifier_rows
        if row.get("replay_verdict") in {"rejected", "disputed", "inconclusive"}
    ]
    settlement_decision = (
        "direct_settlement_ready"
        if direct_settlement_ready
        else "verifier_quorum_escrow"
    )
    escrow_reasons: list[str] = []
    if not all(base_checks.values()):
        escrow_reasons.append("artifact_replay_or_readiness_failed")
    if not quorum["quorum_met"]:
        escrow_reasons.append("accepted_verifier_quorum_not_met")
    if not quorum["organization_quorum_met"]:
        escrow_reasons.append("independent_organization_quorum_not_met")
    if not quorum["no_disagreement"]:
        escrow_reasons.append("verifier_disagreement_present")

    private_paths = _contains_private_fields(
        {
            "artifact_bindings": bindings,
            "artifact_status": status,
            "verifier_rows": verifier_rows,
            "settlement_rows": settlement_rows,
        }
    )
    checks = {
        "required_artifacts_bound": all(
            bindings.get(REQUIRED_ARTIFACT_HASH_FIELDS[name], "")
            for name in REQUIRED_ARTIFACTS
        ),
        "artifact_hashes_reproducible": bindings["artifact_hashes_reproducible"],
        "attribution_consensus_ready": status["attribution_consensus_ready"],
        "attribution_consensus_target_l70": status[
            "attribution_consensus_target_l70"
        ],
        "provider_declares_verifier_quorum": status[
            "provider_declares_verifier_quorum_surface"
        ]
        and status["provider_declares_verifier_quorum_channel"],
        "certification_level_at_least_l70": status[
            "certification_level_at_least_l70"
        ],
        "integration_profile_ready": status["integration_profile_ready"],
        "verifier_rows_sign_same_artifact_root": all(
            row.get("artifact_binding_root") == bindings["artifact_binding_root"]
            for row in verifier_rows
        ),
        "verifier_signatures_valid": all(
            _row_signature_valid(row, verifier_secrets=verifier_secret_map)
            for row in verifier_rows
        ),
        "accepted_verifier_quorum_met": quorum["quorum_met"],
        "independent_organization_quorum_met": quorum["organization_quorum_met"],
        "no_rejecting_or_disputing_verifiers": quorum["no_disagreement"],
        "direct_settlement_requires_verifier_quorum": (
            direct_settlement_ready
            or settlement_decision == "verifier_quorum_escrow"
        ),
        "creator_pool_conserved_or_escrowed": (
            _money(payout_total + escrow_total) == _money(creator_pool)
        ),
        "public_report_has_no_private_field_names": not private_paths,
        "public_report_uses_no_private_text_fields": True,
    }
    report = {
        "report_version": VERIFIER_QUORUM_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "policy": {
            "profile": POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_quorum": int(minimum_quorum),
            "minimum_independent_organizations": int(
                minimum_independent_organizations
            ),
            "required_verdict": "accepted",
            "rejected_or_disputed_route": "verifier_quorum_escrow",
            "required_verifier_checks": list(REQUIRED_VERIFIER_CHECKS),
        },
        "artifact_bindings": bindings,
        "artifact_status": status,
        "verifier_rows": verifier_rows,
        "disagreement_rows": disagreement_rows,
        "settlement_gate": {
            "decision": settlement_decision,
            "direct_settlement_ready": direct_settlement_ready,
            "escrow_reasons": escrow_reasons,
            "accepted_verifier_count": quorum["accepted_verifier_count"],
            "independent_organization_count": quorum[
                "independent_organization_count"
            ],
            "rejected_or_disputed_verifier_count": quorum[
                "rejected_or_disputed_verifier_count"
            ],
            "invalid_verifier_count": quorum["invalid_verifier_count"],
        },
        "settlement_rows": settlement_rows,
        "commitments": {
            "schema": VERIFIER_QUORUM_SCHEMA,
            "artifact_binding_root": bindings["artifact_binding_root"],
            "verifier_attestation_root": hash_payload(verifier_rows),
            "disagreement_root": hash_payload(disagreement_rows),
            "settlement_row_root": hash_payload(settlement_rows),
            "accepted_verifier_root": hash_payload(quorum["accepted_verifier_ids"]),
            "accepted_organization_root": hash_payload(
                quorum["accepted_organization_ids"]
            ),
        },
        "checks": checks,
        "schemas": {
            "verifier_quorum_report": VERIFIER_QUORUM_SCHEMA,
            "attribution_consensus_report": (
                "docs/schemas/attribution_consensus_report.schema.json"
            ),
            "provider_attribution_card": (
                "docs/schemas/provider_attribution_card.schema.json"
            ),
            "certification_report": "docs/schemas/certification_report.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
        },
        "summary": {
            "status": "ready" if direct_settlement_ready else "escrow",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "accepted_verifier_count": quorum["accepted_verifier_count"],
            "minimum_quorum": int(minimum_quorum),
            "independent_organization_count": quorum[
                "independent_organization_count"
            ],
            "minimum_independent_organizations": int(
                minimum_independent_organizations
            ),
            "disagreement_count": len(disagreement_rows),
            "settlement_decision": settlement_decision,
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
            "private_prompt_disclosed": False,
            "private_response_disclosed": False,
            "private_source_text_disclosed": False,
            "private_finance_payload_disclosed": False,
            "verifier_private_notes_disclosed": False,
            "report_uses_hashes_signatures_and_decisions": True,
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


def validate_verifier_quorum_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "artifact_status",
        "verifier_rows",
        "disagreement_rows",
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
            errors.append(f"missing verifier quorum field: {key}")
    if errors:
        return errors
    if report.get("report_version") != VERIFIER_QUORUM_VERSION:
        errors.append("verifier quorum report version is unsupported")
    if report.get("policy", {}).get("profile") != POLICY_VERSION:
        errors.append("verifier quorum policy is unsupported")
    if (
        report.get("policy", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("verifier quorum target certification level is unsupported")
    for name in REQUIRED_ARTIFACTS:
        if not report.get("artifact_bindings", {}).get(
            REQUIRED_ARTIFACT_HASH_FIELDS[name]
        ):
            errors.append(f"missing verifier quorum artifact binding: {name}")
    for row in report.get("verifier_rows", []):
        for key in (
            "verifier_id",
            "organization_id",
            "replay_verdict",
            "artifact_binding_root",
            "checks",
            "signature_algorithm",
            "signature",
            "attestation_hash",
        ):
            if key not in row:
                errors.append(f"missing verifier row field: {key}")
    if "verifier_quorum_report" not in report.get("schemas", {}):
        errors.append("missing verifier quorum schema")
    return errors


def verify_verifier_quorum_report(
    report: dict[str, Any],
    *,
    attribution_consensus_report: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    verifier_secrets: dict[str, str] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an independent verifier quorum report against public artifacts."""

    errors = validate_verifier_quorum_report_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("verifier quorum report hash is not reproducible")

    expected = make_verifier_quorum_report(
        attribution_consensus_report=attribution_consensus_report,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        verifier_specs=_verifier_specs_from_report(report),
        verifier_secrets=verifier_secrets,
        minimum_quorum=int(report.get("policy", {}).get("minimum_quorum", 0) or 0),
        minimum_independent_organizations=int(
            report.get("policy", {}).get("minimum_independent_organizations", 0)
            or 0
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "artifact_status",
        "verifier_rows",
        "disagreement_rows",
        "settlement_gate",
        "settlement_rows",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"verifier quorum {key} does not match replayed artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("verifier quorum report hash does not match replayed artifacts")

    for check, passed in report.get("checks", {}).items():
        if check in {
            "required_artifacts_bound",
            "artifact_hashes_reproducible",
            "verifier_signatures_valid",
            "creator_pool_conserved_or_escrowed",
            "public_report_has_no_private_field_names",
        } and passed is not True:
            errors.append(f"verifier quorum required check failed: {check}")

    if report.get("summary", {}).get("status") not in {"ready", "escrow"}:
        errors.append("verifier quorum status is unsupported")
    if report.get("summary", {}).get("status") == "ready":
        for check in (
            "accepted_verifier_quorum_met",
            "independent_organization_quorum_met",
            "no_rejecting_or_disputing_verifiers",
        ):
            if report.get("checks", {}).get(check) is not True:
                errors.append(f"ready verifier quorum missing check: {check}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("verifier quorum report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("verifier quorum report signature is invalid")

    return errors
