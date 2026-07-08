"""Concurrent smoke test for the RDLLM service boundary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from rdllm.service_audit_verifier import verify_service_audit_log

from service_smoke import (
    SERVICE_TOKEN,
    TEXT_ATTRIBUTION_OUTPUT,
    free_port,
    request_json,
    token_hash,
    wait_for_health,
    write_temp_config,
)


ROOT = Path(__file__).resolve().parents[1]


def _attribute_once(base_url: str, index: int) -> tuple[int, dict[str, Any]]:
    return request_json(
        base_url,
        "/v1/attribute",
        method="POST",
        token=SERVICE_TOKEN,
        payload={
            "prompt": f"What should attribution answers expose? request={index}",
            "output": TEXT_ATTRIBUTION_OUTPUT,
            "gross_revenue": "1.00",
        },
    )[:2]


def _verify_audit_chain(path: Path, expected_count: int) -> list[str]:
    report = verify_service_audit_log(path, expected_count=expected_count)
    return [
        f"service audit verification: {error}"
        for error in report["errors"]
    ]


def run_load_smoke(concurrency: int = 8, request_count: int = 16) -> dict[str, Any]:
    errors: list[str] = []
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="rdllm-service-load-") as temp_dir:
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
        started_at = time.time()
        try:
            errors.extend(wait_for_health(base_url))
            if errors:
                return {"status": "failed", "errors": errors, "sections": {}}
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(_attribute_once, base_url, index)
                    for index in range(request_count)
                ]
                responses = [future.result() for future in as_completed(futures)]
            failed = [
                {"status": status, "payload": payload}
                for status, payload in responses
                if status != 200 or payload.get("status") != "ready"
            ]
            if failed:
                errors.append(f"{len(failed)} attribution requests failed")
            metrics_status, metrics, _headers = request_json(
                base_url,
                "/v1/metrics",
                token=SERVICE_TOKEN,
            )
            if metrics_status != 200:
                errors.append(f"metrics returned {metrics_status}")
            if metrics.get("attribution_requests_total") != request_count:
                errors.append(
                    "metrics attribution count "
                    f"{metrics.get('attribution_requests_total')} != {request_count}"
                )
            errors.extend(
                _verify_audit_chain(temp_path / "service_audit.jsonl", request_count)
            )
            elapsed = round(time.time() - started_at, 3)
            return {
                "status": "passed" if not errors else "failed",
                "errors": errors,
                "sections": {
                    "request_count": request_count,
                    "concurrency": concurrency,
                    "elapsed_seconds": elapsed,
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
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--request-count", type=int, default=16)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_load_smoke(
        concurrency=args.concurrency,
        request_count=args.request_count,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"service_load_smoke status: {report['status']}")
        for key, value in report["sections"].items():
            print(f"{key}: {json.dumps(value, sort_keys=True)}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
