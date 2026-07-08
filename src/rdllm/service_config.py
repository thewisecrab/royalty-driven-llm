"""Create and validate RDLLM service configuration files."""

from __future__ import annotations

import argparse
from importlib import resources
import json
import posixpath
import re
from pathlib import Path
from typing import Any

from rdllm.service import ServiceConfig, ServiceState, load_json, readiness_report


DATA_PACKAGE = "rdllm.data"
SERVICE_SCHEMA_RESOURCE = ("schemas", "service_config.schema.json")
SERVICE_CONFIG_VERIFICATION_SCHEMA = "rdllm-service-config-verification/v1"
SERVICE_CONFIG_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "service_config_verification.schema.json",
)
TEMPLATE_RESOURCES = {
    "default": ("service_configs", "default.json"),
    "openai_compatible": ("service_configs", "openai_compatible.json"),
    "container": ("service_configs", "container.json"),
}

TOP_LEVEL_FIELDS = {
    "schema",
    "host",
    "port",
    "corpus",
    "creator_pool_rate",
    "top_k",
    "jurisdiction",
    "default_gross_revenue",
    "audit_log_path",
    "auth",
    "limits",
    "artifacts",
    "enforce_registry",
    "providers",
}
REQUIRED_ARTIFACTS = {
    "certification_report",
    "discovery_manifest",
    "provider_attribution_card",
    "production_readiness_report",
    "universal_production_invocation_admission",
    "universal_runtime_conformance_receipt",
    "universal_source_grounded_response_receipt",
}
AUTH_FIELDS = {"mode", "token_sha256_env", "token_sha256"}
LIMIT_FIELDS = {
    "max_request_bytes",
    "max_prompt_chars",
    "max_output_chars",
    "rate_limit_requests_per_window",
    "rate_limit_window_seconds",
}
PROVIDER_FIELDS = {
    "provider_id",
    "family",
    "base_url",
    "model",
    "api_key_env",
    "timeout_seconds",
    "max_response_bytes",
}
ARTIFACT_FILENAMES = {
    "certification_report": "certification_report.json",
    "discovery_manifest": "discovery_manifest.json",
    "provider_attribution_card": "provider_attribution_card.json",
    "production_readiness_report": "production_readiness_report.json",
    "universal_production_invocation_admission": (
        "universal_production_invocation_admission.json"
    ),
    "universal_runtime_conformance_receipt": "universal_runtime_conformance_receipt.json",
    "universal_source_grounded_response_receipt": (
        "universal_source_grounded_response_receipt.json"
    ),
}


def _resource_json(parts: tuple[str, ...]) -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*parts)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_service_schema() -> dict[str, Any]:
    return _resource_json(SERVICE_SCHEMA_RESOURCE)


def load_service_config_verification_schema() -> dict[str, Any]:
    return _resource_json(SERVICE_CONFIG_VERIFICATION_SCHEMA_RESOURCE)


def load_service_template(template: str) -> dict[str, Any]:
    if template not in TEMPLATE_RESOURCES:
        choices = ", ".join(sorted(TEMPLATE_RESOURCES))
        raise ValueError(f"unknown template {template!r}; choose one of: {choices}")
    return _resource_json(TEMPLATE_RESOURCES[template])


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _numeric_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]+(\.[0-9]+)?", value) is not None
    )


def _validate_unknown_fields(
    payload: dict[str, Any],
    allowed: set[str],
    path: str,
) -> list[str]:
    return [f"{path}.{field}: unknown field" for field in sorted(set(payload) - allowed)]


