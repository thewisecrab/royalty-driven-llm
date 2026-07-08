"""Helpers for compact replay fixtures that reference generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_REF_KEY = "$artifact_ref"


def resolve_artifact_refs(value: Any, *, base_path: str | Path | None = None) -> Any:
    """Return a copy of ``value`` with local artifact references hydrated."""

    if isinstance(value, dict):
        ref = value.get(ARTIFACT_REF_KEY)
        if isinstance(ref, str) and ref:
            path = Path(ref)
            if not path.is_absolute():
                root = Path(base_path) if base_path is not None else Path.cwd()
                path = root / path
            loaded = json.loads(path.read_text(encoding="utf-8"))
            return resolve_artifact_refs(loaded, base_path=path.parent.parent)
        return {
            key: resolve_artifact_refs(child, base_path=base_path)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [resolve_artifact_refs(item, base_path=base_path) for item in value]
    return value
