"""Build and smoke-test the RDLLM package in an isolated virtual environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"command failed ({joined}):\n{result.stdout}")
    return result.stdout


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _console_script(venv_dir: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def smoke() -> dict[str, Any]:
    try:
        import build  # noqa: F401
    except ImportError as exc:
        return {
            "status": "failed",
            "errors": [f"build is required for package smoke testing: {exc}"],
        }

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="rdllm-package-smoke-") as temp_name:
        temp_dir = Path(temp_name)
        dist_dir = temp_dir / "dist"
        venv_dir = temp_dir / "venv"
        run_dir = temp_dir / "run"
        run_dir.mkdir()

        try:
            _run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--sdist",
                    "--wheel",
                    "--outdir",
                    str(dist_dir),
                ],
                cwd=ROOT,
            )
            wheels = sorted(dist_dir.glob("royalty_driven_llm-*.whl"))
            sdists = sorted(dist_dir.glob("royalty_driven_llm-*.tar.gz"))
            if not wheels:
                errors.append("package build did not produce a wheel")
            if not sdists:
                errors.append("package build did not produce an sdist")
            if errors:
                return {
                    "status": "failed",
                    "errors": errors,
                    "wheel_count": len(wheels),
                    "sdist_count": len(sdists),
                }
            with tarfile.open(sdists[0], "r:gz") as archive:
                sdist_names = set(archive.getnames())
            required_sdist_suffixes = (
                "Dockerfile",
                "compose.yaml",
                "deploy/docker/service_config.container.json",
                "deploy/kubernetes/deployment.yaml",
                "deploy/kubernetes/kustomization.yaml",
                "docs/schemas/operator_acceptance_matrix.schema.json",
                "docs/schemas/operator_acceptance_report.schema.json",
                "docs/schemas/operator_acceptance_verification.schema.json",
                "docs/schemas/operator_bootstrap_manifest.schema.json",
                "docs/schemas/operator_bootstrap_verification.schema.json",
                "docs/schemas/operator_doctor.schema.json",
                "docs/schemas/operator_launch_gate.schema.json",
                "docs/schemas/operator_recovery_manifest.schema.json",
                "docs/schemas/operator_recovery_verification.schema.json",
                "docs/schemas/operator_profile_verification.schema.json",
                "docs/schemas/operator_support_bundle.schema.json",
                "docs/schemas/service_audit_entry.schema.json",
                "docs/schemas/production_readiness_profile.schema.json",
                "docs/schemas/production_readiness_repository_report.schema.json",
                "docs/schemas/service_audit_verification.schema.json",
                "docs/schemas/service_attribution_response.schema.json",
                "docs/schemas/service_response_verification.schema.json",
                "docs/schemas/service_source_footer_verification.schema.json",
                "docs/schemas/service_config_verification.schema.json",
                "src/rdllm/operator_acceptance.py",
                "src/rdllm/operator_acceptance_matrix.py",
                "src/rdllm/operator_bootstrap.py",
                "src/rdllm/operator_doctor.py",
                "src/rdllm/operator_launch_gate.py",
                "src/rdllm/operator_profile.py",
                "src/rdllm/operator_recovery.py",
                "src/rdllm/operator_support_bundle.py",
                "src/rdllm/service_audit_verifier.py",
                "src/rdllm/service_response_verifier.py",
                "src/rdllm/source_footer_verifier.py",
                "src/rdllm/data/production_profiles/individual_escrow_only.json",
                "src/rdllm/data/production_profiles/company_instruction_only.json",
                "src/rdllm/data/production_profiles/institution_instruction_only.json",
                "src/rdllm/data/production_profiles/government_escrow_only.json",
                "src/rdllm/data/production_profiles/public_sector_processor_required.json",
                "src/rdllm/data/reference_artifacts/certification_report.json",
                "src/rdllm/data/reference_artifacts/discovery_manifest.json",
                "src/rdllm/data/reference_artifacts/production_readiness_report.json",
                "src/rdllm/data/reference_artifacts/provider_attribution_card.json",
                "src/rdllm/data/reference_artifacts/universal_production_invocation_admission.json",
                "src/rdllm/data/reference_artifacts/universal_runtime_conformance_receipt.json",
                "src/rdllm/data/reference_artifacts/universal_source_grounded_response_receipt.json",
                "src/rdllm/data/schemas/operator_bootstrap_manifest.schema.json",
                "src/rdllm/data/schemas/operator_bootstrap_verification.schema.json",
                "src/rdllm/data/schemas/operator_acceptance_matrix.schema.json",
                "src/rdllm/data/schemas/operator_acceptance_report.schema.json",
                "src/rdllm/data/schemas/operator_acceptance_verification.schema.json",
                "src/rdllm/data/schemas/operator_doctor.schema.json",
                "src/rdllm/data/schemas/operator_launch_gate.schema.json",
                "src/rdllm/data/schemas/operator_recovery_manifest.schema.json",
                "src/rdllm/data/schemas/operator_recovery_verification.schema.json",
                "src/rdllm/data/schemas/operator_profile_verification.schema.json",
                "src/rdllm/data/schemas/operator_support_bundle.schema.json",
                "src/rdllm/data/schemas/service_audit_entry.schema.json",
                "src/rdllm/data/schemas/production_readiness_profile.schema.json",
                "src/rdllm/data/schemas/production_readiness_repository_report.schema.json",
                "src/rdllm/data/schemas/service_audit_verification.schema.json",
                "src/rdllm/data/schemas/service_attribution_response.schema.json",
                "src/rdllm/data/schemas/service_response_verification.schema.json",
                "src/rdllm/data/schemas/service_source_footer_verification.schema.json",
                "src/rdllm/data/schemas/service_config_verification.schema.json",
                "src/rdllm/service_config.py",
                "src/rdllm/data/service_configs/container.json",
                "src/rdllm/data/service_configs/default.json",
                "src/rdllm/data/service_configs/openai_compatible.json",
                "src/rdllm/data/schemas/service_config.schema.json",
                "tools/adopter_quickstart_audit.py",
                "tools/operator_bootstrap.py",
                "tools/operator_doctor.py",
                "tools/operator_launch_gate.py",
                "tools/operator_acceptance.py",
                "tools/operator_acceptance_matrix.py",
                "tools/operator_profile.py",
                "tools/package_metadata_audit.py",
                "tools/operator_recovery.py",
                "tools/operator_support_bundle.py",
                "tools/service_audit_verify.py",
                "tools/service_config.py",
                "tools/service_response_verify.py",
                "tools/source_footer_verify.py",
                "examples/production_profiles/individual_escrow_only.json",
                "examples/production_profiles/company_instruction_only.json",
                "examples/production_profiles/institution_instruction_only.json",
                "examples/production_profiles/government_escrow_only.json",
                "examples/production_profiles/public_sector_processor_required.json",
                "examples/service_config.openai_compatible.json",
            )
            for suffix in required_sdist_suffixes:
                if not any(name.endswith(suffix) for name in sdist_names):
                    errors.append(f"sdist missing deployment file: {suffix}")
            if errors:
                return {
                    "status": "failed",
                    "errors": errors,
                    "wheel": wheels[0].name,
                    "sdist": sdists[0].name,
                }

            _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=ROOT)
            python = _venv_python(venv_dir)
            rdllm = _console_script(venv_dir, "rdllm")
            rdllm_first_run = _console_script(venv_dir, "rdllm-first-run")
            rdllm_operator_acceptance = _console_script(
                venv_dir,
                "rdllm-operator-acceptance",
            )
            rdllm_operator_acceptance_matrix = _console_script(
                venv_dir,
                "rdllm-operator-acceptance-matrix",
            )
            rdllm_operator_bootstrap = _console_script(
                venv_dir,
                "rdllm-operator-bootstrap",
            )
            rdllm_operator_doctor = _console_script(
                venv_dir,
                "rdllm-operator-doctor",
            )
            rdllm_operator_launch_gate = _console_script(
                venv_dir,
                "rdllm-operator-launch-gate",
            )
            rdllm_operator_profile = _console_script(
                venv_dir,
                "rdllm-operator-profile",
            )
            rdllm_operator_recovery = _console_script(
                venv_dir,
                "rdllm-operator-recovery",
            )
            rdllm_operator_support_bundle = _console_script(
                venv_dir,
                "rdllm-operator-support-bundle",
            )
            rdllm_production_readiness_verify = _console_script(
                venv_dir,
                "rdllm-production-readiness-verify",
            )
            rdllm_service_audit_verify = _console_script(
                venv_dir,
                "rdllm-service-audit-verify",
            )
            rdllm_service_config = _console_script(venv_dir, "rdllm-service-config")
            rdllm_service_response_verify = _console_script(
                venv_dir,
                "rdllm-service-response-verify",
            )
            rdllm_source_footer_verify = _console_script(
                venv_dir,
                "rdllm-source-footer-verify",
            )
            rdllm_service = _console_script(venv_dir, "rdllm-service")
            _run(
                [str(python), "-m", "pip", "install", str(wheels[0])],
                cwd=run_dir,
            )

            import_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "import rdllm; "
                        "from importlib.metadata import version; "
                        "print(version('royalty-driven-llm'))"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            support_bundle_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_support_bundle import "
                        "load_support_bundle_schema; "
                        "schema = load_support_bundle_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            doctor_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_doctor import load_doctor_schema; "
                        "schema = load_doctor_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            profile_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_profile import "
                        "load_profile_schema, "
                        "load_profile_verification_schema; "
                        "profile = load_profile_schema(); "
                        "verification = load_profile_verification_schema(); "
                        "print(profile['properties']['schema']['const'] + '|' + "
                        "verification['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            repository_readiness_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.production_readiness import "
                        "load_repository_report_schema; "
                        "schema = load_repository_report_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            bootstrap_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_bootstrap import "
                        "load_bootstrap_schema, "
                        "load_bootstrap_verification_schema; "
                        "manifest = load_bootstrap_schema(); "
                        "verification = load_bootstrap_verification_schema(); "
                        "print(manifest['properties']['schema']['const'] + '|' + "
                        "verification['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            launch_gate_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_launch_gate import "
                        "load_launch_gate_schema; "
                        "schema = load_launch_gate_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            acceptance_verification_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_acceptance import "
                        "load_acceptance_verification_schema; "
                        "schema = load_acceptance_verification_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            acceptance_matrix_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_acceptance_matrix import "
                        "load_acceptance_matrix_schema; "
                        "schema = load_acceptance_matrix_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            source_footer_verification_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.source_footer_verifier import "
                        "load_source_footer_verification_schema; "
                        "schema = load_source_footer_verification_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            recovery_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.operator_recovery import "
                        "load_recovery_manifest_schema, "
                        "load_recovery_verification_schema; "
                        "manifest = load_recovery_manifest_schema(); "
                        "verification = load_recovery_verification_schema(); "
                        "print(manifest['properties']['schema']['const'] + '|' + "
                        "verification['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            audit_verification_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.service_audit_verifier import "
                        "load_audit_entry_schema, "
                        "load_audit_verification_schema; "
                        "entry = load_audit_entry_schema(); "
                        "verification = load_audit_verification_schema(); "
                        "print(entry['properties']['schema']['const'] + '|' + "
                        "verification['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            response_verification_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.service_response_verifier import "
                        "load_response_verification_schema; "
                        "schema = load_response_verification_schema(); "
                        "print(schema['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            service_config_schema_output = _run(
                [
                    str(python),
                    "-c",
                    (
                        "from rdllm.service_config import "
                        "load_service_schema, "
                        "load_service_config_verification_schema; "
                        "config = load_service_schema(); "
                        "verification = load_service_config_verification_schema(); "
                        "print(config['properties']['schema']['const'] + '|' + "
                        "verification['properties']['schema']['const'])"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            help_output = _run([str(rdllm), "--help"], cwd=run_dir)
            first_run_output = _run([str(rdllm_first_run)], cwd=run_dir)
            service_help_output = _run([str(rdllm_service), "--help"], cwd=run_dir)
            ledger_path = run_dir / "installed_demo_ledger.json"
            demo_output = _run(
                [str(rdllm), "demo", "--ledger", str(ledger_path)],
                cwd=run_dir,
            )
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            profile_path = run_dir / "installed_operator_profile.json"
            report_path = run_dir / "installed_operator_report.json"
            operator_profile_output = _run(
                [
                    str(rdllm_operator_profile),
                    "create",
                    "--template",
                    "company",
                    "--operator-name",
                    "Installed RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--output",
                    str(profile_path),
                    "--write-report",
                    str(report_path),
                ],
                cwd=run_dir,
            )
            operator_profile = json.loads(profile_path.read_text(encoding="utf-8"))
            operator_report = json.loads(report_path.read_text(encoding="utf-8"))
            service_config_path = run_dir / "installed_service_config.json"
            service_config_output = _run(
                [
                    str(rdllm_service_config),
                    "create",
                    "--template",
                    "default",
                    "--corpus",
                    "operator_corpus.json",
                    "--artifact-dir",
                    "/srv/rdllm/artifacts",
                    "--provider-id",
                    "installed-provider",
                    "--provider-base-url",
                    "https://provider.example",
                    "--provider-model",
                    "installed-model",
                    "--provider-api-key-env",
                    "INSTALLED_PROVIDER_KEY",
                    "--output",
                    str(service_config_path),
                ],
                cwd=run_dir,
            )
            service_config = json.loads(service_config_path.read_text(encoding="utf-8"))
            repository_readiness_path = run_dir / "installed_repository_readiness.json"
            repository_verification_path = (
                run_dir / "installed_repository_readiness_verification.json"
            )
            _run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--write-report",
                    str(repository_readiness_path),
                ],
                cwd=ROOT,
            )
            repository_verify_output = _run(
                [
                    str(rdllm_production_readiness_verify),
                    "--report",
                    str(repository_readiness_path),
                    "--write-report",
                    str(repository_verification_path),
                ],
                cwd=run_dir,
            )
            repository_verification = json.loads(
                repository_verification_path.read_text(encoding="utf-8")
            )
            events = ledger.get("events", [])
            if len(events) != 4:
                errors.append(f"installed demo wrote {len(events)} events, expected 4")
            if "Royalty Driven LLM" not in help_output:
                errors.append("console help output did not identify RDLLM")
            for token in (
                "rdllm_first_run status: passed",
                "What just happened:",
                "Generated demo output:",
                "Sources",
                "Claim Evidence",
                "payout=",
                "disagreement=passed",
            ):
                if token not in first_run_output:
                    errors.append(f"first-run console output missing {token!r}")
            if "production service boundary" not in service_help_output:
                errors.append("service console help output did not identify service")
            if "events" not in demo_output:
                errors.append("console demo output did not include ledger events")
            if "operator_profile status: ready" not in operator_profile_output:
                errors.append("operator profile console did not report ready status")
            if (
                "production_readiness_repository_verification status: passed"
                not in repository_verify_output
            ):
                errors.append(
                    "production readiness verifier console did not report passed"
                )
            if repository_verification.get("status") != "passed":
                errors.append("production readiness verifier report did not pass")
            operator_doctor_output = _run(
                [str(rdllm_operator_doctor)],
                cwd=run_dir,
            )
            if "operator_doctor status: passed" not in operator_doctor_output:
                errors.append("operator doctor console did not report passed")
            if (
                "response_source_grounding_acceptance_status: passed"
                not in operator_doctor_output
            ):
                errors.append(
                    "operator doctor console did not report grounded-source acceptance"
                )
            if doctor_schema_output != "rdllm-operator-doctor/v1":
                errors.append("operator doctor schema did not load")
            if (
                profile_schema_output
                != (
                    "rdllm-production-readiness-profile/v1|"
                    "rdllm-operator-profile-verification/v1"
                )
            ):
                errors.append("operator profile schemas did not load")
            if (
                repository_readiness_schema_output
                != "rdllm-production-readiness-repository-report/v1"
            ):
                errors.append("repository production readiness schema did not load")
            if (
                bootstrap_schema_output
                != (
                    "rdllm-operator-bootstrap/v1|"
                    "rdllm-operator-bootstrap-verification/v1"
                )
            ):
                errors.append("operator bootstrap schemas did not load")
            if launch_gate_schema_output != "rdllm-operator-launch-gate/v1":
                errors.append("operator launch gate schema did not load")
            if (
                acceptance_verification_schema_output
                != "rdllm-operator-acceptance-verification/v1"
            ):
                errors.append("operator acceptance verification schema did not load")
            if (
                acceptance_matrix_schema_output
                != "rdllm-operator-acceptance-matrix/v1"
            ):
                errors.append("operator acceptance matrix schema did not load")
            if (
                recovery_schema_output
                != (
                    "rdllm-operator-recovery-manifest/v1|"
                    "rdllm-operator-recovery-verification/v1"
                )
            ):
                errors.append("operator recovery schemas did not load")
            if (
                audit_verification_schema_output
                != (
                    "rdllm-service-audit-entry/v1|"
                    "rdllm-service-audit-verification/v1"
                )
            ):
                errors.append("service audit schemas did not load")
            if (
                response_verification_schema_output
                != "rdllm-service-response-verification/v1"
            ):
                errors.append("service response verification schema did not load")
            if (
                source_footer_verification_schema_output
                != "rdllm-service-source-footer-verification/v1"
            ):
                errors.append("service source footer verification schema did not load")
            if (
                service_config_schema_output
                != (
                    "rdllm-service-config/v1|"
                    "rdllm-service-config-verification/v1"
                )
            ):
                errors.append("service config schemas did not load")
            support_bundle_path = run_dir / "installed_support_bundle.json"
            operator_support_bundle_output = _run(
                [
                    str(rdllm_operator_support_bundle),
                    "--output",
                    str(support_bundle_path),
                ],
                cwd=run_dir,
            )
            if (
                "operator_support_bundle status: passed"
                not in operator_support_bundle_output
            ):
                errors.append("operator support bundle console did not report passed")
            if (
                support_bundle_schema_output
                != "rdllm-operator-support-bundle/v1"
            ):
                errors.append("operator support bundle schema did not load")
            support_bundle = json.loads(
                support_bundle_path.read_text(encoding="utf-8")
            )
            if support_bundle.get("status") != "passed":
                errors.append("operator support bundle report is not passed")
            if (
                support_bundle.get("redaction", {}).get("raw_prompts_included")
                is not False
            ):
                errors.append("operator support bundle did not declare prompt redaction")
            if operator_profile["deployment"]["operator_name"] != "Installed RDLLM":
                errors.append("operator profile console did not write operator name")
            if operator_report["summary"]["status"] != "ready":
                errors.append("operator profile console did not write a ready report")
            if (
                operator_report["summary"]["direct_creator_settlement_allowed"]
                is not False
            ):
                errors.append("company instruction-only profile allowed direct settlement")
            bootstrap_dir = run_dir / "installed_operator_bootstrap"
            bootstrap_output = _run(
                [
                    str(rdllm_operator_bootstrap),
                    "--output-dir",
                    str(bootstrap_dir),
                    "--operator-template",
                    "company",
                    "--operator-name",
                    "Installed RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--include-sample-corpus",
                    "--include-reference-artifacts",
                ],
                cwd=run_dir,
            )
            bootstrap_manifest = json.loads(
                (bootstrap_dir / "operator_bootstrap_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            bootstrap_verify_output = _run(
                [
                    str(rdllm_operator_bootstrap),
                    "--verify-dir",
                    str(bootstrap_dir),
                ],
                cwd=run_dir,
            )
            response_path = run_dir / "installed_service_response.json"
            display_text_path = run_dir / "installed_service_display.txt"
            _run(
                [
                    str(python),
                    "-c",
                    (
                        "import json; "
                        "from pathlib import Path; "
                        "from rdllm.service import ServiceConfig, ServiceState, "
                        "_attribute, load_json; "
                        f"root = Path({str(bootstrap_dir)!r}); "
                        "config = load_json(root / 'service_config.json'); "
                        "state = ServiceState.from_config(ServiceConfig(raw=config, root=root)); "
                        "status, response = _attribute(state, {"
                        "'prompt': 'What should royalty-bearing AI answers expose?', "
                        "'output': "
                        "'Every royalty bearing AI answer should have a provenance "
                        "record. The record should include source identifiers, "
                        "content hashes, retrieval scores, output citations, payout "
                        "weights, and an event hash that allows auditors to replay "
                        "the attribution.', "
                        "'gross_revenue': '1.00'}); "
                        "Path('installed_service_response.json').write_text("
                        "json.dumps(response), encoding='utf-8'); "
                        "Path('installed_service_display.txt').write_text("
                        "response['display']['rendered_text'], encoding='utf-8'); "
                        "print(status)"
                    ),
                ],
                cwd=run_dir,
            )
            response_verify_output = _run(
                [
                    str(rdllm_service_response_verify),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                ],
                cwd=run_dir,
            )
            installed_response = json.loads(response_path.read_text(encoding="utf-8"))
            installed_footer = installed_response.get("source_footer", {})
            source_footer_path = run_dir / "installed_service_source_footer.json"
            source_footer_path.write_text(
                json.dumps(installed_footer, sort_keys=True),
                encoding="utf-8",
            )
            source_footer_verify_output = _run(
                [
                    str(rdllm_source_footer_verify),
                    "--footer",
                    str(source_footer_path),
                    "--display-text",
                    str(display_text_path),
                ],
                cwd=run_dir,
            )
            tampered_response_path = (
                run_dir / "installed_tampered_service_response.json"
            )
            _run(
                [
                    str(python),
                    "-c",
                    (
                        "import json; "
                        "from pathlib import Path; "
                        "from rdllm.service import canonical_hash, load_json; "
                        "response = load_json('installed_service_response.json'); "
                        "row = response['source_footer']['source_rows'][0]; "
                        "row['minimum_support_score'] = 0.0 "
                        "if row['minimum_support_score'] != 0.0 else 1.0; "
                        "row['row_hash'] = canonical_hash(row); "
                        "footer = response['source_footer']; "
                        "footer['footer_hash'] = canonical_hash({"
                        "key: value for key, value in footer.items() "
                        "if key != 'footer_hash'}); "
                        "response['summary']['source_footer_hash'] = "
                        "footer['footer_hash']; "
                        "response['display']['source_footer_hash'] = "
                        "footer['footer_hash']; "
                        "Path('installed_tampered_service_response.json')"
                        ".write_text(json.dumps(response), encoding='utf-8')"
                    ),
                ],
                cwd=run_dir,
            )
            tampered_response_verify = subprocess.run(
                [
                    str(rdllm_service_response_verify),
                    "--response",
                    str(tampered_response_path),
                ],
                cwd=run_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            audit_path = run_dir / "installed_service_audit.jsonl"
            _run(
                [
                    str(python),
                    "-c",
                    (
                        "import json; "
                        "from pathlib import Path; "
                        "from rdllm.service import canonical_hash, load_json; "
                        "response = load_json('installed_service_response.json'); "
                        "event = response['event']; "
                        "entry = {"
                        "'schema': 'rdllm-service-audit-entry/v1', "
                        "'request_id': 'installed-package-smoke', "
                        "'timestamp': '2026-07-01T00:00:00Z', "
                        "'status': response['status'], "
                        "'event_id': event['event_id'], "
                        "'event_hash': event['event_hash'], "
                        "'source_footer_hash': response['summary']['source_footer_hash'], "
                        "'display_hash': response['summary']['display_hash'], "
                        "'source_count': len(event.get('source_references', [])), "
                        "'audit_error_count': len(response.get('audit_errors', [])), "
                        "'previous_entry_hash': ''"
                        "}; "
                        "entry['entry_hash'] = canonical_hash(entry); "
                        "Path('installed_service_audit.jsonl').write_text("
                        "json.dumps(entry, sort_keys=True) + '\\n', encoding='utf-8')"
                    ),
                ],
                cwd=run_dir,
            )
            audit_verify_output = _run(
                [
                    str(rdllm_service_audit_verify),
                    "--audit-log",
                    str(audit_path),
                    "--expected-count",
                    "1",
                ],
                cwd=run_dir,
            )
            dirty_audit_path = run_dir / "installed_dirty_service_audit.jsonl"
            _run(
                [
                    str(python),
                    "-c",
                    (
                        "import json; "
                        "from pathlib import Path; "
                        "from rdllm.service import canonical_hash; "
                        "entry = json.loads(Path('installed_service_audit.jsonl')"
                        ".read_text(encoding='utf-8').splitlines()[0]); "
                        "entry['audit_error_count'] = 1; "
                        "entry['entry_hash'] = canonical_hash(entry); "
                        "Path('installed_dirty_service_audit.jsonl').write_text("
                        "json.dumps(entry, sort_keys=True) + '\\n', encoding='utf-8')"
                    ),
                ],
                cwd=run_dir,
            )
            dirty_audit_verify = subprocess.run(
                [
                    str(rdllm_service_audit_verify),
                    "--audit-log",
                    str(dirty_audit_path),
                    "--expected-count",
                    "1",
                ],
                cwd=run_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            launch_gate_report_path = run_dir / "installed_launch_gate_report.json"
            launch_support_bundle_path = (
                run_dir / "installed_launch_support_bundle.json"
            )
            launch_env = os.environ.copy()
            launch_env["RDLLM_SERVICE_TOKEN_SHA256"] = hashlib.sha256(
                b"rdllm-local-dev-token"
            ).hexdigest()
            operator_launch_gate_output = _run(
                [
                    str(rdllm_operator_launch_gate),
                    "--profile",
                    str(bootstrap_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(bootstrap_dir / "service_config.json"),
                    "--service-root",
                    str(bootstrap_dir),
                    "--bootstrap-dir",
                    str(bootstrap_dir),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--write-support-bundle",
                    str(launch_support_bundle_path),
                    "--write-report",
                    str(launch_gate_report_path),
                ],
                cwd=run_dir,
                env=launch_env,
            )
            if "operator_bootstrap status: ready" not in bootstrap_output:
                errors.append("operator bootstrap console did not report ready status")
            if "operator_bootstrap_verification status: passed" not in bootstrap_verify_output:
                errors.append("operator bootstrap verify console did not report passed")
            if "service_response_verification status: passed" not in response_verify_output:
                errors.append("service response verify console did not report passed")
            if "production_display_ready: true" not in response_verify_output:
                errors.append("service response verify did not report display ready")
            if "source_grounding_acceptance: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report grounded-source acceptance"
                )
            if "source_usage_metric_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report source usage metrics passed"
                )
            if (
                "source_usage_metric_provenance_status: passed"
                not in response_verify_output
            ):
                errors.append(
                    "service response verify did not report source usage metric "
                    "provenance passed"
                )
            if "source_locator_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report source locators passed"
                )
            if "source_identity_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report source identity passed"
                )
            if "temporal_grounding_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report temporal grounding passed"
                )
            if "answer_link_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report answer link status"
                )
            if "unresolved_answer_link_uris:" not in response_verify_output:
                errors.append(
                    "service response verify did not report answer link URI list"
                )
            if "claim_evidence_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report claim evidence passed"
                )
            if "claim_warrant_strength_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report claim warrant strength "
                    "passed"
                )
            if "claim_source_disagreement_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report claim source "
                    "disagreement passed"
                )
            if "claim_source_closure_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report claim-source closure passed"
                )
            if "answer_claim_coverage_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report answer claim coverage passed"
                )
            if "model_reliance_claim_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report model reliance claim status"
                )
            if "attribution_gap_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report attribution gap passed"
                )
            if "answer_citation_marker_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report answer citation marker status"
                )
            if "unresolved_answer_citation_markers:" not in response_verify_output:
                errors.append(
                    "service response verify did not report answer citation marker list"
                )
            if "display_text_status: passed" not in response_verify_output:
                errors.append(
                    "service response verify did not report copied display text passed"
                )
            if (
                "service_source_footer_verification status: passed"
                not in source_footer_verify_output
            ):
                errors.append("source footer verify console did not report passed")
            if "copied_display_footer_ready: true" not in source_footer_verify_output:
                errors.append("source footer verify did not report copied footer ready")
            if (
                "source_usage_metric_provenance_status: passed"
                not in source_footer_verify_output
            ):
                errors.append(
                    "source footer verify did not report source usage metric "
                    "provenance passed"
                )
            if (
                "claim_warrant_strength_status: passed"
                not in source_footer_verify_output
            ):
                errors.append(
                    "source footer verify did not report claim warrant strength "
                    "passed"
                )
            if (
                "claim_source_disagreement_status: passed"
                not in source_footer_verify_output
            ):
                errors.append(
                    "source footer verify did not report claim source disagreement "
                    "passed"
                )
            if not all(
                row.get("verification_handle")
                for row in installed_footer.get("source_rows", [])
                if isinstance(row, dict)
            ):
                errors.append("installed response source rows lack verification handles")
            if "verify=rdllm://verify/source-footer/" not in str(
                installed_footer.get("rendered_text", "")
            ):
                errors.append("installed response footer did not render verification handles")
            rendered_footer = str(installed_footer.get("rendered_text", ""))
            for token in (
                "support=",
                "text_match=",
                "weight=",
                "payout=",
                "metrics=rdllm-observable-source-usage-metrics/v1",
                "scope=observable_support_allocation_not_model_internal_reliance",
                "methods=support:rdllm-claim-overlap-support/v1",
                "warrant=passed",
                "disagreement=passed",
                "conflicts=none",
                "profile=rdllm-evidence-force-calibration/v1",
                "disagreement_profile=rdllm-visible-source-disagreement/v1",
                "Claim:",
            ):
                if token not in rendered_footer:
                    errors.append(
                        f"installed response footer did not render {token.rstrip('=')}"
                    )
            if tampered_response_verify.returncode == 0:
                errors.append("service response verify allowed tampered footer semantics")
            if (
                "minimum_support_score: does not match supported claim rows"
                not in tampered_response_verify.stdout
            ):
                errors.append(
                    "service response verify did not explain tampered footer semantics"
                )
            if "production_display_ready: false" not in tampered_response_verify.stdout:
                errors.append(
                    "service response verify reported tampered response display-ready"
                )
            if "service_audit_verification status: passed" not in audit_verify_output:
                errors.append("service audit verify console did not report passed")
            if dirty_audit_verify.returncode == 0:
                errors.append("service audit verify allowed dirty ready audit entry")
            if (
                "ready entry must have zero audit errors"
                not in dirty_audit_verify.stdout
            ):
                errors.append("service audit verify did not explain dirty ready entry")
            if "operator_launch_gate status: ready" not in operator_launch_gate_output:
                errors.append("operator launch gate console did not report ready")
            if "display_text_status: passed" not in operator_launch_gate_output:
                errors.append("operator launch gate did not verify copied display text")
            launch_gate_report = json.loads(
                launch_gate_report_path.read_text(encoding="utf-8")
            )
            if launch_gate_report.get("summary", {}).get("traffic_decision") != "allow":
                errors.append("operator launch gate did not allow ready traffic")
            if not launch_support_bundle_path.is_file():
                errors.append("operator launch gate did not write support bundle")
            blocked_response_path = run_dir / "installed_blocked_service_response.json"
            blocked_display_text_path = (
                run_dir / "installed_blocked_service_display.txt"
            )
            blocked_generation_status = _run(
                [
                    str(python),
                    "-c",
                    (
                        "import json; "
                        "from pathlib import Path; "
                        "from rdllm.service import ServiceConfig, ServiceState, "
                        "_attribute, load_json; "
                        f"root = Path({str(bootstrap_dir)!r}); "
                        "config = load_json(root / 'service_config.json'); "
                        "state = ServiceState.from_config("
                        "ServiceConfig(raw=config, root=root)); "
                        "status, response = _attribute(state, {"
                        "'prompt': 'What should royalty-bearing AI answers expose?', "
                        "'output': 'The moon is made of green cheese and every "
                        "library must pay royalties to unrelated fictional parties.', "
                        "'gross_revenue': '1.00'}); "
                        "Path('installed_blocked_service_response.json').write_text("
                        "json.dumps(response), encoding='utf-8'); "
                        "Path('installed_blocked_service_display.txt').write_text("
                        "response['display']['rendered_text'], encoding='utf-8'); "
                        "print(status)"
                    ),
                ],
                cwd=run_dir,
            ).strip()
            if blocked_generation_status != "422":
                errors.append("blocked response fixture did not return HTTP 422")
            blocked_launch = subprocess.run(
                [
                    str(rdllm_operator_launch_gate),
                    "--profile",
                    str(bootstrap_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(bootstrap_dir / "service_config.json"),
                    "--service-root",
                    str(bootstrap_dir),
                    "--bootstrap-dir",
                    str(bootstrap_dir),
                    "--response",
                    str(blocked_response_path),
                    "--display-text",
                    str(blocked_display_text_path),
                ],
                cwd=run_dir,
                env=launch_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if blocked_launch.returncode == 0:
                errors.append("operator launch gate allowed a blocked response")
            if "operator_launch_gate status: blocked" not in blocked_launch.stdout:
                errors.append("operator launch gate did not report blocked response")
            if (
                "response.status: expected ready for production display, got blocked"
                not in blocked_launch.stdout
            ):
                errors.append("operator launch gate did not explain blocked response")
            recovery_manifest_path = run_dir / "installed_recovery_manifest.json"
            recovery_create_output = _run(
                [
                    str(rdllm_operator_recovery),
                    "create",
                    "--root",
                    str(bootstrap_dir),
                    "--output",
                    str(recovery_manifest_path),
                ],
                cwd=run_dir,
            )
            recovery_verify_output = _run(
                [
                    str(rdllm_operator_recovery),
                    "verify",
                    "--manifest",
                    str(recovery_manifest_path),
                    "--root",
                    str(bootstrap_dir),
                ],
                cwd=run_dir,
            )
            if "operator_recovery_manifest status: ready" not in recovery_create_output:
                errors.append("operator recovery create did not report ready")
            if (
                "operator_recovery_verification status: passed"
                not in recovery_verify_output
            ):
                errors.append("operator recovery verify did not report passed")
            acceptance_report_path = run_dir / "installed_acceptance_report.json"
            operator_acceptance_output = _run(
                [
                    str(rdllm_operator_acceptance),
                    "--profile",
                    str(bootstrap_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(bootstrap_dir / "service_config.json"),
                    "--service-root",
                    str(bootstrap_dir),
                    "--bootstrap-dir",
                    str(bootstrap_dir),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--audit-log",
                    str(audit_path),
                    "--expected-audit-count",
                    "1",
                    "--recovery-manifest",
                    str(recovery_manifest_path),
                    "--recovery-root",
                    str(bootstrap_dir),
                    "--output",
                    str(acceptance_report_path),
                ],
                cwd=run_dir,
                env=launch_env,
            )
            if "operator_acceptance status: ready" not in operator_acceptance_output:
                errors.append("operator acceptance console did not report ready")
            if "response_display_text_status: passed" not in operator_acceptance_output:
                errors.append("operator acceptance did not verify copied display text")
            operator_acceptance_verify_output = _run(
                [
                    str(rdllm_operator_acceptance),
                    "verify",
                    "--report",
                    str(acceptance_report_path),
                ],
                cwd=run_dir,
            )
            if (
                "operator_acceptance_verification status: passed"
                not in operator_acceptance_verify_output
            ):
                errors.append("operator acceptance verifier did not report passed")
            acceptance_support_bundle_path = (
                run_dir / "installed_acceptance_support_bundle.json"
            )
            acceptance_support_bundle_output = _run(
                [
                    str(rdllm_operator_support_bundle),
                    "--skip-doctor",
                    "--acceptance-report",
                    str(acceptance_report_path),
                    "--output",
                    str(acceptance_support_bundle_path),
                ],
                cwd=run_dir,
            )
            if (
                "acceptance_verification_status: passed"
                not in acceptance_support_bundle_output
            ):
                errors.append(
                    "operator support bundle did not verify acceptance report"
                )
            acceptance_matrix_dir = run_dir / "installed_acceptance_matrix"
            acceptance_matrix_report_path = (
                run_dir / "installed_acceptance_matrix_report.json"
            )
            operator_acceptance_matrix_output = _run(
                [
                    str(rdllm_operator_acceptance_matrix),
                    "--output-dir",
                    str(acceptance_matrix_dir),
                    "--write-report",
                    str(acceptance_matrix_report_path),
                ],
                cwd=run_dir,
            )
            if (
                "operator_acceptance_matrix status: passed"
                not in operator_acceptance_matrix_output
            ):
                errors.append("operator acceptance matrix did not report passed")
            acceptance_report = json.loads(
                acceptance_report_path.read_text(encoding="utf-8")
            )
            acceptance_matrix_report = json.loads(
                acceptance_matrix_report_path.read_text(encoding="utf-8")
            )
            acceptance_support_bundle = json.loads(
                acceptance_support_bundle_path.read_text(encoding="utf-8")
            )
            if acceptance_matrix_report.get("status") != "passed":
                errors.append("operator acceptance matrix report did not pass")
            if (
                acceptance_matrix_report.get("summary", {}).get(
                    "operator_template_count"
                )
                != 5
            ):
                errors.append(
                    "operator acceptance matrix did not cover all operator templates"
                )
            if (
                acceptance_matrix_report.get("summary", {}).get("passed_count")
                != 5
            ):
                errors.append(
                    "operator acceptance matrix did not pass all operator templates"
                )
            if (
                acceptance_report.get("summary", {}).get(
                    "production_acceptance_decision"
                )
                != "block"
            ):
                errors.append(
                    "unattested packaged profile did not block production acceptance"
                )
            if (
                acceptance_report.get("summary", {}).get(
                    "production_grade_claim_allowed"
                )
                is not False
            ):
                errors.append("packaged profile self-authorized a production claim")
            if (
                acceptance_report.get("summary", {}).get(
                    "direct_creator_settlement_allowed"
                )
                is not False
            ):
                errors.append("packaged profile self-authorized direct settlement")
            if acceptance_support_bundle.get("status") != "passed":
                errors.append("acceptance support bundle did not pass")
            if (
                acceptance_support_bundle.get("acceptance_verification", {}).get(
                    "recorded_acceptance_report_hash"
                )
                != acceptance_report.get("acceptance_report_hash")
            ):
                errors.append("acceptance support bundle hash did not match report")
            if (
                acceptance_report.get("summary", {}).get(
                    "audit_response_binding_status"
                )
                != "passed"
            ):
                errors.append("operator acceptance did not bind audit to response")
            audit_binding = acceptance_report.get("audit_response_binding", {})
            if audit_binding.get("latest_entry_status") != "ready":
                errors.append("operator acceptance did not bind a ready audit row")
            if audit_binding.get("latest_audit_error_count") != 0:
                errors.append("operator acceptance did not require clean audit row")
            if audit_binding.get("source_footer_hash_matches_response") is not True:
                errors.append(
                    "operator acceptance did not bind audit source footer hash"
                )
            if audit_binding.get("display_hash_matches_response") is not True:
                errors.append("operator acceptance did not bind audit display hash")
            if bootstrap_manifest["status"] != "ready":
                errors.append("operator bootstrap manifest is not ready")
            if not (bootstrap_dir / "service_config.json").is_file():
                errors.append("operator bootstrap did not write service config")
            if not (bootstrap_dir / "corpus" / "sample_corpus.json").is_file():
                errors.append("operator bootstrap did not write sample corpus")
            if not (bootstrap_dir / "artifacts" / "certification_report.json").is_file():
                errors.append("operator bootstrap did not write reference artifacts")
            if "service_config status: ready" not in service_config_output:
                errors.append("service config console did not report ready status")
            if service_config["schema"] != "rdllm-service-config/v1":
                errors.append("service config console wrote the wrong schema")
            if service_config["corpus"] != "operator_corpus.json":
                errors.append("service config console did not apply corpus override")
            if (
                service_config["artifacts"]["certification_report"]
                != "/srv/rdllm/artifacts/certification_report.json"
            ):
                errors.append("service config console did not apply artifact directory")
            service_providers = service_config.get("providers", [])
            if not service_providers:
                errors.append("service config console did not add provider route")
            else:
                provider = service_providers[0]
                if provider.get("provider_id") != "installed-provider":
                    errors.append("service config console did not apply provider id")
                if provider.get("model") != "installed-model":
                    errors.append("service config console did not apply provider model")

            return {
                "status": "failed" if errors else "passed",
                "errors": errors,
                "wheel": wheels[0].name,
                "sdist": sdists[0].name,
                "installed_version": import_output,
                "demo_event_count": len(events),
                "console_script": rdllm.name,
                "first_run_console_script": rdllm_first_run.name,
                "operator_acceptance_console_script": (
                    rdllm_operator_acceptance.name
                ),
                "operator_acceptance_matrix_console_script": (
                    rdllm_operator_acceptance_matrix.name
                ),
                "operator_bootstrap_console_script": rdllm_operator_bootstrap.name,
                "operator_doctor_console_script": rdllm_operator_doctor.name,
                "operator_launch_gate_console_script": (
                    rdllm_operator_launch_gate.name
                ),
                "operator_profile_console_script": rdllm_operator_profile.name,
                "operator_recovery_console_script": rdllm_operator_recovery.name,
                "operator_support_bundle_console_script": (
                    rdllm_operator_support_bundle.name
                ),
                "production_readiness_verify_console_script": (
                    rdllm_production_readiness_verify.name
                ),
                "service_audit_verify_console_script": rdllm_service_audit_verify.name,
                "service_config_console_script": rdllm_service_config.name,
                "service_response_verify_console_script": (
                    rdllm_service_response_verify.name
                ),
                "source_footer_verify_console_script": rdllm_source_footer_verify.name,
                "service_console_script": rdllm_service.name,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"package_smoke status: {report['status']}",
        f"wheel: {report.get('wheel', '<missing>')}",
        f"sdist: {report.get('sdist', '<missing>')}",
        f"installed_version: {report.get('installed_version', '<unknown>')}",
        f"demo_event_count: {report.get('demo_event_count', 0)}",
        "first_run_console_script: "
        f"{report.get('first_run_console_script', '<missing>')}",
        "operator_acceptance_console_script: "
        f"{report.get('operator_acceptance_console_script', '<missing>')}",
        "operator_acceptance_matrix_console_script: "
        f"{report.get('operator_acceptance_matrix_console_script', '<missing>')}",
        "operator_bootstrap_console_script: "
        f"{report.get('operator_bootstrap_console_script', '<missing>')}",
        "operator_doctor_console_script: "
        f"{report.get('operator_doctor_console_script', '<missing>')}",
        "operator_launch_gate_console_script: "
        f"{report.get('operator_launch_gate_console_script', '<missing>')}",
        "operator_profile_console_script: "
        f"{report.get('operator_profile_console_script', '<missing>')}",
        "operator_recovery_console_script: "
        f"{report.get('operator_recovery_console_script', '<missing>')}",
        "operator_support_bundle_console_script: "
        f"{report.get('operator_support_bundle_console_script', '<missing>')}",
        "production_readiness_verify_console_script: "
        f"{report.get('production_readiness_verify_console_script', '<missing>')}",
        "service_audit_verify_console_script: "
        f"{report.get('service_audit_verify_console_script', '<missing>')}",
        "service_config_console_script: "
        f"{report.get('service_config_console_script', '<missing>')}",
        "service_response_verify_console_script: "
        f"{report.get('service_response_verify_console_script', '<missing>')}",
        "source_footer_verify_console_script: "
        f"{report.get('source_footer_verify_console_script', '<missing>')}",
        "service_console_script: "
        f"{report.get('service_console_script', '<missing>')}",
    ]
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = smoke()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
