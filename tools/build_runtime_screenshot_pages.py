"""Build browser-ready pages from current RDLLM runtime command output."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp" / "runtime-screenshots"


def _run(command: list[str]) -> str:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return result.stdout.strip()


def _json(command: list[str]) -> dict[str, Any]:
    return json.loads(_run(command))


def _first_run() -> str:
    lines = _run([sys.executable, "-m", "rdllm.first_run"]).splitlines()
    selected = lines[:18]
    source = next((line for line in lines if line.startswith("[S1]")), "")
    claim = next((line for line in lines if line.startswith("[C1]")), "")
    return "\n".join([*selected, "", source, "", claim])


def _cli_answer() -> str:
    lines = _run(
        [
            sys.executable,
            "-m",
            "rdllm.cli",
            "answer",
            "How should AI prove attribution?",
        ]
    ).splitlines()
    answer = lines[:8]
    source = next((line for line in lines if line.startswith("[S1]")), "")
    claim = next((line for line in lines if line.startswith("[C1]")), "")
    return "\n".join([*answer, "", "Sources", source, "", "Claim Evidence", claim])


def _summary(payload: dict[str, Any], section: str) -> str:
    summary = payload["sections"][section]
    ordered = [
        ("status", payload["status"]),
        *summary.items(),
    ]
    return "\n".join(f"{key}: {str(value).lower() if isinstance(value, bool) else value}" for key, value in ordered)


STYLE = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; background: #111418; }
body { color: #edf0f2; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
main { width: 1200px; min-height: 760px; padding: 46px 54px; background: #15191e; }
.top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.brand { display: flex; align-items: center; gap: 13px; font-size: 18px; font-weight: 700; }
.mark { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid #4e5965; background: #20262d; font: 700 13px ui-monospace, monospace; }
.chip { padding: 6px 9px; border: 1px solid #755f2a; color: #f3cf72; background: #211d14; font: 700 11px ui-monospace, monospace; text-transform: uppercase; }
.window { overflow: hidden; border: 1px solid #3b444e; background: #0d1013; box-shadow: 0 22px 55px rgba(0,0,0,.28); }
.bar { display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 16px; border-bottom: 1px solid #303840; background: #20252b; }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #66717c; }
.command { margin-left: 10px; color: #aeb7bf; font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; }
pre { height: 575px; margin: 0; padding: 25px 27px; overflow: hidden; white-space: pre-wrap; overflow-wrap: anywhere; color: #d7dde2; font: 14px/1.52 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }
.passed { color: #71d99e; }
.footer { display: flex; justify-content: space-between; margin-top: 18px; color: #87929d; font-size: 12px; }
"""


def _page(title: str, command: str, content: str) -> str:
    escaped = html.escape(content)
    escaped = escaped.replace("status: passed", '<span class="passed">status: passed</span>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main><div class="top"><div class="brand"><span class="mark">RD</span>{html.escape(title)}</div>
<span class="chip">synthetic fixture</span></div><section class="window"><div class="bar">
<span class="dot"></span><span class="dot"></span><span class="dot"></span>
<span class="command">$ {html.escape(command)}</span></div><pre>{escaped}</pre></section>
<div class="footer"><span>Captured from RDLLM 1.0 runtime</span><span>No external provider or payment execution</span></div>
</main></body></html>"""


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    service = _json([sys.executable, "tools/service_smoke.py", "--json"])
    provider = _json([sys.executable, "tools/provider_live_smoke.py", "--json"])
    pages = {
        "first-run.html": (
            "First run",
            "rdllm-first-run",
            _first_run(),
        ),
        "cli-answer-sources.html": (
            "Answer with sources",
            'rdllm answer "How should AI prove attribution?"',
            _cli_answer(),
        ),
        "service-smoke.html": (
            "Service verification",
            "python tools/service_smoke.py --json",
            _summary(service, "attribute"),
        ),
        "provider-live-smoke.html": (
            "Provider-grounded attribution",
            "python tools/provider_live_smoke.py --json",
            _summary(provider, "provider"),
        ),
    }
    for name, (title, command, content) in pages.items():
        (OUTPUT / name).write_text(_page(title, command, content), encoding="utf-8")
    print(f"runtime_screenshot_pages status: passed ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
