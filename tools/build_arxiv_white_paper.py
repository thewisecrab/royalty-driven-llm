"""Build the RDLLM white paper PDF for arXiv-style submission.

The source of truth is paper/rdllm_white_paper.md. The output is an
author-produced, machine-readable PDF with simple scholarly formatting.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "rdllm_white_paper.md"
OUT_DIR = ROOT / "paper" / "arxiv"
OUTPUT = OUT_DIR / "rdllm_white_paper.pdf"

TITLE = (
    "RDLLM: Verifiable Source Attribution and Creator-Value Accounting "
    "for Grounded AI Outputs"
)
AUTHOR = "Siddharth Nilesh Patel"
SUBTITLE = "Public technical white paper, version 2026-07-10"


def inline_markup(text: str) -> str:
    """Escape text and preserve lightweight inline code spans."""
    escaped = html.escape(text)
    escaped = re.sub(
        r"`([^`]+)`",
        lambda match: '<font name="Courier">%s</font>' % match.group(1),
        escaped,
    )
    return escaped


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|?[\s:\-|\+]+\|?", stripped)) and "---" in stripped


def parse_table(lines: list[str], start: int) -> tuple[Table, int]:
    rows: list[list[str]] = []
    i = start
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            rows.append(cells)
        i += 1

    if not rows:
        return Table([[""]]), i

    max_cols = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (max_cols - len(row)))

    styles = build_styles()
    body_style = styles["TableCell"]
    header_style = styles["TableHeader"]
    data = []
    for row_index, row in enumerate(rows):
        style = header_style if row_index == 0 else body_style
        data.append([Paragraph(inline_markup(cell), style) for cell in row])

    total_width = 7.0 * inch
    col_widths = [total_width / max_cols] * max_cols
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table, i


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitlePageTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Byline",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyJustified",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13.5,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletBody",
            parent=styles["BodyJustified"],
            leftIndent=18,
            firstLineIndent=-10,
            bulletIndent=6,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlock",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            leftIndent=8,
            rightIndent=8,
            borderPadding=6,
            backColor=colors.HexColor("#F8FAFC"),
            borderColor=colors.HexColor("#CBD5E1"),
            borderWidth=0.25,
            spaceBefore=6,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
        )
    )
    return styles


def make_code_block(lines: list[str], styles) -> Paragraph:
    rendered = "<br/>".join(inline_markup(line) for line in lines)
    return Paragraph(rendered or " ", styles["CodeBlock"])


def flush_paragraph(story, paragraph_lines: list[str], styles) -> None:
    if not paragraph_lines:
        return
    text = " ".join(line.strip() for line in paragraph_lines)
    story.append(Paragraph(inline_markup(text), styles["BodyJustified"]))
    paragraph_lines.clear()


def build_story(markdown: str):
    styles = build_styles()
    story = [
        Paragraph(TITLE, styles["TitlePageTitle"]),
        Paragraph(f"Author: {AUTHOR}", styles["Byline"]),
        Paragraph(SUBTITLE, styles["Byline"]),
        Spacer(1, 0.18 * inch),
    ]

    lines = markdown.splitlines()
    paragraph_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("# "):
            i += 1
            continue

        if (
            line.startswith("Version:")
            or line.startswith("Author:")
            or line.startswith("Status:")
            or line.startswith("Document label:")
        ):
            i += 1
            continue

        if line.strip() == "Companion artifacts:":
            flush_paragraph(story, paragraph_lines, styles)
            story.append(Paragraph("Companion artifacts", styles["H2Custom"]))
            i += 1
            continue

        if line.strip().startswith("```"):
            if in_code:
                story.append(make_code_block(code_lines, styles))
                code_lines = []
                in_code = False
            else:
                flush_paragraph(story, paragraph_lines, styles)
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if not line.strip():
            flush_paragraph(story, paragraph_lines, styles)
            i += 1
            continue

        if line.lstrip().startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            flush_paragraph(story, paragraph_lines, styles)
            table, next_i = parse_table(lines, i)
            story.append(table)
            story.append(Spacer(1, 0.12 * inch))
            i = next_i
            continue

        if line.startswith("## "):
            flush_paragraph(story, paragraph_lines, styles)
            heading = line[3:].strip()
            if heading == "Primary Sources And Evidence Base":
                story.append(PageBreak())
            story.append(Paragraph(inline_markup(heading), styles["H1Custom"]))
            i += 1
            continue

        if line.startswith("### "):
            flush_paragraph(story, paragraph_lines, styles)
            story.append(Paragraph(inline_markup(line[4:].strip()), styles["H2Custom"]))
            i += 1
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", line)
        numbered = re.match(r"^(\d+)\.\s+(.*)$", line)
        if bullet:
            flush_paragraph(story, paragraph_lines, styles)
            story.append(Paragraph(inline_markup(bullet.group(1)), styles["BulletBody"], bulletText="-"))
            i += 1
            continue
        if numbered:
            flush_paragraph(story, paragraph_lines, styles)
            story.append(
                Paragraph(
                    inline_markup(numbered.group(2)),
                    styles["BulletBody"],
                    bulletText=f"{numbered.group(1)}.",
                )
            )
            i += 1
            continue

        paragraph_lines.append(line)
        i += 1

    flush_paragraph(story, paragraph_lines, styles)
    return story


def add_page_metadata(canvas, doc):
    canvas.setTitle(TITLE)
    canvas.setAuthor(AUTHOR)
    canvas.setSubject("Verifiable AI source attribution and creator-value accounting")
    canvas.setCreator("RDLLM build_arxiv_white_paper.py")
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawRightString(7.5 * inch, 0.45 * inch, f"{doc.page}")
    canvas.restoreState()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    markdown = SOURCE.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.7 * inch,
        title=TITLE,
        author=AUTHOR,
        subject="Verifiable AI source attribution and creator-value accounting",
    )
    doc.build(build_story(markdown), onFirstPage=add_page_metadata, onLaterPages=add_page_metadata)
    print(OUTPUT)


if __name__ == "__main__":
    main()
