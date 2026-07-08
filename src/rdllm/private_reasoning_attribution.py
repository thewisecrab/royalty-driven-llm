"""Private reasoning attribution receipts.

This layer closes the gap between public source footers and private model or
agent reasoning. It lets a provider prove that hidden scratchpads, router
handoffs, sub-agent summaries, and memory-influenced reasoning did not introduce
unfootered source influence, while keeping the raw chain of thought private.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.agent_tool_attribution import verify_agent_tool_attribution_ledger
from rdllm.artifact_refs import resolve_artifact_refs
from rdllm.client_attribution_enforcement import (
    verify_client_attribution_enforcement_receipt,
)
from rdllm.persistent_memory_provenance import (
    verify_persistent_memory_provenance_receipt,
)
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.source_footer_delivery import verify_source_footer_delivery_receipt
from rdllm.text import stable_hash

PRIVATE_REASONING_ATTRIBUTION_VERSION = "rdllm-private-reasoning-attribution/v1"
PRIVATE_REASONING_ATTRIBUTION_SCHEMA = (
    "docs/schemas/private_reasoning_attribution.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L107"
MINIMUM_MEMORY_LEVEL = "RDLLM-L106"

DECLARED_HASH_FIELDS = (
    "private_reasoning_attribution_hash",
    "persistent_memory_provenance_hash",
    "client_enforcement_hash",
    "source_footer_delivery_hash",
    "tool_ledger_hash",
    "conversation_ledger_hash",
    "proof_response_hash",
    "foundation_profile_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
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
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
    "scratchpad_text",
    "hidden_trace",
    "private_trace",
    "memory_text",
    "raw_memory_text",
    "memory_value",
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


def load_private_reasoning_attribution_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a private reasoning attribution receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"private_reasoning_attribution_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if isinstance(metadata, dict) and "foundation_profile_hash" in artifact:
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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


def _private_strings_absent(receipt: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(receipt)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("-1")


def _source_labels_from_delivery(delivery: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(row.get("label", ""))
            for row in delivery.get("source_delivery_rows", [])
            if row.get("label")
        }
    )


def _client_source_labels(client_receipt: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(label)
            for label in client_receipt.get("client_decision", {}).get(
                "source_labels", []
            )
            if str(label)
        }
    )


def _client_rendered_output_hash(client_receipt: dict[str, Any]) -> str:
    return str(
        client_receipt.get("client_decision", {}).get("rendered_output_hash")
        or client_receipt.get("artifact_bindings", {}).get("rendered_output_hash")
        or ""
    )


def _private_trace_hash(step: dict[str, Any]) -> str:
    if step.get("private_trace_hash"):
        return str(step["private_trace_hash"])
    if step.get("private_trace_text"):
        return stable_hash(str(step["private_trace_text"]))
    return ""


def _private_trace_salt_hash(step: dict[str, Any]) -> str:
    if step.get("private_trace_salt_hash"):
        return str(step["private_trace_salt_hash"])
    if step.get("private_trace_salt"):
        return stable_hash(str(step["private_trace_salt"]))
    return ""


def _step_output_commitment_hash(step: dict[str, Any]) -> str:
    if step.get("output_commitment_hash"):
        return str(step["output_commitment_hash"])
    if step.get("private_step_output"):
        return stable_hash(str(step["private_step_output"]))
    return ""


def _audit_opening_commitment(
    *,
    step_id: str,
    private_trace_hash: str,
    private_trace_salt_hash: str,
    input_artifact_hashes: list[str],
    output_commitment_hash: str,
    rendered_output_hash: str,
) -> str:
    return hash_payload(
        {
            "input_artifact_root": hash_payload(input_artifact_hashes),
            "output_commitment_hash": output_commitment_hash,
            "private_trace_hash": private_trace_hash,
            "private_trace_salt_hash": private_trace_salt_hash,
            "rendered_output_hash": rendered_output_hash,
            "step_id": step_id,
            "version": PRIVATE_REASONING_ATTRIBUTION_VERSION,
        }
    )


def _reasoning_step_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    client_receipt = receipt_input.get("client_attribution_enforcement", {})
    rendered_output_hash = _client_rendered_output_hash(client_receipt)
    rows: list[dict[str, Any]] = []
    for step in sorted(
        receipt_input.get("reasoning_steps", []),
        key=lambda item: (
            int(item.get("sequence", 0) or 0),
            str(item.get("step_id", "")),
        ),
    ):
        step_id = str(step.get("step_id", ""))
        input_hashes = sorted(
            {str(value) for value in step.get("input_artifact_hashes", []) if value}
        )
        trace_hash = _private_trace_hash(step)
        salt_hash = _private_trace_salt_hash(step)
        output_hash = _step_output_commitment_hash(step)
        row_rendered_output_hash = str(
            step.get("rendered_output_hash") or rendered_output_hash
        )
        row = {
            "step_id": step_id,
            "sequence": int(step.get("sequence", 0) or 0),
            "step_type": str(step.get("step_type", "private_reasoning")),
            "operation": str(step.get("operation", "source_influenced_reasoning")),
            "private_trace_hash": trace_hash,
            "private_trace_salt_hash": salt_hash,
            "input_artifact_hashes": input_hashes,
            "source_labels": sorted(
                {str(label) for label in step.get("source_labels", []) if str(label)}
            ),
            "visible_source_labels": sorted(
                {
                    str(label)
                    for label in step.get("visible_source_labels", [])
                    if str(label)
                }
            ),
            "claim_hashes": sorted(
                {str(value) for value in step.get("claim_hashes", []) if value}
            ),
            "tool_call_ids": sorted(
                {str(value) for value in step.get("tool_call_ids", []) if value}
            ),
            "memory_ids": sorted(
                {str(value) for value in step.get("memory_ids", []) if value}
            ),
            "delegate_model_id": str(step.get("delegate_model_id", "")),
            "output_commitment_hash": output_hash,
            "rendered_output_hash": row_rendered_output_hash,
            "audit_opening_commitment": str(
                step.get("audit_opening_commitment")
                or _audit_opening_commitment(
                    step_id=step_id,
                    private_trace_hash=trace_hash,
                    private_trace_salt_hash=salt_hash,
                    input_artifact_hashes=input_hashes,
                    output_commitment_hash=output_hash,
                    rendered_output_hash=row_rendered_output_hash,
                )
            ),
            "raw_private_reasoning_disclosed": False,
        }
        row["reasoning_step_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _royalty_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for obligation in sorted(
        receipt_input.get("reasoning_royalty_obligations", []),
        key=lambda item: (
            str(item.get("source_label", "")),
            str(item.get("creator_id", "")),
            str(item.get("work_id", "")),
        ),
    ):
        row = {
            "source_label": str(obligation.get("source_label", "")),
            "creator_id": str(obligation.get("creator_id", "")),
            "work_id": str(obligation.get("work_id", "")),
            "share": str(obligation.get("share", "0")),
            "settlement_state": str(obligation.get("settlement_state", "direct")),
            "basis": str(
                obligation.get("basis", "private_reasoning_source_influence")
            ),
            "obligation_hash": hash_payload(obligation),
        }
        row["royalty_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _memory_ids_from_persistent_receipt(receipt: dict[str, Any]) -> set[str]:
    return {
        str(row.get("memory_id", ""))
        for row in receipt.get("memory_entries", [])
        if row.get("memory_id")
    }


def _tool_call_ids_from_ledger(ledger: dict[str, Any]) -> set[str]:
    return {
        str(row.get("tool_call_id", ""))
        for row in ledger.get("tool_calls", [])
        if row.get("tool_call_id")
    }


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    source_footer_delivery = receipt_input.get("source_footer_delivery")
    client_receipt = receipt_input.get("client_attribution_enforcement")
    persistent_memory = receipt_input.get("persistent_memory_provenance")
    agent_tool = receipt_input.get("agent_tool_attribution_ledger")
    reasoning_steps = receipt_input.get("reasoning_steps", [])
    return {
        "source_footer_delivery_hash": _declared_hash(source_footer_delivery),
        "source_footer_delivery_hash_reproducible": _artifact_hash_is_reproducible(
            source_footer_delivery
        ),
        "client_enforcement_hash": _declared_hash(client_receipt),
        "client_enforcement_hash_reproducible": _artifact_hash_is_reproducible(
            client_receipt
        ),
        "persistent_memory_provenance_hash": _declared_hash(persistent_memory),
        "persistent_memory_provenance_hash_reproducible": _artifact_hash_is_reproducible(
            persistent_memory
        )
        if persistent_memory
        else True,
        "agent_tool_attribution_ledger_hash": _declared_hash(agent_tool),
        "agent_tool_attribution_ledger_hash_reproducible": _artifact_hash_is_reproducible(
            agent_tool
        )
        if agent_tool
        else True,
        "reasoning_step_root": hash_payload(_reasoning_step_rows(receipt_input)),
        "reasoning_step_input_hash": hash_payload(reasoning_steps),
        "royalty_obligation_root": hash_payload(_royalty_rows(receipt_input)),
        "rendered_output_hash": _client_rendered_output_hash(client_receipt),
    }


def _policy_summary(receipt_input: dict[str, Any]) -> dict[str, Any]:
    policy = receipt_input.get("reasoning_policy", {})
    return {
        "policy_id": str(
            policy.get("policy_id", "policy:private-reasoning-attribution")
        ),
        "requires_private_trace_commitments": policy.get(
            "requires_private_trace_commitments"
        )
        is True,
        "requires_source_carry_forward": policy.get("requires_source_carry_forward")
        is True,
        "requires_footer_closure": policy.get("requires_footer_closure") is True,
        "requires_memory_receipts_for_memory_steps": policy.get(
            "requires_memory_receipts_for_memory_steps"
        )
        is True,
        "requires_auditor_challenge_support": policy.get(
            "requires_auditor_challenge_support"
        )
        is True,
        "requires_no_raw_private_reasoning": policy.get(
            "requires_no_raw_private_reasoning"
        )
        is True,
        "policy_hash": hash_payload(policy),
    }


def _known_upstream_hashes(
    artifact_bindings: dict[str, Any],
) -> set[str]:
    return {
        str(value)
        for key, value in artifact_bindings.items()
        if key.endswith("_hash") and isinstance(value, str) and value
    }


def _is_delegation_step(row: dict[str, Any]) -> bool:
    step_type = str(row.get("step_type", ""))
    return (
        step_type in {"delegation", "subagent_handoff", "model_router_synthesis"}
        or "delegat" in step_type
        or bool(row.get("delegate_model_id"))
    )


def _base_checks(
    *,
    receipt_input: dict[str, Any],
    reasoning_steps: list[dict[str, Any]],
    royalty_rows: list[dict[str, Any]],
    artifact_bindings: dict[str, Any],
    source_footer_errors: list[str],
    client_errors: list[str],
    persistent_memory_errors: list[str],
    agent_tool_errors: list[str],
) -> dict[str, bool]:
    delivery = receipt_input.get("source_footer_delivery", {})
    client_receipt = receipt_input.get("client_attribution_enforcement", {})
    persistent_memory = receipt_input.get("persistent_memory_provenance", {})
    agent_tool = receipt_input.get("agent_tool_attribution_ledger", {})
    delivered_labels = set(_source_labels_from_delivery(delivery))
    client_labels = set(_client_source_labels(client_receipt))
    visible_labels = delivered_labels | client_labels
    used_labels = {
        label for row in reasoning_steps for label in row.get("source_labels", [])
    }
    known_hashes = _known_upstream_hashes(artifact_bindings)
    memory_ids = {
        memory_id
        for row in reasoning_steps
        for memory_id in row.get("memory_ids", [])
    }
    tool_ids = {
        tool_id
        for row in reasoning_steps
        for tool_id in row.get("tool_call_ids", [])
    }
    memory_receipt_hash = artifact_bindings.get("persistent_memory_provenance_hash", "")
    agent_tool_hash = artifact_bindings.get("agent_tool_attribution_ledger_hash", "")
    obligations_by_label = {row.get("source_label", ""): row for row in royalty_rows}
    total_share = sum((_as_decimal(row["share"]) for row in royalty_rows), Decimal("0"))
    rendered_output_hash = artifact_bindings.get("rendered_output_hash", "")

    return {
        "source_footer_delivery_verified": not source_footer_errors,
        "client_attribution_enforcement_verified": not client_errors
        and client_receipt.get("client_decision", {}).get(
            "may_render_attributed_answer"
        )
        is True,
        "persistent_memory_provenance_verified": not memory_ids
        or (
            bool(persistent_memory)
            and not persistent_memory_errors
            and persistent_memory.get("summary", {}).get(
                "target_certification_level"
            )
            == MINIMUM_MEMORY_LEVEL
        ),
        "agent_tool_ledger_verified_when_tools_used": not tool_ids
        or (bool(agent_tool) and not agent_tool_errors),
        "artifact_hashes_reproducible": artifact_bindings[
            "source_footer_delivery_hash_reproducible"
        ]
        and artifact_bindings["client_enforcement_hash_reproducible"]
        and artifact_bindings["persistent_memory_provenance_hash_reproducible"]
        and artifact_bindings["agent_tool_attribution_ledger_hash_reproducible"],
        "reasoning_steps_have_private_commitments": bool(reasoning_steps)
        and all(
            row["step_id"]
            and row["private_trace_hash"]
            and row["private_trace_salt_hash"]
            and row["output_commitment_hash"]
            and row["audit_opening_commitment"]
            for row in reasoning_steps
        ),
        "reasoning_steps_bind_upstream_artifacts": bool(reasoning_steps)
        and all(
            set(row["input_artifact_hashes"])
            and set(row["input_artifact_hashes"]) <= known_hashes
            for row in reasoning_steps
        ),
        "reasoning_source_labels_declared": bool(used_labels)
        and all(row["source_labels"] for row in reasoning_steps),
        "reasoning_source_labels_visible_in_footer": all(
            set(row["source_labels"]) <= set(row["visible_source_labels"])
            and set(row["visible_source_labels"]) <= visible_labels
            for row in reasoning_steps
        ),
        "reasoning_royalty_obligations_cover_sources": bool(royalty_rows)
        and used_labels.issubset(set(obligations_by_label))
        and total_share == Decimal("1.0"),
        "memory_reasoning_steps_bind_l106_receipt": not memory_ids
        or (
            memory_ids <= _memory_ids_from_persistent_receipt(persistent_memory)
            and all(
                (
                    not row["memory_ids"]
                    or memory_receipt_hash in row["input_artifact_hashes"]
                )
                for row in reasoning_steps
            )
        ),
        "tool_reasoning_steps_bind_tool_ledger": not tool_ids
        or (
            tool_ids <= _tool_call_ids_from_ledger(agent_tool)
            and all(
                (
                    not row["tool_call_ids"]
                    or agent_tool_hash in row["input_artifact_hashes"]
                )
                for row in reasoning_steps
            )
        ),
        "delegation_steps_identify_model_and_artifacts": all(
            (
                bool(row["delegate_model_id"]) and bool(row["input_artifact_hashes"])
            )
            if _is_delegation_step(row)
            else True
            for row in reasoning_steps
        ),
        "reasoning_steps_bind_client_rendered_output": bool(rendered_output_hash)
        and all(row["rendered_output_hash"] == rendered_output_hash for row in reasoning_steps),
        "raw_private_reasoning_not_disclosed": not _contains_private_fields(
            receipt_input.get("public_overrides", {})
        ),
    }


def make_private_reasoning_attribution_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public receipt for private reasoning source carry-forward."""

    receipt_input = resolve_artifact_refs(receipt_input)
    source_footer_errors = verify_source_footer_delivery_receipt(
        receipt_input.get("source_footer_delivery", {}),
        receipt_input.get("source_footer_delivery_input", {}),
        signing_secret=signing_secret,
    )
    client_errors = verify_client_attribution_enforcement_receipt(
        receipt_input.get("client_attribution_enforcement", {}),
        receipt_input.get("client_attribution_input", {}),
        signing_secret=signing_secret,
    )
    persistent_memory_errors: list[str] = []
    if receipt_input.get("persistent_memory_provenance"):
        persistent_memory_errors = verify_persistent_memory_provenance_receipt(
            receipt_input.get("persistent_memory_provenance", {}),
            receipt_input.get("persistent_memory_input", {}),
            signing_secret=signing_secret,
        )
    agent_tool_errors: list[str] = []
    if receipt_input.get("agent_tool_attribution_ledger"):
        agent_tool_errors = verify_agent_tool_attribution_ledger(
            receipt_input.get("agent_tool_attribution_ledger", {}),
            signing_secret=signing_secret,
        )
    reasoning_steps = _reasoning_step_rows(receipt_input)
    royalty_rows = _royalty_rows(receipt_input)
    artifact_bindings = _artifact_bindings(receipt_input)
    checks = _base_checks(
        receipt_input=receipt_input,
        reasoning_steps=reasoning_steps,
        royalty_rows=royalty_rows,
        artifact_bindings=artifact_bindings,
        source_footer_errors=source_footer_errors,
        client_errors=client_errors,
        persistent_memory_errors=persistent_memory_errors,
        agent_tool_errors=agent_tool_errors,
    )
    policy = _policy_summary(receipt_input)
    checks["reasoning_policy_is_fail_closed"] = (
        policy["requires_private_trace_commitments"]
        and policy["requires_source_carry_forward"]
        and policy["requires_footer_closure"]
        and policy["requires_memory_receipts_for_memory_steps"]
        and policy["requires_auditor_challenge_support"]
        and policy["requires_no_raw_private_reasoning"]
    )

    receipt: dict[str, Any] = {
        "version": PRIVATE_REASONING_ATTRIBUTION_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get(
                    "case_id", "case:private-reasoning-attribution"
                )
            ),
            "status": "ready" if all(checks.values()) else "blocked",
        },
        "reasoning_system": {
            "system_id": str(
                receipt_input.get("reasoning_system", {}).get(
                    "system_id", "reasoning:unknown"
                )
            ),
            "system_version": str(
                receipt_input.get("reasoning_system", {}).get(
                    "system_version", ""
                )
            ),
            "scope": str(
                receipt_input.get("reasoning_system", {}).get(
                    "scope", "private_reasoning_and_delegation"
                )
            ),
            "minimum_memory_level": MINIMUM_MEMORY_LEVEL,
        },
        "artifact_bindings": artifact_bindings,
        "reasoning_policy": policy,
        "reasoning_steps": reasoning_steps,
        "royalty_obligations": royalty_rows,
        "verification_errors": {
            "source_footer_delivery": len(source_footer_errors),
            "client_attribution_enforcement": len(client_errors),
            "persistent_memory_provenance": len(persistent_memory_errors),
            "agent_tool_attribution_ledger": len(agent_tool_errors),
        },
        "checks": checks,
        "privacy": {
            "raw_private_reasoning_disclosed": False,
            "chain_of_thought_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "memory_text_disclosed": False,
            "tool_output_text_disclosed": False,
            "payment_data_disclosed": False,
            "receipt_uses_hashes_labels_and_commitments": True,
        },
        "schemas": {
            "private_reasoning_attribution": PRIVATE_REASONING_ATTRIBUTION_SCHEMA,
            "persistent_memory_provenance": "docs/schemas/persistent_memory_provenance.schema.json",
            "client_attribution_enforcement": "docs/schemas/client_attribution_enforcement.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
    }
    checks["raw_private_reasoning_not_disclosed"] = (
        checks["raw_private_reasoning_not_disclosed"]
        and _private_strings_absent(receipt, receipt_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    receipt["case"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    receipt["summary"] = {
        "status": receipt["case"]["status"],
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_memory_level": MINIMUM_MEMORY_LEVEL,
        "reasoning_step_count": len(reasoning_steps),
        "source_label_count": len(
            sorted(
                {
                    label
                    for row in reasoning_steps
                    for label in row.get("source_labels", [])
                }
            )
        ),
        "memory_step_count": sum(1 for row in reasoning_steps if row["memory_ids"]),
        "tool_step_count": sum(1 for row in reasoning_steps if row["tool_call_ids"]),
        "delegation_step_count": sum(1 for row in reasoning_steps if _is_delegation_step(row)),
        "royalty_obligation_count": len(royalty_rows),
        "failed_check_count": failed_check_count,
        "private_reasoning_attribution_ready": failed_check_count == 0,
        "privacy_preserved": checks["raw_private_reasoning_not_disclosed"],
    }
    receipt["private_reasoning_attribution_hash"] = hash_payload(
        _hashable_receipt(receipt)
    )
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_receipt(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_private_reasoning_attribution_shape(
    receipt: dict[str, Any]
) -> list[str]:
    """Validate the public shape of a private reasoning attribution receipt."""

    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "reasoning_system",
        "artifact_bindings",
        "reasoning_policy",
        "reasoning_steps",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "private_reasoning_attribution_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing private reasoning attribution field: {key}")
    if errors:
        return errors
    if receipt.get("version") != PRIVATE_REASONING_ATTRIBUTION_VERSION:
        errors.append("private reasoning attribution version is unsupported")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("private reasoning attribution target level is not RDLLM-L107")
    if "private_reasoning_attribution" not in receipt.get("schemas", {}):
        errors.append("missing private reasoning attribution schema")
    if not isinstance(receipt.get("reasoning_steps"), list):
        errors.append("private reasoning steps must be a list")
    if _contains_private_fields(receipt):
        errors.append("private reasoning attribution receipt contains private field")
    return errors


def verify_private_reasoning_attribution_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a private reasoning attribution receipt against replay inputs."""

    errors = validate_private_reasoning_attribution_shape(receipt)
    expected = make_private_reasoning_attribution_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "reasoning_system",
        "artifact_bindings",
        "reasoning_policy",
        "reasoning_steps",
        "royalty_obligations",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if receipt.get(key) != expected.get(key):
            errors.append(f"private reasoning attribution {key} mismatch")
    if receipt.get("private_reasoning_attribution_hash") != expected.get(
        "private_reasoning_attribution_hash"
    ):
        errors.append("private reasoning attribution hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get(
        "value"
    ):
        errors.append("private reasoning attribution signature mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("private reasoning attribution has failing checks")
    return errors
