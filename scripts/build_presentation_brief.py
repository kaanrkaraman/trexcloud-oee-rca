# -*- coding: utf-8 -*-
"""Build a shareable PDF companion for the professional presentation brief."""
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

SOURCE = Path("SUNUM_PROFESYONEL_TASARIM_BRIFI.md")
OUT = Path("SUNUM_PROFESYONEL_TASARIM_BRIFI.pdf")


def first_font(*paths):
    return next(str(p) for p in map(Path, paths) if p.exists())


pdfmetrics.registerFont(TTFont("AR", first_font(
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf")))
pdfmetrics.registerFont(TTFont("ARB", first_font(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf")))

INK = colors.HexColor("#17201c")
GREEN = colors.HexColor("#127145")
MUTED = colors.HexColor("#637169")
LINE = colors.HexColor("#d5dfd9")
SOFT = colors.HexColor("#edf5f0")

H1 = ParagraphStyle("h1", fontName="ARB", fontSize=23, leading=27, textColor=INK,
                    spaceAfter=12)
H2 = ParagraphStyle("h2", fontName="ARB", fontSize=15, leading=19, textColor=GREEN,
                    spaceBefore=10, spaceAfter=6)
H3 = ParagraphStyle("h3", fontName="ARB", fontSize=11.5, leading=15, textColor=INK,
                    spaceBefore=7, spaceAfter=4)
BODY = ParagraphStyle("body", fontName="AR", fontSize=9.3, leading=13.2, textColor=INK,
                      spaceAfter=4)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=12, firstLineIndent=-7,
                        bulletIndent=2, spaceAfter=2)
QUOTE = ParagraphStyle("quote", parent=BODY, leftIndent=12, rightIndent=8,
                       borderColor=GREEN, borderWidth=1, borderPadding=7,
                       backColor=SOFT, textColor=INK, spaceBefore=4, spaceAfter=7)
CODE = ParagraphStyle("code", parent=BODY, fontName="AR", fontSize=8.5,
                      textColor=MUTED, leftIndent=8)


def inline(text):
    text = re.sub(r"`([^`]+)`", r'<font name="AR" color="#526159">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text.replace("&", "&amp;").replace("&amp;lt;", "&lt;").replace(
        "&amp;gt;", "&gt;")


def table_from(lines):
    rows = []
    for line in lines:
        values = [v.strip() for v in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", value) for value in values):
            continue
        rows.append([Paragraph(inline(v), BODY) for v in values])
    if not rows:
        return None
    count = len(rows[0])
    widths = [165 * mm / count] * count
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "ARB"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse_markdown(text):
    story = []
    lines = text.splitlines()
    index = 0
    table_lines = []
    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            table = table_from(table_lines)
            if table:
                story.extend([table, Spacer(1, 6)])
            continue
        if line.startswith("# "):
            story.extend([Paragraph(inline(line[2:]), H1), Spacer(1, 3)])
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), H2))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), H3))
        elif line.startswith("- [ ] "):
            story.append(Paragraph("□ " + inline(line[6:]), BULLET))
        elif line.startswith("- "):
            story.append(Paragraph("• " + inline(line[2:]), BULLET))
        elif re.match(r"^\d+\. ", line):
            story.append(Paragraph(inline(line), BULLET))
        elif line.startswith("> "):
            story.append(Paragraph(inline(line[2:]), QUOTE))
        elif line.strip():
            story.append(Paragraph(inline(line), BODY))
        else:
            story.append(Spacer(1, 3))
        index += 1
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 13 * mm, 190 * mm, 13 * mm)
    canvas.setFont("AR", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 8 * mm, "trexCloud · Profesyonel Sunum Tasarım Brifi")
    canvas.drawRightString(190 * mm, 8 * mm, f"s. {doc.page}")
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="trexCloud Profesyonel Sunum Tasarım Brifi",
    )
    doc.build(parse_markdown(SOURCE.read_text(encoding="utf-8")),
              onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
