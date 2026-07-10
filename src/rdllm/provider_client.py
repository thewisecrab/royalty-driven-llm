"""Provider clients used by the RDLLM service boundary."""

from __future__ import annotations

import json
import os
import re
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
    require_grounding_evidence: bool = True

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
            require_grounding_evidence=bool(
                data.get("require_grounding_evidence", True)
            ),
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
    provider_request_hash: str = ""
    response_id: str = ""
    system_fingerprint: str = ""
    evidence_mode: str = "unverified_post_hoc"
    evidence_verified: bool = False
    grounding_context_hash: str = ""
    grounding_source_ids: tuple[str, ...] = ()
    source_annotations: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "family": self.family,
            "model": self.model,
            "output": self.output,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "provider_response_hash": self.provider_response_hash,
            "provider_request_hash": self.provider_request_hash,
            "response_id": self.response_id,
            "system_fingerprint": self.system_fingerprint,
            "evidence_mode": self.evidence_mode,
            "evidence_verified": self.evidence_verified,
            "grounding_context_hash": self.grounding_context_hash,
            "grounding_source_ids": list(self.grounding_source_ids),
            "source_annotations": list(self.source_annotations),
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


SOURCE_MARKER_PATTERN = re.compile(r"\[S([1-9][0-9]*)\]", re.IGNORECASE)


def _provider_annotations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    choices = payload.get("choices", [])
    first = choices[0] if isinstance(choices, list) and choices else {}
    message = first.get("message", {}) if isinstance(first, dict) else {}
    candidates: list[Any] = []
    for container in (message, first, payload):
        if not isinstance(container, dict):
            continue
        for key in ("annotations", "citations", "sources"):
            value = container.get(key)
            if isinstance(value, list):
                candidates.extend(value)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        citation = item.get("url_citation", item)
        if not isinstance(citation, dict):
            continue
        source_id = str(
            citation.get("source_id")
            or citation.get("label")
            or citation.get("id")
            or ""
        ).strip()
        if source_id and source_id.isdigit():
            source_id = f"S{source_id}"
        row = {
            "annotation_id": str(item.get("id") or f"annotation:{index}"),
            "type": str(item.get("type") or citation.get("type") or "citation"),
            "source_id": source_id.upper(),
            "title": str(citation.get("title") or citation.get("name") or ""),
            "url": str(citation.get("url") or citation.get("uri") or ""),
            "start_index": citation.get("start_index"),
            "end_index": citation.get("end_index"),
            "origin": "provider_native",
        }
        rows.append(row)
    return rows


def _grounding_messages(
    messages: list[dict[str, Any]],
    grounding_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not grounding_manifest:
        return list(messages)
    source_rows = grounding_manifest.get("source_rows", [])
    blocks = []
    for row in source_rows if isinstance(source_rows, list) else []:
        if not isinstance(row, dict):
            continue
        blocks.append(
            "\n".join(
                (
                    f"SOURCE {row.get('source_id', '')}",
                    f"title: {row.get('title', '')}",
                    f"uri: {row.get('source_uri', '')}",
                    f"content_hash: {row.get('content_hash', '')}",
                    f"text: {row.get('text', '')}",
                )
            )
        )
    instruction = (
        "RDLLM grounded-generation policy: answer only from the source blocks "
        "below. Cite each factual claim with its source marker such as [S1]. "
        "Do not invent a marker or claim that a source says more than its text. "
        "If the sources are insufficient, say that the evidence is insufficient.\n\n"
        + "\n\n".join(blocks)
    )
    return [{"role": "system", "content": instruction}, *messages]


def _normalized_evidence(
    payload: dict[str, Any],
    output: str,
    grounding_manifest: dict[str, Any] | None,
) -> tuple[str, bool, tuple[str, ...], tuple[dict[str, Any], ...]]:
    source_rows = (
        grounding_manifest.get("source_rows", [])
        if isinstance(grounding_manifest, dict)
        else []
    )
    valid_ids = {
        str(row.get("source_id", "")).upper()
        for row in source_rows
        if isinstance(row, dict) and row.get("source_id")
    }
    native = _provider_annotations(payload)
    marker_ids = tuple(
        sorted({f"S{match}" for match in SOURCE_MARKER_PATTERN.findall(output)})
    )
    rows = list(native)
    native_ids = {str(row.get("source_id", "")).upper() for row in native}
    for source_id in marker_ids:
        if source_id not in native_ids:
            rows.append(
                {
                    "annotation_id": f"context-marker:{source_id}",
                    "type": "source_marker",
                    "source_id": source_id,
                    "title": "",
                    "url": "",
                    "start_index": None,
                    "end_index": None,
                    "origin": "rdllm_context_marker",
                }
            )
    cited_ids = {str(row.get("source_id", "")).upper() for row in rows if row.get("source_id")}
    evidence_verified = bool(valid_ids and cited_ids and cited_ids.issubset(valid_ids))
    if evidence_verified and native:
        mode = "provider_native_annotations"
    elif evidence_verified:
        mode = "provider_context_grounded"
    else:
        mode = "unverified_post_hoc"
    return mode, evidence_verified, marker_ids, tuple(rows)


def call_openai_compatible_chat(
    route: ProviderRoute,
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    grounding_manifest: dict[str, Any] | None = None,
) -> ProviderGeneration:
    if route.family != "openai_compatible_chat":
        raise ProviderClientError(f"unsupported provider family: {route.family}")
    api_key = route.api_key()
    if not api_key:
        raise ProviderClientError(f"provider API key env is unset: {route.api_key_env}")
    selected_model = model or route.model
    if not selected_model:
        raise ProviderClientError("provider model is required")
    grounded_messages = _grounding_messages(messages, grounding_manifest)
    body = {
        "model": selected_model,
        "messages": grounded_messages,
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
    evidence_mode, evidence_verified, marker_ids, annotations = _normalized_evidence(
        payload,
        output,
        grounding_manifest,
    )
    if route.require_grounding_evidence and not evidence_verified:
        raise ProviderClientError(
            "provider output did not bind any supplied source identifier; "
            "include markers such as [S1] or provider-native source annotations"
        )
    usage = payload.get("usage", {})
    return ProviderGeneration(
        provider_id=route.provider_id,
        family=route.family,
        model=str(payload.get("model", selected_model)),
        output=output,
        usage=usage if isinstance(usage, dict) else {},
        finish_reason=finish_reason,
        provider_response_hash=canonical_hash(payload),
        provider_request_hash=canonical_hash(body),
        response_id=str(payload.get("id", "")),
        system_fingerprint=str(payload.get("system_fingerprint", "")),
        evidence_mode=evidence_mode,
        evidence_verified=evidence_verified,
        grounding_context_hash=(
            canonical_hash(grounding_manifest) if grounding_manifest else ""
        ),
        grounding_source_ids=marker_ids,
        source_annotations=annotations,
    )
