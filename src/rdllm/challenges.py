"""Creator attribution challenge and correction reports."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.matching import TextAttributor
from rdllm.models import Chunk, UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

CHALLENGE_VERSION = "rdllm-attribution-challenge/v1"
MONEY_QUANT = Decimal("0.000001")
DEFAULT_ACCEPT_THRESHOLD = 0.20


def _money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT)


def _money_str(value: Decimal | str | int | float) -> str:
    return str(_money(value))


def _statement_hash(statement: dict[str, Any] | None) -> str:
    return statement.get("statement_hash", "") if statement else ""


def _source_commitments(event: UsageEvent) -> dict[str, str]:
    return {
        "source_access_root": hash_payload(
            [access.to_dict() for access in event.source_accesses]
        ),
        "source_reference_root": hash_payload(
            [source.to_dict() for source in event.source_references]
        ),
        "share_root": hash_payload([share.to_dict() for share in event.royalty_shares]),
        "claim_support_root": hash_payload(
            [support.to_dict() for support in event.claim_support]
        ),
    }


def _match_challenged_chunk(event: UsageEvent, chunk: Chunk) -> dict[str, Any]:
    answer_text = event.answer_text or event.output
    matches = TextAttributor([chunk], min_score=0.0).match(answer_text, limit=1)
    if not matches:
        return {
            "score": 0.0,
            "exact_score": 0.0,
            "ngram_score": 0.0,
            "longest_sequence_tokens": 0,
            "matched_text_hash": "",
        }
    match = matches[0]
    return {
        "score": round(match.score, 8),
        "exact_score": round(match.exact_score, 8),
        "ngram_score": round(match.ngram_score, 8),
        "longest_sequence_tokens": match.longest_sequence_tokens,
        "matched_text_hash": hash_payload(match.matched_text) if match.matched_text else "",
    }


def _challenge_status(
    event: UsageEvent,
    chunk: Chunk,
    match: dict[str, Any],
    *,
    accept_threshold: float,
) -> dict[str, Any]:
    already_visible = any(
        source.chunk_id == chunk.chunk_id and source.content_hash == chunk.content_hash
        for source in event.source_references
    )
    already_paid = any(
        share.chunk_id == chunk.chunk_id
        and share.content_hash == chunk.content_hash
        and not share.creator_id.endswith("_escrow")
        and share.payout > Decimal("0")
        for share in event.royalty_shares
    )
    already_accessed = any(
        access.chunk_id == chunk.chunk_id and access.content_hash == chunk.content_hash
        for access in event.source_accesses
    )
    already_credited = already_visible or already_paid
    score = float(match.get("score", 0.0))
    licensed_for_generation = (
        "generation" in chunk.allowed_uses or "external_attribution" in chunk.allowed_uses
    ) and "generation" not in chunk.prohibited_uses

    if already_credited:
        verdict = "already_credited"
        remedy_status = "no_action"
        account = ""
        issues = []
    elif score < accept_threshold:
        verdict = "rejected"
        remedy_status = "no_action"
        account = ""
        issues = ["challenge evidence is below acceptance threshold"]
    elif not licensed_for_generation:
        verdict = "accepted_escrow"
        remedy_status = "escrow_unlicensed"
        account = "rights_conflict_escrow"
        issues = ["challenged source appears influential but is not licensed for generation"]
    else:
        verdict = "accepted"
        remedy_status = "pay_claimant"
        account = chunk.creator_id
        issues = []

    adjustment_amount = Decimal("0")
    if remedy_status in {"pay_claimant", "escrow_unlicensed"}:
        adjustment_amount = (
            event.creator_pool * Decimal(str(min(score, 1.0)))
        ).quantize(MONEY_QUANT)

    return {
        "already_visible": already_visible,
        "already_paid": already_paid,
        "already_accessed": already_accessed,
        "already_credited": already_credited,
        "licensed_for_generation": licensed_for_generation,
        "verdict": verdict,
        "issues": issues,
        "remedy_status": remedy_status,
        "remedy_account": account,
        "adjustment_amount": adjustment_amount,
    }


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def make_attribution_challenge(
    event: UsageEvent,
    chunk: Chunk,
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    claimant_id: str | None = None,
    reason: str = "missing_attribution",
    statement: dict[str, Any] | None = None,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed creator challenge report for an omitted or disputed source."""

    issued_at = created_at or now_iso()
    match = _match_challenged_chunk(event, chunk)
    status = _challenge_status(
        event,
        chunk,
        match,
        accept_threshold=accept_threshold,
    )
    statement_hash = _statement_hash(statement)
    claimant = claimant_id or chunk.creator_id
    report = {
        "challenge_version": CHALLENGE_VERSION,
        "issuer": issuer,
        "created_at": issued_at,
        "challenge_id": "chl_"
        + hash_payload(
            {
                "event_hash": event.event_hash,
                "chunk_id": chunk.chunk_id,
                "content_hash": chunk.content_hash,
                "statement_hash": statement_hash,
                "created_at": issued_at,
            }
        )[:16],
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "statement_hash": statement_hash,
        },
        "claimant": {
            "claimant_id": claimant,
            "creator_id": chunk.creator_id,
            "work_id": chunk.work_id,
            "chunk_id": chunk.chunk_id,
            "title": chunk.title,
            "source_uri": chunk.source_uri,
            "content_hash": chunk.content_hash,
        },
        "claim": {
            "reason": reason,
            "accept_threshold": round(accept_threshold, 8),
            "submitted_content_hash": chunk.content_hash,
        },
        "evaluation": {
            **match,
            "already_visible": status["already_visible"],
            "already_paid": status["already_paid"],
            "already_accessed": status["already_accessed"],
            "already_credited": status["already_credited"],
            "licensed_for_generation": status["licensed_for_generation"],
            "verdict": status["verdict"],
            "issues": status["issues"],
        },
        "remedy": {
            "status": status["remedy_status"],
            "account": status["remedy_account"],
            "adjustment_amount": _money_str(status["adjustment_amount"]),
            "adjustment_basis": "creator_pool_times_match_score",
            "original_creator_pool": _money_str(event.creator_pool),
            "does_not_rewrite_event": True,
        },
        "commitments": {
            "event_hash": event.event_hash,
            "statement_hash": statement_hash,
            "challenged_content_hash": chunk.content_hash,
            **_source_commitments(event),
        },
        "privacy": {
            "prompt_disclosed": False,
            "answer_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "matched_text_hash_only": True,
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


def validate_challenge_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "challenge_version",
        "issuer",
        "created_at",
        "challenge_id",
        "event",
        "claimant",
        "claim",
        "evaluation",
        "remedy",
        "commitments",
        "privacy",
        "report_hash",
        "signature",
    ):
        if key not in report:
            errors.append(f"missing challenge field: {key}")
    if errors:
        return errors
    if report.get("challenge_version") != CHALLENGE_VERSION:
        errors.append("challenge version is unsupported")
    for key in ("event_id", "event_hash", "statement_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing challenge event field: {key}")
    for key in ("creator_id", "work_id", "chunk_id", "content_hash"):
        if key not in report.get("claimant", {}):
            errors.append(f"missing challenge claimant field: {key}")
    for key in ("score", "verdict", "matched_text_hash"):
        if key not in report.get("evaluation", {}):
            errors.append(f"missing challenge evaluation field: {key}")
    for key in ("status", "adjustment_amount", "does_not_rewrite_event"):
        if key not in report.get("remedy", {}):
            errors.append(f"missing challenge remedy field: {key}")
    return errors


