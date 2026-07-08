"""Beginner-friendly first-run demo for RDLLM."""

from __future__ import annotations

import argparse
from decimal import Decimal
from importlib import resources

from rdllm.engine import RoyaltyDrivenLLM


DEFAULT_PROMPT = "How should AI prove attribution?"
REQUIRED_OUTPUT_MARKERS = (
    "Sources",
    "Claim Evidence",
    "support=",
    "text_match=",
    "payout=",
    "disagreement=passed",
)


def _sample_corpus_path() -> str:
    return str(resources.files("rdllm.data").joinpath("sample_corpus.json"))


def run_first_demo(
    *,
    prompt: str = DEFAULT_PROMPT,
    gross_revenue: Decimal | str = Decimal("1.00"),
) -> tuple[int, str]:
    engine = RoyaltyDrivenLLM.from_corpus_file(_sample_corpus_path())
    event = engine.generate(prompt, gross_revenue=Decimal(str(gross_revenue)))
    output = event.output
    missing = [marker for marker in REQUIRED_OUTPUT_MARKERS if marker not in output]
    source_count = len(event.source_references)
    claim_count = len([claim for claim in event.claim_support if claim.supported])
    payout_count = len(
        [
            share
            for share in event.royalty_shares
            if share.payout > Decimal("0")
            and not share.creator_id.endswith("_escrow")
        ]
    )
    if source_count < 1:
        missing.append("at least one visible source")
    if claim_count < 1:
        missing.append("at least one supported claim")
    if payout_count < 1:
        missing.append("at least one creator payout row")

    status = "failed" if missing else "passed"
    lines = [
        f"rdllm_first_run status: {status}",
        "",
        "What just happened:",
        f"1. Generated an answer for: {prompt}",
        f"2. Found visible sources: {source_count}",
        f"3. Found supported claim-evidence rows: {claim_count}",
        f"4. Found creator payout rows: {payout_count}",
        "",
        "What to look for below:",
        "- [S1], [S2], ... labels in the answer",
        "- Sources section with support, text_match, payout, and hash fields",
        "- Claim Evidence rows showing which source supports each claim",
        "- disagreement=passed, which means no visible source plainly contradicted the claim",
        "",
        "Generated demo output:",
        output,
        "",
        "Next steps:",
        "- Read docs/first_5_minutes.md for the slow, hand-held path.",
        "- Read examples/api_clients/README.md when you want to call the HTTP API.",
        "- Run rdllm-operator-doctor when you want the packaged self-test.",
    ]
    if missing:
        lines.extend(
            [
                "",
                "Missing expected proof markers:",
                *[f"- {marker}" for marker in missing],
            ]
        )
    return (1 if missing else 0), "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt for the bundled first-run demo.",
    )
    parser.add_argument(
        "--gross-revenue",
        default="1.00",
        help="Demo gross revenue used to show payout allocation.",
    )
    args = parser.parse_args(argv)

    exit_code, text = run_first_demo(
        prompt=args.prompt,
        gross_revenue=args.gross_revenue,
    )
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
