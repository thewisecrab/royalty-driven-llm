"""Decision provenance graphs for RDLLM response attribution and release."""

from __future__ import annotations

from typing import Any

from rdllm.attribution_capsule import validate_attribution_capsule_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.release_gate import verify_release_gate_report
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_boundary import (
    validate_source_boundary_report_shape,
    verify_source_boundary_report,
)
from rdllm.telemetry import verify_trace_exchange

DECISION_PROVENANCE_REPORT_VERSION = "rdllm-decision-provenance-report/v1"
DECISION_PROVENANCE_SCHEMA = "docs/schemas/decision_provenance_report.schema.json"
DECISION_PROVENANCE_POLICY_VERSION = "rdllm-decision-provenance-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L62"

DECLARED_HASH_FIELDS = (
    "gate_hash",
    "capsule_hash",
    "envelope_hash",
    "trace_hash",
    "report_hash",
    "card_hash",
    "contract_hash",
    "receipt_hash",
    "summary_hash",
    "bundle_hash",
    "profile_hash",
    "manifest_hash",
    "attestation_hash",
    "graph_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "hidden_state",
    "token_logits",
    "private_trace",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
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
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            if field == "receipt_hash":
                return True
            if field == "trace_hash":
                hashable = {
                    key: value
                    for key, value in artifact.items()
                    if key not in {"trace_hash", "signature"}
                }
                return hash_payload(hashable) == artifact[field]
            if field == "capsule_hash":
                hashable = _hashable_artifact(artifact)
                surfaces = hashable.get("portable_surfaces")
                if isinstance(surfaces, dict):
                    surfaces = dict(surfaces)
                    headers = dict(surfaces.get("http_headers", {}))
                    headers.pop("RDLLM-Capsule-Hash", None)
                    surfaces["http_headers"] = headers
                    hashable["portable_surfaces"] = surfaces
                return hash_payload(hashable) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _artifact_node(
    node_id: str,
    artifact_name: str,
    artifact_type: str,
    artifact: dict[str, Any],
    *,
    node_type: str,
    influence_boundary: str,
) -> dict[str, Any]:
    row = {
        "node_id": node_id,
        "node_type": node_type,
        "artifact_name": artifact_name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(artifact),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "influence_boundary": influence_boundary,
    }
    row["node_hash"] = hash_payload(row)
    return row


def _decision_node(
    node_id: str,
    *,
    decision_type: str,
    decision_scope: str,
    decision_status: str,
    subject: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "node_id": node_id,
        "node_type": "decision",
        "decision_type": decision_type,
        "decision_scope": decision_scope,
        "decision_status": decision_status,
        "subject": subject,
    }
    row["node_hash"] = hash_payload(row)
    return row


def _edge_row(
    source_node: str,
    target_node: str,
    *,
    edge_class: str,
    influence_channel: str,
    allowed_influence: bool,
    reason: str,
) -> dict[str, Any]:
    row = {
        "source_node": source_node,
        "target_node": target_node,
        "edge_class": edge_class,
        "influence_channel": influence_channel,
        "allowed_influence": allowed_influence,
        "reason": reason,
    }
    row["edge_hash"] = hash_payload(row)
    return row


def _embedded(response_envelope: dict[str, Any], name: str) -> dict[str, Any]:
    value = response_envelope.get("embedded_artifacts", {}).get(name, {})
    return value if isinstance(value, dict) else {}


def _event(response_envelope: dict[str, Any], release_gate: dict[str, Any], trace_exchange: dict[str, Any]) -> dict[str, Any]:
    response = response_envelope.get("response", {})
    gate_subject = release_gate.get("subject", {})
    return {
        "event_id": response.get("event_id", ""),
        "event_hash": response.get("event_hash", ""),
        "rendered_output_hash": response.get("rendered_output_hash", ""),
        "answer_hash": response.get("answer_hash", ""),
        "trace_hash": trace_exchange.get("trace_hash", ""),
        "response_envelope_hash": response_envelope.get("envelope_hash", ""),
        "release_gate_hash": release_gate.get("gate_hash", ""),
        "gate_event_hash": gate_subject.get("event_hash", ""),
        "gate_rendered_output_hash": gate_subject.get("rendered_output_hash", ""),
    }


def _artifact_bindings(
    *,
    response_envelope: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
) -> dict[str, str]:
    artifacts = response_envelope.get("embedded_artifacts", {})
    bindings = {
        "response_envelope_hash": _declared_hash(response_envelope),
        "release_gate_hash": _declared_hash(release_gate),
        "trace_exchange_hash": _declared_hash(trace_exchange),
        "attribution_capsule_hash": _declared_hash(attribution_capsule),
    }
    for name in (
        "answer_provenance_card",
        "source_verification_report",
        "source_confidence_report",
        "creator_license_contract",
        "citation_footer_contract",
        "source_availability_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "answer_claim_coverage_report",
        "generation_context_closure_report",
        "source_boundary_report",
        "public_receipt",
        "provider_attribution_card",
        "certification_report",
    ):
        artifact = artifacts.get(name, {})
        if isinstance(artifact, dict) and artifact:
            bindings[f"{name}_hash"] = _declared_hash(artifact)
    return bindings


def _artifact_nodes(
    *,
    response_envelope: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
) -> list[dict[str, Any]]:
    artifacts = response_envelope.get("embedded_artifacts", {})
    definitions = [
        (
            "response_envelope",
            "response_envelope",
            "rdllm-response-envelope/v1",
            response_envelope,
            "proof_container",
            "trusted_proof_packaging",
        ),
        (
            "release_gate",
            "release_gate",
            "rdllm-response-release-gate/v1",
            release_gate,
            "trusted_release_control",
            "release_policy_decision",
        ),
        (
            "trace_exchange",
            "trace_exchange",
            "rdllm-trace-exchange/v1",
            trace_exchange,
            "telemetry_proof",
            "runtime_observation",
        ),
        (
            "attribution_capsule",
            "attribution_capsule",
            "rdllm-attribution-capsule/v1",
            attribution_capsule,
            "portable_control",
            "copied_output_binding",
        ),
    ]
    embedded_definitions = {
        "answer_provenance_card": (
            "answer_provenance_card",
            "rdllm-answer-provenance-card/v1",
            "accounting_proof",
            "answer_source_accounting",
        ),
        "source_verification_report": (
            "source_verification_report",
            "rdllm-source-verification-report/v1",
            "evidence_proof",
            "materialized_source_identity",
        ),
        "source_confidence_report": (
            "source_confidence_report",
            "rdllm-source-confidence-report/v1",
            "quality_proof",
            "source_confidence_status",
        ),
        "creator_license_contract": (
            "creator_license_contract",
            "rdllm-creator-license-contract/v1",
            "trusted_policy",
            "rights_and_royalty_policy",
        ),
        "citation_footer_contract": (
            "citation_footer_contract",
            "rdllm-citation-footer-contract/v1",
            "trusted_display_contract",
            "client_visible_attribution",
        ),
        "source_availability_report": (
            "source_availability_report",
            "rdllm-source-availability-report/v1",
            "evidence_proof",
            "source_resolution",
        ),
        "evidence_sufficiency_report": (
            "evidence_sufficiency_report",
            "rdllm-evidence-sufficiency-report/v1",
            "evidence_proof",
            "minimal_sufficient_evidence",
        ),
        "counterevidence_report": (
            "counterevidence_report",
            "rdllm-counterevidence-adjudication-report/v1",
            "evidence_proof",
            "counterevidence_adjudication",
        ),
        "answer_claim_coverage_report": (
            "answer_claim_coverage_report",
            "rdllm-answer-claim-coverage-report/v1",
            "claim_proof",
            "answer_claim_coverage",
        ),
        "generation_context_closure_report": (
            "generation_context_closure_report",
            "rdllm-generation-context-closure-report/v1",
            "context_proof",
            "traced_generation_context",
        ),
        "source_boundary_report": (
            "source_boundary_report",
            "rdllm-source-boundary-report/v1",
            "boundary_proof",
            "source_data_cannot_control_decisions",
        ),
        "public_receipt": (
            "public_receipt",
            "rdllm-attribution-receipt/v1-public",
            "accounting_proof",
            "public_usage_receipt",
        ),
        "provider_attribution_card": (
            "provider_attribution_card",
            "rdllm-provider-attribution-card/v1",
            "trusted_policy",
            "provider_public_posture",
        ),
        "certification_report": (
            "certification_report",
            "rdllm-certification/v1",
            "trusted_policy",
            "conformance_level",
        ),
    }
    for name, (
        artifact_name,
        artifact_type,
        node_type,
        influence_boundary,
    ) in embedded_definitions.items():
        artifact = artifacts.get(name)
        if isinstance(artifact, dict) and artifact:
            definitions.append(
                (name, artifact_name, artifact_type, artifact, node_type, influence_boundary)
            )
    return [
        _artifact_node(
            node_id=node_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            artifact=artifact,
            node_type=node_type,
            influence_boundary=influence_boundary,
        )
        for node_id, artifact_name, artifact_type, artifact, node_type, influence_boundary in definitions
        if artifact
    ]


def _claim_decision_nodes(answer_coverage: dict[str, Any], source_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit in answer_coverage.get("answer_units", []):
        if unit.get("requires_support") is not True:
            continue
        index = int(unit.get("unit_index", len(rows) + 1) or 0)
        rows.append(
            _decision_node(
                f"claim_decision:{index}",
                decision_type="claim_grounding",
                decision_scope="answer_unit",
                decision_status="covered" if unit.get("covered") is True else "unsupported",
                subject={
                    "unit_index": index,
                    "unit_hash": str(unit.get("unit_hash", "")),
                    "text_hash": str(unit.get("text_hash", "")),
                    "matched_claim_index": int(unit.get("matched_claim_index", 0) or 0),
                    "matched_source_label": str(unit.get("matched_source_label", "")),
                    "matched_evidence_span_prefix": str(
                        unit.get("matched_evidence_span_prefix", "")
                    ),
                    "evidence_sufficient": unit.get("evidence_sufficient") is True,
                    "counterevidence_free": unit.get("counterevidence_free") is True,
                },
            )
        )
    if rows:
        return rows
    for claim in source_report.get("claims", []):
        index = int(claim.get("claim_index", len(rows) + 1) or 0)
        rows.append(
            _decision_node(
                f"claim_decision:{index}",
                decision_type="claim_grounding",
                decision_scope="source_claim",
                decision_status="covered" if claim.get("supported") is True else "unsupported",
                subject={
                    "claim_index": index,
                    "claim_hash": str(claim.get("claim_hash", "")),
                    "source_label": str(claim.get("source_label", "")),
                    "evidence_span_prefix": str(claim.get("evidence_span_prefix", "")),
                    "work_id": str(claim.get("work_id", "")),
                    "chunk_id": str(claim.get("chunk_id", "")),
                },
            )
        )
    return rows


def _footer_decision_nodes(citation_footer: dict[str, Any], source_confidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_rows = citation_footer.get("sources") or source_confidence.get("sources", [])
    for source in source_rows:
        label = str(source.get("label") or source.get("display_label", "")).strip("[]")
        if not label:
            label = f"S{len(rows) + 1}"
        rows.append(
            _decision_node(
                f"footer_decision:{label}",
                decision_type="visible_attribution_footer",
                decision_scope="source_footer_row",
                decision_status=str(
                    source.get("confidence_level")
                    or source.get("footer_status")
                    or "verified"
                ),
                subject={
                    "source_label": label,
                    "work_id": str(source.get("work_id", "")),
                    "chunk_id": str(source.get("chunk_id", "")),
                    "creator_id": str(source.get("creator_id", "")),
                    "content_hash_prefix": str(source.get("content_hash_prefix", "")),
                    "footer_row_hash": str(
                        source.get("footer_row_hash")
                        or source.get("display_row_hash")
                        or source.get("source_confidence_hash")
                        or ""
                    ),
                    "license_status": str(source.get("license_status", "")),
                    "royalty_status": str(source.get("royalty_status", "")),
                },
            )
        )
    return rows


def _payout_decision_nodes(answer_card: dict[str, Any], public_receipt: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_rows = answer_card.get("sources") or public_receipt.get("sources", [])
    for source in source_rows:
        label = str(source.get("label", f"S{len(rows) + 1}"))
        rows.append(
            _decision_node(
                f"payout_decision:{label}",
                decision_type="royalty_participation",
                decision_scope="source_share",
                decision_status="royalty_active",
                subject={
                    "source_label": label,
                    "creator_id": str(source.get("creator_id", "")),
                    "work_id": str(source.get("work_id", "")),
                    "chunk_id": str(source.get("chunk_id", "")),
                    "content_hash": str(source.get("content_hash", "")),
                    "contribution_weight": str(source.get("contribution_weight", "")),
                    "source_entry_hash": str(source.get("source_entry_hash", "")),
                },
            )
        )
    return rows


def _release_decision_node(release_gate: dict[str, Any]) -> dict[str, Any]:
    summary = release_gate.get("summary", {})
    subject = release_gate.get("subject", {})
    return _decision_node(
        "release_decision:response",
        decision_type="response_release",
        decision_scope="model_egress",
        decision_status=str(summary.get("decision", "")),
        subject={
            "event_hash": str(subject.get("event_hash", "")),
            "rendered_output_hash": str(subject.get("rendered_output_hash", "")),
            "release_mode": str(summary.get("release_mode", "")),
            "release_gate_hash": str(release_gate.get("gate_hash", "")),
        },
    )


def _decision_nodes(response_envelope: dict[str, Any], release_gate: dict[str, Any]) -> list[dict[str, Any]]:
    answer_card = _embedded(response_envelope, "answer_provenance_card")
    source_report = _embedded(response_envelope, "source_verification_report")
    source_confidence = _embedded(response_envelope, "source_confidence_report")
    citation_footer = _embedded(response_envelope, "citation_footer_contract")
    answer_coverage = _embedded(response_envelope, "answer_claim_coverage_report")
    public_receipt = _embedded(response_envelope, "public_receipt")
    return [
        *_claim_decision_nodes(answer_coverage, source_report),
        *_footer_decision_nodes(citation_footer, source_confidence),
        *_payout_decision_nodes(answer_card, public_receipt),
        _release_decision_node(release_gate),
    ]


def _edges_for_nodes(decision_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in decision_nodes:
        node_id = str(node.get("node_id", ""))
        decision_type = node.get("decision_type")
        if decision_type == "claim_grounding":
            for source_node, edge_class, reason in (
                ("certification_report", "certified_proof_requirement", "provider claims L62-grade decision provenance"),
                ("source_verification_report", "source_materialization", "claim must resolve to a materialized source row"),
                ("source_availability_report", "source_resolution", "claim source must be reachable or archived"),
                ("evidence_sufficiency_report", "minimal_evidence", "claim needs sufficient evidence margin"),
                ("counterevidence_report", "counterevidence_adjudication", "claim must have no unaddressed counterevidence"),
                ("answer_claim_coverage_report", "claim_coverage", "public answer unit must bind to a verified claim row"),
                ("generation_context_closure_report", "context_closure", "claim must be present in traced generation context"),
                ("source_boundary_report", "boundary_guard", "source material is evidence-only, not instruction/control"),
            ):
                rows.append(
                    _edge_row(
                        source_node,
                        node_id,
                        edge_class=edge_class,
                        influence_channel="trusted_proof_summary",
                        allowed_influence=True,
                        reason=reason,
                    )
                )
        elif decision_type == "visible_attribution_footer":
            for source_node, edge_class, reason in (
                ("certification_report", "certified_proof_requirement", "provider claims L62-grade decision provenance"),
                ("source_verification_report", "source_materialization", "footer source row must resolve to registered material"),
                ("source_confidence_report", "source_confidence", "footer confidence label must match verification checks"),
                ("citation_footer_contract", "display_contract", "client-visible footer row must be hash-bound"),
                ("creator_license_contract", "rights_duty", "license terms require attribution"),
                ("source_boundary_report", "boundary_guard", "source content cannot rewrite attribution decisions"),
            ):
                rows.append(
                    _edge_row(
                        source_node,
                        node_id,
                        edge_class=edge_class,
                        influence_channel="trusted_display_or_policy",
                        allowed_influence=True,
                        reason=reason,
                    )
                )
        elif decision_type == "royalty_participation":
            for source_node, edge_class, reason in (
                ("certification_report", "certified_proof_requirement", "provider claims L62-grade decision provenance"),
                ("creator_license_contract", "royalty_policy", "license terms require royalty handling"),
                ("answer_provenance_card", "accounting_commitment", "answer card commits source identity and contribution weight"),
                ("public_receipt", "usage_receipt_commitment", "public receipt commits usage event and credited sources"),
                ("provider_attribution_card", "provider_public_posture", "provider declares royalty and settlement surfaces"),
                ("source_boundary_report", "boundary_guard", "source content cannot modify payout decisions"),
            ):
                rows.append(
                    _edge_row(
                        source_node,
                        node_id,
                        edge_class=edge_class,
                        influence_channel="trusted_policy_or_accounting",
                        allowed_influence=True,
                        reason=reason,
                    )
                )
        elif decision_type == "response_release":
            for source_node, edge_class, reason in (
                ("response_envelope", "proof_container", "release operates on the verified response envelope"),
                ("release_gate", "release_policy", "emit decision comes from the signed release gate"),
                ("attribution_capsule", "portable_binding", "released answer must preserve portable attribution binding"),
                ("provider_attribution_card", "provider_public_posture", "provider must disclose compatible surfaces"),
                ("certification_report", "certified_proof_requirement", "provider must meet the decision provenance level"),
                ("source_availability_report", "source_resolution", "release requires inspectable source rows"),
                ("evidence_sufficiency_report", "minimal_evidence", "release requires sufficient evidence"),
                ("counterevidence_report", "counterevidence_adjudication", "release requires counterevidence closure"),
                ("answer_claim_coverage_report", "claim_coverage", "release requires all public claims to be covered"),
                ("generation_context_closure_report", "context_closure", "release requires generation context closure"),
                ("source_boundary_report", "boundary_guard", "release requires source boundary integrity"),
            ):
                rows.append(
                    _edge_row(
                        source_node,
                        node_id,
                        edge_class=edge_class,
                        influence_channel="trusted_release_control",
                        allowed_influence=True,
                        reason=reason,
                    )
                )
    deduped = {
        (
            row["source_node"],
            row["target_node"],
            row["edge_class"],
            row["influence_channel"],
            row["reason"],
        ): row
        for row in rows
    }
    return sorted(
        deduped.values(),
        key=lambda row: (
            row["target_node"],
            row["source_node"],
            row["edge_class"],
            row["reason"],
        ),
    )


def _incoming(edges: list[dict[str, Any]]) -> dict[str, set[str]]:
    rows: dict[str, set[str]] = {}
    for edge in edges:
        rows.setdefault(str(edge.get("target_node", "")), set()).add(
            str(edge.get("source_node", ""))
        )
    return rows


def _input_checks(
    *,
    response_envelope: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    signing_secret: str | None,
) -> dict[str, bool]:
    artifacts = response_envelope.get("embedded_artifacts", {})
    answer_card = artifacts.get("answer_provenance_card", {})
    source_report = artifacts.get("source_verification_report", {})
    answer_coverage = artifacts.get("answer_claim_coverage_report", {})
    context_closure = artifacts.get("generation_context_closure_report", {})
    source_boundary = artifacts.get("source_boundary_report", {})
    creator_license = artifacts.get("creator_license_contract", {})
    provider_card = artifacts.get("provider_attribution_card", {})
    certification = artifacts.get("certification_report", {})

    release_errors: list[str]
    if attribution_capsule:
        release_errors = verify_release_gate_report(
            release_gate,
            response_envelope=response_envelope,
            attribution_capsule=attribution_capsule,
            creator_license_contract=creator_license,
            provider_card=provider_card,
            certification_report=certification,
            signing_secret=signing_secret,
        )
    else:
        release_errors = ["missing attribution capsule"]

    boundary_errors: list[str]
    if source_boundary and context_closure:
        boundary_errors = verify_source_boundary_report(
            source_boundary,
            trace_exchange=trace_exchange,
            source_verification_report=source_report,
            generation_context_closure_report=context_closure,
            answer_claim_coverage_report=answer_coverage,
            signing_secret=signing_secret,
        )
    else:
        boundary_errors = ["missing source boundary or generation context closure"]

    response = response_envelope.get("response", {})
    gate_subject = release_gate.get("subject", {})
    trace_hash = trace_exchange.get("trace_hash", "")
    card_event = answer_card.get("event", {})
    return {
        "response_envelope_verified": not verify_response_envelope(
            response_envelope,
            signing_secret=signing_secret,
        ),
        "release_gate_verified": not release_errors,
        "trace_exchange_verified": not verify_trace_exchange(trace_exchange),
        "attribution_capsule_shape_valid": not validate_attribution_capsule_shape(
            attribution_capsule
        ),
        "source_boundary_verified": not validate_source_boundary_report_shape(
            source_boundary
        )
        and not boundary_errors,
        "event_hashes_match": (
            response.get("event_hash", "")
            == gate_subject.get("event_hash", "")
            == card_event.get("event_hash", "")
        ),
        "rendered_output_hashes_match": (
            response.get("rendered_output_hash", "")
            == gate_subject.get("rendered_output_hash", "")
            == card_event.get("rendered_output_hash", "")
        ),
        "trace_hashes_match": trace_hash
        == response_envelope.get("commitments", {}).get("trace_exchange_hash", "")
        == card_event.get("trace_hash", ""),
        "source_boundary_blocks_attribution_and_payout_mutation": all(
            row.get("source_cannot_modify_attribution") is True
            and row.get("source_cannot_modify_payout") is True
            and row.get("control_channel_blocked") is True
            and row.get("instruction_channel_blocked") is True
            for row in source_boundary.get("source_boundary_rows", [])
        )
        and bool(source_boundary.get("source_boundary_rows")),
    }


def _graph_checks(
    *,
    artifact_nodes: list[dict[str, Any]],
    decision_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    input_checks: dict[str, bool],
) -> dict[str, bool]:
    node_ids = {node["node_id"] for node in artifact_nodes + decision_nodes}
    incoming = _incoming(edges)
    claim_nodes = [
        node for node in decision_nodes if node.get("decision_type") == "claim_grounding"
    ]
    footer_nodes = [
        node
        for node in decision_nodes
        if node.get("decision_type") == "visible_attribution_footer"
    ]
    payout_nodes = [
        node
        for node in decision_nodes
        if node.get("decision_type") == "royalty_participation"
    ]
    release_nodes = [
        node
        for node in decision_nodes
        if node.get("decision_type") == "response_release"
    ]

    disallowed_payout_edges = [
        edge
        for edge in edges
        if str(edge.get("target_node", "")).startswith("payout_decision:")
        and edge.get("source_node")
        in {
            "trace_exchange",
            "source_verification_report",
            "source_availability_report",
            "evidence_sufficiency_report",
            "counterevidence_report",
            "answer_claim_coverage_report",
            "generation_context_closure_report",
        }
    ]
    private_paths = _contains_private_fields(
        {
            "artifacts": artifact_nodes,
            "decisions": decision_nodes,
            "edges": edges,
        }
    )

    checks = {
        **input_checks,
        "artifact_nodes_have_reproducible_hashes": all(
            node.get("hash_reproducible") is True for node in artifact_nodes
        ),
        "decision_node_count_positive": bool(decision_nodes),
        "claim_decisions_present": bool(claim_nodes),
        "footer_decisions_present": bool(footer_nodes),
        "payout_decisions_present": bool(payout_nodes),
        "single_release_decision_present": len(release_nodes) == 1,
        "influence_edges_reference_known_nodes": all(
            edge.get("source_node") in node_ids and edge.get("target_node") in node_ids
            for edge in edges
        ),
        "all_influence_edges_allowed": all(
            edge.get("allowed_influence") is True for edge in edges
        ),
        "claim_decisions_have_required_proof_edges": all(
            {
                "certification_report",
                "source_verification_report",
                "evidence_sufficiency_report",
                "counterevidence_report",
                "answer_claim_coverage_report",
                "generation_context_closure_report",
                "source_boundary_report",
            }.issubset(incoming.get(node["node_id"], set()))
            for node in claim_nodes
        )
        and bool(claim_nodes),
        "footer_decisions_have_required_display_edges": all(
            {
                "certification_report",
                "source_verification_report",
                "source_confidence_report",
                "citation_footer_contract",
                "creator_license_contract",
                "source_boundary_report",
            }.issubset(incoming.get(node["node_id"], set()))
            for node in footer_nodes
        )
        and bool(footer_nodes),
        "payout_decisions_have_policy_and_accounting_edges": all(
            {
                "certification_report",
                "creator_license_contract",
                "answer_provenance_card",
                "public_receipt",
                "provider_attribution_card",
                "source_boundary_report",
            }.issubset(incoming.get(node["node_id"], set()))
            for node in payout_nodes
        )
        and bool(payout_nodes),
        "payout_decisions_have_no_untrusted_source_text_edges": not disallowed_payout_edges,
        "release_decision_has_required_proof_edges": all(
            {
                "response_envelope",
                "release_gate",
                "attribution_capsule",
                "provider_attribution_card",
                "certification_report",
                "answer_claim_coverage_report",
                "generation_context_closure_report",
                "source_boundary_report",
            }.issubset(incoming.get(node["node_id"], set()))
            for node in release_nodes
        )
        and len(release_nodes) == 1,
        "private_input_fields_absent": not private_paths,
    }
    return checks


def make_decision_provenance_report(
    *,
    response_envelope: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed graph of allowed influences for response decisions."""

    artifact_nodes = _artifact_nodes(
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
    )
    decisions = _decision_nodes(response_envelope, release_gate)
    edges = _edges_for_nodes(decisions)
    input_checks = _input_checks(
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        signing_secret=signing_secret,
    )
    checks = _graph_checks(
        artifact_nodes=artifact_nodes,
        decision_nodes=decisions,
        edges=edges,
        input_checks=input_checks,
    )
    issues = [name for name, passed in checks.items() if passed is not True]
    report = {
        "report_version": DECISION_PROVENANCE_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "policy_version": DECISION_PROVENANCE_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "claim_decisions_may_use_verified_evidence": True,
            "footer_decisions_must_use_display_contracts": True,
            "payout_decisions_must_use_license_and_accounting_channels": True,
            "source_content_may_not_modify_attribution_or_payout": True,
            "release_decisions_must_bind_l55_to_l61_closure": True,
            "requires_machine_verifiable_decision_edges": True,
        },
        "event": _event(response_envelope, release_gate, trace_exchange),
        "artifact_bindings": _artifact_bindings(
            response_envelope=response_envelope,
            release_gate=release_gate,
            trace_exchange=trace_exchange,
            attribution_capsule=attribution_capsule,
        ),
        "artifact_nodes": artifact_nodes,
        "decision_nodes": decisions,
        "influence_edges": edges,
        "checks": checks,
        "commitments": {
            "artifact_node_root": hash_payload(
                [node["node_hash"] for node in artifact_nodes]
            ),
            "decision_node_root": hash_payload(
                [node["node_hash"] for node in decisions]
            ),
            "influence_edge_root": hash_payload(
                [edge["edge_hash"] for edge in edges]
            ),
            "check_root": hash_payload(checks),
            "issue_root": hash_payload(issues),
            "schema": DECISION_PROVENANCE_SCHEMA,
        },
        "schemas": {
            "decision_provenance_report": DECISION_PROVENANCE_SCHEMA,
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "release_gate": "docs/schemas/release_gate.schema.json",
            "trace_exchange": "docs/schemas/trace_exchange.schema.json",
            "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
            "source_boundary_report": "docs/schemas/source_boundary_report.schema.json",
        },
        "summary": {
            "status": "verified" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "artifact_node_count": len(artifact_nodes),
            "decision_node_count": len(decisions),
            "claim_decision_count": sum(
                1
                for node in decisions
                if node.get("decision_type") == "claim_grounding"
            ),
            "footer_decision_count": sum(
                1
                for node in decisions
                if node.get("decision_type") == "visible_attribution_footer"
            ),
            "payout_decision_count": sum(
                1
                for node in decisions
                if node.get("decision_type") == "royalty_participation"
            ),
            "release_decision_count": sum(
                1
                for node in decisions
                if node.get("decision_type") == "response_release"
            ),
            "influence_edge_count": len(edges),
            "passed_check_count": sum(1 for value in checks.values() if value),
            "check_count": len(checks),
            "issue_count": len(issues),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "hidden_state_disclosed": False,
            "payout_account_disclosed": False,
            "report_uses_hashes_decision_ids_and_allowed_influence_edges": True,
        },
        "issues": issues,
    }
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


def validate_decision_provenance_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "artifact_nodes",
        "decision_nodes",
        "influence_edges",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "issues",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing decision provenance field: {key}")
    if errors:
        return errors
    if report.get("report_version") != DECISION_PROVENANCE_REPORT_VERSION:
        errors.append("decision provenance report version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "answer_hash",
        "trace_hash",
        "response_envelope_hash",
        "release_gate_hash",
    ):
        if key not in report.get("event", {}):
            errors.append(f"missing decision provenance event field: {key}")
    for node in report.get("artifact_nodes", []):
        for key in (
            "node_id",
            "node_type",
            "artifact_name",
            "artifact_type",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "influence_boundary",
            "node_hash",
        ):
            if key not in node:
                errors.append(f"missing decision provenance artifact node field: {key}")
    for node in report.get("decision_nodes", []):
        for key in (
            "node_id",
            "node_type",
            "decision_type",
            "decision_scope",
            "decision_status",
            "subject",
            "node_hash",
        ):
            if key not in node:
                errors.append(f"missing decision provenance decision node field: {key}")
    for edge in report.get("influence_edges", []):
        for key in (
            "source_node",
            "target_node",
            "edge_class",
            "influence_channel",
            "allowed_influence",
            "reason",
            "edge_hash",
        ):
            if key not in edge:
                errors.append(f"missing decision provenance edge field: {key}")
    for check in (
        "response_envelope_verified",
        "release_gate_verified",
        "trace_exchange_verified",
        "source_boundary_verified",
        "claim_decisions_have_required_proof_edges",
        "footer_decisions_have_required_display_edges",
        "payout_decisions_have_policy_and_accounting_edges",
        "payout_decisions_have_no_untrusted_source_text_edges",
        "release_decision_has_required_proof_edges",
        "private_input_fields_absent",
    ):
        if check not in report.get("checks", {}):
            errors.append(f"missing decision provenance check: {check}")
    return errors


def verify_decision_provenance_report(
    report: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    release_gate: dict[str, Any],
    trace_exchange: dict[str, Any],
    attribution_capsule: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify decision provenance against public response and release artifacts."""

    errors = validate_decision_provenance_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("decision provenance report hash is not reproducible")

    expected = make_decision_provenance_report(
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "artifact_nodes",
        "decision_nodes",
        "influence_edges",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"decision provenance {key} does not match artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("decision provenance report hash does not match artifacts")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("decision provenance report status is not verified")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"decision provenance check failed: {check}")
    if report.get("issues"):
        errors.append("decision provenance report contains issues")
    if report.get("privacy", {}).get(
        "report_uses_hashes_decision_ids_and_allowed_influence_edges"
    ) is not True:
        errors.append("decision provenance report must use hashes and influence edges")

    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append(
            "decision provenance report exposes private fields: "
            + ", ".join(private_paths[:5])
        )
    report_json = canonical_json(report)
    for private_literal in ('"prompt"', '"output"', '"source_text"', '"evidence_text"', '"hidden_state"'):
        if private_literal in report_json:
            errors.append(f"decision provenance report exposes private field {private_literal}")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("decision provenance report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("decision provenance report signature is invalid")
    return errors
