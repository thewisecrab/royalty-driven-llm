"""Audit RDLLM provider-family taxonomy consistency."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.provider_family_registry import (  # noqa: E402
    CANONICAL_PROVIDER_FAMILIES,
    canonical_provider_families,
    provider_family_coverage,
)


MODULE_SURFACES = (
    {
        "name": "foundation_runtime_router",
        "module": "rdllm.foundation_runtime_router",
        "full_canonical_required": False,
    },
    {
        "name": "universal_foundation_adoption_kernel",
        "module": "rdllm.universal_foundation_adoption_kernel",
        "full_canonical_required": False,
    },
    {
        "name": "universal_provider_adapter_harness",
        "module": "rdllm.universal_provider_adapter_harness",
        "full_canonical_required": False,
    },
    {
        "name": "universal_attribution_negotiation_handshake",
        "module": "rdllm.universal_attribution_negotiation_handshake",
        "full_canonical_required": False,
    },
    {
        "name": "universal_negotiated_invocation_enforcement",
        "module": "rdllm.universal_negotiated_invocation_enforcement",
        "full_canonical_required": False,
    },
    {
        "name": "universal_provider_drift_sentinel",
        "module": "rdllm.universal_provider_drift_sentinel",
        "full_canonical_required": False,
    },
    {
        "name": "universal_foundation_provider_adoption_pack",
        "module": "rdllm.universal_foundation_provider_adoption_pack",
        "full_canonical_required": False,
    },
    {
        "name": "universal_foundation_provider_binding_matrix",
        "module": "rdllm.universal_foundation_provider_binding_matrix",
        "full_canonical_required": True,
    },
    {
        "name": "universal_provider_conformance_runner_receipt",
        "module": "rdllm.universal_provider_conformance_runner_receipt",
        "full_canonical_required": True,
    },
    {
        "name": "universal_production_invocation_admission",
        "module": "rdllm.universal_production_invocation_admission",
        "full_canonical_required": True,
    },
    {
        "name": "universal_live_capability_discovery_contract",
        "module": "rdllm.universal_live_capability_discovery_contract",
        "full_canonical_required": True,
    },
)

ARTIFACT_SURFACES = (
    {
        "name": "universal_foundation_provider_binding_matrix",
        "path": "artifacts/universal_foundation_provider_binding_matrix.json",
        "field": "provider_binding_rows",
        "full_canonical_required": True,
    },
    {
        "name": "universal_provider_conformance_runner_receipt",
        "path": "artifacts/universal_provider_conformance_runner_receipt.json",
        "field": "provider_run_rows",
        "full_canonical_required": True,
    },
    {
        "name": "universal_production_invocation_admission",
        "path": "artifacts/universal_production_invocation_admission.json",
        "field": "provider_admission_rows",
        "full_canonical_required": True,
    },
    {
        "name": "universal_live_capability_discovery_contract",
        "path": "artifacts/universal_live_capability_discovery_contract.json",
        "field": "provider_family_rows",
        "full_canonical_required": True,
    },
)


def _load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _module_row(surface: dict[str, Any]) -> dict[str, Any]:
    module = importlib.import_module(str(surface["module"]))
    families = tuple(getattr(module, "REQUIRED_PROVIDER_FAMILIES", ()))
    coverage = provider_family_coverage(families)
    return {
        "name": surface["name"],
        "source": surface["module"],
        "surface_type": "module",
        "full_canonical_required": bool(surface["full_canonical_required"]),
        **coverage,
    }


def _artifact_families(payload: dict[str, Any], field: str) -> tuple[str, ...]:
    rows = payload.get(field, {})
    if isinstance(rows, dict):
        return tuple(str(key) for key in rows)
    if isinstance(rows, list):
        values: list[str] = []
        for row in rows:
            if isinstance(row, dict) and row.get("provider_family"):
                values.append(str(row["provider_family"]))
        return tuple(values)
    return ()


def _artifact_row(surface: dict[str, Any]) -> dict[str, Any]:
    payload = _load_json(str(surface["path"]))
    families = _artifact_families(payload, str(surface["field"]))
    coverage = provider_family_coverage(families)
    return {
        "name": surface["name"],
        "source": surface["path"],
        "field": surface["field"],
        "surface_type": "artifact",
        "full_canonical_required": bool(surface["full_canonical_required"]),
        **coverage,
    }


def audit() -> dict[str, Any]:
    rows = [_module_row(surface) for surface in MODULE_SURFACES]
    rows.extend(_artifact_row(surface) for surface in ARTIFACT_SURFACES)

    matrix = (ROOT / "docs" / "provider_compatibility_matrix.md").read_text(
        encoding="utf-8"
    )
    docs_missing = [
        family for family in CANONICAL_PROVIDER_FAMILIES if f"`{family}`" not in matrix
    ]

    errors: list[str] = []
    for row in rows:
        if row["unmapped_provider_families"]:
            errors.append(
                f"{row['name']} has unmapped provider families: "
                f"{', '.join(row['unmapped_provider_families'])}"
            )
        if row["full_canonical_required"] and row["missing_canonical_provider_families"]:
            errors.append(
                f"{row['name']} is missing canonical provider families: "
                f"{', '.join(row['missing_canonical_provider_families'])}"
            )
    if docs_missing:
        errors.append(
            "docs/provider_compatibility_matrix.md is missing canonical families: "
            + ", ".join(docs_missing)
        )

    current_full_surfaces = [
        row
        for row in rows
        if row["full_canonical_required"]
        and not row["unmapped_provider_families"]
        and not row["missing_canonical_provider_families"]
    ]
    return {
        "status": "failed" if errors else "passed",
        "canonical_provider_family_count": len(CANONICAL_PROVIDER_FAMILIES),
        "canonical_provider_families": list(CANONICAL_PROVIDER_FAMILIES),
        "current_full_surface_count": len(current_full_surfaces),
        "surface_count": len(rows),
        "surfaces": rows,
        "docs_missing_canonical_provider_families": docs_missing,
        "errors": errors,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"provider_family_audit status: {report['status']}",
        f"canonical_provider_family_count: {report['canonical_provider_family_count']}",
        f"current_full_surface_count: {report['current_full_surface_count']}",
        f"surface_count: {report['surface_count']}",
    ]
    for row in report["surfaces"]:
        missing = len(row["missing_canonical_provider_families"])
        unmapped = len(row["unmapped_provider_families"])
        requirement = "full" if row["full_canonical_required"] else "alias-compatible"
        lines.append(
            "- "
            f"{row['name']} ({row['surface_type']}, {requirement}): "
            f"raw={row['raw_provider_family_count']} "
            f"canonical={row['canonical_provider_family_count']} "
            f"missing={missing} unmapped={unmapped}"
        )
    if report["errors"]:
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
