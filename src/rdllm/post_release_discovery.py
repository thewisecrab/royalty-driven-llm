"""Post-release discovery reports for late-bound RDLLM output artifacts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.discovery_manifest import DISCOVERY_WELL_KNOWN_PATH, WELL_KNOWN_PATHS
from rdllm.output_provenance_binding import verify_output_provenance_binding_report
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

POST_RELEASE_DISCOVERY_VERSION = "rdllm-post-release-discovery-report/v1"
POST_RELEASE_DISCOVERY_SCHEMA = (
    "docs/schemas/post_release_discovery_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L76"
MINIMUM_OUTPUT_BINDING_LEVEL = "RDLLM-L75"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/post-release-discovery-report.json"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "copied_output",
    "rendered_output",
    "delivered_output",
    "raw_model_output",
    "customer_id",
    "customer_email",
    "secret",
    "signing_secret",
    "private_key",
}

DECLARED_HASH_FIELDS = (
    "post_release_report_hash",
    "binding_report_hash",
    "watchtower_report_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "capsule_hash",
    "graph_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "attestation_hash",
    "bundle_hash",
    "envelope_hash",
    "gate_hash",
    "contract_hash",
    "receipt_hash",
    "event_hash",
)

POST_RELEASE_ARTIFACT_NAMES = (
    "proof_carrying_response",
    "serving_gateway_report",
    "attribution_capsule",
    "watchtower_challenge_settlement_report",
    "output_provenance_binding_report",
    "proof_dependency_graph",
)


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"post_release_report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    if artifact.get("capsule_hash") and isinstance(payload.get("portable_surfaces"), dict):
        surfaces = deepcopy(payload["portable_surfaces"])
        headers = surfaces.get("http_headers")
        if isinstance(headers, dict):
            headers.pop("RDLLM-Capsule-Hash", None)
        payload["portable_surfaces"] = surfaces
    return payload


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if not value:
            continue
        if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
            return hash_payload(artifact["payload"]) == value
        return hash_payload(_hashable_artifact(artifact)) == value
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


def _artifact_entry(
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
    *,
    phase: str,
    required: bool,
    release_subject_hash: str,
) -> dict[str, Any]:
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "well_known_path": (
            DISCOVERY_WELL_KNOWN_PATH
            if name == "discovery_manifest"
            else WELL_KNOWN_PATHS[name]
        ),
        "publication_phase": phase,
        "required": required,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
        "bound_release_subject_hash": release_subject_hash,
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _release_subject(
    *,
    discovery_manifest: dict[str, Any],
    output_provenance_binding_report: dict[str, Any],
    proof_dependency_graph: dict[str, Any],
    integration_profile: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    binding_subject = output_provenance_binding_report.get("binding_subject", {})
    binding_summary = output_provenance_binding_report.get("summary", {})
    graph_summary = proof_dependency_graph.get("summary", {})
    discovery_summary = discovery_manifest.get("summary", {})
    certification_summary = certification_report.get("summary", {})
    subject = {
        "base_discovery_manifest_hash": _declared_hash(discovery_manifest),
        "output_provenance_binding_report_hash": _declared_hash(
            output_provenance_binding_report
        ),
        "proof_dependency_graph_hash": _declared_hash(proof_dependency_graph),
        "integration_profile_hash": _declared_hash(integration_profile),
        "provider_card_hash": _declared_hash(provider_card),
        "certification_report_hash": _declared_hash(certification_report),
        "copied_output_hash": str(binding_subject.get("copied_output_hash", "")),
        "rendered_output_hash": str(binding_subject.get("rendered_output_hash", "")),
        "output_binding_subject_hash": str(binding_subject.get("subject_hash", "")),
        "output_binding_status": str(binding_summary.get("status", "")),
        "output_binding_target_certification_level": str(
            binding_summary.get("target_certification_level", "")
        ),
        "proof_graph_status": str(graph_summary.get("status", "")),
        "proof_graph_target_certification_level": str(
            graph_summary.get("target_certification_level", "")
        ),
        "base_discovery_status": str(discovery_summary.get("status", "")),
        "base_discovery_highest_level": str(discovery_summary.get("highest_level", "")),
        "certification_highest_level": str(
            certification_summary.get("highest_level", "")
        ),
    }
    subject["release_subject_hash"] = hash_payload(subject)
    return subject


def _artifact_catalog(
    *,
    release_subject_hash: str,
    discovery_manifest: dict[str, Any],
    output_provenance_binding_report: dict[str, Any],
    proof_dependency_graph: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    integration_profile: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
) -> list[dict[str, Any]]:
    specs = [
        (
            "discovery_manifest",
            "rdllm-discovery-manifest/v1",
            discovery_manifest,
            "pre_release",
        ),
        (
            "integration_profile",
            "rdllm-integration-profile/v1",
            integration_profile,
            "pre_release",
        ),
        (
            "provider_attribution_card",
            "rdllm-provider-attribution-card/v1",
            provider_card,
            "pre_release",
        ),
        (
            "certification_report",
            "rdllm-certification/v1",
            certification_report,
            "pre_release",
        ),
        (
            "proof_carrying_response",
            "rdllm-proof-carrying-response/v1",
            proof_carrying_response,
            "post_release",
        ),
        (
            "serving_gateway_report",
            "rdllm-serving-gateway-report/v1",
            serving_gateway_report,
            "post_release",
        ),
        (
            "attribution_capsule",
            "rdllm-attribution-capsule/v1",
            attribution_capsule,
            "post_release",
        ),
        (
            "watchtower_challenge_settlement_report",
            "rdllm-watchtower-challenge-settlement-report/v1",
            watchtower_challenge_settlement_report,
            "post_release",
        ),
        (
            "output_provenance_binding_report",
            "rdllm-output-provenance-binding-report/v1",
            output_provenance_binding_report,
            "post_release",
        ),
        (
            "proof_dependency_graph",
            "rdllm-proof-dependency-graph/v1",
            proof_dependency_graph,
            "post_release",
        ),
    ]
    return [
        _artifact_entry(
            name,
            artifact_type,
            payload,
            phase=phase,
            required=True,
            release_subject_hash=release_subject_hash,
        )
        for name, artifact_type, payload, phase in specs
    ]


def _graph_node_names(proof_dependency_graph: dict[str, Any]) -> set[str]:
    return {
        str(node.get("name", ""))
        for node in proof_dependency_graph.get("artifacts", [])
        if isinstance(node, dict)
    }


def _verification_rows(subject: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "surface": "post_release_discovery_report",
            "path": DEFAULT_WELL_KNOWN_PATH,
            "verifier_command": "verify-post-release-discovery-report",
            "bound_release_subject_hash": subject["release_subject_hash"],
            "required": True,
        },
        {
            "surface": "output_provenance_binding_report",
            "path": WELL_KNOWN_PATHS["output_provenance_binding_report"],
            "verifier_command": "verify-output-provenance-binding-report",
            "bound_release_subject_hash": subject["release_subject_hash"],
            "required": True,
        },
        {
            "surface": "proof_dependency_graph",
            "path": WELL_KNOWN_PATHS["proof_dependency_graph"],
            "verifier_command": "verify-proof-dependency-graph",
            "bound_release_subject_hash": subject["release_subject_hash"],
            "required": True,
        },
        {
            "surface": "base_discovery_manifest",
            "path": DISCOVERY_WELL_KNOWN_PATH,
            "verifier_command": "verify-discovery-manifest",
            "bound_release_subject_hash": subject["release_subject_hash"],
            "required": True,
        },
    ]
    for row in rows:
        row["verification_row_hash"] = hash_payload(row)
    return rows


def make_post_release_discovery_report(
    *,
    discovery_manifest: dict[str, Any],
    output_provenance_binding_report: dict[str, Any],
    proof_dependency_graph: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    integration_profile: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Publish late-bound output proof artifacts without mutating base discovery."""

    subject = _release_subject(
        discovery_manifest=discovery_manifest,
        output_provenance_binding_report=output_provenance_binding_report,
        proof_dependency_graph=proof_dependency_graph,
        integration_profile=integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    catalog = _artifact_catalog(
        release_subject_hash=subject["release_subject_hash"],
        discovery_manifest=discovery_manifest,
        output_provenance_binding_report=output_provenance_binding_report,
        proof_dependency_graph=proof_dependency_graph,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        integration_profile=integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
    )
    output_binding_errors = verify_output_provenance_binding_report(
        output_provenance_binding_report,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=signing_secret,
    )
    graph_nodes = _graph_node_names(proof_dependency_graph)
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    channels = provider_card.get("supported_evidence_channels", {})
    integration_schemas = integration_profile.get("schemas", {})
    integration_surfaces = integration_profile.get("public_surfaces", {})
    discovery_schemas = discovery_manifest.get("schemas", {})
    discovery_paths = discovery_manifest.get("discovery", {})
    catalog_names = {entry["name"] for entry in catalog}
    post_release_entries = [
        entry for entry in catalog if entry["publication_phase"] == "post_release"
    ]
    private_findings = _contains_private_fields(
        {
            "release_subject": subject,
            "artifact_catalog": catalog,
            "verification_rows": _verification_rows(subject),
        }
    )
    checks = {
        "base_discovery_manifest_ready": subject["base_discovery_status"] == "ready",
        "base_discovery_declares_post_release_surface": (
            discovery_schemas.get("post_release_discovery_report")
            == POST_RELEASE_DISCOVERY_SCHEMA
            and discovery_paths.get("post_release_discovery_report_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "base_discovery_declares_output_binding_surface": (
            discovery_schemas.get("output_provenance_binding_report")
            == "docs/schemas/output_provenance_binding_report.schema.json"
            and discovery_paths.get("output_provenance_binding_report_path")
            == WELL_KNOWN_PATHS["output_provenance_binding_report"]
        ),
        "output_provenance_binding_verified": not output_binding_errors,
        "output_provenance_binding_ready": (
            subject["output_binding_status"] == "ready"
            and _level_number(subject["output_binding_target_certification_level"])
            >= _level_number(MINIMUM_OUTPUT_BINDING_LEVEL)
        ),
        "proof_dependency_graph_ready": (
            subject["proof_graph_status"] == "ready"
            and _artifact_hash_is_reproducible(proof_dependency_graph)
        ),
        "proof_dependency_graph_contains_late_artifacts": set(
            POST_RELEASE_ARTIFACT_NAMES[:-1]
        ).issubset(graph_nodes),
        "all_late_artifacts_cataloged": set(POST_RELEASE_ARTIFACT_NAMES).issubset(
            catalog_names
        ),
        "late_artifact_hashes_reproducible": all(
            entry["hash_reproducible"] for entry in post_release_entries
        ),
        "publication_entries_bind_release_subject": all(
            entry["bound_release_subject_hash"] == subject["release_subject_hash"]
            for entry in catalog
        ),
        "provider_declares_post_release_discovery_surface": public_surfaces.get(
            "post_release_discovery_report"
        )
        is True,
        "provider_declares_post_release_discovery_channel": channels.get(
            "post_release_discovery"
        )
        is True,
        "integration_declares_post_release_schema_and_surface": (
            integration_schemas.get("post_release_discovery_report")
            == POST_RELEASE_DISCOVERY_SCHEMA
            and integration_surfaces.get("post_release_discovery_report") is True
        ),
        "certification_level_at_least_l75": (
            certification_report.get("summary", {}).get("status") == "passed"
            and _level_number(subject["certification_highest_level"])
            >= _level_number(MINIMUM_OUTPUT_BINDING_LEVEL)
        ),
        "self_catalog_cycle_absent": "post_release_discovery_report"
        not in catalog_names,
        "public_report_has_no_private_field_names": not private_findings,
    }
    ready = all(checks.values())
    verification_rows = _verification_rows(subject)
    report: dict[str, Any] = {
        "report_version": POST_RELEASE_DISCOVERY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-post-release-discovery-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_output_binding_level": MINIMUM_OUTPUT_BINDING_LEVEL,
            "two_phase_publication_required": True,
            "base_manifest_must_not_be_mutated_after_release": True,
            "self_hash_excluded_from_artifact_catalog": True,
            "late_artifacts_required": list(POST_RELEASE_ARTIFACT_NAMES),
        },
        "release_subject": subject,
        "artifact_catalog": {
            "artifact_count": len(catalog),
            "post_release_artifact_count": len(post_release_entries),
            "artifact_root": merkle_root([entry["entry_hash"] for entry in catalog]),
            "entries": catalog,
        },
        "publication_plan": {
            "base_manifest_path": DISCOVERY_WELL_KNOWN_PATH,
            "post_release_report_path": DEFAULT_WELL_KNOWN_PATH,
            "publication_sequence": [
                "publish_base_discovery_manifest",
                "release_proof_carrying_response",
                "publish_output_provenance_binding_report",
                "publish_post_release_discovery_report",
            ],
            "base_manifest_mutation_required": False,
            "hash_cycle_prevented": True,
        },
        "verification": {
            "output_provenance_binding_errors": output_binding_errors,
            "graph_node_count": len(graph_nodes),
            "verification_rows": verification_rows,
        },
        "commitments": {
            "release_subject_hash": subject["release_subject_hash"],
            "artifact_root": merkle_root([entry["entry_hash"] for entry in catalog]),
            "verification_root": merkle_root(
                [row["verification_row_hash"] for row in verification_rows]
            ),
            "schema": POST_RELEASE_DISCOVERY_SCHEMA,
        },
        "checks": checks,
        "schemas": {
            "post_release_discovery_report": POST_RELEASE_DISCOVERY_SCHEMA,
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "output_provenance_binding_report": "docs/schemas/output_provenance_binding_report.schema.json",
            "proof_dependency_graph": "docs/schemas/proof_dependency_graph.schema.json",
            "proof_carrying_response": "docs/schemas/proof_carrying_response.schema.json",
            "serving_gateway_report": "docs/schemas/serving_gateway_report.schema.json",
            "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
            "watchtower_challenge_settlement_report": "docs/schemas/watchtower_challenge_settlement_report.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "release_subject_hash": subject["release_subject_hash"],
            "copied_output_hash": subject["copied_output_hash"],
            "artifact_count": len(catalog),
            "post_release_artifact_count": len(post_release_entries),
            "base_manifest_mutation_required": False,
            "hash_cycle_prevented": True,
            "raw_output_text_disclosed": False,
            "offline_verification_supported": True,
        },
        "privacy": {
            "raw_output_text_disclosed": False,
            "prompt_text_disclosed": False,
            "source_text_disclosed": False,
            "artifact_payloads_embedded": False,
            "report_uses_hashes_paths_and_release_subjects": True,
            "private_field_findings": private_findings,
        },
    }
    report["post_release_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_post_release_discovery_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "release_subject",
        "artifact_catalog",
        "publication_plan",
        "verification",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "post_release_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing post-release discovery field: {key}")
    if errors:
        return errors
    if report.get("report_version") != POST_RELEASE_DISCOVERY_VERSION:
        errors.append("post-release discovery version is unsupported")
    if report.get("schemas", {}).get("post_release_discovery_report") != (
        POST_RELEASE_DISCOVERY_SCHEMA
    ):
        errors.append("post-release discovery schema is not declared")
    for entry in report.get("artifact_catalog", {}).get("entries", []):
        for key in (
            "name",
            "artifact_type",
            "well_known_path",
            "publication_phase",
            "required",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "bound_release_subject_hash",
            "entry_hash",
        ):
            if key not in entry:
                errors.append(f"missing post-release catalog field: {key}")
    return errors


def verify_post_release_discovery_report(
    report: dict[str, Any],
    *,
    discovery_manifest: dict[str, Any],
    output_provenance_binding_report: dict[str, Any],
    proof_dependency_graph: dict[str, Any],
    proof_carrying_response: dict[str, Any],
    serving_gateway_report: dict[str, Any],
    attribution_capsule: dict[str, Any],
    watchtower_challenge_settlement_report: dict[str, Any],
    integration_profile: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a post-release discovery report against published proof artifacts."""

    errors = validate_post_release_discovery_report_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get("post_release_report_hash"):
        errors.append("post-release discovery hash is not reproducible")

    expected = make_post_release_discovery_report(
        discovery_manifest=discovery_manifest,
        output_provenance_binding_report=output_provenance_binding_report,
        proof_dependency_graph=proof_dependency_graph,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        integration_profile=integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "release_subject",
        "artifact_catalog",
        "publication_plan",
        "verification",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"post-release discovery {key} does not match artifacts")
    if expected.get("post_release_report_hash") != report.get("post_release_report_hash"):
        errors.append("post-release discovery hash does not match artifacts")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("post-release discovery status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"post-release discovery check failed: {check}")

    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append(
            "post-release discovery exposes private fields: "
            + ", ".join(private_paths[:5])
        )

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("post-release discovery is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("post-release discovery signature is invalid")

    return errors
