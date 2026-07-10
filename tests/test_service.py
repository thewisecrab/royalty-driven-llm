from __future__ import annotations

import hashlib
from io import BytesIO
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from rdllm.answer_citations import (
    answer_link_uris,
    answer_citation_markers,
    claim_citation_keys,
    model_reliance_claim_markers,
    resolved_answer_link_uris,
    resolved_answer_citation_markers,
    source_citation_keys,
    unresolved_answer_link_uris,
    unresolved_answer_citation_markers,
)
from rdllm.claim_warrant import CLAIM_WARRANT_PROFILE, claim_warrant_report
from rdllm.operator_acceptance import (
    load_acceptance_schema,
    load_acceptance_verification_schema,
    verify_acceptance_report,
)
from rdllm.operator_acceptance_matrix import (
    load_acceptance_matrix_schema,
    run_acceptance_matrix,
)
from rdllm.operator_bootstrap import (
    REFERENCE_ARTIFACT_RESOURCES,
    bootstrap_manifest_errors,
    load_bootstrap_schema,
    load_bootstrap_verification_schema,
    verify_bootstrap_dir,
)
from rdllm.operator_doctor import load_doctor_schema
from rdllm.operator_launch_gate import load_launch_gate_schema
from rdllm.operator_recovery import (
    load_recovery_manifest_schema,
    load_recovery_verification_schema,
)
from rdllm.operator_support_bundle import load_support_bundle_schema
from rdllm.service_config import (
    load_service_config_verification_schema,
    load_service_schema,
    load_service_template,
    service_config_schema_errors,
    service_config_result,
)
from rdllm.service_audit_verifier import (
    load_audit_entry_schema,
    load_audit_verification_schema,
    verify_service_audit_log,
)
from rdllm.service_response_verifier import (
    event_hash_from_event,
    load_response_schema,
    load_response_verification_schema,
    verify_service_response,
)
from rdllm.source_disagreement import (
    SOURCE_DISAGREEMENT_PROFILE,
    claim_source_disagreement_report,
)
from rdllm.source_footer_verifier import (
    load_source_footer_verification_schema,
    verify_source_footer,
)
from rdllm.source_footer_rendering import render_source_footer_text
from rdllm.service import (
    AuditLogError,
    ServiceConfig,
    ServiceState,
    _attribute,
    canonical_hash,
    load_json,
    make_app,
    prometheus_metrics,
    readiness_report,
)
from rdllm.source_usage_metrics import (
    SOURCE_USAGE_METRIC_METHODS,
    SOURCE_USAGE_METRIC_PROFILE,
    SOURCE_USAGE_METRIC_SCOPE,
)
from rdllm.text import stable_hash


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "examples" / "service_config.json"
TOKEN_ENV = "RDLLM_SERVICE_TOKEN_SHA256"
PACKAGED_SERVICE_TEMPLATE_EXAMPLES = {
    "default": ROOT / "examples" / "service_config.json",
    "openai_compatible": ROOT / "examples" / "service_config.openai_compatible.json",
    "container": ROOT / "deploy" / "docker" / "service_config.container.json",
}
REFERENCE_ARTIFACT_EXAMPLES = {
    name: ROOT / "artifacts" / resource[-1]
    for name, resource in REFERENCE_ARTIFACT_RESOURCES.items()
}


class ServiceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_token_hash = os.environ.get(TOKEN_ENV)
        os.environ[TOKEN_ENV] = hashlib.sha256(
            b"rdllm-local-dev-token"
        ).hexdigest()

    def tearDown(self) -> None:
        if self._old_token_hash is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = self._old_token_hash

    def test_answer_citation_parser_resolves_supported_marker_forms(self) -> None:
        allowed = source_citation_keys(["S1", "S2", "S3"]) | claim_citation_keys([1])
        text = "Grounded answer [1, 2] with claim support [C1] and year [2026]."
        self.assertEqual(answer_citation_markers(text), ["[1, 2]", "[C1]"])
        self.assertEqual(
            resolved_answer_citation_markers(text, allowed),
            ["[1, 2]", "[C1]"],
        )
        self.assertEqual(unresolved_answer_citation_markers(text, allowed), [])
        self.assertEqual(
            unresolved_answer_citation_markers("Missing source [1-4].", allowed),
            ["[1-4]"],
        )
        linked_text = (
            "Grounded answer [RDLLM source]"
            "(registered://works/source#chunk:c1) and unverified "
            "https://example.invalid/citation."
        )
        allowed_uris = {"registered://works/source#chunk:c1"}
        self.assertEqual(
            answer_link_uris(linked_text),
            [
                "registered://works/source#chunk:c1",
                "https://example.invalid/citation",
            ],
        )
        self.assertEqual(
            resolved_answer_link_uris(linked_text, allowed_uris),
            ["registered://works/source#chunk:c1"],
        )
        self.assertEqual(
            unresolved_answer_link_uris(linked_text, allowed_uris),
            ["https://example.invalid/citation"],
        )
        self.assertEqual(
            model_reliance_claim_markers(
                "I used [S1] in my reasoning, but visible source support is different."
            ),
            ["i used", "my reasoning"],
        )

    def test_service_config_validates_against_schema(self) -> None:
        config = load_json(CONFIG_PATH)
        schema = load_json(ROOT / "docs" / "schemas" / "service_config.schema.json")
        errors = list(Draft202012Validator(schema).iter_errors(config))
        self.assertEqual(errors, [])

    def test_container_service_config_validates_against_schema(self) -> None:
        config = load_json(ROOT / "deploy" / "docker" / "service_config.container.json")
        schema = load_json(ROOT / "docs" / "schemas" / "service_config.schema.json")
        errors = list(Draft202012Validator(schema).iter_errors(config))
        self.assertEqual(errors, [])

    def test_provider_service_config_validates_against_schema(self) -> None:
        config = load_json(ROOT / "examples" / "service_config.openai_compatible.json")
        schema = load_json(ROOT / "docs" / "schemas" / "service_config.schema.json")
        errors = list(Draft202012Validator(schema).iter_errors(config))
        self.assertEqual(errors, [])

    def test_packaged_service_config_templates_match_repository_examples(self) -> None:
        for template, path in PACKAGED_SERVICE_TEMPLATE_EXAMPLES.items():
            with self.subTest(template=template):
                self.assertEqual(load_service_template(template), load_json(path))
        self.assertEqual(
            load_service_schema(),
            load_json(ROOT / "docs" / "schemas" / "service_config.schema.json"),
        )

    def test_packaged_service_config_verification_schema_matches_repository_schema(
        self,
    ) -> None:
        self.assertEqual(
            load_service_config_verification_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "service_config_verification.schema.json"
            ),
        )

    def test_packaged_service_response_schema_matches_repository_schema(self) -> None:
        self.assertEqual(
            load_response_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "service_attribution_response.schema.json"
            ),
        )

    def test_packaged_service_response_verification_schema_matches_repository_schema(
        self,
    ) -> None:
        self.assertEqual(
            load_response_verification_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "service_response_verification.schema.json"
            ),
        )

    def test_packaged_service_audit_verification_schema_matches_repository_schema(
        self,
    ) -> None:
        self.assertEqual(
            load_audit_entry_schema(),
            load_json(ROOT / "docs" / "schemas" / "service_audit_entry.schema.json"),
        )
        self.assertEqual(
            load_audit_verification_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "service_audit_verification.schema.json"
            ),
        )

    def test_packaged_service_config_schema_rejects_unknown_fields(self) -> None:
        config = load_service_template("default")
        config["unknown"] = True
        errors = service_config_schema_errors(config)
        self.assertIn("<root>.unknown: unknown field", errors)

    def test_packaged_reference_artifacts_match_repository_examples(self) -> None:
        for name, path in REFERENCE_ARTIFACT_EXAMPLES.items():
            with self.subTest(name=name):
                packaged = load_json(
                    ROOT
                    / "src"
                    / "rdllm"
                    / "data"
                    / "reference_artifacts"
                    / path.name
                )
                self.assertEqual(packaged, load_json(path))

    def test_packaged_bootstrap_schemas_match_repository_schemas(self) -> None:
        self.assertEqual(
            load_bootstrap_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "operator_bootstrap_manifest.schema.json"
            ),
        )
        self.assertEqual(
            load_bootstrap_verification_schema(),
            load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_bootstrap_verification.schema.json"
            ),
        )

    def test_packaged_support_bundle_schema_matches_repository_schema(self) -> None:
        self.assertEqual(
            load_support_bundle_schema(),
            load_json(ROOT / "docs" / "schemas" / "operator_support_bundle.schema.json"),
        )

    def test_packaged_doctor_schema_matches_repository_schema(self) -> None:
        self.assertEqual(
            load_doctor_schema(),
            load_json(ROOT / "docs" / "schemas" / "operator_doctor.schema.json"),
        )

    def test_packaged_launch_gate_schema_matches_repository_schema(self) -> None:
        self.assertEqual(
            load_launch_gate_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "operator_launch_gate.schema.json"
            ),
        )

    def test_packaged_acceptance_verification_schema_matches_repository_schema(
        self,
    ) -> None:
        self.assertEqual(
            load_acceptance_verification_schema(),
            load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_acceptance_verification.schema.json"
            ),
        )

    def test_packaged_recovery_schemas_match_repository_schemas(self) -> None:
        self.assertEqual(
            load_recovery_manifest_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "operator_recovery_manifest.schema.json"
            ),
        )
        self.assertEqual(
            load_recovery_verification_schema(),
            load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_recovery_verification.schema.json"
            ),
        )

    def test_service_config_cli_create_writes_ready_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-service-config-") as temp_name:
            config_path = Path(temp_name) / "service_config.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/service_config.py",
                    "create",
                    "--template",
                    "default",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8766",
                    "--corpus",
                    "operator_corpus.json",
                    "--artifact-dir",
                    "/srv/rdllm/artifacts",
                    "--provider-id",
                    "acme-provider",
                    "--provider-base-url",
                    "https://provider.example",
                    "--provider-model",
                    "acme-model",
                    "--provider-api-key-env",
                    "ACME_PROVIDER_KEY",
                    "--output",
                    str(config_path),
                    "--json",
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
            payload = json.loads(result.stdout)
            config = load_json(config_path)
            verification_schema = load_json(
                ROOT / "docs" / "schemas" / "service_config_verification.schema.json"
            )
            self.assertEqual(
                load_service_config_verification_schema(),
                verification_schema,
            )
            self.assertEqual(
                payload["schema"],
                "rdllm-service-config-verification/v1",
            )
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(
                [],
                list(Draft202012Validator(verification_schema).iter_errors(payload)),
            )
            self.assertEqual(config["port"], 8766)
            self.assertEqual(config["corpus"], "operator_corpus.json")
            self.assertEqual(
                config["artifacts"]["certification_report"],
                "/srv/rdllm/artifacts/certification_report.json",
            )
            self.assertEqual(
                config["artifacts"]["universal_source_grounded_response_receipt"],
                "/srv/rdllm/artifacts/universal_source_grounded_response_receipt.json",
            )
            provider = config["providers"][0]
            self.assertEqual(provider["provider_id"], "acme-provider")
            self.assertEqual(provider["base_url"], "https://provider.example")
            self.assertEqual(provider["model"], "acme-model")
            self.assertEqual(provider["api_key_env"], "ACME_PROVIDER_KEY")

    def test_service_config_cli_rejects_unknown_artifact_override(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/service_config.py",
                "create",
                "--template",
                "default",
                "--artifact",
                "unknown=artifact.json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown artifact", result.stderr)

    def test_service_config_cli_validate_blocks_bad_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-service-config-") as temp_name:
            config_path = Path(temp_name) / "bad_service_config.json"
            config = load_service_template("default")
            config["limits"]["max_request_bytes"] = 1
            config_path.write_text(json.dumps(config), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/service_config.py",
                    "validate",
                    "--config",
                    str(config_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            verification_schema = load_service_config_verification_schema()
            self.assertEqual(
                payload["schema"],
                "rdllm-service-config-verification/v1",
            )
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["schema_status"], "failed")
            self.assertEqual(
                [],
                list(Draft202012Validator(verification_schema).iter_errors(payload)),
            )

    def test_service_config_cli_validate_runtime_ready_config(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/service_config.py",
                "validate",
                "--config",
                "examples/service_config.json",
                "--root",
                str(ROOT),
                "--check-runtime",
                "--json",
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
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["runtime_status"], "ready")

    def test_operator_bootstrap_cli_writes_profile_report_and_service_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-bootstrap-") as temp_name:
            output_dir = Path(temp_name) / "operator"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--output-dir",
                    str(output_dir),
                    "--operator-template",
                    "company",
                    "--operator-name",
                    "Acme RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--corpus",
                    "/srv/rdllm/corpus.json",
                    "--service-template",
                    "openai_compatible",
                    "--provider-id",
                    "acme-provider",
                    "--provider-base-url",
                    "https://provider.example",
                    "--provider-model",
                    "acme-model",
                    "--provider-api-key-env",
                    "ACME_PROVIDER_KEY",
                    "--json",
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
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["summary"]["operator_template"], "company")
            self.assertFalse(payload["summary"]["direct_creator_settlement_allowed"])

            profile = load_json(output_dir / "production_readiness_profile.json")
            report = load_json(output_dir / "production_readiness_report.json")
            config = load_json(output_dir / "service_config.json")
            manifest = load_json(output_dir / "operator_bootstrap_manifest.json")
            schema = load_json(
                ROOT / "docs" / "schemas" / "operator_bootstrap_manifest.schema.json"
            )
            verification_schema = load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_bootstrap_verification.schema.json"
            )
            schema_errors = list(Draft202012Validator(schema).iter_errors(manifest))
            verification = verify_bootstrap_dir(output_dir)
            self.assertEqual(profile["deployment"]["operator_name"], "Acme RDLLM")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(manifest["schema"], "rdllm-operator-bootstrap/v1")
            self.assertEqual(schema_errors, [])
            self.assertEqual(bootstrap_manifest_errors(manifest), [])
            self.assertEqual(verification["status"], "passed")
            self.assertEqual(
                load_bootstrap_verification_schema(),
                verification_schema,
            )
            self.assertEqual(
                [],
                list(Draft202012Validator(verification_schema).iter_errors(verification)),
            )
            self.assertEqual(config["corpus"], "/srv/rdllm/corpus.json")
            self.assertEqual(config["providers"][0]["provider_id"], "acme-provider")
            self.assertEqual(
                config["artifacts"]["certification_report"],
                (
                    f"{output_dir.resolve().as_posix()}"
                    "/artifacts/certification_report.json"
                ),
            )
            self.assertTrue((output_dir / "README.md").is_file())
            verify_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--verify-dir",
                    str(output_dir),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                verify_result.returncode,
                0,
                msg=f"stdout:\n{verify_result.stdout}\nstderr:\n{verify_result.stderr}",
            )
            verify_payload = json.loads(verify_result.stdout)
            self.assertEqual(verify_payload["status"], "passed")
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(verification_schema).iter_errors(
                        verify_payload
                    )
                ),
            )

    def test_operator_bootstrap_cli_can_include_runtime_ready_reference_pack(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-bootstrap-") as temp_name:
            output_dir = Path(temp_name) / "operator"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--output-dir",
                    str(output_dir),
                    "--operator-template",
                    "individual",
                    "--operator-name",
                    "Local RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--include-sample-corpus",
                    "--include-reference-artifacts",
                    "--check-runtime",
                    "--json",
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
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ready")
            self.assertTrue(payload["summary"]["sample_corpus_included"])
            self.assertTrue(payload["summary"]["reference_artifacts_included"])
            self.assertTrue((output_dir / "corpus" / "sample_corpus.json").is_file())
            self.assertTrue(
                (output_dir / "artifacts" / "certification_report.json").is_file()
            )
            config = load_json(output_dir / "service_config.json")
            state = ServiceState.from_config(
                ServiceConfig(raw=config, root=output_dir.resolve())
            )
            self.assertEqual(readiness_report(state)["status"], "ready")
            verify_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--verify-dir",
                    str(output_dir),
                    "--check-runtime",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                verify_result.returncode,
                0,
                msg=f"stdout:\n{verify_result.stdout}\nstderr:\n{verify_result.stderr}",
            )
            verify_payload = json.loads(verify_result.stdout)
            self.assertEqual(verify_payload["status"], "passed")
            self.assertEqual(verify_payload["runtime_status"], "ready")
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(
                        load_bootstrap_verification_schema()
                    ).iter_errors(verify_payload)
                ),
            )

    def test_operator_launch_gate_allows_runtime_ready_deployment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-launch-gate-") as temp_name:
            output_dir = Path(temp_name) / "operator"
            bootstrap_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--output-dir",
                    str(output_dir),
                    "--operator-template",
                    "individual",
                    "--operator-name",
                    "Local RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--include-sample-corpus",
                    "--include-reference-artifacts",
                    "--check-runtime",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                bootstrap_result.returncode,
                0,
                msg=(
                    f"stdout:\n{bootstrap_result.stdout}\n"
                    f"stderr:\n{bootstrap_result.stderr}"
                ),
            )
            config = load_json(output_dir / "service_config.json")
            state = ServiceState.from_config(
                ServiceConfig(raw=config, root=output_dir.resolve())
            )
            status_code, response = _attribute(
                state,
                {
                    "prompt": "What should royalty-bearing AI answers expose?",
                    "output": (
                        "Every royalty bearing AI answer should have a provenance "
                        "record. The record should include source identifiers, "
                        "content hashes, retrieval scores, output citations, payout "
                        "weights, and an event hash that allows auditors to replay "
                        "the attribution."
                    ),
                    "gross_revenue": "1.00",
                },
            )
            self.assertEqual(status_code, 200)
            response_path = output_dir / "service_response.json"
            response_path.write_text(json.dumps(response), encoding="utf-8")
            display_text_path = output_dir / "copied_display_text.txt"
            display_text = response["display"]["rendered_text"]
            display_text_path.write_text(display_text, encoding="utf-8")
            support_bundle_path = output_dir / "support_bundle.json"
            gate_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_launch_gate.py",
                    "--profile",
                    str(output_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(output_dir / "service_config.json"),
                    "--service-root",
                    str(output_dir),
                    "--bootstrap-dir",
                    str(output_dir),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--write-support-bundle",
                    str(support_bundle_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                gate_result.returncode,
                0,
                msg=f"stdout:\n{gate_result.stdout}\nstderr:\n{gate_result.stderr}",
            )
            payload = json.loads(gate_result.stdout)
            launch_gate_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_launch_gate.schema.json"
            )
            self.assertEqual(
                list(Draft202012Validator(launch_gate_schema).iter_errors(payload)),
                [],
            )
            self.assertEqual(payload["schema"], "rdllm-operator-launch-gate/v1")
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["summary"]["traffic_decision"], "allow")
            self.assertEqual(payload["summary"]["service_runtime_status"], "ready")
            self.assertEqual(payload["summary"]["response_verification_status"], "passed")
            self.assertEqual(payload["summary"]["display_text_status"], "passed")
            self.assertEqual(payload["response_verification"]["response_status"], "ready")
            self.assertEqual(
                payload["response_verification"]["display_text_status"],
                "passed",
            )
            self.assertEqual(
                payload["response_verification"]["display_text_hash"],
                canonical_hash(display_text),
            )
            self.assertTrue(
                payload["response_verification"]["production_display_ready"]
            )
            self.assertFalse(payload["summary"]["production_grade_claim_allowed"])
            self.assertFalse(payload["summary"]["direct_creator_settlement_allowed"])
            self.assertTrue(payload["support_bundle"]["written"])
            self.assertTrue(support_bundle_path.is_file())

            missing_display_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_launch_gate.py",
                    "--profile",
                    str(output_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(output_dir / "service_config.json"),
                    "--service-root",
                    str(output_dir),
                    "--bootstrap-dir",
                    str(output_dir),
                    "--response",
                    str(response_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(missing_display_result.returncode, 1)
            missing_display_payload = json.loads(missing_display_result.stdout)
            self.assertEqual(missing_display_payload["status"], "blocked")
            self.assertEqual(
                missing_display_payload["summary"]["display_text_status"],
                "failed",
            )
            self.assertIn(
                "response_verification: display_text: copied/exported display text is required for production launch",
                missing_display_payload["errors"],
            )

            blocked_status_code, blocked_response = _attribute(
                state,
                {
                    "prompt": "What should royalty-bearing AI answers expose?",
                    "output": (
                        "The moon is made of green cheese and every library must "
                        "pay royalties to unrelated fictional parties."
                    ),
                    "gross_revenue": "1.00",
                },
            )
            self.assertEqual(blocked_status_code, 422)
            blocked_response_path = output_dir / "blocked_service_response.json"
            blocked_response_path.write_text(
                json.dumps(blocked_response),
                encoding="utf-8",
            )
            blocked_display_text_path = output_dir / "blocked_copied_display_text.txt"
            blocked_display_text_path.write_text(
                blocked_response["display"]["rendered_text"],
                encoding="utf-8",
            )
            blocked_saved_response_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_launch_gate.py",
                    "--profile",
                    str(output_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(output_dir / "service_config.json"),
                    "--service-root",
                    str(output_dir),
                    "--bootstrap-dir",
                    str(output_dir),
                    "--response",
                    str(blocked_response_path),
                    "--display-text",
                    str(blocked_display_text_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(blocked_saved_response_result.returncode, 1)
            blocked_response_payload = json.loads(blocked_saved_response_result.stdout)
            self.assertEqual(
                list(
                    Draft202012Validator(launch_gate_schema).iter_errors(
                        blocked_response_payload
                    )
                ),
                [],
            )
            self.assertEqual(blocked_response_payload["status"], "blocked")
            self.assertEqual(
                blocked_response_payload["summary"]["response_verification_status"],
                "failed",
            )
            self.assertEqual(
                blocked_response_payload["response_verification"]["response_status"],
                "blocked",
            )
            self.assertFalse(
                blocked_response_payload["response_verification"][
                    "production_display_ready"
                ]
            )
            self.assertIn(
                "response_verification: response.status: expected ready for production display, got blocked",
                blocked_response_payload["errors"],
            )

            blocked_result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_launch_gate.py",
                    "--profile",
                    str(output_dir / "production_readiness_profile.json"),
                    "--service-config",
                    str(output_dir / "service_config.json"),
                    "--service-root",
                    str(output_dir),
                    "--bootstrap-dir",
                    str(output_dir),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(blocked_result.returncode, 1)
            blocked_payload = json.loads(blocked_result.stdout)
            self.assertEqual(
                list(
                    Draft202012Validator(launch_gate_schema).iter_errors(
                        blocked_payload
                    )
                ),
                [],
            )
            self.assertEqual(blocked_payload["status"], "blocked")
            self.assertEqual(blocked_payload["summary"]["traffic_decision"], "block")
            self.assertIn(
                "response_verification: response: saved response is required",
                blocked_payload["errors"],
            )

    def test_operator_bootstrap_verification_rejects_stale_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-bootstrap-") as temp_name:
            output_dir = Path(temp_name) / "operator"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--output-dir",
                    str(output_dir),
                    "--operator-template",
                    "individual",
                    "--operator-name",
                    "Local RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--include-sample-corpus",
                    "--include-reference-artifacts",
                    "--json",
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
            report_path = output_dir / "production_readiness_report.json"
            report = load_json(report_path)
            report["summary"]["ready_control_count"] = -1
            report_path.write_text(json.dumps(report), encoding="utf-8")
            verification = verify_bootstrap_dir(output_dir)
            self.assertEqual(verification["status"], "failed")
            self.assertIn(
                "readiness_report: file does not match recomputed profile report",
                verification["errors"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(
                        load_bootstrap_verification_schema()
                    ).iter_errors(verification)
                ),
            )

    def test_operator_doctor_cli_runs_installed_self_test_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-doctor-") as temp_name:
            work_dir = Path(temp_name) / "doctor"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_doctor.py",
                    "--work-dir",
                    str(work_dir),
                    "--json",
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
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema"], "rdllm-operator-doctor/v1")
            self.assertEqual(payload["status"], "passed")
            doctor_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_doctor.schema.json"
            )
            doctor_errors = sorted(
                Draft202012Validator(doctor_schema).iter_errors(payload),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], doctor_errors)
            self.assertEqual(
                payload["package_resources"]["checks"][
                    "bootstrap_verification_schema"
                ],
                "passed",
            )
            self.assertEqual(
                payload["package_resources"]["checks"][
                    "service_config_verification_schema"
                ],
                "passed",
            )
            self.assertTrue(payload["response"]["production_display_ready"])
            self.assertEqual(
                payload["response"]["source_grounding_acceptance_status"],
                "passed",
            )
            self.assertEqual(
                payload["package_resources"]["checks"][
                    "profile_verification_schema"
                ],
                "passed",
            )
            self.assertEqual(payload["bootstrap"]["runtime_status"], "ready")
            self.assertEqual(payload["response"]["verification_status"], "passed")
            self.assertTrue((work_dir / "operator_bootstrap_manifest.json").is_file())
            self.assertTrue((work_dir / "service_response.json").is_file())

    def test_operator_support_bundle_cli_writes_redacted_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-support-bundle-") as temp_name:
            output = Path(temp_name) / "support_bundle.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_support_bundle.py",
                    "--output",
                    str(output),
                    "--json",
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
            payload = json.loads(result.stdout)
            saved = output.read_text(encoding="utf-8")
            self.assertEqual(payload["schema"], "rdllm-operator-support-bundle/v1")
            self.assertEqual(payload["status"], "passed")
            support_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_support_bundle.schema.json"
            )
            support_errors = sorted(
                Draft202012Validator(support_schema).iter_errors(payload),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], support_errors)
            self.assertEqual(payload["doctor"]["status"], "passed")
            self.assertFalse(payload["redaction"]["raw_prompts_included"])
            self.assertFalse(payload["redaction"]["raw_outputs_included"])
            self.assertNotIn("rdllm-local-dev-token", saved)
            self.assertNotIn("rdllm-operator-doctor-token", saved)
            self.assertNotIn("What should royalty-bearing AI answers expose?", saved)
            self.assertNotIn("Every royalty bearing AI answer should have", saved)
            self.assertNotIn("service_response.json", saved)

    def test_service_audit_verifier_checks_hash_chain_and_cli(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 200)

        def entry(request_id: str, previous_hash: str) -> dict[str, object]:
            event = response["event"]
            row: dict[str, object] = {
                "schema": "rdllm-service-audit-entry/v1",
                "request_id": request_id,
                "timestamp": "2026-07-01T00:00:00Z",
                "status": response["status"],
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "source_footer_hash": response["summary"]["source_footer_hash"],
                "display_hash": response["summary"]["display_hash"],
                "source_count": len(event["source_references"]),
                "audit_error_count": len(response["audit_errors"]),
                "previous_entry_hash": previous_hash,
            }
            row["entry_hash"] = canonical_hash(row)
            return row

        with tempfile.TemporaryDirectory(prefix="rdllm-service-audit-") as temp_name:
            audit_log = Path(temp_name) / "service_audit.jsonl"
            first = entry("request-1", "")
            second = entry("request-2", str(first["entry_hash"]))
            audit_log.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in (first, second))
                + "\n",
                encoding="utf-8",
            )
            report = verify_service_audit_log(audit_log, expected_count=2)
            audit_entry_schema = load_json(
                ROOT / "docs" / "schemas" / "service_audit_entry.schema.json"
            )
            audit_verification_schema = load_json(
                ROOT / "docs" / "schemas" / "service_audit_verification.schema.json"
            )
            self.assertEqual(load_audit_entry_schema(), audit_entry_schema)
            self.assertEqual(
                load_audit_verification_schema(),
                audit_verification_schema,
            )
            self.assertEqual(
                [],
                list(Draft202012Validator(audit_entry_schema).iter_errors(first)),
            )
            self.assertEqual(
                [],
                list(Draft202012Validator(audit_entry_schema).iter_errors(second)),
            )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["entry_count"], 2)
            self.assertEqual(report["ready_entry_count"], 2)
            self.assertEqual(report["last_entry_hash"], second["entry_hash"])
            self.assertEqual(
                report["last_source_footer_hash"],
                response["summary"]["source_footer_hash"],
            )
            self.assertEqual(
                report["last_display_hash"],
                response["summary"]["display_hash"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(audit_verification_schema).iter_errors(
                        report
                    )
                ),
            )

            cli_result = subprocess.run(
                [
                    sys.executable,
                    "tools/service_audit_verify.py",
                    "--audit-log",
                    str(audit_log),
                    "--expected-count",
                    "2",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                cli_result.returncode,
                0,
                msg=f"stdout:\n{cli_result.stdout}\nstderr:\n{cli_result.stderr}",
            )
            cli_payload = json.loads(cli_result.stdout)
            self.assertEqual(cli_payload["status"], "passed")
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(audit_verification_schema).iter_errors(
                        cli_payload
                    )
                ),
            )

            tampered_second = dict(second)
            tampered_second["previous_entry_hash"] = "bad-chain"
            tampered_second["entry_hash"] = canonical_hash(tampered_second)
            audit_log.write_text(
                "\n".join(
                    json.dumps(row, sort_keys=True)
                    for row in (first, tampered_second)
                )
                + "\n",
                encoding="utf-8",
            )
            tampered = verify_service_audit_log(audit_log, expected_count=2)
            self.assertEqual(tampered["status"], "failed")
            self.assertIn(
                "line 2.previous_entry_hash: chain mismatch",
                tampered["errors"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(audit_verification_schema).iter_errors(
                        tampered
                    )
                ),
            )

            missing_footer = dict(first)
            missing_footer.pop("source_footer_hash")
            missing_footer["entry_hash"] = canonical_hash(missing_footer)
            audit_log.write_text(
                json.dumps(missing_footer, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            missing_footer_report = verify_service_audit_log(
                audit_log,
                expected_count=1,
            )
            self.assertEqual(missing_footer_report["status"], "failed")
            self.assertIn(
                "line 1.source_footer_hash: missing required field",
                missing_footer_report["errors"],
            )

            dirty_ready = dict(first)
            dirty_ready["audit_error_count"] = 1
            dirty_ready["entry_hash"] = canonical_hash(dirty_ready)
            audit_log.write_text(
                json.dumps(dirty_ready, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            dirty_ready_report = verify_service_audit_log(
                audit_log,
                expected_count=1,
            )
            self.assertEqual(dirty_ready_report["status"], "failed")
            self.assertIn(
                "line 1.audit_error_count: ready entry must have zero audit errors",
                dirty_ready_report["errors"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(audit_verification_schema).iter_errors(
                        dirty_ready_report
                    )
                ),
            )

            empty_blocked = dict(first)
            empty_blocked["status"] = "blocked"
            empty_blocked["audit_error_count"] = 0
            empty_blocked["entry_hash"] = canonical_hash(empty_blocked)
            audit_log.write_text(
                json.dumps(empty_blocked, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            empty_blocked_report = verify_service_audit_log(
                audit_log,
                expected_count=1,
            )
            self.assertEqual(empty_blocked_report["status"], "failed")
            self.assertIn(
                "line 1.audit_error_count: blocked entry must have audit errors",
                empty_blocked_report["errors"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(audit_verification_schema).iter_errors(
                        empty_blocked_report
                    )
                ),
            )

    def test_operator_recovery_cli_verifies_restored_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-recovery-") as temp_name:
            root = Path(temp_name) / "operator"
            (root / "artifacts").mkdir(parents=True)
            (root / "runtime").mkdir()
            (root / "production_readiness_profile.json").write_text(
                json.dumps({"schema": "profile", "status": "ready"}),
                encoding="utf-8",
            )
            (root / "service_config.json").write_text(
                json.dumps({"schema": "rdllm-service-config/v1"}),
                encoding="utf-8",
            )
            (root / "operator_bootstrap_manifest.json").write_text(
                json.dumps({"schema": "rdllm-operator-bootstrap/v1"}),
                encoding="utf-8",
            )
            (root / "artifacts" / "proof.json").write_text(
                json.dumps({"summary": {"status": "ready"}}),
                encoding="utf-8",
            )
            (root / "runtime" / "audit.jsonl").write_text(
                '{"schema":"rdllm-service-audit-entry/v1"}\n',
                encoding="utf-8",
            )
            manifest = Path(temp_name) / "recovery_manifest.json"
            create = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_recovery.py",
                    "create",
                    "--root",
                    str(root),
                    "--output",
                    str(manifest),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                create.returncode,
                0,
                msg=f"stdout:\n{create.stdout}\nstderr:\n{create.stderr}",
            )
            created = json.loads(create.stdout)
            manifest_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_recovery_manifest.schema.json"
            )
            self.assertEqual(load_recovery_manifest_schema(), manifest_schema)
            manifest_errors = sorted(
                Draft202012Validator(manifest_schema).iter_errors(created),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], manifest_errors)
            self.assertEqual(created["schema"], "rdllm-operator-recovery-manifest/v1")
            self.assertEqual(created["status"], "ready")
            self.assertGreaterEqual(created["summary"]["file_count"], 5)

            verify = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_recovery.py",
                    "verify",
                    "--manifest",
                    str(manifest),
                    "--root",
                    str(root),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                verify.returncode,
                0,
                msg=f"stdout:\n{verify.stdout}\nstderr:\n{verify.stderr}",
            )
            verified = json.loads(verify.stdout)
            verification_schema = load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_recovery_verification.schema.json"
            )
            self.assertEqual(load_recovery_verification_schema(), verification_schema)
            verification_errors = sorted(
                Draft202012Validator(verification_schema).iter_errors(verified),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], verification_errors)
            self.assertEqual(
                verified["schema"],
                "rdllm-operator-recovery-verification/v1",
            )
            self.assertEqual(verified["status"], "passed")
            self.assertEqual(
                verified["checked_count"],
                created["summary"]["file_count"],
            )

            (root / "service_config.json").write_text(
                json.dumps({"schema": "tampered"}),
                encoding="utf-8",
            )
            tampered = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_recovery.py",
                    "verify",
                    "--manifest",
                    str(manifest),
                    "--root",
                    str(root),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(tampered.returncode, 1)
            tampered_payload = json.loads(tampered.stdout)
            tampered_errors = sorted(
                Draft202012Validator(verification_schema).iter_errors(
                    tampered_payload
                ),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], tampered_errors)
            self.assertEqual(tampered_payload["status"], "failed")
            self.assertIn(
                "service_config.json: sha256 mismatch",
                tampered_payload["errors"],
            )

    def test_operator_acceptance_cli_binds_response_audit_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-acceptance-") as temp_name:
            root = Path(temp_name) / "operator"
            bootstrap = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_bootstrap.py",
                    "--output-dir",
                    str(root),
                    "--operator-template",
                    "company",
                    "--operator-name",
                    "Acceptance RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--include-sample-corpus",
                    "--include-reference-artifacts",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                bootstrap.returncode,
                0,
                msg=f"stdout:\n{bootstrap.stdout}\nstderr:\n{bootstrap.stderr}",
            )
            config = load_json(root / "service_config.json")
            state = ServiceState.from_config(ServiceConfig(raw=config, root=root))
            status_code, response = _attribute(
                state,
                {
                    "prompt": "What should royalty-bearing AI answers expose?",
                    "output": (
                        "Every royalty bearing AI answer should have a provenance "
                        "record. The record should include source identifiers, "
                        "content hashes, retrieval scores, output citations, payout "
                        "weights, and an event hash that allows auditors to replay "
                        "the attribution."
                    ),
                    "gross_revenue": "1.00",
                },
            )
            self.assertEqual(status_code, 200)
            response_path = Path(temp_name) / "response.json"
            response_path.write_text(json.dumps(response), encoding="utf-8")
            display_text_path = Path(temp_name) / "copied_display_text.txt"
            display_text = response["display"]["rendered_text"]
            display_text_path.write_text(display_text, encoding="utf-8")
            event = response["event"]
            audit_path = Path(temp_name) / "audit.jsonl"
            entry = {
                "schema": "rdllm-service-audit-entry/v1",
                "request_id": "acceptance-test",
                "timestamp": "2026-07-02T00:00:00Z",
                "status": response["status"],
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "source_footer_hash": response["summary"]["source_footer_hash"],
                "display_hash": response["summary"]["display_hash"],
                "source_count": len(event.get("source_references", [])),
                "audit_error_count": len(response.get("audit_errors", [])),
                "previous_entry_hash": "",
            }
            entry["entry_hash"] = canonical_hash(entry)
            audit_path.write_text(
                json.dumps(entry, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            recovery_manifest = Path(temp_name) / "recovery_manifest.json"
            recovery = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_recovery.py",
                    "create",
                    "--root",
                    str(root),
                    "--output",
                    str(recovery_manifest),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                recovery.returncode,
                0,
                msg=f"stdout:\n{recovery.stdout}\nstderr:\n{recovery.stderr}",
            )
            report_path = Path(temp_name) / "acceptance.json"
            acceptance = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "--profile",
                    str(root / "production_readiness_profile.json"),
                    "--service-config",
                    str(root / "service_config.json"),
                    "--service-root",
                    str(root),
                    "--bootstrap-dir",
                    str(root),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--audit-log",
                    str(audit_path),
                    "--expected-audit-count",
                    "1",
                    "--recovery-manifest",
                    str(recovery_manifest),
                    "--recovery-root",
                    str(root),
                    "--no-runtime-check",
                    "--output",
                    str(report_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                acceptance.returncode,
                0,
                msg=f"stdout:\n{acceptance.stdout}\nstderr:\n{acceptance.stderr}",
            )
            report = json.loads(acceptance.stdout)
            self.assertEqual(report["status"], "ready")
            schema = load_json(
                ROOT / "docs" / "schemas" / "operator_acceptance_report.schema.json"
            )
            self.assertEqual(load_acceptance_schema(), schema)
            validation_errors = sorted(
                Draft202012Validator(schema).iter_errors(report),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], validation_errors)
            self.assertEqual(
                report["summary"]["production_acceptance_decision"],
                "block",
            )
            self.assertEqual(
                report["summary"]["audit_response_binding_status"],
                "passed",
            )
            self.assertEqual(
                report["summary"]["response_display_text_status"],
                "passed",
            )
            self.assertEqual(
                report["audit_response_binding"]["latest_entry_status"],
                "ready",
            )
            self.assertEqual(
                report["audit_response_binding"]["latest_audit_error_count"],
                0,
            )
            self.assertTrue(report["audit_response_binding"]["latest_entry_ready"])
            self.assertTrue(report["audit_response_binding"]["latest_entry_clean"])
            self.assertEqual(
                report["audit_response_binding"]["response_footer_hash"],
                response["summary"]["source_footer_hash"],
            )
            self.assertEqual(
                report["audit_response_binding"]["response_display_hash"],
                response["summary"]["display_hash"],
            )
            self.assertTrue(
                report["audit_response_binding"][
                    "source_footer_hash_matches_response"
                ]
            )
            self.assertTrue(
                report["audit_response_binding"]["display_hash_matches_response"]
            )
            self.assertEqual(
                report["evidence"]["response_display_hash"],
                response["summary"]["display_hash"],
            )
            self.assertEqual(
                report["evidence"]["response_display_text_hash"],
                canonical_hash(display_text),
            )
            self.assertEqual(verify_acceptance_report(report)["status"], "passed")
            verified = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "verify",
                    "--report",
                    str(report_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                verified.returncode,
                0,
                msg=f"stdout:\n{verified.stdout}\nstderr:\n{verified.stderr}",
            )
            verified_report = json.loads(verified.stdout)
            verification_schema = load_json(
                ROOT
                / "docs"
                / "schemas"
                / "operator_acceptance_verification.schema.json"
            )
            self.assertEqual(load_acceptance_verification_schema(), verification_schema)
            verification_errors = sorted(
                Draft202012Validator(verification_schema).iter_errors(
                    verified_report
                ),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], verification_errors)
            self.assertEqual(verified_report["status"], "passed")
            self.assertEqual(
                verified_report["computed_acceptance_report_hash"],
                report["acceptance_report_hash"],
            )
            acceptance_support_bundle_path = (
                Path(temp_name) / "acceptance_support_bundle.json"
            )
            acceptance_support = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_support_bundle.py",
                    "--skip-doctor",
                    "--acceptance-report",
                    str(report_path),
                    "--output",
                    str(acceptance_support_bundle_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                acceptance_support.returncode,
                0,
                msg=(
                    f"stdout:\n{acceptance_support.stdout}\n"
                    f"stderr:\n{acceptance_support.stderr}"
                ),
            )
            support_bundle = json.loads(acceptance_support.stdout)
            self.assertEqual(support_bundle["status"], "passed")
            support_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_support_bundle.schema.json"
            )
            support_errors = sorted(
                Draft202012Validator(support_schema).iter_errors(support_bundle),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], support_errors)
            self.assertEqual(
                support_bundle["checks_run"],
                ["acceptance_verification"],
            )
            self.assertEqual(
                support_bundle["acceptance_verification"]["status"],
                "passed",
            )
            self.assertEqual(
                support_bundle["acceptance_verification"][
                    "recorded_acceptance_report_hash"
                ],
                report["acceptance_report_hash"],
            )
            saved_support = acceptance_support_bundle_path.read_text(encoding="utf-8")
            self.assertNotIn(
                "What should royalty-bearing AI answers expose?",
                saved_support,
            )
            self.assertNotIn(
                "Every royalty bearing AI answer should have",
                saved_support,
            )

            tampered_report = json.loads(json.dumps(report))
            tampered_report["evidence"]["response_display_hash"] = "0" * 64
            tampered_report_path = Path(temp_name) / "tampered_acceptance.json"
            tampered_report_path.write_text(
                json.dumps(tampered_report, sort_keys=True),
                encoding="utf-8",
            )
            tampered = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "verify",
                    "--report",
                    str(tampered_report_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(tampered.returncode, 1)
            tampered_verification = json.loads(tampered.stdout)
            tampered_verification_errors = sorted(
                Draft202012Validator(verification_schema).iter_errors(
                    tampered_verification
                ),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], tampered_verification_errors)
            self.assertEqual(tampered_verification["status"], "failed")
            self.assertIn(
                "acceptance_report_hash: mismatch",
                tampered_verification["errors"],
            )
            self.assertIn(
                "evidence.response_display_hash: binding mismatch",
                tampered_verification["errors"],
            )
            tampered_support = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_support_bundle.py",
                    "--skip-doctor",
                    "--acceptance-report",
                    str(tampered_report_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(tampered_support.returncode, 1)
            tampered_support_report = json.loads(tampered_support.stdout)
            self.assertEqual(tampered_support_report["status"], "failed")
            self.assertEqual(
                tampered_support_report["acceptance_verification"]["status"],
                "failed",
            )
            self.assertIn(
                "acceptance_verification: acceptance_report_hash: mismatch",
                tampered_support_report["errors"],
            )

            wrong_footer_entry = dict(entry)
            wrong_footer_entry["source_footer_hash"] = "0" * 64
            wrong_footer_entry["entry_hash"] = canonical_hash(wrong_footer_entry)
            audit_path.write_text(
                json.dumps(wrong_footer_entry, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            wrong_footer_acceptance = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "--profile",
                    str(root / "production_readiness_profile.json"),
                    "--service-config",
                    str(root / "service_config.json"),
                    "--service-root",
                    str(root),
                    "--bootstrap-dir",
                    str(root),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--audit-log",
                    str(audit_path),
                    "--expected-audit-count",
                    "1",
                    "--recovery-manifest",
                    str(recovery_manifest),
                    "--recovery-root",
                    str(root),
                    "--no-runtime-check",
                    "--output",
                    str(Path(temp_name) / "wrong_footer_acceptance.json"),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(wrong_footer_acceptance.returncode, 1)
            wrong_footer_report = json.loads(wrong_footer_acceptance.stdout)
            self.assertEqual(wrong_footer_report["status"], "blocked")
            self.assertFalse(
                wrong_footer_report["audit_response_binding"][
                    "source_footer_hash_matches_response"
                ]
            )
            self.assertIn(
                (
                    "audit_response_binding: audit_log: source footer hash does "
                    "not match saved response"
                ),
                wrong_footer_report["errors"],
            )

            dirty_entry = dict(entry)
            dirty_entry["status"] = "blocked"
            dirty_entry["audit_error_count"] = 1
            dirty_entry["entry_hash"] = canonical_hash(dirty_entry)
            audit_path.write_text(
                json.dumps(dirty_entry, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            dirty_acceptance = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "--profile",
                    str(root / "production_readiness_profile.json"),
                    "--service-config",
                    str(root / "service_config.json"),
                    "--service-root",
                    str(root),
                    "--bootstrap-dir",
                    str(root),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--audit-log",
                    str(audit_path),
                    "--expected-audit-count",
                    "1",
                    "--recovery-manifest",
                    str(recovery_manifest),
                    "--recovery-root",
                    str(root),
                    "--no-runtime-check",
                    "--output",
                    str(Path(temp_name) / "dirty_acceptance.json"),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(dirty_acceptance.returncode, 1)
            dirty_report = json.loads(dirty_acceptance.stdout)
            self.assertEqual(dirty_report["status"], "blocked")
            self.assertIn(
                "audit_response_binding: audit_log: latest entry status is not ready",
                dirty_report["errors"],
            )
            self.assertIn(
                "audit_response_binding: audit_log: latest entry has audit errors",
                dirty_report["errors"],
            )

            later = dict(entry)
            later["request_id"] = "acceptance-test-later"
            later["event_hash"] = "a" * 64
            later["event_id"] = "evt_aaaaaaaaaaaaaaaa"
            later["previous_entry_hash"] = entry["entry_hash"]
            later["entry_hash"] = canonical_hash(later)
            audit_path.write_text(
                json.dumps(entry, sort_keys=True)
                + "\n"
                + json.dumps(later, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            blocked = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_acceptance.py",
                    "--profile",
                    str(root / "production_readiness_profile.json"),
                    "--service-config",
                    str(root / "service_config.json"),
                    "--service-root",
                    str(root),
                    "--bootstrap-dir",
                    str(root),
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--audit-log",
                    str(audit_path),
                    "--expected-audit-count",
                    "2",
                    "--recovery-manifest",
                    str(recovery_manifest),
                    "--recovery-root",
                    str(root),
                    "--no-runtime-check",
                    "--output",
                    str(Path(temp_name) / "blocked_acceptance.json"),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(blocked.returncode, 1)
            blocked_report = json.loads(blocked.stdout)
            self.assertEqual(blocked_report["status"], "blocked")
            self.assertIn(
                "audit_response_binding: audit_log: latest event does not match saved response",
                blocked_report["errors"],
            )

    def test_operator_acceptance_matrix_covers_all_operator_roles(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="rdllm-operator-acceptance-matrix-"
        ) as temp_name:
            output_dir = Path(temp_name) / "matrix"
            report = run_acceptance_matrix(output_dir=output_dir)
            schema = load_json(
                ROOT / "docs" / "schemas" / "operator_acceptance_matrix.schema.json"
            )
            self.assertEqual(load_acceptance_matrix_schema(), schema)
            validation_errors = sorted(
                Draft202012Validator(schema).iter_errors(report),
                key=lambda error: list(error.path),
            )
            self.assertEqual([], validation_errors)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["operator_template_count"], 5)
            self.assertEqual(report["summary"]["passed_count"], 5)
            self.assertEqual(report["summary"]["failed_count"], 0)
            self.assertEqual(report["summary"]["copied_display_verified_count"], 5)
            self.assertEqual(
                set(report["summary"]["operator_templates"]),
                {"individual", "company", "institution", "government", "public_sector"},
            )
            self.assertEqual(
                set(report["summary"]["settlement_modes"]),
                {"escrow_only", "instruction_only", "processor_attested"},
            )
            rows = {row["operator_template"]: row for row in report["rows"]}
            self.assertFalse(rows["individual"]["direct_creator_settlement_allowed"])
            self.assertFalse(rows["company"]["direct_creator_settlement_allowed"])
            self.assertFalse(rows["institution"]["direct_creator_settlement_allowed"])
            self.assertFalse(rows["government"]["direct_creator_settlement_allowed"])
            self.assertFalse(rows["public_sector"]["direct_creator_settlement_allowed"])
            self.assertFalse(rows["individual"]["public_sector_use_supported"])
            self.assertFalse(rows["company"]["public_sector_use_supported"])
            self.assertFalse(rows["institution"]["public_sector_use_supported"])
            self.assertFalse(rows["government"]["public_sector_use_supported"])
            self.assertFalse(rows["public_sector"]["public_sector_use_supported"])
            for row in rows.values():
                with self.subTest(operator_template=row["operator_template"]):
                    self.assertEqual(row["status"], "passed")
                    self.assertEqual(row["acceptance_status"], "ready")
                    self.assertEqual(row["acceptance_verification_status"], "passed")
                    self.assertEqual(row["production_acceptance_decision"], "block")
                    self.assertFalse(row["production_grade_claim_allowed"])
                    self.assertTrue(row["response_production_display_ready"])
                    self.assertEqual(row["response_display_text_status"], "passed")
                    self.assertRegex(
                        row["response_display_text_hash"],
                        r"^[0-9a-f]{64}$",
                    )
                    self.assertEqual(
                        row["source_grounding_acceptance_status"],
                        "passed",
                    )
                    self.assertTrue(Path(row["acceptance_report_path"]).is_file())
                    self.assertTrue(Path(row["response_path"]).is_file())
                    self.assertTrue(Path(row["display_text_path"]).is_file())
                    self.assertTrue(Path(row["audit_log_path"]).is_file())
                    self.assertTrue(Path(row["recovery_manifest_path"]).is_file())

    def test_readiness_is_ready_with_token_hash(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        report = readiness_report(state)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["blocked_check_count"], 0)
        ready_checks = {
            row["name"] for row in report["checks"] if row["status"] == "ready"
        }
        self.assertIn("audit_log_writable", ready_checks)

    def test_readiness_blocks_without_token_hash(self) -> None:
        os.environ.pop(TOKEN_ENV, None)
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        report = readiness_report(state)
        self.assertEqual(report["status"], "blocked")
        blocked = {row["name"] for row in report["checks"] if row["status"] != "ready"}
        self.assertIn("auth_token_hash", blocked)

    def test_readiness_blocks_unwritable_audit_log_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-audit-log-") as temp_name:
            audit_log_path = Path(temp_name) / "audit-log-as-directory"
            audit_log_path.mkdir()
            config = load_json(CONFIG_PATH)
            config["audit_log_path"] = audit_log_path.as_posix()
            state = ServiceState.from_config(ServiceConfig(raw=config))
            report = readiness_report(state)
            self.assertEqual(report["status"], "blocked")
            audit_check = next(
                row for row in report["checks"] if row["name"] == "audit_log_writable"
            )
            self.assertEqual(audit_check["status"], "blocked")
            self.assertIn("audit log is not writable", audit_check["reason"])

    def test_readiness_blocks_corrupt_existing_audit_log_chain(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-audit-log-") as temp_name:
            audit_log_path = Path(temp_name) / "service-audit.jsonl"
            audit_log_path.write_text(
                json.dumps(
                    {
                        "schema": "rdllm-service-audit-entry/v1",
                        "request_id": "request-1",
                        "timestamp": "2026-07-01T00:00:00Z",
                        "status": "ready",
                        "event_id": "evt_deadbeefdeadbeef",
                        "event_hash": "deadbeefdeadbeef" + "0" * 48,
                        "source_footer_hash": "1" * 64,
                        "display_hash": "2" * 64,
                        "source_count": 1,
                        "audit_error_count": 0,
                        "previous_entry_hash": "",
                        "entry_hash": "bad-entry-hash",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            config = load_json(CONFIG_PATH)
            config["audit_log_path"] = audit_log_path.as_posix()
            state = ServiceState.from_config(ServiceConfig(raw=config))
            report = readiness_report(state)
            self.assertEqual(report["status"], "blocked")
            audit_check = next(
                row for row in report["checks"] if row["name"] == "audit_log_writable"
            )
            self.assertEqual(audit_check["status"], "blocked")
            self.assertIn("audit log integrity failed", audit_check["reason"])
            self.assertIn("line 1.entry_hash: mismatch", audit_check["reason"])

    def test_service_config_runtime_blocks_unwritable_audit_log_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-audit-log-") as temp_name:
            audit_log_path = Path(temp_name) / "audit-log-as-directory"
            audit_log_path.mkdir()
            config = load_json(CONFIG_PATH)
            config["audit_log_path"] = audit_log_path.as_posix()
            result = service_config_result(config, root=ROOT, check_runtime=True)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["schema_status"], "passed")
            self.assertEqual(result["runtime_status"], "blocked")
            self.assertTrue(
                any(
                    error.startswith("audit_log_writable: audit log is not writable")
                    for error in result["errors"]
                )
            )

    def test_attribute_route_blocks_when_audit_commit_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-audit-commit-") as temp_name:
            config = load_json(CONFIG_PATH)
            config["audit_log_path"] = (
                Path(temp_name) / "service-audit.jsonl"
            ).as_posix()
            state = ServiceState.from_config(ServiceConfig(raw=config))
            app = make_app(state)
            body = json.dumps(
                {
                    "prompt": "What should royalty-bearing AI answers expose?",
                    "output": (
                        "Every royalty bearing AI answer should have a provenance record. "
                        "The record should include source identifiers, content hashes, "
                        "retrieval scores, output citations, payout weights, and an "
                        "event hash that allows auditors to replay the attribution."
                    ),
                    "gross_revenue": "1.00",
                }
            ).encode("utf-8")
            captured: list[tuple[str, list[tuple[str, str]]]] = []

            def start_response(
                status: str,
                headers: list[tuple[str, str]],
            ) -> None:
                captured.append((status, headers))

            environ = {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/v1/attribute",
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": BytesIO(body),
                "HTTP_AUTHORIZATION": "Bearer rdllm-local-dev-token",
                "REMOTE_ADDR": "127.0.0.1",
            }
            with patch(
                "rdllm.service._append_audit_log",
                side_effect=AuditLogError("simulated durable audit failure"),
            ):
                raw_body = b"".join(app(environ, start_response))

            self.assertEqual(captured[0][0], "503 Service Unavailable")
            payload = json.loads(raw_body)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["error"], "audit log append failed")
            self.assertIn(
                "audit_log: simulated durable audit failure",
                payload["audit_errors"],
            )
            self.assertNotIn("display", payload)
            self.assertNotIn("source_footer", payload)
            self.assertEqual(state.blocked_requests_total, 1)
            self.assertEqual(state.audit_errors_total, 1)

    def test_readiness_blocks_configured_provider_without_api_key(self) -> None:
        config = load_json(ROOT / "examples" / "service_config.openai_compatible.json")
        state = ServiceState.from_config(ServiceConfig(raw=config))
        report = readiness_report(state)
        self.assertEqual(report["status"], "blocked")
        blocked = {row["name"] for row in report["checks"] if row["status"] != "ready"}
        self.assertIn("provider_route:openai-compatible-default", blocked)

    def test_readiness_blocks_placeholder_provider_route_even_with_api_key(self) -> None:
        config = load_json(ROOT / "examples" / "service_config.openai_compatible.json")
        old_provider_key = os.environ.get("RDLLM_PROVIDER_OPENAI_KEY")
        try:
            os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = "test-provider-key"
            state = ServiceState.from_config(ServiceConfig(raw=config))
            report = readiness_report(state)
        finally:
            if old_provider_key is None:
                os.environ.pop("RDLLM_PROVIDER_OPENAI_KEY", None)
            else:
                os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = old_provider_key
        self.assertEqual(report["status"], "blocked")
        provider_check = next(
            row
            for row in report["checks"]
            if row["name"] == "provider_route:openai-compatible-default"
        )
        self.assertEqual(provider_check["status"], "blocked")
        self.assertIn("provider model is still a placeholder", provider_check["reason"])

    def test_service_config_runtime_blocks_placeholder_provider_route(self) -> None:
        config = load_json(ROOT / "examples" / "service_config.openai_compatible.json")
        old_provider_key = os.environ.get("RDLLM_PROVIDER_OPENAI_KEY")
        try:
            os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = "test-provider-key"
            result = service_config_result(config, root=ROOT, check_runtime=True)
        finally:
            if old_provider_key is None:
                os.environ.pop("RDLLM_PROVIDER_OPENAI_KEY", None)
            else:
                os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = old_provider_key
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["schema_status"], "passed")
        self.assertEqual(result["runtime_status"], "blocked")
        self.assertIn(
            "provider_route:openai-compatible-default: "
            "provider model is still a placeholder: replace-with-provider-model",
            result["errors"],
        )

    def test_readiness_blocks_reserved_example_provider_base_url(self) -> None:
        config = load_json(ROOT / "examples" / "service_config.openai_compatible.json")
        config["providers"][0]["model"] = "real-provider-model"
        config["providers"][0]["base_url"] = "https://provider.example"
        old_provider_key = os.environ.get("RDLLM_PROVIDER_OPENAI_KEY")
        try:
            os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = "test-provider-key"
            state = ServiceState.from_config(ServiceConfig(raw=config))
            report = readiness_report(state)
        finally:
            if old_provider_key is None:
                os.environ.pop("RDLLM_PROVIDER_OPENAI_KEY", None)
            else:
                os.environ["RDLLM_PROVIDER_OPENAI_KEY"] = old_provider_key
        provider_check = next(
            row
            for row in report["checks"]
            if row["name"] == "provider_route:openai-compatible-default"
        )
        self.assertEqual(provider_check["status"], "blocked")
        self.assertIn("provider base_url is still a placeholder", provider_check["reason"])

    def test_prometheus_metrics_export_ready_state(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        text = prometheus_metrics(state)
        self.assertIn("rdllm_service_ready 1", text)
        self.assertIn("rdllm_service_requests_total", text)

    def test_attribute_response_exposes_verifiable_source_footer(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "ready")
        schema = load_json(
            ROOT / "docs" / "schemas" / "service_attribution_response.schema.json"
        )
        errors = list(Draft202012Validator(schema).iter_errors(response))
        self.assertEqual(errors, [])
        footer = response["source_footer"]
        display = response["display"]
        self.assertEqual(footer["schema"], "rdllm-service-source-footer/v1")
        self.assertEqual(footer["status"], "verified")
        self.assertEqual(footer["event_hash"], response["summary"]["event_hash"])
        self.assertEqual(footer["footer_hash"], response["summary"]["source_footer_hash"])
        self.assertEqual(display["schema"], "rdllm-service-display/v1")
        self.assertEqual(display["event_hash"], response["summary"]["event_hash"])
        self.assertEqual(display["source_footer_hash"], footer["footer_hash"])
        self.assertEqual(
            display["rendered_text_hash"],
            response["summary"]["display_hash"],
        )
        self.assertTrue(
            display["rendered_text"].startswith(response["event"]["answer_text"])
        )
        self.assertIn(footer["rendered_text"], display["rendered_text"])
        self.assertGreaterEqual(footer["source_count"], 1)
        self.assertGreaterEqual(footer["claim_count"], 1)
        self.assertIn("Sources", footer["rendered_text"])
        self.assertIn("Claim Evidence", footer["rendered_text"])
        first_source_row = footer["source_rows"][0]
        self.assertIn(
            f"support={first_source_row['output_support']:.3f}",
            footer["rendered_text"],
        )
        self.assertIn(
            f"text_match={first_source_row['text_match_score']:.3f}",
            footer["rendered_text"],
        )
        self.assertIn(
            f"weight={first_source_row['contribution_weight']}",
            footer["rendered_text"],
        )
        self.assertIn(
            f"payout={first_source_row['payout']}",
            footer["rendered_text"],
        )
        self.assertEqual(
            first_source_row["usage_metric_profile"],
            SOURCE_USAGE_METRIC_PROFILE,
        )
        self.assertEqual(
            first_source_row["usage_metric_scope"],
            SOURCE_USAGE_METRIC_SCOPE,
        )
        self.assertEqual(
            first_source_row["support_metric_method"],
            SOURCE_USAGE_METRIC_METHODS["support"],
        )
        self.assertEqual(
            first_source_row["text_match_metric_method"],
            SOURCE_USAGE_METRIC_METHODS["text_match"],
        )
        self.assertEqual(
            first_source_row["weight_metric_method"],
            SOURCE_USAGE_METRIC_METHODS["weight"],
        )
        self.assertEqual(
            first_source_row["payout_metric_method"],
            SOURCE_USAGE_METRIC_METHODS["payout"],
        )
        self.assertIn(
            f"metrics={SOURCE_USAGE_METRIC_PROFILE};",
            footer["rendered_text"],
        )
        self.assertIn(
            f"scope={SOURCE_USAGE_METRIC_SCOPE};",
            footer["rendered_text"],
        )
        self.assertIn(
            f"support:{SOURCE_USAGE_METRIC_METHODS['support']}",
            footer["rendered_text"],
        )
        self.assertIn("methods=", footer["rendered_text"])
        claim_section = footer["rendered_text"].split("Claim Evidence\n", 1)[1]
        supported_claim_row = next(
            row for row in footer["claim_rows"] if row["supported"]
        )
        expected_warrant = claim_warrant_report(
            claim=supported_claim_row["claim_preview"],
            evidence=supported_claim_row["evidence_preview"],
            supported=True,
        )
        expected_disagreement = claim_source_disagreement_report(
            claim=supported_claim_row["claim_preview"],
            source_label=supported_claim_row["source_label"],
            source_rows=footer["source_rows"],
            supported=True,
        )
        self.assertEqual(
            supported_claim_row["claim_warrant_profile"],
            CLAIM_WARRANT_PROFILE,
        )
        self.assertEqual(
            supported_claim_row["warrant_strength_status"],
            "passed",
        )
        self.assertEqual(supported_claim_row["warrant_mismatch_flags"], [])
        self.assertEqual(
            {
                key: supported_claim_row[key]
                for key in (
                    "claim_warrant_profile",
                    "claim_force_flags",
                    "evidence_force_flags",
                    "warrant_mismatch_flags",
                    "warrant_strength_status",
                )
            },
            expected_warrant,
        )
        self.assertEqual(
            supported_claim_row["source_disagreement_profile"],
            SOURCE_DISAGREEMENT_PROFILE,
        )
        self.assertEqual(
            supported_claim_row["source_disagreement_status"],
            "passed",
        )
        self.assertEqual(supported_claim_row["disagreement_source_labels"], [])
        self.assertIn(
            supported_claim_row["source_label"],
            supported_claim_row["agreement_source_labels"],
        )
        self.assertEqual(
            {
                key: supported_claim_row[key]
                for key in (
                    "source_disagreement_profile",
                    "agreement_source_labels",
                    "disagreement_source_labels",
                    "source_disagreement_status",
                )
            },
            expected_disagreement,
        )
        self.assertIn(
            f"[C{supported_claim_row['claim_index']}] "
            f"{supported_claim_row['source_label']};",
            claim_section,
        )
        self.assertIn(
            f"Claim: {supported_claim_row['claim_preview']}",
            claim_section,
        )
        self.assertIn("warrant=passed;", claim_section)
        self.assertIn("disagreement=passed;", claim_section)
        self.assertIn("conflicts=none;", claim_section)
        self.assertIn(f"disagreement_profile={SOURCE_DISAGREEMENT_PROFILE}.", claim_section)
        self.assertIn(f"profile={CLAIM_WARRANT_PROFILE}.", claim_section)
        self.assertIn(
            f"Evidence: {supported_claim_row['evidence_preview']}",
            claim_section,
        )
        self.assertTrue(all(row["source_uri"] for row in footer["source_rows"]))
        self.assertTrue(
            all(row["content_hash"] for row in footer["source_rows"])
        )
        self.assertTrue(
            all(row["verification_handle"] for row in footer["source_rows"])
        )
        self.assertTrue(
            all(
                row["verification_handle"].startswith(
                    "rdllm://verify/source-footer/"
                )
                for row in footer["source_rows"]
            )
        )
        self.assertIn("verify=rdllm://verify/source-footer/", footer["rendered_text"])
        self.assertTrue(
            any(row["supported"] for row in footer["claim_rows"])
        )
        self.assertEqual(
            footer["footer_hash"],
            canonical_hash(
                {key: value for key, value in footer.items() if key != "footer_hash"}
            ),
        )
        footer_verification_schema = load_json(
            ROOT
            / "docs"
            / "schemas"
            / "service_source_footer_verification.schema.json"
        )
        self.assertEqual(
            load_source_footer_verification_schema(),
            footer_verification_schema,
        )
        footer_verification = verify_source_footer(
            footer,
            display_text=display["rendered_text"],
            display_text_path="copied-output.txt",
        )
        self.assertEqual(footer_verification["status"], "passed")
        self.assertTrue(footer_verification["public_footer_ready"])
        self.assertTrue(footer_verification["copied_display_footer_ready"])
        self.assertEqual(footer_verification["display_text_status"], "passed")
        self.assertEqual(footer_verification["handle_status"], "passed")
        self.assertEqual(
            footer_verification["source_usage_metric_provenance_status"],
            "passed",
        )
        self.assertEqual(
            footer_verification["claim_warrant_strength_status"],
            "passed",
        )
        self.assertEqual(
            footer_verification["claim_source_disagreement_status"],
            "passed",
        )
        self.assertEqual(footer_verification["row_hash_status"], "passed")
        self.assertEqual(footer_verification["claim_hash_status"], "passed")
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )
        verification = verify_service_response(response)
        verification_schema = load_json(
            ROOT / "docs" / "schemas" / "service_response_verification.schema.json"
        )
        self.assertEqual(load_response_verification_schema(), verification_schema)
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(verification["response_status"], "ready")
        self.assertTrue(verification["production_display_ready"])
        self.assertEqual(verification["display_text_status"], "not_checked")
        copied_verification = verify_service_response(
            response,
            display_text=display["rendered_text"],
            display_text_path="copied-output.txt",
        )
        self.assertEqual(copied_verification["status"], "passed")
        self.assertEqual(copied_verification["display_text_status"], "passed")
        self.assertEqual(
            copied_verification["display_text_hash"],
            canonical_hash(display["rendered_text"]),
        )
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(
            acceptance["schema"],
            "rdllm-service-source-grounding-acceptance/v1",
        )
        self.assertEqual(acceptance["status"], "passed")
        self.assertEqual(acceptance["source_materialization_status"], "passed")
        self.assertEqual(acceptance["fact_support_status"], "passed")
        self.assertEqual(acceptance["royalty_attribution_status"], "passed")
        self.assertEqual(acceptance["display_binding_status"], "passed")
        self.assertEqual(acceptance["citation_marker_status"], "passed")
        self.assertEqual(acceptance["source_locator_status"], "passed")
        self.assertEqual(acceptance["source_usage_metric_status"], "passed")
        self.assertEqual(
            acceptance["source_usage_metric_provenance_status"],
            "passed",
        )
        self.assertEqual(acceptance["source_identity_status"], "passed")
        self.assertEqual(acceptance["temporal_grounding_status"], "passed")
        self.assertEqual(acceptance["answer_link_status"], "passed")
        self.assertEqual(acceptance["answer_claim_coverage_status"], "passed")
        self.assertEqual(acceptance["model_reliance_claim_status"], "passed")
        self.assertEqual(acceptance["claim_evidence_status"], "passed")
        self.assertEqual(acceptance["claim_warrant_strength_status"], "passed")
        self.assertEqual(acceptance["claim_source_disagreement_status"], "passed")
        self.assertEqual(acceptance["claim_source_closure_status"], "passed")
        self.assertEqual(acceptance["attribution_gap_status"], "passed")
        self.assertEqual(acceptance["attribution_gap_verdict"], "closed")
        self.assertEqual(
            acceptance["attribution_gap_consumed_without_credit_count"],
            0,
        )
        self.assertEqual(
            acceptance["attribution_gap_cited_without_access_count"],
            0,
        )
        self.assertEqual(acceptance["attribution_gap_paid_hidden_count"], 0)
        self.assertGreaterEqual(
            acceptance["attribution_gap_accessed_source_count"],
            1,
        )
        self.assertGreaterEqual(
            acceptance["attribution_gap_credited_source_count"],
            1,
        )
        self.assertEqual(
            acceptance["source_usage_metric_names"],
            ["support", "text_match", "weight", "payout"],
        )
        self.assertEqual(
            acceptance["source_usage_metric_row_count"],
            acceptance["source_count"],
        )
        self.assertEqual(
            acceptance["source_usage_metric_profile"],
            SOURCE_USAGE_METRIC_PROFILE,
        )
        self.assertEqual(
            acceptance["source_usage_metric_scope"],
            SOURCE_USAGE_METRIC_SCOPE,
        )
        self.assertEqual(
            acceptance["source_usage_metric_methods"],
            SOURCE_USAGE_METRIC_METHODS,
        )
        self.assertEqual(
            acceptance["source_usage_metric_provenance_count"],
            acceptance["source_count"],
        )
        self.assertEqual(
            acceptance["source_locator_count"],
            acceptance["source_count"],
        )
        self.assertEqual(
            acceptance["source_identity_count"],
            acceptance["source_count"],
        )
        self.assertEqual(
            acceptance["claim_evidence_row_count"],
            acceptance["supported_claim_count"],
        )
        self.assertEqual(acceptance["claim_warrant_profile"], CLAIM_WARRANT_PROFILE)
        self.assertEqual(
            acceptance["claim_warrant_strength_count"],
            acceptance["supported_claim_count"],
        )
        self.assertEqual(
            acceptance["source_disagreement_profile"],
            SOURCE_DISAGREEMENT_PROFILE,
        )
        self.assertEqual(
            acceptance["claim_source_disagreement_count"],
            acceptance["supported_claim_count"],
        )
        self.assertEqual(
            acceptance["claim_source_closure_count"],
            acceptance["supported_claim_count"],
        )
        self.assertEqual(acceptance["answer_citation_markers"], [])
        self.assertEqual(acceptance["resolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["unresolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["answer_citation_marker_count"], 0)
        self.assertEqual(acceptance["resolved_answer_citation_marker_count"], 0)
        self.assertEqual(acceptance["answer_link_uris"], [])
        self.assertEqual(acceptance["resolved_answer_link_uris"], [])
        self.assertEqual(acceptance["unresolved_answer_link_uris"], [])
        self.assertEqual(acceptance["answer_link_uri_count"], 0)
        self.assertEqual(acceptance["resolved_answer_link_uri_count"], 0)
        self.assertEqual(acceptance["unresolved_answer_link_uri_count"], 0)
        self.assertEqual(
            acceptance["answer_claim_row_coverage_count"],
            acceptance["answer_claim_unit_count"],
        )
        self.assertEqual(acceptance["answer_claim_unit_count"], acceptance["claim_count"])
        self.assertEqual(acceptance["uncovered_answer_claim_hashes"], [])
        self.assertEqual(acceptance["extra_claim_row_hashes"], [])
        self.assertEqual(acceptance["model_reliance_claim_markers"], [])
        self.assertEqual(acceptance["model_reliance_claim_marker_count"], 0)
        self.assertEqual(acceptance["temporal_claim_markers"], [])
        self.assertEqual(acceptance["temporal_claim_marker_count"], 0)
        self.assertGreaterEqual(acceptance["source_count"], 1)
        self.assertEqual(
            acceptance["verification_handle_count"],
            acceptance["source_count"],
        )
        self.assertGreaterEqual(acceptance["supported_claim_count"], 1)
        self.assertEqual(acceptance["unsupported_claim_count"], 0)
        self.assertGreaterEqual(acceptance["minimum_support_score"], 0.75)
        self.assertEqual(
            acceptance["royalty_covered_source_count"],
            acceptance["source_count"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        with tempfile.TemporaryDirectory(prefix="rdllm-response-verify-") as temp_name:
            response_path = Path(temp_name) / "response.json"
            footer_path = Path(temp_name) / "source-footer.json"
            display_text_path = Path(temp_name) / "copied-output.txt"
            stripped_display_path = Path(temp_name) / "stripped-output.txt"
            response_path.write_text(json.dumps(response), encoding="utf-8")
            footer_path.write_text(json.dumps(footer), encoding="utf-8")
            display_text_path.write_text(display["rendered_text"], encoding="utf-8")
            stripped_display_path.write_text(
                response["event"]["answer_text"],
                encoding="utf-8",
            )
            footer_cli = subprocess.run(
                [
                    sys.executable,
                    "tools/source_footer_verify.py",
                    "--footer",
                    str(footer_path),
                    "--display-text",
                    str(display_text_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                footer_cli.returncode,
                0,
                msg=f"stdout:\n{footer_cli.stdout}\nstderr:\n{footer_cli.stderr}",
            )
            footer_cli_payload = json.loads(footer_cli.stdout)
            self.assertEqual(footer_cli_payload["status"], "passed")
            self.assertTrue(footer_cli_payload["copied_display_footer_ready"])
            stripped_footer_cli = subprocess.run(
                [
                    sys.executable,
                    "tools/source_footer_verify.py",
                    "--footer",
                    str(footer_path),
                    "--display-text",
                    str(stripped_display_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(stripped_footer_cli.returncode, 1)
            stripped_footer_payload = json.loads(stripped_footer_cli.stdout)
            self.assertEqual(stripped_footer_payload["status"], "failed")
            self.assertEqual(stripped_footer_payload["display_text_status"], "failed")
            self.assertIn(
                "display_text: missing exact source footer",
                stripped_footer_payload["errors"],
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/service_response_verify.py",
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(display_text_path),
                    "--json",
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
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["display_text_status"], "passed")
            self.assertEqual(
                payload["display_text_hash"],
                canonical_hash(display["rendered_text"]),
            )
            self.assertEqual(
                payload["source_grounding_acceptance"]["status"],
                "passed",
            )
            self.assertEqual(
                [],
                list(Draft202012Validator(verification_schema).iter_errors(payload)),
            )
            self.assertEqual(
                payload["display_hash"],
                response["summary"]["display_hash"],
            )
            stripped_result = subprocess.run(
                [
                    sys.executable,
                    "tools/service_response_verify.py",
                    "--response",
                    str(response_path),
                    "--display-text",
                    str(stripped_display_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(stripped_result.returncode, 0)
            stripped_payload = json.loads(stripped_result.stdout)
            self.assertEqual(stripped_payload["status"], "failed")
            self.assertEqual(stripped_payload["display_text_status"], "failed")
            self.assertFalse(stripped_payload["production_display_ready"])
            self.assertIn(
                "display_text: does not match answer plus footer",
                stripped_payload["errors"],
            )
            self.assertIn(
                "display_text: missing source verification handles",
                stripped_payload["errors"],
            )
            self.assertEqual(
                [],
                list(
                    Draft202012Validator(verification_schema).iter_errors(
                        stripped_payload
                    )
                ),
            )

    def test_attribute_response_resolves_numeric_answer_citation_markers(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record [1]. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "ready")
        self.assertEqual(response["audit_errors"], [])
        self.assertEqual(response["source_footer"]["source_rows"][0]["label"], "S1")
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertTrue(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["status"], "passed")
        self.assertEqual(acceptance["citation_marker_status"], "passed")
        self.assertEqual(acceptance["answer_citation_markers"], ["[1]"])
        self.assertEqual(acceptance["resolved_answer_citation_markers"], ["[1]"])
        self.assertEqual(acceptance["unresolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["answer_citation_marker_count"], 1)
        self.assertEqual(acceptance["resolved_answer_citation_marker_count"], 1)
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_attribute_response_ignores_bracketed_years_as_citations(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record [2026]. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "ready")
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertTrue(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["citation_marker_status"], "passed")
        self.assertEqual(acceptance["answer_citation_markers"], [])
        self.assertEqual(acceptance["resolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["unresolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["answer_citation_marker_count"], 0)
        self.assertEqual(acceptance["resolved_answer_citation_marker_count"], 0)
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_attribute_response_blocks_partly_unresolved_citation_groups(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record [1, 2]. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(response["status"], "blocked")
        self.assertTrue(
            any(
                error.startswith(
                    "answer_citations: unresolved inline citation markers [1, 2]"
                )
                for error in response["audit_errors"]
            )
        )
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertFalse(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["status"], "failed")
        self.assertEqual(acceptance["citation_marker_status"], "failed")
        self.assertEqual(acceptance["answer_citation_markers"], ["[1, 2]"])
        self.assertEqual(acceptance["resolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["unresolved_answer_citation_markers"], ["[1, 2]"])
        self.assertEqual(acceptance["answer_citation_marker_count"], 1)
        self.assertEqual(acceptance["resolved_answer_citation_marker_count"], 0)
        self.assertIn(
            "answer_citations: unresolved inline citation markers [1, 2]",
            acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_attribute_response_blocks_unresolved_answer_citation_markers(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record [2]. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(response["status"], "blocked")
        self.assertTrue(
            any(
                error.startswith(
                    "answer_citations: unresolved inline citation markers [2]"
                )
                for error in response["audit_errors"]
            )
        )
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertFalse(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["status"], "failed")
        self.assertEqual(acceptance["citation_marker_status"], "failed")
        self.assertEqual(acceptance["answer_citation_markers"], ["[2]"])
        self.assertEqual(acceptance["resolved_answer_citation_markers"], [])
        self.assertEqual(acceptance["unresolved_answer_citation_markers"], ["[2]"])
        self.assertEqual(acceptance["answer_citation_marker_count"], 1)
        self.assertEqual(acceptance["resolved_answer_citation_marker_count"], 0)
        self.assertIn(
            "answer_citations: unresolved inline citation markers [2]",
            acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_attribute_response_blocks_unverified_answer_links(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        foreign_uri = "https://example.invalid/unsupported-source"
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution. "
                    f"See [outside source]({foreign_uri})."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(response["status"], "blocked")
        self.assertTrue(
            any(
                error.startswith("answer_links: unverified answer source links")
                for error in response["audit_errors"]
            )
        )
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertFalse(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["status"], "failed")
        self.assertEqual(acceptance["answer_link_status"], "failed")
        self.assertEqual(acceptance["answer_link_uris"], [foreign_uri])
        self.assertEqual(acceptance["resolved_answer_link_uris"], [])
        self.assertEqual(acceptance["unresolved_answer_link_uris"], [foreign_uri])
        self.assertEqual(acceptance["answer_link_uri_count"], 1)
        self.assertEqual(acceptance["resolved_answer_link_uri_count"], 0)
        self.assertEqual(acceptance["unresolved_answer_link_uri_count"], 1)
        self.assertIn(
            f"answer_links: unverified answer source links {foreign_uri}",
            acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_attribute_response_blocks_model_reliance_claims(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution. "
                    "I used the provenance ledger in my reasoning."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(response["status"], "blocked")
        self.assertTrue(
            any(
                error.startswith(
                    "answer_model_reliance: unverified model-internal reliance claims"
                )
                for error in response["audit_errors"]
            )
        )
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertFalse(verification["production_display_ready"])
        acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(acceptance["model_reliance_claim_status"], "failed")
        self.assertIn("i used", acceptance["model_reliance_claim_markers"])
        self.assertIn("my reasoning", acceptance["model_reliance_claim_markers"])
        self.assertIn(
            (
                "answer_model_reliance: unverified model-internal reliance claims "
                "i used, my reasoning"
            ),
            acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_service_response_verifier_rejects_tampered_footer(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        _status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        response["source_footer"]["source_rows"][0]["title"] = "Tampered Source"
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "failed")
        self.assertIn(
            "source_footer.source_rows[0].row_hash: mismatch",
            verification["errors"],
        )
        self.assertIn("source_footer.footer_hash: mismatch", verification["errors"])
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_display = json.loads(json.dumps(response))
        tampered_display["source_footer"]["source_rows"][0]["title"] = (
            "Provenance Ledgers for AI Outputs"
        )
        tampered_display["display"]["rendered_text"] = "Answer without sources"
        verification = verify_service_response(tampered_display)
        self.assertEqual(verification["status"], "failed")
        self.assertIn(
            "display.rendered_text: does not match answer plus footer",
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

    def test_service_response_verifier_rejects_self_consistent_footer_lies(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        _status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "Every royalty bearing AI answer should have a provenance record. "
                    "The record should include source identifiers, content hashes, "
                    "retrieval scores, output citations, payout weights, and an "
                    "event hash that allows auditors to replay the attribution."
                ),
                "gross_revenue": "1.00",
            },
        )
        verification_schema = load_response_verification_schema()
        footer_verification_schema = load_source_footer_verification_schema()

        def rebind_footer(payload: dict[str, object]) -> None:
            footer = payload["source_footer"]
            assert isinstance(footer, dict)
            footer["footer_hash"] = canonical_hash(
                {key: value for key, value in footer.items() if key != "footer_hash"}
            )
            summary = payload["summary"]
            display = payload["display"]
            event = payload["event"]
            assert isinstance(summary, dict)
            assert isinstance(display, dict)
            assert isinstance(event, dict)
            summary["source_footer_hash"] = footer["footer_hash"]
            display["source_footer_hash"] = footer["footer_hash"]
            display["rendered_text"] = (
                f"{str(event.get('answer_text', event.get('output', ''))).rstrip()}"
                f"\n\n{footer['rendered_text']}"
            )
            display["rendered_text_hash"] = canonical_hash(display["rendered_text"])
            summary["display_hash"] = display["rendered_text_hash"]

        def rerender_footer(payload: dict[str, object]) -> None:
            footer = payload["source_footer"]
            event = payload["event"]
            assert isinstance(footer, dict)
            assert isinstance(event, dict)
            footer["rendered_text"] = render_source_footer_text(
                source_rows=[
                    row for row in footer["source_rows"] if isinstance(row, dict)
                ],
                claim_rows=[
                    row for row in footer["claim_rows"] if isinstance(row, dict)
                ],
                grounding_report=event.get("grounding_report", {}),
            )

        def rehash_row(row: dict[str, object]) -> None:
            row["row_hash"] = canonical_hash(
                {key: value for key, value in row.items() if key != "row_hash"}
            )

        def rebind_event(payload: dict[str, object]) -> None:
            event = payload["event"]
            summary = payload["summary"]
            footer = payload["source_footer"]
            display = payload["display"]
            assert isinstance(event, dict)
            assert isinstance(summary, dict)
            assert isinstance(footer, dict)
            assert isinstance(display, dict)

            event["event_hash"] = event_hash_from_event(event)
            event["event_id"] = f"evt_{event['event_hash'][:16]}"
            summary["event_id"] = event["event_id"]
            summary["event_hash"] = event["event_hash"]
            summary["attribution_gap_verdict"] = event["attribution_gap"]["verdict"]
            footer["event_id"] = event["event_id"]
            footer["event_hash"] = event["event_hash"]
            public_verifier = footer["public_verifier"]
            assert isinstance(public_verifier, dict)
            public_verifier["event_hash"] = event["event_hash"]
            public_verifier["attribution_gap_verdict"] = event["attribution_gap"][
                "verdict"
            ]
            display["event_id"] = event["event_id"]
            display["event_hash"] = event["event_hash"]
            display["answer_text_hash"] = canonical_hash(
                str(event.get("answer_text", event.get("output", "")))
            )

            for source_row in footer["source_rows"]:
                assert isinstance(source_row, dict)
                old_handle = source_row["verification_handle"]
                source_row["verification_handle"] = (
                    "rdllm://verify/source-footer/"
                    f"{event['event_id']}/{source_row['label']}/"
                    f"{source_row['content_hash'][:12]}"
                )
                rehash_row(source_row)
                footer["rendered_text"] = footer["rendered_text"].replace(
                    old_handle,
                    source_row["verification_handle"],
                )

            rebind_footer(payload)

        tampered_score = json.loads(json.dumps(response))
        source_row = tampered_score["source_footer"]["source_rows"][0]
        source_row["minimum_support_score"] = (
            0.0 if source_row["minimum_support_score"] != 0.0 else 1.0
        )
        source_row["row_hash"] = canonical_hash(source_row)
        rebind_footer(tampered_score)
        verification = verify_service_response(tampered_score)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        self.assertIn(
            (
                "source_footer.source_rows[0].minimum_support_score: "
                "does not match supported claim rows"
            ),
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_identity = json.loads(json.dumps(response))
        source_row = tampered_identity["source_footer"]["source_rows"][0]
        old_uri = source_row["source_uri"]
        source_row["source_uri"] = "https://example.invalid/swapped-source"
        rehash_row(source_row)
        tampered_identity["source_footer"]["rendered_text"] = tampered_identity[
            "source_footer"
        ]["rendered_text"].replace(old_uri, source_row["source_uri"], 1)
        rebind_footer(tampered_identity)
        verification = verify_service_response(tampered_identity)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        identity_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(identity_acceptance["source_identity_status"], "failed")
        self.assertEqual(identity_acceptance["source_locator_status"], "passed")
        self.assertEqual(identity_acceptance["source_identity_count"], 0)
        self.assertIn(
            (
                "source_identity: not every visible source row matches event "
                "source reference identity"
            ),
            identity_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_metric_provenance = json.loads(json.dumps(response))
        source_row = tampered_metric_provenance["source_footer"]["source_rows"][0]
        old_method = source_row["support_metric_method"]
        source_row["support_metric_method"] = "rdllm-unvalidated-support-method/v0"
        rehash_row(source_row)
        tampered_metric_provenance["source_footer"]["rendered_text"] = (
            tampered_metric_provenance["source_footer"]["rendered_text"].replace(
                old_method,
                source_row["support_metric_method"],
                1,
            )
        )
        rebind_footer(tampered_metric_provenance)
        verification = verify_service_response(tampered_metric_provenance)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        metric_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(
            metric_acceptance["source_usage_metric_provenance_status"],
            "failed",
        )
        self.assertLess(
            metric_acceptance["source_usage_metric_provenance_count"],
            metric_acceptance["source_count"],
        )
        self.assertIn(
            (
                "source_usage_metric_provenance: not every visible source row "
                "exposes metric profile, scope, and methods"
            ),
            metric_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )
        footer_verification = verify_source_footer(
            tampered_metric_provenance["source_footer"],
            display_text=tampered_metric_provenance["display"]["rendered_text"],
        )
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(
            footer_verification["source_usage_metric_provenance_status"],
            "failed",
        )
        self.assertIn(
            (
                "source_rows: every source row must include source usage metric "
                "profile, scope, and methods"
            ),
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )

        tampered_warrant = json.loads(json.dumps(response))
        footer = tampered_warrant["source_footer"]
        event = tampered_warrant["event"]
        assert isinstance(footer, dict)
        assert isinstance(event, dict)
        claim_row = next(
            row
            for row in footer["claim_rows"]
            if isinstance(row, dict)
            and row.get("supported")
            and row.get("claim_force_flags")
        )
        old_span_hash = claim_row["evidence_span_hash"]
        weak_evidence = "A provenance record can help auditors inspect attribution."
        weak_span_hash = stable_hash(weak_evidence)
        claim_row["evidence_preview"] = weak_evidence
        claim_row["evidence_span_hash"] = weak_span_hash
        claim_row["evidence_span_hash_prefix"] = weak_span_hash[:12]
        claim_row["evidence_start_char"] = 0
        claim_row["evidence_end_char"] = len(weak_evidence)
        claim_row.update(
            claim_warrant_report(
                claim=claim_row["claim_preview"],
                evidence=weak_evidence,
                supported=True,
            )
        )
        rehash_row(claim_row)
        source_row = next(
            row
            for row in footer["source_rows"]
            if isinstance(row, dict) and row["label"] == claim_row["source_label"]
        )
        source_row["evidence_span_hashes"] = [
            weak_span_hash if value == old_span_hash else value
            for value in source_row["evidence_span_hashes"]
        ]
        rehash_row(source_row)
        event_claim = event["claim_support"][claim_row["claim_index"] - 1]
        event_claim["evidence_text"] = weak_evidence
        event_claim["evidence_span_hash"] = weak_span_hash
        event_claim["evidence_start_char"] = 0
        event_claim["evidence_end_char"] = len(weak_evidence)
        event_source = next(
            row
            for row in event["source_references"]
            if row["label"] == claim_row["source_label"]
        )
        event_source["evidence_span_hashes"] = [
            weak_span_hash if value == old_span_hash else value
            for value in event_source["evidence_span_hashes"]
        ]
        rerender_footer(tampered_warrant)
        rebind_event(tampered_warrant)
        verification = verify_service_response(tampered_warrant)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        warrant_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(warrant_acceptance["claim_evidence_status"], "passed")
        self.assertEqual(
            warrant_acceptance["claim_warrant_strength_status"],
            "failed",
        )
        self.assertLess(
            warrant_acceptance["claim_warrant_strength_count"],
            warrant_acceptance["supported_claim_count"],
        )
        self.assertIn(
            (
                "claim_warrant_strength: not every supported claim passes "
                "evidence-force calibration"
            ),
            warrant_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )
        footer_verification = verify_source_footer(
            tampered_warrant["source_footer"],
            display_text=tampered_warrant["display"]["rendered_text"],
        )
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(
            footer_verification["claim_warrant_strength_status"],
            "failed",
        )
        self.assertIn(
            (
                "claim_rows: every supported claim must pass evidence-force "
                "calibration"
            ),
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )

        tampered_disagreement = json.loads(json.dumps(response))
        footer = tampered_disagreement["source_footer"]
        event = tampered_disagreement["event"]
        assert isinstance(footer, dict)
        assert isinstance(event, dict)
        source_row = footer["source_rows"][0]
        conflicting_quote = (
            "No royalty bearing AI answer should have a provenance record."
        )
        source_row["evidence_preview"] = conflicting_quote
        rehash_row(source_row)
        event_source = event["source_references"][0]
        event_source["quote"] = conflicting_quote
        for claim_row in footer["claim_rows"]:
            if not isinstance(claim_row, dict) or not claim_row.get("supported"):
                continue
            claim_row.update(
                claim_source_disagreement_report(
                    claim=claim_row["claim_preview"],
                    source_label=claim_row["source_label"],
                    source_rows=footer["source_rows"],
                    supported=True,
                )
            )
            rehash_row(claim_row)
        rerender_footer(tampered_disagreement)
        rebind_event(tampered_disagreement)
        verification = verify_service_response(tampered_disagreement)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        disagreement_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(
            disagreement_acceptance["claim_warrant_strength_status"],
            "passed",
        )
        self.assertEqual(
            disagreement_acceptance["claim_source_disagreement_status"],
            "failed",
        )
        self.assertLess(
            disagreement_acceptance["claim_source_disagreement_count"],
            disagreement_acceptance["supported_claim_count"],
        )
        self.assertIn(
            (
                "claim_source_disagreement: not every supported claim is free of "
                "visible source disagreement"
            ),
            disagreement_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )
        footer_verification = verify_source_footer(
            tampered_disagreement["source_footer"],
            display_text=tampered_disagreement["display"]["rendered_text"],
        )
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(
            footer_verification["claim_source_disagreement_status"],
            "failed",
        )
        self.assertIn(
            (
                "claim_rows: every supported claim must be free of visible source "
                "disagreement"
            ),
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )

        tampered_answer_claim = json.loads(json.dumps(response))
        event = tampered_answer_claim["event"]
        assert isinstance(event, dict)
        extra_answer = (
            f"{str(event.get('answer_text', event.get('output', ''))).rstrip()} "
            "This response creates a binding guarantee for every downstream payer."
        )
        event["answer_text"] = extra_answer
        event["output"] = extra_answer
        rebind_event(tampered_answer_claim)
        verification = verify_service_response(tampered_answer_claim)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        coverage_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(
            coverage_acceptance["answer_claim_coverage_status"],
            "failed",
        )
        self.assertEqual(len(coverage_acceptance["uncovered_answer_claim_hashes"]), 1)
        self.assertEqual(coverage_acceptance["extra_claim_row_hashes"], [])
        self.assertEqual(
            coverage_acceptance["answer_claim_unit_count"],
            coverage_acceptance["claim_count"] + 1,
        )
        self.assertIn(
            (
                "answer_claim_coverage: answer text claims do not match footer "
                "claim rows"
            ),
            coverage_acceptance["errors"],
        )
        self.assertIn(
            (
                "source_grounding_acceptance: ready response does not meet "
                "grounded source display profile"
            ),
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_model_reliance = json.loads(json.dumps(response))
        event = tampered_model_reliance["event"]
        assert isinstance(event, dict)
        reliance_answer = (
            f"{str(event.get('answer_text', event.get('output', ''))).rstrip()} "
            "I used the provenance ledger in my reasoning."
        )
        event["answer_text"] = reliance_answer
        event["output"] = reliance_answer
        rebind_event(tampered_model_reliance)
        verification = verify_service_response(tampered_model_reliance)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        reliance_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(
            reliance_acceptance["model_reliance_claim_status"],
            "failed",
        )
        self.assertIn("i used", reliance_acceptance["model_reliance_claim_markers"])
        self.assertIn(
            "my reasoning",
            reliance_acceptance["model_reliance_claim_markers"],
        )
        self.assertIn(
            (
                "answer_model_reliance: unverified model-internal reliance claims "
                "i used, my reasoning"
            ),
            reliance_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_temporal = json.loads(json.dumps(response))
        event = tampered_temporal["event"]
        assert isinstance(event, dict)
        temporal_answer = (
            f"{str(event.get('answer_text', event.get('output', ''))).rstrip()} "
            "Currently, this answer relies on current source evidence."
        )
        event["answer_text"] = temporal_answer
        event["output"] = temporal_answer
        rebind_event(tampered_temporal)
        verification = verify_service_response(tampered_temporal)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        temporal_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(temporal_acceptance["temporal_grounding_status"], "failed")
        self.assertEqual(temporal_acceptance["source_temporal_metadata_count"], 0)
        self.assertIn("currently", temporal_acceptance["temporal_claim_markers"])
        self.assertIn("current", temporal_acceptance["temporal_claim_markers"])
        self.assertIn(
            (
                "temporal_grounding: temporal answer claims require source "
                "freshness metadata"
            ),
            temporal_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_answer_link = json.loads(json.dumps(response))
        event = tampered_answer_link["event"]
        assert isinstance(event, dict)
        foreign_uri = "https://example.invalid/unsupported-source"
        linked_answer = (
            f"{str(event.get('answer_text', event.get('output', ''))).rstrip()} "
            f"See [outside source]({foreign_uri})."
        )
        event["answer_text"] = linked_answer
        event["output"] = linked_answer
        rebind_event(tampered_answer_link)
        verification = verify_service_response(tampered_answer_link)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        link_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(link_acceptance["answer_link_status"], "failed")
        self.assertEqual(link_acceptance["answer_link_uris"], [foreign_uri])
        self.assertEqual(link_acceptance["resolved_answer_link_uris"], [])
        self.assertEqual(link_acceptance["unresolved_answer_link_uris"], [foreign_uri])
        self.assertIn(
            f"answer_links: unverified answer source links {foreign_uri}",
            link_acceptance["errors"],
        )
        self.assertIn(
            (
                "source_grounding_acceptance: ready response does not meet "
                "grounded source display profile"
            ),
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_gap = json.loads(json.dumps(response))
        attribution_gap = tampered_gap["event"]["attribution_gap"]
        attribution_gap["verdict"] = "open_gap"
        attribution_gap["summary"]["consumed_without_credit_count"] = 1
        attribution_gap["classifications"]["consumed_without_credit"] = [
            "chunk:uncredited"
        ]
        attribution_gap["issues"] = [
            "accessed source is neither cited, paid, nor escrowed: chunk:uncredited"
        ]
        rebind_event(tampered_gap)
        verification = verify_service_response(tampered_gap)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        gap_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(gap_acceptance["attribution_gap_status"], "failed")
        self.assertEqual(gap_acceptance["attribution_gap_verdict"], "open_gap")
        self.assertEqual(
            gap_acceptance["attribution_gap_consumed_without_credit_count"],
            1,
        )
        self.assertIn(
            (
                "attribution_gap: accessed, visible, and paid source coverage "
                "is not closed"
            ),
            gap_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_locator = json.loads(json.dumps(response))
        source_row = tampered_locator["source_footer"]["source_rows"][0]
        rendered_token = f"uri={source_row['source_uri']}; "
        tampered_locator["source_footer"]["rendered_text"] = tampered_locator[
            "source_footer"
        ]["rendered_text"].replace(rendered_token, "", 1)
        rebind_footer(tampered_locator)
        verification = verify_service_response(tampered_locator)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        locator_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(locator_acceptance["source_locator_status"], "failed")
        self.assertIn(
            (
                "source_locator: not every visible source row exposes uri, "
                "verify, and hash locators"
            ),
            locator_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_usage = json.loads(json.dumps(response))
        source_row = tampered_usage["source_footer"]["source_rows"][0]
        rendered_token = f"weight={source_row['contribution_weight']}; "
        tampered_usage["source_footer"]["rendered_text"] = tampered_usage[
            "source_footer"
        ]["rendered_text"].replace(rendered_token, "")
        rebind_footer(tampered_usage)
        verification = verify_service_response(tampered_usage)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        usage_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(usage_acceptance["source_usage_metric_status"], "failed")
        self.assertIn(
            (
                "source_usage: not every visible source row exposes support, "
                "text_match, weight, and payout"
            ),
            usage_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_claim_source_closure = json.loads(json.dumps(response))
        claim_row = next(
            row
            for row in tampered_claim_source_closure["source_footer"]["claim_rows"]
            if row["supported"]
        )
        claim_row["work_id"] = f"swapped:{claim_row['work_id']}"
        claim_row["chunk_id"] = f"swapped:{claim_row['chunk_id']}"
        rehash_row(claim_row)
        rebind_footer(tampered_claim_source_closure)
        verification = verify_service_response(tampered_claim_source_closure)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        claim_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(claim_acceptance["claim_source_closure_status"], "failed")
        self.assertIn(
            (
                "claim_source_closure: not every supported claim binds to the "
                "visible source row work and chunk"
            ),
            claim_acceptance["errors"],
        )
        self.assertIn(
            (
                "source_footer.claim_rows[0].source_binding: "
                "does not match source row work and chunk"
            ),
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_claim_evidence = json.loads(json.dumps(response))
        claim_row = next(
            row for row in tampered_claim_evidence["source_footer"]["claim_rows"]
            if row["supported"]
        )
        rendered_token = f"span={claim_row['evidence_span_hash_prefix']}; "
        tampered_claim_evidence["source_footer"]["rendered_text"] = (
            tampered_claim_evidence["source_footer"]["rendered_text"].replace(
                rendered_token,
                "",
                1,
            )
        )
        rebind_footer(tampered_claim_evidence)
        verification = verify_service_response(tampered_claim_evidence)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        claim_acceptance = verification["source_grounding_acceptance"]
        self.assertEqual(claim_acceptance["claim_evidence_status"], "failed")
        self.assertIn(
            (
                "claim_evidence: not every supported claim exposes a visible "
                "evidence span"
            ),
            claim_acceptance["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_evidence = json.loads(json.dumps(response))
        claim_row = next(
            row for row in tampered_evidence["source_footer"]["claim_rows"]
            if row["supported"]
        )
        claim_row["evidence_preview"] = "Fabricated evidence preview."
        claim_row["row_hash"] = canonical_hash(claim_row)
        rebind_footer(tampered_evidence)
        verification = verify_service_response(tampered_evidence)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        self.assertIn(
            (
                "source_footer.claim_rows[0].evidence_span_hash: "
                "does not match evidence preview"
            ),
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_handle = json.loads(json.dumps(response))
        source_row = tampered_handle["source_footer"]["source_rows"][0]
        old_handle = source_row["verification_handle"]
        source_row["verification_handle"] = (
            "rdllm://verify/source-footer/evt_forged/S1/deadbeefdead"
        )
        source_row["row_hash"] = canonical_hash(source_row)
        tampered_handle["source_footer"]["rendered_text"] = tampered_handle[
            "source_footer"
        ]["rendered_text"].replace(old_handle, source_row["verification_handle"])
        rebind_footer(tampered_handle)
        verification = verify_service_response(tampered_handle)
        self.assertEqual(verification["status"], "failed")
        self.assertFalse(verification["production_display_ready"])
        self.assertIn(
            "source_footer.source_rows[0].verification_handle: mismatch",
            verification["errors"],
        )
        footer_verification = verify_source_footer(
            tampered_handle["source_footer"],
            display_text=tampered_handle["display"]["rendered_text"],
        )
        footer_verification_schema = load_source_footer_verification_schema()
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(footer_verification["handle_status"], "failed")
        self.assertFalse(footer_verification["public_footer_ready"])
        self.assertIn(
            "source_rows[0].verification_handle: mismatch",
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered_event_id = json.loads(json.dumps(response))
        footer = tampered_event_id["source_footer"]
        forged_event_id = "evt_deadbeefdeadbeef"
        if footer["event_id"] == forged_event_id:
            forged_event_id = "evt_feedfacefeedface"
        footer["event_id"] = forged_event_id
        for source_row in footer["source_rows"]:
            old_handle = source_row["verification_handle"]
            source_row["verification_handle"] = (
                "rdllm://verify/source-footer/"
                f"{forged_event_id}/{source_row['label']}/"
                f"{source_row['content_hash'][:12]}"
            )
            rehash_row(source_row)
            footer["rendered_text"] = footer["rendered_text"].replace(
                old_handle,
                source_row["verification_handle"],
            )
        rebind_footer(tampered_event_id)
        footer_verification = verify_source_footer(
            tampered_event_id["source_footer"],
            display_text=tampered_event_id["display"]["rendered_text"],
        )
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(footer_verification["row_hash_status"], "passed")
        self.assertEqual(footer_verification["handle_status"], "passed")
        self.assertFalse(footer_verification["public_footer_ready"])
        self.assertIn(
            "event_id: does not match event hash",
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )

        tampered_public_verifier = json.loads(json.dumps(response))
        tampered_public_verifier["source_footer"]["public_verifier"][
            "grounding_verdict"
        ] = "failed"
        rebind_footer(tampered_public_verifier)
        footer_verification = verify_source_footer(
            tampered_public_verifier["source_footer"],
            display_text=tampered_public_verifier["display"]["rendered_text"],
        )
        self.assertEqual(footer_verification["status"], "failed")
        self.assertEqual(footer_verification["public_verifier_status"], "failed")
        self.assertEqual(footer_verification["row_hash_status"], "passed")
        self.assertEqual(footer_verification["handle_status"], "passed")
        self.assertFalse(footer_verification["public_footer_ready"])
        self.assertIn(
            "public_verifier.grounding_verdict: does not match footer status",
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )

    def test_attribute_response_blocks_non_display_safe_grounding(self) -> None:
        state = ServiceState.from_config(ServiceConfig(raw=load_json(CONFIG_PATH)))
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": (
                    "The moon is made of green cheese and every library must pay "
                    "royalties to unrelated fictional parties."
                ),
                "gross_revenue": "1.00",
            },
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["summary"]["grounding_verdict"], "failed")
        self.assertIn(
            "grounding_quality: verdict failed is not safe for production display",
            response["audit_errors"],
        )
        footer = response["source_footer"]
        display = response["display"]
        self.assertIn("Unsupported Claims", footer["rendered_text"])
        self.assertIn("Unsupported Claims", display["rendered_text"])
        footer_verification = verify_source_footer(
            footer,
            display_text=display["rendered_text"],
        )
        footer_verification_schema = load_source_footer_verification_schema()
        self.assertEqual(footer_verification["status"], "failed")
        self.assertFalse(footer_verification["public_footer_ready"])
        self.assertIn(
            "footer_status: expected verified",
            footer_verification["errors"],
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(footer_verification_schema).iter_errors(
                    footer_verification
                )
            ),
        )
        verification = verify_service_response(response)
        verification_schema = load_response_verification_schema()
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(verification["response_status"], "blocked")
        self.assertFalse(verification["production_display_ready"])
        self.assertEqual(
            verification["source_grounding_acceptance"]["status"],
            "failed",
        )
        self.assertIn(
            "fact_support: unsupported claim rows are present",
            verification["source_grounding_acceptance"]["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )

        tampered = json.loads(json.dumps(response))
        tampered["status"] = "ready"
        tampered["display"]["status"] = "ready"
        tampered["audit_errors"] = []
        verification = verify_service_response(tampered)
        self.assertEqual(verification["status"], "failed")
        self.assertIn(
            "status: ready response has non-display-safe grounding verdict",
            verification["errors"],
        )
        self.assertIn(
            "audit_errors: missing grounding display gate error",
            verification["errors"],
        )
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(verification)),
        )


if __name__ == "__main__":
    unittest.main()
