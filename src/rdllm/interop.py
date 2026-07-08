"""Interoperability exports for attribution receipts and settlement reports."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.receipts import canonical_json, sign_payload, validate_receipt_shape
from rdllm.telemetry import make_trace_exchange, verify_trace_exchange
from rdllm.text import stable_hash

INTEROP_VERSION = "rdllm-interop/v1"
VC_CONTEXTS = (
    "https://www.w3.org/ns/credentials/v2",
    "https://rdllm.local/contexts/rdllm/v1",
)
PROV_CONTEXT = {
    "prov": "http://www.w3.org/ns/prov#",
    "rdllm": "https://rdllm.local/ns#",
}
CRYPTOSUITE = "rdllm-hmac-sha256-2026"


def receipt_credential(
    receipt: dict[str, Any],
    *,
    credential_id: str | None = None,
    issuer: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Export an attribution receipt as a VC-shaped, proof-carrying claim."""

    errors = validate_receipt_shape(receipt)
    if errors:
        raise ValueError(f"invalid attribution receipt: {errors}")

    payload = receipt["payload"]
    event = payload["event"]
    grounding = payload["grounding"]
    economics = payload["economics"]
    credential = {
        "@context": list(VC_CONTEXTS),
        "id": credential_id or f"urn:rdllm:receipt:{receipt['receipt_hash']}",
        "type": [
            "VerifiableCredential",
            "RDLLMAttributionReceiptCredential",
        ],
        "issuer": issuer or payload["issuer"],
        "validFrom": payload["issued_at"],
        "credentialSubject": {
            "id": f"urn:rdllm:event:{event['event_id']}",
            "receiptHash": receipt["receipt_hash"],
            "eventHash": event["event_hash"],
            "promptHash": event["prompt_hash"],
            "answerHash": event["answer_hash"],
            "renderedOutputHash": event["rendered_output_hash"],
            "model": payload["model"],
            "groundingStatus": grounding["report"].get("status", ""),
            "groundingQualityVerdict": grounding["quality"].get("verdict", ""),
            "policyStatus": payload["rights"]["policy_status"],
            "registryStatus": payload["registry"]["registry_status"],
            "attributionGapVerdict": grounding.get("attribution_gap", {}).get(
                "verdict", ""
            ),
            "sourceCount": len(grounding["sources"]),
            "sourceAccessCount": len(grounding.get("source_accesses", [])),
            "claimCount": len(grounding["claims"]),
            "disclosureVersion": payload["privacy"].get("disclosure_version", ""),
            "disclosureRoot": payload["privacy"].get("disclosure_root", ""),
            "traceExchangeVersion": payload.get("telemetry", {}).get(
                "trace_exchange_version", ""
            ),
            "sourceAccessTraceHash": payload.get("telemetry", {}).get(
                "source_access_trace_hash", ""
            ),
            "sourceReferenceTraceHash": payload.get("telemetry", {}).get(
                "source_reference_trace_hash", ""
            ),
            "claimSupportTraceHash": payload.get("telemetry", {}).get(
                "claim_support_trace_hash", ""
            ),
            "creatorPool": economics["creator_pool"],
            "creatorPoolRate": economics["creator_pool_rate"],
            "shareCommitment": _commit(economics["shares"]),
            "sourceCommitment": _commit(grounding["sources"]),
            "claimCommitment": _commit(grounding["claims"]),
            "sourceAccessCommitment": _commit(grounding.get("source_accesses", [])),
            "attributionGapCommitment": _commit(grounding.get("attribution_gap", {})),
            "rightsCommitment": _commit(payload["rights"]),
            "registryCommitment": _commit(payload["registry"]),
        },
        "evidence": _receipt_evidence(payload),
    }
    _attach_proof(
        credential,
        signing_secret=signing_secret,
        created=payload["issued_at"],
        verification_method=f"{credential['issuer']}#rdllm-attribution-key",
    )
    return credential


