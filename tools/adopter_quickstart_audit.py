"""Audit the adopter quickstart for rootless production evaluation."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.operator_bootstrap import bootstrap_operator, verify_bootstrap_dir
from rdllm.service import ServiceConfig, ServiceState, load_json, make_app
from rdllm.service_audit_verifier import verify_service_audit_log
from rdllm.service_response_verifier import verify_service_response

QUICKSTART = ROOT / "docs" / "adopter_quickstart.md"
PROBE_TOKEN = "rdllm-local-dev-token"
PROBE_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval "
    "scores, output citations, payout weights, and an event hash that allows "
    "auditors to replay the attribution."
)

REQUIRED_TERMS = (
    "individual",
    "company",
    "institution",
    "government",
    "public_sector",
    "RDLLM_HOME",
    "RDLLM_STATE",
    "RDLLM_AUDIT_LOG",
    "RDLLM_SERVICE_TOKEN",
    "RDLLM_SERVICE_TOKEN_SHA256",
    'mkdir -p "$RDLLM_HOME" "$RDLLM_STATE" "$(dirname "$RDLLM_AUDIT_LOG")"',
    '--output-dir "$RDLLM_HOME"',
    '--audit-log-path "$RDLLM_AUDIT_LOG"',
    '--verify-dir "$RDLLM_HOME"',
    '--config "$RDLLM_HOME/service_config.json"',
    "Authorization: Bearer $RDLLM_SERVICE_TOKEN",
    '--profile "$RDLLM_HOME/production_readiness_profile.json"',
    '--service-config "$RDLLM_HOME/service_config.json"',
    '--service-root "$RDLLM_HOME"',
    '--bootstrap-dir "$RDLLM_HOME"',
    '--root "$RDLLM_HOME"',
    '--manifest "$RDLLM_STATE/recovery_manifest.json"',
    '--audit-log "$RDLLM_AUDIT_LOG"',
    '--output "$RDLLM_STATE/operator_acceptance_report.json"',
    '--output-dir "$RDLLM_STATE/acceptance-matrix"',
    "rdllm-operator-doctor",
    "rdllm-operator-bootstrap",
    "rdllm-service-response-verify",
    "rdllm-source-footer-verify",
    "rdllm-operator-launch-gate",
    "rdllm-operator-recovery",
    "rdllm-service-audit-verify",
    "rdllm-operator-acceptance",
    "rdllm-operator-acceptance-matrix",
    "rdllm-operator-support-bundle",
    "production_display_ready",
    "source_grounding_acceptance",
    "production_acceptance_decision",
)
BANNED_TERMS = (
    "/etc/rdllm",
    "/var/lib/rdllm",
    "Bearer <token>",
    "<sha256 token hash>",
)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _attribute_request(
    state: ServiceState,
    *,
    token: str,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    status_headers: dict[str, Any] = {"status": ""}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_headers["status"] = status
        status_headers["headers"] = headers

    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/v1/attribute",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/json",
        "HTTP_AUTHORIZATION": f"Bearer {token}",
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.input": io.BytesIO(body),
    }
    response_body = b"".join(make_app(state)(environ, start_response)).decode(
        "utf-8"
    )
    return str(status_headers["status"]), json.loads(response_body)


def _rootless_probe() -> dict[str, Any]:
    errors: list[str] = []
    previous_token_hash = os.environ.get("RDLLM_SERVICE_TOKEN_SHA256")
    response: dict[str, Any] = {}
    response_verification: dict[str, Any] = {}
    audit_verification: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    bootstrap_verification: dict[str, Any] = {}
    config: dict[str, Any] = {}
    status_line = ""
    audit_log_bound = False
    probe_exception = ""

    try:
        with tempfile.TemporaryDirectory(prefix="rdllm-quickstart-audit-") as raw_temp:
            temp = Path(raw_temp)
            operator_root = temp / ".rdllm" / "operator"
            state_root = temp / ".rdllm" / "state"
            audit_log = state_root / "audit" / "service.jsonl"
            audit_log.parent.mkdir(parents=True, exist_ok=True)
            os.environ["RDLLM_SERVICE_TOKEN_SHA256"] = _token_hash(PROBE_TOKEN)
            try:
                manifest = bootstrap_operator(
                    output_dir=operator_root,
                    operator_template="company",
                    operator_name="Quickstart Probe",
                    security_contact="security@example.com",
                    audit_log_path=audit_log.as_posix(),
                    include_sample_corpus=True,
                    include_reference_artifacts=True,
                    check_runtime=True,
                )
                bootstrap_verification = verify_bootstrap_dir(
                    operator_root,
                    check_runtime=True,
                )
                config = load_json(operator_root / "service_config.json")
                audit_log_bound = config.get("audit_log_path") == audit_log.as_posix()
                state = ServiceState.from_config(
                    ServiceConfig(raw=config, root=operator_root)
                )
                status_line, response = _attribute_request(
                    state,
                    token=PROBE_TOKEN,
                    payload={
                        "prompt": (
                            "What should provenance records include for AI outputs?"
                        ),
                        "output": PROBE_OUTPUT,
                        "gross_revenue": "1.00",
                    },
                )
                display_text = str(
                    response.get("display", {}).get("rendered_text", "")
                )
                response_verification = verify_service_response(
                    response,
                    display_text=display_text,
                    display_text_path="quickstart-copied-output.txt",
                )
                audit_verification = verify_service_audit_log(
                    audit_log,
                    expected_count=1,
                )
            finally:
                if previous_token_hash is None:
                    os.environ.pop("RDLLM_SERVICE_TOKEN_SHA256", None)
                else:
                    os.environ["RDLLM_SERVICE_TOKEN_SHA256"] = previous_token_hash
    except Exception as exc:
        probe_exception = f"{type(exc).__name__}: {exc}"
        errors.append(f"rootless_probe.exception: {probe_exception}")

    if not probe_exception:
        if manifest.get("status") != "ready":
            errors.append(
                "rootless_probe.bootstrap: expected ready, got "
                f"{manifest.get('status')}"
            )
        if bootstrap_verification.get("status") != "passed":
            errors.append("rootless_probe.bootstrap_verification: failed")
        if not audit_log_bound:
            errors.append("rootless_probe.audit_log_path: service config is not bound")
        if not status_line.startswith("200"):
            errors.append(
                "rootless_probe.attribute_status: expected 200, got "
                f"{status_line}"
            )
        if response.get("status") != "ready":
            errors.append(
                "rootless_probe.response_status: expected ready, got "
                f"{response.get('status')}"
            )
        if response_verification.get("status") != "passed":
            errors.append("rootless_probe.response_verification: failed")
        if not response_verification.get("production_display_ready"):
            errors.append("rootless_probe.production_display_ready: expected true")
        if audit_verification.get("status") != "passed":
            errors.append("rootless_probe.audit_verification: failed")
        if audit_verification.get("ready_entry_count") != 1:
            errors.append("rootless_probe.audit_log: expected one ready entry")

        nested_errors = (
            bootstrap_verification.get("errors", [])
            + response_verification.get("errors", [])
            + audit_verification.get("errors", [])
        )
        errors.extend(f"rootless_probe.detail: {error}" for error in nested_errors)

    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "operator_template": manifest.get("summary", {}).get("operator_template", ""),
        "bootstrap_status": manifest.get("status", ""),
        "bootstrap_verification_status": bootstrap_verification.get("status", ""),
        "service_status_line": status_line,
        "response_status": response.get("status", ""),
        "response_verification_status": response_verification.get("status", ""),
        "production_display_ready": bool(
            response_verification.get("production_display_ready")
        ),
        "source_grounding_acceptance": (
            response_verification.get("source_grounding_acceptance", {}).get(
                "status",
                "",
            )
        ),
        "audit_log_bound": audit_log_bound,
        "audit_verification_status": audit_verification.get("status", ""),
        "audit_entry_count": audit_verification.get("entry_count", 0),
        "audit_ready_entry_count": audit_verification.get("ready_entry_count", 0),
        "exception": probe_exception,
    }


def audit(path: Path = QUICKSTART, *, runtime_probe: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for term in REQUIRED_TERMS:
        if term not in text:
            errors.append(f"missing required quickstart term: {term}")
    for term in BANNED_TERMS:
        if term in text:
            errors.append(f"quickstart should be rootless/copyable; found: {term}")
    rootless_probe = _rootless_probe() if runtime_probe else {"status": "skipped"}
    errors.extend(rootless_probe.get("errors", []))
    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "path": path.relative_to(ROOT).as_posix(),
        "required_term_count": len(REQUIRED_TERMS),
        "banned_term_count": len(BANNED_TERMS),
        "rootless_probe": rootless_probe,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"adopter_quickstart_audit status: {report['status']}",
        f"path: {report.get('path', '')}",
        f"required_term_count: {report.get('required_term_count', 0)}",
        f"banned_term_count: {report.get('banned_term_count', 0)}",
    ]
    rootless_probe = report.get("rootless_probe", {})
    if isinstance(rootless_probe, dict):
        lines.append(
            f"rootless_probe_status: {rootless_probe.get('status', 'unknown')}"
        )
        if rootless_probe.get("status") != "skipped":
            lines.extend(
                [
                    "rootless_probe_bootstrap_status: "
                    f"{rootless_probe.get('bootstrap_status', '')}",
                    "rootless_probe_audit_log_bound: "
                    f"{json.dumps(bool(rootless_probe.get('audit_log_bound', False)))}",
                    "rootless_probe_production_display_ready: "
                    f"{json.dumps(bool(rootless_probe.get('production_display_ready', False)))}",
                    "rootless_probe_source_grounding_acceptance: "
                    f"{rootless_probe.get('source_grounding_acceptance', '')}",
                    "rootless_probe_response_verification_status: "
                    f"{rootless_probe.get('response_verification_status', '')}",
                    "rootless_probe_audit_verification_status: "
                    f"{rootless_probe.get('audit_verification_status', '')}",
                    "rootless_probe_audit_entry_count: "
                    f"{rootless_probe.get('audit_entry_count', 0)}",
                ]
            )
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-runtime-probe", action="store_true")
    args = parser.parse_args(argv)
    report = audit(runtime_probe=not args.skip_runtime_probe)
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
