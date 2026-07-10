"""End-to-end shipping checks for the RDLLM reference repository."""

from __future__ import annotations

import argparse
import compileall
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "compose.yaml",
    "MANIFEST.in",
    "pyproject.toml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/provider_integration.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/pages.yml",
    ".github/workflows/release.yml",
    "docs/index.html",
    "docs/first_5_minutes.md",
    "docs/github_start_here.md",
    "docs/public_explainer.md",
    "docs/project_attribution.md",
    "docs/i18n/en/quickstart.md",
    "docs/i18n/es/quickstart.md",
    "docs/i18n/zh-Hans/quickstart.md",
    "docs/i18n/hi/quickstart.md",
    "docs/i18n/ar/quickstart.md",
    "docs/adopter_quickstart.md",
    "docs/deployment.md",
    "docs/service_api.md",
    "docs/hosting.md",
    "docs/provider_onboarding.md",
    "docs/provider_compatibility_matrix.md",
    "docs/production_readiness.md",
    "docs/operator_runbook.md",
    "docs/release_checklist.md",
    "docs/references.md",
    "docs/mechanism.md",
    "docs/evidence.md",
    "docs/recent_research.md",
    "docs/schemas/production_readiness_profile.schema.json",
    "docs/schemas/deployment_trust_store.schema.json",
    "docs/schemas/production_readiness_report.schema.json",
    "docs/schemas/production_readiness_repository_report.schema.json",
    "docs/schemas/operator_profile_verification.schema.json",
    "docs/schemas/operator_bootstrap_manifest.schema.json",
    "docs/schemas/operator_bootstrap_verification.schema.json",
    "docs/schemas/operator_acceptance_matrix.schema.json",
    "docs/schemas/operator_acceptance_report.schema.json",
    "docs/schemas/operator_acceptance_verification.schema.json",
    "docs/schemas/operator_doctor.schema.json",
    "docs/schemas/operator_launch_gate.schema.json",
    "docs/schemas/operator_recovery_manifest.schema.json",
    "docs/schemas/operator_recovery_verification.schema.json",
    "docs/schemas/operator_support_bundle.schema.json",
    "docs/schemas/service_audit_entry.schema.json",
    "docs/schemas/service_audit_verification.schema.json",
    "docs/schemas/service_attribution_response.schema.json",
    "docs/schemas/service_response_verification.schema.json",
    "docs/schemas/service_source_footer_verification.schema.json",
    "docs/schemas/service_config.schema.json",
    "docs/schemas/service_config_verification.schema.json",
    "artifacts/production_readiness_report.json",
    "examples/service_config.json",
    "examples/service_config.openai_compatible.json",
    "examples/live_use_cases/README.md",
    "examples/api_clients/README.md",
    "examples/production_profiles/company_instruction_only.json",
    "examples/production_profiles/government_escrow_only.json",
    "examples/production_profiles/individual_escrow_only.json",
    "examples/production_profiles/institution_instruction_only.json",
    "examples/production_profiles/public_sector_processor_required.json",
    "src/rdllm/operator_bootstrap.py",
    "src/rdllm/first_run.py",
    "src/rdllm/operator_profile.py",
    "src/rdllm/data/production_profiles/company_instruction_only.json",
    "src/rdllm/data/production_profiles/government_escrow_only.json",
    "src/rdllm/data/production_profiles/individual_escrow_only.json",
    "src/rdllm/data/production_profiles/institution_instruction_only.json",
    "src/rdllm/data/production_profiles/public_sector_processor_required.json",
    "src/rdllm/data/reference_artifacts/certification_report.json",
    "src/rdllm/data/reference_artifacts/discovery_manifest.json",
    "src/rdllm/data/reference_artifacts/production_readiness_report.json",
    "src/rdllm/data/reference_artifacts/provider_attribution_card.json",
    "src/rdllm/data/reference_artifacts/universal_production_invocation_admission.json",
    "src/rdllm/data/reference_artifacts/universal_runtime_conformance_receipt.json",
    "src/rdllm/data/reference_artifacts/universal_source_grounded_response_receipt.json",
    "src/rdllm/data/schemas/production_readiness_profile.schema.json",
    "src/rdllm/data/schemas/deployment_trust_store.schema.json",
    "src/rdllm/data/schemas/production_readiness_repository_report.schema.json",
    "src/rdllm/data/schemas/operator_profile_verification.schema.json",
    "src/rdllm/data/schemas/operator_bootstrap_manifest.schema.json",
    "src/rdllm/data/schemas/operator_bootstrap_verification.schema.json",
    "src/rdllm/data/schemas/operator_acceptance_matrix.schema.json",
    "src/rdllm/data/schemas/operator_acceptance_report.schema.json",
    "src/rdllm/data/schemas/operator_acceptance_verification.schema.json",
    "src/rdllm/data/schemas/operator_doctor.schema.json",
    "src/rdllm/data/schemas/operator_launch_gate.schema.json",
    "src/rdllm/data/schemas/operator_recovery_manifest.schema.json",
    "src/rdllm/data/schemas/operator_recovery_verification.schema.json",
    "src/rdllm/data/schemas/operator_support_bundle.schema.json",
    "src/rdllm/data/schemas/service_audit_entry.schema.json",
    "src/rdllm/data/schemas/service_audit_verification.schema.json",
    "src/rdllm/data/schemas/service_attribution_response.schema.json",
    "src/rdllm/data/schemas/service_response_verification.schema.json",
    "src/rdllm/data/schemas/service_source_footer_verification.schema.json",
    "src/rdllm/data/schemas/service_config_verification.schema.json",
    "src/rdllm/operator_acceptance.py",
    "src/rdllm/operator_acceptance_matrix.py",
    "src/rdllm/operator_doctor.py",
    "src/rdllm/operator_launch_gate.py",
    "src/rdllm/operator_recovery.py",
    "src/rdllm/service_response_verifier.py",
    "src/rdllm/source_footer_verifier.py",
    "src/rdllm/service_audit_verifier.py",
    "src/rdllm/operator_support_bundle.py",
    "src/rdllm/service_config.py",
    "src/rdllm/data/service_configs/container.json",
    "src/rdllm/data/service_configs/default.json",
    "src/rdllm/data/service_configs/openai_compatible.json",
    "src/rdllm/data/schemas/service_config.schema.json",
    "deploy/docker/README.md",
    "deploy/docker/service_config.container.json",
    "deploy/kubernetes/README.md",
    "deploy/kubernetes/kustomization.yaml",
    "deploy/kubernetes/namespace.yaml",
    "deploy/kubernetes/configmap.yaml",
    "deploy/kubernetes/deployment.yaml",
    "deploy/kubernetes/service.yaml",
    "deploy/kubernetes/networkpolicy.yaml",
    "deploy/kubernetes/persistent-volume-claim.yaml",
    "deploy/kubernetes/secret.example.yaml",
    "paper/rdllm_white_paper.md",
    "paper/references.bib",
    "tools/adopter_quickstart_audit.py",
    "tools/build_public_site.py",
    "tools/build_runtime_screenshot_pages.py",
    "tools/artifact_schema_audit.py",
    "tools/deployment_audit.py",
    "tools/docs_link_audit.py",
    "tools/e2e_smoke.py",
    "tools/github_readiness.py",
    "tools/github_docs_readiness_audit.py",
    "tools/hosting_export.py",
    "tools/hosted_surface_audit.py",
    "tools/package_metadata_audit.py",
    "tools/package_smoke.py",
    "tools/operator_acceptance.py",
    "tools/operator_acceptance_matrix.py",
    "tools/operator_bootstrap.py",
    "tools/operator_doctor.py",
    "tools/operator_launch_gate.py",
    "tools/operator_recovery.py",
    "tools/operator_support_bundle.py",
    "tools/operator_profile.py",
    "tools/production_profile_matrix.py",
    "tools/production_readiness.py",
    "tools/provider_live_smoke.py",
    "tools/security_abuse_smoke.py",
    "tools/service_config.py",
    "tools/service_audit_verify.py",
    "tools/service_response_verify.py",
    "tools/source_footer_verify.py",
    "tools/provider_family_audit.py",
    "tools/provider_matrix.py",
    "tools/public_surface_privacy_audit.py",
    "tools/regenerate_reference_artifacts.py",
    "tools/service_load_smoke.py",
    "tools/service_smoke.py",
)

