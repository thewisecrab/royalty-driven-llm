from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from rdllm.operator_profile import (
    load_profile_schema,
    load_profile_verification_schema,
    load_template,
    profile_schema_errors,
)
from rdllm.production_readiness import (
    evaluate_production_profile,
    load_repository_report_schema,
    load_json,
    verify_repository_readiness_report,
    verify_production_readiness_report,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "examples" / "production_readiness_profile.json"
PROFILE_DIR = ROOT / "examples" / "production_profiles"
PACKAGED_TEMPLATE_EXAMPLES = {
    "individual": PROFILE_DIR / "individual_escrow_only.json",
    "company": PROFILE_DIR / "company_instruction_only.json",
    "institution": PROFILE_DIR / "institution_instruction_only.json",
    "government": PROFILE_DIR / "government_escrow_only.json",
    "public_sector": PROFILE_DIR / "public_sector_processor_attested.json",
}


class ProductionReadinessTests(unittest.TestCase):
    def test_example_profile_is_ready(self) -> None:
        profile = load_json(PROFILE_PATH)
        report = evaluate_production_profile(profile)
        self.assertEqual(report["summary"]["status"], "ready")
        self.assertEqual(report["summary"]["blocked_control_count"], 0)
        self.assertTrue(report["summary"]["production_grade_claim_allowed"])
        self.assertTrue(report["summary"]["direct_creator_settlement_allowed"])
        self.assertTrue(report["summary"]["public_sector_use_supported"])
        self.assertEqual(report["summary"]["settlement_mode"], "processor_attested")

    def test_missing_auth_blocks_production_claims(self) -> None:
        profile = load_json(PROFILE_PATH)
        profile["runtime_controls"]["auth_required"] = False
        report = evaluate_production_profile(profile)
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertFalse(report["summary"]["production_grade_claim_allowed"])
        blocked_ids = {row["control_id"] for row in report["blocked_controls"]}
        self.assertIn("runtime_controls.auth_required", blocked_ids)

    def test_report_verification_detects_tampering(self) -> None:
        profile = load_json(PROFILE_PATH)
        report = evaluate_production_profile(profile)
        tampered = copy.deepcopy(report)
        tampered["summary"]["ready_control_count"] += 1
        verification = verify_production_readiness_report(profile, tampered)
        self.assertEqual(verification["status"], "failed")
        self.assertIn("summary.ready_control_count mismatch", verification["errors"])

    def test_report_schema_accepts_example_report(self) -> None:
        from jsonschema import Draft202012Validator

        profile = load_json(PROFILE_PATH)
        report = evaluate_production_profile(profile)
        schema = json.loads(
            (ROOT / "docs" / "schemas" / "production_readiness_report.schema.json")
            .read_text(encoding="utf-8")
        )
        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

    def test_profile_schema_accepts_all_operator_examples(self) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads(
            (ROOT / "docs" / "schemas" / "production_readiness_profile.schema.json")
            .read_text(encoding="utf-8")
        )
        for path in [PROFILE_PATH, *sorted(PROFILE_DIR.glob("*.json"))]:
            with self.subTest(path=path.name):
                profile = load_json(path)
                errors = list(Draft202012Validator(schema).iter_errors(profile))
                self.assertEqual(errors, [])

    def test_packaged_operator_templates_match_repository_examples(self) -> None:
        for template, path in PACKAGED_TEMPLATE_EXAMPLES.items():
            with self.subTest(template=template):
                self.assertEqual(load_template(template), load_json(path))
        self.assertEqual(
            load_profile_schema(),
            load_json(ROOT / "docs" / "schemas" / "production_readiness_profile.schema.json"),
        )
        self.assertEqual(
            load_profile_verification_schema(),
            load_json(
                ROOT / "docs" / "schemas" / "operator_profile_verification.schema.json"
            ),
        )

    def test_packaged_profile_schema_rejects_unknown_fields(self) -> None:
        profile = load_template("company")
        profile["deployment"]["unexpected_field"] = "unexpected"
        errors = profile_schema_errors(profile)
        self.assertIn("deployment.unexpected_field: unknown field", errors)

    def test_no_payment_profiles_are_ready_without_direct_settlement(self) -> None:
        no_payment_profiles = [
            PROFILE_DIR / "individual_escrow_only.json",
            PROFILE_DIR / "company_instruction_only.json",
            PROFILE_DIR / "institution_instruction_only.json",
            PROFILE_DIR / "government_escrow_only.json",
        ]
        for path in no_payment_profiles:
            with self.subTest(path=path.name):
                profile = load_json(path)
                report = evaluate_production_profile(profile)
                self.assertEqual(report["summary"]["status"], "ready")
                self.assertTrue(report["summary"]["production_grade_claim_allowed"])
                self.assertFalse(report["summary"]["direct_creator_settlement_allowed"])
                self.assertFalse(report["summary"]["direct_payout_enabled"])

    def test_public_sector_readiness_is_operator_specific(self) -> None:
        individual = evaluate_production_profile(
            load_json(PROFILE_DIR / "individual_escrow_only.json")
        )
        government = evaluate_production_profile(
            load_json(PROFILE_DIR / "government_escrow_only.json")
        )
        self.assertFalse(individual["summary"]["public_sector_use_supported"])
        self.assertTrue(government["summary"]["public_sector_use_supported"])

    def test_legacy_default_profile_matches_public_sector_example(self) -> None:
        self.assertEqual(
            load_json(PROFILE_PATH),
            load_json(PROFILE_DIR / "public_sector_processor_attested.json"),
        )

    def test_profile_only_cli_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/production_readiness.py",
                "--profile-only",
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

    def test_repository_gate_reports_profile_settlement_semantics(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/production_readiness.py",
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
        report = json.loads(result.stdout)
        repository_schema = load_json(
            ROOT
            / "docs"
            / "schemas"
            / "production_readiness_repository_report.schema.json"
        )
        self.assertEqual(load_repository_report_schema(), repository_schema)
        validation_errors = list(
            Draft202012Validator(repository_schema).iter_errors(report)
        )
        self.assertEqual([], validation_errors)
        verification = verify_repository_readiness_report(report)
        self.assertEqual(verification["status"], "passed")
        summary = report["summary"]
        self.assertEqual(summary["settlement_mode"], "processor_attested")
        self.assertEqual(summary["acceptance_matrix_status"], "passed")
        self.assertEqual(summary["acceptance_matrix_operator_template_count"], 5)
        self.assertEqual(summary["acceptance_matrix_passed_count"], 5)
        self.assertEqual(
            summary["acceptance_matrix_production_acceptance_allowed_count"],
            5,
        )
        self.assertTrue(summary["direct_payout_enabled"])
        self.assertTrue(summary["payment_processor_attested"])
        self.assertTrue(summary["direct_creator_settlement_allowed"])
        self.assertTrue(summary["public_sector_use_supported"])
        acceptance_rows = {
            row["operator_template"]: row for row in report["acceptance_matrix"]["rows"]
        }
        self.assertEqual(
            set(acceptance_rows),
            {"individual", "company", "institution", "government", "public_sector"},
        )
        for row in acceptance_rows.values():
            with self.subTest(operator_template=row["operator_template"]):
                self.assertEqual(row["status"], "passed")
                self.assertEqual(row["acceptance_status"], "ready")
                self.assertEqual(row["acceptance_verification_status"], "passed")
                self.assertEqual(row["production_acceptance_decision"], "allow")
                self.assertEqual(row["source_grounding_acceptance_status"], "passed")
                self.assertEqual(row["audit_response_binding_status"], "passed")
                self.assertEqual(row["recovery_verification_status"], "passed")

    def test_repository_readiness_verify_cli_passes_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="rdllm-repository-readiness-"
        ) as temp_name:
            temp_dir = Path(temp_name)
            report_path = temp_dir / "repository_readiness.json"
            verification_path = temp_dir / "repository_verification.json"
            create_result = subprocess.run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--write-report",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                create_result.returncode,
                0,
                msg=f"stdout:\n{create_result.stdout}\nstderr:\n{create_result.stderr}",
            )
            verify_result = subprocess.run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--verify-report",
                    str(report_path),
                    "--write-report",
                    str(verification_path),
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
            verification = load_json(verification_path)
            self.assertEqual(verification["status"], "passed")
            module_verification_path = temp_dir / "module_repository_verification.json"
            module_verify_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rdllm.production_readiness",
                    "--report",
                    str(report_path),
                    "--write-report",
                    str(module_verification_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                module_verify_result.returncode,
                0,
                msg=(
                    f"stdout:\n{module_verify_result.stdout}\n"
                    f"stderr:\n{module_verify_result.stderr}"
                ),
            )
            self.assertIn(
                "production_readiness_repository_verification status: passed",
                module_verify_result.stdout,
            )
            module_verification = load_json(module_verification_path)
            self.assertEqual(module_verification["status"], "passed")
            tampered_path = temp_dir / "tampered_repository_readiness.json"
            tampered = load_json(report_path)
            tampered["summary"]["acceptance_matrix_passed_count"] = 4
            tampered_path.write_text(
                json.dumps(tampered, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tampered_result = subprocess.run(
                [
                    sys.executable,
                    "tools/production_readiness.py",
                    "--verify-report",
                    str(tampered_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(tampered_result.returncode, 0)
            tampered_verification = json.loads(tampered_result.stdout)
            self.assertEqual(tampered_verification["status"], "failed")
            self.assertIn(
                "repository_report_hash mismatch",
                tampered_verification["errors"],
            )

    def test_production_profile_matrix_cli_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/production_profile_matrix.py",
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
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["profile_count"], 5)
        self.assertEqual(
            set(report["summary"]["operator_types"]),
            {"individual", "company", "institution", "government", "public_sector"},
        )
        paths = {row["path"] for row in report["profiles"]}
        self.assertIn(
            "examples/production_profiles/public_sector_processor_attested.json",
            paths,
        )
        self.assertNotIn("examples/production_readiness_profile.json", paths)

    def test_operator_profile_create_writes_ready_company_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rdllm-operator-profile-") as temp_name:
            temp_dir = Path(temp_name)
            profile_path = temp_dir / "company_profile.json"
            report_path = temp_dir / "company_report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/operator_profile.py",
                    "create",
                    "--template",
                    "company",
                    "--operator-name",
                    "Acme RDLLM",
                    "--security-contact",
                    "security@example.com",
                    "--output",
                    str(profile_path),
                    "--write-report",
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
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            payload = json.loads(result.stdout)
            profile = load_json(profile_path)
            report = load_json(report_path)
            verification_schema = load_json(
                ROOT / "docs" / "schemas" / "operator_profile_verification.schema.json"
            )
            self.assertEqual(
                load_profile_verification_schema(),
                verification_schema,
            )
            self.assertEqual(
                payload["schema"],
                "rdllm-operator-profile-verification/v1",
            )
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(
                [],
                list(Draft202012Validator(verification_schema).iter_errors(payload)),
            )
            self.assertEqual(profile["deployment"]["operator_name"], "Acme RDLLM")
            self.assertEqual(
                profile["public_surfaces"]["security_contact"],
                "security@example.com",
            )
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertTrue(report["summary"]["production_grade_claim_allowed"])
            self.assertFalse(report["summary"]["direct_creator_settlement_allowed"])

    def test_operator_profile_validate_reports_public_sector_support(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/operator_profile.py",
                "validate",
                "--profile",
                "examples/production_profiles/government_escrow_only.json",
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
        verification_schema = load_profile_verification_schema()
        self.assertEqual(
            payload["schema"],
            "rdllm-operator-profile-verification/v1",
        )
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(
            [],
            list(Draft202012Validator(verification_schema).iter_errors(payload)),
        )
        summary = payload["readiness_report"]["summary"]
        self.assertTrue(summary["production_grade_claim_allowed"])
        self.assertTrue(summary["public_sector_use_supported"])
        self.assertFalse(summary["direct_creator_settlement_allowed"])


if __name__ == "__main__":
    unittest.main()
