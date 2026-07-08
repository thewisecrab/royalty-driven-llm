"""GitHub and static-hosting readiness checks for RDLLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from hosting_export import audit as audit_hosting_export
from hosted_surface_audit import audit as audit_hosted_surface
from docs_link_audit import audit as audit_docs_links
from public_surface_privacy_audit import audit as audit_public_surface_privacy


ROOT = Path(__file__).resolve().parents[1]
MAX_GITHUB_FILE_BYTES = 95 * 1024 * 1024
WARN_LARGE_FILE_BYTES = 50 * 1024 * 1024
MAX_DOCS_SITE_BYTES = 150 * 1024 * 1024

IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "src/royalty_driven_llm.egg-info",
}

REQUIRED_GITHUB_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    ".github/workflows/release.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/provider_integration.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/dependabot.yml",
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "compose.yaml",
)

REQUIRED_HOSTING_FILES = (
    "docs/index.html",
    "docs/deployment.md",
    "docs/service_api.md",
    "docs/hosting.md",
    "docs/production_readiness.md",
    "docs/operator_runbook.md",
    "docs/.well-known/rdllm.json",
    "docs/provider_compatibility_matrix.md",
    "docs/release_checklist.md",
    "docs/references.md",
    "deploy/docker/README.md",
    "deploy/docker/service_config.container.json",
    "examples/service_config.openai_compatible.json",
    "deploy/kubernetes/README.md",
    "deploy/kubernetes/kustomization.yaml",
    "deploy/kubernetes/deployment.yaml",
    "deploy/kubernetes/service.yaml",
    "deploy/kubernetes/networkpolicy.yaml",
)

REQUIRED_SOURCE_PACKAGE_RULES = (
    "prune artifacts",
    "prune dist",
    "prune build",
    "recursive-include docs",
    "recursive-include deploy",
    "recursive-include examples",
    "recursive-include paper",
    "recursive-include tests",
    "recursive-include tools",
)

REQUIRED_GITIGNORE_PATTERNS = (
    "__pycache__/",
    "*.py[cod]",
    "dist/",
    "build/",
    "*.egg-info/",
)


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_ignored_path(path: Path) -> bool:
    relative = relpath(path)
    parts = relative.split("/")
    for ignored in IGNORED_DIRS:
        ignored_parts = ignored.split("/")
        if parts[: len(ignored_parts)] == ignored_parts:
            return True
        if ignored in parts:
            return True
    return False


def iter_repository_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not is_ignored_path(path):
            files.append(path)
    return sorted(files)


def file_size(path: Path) -> int:
    return path.stat().st_size


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def required_file_errors() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_GITHUB_FILES + REQUIRED_HOSTING_FILES:
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing GitHub/hosting file: {name}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty GitHub/hosting file: {name}")
    return errors


def size_findings(files: list[Path]) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    large_files: list[dict[str, Any]] = []
    for path in files:
        size = file_size(path)
        if size >= WARN_LARGE_FILE_BYTES:
            large_files.append({"path": relpath(path), "bytes": size})
        if size > MAX_GITHUB_FILE_BYTES:
            errors.append(
                f"file exceeds GitHub-safe limit ({MAX_GITHUB_FILE_BYTES} bytes): "
                f"{relpath(path)} ({size} bytes)"
            )
    return errors, large_files


def docs_site_errors() -> tuple[list[str], int]:
    errors: list[str] = []
    docs = ROOT / "docs"
    total = sum(file_size(path) for path in docs.rglob("*") if path.is_file())
    if total > MAX_DOCS_SITE_BYTES:
        errors.append(
            f"docs site exceeds static-hosting budget: {total} bytes "
            f"> {MAX_DOCS_SITE_BYTES} bytes"
        )
    index = (docs / "index.html").read_text(encoding="utf-8")
    required_links = (
        "provider_compatibility_matrix.md",
        "deployment.md",
        "service_api.md",
        "provider_onboarding.md",
        "production_readiness.md",
        "operator_runbook.md",
        "release_checklist.md",
        "references.md",
        "../paper/rdllm_white_paper.md",
    )
    for link in required_links:
        if link not in index:
            errors.append(f"docs/index.html does not link {link}")
    return errors, total


def workflow_errors() -> list[str]:
    errors: list[str] = []
    ci = read_text(".github/workflows/ci.yml")
    pages = read_text(".github/workflows/pages.yml")
    release = read_text(".github/workflows/release.yml")
    if "tools/ship_check.py" not in ci:
        errors.append("CI workflow does not run tools/ship_check.py")
    if "tools/github_readiness.py" not in ci and "tools/ship_check.py" not in ci:
        errors.append("CI workflow does not reach GitHub readiness checks")
    if "actions/upload-pages-artifact" not in pages or "path: docs" not in pages:
        errors.append("Pages workflow does not upload docs/")
    if "python -m build" not in release:
        errors.append("release workflow does not build the package")
    if "tools/ship_check.py" not in release:
        errors.append("release workflow does not run the ship gate")
    return errors


def source_package_errors() -> list[str]:
    errors: list[str] = []
    manifest = read_text("MANIFEST.in")
    for rule in REQUIRED_SOURCE_PACKAGE_RULES:
        if rule not in manifest:
            errors.append(f"MANIFEST.in missing source package rule: {rule}")
    gitignore = read_text(".gitignore")
    for pattern in REQUIRED_GITIGNORE_PATTERNS:
        if pattern not in gitignore:
            errors.append(f".gitignore missing build/cache pattern: {pattern}")
    return errors


def artifact_errors() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    artifacts = ROOT / "artifacts"
    artifact_files = sorted(artifacts.glob("*.json"))
    required = {
        "certification_report.json",
        "discovery_manifest.json",
        "proof_dependency_graph.json",
        "provider_attribution_card.json",
        "production_readiness_report.json",
        "universal_provider_response_state_normalization_contract.json",
    }
    present = {path.name for path in artifact_files}
    missing = sorted(required - present)
    for name in missing:
        errors.append(f"missing required artifact: artifacts/{name}")
    summary = {
        "artifact_json_count": len(artifact_files),
        "largest_artifact_bytes": max(
            (file_size(path) for path in artifact_files),
            default=0,
        ),
        "required_artifacts_present": not missing,
    }
    return errors, summary


def run_checks() -> dict[str, Any]:
    files = iter_repository_files()
    errors: list[str] = []
    errors.extend(required_file_errors())
    size_errors, large_files = size_findings(files)
    errors.extend(size_errors)
    docs_errors, docs_total = docs_site_errors()
    errors.extend(docs_errors)
    docs_link_report = audit_docs_links()
    if docs_link_report["status"] != "passed":
        errors.extend(
            f"docs link audit: {error}" for error in docs_link_report["errors"]
        )
    hosting_export_report = audit_hosting_export()
    if hosting_export_report["status"] != "passed":
        errors.extend(
            f"hosting export audit: {error}"
            for error in hosting_export_report["errors"]
        )
    hosted_surface_report = audit_hosted_surface()
    if hosted_surface_report["status"] != "passed":
        errors.extend(
            f"hosted surface audit: {error}"
            for error in hosted_surface_report["errors"]
        )
    public_privacy_report = audit_public_surface_privacy()
    if public_privacy_report["status"] != "passed":
        errors.extend(
            f"public privacy audit: {error}"
            for error in public_privacy_report["errors"]
        )
    errors.extend(workflow_errors())
    errors.extend(source_package_errors())
    artifact_check_errors, artifact_summary = artifact_errors()
    errors.extend(artifact_check_errors)

    source_files = [
        path
        for path in files
        if not relpath(path).startswith("artifacts/")
    ]
    return {
        "status": "ready" if not errors else "failed",
        "errors": errors,
        "summary": {
            "repository_file_count": len(files),
            "source_file_count_excluding_artifacts": len(source_files),
            "large_file_count": len(large_files),
            "max_github_file_bytes": MAX_GITHUB_FILE_BYTES,
            "docs_site_bytes": docs_total,
            "docs_link_document_count": docs_link_report["document_count"],
            "docs_checked_local_link_count": docs_link_report[
                "checked_local_link_count"
            ],
            "well_known_export_count": hosting_export_report["export_count"],
            "well_known_export_bytes": hosting_export_report["exported_byte_count"],
            "hosted_artifact_count": hosted_surface_report["hosted_artifact_count"],
            "hosted_schema_count": hosted_surface_report["hosted_schema_count"],
            "public_privacy_hosted_json_count": public_privacy_report[
                "hosted_json_count"
            ],
            "public_privacy_file_count": public_privacy_report["public_file_count"],
            "public_privacy_forbidden_key_count": len(
                public_privacy_report["forbidden_key_findings"]
            ),
            "public_privacy_disclosure_flag_count": len(
                public_privacy_report["disclosure_flag_findings"]
            ),
            "public_privacy_secret_value_count": len(
                public_privacy_report["secret_value_findings"]
            ),
            "public_privacy_file_secret_count": len(
                public_privacy_report["public_file_secret_findings"]
            ),
            **artifact_summary,
        },
        "large_files": large_files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full readiness report as JSON.",
    )
    args = parser.parse_args(argv)

    report = run_checks()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"github_readiness status: {report['status']}")
        for key, value in report["summary"].items():
            print(f"{key}: {value}")
        if report["large_files"]:
            print("large_files:")
            for row in report["large_files"]:
                print(f"- {row['path']} ({row['bytes']} bytes)")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
