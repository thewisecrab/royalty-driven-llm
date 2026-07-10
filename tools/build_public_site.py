"""Build and audit the static RDLLM documentation site."""

from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import unquote, urlparse

import markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "_site"
REQUIRED_OUTPUTS = (
    "index.html",
    ".nojekyll",
    ".well-known/rdllm.json",
    "github_start_here.html",
    "first_5_minutes.html",
    "examples/live_use_cases/README.html",
    "examples/live_use_cases/screenshots/first-run.png",
    "examples/api_clients/README.html",
    "paper/rdllm_white_paper.html",
    "paper/rdllm_white_paper.pdf",
)

SITE_CSS = """
:root { color-scheme: light dark; --bg:#f7f8fa; --panel:#fff; --text:#17202a;
  --muted:#52606d; --line:#d7dde4; --accent:#087e8b; --code:#eef2f5; }
@media (prefers-color-scheme: dark) { :root { --bg:#111418; --panel:#171c21;
  --text:#edf2f7; --muted:#b8c2cc; --line:#38434d; --accent:#55c7d2; --code:#20272e; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:16px/1.6 system-ui,-apple-system,sans-serif; }
header { border-bottom:1px solid var(--line); background:var(--panel); }
.nav { max-width:1040px; margin:auto; padding:12px 20px; display:flex; gap:18px; align-items:center; flex-wrap:wrap; }
.brand { color:var(--text); font-weight:750; text-decoration:none; margin-right:auto; }
.nav a:not(.brand) { color:var(--muted); text-decoration:none; }
main { width:min(100% - 32px, 900px); margin:0 auto; padding:36px 0 72px; overflow-wrap:anywhere; }
h1 { font-size:clamp(2rem,4vw,3.2rem); line-height:1.1; margin:0 0 20px; letter-spacing:0; }
h2 { margin-top:38px; border-top:1px solid var(--line); padding-top:22px; }
h3 { margin-top:28px; }
p,li { max-width:76ch; }
a { color:var(--accent); }
pre { overflow-x:auto; padding:14px; border:1px solid var(--line); background:var(--code); border-radius:6px; }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.92em; }
:not(pre)>code { background:var(--code); padding:2px 5px; border-radius:4px; }
table { border-collapse:collapse; width:100%; display:block; overflow-x:auto; }
th,td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }
blockquote { margin-left:0; padding-left:16px; border-left:3px solid var(--accent); color:var(--muted); }
img { max-width:100%; height:auto; border:1px solid var(--line); }
.notice { border-left:4px solid var(--accent); background:var(--panel); padding:12px 16px; margin:18px 0; }
@media (max-width:560px) { main { width:min(100% - 24px,900px); padding-top:24px; }
  .nav { gap:12px; } h1 { font-size:2rem; } }
""".strip()


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


def _copy_sources(output: Path) -> None:
    shutil.copytree(ROOT / "docs", output)
    shutil.copytree(
        ROOT / "examples" / "live_use_cases",
        output / "examples" / "live_use_cases",
    )
    shutil.copytree(
        ROOT / "examples" / "api_clients",
        output / "examples" / "api_clients",
    )
    shutil.copy2(ROOT / "README.md", output / "README.md")
    (output / "paper").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / "paper" / "rdllm_white_paper.md",
        output / "paper" / "rdllm_white_paper.md",
    )
    shutil.copy2(
        ROOT / "paper" / "arxiv" / "rdllm_white_paper.pdf",
        output / "paper" / "rdllm_white_paper.pdf",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")


def _rewrite_links(text: str, path: Path, output: Path) -> str:
    relative = path.relative_to(output)
    if relative == Path("README.md"):
        text = text.replace("(docs/", "(")
    if relative.parts[:1] == ("i18n",):
        text = text.replace("../../../examples/", "../../examples/")
        text = text.replace("../../../README.md", "../../README.md")
    elif len(relative.parts) == 1:
        text = text.replace("../examples/", "examples/")
        text = text.replace("../paper/", "paper/")
        text = text.replace("../README.md", "README.md")
    text = re.sub(r"(?P<path>[^\s\"')>]+)\.md(?P<anchor>#[^\s\"')>]*)?", r"\g<path>.html\g<anchor>", text)
    return text


def _title(markdown_text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | RDLLM</title><style>{SITE_CSS}</style></head>
<body><header><nav class="nav"><a class="brand" href="/royalty-driven-llm/">RDLLM</a>
<a href="/royalty-driven-llm/first_5_minutes.html">Start</a>
<a href="/royalty-driven-llm/examples/live_use_cases/README.html">Use cases</a>
<a href="/royalty-driven-llm/paper/rdllm_white_paper.html">Paper</a>
<a href="https://github.com/thewisecrab/royalty-driven-llm">GitHub</a></nav></header>
<main>{body}</main></body></html>\n"""


def _render_markdown(output: Path) -> None:
    for path in sorted(output.rglob("*.md")):
        source = _rewrite_links(path.read_text(encoding="utf-8"), path, output)
        body = markdown.markdown(
            source,
            extensions=("fenced_code", "tables", "toc", "sane_lists"),
            output_format="html5",
        )
        destination = path.with_suffix(".html")
        destination.write_text(
            _html_page(_title(source, path.stem.replace("_", " ").title()), body),
            encoding="utf-8",
        )


def _rewrite_existing_html(output: Path) -> None:
    for path in sorted(output.rglob("*.html")):
        if path.name != "index.html":
            continue
        text = _rewrite_links(path.read_text(encoding="utf-8"), path, output)
        text = text.replace("../examples/", "examples/").replace("../paper/", "paper/")
        path.write_text(text, encoding="utf-8")


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    _copy_sources(output)
    _render_markdown(output)
    _rewrite_existing_html(output)


def audit(output: Path) -> list[str]:
    errors = [name for name in REQUIRED_OUTPUTS if not (output / name).is_file()]
    for path in sorted(output.rglob("*.html")):
        parser = _Links()
        parser.feed(path.read_text(encoding="utf-8"))
        for href in parser.hrefs:
            parsed = urlparse(href)
            if parsed.scheme or href.startswith(("#", "mailto:")):
                continue
            target_path = unquote(parsed.path)
            if target_path.startswith("/royalty-driven-llm/"):
                target = output / target_path.removeprefix("/royalty-driven-llm/")
            elif target_path == "/royalty-driven-llm/":
                target = output / "index.html"
            else:
                target = (path.parent / target_path).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                errors.append(f"{path.relative_to(output)}: broken link {href}")
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="rdllm-public-site-") as name:
            output = Path(name)
            build(output)
            errors = audit(output)
    else:
        output = args.output.resolve()
        build(output)
        errors = audit(output)
    if errors:
        print("public_site_build status: failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("public_site_build status: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
