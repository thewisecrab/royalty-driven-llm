"""Portable content credentials for universal RDLLM attribution.

The L136 layer packages the public proof stack into one asset-level credential.
It is designed to sit beside C2PA/Content Credentials, watermark detectors,
fingerprint registries, and source-footers: the credential does not replace
those systems, it binds them to source attribution, payout eligibility, and the
non-repudiable provider invocation witness introduced at L135.
"""

from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash
from rdllm.transparency import merkle_root

UNIVERSAL_CONTENT_CREDENTIAL_VERSION = "rdllm-universal-content-credential/v1"
UNIVERSAL_CONTENT_CREDENTIAL_SCHEMA = (
    "docs/schemas/universal_content_credential.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L136"
MINIMUM_INPUT_LEVEL = "RDLLM-L135"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-content-credential.json"

DECLARED_HASH_FIELDS = (
    "universal_content_credential_hash",
    "universal_invocation_witness_hash",
    "binding_report_hash",
    "grounded_source_footer_hash",
    "source_footer_delivery_hash",
    "warranted_source_footer_hash",
    "evidence_preview_footer_hash",
    "evidence_locator_manifest_hash",
    "citation_url_health_hash",
    "card_hash",
    "envelope_hash",
    "statement_hash",
    "report_hash",
    "profile_hash",
    "manifest_hash",
    "bundle_hash",
    "graph_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_answer_text",
    "rendered_output",
    "copied_output",
    "delivered_output",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "customer_email",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "license_server_secret",
    "raw_license_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_content_credential_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L136 universal content credential."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_content_credential_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(
    report: dict[str, Any], credential_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in credential_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: str) -> int:
    try:
        return int(str(level).rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _artifact_type(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for key in (
        "credential_version",
        "witness_version",
        "report_version",
        "version",
        "envelope_version",
        "card_version",
        "statement_version",
        "profile_version",
        "manifest_version",
        "footer_version",
        "delivery_version",
        "preview_version",
        "locator_version",
        "url_health_version",
        "certification_version",
    ):
        value = artifact.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _artifact_bindings(credential_input: dict[str, Any]) -> dict[str, Any]:
    names = (
        "certification_report",
        "provider_attribution_card",
        "response_envelope",
        "answer_provenance_card",
        "grounded_source_footer",
        "source_footer_delivery",
        "warranted_source_footer",
        "evidence_preview_footer",
        "evidence_locator_manifest",
        "citation_url_health",
        "output_provenance_binding_report",
        "universal_invocation_witness",
        "royalty_statement",
        "revenue_allocation_report",
        "integration_profile",
        "discovery_manifest",
    )
    rows = []
    for name in names:
        artifact = credential_input.get(name)
        if not artifact:
            continue
        row = {
            "name": name,
            "artifact_type": _artifact_type(artifact),
            "declared_hash": _declared_hash(artifact),
            "payload_hash": hash_payload(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        }
        row["binding_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": merkle_root([row["binding_hash"] for row in rows]),
        "bindings": rows,
    }


def _by_label(rows: list[dict[str, Any]], label_key: str = "label") -> dict[str, dict[str, Any]]:
    return {str(row.get(label_key, "")): row for row in rows if row.get(label_key)}


def _first_by_label(
    rows: list[dict[str, Any]], label_key: str = "source_label"
) -> dict[str, dict[str, Any]]:
    by_label: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = str(row.get(label_key, ""))
        if label and label not in by_label:
            by_label[label] = row
    return by_label


def _source_attribution_rows(credential_input: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = credential_input.get("source_attribution_rows")
    if isinstance(explicit, list):
        rows = [dict(row) for row in explicit]
        for row in rows:
            row.setdefault("source_credential_row_hash", hash_payload(row))
        return rows

    footer_rows = credential_input.get("grounded_source_footer", {}).get("footer_rows", [])
    answer_sources = _by_label(
        credential_input.get("answer_provenance_card", {}).get("sources", [])
    )
    preview_sources = _by_label(
        credential_input.get("evidence_preview_footer", {}).get("source_preview_rows", [])
    )
    locator_rows = _first_by_label(
        credential_input.get("evidence_locator_manifest", {}).get(
            "evidence_locator_rows", []
        )
    )
    health_rows = _first_by_label(
        credential_input.get("citation_url_health", {}).get("citation_url_health_rows", [])
    )
    delivery_sources = _by_label(
        credential_input.get("source_footer_delivery", {}).get("source_delivery_rows", [])
    )
    rows = []
    for footer in footer_rows:
        label = str(footer.get("label", ""))
        answer = answer_sources.get(label, {})
        preview = preview_sources.get(label, {})
        locator = locator_rows.get(label, {})
        health = health_rows.get(label, {})
        delivery = delivery_sources.get(label, {})
        public = {
            "source_label": label,
            "display_label": str(footer.get("display_label", "")),
            "work_id": str(footer.get("work_id", "")),
            "chunk_id": str(footer.get("chunk_id", "")),
            "creator_id": str(footer.get("creator_id", "")),
            "creator_name_hash": stable_hash(str(footer.get("creator_name", ""))),
            "title_hash": stable_hash(str(footer.get("title", ""))),
            "source_uri_hash": stable_hash(str(footer.get("source_uri", ""))),
            "content_hash_prefix": str(footer.get("content_hash_prefix", "")),
            "supported_claim_count": int(footer.get("supported_claim_count", 0) or 0),
            "license_status": str(footer.get("license_status", "")),
            "royalty_status": str(footer.get("royalty_status", "")),
            "confidence_level": str(footer.get("confidence_level", "")),
            "source_available": bool(footer.get("source_available")),
            "footer_row_hash": str(footer.get("footer_row_hash", "")),
            "answer_card_source_hash": str(answer.get("source_entry_hash", "")),
            "source_preview_row_hash": str(preview.get("source_preview_row_hash", "")),
            "evidence_locator_row_hash": str(locator.get("evidence_locator_row_hash", "")),
            "citation_url_health_row_hash": str(
                health.get("citation_url_health_row_hash", "")
            ),
            "source_delivery_row_hash": str(delivery.get("source_delivery_row_hash", "")),
            "direct_payout_allowed": bool(
                preview.get("source_creator_direct_payout_allowed", True)
            ),
            "settlement_action": str(
                preview.get(
                    "settlement_action",
                    "direct_source_creator_payout"
                    if footer.get("royalty_status") == "active"
                    else "escrow_or_hold",
                )
            ),
        }
        public["source_credential_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _payout_rows(credential_input: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = credential_input.get("payout_eligibility_rows")
    if isinstance(explicit, list):
        rows = [dict(row) for row in explicit]
        for row in rows:
            row.setdefault("payout_credential_row_hash", hash_payload(row))
        return rows

    royalty = credential_input.get("royalty_statement", {})
    rows = []
    for work in royalty.get("work_statements", []):
        public = {
            "creator_id": str(work.get("creator_id", "")),
            "work_id": str(work.get("work_id", "")),
            "event_count": int(work.get("event_count", 0) or 0),
            "visible_source_count": int(work.get("visible_source_count", 0) or 0),
            "supported_claim_count": int(work.get("supported_claim_count", 0) or 0),
            "source_access_count": int(work.get("source_access_count", 0) or 0),
            "payout_state": "payable"
            if Decimal(str(work.get("total_payout", "0") or "0")) > Decimal("0")
            else "held_or_escrow",
            "total_payout": str(work.get("total_payout", "0")),
            "royalty_statement_hash": _declared_hash(royalty),
        }
        public["payout_credential_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _provider_invocation_rows(credential_input: dict[str, Any]) -> list[dict[str, Any]]:
    witness = credential_input.get("universal_invocation_witness", {})
    receipts = {
        str(row.get("invocation_id", "")): row
        for row in witness.get("provider_receipt_rows", [])
    }
    witnesses_by_invocation: dict[str, list[dict[str, Any]]] = {}
    for row in witness.get("witness_rows", []):
        witnesses_by_invocation.setdefault(str(row.get("invocation_id", "")), []).append(row)

    rows = []
    for call in witness.get("coverage_call_rows", []):
        invocation_id = str(call.get("invocation_id", ""))
        receipt = receipts.get(invocation_id, {})
        witness_rows = witnesses_by_invocation.get(invocation_id, [])
        public = {
            "invocation_id_hash": stable_hash(invocation_id),
            "request_id_hash": stable_hash(str(call.get("request_id", ""))),
            "provider_family": str(call.get("provider_family", "")),
            "route_id_hash": stable_hash(str(call.get("route_id", ""))),
            "native_model_hash": stable_hash(str(call.get("native_model", ""))),
            "coverage_call_hash": str(call.get("coverage_call_hash", "")),
            "provider_receipt_hash": str(receipt.get("provider_receipt_hash", "")),
            "egress_event_bound": any(
                row.get("invocation_id") == invocation_id
                for row in witness.get("egress_event_rows", [])
            ),
            "independent_witness_count": len(
                {
                    str(row.get("organization_id", ""))
                    for row in witness_rows
                    if row.get("independent") is True
                    and row.get("replay_verdict") == "accepted"
                }
            ),
            "nonrepudiation_complete": witness.get("summary", {}).get(
                "nonrepudiation_complete"
            )
            is True,
        }
        public["provider_invocation_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _content_subject(credential_input: dict[str, Any]) -> dict[str, Any]:
    content = credential_input.get("content", {})
    response = credential_input.get("response_envelope", {}).get("response", {})
    output_binding = credential_input.get("output_provenance_binding_report", {})
    output_summary = output_binding.get("summary", {})
    output_subject = output_binding.get("binding_subject", {})
    source_rows = _source_attribution_rows(credential_input)
    payout_rows = _payout_rows(credential_input)
    provider_rows = _provider_invocation_rows(credential_input)
    output_hash = str(
        content.get("output_hash")
        or output_summary.get("copied_output_hash")
        or output_subject.get("copied_output_hash")
        or response.get("answer_hash", "")
    )
    rendered_hash = str(
        content.get("rendered_output_hash")
        or output_subject.get("rendered_output_hash")
        or response.get("rendered_output_hash", "")
    )
    subject = {
        "content_id": str(
            content.get("content_id") or f"rdllm-content-{output_hash[:16]}"
        ),
        "content_kind": str(content.get("content_kind", "ai_generated_answer")),
        "media_type": str(content.get("media_type", "text/markdown")),
        "modality": str(content.get("modality", "text")),
        "language": str(content.get("language", "en")),
        "output_hash": output_hash,
        "rendered_output_hash": rendered_hash,
        "response_envelope_hash": _declared_hash(
            credential_input.get("response_envelope")
        ),
        "answer_provenance_card_hash": _declared_hash(
            credential_input.get("answer_provenance_card")
        ),
        "output_provenance_binding_hash": _declared_hash(output_binding),
        "output_provenance_subject_hash": str(output_summary.get("subject_hash", "")),
        "universal_invocation_witness_hash": _declared_hash(
            credential_input.get("universal_invocation_witness")
        ),
        "discovery_manifest_hash": _declared_hash(
            credential_input.get("discovery_manifest")
        ),
        "source_count": len(source_rows),
        "payout_row_count": len(payout_rows),
        "provider_invocation_count": len(provider_rows),
        "source_root": merkle_root(
            [row["source_credential_row_hash"] for row in source_rows]
        ),
        "payout_root": merkle_root(
            [row["payout_credential_row_hash"] for row in payout_rows]
        ),
        "provider_invocation_root": merkle_root(
            [row["provider_invocation_row_hash"] for row in provider_rows]
        ),
    }
    subject["content_subject_hash"] = hash_payload(subject)
    return subject


def _output_credential_rows(
    credential_input: dict[str, Any],
    subject: dict[str, Any],
    artifact_bindings: dict[str, Any],
    *,
    signing_secret: str | None,
) -> list[dict[str, Any]]:
    rows = []
    existing = credential_input.get("output_provenance_binding_report", {}).get(
        "content_credential_rows", []
    )
    for row in existing:
        payload = {
            "manifest_profile": "c2pa-compatible-rdllm-universal-attribution-credential/v1",
            "manifest_id": str(
                row.get("manifest_id")
                or f"rdllm-ucc-{subject['output_hash'][:16]}"
            ),
            "assertion_label": "org.rdllm.universal_attribution.v1",
            "source_assertion_label": str(row.get("assertion_label", "")),
            "provenance_pointer": DEFAULT_WELL_KNOWN_PATH,
            "bound_output_hash": subject["output_hash"],
            "bound_rendered_output_hash": subject["rendered_output_hash"],
            "bound_content_subject_hash": subject["content_subject_hash"],
            "bound_output_provenance_subject_hash": subject[
                "output_provenance_subject_hash"
            ],
            "bound_output_credential_row_hash": str(row.get("credential_row_hash", "")),
            "bound_universal_invocation_witness_hash": subject[
                "universal_invocation_witness_hash"
            ],
            "bound_source_root": subject["source_root"],
            "bound_payout_root": subject["payout_root"],
            "bound_provider_invocation_root": subject["provider_invocation_root"],
            "bound_artifact_root": artifact_bindings["artifact_binding_root"],
            "ai_generated": bool(row.get("ai_generated", True)),
            "not_a_tdm_rights_assertion": bool(
                row.get("not_a_tdm_rights_assertion", True)
            ),
            "raw_output_text_disclosed": False,
        }
        credential = {
            **payload,
            "credential_payload_hash": hash_payload(payload),
            "signature_algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
            "signature": sign_payload(payload, signing_secret)
            if signing_secret
            else "",
            "verified": bool(row.get("verified", True)),
        }
        credential["credential_row_hash"] = hash_payload(credential)
        rows.append(credential)
    if rows:
        return rows

    payload = {
        "manifest_profile": "c2pa-compatible-rdllm-universal-attribution-credential/v1",
        "manifest_id": f"rdllm-ucc-{subject['output_hash'][:16]}",
        "assertion_label": "org.rdllm.universal_attribution.v1",
        "source_assertion_label": "",
        "provenance_pointer": DEFAULT_WELL_KNOWN_PATH,
        "bound_output_hash": subject["output_hash"],
        "bound_rendered_output_hash": subject["rendered_output_hash"],
        "bound_content_subject_hash": subject["content_subject_hash"],
        "bound_output_provenance_subject_hash": subject[
            "output_provenance_subject_hash"
        ],
        "bound_output_credential_row_hash": "",
        "bound_universal_invocation_witness_hash": subject[
            "universal_invocation_witness_hash"
        ],
        "bound_source_root": subject["source_root"],
        "bound_payout_root": subject["payout_root"],
        "bound_provider_invocation_root": subject["provider_invocation_root"],
        "bound_artifact_root": artifact_bindings["artifact_binding_root"],
        "ai_generated": True,
        "not_a_tdm_rights_assertion": True,
        "raw_output_text_disclosed": False,
    }
    credential = {
        **payload,
        "credential_payload_hash": hash_payload(payload),
        "signature_algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "signature": sign_payload(payload, signing_secret) if signing_secret else "",
        "verified": False,
    }
    credential["credential_row_hash"] = hash_payload(credential)
    return [credential]


def _durable_signal_rows(
    credential_input: dict[str, Any], subject: dict[str, Any]
) -> list[dict[str, Any]]:
    existing = credential_input.get("output_provenance_binding_report", {}).get(
        "durable_signal_rows", []
    )
    rows = []
    for row in existing:
        public = {
            "signal_type": str(row.get("signal_type", "")),
            "verifier": str(row.get("verifier", "")),
            "purpose": str(row.get("purpose", "")),
            "bound_output_hash": subject["output_hash"],
            "bound_content_subject_hash": subject["content_subject_hash"],
            "bound_output_provenance_subject_hash": subject[
                "output_provenance_subject_hash"
            ],
            "confidence": str(row.get("confidence", "0")),
            "signal_present": bool(row.get("signal_present", False)),
            "raw_output_text_disclosed": bool(
                row.get("raw_output_text_disclosed", False)
            ),
        }
        public["signal_id"] = stable_hash(
            f"rdllm-ucc-signal:{public['signal_type']}:{subject['content_subject_hash']}"
        )
        public["signal_row_hash"] = hash_payload(public)
        rows.append(public)
    footer_signal = {
        "signal_type": "rdllm_visible_source_footer",
        "verifier": "verify-universal-content-credential",
        "purpose": "visible source footer binds output to source attribution and payout proof",
        "bound_output_hash": subject["output_hash"],
        "bound_content_subject_hash": subject["content_subject_hash"],
        "bound_output_provenance_subject_hash": subject[
            "output_provenance_subject_hash"
        ],
        "confidence": "1.000000" if subject["source_count"] else "0.000000",
        "signal_present": bool(subject["source_count"]),
        "raw_output_text_disclosed": False,
    }
    footer_signal["signal_id"] = stable_hash(
        f"rdllm-ucc-signal:footer:{subject['content_subject_hash']}"
    )
    footer_signal["signal_row_hash"] = hash_payload(footer_signal)
    rows.append(footer_signal)
    return rows


def _public_verification_rows(
    credential_input: dict[str, Any], subject: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [
        {
            "surface": "well_known",
            "path": DEFAULT_WELL_KNOWN_PATH,
            "verifier_command": "verify-universal-content-credential",
            "bound_content_subject_hash": subject["content_subject_hash"],
            "required": True,
        },
        {
            "surface": "c2pa_content_credential",
            "path": "org.rdllm.universal_attribution.v1",
            "verifier_command": "verify-universal-content-credential",
            "bound_content_subject_hash": subject["content_subject_hash"],
            "required": True,
        },
        {
            "surface": "visible_source_footer",
            "path": "embedded-rdllm-source-footer",
            "verifier_command": "verify-grounded-source-footer",
            "bound_content_subject_hash": subject["content_subject_hash"],
            "required": True,
        },
    ]
    for row in credential_input.get("output_provenance_binding_report", {}).get(
        "public_verification_rows", []
    ):
        rows.append(
            {
                "surface": str(row.get("surface", "")),
                "path": str(row.get("path", "")),
                "verifier_command": str(row.get("verifier_command", "")),
                "bound_content_subject_hash": subject["content_subject_hash"],
                "required": bool(row.get("required", True)),
            }
        )
    normalized = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["surface"], row["path"])
        if key in seen:
            continue
        seen.add(key)
        item = dict(row)
        item["verification_row_hash"] = hash_payload(item)
        normalized.append(item)
    return normalized


def _credential_rows_bind_subject(
    rows: list[dict[str, Any]], subject: dict[str, Any], artifact_root: str
) -> bool:
    return bool(rows) and all(
        row.get("bound_output_hash") == subject["output_hash"]
        and row.get("bound_rendered_output_hash") == subject["rendered_output_hash"]
        and row.get("bound_content_subject_hash") == subject["content_subject_hash"]
        and row.get("bound_universal_invocation_witness_hash")
        == subject["universal_invocation_witness_hash"]
        and row.get("bound_source_root") == subject["source_root"]
        and row.get("bound_payout_root") == subject["payout_root"]
        and row.get("bound_provider_invocation_root")
        == subject["provider_invocation_root"]
        and row.get("bound_artifact_root") == artifact_root
        and row.get("verified") is True
        for row in rows
    )


def _durable_signals_cover_content(rows: list[dict[str, Any]], subject: dict[str, Any]) -> bool:
    signal_types = {str(row.get("signal_type", "")) for row in rows}
    has_durable_provenance = bool(
        {"content_credential", "watermark_commitment", "fingerprint_registry"}
        <= signal_types
    )
    has_visible_footer = "rdllm_visible_source_footer" in signal_types
    confidence_ok = True
    for row in rows:
        try:
            confidence_ok = confidence_ok and Decimal(
                str(row.get("confidence", "0"))
            ) >= Decimal("0.500000")
        except InvalidOperation:
            confidence_ok = False
    return (
        has_durable_provenance
        and has_visible_footer
        and all(row.get("signal_present") is True for row in rows)
        and all(row.get("bound_output_hash") == subject["output_hash"] for row in rows)
        and all(
            row.get("bound_content_subject_hash") == subject["content_subject_hash"]
            for row in rows
        )
        and confidence_ok
    )


def make_universal_content_credential(
    credential_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a portable content credential binding attribution, payout, and provenance."""

    artifact_bindings = _artifact_bindings(credential_input)
    subject = _content_subject(credential_input)
    source_rows = _source_attribution_rows(credential_input)
    payout_rows = _payout_rows(credential_input)
    provider_rows = _provider_invocation_rows(credential_input)
    credential_rows = _output_credential_rows(
        credential_input,
        subject,
        artifact_bindings,
        signing_secret=signing_secret,
    )
    signal_rows = _durable_signal_rows(credential_input, subject)
    verification_rows = _public_verification_rows(credential_input, subject)
    certification = credential_input.get("certification_report", {}).get("summary", {})
    response_summary = credential_input.get("response_envelope", {}).get("summary", {})
    output_summary = credential_input.get("output_provenance_binding_report", {}).get(
        "summary", {}
    )
    witness_summary = credential_input.get("universal_invocation_witness", {}).get(
        "summary", {}
    )
    discovery_summary = credential_input.get("discovery_manifest", {}).get("summary", {})
    source_work_ids = {(row["creator_id"], row["work_id"]) for row in source_rows}
    payout_work_ids = {(row["creator_id"], row["work_id"]) for row in payout_rows}
    private_findings = _contains_private_fields(
        {
            "content_subject": subject,
            "source_attribution_rows": source_rows,
            "payout_eligibility_rows": payout_rows,
            "provider_invocation_rows": provider_rows,
            "output_credential_rows": credential_rows,
            "durable_signal_rows": signal_rows,
            "public_verification_rows": verification_rows,
        }
    )
    checks = {
        "certification_level_at_least_l135": (
            certification.get("status") == "passed"
            and _level_number(str(certification.get("highest_level", ""))) >= 135
        ),
        "response_envelope_verified": response_summary.get("status") == "verified",
        "output_provenance_binding_ready": output_summary.get("status") == "ready",
        "universal_invocation_witness_ready": (
            witness_summary.get("status") == "ready"
            and witness_summary.get("nonrepudiation_complete") is True
            and _level_number(str(witness_summary.get("target_certification_level", "")))
            >= 135
        ),
        "discovery_manifest_publishes_l135_or_better": (
            discovery_summary.get("status") == "ready"
            and _level_number(str(discovery_summary.get("highest_level", ""))) >= 135
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "sources_bound_to_visible_footer": bool(source_rows)
        and all(row["footer_row_hash"] for row in source_rows)
        and all(row["answer_card_source_hash"] for row in source_rows),
        "evidence_preview_locator_and_url_health_bound": bool(source_rows)
        and all(row["source_preview_row_hash"] for row in source_rows)
        and all(row["evidence_locator_row_hash"] for row in source_rows)
        and all(row["citation_url_health_row_hash"] for row in source_rows),
        "payout_rows_cover_sources": bool(payout_rows)
        and source_work_ids <= payout_work_ids,
        "provider_invocations_are_nonrepudiable": bool(provider_rows)
        and all(row["nonrepudiation_complete"] for row in provider_rows)
        and all(row["provider_receipt_hash"] for row in provider_rows)
        and all(row["egress_event_bound"] for row in provider_rows)
        and all(row["independent_witness_count"] >= 2 for row in provider_rows),
        "content_credentials_bind_subject": _credential_rows_bind_subject(
            credential_rows, subject, artifact_bindings["artifact_binding_root"]
        ),
        "durable_signals_cover_content": _durable_signals_cover_content(
            signal_rows, subject
        ),
        "public_verification_surfaces_present": (
            len(verification_rows) >= 3
            and all(row["required"] for row in verification_rows[:3])
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    ready = all(checks.values())
    report: dict[str, Any] = {
        "credential_version": UNIVERSAL_CONTENT_CREDENTIAL_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "credential_policy": {
            "profile": "rdllm-universal-content-credential-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "required_bindings": [
                "content_credential_assertion",
                "durable_watermark_or_fingerprint_signal",
                "visible_source_footer",
                "creator_payout_rows",
                "universal_invocation_witness",
                "public_verification_surface",
            ],
            "compatible_with": [
                "c2pa-content-credentials",
                "scitt-statement-subjects",
                "w3c-verifiable-credentials",
                "prov-o-provenance-graphs",
                "provider-watermark-detectors",
            ],
            "raw_prompt_output_source_or_payment_text_must_not_be_embedded": True,
        },
        "artifact_bindings": artifact_bindings,
        "content_subject": subject,
        "source_attribution_rows": source_rows,
        "payout_eligibility_rows": payout_rows,
        "provider_invocation_rows": provider_rows,
        "output_credential_rows": credential_rows,
        "durable_signal_rows": signal_rows,
        "public_verification_rows": verification_rows,
        "commitments": {
            "content_subject_hash": subject["content_subject_hash"],
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "source_root": subject["source_root"],
            "payout_root": subject["payout_root"],
            "provider_invocation_root": subject["provider_invocation_root"],
            "output_credential_root": merkle_root(
                [row["credential_row_hash"] for row in credential_rows]
            ),
            "durable_signal_root": merkle_root(
                [row["signal_row_hash"] for row in signal_rows]
            ),
            "public_verification_root": merkle_root(
                [row["verification_row_hash"] for row in verification_rows]
            ),
        },
        "checks": checks,
        "credential_decision": {
            "decision": "publish_universal_content_credential"
            if ready
            else "block_universal_content_credential",
            "failure_modes": [
                name for name, passed in checks.items() if passed is not True
            ],
            "all_required_bindings_present": ready,
        },
        "schemas": {
            "universal_content_credential": UNIVERSAL_CONTENT_CREDENTIAL_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "answer_provenance_card": "docs/schemas/answer_provenance_card.schema.json",
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "output_provenance_binding_report": "docs/schemas/output_provenance_binding_report.schema.json",
            "universal_invocation_witness": "docs/schemas/universal_invocation_witness.schema.json",
            "royalty_statement": "docs/schemas/royalty_statement.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "content_subject_hash": subject["content_subject_hash"],
            "output_hash": subject["output_hash"],
            "source_count": len(source_rows),
            "payout_row_count": len(payout_rows),
            "provider_invocation_count": len(provider_rows),
            "credential_count": len(credential_rows),
            "durable_signal_count": len(signal_rows),
            "public_verification_surface_count": len(verification_rows),
            "failed_check_count": sum(1 for passed in checks.values() if not passed),
            "artifact_count": artifact_bindings["artifact_count"],
            "offline_verification_supported": True,
            "raw_prompt_output_source_or_payment_text_disclosed": False,
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_output_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "private_payment_details_disclosed": False,
            "credential_uses_hashes_footers_public_status_and_verifier_paths": True,
            "private_field_findings": private_findings,
        },
    }
    report["universal_content_credential_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_content_credential_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "credential_version",
        "issuer",
        "created_at",
        "credential_policy",
        "artifact_bindings",
        "content_subject",
        "source_attribution_rows",
        "payout_eligibility_rows",
        "provider_invocation_rows",
        "output_credential_rows",
        "durable_signal_rows",
        "public_verification_rows",
        "commitments",
        "checks",
        "credential_decision",
        "schemas",
        "summary",
        "privacy",
        "universal_content_credential_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal content credential field: {key}")
    if errors:
        return errors
    if report.get("credential_version") != UNIVERSAL_CONTENT_CREDENTIAL_VERSION:
        errors.append("universal content credential version is unsupported")
    if (
        report.get("schemas", {}).get("universal_content_credential")
        != UNIVERSAL_CONTENT_CREDENTIAL_SCHEMA
    ):
        errors.append("universal content credential schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal content credential target level is not RDLLM-L136")
    for finding in _contains_private_fields(report):
        errors.append(f"universal content credential contains private field: {finding}")
    return errors


def verify_universal_content_credential(
    report: dict[str, Any],
    *,
    credential_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L136 content credential against replay inputs."""

    errors = validate_universal_content_credential_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_content_credential_hash"):
        errors.append("universal content credential hash is not reproducible")

    expected = make_universal_content_credential(
        credential_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "credential_policy",
        "artifact_bindings",
        "content_subject",
        "source_attribution_rows",
        "payout_eligibility_rows",
        "provider_invocation_rows",
        "output_credential_rows",
        "durable_signal_rows",
        "public_verification_rows",
        "commitments",
        "checks",
        "credential_decision",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal content credential {key} does not match replay")
    if expected.get("universal_content_credential_hash") != report.get(
        "universal_content_credential_hash"
    ):
        errors.append("universal content credential hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal content credential status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal content credential check failed: {check}")

    if not _private_strings_absent(report, credential_input):
        errors.append("universal content credential leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal content credential is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal content credential signature is invalid")

    return errors