def service_config_schema_errors(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "host",
        "port",
        "corpus",
        "creator_pool_rate",
        "top_k",
        "jurisdiction",
        "default_gross_revenue",
        "audit_log_path",
        "auth",
        "limits",
        "artifacts",
    }
    for field in sorted(required - set(config)):
        errors.append(f"<root>.{field}: missing required field")
    errors.extend(_validate_unknown_fields(config, TOP_LEVEL_FIELDS, "<root>"))
    if config.get("schema") != "rdllm-service-config/v1":
        errors.append("<root>.schema: expected 'rdllm-service-config/v1'")
    if not _is_nonempty_string(config.get("host")):
        errors.append("<root>.host: expected non-empty string")
    port = config.get("port")
    if not _is_int(port) or not 1 <= port <= 65535:
        errors.append("<root>.port: expected integer from 1 to 65535")
    for field in ("corpus", "jurisdiction", "audit_log_path"):
        if not _is_nonempty_string(config.get(field)):
            errors.append(f"<root>.{field}: expected non-empty string")
    for field in ("creator_pool_rate", "default_gross_revenue"):
        if not _numeric_string(config.get(field)):
            errors.append(f"<root>.{field}: expected decimal string")
    top_k = config.get("top_k")
    if not _is_int(top_k) or top_k < 1:
        errors.append("<root>.top_k: expected integer >= 1")
    if "enforce_registry" in config and not isinstance(config["enforce_registry"], bool):
        errors.append("<root>.enforce_registry: expected boolean")

    auth = config.get("auth")
    if not isinstance(auth, dict):
        errors.append("<root>.auth: expected object")
    else:
        errors.extend(_validate_unknown_fields(auth, AUTH_FIELDS, "auth"))
        if auth.get("mode") != "shared_token_sha256":
            errors.append("auth.mode: expected 'shared_token_sha256'")
        if not _is_nonempty_string(auth.get("token_sha256_env")):
            errors.append("auth.token_sha256_env: expected non-empty string")
        token_sha256 = auth.get("token_sha256")
        if token_sha256 is not None:
            if (
                not isinstance(token_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", token_sha256) is None
            ):
                errors.append("auth.token_sha256: expected 64 lowercase hex characters")

    limits = config.get("limits")
    if not isinstance(limits, dict):
        errors.append("<root>.limits: expected object")
    else:
        errors.extend(_validate_unknown_fields(limits, LIMIT_FIELDS, "limits"))
        for field in LIMIT_FIELDS:
            value = limits.get(field)
            minimum = 1024 if field in {"max_request_bytes"} else 1
            if not _is_int(value) or value < minimum:
                errors.append(f"limits.{field}: expected integer >= {minimum}")

    artifacts = config.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("<root>.artifacts: expected object")
    else:
        for field in sorted(REQUIRED_ARTIFACTS - set(artifacts)):
            errors.append(f"artifacts.{field}: missing required field")
        errors.extend(_validate_unknown_fields(artifacts, REQUIRED_ARTIFACTS, "artifacts"))
        for field in REQUIRED_ARTIFACTS:
            if field in artifacts and not _is_nonempty_string(artifacts.get(field)):
                errors.append(f"artifacts.{field}: expected non-empty string")

    if "providers" in config:
        providers = config["providers"]
        if not isinstance(providers, list):
            errors.append("<root>.providers: expected array")
        else:
            for index, provider in enumerate(providers):
                path = f"providers[{index}]"
                if not isinstance(provider, dict):
                    errors.append(f"{path}: expected object")
                    continue
                required_provider = {
                    "provider_id",
                    "family",
                    "base_url",
                    "model",
                    "api_key_env",
                }
                for field in sorted(required_provider - set(provider)):
                    errors.append(f"{path}.{field}: missing required field")
                errors.extend(_validate_unknown_fields(provider, PROVIDER_FIELDS, path))
                if provider.get("family") != "openai_compatible_chat":
                    errors.append(f"{path}.family: expected 'openai_compatible_chat'")
                for field in ("provider_id", "base_url", "model", "api_key_env"):
                    if not _is_nonempty_string(provider.get(field)):
                        errors.append(f"{path}.{field}: expected non-empty string")
                timeout = provider.get("timeout_seconds")
                if timeout is not None:
                    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
                        errors.append(f"{path}.timeout_seconds: expected number")
                    elif not 0 < timeout <= 120:
                        errors.append(f"{path}.timeout_seconds: expected > 0 and <= 120")
                max_response_bytes = provider.get("max_response_bytes")
                if max_response_bytes is not None:
                    if not _is_int(max_response_bytes) or max_response_bytes < 1024:
                        errors.append(f"{path}.max_response_bytes: expected integer >= 1024")
    return errors


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_path(directory: str, filename: str) -> str:
    clean = directory.rstrip("/")
    return f"/{filename}" if not clean else posixpath.join(clean, filename)


def _parse_artifact_overrides(rows: list[str] | None) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for row in rows or []:
        if "=" not in row:
            raise ValueError(f"artifact override must be name=path: {row}")
        name, value = row.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name not in REQUIRED_ARTIFACTS:
            choices = ", ".join(sorted(REQUIRED_ARTIFACTS))
            raise ValueError(f"unknown artifact {name!r}; choose one of: {choices}")
        if not value:
            raise ValueError(f"artifact override for {name!r} cannot be empty")
        overrides[name] = value
    return overrides


def _apply_artifact_paths(
    config: dict[str, Any],
    *,
    artifact_dir: str | None = None,
    artifact_overrides: dict[str, str] | None = None,
) -> None:
    if artifact_dir:
        config["artifacts"] = {
            name: _artifact_path(artifact_dir, filename)
            for name, filename in sorted(ARTIFACT_FILENAMES.items())
        }
    if artifact_overrides:
        artifacts = config.setdefault("artifacts", {})
        artifacts.update(artifact_overrides)


def _apply_provider_overrides(
    config: dict[str, Any],
    *,
    provider_id: str | None = None,
    provider_base_url: str | None = None,
    provider_model: str | None = None,
    provider_api_key_env: str | None = None,
) -> None:
    if not any((provider_id, provider_base_url, provider_model, provider_api_key_env)):
        return
    providers = config.get("providers")
    if not isinstance(providers, list) or not providers:
        providers = [
            {
                "provider_id": "operator-provider",
                "family": "openai_compatible_chat",
                "base_url": "https://api.openai.com",
                "model": "replace-with-provider-model",
                "api_key_env": "RDLLM_PROVIDER_API_KEY",
                "timeout_seconds": 30,
                "max_response_bytes": 1000000,
            }
        ]
        config["providers"] = providers
    provider = providers[0]
    if provider_id:
        provider["provider_id"] = provider_id
    if provider_base_url:
        provider["base_url"] = provider_base_url
    if provider_model:
        provider["model"] = provider_model
    if provider_api_key_env:
        provider["api_key_env"] = provider_api_key_env


def create_service_config(
    *,
    template: str,
    host: str | None = None,
    port: int | None = None,
    corpus: str | None = None,
    audit_log_path: str | None = None,
    token_sha256_env: str | None = None,
    creator_pool_rate: str | None = None,
    default_gross_revenue: str | None = None,
    jurisdiction: str | None = None,
    top_k: int | None = None,
    artifact_dir: str | None = None,
    artifact_overrides: dict[str, str] | None = None,
    provider_id: str | None = None,
    provider_base_url: str | None = None,
    provider_model: str | None = None,
    provider_api_key_env: str | None = None,
) -> dict[str, Any]:
    config = load_service_template(template)
    if host:
        config["host"] = host
    if port is not None:
        config["port"] = port
    if corpus:
        config["corpus"] = corpus
    if audit_log_path:
        config["audit_log_path"] = audit_log_path
    if token_sha256_env:
        config.setdefault("auth", {})["token_sha256_env"] = token_sha256_env
    if creator_pool_rate:
        config["creator_pool_rate"] = creator_pool_rate
    if default_gross_revenue:
        config["default_gross_revenue"] = default_gross_revenue
    if jurisdiction:
        config["jurisdiction"] = jurisdiction
    if top_k is not None:
        config["top_k"] = top_k
    _apply_artifact_paths(
        config,
        artifact_dir=artifact_dir,
        artifact_overrides=artifact_overrides,
    )
    _apply_provider_overrides(
        config,
        provider_id=provider_id,
        provider_base_url=provider_base_url,
        provider_model=provider_model,
        provider_api_key_env=provider_api_key_env,
    )
    return config


def service_config_result(
    config: dict[str, Any],
    *,
    root: Path | None = None,
    check_runtime: bool = False,
) -> dict[str, Any]:
    schema_errors = service_config_schema_errors(config)
    runtime: dict[str, Any] | None = None
    runtime_errors: list[str] = []
    if check_runtime and not schema_errors:
        try:
            state = ServiceState.from_config(
                ServiceConfig(raw=config, root=(root or Path.cwd()).resolve())
            )
            runtime = readiness_report(state)
            if runtime["status"] != "ready":
                runtime_errors.extend(
                    f"{row['name']}: {row.get('reason', 'blocked')}"
                    for row in runtime["checks"]
                    if row["status"] != "ready"
                )
        except Exception as exc:  # pragma: no cover - exercised through CLI behavior
            runtime_errors.append(f"runtime readiness failed: {exc}")
    errors = [
        *(f"service config schema: {error}" for error in schema_errors),
        *runtime_errors,
    ]
    return {
        "schema": SERVICE_CONFIG_VERIFICATION_SCHEMA,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "schema_status": "passed" if not schema_errors else "failed",
        "runtime_status": runtime["status"] if runtime else "skipped",
        "service_config": config,
        "runtime_readiness": runtime,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"service_config status: {result['status']}",
        f"schema_status: {result['schema_status']}",
        f"runtime_status: {result['runtime_status']}",
    ]
    if result.get("template_resource"):
        lines.append(f"template_resource: {result['template_resource']}")
    if result.get("config_path"):
        lines.append(f"config_path: {result['config_path']}")
    if result.get("root"):
        lines.append(f"root: {result['root']}")
    if result.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines)


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    print(
        json.dumps(result, indent=2, sort_keys=True)
        if as_json
        else render_text(result)
    )


