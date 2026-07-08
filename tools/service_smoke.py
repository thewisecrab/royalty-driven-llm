"""Smoke test the RDLLM production service boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SERVICE_TOKEN = "rdllm-local-dev-token"
TEXT_ATTRIBUTION_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval "
    "scores, output citations, payout weights, and an event hash that allows "
    "auditors to replay the attribution."
)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body), dict(exc.headers.items())


def request_text(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
) -> tuple[int, str, dict[str, str]]:
    headers = {"Accept": "text/plain"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url}{path}",
        method="GET",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return (
                response.status,
                response.read().decode("utf-8"),
                dict(response.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8"), dict(exc.headers.items())


def wait_for_health(base_url: str) -> list[str]:
    errors: list[str] = []
    for _ in range(60):
        try:
            status, payload, _headers = request_json(base_url, "/healthz")
            if status == 200 and payload.get("status") == "ok":
                return []
        except (OSError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    errors.append("service did not become healthy")
    return errors


def write_temp_config(directory: Path, port: int) -> Path:
    template = json.loads((ROOT / "examples" / "service_config.json").read_text())
    template["port"] = port
    template["audit_log_path"] = str(directory / "service_audit.jsonl")
    path = directory / "service_config.json"
    path.write_text(json.dumps(template, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_smoke() -> dict[str, Any]:
    errors: list[str] = []
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="rdllm-service-smoke-") as temp_dir:
        temp_path = Path(temp_dir)
        config_path = write_temp_config(temp_path, port)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        env["RDLLM_SERVICE_TOKEN_SHA256"] = token_hash(SERVICE_TOKEN)
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

            ready_status, ready, ready_headers = request_json(base_url, "/readyz")
            if ready_status != 200 or ready.get("status") != "ready":
                errors.append(f"readyz failed: {ready_status} {ready}")
            if ready_headers.get("X-Content-Type-Options") != "nosniff":
                errors.append("security header X-Content-Type-Options missing")

            unauthorized_status, unauthorized, _headers = request_json(
                base_url,
                "/v1/metrics",
            )
            if unauthorized_status != 401:
                errors.append(
                    f"unauthorized metrics request should return 401, got {unauthorized_status}"
                )
            if unauthorized.get("status") != "blocked":
                errors.append("unauthorized response should be blocked")

            payload = {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": TEXT_ATTRIBUTION_OUTPUT,
                "gross_revenue": "1.00",
            }
            attribute_status, attribute, _headers = request_json(
                base_url,
                "/v1/attribute",
                method="POST",
                payload=payload,
                token=SERVICE_TOKEN,
            )
            if attribute_status != 200:
                errors.append(f"attribute request failed: {attribute_status} {attribute}")
            if attribute.get("status") != "ready":
                errors.append("attribute response is not ready")
            if attribute.get("summary", {}).get("source_count", 0) < 1:
                errors.append("attribute response should include at least one source")
            footer = attribute.get("source_footer", {})
            if footer.get("schema") != "rdllm-service-source-footer/v1":
                errors.append("attribute response should include a service source footer")
            if footer.get("footer_hash") != attribute.get("summary", {}).get(
                "source_footer_hash"
            ):
                errors.append("source footer hash should match response summary")
            if "Sources" not in str(footer.get("rendered_text", "")):
                errors.append("source footer should include rendered source text")
            if not footer.get("source_rows"):
                errors.append("source footer should include source rows")
            elif not all(row.get("verification_handle") for row in footer["source_rows"]):
                errors.append("source footer rows should include verification handles")
            if not footer.get("claim_rows"):
                errors.append("source footer should include claim rows")
            if "verify=rdllm://verify/source-footer/" not in str(
                footer.get("rendered_text", "")
            ):
                errors.append("source footer should render source verification handles")
            rendered_footer = str(footer.get("rendered_text", ""))
            for token in ("support=", "text_match=", "weight=", "payout="):
                if token not in rendered_footer:
                    errors.append(f"source footer should render {token.rstrip('=')}")
            display = attribute.get("display", {})
            if display.get("schema") != "rdllm-service-display/v1":
                errors.append("attribute response should include a display surface")
            if display.get("source_footer_hash") != footer.get("footer_hash"):
                errors.append("display should bind the source footer hash")
            if display.get("rendered_text_hash") != attribute.get("summary", {}).get(
                "display_hash"
            ):
                errors.append("display hash should match response summary")
            if "Sources" not in str(display.get("rendered_text", "")):
                errors.append("display should include rendered source footer text")

            metrics_status, metrics, _headers = request_json(
                base_url,
                "/v1/metrics",
                token=SERVICE_TOKEN,
            )
            if metrics_status != 200 or metrics.get("ready_status") != "ready":
                errors.append(f"metrics failed: {metrics_status} {metrics}")
            if metrics.get("attribution_requests_total") != 1:
                errors.append("metrics should count one attribution request")

            prometheus_status, prometheus_text, prometheus_headers = request_text(
                base_url,
                "/v1/metrics/prometheus",
                token=SERVICE_TOKEN,
            )
            if prometheus_status != 200:
                errors.append(f"prometheus metrics failed: {prometheus_status}")
            if "rdllm_service_attribution_requests_total 1" not in prometheus_text:
                errors.append("prometheus metrics should count one attribution request")
            content_type = prometheus_headers.get("Content-Type", "")
            if "text/plain" not in content_type:
                errors.append("prometheus metrics should use text/plain content type")

            audit_path = temp_path / "service_audit.jsonl"
            if not audit_path.is_file():
                errors.append("service audit log was not written")
            else:
                rows = [
                    json.loads(line)
                    for line in audit_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if len(rows) != 1:
                    errors.append("service audit log should contain one row")
                elif rows[0].get("event_hash") != attribute.get("summary", {}).get(
                    "event_hash"
                ):
                    errors.append("service audit log does not bind response event hash")
                else:
                    if rows[0].get("source_footer_hash") != attribute.get(
                        "summary",
                        {},
                    ).get("source_footer_hash"):
                        errors.append(
                            "service audit log does not bind response source footer hash"
                        )
                    if rows[0].get("display_hash") != attribute.get(
                        "summary",
                        {},
                    ).get("display_hash"):
                        errors.append(
                            "service audit log does not bind response display hash"
                        )

            return {
                "status": "passed" if not errors else "failed",
                "errors": errors,
                "sections": {
                    "ready": {
                        "ready_check_count": ready.get("ready_check_count"),
                        "blocked_check_count": ready.get("blocked_check_count"),
                    },
                    "attribute": attribute.get("summary", {}),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_smoke()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"service_smoke status: {report['status']}")
        for name, section in report["sections"].items():
            print(f"{name}: {json.dumps(section, sort_keys=True)}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
