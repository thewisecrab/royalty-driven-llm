"""Smoke test RDLLM's guarded OpenAI-compatible provider route."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from service_smoke import (
    SERVICE_TOKEN,
    TEXT_ATTRIBUTION_OUTPUT,
    free_port,
    request_json,
    token_hash,
    wait_for_health,
)


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ID = "mock-openai-compatible"
PROVIDER_KEY = "mock-provider-key"


class MockProviderHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    request_count = 0
    auth_seen = False

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400)
            return
        MockProviderHandler.request_count += 1
        MockProviderHandler.auth_seen = (
            self.headers.get("Authorization") == f"Bearer {PROVIDER_KEY}"
        )
        if not MockProviderHandler.auth_seen:
            self.send_error(401)
            return
        response = {
            "id": "chatcmpl-rdllm-mock",
            "object": "chat.completion",
            "model": payload.get("model", "mock-model"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": TEXT_ATTRIBUTION_OUTPUT,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 32,
                "total_tokens": 44,
            },
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def start_mock_provider(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), MockProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def write_provider_config(directory: Path, service_port: int, provider_port: int) -> Path:
    template = json.loads((ROOT / "examples" / "service_config.json").read_text())
    template["port"] = service_port
    template["audit_log_path"] = str(directory / "provider_audit.jsonl")
    template["providers"] = [
        {
            "provider_id": PROVIDER_ID,
            "family": "openai_compatible_chat",
            "base_url": f"http://127.0.0.1:{provider_port}",
            "model": "mock-model",
            "api_key_env": "RDLLM_PROVIDER_MOCK_KEY",
            "timeout_seconds": 5,
            "max_response_bytes": 100000,
        }
    ]
    path = directory / "service_config.provider.json"
    path.write_text(json.dumps(template, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_smoke() -> dict[str, Any]:
    errors: list[str] = []
    service_port = free_port()
    provider_port = free_port()
    base_url = f"http://127.0.0.1:{service_port}"
    MockProviderHandler.request_count = 0
    MockProviderHandler.auth_seen = False
    provider_server = start_mock_provider(provider_port)
    with tempfile.TemporaryDirectory(prefix="rdllm-provider-smoke-") as temp_dir:
        temp_path = Path(temp_dir)
        config_path = write_provider_config(temp_path, service_port, provider_port)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        env["RDLLM_SERVICE_TOKEN_SHA256"] = token_hash(SERVICE_TOKEN)
        env["RDLLM_PROVIDER_MOCK_KEY"] = PROVIDER_KEY
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "rdllm.service",
                "--config",
                str(config_path),
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            errors.extend(wait_for_health(base_url))
            if errors:
                return {"status": "failed", "errors": errors, "sections": {}}
            ready_status, ready, _headers = request_json(base_url, "/readyz")
            if ready_status != 200 or ready.get("status") != "ready":
                errors.append(f"readyz failed: {ready_status} {ready}")
            provider_checks = [
                row
                for row in ready.get("checks", [])
                if row.get("name") == f"provider_route:{PROVIDER_ID}"
            ]
            if not provider_checks or provider_checks[0].get("status") != "ready":
                errors.append("provider route readiness check is missing or blocked")

            payload = {
                "provider_id": PROVIDER_ID,
                "messages": [
                    {
                        "role": "user",
                        "content": "What should royalty-bearing AI answers expose?",
                    }
                ],
                "gross_revenue": "1.00",
            }
            status, response, _headers = request_json(
                base_url,
                "/v1/provider/attribute",
                method="POST",
                payload=payload,
                token=SERVICE_TOKEN,
            )
            if status != 200:
                errors.append(f"provider attribution failed: {status} {response}")
            if response.get("status") != "ready":
                errors.append("provider attribution response is not ready")
            summary = response.get("summary", {})
            if summary.get("provider_id") != PROVIDER_ID:
                errors.append("response summary does not bind provider_id")
            if summary.get("source_count", 0) < 1:
                errors.append("provider attribution should include at least one source")
            footer = response.get("source_footer", {})
            if footer.get("schema") != "rdllm-service-source-footer/v1":
                errors.append("provider attribution should include a service source footer")
            if footer.get("footer_hash") != summary.get("source_footer_hash"):
                errors.append("provider source footer hash should match response summary")
            if not footer.get("source_rows"):
                errors.append("provider source footer should include source rows")
            elif not all(row.get("verification_handle") for row in footer["source_rows"]):
                errors.append(
                    "provider source footer rows should include verification handles"
                )
            if "Sources" not in str(footer.get("rendered_text", "")):
                errors.append("provider source footer should include rendered source text")
            if "verify=rdllm://verify/source-footer/" not in str(
                footer.get("rendered_text", "")
            ):
                errors.append(
                    "provider source footer should render source verification handles"
                )
            rendered_footer = str(footer.get("rendered_text", ""))
            if "metrics=rdllm-observable-source-usage-metrics/v1" not in rendered_footer:
                errors.append(
                    "provider source footer should render source usage metric profile"
                )
            if (
                "scope=observable_support_allocation_not_model_internal_reliance"
                not in rendered_footer
            ):
                errors.append(
                    "provider source footer should render source usage metric scope"
                )
            if "methods=support:rdllm-claim-overlap-support/v1" not in rendered_footer:
                errors.append(
                    "provider source footer should render source usage metric methods"
                )
            if "warrant=passed" not in rendered_footer:
                errors.append(
                    "provider source footer should render claim warrant status"
                )
            if "profile=rdllm-evidence-force-calibration/v1" not in rendered_footer:
                errors.append(
                    "provider source footer should render claim warrant profile"
                )
            if "disagreement=passed" not in rendered_footer:
                errors.append(
                    "provider source footer should render claim source disagreement status"
                )
            if "conflicts=none" not in rendered_footer:
                errors.append(
                    "provider source footer should render empty source conflict list"
                )
            if (
                "disagreement_profile=rdllm-visible-source-disagreement/v1"
                not in rendered_footer
            ):
                errors.append(
                    "provider source footer should render source disagreement profile"
                )
            display = response.get("display", {})
            if display.get("schema") != "rdllm-service-display/v1":
                errors.append("provider attribution should include a display surface")
            if display.get("source_footer_hash") != footer.get("footer_hash"):
                errors.append("provider display should bind the source footer hash")
            if display.get("rendered_text_hash") != summary.get("display_hash"):
                errors.append("provider display hash should match response summary")
            if "Sources" not in str(display.get("rendered_text", "")):
                errors.append("provider display should include rendered source text")
            if not response.get("provider_generation", {}).get("provider_response_hash"):
                errors.append("provider response hash is missing")
            if MockProviderHandler.request_count != 1 or not MockProviderHandler.auth_seen:
                errors.append("mock provider did not receive one authenticated request")

            metrics_status, metrics, _headers = request_json(
                base_url,
                "/v1/metrics",
                token=SERVICE_TOKEN,
            )
            if metrics_status != 200:
                errors.append(f"metrics failed: {metrics_status}")
            if metrics.get("provider_requests_total") != 1:
                errors.append("metrics should count one provider request")

            audit_path = temp_path / "provider_audit.jsonl"
            if not audit_path.is_file():
                errors.append("provider audit log was not written")
            else:
                rows = [
                    json.loads(line)
                    for line in audit_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if len(rows) != 1:
                    errors.append("provider audit log should contain one row")
                elif rows[0].get("event_hash") != summary.get("event_hash"):
                    errors.append("provider audit log does not bind event hash")

            return {
                "status": "passed" if not errors else "failed",
                "errors": errors,
                "sections": {
                    "ready": {
                        "ready_check_count": ready.get("ready_check_count"),
                        "blocked_check_count": ready.get("blocked_check_count"),
                    },
                    "provider": summary,
                    "source_footer": {
                        "footer_hash": footer.get("footer_hash"),
                        "source_count": footer.get("source_count"),
                        "claim_count": footer.get("claim_count"),
                    },
                    "display": {
                        "display_hash": display.get("rendered_text_hash"),
                    },
                    "metrics": metrics,
                },
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            provider_server.shutdown()
            provider_server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_smoke()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"provider_live_smoke status: {report['status']}")
        for name, section in report["sections"].items():
            print(f"{name}: {json.dumps(section, sort_keys=True)}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