def settlement_credential(
    settlement_report: dict[str, Any],
    *,
    credential_id: str | None = None,
    issuer: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Export a post-dispute settlement report as a VC-shaped claim."""

    resolution = settlement_report.get("resolution", {})
    subject = {
        "id": f"urn:rdllm:settlement:{settlement_report.get('report_hash', '')}",
        "reportHash": settlement_report.get("report_hash", ""),
        "sourceLedgerHash": settlement_report.get("source_ledger_hash", ""),
        "settlementStatus": settlement_report.get("status", ""),
        "resolutionId": resolution.get("resolution_id", ""),
        "conflictId": resolution.get("conflict_id", ""),
        "registryReportHash": resolution.get("registry_report_hash", ""),
        "totalReleased": settlement_report.get("summary", {}).get("total_released", "0"),
        "releaseCount": settlement_report.get("summary", {}).get("release_count", 0),
        "releaseCommitment": _commit(settlement_report.get("releases", [])),
        "releaseBalancesCommitment": _commit(
            settlement_report.get("release_balances", {})
        ),
        "balancesAfterCommitment": _commit(settlement_report.get("balances_after", {})),
        "resolutionCommitment": _commit(resolution),
    }
    credential = {
        "@context": list(VC_CONTEXTS),
        "id": credential_id or f"urn:rdllm:settlement-credential:{subject['reportHash']}",
        "type": [
            "VerifiableCredential",
            "RDLLMEscrowSettlementCredential",
        ],
        "issuer": issuer or resolution.get("resolver", "rdllm-settlement-authority"),
        "validFrom": resolution.get("resolved_at", ""),
        "credentialSubject": subject,
    }
    _attach_proof(
        credential,
        signing_secret=signing_secret,
        created=credential["validFrom"],
        verification_method=f"{credential['issuer']}#rdllm-settlement-key",
    )
    return credential


def receipt_prov_graph(receipt: dict[str, Any]) -> dict[str, Any]:
    """Export a receipt as a PROV-shaped provenance graph."""

    errors = validate_receipt_shape(receipt)
    if errors:
        raise ValueError(f"invalid attribution receipt: {errors}")

    payload = receipt["payload"]
    event = payload["event"]
    activity_id = f"urn:rdllm:activity:{event['event_id']}"
    prompt_id = f"urn:rdllm:prompt:{event['prompt_hash']}"
    answer_id = f"urn:rdllm:answer:{event['rendered_output_hash']}"

    source_entities = [
        _source_entity(source) for source in payload["grounding"]["sources"]
    ]
    claim_entities = [
        _claim_entity(event["event_id"], index, claim)
        for index, claim in enumerate(payload["grounding"]["claims"], start=1)
    ]
    creators = _creator_agents(payload["grounding"]["sources"])
    used_entities = [prompt_id] + [entity["id"] for entity in source_entities]

    graph = {
        "@context": PROV_CONTEXT,
        "type": "RDLLMProvenanceGraph",
        "id": f"urn:rdllm:prov:{receipt['receipt_hash']}",
        "receipt_hash": receipt["receipt_hash"],
        "event_hash": event["event_hash"],
        "entities": [
            {
                "id": prompt_id,
                "type": "rdllm:PromptCommitment",
                "promptHash": event["prompt_hash"],
            },
            {
                "id": answer_id,
                "type": "rdllm:RenderedOutput",
                "answerHash": event["answer_hash"],
                "renderedOutputHash": event["rendered_output_hash"],
            },
            *source_entities,
            *claim_entities,
        ],
        "activities": [
            {
                "id": activity_id,
                "type": "rdllm:GenerationAttribution",
                "startedAtTime": payload["issued_at"],
                "used": used_entities,
                "generated": answer_id,
                "model": payload["model"],
                "groundingStatus": payload["grounding"]["report"].get("status", ""),
            }
        ],
        "agents": [
            {
                "id": f"urn:rdllm:issuer:{stable_hash(payload['issuer'])[:16]}",
                "type": "prov:Agent",
                "name": payload["issuer"],
                "role": "issuer",
            },
            {
                "id": f"urn:rdllm:model:{stable_hash(canonical_json(payload['model']))[:16]}",
                "type": "prov:SoftwareAgent",
                "name": payload["model"].get("id", ""),
                "version": payload["model"].get("version", ""),
                "routeId": payload["model"].get("route_id", ""),
            },
            *creators,
        ],
        "relations": _prov_relations(activity_id, answer_id, payload),
    }
    graph["graph_hash"] = stable_hash(canonical_json(_without_keys(graph, {"graph_hash"})))
    return graph


def make_interop_bundle(
    receipt: dict[str, Any],
    *,
    settlement_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a portable attribution bundle for wallets, auditors, and registries."""

    bundle: dict[str, Any] = {
        "interop_version": INTEROP_VERSION,
        "receipt_hash": receipt["receipt_hash"],
        "receipt_credential": receipt_credential(
            receipt,
            signing_secret=signing_secret,
        ),
        "receipt_prov_graph": receipt_prov_graph(receipt),
        "trace_exchange": make_trace_exchange(receipt=receipt),
    }
    if settlement_report is not None:
        bundle["settlement_report_hash"] = settlement_report.get("report_hash", "")
        bundle["settlement_credential"] = settlement_credential(
            settlement_report,
            signing_secret=signing_secret,
        )
    bundle["bundle_hash"] = stable_hash(canonical_json(_hashable_bundle(bundle)))
    return bundle


def verify_interop_bundle(
    bundle: dict[str, Any],
    receipt: dict[str, Any],
    *,
    settlement_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a portable interop bundle against canonical receipt/report inputs."""

    errors: list[str] = []
    if bundle.get("interop_version") != INTEROP_VERSION:
        errors.append("interop version is unsupported")
        return errors
    expected_bundle_hash = stable_hash(canonical_json(_hashable_bundle(bundle)))
    if bundle.get("bundle_hash") != expected_bundle_hash:
        errors.append("bundle hash is not reproducible")
    if bundle.get("receipt_hash") != receipt.get("receipt_hash"):
        errors.append("bundle receipt_hash does not match receipt")

    credential = bundle.get("receipt_credential", {})
    subject = credential.get("credentialSubject", {})
    if subject.get("receiptHash") != receipt.get("receipt_hash"):
        errors.append("receipt credential subject does not match receipt hash")
    if subject.get("eventHash") != receipt.get("payload", {}).get("event", {}).get("event_hash"):
        errors.append("receipt credential subject does not match event hash")
    errors.extend(
        f"receipt credential: {error}"
        for error in verify_credential(credential, signing_secret=signing_secret)
    )

    graph = bundle.get("receipt_prov_graph", {})
    errors.extend(
        f"receipt provenance graph: {error}"
        for error in verify_prov_graph(receipt, graph)
    )

    trace = bundle.get("trace_exchange", {})
    errors.extend(
        f"trace exchange: {error}"
        for error in verify_trace_exchange(trace, receipt=receipt)
    )

    settlement_cred = bundle.get("settlement_credential")
    if settlement_report is not None:
        if not settlement_cred:
            errors.append("settlement credential is missing")
        else:
            settlement_subject = settlement_cred.get("credentialSubject", {})
            if settlement_subject.get("reportHash") != settlement_report.get("report_hash"):
                errors.append("settlement credential subject does not match report hash")
            if bundle.get("settlement_report_hash") != settlement_report.get("report_hash"):
                errors.append("bundle settlement_report_hash does not match settlement report")
            errors.extend(
                f"settlement credential: {error}"
                for error in verify_credential(
                    settlement_cred,
                    signing_secret=signing_secret,
                )
            )
    elif settlement_cred:
        errors.extend(
            f"settlement credential: {error}"
            for error in verify_credential(
                settlement_cred,
                signing_secret=signing_secret,
            )
        )
    return errors


def verify_credential(
    credential: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify the deterministic RDLLM proof envelope on a VC-shaped document."""

    errors: list[str] = []
    for key in ("@context", "id", "type", "issuer", "credentialSubject", "proof"):
        if key not in credential:
            errors.append(f"missing credential field: {key}")
    if errors:
        return errors

    types = credential.get("type", [])
    if "VerifiableCredential" not in types:
        errors.append("credential is not typed as VerifiableCredential")
    proof = credential.get("proof", {})
    if signing_secret:
        proof_options = _without_keys(proof, {"proofValue"})
        expected = sign_payload(
            {
                "document": _without_keys(credential, {"proof"}),
                "proof_options": proof_options,
            },
            signing_secret,
        )
        if proof.get("cryptosuite") != CRYPTOSUITE:
            errors.append("credential proof cryptosuite is unsupported")
        elif proof.get("proofValue") != expected:
            errors.append("credential proof value is invalid")
    return errors


def verify_prov_graph(receipt: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    """Verify that a PROV-shaped graph agrees with an attribution receipt."""

    errors: list[str] = []
    receipt_errors = validate_receipt_shape(receipt)
    if receipt_errors:
        return [f"receipt: {error}" for error in receipt_errors]

    payload = receipt["payload"]
    event = payload["event"]
    expected_hash = stable_hash(canonical_json(_without_keys(graph, {"graph_hash"})))
    if graph.get("graph_hash") != expected_hash:
        errors.append("provenance graph hash is not reproducible")
    if graph.get("receipt_hash") != receipt.get("receipt_hash"):
        errors.append("provenance graph receipt hash does not match receipt")
    if graph.get("event_hash") != event.get("event_hash"):
        errors.append("provenance graph event hash does not match receipt")

    entities = {entity.get("id"): entity for entity in graph.get("entities", [])}
    prompt_id = f"urn:rdllm:prompt:{event['prompt_hash']}"
    answer_id = f"urn:rdllm:answer:{event['rendered_output_hash']}"
    if prompt_id not in entities:
        errors.append("prompt commitment entity is missing")
    if answer_id not in entities:
        errors.append("rendered output entity is missing")

    source_entities = [
        entity
        for entity in graph.get("entities", [])
        if entity.get("type") == "rdllm:SourceChunk"
    ]
    sources = payload["grounding"]["sources"]
    if len(source_entities) != len(sources):
        errors.append("source entity count does not match receipt")
    for source in sources:
        source_entity = entities.get(_source_entity_id(source))
        if not source_entity:
            errors.append(f"source entity missing for {source['label']}")
            continue
        if source_entity.get("contentHash") != source["content_hash"]:
            errors.append(f"source entity content hash mismatch for {source['label']}")

    relations = graph.get("relations", [])
    supported_claims = [
        claim for claim in payload["grounding"]["claims"] if claim.get("supported")
    ]
    supported_relations = [
        relation
        for relation in relations
        if relation.get("type") == "rdllm:supportedClaim"
    ]
    if len(supported_relations) != len(supported_claims):
        errors.append("supported claim relation count does not match receipt")

    payout_relations = [
        relation for relation in relations if relation.get("type") == "rdllm:paidShare"
    ]
    shares = payload["economics"]["shares"]
    if len(payout_relations) != len(shares):
        errors.append("paid share relation count does not match receipt")
    return errors


def _receipt_evidence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for source in payload["grounding"]["sources"]:
        evidence.append(
            {
                "type": "RDLLMSourceEvidence",
                "sourceLabel": source["label"],
                "creatorId": source["creator_id"],
                "workId": source["work_id"],
                "chunkId": source["chunk_id"],
                "sourceUri": source["source_uri"],
                "contentHash": source["content_hash"],
                "evidenceSpanHashes": source.get("evidence_span_hashes", []),
            }
        )
    for index, claim in enumerate(payload["grounding"]["claims"], start=1):
        evidence.append(
            {
                "type": "RDLLMClaimEvidence",
                "claimId": f"claim:{index}",
                "claimHash": stable_hash(claim.get("claim", "")),
                "supported": claim.get("supported", False),
                "sourceLabel": claim.get("source_label", ""),
                "workId": claim.get("work_id", ""),
                "chunkId": claim.get("chunk_id", ""),
                "evidenceSpanHash": claim.get("evidence_span_hash", ""),
            }
        )
    return evidence


def _source_entity(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _source_entity_id(source),
        "type": "rdllm:SourceChunk",
        "label": source["label"],
        "creatorId": source["creator_id"],
        "workId": source["work_id"],
        "chunkId": source["chunk_id"],
        "title": source["title"],
        "sourceUri": source["source_uri"],
        "contentHash": source["content_hash"],
        "quoteHash": stable_hash(source.get("quote", "")),
        "license": source.get("license", ""),
        "policyId": source.get("policy_id", ""),
        "evidenceSpanHashes": source.get("evidence_span_hashes", []),
    }


def _claim_entity(event_id: str, index: int, claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"urn:rdllm:claim:{event_id}:{index}",
        "type": "rdllm:SupportedClaim" if claim.get("supported") else "rdllm:UnsupportedClaim",
        "claimHash": stable_hash(claim.get("claim", "")),
        "sourceLabel": claim.get("source_label", ""),
        "workId": claim.get("work_id", ""),
        "chunkId": claim.get("chunk_id", ""),
        "supportScore": claim.get("support_score", 0),
        "evidenceSpanHash": claim.get("evidence_span_hash", ""),
        "evidenceStartChar": claim.get("evidence_start_char", -1),
        "evidenceEndChar": claim.get("evidence_end_char", -1),
    }


def _creator_agents(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    creators: dict[str, dict[str, Any]] = {}
    for source in sources:
        creator_id = source["creator_id"]
        creators.setdefault(
            creator_id,
            {
                "id": f"urn:rdllm:creator:{creator_id}",
                "type": "prov:Agent",
                "creatorId": creator_id,
                "name": source.get("creator_name", creator_id),
                "role": "creator",
            },
        )
    return [creators[key] for key in sorted(creators)]


def _prov_relations(
    activity_id: str,
    answer_id: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = [
        {
            "type": "prov:wasGeneratedBy",
            "entity": answer_id,
            "activity": activity_id,
        }
    ]
    for source in payload["grounding"]["sources"]:
        source_id = _source_entity_id(source)
        relations.append(
            {
                "type": "prov:used",
                "activity": activity_id,
                "entity": source_id,
                "sourceLabel": source["label"],
            }
        )
        relations.append(
            {
                "type": "prov:wasAttributedTo",
                "entity": source_id,
                "agent": f"urn:rdllm:creator:{source['creator_id']}",
            }
        )
    for index, claim in enumerate(payload["grounding"]["claims"], start=1):
        if not claim.get("supported"):
            continue
        relations.append(
            {
                "type": "rdllm:supportedClaim",
                "claim": f"urn:rdllm:claim:{payload['event']['event_id']}:{index}",
                "source": _source_entity_id_from_claim(claim, payload["grounding"]["sources"]),
                "sourceLabel": claim.get("source_label", ""),
                "supportScore": claim.get("support_score", 0),
                "evidenceSpanHash": claim.get("evidence_span_hash", ""),
            }
        )
    for share in payload["economics"]["shares"]:
        relations.append(
            {
                "type": "rdllm:paidShare",
                "activity": activity_id,
                "creator": f"urn:rdllm:creator:{share['creator_id']}",
                "workId": share["work_id"],
                "chunkId": share["chunk_id"],
                "contributionWeight": share["contribution_weight"],
                "payout": share["payout"],
                "contentHash": share["content_hash"],
            }
        )
    for decision in payload["rights"].get("decisions", []):
        relations.append(
            {
                "type": "rdllm:rightsDecision",
                "activity": activity_id,
                "policyStatus": payload["rights"].get("policy_status", ""),
                "decisionHash": _commit(decision),
            }
        )
    for decision in payload["registry"].get("decisions", []):
        relations.append(
            {
                "type": "rdllm:registryDecision",
                "activity": activity_id,
                "registryStatus": payload["registry"].get("registry_status", ""),
                "decisionHash": _commit(decision),
            }
        )
    gap_report = payload["grounding"].get("attribution_gap", {})
    if gap_report:
        relations.append(
            {
                "type": "rdllm:attributionGapDecision",
                "activity": activity_id,
                "verdict": gap_report.get("verdict", ""),
                "reportHash": gap_report.get("report_hash", ""),
                "sourceAccessCount": gap_report.get("summary", {}).get(
                    "access_record_count", 0
                ),
                "consumedWithoutCredit": gap_report.get("summary", {}).get(
                    "consumed_without_credit_count", 0
                ),
            }
        )
    return relations


def _source_entity_id(source: dict[str, Any]) -> str:
    return f"urn:rdllm:source:{source['chunk_id']}:{source['content_hash'][:16]}"


def _source_entity_id_from_claim(
    claim: dict[str, Any],
    sources: list[dict[str, Any]],
) -> str:
    for source in sources:
        if (
            source.get("label") == claim.get("source_label")
            or source.get("chunk_id") == claim.get("chunk_id")
        ):
            return _source_entity_id(source)
    chunk_id = claim.get("chunk_id", "")
    return f"urn:rdllm:source:{chunk_id}:unknown"


def _commit(data: Any) -> str:
    return stable_hash(canonical_json(data))


def _attach_proof(
    document: dict[str, Any],
    *,
    signing_secret: str | None,
    created: str,
    verification_method: str,
) -> None:
    if not signing_secret:
        document["proof"] = {
            "type": "UnsignedProof",
            "cryptosuite": "UNSIGNED",
            "created": created,
            "verificationMethod": verification_method,
            "proofPurpose": "assertionMethod",
            "proofValue": "",
        }
        return

    proof_options = {
        "type": "DataIntegrityProof",
        "cryptosuite": CRYPTOSUITE,
        "created": created,
        "verificationMethod": verification_method,
        "proofPurpose": "assertionMethod",
    }
    proof_value = sign_payload(
        {
            "document": _without_keys(document, {"proof"}),
            "proof_options": proof_options,
        },
        signing_secret,
    )
    document["proof"] = {**proof_options, "proofValue": proof_value}


def _without_keys(data: Any, keys: set[str]) -> Any:
    copied = deepcopy(data)
    if isinstance(copied, dict):
        for key in keys:
            copied.pop(key, None)
    return copied


def _hashable_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return _without_keys(bundle, {"bundle_hash"})
