"""Pre-settlement ownership claim verification for RDLLM registries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.models import Work
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.registry import (
    DEFAULT_DUPLICATE_THRESHOLD,
    OwnershipAttestation,
    conflicts_by_work_id,
    registry_report_for_works,
)
from rdllm.text import stable_hash

CLAIM_VERIFICATION_VERSION = "rdllm-claim-verification-report/v1"
CLAIM_VERIFICATION_SCHEMA = "docs/schemas/claim_verification_report.schema.json"
CLAIM_VERIFICATION_POLICY_VERSION = "rdllm-claim-verification-policy/v1"
DEFAULT_DIRECT_SETTLEMENT_THRESHOLD = 0.75
DEFAULT_REVIEW_THRESHOLD = 0.40

HIGH_TRUST_CLAIM_TYPES = {
    "copyright_office",
    "collective_license",
    "digital_signature",
    "publisher_verified",
    "registry_verified",
}


def load_claim_verification_inputs(path: str | Path) -> dict[str, Any]:
    """Load ownership attestations, trusted issuers, and optional issuer keys."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "attestations": [
            OwnershipAttestation.from_dict(item)
            for item in data.get("attestations", [])
        ],
        "trusted_issuers": [str(item) for item in data.get("trusted_issuers", [])],
        "issuer_keys": {
            str(key): str(value) for key, value in data.get("issuer_keys", {}).items()
        },
    }


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _attestation_payload(attestation: OwnershipAttestation | dict[str, Any]) -> dict[str, Any]:
    data = (
        attestation.to_dict()
        if isinstance(attestation, OwnershipAttestation)
        else dict(attestation)
    )
    data.pop("signature", None)
    return data


def sign_ownership_attestation(
    attestation: dict[str, Any],
    issuer_key: str,
) -> str:
    """Create the deterministic HMAC signature used by claim verification tests."""

    return sign_payload(_attestation_payload(attestation), issuer_key)


def _signature_verified(
    attestation: OwnershipAttestation,
    issuer_keys: dict[str, str],
) -> bool:
    key = issuer_keys.get(attestation.issuer)
    if not key or not attestation.signature:
        return False
    return sign_payload(_attestation_payload(attestation), key) == attestation.signature


