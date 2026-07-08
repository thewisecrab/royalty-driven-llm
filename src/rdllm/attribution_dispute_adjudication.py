"""Public adjudication reports for disputed attribution and creator escrow."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

ATTRIBUTION_DISPUTE_ADJUDICATION_VERSION = (
    "rdllm-attribution-dispute-adjudication-report/v1"
)
ATTRIBUTION_DISPUTE_ADJUDICATION_SCHEMA = (
    "docs/schemas/attribution_dispute_adjudication_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L93"
MONEY_QUANT = Decimal("0.000001")
SCORE_QUANT = Decimal("0.000001")
DEFAULT_REQUIRED_QUORUM = 2
DEFAULT_ACCEPTANCE_THRESHOLD = Decimal("0.66")
DEFAULT_MIN_EVIDENCE_SCORE = Decimal("0.70")
DEFAULT_SLASH_FRACTION = Decimal("0.10")
DEFAULT_BOUNTY_FRACTION = Decimal("0.50")

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "response_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "private_note",
    "private_notes",
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
    "report_hash",
    "card_hash",
    "manifest_hash",
    "bundle_hash",
    "graph_hash",
    "attestation_hash",
    "receipt_hash",
    "event_hash",
    "artifact_hash",
)


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _money(value: Any) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _score(value: Any) -> str:
    return str(_clamp(_decimal(value)).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP))


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value))


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


def _declared_artifact_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _public_hash(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) or isinstance(value, list):
        return hash_payload(value)
    return stable_hash(str(value))


def _subject_row(dispute_input: dict[str, Any]) -> dict[str, Any]:
    subject = dict(dispute_input.get("subject_artifact", dispute_input.get("subject", {})))
    artifact_payload = subject.get("artifact_payload")
    declared_hash = str(
        subject.get("artifact_hash")
        or subject.get("report_hash")
        or subject.get("event_hash")
        or ""
    )
    payload_hash = ""
    payload_hash_candidates: set[str] = set()
    if isinstance(artifact_payload, dict):
        payload_declared_hash = _declared_artifact_hash(artifact_payload)
        payload_canonical_hash = hash_payload(artifact_payload)
        payload_replay_hash = hash_payload(_hashable_artifact(artifact_payload))
        payload_hash = payload_declared_hash or payload_replay_hash
        payload_hash_candidates = {
            value
            for value in (
                payload_declared_hash,
                payload_canonical_hash,
                payload_replay_hash,
            )
            if value
        }
    hash_reproducible = True
    if declared_hash and payload_hash_candidates:
        hash_reproducible = declared_hash in payload_hash_candidates
    subject_row = {
        "artifact_type": str(subject.get("artifact_type", subject.get("type", ""))),
        "artifact_hash": declared_hash or payload_hash,
        "payload_hash": payload_hash,
        "hash_reproducible": hash_reproducible,
        "event_hash": str(subject.get("event_hash", "")),
        "output_hash": str(subject.get("output_hash", "")),
        "model_hash": str(subject.get("model_hash", subject.get("model_id_hash", ""))),
        "provider_id": str(subject.get("provider_id", "")),
        "public_locator_hash": stable_hash(str(subject.get("public_locator", "")))
        if subject.get("public_locator")
        else "",
    }
    subject_row["subject_hash"] = hash_payload(subject_row)
    return subject_row


def _contract_row(policy: dict[str, Any], subject: dict[str, Any]) -> dict[str, Any]:
    contract = dict(policy.get("attribution_contract", {}))
    row = {
        "output_explained_hash": str(
            contract.get("output_explained_hash")
            or subject.get("output_hash")
            or subject.get("artifact_hash")
            or ""
        ),
        "eligible_feature_classes": sorted(
            str(item)
            for item in contract.get(
                "eligible_feature_classes",
                ["source_rows", "retrieved_context", "model_lineage", "black_box_probe"],
            )
        ),
        "held_fixed": sorted(str(item) for item in contract.get("held_fixed", [])),
        "score_definition": str(
            contract.get("score_definition", "claim_evidence_and_verifier_quorum")
        ),
        "counterfactual_question": str(
            contract.get(
                "counterfactual_question",
                "Would attribution or payout materially change if the disputed source were removed?",
            )
        ),
    }
    row["contract_hash"] = hash_payload(row)
    return row


def _claim_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "claim_id": str(row.get("claim_id", f"claim:{index}")),
        "claimant_id": str(row.get("claimant_id", row.get("creator_id", ""))),
        "creator_id": str(row.get("creator_id", row.get("claimant_id", ""))),
        "creator_name": str(row.get("creator_name", "")),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": str(row.get("chunk_id", "")),
        "source_row_hash": str(row.get("source_row_hash", "")),
        "claim_type": str(row.get("claim_type", "omitted_or_underpaid_attribution")),
        "claimed_amount": _money(row.get("claimed_amount", row.get("amount", "0"))),
        "claimed_share": _score(row.get("claimed_share", "0")),
        "notice_sent": bool(row.get("notice_sent", row.get("party_notified", False))),
        "standing_evidence_hash": str(
            row.get("standing_evidence_hash")
            or row.get("ownership_attestation_hash")
            or row.get("source_evidence_hash", "")
        ),
        "basis_hash": str(row.get("basis_hash") or stable_hash(str(row.get("basis", ""))))
        if row.get("basis") or row.get("basis_hash")
        else "",
    }
    public["claim_hash"] = str(row.get("claim_hash") or hash_payload(public))
    return public


def _respondent_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    rebutted = sorted(str(item) for item in row.get("rebutted_claim_ids", []))
    public = {
        "response_id": str(row.get("response_id", f"response:{index}")),
        "respondent_id": str(row.get("respondent_id", row.get("provider_id", ""))),
        "provider_id": str(row.get("provider_id", row.get("respondent_id", ""))),
        "position": str(row.get("position", "rebut")),
        "rebutted_claim_ids": rebutted,
        "notice_sent": bool(row.get("notice_sent", row.get("party_notified", False))),
        "rebuttal_evidence_hash": str(
            row.get("rebuttal_evidence_hash") or row.get("evidence_hash", "")
        ),
        "rebuttal_strength": _score(row.get("rebuttal_strength", "0")),
    }
    public["response_hash"] = str(row.get("response_hash") or hash_payload(public))
    return public


def _evidence_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    supports = sorted(str(item) for item in row.get("supports_claim_ids", row.get("supports", [])))
    rebuts = sorted(str(item) for item in row.get("rebuts_claim_ids", row.get("rebuts", [])))
    evidence_hash = str(
        row.get("evidence_hash")
        or row.get("commitment_hash")
        or row.get("artifact_hash")
        or ""
    )
    if not evidence_hash and "evidence_payload" in row:
        evidence_hash = _public_hash(row.get("evidence_payload"))
    public = {
        "evidence_id": str(row.get("evidence_id", f"evidence:{index}")),
        "submitted_by": str(row.get("submitted_by", "")),
        "evidence_type": str(row.get("evidence_type", row.get("type", "hash_commitment"))),
        "artifact_type": str(row.get("artifact_type", "")),
        "artifact_hash": str(row.get("artifact_hash", "")),
        "evidence_hash": evidence_hash,
        "supports_claim_ids": supports,
        "rebuts_claim_ids": rebuts,
        "source_row_hash": str(row.get("source_row_hash", "")),
        "relevance_score": _score(row.get("relevance_score", "0")),
        "probative_score": _score(row.get("probative_score", "0")),
        "replayable": bool(row.get("replayable", False)),
        "independent": bool(row.get("independent", True)),
    }
    public["evidence_row_hash"] = str(row.get("evidence_row_hash") or hash_payload(public))
    return public


def _vote_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    accepted = sorted(str(item) for item in row.get("accepted_claim_ids", []))
    rejected = sorted(str(item) for item in row.get("rejected_claim_ids", []))
    disclosures = sorted(str(item) for item in row.get("conflict_disclosures", []))
    public = {
        "vote_id": str(row.get("vote_id", f"vote:{index}")),
        "verifier_id": str(row.get("verifier_id", "")),
        "verifier_role": str(row.get("verifier_role", "independent_verifier")),
        "accepted_claim_ids": accepted,
        "rejected_claim_ids": rejected,
        "confidence": _score(row.get("confidence", "0")),
        "bond_amount": _money(row.get("bond_amount", "0")),
        "conflict_disclosures": disclosures,
        "conflicted": bool(row.get("conflicted", False)),
        "vote_signature_hash": str(
            row.get("vote_signature_hash") or row.get("signature_hash", "")
        ),
        "reasoning_hash": str(row.get("reasoning_hash", "")),
    }
    public["eligible_for_quorum"] = (
        bool(public["verifier_id"])
        and public["verifier_role"] in {"independent_verifier", "auditor", "watchtower"}
        and _decimal(public["bond_amount"]) > 0
        and not public["conflicted"]
        and bool(public["vote_signature_hash"])
    )
    public["vote_row_hash"] = str(row.get("vote_row_hash") or hash_payload(public))
    return public


def _misconduct_row(
    row: dict[str, Any],
    index: int,
    *,
    slash_fraction: Decimal,
    bounty_fraction: Decimal,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    bond = _decimal(row.get("bond_amount", "0"))
    slash_amount = (bond * slash_fraction).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    bounty_amount = (slash_amount * bounty_fraction).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )
    public = {
        "slash_id": str(row.get("slash_id", f"slash:{index}")),
        "party_id": str(row.get("party_id", row.get("verifier_id", ""))),
        "party_role": str(row.get("party_role", "verifier")),
        "misconduct_type": str(row.get("misconduct_type", "bad_faith_or_conflict")),
        "misconduct_hash": str(row.get("misconduct_hash", "")),
        "bond_amount": _money(bond),
        "slash_fraction": str(slash_fraction),
        "slash_amount": _money(slash_amount),
    }
    public["slash_row_hash"] = str(row.get("slash_row_hash") or hash_payload(public))
    bounty = None
    if bounty_amount > 0:
        bounty = {
            "bounty_id": str(row.get("bounty_id", f"bounty:{index}")),
            "slash_id": public["slash_id"],
            "recipient_id": str(row.get("bounty_recipient_id", "creator:dispute_bounty")),
            "basis": "successful_attribution_dispute_or_bad_faith_detection",
            "amount": _money(bounty_amount),
        }
        bounty["bounty_row_hash"] = str(row.get("bounty_row_hash") or hash_payload(bounty))
    return public, bounty


def _evidence_scores(
    evidence_rows: list[dict[str, Any]],
    respondent_rows: list[dict[str, Any]],
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    support_scores: dict[str, Decimal] = {}
    rebut_scores: dict[str, Decimal] = {}
    for evidence in evidence_rows:
        score = max(
            _decimal(evidence.get("relevance_score", "0")),
            _decimal(evidence.get("probative_score", "0")),
        )
        if not evidence.get("evidence_hash") and not evidence.get("artifact_hash"):
            score = Decimal("0")
        for claim_id in evidence.get("supports_claim_ids", []):
            support_scores[claim_id] = max(support_scores.get(claim_id, Decimal("0")), score)
        for claim_id in evidence.get("rebuts_claim_ids", []):
            rebut_scores[claim_id] = max(rebut_scores.get(claim_id, Decimal("0")), score)
    for response in respondent_rows:
        score = _decimal(response.get("rebuttal_strength", "0"))
        if not response.get("rebuttal_evidence_hash"):
            score = Decimal("0")
        for claim_id in response.get("rebutted_claim_ids", []):
            rebut_scores[claim_id] = max(rebut_scores.get(claim_id, Decimal("0")), score)
    return support_scores, rebut_scores


def _decision_rows(
    claim_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    respondent_rows: list[dict[str, Any]],
    vote_rows: list[dict[str, Any]],
    *,
    required_quorum: int,
    acceptance_threshold: Decimal,
    min_evidence_score: Decimal,
) -> tuple[list[dict[str, Any]], bool]:
    valid_votes = [row for row in vote_rows if row.get("eligible_for_quorum")]
    quorum_met = len(valid_votes) >= required_quorum
    support_scores, rebut_scores = _evidence_scores(evidence_rows, respondent_rows)
    rows = []
    for claim in claim_rows:
        claim_id = claim["claim_id"]
        accept_count = sum(1 for vote in valid_votes if claim_id in vote["accepted_claim_ids"])
        reject_count = sum(1 for vote in valid_votes if claim_id in vote["rejected_claim_ids"])
        accept_ratio = (
            Decimal(accept_count) / Decimal(len(valid_votes)) if valid_votes else Decimal("0")
        )
        support_score = support_scores.get(claim_id, Decimal("0"))
        rebut_score = rebut_scores.get(claim_id, Decimal("0"))
        accepted = (
            quorum_met
            and accept_ratio >= acceptance_threshold
            and support_score >= min_evidence_score
            and support_score >= rebut_score
            and bool(claim.get("standing_evidence_hash") or claim.get("source_row_hash"))
        )
        if accepted:
            decision = "accepted"
        elif not quorum_met:
            decision = "needs_more_verifiers"
        elif support_score < min_evidence_score:
            decision = "insufficient_supporting_evidence"
        elif rebut_score > support_score:
            decision = "respondent_rebuttal_prevailed"
        else:
            decision = "rejected_by_verifier_vote"
        row = {
            "claim_id": claim_id,
            "claim_hash": claim["claim_hash"],
            "creator_id": claim["creator_id"],
            "work_id": claim["work_id"],
            "chunk_id": claim["chunk_id"],
            "source_row_hash": claim["source_row_hash"],
            "claimed_amount": claim["claimed_amount"],
            "supporting_evidence_score": _score(support_score),
            "rebuttal_evidence_score": _score(rebut_score),
            "accepted_vote_count": accept_count,
            "rejected_vote_count": reject_count,
            "eligible_verifier_count": len(valid_votes),
            "acceptance_ratio": _score(accept_ratio),
            "decision": decision,
        }
        row["decision_hash"] = hash_payload(row)
        rows.append(row)
    return rows, quorum_met


def _appeal_state(dispute_input: dict[str, Any]) -> str:
    appeal = dict(dispute_input.get("appeal_window", {}))
    if appeal.get("appeal_filed"):
        return "appeal_pending"
    state = str(appeal.get("state", appeal.get("status", "closed"))).lower()
    if state in {"open", "pending", "appeal_pending"}:
        return "appeal_pending"
    return "closed"


def _settlement_rows(
    decision_rows: list[dict[str, Any]],
    escrow_pool: dict[str, Any],
    *,
    case_status: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pool_amount = _decimal(escrow_pool.get("amount", "0"))
    escrow_account_hash = str(escrow_pool.get("escrow_account_hash", ""))
    currency = str(escrow_pool.get("currency", "USD"))
    accepted = [row for row in decision_rows if row["decision"] == "accepted"]
    release_rows: list[dict[str, Any]] = []
    freeze_rows: list[dict[str, Any]] = []
    if case_status != "ready" or not accepted:
        freeze = {
            "freeze_id": "freeze:attribution-dispute:1",
            "escrow_account_hash": escrow_account_hash,
            "currency": currency,
            "amount": _money(pool_amount),
            "reason": "appeal_or_unresolved_attribution_dispute",
            "claim_ids": sorted(row["claim_id"] for row in decision_rows),
        }
        freeze["freeze_row_hash"] = hash_payload(freeze)
        return release_rows, [freeze]

    total_claimed = sum(_decimal(row["claimed_amount"]) for row in accepted)
    if total_claimed <= 0:
        total_claimed = Decimal(len(accepted))
    released_so_far = Decimal("0")
    for index, row in enumerate(accepted):
        if index == len(accepted) - 1:
            amount = pool_amount - released_so_far
        else:
            weight = _decimal(row["claimed_amount"]) if _decimal(row["claimed_amount"]) > 0 else Decimal("1")
            amount = (pool_amount * weight / total_claimed).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            released_so_far += amount
        release = {
            "release_id": f"release:attribution-dispute:{index + 1}",
            "claim_id": row["claim_id"],
            "claim_hash": row["claim_hash"],
            "recipient_creator_id": row["creator_id"],
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "source_row_hash": row["source_row_hash"],
            "currency": currency,
            "amount": _money(amount),
            "basis": "final_attribution_dispute_adjudication",
            "escrow_account_hash": escrow_account_hash,
        }
        release["release_row_hash"] = hash_payload(release)
        release_rows.append(release)
    return release_rows, freeze_rows


def load_attribution_dispute_adjudication_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_attribution_dispute_adjudication_report(
    dispute_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed public adjudication report for disputed attribution value."""

    policy = dict(dispute_input.get("policy", {}))
    required_quorum = int(policy.get("required_quorum", DEFAULT_REQUIRED_QUORUM))
    acceptance_threshold = _decimal(
        policy.get("acceptance_threshold", DEFAULT_ACCEPTANCE_THRESHOLD)
    )
    min_evidence_score = _decimal(
        policy.get("minimum_evidence_score", DEFAULT_MIN_EVIDENCE_SCORE)
    )
    slash_fraction = _decimal(policy.get("slash_fraction", DEFAULT_SLASH_FRACTION))
    bounty_fraction = _decimal(policy.get("bounty_fraction", DEFAULT_BOUNTY_FRACTION))
    subject = _subject_row(dispute_input)
    attribution_contract = _contract_row(policy, subject)
    claimant_rows = [
        _claim_row(row, index)
        for index, row in enumerate(dispute_input.get("claimant_rows", []), start=1)
    ]
    respondent_rows = [
        _respondent_row(row, index)
        for index, row in enumerate(dispute_input.get("respondent_rows", []), start=1)
    ]
    evidence_rows = [
        _evidence_row(row, index)
        for index, row in enumerate(dispute_input.get("evidence_items", []), start=1)
    ]
    vote_rows = [
        _vote_row(row, index)
        for index, row in enumerate(dispute_input.get("verifier_votes", []), start=1)
    ]
    decision_rows, quorum_met = _decision_rows(
        claimant_rows,
        evidence_rows,
        respondent_rows,
        vote_rows,
        required_quorum=required_quorum,
        acceptance_threshold=acceptance_threshold,
        min_evidence_score=min_evidence_score,
    )
    appeal_state = _appeal_state(dispute_input)
    preliminary_ready = (
        bool(claimant_rows)
        and bool(respondent_rows)
        and quorum_met
        and subject["hash_reproducible"]
        and any(row["decision"] == "accepted" for row in decision_rows)
    )
    if preliminary_ready and appeal_state == "closed":
        case_status = "ready"
    elif preliminary_ready and appeal_state == "appeal_pending":
        case_status = "appeal_pending"
    else:
        case_status = "needs_review"

    escrow_pool = dict(dispute_input.get("escrow_pool", {}))
    release_rows, freeze_rows = _settlement_rows(
        decision_rows,
        escrow_pool,
        case_status=case_status,
    )
    slash_rows: list[dict[str, Any]] = []
    bounty_rows: list[dict[str, Any]] = []
    for index, row in enumerate(dispute_input.get("misconduct_rows", []), start=1):
        slash, bounty = _misconduct_row(
            row,
            index,
            slash_fraction=slash_fraction,
            bounty_fraction=bounty_fraction,
        )
        slash_rows.append(slash)
        if bounty:
            bounty_rows.append(bounty)

    escrow_amount = _decimal(escrow_pool.get("amount", "0"))
    released_total = sum(_decimal(row["amount"]) for row in release_rows)
    frozen_total = sum(_decimal(row["amount"]) for row in freeze_rows)
    slash_total = sum(_decimal(row["slash_amount"]) for row in slash_rows)
    bounty_total = sum(_decimal(row["amount"]) for row in bounty_rows)
    appeal_enforced = (
        appeal_state == "closed"
        or (appeal_state == "appeal_pending" and not release_rows and frozen_total == escrow_amount)
    )
    settlement_matches_decision = (
        (case_status == "ready" and bool(release_rows) and frozen_total == 0)
        or (case_status != "ready" and not release_rows and frozen_total == escrow_amount)
    )
    checks = {
        "subject_artifact_hash_reproducible": subject["hash_reproducible"]
        and bool(subject["artifact_hash"]),
        "attribution_contract_complete": bool(attribution_contract["output_explained_hash"])
        and bool(attribution_contract["eligible_feature_classes"])
        and bool(attribution_contract["score_definition"]),
        "claimants_and_respondents_have_notice": all(
            row["notice_sent"] for row in claimant_rows + respondent_rows
        )
        and bool(claimant_rows)
        and bool(respondent_rows),
        "evidence_commitments_present": all(
            row["evidence_hash"] or row["artifact_hash"] for row in evidence_rows
        )
        and bool(evidence_rows),
        "verifier_quorum_met": quorum_met,
        "conflicted_votes_excluded_from_quorum": all(
            not row["eligible_for_quorum"] for row in vote_rows if row["conflicted"]
        ),
        "appeal_window_enforced": appeal_enforced,
        "escrow_conserved": escrow_amount == released_total + frozen_total,
        "settlement_rows_match_decision": settlement_matches_decision,
        "slash_and_bounty_bounded_by_bond": bounty_total <= slash_total,
        "private_text_not_disclosed": True,
    }
    if not all(checks.values()) and case_status == "ready":
        case_status = "needs_review"

    footer_rows = [
        {
            "claim_id": row["claim_id"],
            "creator_id": row["creator_id"],
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "source_row_hash": row["source_row_hash"],
            "supporting_evidence_score": row["supporting_evidence_score"],
            "basis": "adjudicated_attribution_footer",
            "decision": row["decision"],
        }
        for row in decision_rows
        if row["decision"] == "accepted"
    ]

    report = {
        "version": ATTRIBUTION_DISPUTE_ADJUDICATION_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(dispute_input.get("case_id", "")),
            "case_type": str(
                dispute_input.get("case_type", "attribution_dispute_adjudication")
            ),
            "status": case_status,
            "opened_at": str(dispute_input.get("opened_at", "")),
            "subject": subject,
            "attribution_contract": attribution_contract,
        },
        "policy": {
            "required_quorum": required_quorum,
            "acceptance_threshold": str(acceptance_threshold),
            "minimum_evidence_score": str(min_evidence_score),
            "slash_fraction": str(slash_fraction),
            "bounty_fraction": str(bounty_fraction),
        },
        "appeal": {
            "state": appeal_state,
            "opened_at": str(dispute_input.get("appeal_window", {}).get("opened_at", "")),
            "closes_at": str(dispute_input.get("appeal_window", {}).get("closes_at", "")),
            "appeal_filed": bool(
                dispute_input.get("appeal_window", {}).get("appeal_filed", False)
            ),
        },
        "claimant_rows": claimant_rows,
        "respondent_rows": respondent_rows,
        "evidence_rows": evidence_rows,
        "verifier_vote_rows": vote_rows,
        "decision_rows": decision_rows,
        "adjudicated_footer_rows": footer_rows,
        "escrow": {
            "escrow_id": str(escrow_pool.get("escrow_id", "")),
            "escrow_account_hash": str(escrow_pool.get("escrow_account_hash", "")),
            "currency": str(escrow_pool.get("currency", "USD")),
            "amount": _money(escrow_amount),
            "released_total": _money(released_total),
            "frozen_total": _money(frozen_total),
        },
        "settlement_release_rows": release_rows,
        "escrow_freeze_rows": freeze_rows,
        "slash_rows": slash_rows,
        "bounty_rows": bounty_rows,
        "checks": checks,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_output_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "public_report_uses_hash_commitments": True,
        },
        "schemas": {
            "attribution_dispute_adjudication_report": (
                ATTRIBUTION_DISPUTE_ADJUDICATION_SCHEMA
            )
        },
        "summary": {
            "status": case_status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "case_id": str(dispute_input.get("case_id", "")),
            "claim_count": len(claimant_rows),
            "respondent_count": len(respondent_rows),
            "evidence_count": len(evidence_rows),
            "verifier_vote_count": len(vote_rows),
            "eligible_verifier_count": sum(
                1 for row in vote_rows if row["eligible_for_quorum"]
            ),
            "accepted_claim_count": sum(
                1 for row in decision_rows if row["decision"] == "accepted"
            ),
            "rejected_claim_count": sum(
                1 for row in decision_rows if row["decision"] != "accepted"
            ),
            "footer_row_count": len(footer_rows),
            "settlement_release_count": len(release_rows),
            "escrow_freeze_count": len(freeze_rows),
            "slash_row_count": len(slash_rows),
            "bounty_row_count": len(bounty_rows),
            "appeal_state": appeal_state,
            "escrow_amount": _money(escrow_amount),
            "released_total": _money(released_total),
            "frozen_total": _money(frozen_total),
            "creator_pool_conserved": checks["escrow_conserved"],
        },
    }
    if _contains_private_fields(report):
        report["checks"]["private_text_not_disclosed"] = False
        report["summary"]["status"] = "needs_review"
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


