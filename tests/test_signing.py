from __future__ import annotations

from decimal import Decimal
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rdllm.engine import RoyaltyDrivenLLM
from rdllm.receipts import make_attribution_receipt, verify_receipt
from rdllm.signing import generate_ed25519_keypair, main as signing_main


class PublicSigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = RoyaltyDrivenLLM.from_corpus_file(
            "src/rdllm/data/sample_corpus.json"
        )

    def test_ed25519_receipt_is_publicly_verifiable(self) -> None:
        private_key, public_key = generate_ed25519_keypair()
        event = self.engine.generate("How should AI prove attribution?", Decimal("1"))
        receipt = make_attribution_receipt(
            event,
            signing_private_key=private_key,
            signing_key_id="https://example.test/keys/receipt-1",
        )
        self.assertEqual(receipt["signature"]["algorithm"], "Ed25519")
        self.assertEqual(receipt["signature"]["security_level"], "publicly_verifiable")
        self.assertEqual(
            verify_receipt(
                receipt,
                verification_public_key=public_key,
                expected_key_id="https://example.test/keys/receipt-1",
                require_public_signature=True,
            ),
            [],
        )

    def test_tampered_ed25519_receipt_fails(self) -> None:
        private_key, public_key = generate_ed25519_keypair()
        event = self.engine.generate("How should AI prove attribution?", Decimal("1"))
        receipt = make_attribution_receipt(
            event,
            signing_private_key=private_key,
            signing_key_id="key:one",
        )
        receipt["payload"]["model"]["id"] = "tampered"
        errors = verify_receipt(
            receipt,
            verification_public_key=public_key,
            require_public_signature=True,
        )
        self.assertIn("receipt hash is not reproducible", errors)
        self.assertIn("signature is invalid", errors)

    def test_hmac_receipt_is_rejected_for_public_verification(self) -> None:
        event = self.engine.generate("How should AI prove attribution?", Decimal("1"))
        receipt = make_attribution_receipt(event, signing_secret="demo")
        self.assertEqual(receipt["signature"]["security_level"], "demo_shared_secret")
        self.assertIn(
            "receipt requires a publicly verifiable Ed25519 signature",
            verify_receipt(receipt, require_public_signature=True),
        )

    def test_keygen_writes_private_key_with_restricted_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_path = Path(directory) / "private.pem"
            public_path = Path(directory) / "public.pem"
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                result = signing_main(
                    [
                        "--private-key",
                        str(private_path),
                        "--public-key",
                        str(public_path),
                    ]
                )
            self.assertEqual(result, 0)
            self.assertEqual(os.stat(private_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(public_path).st_mode & 0o777, 0o644)
            self.assertNotIn(private_path.read_text(encoding="ascii"), stdout.getvalue())
            self.assertEqual(
                signing_main(
                    [
                        "--private-key",
                        str(private_path),
                        "--public-key",
                        str(public_path),
                    ]
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
