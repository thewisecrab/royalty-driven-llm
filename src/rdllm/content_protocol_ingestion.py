"""External content-protocol ingestion for RDLLM rights and royalty proof.

This layer binds web-scale licensing signals such as RSL, CoMP, SCP, ODRL,
Croissant, robots.txt, and C2PA/TDM reservations to RDLLM creator contracts and
source-access leases.  It prevents a provider from claiming direct settlement
when the external publisher protocol was missing, denied the use, or was not
preserved into the internal RDLLM proof chain.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

CONTENT_PROTOCOL_INGESTION_VERSION = "rdllm-content-protocol-ingestion/v1"
CONTENT_PROTOCOL_INGESTION_SCHEMA = (
    "docs/schemas/content_protocol_ingestion_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L99"

SUPPORTED_PROTOCOLS = {
    "rsl",
    "comp",
    "scp",
    "odrl",
    "croissant",
    "c2pa_tdm",
    "robots_txt",
    "custom",
}

DECLARED_HASH_FIELDS = (
    "protocol_ingestion_report_hash",
    "lease_report_hash",
    "binding_report_hash",
    "report_hash",
    "contract_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
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
    "raw_notice_text",
    "raw_protocol_payload",
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
}

ESCROW_STATUSES = {
    "escrow",
    "held",
    "rights_conflict_escrow",
    "source_access_lease_escrow",
    "content_protocol_escrow",
    "license_escrow",
}
DIRECT_STATUSES = {"direct", "accepted", "payable", "paid", "settled"}
DENY_PAYMENT_TYPES = {"deny", "denied", "blocked", "forbidden", "none"}
NON_ROYALTY_PAYMENT_TYPES = {"free", "attribution", "cc-by"}

USE_ALIASES = {
    "retrieval": {
        "retrieval",
        "search",
        "crawl",
        "ai-search",
        "ai_search",
        "all",
        "ai-use",
        "ai_use",
    },
    "retrieval_inference": {
        "retrieval_inference",
        "retrieval",
        "inference",
        "generation",
        "ai-inference",
        "ai_inference",
        "all",
        "ai-use",
        "ai_use",
    },
    "inference": {
        "inference",
        "generation",
        "ai-inference",
        "ai_inference",
        "all",
        "ai-use",
        "ai_use",
    },
    "generation": {
        "generation",
        "inference",
        "ai-inference",
        "ai_inference",
        "all",
        "ai-use",
        "ai_use",
    },
    "training": {"training", "ai-train", "ai_train", "all", "ai-use", "ai_use"},
}


def load_content_protocol_ingestion_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a content-protocol ingestion report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"protocol_ingestion_report_hash", "signature"}
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


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "protocol_record_hash",
            "coverage_row_hash",
            "declared_record_hash",
            "record_hash_matches_declared",
        }
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


def _private_strings_absent(report: dict[str, Any], protocol_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in protocol_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _policy(protocol_input: dict[str, Any]) -> dict[str, Any]:
    configured = dict(protocol_input.get("policy", {}))
    return {
        "require_protocol_record_for_direct_sources": bool(
            configured.get("require_protocol_record_for_direct_sources", True)
        ),
        "require_supported_external_protocol": bool(
            configured.get("require_supported_external_protocol", True)
        ),
        "require_protocol_terms_allow_use": bool(
            configured.get("require_protocol_terms_allow_use", True)
        ),
        "require_creator_contract_matches_protocol": bool(
            configured.get("require_creator_contract_matches_protocol", True)
        ),
        "require_source_lease_matches_protocol": bool(
            configured.get("require_source_lease_matches_protocol", True)
        ),
        "require_protocol_hash_replay": bool(
            configured.get("require_protocol_hash_replay", True)
        ),
        "require_denied_or_missing_protocol_escrowed": bool(
            configured.get("require_denied_or_missing_protocol_escrowed", True)
        ),
    }


def _protocol_name(value: Any) -> str:
    normalized = str(value or "custom").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "really_simple_licensing": "rsl",
        "rsl_1.0": "rsl",
        "iab_comp": "comp",
        "content_monetization_protocol": "comp",
        "sovereign_context_protocol": "scp",
        "c2pa_tdm_reservation": "c2pa_tdm",
        "robots": "robots_txt",
        "robots.txt": "robots_txt",
    }
    return aliases.get(normalized, normalized)


def _uses(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        items = [value]
    else:
        items = list(value)
    return {str(item).strip().lower().replace("-", "_") for item in items if str(item)}


def _purpose_aliases(purpose: str) -> set[str]:
    normalized = str(purpose or "retrieval_inference").strip().lower().replace("-", "_")
    return USE_ALIASES.get(normalized, {normalized, "all", "ai-use", "ai_use"})


def _use_allowed(allowed: set[str], prohibited: set[str], purpose: str) -> bool:
    aliases = _purpose_aliases(purpose)
    denied = prohibited & aliases or "all" in prohibited
    permitted = bool(allowed & aliases or "all" in allowed)
    return permitted and not denied


def _is_escrow(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    route = str(row.get("escrow_account", row.get("settlement_route", "")))
    return status in ESCROW_STATUSES or route.endswith("escrow") or "escrow" in route


def _is_direct(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    return bool(row.get("direct_settlement", False)) or (
        status in DIRECT_STATUSES and not _is_escrow(row)
    )


def _protocol_rows(protocol_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(protocol_input.get("protocol_records", []), start=1):
        raw_notice = str(row.get("raw_notice_text", row.get("raw_protocol_payload", "")))
        protocol = _protocol_name(row.get("protocol"))
        payment_type = str(row.get("payment_type", "attribution")).strip().lower()
        public = {
            "protocol_record_id": str(
                row.get("protocol_record_id") or row.get("record_id") or f"protocol:{index}"
            ),
            "protocol": protocol,
            "protocol_version": str(row.get("protocol_version", "")),
            "protocol_supported": protocol in SUPPORTED_PROTOCOLS,
            "record_uri": str(
                row.get("record_uri") or row.get("fetched_from") or row.get("source_uri", "")
            ),
            "source_uri": str(row.get("source_uri", "")),
            "work_id": str(row.get("work_id", "")),
            "content_hash": str(row.get("content_hash", "")),
            "discovered_at": str(row.get("discovered_at", "")),
            "fetched_from": str(row.get("fetched_from", "")),
            "license_server": str(row.get("license_server", "")),
            "license_url": str(row.get("license_url", row.get("standard", ""))),
            "allowed_uses": sorted(_uses(row.get("allowed_uses", []))),
            "prohibited_uses": sorted(_uses(row.get("prohibited_uses", []))),
            "payment_type": payment_type,
            "minimum_creator_pool_rate": str(row.get("minimum_creator_pool_rate", "0")),
            "attribution_required": bool(row.get("attribution_required", True)),
            "royalty_required": bool(
                row.get("royalty_required", payment_type not in NON_ROYALTY_PAYMENT_TYPES)
            ),
            "access_token_hash": str(row.get("access_token_hash", "")),
            "notice_hash": str(row.get("notice_hash") or hash_payload(raw_notice or row)),
            "raw_notice_disclosed": False,
        }
        public["declared_record_hash"] = str(row.get("record_hash", ""))
        public["protocol_record_hash"] = hash_payload(_hashable_row(public))
        public["record_hash_matches_declared"] = (
            not public["declared_record_hash"]
            or public["declared_record_hash"] == public["protocol_record_hash"]
        )
        rows.append(public)
    return rows


def _source_usage_rows(protocol_input: dict[str, Any]) -> list[dict[str, Any]]:
    report_rows = (
        protocol_input.get("source_access_lease_report", {}).get("source_usage_rows", [])
    )
    raw_rows = report_rows or protocol_input.get("source_usage_rows", [])
    rows = []
    for index, row in enumerate(raw_rows, start=1):
        public = {
            "source_usage_id": str(row.get("source_usage_id", f"source-use:{index}")),
            "source_label": str(row.get("source_label", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash": str(row.get("content_hash", "")),
            "usage_purpose": str(row.get("usage_purpose", "retrieval_inference")),
            "settlement_status": str(row.get("settlement_status", "direct")),
            "escrow_account": str(row.get("escrow_account", "")),
            "creator_pool_rate": str(row.get("creator_pool_rate", "")),
        }
        public["direct_settlement"] = _is_direct(public)
        public["escrowed"] = _is_escrow(public)
        rows.append(public)
    return rows


def _terms_by_work(contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        str(term.get("work_id", "")): term
        for term in (contract or {}).get("terms", [])
        if term.get("work_id")
    }


def _leases_by_work(source_access_lease_report: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    leases: dict[str, list[dict[str, Any]]] = {}
    for lease in (source_access_lease_report or {}).get("lease_rows", []):
        leases.setdefault(str(lease.get("work_id", "")), []).append(lease)
    return leases


def _source_access_coverage(source_access_lease_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_usage_id", "")): row
        for row in (source_access_lease_report or {}).get("coverage_rows", [])
        if row.get("source_usage_id")
    }


def _protocol_matches_usage(protocol: dict[str, Any], usage: dict[str, Any]) -> bool:
    work_ok = not usage.get("work_id") or protocol.get("work_id") == usage.get("work_id")
    uri_ok = (
        not usage.get("source_uri")
        or protocol.get("source_uri") == usage.get("source_uri")
        or protocol.get("record_uri") == usage.get("source_uri")
    )
    hash_ok = (
        not protocol.get("content_hash")
        or not usage.get("content_hash")
        or protocol.get("content_hash") == usage.get("content_hash")
    )
    return bool((work_ok or uri_ok) and hash_ok)


def _protocol_allows_usage(protocol: dict[str, Any], usage: dict[str, Any]) -> bool:
    payment_type = str(protocol.get("payment_type", ""))
    if payment_type in DENY_PAYMENT_TYPES:
        return False
    return _use_allowed(
        set(protocol.get("allowed_uses", [])),
        set(protocol.get("prohibited_uses", [])),
        str(usage.get("usage_purpose", "retrieval_inference")),
    )


def _contract_matches_protocol(
    term: dict[str, Any],
    protocol: dict[str, Any],
    usage: dict[str, Any],
) -> bool:
    if not term or term.get("consent_status") != "active" or term.get("revoked", False):
        return False
    if protocol.get("content_hash") and term.get("content_hash") != protocol.get("content_hash"):
        return False
    purpose = str(usage.get("usage_purpose", "retrieval_inference"))
    if not _use_allowed(_uses(term.get("allowed_uses", [])), _uses(term.get("prohibited_uses", [])), purpose):
        return False
    if bool(protocol.get("attribution_required", False)) and not bool(
        term.get("requires_attribution", term.get("attribution_required", True))
    ):
        return False
    if bool(protocol.get("royalty_required", False)) and not bool(
        term.get("requires_royalty", term.get("royalty_required", True))
    ):
        return False
    return _decimal(term.get("minimum_creator_pool_rate", "0")) >= _decimal(
        protocol.get("minimum_creator_pool_rate", "0")
    )


def _lease_matches_protocol(
    leases: list[dict[str, Any]],
    protocol: dict[str, Any],
    usage: dict[str, Any],
) -> bool:
    purpose = str(usage.get("usage_purpose", "retrieval_inference"))
    required_rate = _decimal(protocol.get("minimum_creator_pool_rate", "0"))
    for lease in leases:
        if lease.get("revoked", False):
            continue
        if protocol.get("content_hash") and lease.get("content_hash") != protocol.get("content_hash"):
            continue
        if not _use_allowed(_uses(lease.get("allowed_uses", [])), _uses(lease.get("prohibited_uses", [])), purpose):
            continue
        if _decimal(lease.get("minimum_creator_pool_rate", "0")) < required_rate:
            continue
        if bool(protocol.get("attribution_required", False)) and not bool(
            lease.get("attribution_required", True)
        ):
            continue
        if bool(protocol.get("royalty_required", False)) and not bool(
            lease.get("royalty_required", True)
        ):
            continue
        return True
    return False


def _artifact_bindings(protocol_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "creator_license_contract_hash": _declared_hash(
            protocol_input.get("creator_license_contract")
        ),
        "source_access_lease_report_hash": _declared_hash(
            protocol_input.get("source_access_lease_report")
        ),
        "source_availability_report_hash": _declared_hash(
            protocol_input.get("source_availability_report")
        ),
        "evidence_region_binding_report_hash": _declared_hash(
            protocol_input.get("evidence_region_binding_report")
        ),
        "creator_license_contract_hash_reproducible": _artifact_hash_is_reproducible(
            protocol_input.get("creator_license_contract")
        ),
        "source_access_lease_hash_reproducible": _artifact_hash_is_reproducible(
            protocol_input.get("source_access_lease_report")
        ),
        "source_availability_hash_reproducible": _artifact_hash_is_reproducible(
            protocol_input.get("source_availability_report")
        ),
        "evidence_region_binding_hash_reproducible": _artifact_hash_is_reproducible(
            protocol_input.get("evidence_region_binding_report")
        ),
    }


def _coverage_rows(
    *,
    usage_rows: list[dict[str, Any]],
    protocol_rows: list[dict[str, Any]],
    creator_license_contract: dict[str, Any] | None,
    source_access_lease_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    terms = _terms_by_work(creator_license_contract)
    leases = _leases_by_work(source_access_lease_report)
    source_access_rows = _source_access_coverage(source_access_lease_report)
    rows = []
    for usage in usage_rows:
        matching_protocols = [
            protocol for protocol in protocol_rows if _protocol_matches_usage(protocol, usage)
        ]
        allowing_protocols = [
            protocol
            for protocol in matching_protocols
            if protocol["protocol_supported"] and _protocol_allows_usage(protocol, usage)
        ]
        selected = allowing_protocols[0] if allowing_protocols else (
            matching_protocols[0] if matching_protocols else {}
        )
        contract_ok = bool(
            selected and _contract_matches_protocol(terms.get(usage["work_id"], {}), selected, usage)
        )
        lease_ok = bool(
            selected and _lease_matches_protocol(leases.get(usage["work_id"], []), selected, usage)
        )
        source_access_row = source_access_rows.get(usage["source_usage_id"], {})
        source_access_covered = bool(
            source_access_row.get("covered_for_direct_settlement", False)
            or (
                not usage["direct_settlement"]
                and source_access_row.get("denied_or_unleased_escrowed", False)
            )
        )
        protocol_allows = bool(selected and selected in allowing_protocols)
        missing_or_denied_escrowed = bool(
            (not matching_protocols or not protocol_allows) and usage["escrowed"]
        )
        row = {
            "source_usage_id": usage["source_usage_id"],
            "source_label": usage["source_label"],
            "work_id": usage["work_id"],
            "chunk_id": usage["chunk_id"],
            "usage_purpose": usage["usage_purpose"],
            "direct_settlement": usage["direct_settlement"],
            "escrowed": usage["escrowed"],
            "matching_protocol_count": len(matching_protocols),
            "supported_protocol_count": sum(
                1 for protocol in matching_protocols if protocol["protocol_supported"]
            ),
            "selected_protocol_record_id": str(selected.get("protocol_record_id", "")),
            "selected_protocol": str(selected.get("protocol", "")),
            "protocol_allows_use": protocol_allows,
            "protocol_payment_type": str(selected.get("payment_type", "")),
            "protocol_attribution_required": bool(
                selected.get("attribution_required", False)
            ),
            "protocol_royalty_required": bool(selected.get("royalty_required", False)),
            "protocol_minimum_creator_pool_rate": str(
                selected.get("minimum_creator_pool_rate", "0")
            ),
            "creator_contract_matches_protocol": contract_ok,
            "source_lease_matches_protocol": lease_ok,
            "source_access_lease_covered": source_access_covered,
            "covered_for_protocol_ingestion": bool(
                usage["direct_settlement"]
                and protocol_allows
                and contract_ok
                and lease_ok
                and source_access_covered
            ),
            "missing_or_denied_protocol_escrowed": missing_or_denied_escrowed,
        }
        row["coverage_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _checks(
    *,
    protocol_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, Any],
    usage_rows: list[dict[str, Any]],
    protocol_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    direct_rows = [row for row in coverage_rows if row["direct_settlement"]]
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "supported_external_protocols_present": (
            not policy["require_supported_external_protocol"]
            or any(row["protocol_supported"] for row in protocol_rows)
        ),
        "protocol_record_hashes_reproducible": (
            not policy["require_protocol_hash_replay"]
            or all(row["record_hash_matches_declared"] for row in protocol_rows)
        ),
        "direct_sources_have_protocol_records": (
            not policy["require_protocol_record_for_direct_sources"]
            or all(row["matching_protocol_count"] > 0 for row in direct_rows)
        ),
        "direct_protocol_terms_allow_use": (
            not policy["require_protocol_terms_allow_use"]
            or all(row["protocol_allows_use"] for row in direct_rows)
        ),
        "direct_protocol_terms_preserved_in_contract": (
            not policy["require_creator_contract_matches_protocol"]
            or all(row["creator_contract_matches_protocol"] for row in direct_rows)
        ),
        "direct_protocol_terms_preserved_in_source_lease": (
            not policy["require_source_lease_matches_protocol"]
            or all(
                row["source_lease_matches_protocol"]
                and row["source_access_lease_covered"]
                for row in direct_rows
            )
        ),
        "no_direct_settlement_without_protocol_permission": all(
            row["covered_for_protocol_ingestion"] for row in direct_rows
        ),
        "denied_or_missing_protocol_use_escrowed": (
            not policy["require_denied_or_missing_protocol_escrowed"]
            or all(
                row["direct_settlement"]
                or row["protocol_allows_use"]
                or row["missing_or_denied_protocol_escrowed"]
                for row in coverage_rows
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(
                {
                    "usage_rows": usage_rows,
                    "protocol_rows": protocol_rows,
                    "coverage_rows": coverage_rows,
                }
            )
            and _private_strings_absent(
                {
                    "usage_rows": usage_rows,
                    "protocol_rows": protocol_rows,
                    "coverage_rows": coverage_rows,
                },
                protocol_input,
            )
        ),
        "direct_source_count_positive": bool(direct_rows),
    }


def make_content_protocol_ingestion_report(
    protocol_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable external content-protocol ingestion report."""

    policy = _policy(protocol_input)
    protocol_rows = _protocol_rows(protocol_input)
    usage_rows = _source_usage_rows(protocol_input)
    artifact_bindings = _artifact_bindings(protocol_input)
    coverage_rows = _coverage_rows(
        usage_rows=usage_rows,
        protocol_rows=protocol_rows,
        creator_license_contract=protocol_input.get("creator_license_contract"),
        source_access_lease_report=protocol_input.get("source_access_lease_report"),
    )
    checks = _checks(
        protocol_input=protocol_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        usage_rows=usage_rows,
        protocol_rows=protocol_rows,
        coverage_rows=coverage_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    supported_protocols = sorted(
        {row["protocol"] for row in protocol_rows if row["protocol_supported"]}
    )
    report = {
        "version": CONTENT_PROTOCOL_INGESTION_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                protocol_input.get("case_id", "case:content-protocol-ingestion")
            ),
            "status": status,
        },
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "protocol_rows": protocol_rows,
        "source_usage_rows": usage_rows,
        "coverage_rows": coverage_rows,
        "checks": checks,
        "privacy": {
            "prompt_disclosed": False,
            "output_disclosed": False,
            "source_text_disclosed": False,
            "raw_protocol_notice_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_protocol_notices": True,
        },
        "schemas": {
            "content_protocol_ingestion_report": CONTENT_PROTOCOL_INGESTION_SCHEMA,
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "source_access_lease_report": "docs/schemas/source_access_lease_report.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "evidence_region_binding_report": "docs/schemas/evidence_region_binding_report.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "protocol_record_count": len(protocol_rows),
            "supported_protocol_count": len(supported_protocols),
            "supported_protocols": supported_protocols,
            "source_usage_count": len(usage_rows),
            "direct_source_usage_count": sum(1 for row in usage_rows if row["direct_settlement"]),
            "coverage_row_count": len(coverage_rows),
            "covered_direct_source_count": sum(
                1 for row in coverage_rows if row["covered_for_protocol_ingestion"]
            ),
            "escrowed_missing_or_denied_protocol_count": sum(
                1 for row in coverage_rows if row["missing_or_denied_protocol_escrowed"]
            ),
            "failed_check_count": len(failed),
            "external_content_protocol_ingestion_supported": True,
            "rsl_comp_scp_bridge_supported": True,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["protocol_ingestion_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_content_protocol_ingestion_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "policy",
        "artifact_bindings",
        "protocol_rows",
        "source_usage_rows",
        "coverage_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "protocol_ingestion_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing content protocol ingestion report field: {key}")
    if report.get("version") != CONTENT_PROTOCOL_INGESTION_VERSION:
        errors.append("content protocol ingestion report version is unsupported")
    if "content_protocol_ingestion_report" not in report.get("schemas", {}):
        errors.append("missing content protocol ingestion report schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("content protocol ingestion report target level is not RDLLM-L99")
    for index, row in enumerate(report.get("coverage_rows", [])):
        for key in (
            "source_usage_id",
            "matching_protocol_count",
            "protocol_allows_use",
            "creator_contract_matches_protocol",
            "source_lease_matches_protocol",
            "covered_for_protocol_ingestion",
            "coverage_row_hash",
        ):
            if key not in row:
                errors.append(f"content protocol coverage row {index} missing {key}")
    return errors


def verify_content_protocol_ingestion_report(
    report: dict[str, Any],
    protocol_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a content-protocol ingestion report by replaying private inputs."""

    errors = validate_content_protocol_ingestion_report_shape(report)
    expected = make_content_protocol_ingestion_report(
        protocol_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(report.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    if report.get("protocol_ingestion_report_hash") != expected.get(
        "protocol_ingestion_report_hash"
    ):
        errors.append("content protocol ingestion report hash mismatch")
    if report.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("content protocol ingestion report signature mismatch")
    if report.get("checks") != expected.get("checks"):
        errors.append("content protocol ingestion checks mismatch")
    if report.get("summary") != expected.get("summary"):
        errors.append("content protocol ingestion summary mismatch")
    if report.get("coverage_rows") != expected.get("coverage_rows"):
        errors.append("content protocol ingestion coverage rows mismatch")
    if report.get("protocol_rows") != expected.get("protocol_rows"):
        errors.append("content protocol ingestion protocol rows mismatch")
    if any(value is not True for value in report.get("checks", {}).values()):
        errors.append("content protocol ingestion report has failing checks")
    return errors
