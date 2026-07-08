"""Delivery receipts for grounded source footers.

This layer proves that a grounded source footer did not remain an offline audit
artifact. It binds the L102 footer receipt to the response envelope, proof-
carrying response, serving gateway, and delivery metadata that a client can
verify before rendering or relaying the answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.proof_carrying_response import verify_proof_carrying_response
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.response_envelope import verify_response_envelope
from rdllm.serving_gateway import verify_serving_gateway_report
from rdllm.text import stable_hash

SOURCE_FOOTER_DELIVERY_VERSION = "rdllm-source-footer-delivery/v1"
SOURCE_FOOTER_DELIVERY_SCHEMA = (
    "docs/schemas/source_footer_delivery.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L103"

DECLARED_HASH_FIELDS = (
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "envelope_hash",
    "contract_hash",
    "report_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "raw_license_token",
    "license_server_secret",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_source_footer_delivery_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a source footer delivery receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"source_footer_delivery_hash", "signature"}
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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(report: dict[str, Any], receipt_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _artifact_bindings(receipt_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "grounded_source_footer": receipt_input.get("grounded_source_footer"),
        "response_envelope": receipt_input.get("response_envelope"),
        "proof_carrying_response": receipt_input.get("proof_carrying_response"),
        "serving_gateway_report": receipt_input.get("serving_gateway_report"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(
            artifact
        )
    grounded = receipt_input.get("grounded_source_footer", {})
    bindings["grounded_footer_contract_hash"] = grounded.get(
        "artifact_bindings", {}
    ).get("citation_footer_contract_hash", "")
    bindings["grounded_footer_source_confidence_hash"] = grounded.get(
        "artifact_bindings", {}
    ).get("source_confidence_report_hash", "")
    bindings["grounded_footer_source_availability_hash"] = grounded.get(
        "artifact_bindings", {}
    ).get("source_availability_report_hash", "")
    bindings["response_envelope_citation_footer_contract_hash"] = receipt_input.get(
        "response_envelope", {}
    ).get("commitments", {}).get("citation_footer_contract_hash", "")
    bindings["response_envelope_source_confidence_hash"] = receipt_input.get(
        "response_envelope", {}
    ).get("commitments", {}).get("source_confidence_report_hash", "")
    bindings["response_envelope_source_availability_hash"] = receipt_input.get(
        "response_envelope", {}
    ).get("commitments", {}).get("source_availability_report_hash", "")
    return bindings


def _rendered_output(receipt_input: dict[str, Any]) -> str:
    envelope = receipt_input.get("response_envelope", {})
    return str(envelope.get("response", {}).get("rendered_output", ""))


def _copied_output(receipt_input: dict[str, Any]) -> str:
    proof = receipt_input.get("proof_carrying_response", {})
    return str(proof.get("display", {}).get("copied_output", ""))


def _delivered_output(receipt_input: dict[str, Any]) -> str:
    return str(receipt_input.get("delivered_output") or _copied_output(receipt_input))


def _source_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    grounded = receipt_input.get("grounded_source_footer", {})
    rendered = _rendered_output(receipt_input)
    delivered = _delivered_output(receipt_input)
    rows = []
    for row in grounded.get("footer_rows", []):
        label = str(row.get("label", ""))
        display_label = str(row.get("display_label", f"[{label}]"))
        source_uri = str(row.get("source_uri", ""))
        title = str(row.get("title", ""))
        public = {
            "display_order": int(row.get("display_order", 0) or 0),
            "label": label,
            "display_label": display_label,
            "title": title,
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": source_uri,
            "footer_row_hash": str(row.get("footer_row_hash", "")),
            "proof_row_hash": "",
            "label_visible_in_rendered_output": bool(
                label and (display_label in rendered or f"[{label}]" in rendered)
            ),
            "title_visible_in_rendered_output": bool(title and title in rendered),
            "uri_visible_in_rendered_output": bool(source_uri and source_uri in rendered),
            "label_visible_in_delivered_output": bool(
                label and (display_label in delivered or f"[{label}]" in delivered)
            ),
            "claim_count": int(row.get("supported_claim_count", 0) or 0),
            "source_confidence_verified": row.get("source_confidence_verified") is True,
            "source_available": row.get("source_available") is True,
            "citation_reliance_covered": row.get("citation_reliance_covered") is True,
            "license_transaction_covered": row.get(
                "license_transaction_covered"
            )
            is True,
            "source_rationale": row.get("source_rationale", {}),
            "source_rationale_hash": str(row.get("source_rationale_hash", "")),
        }
        for proof_row in grounded.get("proof_rows", []):
            if str(proof_row.get("label", "")) == label:
                public["proof_row_hash"] = str(proof_row.get("proof_row_hash", ""))
                break
        public["source_delivery_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _claim_rows(receipt_input: dict[str, Any]) -> list[dict[str, Any]]:
    grounded = receipt_input.get("grounded_source_footer", {})
    rendered = _rendered_output(receipt_input)
    delivered = _delivered_output(receipt_input)
    rows = []
    for row in grounded.get("claim_rows", []):
        source_label = str(row.get("source_label", ""))
        span = str(row.get("evidence_span_prefix", ""))
        display_anchor = str(row.get("display_anchor", ""))
        public = {
            "claim_index": int(row.get("claim_index", 0) or 0),
            "claim_hash": str(row.get("claim_hash", "")),
            "source_label": source_label,
            "display_anchor": display_anchor,
            "evidence_span_prefix": span,
            "region_id": str(row.get("region_id", "")),
            "region_hash": str(row.get("region_hash", "")),
            "claim_footer_row_hash": str(row.get("claim_footer_row_hash", "")),
            "span_visible_in_rendered_output": bool(span and span in rendered),
            "span_visible_in_delivered_output": bool(span and span in delivered),
            "display_anchor_or_label_visible": bool(
                (display_anchor and display_anchor in rendered)
                or (source_label and f"[{source_label}]" in rendered)
            ),
            "public_region_bound": bool(
                row.get("region_verified") is True
                and row.get("public_location") is True
                and row.get("location_hash")
            ),
        }
        public["claim_delivery_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _delivery_metadata(
    *,
    grounded_source_footer: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    metadata = {
        "profile": "rdllm-grounded-source-footer-delivery/v1",
        "grounded_source_footer_hash": grounded_source_footer.get(
            "grounded_source_footer_hash", ""
        ),
        "source_footer_delivery_well_known_path": (
            "/.well-known/rdllm/source-footer-delivery.json"
        ),
        "grounded_source_footer_well_known_path": (
            "/.well-known/rdllm/grounded-source-footer.json"
        ),
        "verifier_command": "verify-source-footer-delivery",
        "grounded_footer_verifier_command": "verify-grounded-source-footer",
        "proof_response_hash": proof_carrying_response.get("proof_response_hash", ""),
        "gateway_report_hash": serving_gateway_report.get("gateway_report_hash", ""),
        "delivered_output_hash": serving_gateway_report.get("egress", {}).get(
            "delivered_output_hash", ""
        ),
        "source_label_order": [row["label"] for row in source_rows],
        "source_delivery_row_hashes": [
            row["source_delivery_row_hash"] for row in source_rows
        ],
        "source_rationale_hashes": [
            row["source_rationale_hash"] for row in source_rows
        ],
        "claim_delivery_row_hashes": [
            row["claim_delivery_row_hash"] for row in claim_rows
        ],
        "proof_row_hashes": [
            row.get("proof_row_hash", "") for row in grounded_source_footer.get("proof_rows", [])
        ],
    }
    metadata["metadata_hash"] = hash_payload(metadata)
    return metadata


def _checks(
    *,
    receipt_input: dict[str, Any],
    artifact_bindings: dict[str, Any],
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    delivery_metadata: dict[str, Any],
    response_errors: list[str],
    proof_errors: list[str],
    gateway_errors: list[str],
) -> dict[str, bool]:
    grounded = receipt_input.get("grounded_source_footer", {})
    envelope = receipt_input.get("response_envelope", {})
    proof = receipt_input.get("proof_carrying_response", {})
    gateway = receipt_input.get("serving_gateway_report", {})
    rendered = _rendered_output(receipt_input)
    copied = _copied_output(receipt_input)
    delivered = _delivered_output(receipt_input)
    envelope_hash = envelope.get("envelope_hash", "")
    proof_bindings = proof.get("artifact_bindings", {})
    gateway_bindings = gateway.get("artifact_bindings", {})
    egress = gateway.get("egress", {})
    envelope_labels = set(envelope.get("response", {}).get("source_labels", []))
    footer_labels = {row["label"] for row in source_rows}
    public_report = {
        "artifact_bindings": artifact_bindings,
        "source_rows": source_rows,
        "claim_rows": claim_rows,
        "delivery_metadata": delivery_metadata,
    }
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "grounded_source_footer_ready_l102": (
            grounded.get("summary", {}).get("status") == "ready"
            and grounded.get("summary", {}).get("target_certification_level")
            == "RDLLM-L102"
            and int(grounded.get("summary", {}).get("failed_check_count", 1))
            == 0
        ),
        "response_envelope_verified": not response_errors,
        "proof_carrying_response_verified": not proof_errors,
        "serving_gateway_verified": not gateway_errors,
        "proof_response_embeds_response_envelope": (
            proof_bindings.get("response_envelope_hash") == envelope_hash
        ),
        "gateway_served_proof_response": (
            gateway_bindings.get("proof_response_hash")
            == proof.get("proof_response_hash", "")
            and gateway.get("summary", {}).get("status") == "served"
            and gateway.get("summary", {}).get("release_decision") == "emit"
        ),
        "delivered_output_matches_gateway": (
            stable_hash(delivered) == egress.get("delivered_output_hash", "")
            and egress.get("delivered_output_hash")
            == proof.get("display", {}).get("copied_output_hash", "")
        ),
        "rendered_output_matches_envelope": (
            stable_hash(rendered)
            == envelope.get("response", {}).get("rendered_output_hash", "")
        ),
        "copied_output_contains_rendered_answer": bool(rendered and rendered in copied),
        "delivered_output_contains_copied_output": bool(copied and delivered == copied),
        "grounded_footer_matches_response_contract": (
            artifact_bindings.get("grounded_footer_contract_hash")
            == artifact_bindings.get("response_envelope_citation_footer_contract_hash")
            and artifact_bindings.get("grounded_footer_source_confidence_hash")
            == artifact_bindings.get("response_envelope_source_confidence_hash")
            and artifact_bindings.get("grounded_footer_source_availability_hash")
            == artifact_bindings.get("response_envelope_source_availability_hash")
        ),
        "all_grounded_sources_visible_in_rendered_output": bool(source_rows)
        and all(
            row["label_visible_in_rendered_output"]
            and row["title_visible_in_rendered_output"]
            and row["uri_visible_in_rendered_output"]
            for row in source_rows
        ),
        "all_grounded_sources_visible_in_delivered_output": bool(source_rows)
        and all(row["label_visible_in_delivered_output"] for row in source_rows),
        "all_grounded_claim_spans_visible": bool(claim_rows)
        and all(
            row["span_visible_in_rendered_output"]
            and row["span_visible_in_delivered_output"]
            and row["display_anchor_or_label_visible"]
            and row["public_region_bound"]
            for row in claim_rows
        ),
        "response_source_labels_match_grounded_footer": bool(footer_labels)
        and envelope_labels == footer_labels,
        "delivery_metadata_contains_verifier_handles": (
            delivery_metadata.get("grounded_source_footer_hash")
            == grounded.get("grounded_source_footer_hash", "")
            and delivery_metadata.get("verifier_command")
            == "verify-source-footer-delivery"
            and delivery_metadata.get("grounded_source_footer_well_known_path")
            == "/.well-known/rdllm/grounded-source-footer.json"
            and all(delivery_metadata.get("proof_row_hashes", []))
        ),
        "delivery_rows_carry_source_rationale": bool(source_rows)
        and all(
            row.get("source_rationale_hash")
            and row.get("source_rationale", {}).get("reason_code")
            and row.get("source_rationale_hash")
            == row.get("source_rationale", {}).get("source_rationale_hash")
            for row in source_rows
        )
        and delivery_metadata.get("source_rationale_hashes")
        == [row["source_rationale_hash"] for row in source_rows],
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, receipt_input)
        ),
    }


def make_source_footer_delivery_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a receipt proving grounded footer delivery at the API boundary."""

    grounded = receipt_input.get("grounded_source_footer", {})
    envelope = receipt_input.get("response_envelope", {})
    proof = receipt_input.get("proof_carrying_response", {})
    gateway = receipt_input.get("serving_gateway_report", {})
    artifact_bindings = _artifact_bindings(receipt_input)
    source_rows = _source_rows(receipt_input)
    claim_rows = _claim_rows(receipt_input)
    delivery_metadata = _delivery_metadata(
        grounded_source_footer=grounded,
        proof_carrying_response=proof,
        serving_gateway_report=gateway,
        source_rows=source_rows,
        claim_rows=claim_rows,
    )
    response_errors = verify_response_envelope(envelope, signing_secret=signing_secret)
    proof_errors = verify_proof_carrying_response(proof, signing_secret=signing_secret)
    gateway_errors = verify_serving_gateway_report(
        gateway,
        delivered_output=receipt_input.get("delivered_output"),
        signing_secret=signing_secret,
    )
    checks = _checks(
        receipt_input=receipt_input,
        artifact_bindings=artifact_bindings,
        source_rows=source_rows,
        claim_rows=claim_rows,
        delivery_metadata=delivery_metadata,
        response_errors=response_errors,
        proof_errors=proof_errors,
        gateway_errors=gateway_errors,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    receipt = {
        "version": SOURCE_FOOTER_DELIVERY_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(
                receipt_input.get("case_id", "case:source-footer-delivery")
            ),
            "status": status,
        },
        "artifact_bindings": artifact_bindings,
        "delivery_subject": {
            "event_id": str(envelope.get("response", {}).get("event_id", "")),
            "event_hash": str(envelope.get("response", {}).get("event_hash", "")),
            "rendered_output_hash": str(
                envelope.get("response", {}).get("rendered_output_hash", "")
            ),
            "copied_output_hash": str(proof.get("display", {}).get("copied_output_hash", "")),
            "delivered_output_hash": str(
                gateway.get("egress", {}).get("delivered_output_hash", "")
            ),
            "grounded_source_footer_hash": str(
                grounded.get("grounded_source_footer_hash", "")
            ),
        },
        "source_delivery_rows": source_rows,
        "claim_delivery_rows": claim_rows,
        "delivery_metadata": delivery_metadata,
        "verification_errors": {
            "response_envelope_error_count": len(response_errors),
            "proof_carrying_response_error_count": len(proof_errors),
            "serving_gateway_error_count": len(gateway_errors),
        },
        "checks": checks,
        "privacy": {
            "rendered_output_text_disclosed": False,
            "copied_output_text_disclosed": False,
            "delivered_output_text_disclosed": False,
            "prompt_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_delivery_commitments": True,
        },
        "schemas": {
            "source_footer_delivery": SOURCE_FOOTER_DELIVERY_SCHEMA,
            "grounded_source_footer": "docs/schemas/grounded_source_footer.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "visible_source_count": len(source_rows),
            "delivered_source_count": sum(
                1 for row in source_rows if row["label_visible_in_delivered_output"]
            ),
            "claim_span_count": len(claim_rows),
            "delivered_claim_span_count": sum(
                1 for row in claim_rows if row["span_visible_in_delivered_output"]
            ),
            "failed_check_count": len(failed),
            "grounded_footer_delivery_enforced": not failed,
            "client_verifier_handles_present": checks[
                "delivery_metadata_contains_verifier_handles"
            ],
            "source_selection_rationale_delivered": checks[
                "delivery_rows_carry_source_rationale"
            ],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    receipt["source_footer_delivery_hash"] = hash_payload(_hashable_report(receipt))
    receipt["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(receipt), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return receipt


def validate_source_footer_delivery_shape(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "artifact_bindings",
        "delivery_subject",
        "source_delivery_rows",
        "claim_delivery_rows",
        "delivery_metadata",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "source_footer_delivery_hash",
        "signature",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing source footer delivery field: {key}")
    if receipt.get("version") != SOURCE_FOOTER_DELIVERY_VERSION:
        errors.append("source footer delivery version is unsupported")
    if "source_footer_delivery" not in receipt.get("schemas", {}):
        errors.append("missing source footer delivery schema")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source footer delivery target level is not RDLLM-L103")
    for index, row in enumerate(receipt.get("source_delivery_rows", [])):
        for key in (
            "label",
            "source_uri",
            "footer_row_hash",
            "proof_row_hash",
            "label_visible_in_rendered_output",
            "label_visible_in_delivered_output",
            "source_rationale_hash",
            "source_delivery_row_hash",
        ):
            if key not in row:
                errors.append(f"source delivery row {index} missing {key}")
    for index, row in enumerate(receipt.get("claim_delivery_rows", [])):
        for key in (
            "claim_index",
            "source_label",
            "evidence_span_prefix",
            "span_visible_in_rendered_output",
            "span_visible_in_delivered_output",
            "claim_delivery_row_hash",
        ):
            if key not in row:
                errors.append(f"claim delivery row {index} missing {key}")
    return errors


def verify_source_footer_delivery_receipt(
    receipt: dict[str, Any],
    receipt_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a source footer delivery receipt by replaying its public inputs."""

    errors = validate_source_footer_delivery_shape(receipt)
    expected = make_source_footer_delivery_receipt(
        receipt_input,
        issuer=str(receipt.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(receipt.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "artifact_bindings",
        "delivery_subject",
        "source_delivery_rows",
        "claim_delivery_rows",
        "delivery_metadata",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if receipt.get(key) != expected.get(key):
            errors.append(f"source footer delivery {key} mismatch")
    if receipt.get("source_footer_delivery_hash") != expected.get(
        "source_footer_delivery_hash"
    ):
        errors.append("source footer delivery hash mismatch")
    if receipt.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("source footer delivery signature mismatch")
    if any(value is not True for value in receipt.get("checks", {}).values()):
        errors.append("source footer delivery has failing checks")
    return errors