def validate_attribution_dispute_adjudication_report_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "case",
        "policy",
        "appeal",
        "claimant_rows",
        "respondent_rows",
        "evidence_rows",
        "verifier_vote_rows",
        "decision_rows",
        "adjudicated_footer_rows",
        "escrow",
        "settlement_release_rows",
        "escrow_freeze_rows",
        "slash_rows",
        "bounty_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing attribution dispute adjudication report field: {key}")
    if report.get("version") != ATTRIBUTION_DISPUTE_ADJUDICATION_VERSION:
        errors.append("attribution dispute adjudication report version is unsupported")
    if "attribution_dispute_adjudication_report" not in report.get("schemas", {}):
        errors.append("missing attribution dispute adjudication report schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("attribution dispute adjudication target level is incorrect")
    return errors


def verify_attribution_dispute_adjudication_report(
    report: dict[str, Any],
    dispute_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a public adjudication report against private dispute evidence."""

    errors = validate_attribution_dispute_adjudication_report_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("report_hash", ""):
        errors.append("attribution dispute adjudication report hash is not reproducible")
    expected = make_attribution_dispute_adjudication_report(
        dispute_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at"),
        signing_secret=signing_secret,
    )
    comparable_keys = (
        "case",
        "policy",
        "appeal",
        "claimant_rows",
        "respondent_rows",
        "evidence_rows",
        "verifier_vote_rows",
        "decision_rows",
        "adjudicated_footer_rows",
        "escrow",
        "settlement_release_rows",
        "escrow_freeze_rows",
        "slash_rows",
        "bounty_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
    )
    for key in comparable_keys:
        if report.get(key) != expected.get(key):
            errors.append(f"attribution dispute adjudication report {key} does not match evidence")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("attribution dispute adjudication report hash does not match evidence")
    if report.get("summary", {}).get("status") not in {"ready", "appeal_pending"}:
        errors.append("attribution dispute adjudication report status is not settled or appeal-safe")
    for check, passed in report.get("checks", {}).items():
        if not passed:
            errors.append(f"attribution dispute adjudication check failed: {check}")
    if _contains_private_fields(report) or any(
        private and private in canonical_json(report)
        for private in dispute_input.get("private_strings", [])
    ):
        errors.append("attribution dispute adjudication report discloses private text")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("attribution dispute adjudication report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("attribution dispute adjudication report signature is invalid")
    return errors
