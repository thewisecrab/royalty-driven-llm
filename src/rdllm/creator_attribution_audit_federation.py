"""Cross-provider creator attribution audit federation.

L110 proves a creator query inside one provider boundary. This layer federates
multiple L110 indexes so a creator, auditor, marketplace, or regulator can verify
the same creator/work/hash query across providers without treating any one
provider's source-label namespace as global truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.creator_attribution_audit_index import (
    validate_creator_attribution_audit_index_shape,
    verify_creator_attribution_audit_index,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

CREATOR_ATTRIBUTION_AUDIT_FEDERATION_VERSION = (
    "rdllm-creator-attribution-audit-federation/v1"
)
CREATOR_ATTRIBUTION_AUDIT_FEDERATION_SCHEMA = (
    "docs/schemas/creator_attribution_audit_federation.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L111"
MINIMUM_CERTIFICATION_LEVEL = "RDLLM-L110"

DECLARED_HASH_FIELDS = (
    "creator_attribution_audit_federation_hash",
    "creator_attribution_audit_index_hash",
    "attribution_bom_hash",
    "handshake_hash",
    "exchange_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "report_hash",
    "receipt_hash",
    "contract_hash",
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
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "notice_text",
    "license_text",
    "feedback_text",
    "critique_text",
    "reward_explanation_text",
    "verifier_rationale",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
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
    "participant_signing_secret",
}


def load_creator_attribution_audit_federation_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a creator audit federation report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _level_number(level: str) -> int:
    try:
        return int(str(level).rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_federation(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"creator_attribution_audit_federation_hash", "signature"}
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
        return True
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


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


def _private_strings_absent(report: dict[str, Any], federation_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in federation_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _provider_id(participant: dict[str, Any]) -> str:
    provider_card = participant.get("provider_attribution_card", {})
    return str(
        participant.get("provider_id")
        or provider_card.get("provider", {}).get("id")
        or participant.get("creator_attribution_audit_index", {}).get("issuer", "")
    )


def _query_commitment(index: dict[str, Any]) -> dict[str, Any]:
    return dict(index.get("case", {}).get("query_commitment", {}))


def _participant_errors(participant: dict[str, Any]) -> list[str]:
    index = participant.get("creator_attribution_audit_index", {})
    errors = validate_creator_attribution_audit_index_shape(index)
    audit_input = participant.get("audit_input")
    if isinstance(audit_input, dict):
        errors.extend(
            verify_creator_attribution_audit_index(
                index,
                audit_input,
                signing_secret=participant.get("participant_signing_secret"),
            )
        )
    if index.get("summary", {}).get("status") != "ready":
        errors.append("participant creator audit index is not ready")
    if index.get("summary", {}).get("target_certification_level") != "RDLLM-L110":
        errors.append("participant creator audit index target level is not RDLLM-L110")
    return sorted(set(errors))


def _participant_rows(federation_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sequence, participant in enumerate(federation_input.get("participants", []), start=1):
        index = participant.get("creator_attribution_audit_index", {})
        provider_card = participant.get("provider_attribution_card", {})
        discovery_manifest = participant.get("discovery_manifest", {})
        handshake = participant.get("federation_handshake", {})
        exchange = participant.get("attribution_exchange", {})
        provider_id = _provider_id(participant)
        public_surfaces = provider_card.get("public_disclosure_surfaces", {})
        evidence_channels = provider_card.get("supported_evidence_channels", {})
        row = {
            "sequence": sequence,
            "provider_id": provider_id,
            "provider_model_id": str(provider_card.get("provider", {}).get("model_id", "")),
            "provider_card_hash": _declared_hash(provider_card),
            "creator_attribution_audit_index_hash": _declared_hash(index),
            "index_hash_reproducible": _artifact_hash_is_reproducible(index),
            "index_ready": index.get("summary", {}).get("status") == "ready",
            "index_target_level": str(index.get("summary", {}).get("target_certification_level", "")),
            "query_hash": str(_query_commitment(index).get("query_hash", "")),
            "creator_work_count": int(index.get("summary", {}).get("creator_work_count", 0) or 0),
            "surface_row_count": int(index.get("summary", {}).get("surface_row_count", 0) or 0),
            "provider_declares_creator_audit_index": public_surfaces.get("creator_attribution_audit_index") is True
            and evidence_channels.get("creator_attribution_audit_index") is True,
            "discovery_creator_audit_index_path": str(
                discovery_manifest.get("discovery", {}).get(
                    "creator_attribution_audit_index_path", ""
                )
            ),
            "federation_handshake_hash": _declared_hash(handshake),
            "attribution_exchange_hash": _declared_hash(exchange),
            "participant_error_count": len(_participant_errors(participant)),
        }
        row["participant_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _federated_surface_rows(federation_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for participant in federation_input.get("participants", []):
        provider_id = _provider_id(participant)
        index = participant.get("creator_attribution_audit_index", {})
        index_hash = _declared_hash(index)
        for surface in index.get("surface_rows", []):
            row = {
                "provider_id": provider_id,
                "participant_index_hash": index_hash,
                "surface": str(surface.get("surface", "")),
                "artifact_name": str(surface.get("artifact_name", "")),
                "artifact_hash": str(surface.get("artifact_hash", "")),
                "source_label": str(surface.get("source_label", "")),
                "source_label_namespace": str(surface.get("source_label_namespace", "")),
                "provider_source_label_namespace": f"{provider_id}:{surface.get('source_label_namespace', '')}",
                "creator_id": str(surface.get("creator_id", "")),
                "work_id": str(surface.get("work_id", "")),
                "chunk_id": str(surface.get("chunk_id", "")),
                "content_hash_prefix": str(surface.get("content_hash_prefix", "")),
                "settlement_state": str(surface.get("settlement_state", "")),
                "surface_row_hash": str(surface.get("surface_row_hash", "")),
            }
            row["federated_surface_row_hash"] = hash_payload(row)
            rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            row["provider_id"],
            row["work_id"],
            row["surface"],
            row["surface_row_hash"],
        ),
    )


def _federated_creator_work_rows(surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    creator_by_work = {
        row.get("work_id", ""): row.get("creator_id", "")
        for row in surface_rows
        if row.get("work_id") and row.get("creator_id")
    }
    for row in surface_rows:
        work_id = str(row.get("work_id", ""))
        creator_id = str(row.get("creator_id", "")) or str(creator_by_work.get(work_id, ""))
        key = (creator_id, work_id, str(row.get("chunk_id", "")))
        grouped.setdefault(key, []).append(row)
    result: list[dict[str, Any]] = []
    for (creator_id, work_id, chunk_id), rows in sorted(grouped.items()):
        provider_ids = sorted({row["provider_id"] for row in rows if row.get("provider_id")})
        surfaces = sorted({row["surface"] for row in rows if row.get("surface")})
        row = {
            "creator_id": creator_id,
            "work_id": work_id,
            "chunk_id": chunk_id,
            "provider_ids": provider_ids,
            "provider_count": len(provider_ids),
            "surface_count": len(surfaces),
            "surfaces": surfaces,
            "provider_index_hashes": sorted(
                {row["participant_index_hash"] for row in rows if row.get("participant_index_hash")}
            ),
            "provider_surface_root": hash_payload(
                sorted(row["federated_surface_row_hash"] for row in rows)
            ),
        }
        row["federated_creator_work_row_hash"] = hash_payload(row)
        result.append(row)
    return result


def _identity_conflict_rows(surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    creators_by_work: dict[str, set[str]] = {}
    for row in surface_rows:
        work_id = str(row.get("work_id", ""))
        creator_id = str(row.get("creator_id", ""))
        if work_id and creator_id:
            creators_by_work.setdefault(work_id, set()).add(creator_id)
    conflicts: list[dict[str, Any]] = []
    for work_id, creator_ids in sorted(creators_by_work.items()):
        if len(creator_ids) > 1:
            row = {
                "work_id": work_id,
                "creator_id_hashes": [hash_payload(item) for item in sorted(creator_ids)],
                "conflict_type": "cross_provider_creator_identity_mismatch",
                "requires_review": True,
            }
            row["conflict_row_hash"] = hash_payload(row)
            conflicts.append(row)
    return conflicts


def _query_federation(participant_rows: list[dict[str, Any]]) -> dict[str, Any]:
    hashes = sorted({row.get("query_hash", "") for row in participant_rows if row.get("query_hash")})
    return {
        "query_hashes": hashes,
        "agreed_query_hash": hashes[0] if len(hashes) == 1 else "",
        "query_hash_count": len(hashes),
        "query_terms_disclosed": False,
    }


def _base_checks(
    *,
    federation_input: dict[str, Any],
    participant_rows: list[dict[str, Any]],
    surface_rows: list[dict[str, Any]],
    creator_work_rows: list[dict[str, Any]],
    conflict_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    policy = federation_input.get("policy", {})
    minimum_participants = int(policy.get("minimum_participants", 2) or 2)
    provider_ids = [row.get("provider_id", "") for row in participant_rows]
    query_hashes = {row.get("query_hash", "") for row in participant_rows if row.get("query_hash")}
    federated_surface_hashes = [
        row.get("federated_surface_row_hash", "") for row in surface_rows
    ]

    return {
        "minimum_two_participants_present": len(participant_rows) >= minimum_participants,
        "participant_provider_ids_unique": len(provider_ids) == len(set(provider_ids))
        and all(provider_ids),
        "all_participant_indexes_ready_l110": bool(participant_rows)
        and all(row.get("index_ready") is True and row.get("index_target_level") == "RDLLM-L110" for row in participant_rows)
        and all(row.get("participant_error_count", 1) == 0 for row in participant_rows),
        "participant_query_hashes_match": len(query_hashes) == 1,
        "all_participant_indexes_hash_reproducible": bool(participant_rows)
        and all(row.get("index_hash_reproducible") is True for row in participant_rows),
        "participant_provider_cards_declare_creator_audit": bool(participant_rows)
        and all(row.get("provider_declares_creator_audit_index") is True for row in participant_rows),
        "participant_discovery_paths_present": bool(participant_rows)
        and all(row.get("discovery_creator_audit_index_path") for row in participant_rows),
        "federation_artifacts_bound_when_present": all(
            row.get("federation_handshake_hash") or row.get("attribution_exchange_hash")
            for row in participant_rows
        ),
        "source_label_namespaces_are_provider_scoped": bool(surface_rows)
        and all(row.get("provider_source_label_namespace") for row in surface_rows),
        "duplicate_surface_rows_not_double_counted": len(federated_surface_hashes)
        == len(set(federated_surface_hashes)),
        "creator_work_rows_merge_multiple_providers": bool(creator_work_rows)
        and any(row.get("provider_count", 0) >= 2 for row in creator_work_rows),
        "no_unresolved_creator_identity_conflicts": not conflict_rows,
        "notices_and_private_text_not_disclosed": not _contains_private_fields(
            federation_input.get("public_overrides", {})
        ),
    }


def make_creator_attribution_audit_federation(
    federation_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed cross-provider creator attribution audit federation."""

    issued_at = issued_at or now_iso()
    participant_rows = _participant_rows(federation_input)
    surface_rows = _federated_surface_rows(federation_input)
    creator_work_rows = _federated_creator_work_rows(surface_rows)
    conflict_rows = _identity_conflict_rows(surface_rows)
    checks = _base_checks(
        federation_input=federation_input,
        participant_rows=participant_rows,
        surface_rows=surface_rows,
        creator_work_rows=creator_work_rows,
        conflict_rows=conflict_rows,
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    report: dict[str, Any] = {
        "version": CREATOR_ATTRIBUTION_AUDIT_FEDERATION_VERSION,
        "issued_at": issued_at,
        "issuer": issuer,
        "case": {
            "case_id": str(
                federation_input.get("case_id", "case:creator-attribution-audit-federation")
            ),
            "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
            "query_federation": _query_federation(participant_rows),
        },
        "participant_rows": participant_rows,
        "federated_surface_rows": surface_rows,
        "federated_creator_work_rows": creator_work_rows,
        "identity_conflict_rows": conflict_rows,
        "commitments": {
            "participant_root": hash_payload(
                [row["participant_row_hash"] for row in participant_rows]
            ),
            "federated_surface_root": hash_payload(
                [row["federated_surface_row_hash"] for row in surface_rows]
            ),
            "federated_creator_work_root": hash_payload(
                [row["federated_creator_work_row_hash"] for row in creator_work_rows]
            ),
            "identity_conflict_root": hash_payload(
                [row["conflict_row_hash"] for row in conflict_rows]
            ),
        },
        "checks": checks,
        "privacy": {
            "query_terms_disclosed": False,
            "raw_prompt_disclosed": False,
            "raw_answer_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_feedback_text_disclosed": False,
            "raw_notice_text_disclosed": False,
            "raw_license_text_disclosed": False,
            "raw_payment_data_disclosed": False,
            "federation_uses_provider_scoped_hashes_and_statuses": True,
        },
        "schemas": {
            "creator_attribution_audit_federation": CREATOR_ATTRIBUTION_AUDIT_FEDERATION_SCHEMA,
            "creator_attribution_audit_index": "docs/schemas/creator_attribution_audit_index.schema.json",
            "federation_handshake": "docs/schemas/federation_handshake.schema.json",
            "attribution_exchange": "docs/schemas/attribution_exchange.schema.json",
        },
        "summary": {
            "status": "ready" if failed_check_count == 0 else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
            "participant_count": len(participant_rows),
            "provider_count": len({row.get("provider_id", "") for row in participant_rows}),
            "federated_surface_row_count": len(surface_rows),
            "federated_creator_work_count": len(creator_work_rows),
            "identity_conflict_count": len(conflict_rows),
            "failed_check_count": failed_check_count,
            "creator_audit_federation_ready": failed_check_count == 0,
            "privacy_preserved": checks["notices_and_private_text_not_disclosed"],
        },
    }
    checks["notices_and_private_text_not_disclosed"] = (
        checks["notices_and_private_text_not_disclosed"]
        and _private_strings_absent(report, federation_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    report["summary"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    report["summary"]["failed_check_count"] = failed_check_count
    report["summary"]["creator_audit_federation_ready"] = failed_check_count == 0
    report["summary"]["privacy_preserved"] = checks["notices_and_private_text_not_disclosed"]
    report["creator_attribution_audit_federation_hash"] = hash_payload(
        _hashable_federation(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_federation(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_creator_attribution_audit_federation_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of a creator attribution audit federation."""

    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "participant_rows",
        "federated_surface_rows",
        "federated_creator_work_rows",
        "identity_conflict_rows",
        "commitments",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "creator_attribution_audit_federation_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing creator audit federation field: {key}")
    if errors:
        return errors
    if report.get("version") != CREATOR_ATTRIBUTION_AUDIT_FEDERATION_VERSION:
        errors.append("creator audit federation version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("creator audit federation target level is not RDLLM-L111")
    if "creator_attribution_audit_federation" not in report.get("schemas", {}):
        errors.append("missing creator audit federation schema")
    if not isinstance(report.get("participant_rows"), list):
        errors.append("creator audit federation participant_rows must be a list")
    if _contains_private_fields(report):
        errors.append("creator audit federation contains private field")
    return errors


def verify_creator_attribution_audit_federation(
    report: dict[str, Any],
    federation_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a creator audit federation against replay inputs."""

    errors = validate_creator_attribution_audit_federation_shape(report)
    expected = make_creator_attribution_audit_federation(
        federation_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(report.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "version",
        "case",
        "participant_rows",
        "federated_surface_rows",
        "federated_creator_work_rows",
        "identity_conflict_rows",
        "commitments",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if report.get(key) != expected.get(key):
            errors.append(f"creator audit federation {key} mismatch")
    if report.get("creator_attribution_audit_federation_hash") != expected.get(
        "creator_attribution_audit_federation_hash"
    ):
        errors.append("creator audit federation hash mismatch")
    if report.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("creator audit federation signature mismatch")
    if any(value is not True for value in report.get("checks", {}).values()):
        errors.append("creator audit federation has failing checks")
    return errors
