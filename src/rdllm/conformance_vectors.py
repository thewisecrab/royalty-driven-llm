"""Portable conformance vector packs for RDLLM implementers."""

from __future__ import annotations

from typing import Any

from rdllm.attribution_exchange import verify_attribution_exchange_manifest
from rdllm.integration_profile import SCHEMA_MAP
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope

CONFORMANCE_VECTOR_PACK_VERSION = "rdllm-conformance-vector-pack/v1"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "vector_pack_hash",
    "exchange_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "contract_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

REQUIRED_VECTOR_ARTIFACTS = (
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "discovery_manifest",
    "response_envelope",
    "assurance_bundle",
    "semantic_text_attribution_report",
    "creator_license_contract",
    "attribution_exchange",
)

VECTOR_SCHEMA_MAP = {
    **SCHEMA_MAP,
    "attribution_exchange": "docs/schemas/attribution_exchange.schema.json",
    "conformance_vector_pack": "docs/schemas/conformance_vector_pack.schema.json",
}


def _hashable_pack(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in pack.items()
        if key not in {"vector_pack_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "trace_hash":
                return (
                    hash_payload(
                        {
                            key: value
                            for key, value in artifact.items()
                            if key not in {"trace_hash", "signature"}
                        }
                    )
                    == artifact[field]
                )
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _artifact_entry(
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
    *,
    required: bool,
) -> dict[str, Any]:
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "schema": VECTOR_SCHEMA_MAP.get(name, ""),
        "required": required,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _artifact_catalog(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    training_summary: dict[str, Any] | None,
    provenance_evaluation_report: dict[str, Any] | None,
    counterfactual_report: dict[str, Any] | None,
    media_attribution_report: dict[str, Any] | None,
    model_signal_report: dict[str, Any] | None,
    rights_remediation_report: dict[str, Any] | None,
    source_confidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    private_audit_challenge: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    artifacts: list[tuple[str, str, dict[str, Any], bool]] = [
        ("provider_attribution_card", "rdllm-provider-attribution-card/v1", provider_card, True),
        ("certification_report", "rdllm-certification/v1", certification_report, True),
        ("integration_profile", "rdllm-integration-profile/v1", integration_profile, True),
        ("discovery_manifest", "rdllm-discovery-manifest/v1", discovery_manifest, True),
        ("response_envelope", "rdllm-response-envelope/v1", response_envelope, True),
        ("assurance_bundle", "rdllm-assurance-bundle/v1", assurance_bundle, True),
        (
            "semantic_text_attribution_report",
            "rdllm-semantic-text-attribution/v1",
            semantic_text_attribution_report,
            True,
        ),
        (
            "creator_license_contract",
            "rdllm-creator-license-contract/v1",
            creator_license_contract,
            True,
        ),
        ("attribution_exchange", "rdllm-attribution-exchange/v1", attribution_exchange, True),
    ]
    if training_summary is not None:
        artifacts.append(
            (
                "training_content_summary",
                "rdllm-training-content-summary/v1",
                training_summary,
                False,
            )
        )
    if provenance_evaluation_report is not None:
        artifacts.append(
            (
                "provenance_evaluation_report",
                "rdllm-provenance-evaluation/v1",
                provenance_evaluation_report,
                False,
            )
        )
    if counterfactual_report is not None:
        artifacts.append(
            (
                "counterfactual_influence_report",
                "rdllm-counterfactual-influence/v1",
                counterfactual_report,
                False,
            )
        )
    if media_attribution_report is not None:
        artifacts.append(
            (
                "media_attribution_report",
                "rdllm-media-attribution/v1",
                media_attribution_report,
                False,
            )
        )
    if model_signal_report is not None:
        artifacts.append(
            (
                "model_signal_attribution_report",
                "rdllm-model-signal-attribution/v1",
                model_signal_report,
                False,
            )
        )
    if rights_remediation_report is not None:
        artifacts.append(
            (
                "rights_remediation_report",
                "rdllm-rights-remediation/v1",
                rights_remediation_report,
                False,
            )
        )
    if source_confidence_report is not None:
        artifacts.append(
            (
                "source_confidence_report",
                "rdllm-source-confidence-report/v1",
                source_confidence_report,
                False,
            )
        )
    if citation_footer_contract is not None:
        artifacts.append(
            (
                "citation_footer_contract",
                "rdllm-citation-footer-contract/v1",
                citation_footer_contract,
                False,
            )
        )
    if private_audit_challenge is not None:
        artifacts.append(
            (
                "private_audit_challenge",
                "rdllm-private-audit-challenge/v1",
                private_audit_challenge,
                False,
            )
        )
    return [
        _artifact_entry(name, artifact_type, payload, required=required)
        for name, artifact_type, payload, required in artifacts
    ]


def _vector(
    *,
    vector_id: str,
    title: str,
    level: str,
    artifact: str,
    verifier_command: str,
    expected: dict[str, Any],
    negative_mutations: list[dict[str, str]],
) -> dict[str, Any]:
    item = {
        "vector_id": vector_id,
        "title": title,
        "level": level,
        "artifact": artifact,
        "verifier_command": verifier_command,
        "expected": expected,
        "negative_mutations": negative_mutations,
    }
    item["vector_hash"] = hash_payload(item)
    return item


def _test_vectors(
    *,
    certification_report: dict[str, Any],
    response_envelope: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    attribution_exchange: dict[str, Any],
) -> list[dict[str, Any]]:
    certification_summary = certification_report.get("summary", {})
    response_summary = response_envelope.get("summary", {})
    semantic_summary = semantic_text_attribution_report.get("summary", {})
    exchange_summary = attribution_exchange.get("summary", {})
    return [
        _vector(
            vector_id="rdllm.v1.response_envelope.public_proof",
            title="Response envelope packages a rendered answer with public proof artifacts.",
            level="RDLLM-L21",
            artifact="response_envelope",
            verifier_command="verify-response-envelope",
            expected={
                "status": "verified",
                "source_count_min": 1,
                "claim_count_min": 1,
                "artifact_count_min": 5,
            },
            negative_mutations=[
                {
                    "mutation": "rendered_output_hash_drift",
                    "expected_failure": "response envelope hash is not reproducible",
                },
                {
                    "mutation": "embedded_answer_card_hash_drift",
                    "expected_failure": "embedded artifact hash mismatch",
                },
            ],
        ),
        _vector(
            vector_id="rdllm.v1.discovery.provider_surface",
            title="Discovery manifest exposes well-known artifact paths and verifier commands.",
            level="RDLLM-L23",
            artifact="discovery_manifest",
            verifier_command="verify-discovery-manifest",
            expected={
                "status": "ready",
                "highest_level_min": "RDLLM-L31",
                "schema_count_min": 23,
                "artifact_count_min": 12,
            },
            negative_mutations=[
                {
                    "mutation": "api_contract_required_response_format_drift",
                    "expected_failure": "discovery manifest api_contract does not match artifacts",
                },
                {
                    "mutation": "missing_attribution_exchange_path",
                    "expected_failure": "discovery readiness check failed",
                },
            ],
        ),
        _vector(
            vector_id="rdllm.v1.semantic_text.paraphrase_and_escrow",
            title="Semantic text attribution credits paraphrased text and escrows unmatched text.",
            level="RDLLM-L30",
            artifact="semantic_text_attribution_report",
            verifier_command="verify-semantic-text-attribution",
            expected={
                "status": "ready",
                "accepted_input_count_min": 1,
                "escrow_input_count_min": 1,
                "source_footer_count_min": 1,
                "creator_pool_conserved": True,
            },
            negative_mutations=[
                {
                    "mutation": "footer_text_hash_drift",
                    "expected_failure": "semantic attribution footer replay drift",
                },
                {
                    "mutation": "hard_decoy_promoted_to_owner",
                    "expected_failure": "royalty shares do not match recomputed report",
                },
            ],
        ),
        _vector(
            vector_id="rdllm.v1.exchange.cross_provider_relay",
            title="Attribution exchange imports upstream proof hashes and relays source footers.",
            level="RDLLM-L31",
            artifact="attribution_exchange",
            verifier_command="verify-attribution-exchange",
            expected={
                "status": "ready",
                "cross_provider_ready": True,
                "artifact_count_min": len(REQUIRED_VECTOR_ARTIFACTS),
                "source_footer_count_min": 1,
            },
            negative_mutations=[
                {
                    "mutation": "imported_artifact_payload_hash_drift",
                    "expected_failure": "attribution exchange imported_artifacts does not match artifacts",
                },
                {
                    "mutation": "source_footer_row_removed",
                    "expected_failure": "source_footers_portable",
                },
            ],
        ),
        _vector(
            vector_id="rdllm.v1.certification.full_stack",
            title="Reference certification passes every public RDLLM requirement through L32.",
            level="RDLLM-L31",
            artifact="certification_report",
            verifier_command="certify",
            expected={
                "status": "passed",
                "highest_level": certification_summary.get("highest_level", ""),
                "case_count_min": int(certification_summary.get("case_count", 0) or 0),
                "score": float(certification_summary.get("score", 0.0) or 0.0),
            },
            negative_mutations=[
                {
                    "mutation": "highest_level_regression",
                    "expected_failure": "minimum certification level not met",
                },
                {
                    "mutation": "case_status_regression",
                    "expected_failure": "certification report hash is not reproducible",
                },
            ],
        ),
        _vector(
            vector_id="rdllm.v1.hashes.privacy_and_commitments",
            title="Public vector pack is hash-bound and private-text redacted.",
            level="RDLLM-L32",
            artifact="conformance_vector_pack",
            verifier_command="verify-conformance-vector-pack",
            expected={
                "response_status": response_summary.get("status", ""),
                "semantic_status": semantic_summary.get("status", ""),
                "exchange_status": exchange_summary.get("status", ""),
                "artifact_payloads_embedded": False,
            },
            negative_mutations=[
                {
                    "mutation": "vector_expected_status_drift",
                    "expected_failure": "conformance vector pack test_vectors does not match artifacts",
                },
                {
                    "mutation": "raw_prompt_text_inserted",
                    "expected_failure": "conformance vector pack discloses private prompt field",
                },
            ],
        ),
    ]


def _fixture_hashes(fixture_paths: dict[str, str] | None) -> dict[str, str]:
    fixtures = fixture_paths or {
        "sample_corpus": "examples/sample_corpus.json",
        "restricted_corpus": "examples/restricted_corpus.json",
        "conflict_corpus": "examples/conflict_corpus.json",
        "semantic_text_inputs": "examples/semantic_text_inputs.json",
        "provenance_benchmark_corpus": "examples/provenance_benchmark_corpus.json",
    }
    return {
        name: hash_payload({"path": path})
        for name, path in sorted(fixtures.items())
    }


def make_conformance_vector_pack(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    fixture_paths: dict[str, str] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed conformance vector pack for independent implementations."""

    provider = provider_card.get("provider", {})
    certification_summary = certification_report.get("summary", {})
    artifacts = _artifact_catalog(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
    )
    vectors = _test_vectors(
        certification_report=certification_report,
        response_envelope=response_envelope,
        semantic_text_attribution_report=semantic_text_attribution_report,
        attribution_exchange=attribution_exchange,
    )
    artifact_names = {entry["name"] for entry in artifacts}
    covered_levels = sorted({vector["level"] for vector in vectors})
    readiness_checks = {
        "all_required_artifacts_bound": set(REQUIRED_VECTOR_ARTIFACTS).issubset(
            artifact_names
        ),
        "certification_reaches_l31": (
            certification_summary.get("status") == "passed"
            and _level_number(str(certification_summary.get("highest_level", ""))) >= 31
        ),
        "response_envelope_verified": response_envelope.get("summary", {}).get("status")
        == "verified",
        "semantic_text_report_ready": semantic_text_attribution_report.get(
            "summary", {}
        ).get("status")
        == "ready",
        "attribution_exchange_ready": attribution_exchange.get("summary", {}).get(
            "cross_provider_ready"
        )
        is True,
        "creator_license_contract_ready": creator_license_contract.get(
            "summary", {}
        ).get("status")
        == "ready",
        "negative_vectors_present": all(
            bool(vector.get("negative_mutations")) for vector in vectors
        ),
        "l32_vector_present": any(vector["level"] == "RDLLM-L32" for vector in vectors),
        "artifact_hashes_reproducible": all(
            entry.get("hash_reproducible") is True for entry in artifacts
        ),
        "vector_schema_declared": "conformance_vector_pack" in VECTOR_SCHEMA_MAP,
        "offline_verifier_declared": "verify-conformance-vector-pack"
        in integration_profile.get("verifier_contract", {}).get(
            "reference_cli_commands", []
        ),
    }
    pack = {
        "vector_pack_version": CONFORMANCE_VECTOR_PACK_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider.get("id", "provider:unspecified"),
            "model_id": provider.get("model_id", "model:unspecified"),
            "model_version": provider.get("model_version", "unknown"),
        },
        "conformance_contract": {
            "profile": "rdllm-reference-conformance-vectors/v1",
            "well_known_path": "/.well-known/rdllm/conformance-vector-pack.json",
            "target_certification_level": "RDLLM-L32",
            "implementation_rule": "providers must reproduce expected public artifacts or fail the listed negative mutations",
            "required_verifier_commands": sorted(
                {vector["verifier_command"] for vector in vectors}
            ),
        },
        "fixture_hashes": _fixture_hashes(fixture_paths),
        "artifact_catalog": artifacts,
        "test_vectors": vectors,
        "schemas": VECTOR_SCHEMA_MAP,
        "commitments": {
            "artifact_catalog_root": hash_payload(artifacts),
            "test_vector_root": hash_payload(vectors),
            "fixture_root": hash_payload(_fixture_hashes(fixture_paths)),
            "schema_root": hash_payload(VECTOR_SCHEMA_MAP),
            "provider_card_hash": provider_card.get("card_hash", ""),
            "certification_report_hash": certification_report.get("report_hash", ""),
            "integration_profile_hash": integration_profile.get("profile_hash", ""),
            "discovery_manifest_hash": discovery_manifest.get("manifest_hash", ""),
            "response_envelope_hash": response_envelope.get("envelope_hash", ""),
            "assurance_bundle_hash": assurance_bundle.get("bundle_hash", ""),
            "semantic_text_attribution_report_hash": semantic_text_attribution_report.get(
                "report_hash", ""
            ),
            "creator_license_contract_hash": creator_license_contract.get(
                "contract_hash", ""
            ),
            "attribution_exchange_hash": attribution_exchange.get("exchange_hash", ""),
            "private_audit_challenge_hash": (
                private_audit_challenge or {}
            ).get("report_hash", ""),
        },
        "readiness_checks": readiness_checks,
        "summary": {
            "status": "ready" if all(readiness_checks.values()) else "failed",
            "target_certification_level": "RDLLM-L32",
            "highest_upstream_level": certification_summary.get("highest_level", ""),
            "artifact_count": len(artifacts),
            "required_artifact_count": len(REQUIRED_VECTOR_ARTIFACTS),
            "test_vector_count": len(vectors),
            "negative_mutation_count": sum(
                len(vector.get("negative_mutations", [])) for vector in vectors
            ),
            "covered_levels": covered_levels,
            "schema_count": len(VECTOR_SCHEMA_MAP),
            "offline_verification_supported": True,
        },
        "privacy": {
            "artifact_payloads_embedded": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "vector_pack_uses_hashes_expected_outcomes_and_mutation_names": True,
        },
    }
    pack["vector_pack_hash"] = hash_payload(_hashable_pack(pack))
    pack["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_pack(pack), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return pack


def validate_conformance_vector_pack_shape(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "vector_pack_version",
        "issuer",
        "created_at",
        "provider",
        "conformance_contract",
        "fixture_hashes",
        "artifact_catalog",
        "test_vectors",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
        "vector_pack_hash",
        "signature",
    )
    for key in required:
        if key not in pack:
            errors.append(f"missing conformance vector pack field: {key}")
    if errors:
        return errors
    if pack.get("vector_pack_version") != CONFORMANCE_VECTOR_PACK_VERSION:
        errors.append("conformance vector pack version is unsupported")
    names = {entry.get("name", "") for entry in pack.get("artifact_catalog", [])}
    for name in REQUIRED_VECTOR_ARTIFACTS:
        if name not in names:
            errors.append(f"missing conformance vector artifact: {name}")
    if "conformance_vector_pack" not in pack.get("schemas", {}):
        errors.append("missing conformance vector pack schema")
    for vector in pack.get("test_vectors", []):
        for key in (
            "vector_id",
            "title",
            "level",
            "artifact",
            "verifier_command",
            "expected",
            "negative_mutations",
            "vector_hash",
        ):
            if key not in vector:
                errors.append(f"missing conformance vector field: {key}")
    return errors


def verify_conformance_vector_pack(
    pack: dict[str, Any],
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    fixture_paths: dict[str, str] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a conformance vector pack against public provider artifacts."""

    errors = validate_conformance_vector_pack_shape(pack)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_pack(pack))
    if expected_hash != pack.get("vector_pack_hash"):
        errors.append("conformance vector pack hash is not reproducible")

    errors.extend(
        f"response envelope: {error}"
        for error in verify_response_envelope(
            response_envelope,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"attribution exchange: {error}"
        for error in verify_attribution_exchange_manifest(
            attribution_exchange,
            provider_card=provider_card,
            certification_report=certification_report,
            integration_profile=integration_profile,
            discovery_manifest=discovery_manifest,
            response_envelope=response_envelope,
            assurance_bundle=assurance_bundle,
            semantic_text_attribution_report=semantic_text_attribution_report,
            creator_license_contract=creator_license_contract,
            training_summary=training_summary,
            provenance_evaluation_report=provenance_evaluation_report,
            counterfactual_report=counterfactual_report,
            media_attribution_report=media_attribution_report,
            model_signal_report=model_signal_report,
            rights_remediation_report=rights_remediation_report,
            source_confidence_report=source_confidence_report,
            citation_footer_contract=citation_footer_contract,
            private_audit_challenge=private_audit_challenge,
            signing_secret=signing_secret,
        )
    )

    expected = make_conformance_vector_pack(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        fixture_paths=fixture_paths,
        issuer=pack.get("issuer", DEFAULT_ISSUER),
        created_at=pack.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider",
        "conformance_contract",
        "fixture_hashes",
        "artifact_catalog",
        "test_vectors",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
    ):
        if expected.get(key) != pack.get(key):
            errors.append(f"conformance vector pack {key} does not match artifacts")
    if expected.get("vector_pack_hash") != pack.get("vector_pack_hash"):
        errors.append("conformance vector pack hash does not match artifacts")

    if pack.get("summary", {}).get("status") != "ready":
        errors.append("conformance vector pack status is not ready")
    for check, passed in pack.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"conformance vector readiness check failed: {check}")
    for vector in pack.get("test_vectors", []):
        vector_copy = dict(vector)
        declared = vector_copy.pop("vector_hash", "")
        if hash_payload(vector_copy) != declared:
            errors.append(f"conformance vector hash is not reproducible: {vector.get('vector_id', '')}")
        if not vector.get("negative_mutations"):
            errors.append(f"conformance vector lacks negative mutations: {vector.get('vector_id', '')}")

    pack_json = canonical_json(pack)
    for field in ("prompt", "output", "source_text", "matched_text"):
        if f'"{field}"' in pack_json:
            errors.append(f"conformance vector pack discloses private {field} field")
    if pack.get("privacy", {}).get(
        "vector_pack_uses_hashes_expected_outcomes_and_mutation_names"
    ) is not True:
        errors.append("conformance vector pack must use hashes, expected outcomes, and mutation names")

    signature = pack.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_pack(pack), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("conformance vector pack is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("conformance vector pack signature is invalid")

    return errors
