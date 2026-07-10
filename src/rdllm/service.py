"""Minimal production service boundary for RDLLM."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Lock
from typing import Any, Callable, Iterable
from urllib.parse import urlparse
from wsgiref.simple_server import WSGIServer, make_server

from rdllm.answer_citations import (
    claim_citation_keys,
    model_reliance_claim_markers,
    source_citation_keys,
    unresolved_answer_link_uris,
    unresolved_answer_citation_markers,
)
from rdllm.claim_warrant import claim_warrant_report
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.provider_client import (
    ProviderClientError,
    ProviderRoute,
    call_openai_compatible_chat,
)
from rdllm.source_disagreement import claim_source_disagreement_report
from rdllm.source_footer_rendering import render_source_footer_text
from rdllm.source_usage_metrics import source_usage_metric_row_fields
from rdllm.text import stable_hash


ROOT = Path(__file__).resolve().parents[2]
CONFIG_SCHEMA = "rdllm-service-config/v1"
RESPONSE_SCHEMA = "rdllm-service-attribution-response/v1"
DISPLAY_SCHEMA = "rdllm-service-display/v1"
READY_SCHEMA = "rdllm-service-readiness/v1"
METRICS_SCHEMA = "rdllm-service-metrics/v1"
OPENAPI_SCHEMA = "rdllm-service-openapi/v1"
DISPLAY_READY_GROUNDING_VERDICTS = {"verified"}

StartResponse = Callable[[str, list[tuple[str, str]]], None]


class AuditLogError(RuntimeError):
    """Raised when the service cannot preserve a verifiable audit trail."""


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class ServiceConfig:
    raw: dict[str, Any]
    root: Path = ROOT

    @property
    def host(self) -> str:
        return str(self.raw.get("host", "127.0.0.1"))

    @property
    def port(self) -> int:
        return int(self.raw.get("port", 8765))

    @property
    def max_request_bytes(self) -> int:
        limits = self.raw.get("limits", {})
        return int(limits.get("max_request_bytes", 65536))

    @property
    def max_prompt_chars(self) -> int:
        limits = self.raw.get("limits", {})
        return int(limits.get("max_prompt_chars", 4000))

    @property
    def max_output_chars(self) -> int:
        limits = self.raw.get("limits", {})
        return int(limits.get("max_output_chars", 16000))

    @property
    def rate_limit_requests_per_window(self) -> int:
        limits = self.raw.get("limits", {})
        return int(limits.get("rate_limit_requests_per_window", 120))

    @property
    def rate_limit_window_seconds(self) -> int:
        limits = self.raw.get("limits", {})
        return int(limits.get("rate_limit_window_seconds", 60))

    @property
    def default_gross_revenue(self) -> Decimal:
        return Decimal(str(self.raw.get("default_gross_revenue", "1.00")))

    @property
    def audit_log_path(self) -> Path | None:
        return resolve_path(self.root, self.raw.get("audit_log_path"))

    def artifact_path(self, name: str) -> Path | None:
        artifacts = self.raw.get("artifacts", {})
        value = artifacts.get(name) if isinstance(artifacts, dict) else None
        return resolve_path(self.root, value)

    def corpus_path(self) -> Path:
        value = str(self.raw.get("corpus", "examples/sample_corpus.json"))
        path = resolve_path(self.root, value)
        if path is None:
            raise ValueError("corpus path is required")
        return path

    def auth_mode(self) -> str:
        auth = self.raw.get("auth", {})
        return str(auth.get("mode", "shared_token_sha256"))

    def configured_token_hash(self) -> str:
        auth = self.raw.get("auth", {})
        if not isinstance(auth, dict):
            return ""
        env_name = str(auth.get("token_sha256_env", "")).strip()
        if env_name:
            env_value = os.environ.get(env_name, "").strip()
            if env_value:
                return env_value
        return str(auth.get("token_sha256", "")).strip()

    def provider_routes(self) -> dict[str, ProviderRoute]:
        routes: dict[str, ProviderRoute] = {}
        for row in self.raw.get("providers", []) or []:
            if isinstance(row, dict):
                route = ProviderRoute.from_dict(row)
                routes[route.provider_id] = route
        return routes


@dataclass
class ServiceState:
    config: ServiceConfig
    engine: RoyaltyDrivenLLM
    started_at: float = field(default_factory=time.time)
    requests_total: int = 0
    attribution_requests_total: int = 0
    blocked_requests_total: int = 0
    audit_errors_total: int = 0
    provider_requests_total: int = 0
    rate_limited_requests_total: int = 0
    lock: Lock = field(default_factory=Lock)
    rate_limit_events: dict[str, list[float]] = field(default_factory=dict)
    provider_routes: dict[str, ProviderRoute] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: ServiceConfig) -> "ServiceState":
        engine = RoyaltyDrivenLLM.from_corpus_file(
            config.corpus_path(),
            creator_pool_rate=Decimal(str(config.raw.get("creator_pool_rate", "0.55"))),
            top_k=int(config.raw.get("top_k", 3)),
            jurisdiction=str(config.raw.get("jurisdiction", "GLOBAL")),
            enforce_registry=bool(config.raw.get("enforce_registry", False)),
        )
        return cls(
            config=config,
            engine=engine,
            provider_routes=config.provider_routes(),
        )


def load_service_config(path: str | Path) -> ServiceConfig:
    raw = load_json(path)
    return ServiceConfig(raw=raw)


def security_headers(content_type: str = "application/json") -> list[tuple[str, str]]:
    return [
        ("Content-Type", content_type),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
        ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    ]


def json_response(
    start_response: StartResponse,
    status: str,
    payload: dict[str, Any],
    request_id: str,
) -> Iterable[bytes]:
    headers = security_headers()
    headers.append(("X-RDLLM-Request-Id", request_id))
    start_response(status, headers)
    return [json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")]


def text_response(
    start_response: StartResponse,
    status: str,
    body: str,
    request_id: str,
    content_type: str = "text/plain; version=0.0.4; charset=utf-8",
) -> Iterable[bytes]:
    headers = security_headers(content_type)
    headers.append(("X-RDLLM-Request-Id", request_id))
    start_response(status, headers)
    return [body.encode("utf-8")]


def status_line(status_code: int) -> str:
    reasons = {
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        413: "Payload Too Large",
        422: "Unprocessable Entity",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }
    return f"{status_code} {reasons.get(status_code, 'Error')}"


def increment(state: ServiceState, field_name: str, amount: int = 1) -> None:
    with state.lock:
        setattr(state, field_name, getattr(state, field_name) + amount)


def _read_request_body(environ: dict[str, Any], limit: int) -> tuple[dict[str, Any], str]:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        return {}, "invalid Content-Length"
    if content_length <= 0:
        return {}, "request body is required"
    if content_length > limit:
        return {}, f"request body exceeds limit of {limit} bytes"
    body = environ["wsgi.input"].read(content_length)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f"invalid JSON body: {exc}"
    if not isinstance(payload, dict):
        return {}, "JSON body must be an object"
    return payload, ""


def _authorize(state: ServiceState, environ: dict[str, Any]) -> bool:
    mode = state.config.auth_mode()
    if mode == "disabled":
        return True
    if mode != "shared_token_sha256":
        return False
    expected_hash = state.config.configured_token_hash()
    if not expected_hash:
        return False
    header = str(environ.get("HTTP_AUTHORIZATION", ""))
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    provided_hash = token_hash(header.removeprefix(prefix).strip())
    return hmac.compare_digest(provided_hash, expected_hash)


def _client_identity(environ: dict[str, Any]) -> str:
    header = str(environ.get("HTTP_AUTHORIZATION", ""))
    if header.startswith("Bearer "):
        return f"bearer:{token_hash(header.removeprefix('Bearer ').strip())}"
    return f"remote:{environ.get('REMOTE_ADDR', 'unknown')}"


def _rate_limit(state: ServiceState, environ: dict[str, Any]) -> tuple[bool, int]:
    maximum = state.config.rate_limit_requests_per_window
    window = state.config.rate_limit_window_seconds
    if maximum <= 0 or window <= 0:
        return False, max(1, window)
    now = time.time()
    cutoff = now - window
    identity = _client_identity(environ)
    with state.lock:
        events = [
            timestamp
            for timestamp in state.rate_limit_events.get(identity, [])
            if timestamp >= cutoff
        ]
        if len(events) >= maximum:
            retry_after = max(1, int(window - (now - events[0])))
            state.rate_limit_events[identity] = events
            return False, retry_after
        events.append(now)
        state.rate_limit_events[identity] = events
    return True, 0


def _rate_limit_response(
    state: ServiceState,
    start_response: StartResponse,
    request_id: str,
    retry_after: int,
) -> Iterable[bytes]:
    increment(state, "blocked_requests_total")
    increment(state, "rate_limited_requests_total")
    headers = security_headers()
    headers.append(("X-RDLLM-Request-Id", request_id))
    headers.append(("Retry-After", str(retry_after)))
    start_response("429 Too Many Requests", headers)
    payload = {
        "status": "blocked",
        "error": "rate limit exceeded",
        "retry_after_seconds": retry_after,
    }
    return [json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")]


def _artifact_ready(path: Path | None, checks: list[dict[str, Any]], name: str) -> None:
    if path is None:
        checks.append({"name": name, "status": "blocked", "reason": "path missing"})
        return
    if not path.is_file():
        checks.append(
            {"name": name, "status": "blocked", "reason": f"missing {path}"}
        )
        return
    try:
        payload = load_json(path)
    except json.JSONDecodeError as exc:
        checks.append({"name": name, "status": "blocked", "reason": str(exc)})
        return
    summary = payload.get("summary", {})
    status = summary.get("status")
    if name == "certification_report":
        status = "ready" if summary.get("status") == "passed" else summary.get("status")
    if name == "provider_attribution_card":
        certification = payload.get("certification", {})
        status = (
            "ready"
            if certification.get("status") == "passed"
            and certification.get("highest_level") == "RDLLM-L186"
            else certification.get("status")
        )
    if status != "ready":
        checks.append(
            {"name": name, "status": "blocked", "reason": f"status is {status!r}"}
        )
        return
    checks.append(
        {
            "name": name,
            "status": "ready",
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "hash": canonical_hash(payload),
        }
    )


def _provider_route_check(provider_id: str, route: ProviderRoute) -> dict[str, Any]:
    reason = ""
    parsed_base_url = urlparse(route.base_url)
    placeholder_model = route.model.startswith("replace-with-")
    placeholder_base_url = parsed_base_url.hostname in {
        "provider.example",
        "example.com",
    } or str(parsed_base_url.hostname or "").endswith(".example")
    if not route.api_key():
        reason = f"API key env is unset: {route.api_key_env}"
    elif placeholder_model:
        reason = f"provider model is still a placeholder: {route.model}"
    elif placeholder_base_url:
        reason = f"provider base_url is still a placeholder: {route.base_url}"
    return {
        "name": f"provider_route:{provider_id}",
        "status": "blocked" if reason else "ready",
        "reason": reason,
        "family": route.family,
        "model": route.model,
        "base_url": route.base_url,
        "api_key_env": route.api_key_env,
    }


def _audit_log_chain_state(path: Path) -> tuple[str, list[str]]:
    errors: list[str] = []
    previous_hash = ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return "", [f"audit log failed to read: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: expected object")
            continue
        required = {
            "schema",
            "request_id",
            "timestamp",
            "status",
            "event_id",
            "event_hash",
            "source_footer_hash",
            "display_hash",
            "source_count",
            "audit_error_count",
            "previous_entry_hash",
            "entry_hash",
        }
        for field in sorted(required - set(row)):
            errors.append(f"line {line_number}.{field}: missing required field")
        if row.get("previous_entry_hash") != previous_hash:
            errors.append(f"line {line_number}.previous_entry_hash: chain mismatch")
        entry_hash = row.get("entry_hash")
        expected_entry_hash = canonical_hash(
            {key: value for key, value in row.items() if key != "entry_hash"}
        )
        if not isinstance(entry_hash, str) or entry_hash != expected_entry_hash:
            errors.append(f"line {line_number}.entry_hash: mismatch")
        if row.get("status") == "ready" and not row.get("source_footer_hash"):
            errors.append(
                f"line {line_number}.source_footer_hash: "
                "ready entry must bind a source footer"
            )
        if row.get("status") == "ready" and not row.get("display_hash"):
            errors.append(
                f"line {line_number}.display_hash: ready entry must bind a display"
            )
        previous_hash = str(entry_hash or "")
    return previous_hash, errors


def _audit_log_integrity_error(path: Path) -> str:
    _previous_hash, errors = _audit_log_chain_state(path)
    if not errors:
        return ""
    preview = "; ".join(errors[:3])
    if len(errors) > 3:
        preview = f"{preview}; +{len(errors) - 3} more"
    return f"audit log integrity failed: {preview}"


def _audit_log_check(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "name": "audit_log_writable",
            "status": "blocked",
            "reason": "audit log path is not configured",
            "path": "",
        }
    try:
        if path.exists():
            if not path.is_file():
                raise OSError("audit log path is not a file")
            with path.open("a", encoding="utf-8"):
                pass
            integrity_error = _audit_log_integrity_error(path)
            if integrity_error:
                raise AuditLogError(integrity_error)
        else:
            created_parent = not path.parent.exists()
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with tempfile.NamedTemporaryFile(
                    dir=path.parent,
                    prefix=".rdllm-audit-write-",
                    delete=True,
                ):
                    pass
            finally:
                if created_parent:
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass
    except AuditLogError as exc:
        return {
            "name": "audit_log_writable",
            "status": "blocked",
            "reason": f"audit log is not usable: {exc}",
            "path": str(path),
        }
    except OSError as exc:
        return {
            "name": "audit_log_writable",
            "status": "blocked",
            "reason": f"audit log is not writable: {exc}",
            "path": str(path),
        }
    return {
        "name": "audit_log_writable",
        "status": "ready",
        "path": str(path),
    }


def readiness_report(state: ServiceState) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "service_config_schema",
            "status": "ready"
            if state.config.raw.get("schema") == CONFIG_SCHEMA
            else "blocked",
            "expected": CONFIG_SCHEMA,
            "actual": state.config.raw.get("schema"),
        }
    )
    checks.append(
        {
            "name": "auth_token_hash",
            "status": "ready" if state.config.configured_token_hash() else "blocked",
            "mode": state.config.auth_mode(),
        }
    )
    checks.append(
        {
            "name": "engine_loaded",
            "status": "ready" if state.engine.chunks else "blocked",
            "chunk_count": len(state.engine.chunks),
        }
    )
    checks.append(
        {
            "name": "rate_limit_configured",
            "status": "ready"
            if state.config.rate_limit_requests_per_window > 0
            and state.config.rate_limit_window_seconds > 0
            else "blocked",
            "requests_per_window": state.config.rate_limit_requests_per_window,
            "window_seconds": state.config.rate_limit_window_seconds,
        }
    )
    checks.append(_audit_log_check(state.config.audit_log_path))
    for name in (
        "certification_report",
        "discovery_manifest",
        "provider_attribution_card",
        "production_readiness_report",
        "universal_production_invocation_admission",
        "universal_runtime_conformance_receipt",
        "universal_source_grounded_response_receipt",
    ):
        _artifact_ready(state.config.artifact_path(name), checks, name)
    for provider_id, route in sorted(state.provider_routes.items()):
        checks.append(_provider_route_check(provider_id, route))
    blocked = [row for row in checks if row["status"] != "ready"]
    return {
        "schema": READY_SCHEMA,
        "status": "ready" if not blocked else "blocked",
        "service": "rdllm",
        "checks": checks,
        "blocked_check_count": len(blocked),
        "ready_check_count": len(checks) - len(blocked),
        "uptime_seconds": round(time.time() - state.started_at, 3),
    }


def metrics_report(state: ServiceState) -> dict[str, Any]:
    ready = readiness_report(state)
    return {
        "schema": METRICS_SCHEMA,
        "service": "rdllm",
        "ready_status": ready["status"],
        "uptime_seconds": ready["uptime_seconds"],
        "requests_total": state.requests_total,
        "attribution_requests_total": state.attribution_requests_total,
        "blocked_requests_total": state.blocked_requests_total,
        "audit_errors_total": state.audit_errors_total,
        "provider_requests_total": state.provider_requests_total,
        "provider_route_count": len(state.provider_routes),
        "rate_limited_requests_total": state.rate_limited_requests_total,
    }


def prometheus_metrics(state: ServiceState) -> str:
    metrics = metrics_report(state)
    ready = 1 if metrics["ready_status"] == "ready" else 0
    rows = [
        "# HELP rdllm_service_ready RDLLM service readiness state.",
        "# TYPE rdllm_service_ready gauge",
        f"rdllm_service_ready {ready}",
        "# HELP rdllm_service_uptime_seconds RDLLM service uptime in seconds.",
        "# TYPE rdllm_service_uptime_seconds gauge",
        f"rdllm_service_uptime_seconds {metrics['uptime_seconds']}",
        "# HELP rdllm_service_requests_total Total HTTP requests.",
        "# TYPE rdllm_service_requests_total counter",
        f"rdllm_service_requests_total {metrics['requests_total']}",
        "# HELP rdllm_service_attribution_requests_total Total attribution requests.",
        "# TYPE rdllm_service_attribution_requests_total counter",
        (
            "rdllm_service_attribution_requests_total "
            f"{metrics['attribution_requests_total']}"
        ),
        "# HELP rdllm_service_blocked_requests_total Total blocked requests.",
        "# TYPE rdllm_service_blocked_requests_total counter",
        f"rdllm_service_blocked_requests_total {metrics['blocked_requests_total']}",
        "# HELP rdllm_service_audit_errors_total Total attribution audit errors.",
        "# TYPE rdllm_service_audit_errors_total counter",
        f"rdllm_service_audit_errors_total {metrics['audit_errors_total']}",
        "# HELP rdllm_service_provider_requests_total Total provider-backed attribution requests.",
        "# TYPE rdllm_service_provider_requests_total counter",
        f"rdllm_service_provider_requests_total {metrics['provider_requests_total']}",
        "# HELP rdllm_service_provider_route_count Configured provider routes.",
        "# TYPE rdllm_service_provider_route_count gauge",
        f"rdllm_service_provider_route_count {metrics['provider_route_count']}",
        "# HELP rdllm_service_rate_limited_requests_total Total rate-limited requests.",
        "# TYPE rdllm_service_rate_limited_requests_total counter",
        f"rdllm_service_rate_limited_requests_total {metrics['rate_limited_requests_total']}",
    ]
    return "\n".join(rows) + "\n"


def _source_verification_handle(
    *, event_id: str, label: str, content_hash: str
) -> str:
    return f"rdllm://verify/source-footer/{event_id}/{label}/{content_hash[:12]}"


def _source_footer_for_event(event: Any) -> dict[str, Any]:
    supported_counts: dict[str, int] = {}
    minimum_support_by_label: dict[str, float] = {}
    for support in event.claim_support:
        if not support.supported or not support.source_label:
            continue
        supported_counts[support.source_label] = (
            supported_counts.get(support.source_label, 0) + 1
        )
        current = minimum_support_by_label.get(
            support.source_label,
            support.support_score,
        )
        minimum_support_by_label[support.source_label] = min(
            current,
            support.support_score,
        )

    source_rows: list[dict[str, Any]] = []
    settlement_eligible = event.settlement_decision.get(
        "eligible_for_settlement_instruction",
        False,
    ) is True
    for reference in event.source_references:
        supported_claims = supported_counts.get(reference.label, 0)
        minimum_support = minimum_support_by_label.get(reference.label, 0.0)
        confidence = (
            "verified"
            if supported_claims
            and minimum_support >= 0.75
            and reference.source_uri
            and reference.content_hash
            and reference.quote
            else "warning"
        )
        settlement_status = (
            "allocated_not_executed"
            if reference.payout > 0 and settlement_eligible
            else "candidate_held_for_review"
            if reference.payout > 0
            else "not_allocated"
        )
        why = (
            "verified_context_bound_claim_support_identity_rights_royalty"
            if confidence == "verified" and reference.payout > 0 and settlement_eligible
            else "post_hoc_candidate_needs_review"
            if confidence == "verified" and reference.payout > 0
            else "claim_support_needs_review"
        )
        row = {
            "label": reference.label,
            "display_label": f"[{reference.label}]",
            "title": reference.title,
            "creator_id": reference.creator_id,
            "creator_name": reference.creator_name,
            "work_id": reference.work_id,
            "chunk_id": reference.chunk_id,
            "source_uri": reference.source_uri,
            "license": reference.license,
            "license_uri": reference.license_uri,
            "content_hash": reference.content_hash,
            "content_hash_prefix": reference.content_hash[:12],
            "verification_handle": _source_verification_handle(
                event_id=event.event_id,
                label=reference.label,
                content_hash=reference.content_hash,
            ),
            "evidence_span_hashes": list(reference.evidence_span_hashes),
            "supported_claim_count": supported_claims,
            "minimum_support_score": round(minimum_support, 8),
            "confidence": confidence,
            "why": why,
            "settlement_status": settlement_status,
            "payout": str(reference.payout),
            "contribution_weight": str(reference.contribution_weight),
            "output_support": round(reference.output_support, 8),
            "text_match_score": round(reference.text_match_score, 8),
            "retrieval_score": round(reference.retrieval_score, 8),
            "citation_score": round(reference.citation_score, 8),
            "evidence_preview": reference.quote,
            **source_usage_metric_row_fields(),
        }
        row["row_hash"] = canonical_hash(row)
        source_rows.append(row)

    claim_rows: list[dict[str, Any]] = []
    for index, support in enumerate(event.claim_support, start=1):
        warrant_report = claim_warrant_report(
            claim=support.claim,
            evidence=support.evidence_text,
            supported=support.supported,
        )
        disagreement_report = claim_source_disagreement_report(
            claim=support.claim,
            source_label=support.source_label,
            source_rows=source_rows,
            supported=support.supported,
        )
        row = {
            "claim_index": index,
            "source_label": support.source_label,
            "claim_preview": support.claim,
            "claim_hash": stable_hash(support.claim),
            "claim_hash_prefix": stable_hash(support.claim)[:12],
            "support_score": round(support.support_score, 8),
            "supported": support.supported,
            "work_id": support.work_id,
            "chunk_id": support.chunk_id,
            "evidence_span_hash": support.evidence_span_hash,
            "evidence_span_hash_prefix": support.evidence_span_hash[:12],
            "evidence_start_char": support.evidence_start_char,
            "evidence_end_char": support.evidence_end_char,
            "evidence_preview": support.evidence_text,
            **warrant_report,
            **disagreement_report,
        }
        row["row_hash"] = canonical_hash(row)
        claim_rows.append(row)

    footer = {
        "schema": "rdllm-service-source-footer/v1",
        "status": event.grounding_quality.get("verdict", "unverified"),
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "source_count": len(source_rows),
        "claim_count": len(claim_rows),
        "source_rows": source_rows,
        "claim_rows": claim_rows,
        "rendered_text": render_source_footer_text(
            source_rows=source_rows,
            claim_rows=claim_rows,
            grounding_report=event.grounding_report,
        ),
        "public_verifier": {
            "event_hash": event.event_hash,
            "grounding_verdict": event.grounding_quality.get("verdict", ""),
            "attribution_gap_verdict": event.attribution_gap.get("verdict", ""),
            "generation_evidence_mode": event.generation_evidence.get("mode", ""),
            "settlement_status": event.settlement_decision.get("status", ""),
            "settlement_instruction_eligible": event.settlement_decision.get(
                "eligible_for_settlement_instruction",
                False,
            ),
        },
    }
    footer["footer_hash"] = canonical_hash(
        {key: value for key, value in footer.items() if key != "footer_hash"}
    )
    return footer


def _display_for_event(
    event: Any,
    source_footer: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    answer_text = str(getattr(event, "answer_text", "") or getattr(event, "output", ""))
    rendered_text = f"{answer_text.rstrip()}\n\n{source_footer['rendered_text']}"
    display = {
        "schema": DISPLAY_SCHEMA,
        "status": status,
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "answer_text_hash": canonical_hash(answer_text),
        "source_footer_hash": source_footer["footer_hash"],
        "render_policy": "answer_plus_verified_source_footer",
        "rendered_text": rendered_text,
    }
    display["rendered_text_hash"] = canonical_hash(rendered_text)
    return display


def _unresolved_answer_citation_markers(
    answer_text: str,
    source_footer: dict[str, Any],
) -> list[str]:
    source_labels = [
        str(row.get("label", ""))
        for row in source_footer.get("source_rows", [])
        if isinstance(row, dict)
    ]
    supported_claim_indexes = [
        row.get("claim_index")
        for row in source_footer.get("claim_rows", [])
        if isinstance(row, dict) and row.get("supported") is True
    ]
    allowed = source_citation_keys(source_labels) | claim_citation_keys(
        supported_claim_indexes
    )
    return unresolved_answer_citation_markers(answer_text, allowed)


def _unresolved_answer_link_uris(
    answer_text: str,
    source_footer: dict[str, Any],
) -> list[str]:
    source_uris = {
        str(row.get("source_uri", ""))
        for row in source_footer.get("source_rows", [])
        if isinstance(row, dict)
        and row.get("confidence") == "verified"
        and row.get("source_uri")
    }
    return unresolved_answer_link_uris(answer_text, source_uris)


def _display_gate_errors(event: Any, source_footer: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    verdict = str(event.grounding_quality.get("verdict", ""))
    if verdict not in DISPLAY_READY_GROUNDING_VERDICTS:
        errors.append(
            "grounding_quality: "
            f"verdict {verdict or '<missing>'} is not safe for production display"
        )
    answer_text = str(getattr(event, "answer_text", "") or getattr(event, "output", ""))
    unresolved_markers = _unresolved_answer_citation_markers(
        answer_text,
        source_footer,
    )
    if unresolved_markers:
        errors.append(
            "answer_citations: unresolved inline citation markers "
            f"{', '.join(unresolved_markers)}; markers must match verified "
            "source footer labels"
        )
    unresolved_links = _unresolved_answer_link_uris(answer_text, source_footer)
    if unresolved_links:
        errors.append(
            "answer_links: unverified answer source links "
            f"{', '.join(unresolved_links)}; links must match verified source "
            "footer URIs"
        )
    model_reliance_markers = model_reliance_claim_markers(answer_text)
    if model_reliance_markers:
        errors.append(
            "answer_model_reliance: unverified model-internal reliance claims "
            f"{', '.join(model_reliance_markers)}; service answers may claim "
            "observable support and allocation only"
        )
    settlement = event.settlement_decision
    if settlement.get("direct_execution_allowed") is not False:
        errors.append(
            "settlement: direct payment execution must remain disabled until an "
            "external processor attestation is verified"
        )
    generation_evidence = event.generation_evidence
    if (
        generation_evidence.get("mode") == "provider_context_grounded"
        and generation_evidence.get("provider_evidence_verified") is not True
    ):
        errors.append(
            "provider_evidence: provider output is not bound to supplied source context"
        )
    return errors


def openapi_document() -> dict[str, Any]:
    return {
        "schema": OPENAPI_SCHEMA,
        "openapi": "3.1.0",
        "info": {
            "title": "RDLLM Service API",
            "version": "1.0.0",
        },
        "paths": {
            "/healthz": {"get": {"summary": "Liveness check"}},
            "/readyz": {"get": {"summary": "Readiness and proof artifact check"}},
            "/v1/attribute": {
                "post": {
                    "summary": "Generate or attribute an answer with RDLLM proofs",
                    "security": [{"bearerAuth": []}],
                }
            },
            "/v1/provider/attribute": {
                "post": {
                    "summary": "Call an allowed provider, then attribute the generated answer",
                    "security": [{"bearerAuth": []}],
                }
            },
            "/v1/metrics": {
                "get": {
                    "summary": "JSON service counters",
                    "security": [{"bearerAuth": []}],
                }
            },
            "/v1/metrics/prometheus": {
                "get": {
                    "summary": "Prometheus text service counters",
                    "security": [{"bearerAuth": []}],
                }
            },
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
    }


def _append_audit_log(
    state: ServiceState,
    request_id: str,
    status: str,
    event_payload: dict[str, Any] | None,
    audit_errors: list[str],
    source_footer_hash: str = "",
    display_hash: str = "",
) -> None:
    path = state.config.audit_log_path
    if path is None:
        raise AuditLogError("audit log path is not configured")
    with state.lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and not path.is_file():
                raise AuditLogError("audit log path is not a file")
            previous_hash = ""
            if path.is_file():
                previous_hash, chain_errors = _audit_log_chain_state(path)
                if chain_errors:
                    integrity_error = _audit_log_integrity_error(path)
                    raise AuditLogError(integrity_error)
        except OSError as exc:
            raise AuditLogError(f"audit log is not writable: {exc}") from exc
        entry = {
            "schema": "rdllm-service-audit-entry/v1",
            "request_id": request_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": status,
            "event_id": event_payload.get("event_id") if event_payload else "",
            "event_hash": event_payload.get("event_hash") if event_payload else "",
            "source_footer_hash": source_footer_hash,
            "display_hash": display_hash,
            "source_count": len(event_payload.get("source_references", []))
            if event_payload
            else 0,
            "audit_error_count": len(audit_errors)
            if status == "ready"
            else max(1, len(audit_errors)),
            "previous_entry_hash": previous_hash,
        }
        entry["entry_hash"] = canonical_hash(entry)
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
        except OSError as exc:
            raise AuditLogError(f"audit log append failed: {exc}") from exc


def _audit_commit_failure_response(
    state: ServiceState,
    start_response: StartResponse,
    request_id: str,
    response: dict[str, Any],
    exc: AuditLogError,
) -> Iterable[bytes]:
    increment(state, "audit_errors_total")
    if response.get("status") == "ready":
        increment(state, "blocked_requests_total")
    return json_response(
        start_response,
        "503 Service Unavailable",
        {
            "status": "blocked",
            "error": "audit log append failed",
            "audit_errors": [f"audit_log: {exc}"],
        },
        request_id,
    )


def _attribute(state: ServiceState, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return 400, {"status": "blocked", "error": "prompt must be a non-empty string"}
    if len(prompt) > state.config.max_prompt_chars:
        return 413, {"status": "blocked", "error": "prompt exceeds configured limit"}

    output = payload.get("output")
    if output is not None and not isinstance(output, str):
        return 400, {"status": "blocked", "error": "output must be a string"}
    if isinstance(output, str) and len(output) > state.config.max_output_chars:
        return 413, {"status": "blocked", "error": "output exceeds configured limit"}

    try:
        gross_revenue = Decimal(
            str(payload.get("gross_revenue", state.config.default_gross_revenue))
        )
    except Exception:
        return 400, {"status": "blocked", "error": "gross_revenue must be decimal"}
    if gross_revenue < 0:
        return 400, {"status": "blocked", "error": "gross_revenue must be nonnegative"}
    if output:
        event = state.engine.attribute_text(prompt, output, gross_revenue=gross_revenue)
    else:
        event = state.engine.generate(prompt, gross_revenue=gross_revenue)
    event_payload = event.to_dict()
    source_footer = _source_footer_for_event(event)
    audit_errors = state.engine.audit_event(event)
    audit_errors.extend(_display_gate_errors(event, source_footer))
    status = "ready" if not audit_errors else "blocked"
    display = _display_for_event(event, source_footer, status)
    response = {
        "schema": RESPONSE_SCHEMA,
        "status": status,
        "summary": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "source_count": len(event.source_references),
            "source_footer_hash": source_footer["footer_hash"],
            "display_hash": display["rendered_text_hash"],
            "royalty_share_count": len(event.royalty_shares),
            "grounding_verdict": event.grounding_quality.get("verdict", ""),
            "attribution_gap_verdict": event.attribution_gap.get("verdict", ""),
            "generation_evidence_mode": event.generation_evidence.get("mode", ""),
            "settlement_status": event.settlement_decision.get("status", ""),
            "settlement_instruction_eligible": event.settlement_decision.get(
                "eligible_for_settlement_instruction",
                False,
            ),
        },
        "source_footer": source_footer,
        "display": display,
        "audit_errors": audit_errors,
        "event": event_payload,
    }
    return (200 if not audit_errors else 422), response


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    user_parts = [
        str(message.get("content", ""))
        for message in messages
        if isinstance(message, dict) and message.get("role") == "user"
    ]
    return "\n".join(part for part in user_parts if part.strip())


def _provider_grounding_manifest(
    state: ServiceState,
    prompt: str,
) -> tuple[list[Any], dict[str, Any]]:
    hits = state.engine.retrieve(prompt, use="retrieval")
    source_rows = [
        {
            "source_id": f"S{index}",
            "work_id": hit.chunk.work_id,
            "chunk_id": hit.chunk.chunk_id,
            "title": hit.chunk.title,
            "source_uri": hit.chunk.source_uri,
            "content_hash": hit.chunk.content_hash,
            "retrieval_score": round(hit.score, 8),
            "text": hit.chunk.text,
        }
        for index, hit in enumerate(hits, start=1)
    ]
    manifest = {
        "schema": "rdllm-provider-grounding-context/v1",
        "source_rows": source_rows,
    }
    manifest["context_hash"] = canonical_hash(manifest)
    return hits, manifest


def _validate_messages(value: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(value, list) or not value:
        return [], "messages must be a non-empty list"
    messages: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            return [], "each message must be an object"
        role = item.get("role")
        content = item.get("content")
        if role not in {"system", "user", "assistant"}:
            return [], "message role must be system, user, or assistant"
        if not isinstance(content, str) or not content.strip():
            return [], "message content must be a non-empty string"
        messages.append({"role": role, "content": content})
    return messages, ""


def _provider_attribute(
    state: ServiceState, payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    provider_id = str(payload.get("provider_id", "")).strip()
    if not provider_id:
        return 400, {"status": "blocked", "error": "provider_id is required"}
    route = state.provider_routes.get(provider_id)
    if route is None:
        return 404, {"status": "blocked", "error": "provider route is not allowed"}
    messages, message_error = _validate_messages(payload.get("messages"))
    if message_error:
        return 400, {"status": "blocked", "error": message_error}
    prompt = str(payload.get("prompt") or _messages_to_prompt(messages)).strip()
    if not prompt:
        return 400, {"status": "blocked", "error": "prompt or user message is required"}
    if len(prompt) > state.config.max_prompt_chars:
        return 413, {"status": "blocked", "error": "prompt exceeds configured limit"}
    model = payload.get("model")
    if model is not None and not isinstance(model, str):
        return 400, {"status": "blocked", "error": "model must be a string"}
    try:
        gross_revenue = Decimal(
            str(payload.get("gross_revenue", state.config.default_gross_revenue))
        )
    except Exception:
        return 400, {"status": "blocked", "error": "gross_revenue must be decimal"}
    if gross_revenue < 0:
        return 400, {"status": "blocked", "error": "gross_revenue must be nonnegative"}
    hits, grounding_manifest = _provider_grounding_manifest(state, prompt)
    if not hits:
        return 422, {
            "status": "blocked",
            "error": "no policy-allowed source evidence was retrieved for provider generation",
        }
    try:
        generation = call_openai_compatible_chat(
            route,
            messages,
            model=model,
            grounding_manifest=grounding_manifest,
        )
    except ProviderClientError as exc:
        return 502, {"status": "blocked", "error": str(exc)}
    if len(generation.output) > state.config.max_output_chars:
        return 413, {"status": "blocked", "error": "provider output exceeds configured limit"}
    event = state.engine.attribute_grounded_text(
        prompt,
        generation.output,
        gross_revenue=gross_revenue,
        hits=hits,
        provider_evidence={
            "provider_id": generation.provider_id,
            "provider_family": generation.family,
            "provider_model": generation.model,
            "provider_request_hash": generation.provider_request_hash,
            "provider_response_hash": generation.provider_response_hash,
            "provider_evidence_mode": generation.evidence_mode,
            "provider_evidence_verified": generation.evidence_verified,
            "grounding_context_hash": generation.grounding_context_hash,
            "grounding_source_ids": list(generation.grounding_source_ids),
            "source_annotation_hash": canonical_hash(
                list(generation.source_annotations)
            ),
        },
    )
    event_payload = event.to_dict()
    source_footer = _source_footer_for_event(event)
    audit_errors = state.engine.audit_event(event)
    audit_errors.extend(_display_gate_errors(event, source_footer))
    status = "ready" if not audit_errors else "blocked"
    display = _display_for_event(event, source_footer, status)
    response = {
        "schema": RESPONSE_SCHEMA,
        "status": status,
        "summary": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "source_count": len(event.source_references),
            "source_footer_hash": source_footer["footer_hash"],
            "display_hash": display["rendered_text_hash"],
            "royalty_share_count": len(event.royalty_shares),
            "grounding_verdict": event.grounding_quality.get("verdict", ""),
            "attribution_gap_verdict": event.attribution_gap.get("verdict", ""),
            "provider_id": generation.provider_id,
            "provider_response_hash": generation.provider_response_hash,
            "provider_evidence_mode": generation.evidence_mode,
            "provider_evidence_verified": generation.evidence_verified,
            "settlement_status": event.settlement_decision.get("status", ""),
            "settlement_instruction_eligible": event.settlement_decision.get(
                "eligible_for_settlement_instruction",
                False,
            ),
        },
        "provider_generation": generation.to_dict(),
        "source_footer": source_footer,
        "display": display,
        "audit_errors": audit_errors,
        "event": event_payload,
    }
    return (200 if not audit_errors else 422), response


def make_app(state: ServiceState) -> Callable[[dict[str, Any], StartResponse], Iterable[bytes]]:
    def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        increment(state, "requests_total")
        request_id = str(uuid.uuid4())
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        if method == "GET" and path == "/healthz":
            return json_response(
                start_response,
                "200 OK",
                {"status": "ok", "service": "rdllm"},
                request_id,
            )
        if method == "GET" and path == "/readyz":
            report = readiness_report(state)
            code = "200 OK" if report["status"] == "ready" else "503 Service Unavailable"
            return json_response(start_response, code, report, request_id)
        if method == "GET" and path == "/openapi.json":
            return json_response(start_response, "200 OK", openapi_document(), request_id)
        if method == "GET" and path == "/.well-known/rdllm.json":
            manifest_path = state.config.artifact_path("discovery_manifest")
            if manifest_path and manifest_path.is_file():
                return json_response(
                    start_response,
                    "200 OK",
                    load_json(manifest_path),
                    request_id,
                )
            return json_response(
                start_response,
                "503 Service Unavailable",
                {"status": "blocked", "error": "discovery manifest unavailable"},
                request_id,
            )

        if not _authorize(state, environ):
            increment(state, "blocked_requests_total")
            return json_response(
                start_response,
                "401 Unauthorized",
                {"status": "blocked", "error": "authorization required"},
                request_id,
            )

        rate_allowed, retry_after = _rate_limit(state, environ)
        if not rate_allowed:
            return _rate_limit_response(state, start_response, request_id, retry_after)

        if method == "GET" and path == "/v1/metrics":
            return json_response(start_response, "200 OK", metrics_report(state), request_id)
        if method == "GET" and path == "/v1/metrics/prometheus":
            return text_response(
                start_response,
                "200 OK",
                prometheus_metrics(state),
                request_id,
            )
        if method == "POST" and path == "/v1/attribute":
            ready = readiness_report(state)
            if ready["status"] != "ready":
                increment(state, "blocked_requests_total")
                return json_response(
                    start_response,
                    "503 Service Unavailable",
                    ready,
                    request_id,
                )
            payload, error = _read_request_body(environ, state.config.max_request_bytes)
            if error:
                increment(state, "blocked_requests_total")
                return json_response(
                    start_response,
                    "400 Bad Request",
                    {"status": "blocked", "error": error},
                    request_id,
                )
            increment(state, "attribution_requests_total")
            status_code, response = _attribute(state, payload)
            audit_errors = response.get("audit_errors", [])
            if audit_errors:
                increment(state, "audit_errors_total", len(audit_errors))
            if response.get("status") != "ready":
                increment(state, "blocked_requests_total")
            try:
                _append_audit_log(
                    state,
                    request_id,
                    str(response.get("status", "blocked")),
                    response.get("event"),
                    audit_errors,
                    source_footer_hash=str(
                        response.get("summary", {}).get("source_footer_hash", "")
                    ),
                    display_hash=str(
                        response.get("summary", {}).get("display_hash", "")
                    ),
                )
            except AuditLogError as exc:
                return _audit_commit_failure_response(
                    state,
                    start_response,
                    request_id,
                    response,
                    exc,
                )
            return json_response(
                start_response,
                status_line(status_code),
                response,
                request_id,
            )
        if method == "POST" and path == "/v1/provider/attribute":
            ready = readiness_report(state)
            if ready["status"] != "ready":
                increment(state, "blocked_requests_total")
                return json_response(
                    start_response,
                    "503 Service Unavailable",
                    ready,
                    request_id,
                )
            payload, error = _read_request_body(environ, state.config.max_request_bytes)
            if error:
                increment(state, "blocked_requests_total")
                return json_response(
                    start_response,
                    "400 Bad Request",
                    {"status": "blocked", "error": error},
                    request_id,
                )
            increment(state, "provider_requests_total")
            increment(state, "attribution_requests_total")
            status_code, response = _provider_attribute(state, payload)
            audit_errors = response.get("audit_errors", [])
            if audit_errors:
                increment(state, "audit_errors_total", len(audit_errors))
            if response.get("status") != "ready":
                increment(state, "blocked_requests_total")
            try:
                _append_audit_log(
                    state,
                    request_id,
                    str(response.get("status", "blocked")),
                    response.get("event"),
                    audit_errors,
                    source_footer_hash=str(
                        response.get("summary", {}).get("source_footer_hash", "")
                    ),
                    display_hash=str(
                        response.get("summary", {}).get("display_hash", "")
                    ),
                )
            except AuditLogError as exc:
                return _audit_commit_failure_response(
                    state,
                    start_response,
                    request_id,
                    response,
                    exc,
                )
            return json_response(
                start_response,
                status_line(status_code),
                response,
                request_id,
            )

        increment(state, "blocked_requests_total")
        return json_response(
            start_response,
            "404 Not Found",
            {"status": "blocked", "error": f"unknown route: {method} {path}"},
            request_id,
        )

    return app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def serve(config_path: str | Path, host: str | None = None, port: int | None = None) -> None:
    config = load_service_config(config_path)
    if host is not None:
        config.raw["host"] = host
    if port is not None:
        config.raw["port"] = port
    state = ServiceState.from_config(config)
    app = make_app(state)
    with make_server(
        config.host,
        config.port,
        app,
        server_class=ThreadingWSGIServer,
    ) as server:
        print(f"rdllm service listening on http://{config.host}:{config.port}", flush=True)
        server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="examples/service_config.json",
        help="Path to an RDLLM service config JSON file.",
    )
    parser.add_argument("--host", help="Override host from config.")
    parser.add_argument("--port", type=int, help="Override port from config.")
    args = parser.parse_args(argv)
    serve(args.config, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
