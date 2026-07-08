"""Repository wrapper for the installable RDLLM service audit verifier CLI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.service_audit_verifier import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
