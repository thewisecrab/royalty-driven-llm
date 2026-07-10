"""Audit RDLLM production-readiness controls for open-source operators."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.production_readiness import (  # noqa: E402
    REPOSITORY_REPORT_SCHEMA,
    evaluate_production_profile,
    load_json,
    render_repository_verification_text,
    repository_readiness_report_hash,
    required_profile_control_count,
    verify_repository_readiness_report,
    verify_production_readiness_report,
)
from rdllm.operator_acceptance_matrix import run_acceptance_matrix  # noqa: E402
from production_profile_matrix import audit as audit_profile_matrix  # noqa: E402


REQUIRED_OPERATOR_DOCS = (
    "docs/deployment.md",
    "docs/service_api.md",
    "docs/production_readiness.md",
    "docs/operator_runbook.md",
    "docs/provider_onboarding.md",
    "docs/provider_compatibility_matrix.md",
    "docs/release_checklist.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "artifacts/README.md",
)

REQUIRED_DOC_TERMS = {
    "docs/production_readiness.md": (
        "NIST AI RMF",
        "NIST SSDF",
        "OWASP",
        "SLSA",
        "individual",
        "company",
        "institution",
        "government",
        "source footer",
        "settlement",
        "escrow",
        "production_profile_matrix",
        "acceptance_matrix_status",
        "examples/production_profiles",
        "revocation",
        "incident",
        "tenancy",
    ),
    "docs/operator_runbook.md": (
        "deployment profile",
        "tenant",
        "provider route",
        "rights registry",
        "settlement",
        "examples/production_profiles",
        "incident",
        "backup",
        "upgrade",
        "government",
    ),
    "docs/deployment.md": (
        "RDLLM_SERVICE_TOKEN_SHA256",
        "/healthz",
        "/readyz",
        "audit log",
        "fail closed",
        "backup",
        "Docker Compose",
        "Kubernetes",
        "deployment_audit",
    ),
    "docs/service_api.md": (
        "/v1/attribute",
        "/v1/metrics",
        "/v1/metrics/prometheus",
        "bearer-token",
        "readiness",
        "hash-chained audit",
        "service_smoke",
        "service_load_smoke",
        "provider_live_smoke",
        "security_abuse_smoke",
        "rate limiting",
    ),
    "SECURITY.md": (
        "Secrets",
        "Supply Chain",
        "Incident Response",
        "Abuse",
        "Vulnerability",
    ),
}

REQUIRED_ARTIFACT_SUMMARIES = {
    "artifacts/certification_report.json": {
        "summary.status": "passed",
        "summary.highest_level": "RDLLM-L186",
    },
    "artifacts/discovery_manifest.json": {
        "summary.status": "ready",
        "summary.offline_verification_supported": True,
    },
    "artifacts/universal_production_invocation_admission.json": {
        "summary.status": "ready",
    },
    "artifacts/universal_runtime_conformance_receipt.json": {
        "summary.status": "ready",
        "runtime_decision.provider_invocation_allowed": True,
        "runtime_decision.response_display_allowed": True,
    },
    "artifacts/universal_source_grounded_response_receipt.json": {
        "summary.status": "ready",
    },
    "artifacts/universal_verified_source_footer_contract.json": {
        "summary.status": "ready",
    },
    "artifacts/universal_composition_settlement.json": {
        "summary.status": "ready",
    },
    "artifacts/payment_execution_report.json": {
        "summary.status": "ready",
    },
    "artifacts/payment_rail_attestation.json": {
        "summary.status": "ready",
    },
    "artifacts/production_readiness_report.json": {
        "summary.status": "ready",
        "summary.production_grade_claim_allowed": False,
        "summary.direct_creator_settlement_allowed": False,
        "summary.public_sector_use_supported": False,
        "summary.external_evidence_status": "unverified",
    },
}


def _get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _read_text(root: Path, relpath: str) -> str:
    return (root / relpath).read_text(encoding="utf-8")


def audit_docs(root: Path) -> list[str]:
    errors: list[str] = []
    for relpath in REQUIRED_OPERATOR_DOCS:
        path = root / relpath
        if not path.is_file():
            errors.append(f"missing operator document: {relpath}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty operator document: {relpath}")
    for relpath, terms in REQUIRED_DOC_TERMS.items():
        path = root / relpath
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for term in terms:
            if term not in text:
                errors.append(f"{relpath} does not mention required term: {term}")
    readme = _read_text(root, "README.md")
    if "working prototype and publishable research package" in readme:
        errors.append("README still positions RDLLM as a prototype/research package")
    if "tools/production_readiness.py" not in readme:
        errors.append("README does not expose the production-readiness gate")
    return errors


def audit_artifacts(root: Path) -> list[str]:
    errors: list[str] = []
    for relpath, expected_values in REQUIRED_ARTIFACT_SUMMARIES.items():
        path = root / relpath
        if not path.is_file():
            errors.append(f"missing production artifact: {relpath}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for dotted_path, expected in expected_values.items():
            actual = _get_path(payload, dotted_path)
            if actual != expected:
                errors.append(
                    f"{relpath}:{dotted_path} expected {expected!r}, got {actual!r}"
                )
    return errors


def audit_profile(
    profile_path: Path,
    trust_store_path: Path | None = None,
) -> dict[str, Any]:
    profile = load_json(profile_path)
    trust_store = load_json(trust_store_path) if trust_store_path else None
    report = evaluate_production_profile(profile, trust_store=trust_store)
    verification = verify_production_readiness_report(
        profile,
        report,
        trust_store=trust_store,
    )
    if verification["status"] != "passed":
        report["summary"]["status"] = "blocked"
        report["blocked_controls"].append(
            {
                "control_id": "profile.self_verification",
                "requirement": "generated report must verify against profile",
                "evidence": verification["errors"],
            }
        )
    return report


def _summarize_acceptance_matrix(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    rows = []
    for row in report.get("rows", []):
        rows.append(
            {
                "operator_template": row.get("operator_template", ""),
                "status": row.get("status", "unknown"),
                "acceptance_status": row.get("acceptance_status", "unknown"),
                "acceptance_verification_status": row.get(
                    "acceptance_verification_status",
                    "unknown",
                ),
                "production_acceptance_decision": row.get(
                    "production_acceptance_decision",
                    "unknown",
                ),
                "settlement_mode": row.get("settlement_mode", ""),
                "direct_creator_settlement_allowed": row.get(
                    "direct_creator_settlement_allowed",
                    False,
                ),
                "public_sector_use_supported": row.get(
                    "public_sector_use_supported",
                    False,
                ),
                "source_grounding_acceptance_status": row.get(
                    "source_grounding_acceptance_status",
                    "unknown",
                ),
                "audit_response_binding_status": row.get(
                    "audit_response_binding_status",
                    "unknown",
                ),
                "recovery_verification_status": row.get(
                    "recovery_verification_status",
                    "unknown",
                ),
            }
        )
    return {
        "status": report.get("status", "failed"),
        "errors": list(report.get("errors", [])),
        "summary": {
            "operator_template_count": summary.get("operator_template_count", 0),
            "passed_count": summary.get("passed_count", 0),
            "failed_count": summary.get("failed_count", 0),
            "operator_templates": list(summary.get("operator_templates", [])),
            "settlement_modes": list(summary.get("settlement_modes", [])),
            "direct_settlement_template_count": summary.get(
                "direct_settlement_template_count",
                0,
            ),
            "no_direct_settlement_template_count": summary.get(
                "no_direct_settlement_template_count",
                0,
            ),
            "public_sector_template_count": summary.get(
                "public_sector_template_count",
                0,
            ),
            "production_acceptance_allowed_count": summary.get(
                "production_acceptance_allowed_count",
                0,
            ),
            "runtime_checked": summary.get("runtime_checked", False),
        },
        "rows": rows,
    }


def audit_acceptance_matrix() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="rdllm-production-acceptance-matrix-"
    ) as temp_name:
        report = run_acceptance_matrix(output_dir=Path(temp_name) / "matrix")
    return _summarize_acceptance_matrix(report)


def audit_repository(
    root: Path,
    profile_path: Path,
    trust_store_path: Path | None = None,
) -> dict[str, Any]:
    doc_errors = audit_docs(root)
    artifact_errors = audit_artifacts(root)
    profile_report = audit_profile(profile_path, trust_store_path)
    profile_matrix = audit_profile_matrix()
    acceptance_matrix = audit_acceptance_matrix()
    profile = load_json(profile_path)
    trust_store = load_json(trust_store_path) if trust_store_path else None
    checked_in_report = load_json(root / "artifacts" / "production_readiness_report.json")
    checked_in_verification = verify_production_readiness_report(
        profile,
        checked_in_report,
        trust_store=trust_store,
    )
    if checked_in_verification["status"] != "passed":
        artifact_errors.extend(
            f"production readiness report stale: {error}"
            for error in checked_in_verification["errors"]
        )
    profile_errors = [
        f"profile:{row['control_id']}: {row['requirement']}"
        for row in profile_report["blocked_controls"]
    ]
    profile_matrix_errors = [
        f"profile_matrix:{error}" for error in profile_matrix["errors"]
    ]
    acceptance_matrix_errors = [
        f"acceptance_matrix:{error}" for error in acceptance_matrix["errors"]
    ]
    if acceptance_matrix["status"] != "passed" and not acceptance_matrix_errors:
        acceptance_matrix_errors.append("acceptance_matrix:status is not passed")
    errors = (
        doc_errors
        + artifact_errors
        + profile_errors
        + profile_matrix_errors
        + acceptance_matrix_errors
    )
    audit_ready = not errors
    profile_summary = profile_report["summary"]
    acceptance_summary = acceptance_matrix["summary"]
    report = {
        "schema": REPOSITORY_REPORT_SCHEMA,
        "status": "ready" if audit_ready else "blocked",
        "errors": errors,
        "summary": {
            "operator_document_count": len(REQUIRED_OPERATOR_DOCS),
            "artifact_gate_count": len(REQUIRED_ARTIFACT_SUMMARIES),
            "profile_control_count": required_profile_control_count(),
            "profile_status": profile_summary["status"],
            "profile_matrix_status": profile_matrix["status"],
            "profile_matrix_profile_count": profile_matrix["summary"]["profile_count"],
            "acceptance_matrix_status": acceptance_matrix["status"],
            "acceptance_matrix_operator_template_count": acceptance_summary[
                "operator_template_count"
            ],
            "acceptance_matrix_passed_count": acceptance_summary["passed_count"],
            "acceptance_matrix_production_acceptance_allowed_count": (
                acceptance_summary["production_acceptance_allowed_count"]
            ),
            "settlement_mode": profile_summary.get("settlement_mode"),
            "direct_payout_enabled": profile_summary.get("direct_payout_enabled"),
            "payment_processor_attested": profile_summary.get(
                "payment_processor_attested"
            ),
            "software_release_status": "ready" if audit_ready else "blocked",
            "operator_deployment_status": profile_summary.get(
                "external_evidence_status",
                "unverified",
            ),
            "production_grade_claim_allowed": False,
            "direct_creator_settlement_allowed": False,
            "public_sector_use_supported": False,
        },
        "profile_report": profile_report,
        "profile_matrix": profile_matrix,
        "acceptance_matrix": acceptance_matrix,
    }
    report["repository_report_hash"] = repository_readiness_report_hash(report)
    return report


def _apply_repository_verification(report: dict[str, Any]) -> dict[str, Any]:
    verification = verify_repository_readiness_report(report)
    if verification["status"] == "passed":
        return report
    report["status"] = "blocked"
    report["errors"] = [
        *list(report.get("errors", [])),
        *[
            f"repository_verification:{error}"
            for error in verification.get("errors", [])
        ],
    ]
    summary = report.get("summary", {})
    if isinstance(summary, dict):
        summary["production_grade_claim_allowed"] = False
        summary["direct_creator_settlement_allowed"] = False
        summary["public_sector_use_supported"] = False
    report["repository_report_hash"] = repository_readiness_report_hash(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-report",
        help="Verify a saved repository-mode production readiness report.",
    )
    parser.add_argument(
        "--profile",
        default="examples/production_readiness_profile.json",
        help="Operator production-readiness profile to evaluate.",
    )
    parser.add_argument(
        "--trust-store",
        type=Path,
        help="Externally managed trust store used to verify deployment attestations.",
    )
    parser.add_argument(
        "--profile-only",
        action="store_true",
        help="Evaluate only the supplied operator profile.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full readiness report as JSON.",
    )
    parser.add_argument(
        "--write-report",
        help="Optional path to write the JSON readiness report or verification result.",
    )
    args = parser.parse_args(argv)

    if args.verify_report:
        report_path = Path(args.verify_report)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verification = verify_repository_readiness_report(report)
        if args.write_report:
            destination = Path(args.write_report)
            if not destination.is_absolute():
                destination = ROOT / destination
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(verification, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if args.json:
            print(json.dumps(verification, indent=2, sort_keys=True))
        else:
            print(render_repository_verification_text(verification))
        return 0 if verification["status"] == "passed" else 1

    profile_path = (ROOT / args.profile).resolve()
    if args.profile_only:
        report = audit_profile(profile_path, args.trust_store)
        status = report["summary"]["status"]
        errors = [
            f"{row['control_id']}: {row['requirement']}"
            for row in report["blocked_controls"]
        ]
    else:
        report = _apply_repository_verification(
            audit_repository(ROOT, profile_path, args.trust_store)
        )
        status = report["status"]
        errors = report["errors"]

    if args.write_report:
        destination = Path(args.write_report)
        if not destination.is_absolute():
            destination = ROOT / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"production_readiness status: {status}")
        summary = report.get("summary", {})
        for key, value in summary.items():
            print(f"{key}: {value}")
        if errors:
            print("errors:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
