"""Create and verify RDLLM operator recovery manifests."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import resources
import json
from pathlib import Path
from typing import Any


RECOVERY_MANIFEST_SCHEMA = "rdllm-operator-recovery-manifest/v1"
RECOVERY_VERIFICATION_SCHEMA = "rdllm-operator-recovery-verification/v1"
DATA_PACKAGE = "rdllm.data"
RECOVERY_MANIFEST_SCHEMA_RESOURCE = ("schemas", "operator_recovery_manifest.schema.json")
RECOVERY_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "operator_recovery_verification.schema.json",
)
DEFAULT_FILES = (
    "production_readiness_profile.json",
    "production_readiness_report.json",
    "service_config.json",
    "operator_bootstrap_manifest.json",
    "README.md",
)
DEFAULT_DIRS = ("artifacts", "corpus", "runtime")


def load_recovery_manifest_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*RECOVERY_MANIFEST_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_recovery_verification_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(
        *RECOVERY_VERIFICATION_SCHEMA_RESOURCE
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _collect_files(
    root: Path,
    *,
    include: list[Path] | None = None,
    include_dir: list[Path] | None = None,
    include_defaults: bool = True,
) -> tuple[list[Path], list[str]]:
    errors: list[str] = []
    paths: set[Path] = set()
    root = root.resolve()

    def add_file(path: Path) -> None:
        try:
            resolved = (
                (root / path).resolve() if not path.is_absolute() else path.resolve()
            )
            resolved.relative_to(root)
        except ValueError:
            errors.append(f"{path}: must be inside root {root}")
            return
        if not resolved.is_file():
            errors.append(f"{path}: file does not exist")
            return
        paths.add(resolved)

    def add_dir(path: Path) -> None:
        try:
            resolved = (
                (root / path).resolve() if not path.is_absolute() else path.resolve()
            )
            resolved.relative_to(root)
        except ValueError:
            errors.append(f"{path}: must be inside root {root}")
            return
        if not resolved.exists():
            return
        if not resolved.is_dir():
            errors.append(f"{path}: expected directory")
            return
        for child in sorted(resolved.rglob("*")):
            if child.is_file():
                paths.add(child.resolve())

    if include_defaults:
        for relpath in DEFAULT_FILES:
            candidate = root / relpath
            if candidate.is_file():
                paths.add(candidate.resolve())
        for relpath in DEFAULT_DIRS:
            add_dir(Path(relpath))

    for path in include or []:
        add_file(path)
    for path in include_dir or []:
        add_dir(path)

    return sorted(paths, key=lambda item: _relative_path(root, item)), errors


def _manifest_row(root: Path, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": _relative_path(root, path),
        "size_bytes": stat.st_size,
        "sha256": _sha256_file(path),
    }


def create_recovery_manifest(
    *,
    root: Path,
    include: list[Path] | None = None,
    include_dir: list[Path] | None = None,
    include_defaults: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    files, errors = _collect_files(
        root,
        include=include,
        include_dir=include_dir,
        include_defaults=include_defaults,
    )
    rows = [_manifest_row(root, path) for path in files]
    return {
        "schema": RECOVERY_MANIFEST_SCHEMA,
        "status": "ready" if rows and not errors else "blocked",
        "generated_at": _utc_now(),
        "root": root.as_posix(),
        "summary": {
            "file_count": len(rows),
            "total_bytes": sum(row["size_bytes"] for row in rows),
            "default_scope_included": include_defaults,
            "operator_include_count": len(include or []),
            "operator_include_dir_count": len(include_dir or []),
        },
        "files": rows,
        "errors": errors,
    }


def _safe_manifest_path(root: Path, relpath: Any, errors: list[str]) -> Path | None:
    if not isinstance(relpath, str) or not relpath.strip():
        errors.append("files[].path: expected non-empty string")
        return None
    path = Path(relpath)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{relpath}: path must be relative and stay inside root")
        return None
    return root / path


def verify_recovery_manifest(
    manifest: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if manifest.get("schema") != RECOVERY_MANIFEST_SCHEMA:
        errors.append(f"schema: expected {RECOVERY_MANIFEST_SCHEMA!r}")
    files = manifest.get("files", [])
    if not isinstance(files, list):
        errors.append("files: expected array")
        files = []
    manifest_root = manifest.get("root")
    if root is None:
        if isinstance(manifest_root, str) and manifest_root.strip():
            root = Path(manifest_root)
        else:
            errors.append("root: required when manifest root is missing")
            root = Path.cwd()
    root = root.resolve()

    checked_count = 0
    missing_count = 0
    mismatch_count = 0
    total_bytes = 0
    for index, row in enumerate(files):
        if not isinstance(row, dict):
            errors.append(f"files[{index}]: expected object")
            mismatch_count += 1
            continue
        path = _safe_manifest_path(root, row.get("path"), errors)
        expected_size = row.get("size_bytes")
        expected_hash = row.get("sha256")
        if not isinstance(expected_size, int) or expected_size < 0:
            errors.append(f"files[{index}].size_bytes: expected non-negative integer")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            errors.append(f"files[{index}].sha256: expected SHA-256 hex string")
        if path is None:
            mismatch_count += 1
            continue
        if not path.is_file():
            errors.append(f"{row.get('path')}: missing restored file")
            missing_count += 1
            continue
        checked_count += 1
        actual_size = path.stat().st_size
        total_bytes += actual_size
        if actual_size != expected_size:
            errors.append(
                f"{row.get('path')}: size mismatch expected {expected_size}, "
                f"got {actual_size}"
            )
            mismatch_count += 1
        actual_hash = _sha256_file(path)
        if actual_hash != expected_hash:
            errors.append(f"{row.get('path')}: sha256 mismatch")
            mismatch_count += 1

    summary = manifest.get("summary", {})
    if isinstance(summary, dict):
        if summary.get("file_count") != len(files):
            errors.append("summary.file_count: does not match files")
        if summary.get("total_bytes") != sum(
            row.get("size_bytes", 0) for row in files if isinstance(row, dict)
        ):
            errors.append("summary.total_bytes: does not match files")

    return {
        "schema": RECOVERY_VERIFICATION_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "checked_count": checked_count,
        "missing_count": missing_count,
        "mismatch_count": mismatch_count,
        "manifest_file_count": len(files),
        "restored_total_bytes": total_bytes,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_manifest_text(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        f"operator_recovery_manifest status: {manifest['status']}",
        f"file_count: {summary['file_count']}",
        f"total_bytes: {summary['total_bytes']}",
    ]
    if manifest["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in manifest["errors"])
    return "\n".join(lines)


def render_verification_text(report: dict[str, Any]) -> str:
    lines = [
        f"operator_recovery_verification status: {report['status']}",
        f"checked_count: {report['checked_count']}",
        f"manifest_file_count: {report['manifest_file_count']}",
        f"missing_count: {report['missing_count']}",
        f"mismatch_count: {report['mismatch_count']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--include", type=Path, action="append")
    create.add_argument("--include-dir", type=Path, action="append")
    create.add_argument("--no-defaults", action="store_true")
    create.add_argument("--json", action="store_true")

    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--root", type=Path)
    verify.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "create":
        manifest = create_recovery_manifest(
            root=args.root,
            include=args.include,
            include_dir=args.include_dir,
            include_defaults=not args.no_defaults,
        )
        _write_json(args.output, manifest)
        print(
            json.dumps(manifest, indent=2, sort_keys=True)
            if args.json
            else render_manifest_text(manifest)
        )
        return 0 if manifest["status"] == "ready" else 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = verify_recovery_manifest(manifest, root=args.root)
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_verification_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
