"""Universal emission enforcement gateway artifact.

The L147 layer is the response-time proof that a concrete foundation-model
emission was either blocked or released only after the L146 root, invocation
guard, proof-carrying response, serving gateway, source footer, live witness,
transparency log, and client display enforcement all agreed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_VERSION = (
    "rdllm-universal-emission-enforcement-gateway/v1"
)
UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_SCHEMA = (
    "docs/schemas/universal_emission_enforcement_gateway.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L147"
MINIMUM_ROOT_LEVEL = "RDLLM-L146"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-emission-enforcement-gateway.json"
)

REQUIRED_RUNTIME_ARTIFACTS = (
    "universal_rdllm_root",
    "release_gate",
    "proof_carrying_response",
    "serving_gateway_report",
    "response_envelope",
    "source_footer_delivery",
    "emission_evidence_enforcement",
    "live_emission_witness",
    "live_emission_transparency",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "foundation_runtime_router",
    "foundation_runtime_adapter",
    "foundation_api_profile",
    "foundation_model_deployment_attestation",
    "client_attribution_enforcement",
    "trust_registry",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google",
    "meta",
    "mistral",
    "cohere",
    "xai",
    "deepseek",
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_EMISSION_CHANNELS = (
    "chat_completion",
    "responses_api",
    "streaming_tokens",
    "tool_call",
    "retrieval_augmented_answer",
    "agent_action",
    "memory_influenced_answer",
    "batch_job",
    "fine_tune_or_eval_output",
    "enterprise_gateway_route",
)

REQUIRED_ENFORCEMENT_STAGES = (
    "root_preflight",
    "provider_route",
    "native_invocation",
    "release_gate",
    "proof_response",
    "gateway_egress",
    "source_footer_delivery",
    "live_witness_transparency",
    "client_display",
)

REQUIRED_FAILURE_CASES = (
    "missing_l146_root",
    "root_not_ready",
    "root_hash_mismatch",
    "release_gate_blocks",
    "proof_response_hash_mismatch",
    "serving_gateway_hash_mismatch",
    "source_footer_not_delivered",
    "invocation_guard_missing",
    "invocation_witness_missing",
    "client_enforcement_missing",
    "private_field_leak",
    "unsupported_provider_family",
)

DECLARED_HASH_FIELDS = (
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "universal_attribution_authority_control_plane_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "universal_context_provenance_bridge_hash",
    "universal_invocation_witness_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_profile_hash",
    "gateway_report_hash",
    "client_enforcement_hash",
    "live_emission_transparency_hash",
    "live_witness_hash",
    "source_footer_delivery_hash",
    "proof_response_hash",
    "envelope_hash",
    "trust_registry_hash",
    "gate_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "contract_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_query",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "raw_training_record",
    "training_text",
    "dataset_sample",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "reward_text",
    "preference_text",
    "critique_text",
    "hidden_state",
    "activation",
    "gradient",
    "model_weight",
    "model_weights",
    "model_parameters",
    "serving_log",
    "customer_log",
    "billing_record",
    "customer_id",
    "customer_email",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "raw_gateway_payload",
    "raw_emission_payload",
    "raw_artifact",
    "private_settlement_record",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_emission_enforcement_gateway_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L147 universal emission gateway."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_emission_enforcement_gateway_hash", "signature"}
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
        return False
    declared = _declared_hash(artifact)
    if artifact.get("receipt_hash") and isinstance(artifact.get("payload"), dict):
        return artifact["receipt_hash"] == hash_payload(artifact["payload"])
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(
    report_or_projection: dict[str, Any], gateway_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report_or_projection)
    private_strings = [
        str(item)
        for item in gateway_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_version(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for key, value in artifact.items():
        if key.endswith("_version") and isinstance(value, str):
            return value
    return ""


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _component_input_map(
    gateway_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = gateway_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("provider_family")
                or row.get("emission_channel")
                or row.get("stage")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(gateway_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(gateway_input.get("runtime_policy", {}))
    return {
        "profile": "rdllm-universal-emission-enforcement-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_root_level": MINIMUM_ROOT_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_runtime_artifacts": list(
            policy.get("required_runtime_artifacts", REQUIRED_RUNTIME_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_emission_channels": list(
            policy.get("required_emission_channels", REQUIRED_EMISSION_CHANNELS)
        ),
        "required_enforcement_stages": list(
            policy.get("required_enforcement_stages", REQUIRED_ENFORCEMENT_STAGES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "on_missing_root": "block_emission",
        "on_unverifiable_hash": "block_emission",
        "on_missing_source_footer": "block_display_and_settlement",
        "on_missing_invocation_witness": "block_settlement_and_open_challenge",
        "on_private_payload_leak": "block_publication",
        "settlement_policy": "settle_only_emissions_with_root_bound_footer_and_metered_invocation",
    }


def _artifact_bindings(gateway_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = gateway_input.get(name)
        if not isinstance(artifact, dict):
            artifact = None
        row = {
            "name": name,
            "version": _artifact_version(artifact),
            "declared_hash": _declared_hash(artifact),
            "payload_hash": hash_payload(artifact) if artifact else "",
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "status": _artifact_status(artifact),
            "target_level": _artifact_target_level(artifact),
            "present": bool(artifact),
        }
        row["artifact_binding_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": merkle_root(
            [row["artifact_binding_hash"] for row in rows]
        ),
        "bindings": rows,
    }


def _binding_by_name(artifact_bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name", "")): row
        for row in artifact_bindings.get("bindings", [])
        if isinstance(row, dict)
    }


def _provider_family_rows(
    gateway_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(gateway_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "root_hash": str(item.get("root_hash", "")),
            "gateway_policy_hash": str(item.get("gateway_policy_hash", "")),
            "invocation_guard_hash": str(item.get("invocation_guard_hash", "")),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", "")
            ),
            "client_enforcement_hash": str(item.get("client_enforcement_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_runtime_emission_enforcement": item.get(
                "supports_runtime_emission_enforcement"
            )
            is True,
            "supports_source_footer_delivery": item.get(
                "supports_source_footer_delivery"
            )
            is True,
            "supports_creator_settlement_metering": item.get(
                "supports_creator_settlement_metering"
            )
            is True,
            "supports_customer_verification": item.get(
                "supports_customer_verification"
            )
            is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["root_hash"])
            and bool(row["gateway_policy_hash"])
            and bool(row["invocation_guard_hash"])
            and bool(row["source_footer_delivery_hash"])
            and bool(row["client_enforcement_hash"])
            and row["public_verifier_command"]
            == "verify-universal-emission-enforcement-gateway"
            and row["supports_runtime_emission_enforcement"]
            and row["supports_source_footer_delivery"]
            and row["supports_creator_settlement_metering"]
            and row["supports_customer_verification"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _emission_channel_rows(
    gateway_input: dict[str, Any], required_channels: list[str]
) -> list[dict[str, Any]]:
    channel_map = _component_input_map(gateway_input, "emission_channel_rows")
    rows = []
    for channel in sorted(required_channels):
        item = channel_map.get(channel, {})
        row = {
            "emission_channel": channel,
            "entrypoint_hash": str(item.get("entrypoint_hash", "")),
            "root_binding_hash": str(item.get("root_binding_hash", "")),
            "invocation_witness_hash": str(item.get("invocation_witness_hash", "")),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", "")
            ),
            "client_surface_hash": str(item.get("client_surface_hash", "")),
            "covered": item.get("covered") is True,
            "source_footer_required": item.get("source_footer_required") is True,
            "metering_required": item.get("metering_required") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["entrypoint_hash"])
            and bool(row["root_binding_hash"])
            and bool(row["invocation_witness_hash"])
            and bool(row["source_footer_delivery_hash"])
            and bool(row["client_surface_hash"])
            and row["covered"]
            and row["source_footer_required"]
            and row["metering_required"]
            and row["fail_closed"]
        )
        row["emission_channel_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _enforcement_stage_rows(
    gateway_input: dict[str, Any], required_stages: list[str]
) -> list[dict[str, Any]]:
    stage_map = _component_input_map(gateway_input, "enforcement_stage_rows")
    rows = []
    for stage in sorted(required_stages):
        item = stage_map.get(stage, {})
        row = {
            "stage": stage,
            "artifact_name": str(item.get("artifact_name", "")),
            "artifact_hash": str(item.get("artifact_hash", "")),
            "stage_policy_hash": str(item.get("stage_policy_hash", "")),
            "precondition_hash": str(item.get("precondition_hash", "")),
            "postcondition_hash": str(item.get("postcondition_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "blocks_on_failure": item.get("blocks_on_failure") is True,
            "observed": item.get("observed") is True,
            "root_bound": item.get("root_bound") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["artifact_name"])
            and bool(row["artifact_hash"])
            and bool(row["stage_policy_hash"])
            and bool(row["precondition_hash"])
            and bool(row["postcondition_hash"])
            and row["verifier_command"]
            == "verify-universal-emission-enforcement-gateway"
            and row["blocks_on_failure"]
            and row["observed"]
            and row["root_bound"]
            and row["privacy_preserving"]
        )
        row["enforcement_stage_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    gateway_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(gateway_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = case_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
            "required": True,
        }
        row["passed"] = (
            bool(row["fixture_hash"])
            and row["verifier_command"]
            == "verify-universal-emission-enforcement-gateway"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _research_alignment_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "reference_id": "opentelemetry:genai-semconv",
            "reference_url": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "control": "standardized GenAI spans, events, exceptions, metrics, provider-specific conventions, and MCP conventions",
            "gateway_binding": "L147 binds emission decisions to traceable provider invocation, token usage, response id, and content-reference hooks without requiring raw prompt disclosure",
        },
        {
            "reference_id": "arxiv:2605.06635",
            "reference_url": "https://arxiv.org/abs/2605.06635",
            "control": "parse, retrieve, and evaluate LLM-generated citations instead of trusting self-citation",
            "gateway_binding": "L147 blocks displayed source footers unless delivery rows, source handles, and claim-span support are present and replayable",
        },
        {
            "reference_id": "arxiv:2605.11039",
            "reference_url": "https://arxiv.org/abs/2605.11039",
            "control": "argument-level provenance for runtime enforcement across agent steps",
            "gateway_binding": "L147 requires enforcement-stage rows and invocation witness coverage for every authority-bearing route before egress",
        },
        {
            "reference_id": "arxiv:2604.17562",
            "reference_url": "https://arxiv.org/abs/2604.17562",
            "control": "runtime controller separating execution governance from model reasoning",
            "gateway_binding": "L147 treats the gateway and client enforcement boundary as the decision point, so model text cannot self-authorize release",
        },
        {
            "reference_id": "arxiv:2603.28988",
            "reference_url": "https://arxiv.org/abs/2603.28988",
            "control": "attestation-aware promotion gates that bind training and release claims to artifacts",
            "gateway_binding": "L147 requires the L146 root, release gate, proof response, and foundation deployment attestation before runtime emission",
        },
        {
            "reference_id": "ietf:draft-bondar-wca-00",
            "reference_url": "https://www.ietf.org/archive/id/draft-bondar-wca-00.html",
            "control": "reference-monitor properties for provenance-layer agent tool-call attestations",
            "gateway_binding": "L147 records fail-closed mediation, tamper-evident artifact hashes, and verifier commands for every provider family and channel",
        },
        {
            "reference_id": "attested-intelligence:verifiable-runtime-governance-2026",
            "reference_url": "https://attestedintelligence.com/documents/verifiable-runtime-governance.pdf",
            "control": "offline-verifiable cryptographic evidence of runtime authorization decisions",
            "gateway_binding": "L147 emits a signed, replayable emission decision rather than relying on mutable logs or prompt-level assertions",
        },
        {
            "reference_id": "arxiv:2604.21193",
            "reference_url": "https://arxiv.org/abs/2604.21193",
            "control": "dual attribution and verification of generated claims against internal and external evidence",
            "gateway_binding": "L147 couples visible source-footer delivery with proof-carrying response and client display enforcement for each emitted answer",
        },
    ]
    for row in rows:
        row["research_alignment_row_hash"] = hash_payload(row)
    return rows


def _all_checks_true(artifact: dict[str, Any] | None) -> bool:
    checks = artifact.get("checks", {}) if isinstance(artifact, dict) else {}
    return isinstance(checks, dict) and bool(checks) and all(
        value is True for value in checks.values()
    )


def _count(summary: dict[str, Any], key: str) -> int:
    try:
        return int(summary.get(key, 0))
    except (TypeError, ValueError):
        return 0


def make_universal_emission_enforcement_gateway(
    gateway_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L147 runtime emission enforcement gateway report."""

    created_at = created_at or now_iso()
    policy = _policy(gateway_input)
    required_artifacts = [str(name) for name in policy["required_runtime_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_channels = [str(name) for name in policy["required_emission_channels"]]
    required_stages = [str(name) for name in policy["required_enforcement_stages"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]

    artifact_bindings = _artifact_bindings(gateway_input, required_artifacts)
    bindings_by_name = _binding_by_name(artifact_bindings)
    provider_rows = _provider_family_rows(gateway_input, required_families)
    channel_rows = _emission_channel_rows(gateway_input, required_channels)
    stage_rows = _enforcement_stage_rows(gateway_input, required_stages)
    failure_rows = _failure_case_rows(gateway_input, required_cases)
    research_rows = _research_alignment_rows()

    root = gateway_input.get("universal_rdllm_root", {})
    release_gate = gateway_input.get("release_gate", {})
    proof = gateway_input.get("proof_carrying_response", {})
    gateway = gateway_input.get("serving_gateway_report", {})
    envelope = gateway_input.get("response_envelope", {})
    source_footer = gateway_input.get("source_footer_delivery", {})
    emission = gateway_input.get("emission_evidence_enforcement", {})
    live_witness = gateway_input.get("live_emission_witness", {})
    live_transparency = gateway_input.get("live_emission_transparency", {})
    guard = gateway_input.get("universal_invocation_guard", {})
    coverage = gateway_input.get("universal_invocation_coverage", {})
    invocation_witness = gateway_input.get("universal_invocation_witness", {})
    router = gateway_input.get("foundation_runtime_router", {})
    adapter = gateway_input.get("foundation_runtime_adapter", {})
    deployment = gateway_input.get("foundation_model_deployment_attestation", {})
    client = gateway_input.get("client_attribution_enforcement", {})
    trust_registry = gateway_input.get("trust_registry", {})

    root_decision = root.get("root_decision", {}) if isinstance(root, dict) else {}
    release_summary = _summary(release_gate)
    proof_summary = _summary(proof)
    gateway_summary = _summary(gateway)
    envelope_summary = _summary(envelope)
    source_summary = _summary(source_footer)
    emission_summary = _summary(emission)
    witness_summary = _summary(live_witness)
    transparency_summary = _summary(live_transparency)
    guard_summary = _summary(guard)
    coverage_summary = _summary(coverage)
    invocation_witness_summary = _summary(invocation_witness)
    router_summary = _summary(router)
    adapter_summary = _summary(adapter)
    deployment_summary = _summary(deployment)
    client_summary = _summary(client)
    registry_summary = _summary(trust_registry)

    proof_bindings = proof.get("artifact_bindings", {}) if isinstance(proof, dict) else {}
    gateway_bindings = (
        gateway.get("artifact_bindings", {}) if isinstance(gateway, dict) else {}
    )
    source_bindings = (
        source_footer.get("artifact_bindings", {})
        if isinstance(source_footer, dict)
        else {}
    )
    emission_bindings = (
        emission.get("artifact_bindings", {}) if isinstance(emission, dict) else {}
    )
    witness_bindings = (
        live_witness.get("artifact_bindings", {})
        if isinstance(live_witness, dict)
        else {}
    )
    client_bindings = client.get("artifact_bindings", {}) if isinstance(client, dict) else {}
    delivery_subject = (
        source_footer.get("delivery_subject", {})
        if isinstance(source_footer, dict)
        else {}
    )

    root_hash = _declared_hash(root)
    release_gate_hash = _declared_hash(release_gate)
    proof_hash = _declared_hash(proof)
    gateway_hash = _declared_hash(gateway)
    envelope_hash = _declared_hash(envelope)
    source_footer_hash = _declared_hash(source_footer)
    emission_hash = _declared_hash(emission)
    live_witness_hash = _declared_hash(live_witness)
    invocation_guard_hash = _declared_hash(guard)
    invocation_witness_hash = _declared_hash(invocation_witness)
    client_hash = _declared_hash(client)

    selected_provider_family = str(
        guard_summary.get("selected_provider_family")
        or router_summary.get("selected_provider_family")
        or adapter_summary.get("provider_family")
        or ""
    )

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "emission_channel_rows": channel_rows,
        "enforcement_stage_rows": stage_rows,
        "failure_case_rows": failure_rows,
        "research_alignment_rows": research_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    source_rows = source_footer.get("source_delivery_rows", [])
    source_rows_visible = (
        isinstance(source_rows, list)
        and bool(source_rows)
        and all(
            isinstance(row, dict)
            and row.get("label_visible_in_delivered_output") is True
            and row.get("label_visible_in_rendered_output") is True
            and row.get("source_available") is True
            and row.get("source_confidence_verified") is True
            and row.get("license_transaction_covered") is True
            and row.get("citation_reliance_covered") is True
            for row in source_rows
        )
    )

    checks = {
        "required_runtime_artifacts_present": all(
            bindings_by_name.get(name, {}).get("present") is True
            for name in required_artifacts
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "l146_root_ready_and_authorizes_attribution": (
            _artifact_status(root) == "ready"
            and _level_at_least(_artifact_target_level(root), MINIMUM_ROOT_LEVEL)
            and root_decision.get("publication_authorized") is True
            and root_decision.get("attribution_footer_authorized") is True
            and root_decision.get("creator_settlement_authorized") is True
            and root_decision.get("customer_confidence_footer_enabled") is True
        ),
        "root_safe_output_policy_enforced": (
            "emit_only_outputs" in str(root_decision.get("safe_output_policy", ""))
        ),
        "release_gate_emits_authorized_output": (
            release_summary.get("decision") == "emit"
            and _level_at_least(
                release_summary.get("target_certification_level", ""), "RDLLM-L35"
            )
            and _all_checks_true(release_gate)
        ),
        "proof_carrying_response_released_and_bound": (
            proof_summary.get("status") == "released"
            and proof_summary.get("decision") == "emit"
            and proof_summary.get("release_gate_hash") == release_gate_hash
            and proof_bindings.get("release_gate_hash") == release_gate_hash
            and proof_bindings.get("response_envelope_hash") == envelope_hash
            and _all_checks_true(proof)
        ),
        "serving_gateway_released_and_matches_proof": (
            gateway_summary.get("status") == "served"
            and gateway_summary.get("delivery_status") == "released"
            and gateway_summary.get("release_decision") == "emit"
            and gateway_summary.get("proof_response_hash") == proof_hash
            and gateway_summary.get("release_gate_hash") == release_gate_hash
            and gateway_bindings.get("proof_response_hash") == proof_hash
            and gateway_bindings.get("response_envelope_hash") == envelope_hash
            and _all_checks_true(gateway)
        ),
        "response_envelope_verified_with_visible_footer": (
            envelope_summary.get("status") == "verified"
            and _count(envelope_summary, "source_count") > 0
            and _count(envelope_summary, "claim_count") > 0
            and _count(envelope_summary, "visible_footer_source_count")
            == _count(envelope_summary, "source_count")
            and _count(envelope_summary, "visible_footer_span_count")
            == _count(envelope_summary, "claim_count")
        ),
        "source_footer_delivery_ready_and_complete": (
            source_summary.get("status") == "ready"
            and source_summary.get("grounded_footer_delivery_enforced") is True
            and source_summary.get("privacy_preserved") is True
            and _count(source_summary, "failed_check_count") == 0
            and _count(source_summary, "delivered_source_count")
            == _count(source_summary, "visible_source_count")
            and _count(source_summary, "delivered_source_count") > 0
            and _count(source_summary, "delivered_claim_span_count")
            == _count(source_summary, "claim_span_count")
            and _count(source_summary, "delivered_claim_span_count") > 0
            and delivery_subject.get("delivered_output_hash")
            == gateway_summary.get("delivered_output_hash")
            and source_bindings.get("proof_carrying_response_hash") == proof_hash
            and source_bindings.get("response_envelope_hash") == envelope_hash
            and source_bindings.get("serving_gateway_report_hash") == gateway_hash
            and source_rows_visible
            and _all_checks_true(source_footer)
        ),
        "emission_evidence_ready_and_gateway_bound": (
            emission_summary.get("status") == "ready"
            and emission_summary.get("serving_emission_enforced") is True
            and _count(emission_summary, "authorized_emission_unit_count")
            == _count(emission_summary, "emission_unit_count")
            and _count(emission_summary, "support_required_unit_count")
            == _count(emission_summary, "emission_unit_count")
            and emission_bindings.get("proof_carrying_response_hash") == proof_hash
            and emission_bindings.get("response_envelope_hash") == envelope_hash
            and emission_bindings.get("serving_gateway_report_hash") == gateway_hash
            and _all_checks_true(emission)
        ),
        "live_witness_and_transparency_ready": (
            witness_summary.get("status") == "ready"
            and witness_summary.get("live_emission_witnessed") is True
            and witness_summary.get("final_chain_hash")
            == emission_summary.get("final_chain_hash")
            and _count(witness_summary, "completion_accepted_witness_count")
            >= _count(witness_summary, "required_quorum")
            and _count(witness_summary, "preflight_accepted_witness_count")
            >= _count(witness_summary, "required_quorum")
            and witness_bindings.get("emission_evidence_enforcement_hash")
            == emission_hash
            and witness_bindings.get("gateway_report_hash") == gateway_hash
            and witness_bindings.get("proof_response_hash") == proof_hash
            and transparency_summary.get("status") == "ready"
            and transparency_summary.get("live_emission_transparency_included") is True
            and _count(transparency_summary, "missing_subject_count") == 0
            and _count(transparency_summary, "split_view_conflict_count") == 0
            and _all_checks_true(live_witness)
            and _all_checks_true(live_transparency)
        ),
        "universal_invocation_nonrepudiation_ready": (
            guard_summary.get("status") == "ready"
            and guard_summary.get("preflight_authorized") is True
            and guard_summary.get("native_provider_call_allowed") is True
            and guard_summary.get("source_footer_required") is True
            and coverage_summary.get("status") == "ready"
            and coverage_summary.get("coverage_complete") is True
            and _count(coverage_summary, "uncovered_call_count") == 0
            and invocation_witness_summary.get("status") == "ready"
            and invocation_witness_summary.get("nonrepudiation_complete") is True
            and _count(invocation_witness_summary, "missing_egress_count") == 0
            and _count(invocation_witness_summary, "missing_provider_receipt_count")
            == 0
            and _count(invocation_witness_summary, "missing_witness_count") == 0
            and _all_checks_true(guard)
            and _all_checks_true(coverage)
            and _all_checks_true(invocation_witness)
        ),
        "foundation_runtime_route_ready": (
            router_summary.get("status") == "released"
            and router_summary.get("router_release_authorized") is True
            and router_summary.get("fail_closed_router_supported") is True
            and router_summary.get("universal_foundation_routing_supported") is True
            and adapter_summary.get("status") == "released"
            and adapter_summary.get("runtime_release_authorized") is True
            and adapter_summary.get("fail_closed_runtime_adapter_supported") is True
            and adapter_summary.get("native_response_normalized_to_rdllm") is True
            and deployment_summary.get("status") == "released"
            and registry_summary.get("status") == "ready"
            and selected_provider_family
            and str(adapter_summary.get("provider_family", ""))
            == selected_provider_family
            and _count(router_summary, "failed_check_count") == 0
            and _count(adapter_summary, "failed_check_count") == 0
        ),
        "client_display_enforces_source_footer": (
            client_summary.get("status") == "ready"
            and client_summary.get("client_enforcement_ready") is True
            and client_summary.get("privacy_preserved") is True
            and _count(client_summary, "failed_check_count") == 0
            and client_bindings.get("source_footer_delivery_hash") == source_footer_hash
            and client_bindings.get("response_envelope_hash") == envelope_hash
            and _count(client_summary, "source_label_count")
            == _count(source_summary, "visible_source_count")
            and _all_checks_true(client)
        ),
        "output_hash_chain_bound": (
            proof_summary.get("displayed_output_hash")
            == delivery_subject.get("rendered_output_hash")
            and gateway_summary.get("delivered_output_hash")
            == delivery_subject.get("delivered_output_hash")
            and gateway_summary.get("delivered_output_hash")
            == proof.get("display", {}).get("copied_output_hash")
            and source_bindings.get("source_footer_delivery_hash", source_footer_hash)
            in {"", source_footer_hash}
        ),
        "root_gateway_invocation_hash_chain_bound": (
            bool(root_hash)
            and bool(invocation_guard_hash)
            and bool(invocation_witness_hash)
            and bool(live_witness_hash)
            and bool(client_hash)
            and guard_summary.get("response_binding_hash")
            and _count(invocation_witness_summary, "covered_call_count") > 0
        ),
        "provider_family_coverage_complete": all(row["ready"] for row in provider_rows),
        "emission_channel_coverage_complete": all(row["ready"] for row in channel_rows),
        "enforcement_stage_chain_complete": all(row["ready"] for row in stage_rows),
        "failure_cases_fail_closed": all(row["passed"] for row in failure_rows),
        "research_controls_mapped_to_mechanism": all(
            row["reference_url"] and row["gateway_binding"] for row in research_rows
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        public_projection, gateway_input
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_runtime_artifacts_present": "emission_artifact_missing",
        "artifact_hashes_reproducible": "emission_artifact_hash_not_reproducible",
        "l146_root_ready_and_authorizes_attribution": "emission_root_not_ready",
        "root_safe_output_policy_enforced": "emission_root_safe_output_policy_missing",
        "release_gate_emits_authorized_output": "emission_release_gate_blocked",
        "proof_carrying_response_released_and_bound": "emission_proof_response_not_bound",
        "serving_gateway_released_and_matches_proof": "emission_serving_gateway_mismatch",
        "response_envelope_verified_with_visible_footer": "emission_response_envelope_footer_gap",
        "source_footer_delivery_ready_and_complete": "emission_source_footer_delivery_gap",
        "emission_evidence_ready_and_gateway_bound": "emission_evidence_gateway_gap",
        "live_witness_and_transparency_ready": "emission_live_witness_or_transparency_gap",
        "universal_invocation_nonrepudiation_ready": "emission_invocation_nonrepudiation_gap",
        "foundation_runtime_route_ready": "emission_foundation_route_gap",
        "client_display_enforces_source_footer": "emission_client_enforcement_gap",
        "output_hash_chain_bound": "emission_output_hash_chain_gap",
        "root_gateway_invocation_hash_chain_bound": "emission_root_invocation_hash_chain_gap",
        "provider_family_coverage_complete": "emission_provider_family_gap",
        "emission_channel_coverage_complete": "emission_channel_gap",
        "enforcement_stage_chain_complete": "emission_stage_gap",
        "failure_cases_fail_closed": "emission_negative_case_not_blocked",
        "research_controls_mapped_to_mechanism": "emission_research_mapping_missing",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["provider_family_row_hash"] for row in provider_rows]
        ),
        "emission_channel_root": merkle_root(
            [row["emission_channel_row_hash"] for row in channel_rows]
        ),
        "enforcement_stage_root": merkle_root(
            [row["enforcement_stage_row_hash"] for row in stage_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_rows]
        ),
        "research_alignment_root": merkle_root(
            [row["research_alignment_row_hash"] for row in research_rows]
        ),
        "universal_rdllm_root_hash": root_hash,
        "release_gate_hash": release_gate_hash,
        "proof_carrying_response_hash": proof_hash,
        "serving_gateway_report_hash": gateway_hash,
        "response_envelope_hash": envelope_hash,
        "source_footer_delivery_hash": source_footer_hash,
        "emission_evidence_enforcement_hash": emission_hash,
        "live_emission_witness_hash": live_witness_hash,
        "universal_invocation_guard_hash": invocation_guard_hash,
        "universal_invocation_witness_hash": invocation_witness_hash,
        "client_attribution_enforcement_hash": client_hash,
    }
    commitments["gateway_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "gateway_version": UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "runtime_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "emission_channel_rows": channel_rows,
        "enforcement_stage_rows": stage_rows,
        "failure_case_rows": failure_rows,
        "research_alignment_rows": research_rows,
        "commitments": commitments,
        "checks": checks,
        "emission_decision": {
            "decision": "emit_root_bound_attributed_response"
            if ready
            else "block_universal_emission",
            "emission_authorized": ready,
            "source_footer_delivery_required": True,
            "source_footer_delivered": checks["source_footer_delivery_ready_and_complete"],
            "proof_carrying_response_required": True,
            "creator_settlement_authorized": ready,
            "customer_confidence_footer_required": True,
            "client_display_authorized": ready,
            "selected_provider_family": selected_provider_family,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "emit_only_after_l146_root_footer_gateway_invocation_witness_and_client_enforcement_verify"
            if ready
            else "block_display_and_settlement_preserve_challenge_evidence",
        },
        "schemas": {
            "universal_emission_enforcement_gateway": UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_SCHEMA,
            "universal_rdllm_root": "docs/schemas/universal_rdllm_root.schema.json",
            "release_gate": "docs/schemas/release_gate.schema.json",
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "emission_evidence_enforcement": "docs/schemas/emission_evidence_enforcement.schema.json",
            "live_emission_witness": "docs/schemas/live_emission_witness.schema.json",
            "live_emission_transparency": "docs/schemas/live_emission_transparency.schema.json",
            "universal_invocation_guard": "docs/schemas/universal_invocation_guard.schema.json",
            "universal_invocation_coverage": "docs/schemas/universal_invocation_coverage.schema.json",
            "universal_invocation_witness": "docs/schemas/universal_invocation_witness.schema.json",
            "client_attribution_enforcement": "docs/schemas/client_attribution_enforcement.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_training_text_disclosed": False,
            "raw_tool_payload_disclosed": False,
            "raw_memory_payload_disclosed": False,
            "raw_customer_or_billing_logs_disclosed": False,
            "model_weights_or_hidden_states_disclosed": False,
            "payment_details_disclosed": False,
            "hash_only_runtime_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_root_level": MINIMUM_ROOT_LEVEL,
            "runtime_artifact_count": len(artifact_bindings["bindings"]),
            "provider_family_count": len(provider_rows),
            "emission_channel_count": len(channel_rows),
            "enforcement_stage_count": len(stage_rows),
            "failure_case_count": len(failure_rows),
            "research_control_count": len(research_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "universal_rdllm_root_hash": root_hash,
            "release_gate_hash": release_gate_hash,
            "proof_carrying_response_hash": proof_hash,
            "serving_gateway_report_hash": gateway_hash,
            "response_envelope_hash": envelope_hash,
            "source_footer_delivery_hash": source_footer_hash,
            "emission_evidence_enforcement_hash": emission_hash,
            "live_emission_witness_hash": live_witness_hash,
            "client_attribution_enforcement_hash": client_hash,
            "selected_provider_family": selected_provider_family,
            "delivered_output_hash": gateway_summary.get("delivered_output_hash", ""),
            "visible_source_count": _count(source_summary, "visible_source_count"),
            "delivered_claim_span_count": _count(
                source_summary, "delivered_claim_span_count"
            ),
            "offline_verification_supported": True,
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
        },
    }
    report["universal_emission_enforcement_gateway_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_emission_enforcement_gateway_shape(
    report: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "gateway_version",
        "issuer",
        "created_at",
        "runtime_policy",
        "artifact_bindings",
        "provider_family_rows",
        "emission_channel_rows",
        "enforcement_stage_rows",
        "failure_case_rows",
        "research_alignment_rows",
        "commitments",
        "checks",
        "emission_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_emission_enforcement_gateway_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal emission enforcement field: {key}")
    if errors:
        return errors
    if report.get("gateway_version") != UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_VERSION:
        errors.append("universal emission enforcement gateway version is unsupported")
    if (
        report.get("schemas", {}).get("universal_emission_enforcement_gateway")
        != UNIVERSAL_EMISSION_ENFORCEMENT_GATEWAY_SCHEMA
    ):
        errors.append("universal emission enforcement gateway schema path is not declared")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append(
            "universal emission enforcement gateway target level is not RDLLM-L147"
        )
    for finding in _contains_private_fields(report):
        errors.append(
            f"universal emission enforcement gateway contains private field: {finding}"
        )
    return errors


def verify_universal_emission_enforcement_gateway(
    report: dict[str, Any],
    *,
    gateway_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L147 universal emission gateway by replaying public inputs."""

    errors = validate_universal_emission_enforcement_gateway_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_emission_enforcement_gateway_hash"):
        errors.append("universal emission enforcement gateway hash is not reproducible")

    expected = make_universal_emission_enforcement_gateway(
        gateway_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "runtime_policy",
        "artifact_bindings",
        "provider_family_rows",
        "emission_channel_rows",
        "enforcement_stage_rows",
        "failure_case_rows",
        "research_alignment_rows",
        "commitments",
        "checks",
        "emission_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal emission enforcement gateway {key} does not match replay")
    if expected.get("universal_emission_enforcement_gateway_hash") != report.get(
        "universal_emission_enforcement_gateway_hash"
    ):
        errors.append("universal emission enforcement gateway hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal emission enforcement gateway status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal emission enforcement gateway check failed: {check}")

    if not _private_strings_absent(report, gateway_input):
        errors.append("universal emission enforcement gateway leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal emission enforcement gateway is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal emission enforcement gateway signature is invalid")

    return errors
