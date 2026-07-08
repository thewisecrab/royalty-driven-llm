"""Cross-artifact conformance checks for RDLLM deployments."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import verify_receipt
from rdllm.statements import verify_royalty_statement
from rdllm.telemetry import verify_trace_exchange
from rdllm.text import stable_hash
from rdllm.transparency import TransparencyLog, verify_inclusion

SOURCE_LABEL_RE = re.compile(r"^\[(S\d+)\]\s+", re.MULTILINE)
SPAN_HASH_RE = re.compile(r"span=([a-f0-9]{12})")


def source_labels_in_output(output: str) -> list[str]:
    return SOURCE_LABEL_RE.findall(output)


def span_hash_prefixes_in_output(output: str) -> list[str]:
    return SPAN_HASH_RE.findall(output)


def verify_event_receipt(
    event: UsageEvent,
    receipt: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    errors = verify_receipt(receipt, signing_secret=signing_secret)
    if errors:
        return errors

    payload = receipt["payload"]
    receipt_event = payload["event"]
    if receipt_event["event_id"] != event.event_id:
        errors.append("receipt event_id does not match ledger event")
    if receipt_event["event_hash"] != event.event_hash:
        errors.append("receipt event_hash does not match ledger event")
    if receipt_event["prompt_hash"] != stable_hash(event.prompt):
        errors.append("receipt prompt hash does not match ledger event")
    if receipt_event["answer_hash"] != stable_hash(event.answer_text or event.output):
        errors.append("receipt answer hash does not match ledger event")
    if receipt_event["rendered_output_hash"] != stable_hash(event.output):
        errors.append("receipt rendered output hash does not match ledger event")

    if payload["grounding"]["report"] != event.grounding_report:
        errors.append("receipt grounding report does not match ledger event")
    if payload["grounding"].get("quality") != event.grounding_quality:
        errors.append("receipt grounding quality does not match ledger event")
    if payload["grounding"].get("attribution_gap") != event.attribution_gap:
        errors.append("receipt attribution gap report does not match ledger event")

    event_accesses = [access.to_dict() for access in event.source_accesses]
    if payload["grounding"].get("source_accesses") != event_accesses:
        errors.append("receipt source access trace does not match ledger event")

    event_sources = [reference.to_dict() for reference in event.source_references]
    if payload["grounding"]["sources"] != event_sources:
        errors.append("receipt sources do not match ledger event")

    event_claims = [claim.to_dict() for claim in event.claim_support]
    if payload["grounding"]["claims"] != event_claims:
        errors.append("receipt claims do not match ledger event")

    output_span_hashes = set(span_hash_prefixes_in_output(event.output))
    for claim in payload["grounding"]["claims"]:
        if claim.get("supported") and claim.get("evidence_span_hash"):
            span_prefix = claim["evidence_span_hash"][:12]
            if span_prefix not in output_span_hashes:
                errors.append(
                    f"rendered output missing evidence span hash {span_prefix}"
                )

    if payload["rights"]["decisions"] != event.policy_decisions:
        errors.append("receipt rights decisions do not match ledger event")
    if payload["rights"]["policy_status"] != event.grounding_report.get("policy_status"):
        errors.append("receipt policy status does not match ledger event")
    if payload["rights"]["policy_denials"] != event.grounding_report.get("policy_denials"):
        errors.append("receipt policy denial count does not match ledger event")

    if payload["registry"]["decisions"] != event.registry_decisions:
        errors.append("receipt registry decisions do not match ledger event")
    if payload["registry"]["registry_status"] != event.grounding_report.get(
        "registry_status"
    ):
        errors.append("receipt registry status does not match ledger event")
    if payload["registry"]["registry_conflicts"] != event.grounding_report.get(
        "registry_conflicts", 0
    ):
        errors.append("receipt registry conflict count does not match ledger event")
    if payload["registry"]["registry_report_hash"] != event.grounding_report.get(
        "registry_report_hash", ""
    ):
        errors.append("receipt registry report hash does not match ledger event")

    event_shares = [share.to_dict() for share in event.royalty_shares]
    if payload["economics"]["shares"] != event_shares:
        errors.append("receipt payout shares do not match ledger event")

    creator_pool = Decimal(payload["economics"]["creator_pool"])
    payout_total = sum(
        (Decimal(share["payout"]) for share in payload["economics"]["shares"]),
        Decimal("0"),
    )
    if payout_total != creator_pool:
        errors.append("receipt payouts do not sum to creator pool")

    footer_labels = source_labels_in_output(event.output)
    receipt_labels = [source["label"] for source in payload["grounding"]["sources"]]
    if footer_labels != receipt_labels:
        errors.append("rendered source footer labels do not match receipt sources")

    if event.grounding_report.get("status") == "grounded":
        unsupported = [
            claim for claim in payload["grounding"]["claims"] if not claim["supported"]
        ]
        if unsupported:
            errors.append("grounded event has unsupported claims")

    return errors


def verify_conformance_bundle(
    *,
    event: UsageEvent,
    receipt: dict[str, Any],
    signing_secret: str | None = None,
    transparency_log: TransparencyLog | None = None,
    proof: dict[str, Any] | None = None,
    trace_exchange: dict[str, Any] | None = None,
    ledger_data: dict[str, Any] | None = None,
    royalty_statement: dict[str, Any] | None = None,
    statement_receipts: list[dict[str, Any]] | None = None,
    statement_traces: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors = verify_event_receipt(event, receipt, signing_secret=signing_secret)
    proof_verified = None
    log_root = None

    if proof:
        proof_verified = verify_inclusion(proof)
        if not proof_verified:
            errors.append("transparency proof is invalid")
        if proof.get("leaf_hash") != receipt.get("receipt_hash"):
            errors.append("transparency proof leaf hash does not match receipt")

    if transparency_log:
        log_root = transparency_log.root()
        receipt_hashes = [entry["receipt_hash"] for entry in transparency_log.entries]
        if receipt["receipt_hash"] not in receipt_hashes:
            errors.append("receipt hash is not present in transparency log")
        if proof and proof.get("root") != log_root:
            errors.append("transparency proof root does not match current log root")

    trace_hash = None
    if trace_exchange:
        trace_hash = trace_exchange.get("trace_hash")
        errors.extend(
            f"trace exchange: {error}"
            for error in verify_trace_exchange(
                trace_exchange,
                event=event,
                receipt=receipt,
            )
        )

    statement_hash = None
    if royalty_statement:
        statement_hash = royalty_statement.get("statement_hash")
        if ledger_data is None:
            errors.append("royalty statement requires ledger_data for verification")
        else:
            errors.extend(
                f"royalty statement: {error}"
                for error in verify_royalty_statement(
                    ledger_data,
                    royalty_statement,
                    receipts=statement_receipts
                    if statement_receipts is not None
                    else [receipt],
                    traces=statement_traces
                    if statement_traces is not None
                    else ([trace_exchange] if trace_exchange else []),
                    signing_secret=signing_secret,
                )
            )

    checks = {
        "receipt_hash": receipt.get("receipt_hash"),
        "event_id": event.event_id,
        "source_count": len(event.source_references),
        "claim_count": len(event.claim_support),
        "grounding_status": event.grounding_report.get("status"),
        "grounding_quality_verdict": event.grounding_quality.get("verdict"),
        "grounding_quality_score": event.grounding_quality.get("overall_score"),
        "attribution_gap_verdict": event.attribution_gap.get("verdict"),
        "attribution_gap_rate": event.attribution_gap.get("scores", {}).get(
            "attribution_gap_rate"
        ),
        "policy_status": event.grounding_report.get("policy_status"),
        "policy_denials": event.grounding_report.get("policy_denials", 0),
        "registry_status": event.grounding_report.get("registry_status", "clear"),
        "registry_conflicts": event.grounding_report.get("registry_conflicts", 0),
        "proof_verified": proof_verified,
        "log_root": log_root,
        "trace_hash": trace_hash,
        "statement_hash": statement_hash,
    }
    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "checks": checks,
    }