def create(args: argparse.Namespace) -> int:
    artifact_overrides = _parse_artifact_overrides(args.artifact)
    config = create_service_config(
        template=args.template,
        host=args.host,
        port=args.port,
        corpus=args.corpus,
        audit_log_path=args.audit_log_path,
        token_sha256_env=args.token_sha256_env,
        creator_pool_rate=args.creator_pool_rate,
        default_gross_revenue=args.default_gross_revenue,
        jurisdiction=args.jurisdiction,
        top_k=args.top_k,
        artifact_dir=args.artifact_dir,
        artifact_overrides=artifact_overrides,
        provider_id=args.provider_id,
        provider_base_url=args.provider_base_url,
        provider_model=args.provider_model,
        provider_api_key_env=args.provider_api_key_env,
    )
    if args.output:
        write_json(args.output, config)
    result = service_config_result(
        config,
        root=args.root,
        check_runtime=args.check_runtime,
    )
    result["template_resource"] = "/".join(
        (DATA_PACKAGE, *TEMPLATE_RESOURCES[args.template])
    )
    if args.output:
        result["config_path"] = args.output.as_posix()
    if args.root:
        result["root"] = args.root.as_posix()
    _print_result(result, args.json)
    return 0 if result["status"] == "ready" else 1


def validate(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    result = service_config_result(
        config,
        root=args.root,
        check_runtime=args.check_runtime,
    )
    result["config_path"] = args.config.as_posix()
    if args.root:
        result["root"] = args.root.as_posix()
    _print_result(result, args.json)
    return 0 if result["status"] == "ready" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create",
        help="Create an operator-controlled service config from a packaged template.",
    )
    create_parser.add_argument(
        "--template",
        choices=sorted(TEMPLATE_RESOURCES),
        required=True,
    )
    create_parser.add_argument("--output", type=Path)
    create_parser.add_argument("--host")
    create_parser.add_argument("--port", type=int)
    create_parser.add_argument("--corpus")
    create_parser.add_argument("--audit-log-path")
    create_parser.add_argument("--token-sha256-env")
    create_parser.add_argument("--creator-pool-rate")
    create_parser.add_argument("--default-gross-revenue")
    create_parser.add_argument("--jurisdiction")
    create_parser.add_argument("--top-k", type=int)
    create_parser.add_argument(
        "--artifact-dir",
        help="Set all proof artifact paths to this directory plus canonical filenames.",
    )
    create_parser.add_argument(
        "--artifact",
        action="append",
        help="Override one proof artifact path as name=path. Can be repeated.",
    )
    create_parser.add_argument("--provider-id")
    create_parser.add_argument("--provider-base-url")
    create_parser.add_argument("--provider-model")
    create_parser.add_argument("--provider-api-key-env")
    create_parser.add_argument("--root", type=Path)
    create_parser.add_argument("--check-runtime", action="store_true")
    create_parser.add_argument("--json", action="store_true")
    create_parser.set_defaults(func=create)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an existing service config and optionally run runtime checks.",
    )
    validate_parser.add_argument("--config", type=Path, required=True)
    validate_parser.add_argument("--root", type=Path)
    validate_parser.add_argument("--check-runtime", action="store_true")
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=validate)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
