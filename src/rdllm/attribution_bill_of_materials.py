"""Attribution Bill of Materials for model and proof supply chains.

This layer packages RDLLM's proof stack as a CycloneDX-aligned AI bill of
materials. It is intentionally not another payout formula: it is the portable
model-release artifact that preserves source notices, licenses, proof hashes, and
post-training provenance across model, dataset, API, and downstream application
boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.proof_dependency_graph import verify_proof_dependency_graph
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

ATTRIBUTION_BOM_VERSION = "rdllm-attribution-bom/v1"
ATTRIBUTION_BOM_SCHEMA = "docs/schemas/attribution_bom.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L109"
MINIMUM_CERTIFICATION_LEVEL = "RDLLM-L108"

DECLARED_HASH_FIELDS = (
    "attribution_bom_hash",
    "post_training_signal_provenance_hash",
    "private_reasoning_attribution_hash",
    "persistent_memory_provenance_hash",
    "protocol_ingestion_report_hash",
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "attested_runtime_hash",
    "post_release_report_hash",
    "binding_report_hash",
    "watchtower_report_hash",
    "graph_hash",
    "attestation_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "contract_hash",
    "receipt_hash",
    "trace_hash",
    "statement_hash",
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
    "notice_text",
    "license_text",
    "preference_text",
    "feedback_text",
    "critique_text",
    "reward_explanation_text",
    "verifier_rationale",
    "chain_of_thought",
    "reasoning_text",
    "private_reasoning_text",
    "scratchpad",
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


def load_attribution_bom_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an attribution bill of materials."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _level_number(level: str) -> int:
    try:
        return int(str(level).rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_bom(bom: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in bom.items()
        if key not in {"attribution_bom_hash", "signature"}
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
        return True
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


def _private_strings_absent(bom: dict[str, Any], bom_input: dict[str, Any]) -> bool:
    public_json = canonical_json(bom)
    private_strings = [
        str(item)
        for item in bom_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _component_hash(component: dict[str, Any]) -> str:
    hashes = component.get("hashes", [])
    if isinstance(hashes, list):
        for row in hashes:
            if isinstance(row, dict) and row.get("content"):
                return str(row["content"])
    return str(component.get("hash", ""))


def _source_labels_from_model_lineage(report: dict[str, Any] | None) -> set[str]:
    if not report:
        return set()
    return {
        str(source.get("source_label", ""))
        for item in report.get("training_items", [])
        for source in item.get("source_rows", [])
        if source.get("source_label")
    }


def _source_labels_from_post_training(receipt: dict[str, Any] | None) -> set[str]:
    if not receipt:
        return set()
    return {
        str(label)
        for signal in receipt.get("post_training_signals", [])
        for label in signal.get("source_labels", [])
        if label
    }


def _artifact_components(bom_input: dict[str, Any]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for row in sorted(
        bom_input.get("proof_artifacts", []),
        key=lambda item: str(item.get("name", "")),
    ):
        name = str(row.get("name", "artifact"))
        payload = row.get("payload")
        declared_hash = str(row.get("artifact_hash") or _declared_hash(payload))
        component = {
            "bom-ref": str(row.get("bom_ref", f"rdllm:artifact:{name}")),
            "type": "file",
            "name": name,
            "version": str(row.get("version", "1")),
            "scope": "required",
            "hashes": [{"alg": "SHA-256", "content": declared_hash}],
            "externalReferences": [
                ref
                for ref in [
                    {
                        "type": "distribution",
                        "url": str(row.get("well_known_path", "")),
                    }
                ]
                if ref["url"]
            ],
            "properties": [
                {"name": "rdllm:artifact_type", "value": str(row.get("artifact_type", ""))},
                {"name": "rdllm:schema", "value": str(row.get("schema", ""))},
            ],
        }
        components.append(component)
    return components


def _source_components(bom_input: dict[str, Any]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for source in sorted(
        bom_input.get("source_components", []),
        key=lambda item: (
            str(item.get("source_label", "")),
            str(item.get("work_id", "")),
            str(item.get("chunk_id", "")),
        ),
    ):
        label = str(source.get("source_label", ""))
        work_id = str(source.get("work_id", ""))
        chunk_id = str(source.get("chunk_id", ""))
        if source.get("notice_hash"):
            notice_hash = str(source["notice_hash"])
        elif source.get("notice_text"):
            notice_hash = hash_payload(str(source["notice_text"]))
        else:
            notice_hash = ""
        license_terms_hash = str(source.get("license_terms_hash", ""))
        content_hash = str(source.get("content_hash", ""))
        component = {
            "bom-ref": str(
                source.get("bom_ref", f"rdllm:source:{label}:{work_id}:{chunk_id}")
            ),
            "type": "data",
            "name": str(source.get("name", f"{label}:{work_id}")),
            "version": str(source.get("version", chunk_id or "1")),
            "scope": "required",
            "hashes": [{"alg": "SHA-256", "content": content_hash}],
            "licenses": [
                {
                    "license": {
                        "id": str(source.get("license_id", "LicenseRef-RDLLM")),
                        "url": str(source.get("license_url", "")),
                    }
                }
            ],
            "properties": [
                {"name": "rdllm:source_label", "value": label},
                {"name": "rdllm:creator_id", "value": str(source.get("creator_id", ""))},
                {"name": "rdllm:work_id", "value": work_id},
                {"name": "rdllm:chunk_id", "value": chunk_id},
                {"name": "rdllm:content_hash", "value": content_hash},
                {"name": "rdllm:license_terms_hash", "value": license_terms_hash},
                {"name": "rdllm:notice_hash", "value": notice_hash},
                {
                    "name": "rdllm:settlement_state",
                    "value": str(source.get("settlement_state", "direct")),
                },
                {
                    "name": "rdllm:royalty_basis",
                    "value": str(source.get("royalty_basis", "attribution_bom_source")),
                },
            ],
        }
        components.append(component)
    return components


def _model_component(bom_input: dict[str, Any]) -> dict[str, Any]:
    model = bom_input.get("model", {})
    model_hash = str(model.get("model_hash") or hash_payload(model))
    return {
        "bom-ref": str(model.get("bom_ref", "rdllm:model:subject")),
        "type": "machine-learning-model",
        "name": str(model.get("model_id", "model:unspecified")),
        "version": str(model.get("model_version", "unknown")),
        "publisher": str(model.get("provider", bom_input.get("producer", {}).get("provider", ""))),
        "hashes": [{"alg": "SHA-256", "content": model_hash}],
        "properties": [
            {"name": "rdllm:base_model_id", "value": str(model.get("base_model_id", ""))},
            {
                "name": "rdllm:minimum_certification_level",
                "value": MINIMUM_CERTIFICATION_LEVEL,
            },
        ],
    }


def _component_refs(components: list[dict[str, Any]], component_type: str | None = None) -> list[str]:
    refs: list[str] = []
    for component in components:
        if component_type is None or component.get("type") == component_type:
            ref = component.get("bom-ref")
            if ref:
                refs.append(str(ref))
    return sorted(refs)


def _dependencies(model_ref: str, source_refs: list[str], artifact_refs: list[str]) -> list[dict[str, Any]]:
    rows = [{"ref": model_ref, "dependsOn": sorted(set(source_refs + artifact_refs))}]
    rows.extend({"ref": ref, "dependsOn": []} for ref in sorted(source_refs + artifact_refs))
    return rows


def _notice_rows(source_components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for component in source_components:
        props = {
            prop["name"]: prop["value"]
            for prop in component.get("properties", [])
            if isinstance(prop, dict)
        }
        rows.append(
            {
                "source_label": props.get("rdllm:source_label", ""),
                "creator_id": props.get("rdllm:creator_id", ""),
                "work_id": props.get("rdllm:work_id", ""),
                "license_terms_hash": props.get("rdllm:license_terms_hash", ""),
                "notice_hash": props.get("rdllm:notice_hash", ""),
                "notice_text_disclosed": False,
                "license_text_disclosed": False,
            }
        )
    return rows


def _artifact_bindings(bom_input: dict[str, Any]) -> dict[str, Any]:
    named_artifacts: dict[str, Any] = {
        "certification_report": bom_input.get("certification_report"),
        "provider_attribution_card": bom_input.get("provider_attribution_card"),
        "proof_dependency_graph": bom_input.get("proof_dependency_graph"),
        "post_training_signal_provenance": bom_input.get("post_training_signal_provenance"),
        "model_lineage_attribution_report": bom_input.get("model_lineage_attribution_report"),
        "creator_license_contract": bom_input.get("creator_license_contract"),
        "training_content_summary": bom_input.get("training_content_summary"),
    }
    return {
        name: {
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        }
        for name, artifact in named_artifacts.items()
        if artifact
    }


def _base_checks(
    *,
    bom_input: dict[str, Any],
    components: list[dict[str, Any]],
    source_components: list[dict[str, Any]],
    artifact_components: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    notice_rows: list[dict[str, Any]],
    artifact_bindings: dict[str, Any],
    proof_graph_errors: list[str],
) -> dict[str, bool]:
    certification = bom_input.get("certification_report", {})
    certification_summary = certification.get("summary", {})
    provider_card = bom_input.get("provider_attribution_card", {})
    proof_graph = bom_input.get("proof_dependency_graph", {})
    post_training = bom_input.get("post_training_signal_provenance", {})
    model_lineage = bom_input.get("model_lineage_attribution_report", {})
    source_labels = {
        prop.get("value", "")
        for component in source_components
        for prop in component.get("properties", [])
        if prop.get("name") == "rdllm:source_label" and prop.get("value")
    }
    required_source_labels = (
        _source_labels_from_model_lineage(model_lineage)
        | _source_labels_from_post_training(post_training)
    )
    model_ref = str(bom_input.get("model", {}).get("bom_ref", "rdllm:model:subject"))
    dependency_row = next((row for row in dependencies if row["ref"] == model_ref), {})
    dependency_refs = set(dependency_row.get("dependsOn", []))
    source_refs = set(_component_refs(source_components))
    artifact_refs = set(_component_refs(artifact_components))

    return {
        "cyclonedx_required_fields_present": bool(components)
        and all(component.get("bom-ref") and component.get("type") and component.get("name") for component in components),
        "certification_report_verified_l108_or_higher": certification_summary.get("status") == "passed"
        and _level_number(str(certification_summary.get("highest_level", ""))) >= 108,
        "provider_card_declares_attribution_bom_inputs": provider_card.get("certification", {}).get("highest_level") == certification_summary.get("highest_level")
        and provider_card.get("supported_evidence_channels", {}).get("post_training_signal_provenance") is True
        and provider_card.get("supported_evidence_channels", {}).get("proof_dependency_graph") is True
        and provider_card.get("supported_evidence_channels", {}).get("attribution_bom") is True,
        "proof_dependency_graph_verified": bool(proof_graph)
        and not proof_graph_errors
        and _artifact_hash_is_reproducible(proof_graph)
        and proof_graph.get("summary", {}).get("status") == "ready"
        and _level_number(str(proof_graph.get("summary", {}).get("target_certification_level", ""))) >= 108,
        "source_components_have_notice_and_license_hashes": bool(source_components)
        and all(row["notice_hash"] and row["license_terms_hash"] for row in notice_rows),
        "source_components_cover_training_and_post_training_labels": bool(required_source_labels)
        and required_source_labels.issubset(source_labels),
        "proof_artifact_components_have_reproducible_hashes": bool(artifact_components)
        and all(_component_hash(component) for component in artifact_components)
        and all(row["hash_reproducible"] for row in artifact_bindings.values()),
        "dependencies_bind_model_to_sources_and_proofs": source_refs.issubset(dependency_refs)
        and artifact_refs.issubset(dependency_refs),
        "post_training_signal_provenance_bound": bool(post_training)
        and post_training.get("summary", {}).get("target_certification_level") == "RDLLM-L108"
        and post_training.get("summary", {}).get("status") == "ready",
        "notices_and_private_text_not_disclosed": not _contains_private_fields(
            bom_input.get("public_overrides", {})
        ),
    }


def make_attribution_bill_of_materials(
    bom_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed attribution bill of materials."""

    issued_at = issued_at or now_iso()
    proof_graph_errors: list[str] = []
    if bom_input.get("proof_dependency_graph") and bom_input.get("proof_graph_replay_artifacts"):
        proof_graph_errors = verify_proof_dependency_graph(
            bom_input.get("proof_dependency_graph", {}),
            [
                (
                    str(row.get("name", "")),
                    str(row.get("artifact_type", "")),
                    row.get("payload", {}),
                )
                for row in bom_input.get("proof_graph_replay_artifacts", [])
                if isinstance(row.get("payload"), dict)
            ],
            signing_secret=signing_secret,
        )
    model_component = _model_component(bom_input)
    source_components = _source_components(bom_input)
    artifact_components = _artifact_components(bom_input)
    components = [model_component, *source_components, *artifact_components]
    dependencies = _dependencies(
        str(model_component["bom-ref"]),
        _component_refs(source_components),
        _component_refs(artifact_components),
    )
    notice_rows = _notice_rows(source_components)
    artifact_bindings = _artifact_bindings(bom_input)
    checks = _base_checks(
        bom_input=bom_input,
        components=components,
        source_components=source_components,
        artifact_components=artifact_components,
        dependencies=dependencies,
        notice_rows=notice_rows,
        artifact_bindings=artifact_bindings,
        proof_graph_errors=proof_graph_errors,
    )

    failed_check_count = sum(1 for value in checks.values() if value is not True)
    bom: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": str(
            bom_input.get("serial_number", f"urn:rdllm:attribution-bom:{hash_payload(components)[:16]}")
        ),
        "version": ATTRIBUTION_BOM_VERSION,
        "issued_at": issued_at,
        "issuer": issuer,
        "metadata": {
            "timestamp": issued_at,
            "component": model_component,
            "supplier": {
                "name": str(bom_input.get("producer", {}).get("provider", issuer)),
            },
            "properties": [
                {"name": "rdllm:target_certification_level", "value": TARGET_CERTIFICATION_LEVEL},
                {"name": "rdllm:minimum_certification_level", "value": MINIMUM_CERTIFICATION_LEVEL},
                {
                    "name": "rdllm:certification_report_hash",
                    "value": _declared_hash(bom_input.get("certification_report")),
                },
                {
                    "name": "rdllm:proof_dependency_graph_hash",
                    "value": _declared_hash(bom_input.get("proof_dependency_graph")),
                },
            ],
        },
        "components": components,
        "dependencies": dependencies,
        "rdllm": {
            "case_id": str(bom_input.get("case_id", "case:attribution-bom")),
            "artifact_bindings": artifact_bindings,
            "notice_carry_forward": {
                "notice_rows": notice_rows,
                "notice_root": hash_payload(notice_rows),
                "notice_text_disclosed": False,
                "license_text_disclosed": False,
            },
            "verification_errors": {
                "proof_dependency_graph": len(proof_graph_errors),
            },
            "checks": checks,
            "privacy": {
                "raw_prompt_disclosed": False,
                "raw_output_disclosed": False,
                "source_text_disclosed": False,
                "notice_text_disclosed": False,
                "license_text_disclosed": False,
                "feedback_text_disclosed": False,
                "payment_data_disclosed": False,
                "bom_uses_hashes_labels_and_references": True,
            },
            "schemas": {
                "attribution_bom": ATTRIBUTION_BOM_SCHEMA,
                "post_training_signal_provenance": "docs/schemas/post_training_signal_provenance.schema.json",
                "proof_dependency_graph": "docs/schemas/proof_dependency_graph.schema.json",
            },
        },
        "summary": {
            "status": "ready" if failed_check_count == 0 else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_certification_level": MINIMUM_CERTIFICATION_LEVEL,
            "component_count": len(components),
            "source_component_count": len(source_components),
            "proof_artifact_component_count": len(artifact_components),
            "notice_row_count": len(notice_rows),
            "failed_check_count": failed_check_count,
            "attribution_bom_ready": failed_check_count == 0,
            "privacy_preserved": checks["notices_and_private_text_not_disclosed"],
        },
    }
    checks["notices_and_private_text_not_disclosed"] = (
        checks["notices_and_private_text_not_disclosed"]
        and _private_strings_absent(bom, bom_input)
    )
    failed_check_count = sum(1 for value in checks.values() if value is not True)
    bom["summary"]["status"] = "ready" if failed_check_count == 0 else "blocked"
    bom["summary"]["failed_check_count"] = failed_check_count
    bom["summary"]["attribution_bom_ready"] = failed_check_count == 0
    bom["summary"]["privacy_preserved"] = checks["notices_and_private_text_not_disclosed"]
    bom["attribution_bom_hash"] = hash_payload(_hashable_bom(bom))
    bom["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_bom(bom), signing_secret) if signing_secret else ""
        ),
    }
    return bom


