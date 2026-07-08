"""Cross-report attribution consensus and settlement-readiness reports."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

ATTRIBUTION_CONSENSUS_VERSION = "rdllm-attribution-consensus-report/v1"
ATTRIBUTION_CONSENSUS_SCHEMA = "docs/schemas/attribution_consensus_report.schema.json"
ATTRIBUTION_CONSENSUS_POLICY_VERSION = "rdllm-attribution-consensus-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L70"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_MINIMUM_QUORUM = 6
MONEY_QUANT = Decimal("0.000001")

DECLARED_HASH_FIELDS = (
    "report_hash",
    "contract_hash",
    "card_hash",
    "envelope_hash",
    "trace_hash",
    "receipt_hash",
    "summary_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "response_text",
    "output_text",
    "answer_text",
    "source_text",
    "body_text",
    "content",
    "evidence_text",
    "matched_text",
    "quote",
    "quoted_text",
    "private_trace",
    "hidden_state",
    "token_logits",
}

REQUIRED_CHANNELS = (
    "source_confidence",
    "source_authenticity",
    "evidence_sufficiency",
    "counterevidence",
    "pinpoint_provenance",
    "citation_identity",
)


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    return {
        key: value
        for key, value in (artifact or {}).items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _event_hashes(reports: dict[str, dict[str, Any] | None]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, report in reports.items():
        if not report:
            continue
        event_hash = str(report.get("event", {}).get("event_hash", ""))
        if event_hash:
            hashes[name] = event_hash
    return hashes


def _artifact_bindings(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    return {
        f"{name}_hash": _declared_hash(report)
        for name, report in reports.items()
    } | {
        f"{name}_hash_reproducible": _artifact_hash_is_reproducible(report)
        for name, report in reports.items()
    }


def _source_identity_lookup(
    *row_sets: list[dict[str, Any]],
) -> dict[tuple[str, str], tuple[str, str, str]]:
    lookup: dict[tuple[str, str], tuple[str, str, str]] = {}
    for row_set in row_sets:
        for row in row_set:
            work_id = str(row.get("work_id", ""))
            chunk_id = str(row.get("chunk_id", ""))
            creator_id = str(row.get("creator_id", ""))
            label = str(row.get("source_label") or row.get("label") or "")
            if not (work_id and creator_id):
                continue
            identity = (work_id, chunk_id, creator_id)
            lookup[(f"work:{work_id}", "")] = identity
            if chunk_id:
                lookup[(f"work_chunk:{work_id}", chunk_id)] = identity
            if label:
                lookup[(f"label:{label}", "")] = identity
    return lookup


def _source_key(
    row: dict[str, Any],
    lookup: dict[tuple[str, str], tuple[str, str, str]] | None = None,
) -> tuple[str, str, str]:
    work_id = str(row.get("work_id", ""))
    chunk_id = str(row.get("chunk_id", ""))
    creator_id = str(row.get("creator_id", ""))
    label = str(row.get("source_label") or row.get("label") or "")
    if not creator_id and lookup is not None:
        resolved = (
            lookup.get((f"work_chunk:{work_id}", chunk_id))
            or lookup.get((f"work:{work_id}", ""))
            or lookup.get((f"label:{label}", ""))
        )
        if resolved:
            work_id = work_id or resolved[0]
            chunk_id = chunk_id or resolved[1]
            creator_id = resolved[2]
    return (work_id, chunk_id, creator_id)


def _empty_source(key: tuple[str, str, str]) -> dict[str, Any]:
    work_id, chunk_id, creator_id = key
    return {
        "work_id": work_id,
        "chunk_id": chunk_id,
        "creator_id": creator_id,
        "channel_votes": {channel: False for channel in REQUIRED_CHANNELS},
        "channel_scores": {},
        "claim_hashes": set(),
        "source_labels": set(),
        "content_hashes": set(),
        "citation_ids": set(),
        "blockers": [],
    }


def _add_claim(row: dict[str, Any], claim_hash: str | None) -> None:
    if claim_hash:
        row["claim_hashes"].add(str(claim_hash))


def _add_source_label(row: dict[str, Any], label: str | None) -> None:
    if label:
        row["source_labels"].add(str(label))


def _add_content_hash(row: dict[str, Any], content_hash: str | None) -> None:
    if content_hash:
        row["content_hashes"].add(str(content_hash))


def _add_citation_id(row: dict[str, Any], citation_id: str | None) -> None:
    if citation_id:
        row["citation_ids"].add(str(citation_id))


def _source_rows(
    *,
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    counterevidence_report: dict[str, Any],
    source_authenticity_report: dict[str, Any],
    pinpoint_provenance_report: dict[str, Any],
    citation_identity_report: dict[str, Any],
    minimum_quorum: int,
) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_lookup = _source_identity_lookup(
        source_confidence_report.get("sources", []),
        source_authenticity_report.get("source_authenticity_rows", []),
        pinpoint_provenance_report.get("source_footers", []),
        citation_identity_report.get("canonical_footers", []),
    )

    def row_for(key: tuple[str, str, str]) -> dict[str, Any]:
        rows.setdefault(key, _empty_source(key))
        return rows[key]

    for source in source_confidence_report.get("sources", []):
        row = row_for(_source_key(source, source_lookup))
        _add_source_label(row, source.get("label"))
        _add_content_hash(row, source.get("content_hash"))
        score = float(source.get("confidence_score", 0.0) or 0.0)
        row["channel_scores"]["source_confidence"] = round(score, 8)
        verified = source.get("confidence_level") == "verified" and score >= 0.75
        row["channel_votes"]["source_confidence"] = verified
        if not verified:
            row["blockers"].append("source_confidence_not_verified")

    for claim in evidence_sufficiency_report.get("claims", []):
        row = row_for(_source_key(claim, source_lookup))
        _add_claim(row, claim.get("claim_hash"))
        _add_source_label(row, claim.get("source_label"))
        score = float(claim.get("top_support_score", 0.0) or 0.0)
        row["channel_scores"]["evidence_sufficiency"] = max(
            score,
            float(row["channel_scores"].get("evidence_sufficiency", 0.0)),
        )
        sufficient = (
            claim.get("sufficient") is True
            and claim.get("top_candidate_is_cited_span") is True
            and claim.get("source_footer_bound") is True
            and claim.get("source_available") is True
            and claim.get("ambiguous_decoy") is not True
        )
        row["channel_votes"]["evidence_sufficiency"] = (
            row["channel_votes"]["evidence_sufficiency"] or sufficient
        )
        if not sufficient:
            row["blockers"].append("evidence_sufficiency_failed")

    for claim in counterevidence_report.get("claims", []):
        row = row_for(_source_key(claim, source_lookup))
        _add_claim(row, claim.get("claim_hash"))
        _add_source_label(row, claim.get("source_label"))
        free = (
            claim.get("counterevidence_free") is True
            and int(claim.get("unaddressed_counterevidence_count", 0) or 0) == 0
        )
        row["channel_scores"]["counterevidence"] = 1.0 if free else 0.0
        row["channel_votes"]["counterevidence"] = (
            row["channel_votes"]["counterevidence"] or free
        )
        if not free:
            row["blockers"].append("unaddressed_counterevidence")

    for source in source_authenticity_report.get("source_authenticity_rows", []):
        row = row_for(_source_key(source, source_lookup))
        _add_source_label(row, source.get("label"))
        _add_content_hash(row, source.get("content_hash"))
        verified = (
            source.get("source_authenticity_verified") is True
            and source.get("direct_payout_eligible") is True
        )
        score = 1.0 if verified else 0.0
        row["channel_scores"]["source_authenticity"] = score
        row["channel_votes"]["source_authenticity"] = verified
        if not verified:
            row["blockers"].append("source_authenticity_not_direct_payout_eligible")

    for footer in pinpoint_provenance_report.get("source_footers", []):
        row = row_for(_source_key(footer, source_lookup))
        _add_claim(row, footer.get("claim_hash"))
        _add_source_label(row, footer.get("label"))
        _add_content_hash(row, footer.get("content_hash"))
        score = float(footer.get("decision_score", 0.0) or 0.0)
        row["channel_scores"]["pinpoint_provenance"] = max(
            score,
            float(row["channel_scores"].get("pinpoint_provenance", 0.0)),
        )
        row["channel_votes"]["pinpoint_provenance"] = True

    for footer in citation_identity_report.get("canonical_footers", []):
        row = row_for(_source_key(footer, source_lookup))
        for claim_id in footer.get("claim_ids", []):
            _add_claim(row, claim_id)
        _add_source_label(row, footer.get("label"))
        _add_citation_id(row, footer.get("citation_id"))
        verified = footer.get("identity_status") in {"verified", "minor_metadata_drift"}
        row["channel_scores"]["citation_identity"] = 1.0 if verified else 0.0
        row["channel_votes"]["citation_identity"] = verified
        if not verified:
            row["blockers"].append("citation_identity_not_verified")

    normalized: list[dict[str, Any]] = []
    for row in rows.values():
        vote_count = sum(1 for passed in row["channel_votes"].values() if passed)
        missing = [
            channel
            for channel in REQUIRED_CHANNELS
            if row["channel_votes"].get(channel) is not True
        ]
        decision = (
            "accepted"
            if vote_count >= minimum_quorum and not row["blockers"] and not missing
            else "attribution_consensus_escrow"
        )
        score_values = [
            float(value)
            for value in row["channel_scores"].values()
            if isinstance(value, (int, float))
        ]
        consensus_score = (
            sum(score_values) / len(REQUIRED_CHANNELS)
            if score_values
            else 0.0
        )
        item = {
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "creator_id": row["creator_id"],
            "claim_hashes": sorted(row["claim_hashes"]),
            "source_labels": sorted(row["source_labels"]),
            "content_hashes": sorted(row["content_hashes"]),
            "citation_ids": sorted(row["citation_ids"]),
            "channel_votes": dict(row["channel_votes"]),
            "channel_scores": {
                key: round(float(value), 8)
                for key, value in sorted(row["channel_scores"].items())
            },
            "positive_channel_count": vote_count,
            "required_channel_count": len(REQUIRED_CHANNELS),
            "minimum_quorum": minimum_quorum,
            "missing_channels": missing,
            "blockers": sorted(set(row["blockers"])),
            "consensus_score": round(consensus_score, 8),
            "decision": decision,
        }
        item["consensus_row_hash"] = hash_payload(item)
        normalized.append(item)
    normalized.sort(
        key=lambda item: (
            item["decision"] != "accepted",
            -float(item["consensus_score"]),
            item["work_id"],
            item["chunk_id"],
        )
    )
    for index, item in enumerate(normalized, start=1):
        item["rank"] = index
        item["consensus_row_hash"] = hash_payload(
            {key: value for key, value in item.items() if key != "consensus_row_hash"}
        )
    return normalized


def _allocate_pool(
    rows: list[dict[str, Any]],
    *,
    creator_pool: Decimal,
) -> tuple[list[dict[str, Any]], Decimal]:
    accepted = [
        (
            row["creator_id"],
            row["work_id"],
            row["chunk_id"],
            row["claim_hashes"],
            Decimal(str(max(float(row["consensus_score"]), 0.000001))),
        )
        for row in rows
        if row["decision"] == "accepted"
    ]
    escrow_rows = [row for row in rows if row["decision"] != "accepted"]
    escrow_weight = sum(
        (
            Decimal(str(max(float(row["consensus_score"]), 0.000001)))
            for row in escrow_rows
        ),
        Decimal("0"),
    )
    total_weight = sum((item[4] for item in accepted), Decimal("0")) + escrow_weight
    if total_weight <= Decimal("0"):
        return [
            {
                "creator_id": "attribution_consensus_escrow",
                "work_id": "escrow:attribution_consensus",
                "chunk_ids": [],
                "claim_hashes": sorted({claim for row in rows for claim in row["claim_hashes"]}),
                "decision": "attribution_consensus_escrow",
                "payout": _money(creator_pool),
                "contribution_weight": 1.0 if creator_pool else 0.0,
            }
        ], creator_pool

    paid = Decimal("0")
    totals: defaultdict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    chunk_ids: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    claim_hashes: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for index, (creator_id, work_id, chunk_id, claims, weight) in enumerate(accepted):
        if index == len(accepted) - 1 and escrow_weight == Decimal("0"):
            payout = creator_pool - paid
        else:
            payout = (creator_pool * weight / total_weight).quantize(MONEY_QUANT)
        paid += payout
        key = (creator_id, work_id)
        totals[key] += payout
        chunk_ids[key].add(chunk_id)
        claim_hashes[key].update(claims)
    escrow_total = creator_pool - paid if escrow_weight else Decimal("0")

    shares: list[dict[str, Any]] = []
    for (creator_id, work_id), payout in sorted(totals.items()):
        shares.append(
            {
                "creator_id": creator_id,
                "work_id": work_id,
                "chunk_ids": sorted(chunk_ids[(creator_id, work_id)]),
                "claim_hashes": sorted(claim_hashes[(creator_id, work_id)]),
                "decision": "accepted",
                "payout": _money(payout),
                "contribution_weight": round(float(payout / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    if escrow_total:
        shares.append(
            {
                "creator_id": "attribution_consensus_escrow",
                "work_id": "escrow:attribution_consensus",
                "chunk_ids": sorted({row["chunk_id"] for row in escrow_rows}),
                "claim_hashes": sorted({claim for row in escrow_rows for claim in row["claim_hashes"]}),
                "decision": "attribution_consensus_escrow",
                "payout": _money(escrow_total),
                "contribution_weight": round(float(escrow_total / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    return shares, escrow_total


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


def make_attribution_consensus_report(
    *,
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    counterevidence_report: dict[str, Any],
    source_authenticity_report: dict[str, Any],
    pinpoint_provenance_report: dict[str, Any],
    citation_identity_report: dict[str, Any],
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    minimum_quorum: int = DEFAULT_MINIMUM_QUORUM,
    require_event_alignment: bool = True,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public consensus report over independent attribution evidence."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    reports = {
        "source_confidence_report": source_confidence_report,
        "evidence_sufficiency_report": evidence_sufficiency_report,
        "counterevidence_report": counterevidence_report,
        "source_authenticity_report": source_authenticity_report,
        "pinpoint_provenance_report": pinpoint_provenance_report,
        "citation_identity_report": citation_identity_report,
    }
    event_hashes = _event_hashes(reports)
    aligned_event_hashes = len(set(event_hashes.values())) <= 1 and bool(event_hashes)
    rows = _source_rows(
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        source_authenticity_report=source_authenticity_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        minimum_quorum=minimum_quorum,
    )
    shares, escrow_total = _allocate_pool(rows, creator_pool=creator_pool)
    accepted_rows = [row for row in rows if row["decision"] == "accepted"]
    channel_status = {
        "source_confidence_verified": source_confidence_report.get("summary", {}).get("status") == "verified",
        "evidence_sufficiency_verified": evidence_sufficiency_report.get("summary", {}).get("status") == "verified",
        "counterevidence_verified": counterevidence_report.get("summary", {}).get("status") == "verified",
        "source_authenticity_verified": source_authenticity_report.get("summary", {}).get("status") == "verified",
        "pinpoint_provenance_ready": pinpoint_provenance_report.get("summary", {}).get("status") == "ready",
        "citation_identity_ready": citation_identity_report.get("summary", {}).get("status") == "ready",
    }
    report = {
        "report_version": ATTRIBUTION_CONSENSUS_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": ATTRIBUTION_CONSENSUS_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "creator_pool_rate": str(rate),
            "required_channels": list(REQUIRED_CHANNELS),
            "minimum_quorum": int(minimum_quorum),
            "require_event_alignment": bool(require_event_alignment),
            "accepted_decision": "accepted",
            "escrow_decision": "attribution_consensus_escrow",
        },
        "event": {
            "event_hashes": event_hashes,
            "aligned_event_hashes": aligned_event_hashes,
            "event_hash": next(iter(event_hashes.values()), ""),
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(sum((Decimal(share["payout"]) for share in shares), Decimal("0"))),
            "escrow_total": _money(escrow_total),
        },
        "artifact_bindings": _artifact_bindings(reports),
        "channel_status": channel_status,
        "consensus_rows": rows,
        "royalty_shares": shares,
        "commitments": {
            "artifact_binding_root": hash_payload(_artifact_bindings(reports)),
            "consensus_row_root": hash_payload(rows),
            "share_root": hash_payload(shares),
        },
        "checks": {},
        "schemas": {
            "attribution_consensus_report": ATTRIBUTION_CONSENSUS_SCHEMA,
        },
        "summary": {
            "status": "ready",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_count": len(rows),
            "accepted_source_count": len(accepted_rows),
            "escrow_source_count": len(rows) - len(accepted_rows),
            "minimum_quorum": int(minimum_quorum),
            "required_channel_count": len(REQUIRED_CHANNELS),
            "event_alignment_required": bool(require_event_alignment),
            "event_aligned": aligned_event_hashes,
            "creator_pool_conserved": (
                sum((Decimal(share["payout"]) for share in shares), Decimal("0")) == creator_pool
            ),
            "offline_verification_supported": True,
        },
        "privacy": {
            "private_prompt_disclosed": False,
            "private_response_disclosed": False,
            "private_source_text_disclosed": False,
            "private_tool_payload_disclosed": False,
            "report_uses_public_hashes_scores_and_decisions": True,
        },
    }
    private_field_paths = _contains_private_fields(report)
    report["checks"] = {
        "all_artifact_hashes_reproducible": all(
            value is True
            for key, value in report["artifact_bindings"].items()
            if key.endswith("_hash_reproducible")
        ),
        "all_required_channel_reports_bound": all(reports.values()),
        "all_channel_reports_ready": all(channel_status.values()),
        "event_hashes_aligned": aligned_event_hashes or not require_event_alignment,
        "accepted_rows_meet_quorum": all(
            row["positive_channel_count"] >= minimum_quorum
            and not row["missing_channels"]
            and not row["blockers"]
            for row in accepted_rows
        ),
        "blocked_or_incomplete_rows_never_direct_payout": all(
            row["decision"] != "accepted"
            for row in rows
            if row["blockers"] or row["missing_channels"]
        ),
        "non_consensus_rows_route_to_escrow": (
            len(rows) == len(accepted_rows)
            or any(share["decision"] == "attribution_consensus_escrow" for share in shares)
        ),
        "creator_pool_conserved": report["summary"]["creator_pool_conserved"],
        "public_report_has_no_private_field_names": not private_field_paths,
        "public_report_uses_no_private_text_fields": not private_field_paths,
    }
    if not all(report["checks"].values()):
        report["summary"]["status"] = "failed"
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


def validate_attribution_consensus_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "economics",
        "artifact_bindings",
        "channel_status",
        "consensus_rows",
        "royalty_shares",
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
            errors.append(f"missing attribution consensus field: {key}")
    if errors:
        return errors
    if report.get("report_version") != ATTRIBUTION_CONSENSUS_VERSION:
        errors.append("attribution consensus report version is unsupported")
    if report.get("policy", {}).get("profile") != ATTRIBUTION_CONSENSUS_POLICY_VERSION:
        errors.append("attribution consensus policy is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("attribution consensus target certification level is unsupported")
    for row in report.get("consensus_rows", []):
        for key in (
            "work_id",
            "chunk_id",
            "creator_id",
            "channel_votes",
            "positive_channel_count",
            "missing_channels",
            "blockers",
            "consensus_score",
            "decision",
            "consensus_row_hash",
        ):
            if key not in row:
                errors.append(f"missing attribution consensus row field: {key}")
    return errors


def verify_attribution_consensus_report(
    report: dict[str, Any],
    *,
    source_confidence_report: dict[str, Any],
    evidence_sufficiency_report: dict[str, Any],
    counterevidence_report: dict[str, Any],
    source_authenticity_report: dict[str, Any],
    pinpoint_provenance_report: dict[str, Any],
    citation_identity_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify an attribution consensus report from public artifacts."""

    errors = validate_attribution_consensus_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("attribution consensus report hash is not reproducible")
    policy = report.get("policy", {})
    expected = make_attribution_consensus_report(
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        source_authenticity_report=source_authenticity_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=policy.get("creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)),
        minimum_quorum=int(policy.get("minimum_quorum", DEFAULT_MINIMUM_QUORUM)),
        require_event_alignment=policy.get("require_event_alignment") is not False,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "economics",
        "artifact_bindings",
        "channel_status",
        "consensus_rows",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"attribution consensus {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("attribution consensus report hash does not match replay")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("attribution consensus report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"attribution consensus check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("attribution consensus report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("attribution consensus report signature is invalid")
    return errors
