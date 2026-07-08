"""Audit GitHub-facing onboarding, examples, localization, and SEO/GEO docs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "README.md": (
        "GitHub Start Here",
        "docs/github_start_here.md",
        "docs/first_5_minutes.md",
        "rdllm-first-run",
        "docs/public_explainer.md",
        "docs/project_attribution.md",
        "paper/rdllm_white_paper.md",
        "examples/live_use_cases/README.md",
        "examples/api_clients/README.md",
        "docs/i18n/en/quickstart.md",
        "docs/i18n/fr/quickstart.md",
        "docs/i18n/vi/quickstart.md",
    ),
    "docs/github_start_here.md": (
        "RDLLM GitHub Start Here",
        "If You Only Do One Thing",
        "rdllm-first-run",
        "rdllm_first_run status: passed",
        "First 5 Minutes",
        "Choose Your Explanation Depth",
        "project attribution map",
        "white paper",
        "Live Use Cases",
        "Multilingual Quickstarts",
        "Implementation Languages",
        "15",
        "French",
        "Vietnamese",
        "SEO And GEO Notes",
        "Stack Overflow Developer Survey 2025",
        "Google Search Central SEO Starter Guide",
        "GEO paper",
        "15 copyable",
        "live screenshots",
        "source_grounding_acceptance",
        "claim_source_disagreement_status",
    ),
    "docs/first_5_minutes.md": (
        "RDLLM First 5 Minutes",
        "You do not need an API key",
        "python -m pip install .",
        "rdllm-first-run",
        "rdllm_first_run status: passed",
        "Sources",
        "Claim Evidence",
        "support",
        "text_match",
        "payout",
        "disagreement=passed",
        "Common Problems",
        "Where To Go Next",
    ),
    "docs/public_explainer.md": (
        "RDLLM Public Explainer",
        "ELI5",
        "Simple",
        "Non-Technical",
        "Technical",
        "English",
        "French",
        "Vietnamese",
    ),
    "docs/project_attribution.md": (
        "RDLLM Project Attribution Map",
        "What Was Built",
        "Source Classes",
        "How Sources Become Product Rules",
        "Code Attribution",
        "Paper And Research Attribution",
        "paper/rdllm_white_paper.md",
        "Runtime Example Attribution",
        "Public Artifact Attribution",
        "Documentation Attribution",
        "Verification Commands",
        "paper/references.bib",
        "docs/recent_research.md",
        "src/rdllm",
        "tools/ship_check.py",
        "github_docs_readiness_audit.py",
    ),
    "paper/rdllm_white_paper.md": (
        "RDLLM White Paper",
        "State Of The Art",
        "observable_support_allocation_not_model_internal_reliance",
        "Cited but Not Verified",
        "How Do LLMs Cite?",
        "CiteGuard",
        "PaperTrail",
        "The Attribution Crisis in LLM Search Results",
        "Do LLM Attribution Metrics Transfer?",
        "W3C PROV",
        "W3C Verifiable Credentials",
        "C2PA",
        "IETF RFC 9943",
        "NIST AI 600-1",
        "EU AI Act",
        "U.S. Copyright Office",
        "Threat Model",
        "Allocation Mechanism",
        "Primary Sources And Evidence Base",
    ),
    "examples/live_use_cases/README.md": (
        "Live Screenshot Gallery",
        "screenshots/first-run.png",
        "screenshots/cli-answer-sources.png",
        "screenshots/service-smoke.png",
        "screenshots/provider-live-smoke.png",
        "Use Case 1",
        "Use Case 2",
        "Use Case 3",
        "Use Case 4",
        "Use Case 5",
        "Use Case 6",
        "Use Case 7",
        "Use Case 8",
        "Use Case 9",
        "Use Case 10",
        "Use Case 11",
        "Use Case 12",
        "Use Case 13",
        "Use Case 14",
        "Use Case 15",
        "rdllm-first-run",
        "Claim Evidence",
        "support=0.900",
        "text_match=0.900",
        "payout=0.183279",
        "disagreement=passed",
        "service_response_verify.py",
        "source_footer_verify.py",
        "production_display_ready: true",
        "service_load_smoke.py",
        "security_abuse_smoke.py",
        "package_smoke.py",
        "github_docs_readiness_audit.py",
    ),
    "examples/api_clients/README.md": (
        "## JavaScript",
        "## Python",
        "## TypeScript",
        "## Java",
        "## C#",
        "POST http://127.0.0.1:8765/v1/attribute",
        "display.rendered_text",
        "source_footer.rendered_text",
        "claim_source_disagreement_status",
    ),
}

IMPLEMENTATION_LANGUAGES = ("JavaScript", "Python", "TypeScript", "Java", "C#")
LOCALIZED_QUICKSTARTS = (
    "en",
    "es",
    "zh-Hans",
    "hi",
    "ar",
    "fr",
    "bn",
    "pt-BR",
    "id",
    "ur",
    "ru",
    "de",
    "ja",
    "ko",
    "vi",
)
REQUIRED_QUICKSTART_TERMS = (
    "rdllm-operator-doctor",
    "PYTHONPATH=src python3 -m rdllm.cli answer",
    "Claim Evidence",
    "production_display_ready",
    "source_grounding_acceptance",
    "explainer.md",
)
REQUIRED_EXPLAINER_TERMS = (
    "## ELI5",
    "## Simple",
    "## Non-Technical",
    "## Technical",
    "Claim Evidence",
    "source_grounding_acceptance",
)


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _missing_terms(path: Path, terms: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [term for term in terms if term not in text]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    checked_files: list[str] = []

    for file_name, required_terms in REQUIRED_FILES.items():
        path = ROOT / file_name
        if not path.is_file():
            errors.append(f"missing GitHub docs file: {file_name}")
            continue
        if not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty GitHub docs file: {file_name}")
            continue
        checked_files.append(file_name)
        for term in _missing_terms(path, required_terms):
            errors.append(f"{file_name}: missing required term: {term}")

    api_doc = ROOT / "examples" / "api_clients" / "README.md"
    if api_doc.is_file():
        api_lines = api_doc.read_text(encoding="utf-8").splitlines()
        for language in IMPLEMENTATION_LANGUAGES:
            if api_lines.count(f"## {language}") != 1:
                errors.append(
                    "examples/api_clients/README.md: expected one section for "
                    f"{language}"
                )

    i18n_root = ROOT / "docs" / "i18n"
    for language in LOCALIZED_QUICKSTARTS:
        quickstart_path = i18n_root / language / "quickstart.md"
        explainer_path = i18n_root / language / "explainer.md"
        if not quickstart_path.is_file():
            errors.append(f"missing localized quickstart: {relpath(quickstart_path)}")
        else:
            checked_files.append(relpath(quickstart_path))
            for term in _missing_terms(quickstart_path, REQUIRED_QUICKSTART_TERMS):
                errors.append(f"{relpath(quickstart_path)}: missing required term: {term}")
        if not explainer_path.is_file():
            errors.append(f"missing localized explainer: {relpath(explainer_path)}")
        else:
            checked_files.append(relpath(explainer_path))
            for term in _missing_terms(explainer_path, REQUIRED_EXPLAINER_TERMS):
                errors.append(f"{relpath(explainer_path)}: missing required term: {term}")

    return {
        "status": "failed" if errors else "passed",
        "checked_file_count": len(checked_files),
        "localized_quickstart_count": len(
            [
                language
                for language in LOCALIZED_QUICKSTARTS
                if (i18n_root / language / "quickstart.md").is_file()
            ]
        ),
        "localized_explainer_count": len(
            [
                language
                for language in LOCALIZED_QUICKSTARTS
                if (i18n_root / language / "explainer.md").is_file()
            ]
        ),
        "implementation_language_count": len(IMPLEMENTATION_LANGUAGES),
        "errors": errors,
        "checked_files": checked_files,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"github_docs_readiness_audit status: {report['status']}",
        f"checked_file_count: {report['checked_file_count']}",
        f"localized_quickstart_count: {report['localized_quickstart_count']}",
        f"localized_explainer_count: {report['localized_explainer_count']}",
        f"implementation_language_count: {report['implementation_language_count']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