def validate_attribution_bill_of_materials_shape(bom: dict[str, Any]) -> list[str]:
    """Validate the public shape of an attribution bill of materials."""

    errors: list[str] = []
    required = (
        "bomFormat",
        "specVersion",
        "serialNumber",
        "version",
        "issued_at",
        "issuer",
        "metadata",
        "components",
        "dependencies",
        "rdllm",
        "summary",
        "attribution_bom_hash",
        "signature",
    )
    for key in required:
        if key not in bom:
            errors.append(f"missing attribution BOM field: {key}")
    if errors:
        return errors
    if bom.get("bomFormat") != "CycloneDX":
        errors.append("attribution BOM is not CycloneDX formatted")
    if bom.get("specVersion") != "1.7":
        errors.append("attribution BOM specVersion is not 1.7")
    if bom.get("version") != ATTRIBUTION_BOM_VERSION:
        errors.append("attribution BOM version is unsupported")
    if bom.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("attribution BOM target level is not RDLLM-L109")
    if "attribution_bom" not in bom.get("rdllm", {}).get("schemas", {}):
        errors.append("missing attribution BOM schema")
    if not isinstance(bom.get("components"), list) or not bom["components"]:
        errors.append("attribution BOM components must be a non-empty list")
    if _contains_private_fields(bom):
        errors.append("attribution BOM contains private field")
    return errors


def verify_attribution_bill_of_materials(
    bom: dict[str, Any],
    bom_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an attribution BOM against replay inputs."""

    errors = validate_attribution_bill_of_materials_shape(bom)
    expected = make_attribution_bill_of_materials(
        bom_input,
        issuer=str(bom.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(bom.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "bomFormat",
        "specVersion",
        "serialNumber",
        "version",
        "metadata",
        "components",
        "dependencies",
        "rdllm",
        "summary",
    ):
        if bom.get(key) != expected.get(key):
            errors.append(f"attribution BOM {key} mismatch")
    if bom.get("attribution_bom_hash") != expected.get("attribution_bom_hash"):
        errors.append("attribution BOM hash mismatch")
    if bom.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("attribution BOM signature mismatch")
    if any(value is not True for value in bom.get("rdllm", {}).get("checks", {}).values()):
        errors.append("attribution BOM has failing checks")
    return errors
