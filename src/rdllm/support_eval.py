"""Score the support checker on claim/document files.

The on-disk fixture under ``tests/fixtures/support_eval`` is synthetic. It is
not a benchmark sample and not a measured public result. Public datasets such
as LLM-AggreFact are downloaded only when a caller asks, and they are not
committed in this repository.

Accepted row fields, after aliases:

- ``example_id`` (or ``id``)
- ``claim``
- ``document`` (or ``doc`` or ``source``)
- ``label`` as 1/0, true/false, or attributable/not_attributable
- ``dataset``, ``split``, ``fixture_kind``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.entailment_support import score_entailment, text_overlap_score
from rdllm.source_usage_metrics import NLI_SUPPORT_METRIC_ID, TEXT_OVERLAP_METRIC_ID

REPORT_KIND = "rdllm-support-checker-measurement/v1"
TEXT_OVERLAP_THRESHOLD = 0.75

HUGGINGFACE_SOURCES = {
    "llm-aggreFact": {
        "dataset": "lytang/LLM-AggreFact",
        "gated": True,
        "splits": ["dev", "test"],
        "arxiv": "2404.10774",
        "fields": ["dataset", "doc", "claim", "label", "contamination_identifier"],
        "note": (
            "Gated Hugging Face dataset. Accept the terms, then install the "
            "optional datasets package. This repository does not vendor the files."
        ),
    }
}


def _positive_label(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "supported", "attributable", "entailed"}:
        return True
    if text in {"0", "false", "no", "unsupported", "not_attributable", "not_entailed", "contradicted"}:
        return False
    return None


def normalize_example(row: dict[str, Any], *, index: int) -> dict[str, Any]:
    document = row.get("document", row.get("doc", row.get("source", "")))
    label = _positive_label(row.get("label"))
    if label is None:
        raise ValueError(f"example {index} has an unrecognized label")
    claim = str(row.get("claim", "")).strip()
    document_text = str(document).strip()
    if not claim or not document_text:
        raise ValueError(f"example {index} needs a claim and a document")
    return {
        "example_id": str(row.get("example_id", row.get("id", f"example-{index}"))),
        "claim": claim,
        "document": document_text,
        "label": label,
        "dataset": str(row.get("dataset", "")),
        "split": str(row.get("split", "")),
        "fixture_kind": str(row.get("fixture_kind", "")),
    }


def load_examples(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON list or JSONL file of claim/document rows."""

    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("JSON support file must be a list")
        rows = payload
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [normalize_example(row, index=index) for index, row in enumerate(rows, start=1)]