def _attestation_rows(
    attestations: list[OwnershipAttestation],
    *,
    trusted_issuers: set[str],
    issuer_keys: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attestation in sorted(attestations, key=lambda item: item.attestation_id):
        payload = _attestation_payload(attestation)
        signature_verified = _signature_verified(attestation, issuer_keys)
        row = {
            "attestation_id": attestation.attestation_id,
            "work_id": attestation.work_id,
            "creator_id": attestation.creator_id,
            "claim_type": attestation.claim_type,
            "issuer": attestation.issuer,
            "issued_at": attestation.issued_at,
            "status": attestation.status,
            "trusted_issuer": attestation.issuer in trusted_issuers,
            "evidence_uri_present": bool(attestation.evidence_uri),
            "evidence_hash": attestation.evidence_hash,
            "signature_hash": stable_hash(attestation.signature) if attestation.signature else "",
            "signature_verified": signature_verified,
            "attestation_hash": hash_payload(payload),
        }
        row["row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _best_claim_score(rows: list[dict[str, Any]]) -> float:
    best = 0.0
    for row in rows:
        if row.get("status") != "active":
            continue
        score = 0.0
        if row.get("evidence_uri_present") and row.get("evidence_hash"):
            score += 0.20
        if row.get("trusted_issuer"):
            score += 0.20
        if row.get("signature_verified"):
            score += 0.35
        claim_type = str(row.get("claim_type", ""))
        if claim_type in HIGH_TRUST_CLAIM_TYPES:
            score += 0.20
        elif claim_type == "self_asserted":
            score += 0.05
        if row.get("status") == "active":
            score += 0.05
        best = max(best, min(1.0, score))
    return round(best, 8)


def _work_rows(
    works: list[Work],
    attestation_rows: list[dict[str, Any]],
    registry_report: dict[str, Any],
    *,
    direct_settlement_threshold: float,
    review_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_work: dict[str, list[dict[str, Any]]] = {}
    for row in attestation_rows:
        by_work.setdefault(str(row["work_id"]), []).append(row)
    conflicts = conflicts_by_work_id(registry_report)

    claim_rows: list[dict[str, Any]] = []
    escrow_rows: list[dict[str, Any]] = []
    for work in sorted(works, key=lambda item: item.work_id):
        rows = [
            row for row in by_work.get(work.work_id, []) if row.get("creator_id") == work.creator_id
        ]
        confidence = _best_claim_score(rows)
        conflict_rows = conflicts.get(work.work_id, [])
        has_duplicate_conflict = bool(conflict_rows)
        verified_attestations = [
            row for row in rows if row.get("signature_verified") and row.get("trusted_issuer")
        ]
        if has_duplicate_conflict:
            decision = "duplicate_claim_escrow"
            release_recommendation = "hold_for_registry_resolution"
            reason = "duplicate or near-duplicate ownership conflict is still open"
        elif confidence >= direct_settlement_threshold and verified_attestations:
            decision = "direct_settlement_allowed"
            release_recommendation = "allow_settlement"
            reason = "trusted active ownership attestation verifies above threshold"
        elif confidence >= review_threshold:
            decision = "claim_review_escrow"
            release_recommendation = "hold_for_claim_review"
            reason = "claim has evidence but does not meet direct-settlement threshold"
        else:
            decision = "unverified_claim_escrow"
            release_recommendation = "hold_for_claim_review"
            reason = "no trusted verifiable ownership attestation"

        row = {
            "work_id": work.work_id,
            "creator_id": work.creator_id,
            "title_hash": stable_hash(work.title),
            "content_hash": stable_hash(work.content),
            "source_uri_hash": stable_hash(work.source_uri) if work.source_uri else "",
            "attestation_ids": sorted(str(item["attestation_id"]) for item in rows),
            "trusted_attestation_count": len(
                [item for item in rows if item.get("trusted_issuer")]
            ),
            "verified_signature_count": len(verified_attestations),
            "evidence_hash_count": len([item for item in rows if item.get("evidence_hash")]),
            "duplicate_conflict_count": len(conflict_rows),
            "confidence_score": confidence,
            "decision": decision,
            "release_recommendation": release_recommendation,
            "reason": reason,
        }
        row["row_hash"] = hash_payload(row)
        claim_rows.append(row)

        if decision != "direct_settlement_allowed":
            escrow = {
                "work_id": work.work_id,
                "creator_id": work.creator_id,
                "escrow_account": (
                    "registry_duplicate_claim_escrow"
                    if decision == "duplicate_claim_escrow"
                    else "ownership_claim_review_escrow"
                ),
                "decision": decision,
                "release_recommendation": release_recommendation,
                "reason": reason,
                "confidence_score": confidence,
            }
            escrow["escrow_hash"] = hash_payload(escrow)
            escrow_rows.append(escrow)
    return claim_rows, escrow_rows


def make_claim_verification_report(
    works: list[Work] | dict[str, Work],
    attestations: list[OwnershipAttestation],
    *,
    trusted_issuers: list[str] | tuple[str, ...] = (),
    issuer_keys: dict[str, str] | None = None,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    direct_settlement_threshold: float = DEFAULT_DIRECT_SETTLEMENT_THRESHOLD,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public, privacy-safe pre-settlement ownership verification report."""

    work_list = sorted(
        list(works.values()) if isinstance(works, dict) else list(works),
        key=lambda item: item.work_id,
    )
    attestation_list = sorted(attestations, key=lambda item: item.attestation_id)
    trusted = set(str(item) for item in trusted_issuers)
    key_map = dict(issuer_keys or {})
    registry_report = registry_report_for_works(
        work_list,
        attestations=attestation_list,
        duplicate_threshold=duplicate_threshold,
    )
    attestation_rows = _attestation_rows(
        attestation_list,
        trusted_issuers=trusted,
        issuer_keys=key_map,
    )
    claim_rows, escrow_rows = _work_rows(
        work_list,
        attestation_rows,
        registry_report,
        direct_settlement_threshold=direct_settlement_threshold,
        review_threshold=review_threshold,
    )
    direct_count = len(
        [row for row in claim_rows if row["decision"] == "direct_settlement_allowed"]
    )
    review_count = len(claim_rows) - direct_count
    report = {
        "report_version": CLAIM_VERIFICATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": CLAIM_VERIFICATION_POLICY_VERSION,
            "trusted_issuers": sorted(trusted),
            "trusted_issuer_root": hash_payload(sorted(trusted)),
            "issuer_key_root": hash_payload(sorted(key_map)),
            "duplicate_threshold": round(float(duplicate_threshold), 8),
            "direct_settlement_threshold": round(float(direct_settlement_threshold), 8),
            "review_threshold": round(float(review_threshold), 8),
            "direct_settlement_requires_verified_signature": True,
            "duplicate_claims_route_to_escrow": True,
            "unverified_claims_route_to_escrow": True,
        },
        "registry": {
            "registry_report_version": registry_report.get("registry_report_version", ""),
            "report_hash": registry_report.get("report_hash", ""),
            "summary": registry_report.get("summary", {}),
            "conflicts": registry_report.get("conflicts", []),
        },
        "attestation_rows": attestation_rows,
        "claim_rows": claim_rows,
        "escrow_rows": escrow_rows,
        "commitments": {
            "work_root": hash_payload(
                [
                    {
                        "work_id": work.work_id,
                        "creator_id": work.creator_id,
                        "title_hash": stable_hash(work.title),
                        "content_hash": stable_hash(work.content),
                    }
                    for work in work_list
                ]
            ),
            "attestation_root": hash_payload(attestation_rows),
            "claim_root": hash_payload(claim_rows),
            "escrow_root": hash_payload(escrow_rows),
            "conflict_root": hash_payload(registry_report.get("conflicts", [])),
        },
        "summary": {
            "status": "ready",
            "target_certification_level": "RDLLM-L54",
            "work_count": len(work_list),
            "attestation_count": len(attestation_rows),
            "trusted_issuer_count": len(trusted),
            "verified_attestation_count": len(
                [row for row in attestation_rows if row["signature_verified"]]
            ),
            "direct_settlement_work_count": direct_count,
            "review_or_escrow_work_count": review_count,
            "duplicate_conflict_count": registry_report.get("summary", {}).get(
                "open_conflict_count", 0
            ),
            "escrow_row_count": len(escrow_rows),
            "all_direct_rows_have_verified_attestations": all(
                row["verified_signature_count"] > 0
                for row in claim_rows
                if row["decision"] == "direct_settlement_allowed"
            ),
            "unverified_claims_route_to_escrow": all(
                row["decision"] != "direct_settlement_allowed"
                for row in claim_rows
                if row["verified_signature_count"] == 0
                or row["confidence_score"] < direct_settlement_threshold
            ),
            "duplicate_claims_route_to_escrow": all(
                row["decision"] == "duplicate_claim_escrow"
                for row in claim_rows
                if row["duplicate_conflict_count"] > 0
            ),
        },
        "privacy": {
            "work_text_disclosed": False,
            "payout_accounts_disclosed": False,
            "raw_issuer_keys_disclosed": False,
            "raw_attestation_signatures_disclosed": False,
            "report_uses_hashes_claim_metadata_and_escrow_decisions": True,
        },
        "schemas": {
            "claim_verification_report": CLAIM_VERIFICATION_SCHEMA,
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


def validate_claim_verification_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "registry",
        "attestation_rows",
        "claim_rows",
        "escrow_rows",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing claim verification field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CLAIM_VERIFICATION_VERSION:
        errors.append("claim verification report version is unsupported")
    if report.get("policy", {}).get("profile") != CLAIM_VERIFICATION_POLICY_VERSION:
        errors.append("claim verification policy profile is unsupported")
    for row in report.get("claim_rows", []):
        for key in (
            "work_id",
            "creator_id",
            "content_hash",
            "attestation_ids",
            "verified_signature_count",
            "duplicate_conflict_count",
            "confidence_score",
            "decision",
            "release_recommendation",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing claim verification row field: {key}")
    return errors


def verify_claim_verification_report(
    report: dict[str, Any],
    works: list[Work] | dict[str, Work],
    attestations: list[OwnershipAttestation],
    *,
    trusted_issuers: list[str] | tuple[str, ...] = (),
    issuer_keys: dict[str, str] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify an ownership claim verification report."""

    errors = validate_claim_verification_report_shape(report)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("claim verification report hash is not reproducible")
    policy = report.get("policy", {})
    expected = make_claim_verification_report(
        works,
        attestations,
        trusted_issuers=trusted_issuers,
        issuer_keys=issuer_keys,
        duplicate_threshold=float(
            policy.get("duplicate_threshold", DEFAULT_DUPLICATE_THRESHOLD)
        ),
        direct_settlement_threshold=float(
            policy.get(
                "direct_settlement_threshold",
                DEFAULT_DIRECT_SETTLEMENT_THRESHOLD,
            )
        ),
        review_threshold=float(policy.get("review_threshold", DEFAULT_REVIEW_THRESHOLD)),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "registry",
        "attestation_rows",
        "claim_rows",
        "escrow_rows",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"claim verification {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("claim verification report hash does not match replay")

    for row in report.get("claim_rows", []):
        row_copy = dict(row)
        declared = row_copy.pop("row_hash", "")
        if hash_payload(row_copy) != declared:
            errors.append(
                f"claim verification row hash is not reproducible: {row.get('work_id', '')}"
            )
        if (
            row.get("decision") == "direct_settlement_allowed"
            and int(row.get("verified_signature_count", 0)) <= 0
        ):
            errors.append("direct settlement row lacks a verified ownership attestation")
        if (
            int(row.get("duplicate_conflict_count", 0)) > 0
            and row.get("decision") == "direct_settlement_allowed"
        ):
            errors.append("duplicate ownership conflict was allowed for direct settlement")

    for work in (works.values() if isinstance(works, dict) else works):
        if work.content and work.content in canonical_json(report):
            errors.append("claim verification report discloses work text")
            break
    if any("payout_account" in canonical_json(row) for row in report.get("claim_rows", [])):
        errors.append("claim verification report discloses payout accounts")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("claim verification report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("claim verification report signature is invalid")
    return errors
