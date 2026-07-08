"""Audit RDLLM container and orchestrator deployment templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "compose.yaml",
    "deploy/docker/README.md",
    "deploy/docker/service_config.container.json",
    "examples/service_config.openai_compatible.json",
    "deploy/kubernetes/README.md",
    "deploy/kubernetes/kustomization.yaml",
    "deploy/kubernetes/namespace.yaml",
    "deploy/kubernetes/configmap.yaml",
    "deploy/kubernetes/deployment.yaml",
    "deploy/kubernetes/service.yaml",
    "deploy/kubernetes/networkpolicy.yaml",
    "deploy/kubernetes/persistent-volume-claim.yaml",
    "deploy/kubernetes/secret.example.yaml",
)


def read_text(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def require_contains(
    errors: list[str], relpath: str, text: str, required: list[str]
) -> None:
    for item in required:
        if item not in text:
            errors.append(f"{relpath} missing required text: {item}")


def require_absent(
    errors: list[str], relpath: str, text: str, forbidden: list[str]
) -> None:
    for item in forbidden:
        if item in text:
            errors.append(f"{relpath} contains forbidden text: {item}")


def audit_required_files() -> list[str]:
    errors: list[str] = []
    for relpath in REQUIRED_FILES:
        path = ROOT / relpath
        if not path.is_file():
            errors.append(f"missing deployment file: {relpath}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty deployment file: {relpath}")
    return errors


def audit_dockerfile() -> list[str]:
    errors: list[str] = []
    relpath = "Dockerfile"
    text = read_text(relpath)
    require_contains(
        errors,
        relpath,
        text,
        [
            "FROM python:3.12-slim",
            "USER rdllm",
            "EXPOSE 8765",
            "HEALTHCHECK",
            "/readyz",
            "rdllm-service",
            "RDLLM_SERVICE_CONFIG",
        ],
    )
    require_absent(errors, relpath, text, ["RDLLM_SERVICE_TOKEN_SHA256="])
    return errors


def audit_compose() -> list[str]:
    errors: list[str] = []
    relpath = "compose.yaml"
    text = read_text(relpath)
    require_contains(
        errors,
        relpath,
        text,
        [
            "RDLLM_SERVICE_TOKEN_SHA256: ${RDLLM_SERVICE_TOKEN_SHA256:?",
            "read_only: true",
            "cap_drop:",
            "- ALL",
            "no-new-privileges:true",
            "rdllm_audit:/var/lib/rdllm/audit",
            "/readyz",
        ],
    )
    return errors


def audit_env_example() -> list[str]:
    errors: list[str] = []
    relpath = ".env.example"
    text = read_text(relpath)
    if "rdllm-local-dev-token" in text:
        errors.append(".env.example must not contain a raw local development token")
    if not re.search(r"RDLLM_SERVICE_TOKEN_SHA256=.*sha256", text):
        errors.append(".env.example must document token hash, not raw token")
    return errors


def audit_service_configs() -> list[str]:
    errors: list[str] = []
    for relpath in (
        "examples/service_config.json",
        "deploy/docker/service_config.container.json",
        "examples/service_config.openai_compatible.json",
    ):
        payload = json.loads((ROOT / relpath).read_text(encoding="utf-8"))
        if payload.get("schema") != "rdllm-service-config/v1":
            errors.append(f"{relpath} has wrong service config schema")
        auth = payload.get("auth", {})
        if auth.get("mode") != "shared_token_sha256":
            errors.append(f"{relpath} must use shared_token_sha256 auth")
        if auth.get("token_sha256"):
            errors.append(f"{relpath} must not include an inline token hash")
        if auth.get("token_sha256_env") != "RDLLM_SERVICE_TOKEN_SHA256":
            errors.append(f"{relpath} must read token hash from env")
        limits = payload.get("limits", {})
        if int(limits.get("rate_limit_requests_per_window", 0)) <= 0:
            errors.append(f"{relpath} must enable rate_limit_requests_per_window")
        if int(limits.get("rate_limit_window_seconds", 0)) <= 0:
            errors.append(f"{relpath} must enable rate_limit_window_seconds")
        artifacts = payload.get("artifacts", {})
        required_artifacts = {
            "certification_report",
            "discovery_manifest",
            "provider_attribution_card",
            "production_readiness_report",
            "universal_production_invocation_admission",
            "universal_runtime_conformance_receipt",
            "universal_source_grounded_response_receipt",
        }
        missing = sorted(required_artifacts - set(artifacts))
        if missing:
            errors.append(f"{relpath} missing artifact bindings: {missing}")
        for provider in payload.get("providers", []) or []:
            if provider.get("family") != "openai_compatible_chat":
                errors.append(f"{relpath} provider route has unsupported family")
            if provider.get("api_key_env") == "RDLLM_SERVICE_TOKEN_SHA256":
                errors.append(f"{relpath} provider route reuses service auth token env")
            if "api_key" in provider or "token" in provider:
                errors.append(f"{relpath} provider route must not inline credentials")
    return errors


def audit_kubernetes() -> list[str]:
    errors: list[str] = []
    deployment = read_text("deploy/kubernetes/deployment.yaml")
    require_contains(
        errors,
        "deploy/kubernetes/deployment.yaml",
        deployment,
        [
            "replicas: 2",
            "runAsNonRoot: true",
            "runAsUser: 10001",
            "fsGroup: 10001",
            "seccompProfile:",
            "allowPrivilegeEscalation: false",
            "readOnlyRootFilesystem: true",
            "drop:",
            "- ALL",
            "secretKeyRef:",
            "RDLLM_SERVICE_TOKEN_SHA256",
            "readinessProbe:",
            "/readyz",
            "livenessProbe:",
            "/healthz",
            "persistentVolumeClaim:",
            "claimName: rdllm-audit",
            "resources:",
        ],
    )
    network = read_text("deploy/kubernetes/networkpolicy.yaml")
    require_contains(
        errors,
        "deploy/kubernetes/networkpolicy.yaml",
        network,
        [
            "kind: NetworkPolicy",
            "policyTypes:",
            "Ingress",
            'rdllm.network/access: "true"',
        ],
    )
    require_absent(errors, "deploy/kubernetes/networkpolicy.yaml", network, ["namespaceSelector: {}"])
    kustomization = read_text("deploy/kubernetes/kustomization.yaml")
    if "secret.example.yaml" in kustomization:
        errors.append("kustomization must not apply secret.example.yaml")
    secret = read_text("deploy/kubernetes/secret.example.yaml")
    if "replace-with-64-character-sha256-token-hash" not in secret:
        errors.append("secret.example.yaml must use a placeholder token hash")
    if "rdllm-local-dev-token" in secret:
        errors.append("secret.example.yaml must not contain a raw token")
    return errors


def audit() -> dict[str, Any]:
    errors: list[str] = []
    errors.extend(audit_required_files())
    if not errors:
        errors.extend(audit_dockerfile())
        errors.extend(audit_compose())
        errors.extend(audit_env_example())
        errors.extend(audit_service_configs())
        errors.extend(audit_kubernetes())
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "deployment_file_count": len(REQUIRED_FILES),
        "checked_surfaces": [
            "dockerfile",
            "compose",
            "env_example",
            "service_configs",
            "kubernetes",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"deployment_audit status: {report['status']}")
        print(f"deployment_file_count: {report['deployment_file_count']}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