def _rates(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    if not pairs:
        return {
            "example_count": 0,
            "accuracy": None,
            "balanced_accuracy": None,
            "true_positive": 0,
            "false_positive": 0,
            "true_negative": 0,
            "false_negative": 0,
        }
    tp = sum(1 for gold, pred in pairs if gold and pred)
    tn = sum(1 for gold, pred in pairs if not gold and not pred)
    fp = sum(1 for gold, pred in pairs if not gold and pred)
    fn = sum(1 for gold, pred in pairs if gold and not pred)
    positives = tp + fn
    negatives = tn + fp
    recall_pos = tp / positives if positives else None
    recall_neg = tn / negatives if negatives else None
    balanced = None
    if recall_pos is not None and recall_neg is not None:
        balanced = round((recall_pos + recall_neg) / 2, 8)
    return {
        "example_count": len(pairs),
        "accuracy": round((tp + tn) / len(pairs), 8),
        "balanced_accuracy": balanced,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
    }


def score_examples(
    examples: list[dict[str, Any]],
    *,
    backend: str = "auto",
    dataset_label: str = "",
    split: str = "",
) -> dict[str, Any]:
    """Score text overlap and the entailment channel. Does not write a file."""

    overlap_pairs: list[tuple[bool, bool]] = []
    entailment_pairs: list[tuple[bool, bool]] = []
    rows: list[dict[str, Any]] = []
    backend_names: set[str] = set()
    model_name = ""
    model_version = ""
    threshold = None
    for example in examples:
        overlap = text_overlap_score(example["claim"], example["document"])
        entailment = score_entailment(
            example["claim"],
            example["document"],
            backend=backend,
        )
        overlap_pred = overlap >= TEXT_OVERLAP_THRESHOLD
        entailment_pred = entailment["label"] == "entailed"
        gold = bool(example["label"])
        overlap_pairs.append((gold, overlap_pred))
        entailment_pairs.append((gold, entailment_pred))
        backend_names.add(str(entailment["backend"]))
        model_name = str(entailment["model_name"])
        model_version = str(entailment["model_version"])
        threshold = entailment["threshold"]
        rows.append(
            {
                "example_id": example["example_id"],
                "gold_attributable": gold,
                "text_overlap_score": round(overlap, 8),
                "text_overlap_prediction": overlap_pred,
                "entailment_score": entailment["score"],
                "entailment_label": entailment["label"],
                "entailment_backend": entailment["backend"],
                "fixture_kind": example.get("fixture_kind", ""),
            }
        )
    fixture_kinds = sorted({row["fixture_kind"] for row in rows if row["fixture_kind"]})
    synthetic = any("synthetic" in kind for kind in fixture_kinds)
    report = {
        "report_kind": REPORT_KIND,
        "measured": True,
        "benchmark_result": False if synthetic or not dataset_label else True,
        "dataset_label": dataset_label,
        "split": split or next((example["split"] for example in examples if example.get("split")), ""),
        "example_count": len(examples),
        "fixture_kinds": fixture_kinds,
        "warnings": [
            "Numbers in this report describe only the rows that were scored.",
            "A synthetic fixture is not a public benchmark result.",
            "Do not copy this report into the fixture directory.",
        ],
        "metrics": {
            "text_overlap": {
                "metric_id": TEXT_OVERLAP_METRIC_ID,
                "role": "text_overlap_not_entailment",
                "threshold": TEXT_OVERLAP_THRESHOLD,
                **_rates(overlap_pairs),
            },
            "entailment": {
                "metric_id": NLI_SUPPORT_METRIC_ID,
                "model_name": model_name,
                "model_version": model_version,
                "backend": sorted(backend_names)[0] if len(backend_names) == 1 else sorted(backend_names),
                "threshold": threshold,
                **_rates(entailment_pairs),
            },
        },
        "rows": rows,
    }
    if synthetic:
        report["benchmark_result"] = False
        report["warnings"].append("fixture_kind marks these rows as synthetic.")
    if not dataset_label:
        report["benchmark_result"] = False
    return report


def write_report(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    _refuse_fixture_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _refuse_fixture_path(path: Path) -> None:
    resolved = path.resolve()
    fixtures = (Path(__file__).resolve().parents[2] / "tests" / "fixtures").resolve()
    if resolved == fixtures or fixtures in resolved.parents:
        raise ValueError(f"refusing to write into the fixture tree: {resolved}")


def download_examples(
    destination: str | Path,
    *,
    huggingface: str = "",
    url: str = "",
    split: str = "test",
    limit: int | None = None,
) -> dict[str, Any]:
    """Download a caller-selected dataset. Does not run unless asked."""

    output = Path(destination)
    _refuse_fixture_path(output)
    if bool(huggingface) == bool(url):
        raise ValueError("pass exactly one of huggingface or url")
    if huggingface:
        spec = HUGGINGFACE_SOURCES.get(huggingface)
        if spec is None:
            raise ValueError(f"unknown huggingface source: {huggingface}")
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "The optional 'datasets' package is not installed. "
                + spec["note"]
            ) from exc
        loaded = load_dataset(spec["dataset"], split=split)
        rows = []
        for index, row in enumerate(loaded):
            if limit is not None and index >= limit:
                break
            rows.append(
                {
                    "example_id": f"{huggingface}:{split}:{index}",
                    "dataset": row.get("dataset", huggingface),
                    "split": split,
                    "claim": row.get("claim", ""),
                    "document": row.get("doc", row.get("document", "")),
                    "label": row.get("label"),
                }
            )
        source_name = spec["dataset"]
    else:
        import urllib.request

        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
        parsed = [normalize_example(json.loads(line), index=index) for index, line in enumerate(payload.splitlines(), start=1) if line.strip()]
        if limit is not None:
            parsed = parsed[:limit]
        rows = parsed
        source_name = url
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return {
        "output": str(output),
        "example_count": len(rows),
        "source": source_name,
        "split": split,
        "vendored_in_repository": False,
    }
