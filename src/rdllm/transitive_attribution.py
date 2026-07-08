"""Transitive attribution reports for downstream reuse of copied RDLLM outputs."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

TRANSITIVE_ATTRIBUTION_REPORT_VERSION = "rdllm-transitive-attribution-report/v1"
DEFAULT_TRANSITIVE_PASS_THROUGH_RATE = Decimal("0.70")
MONEY_QUANT = Decimal("0.01")
WEIGHT_QUANT = Decimal("0.00000001")


def _decimal(value: Decimal | str | float | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal | str | float | int) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _weight(value: Decimal | str | float | int) -> str:
    return str(_decimal(value).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.items()
        if key not in {"envelope_hash", "signature"}
    }


def _hashable_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in capsule.items()
        if key not in {"capsule_hash", "signature"}
    }
    surfaces = payload.get("portable_surfaces")
    if isinstance(surfaces, dict):
        surfaces = deepcopy(surfaces)
        headers = surfaces.get("http_headers")
        if isinstance(headers, dict):
            headers.pop("RDLLM-Capsule-Hash", None)
        payload["portable_surfaces"] = surfaces
    return payload


def _normalise_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _copied_body_candidates(
    copied_output: str,
    capsule: dict[str, Any],
) -> list[dict[str, str]]:
    copied = _normalise_text(copied_output)
    surfaces = capsule.get("portable_surfaces", {})
    candidates: list[dict[str, str]] = []
    for marker_type in ("text_footer", "markdown_comment"):
        marker = surfaces.get(marker_type, "")
        if not isinstance(marker, str) or not marker:
            continue
        normalized_marker = _normalise_text(marker)
        if normalized_marker not in copied:
            continue
        body = copied.split(normalized_marker, 1)[0].rstrip()
        candidates.append(
            {
                "marker_type": marker_type,
                "marker_hash": stable_hash(normalized_marker),
                "body_hash": stable_hash(body),
            }
        )
    return candidates


def _answer_card(response_envelope: dict[str, Any]) -> dict[str, Any]:
    embedded = response_envelope.get("embedded_artifacts", {})
    card = embedded.get("answer_provenance_card", {})
    return card if isinstance(card, dict) else {}


def _source_rows(response_envelope: dict[str, Any]) -> list[dict[str, Any]]:
    card = _answer_card(response_envelope)
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(card.get("sources", []), start=1):
        source_weight = str(source.get("contribution_weight", "0"))
        raw_weight = _decimal(source_weight)
        row = {
            "source_index": index,
            "label": str(source.get("label", "")),
            "title": str(source.get("title", "")),
            "creator_id": str(source.get("creator_id", "")),
            "creator_name": str(source.get("creator_name", "")),
            "work_id": str(source.get("work_id", "")),
            "chunk_id": str(source.get("chunk_id", "")),
            "source_uri": str(source.get("source_uri", "")),
            "license": str(source.get("license", "")),
            "content_hash": str(source.get("content_hash", "")),
            "evidence_span_hashes": [
                str(item) for item in source.get("evidence_span_hashes", [])
            ],
            "support_score": source.get("support_score", 0.0),
            "retrieval_score": source.get("retrieval_score", 0.0),
            "text_match_score": source.get("text_match_score", 0.0),
            "upstream_contribution_weight": source_weight,
            "answer_card_source_entry_hash": str(
                source.get("source_entry_hash", "")
            ),
        }
        row["source_row_hash"] = hash_payload(row)
        rows.append(row)
    total = sum((_decimal(row["upstream_contribution_weight"]) for row in rows), Decimal("0"))
    if rows and total <= 0:
        equal = Decimal("1") / Decimal(len(rows))
        for row in rows:
            row["normalized_weight"] = _weight(equal)
            row["source_row_hash"] = hash_payload(
                {key: value for key, value in row.items() if key != "source_row_hash"}
            )
        return rows
    for row in rows:
        normalized = (
            _decimal(row["upstream_contribution_weight"]) / total
            if total > 0
            else Decimal("0")
        )
        row["normalized_weight"] = _weight(normalized)
        row["source_row_hash"] = hash_payload(
            {key: value for key, value in row.items() if key != "source_row_hash"}
        )
    return rows


def _settlement_obligations(
    rows: list[dict[str, Any]],
    *,
    downstream_event: UsageEvent,
    transitive_pool: Decimal,
    upstream_capsule_hash: str,
) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    for index, row in enumerate(rows):
        share = _decimal(row.get("normalized_weight", "0"))
        if index == len(rows) - 1:
            payout = transitive_pool - paid_so_far
        else:
            payout = (transitive_pool * share).quantize(
                MONEY_QUANT,
                rounding=ROUND_HALF_UP,
            )
            paid_so_far += payout
        obligation = {
            "obligation_id": f"transitive:{downstream_event.event_id}:{index + 1}",
            "recipient_creator_id": row["creator_id"],
            "recipient_creator_name": row["creator_name"],
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "source_label": row["label"],
            "source_row_hash": row["source_row_hash"],
            "content_hash": row["content_hash"],
            "basis": "copied_upstream_rdllm_output_used_downstream",
            "share_of_transitive_pool": _weight(share),
            "payout": _money(payout),
            "upstream_capsule_hash": upstream_capsule_hash,
            "downstream_event_hash": downstream_event.event_hash,
        }
        obligation["obligation_hash"] = hash_payload(obligation)
        obligations.append(obligation)
    return obligations


def _capsule_subject_hash_matches(capsule: dict[str, Any]) -> bool:
    subject = capsule.get("subject", {})
    if not isinstance(subject, dict):
        return False
    return capsule.get("commitments", {}).get("subject_hash") == hash_payload(subject)


def _source_entry_hashes_reproducible(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        source = {
            "label": row["label"],
            "title": row["title"],
            "creator_id": row["creator_id"],
            "creator_name": row["creator_name"],
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "source_uri": row["source_uri"],
            "license": row["license"],
            "content_hash": row["content_hash"],
            "evidence_span_hashes": row["evidence_span_hashes"],
            "support_score": row["support_score"],
            "retrieval_score": row["retrieval_score"],
            "text_match_score": row["text_match_score"],
            "contribution_weight": row["upstream_contribution_weight"],
        }
        if hash_payload(source) != row.get("answer_card_source_entry_hash"):
            return False
    return True


def _private_strings(
    *,
    downstream_event: UsageEvent,
    upstream_response_envelope: dict[str, Any],
    copied_output: str,
) -> list[str]:
    response = upstream_response_envelope.get("response", {})
    values = [
        downstream_event.prompt,
        downstream_event.output,
        downstream_event.answer_text,
        str(response.get("rendered_output", "")),
        copied_output,
    ]
    for source in downstream_event.source_references:
        values.append(source.quote)
    for claim in downstream_event.claim_support:
        values.append(claim.evidence_text)
    return [value for value in values if len(value) >= 16]


def make_transitive_attribution_report(
    *,
    upstream_capsule: dict[str, Any],
    upstream_response_envelope: dict[str, Any],
    downstream_event: UsageEvent,
    copied_output: str,
    pass_through_rate: Decimal | str | float = DEFAULT_TRANSITIVE_PASS_THROUGH_RATE,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report that preserves upstream attribution in downstream reuse."""

    rate = _decimal(pass_through_rate)
    if rate < 0 or rate > 1:
        raise ValueError("pass_through_rate must be between 0 and 1")

    copied_output = _normalise_text(copied_output)
    capsule_subject = upstream_capsule.get("subject", {})
    response = upstream_response_envelope.get("response", {})
    answer_card = _answer_card(upstream_response_envelope)
    rows = _source_rows(upstream_response_envelope)
    copied_candidates = _copied_body_candidates(copied_output, upstream_capsule)
    upstream_output_hash = str(capsule_subject.get("rendered_output_hash", ""))
    copied_body_matches = any(
        candidate["body_hash"] == upstream_output_hash
        for candidate in copied_candidates
    )
    copied_marker = copied_candidates[0] if copied_candidates else {}
    downstream_creator_pool = _decimal(_money(downstream_event.creator_pool))
    transitive_pool = (downstream_creator_pool * rate).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    residual_pool = downstream_creator_pool - transitive_pool
    capsule_hash = str(upstream_capsule.get("capsule_hash", ""))
    obligations = _settlement_obligations(
        rows,
        downstream_event=downstream_event,
        transitive_pool=transitive_pool,
        upstream_capsule_hash=capsule_hash,
    )
    obligation_total = sum(
        (_decimal(item["payout"]) for item in obligations),
        Decimal("0"),
    )
    response_output = str(response.get("rendered_output", ""))
    checks = {
        "capsule_hash_reproducible": hash_payload(_hashable_capsule(upstream_capsule))
        == capsule_hash,
        "capsule_subject_hash_matches_commitment": _capsule_subject_hash_matches(
            upstream_capsule
        ),
        "response_envelope_hash_reproducible": hash_payload(
            _hashable_envelope(upstream_response_envelope)
        )
        == upstream_response_envelope.get("envelope_hash", ""),
        "response_output_hash_matches_capsule_subject": stable_hash(response_output)
        == upstream_output_hash
        == response.get("rendered_output_hash", ""),
        "answer_card_sources_bound_to_envelope": answer_card.get(
            "commitments", {}
        ).get("source_root")
        == hash_payload(answer_card.get("sources", [])),
        "source_entry_hashes_reproducible": _source_entry_hashes_reproducible(rows),
        "copied_output_marker_present": bool(copied_candidates),
        "copied_output_body_matches_upstream_subject": copied_body_matches,
        "upstream_source_rows_present": bool(rows),
        "transitive_pool_conserved": obligation_total == transitive_pool,
        "downstream_pool_conserved": downstream_creator_pool
        == transitive_pool + residual_pool,
        "original_sources_survive_downstream_reuse": bool(rows)
        and all(item["recipient_creator_id"] for item in obligations),
        "no_private_text_disclosed": True,
    }
    report = {
        "report_version": TRANSITIVE_ATTRIBUTION_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "upstream": {
            "capsule_id": upstream_capsule.get("summary", {}).get(
                "capsule_id",
                upstream_capsule.get("portable_surfaces", {}).get("capsule_id", ""),
            ),
            "capsule_hash": capsule_hash,
            "capsule_subject_hash": upstream_capsule.get("commitments", {}).get(
                "subject_hash", ""
            ),
            "response_envelope_hash": upstream_response_envelope.get(
                "envelope_hash", ""
            ),
            "event_id": response.get("event_id", capsule_subject.get("event_id", "")),
            "event_hash": response.get(
                "event_hash", capsule_subject.get("event_hash", "")
            ),
            "rendered_output_hash": upstream_output_hash,
            "answer_card_hash": answer_card.get("card_hash", ""),
            "answer_card_source_root": answer_card.get("commitments", {}).get(
                "source_root", ""
            ),
            "source_count": len(rows),
        },
        "downstream": {
            "event_id": downstream_event.event_id,
            "event_hash": downstream_event.event_hash,
            "event_replay_hash": hash_payload(downstream_event.to_dict()),
            "prompt_hash": stable_hash(downstream_event.prompt),
            "answer_hash": stable_hash(
                downstream_event.answer_text or downstream_event.output
            ),
            "rendered_output_hash": stable_hash(downstream_event.output),
            "copied_input_hash": stable_hash(copied_output),
            "copied_body_hash": copied_marker.get("body_hash", ""),
            "copied_marker_type": copied_marker.get("marker_type", ""),
            "copied_marker_hash": copied_marker.get("marker_hash", ""),
            "creator_pool": _money(downstream_creator_pool),
        },
        "transitive_policy": {
            "profile": "rdllm-transitive-attribution/v1",
            "pass_through_rate": str(rate),
            "transitive_trigger": "downstream_input_contains_verified_rdllm_capsule_marker",
            "residual_policy": "downstream_local_sources_or_unattributed_escrow",
            "original_sources_survive_derivative_use": True,
            "wrapper_credit_cannot_extinguish_upstream_sources": True,
            "copied_marker_required": True,
            "copied_body_hash_required": True,
        },
        "upstream_source_rows": rows,
        "settlement_obligations": obligations,
        "residual_settlement": {
            "policy": "downstream_local_sources_or_unattributed_escrow",
            "creator_pool": _money(downstream_creator_pool),
            "transitive_pool": _money(transitive_pool),
            "residual_pool": _money(residual_pool),
            "downstream_provider_must_settle_residual_locally": True,
        },
        "checks": checks,
        "commitments": {
            "upstream_capsule_hash": capsule_hash,
            "upstream_response_envelope_hash": upstream_response_envelope.get(
                "envelope_hash", ""
            ),
            "downstream_event_hash": downstream_event.event_hash,
            "downstream_event_replay_hash": hash_payload(downstream_event.to_dict()),
            "copied_input_hash": stable_hash(copied_output),
            "upstream_source_root": hash_payload(rows),
            "obligation_root": hash_payload(obligations),
            "policy_hash": hash_payload(
                {
                    "profile": "rdllm-transitive-attribution/v1",
                    "pass_through_rate": str(rate),
                    "residual_policy": "downstream_local_sources_or_unattributed_escrow",
                }
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L42",
            "minimum_upstream_level": "RDLLM-L34",
            "upstream_source_count": len(rows),
            "transitive_obligation_count": len(obligations),
            "downstream_creator_pool": _money(downstream_creator_pool),
            "transitive_pool": _money(transitive_pool),
            "residual_pool": _money(residual_pool),
            "payout_conserved": obligation_total == transitive_pool
            and downstream_creator_pool == transitive_pool + residual_pool,
            "anti_laundering_enforced": checks[
                "original_sources_survive_downstream_reuse"
            ]
            and copied_body_matches,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "downstream_output_text_disclosed": False,
            "upstream_answer_text_disclosed": False,
            "source_text_disclosed": False,
            "copied_output_text_disclosed": False,
            "report_uses_hashes_capsules_and_source_ids": True,
        },
    }
    report_json = canonical_json(report)
    leaked = [
        value
        for value in _private_strings(
            downstream_event=downstream_event,
            upstream_response_envelope=upstream_response_envelope,
            copied_output=copied_output,
        )
        if value in report_json
    ]
    if leaked:
        report["checks"]["no_private_text_disclosed"] = False
        report["summary"]["status"] = "failed"
        report["summary"]["anti_laundering_enforced"] = False
    report["report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_transitive_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "upstream",
        "downstream",
        "transitive_policy",
        "upstream_source_rows",
        "settlement_obligations",
        "residual_settlement",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing transitive attribution report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != TRANSITIVE_ATTRIBUTION_REPORT_VERSION:
        errors.append("transitive attribution report version is unsupported")
    for key in ("capsule_hash", "rendered_output_hash", "source_count"):
        if key not in report.get("upstream", {}):
            errors.append(f"missing transitive upstream field: {key}")
    for key in ("event_id", "event_hash", "copied_input_hash", "creator_pool"):
        if key not in report.get("downstream", {}):
            errors.append(f"missing transitive downstream field: {key}")
    for key in ("pass_through_rate", "copied_marker_required"):
        if key not in report.get("transitive_policy", {}):
            errors.append(f"missing transitive policy field: {key}")
    for key in ("upstream_source_root", "obligation_root", "policy_hash"):
        if key not in report.get("commitments", {}):
            errors.append(f"missing transitive commitment: {key}")
    return errors


def verify_transitive_attribution_report(
    report: dict[str, Any],
    *,
    upstream_capsule: dict[str, Any],
    upstream_response_envelope: dict[str, Any],
    downstream_event: UsageEvent,
    copied_output: str,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a transitive attribution report against upstream and downstream evidence."""

    errors = validate_transitive_attribution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("transitive attribution report hash is not reproducible")

    rate = report.get("transitive_policy", {}).get(
        "pass_through_rate", str(DEFAULT_TRANSITIVE_PASS_THROUGH_RATE)
    )
    expected = make_transitive_attribution_report(
        upstream_capsule=upstream_capsule,
        upstream_response_envelope=upstream_response_envelope,
        downstream_event=downstream_event,
        copied_output=copied_output,
        pass_through_rate=rate,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "upstream",
        "downstream",
        "transitive_policy",
        "upstream_source_rows",
        "settlement_obligations",
        "residual_settlement",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"transitive attribution report {key} does not match evidence")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("transitive attribution report hash does not match evidence")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("transitive attribution report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"transitive attribution check failed: {check}")
    if report.get("summary", {}).get("anti_laundering_enforced") is not True:
        errors.append("transitive attribution anti-laundering enforcement is not ready")
    if report.get("privacy", {}).get("report_uses_hashes_capsules_and_source_ids") is not True:
        errors.append("transitive attribution report must use hashes, capsules, and source ids")

    report_json = canonical_json(report)
    for private in _private_strings(
        downstream_event=downstream_event,
        upstream_response_envelope=upstream_response_envelope,
        copied_output=_normalise_text(copied_output),
    ):
        if private in report_json:
            errors.append("transitive attribution report discloses private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("transitive attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("transitive attribution report signature is invalid")

    return errors
