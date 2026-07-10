"""Audit production-readiness profile coverage across operator types."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.production_readiness import (  # noqa: E402
    evaluate_production_profile,
    load_json,
    verify_production_readiness_report,
)

PROFILE_SCHEMA_PATH = ROOT / "docs" / "schemas" / "production_readiness_profile.schema.json"
DEFAULT_PROFILE_PATH = ROOT / "examples" / "production_readiness_profile.json"
PROFILE_DIR = ROOT / "examples" / "production_profiles"

REQUIRED_OPERATOR_TYPES = {
    "individual",
    "company",
    "institution",
    "government",
    "public_sector",
}
REQUIRED_SETTLEMENT_MODES = {
    "escrow_only",
    "instruction_only",
    "processor_attested",
}


def _profile_content_hash(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _profile_paths() -> list[Path]:
    paths: list[Path] = []
    if PROFILE_DIR.is_dir():
        paths.extend(sorted(PROFILE_DIR.glob("*.json")))
    seen_hashes: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        profile_hash = _profile_content_hash(path)
        seen_hashes.add(profile_hash)
        unique_paths.append(path)
    if DEFAULT_PROFILE_PATH.is_file():
        default_hash = _profile_content_hash(DEFAULT_PROFILE_PATH)
        if default_hash not in seen_hashes:
            unique_paths.append(DEFAULT_PROFILE_PATH)
    return unique_paths


def _schema_errors(profile: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        return [f"jsonschema is required for profile matrix validation: {exc}"]

    errors = sorted(
        Draft202012Validator(schema).iter_errors(profile),
        key=lambda error: list(error.path),
    )
    rendered: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        rendered.append(f"{location}: {error.message}")
    return rendered


def audit() -> dict[str, Any]:
    errors: list[str] = []
    schema = load_json(PROFILE_SCHEMA_PATH)
    rows: list[dict[str, Any]] = []
    operator_types: set[str] = set()
    settlement_modes: set[str] = set()
    direct_settlement_profiles = 0
    no_payment_profiles = 0
    public_sector_profiles = 0

    paths = _profile_paths()
    if not paths:
        errors.append("no production readiness profiles found")

    for path in paths:
        relpath = path.relative_to(ROOT).as_posix()
        profile = load_json(path)
        schema_errors = _schema_errors(profile, schema)
        if schema_errors:
            errors.extend(f"{relpath}: {error}" for error in schema_errors)
        report = evaluate_production_profile(profile)
        verification = verify_production_readiness_report(profile, report)
        if verification["status"] != "passed":
            errors.extend(
                f"{relpath}: self-verification failed: {error}"
                for error in verification["errors"]
            )
        summary = report["summary"]
        if summary["status"] != "ready":
            errors.extend(
                f"{relpath}: {row['control_id']}: {row['requirement']}"
                for row in report["blocked_controls"]
            )
        operator_type = str(summary.get("operator_type", ""))
        settlement_mode = str(summary.get("settlement_mode", ""))
        operator_types.add(operator_type)
        settlement_modes.add(settlement_mode)
        if summary.get("direct_creator_settlement_allowed") is True:
            direct_settlement_profiles += 1
        else:
            no_payment_profiles += 1
        if summary.get("public_sector_use_supported") is True:
            public_sector_profiles += 1
        rows.append(
            {
                "path": relpath,
                "status": summary["status"],
                "operator_type": operator_type,
                "environment": profile.get("deployment", {}).get("environment"),
                "tenancy_model": profile.get("deployment", {}).get("tenancy_model"),
                "settlement_mode": settlement_mode,
                "direct_creator_settlement_allowed": summary[
                    "direct_creator_settlement_allowed"
                ],
                "public_sector_use_supported": summary["public_sector_use_supported"],
                "profile_hash": report["profile_hash"],
            }
        )

    missing_operator_types = sorted(REQUIRED_OPERATOR_TYPES - operator_types)
    missing_settlement_modes = sorted(REQUIRED_SETTLEMENT_MODES - settlement_modes)
    for operator_type in missing_operator_types:
        errors.append(f"missing production profile for operator_type={operator_type}")
    for settlement_mode in missing_settlement_modes:
        errors.append(f"missing production profile for settlement_mode={settlement_mode}")
    if direct_settlement_profiles != 0:
        errors.append("unattested profile matrix must not allow direct settlement")
    if no_payment_profiles != len(rows):
        errors.append("every unattested profile must keep direct settlement disabled")
    if public_sector_profiles != 0:
        errors.append("unattested profile matrix must not claim public-sector readiness")

    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "summary": {
            "profile_count": len(rows),
            "operator_types": sorted(operator_types),
            "settlement_modes": sorted(settlement_modes),
            "direct_settlement_profile_count": direct_settlement_profiles,
            "no_payment_profile_count": no_payment_profiles,
            "public_sector_profile_count": public_sector_profiles,
        },
        "profiles": rows,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [f"production_profile_matrix status: {report['status']}"]
    summary = report.get("summary", {})
    for key, value in summary.items():
        lines.append(f"{key}: {json.dumps(value, sort_keys=True)}")
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
