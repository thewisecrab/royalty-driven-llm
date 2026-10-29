"""Tests for optional entailment scoring, cooperative payouts, and license parsing."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from rdllm.cooperative_allocation import (
    allocate_creator_pool,
    banzhaf_values,
    monte_carlo_shapley_values,
    output_token_coverage_value,
    shapley_values,
)
from rdllm.content_protocol_ingestion import make_content_protocol_ingestion_report
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.entailment_support import score_entailment, text_overlap_score
from rdllm.licensing_signals import parse_licensing_signal
from rdllm.models import Creator, Work
from rdllm.source_usage_metrics import (
    NLI_SUPPORT_METRIC_ID,
    SOURCE_USAGE_METRIC_METHODS,
    TEXT_OVERLAP_METRIC_ID,
)
from rdllm.support_eval import load_examples, score_examples, write_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _unanimity(required: set[str]):
    def value(coalition: frozenset[str]) -> float:
        return 1.0 if required <= set(coalition) else 0.0

    return value


class EntailmentSupportTests(unittest.TestCase):
    def test_overlap_stays_high_when_negation_blocks_entailment(self) -> None:
        claim = "The bridge is not open to freight trains."
        evidence = "The bridge is open to freight trains."
        overlap = text_overlap_score(claim, evidence)
        result = score_entailment(claim, evidence)
        self.assertGreater(overlap, 0.5)
        self.assertLess(result["score"], 0.75)
        self.assertEqual(result["label"], "not_entailed")
        self.assertEqual(result["metric_id"], NLI_SUPPORT_METRIC_ID)
        self.assertEqual(result["backend"], "deterministic_stub")
        self.assertEqual(result["model_name"], "rdllm-deterministic-entailment-stub")
        self.assertEqual(result["model_version"], "1")
        self.assertEqual(SOURCE_USAGE_METRIC_METHODS["support"], TEXT_OVERLAP_METRIC_ID)
        self.assertEqual(SOURCE_USAGE_METRIC_METHODS["entailment"], NLI_SUPPORT_METRIC_ID)
        self.assertNotEqual(
            SOURCE_USAGE_METRIC_METHODS["support"],
            SOURCE_USAGE_METRIC_METHODS["entailment"],
        )

    def test_verbatim_evidence_is_entailed_by_the_stub(self) -> None:
        sentence = "The ledger records the creator pool before settlement."
        result = score_entailment(sentence, sentence)
        self.assertEqual(result["label"], "entailed")
        self.assertGreaterEqual(result["score"], result["threshold"])

    def test_auto_backend_does_not_import_optional_models(self) -> None:
        def fail_import(name: str):
            raise AssertionError(f"auto backend imported {name}")

        import rdllm.entailment_support as module

        original = module._load_backend
        module._load_backend = fail_import
        try:
            result = score_entailment("Copper conducts electricity.", "Copper conducts electricity.")
        finally:
            module._load_backend = original
        self.assertEqual(result["backend"], "deterministic_stub")
        self.assertEqual(result["fallback_reason"], "")

    def test_named_backend_falls_back_when_the_package_is_missing(self) -> None:
        import rdllm.entailment_support as module

        def missing(name: str):
            raise ImportError(name)

        original = module._load_backend
        module._load_backend = missing
        try:
            result = score_entailment("A claim.", "A claim.", backend="minicheck")
        finally:
            module._load_backend = original
        self.assertEqual(result["backend"], "deterministic_stub")
        self.assertEqual(result["requested_backend"], "minicheck")
        self.assertIn("not installed", result["fallback_reason"])

    def test_imported_backend_without_a_scorer_still_uses_the_stub(self) -> None:
        import rdllm.entailment_support as module

        original = module._load_backend
        module._load_backend = lambda name: type("Backend", (), {"__name__": name})()
        try:
            result = score_entailment("A claim.", "A claim.", backend="alignscore")
        finally:
            module._load_backend = original
        self.assertEqual(result["backend"], "deterministic_stub")
        self.assertIn("no local scorer", result["fallback_reason"])

    def test_injected_scorer_is_used_when_present(self) -> None:
        def scorer(claim: str, evidence: str) -> float:
            return 0.91

        scorer.model_name = "test-nli"
        scorer.model_version = "9"
        result = score_entailment("A claim.", "Unrelated evidence.", backend="minicheck", scorer=scorer)
        self.assertEqual(result["score"], 0.91)
        self.assertEqual(result["label"], "entailed")
        self.assertEqual(result["model_name"], "test-nli")
        self.assertEqual(result["backend"], "minicheck")


class SupportEvalTests(unittest.TestCase):
    def test_synthetic_fixture_is_scored_and_not_called_a_benchmark(self) -> None:
        path = FIXTURES / "support_eval" / "synthetic_factcheck.jsonl"
        readme = (FIXTURES / "support_eval" / "README.md").read_text(encoding="utf-8")
        self.assertIn("not a", readme.lower())
        examples = load_examples(path)
        self.assertGreaterEqual(len(examples), 4)
        self.assertTrue(all(example["fixture_kind"].startswith("synthetic") for example in examples))
        report = score_examples(examples, dataset_label="rdllm-synthetic")
        self.assertTrue(report["measured"])
        self.assertFalse(report["benchmark_result"])
        self.assertEqual(report["metrics"]["text_overlap"]["metric_id"], TEXT_OVERLAP_METRIC_ID)
        self.assertEqual(report["metrics"]["entailment"]["metric_id"], NLI_SUPPORT_METRIC_ID)
        self.assertEqual(report["metrics"]["entailment"]["model_name"], "rdllm-deterministic-entailment-stub")
        negation = next(row for row in report["rows"] if row["example_id"] == "syn-negation")
        self.assertFalse(negation["gold_attributable"])
        self.assertEqual(negation["entailment_label"], "not_entailed")
        before = path.read_text(encoding="utf-8")
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_measurement_writer_refuses_the_fixture_tree(self) -> None:
        report = score_examples(load_examples(FIXTURES / "support_eval" / "synthetic_factcheck.jsonl"))
        with self.assertRaises(ValueError):
            write_report(report, FIXTURES / "support_eval" / "results.json")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "results.json"
            write_report(report, destination)
            self.assertTrue(destination.is_file())
            self.assertFalse((FIXTURES / "support_eval" / "results.json").exists())


class CooperativeAllocationTests(unittest.TestCase):
    def test_shapley_efficiency_symmetry_and_null_player(self) -> None:
        value = _unanimity({"a", "b"})
        values = shapley_values(["a", "b", "c"], value)
        self.assertAlmostEqual(sum(values.values()), 1.0)
        self.assertAlmostEqual(values["a"], values["b"])
        self.assertAlmostEqual(values["c"], 0.0)
        self.assertAlmostEqual(values["a"], 0.5)

    def test_normalized_banzhaf_efficiency_symmetry_and_null_player(self) -> None:
        value = _unanimity({"a", "b", "c"})
        raw = banzhaf_values(["a", "b", "c"], value, normalized=False)
        normalized = banzhaf_values(["a", "b", "c"], value, normalized=True)
        self.assertAlmostEqual(raw["a"], raw["b"])
        self.assertAlmostEqual(raw["a"], raw["c"])
        self.assertNotAlmostEqual(sum(raw.values()), 1.0)
        self.assertAlmostEqual(sum(normalized.values()), 1.0)
        self.assertAlmostEqual(normalized["a"], normalized["b"])
        null_game = _unanimity({"a"})
        null_values = banzhaf_values(["a", "b"], null_game, normalized=True)
        self.assertAlmostEqual(null_values["b"], 0.0)
        self.assertAlmostEqual(sum(null_values.values()), 1.0)

    def test_coverage_value_null_player_and_pool_conservation(self) -> None:
        token_sets = {
            "left": {"alpha", "beta"},
            "right": {"alpha", "beta"},
            "null": {"unrelated"},
        }
        output = {"alpha", "beta"}

        def value(coalition: frozenset[str]) -> float:
            return output_token_coverage_value(coalition, token_sets, output)

        values = shapley_values(["left", "right", "null"], value)
        self.assertAlmostEqual(values["null"], 0.0)
        self.assertAlmostEqual(values["left"], values["right"])
        self.assertAlmostEqual(sum(values.values()), 1.0)
        payouts = allocate_creator_pool(values, Decimal("1.000000"))
        self.assertNotIn("null", payouts)
        self.assertEqual(sum(payouts.values(), Decimal("0")), Decimal("1.000000"))

    def test_monte_carlo_shapley_is_seeded_and_efficient_after_normalization(self) -> None:
        value = _unanimity({"a", "b"})
        first = monte_carlo_shapley_values(["a", "b", "c"], value, samples=32, seed=7)
        second = monte_carlo_shapley_values(["a", "b", "c"], value, samples=32, seed=7)
        self.assertEqual(first, second)
        self.assertAlmostEqual(sum(first.values()), 1.0)
        self.assertAlmostEqual(first["c"], 0.0)

    def test_engine_shapley_option_conserves_the_creator_pool(self) -> None:
        creators = [
            Creator("creator-a", "Ada", "acct-a"),
            Creator("creator-b", "Bea", "acct-b"),
        ]
        sentence = "Provenance ledgers bind an answer to the source that supplied it."
        works = [
            Work("work-a", "creator-a", "Ledger A", sentence, source_uri="https://example.test/a"),
            Work("work-b", "creator-b", "Ledger B", sentence, source_uri="https://example.test/b"),
        ]
        engine = RoyaltyDrivenLLM(creators, works, allocation_method="shapley")
        event = engine.generate("How do provenance ledgers bind an answer?", Decimal("2.00"))
        self.assertEqual(
            sum((share.payout for share in event.royalty_shares), Decimal("0")),
            event.creator_pool,
        )
        self.assertEqual(engine.allocation_method, "shapley")
        with self.assertRaises(ValueError):
            RoyaltyDrivenLLM(creators, works, allocation_method="unknown")


class LicensingSignalTests(unittest.TestCase):
    def test_rsl_permits_prohibits_and_payment(self) -> None:
        text = (FIXTURES / "licensing" / "rsl_attribution.xml").read_text(encoding="utf-8")
        parsed = parse_licensing_signal(text)
        self.assertTrue(parsed["recognized"])
        self.assertEqual(parsed["protocol"], "rsl")
        self.assertEqual(parsed["allowed_uses"], ["retrieval_inference", "retrieval"])
        self.assertEqual(parsed["prohibited_uses"], ["training"])
        self.assertEqual(parsed["payment_type"], "attribution")
        self.assertFalse(parsed["royalty_required"])

    def test_rsl_prohibits_override_permits(self) -> None:
        text = (FIXTURES / "licensing" / "rsl_conflict.xml").read_text(encoding="utf-8")
        parsed = parse_licensing_signal(text)
        self.assertEqual(parsed["allowed_uses"], [])
        self.assertEqual(parsed["prohibited_uses"], ["training"])

    def test_aipref_dictionary_is_case_sensitive_and_last_key_wins(self) -> None:
        text = (FIXTURES / "licensing" / "aipref_header.txt").read_text(encoding="utf-8")
        parsed = parse_licensing_signal(text)
        self.assertEqual(parsed["protocol"], "aipref")
        self.assertEqual(parsed["vocabulary"], "draft-ietf-aipref-vocab-08")
        self.assertEqual(parsed["preferences"]["train-ai"], "y")
        self.assertEqual(parsed["preferences"]["search"], "n")
        self.assertEqual(parsed["preferences"]["ai-use"], "unknown")
        self.assertIn("training", parsed["allowed_uses"])
        self.assertIn("retrieval", parsed["prohibited_uses"])
        duplicate = parse_licensing_signal("train-ai=n, train-ai=y")
        self.assertEqual(duplicate["preferences"]["train-ai"], "y")
        uppercase = parse_licensing_signal("train-ai=Y")
        self.assertEqual(uppercase["preferences"]["train-ai"], "unknown")
        self.assertFalse(uppercase["recognized"])

    def test_robots_tdm_and_content_usage_opt_out(self) -> None:
        text = (FIXTURES / "licensing" / "robots_tdm.txt").read_text(encoding="utf-8")
        parsed = parse_licensing_signal(text)
        self.assertEqual(parsed["protocol"], "robots_txt")
        self.assertEqual(parsed["tdm_reservation"], "1")
        self.assertIn("gptbot", parsed["opt_out_agents"])
        self.assertIn("training", parsed["prohibited_uses"])
        self.assertIn("retrieval", parsed["prohibited_uses"])
        self.assertIn("retrieval_inference", parsed["allowed_uses"])
        self.assertNotIn("training", parsed["allowed_uses"])

    def test_prose_labels_are_not_treated_as_a_parsed_license(self) -> None:
        parsed = parse_licensing_signal("RSL grants retrieval inference with attribution and royalty.")
        self.assertFalse(parsed["recognized"])

    def test_ingestion_uses_parsed_rsl_when_asked(self) -> None:
        notice = (FIXTURES / "licensing" / "rsl_attribution.xml").read_text(encoding="utf-8")
        report = make_content_protocol_ingestion_report(
            {
                "case_id": "case:parsed-rsl",
                "protocol_records": [
                    {
                        "protocol_record_id": "protocol:rsl:parsed",
                        "protocol": "custom",
                        "source_uri": "https://publisher.example/work",
                        "work_id": "work:parsed",
                        "parse_machine_readable": True,
                        "raw_notice_text": notice,
                    }
                ],
                "private_strings": [notice],
            },
            issued_at="2026-10-29T00:00:00Z",
        )
        row = report["protocol_rows"][0]
        self.assertEqual(row["protocol"], "rsl")
        self.assertEqual(row["allowed_uses"], ["retrieval", "retrieval_inference"])
        self.assertEqual(row["prohibited_uses"], ["training"])
        self.assertEqual(row["payment_type"], "attribution")
        self.assertNotIn("<rsl", str(report))
        self.assertNotIn(notice, str(report))


class HonestClaimTests(unittest.TestCase):
    def test_status_and_paper_pointers_stay_honest(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("Development Status :: 4 - Beta", pyproject)
        self.assertNotIn("Development Status :: 5 - Production/Stable", pyproject)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("production-stable software", readme)
        self.assertIn("beta reference implementation", readme.lower())
        attribution = (ROOT / "docs" / "project_attribution.md").read_text(encoding="utf-8")
        self.assertIn("paper/rdllm_white_paper.md", attribution)
        self.assertIn("superseded", attribution.lower())
        long_paper = (ROOT / "paper" / "royalty_driven_llm_paper.md").read_text(encoding="utf-8")
        self.assertTrue(long_paper.splitlines()[2].lower().startswith("> **superseded"))
        matrix = (ROOT / "docs" / "provider_compatibility_matrix.md").read_text(encoding="utf-8")
        self.assertNotIn("ready live capability provider families", matrix)
        self.assertIn("design fixtures", matrix)
        self.assertNotIn("passed at RDLLM-L186", matrix)


if __name__ == "__main__":
    unittest.main()
