"""Provider clients used by the RDLLM service boundary."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderClientError(RuntimeError):
    """Raised when an upstream provider call cannot be safely attributed."""


@dataclass(frozen=True)
class ProviderRoute:
    provider_id: str
    family: str
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: float = 30.0
    max_response_bytes: int = 1_000_000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderRoute":
        return cls(
            provider_id=str(data["provider_id"]),
            family=str(data.get("family", "openai_compatible_chat")),
            base_url=str(data["base_url"]).rstrip("/"),
            model=str(data["model"]),
            api_key_env=str(data["api_key_env"]),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
            max_response_bytes=int(data.get("max_response_bytes", 1_000_000)),
        )

    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "").strip()


@dataclass(frozen=True)
class ProviderGeneration:
    provider_id: str
    family: str
    model: str
    output: str
    usage: dict[str, Any]
    finish_reason: str
    provider_response_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "family": self.family,
            "model": self.model,
            "output": self.output,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "provider_response_hash": self.provider_response_hash,
        }


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    import hashlib

    return hashlib.sha256(encoded).hexdigest()


def _read_limited(response: Any, limit: int) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise ProviderClientError("provider response exceeded configured byte limit")
    return body


def _extract_openai_compatible_output(payload: dict[str, Any]) -> tuple[str, str]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderClientError("provider response did not include choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderClientError("provider choice is not an object")
    message = first.get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        text_parts = [
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        ]
        content = "".join(text_parts)
    if not isinstance(content, str) or not content.strip():
        raise ProviderClientError("provider response did not include text content")
    finish_reason = str(first.get("finish_reason", ""))
    if finish_reason in {"content_filter", "tool_calls"}:
        raise ProviderClientError(f"provider finish_reason blocks attribution: {finish_reason}")
    return content, finish_reason


def call_openai_compatible_chat(
    route: ProviderRoute,
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
) -> ProviderGeneration:
    if route.family != "openai_compatible_chat":
        raise ProviderClientError(f"unsupported provider family: {route.family}")
    api_key = route.api_key()
    if not api_key:
        raise ProviderClientError(f"provider API key env is unset: {route.api_key_env}")
    selected_model = model or route.model
    if not selected_model:
        raise ProviderClientError("provider model is required")
    body = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{route.base_url}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=route.timeout_seconds) as response:
            payload = json.loads(_read_limited(response, route.max_response_bytes))
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise ProviderClientError(
            f"provider returned HTTP {exc.code}: {detail}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderClientError(f"provider request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderClientError("provider response must be a JSON object")
    output, finish_reason = _extract_openai_compatible_output(payload)
    usage = payload.get("usage", {})
    return ProviderGeneration(
        provider_id=route.provider_id,
        family=route.family,
        model=str(payload.get("model", selected_model)),
        output=output,
        usage=usage if isinstance(usage, dict) else {},
        finish_reason=finish_reason,
        provider_response_hash=canonical_hash(payload),
    )