REQUIRED_BINARY_FILES = (
    "examples/live_use_cases/screenshots/first-run.png",
    "examples/live_use_cases/screenshots/cli-answer-sources.png",
    "examples/live_use_cases/screenshots/service-smoke.png",
    "examples/live_use_cases/screenshots/provider-live-smoke.png",
)

SCHEMA_PAIRS = (
    (
        "artifacts/certification_report.json",
        "docs/schemas/certification_report.schema.json",
    ),
    (
        "artifacts/discovery_manifest.json",
        "docs/schemas/discovery_manifest.schema.json",
    ),
    (
        "artifacts/integration_profile.json",
        "docs/schemas/integration_profile.schema.json",
    ),
    (
        "artifacts/provider_attribution_card.json",
        "docs/schemas/provider_attribution_card.schema.json",
    ),
    (
        "artifacts/assurance_bundle.json",
        "docs/schemas/assurance_bundle.schema.json",
    ),
    (
        "artifacts/proof_dependency_graph.json",
        "docs/schemas/proof_dependency_graph.schema.json",
    ),
    (
        "artifacts/universal_provider_meter_normalization_contract.json",
        "docs/schemas/universal_provider_meter_normalization_contract.schema.json",
    ),
    (
        "artifacts/universal_provider_response_state_normalization_contract.json",
        "docs/schemas/universal_provider_response_state_normalization_contract.schema.json",
    ),
    (
        "artifacts/production_readiness_report.json",
        "docs/schemas/production_readiness_report.schema.json",
    ),
    (
        "examples/service_config.json",
        "docs/schemas/service_config.schema.json",
    ),
    (
        "deploy/docker/service_config.container.json",
        "docs/schemas/service_config.schema.json",
    ),
    (
        "examples/service_config.openai_compatible.json",
        "docs/schemas/service_config.schema.json",
    ),
)


