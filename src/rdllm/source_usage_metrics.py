"""Public source-usage metric profile used in RDLLM footers.

``support`` is the historical field name. Its method id is a text-overlap
score, not an entailment or fact-check judgment. ``entailment`` is a separate
optional channel; see ``rdllm.entailment_support``.
"""

from __future__ import annotations


SOURCE_USAGE_METRIC_PROFILE = "rdllm-observable-source-usage-metrics/v1"
SOURCE_USAGE_METRIC_SCOPE = (
    "observable_support_allocation_not_model_internal_reliance"
)
TEXT_OVERLAP_METRIC_ID = "rdllm-claim-text-overlap/v1"
NLI_SUPPORT_METRIC_ID = "rdllm-nli-support/v1"
LEGACY_CLAIM_OVERLAP_SUPPORT_METRIC_ID = "rdllm-claim-overlap-support/v1"
SOURCE_USAGE_METRIC_METHODS = {
    "support": TEXT_OVERLAP_METRIC_ID,
    "entailment": NLI_SUPPORT_METRIC_ID,
    "text_match": "rdllm-ngram-lcs-text-match/v1",
    "weight": "rdllm-normalized-source-utility-weight/v1",
    "payout": "rdllm-creator-pool-weighted-allocation/v1",
}
SOURCE_USAGE_METRIC_METHOD_FIELDS = {
    "support": "support_metric_method",
    "entailment": "entailment_metric_method",
    "text_match": "text_match_metric_method",
    "weight": "weight_metric_method",
    "payout": "payout_metric_method",
}


def source_usage_metric_row_fields() -> dict[str, str]:
    """Return the hash-bound metric provenance fields for a source row."""
    fields = {
        "usage_metric_profile": SOURCE_USAGE_METRIC_PROFILE,
        "usage_metric_scope": SOURCE_USAGE_METRIC_SCOPE,
    }
    for metric, field in SOURCE_USAGE_METRIC_METHOD_FIELDS.items():
        fields[field] = SOURCE_USAGE_METRIC_METHODS[metric]
    return fields
