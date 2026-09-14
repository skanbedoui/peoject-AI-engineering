"""Export the maintained Markdown report and postmortem to styled PDFs.

Optional dependencies: pip install -r requirements-dev.txt
"""

from pathlib import Path
from xml.sax.saxutils import escape

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
)

ROOT = Path(__file__).resolve().parents[1]
INK = colors.HexColor("#263a33")
GREEN = colors.HexColor("#347f60")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=30,
        textColor=INK,
        spaceAfter=14,
    )
)
styles.add(
    ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=GREEN,
        spaceBefore=14,
        spaceAfter=7,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "Copy",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=INK,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        "Cell",
        parent=styles["Copy"],
        fontSize=8,
        leading=11,
        spaceAfter=0,
        alignment=TA_LEFT,
    )
)


def inline(token):
    result = []
    for child in token.children or []:
        if child.type == "text":
            result.append(escape(child.content))
        elif child.type == "code_inline":
            result.append(
                f'<font name="Courier" size="8">{escape(child.content)}</font>'
            )
        elif child.type in ("softbreak", "hardbreak"):
            result.append("<br/>" if child.type == "hardbreak" else " ")
        elif child.type == "strong_open":
            result.append("<b>")
        elif child.type == "strong_close":
            result.append("</b>")
        elif child.type == "em_open":
            result.append("<i>")
        elif child.type == "em_close":
            result.append("</i>")
        # Link labels remain readable in a standalone printed document.
    return "".join(result)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#dce5df"))
    canvas.line(44, 40, A4[0] - 44, 40)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#78847e"))
    canvas.drawString(44, 27, "CS496 / PROJECT 0 / SYNTHETIC DEVELOPMENT BENCHMARK")
    canvas.drawRightString(A4[0] - 44, 27, str(doc.page))
    canvas.restoreState()


def export(source):
    tokens = (
        MarkdownIt("commonmark")
        .enable("table")
        .parse(source.read_text(encoding="utf-8"))
    )
    story, index = [], 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open":
            style = "ReportTitle" if token.tag == "h1" else "Section"
            story.append(Paragraph(inline(tokens[index + 1]), styles[style]))
            index += 3
            continue
        if token.type == "table_open":
            rows, row = [], []
            index += 1
            while tokens[index].type != "table_close":
                current = tokens[index]
                if current.type == "tr_open":
                    row = []
                elif current.type == "inline":
                    row.append(Paragraph(inline(current), styles["Cell"]))
                elif current.type == "tr_close":
                    rows.append(row)
                index += 1
            width = A4[0] - 88
            count = len(rows[0])
            widths = [width / count] * count
            if count >= 5:
                widths = [width * 0.25] + [width * 0.75 / (count - 1)] * (count - 1)
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5efea")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f5f7f6")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#b5cdbf")),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
        elif token.type == "inline":
            story.append(Paragraph(inline(token), styles["Copy"]))
        elif token.type == "fence":
            story.append(Preformatted(token.content.rstrip(), styles["Code"]))
            story.append(Spacer(1, 10))
        index += 1
    output = source.with_suffix(".pdf")
    SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=44,
        rightMargin=44,
        topMargin=42,
        bottomMargin=55,
        title=source.stem.title(),
        author="CS496 Project 0",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {output}")


if __name__ == "__main__":
    for filename in ("report.md", "postmortem.md"):
        export(ROOT / filename)