def load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def require_files() -> list[str]:
    errors: list[str] = []
    for file_name in REQUIRED_FILES:
        path = ROOT / file_name
        if not path.is_file():
            errors.append(f"missing required file: {file_name}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty required file: {file_name}")
    for file_name in REQUIRED_BINARY_FILES:
        path = ROOT / file_name
        if not path.is_file():
            errors.append(f"missing required binary file: {file_name}")
        elif not path.read_bytes():
            errors.append(f"empty required binary file: {file_name}")
    return errors


def compile_sources() -> bool:
    ok = True
    for directory in ("src", "tests", "tools"):
        ok = compileall.compile_dir(
            ROOT / directory,
            quiet=1,
            force=True,
        ) and ok
    return ok


def validate_schemas() -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema is required for schema validation; install .[dev]"]

    errors: list[str] = []
    for artifact_path, schema_path in SCHEMA_PAIRS:
        artifact = load_json(artifact_path)
        schema = load_json(schema_path)
        validation_errors = sorted(
            Draft202012Validator(schema).iter_errors(artifact),
            key=lambda error: list(error.path),
        )
        for error in validation_errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{artifact_path}:{location}: {error.message}")
    return errors


def validate_artifact_state() -> list[str]:
    errors: list[str] = []
    certification = load_json("artifacts/certification_report.json")
    summary = certification.get("summary", {})
    if summary.get("status") != "passed":
        errors.append("certification report is not passed")
    if summary.get("highest_level") != "RDLLM-L186":
        errors.append("certification report highest_level is not RDLLM-L186")
    if summary.get("failed") != 0:
        errors.append("certification report has failed cases")

    response_state = load_json(
        "artifacts/universal_provider_response_state_normalization_contract.json"
    )
    response_summary = response_state.get("summary", {})
    if response_summary.get("status") != "ready":
        errors.append("L186 response-state contract is not ready")
    if response_summary.get("target_certification_level") != "RDLLM-L186":
        errors.append("L186 response-state contract target level mismatch")

    proof_graph = load_json("artifacts/proof_dependency_graph.json")
    graph_summary = proof_graph.get("summary", {})
    if graph_summary.get("status") != "ready":
        errors.append("proof dependency graph is not ready")

    discovery = load_json("artifacts/discovery_manifest.json")
    discovery_summary = discovery.get("summary", {})
    if discovery_summary.get("status") != "ready":
        errors.append("discovery manifest is not ready")

    l186_hash = response_state.get(
        "universal_provider_response_state_normalization_contract_hash"
    )
    graph_rows = {
        row.get("name"): row
        for row in proof_graph.get("artifacts", [])
        if isinstance(row, dict)
    }
    if (
        graph_rows.get("universal_provider_response_state_normalization_contract", {})
        .get("declared_hash")
        != l186_hash
    ):
        errors.append("proof graph does not bind the current L186 contract hash")

    catalog_rows = {
        row.get("name"): row
        for row in discovery.get("artifact_catalog", [])
        if isinstance(row, dict)
    }
    if (
        catalog_rows.get("universal_provider_response_state_normalization_contract", {})
        .get("declared_hash")
        != l186_hash
    ):
        errors.append("discovery manifest does not bind the current L186 contract hash")

    provider_card = load_json("artifacts/provider_attribution_card.json")
    support = provider_card.get("supported_evidence_channels", {})
    if not support.get("universal_provider_response_state_normalization_contract"):
        errors.append("provider card does not disclose L186 support")

    production = load_json("artifacts/production_readiness_report.json")
    production_summary = production.get("summary", {})
    if production_summary.get("status") != "ready":
        errors.append("production readiness configuration report is not ready")
    if production_summary.get("production_grade_claim_allowed") is not False:
        errors.append("reference profile must not self-authorize production claims")
    if production_summary.get("direct_creator_settlement_allowed") is not False:
        errors.append("reference profile must not self-authorize direct settlement")
    if production_summary.get("external_evidence_status") != "unverified":
        errors.append("reference profile must require external deployment evidence")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-regenerate", action="store_true")
    parser.add_argument("--skip-schema", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args(argv)

    errors = require_files()

    if not compile_sources():
        errors.append("Python source compilation failed")

    if not args.skip_regenerate:
        run([sys.executable, "tools/regenerate_reference_artifacts.py"])
        run([sys.executable, "tools/hosting_export.py", "--write"])

    if not args.skip_schema:
        errors.extend(validate_schemas())
        try:
            run([sys.executable, "tools/artifact_schema_audit.py"])
        except subprocess.CalledProcessError:
            errors.append("public artifact schema audit failed")

    try:
        run([sys.executable, "tools/hosting_export.py", "--check"])
    except subprocess.CalledProcessError:
        errors.append("well-known hosting export is stale")

    try:
        run([sys.executable, "tools/hosted_surface_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("hosted well-known discovery surface failed")

    try:
        run([sys.executable, "tools/public_surface_privacy_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("hosted public privacy audit failed")

    try:
        run([sys.executable, "tools/docs_link_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("documentation link audit failed")

    try:
        run([sys.executable, "tools/github_docs_readiness_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("GitHub docs readiness audit failed")

    try:
        run([sys.executable, "tools/build_public_site.py", "--check"])
    except subprocess.CalledProcessError:
        errors.append("public site build or link audit failed")

    try:
        run([sys.executable, "tools/adopter_quickstart_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("adopter quickstart audit failed")

    try:
        run([sys.executable, "tools/package_metadata_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("package metadata audit failed")

    errors.extend(validate_artifact_state())

    try:
        run([sys.executable, "tools/github_readiness.py"])
    except subprocess.CalledProcessError:
        errors.append("GitHub readiness check failed")

    try:
        with tempfile.TemporaryDirectory(prefix="rdllm-ship-readiness-") as temp_name:
            readiness_report = Path(temp_name) / "repository_readiness.json"
            readiness_verification = (
                Path(temp_name) / "repository_readiness_verification.json"
            )
            run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--write-report",
                    str(readiness_report),
                ]
            )
            run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--verify-report",
                    str(readiness_report),
                    "--write-report",
                    str(readiness_verification),
                ]
            )
    except subprocess.CalledProcessError:
        errors.append("production readiness check failed")

    try:
        run([sys.executable, "tools/production_profile_matrix.py"])
    except subprocess.CalledProcessError:
        errors.append("production profile matrix check failed")

    try:
        run([sys.executable, "tools/deployment_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("deployment template audit failed")

    try:
        run([sys.executable, "tools/provider_matrix.py", "--check"])
    except subprocess.CalledProcessError:
        errors.append("provider compatibility matrix is out of date")

    try:
        run([sys.executable, "tools/provider_family_audit.py"])
    except subprocess.CalledProcessError:
        errors.append("provider family taxonomy audit failed")

    try:
        run([sys.executable, "tools/e2e_smoke.py"])
    except subprocess.CalledProcessError:
        errors.append("end-to-end smoke check failed")

    try:
        run([sys.executable, "tools/service_smoke.py"])
    except subprocess.CalledProcessError:
        errors.append("production service smoke check failed")

    try:
        run([sys.executable, "tools/service_load_smoke.py"])
    except subprocess.CalledProcessError:
        errors.append("production service load smoke check failed")

    try:
        run([sys.executable, "tools/provider_live_smoke.py"])
    except subprocess.CalledProcessError:
        errors.append("provider live smoke check failed")

    try:
        run([sys.executable, "tools/security_abuse_smoke.py"])
    except subprocess.CalledProcessError:
        errors.append("security abuse smoke check failed")

    if not args.skip_package:
        try:
            run([sys.executable, "tools/package_smoke.py"])
        except subprocess.CalledProcessError:
            errors.append("isolated package smoke check failed")

    if not args.skip_tests:
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])

    if errors:
        print("ship_check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("ship_check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
