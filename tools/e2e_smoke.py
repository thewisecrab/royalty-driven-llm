"""End-to-end smoke test for a clean RDLLM checkout."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SAMPLE_CORPUS = ROOT / "examples" / "sample_corpus.json"
TEXT_ATTRIBUTION_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval "
    "scores, output citations, payout weights, and an event hash that allows "
    "auditors to replay the attribution."
)

sys.path.insert(0, str(SRC))

from rdllm.engine import RoyaltyDrivenLLM  # noqa: E402
from rdllm.models import UsageEvent  # noqa: E402
from rdllm.receipts import make_attribution_receipt, public_receipt, verify_receipt  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def run_cli_demo() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="rdllm-e2e-") as directory:
        ledger_path = Path(directory) / "demo_ledger.json"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "rdllm.cli",
                "demo",
                "--ledger",
                str(ledger_path),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return [
                "CLI demo failed",
                f"stdout: {result.stdout[-1000:]}",
                f"stderr: {result.stderr[-1000:]}",
            ], {}
        if not ledger_path.is_file():
            return ["CLI demo did not write a ledger"], {}
        ledger = load_json(ledger_path)

    engine = RoyaltyDrivenLLM.from_corpus_file(SAMPLE_CORPUS)
    events = [UsageEvent.from_dict(row) for row in ledger.get("events", [])]
    append_error(errors, len(events) == 4, "CLI demo should emit four usage events")
    for event in events:
        audit_errors = engine.audit_event(event)
        if audit_errors:
            errors.append(f"CLI event audit failed for {event.event_id}: {audit_errors}")
    append_error(
        errors,
        all("Sources" in event.output for event in events),
        "every CLI demo event should render a source footer",
    )
    append_error(
        errors,
        any("Claim Evidence" in event.output for event in events),
        "CLI demo should render claim evidence rows",
    )
    return errors, {
        "event_count": len(events),
        "event_ids": [event.event_id for event in events],
    }


def run_api_attribution() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    engine = RoyaltyDrivenLLM.from_corpus_file(SAMPLE_CORPUS)
    event = engine.attribute_text(
        "What governance process handles disputes and licensing?",
        TEXT_ATTRIBUTION_OUTPUT,
        gross_revenue=Decimal("1.00"),
    )
    errors.extend(engine.audit_event(event))
    append_error(
        errors,
        event.grounding_quality.get("verdict") == "verified",
        "external attribution event should be verified",
    )
    append_error(
        errors,
        event.attribution_gap.get("verdict") == "closed",
        "external attribution event should close the attribution gap",
    )
    append_error(
        errors,
        {source.creator_id for source in event.source_references} == {"arjun"},
        "external attribution should credit only the source that supports the output",
    )
    append_error(
        errors,
        "claims=2; confidence=verified" in event.output,
        "footer should expose verified claim count",
    )
    append_error(
        errors,
        "Creator Governance for AI Licensing" not in event.output,
        "prompt-topical but unsupported governance source should not appear in footer",
    )

    receipt = make_attribution_receipt(
        event,
        issuer="rdllm-e2e-smoke",
        model_id="model:e2e-smoke",
        model_version="2026-07-01",
        route_id="route:e2e-smoke",
        signing_secret="e2e-secret",
    )
    receipt_errors = verify_receipt(receipt, signing_secret="e2e-secret")
    if receipt_errors:
        errors.append(f"receipt verification failed: {receipt_errors}")
    public = public_receipt(receipt)
    append_error(
        errors,
        "economics" not in public,
        "public receipt should not expose economics payload",
    )
    append_error(
        errors,
        public.get("grounding_quality", {}).get("verdict") == "verified",
        "public receipt should expose verified grounding",
    )
    return errors, {
        "event_id": event.event_id,
        "visible_sources": [source.label for source in event.source_references],
        "receipt_hash": receipt.get("receipt_hash", ""),
        "public_receipt_protocol": public.get("protocol_version", ""),
    }


def run_artifact_readiness() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    certification = load_json(ROOT / "artifacts" / "certification_report.json")
    response_state = load_json(
        ROOT
        / "artifacts"
        / "universal_provider_response_state_normalization_contract.json"
    )
    discovery = load_json(ROOT / "artifacts" / "discovery_manifest.json")
    append_error(
        errors,
        certification.get("summary", {}).get("status") == "passed",
        "certification report should be passed",
    )
    append_error(
        errors,
        certification.get("summary", {}).get("highest_level") == "RDLLM-L186",
        "certification report should certify RDLLM-L186",
    )
    append_error(
        errors,
        response_state.get("summary", {}).get("status") == "ready",
        "L186 response-state contract should be ready",
    )
    append_error(
        errors,
        discovery.get("summary", {}).get("status") == "ready",
        "discovery manifest should be ready",
    )
    return errors, {
        "highest_level": certification.get("summary", {}).get("highest_level", ""),
        "case_count": certification.get("summary", {}).get("case_count", 0),
        "discovery_artifact_count": discovery.get("summary", {}).get(
            "artifact_count",
            0,
        ),
    }


def run_smoke() -> dict[str, Any]:
    sections = {
        "cli_demo": run_cli_demo,
        "api_attribution": run_api_attribution,
        "artifact_readiness": run_artifact_readiness,
    }
    errors: list[str] = []
    section_reports: dict[str, Any] = {}
    for name, runner in sections.items():
        section_errors, report = runner()
        section_reports[name] = report
        errors.extend(f"{name}: {error}" for error in section_errors)
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "sections": section_reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_smoke()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"e2e_smoke status: {report['status']}")
        for name, section in report["sections"].items():
            print(f"{name}: {json.dumps(section, sort_keys=True)}")
        if report["errors"]:
            print("errors:", file=sys.stderr)
            for error in report["errors"]:
                print(f"- {error}", file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
