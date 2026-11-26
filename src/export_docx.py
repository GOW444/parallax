"""Export report/A3_report.md to report/A3_report.docx with python-docx.

Handles exactly the markdown subset that src/report.py writes: #/##/### headings,
paragraphs with **bold** and *italic*, "- " bullets, "> " quote blocks (inferences),
pipe tables and ![..](path) images. Anything else is written as plain text, so nothing
is silently dropped.
"""

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from src.report import REPORT_DIR, REPORT_MD

DOCX_PATH = REPORT_DIR / "A3_report.docx"
IMAGE_WIDTH = Cm(16)
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def _add_runs(paragraph, text: str) -> None:
    """Add text to a paragraph, turning **bold**, *italic* and `code` into styled runs."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def _shade(cell, hex_fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), hex_fill)
    props.append(shading)


def _add_table(doc, rows: list[list[str]]) -> None:
    header, body = rows[0], rows[1:]
    table = doc.add_table(rows=1 + len(body), cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r, values in enumerate([header] + body):
        for c, value in enumerate(values):
            cell = table.cell(r, c)
            cell.text = ""
            para = cell.paragraphs[0]
            _add_runs(para, value)
            for run in para.runs:
                run.font.size = Pt(8.5)
                if r == 0:
                    run.bold = True
            if r == 0:
                _shade(cell, "D9E2F3")
    doc.add_paragraph()


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def export(md_path: Path = REPORT_MD, out_path: Path = DOCX_PATH) -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for section in doc.sections:
        section.left_margin = section.right_margin = Cm(2.2)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.fullmatch(r"\|(-+\|)+", lines[i].strip()):
                    block.append(_split_row(lines[i]))
                i += 1
            _add_table(doc, block)
            continue
        image = re.fullmatch(r"!\[[^\]]*\]\(([^)]+)\)", line.strip())
        if image:
            path = (md_path.parent / image.group(1)).resolve()
            doc.add_picture(str(path), width=IMAGE_WIDTH)
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue
        heading = re.match(r"(#{1,3}) (.*)", line)
        if heading:
            level = len(heading.group(1))
            doc.add_heading(heading.group(2), level=0 if level == 1 else level - 1)
            i += 1
            continue
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i].lstrip("> ").strip())
                i += 1
            for text in [b for b in block if b]:
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.8)
                _add_runs(para, text)
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
            continue
        if line.startswith("- "):
            _add_runs(doc.add_paragraph(style="List Bullet"), line[2:])
            i += 1
            continue
        para = doc.add_paragraph()
        _add_runs(para, line)
        if line.startswith("**Figure") or line.startswith("**Table"):
            for run in para.runs:
                run.font.size = Pt(9)
        i += 1

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    print(export())
