from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ShippingReadinessTests(unittest.TestCase):
    def test_required_shipping_files_exist(self) -> None:
        required = [
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
            "docs/schemas/production_readiness_profile.schema.json",
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
            "src/rdllm/operator_profile.py",
            "src/rdllm/first_run.py",
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
            "src/rdllm/operator_bootstrap.py",
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
            "tools/artifact_schema_audit.py",
            "tools/deployment_audit.py",
            "tools/docs_link_audit.py",
            "tools/e2e_smoke.py",
            "tools/github_docs_readiness_audit.py",
            "tools/github_readiness.py",
            "tools/hosting_export.py",
            "tools/hosted_surface_audit.py",
            "tools/package_metadata_audit.py",
            "tools/package_smoke.py",
            "tools/operator_acceptance.py",
            "tools/operator_acceptance_matrix.py",
            "tools/operator_profile.py",
            "tools/operator_bootstrap.py",
            "tools/operator_doctor.py",
            "tools/operator_launch_gate.py",
            "tools/operator_recovery.py",
            "tools/operator_support_bundle.py",
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
            "tools/ship_check.py",
            "tools/adopter_quickstart_audit.py",
            "tools/service_load_smoke.py",
            "tools/service_smoke.py",
        ]
        for file_name in required:
            with self.subTest(file_name=file_name):
                path = ROOT / file_name
                self.assertTrue(path.is_file())
                self.assertTrue(path.read_text(encoding="utf-8").strip())
        required_binary = [
            "examples/live_use_cases/screenshots/first-run.png",
            "examples/live_use_cases/screenshots/cli-answer-sources.png",
            "examples/live_use_cases/screenshots/service-smoke.png",
            "examples/live_use_cases/screenshots/provider-live-smoke.png",
        ]
        for file_name in required_binary:
            with self.subTest(file_name=file_name):
                path = ROOT / file_name
                self.assertTrue(path.is_file())
                self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_white_paper_covers_state_of_art_sources(self) -> None:
        text = (ROOT / "paper" / "rdllm_white_paper.md").read_text(
            encoding="utf-8"
        )
        required_terms = [
            "RDLLM White Paper",
            "State Of The Art",
            "observable_support_allocation_not_model_internal_reliance",
            "Cited but Not Verified",
            "How Do LLMs Cite?",
            "CiteGuard",
            "PaperTrail",
            "Relevant Is Not Warranted",
            "ProvenanceGuard",
            "ProvenAI",
            "Do LLM Attribution Metrics Transfer?",
            "W3C PROV",
            "W3C Verifiable Credentials",
            "C2PA",
            "IETF RFC 9943",
            "NIST AI 600-1",
            "EU AI Act",
            "U.S. Copyright Office",
            "Allocation Mechanism",
            "Runtime Example",
            "Threat Model",
            "Primary Sources And Evidence Base",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_adopter_quickstart_covers_roles_and_gates(self) -> None:
        text = (ROOT / "docs" / "adopter_quickstart.md").read_text(
            encoding="utf-8"
        )
        required_terms = [
            "individual",
            "company",
            "institution",
            "government",
            "public_sector",
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
            "RDLLM_HOME",
            "RDLLM_STATE",
            "RDLLM_AUDIT_LOG",
            "RDLLM_SERVICE_TOKEN",
            "production_display_ready",
            "source_grounding_acceptance",
            "production_acceptance_decision",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)
        for banned in ("/etc/rdllm", "/var/lib/rdllm", "Bearer <token>"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, text)

    def test_adopter_quickstart_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/adopter_quickstart_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("rootless_probe_status: passed", result.stdout)
        self.assertIn("rootless_probe_audit_log_bound: true", result.stdout)
        self.assertIn("rootless_probe_production_display_ready: true", result.stdout)

    def test_ship_check_fast_mode_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/ship_check.py",
                "--skip-tests",
                "--skip-regenerate",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_github_readiness_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/github_readiness.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_e2e_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/e2e_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_service_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/service_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_service_load_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/service_load_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_provider_live_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/provider_live_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_security_abuse_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/security_abuse_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_production_readiness_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/production_readiness.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_production_profile_matrix_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/production_profile_matrix.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_deployment_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/deployment_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_provider_family_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/provider_family_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_artifact_schema_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/artifact_schema_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_docs_link_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/docs_link_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_github_docs_readiness_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/github_docs_readiness_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("localized_quickstart_count: 15", result.stdout)
        self.assertIn("localized_explainer_count: 15", result.stdout)
        self.assertIn("implementation_language_count: 5", result.stdout)

    def test_live_use_cases_cover_screenshots_and_fifteen_paths(self) -> None:
        text = (ROOT / "examples" / "live_use_cases" / "README.md").read_text(
            encoding="utf-8"
        )
        for index in range(1, 16):
            with self.subTest(use_case=index):
                self.assertIn(f"Use Case {index}", text)
        for term in (
            "Live Screenshot Gallery",
            "screenshots/first-run.png",
            "screenshots/cli-answer-sources.png",
            "screenshots/service-smoke.png",
            "screenshots/provider-live-smoke.png",
            "rdllm-first-run",
            "service_load_smoke.py",
            "security_abuse_smoke.py",
            "package_smoke.py",
            "github_docs_readiness_audit.py",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_first_run_demo_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "rdllm.first_run",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("rdllm_first_run status: passed", result.stdout)
        self.assertIn("Sources", result.stdout)
        self.assertIn("Claim Evidence", result.stdout)
        self.assertIn("payout=", result.stdout)
        self.assertIn("disagreement=passed", result.stdout)

    def test_hosting_export_is_current(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/hosting_export.py",
                "--check",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_hosted_surface_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/hosted_surface_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_public_surface_privacy_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/public_surface_privacy_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_package_metadata_audit_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/package_metadata_audit.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn(
            "development_status: Development Status :: 5 - Production/Stable",
            result.stdout,
        )
        self.assertIn("version: 1.0.0", result.stdout)

    def test_package_smoke_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/package_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_provider_compatibility_matrix_covers_required_families(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/provider_matrix.py",
                "--check",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        matrix = (ROOT / "docs" / "provider_compatibility_matrix.md").read_text(
            encoding="utf-8"
        )
        required = [
            "openai_responses",
            "anthropic_messages",
            "google_gemini_generate_content",
            "google_vertex_ai",
            "meta_llama_stack",
            "mistral_chat",
            "cohere_chat",
            "xai_grok",
            "deepseek_chat",
            "azure_openai",
            "aws_bedrock",
            "openrouter_compatible",
            "local_open_weight_runtime",
            "enterprise_gateway_proxy",
            "rag_native_provider",
            "mcp_agent_tool_runtime",
            "openai_responses_usage",
            "anthropic_messages_usage",
            "gemini_usage_metadata",
            "bedrock_converse_usage",
            "openai_responses_status",
            "anthropic_messages_stop_reason",
            "gemini_safety_ratings",
            "bedrock_guardrail_trace",
            "streaming_final_state",
        ]
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, matrix)


if __name__ == "__main__":
    unittest.main()