def verify_attribution_challenge(
    event: UsageEvent,
    chunk: Chunk,
    report: dict[str, Any],
    *,
    statement: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an attribution challenge report against the source event and chunk."""

    errors = validate_challenge_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("challenge report hash is not reproducible")

    expected = make_attribution_challenge(
        event,
        chunk,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        claimant_id=report.get("claimant", {}).get("claimant_id") or chunk.creator_id,
        reason=report.get("claim", {}).get("reason", "missing_attribution"),
        statement=statement,
        accept_threshold=float(report.get("claim", {}).get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)),
        signing_secret=signing_secret,
    )

    for key in (
        "challenge_id",
        "event",
        "claimant",
        "claim",
        "evaluation",
        "remedy",
        "commitments",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"challenge {key} does not match recomputed report")

    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("challenge report hash does not match event and claimant source")

    if report.get("event", {}).get("event_id") != event.event_id:
        errors.append("challenge event_id does not match event")
    if report.get("event", {}).get("event_hash") != event.event_hash:
        errors.append("challenge event_hash does not match event")
    if report.get("claimant", {}).get("chunk_id") != chunk.chunk_id:
        errors.append("challenge chunk_id does not match challenged source")
    if report.get("claimant", {}).get("content_hash") != chunk.content_hash:
        errors.append("challenge content hash does not match challenged source")
    if statement is not None and report.get("event", {}).get("statement_hash") != statement.get(
        "statement_hash"
    ):
        errors.append("challenge statement_hash does not match statement")

    remedy = report.get("remedy", {})
    if remedy.get("does_not_rewrite_event") is not True:
        errors.append("challenge remedy must not rewrite original event")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("challenge report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("challenge signature is invalid")

    return errors
