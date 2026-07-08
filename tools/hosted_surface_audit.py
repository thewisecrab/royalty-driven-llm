"""Verify the static-hosted RDLLM discovery surface resolves locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.discovery_manifest import _declared_hash  # noqa: E402
from rdllm.receipts import hash_payload  # noqa: E402


DOCS_ROOT = ROOT / "docs"
HOSTED_MANIFEST = DOCS_ROOT / ".well-known" / "rdllm.json"
SOURCE_MANIFEST = ROOT / "artifacts" / "discovery_manifest.json"


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_hosted_path(path_value: str) -> Path:
    if path_value.startswith("/"):
        return DOCS_ROOT / path_value.lstrip("/")
    return DOCS_ROOT / path_value


def audit() -> dict[str, Any]:
    errors: list[str] = []
    artifact_rows: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []

    if not HOSTED_MANIFEST.is_file():
        return {
            "status": "failed",
            "errors": [f"missing hosted manifest: {relpath(HOSTED_MANIFEST)}"],
            "hosted_artifact_count": 0,
            "hosted_schema_count": 0,
        }

    hosted_manifest = _load_json(HOSTED_MANIFEST)
    source_manifest = _load_json(SOURCE_MANIFEST)
    if hosted_manifest != source_manifest:
        errors.append(
            f"hosted manifest {relpath(HOSTED_MANIFEST)} does not match {relpath(SOURCE_MANIFEST)}"
        )

    discovery_path = hosted_manifest.get("discovery", {}).get("well_known_path")
    if discovery_path:
        resolved = _resolve_hosted_path(str(discovery_path))
        if resolved != HOSTED_MANIFEST:
            errors.append(
                f"discovery well-known path resolves to {relpath(resolved)}, expected {relpath(HOSTED_MANIFEST)}"
            )

    schemas = hosted_manifest.get("schemas", {})
    if not isinstance(schemas, dict):
        errors.append("hosted manifest schemas field is not an object")
        schemas = {}
    for name, schema_path in sorted(schemas.items()):
        if not isinstance(schema_path, str) or not schema_path:
            errors.append(f"schema path for {name} is not a string")
            continue
        resolved = _resolve_hosted_path(schema_path)
        row = {
            "name": str(name),
            "schema_path": schema_path,
            "resolved_path": relpath(resolved),
            "exists": resolved.is_file(),
        }
        if not resolved.is_file():
            errors.append(f"hosted schema does not resolve: {name} -> {schema_path}")
        schema_rows.append(row)

    catalog = hosted_manifest.get("artifact_catalog", [])
    if not isinstance(catalog, list):
        errors.append("hosted manifest artifact_catalog field is not an array")
        catalog = []
    for row in catalog:
        if not isinstance(row, dict):
            errors.append("hosted artifact catalog contains a non-object row")
            continue
        name = str(row.get("name", ""))
        well_known_path = str(row.get("well_known_path", ""))
        resolved = _resolve_hosted_path(well_known_path)
        artifact_row = {
            "name": name,
            "well_known_path": well_known_path,
            "resolved_path": relpath(resolved),
            "exists": resolved.is_file(),
            "payload_hash_matches": False,
            "declared_hash_matches": False,
        }
        if not name:
            errors.append("hosted artifact catalog row is missing name")
            artifact_rows.append(artifact_row)
            continue
        if not resolved.is_file():
            errors.append(f"hosted artifact does not resolve: {name} -> {well_known_path}")
            artifact_rows.append(artifact_row)
            continue
        artifact = _load_json(resolved)
        payload_hash = hash_payload(artifact)
        declared_hash = _declared_hash(artifact)
        artifact_row["payload_hash_matches"] = payload_hash == row.get("payload_hash")
        artifact_row["declared_hash_matches"] = declared_hash == row.get("declared_hash")
        if not artifact_row["payload_hash_matches"]:
            errors.append(f"hosted artifact payload hash mismatch: {name}")
        if not artifact_row["declared_hash_matches"]:
            errors.append(f"hosted artifact declared hash mismatch: {name}")
        artifact_rows.append(artifact_row)

    return {
        "status": "failed" if errors else "passed",
        "hosted_manifest_path": relpath(HOSTED_MANIFEST),
        "hosted_artifact_count": len(artifact_rows),
        "hosted_schema_count": len(schema_rows),
        "artifact_rows": artifact_rows,
        "schema_rows": schema_rows,
        "errors": errors,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"hosted_surface_audit status: {report['status']}",
        f"hosted_manifest_path: {report.get('hosted_manifest_path', relpath(HOSTED_MANIFEST))}",
        f"hosted_artifact_count: {report['hosted_artifact_count']}",
        f"hosted_schema_count: {report['hosted_schema_count']}",
    ]
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
