"""Canonical provider-family names and legacy aliases.

RDLLM has several historical certification layers. Older layers used compact
vendor labels such as ``openai`` or ``vertex_ai`` while current provider-facing
contracts use capability-specific family names such as ``openai_responses`` and
``google_vertex_ai``. This registry keeps those names interoperable and gives
shipping checks one source of truth for the current provider taxonomy.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

CANONICAL_PROVIDER_FAMILIES = (
    "openai_responses",
    "anthropic_messages",
    "google_gemini_generate_content",
    "google_vertex_ai",
    "meta_llama_stack",
    "mistral_chat",
    "cohere_chat",
    "xai_grok",
    "deepseek_chat",
    "azure_openai",
    "aws_bedrock",
    "openrouter_compatible",
    "local_open_weight_runtime",
    "enterprise_gateway_proxy",
    "rag_native_provider",
    "mcp_agent_tool_runtime",
)

_CANONICAL_SET = set(CANONICAL_PROVIDER_FAMILIES)

PROVIDER_FAMILY_ALIASES = {
    **{family: family for family in CANONICAL_PROVIDER_FAMILIES},
    "openai": "openai_responses",
    "openai_responses_api": "openai_responses",
    "openai_compatible_chat": "openrouter_compatible",
    "chat_completions_compatible": "openrouter_compatible",
    "anthropic": "anthropic_messages",
    "anthropic_messages_api": "anthropic_messages",
    "google_gemini": "google_gemini_generate_content",
    "google_gemini_vertex": "google_vertex_ai",
    "vertex_ai": "google_vertex_ai",
    "meta": "meta_llama_stack",
    "meta_llama": "meta_llama_stack",
    "meta_llama_open_weights": "meta_llama_stack",
    "mistral": "mistral_chat",
    "mistral_api": "mistral_chat",
    "cohere": "cohere_chat",
    "cohere_command": "cohere_chat",
    "xai": "xai_grok",
    "deepseek": "deepseek_chat",
    "deepseek_api": "deepseek_chat",
    "azure_openai_responses": "azure_openai",
    "amazon_bedrock_converse": "aws_bedrock",
    "aws_bedrock_converse": "aws_bedrock",
    "bedrock": "aws_bedrock",
    "groq": "openrouter_compatible",
    "groq_chat": "openrouter_compatible",
    "groq_openai": "openrouter_compatible",
    "perplexity": "rag_native_provider",
    "perplexity_sonar": "rag_native_provider",
    "sonar_api": "rag_native_provider",
    "together": "openrouter_compatible",
    "together_ai": "openrouter_compatible",
    "together_openai": "openrouter_compatible",
    "fireworks": "openrouter_compatible",
    "fireworks_ai": "openrouter_compatible",
    "fireworks_openai": "openrouter_compatible",
    "cerebras": "openrouter_compatible",
    "cerebras_inference": "openrouter_compatible",
    "cerebras_openai": "openrouter_compatible",
    "huggingface": "openrouter_compatible",
    "hugging_face": "openrouter_compatible",
    "huggingface_inference": "openrouter_compatible",
    "huggingface_inference_providers": "openrouter_compatible",
    "hf_inference_providers": "openrouter_compatible",
    "hf_router": "openrouter_compatible",
    "litellm": "enterprise_gateway_proxy",
    "litellm_proxy": "enterprise_gateway_proxy",
    "ai_gateway": "enterprise_gateway_proxy",
    "openai_compatible_gateway": "enterprise_gateway_proxy",
    "replicate": "enterprise_gateway_proxy",
    "replicate_predictions": "enterprise_gateway_proxy",
    "model_marketplace": "enterprise_gateway_proxy",
    "serverless_model_marketplace": "enterprise_gateway_proxy",
    "local_open_weights": "local_open_weight_runtime",
    "local_runtime": "local_open_weight_runtime",
    "ollama": "local_open_weight_runtime",
    "ollama_openai": "local_open_weight_runtime",
    "lm_studio": "local_open_weight_runtime",
    "llama_cpp": "local_open_weight_runtime",
    "llamacpp": "local_open_weight_runtime",
    "vllm": "local_open_weight_runtime",
    "vllm_openai": "local_open_weight_runtime",
    "sglang": "local_open_weight_runtime",
    "tgi": "local_open_weight_runtime",
    "text_generation_inference": "local_open_weight_runtime",
    "enterprise_gateway": "enterprise_gateway_proxy",
    "enterprise_private_model": "enterprise_gateway_proxy",
    "router_gateway": "openrouter_compatible",
    "rag_native": "rag_native_provider",
    "mcp_tool_runtime": "mcp_agent_tool_runtime",
    "agent_tool_runtime": "mcp_agent_tool_runtime",
}


def canonical_provider_family(value: Any) -> str:
    """Return the current canonical provider family for a raw provider label."""

    return PROVIDER_FAMILY_ALIASES.get(str(value), "")


def canonical_provider_families(values: Iterable[Any]) -> tuple[str, ...]:
    """Normalize a sequence of provider-family labels and preserve canonical order."""

    normalized = {canonical_provider_family(value) for value in values}
    return tuple(family for family in CANONICAL_PROVIDER_FAMILIES if family in normalized)


def unmapped_provider_families(values: Iterable[Any]) -> tuple[str, ...]:
    """Return raw labels that do not resolve to a canonical provider family."""

    return tuple(sorted({str(value) for value in values if not canonical_provider_family(value)}))


def provider_family_coverage(values: Iterable[Any]) -> dict[str, Any]:
    """Summarize canonical coverage for a provider-family collection."""

    raw_values = tuple(str(value) for value in values)
    normalized = canonical_provider_families(raw_values)
    normalized_set = set(normalized)
    return {
        "raw_provider_families": list(raw_values),
        "raw_provider_family_count": len(raw_values),
        "canonical_provider_families": list(normalized),
        "canonical_provider_family_count": len(normalized),
        "unmapped_provider_families": list(unmapped_provider_families(raw_values)),
        "missing_canonical_provider_families": [
            family
            for family in CANONICAL_PROVIDER_FAMILIES
            if family not in normalized_set
        ],
        "canonical_provider_taxonomy_complete": normalized
        == CANONICAL_PROVIDER_FAMILIES,
    }
