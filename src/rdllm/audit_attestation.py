"""Independent audit attestations for RDLLM proof packs."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.assurance import validate_assurance_bundle_shape, verify_assurance_bundle
from rdllm.citation_footer import verify_citation_footer_contract
from rdllm.discovery_manifest import validate_discovery_manifest_shape, verify_discovery_manifest
from rdllm.integration_profile import verify_integration_profile
from rdllm.payment_execution import verify_payment_execution_report
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.remittance import verify_remittance_report
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_confidence import verify_source_confidence_report

AUDIT_ATTESTATION_VERSION = "rdllm-third-party-audit-attestation/v1"
AUDIT_ATTESTATION_SCHEMA = "docs/schemas/audit_attestation.schema.json"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "attestation_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "contract_hash",
    "bundle_hash",
    "envelope_hash",
    "statement_hash",
    "trace_hash",
    "receipt_hash",
    "summary_hash",
    "attestation_hash",
)

REQUIRED_ASSURANCE_TYPES = {
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "response_envelope",
    "source_confidence_report",
    "citation_footer_contract",
}

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "quote",
    "evidence_text",
    "matched_text",
    "source_text",
    "payout_account",
    "bank_account",
    "customer_id",
    "invoice_text",
    "raw_finance_record",
    "raw_billing_record",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
}


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key not in {"attestation_hash", "signature"}
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


def _artifact_row(name: str, artifact_type: str, artifact: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(artifact),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
    }
    row["artifact_row_hash"] = hash_payload(row)
    return row


def _artifact_rows(artifacts: dict[str, tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        _artifact_row(name, artifact_type, artifact)
        for name, (artifact_type, artifact) in sorted(artifacts.items())
    ]


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


def _money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _readiness_checks(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    certification_attestation: dict[str, Any] | None,
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any] | None,
    payment_processor_records: list[dict[str, Any]] | None,
    revenue_allocation_report: dict[str, Any] | None,
    finance_ledger_attestation: dict[str, Any] | None,
    auditor_id: str,
) -> dict[str, bool]:
    cert_summary = certification_report.get("summary", {})
    provider = provider_card.get("provider", {})
    provider_cert = provider_card.get("certification", {})
    assurance_types = set(assurance_bundle.get("summary", {}).get("artifact_types", []))
    source_taxonomy = source_confidence_report.get("hallucination_taxonomy", {})
    clearing_summary = clearinghouse_report.get("summary", {})
    remittance_summary = remittance_report.get("summary", {})
    payment_execution_summary = (payment_execution_report or {}).get("summary", {})
    revenue_allocation_summary = (revenue_allocation_report or {}).get("summary", {})
    finance_ledger_summary = (finance_ledger_attestation or {}).get("summary", {})
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    schemas = integration_profile.get("schemas", {})
    verifier_commands = set(
        integration_profile.get("verifier_contract", {}).get(
            "reference_cli_commands",
            [],
        )
    )
    artifact_catalog_names = {
        str(row.get("name", ""))
        for row in discovery_manifest.get("artifact_catalog", [])
    }
    required_catalog_artifacts = {
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
        "response_envelope",
        "assurance_bundle",
    }
    required_assurance_types = set(REQUIRED_ASSURANCE_TYPES)
    if certification_attestation is not None:
        required_catalog_artifacts.add("certification_attestation")
    else:
        required_assurance_types.discard("certification_attestation")
    clearing_total = _money(clearing_summary.get("accounted_total", "0"))
    remittance_total = _money(remittance_summary.get("accounted_total", "0"))
    embedded = response_envelope.get("embedded_artifacts", {})
    assurance_artifacts = [
        ("certification", "certification_report", certification_report),
        ("provider_card", "provider_attribution_card", provider_card),
        ("integration_profile", "integration_profile", integration_profile),
        ("response_envelope", "response_envelope", response_envelope),
        ("source_confidence", "source_confidence_report", source_confidence_report),
        ("citation_footer", "citation_footer_contract", citation_footer_contract),
        ("clearinghouse", "clearinghouse_report", clearinghouse_report),
        ("remittance", "remittance_report", remittance_report),
    ]
    if payment_execution_report is not None:
        assurance_artifacts.append(
            (
                "payment_execution_report",
                "payment_execution_report",
                payment_execution_report,
            )
        )
    if revenue_allocation_report is not None:
        assurance_artifacts.append(
            (
                "revenue_allocation",
                "revenue_allocation_report",
                revenue_allocation_report,
            )
        )
    if finance_ledger_attestation is not None:
        assurance_artifacts.append(
            (
                "finance_ledger",
                "finance_ledger_attestation",
                finance_ledger_attestation,
            )
        )
    response_replay_errors = verify_response_envelope(response_envelope)
    source_confidence_replay_errors = verify_source_confidence_report(
        source_confidence_report,
        answer_card=embedded.get("answer_provenance_card", {}),
        source_verification_report=embedded.get("source_verification_report", {}),
        creator_license_contract=embedded.get("creator_license_contract"),
    )
    footer_replay_errors = verify_citation_footer_contract(
        citation_footer_contract,
        response_envelope=response_envelope,
    )
    if int(assurance_bundle.get("summary", {}).get("artifact_count", 0) or 0) == len(
        assurance_artifacts
    ):
        assurance_replay_errors = verify_assurance_bundle(
            assurance_artifacts,
            assurance_bundle,
        )
    else:
        assurance_replay_errors = validate_assurance_bundle_shape(assurance_bundle)
        if not _artifact_hash_is_reproducible(assurance_bundle):
            assurance_replay_errors.append("assurance bundle hash is not reproducible")
    profile_assurance = (
        assurance_bundle
        if integration_profile.get("bound_artifacts", {}).get("assurance_bundle_hash")
        else None
    )
    integration_replay_errors = verify_integration_profile(
        integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
        response_envelope=response_envelope,
        assurance_bundle=profile_assurance,
        certification_attestation=certification_attestation,
    )
    if int(discovery_manifest.get("summary", {}).get("artifact_count", 0) or 0) <= 10:
        discovery_replay_errors = verify_discovery_manifest(
            discovery_manifest,
            provider_card=provider_card,
            certification_report=certification_report,
            integration_profile=integration_profile,
            response_envelope=response_envelope,
            assurance_bundle=assurance_bundle,
            source_confidence_report=source_confidence_report,
            citation_footer_contract=citation_footer_contract,
            clearinghouse_report=clearinghouse_report,
            remittance_report=remittance_report,
            payment_execution_report=payment_execution_report,
            revenue_allocation_report=revenue_allocation_report,
            finance_ledger_attestation=finance_ledger_attestation,
        )
    else:
        discovery_replay_errors = validate_discovery_manifest_shape(discovery_manifest)
        if not _artifact_hash_is_reproducible(discovery_manifest):
            discovery_replay_errors.append("discovery manifest hash is not reproducible")
    remittance_replay_errors = verify_remittance_report(
        remittance_report,
        clearinghouse_report=clearinghouse_report,
        creator_license_contract=embedded.get("creator_license_contract", {}),
    )
    if payment_execution_report is None:
        payment_execution_replay_errors: list[str] = []
    elif payment_processor_records is None:
        payment_execution_replay_errors = [
            "payment execution processor records missing"
        ]
    else:
        payment_execution_replay_errors = verify_payment_execution_report(
            payment_execution_report,
            remittance_report=remittance_report,
            processor_records=payment_processor_records,
        )
    return {
        "auditor_identity_separate_from_provider": bool(auditor_id)
        and auditor_id != provider.get("id", ""),
        "certification_passed_l44_or_better": cert_summary.get("status") == "passed"
        and _level_number(str(cert_summary.get("highest_level", ""))) >= 44
        and int(cert_summary.get("failed", 0) or 0) == 0,
        "provider_card_bound_to_certification": provider_cert.get("report_hash")
        == certification_report.get("report_hash")
        and _level_number(str(provider_cert.get("highest_level", ""))) >= 44,
        "integration_profile_ready": integration_profile.get("summary", {}).get("status")
        == "ready"
        and "audit_attestation" in schemas
        and "verify-audit-attestation" in verifier_commands,
        "discovery_manifest_ready": discovery_manifest.get("summary", {}).get("status")
        == "ready"
        and discovery_manifest.get("discovery", {}).get("audit_attestation_path", "")
        == "/.well-known/rdllm/audit-attestation.json",
        "provider_declares_audit_attestation_surface": public_surfaces.get(
            "audit_attestation"
        )
        is True,
        "discovery_catalogs_required_provider_artifacts": required_catalog_artifacts.issubset(
            artifact_catalog_names
        ),
        "assurance_bundle_includes_required_artifact_types": required_assurance_types.issubset(
            assurance_types
        ),
        "response_envelope_verified": response_envelope.get("summary", {}).get("status")
        == "verified",
        "source_confidence_verified_without_suppression": source_confidence_report.get(
            "summary", {}
        ).get("status")
        == "verified"
        and int(source_confidence_report.get("summary", {}).get("hallucination_issue_count", 0) or 0)
        == 0
        and int(source_taxonomy.get("attribution_suppression_count", 0) or 0) == 0,
        "citation_footer_contract_verified": citation_footer_contract.get("summary", {}).get(
            "status"
        )
        == "verified",
        "clearinghouse_ready_and_duplicate_safe": clearing_summary.get("status") == "ready"
        and clearing_summary.get("double_payment_prevented") is True,
        "remittance_ready_instruction_only": remittance_summary.get("status") == "ready"
        and remittance_summary.get("instruction_only") is True
        and remittance_report.get("remittance_policy", {}).get("payment_execution_mode")
        == "instruction_only",
        "remittance_matches_clearinghouse_accounted_total": remittance_total
        == clearing_total,
        "payment_execution_optional_or_ready": (
            payment_execution_report is None
            or (
                payment_execution_summary.get("status") == "ready"
                and payment_execution_summary.get("target_certification_level")
                == "RDLLM-L77"
                and payment_execution_summary.get("external_payment_execution_attested")
                is True
            )
        ),
        "payment_execution_optional_or_matches_remittance_total": (
            payment_execution_report is None
            or _money(payment_execution_summary.get("expected_remittance_total", "0"))
            == remittance_total
        ),
        "revenue_allocation_optional_or_ready": (
            revenue_allocation_report is None
            or (
                revenue_allocation_summary.get("status") == "ready"
                and revenue_allocation_summary.get("target_certification_level")
                == "RDLLM-L46"
            )
        ),
        "finance_ledger_attestation_optional_or_ready": (
            finance_ledger_attestation is None
            or (
                finance_ledger_summary.get("status") == "ready"
                and finance_ledger_summary.get("target_certification_level")
                == "RDLLM-L47"
            )
        ),
        "response_envelope_public_replay_verified": not response_replay_errors,
        "source_confidence_public_replay_verified": not source_confidence_replay_errors,
        "citation_footer_public_replay_verified": not footer_replay_errors,
        "assurance_bundle_public_replay_verified": not assurance_replay_errors,
        "integration_profile_public_replay_verified": not integration_replay_errors,
        "discovery_manifest_public_replay_verified": not discovery_replay_errors,
        "remittance_public_replay_verified": not remittance_replay_errors,
        "payment_execution_public_replay_optional_or_verified": (
            payment_execution_report is None or not payment_execution_replay_errors
        ),
        "artifact_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                provider_card,
                certification_report,
                integration_profile,
                discovery_manifest,
                assurance_bundle,
                response_envelope,
                source_confidence_report,
                citation_footer_contract,
                clearinghouse_report,
                remittance_report,
                payment_execution_report or {},
                revenue_allocation_report or {},
                finance_ledger_attestation or {},
            )
        ),
    }


def make_audit_attestation(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    certification_attestation: dict[str, Any] | None = None,
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any] | None = None,
    payment_processor_records: list[dict[str, Any]] | None = None,
    revenue_allocation_report: dict[str, Any] | None = None,
    finance_ledger_attestation: dict[str, Any] | None = None,
    auditor_id: str,
    auditor_name: str = "",
    verifier_id: str = "rdllm-reference-verifier",
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    audit_period_start: str = "",
    audit_period_end: str = "",
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an independent, hash-only attestation over a public proof pack."""

    artifacts = {
        "provider_attribution_card": (
            "rdllm-provider-attribution-card/v1",
            provider_card,
        ),
        "certification_report": ("rdllm-certification/v1", certification_report),
        "integration_profile": ("rdllm-integration-profile/v1", integration_profile),
        "discovery_manifest": ("rdllm-discovery-manifest/v1", discovery_manifest),
        "assurance_bundle": ("rdllm-assurance-bundle/v1", assurance_bundle),
        "response_envelope": ("rdllm-response-envelope/v1", response_envelope),
        "source_confidence_report": (
            "rdllm-source-confidence-report/v1",
            source_confidence_report,
        ),
        "citation_footer_contract": (
            "rdllm-citation-footer-contract/v1",
            citation_footer_contract,
        ),
        "clearinghouse_report": (
            "rdllm-clearinghouse-report/v1",
            clearinghouse_report,
        ),
        "remittance_report": ("rdllm-remittance-report/v1", remittance_report),
    }
    if payment_execution_report is not None:
        artifacts["payment_execution_report"] = (
            "rdllm-payment-execution-report/v1",
            payment_execution_report,
        )
    if certification_attestation is not None:
        artifacts["certification_attestation"] = (
            "rdllm-certification-attestation/v1",
            certification_attestation,
        )
    if revenue_allocation_report is not None:
        artifacts["revenue_allocation_report"] = (
            "rdllm-revenue-allocation-report/v1",
            revenue_allocation_report,
        )
    if finance_ledger_attestation is not None:
        artifacts["finance_ledger_attestation"] = (
            "rdllm-finance-ledger-attestation/v1",
            finance_ledger_attestation,
        )
    rows = _artifact_rows(artifacts)
    checks = _readiness_checks(
        provider_card=provider_card,
        certification_report=certification_report,
        certification_attestation=certification_attestation,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        assurance_bundle=assurance_bundle,
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_processor_records=payment_processor_records,
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        auditor_id=auditor_id,
    )
    status = "attested" if all(checks.values()) else "failed"
    audit_scope = {
        "profile": "rdllm-independent-audit/v1",
        "target_certification_level": "RDLLM-L45",
        "minimum_input_level": "RDLLM-L44",
        "audit_period_start": audit_period_start,
        "audit_period_end": audit_period_end,
        "provider_id": provider_card.get("provider", {}).get("id", ""),
        "model_id": provider_card.get("provider", {}).get("model_id", ""),
        "model_version": provider_card.get("provider", {}).get("model_version", ""),
        "auditor_id": auditor_id,
        "auditor_name": auditor_name,
        "verifier_id": verifier_id,
        "auditor_must_be_independent_of_provider": True,
        "provider_self_attestation_only": False,
    }
    required_cli_verifiers = [
        "verify-provider-card",
        "verify-certification-attestation",
        "verify-integration-profile",
        "verify-discovery-manifest",
        "verify-assurance-bundle",
        "verify-response-envelope",
        "verify-source-confidence-report",
        "verify-citation-footer-contract",
        "verify-clearinghouse-report",
        "verify-remittance-report",
        "verify-audit-attestation",
        "verify-revenue-allocation-report",
        "verify-finance-ledger-attestation",
    ]
    required_negative_controls = [
        "stale_certification_hash",
        "stale_certification_attestation_hash",
        "missing_assurance_artifact",
        "response_hash_drift",
        "footer_suppression",
        "remittance_amount_drift",
        "revenue_allocation_amount_drift",
        "finance_ledger_amount_drift",
    ]
    if payment_execution_report is not None:
        required_cli_verifiers.append("verify-payment-execution-report")
        required_negative_controls.append("payment_execution_amount_drift")
    attestation = {
        "attestation_version": AUDIT_ATTESTATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "audit_scope": audit_scope,
        "audited_artifacts": rows,
        "readiness_checks": checks,
        "verifier_contract": {
            "offline_replay_required": True,
            "reference_verifier_id": verifier_id,
            "minimum_required_artifact_count": len(rows),
            "required_cli_verifiers": required_cli_verifiers,
            "required_negative_controls": required_negative_controls,
        },
        "commitments": {
            "artifact_root": hash_payload(rows),
            "readiness_root": hash_payload(checks),
            "audit_scope_hash": hash_payload(audit_scope),
            "provider_card_hash": provider_card.get("card_hash", ""),
            "certification_report_hash": certification_report.get("report_hash", ""),
            "certification_attestation_hash": (
                (certification_attestation or {}).get("attestation_hash", "")
            ),
            "integration_profile_hash": integration_profile.get("profile_hash", ""),
            "discovery_manifest_hash": discovery_manifest.get("manifest_hash", ""),
            "assurance_bundle_hash": assurance_bundle.get("bundle_hash", ""),
            "assurance_bundle_root": assurance_bundle.get("summary", {}).get("root", ""),
            "response_envelope_hash": response_envelope.get("envelope_hash", ""),
            "clearinghouse_report_hash": clearinghouse_report.get("report_hash", ""),
            "remittance_report_hash": remittance_report.get("report_hash", ""),
            "payment_execution_report_hash": (
                (payment_execution_report or {}).get("report_hash", "")
            ),
            "revenue_allocation_report_hash": (
                (revenue_allocation_report or {}).get("report_hash", "")
            ),
            "finance_ledger_attestation_hash": (
                (finance_ledger_attestation or {}).get("attestation_hash", "")
            ),
        },
        "summary": {
            "status": status,
            "target_certification_level": "RDLLM-L45",
            "audited_artifact_count": len(rows),
            "passed_check_count": sum(1 for passed in checks.values() if passed),
            "failed_check_count": sum(1 for passed in checks.values() if not passed),
            "highest_provider_level": provider_card.get("certification", {}).get(
                "highest_level",
                "",
            ),
            "provider_self_attestation_only": False,
            "independent_audit_supported": True,
            "payment_execution_audited": payment_execution_report is not None,
        },
        "privacy": {
            "artifact_payloads_embedded": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "payout_account_disclosed": False,
            "attestation_uses_hashes_statuses_and_counts": True,
        },
        "schemas": {
            "audit_attestation": AUDIT_ATTESTATION_SCHEMA,
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "certification_report": "docs/schemas/certification_report.schema.json",
            "certification_attestation": "docs/schemas/certification_attestation.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "assurance_bundle": "docs/schemas/assurance_bundle.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "clearinghouse_report": "docs/schemas/clearinghouse_report.schema.json",
            "remittance_report": "docs/schemas/remittance_report.schema.json",
            "payment_execution_report": "docs/schemas/payment_execution_report.schema.json",
            "revenue_allocation_report": "docs/schemas/revenue_allocation_report.schema.json",
            "finance_ledger_attestation": "docs/schemas/finance_ledger_attestation.schema.json",
        },
    }
    private_paths = _contains_private_fields(attestation)
    if private_paths:
        attestation["readiness_checks"]["private_fields_absent"] = False
        attestation["summary"]["private_field_paths"] = private_paths
    else:
        attestation["readiness_checks"]["private_fields_absent"] = True
    attestation["summary"]["status"] = (
        "attested"
        if all(attestation["readiness_checks"].values())
        else "failed"
    )
    attestation["summary"]["passed_check_count"] = sum(
        1 for passed in attestation["readiness_checks"].values() if passed
    )
    attestation["summary"]["failed_check_count"] = sum(
        1 for passed in attestation["readiness_checks"].values() if not passed
    )
    attestation["attestation_hash"] = hash_payload(_hashable_attestation(attestation))
    attestation["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_attestation(attestation), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return attestation


def validate_audit_attestation_shape(attestation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "attestation_version",
        "issuer",
        "created_at",
        "audit_scope",
        "audited_artifacts",
        "readiness_checks",
        "verifier_contract",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "attestation_hash",
        "signature",
    )
    for key in required:
        if key not in attestation:
            errors.append(f"missing audit attestation field: {key}")
    if errors:
        return errors
    if attestation.get("attestation_version") != AUDIT_ATTESTATION_VERSION:
        errors.append("audit attestation version is unsupported")
    for key in (
        "target_certification_level",
        "minimum_input_level",
        "provider_id",
        "auditor_id",
        "verifier_id",
    ):
        if key not in attestation.get("audit_scope", {}):
            errors.append(f"missing audit scope field: {key}")
    for row in attestation.get("audited_artifacts", []):
        for key in (
            "name",
            "artifact_type",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "artifact_row_hash",
        ):
            if key not in row:
                errors.append(f"missing audited artifact field: {key}")
    for key in (
        "artifact_root",
        "readiness_root",
        "audit_scope_hash",
        "provider_card_hash",
        "certification_report_hash",
        "certification_attestation_hash",
        "discovery_manifest_hash",
        "assurance_bundle_hash",
        "response_envelope_hash",
        "clearinghouse_report_hash",
        "remittance_report_hash",
        "payment_execution_report_hash",
        "revenue_allocation_report_hash",
        "finance_ledger_attestation_hash",
    ):
        if key not in attestation.get("commitments", {}):
            errors.append(f"missing audit commitment: {key}")
    if "audit_attestation" not in attestation.get("schemas", {}):
        errors.append("missing audit attestation schema")
    return errors


def verify_audit_attestation(
    attestation: dict[str, Any],
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    certification_attestation: dict[str, Any] | None = None,
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    response_envelope: dict[str, Any],
    source_confidence_report: dict[str, Any],
    citation_footer_contract: dict[str, Any],
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any] | None = None,
    payment_processor_records: list[dict[str, Any]] | None = None,
    revenue_allocation_report: dict[str, Any] | None = None,
    finance_ledger_attestation: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an independent audit attestation against public RDLLM artifacts."""

    errors = validate_audit_attestation_shape(attestation)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_attestation(attestation))
    if expected_hash != attestation.get("attestation_hash"):
        errors.append("audit attestation hash is not reproducible")

    scope = attestation.get("audit_scope", {})
    expected = make_audit_attestation(
        provider_card=provider_card,
        certification_report=certification_report,
        certification_attestation=certification_attestation,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        assurance_bundle=assurance_bundle,
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_processor_records=payment_processor_records,
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        auditor_id=str(scope.get("auditor_id", "")),
        auditor_name=str(scope.get("auditor_name", "")),
        verifier_id=str(scope.get("verifier_id", "rdllm-reference-verifier")),
        issuer=attestation.get("issuer", DEFAULT_ISSUER),
        created_at=attestation.get("created_at", ""),
        audit_period_start=str(scope.get("audit_period_start", "")),
        audit_period_end=str(scope.get("audit_period_end", "")),
        signing_secret=signing_secret,
    )
    for key in (
        "audit_scope",
        "audited_artifacts",
        "readiness_checks",
        "verifier_contract",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != attestation.get(key):
            errors.append(f"audit attestation {key} does not match public artifacts")
    if expected.get("attestation_hash") != attestation.get("attestation_hash"):
        errors.append("audit attestation hash does not match public artifacts")
    if attestation.get("summary", {}).get("status") != "attested":
        errors.append("audit attestation status is not attested")
    for check, passed in attestation.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"audit readiness check failed: {check}")
    if attestation.get("summary", {}).get("provider_self_attestation_only") is not False:
        errors.append("audit attestation must not be provider-self-attestation-only")
    if attestation.get("privacy", {}).get("artifact_payloads_embedded") is not False:
        errors.append("audit attestation must not embed artifact payloads")
    if _contains_private_fields(attestation):
        errors.append("audit attestation exposes private fields")

    signature = attestation.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_attestation(attestation), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("audit attestation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("audit attestation signature is invalid")
    return errors
