"""Export public RDLLM artifacts into docs/.well-known for static hosting."""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "artifacts" / "discovery_manifest.json"
DOCS_ROOT = ROOT / "docs"
EXPORT_ROOT = DOCS_ROOT / ".well-known"

PUBLIC_ARTIFACT_FILE_ALIASES = {
    "counterfactual_influence_report": "counterfactual_report",
    "model_signal_attribution_report": "model_signal_report",
    "response_release_gate": "release_gate",
    "foundation_api_profile": "foundation_attribution_profile",
}


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _artifact_path(name: str) -> Path:
    direct = ROOT / "artifacts" / f"{name}.json"
    if direct.is_file():
        return direct
    alias = PUBLIC_ARTIFACT_FILE_ALIASES.get(name)
    if alias:
        aliased = ROOT / "artifacts" / f"{alias}.json"
        if aliased.is_file():
            return aliased
    return direct


def _destination_for_well_known_path(well_known_path: str) -> Path:
    if not well_known_path.startswith("/.well-known/"):
        raise ValueError(f"unsupported well-known path: {well_known_path}")
    return DOCS_ROOT / well_known_path.removeprefix("/")


def expected_exports() -> dict[Path, Path]:
    manifest = _load_manifest()
    exports = {EXPORT_ROOT / "rdllm.json": MANIFEST_PATH}
    schemas = manifest.get("schemas", {})
    if isinstance(schemas, dict):
        for schema_path in schemas.values():
            if not isinstance(schema_path, str) or not schema_path:
                continue
            source = ROOT / schema_path
            if source.is_file():
                exports[DOCS_ROOT / schema_path] = source
    catalog = manifest.get("artifact_catalog", [])
    if not isinstance(catalog, list):
        return exports
    for row in catalog:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", ""))
        well_known_path = str(row.get("well_known_path", ""))
        if not name or not well_known_path:
            continue
        exports[_destination_for_well_known_path(well_known_path)] = _artifact_path(name)
    return exports


def write_exports() -> dict[str, Any]:
    exports = expected_exports()
    for destination, source in exports.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    expected_destinations = set(exports)
    stale_files = []
    stale_files.extend(
        path for path in (EXPORT_ROOT / "rdllm").glob("*.json") if path not in expected_destinations
    )
    stale_files.extend(
        path
        for path in (DOCS_ROOT / "docs" / "schemas").glob("*.json")
        if path not in expected_destinations
    )
    for path in stale_files:
        path.unlink()
    return audit()


def audit() -> dict[str, Any]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    total_bytes = 0
    exports = expected_exports()

    for destination, source in sorted(exports.items(), key=lambda item: relpath(item[0])):
        row = {
            "source": relpath(source),
            "destination": relpath(destination),
            "bytes": 0,
            "matches_source": False,
        }
        if not source.is_file():
            errors.append(f"missing export source: {relpath(source)}")
            rows.append(row)
            continue
        row["bytes"] = source.stat().st_size
        total_bytes += source.stat().st_size
        if not destination.is_file():
            errors.append(f"missing hosted export: {relpath(destination)}")
            rows.append(row)
            continue
        if not filecmp.cmp(source, destination, shallow=False):
            errors.append(
                f"stale hosted export: {relpath(destination)} does not match {relpath(source)}"
            )
            rows.append(row)
            continue
        row["matches_source"] = True
        rows.append(row)

    stale_files = []
    stale_files.extend(
        path for path in (EXPORT_ROOT / "rdllm").glob("*.json") if path not in exports
    )
    stale_files.extend(
        path
        for path in (DOCS_ROOT / "docs" / "schemas").glob("*.json")
        if path not in exports
    )
    for path in sorted(stale_files):
        errors.append(f"stale unadvertised hosted export: {relpath(path)}")

    return {
        "status": "failed" if errors else "passed",
        "export_count": len(exports),
        "exported_byte_count": total_bytes,
        "hosted_manifest_path": relpath(EXPORT_ROOT / "rdllm.json"),
        "hosted_artifact_directory": relpath(EXPORT_ROOT / "rdllm"),
        "rows": rows,
        "errors": errors,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"hosting_export status: {report['status']}",
        f"export_count: {report['export_count']}",
        f"exported_byte_count: {report['exported_byte_count']}",
        f"hosted_manifest_path: {report['hosted_manifest_path']}",
        f"hosted_artifact_directory: {report['hosted_artifact_directory']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh docs/.well-known exports.")
    parser.add_argument("--check", action="store_true", help="Fail if docs/.well-known exports are stale.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = write_exports() if args.write else audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
