"""Generate or verify the RDLLM provider compatibility matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.universal_foundation_provider_binding_matrix import (  # noqa: E402
    REQUIRED_BINDING_DOMAINS,
    REQUIRED_NATIVE_CAPABILITIES,
    REQUIRED_PROVIDER_FAMILIES,
)
from rdllm.provider_family_registry import PROVIDER_FAMILY_ALIASES  # noqa: E402
from rdllm.universal_provider_meter_normalization_contract import (  # noqa: E402
    REQUIRED_PROVIDER_METER_SURFACES,
)
from rdllm.universal_provider_response_state_normalization_contract import (  # noqa: E402
    REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES,
)


MATRIX_PATH = ROOT / "docs" / "provider_compatibility_matrix.md"

PROVIDER_INTENTS = {
    "openai_responses": "OpenAI Responses-style APIs, response objects, tools, status, usage, and citations",
    "anthropic_messages": "Anthropic Messages-style responses, stop reasons, tool use, usage, cache, and citations",
    "google_gemini_generate_content": "Gemini GenerateContent-style candidates, grounding, safety ratings, finish reasons, and usage metadata",
    "google_vertex_ai": "Vertex AI managed model routes and enterprise Google-hosted deployments",
    "meta_llama_stack": "Llama Stack or Llama-family serving surfaces",
    "mistral_chat": "Mistral chat/conversation surfaces, guardrails, cached prompt usage, and finish reasons",
    "cohere_chat": "Cohere chat surfaces, billed units, finish reasons, and safety errors",
    "xai_grok": "xAI/OpenAI-compatible chat surfaces, cached token accounting, refusals, and finish reasons",
    "deepseek_chat": "DeepSeek/OpenAI-compatible chat and reasoning surfaces",
    "azure_openai": "Azure OpenAI hosted model routes, content filters, usage, and response metadata",
    "aws_bedrock": "Bedrock Converse/InvokeModel routes, guardrails, usage, and stream events",
    "openrouter_compatible": "OpenRouter and OpenAI-compatible routers with native and normalized finish reasons",
    "local_open_weight_runtime": "Local/open-weight runtime manifests, exit status, route attestation, and usage manifests",
    "enterprise_gateway_proxy": "Enterprise proxies, private model gateways, and policy-enforced middleware",
    "rag_native_provider": "Retrieval-native products that emit source context, grounding, or RAG metadata",
    "mcp_agent_tool_runtime": "MCP/tool/agent runtimes that emit tool-call, source, and trajectory evidence",
}

METER_GROUPS = {
    "OpenAI": (
        "openai_responses_usage",
        "openai_chat_completions_usage",
        "openai_batch_usage",
        "openai_cached_input_usage",
        "openai_reasoning_usage",
    ),
    "Anthropic": (
        "anthropic_messages_usage",
        "anthropic_cache_usage",
        "anthropic_message_batches_usage",
    ),
    "Google": (
        "gemini_usage_metadata",
        "gemini_cached_content_usage",
        "gemini_batch_usage",
    ),
    "AWS": (
        "bedrock_converse_usage",
        "bedrock_invoke_model_usage",
        "bedrock_batch_inference_usage",
    ),
    "Other hosted providers": (
        "azure_openai_usage",
        "mistral_usage",
        "cohere_billed_units_usage",
        "xai_openai_compatible_usage",
        "openrouter_pass_through_usage",
    ),
    "Runtime/tool surfaces": (
        "local_runtime_usage_manifest",
        "hosted_endpoint_runtime_meter",
        "rag_tool_meter",
        "agent_tool_meter",
        "media_generation_meter",
    ),
}

RESPONSE_STATE_GROUPS = {
    "OpenAI": (
        "openai_responses_status",
        "openai_responses_incomplete_reason",
        "openai_responses_refusal_output",
        "openai_chat_finish_reason",
        "openai_content_filter_finish",
    ),
    "Anthropic": (
        "anthropic_messages_stop_reason",
        "anthropic_streaming_refusal",
        "anthropic_tool_use_pause",
    ),
    "Google": (
        "gemini_finish_reason",
        "gemini_prompt_feedback_block_reason",
        "gemini_safety_ratings",
    ),
    "AWS": (
        "bedrock_converse_stop_reason",
        "bedrock_guardrail_trace",
        "bedrock_converse_stream_stop_event",
    ),
    "Other hosted providers": (
        "azure_openai_content_filter_results",
        "mistral_finish_reason",
        "mistral_moderation_guardrail",
        "cohere_finish_reason",
        "cohere_safety_error",
        "xai_response_status_finish_reason",
        "openrouter_finish_reason_native_finish_reason",
    ),
    "Runtime/router/stream surfaces": (
        "router_gateway_error_finish_reason",
        "local_runtime_exit_status",
        "streaming_final_state",
    ),
}


def _load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _humanize(value: str) -> str:
    return value.replace("_", " ")


def _code_join(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _alias_groups(provider_aliases: dict[str, str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for alias, canonical in provider_aliases.items():
        groups.setdefault(canonical, []).append(alias)
    return {canonical: sorted(aliases) for canonical, aliases in sorted(groups.items())}


def _assert_group_coverage(
    *,
    label: str,
    required: tuple[str, ...],
    groups: dict[str, tuple[str, ...]],
) -> None:
    grouped = [item for values in groups.values() for item in values]
    missing = sorted(set(required) - set(grouped))
    extra = sorted(set(grouped) - set(required))
    duplicates = sorted({item for item in grouped if grouped.count(item) > 1})
    if missing or extra or duplicates:
        raise ValueError(
            f"{label} group coverage mismatch: missing={missing}, extra={extra}, duplicates={duplicates}"
        )


def matrix_data() -> dict[str, Any]:
    _assert_group_coverage(
        label="meter surfaces",
        required=REQUIRED_PROVIDER_METER_SURFACES,
        groups=METER_GROUPS,
    )
    _assert_group_coverage(
        label="response-state surfaces",
        required=REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES,
        groups=RESPONSE_STATE_GROUPS,
    )
    missing_intents = sorted(set(REQUIRED_PROVIDER_FAMILIES) - set(PROVIDER_INTENTS))
    if missing_intents:
        raise ValueError(f"missing provider intent rows: {missing_intents}")

    binding = _load_json("artifacts/universal_foundation_provider_binding_matrix.json")
    discovery = _load_json("artifacts/universal_live_capability_discovery_contract.json")
    meter = _load_json("artifacts/universal_provider_meter_normalization_contract.json")
    state = _load_json(
        "artifacts/universal_provider_response_state_normalization_contract.json"
    )
    certification = _load_json("artifacts/certification_report.json")

    return {
        "provider_families": list(REQUIRED_PROVIDER_FAMILIES),
        "provider_intents": {
            family: PROVIDER_INTENTS[family] for family in REQUIRED_PROVIDER_FAMILIES
        },
        "provider_aliases": {
            alias: canonical
            for alias, canonical in sorted(PROVIDER_FAMILY_ALIASES.items())
            if alias != canonical
        },
        "binding_domains": list(REQUIRED_BINDING_DOMAINS),
        "native_capabilities": list(REQUIRED_NATIVE_CAPABILITIES),
        "meter_groups": {key: list(value) for key, value in METER_GROUPS.items()},
        "response_state_groups": {
            key: list(value) for key, value in RESPONSE_STATE_GROUPS.items()
        },
        "artifact_summaries": {
            "certification_report": certification.get("summary", {}),
            "universal_foundation_provider_binding_matrix": binding.get("summary", {}),
            "universal_live_capability_discovery_contract": discovery.get("summary", {}),
            "universal_provider_meter_normalization_contract": meter.get("summary", {}),
            "universal_provider_response_state_normalization_contract": state.get(
                "summary", {}
            ),
        },
    }


def render_markdown(data: dict[str, Any]) -> str:
    binding_summary = data["artifact_summaries"][
        "universal_foundation_provider_binding_matrix"
    ]
    discovery_summary = data["artifact_summaries"][
        "universal_live_capability_discovery_contract"
    ]
    meter_summary = data["artifact_summaries"][
        "universal_provider_meter_normalization_contract"
    ]
    state_summary = data["artifact_summaries"][
        "universal_provider_response_state_normalization_contract"
    ]

    lines = [
        "# Provider Compatibility Matrix",
        "",
        "<!-- Generated by tools/provider_matrix.py. Do not edit provider rows manually. -->",
        "",
        "RDLLM does not hard-code a payout path for one model vendor. It defines provider",
        "families and adapter gates. A concrete model is compatible when its native",
        "request, response, source, safety, usage, telemetry, and settlement surfaces map",
        "into these contracts and pass conformance fixtures.",
        "",
        "## Foundation Provider Families",
        "",
        f"The current binding matrix covers {len(data['provider_families'])} provider/runtime families:",
        "",
        "| Provider family | Coverage intent |",
        "| --- | --- |",
    ]
    for family in data["provider_families"]:
        lines.append(f"| `{family}` | {data['provider_intents'][family]} |")

    lines.extend(
        [
            "",
            "## Provider Taxonomy",
            "",
            "Current provider-facing contracts use the canonical family names above. Older",
            "runtime receipts and adoption artifacts can still use legacy or aggregate",
            "labels, but release checks normalize those labels through",
            "`rdllm.provider_family_registry` and fail on unmapped names.",
            "",
            f"The taxonomy currently recognizes {len(data['provider_aliases'])} legacy aliases.",
            "",
            "| Canonical family | Recognized aliases |",
            "| --- | --- |",
        ]
    )
    for canonical, aliases in _alias_groups(data["provider_aliases"]).items():
        lines.append(f"| `{canonical}` | {_code_join(tuple(aliases))} |")

    lines.extend(
        [
            "",
            "## Required Adapter Domains",
            "",
            f"Each provider family must bind all {len(data['binding_domains'])} domains:",
            "",
        ]
    )
    lines.extend(f"- {_humanize(domain)}" for domain in data["binding_domains"])

    lines.extend(
        [
            "",
            "## Required Native Capabilities",
            "",
            f"The matrix expects coverage for {len(data['native_capabilities'])} native capabilities when a provider claims",
            "support:",
            "",
        ]
    )
    lines.extend(f"- {_humanize(capability)}" for capability in data["native_capabilities"])

    lines.extend(
        [
            "",
            "## Meter Surfaces",
            "",
            f"RDLLM normalizes {sum(len(v) for v in data['meter_groups'].values())} usage and billing surfaces before settlement:",
            "",
            "| Surface group | Required surfaces |",
            "| --- | --- |",
        ]
    )
    for group, values in data["meter_groups"].items():
        lines.append(f"| {group} | {_code_join(tuple(values))} |")

    lines.extend(
        [
            "",
            "## Response-State Surfaces",
            "",
            f"RDLLM normalizes {sum(len(v) for v in data['response_state_groups'].values())} response-state surfaces before source-footer reliance:",
            "",
            "| Surface group | Required surfaces |",
            "| --- | --- |",
        ]
    )
    for group, values in data["response_state_groups"].items():
        lines.append(f"| {group} | {_code_join(tuple(values))} |")

    lines.extend(
        [
            "",
            "## Compatibility Rule",
            "",
            "Compatibility is not a vendor-name assertion. A route is compatible only when:",
            "",
            "- its provider family is present in the binding matrix",
            "- its model and route are admitted by the model/provider registry",
            "- its native annotations normalize into verified source-footer rows",
            "- every displayed source row passes claim-evidence verification",
            "- its native usage meters normalize into RDLLM settlement meters",
            "- its native terminal state normalizes into `complete_supported`",
            "- blocked, filtered, refused, truncated, tool-only, errored, unknown, or unsafe",
            "  states block grounded display and creator settlement",
            "",
            "The reference artifacts currently report:",
            "",
            "- `artifacts/certification_report.json`: "
            f"{data['artifact_summaries']['certification_report'].get('status')} at "
            f"{data['artifact_summaries']['certification_report'].get('highest_level')}",
            "- `artifacts/universal_foundation_provider_binding_matrix.json`: "
            f"{binding_summary.get('ready_provider_family_count')} ready provider families",
            "- `artifacts/universal_live_capability_discovery_contract.json`: "
            f"{discovery_summary.get('ready_provider_family_count')} ready live capability provider families",
            "- `artifacts/universal_provider_meter_normalization_contract.json`: "
            f"{meter_summary.get('ready_provider_meter_surface_count')} ready meter surfaces",
            "- `artifacts/universal_provider_response_state_normalization_contract.json`: "
            f"{state_summary.get('ready_provider_response_state_surface_count')} ready response-state surfaces",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write", action="store_true", help="Update docs/provider_compatibility_matrix.md")
    parser.add_argument("--check", action="store_true", help="Fail if generated Markdown differs from the checked-in file")
    args = parser.parse_args(argv)

    data = matrix_data()
    if args.format == "json":
        rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    else:
        rendered = render_markdown(data)

    if args.write:
        if args.format != "markdown":
            parser.error("--write only supports --format markdown")
        MATRIX_PATH.write_text(rendered, encoding="utf-8")
    elif args.check:
        if args.format != "markdown":
            parser.error("--check only supports --format markdown")
        current = MATRIX_PATH.read_text(encoding="utf-8")
        if current != rendered:
            print(
                "docs/provider_compatibility_matrix.md is out of date; run "
                "PYTHONPATH=src python tools/provider_matrix.py --write",
                file=sys.stderr,
            )
            return 1
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
