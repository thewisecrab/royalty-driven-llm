"""Validate local documentation links for static hosting."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]

DOC_GLOBS = (
    "*.md",
    "docs/**/*.md",
    "docs/**/*.html",
    "examples/**/*.md",
    "paper/**/*.md",
    ".github/**/*.md",
    ".github/**/*.yml",
    ".github/**/*.yaml",
)

EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "build",
    "dist",
    "src/royalty_driven_llm.egg-info",
}

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*(?:\][^\[]*\[[^\]\n]*)*\]\(([^)\n]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s*\[(?!@)[^\]]+\]:\s+(\S+)", re.MULTILINE)
HTML_HREF_RE = re.compile(r"\bhref=[\"']([^\"']+)[\"']", re.IGNORECASE)
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_excluded(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    return bool(parts & EXCLUDED_PARTS)


def _iter_doc_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in DOC_GLOBS:
        files.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(path for path in files if not _is_excluded(path))


def _strip_markdown_code_blocks(text: str) -> str:
    return FENCED_BLOCK_RE.sub("", text)


def _normalize_markdown_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")].strip()
    if " " in target:
        return target.split()[0].strip()
    return target


def _is_external_or_virtual(target: str) -> bool:
    parsed = urlsplit(target)
    if parsed.scheme:
        return True
    return target.startswith(("#", "mailto:", "tel:"))


def _split_target(target: str) -> tuple[str, str]:
    before_fragment, _, fragment = target.partition("#")
    return before_fragment, fragment


def _resolve_target(source: Path, target: str) -> Path:
    path_part, _fragment = _split_target(target)
    decoded = unquote(path_part)
    if decoded.startswith("/"):
        return ROOT / decoded.lstrip("/")
    return (source.parent / decoded).resolve()


def _target_exists(path: Path) -> bool:
    if path.is_file():
        return True
    if path.is_dir() and (path / "index.html").is_file():
        return True
    return False


def _extract_links(path: Path, text: str) -> list[str]:
    scan_text = text if path.suffix.lower() in {".html", ".htm"} else _strip_markdown_code_blocks(text)
    links = [match.group(1) for match in MARKDOWN_LINK_RE.finditer(scan_text)]
    links.extend(match.group(1) for match in REFERENCE_LINK_RE.finditer(scan_text))
    links.extend(match.group(1) for match in HTML_HREF_RE.finditer(scan_text))
    return [_normalize_markdown_target(link) for link in links]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    checked_links: list[dict[str, str]] = []
    skipped_links: list[dict[str, str]] = []
    files = _iter_doc_files()

    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in _extract_links(path, text):
            if not target:
                continue
            if _is_external_or_virtual(target):
                skipped_links.append({"source": relpath(path), "target": target})
                continue
            resolved = _resolve_target(path, target)
            if not _target_exists(resolved):
                errors.append(
                    f"{relpath(path)} links to missing local target: {target}"
                )
                continue
            checked_links.append(
                {
                    "source": relpath(path),
                    "target": target,
                    "resolved": relpath(resolved),
                }
            )

    return {
        "status": "failed" if errors else "passed",
        "document_count": len(files),
        "checked_local_link_count": len(checked_links),
        "skipped_external_or_anchor_link_count": len(skipped_links),
        "errors": errors,
        "checked_local_links": checked_links,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"docs_link_audit status: {report['status']}",
        f"document_count: {report['document_count']}",
        f"checked_local_link_count: {report['checked_local_link_count']}",
        (
            "skipped_external_or_anchor_link_count: "
            f"{report['skipped_external_or_anchor_link_count']}"
        ),
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
