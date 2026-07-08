"""Public training-content summaries for foundation-model attribution."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import Work
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

TRAINING_SUMMARY_VERSION = "rdllm-training-content-summary/v1"


def _hashable_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in summary.items()
        if key not in {"summary_hash", "signature"}
    }


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _certification_hash(report: dict[str, Any] | None) -> str:
    if not report:
        return ""
    return str(report.get("report_hash") or hash_payload(report))


def _work_training_entry(engine: RoyaltyDrivenLLM, work: Work) -> dict[str, Any]:
    decision = engine.policy_engine.evaluate_work(
        work,
        "training",
        jurisdiction=engine.jurisdiction,
        creator_pool_rate=engine.creator_pool_rate,
    )
    chunk_ids = [
        chunk.chunk_id for chunk in engine.chunks if chunk.work_id == work.work_id
    ]
    chunk_hashes = [
        chunk.content_hash for chunk in engine.chunks if chunk.work_id == work.work_id
    ]
    training_values = {
        chunk_id: engine.training_value_priors.get(chunk_id, 0.0)
        for chunk_id in chunk_ids
    }
    return {
        "work_id": work.work_id,
        "creator_id": work.creator_id,
        "content_modality": "text",
        "content_category": "registered_creator_text",
        "license": work.license,
        "license_uri": work.license_uri,
        "source_uri": work.source_uri or f"registered://works/{work.work_id}",
        "policy_id": work.policy_id or f"policy:{work.work_id}",
        "content_hash": stable_hash(work.content),
        "chunk_count": len(chunk_ids),
        "chunk_hash_root": hash_payload(chunk_hashes),
        "training_allowed": decision.allowed,
        "training_policy_reasons": list(decision.reasons),
        "allowed_uses": list(work.allowed_uses),
        "prohibited_uses": list(work.prohibited_uses),
        "jurisdictions": list(work.jurisdictions),
        "requires_attribution": work.requires_attribution,
        "requires_royalty": work.requires_royalty,
        "minimum_creator_pool_rate": round(work.minimum_creator_pool_rate, 8),
        "revoked": work.revoked,
        "revoked_at": work.revoked_at,
        "derived_from": list(work.derived_from),
        "has_upstream_lineage": bool(work.derived_from),
        "training_value_root": hash_payload(training_values),
    }


def _aggregate(entries: list[dict[str, Any]], total_work_count: int) -> dict[str, Any]:
    license_counts = Counter(entry["license"] for entry in entries)
    source_counts = Counter(entry["content_category"] for entry in entries)
    allowed_use_counts: Counter[str] = Counter()
    prohibited_use_counts: Counter[str] = Counter()
    for entry in entries:
        allowed_use_counts.update(entry["allowed_uses"])
        prohibited_use_counts.update(entry["prohibited_uses"])
    allowed_training_count = sum(1 for entry in entries if entry["training_allowed"])
    revoked_count = sum(1 for entry in entries if entry["revoked"])
    royalty_required_count = sum(1 for entry in entries if entry["requires_royalty"])
    attribution_required_count = sum(1 for entry in entries if entry["requires_attribution"])
    return {
        "creator_count": len({entry["creator_id"] for entry in entries}),
        "work_count": total_work_count,
        "training_allowed_work_count": allowed_training_count,
        "training_blocked_work_count": total_work_count - allowed_training_count,
        "chunk_count": sum(int(entry["chunk_count"]) for entry in entries),
        "revoked_work_count": revoked_count,
        "royalty_required_work_count": royalty_required_count,
        "attribution_required_work_count": attribution_required_count,
        "training_rights_coverage": (
            round(allowed_training_count / total_work_count, 8)
            if total_work_count
            else 1.0
        ),
        "license_counts": dict(sorted(license_counts.items())),
        "source_category_counts": dict(sorted(source_counts.items())),
        "allowed_use_counts": dict(sorted(allowed_use_counts.items())),
        "prohibited_use_counts": dict(sorted(prohibited_use_counts.items())),
    }


def _private_strings(engine: RoyaltyDrivenLLM) -> list[str]:
    return [work.content for work in engine.works.values() if work.content]


def make_training_content_summary(
    engine: RoyaltyDrivenLLM,
    *,
    certification_report: dict[str, Any] | None = None,
    provider_card: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    provider: str = "provider:unspecified",
    model_id: str = "model:unspecified",
    model_version: str = "unknown",
    training_stage: str = "reference_corpus",
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public, hash-bound training-content summary."""

    entries = [
        _work_training_entry(engine, work)
        for work in sorted(engine.works.values(), key=lambda item: item.work_id)
    ]
    certification_summary = (certification_report or {}).get("summary", {})
    provider_certification = (provider_card or {}).get("certification", {})
    summary = {
        "summary_version": TRAINING_SUMMARY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider,
            "model_id": model_id,
            "model_version": model_version,
            "training_stage": training_stage,
        },
        "template_alignment": {
            "eu_ai_act_article_53_training_summary": True,
            "croissant_1_1_usage_policy": True,
            "spdx_3_ai_dataset_bom": True,
            "odrl_rights_policy": True,
            "public_summary_uses_categories_and_hash_roots": True,
        },
        "certification": {
            "report_hash": _certification_hash(certification_report),
            "highest_level": certification_summary.get("highest_level", ""),
            "status": certification_summary.get("status", ""),
        },
        "provider_card": {
            "card_hash": (provider_card or {}).get("card_hash", ""),
            "highest_level": provider_certification.get("highest_level", ""),
        },
        "training_content": {
            "modalities": {"text": len(entries)},
            "source_scope": "registered_creator_works",
            "training_stage": training_stage,
            "aggregate": _aggregate(entries, len(entries)),
            "cohorts": entries,
        },
        "rights_policy": {
            "rights_checked_before_training": True,
            "revoked_works_excluded": True,
            "minimum_creator_pool_rate_enforced": True,
            "copyright_policy": "respect machine-readable allowed uses, prohibited uses, revocation, attribution duties, and royalty duties",
            "tdm_rights_signal": "rights metadata is expressed separately from provenance credentials",
        },
        "commitments": {
            "work_root": hash_payload([entry["work_id"] for entry in entries]),
            "content_hash_root": hash_payload([entry["content_hash"] for entry in entries]),
            "policy_root": hash_payload(
                [
                    {
                        "work_id": entry["work_id"],
                        "policy_id": entry["policy_id"],
                        "training_allowed": entry["training_allowed"],
                        "reasons": entry["training_policy_reasons"],
                    }
                    for entry in entries
                ]
            ),
            "training_value_root": hash_payload(
                {entry["work_id"]: entry["training_value_root"] for entry in entries}
            ),
            "certification_report_hash": _certification_hash(certification_report),
            "provider_card_hash": (provider_card or {}).get("card_hash", ""),
        },
        "privacy": {
            "work_text_disclosed": False,
            "chunk_text_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "public_summary_uses_counts_and_hash_roots": True,
        },
        "limitations": [
            "reference summary covers registered training corpus, not web-scale unregistered training data",
            "training influence is represented by deterministic training-value priors, not provider hidden states",
            "public summary does not disclose private work text",
        ],
    }
    summary["summary_hash"] = hash_payload(_hashable_summary(summary))
    summary["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_summary(summary), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return summary


def validate_training_summary_shape(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "summary_version",
        "issuer",
        "created_at",
        "provider",
        "template_alignment",
        "certification",
        "provider_card",
        "training_content",
        "rights_policy",
        "commitments",
        "privacy",
        "limitations",
        "summary_hash",
        "signature",
    )
    for key in required:
        if key not in summary:
            errors.append(f"missing training summary field: {key}")
    if errors:
        return errors
    if summary.get("summary_version") != TRAINING_SUMMARY_VERSION:
        errors.append("training summary version is unsupported")
    for key in ("id", "model_id", "model_version", "training_stage"):
        if key not in summary.get("provider", {}):
            errors.append(f"missing training summary provider field: {key}")
    for key in ("aggregate", "cohorts", "modalities"):
        if key not in summary.get("training_content", {}):
            errors.append(f"missing training content field: {key}")
    for key in ("work_root", "content_hash_root", "policy_root", "training_value_root"):
        if key not in summary.get("commitments", {}):
            errors.append(f"missing training summary commitment: {key}")
    return errors


def verify_training_content_summary(
    engine: RoyaltyDrivenLLM,
    summary: dict[str, Any],
    *,
    certification_report: dict[str, Any] | None = None,
    provider_card: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a training-content summary against the registered corpus."""

    errors = validate_training_summary_shape(summary)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_summary(summary))
    if expected_hash != summary.get("summary_hash"):
        errors.append("training summary hash is not reproducible")

    expected = make_training_content_summary(
        engine,
        certification_report=certification_report,
        provider_card=provider_card,
        issuer=summary.get("issuer", DEFAULT_ISSUER),
        provider=summary.get("provider", {}).get("id", "provider:unspecified"),
        model_id=summary.get("provider", {}).get("model_id", "model:unspecified"),
        model_version=summary.get("provider", {}).get("model_version", "unknown"),
        training_stage=summary.get("provider", {}).get("training_stage", "reference_corpus"),
        created_at=summary.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider",
        "template_alignment",
        "certification",
        "provider_card",
        "training_content",
        "rights_policy",
        "commitments",
        "privacy",
        "limitations",
    ):
        if expected.get(key) != summary.get(key):
            errors.append(f"training summary {key} does not match recomputed corpus posture")
    if expected.get("summary_hash") != summary.get("summary_hash"):
        errors.append("training summary hash does not match corpus posture")

    summary_json = canonical_json(summary)
    for private in _private_strings(engine):
        if private in summary_json:
            errors.append("training summary discloses private work text")
            break

    if certification_report:
        cert_summary = certification_report.get("summary", {})
        if cert_summary.get("status") != "passed":
            errors.append("training summary is bound to a failing certification report")
        if _level_number(str(cert_summary.get("highest_level", ""))) < 16:
            errors.append("training summary requires at least RDLLM-L16 certification evidence")

    if provider_card:
        provider_level = provider_card.get("certification", {}).get("highest_level", "")
        if _level_number(str(provider_level)) < 16:
            errors.append("training summary requires an RDLLM-L16 provider card")

    signature = summary.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_summary(summary), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("training summary is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("training summary signature is invalid")

    return errors
