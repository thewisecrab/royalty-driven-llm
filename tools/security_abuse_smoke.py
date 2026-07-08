"""Fail-closed abuse smoke tests for the RDLLM service boundary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

from service_smoke import (
    SERVICE_TOKEN,
    TEXT_ATTRIBUTION_OUTPUT,
    free_port,
    request_json,
    token_hash,
    wait_for_health,
)


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_KEY = "mock-provider-key"


class AbuseProviderHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    mode = "content_filter"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.headers.get("Authorization") != f"Bearer {PROVIDER_KEY}":
            self.send_error(401)
            return
        if AbuseProviderHandler.mode == "missing_choices":
            response: dict[str, Any] = {"model": "mock-model", "usage": {}}
        else:
            finish_reason = (
                "content_filter"
                if AbuseProviderHandler.mode == "content_filter"
                else "stop"
            )
            content = (
                TEXT_ATTRIBUTION_OUTPUT * 20
                if AbuseProviderHandler.mode == "oversized_output"
                else TEXT_ATTRIBUTION_OUTPUT
            )
            response = {
                "id": "chatcmpl-rdllm-abuse",
                "object": "chat.completion",
                "model": "mock-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {"total_tokens": 44},
            }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@contextmanager
def mock_provider(mode: str) -> Iterator[tuple[int, ThreadingHTTPServer]]:
    AbuseProviderHandler.mode = mode
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), AbuseProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, server
    finally:
        server.shutdown()
        server.server_close()


def write_config(
    directory: Path,
    port: int,
    *,
    provider_port: int | None = None,
    provider_key_env: str = "RDLLM_PROVIDER_ABUSE_KEY",
    rate_limit: int = 120,
    rate_limit_window_seconds: int = 60,
    max_prompt_chars: int = 4000,
    max_output_chars: int = 16000,
) -> Path:
    config = json.loads((ROOT / "examples" / "service_config.json").read_text())
    config["port"] = port
    config["audit_log_path"] = str(directory / "security_abuse_audit.jsonl")
    config["limits"]["rate_limit_requests_per_window"] = rate_limit
    config["limits"]["rate_limit_window_seconds"] = rate_limit_window_seconds
    config["limits"]["max_prompt_chars"] = max_prompt_chars
    config["limits"]["max_output_chars"] = max_output_chars
    if provider_port is not None:
        config["providers"] = [
            {
                "provider_id": "abuse-provider",
                "family": "openai_compatible_chat",
                "base_url": f"http://127.0.0.1:{provider_port}",
                "model": "mock-model",
                "api_key_env": provider_key_env,
                "timeout_seconds": 5,
                "max_response_bytes": 200000,
            }
        ]
    path = directory / "service_config.security.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    return path


@contextmanager
def service_process(
    config_path: Path,
    *,
    provider_key: str | None = None,
) -> Iterator[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["RDLLM_SERVICE_TOKEN_SHA256"] = token_hash(SERVICE_TOKEN)
    if provider_key is not None:
        env["RDLLM_PROVIDER_ABUSE_KEY"] = provider_key
    process = subprocess.Popen(
        [sys.executable, "-m", "rdllm.service", "--config", str(config_path)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{json.loads(config_path.read_text())['port']}"
    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def assert_status(
    errors: list[str],
    name: str,
    actual: int,
    expected: int,
    payload: dict[str, Any],
) -> None:
    if actual != expected:
        errors.append(f"{name}: expected HTTP {expected}, got {actual}: {payload}")
    if expected >= 400 and payload.get("status") != "blocked":
        errors.append(f"{name}: failure response should be blocked")


def run_basic_abuse_cases(errors: list[str], temp_path: Path) -> None:
    port = free_port()
    config = write_config(temp_path, port, max_prompt_chars=80)
    with service_process(config) as base_url:
        errors.extend(wait_for_health(base_url))
        status, payload, _headers = request_json(
            base_url,
            "/v1/attribute",
            method="POST",
            payload={"prompt": "hello"},
        )
        assert_status(errors, "unauthorized_attribute", status, 401, payload)

        status, payload, _headers = request_json(
            base_url,
            "/v1/attribute",
            method="POST",
            payload={"prompt": "x" * 120, "output": TEXT_ATTRIBUTION_OUTPUT},
            token=SERVICE_TOKEN,
        )
        assert_status(errors, "oversized_prompt", status, 413, payload)

        status, payload, _headers = request_json(
            base_url,
            "/v1/attribute",
            method="POST",
            payload={
                "prompt": "valid prompt",
                "output": TEXT_ATTRIBUTION_OUTPUT,
                "gross_revenue": "-1.00",
            },
            token=SERVICE_TOKEN,
        )
        assert_status(errors, "negative_revenue", status, 400, payload)

        status, payload, _headers = request_json(
            base_url,
            "/v1/provider/attribute",
            method="POST",
            payload={"provider_id": "missing", "messages": [{"role": "user", "content": "x"}]},
            token=SERVICE_TOKEN,
        )
        assert_status(errors, "unknown_provider", status, 404, payload)


def run_rate_limit_case(errors: list[str], temp_path: Path) -> None:
    port = free_port()
    config = write_config(temp_path, port, rate_limit=2, rate_limit_window_seconds=1)
    with service_process(config) as base_url:
        errors.extend(wait_for_health(base_url))
        statuses = [
            request_json(base_url, "/v1/metrics", token=SERVICE_TOKEN)[0]
            for _ in range(3)
        ]
        if statuses != [200, 200, 429]:
            errors.append(f"rate_limit: expected [200, 200, 429], got {statuses}")
        time.sleep(1.1)
        metrics_status, metrics, _headers = request_json(
            base_url,
            "/v1/metrics",
            token=SERVICE_TOKEN,
        )
        if metrics_status != 200:
            errors.append(f"rate_limit: expected metrics after reset, got {metrics_status}")
        elif metrics.get("rate_limited_requests_total", 0) < 1:
            errors.append("rate_limit: limiter metric did not increment")


def run_missing_provider_key_case(errors: list[str], temp_path: Path) -> None:
    with mock_provider("content_filter") as (provider_port, _server):
        port = free_port()
        config = write_config(temp_path, port, provider_port=provider_port)
        with service_process(config, provider_key=None) as base_url:
            errors.extend(wait_for_health(base_url))
            ready_status, ready, _headers = request_json(base_url, "/readyz")
            assert_status(errors, "missing_provider_key_readyz", ready_status, 503, ready)


def run_provider_failure_case(
    errors: list[str],
    temp_path: Path,
    mode: str,
    expected_status: int,
    *,
    max_output_chars: int = 16000,
) -> None:
    with mock_provider(mode) as (provider_port, _server):
        port = free_port()
        config = write_config(
            temp_path,
            port,
            provider_port=provider_port,
            max_output_chars=max_output_chars,
        )
        with service_process(config, provider_key=PROVIDER_KEY) as base_url:
            errors.extend(wait_for_health(base_url))
            status, payload, _headers = request_json(
                base_url,
                "/v1/provider/attribute",
                method="POST",
                token=SERVICE_TOKEN,
                payload={
                    "provider_id": "abuse-provider",
                    "messages": [{"role": "user", "content": "cite sources"}],
                    "gross_revenue": "1.00",
                },
            )
            assert_status(errors, f"provider_{mode}", status, expected_status, payload)


def run_smoke() -> dict[str, Any]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="rdllm-security-abuse-") as temp_dir:
        temp_path = Path(temp_dir)
        run_basic_abuse_cases(errors, temp_path)
        run_rate_limit_case(errors, temp_path)
        run_missing_provider_key_case(errors, temp_path)
        run_provider_failure_case(errors, temp_path, "content_filter", 502)
        run_provider_failure_case(errors, temp_path, "missing_choices", 502)
        run_provider_failure_case(
            errors,
            temp_path,
            "oversized_output",
            413,
            max_output_chars=64,
        )
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "sections": {
            "basic_abuse_cases": 4,
            "rate_limit_cases": 1,
            "provider_failure_cases": 4,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_smoke()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"security_abuse_smoke status: {report['status']}")
        for name, section in report["sections"].items():
            print(f"{name}: {json.dumps(section, sort_keys=True)}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
