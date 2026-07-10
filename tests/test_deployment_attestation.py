from __future__ import annotations

import copy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest

from rdllm.deployment_attestation import (
    PAYMENT_PROCESSOR_ATTESTATION,
    REQUIRED_PRODUCTION_ATTESTATIONS,
    TRUST_STORE_SCHEMA,
    main as attestation_main,
    make_deployment_attestation,
)
from rdllm.production_readiness import evaluate_production_profile
from rdllm.signing import generate_ed25519_keypair


class DeploymentAttestationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads(
            Path("examples/production_readiness_profile.json").read_text(
                encoding="utf-8"
            )
        )

    def test_profile_cannot_self_declare_external_readiness(self) -> None:
        report = evaluate_production_profile(copy.deepcopy(self.profile))
        self.assertTrue(report["summary"]["configuration_ready"])
        self.assertEqual(report["summary"]["external_evidence_status"], "unverified")
        self.assertFalse(report["summary"]["production_grade_claim_allowed"])
        self.assertFalse(report["summary"]["direct_creator_settlement_allowed"])
        self.assertFalse(report["summary"]["payment_processor_attested"])

    def test_cli_create_attach_and_verify(self) -> None:
        private_key, public_key = generate_ed25519_keypair()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = copy.deepcopy(self.profile)
            profile_path = root / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            private_path = root / "private.pem"
            private_path.write_text(private_key, encoding="ascii")
            evidence_path = root / "evidence.txt"
            evidence_path.write_text("independent evidence", encoding="utf-8")
            attestation_path = root / "attestation.json"
            attested_profile_path = root / "profile-attested.json"
            key_id = "https://auditor.example/keys/one"
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    attestation_main(
                        [
                            "create",
                            "--profile",
                            str(profile_path),
                            "--attestation-type",
                            "security_assessment",
                            "--issuer",
                            "Independent Auditor",
                            "--key-id",
                            key_id,
                            "--private-key",
                            str(private_path),
                            "--evidence",
                            str(evidence_path),
                            "--evidence-uri",
                            "https://auditor.example/reports/one",
                            "--expires-at",
                            expires_at,
                            "--output",
                            str(attestation_path),
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    attestation_main(
                        [
                            "attach",
                            "--profile",
                            str(profile_path),
                            "--attestation",
                            str(attestation_path),
                            "--output",
                            str(attested_profile_path),
                        ]
                    ),
                    0,
                )
            attached = json.loads(attested_profile_path.read_text(encoding="utf-8"))
            self.assertEqual(len(attached["external_attestations"]), 1)
            trust_store = {
                "schema": TRUST_STORE_SCHEMA,
                "keys": [
                    {
                        "key_id": key_id,
                        "issuer": "Independent Auditor",
                        "public_key_pem": public_key,
                        "allowed_attestation_types": ["security_assessment"],
                    }
                ],
            }
            trust_path = root / "trust.json"
            trust_path.write_text(json.dumps(trust_store), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    attestation_main(
                        [
                            "verify",
                            "--profile",
                            str(attested_profile_path),
                            "--trust-store",
                            str(trust_path),
                        ]
                    ),
                    1,
                )

    def test_trusted_signed_attestations_enable_production_claim(self) -> None:
        private_key, public_key = generate_ed25519_keypair()
        key_id = "https://audit.example/keys/2026-1"
        issuer = "Independent Audit Lab"
        attestation_types = sorted(
            REQUIRED_PRODUCTION_ATTESTATIONS | {PAYMENT_PROCESSOR_ATTESTATION}
        )
        profile = copy.deepcopy(self.profile)
        profile["external_attestations"] = [
            make_deployment_attestation(
                attestation_type=attestation_type,
                issuer=issuer,
                subject=profile["deployment"]["operator_name"],
                deployment_id=profile["deployment"]["deployment_id"],
                evidence_uri=f"https://audit.example/evidence/{attestation_type}.json",
                evidence_sha256="a" * 64,
                issued_at="2026-01-01T00:00:00Z",
                expires_at="2030-01-01T00:00:00Z",
                private_key_pem=private_key,
                key_id=key_id,
            )
            for attestation_type in attestation_types
        ]
        trust_store = {
            "schema": TRUST_STORE_SCHEMA,
            "keys": [
                {
                    "key_id": key_id,
                    "issuer": issuer,
                    "public_key_pem": public_key,
                    "allowed_attestation_types": attestation_types,
                }
            ],
        }
        report = evaluate_production_profile(profile, trust_store=trust_store)
        self.assertEqual(report["summary"]["external_evidence_status"], "verified")
        self.assertTrue(report["summary"]["production_grade_claim_allowed"])
        self.assertTrue(report["summary"]["direct_creator_settlement_allowed"])
        self.assertTrue(report["summary"]["payment_processor_attested"])
        self.assertEqual(report["summary"]["missing_external_attestation_types"], [])


if __name__ == "__main__":
    unittest.main()
