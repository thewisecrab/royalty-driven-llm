#!/usr/bin/env python3
"""Score the RDLLM support checker on a local claim/document file.

This tool does not download a dataset unless ``download`` is used. It does not
write into ``tests/fixtures``. A score report is a measurement of the file you
pass in. The committed synthetic fixture is not a benchmark result.

Examples:
  PYTHONPATH=src python3 tools/eval_support_checker.py sources
  PYTHONPATH=src python3 tools/eval_support_checker.py score tests/fixtures/support_eval/synthetic_factcheck.jsonl
  PYTHONPATH=src python3 tools/eval_support_checker.py download --huggingface llm-aggreFact --output /tmp/llm-aggreFact-test.jsonl --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rdllm.support_eval import (  # noqa: E402
    HUGGINGFACE_SOURCES,
    download_examples,
    load_examples,
    score_examples,
    write_report,
)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sources = sub.add_parser("sources", help="List documented external datasets. Nothing is downloaded.")
    sources.set_defaults(command="sources")

    score = sub.add_parser("score", help="Score a local JSON or JSONL file.")
    score.add_argument("path")
    score.add_argument("--backend", default="auto")
    score.add_argument("--dataset-label", default="")
    score.add_argument("--split", default="")
    score.add_argument(
        "--output",
        help="Write the measurement JSON here. Refuses tests/fixtures.",
    )
    score.set_defaults(command="score")

    download = sub.add_parser("download", help="Download a caller-selected dataset.")
    download.add_argument("--huggingface", choices=sorted(HUGGINGFACE_SOURCES))
    download.add_argument("--url", default="")
    download.add_argument("--output", required=True)
    download.add_argument("--split", default="test")
    download.add_argument("--limit", type=int)
    download.set_defaults(command="download")

    args = parser.parse_args(argv)
    if args.command == "sources":
        _print_json(
            {
                "huggingface": HUGGINGFACE_SOURCES,
                "loader_format": {
                    "required": ["claim", "document or doc", "label"],
                    "label_values": ["1/0", "attributable/not_attributable"],
                    "attributionbench": (
                        "Convert AttributionBench rows to this JSONL shape and "
                        "pass the file to score. No AttributionBench file is bundled."
                    ),
                },
                "committed_fixture": "tests/fixtures/support_eval/synthetic_factcheck.jsonl",
                "committed_fixture_is_a_benchmark": False,
            }
        )
        return 0
    if args.command == "score":
        examples = load_examples(args.path)
        report = score_examples(
            examples,
            backend=args.backend,
            dataset_label=args.dataset_label,
            split=args.split,
        )
        if args.output:
            write_report(report, args.output)
        else:
            _print_json(report)
        return 0
    try:
        summary = download_examples(
            args.output,
            huggingface=args.huggingface or "",
            url=args.url,
            split=args.split,
            limit=args.limit,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_json(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
