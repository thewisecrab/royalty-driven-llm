"""Audit public package metadata against the production readiness claim."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"

PRODUCTION_CLASSIFIER = "Development Status :: 5 - Production/Stable"
FORBIDDEN_DEVELOPMENT_STATUS_PREFIXES = (
    "Development Status :: 1 - Planning",
    "Development Status :: 2 - Pre-Alpha",
    "Development Status :: 3 - Alpha",
    "Development Status :: 4 - Beta",
)
REQUIRED_CLASSIFIERS = (
    PRODUCTION_CLASSIFIER,
    "Intended Audience :: Developers",
    "Intended Audience :: Legal Industry",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
)
REQUIRED_KEYWORDS = (
    "ai-attribution",
    "llm",
    "royalties",
    "source-citations",
    "provenance",
    "model-providers",
    "creator-economy",
)
REQUIRED_URLS = ("Homepage", "Documentation", "Issues", "Source")
REQUIRED_CONSOLE_SCRIPTS = (
    "rdllm",
    "rdllm-first-run",
    "rdllm-operator-acceptance",
    "rdllm-operator-acceptance-matrix",
    "rdllm-operator-bootstrap",
    "rdllm-operator-doctor",
    "rdllm-operator-launch-gate",
    "rdllm-operator-profile",
    "rdllm-operator-recovery",
    "rdllm-operator-support-bundle",
    "rdllm-production-readiness-verify",
    "rdllm-service",
    "rdllm-service-audit-verify",
    "rdllm-service-config",
    "rdllm-service-response-verify",
    "rdllm-source-footer-verify",
)
MINIMUM_PRODUCTION_MAJOR_VERSION = 1


def _loads_toml(text: str) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        return _loads_minimal_project_toml(text)
    return tomllib.loads(text)


def _quoted_values(value: str) -> list[str]:
    values: list[str] = []
    for raw in re.findall(r'"((?:[^"\\]|\\.)*)"', value):
        values.append(bytes(raw, "utf-8").decode("unicode_escape"))
    return values


def _loads_minimal_project_toml(text: str) -> dict[str, Any]:
    sections: dict[str, dict[str, Any]] = {}
    current_section = ""
    lines = iter(text.splitlines())
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped.strip("[]")
            sections.setdefault(current_section, {})
            continue
        if not current_section or "=" not in stripped:
            continue
        key, value = (part.strip() for part in stripped.split("=", 1))
        if value == "[":
            collected: list[str] = []
            for array_line in lines:
                if array_line.strip() == "]":
                    break
                collected.append(array_line)
            sections[current_section][key] = _quoted_values("\n".join(collected))
        elif value.startswith("[") and value.endswith("]"):
            sections[current_section][key] = _quoted_values(value)
        elif value.startswith('"') and value.endswith('"'):
            values = _quoted_values(value)
            sections[current_section][key] = values[0] if values else ""
    project = sections.get("project", {})
    if "project.urls" in sections:
        project["urls"] = sections["project.urls"]
    if "project.scripts" in sections:
        project["scripts"] = sections["project.scripts"]
    return {"project": project}


def _major_version(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)\.\d+\.\d+(?:[A-Za-z0-9_.+-]*)?", value)
    if not match:
        return None
    return int(match.group(1))


def audit(path: Path = PYPROJECT) -> dict[str, Any]:
    errors: list[str] = []
    data = _loads_toml(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if not isinstance(project, dict):
        return {
            "status": "failed",
            "errors": ["project metadata section missing"],
            "name": "",
            "version": "",
            "development_status": "",
            "console_script_count": 0,
            "required_console_script_count": len(REQUIRED_CONSOLE_SCRIPTS),
        }

    classifiers = project.get("classifiers", [])
    if not isinstance(classifiers, list):
        classifiers = []
        errors.append("project.classifiers: expected array")
    keywords = project.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
        errors.append("project.keywords: expected array")
    urls = project.get("urls", {})
    if not isinstance(urls, dict):
        urls = {}
        errors.append("project.urls: expected table")
    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
        errors.append("project.scripts: expected table")

    for required in REQUIRED_CLASSIFIERS:
        if required not in classifiers:
            errors.append(f"project.classifiers: missing {required!r}")
    for classifier in classifiers:
        if any(
            str(classifier).startswith(prefix)
            for prefix in FORBIDDEN_DEVELOPMENT_STATUS_PREFIXES
        ):
            errors.append(f"project.classifiers: non-production status {classifier!r}")
    for keyword in REQUIRED_KEYWORDS:
        if keyword not in keywords:
            errors.append(f"project.keywords: missing {keyword!r}")
    for label in REQUIRED_URLS:
        if not urls.get(label):
            errors.append(f"project.urls.{label}: missing")
    for script in REQUIRED_CONSOLE_SCRIPTS:
        if not scripts.get(script):
            errors.append(f"project.scripts.{script}: missing")

    version = str(project.get("version", ""))
    if project.get("name") != "royalty-driven-llm":
        errors.append("project.name: expected 'royalty-driven-llm'")
    if not version:
        errors.append("project.version: missing")
    elif _major_version(version) is None:
        errors.append("project.version: expected semantic version")
    elif _major_version(version) < MINIMUM_PRODUCTION_MAJOR_VERSION:
        errors.append("project.version: production/stable releases must be >=1.0.0")
    if project.get("readme") != "README.md":
        errors.append("project.readme: expected 'README.md'")
    description = str(project.get("description", ""))
    for term in ("Provider-neutral", "source-footer", "royalty-settlement"):
        if term not in description:
            errors.append(f"project.description: missing {term!r}")
    if project.get("dependencies") != []:
        errors.append("project.dependencies: expected no required runtime dependencies")
    if project.get("license") != "MIT":
        errors.append("project.license: expected 'MIT'")
    if project.get("requires-python") != ">=3.10":
        errors.append("project.requires-python: expected '>=3.10'")
    if not (ROOT / "LICENSE").is_file():
        errors.append("LICENSE: missing")

    package_init = (ROOT / "src" / "rdllm" / "__init__.py").read_text(
        encoding="utf-8"
    )
    if "prototype" in package_init.lower():
        errors.append("src/rdllm/__init__.py: must not describe RDLLM as a prototype")
    if "production-grade" not in package_init.lower():
        errors.append("src/rdllm/__init__.py: missing production-grade positioning")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f'version: "{version}"' not in citation:
        errors.append("CITATION.cff: version does not match project.version")
    if 'license: "MIT"' not in citation:
        errors.append("CITATION.cff: missing MIT license")
    if "type: software" not in citation:
        errors.append("CITATION.cff: missing software type")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version} -" not in changelog:
        errors.append("CHANGELOG.md: missing current project.version entry")
    if "production-grade open-source baseline" not in changelog:
        errors.append("CHANGELOG.md: missing production-grade release note")

    development_status = next(
        (
            str(classifier)
            for classifier in classifiers
            if str(classifier).startswith("Development Status ::")
        ),
        "",
    )
    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "name": str(project.get("name", "")),
        "version": version,
        "development_status": development_status,
        "console_script_count": len(scripts),
        "required_console_script_count": len(REQUIRED_CONSOLE_SCRIPTS),
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"package_metadata_audit status: {report['status']}",
        f"name: {report.get('name', '')}",
        f"version: {report.get('version', '')}",
        f"development_status: {report.get('development_status', '')}",
        f"console_script_count: {report.get('console_script_count', 0)}",
        "required_console_script_count: "
        f"{report.get('required_console_script_count', 0)}",
    ]
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = audit()
    output = json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report)
    print(output)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
