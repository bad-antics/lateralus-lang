#!/usr/bin/env python3
"""
Lateralus canonical paper template (ReportLab, A4, Helvetica/Courier).

Matches the style of https://lateralus.dev/papers/pdf/memory-safety-ownership.pdf

Usage:
    from _lateralus_template import render_paper

    render_paper(
        out_path="papers/pdf/my-paper.pdf",
        title="My Paper Title",
        subtitle="A subtitle explaining the topic",
        meta="bad-antics · April 2026 · Lateralus Language Research",
        abstract="One-paragraph abstract of the paper.",
        sections=[
            ("1. Motivation", ["para 1...", "para 2..."]),
            ("2. Approach",   ["para 1...", ("code", "let x = 1\\nfn foo() -> int { 0 }"), "para 2..."]),
            ...
        ],
    )

A section's body is a list of items; each item is either:
  - a string (rendered as a justified paragraph, HTML-safe minimal markup
    supported: <b>, <i>, <code>, &mdash;, etc.)
  - ("code", "<verbatim code block>")
  - ("h3", "sub-heading text")
  - ("rule", "<formal-rule verbatim block>")
  - ("list", ["item 1", "item 2", ...])
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
)

# --------------------------------------------------------------------------
# Page decoration
# --------------------------------------------------------------------------

def _cover_page(canvas, doc):
    """Title page header (handled by flowables; this is intentionally empty)."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(A4[0] / 2, 2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _body_page(canvas, doc):
    """Every non-cover page: '|> LATERALUS' strip + centered title + page#."""
    canvas.saveState()
    # Header strip
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.drawString(2 * cm, A4[1] - 1.3 * cm, "|> LATERALUS")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#444444"))
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.3 * cm, doc.ltl_title)
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, A4[1] - 1.55 * cm, A4[0] - 2 * cm, A4[1] - 1.55 * cm)
    # Footer page number
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.5 * cm, f"Page {doc.page}")
    canvas.restoreState()


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------

def _styles():
    s = getSampleStyleSheet()
    body = ParagraphStyle(
        "LtlBody", parent=s["BodyText"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=colors.HexColor("#111111"),
        spaceAfter=8, alignment=4,  # 4 = TA_JUSTIFY
    )
    h1 = ParagraphStyle(
        "LtlH1", parent=s["Title"],
        fontName="Helvetica-Bold", fontSize=24, leading=28,
        textColor=colors.HexColor("#000000"),
        alignment=1, spaceBefore=0, spaceAfter=6,
    )
    h1sub = ParagraphStyle(
        "LtlH1Sub", parent=body,
        fontName="Helvetica", fontSize=13, leading=18,
        textColor=colors.HexColor("#444444"),
        alignment=1, spaceAfter=14,
    )
    meta = ParagraphStyle(
        "LtlMeta", parent=body,
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=colors.HexColor("#666666"),
        alignment=1, spaceAfter=18,
    )
    h2 = ParagraphStyle(
        "LtlH2", parent=s["Heading2"],
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=colors.HexColor("#111111"),
        spaceBefore=16, spaceAfter=8, keepWithNext=1,
    )
    h3 = ParagraphStyle(
        "LtlH3", parent=s["Heading3"],
        fontName="Helvetica-Bold", fontSize=11.5, leading=15,
        textColor=colors.HexColor("#222222"),
        spaceBefore=10, spaceAfter=5, keepWithNext=1,
    )
    abstract = ParagraphStyle(
        "LtlAbstract", parent=body,
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=colors.HexColor("#222222"),
        leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=14,
        borderPadding=8, borderWidth=0,
        backColor=colors.HexColor("#f4f4f4"),
    )
    code = ParagraphStyle(
        "LtlCode", parent=body,
        fontName="Courier", fontSize=9, leading=12,
        textColor=colors.HexColor("#111111"),
        backColor=colors.HexColor("#f7f7f7"),
        borderColor=colors.HexColor("#dddddd"),
        borderWidth=0.5, borderPadding=6,
        leftIndent=4, rightIndent=4, spaceAfter=8,
    )
    rule = ParagraphStyle(
        "LtlRule", parent=code,
        fontName="Courier", fontSize=9.5, leading=13,
        backColor=colors.HexColor("#fafaff"),
        borderColor=colors.HexColor("#666688"),
        borderWidth=1, borderPadding=7,
        leftIndent=10, rightIndent=10, spaceAfter=10,
    )
    footer = ParagraphStyle(
        "LtlFooter", parent=body,
        fontName="Helvetica", fontSize=9, leading=12,
        textColor=colors.HexColor("#666666"),
        spaceBefore=20, alignment=0,
    )
    tagline = ParagraphStyle(
        "LtlTagline", parent=body,
        fontName="Helvetica", fontSize=12, leading=16,
        textColor=colors.HexColor("#666666"),
        alignment=1, spaceBefore=80, spaceAfter=6,
    )
    return {
        "body": body, "h1": h1, "h1sub": h1sub, "meta": meta,
        "h2": h2, "h3": h3, "abstract": abstract,
        "code": code, "rule": rule, "footer": footer, "tagline": tagline,
    }


# --------------------------------------------------------------------------
# Content building
# --------------------------------------------------------------------------

def _safe_inline(txt: str) -> str:
    """Allow a small whitelist of inline HTML used in our papers.

    Canonical style (memory-safety-ownership.pdf) uses Helvetica + Helvetica-Bold
    + Courier ONLY — no italics embedded. We therefore strip <i>/<em> tags so
    ReportLab never substitutes Helvetica-Oblique.
    """
    import re
    out = re.sub(r"</?i\b[^>]*>", "", txt, flags=re.IGNORECASE)
    out = re.sub(r"</?em\b[^>]*>", "", out, flags=re.IGNORECASE)
    return out


def _build_flowables(title, subtitle, meta, abstract, sections, footer_text):
    st = _styles()
    flow = []

    # Cover
    flow.append(Spacer(1, 4 * cm))
    flow.append(Paragraph(title, st["h1"]))
    if subtitle:
        flow.append(Paragraph(subtitle, st["h1sub"]))
    flow.append(Paragraph("Lateralus Language", st["tagline"]))
    flow.append(PageBreak())

    # Meta + abstract
    if meta:
        flow.append(Paragraph(meta, st["meta"]))
    if abstract:
        flow.append(Paragraph(f"<b>ABSTRACT</b>&nbsp;&nbsp; {abstract}", st["abstract"]))

    # Sections
    for sec in sections:
        name, body = sec
        flow.append(Paragraph(name, st["h2"]))
        for item in body:
            if isinstance(item, str):
                flow.append(Paragraph(_safe_inline(item), st["body"]))
            elif isinstance(item, tuple) and len(item) == 2:
                kind, payload = item
                if kind == "code":
                    flow.append(Preformatted(payload, st["code"]))
                elif kind == "rule":
                    flow.append(Preformatted(payload, st["rule"]))
                elif kind == "h3":
                    flow.append(Paragraph(payload, st["h3"]))
                elif kind == "list":
                    items = [ListItem(Paragraph(_safe_inline(x), st["body"]),
                                      leftIndent=10, value="bulletchar")
                             for x in payload]
                    flow.append(ListFlowable(items, bulletType="bullet",
                                             leftIndent=16, bulletFontName="Helvetica"))
                else:
                    raise ValueError(f"unknown item kind: {kind}")
            else:
                raise ValueError(f"unknown section item: {item!r}")

    # Footer
    if footer_text:
        flow.append(Paragraph(footer_text, st["footer"]))

    return flow


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def render_paper(
    out_path: str | Path,
    title: str,
    subtitle: str = "",
    meta: str = "",
    abstract: str = "",
    sections: Iterable[tuple] = (),
    footer_text: str = (
        "Lateralus is an open-source, zero-dependency programming language. "
        "Project home: <code>https://lateralus.dev</code>. "
        "Source: <code>github.com/bad-antics/lateralus-lang</code>. "
        "Released under CC BY 4.0."
    ),
) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.2 * cm, bottomMargin=2.2 * cm,
        title=title, author="bad-antics",
    )
    doc.ltl_title = title

    # Two page templates: cover (blank) + body (with header/footer)
    cover_frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(2 * cm, 2.2 * cm, A4[0] - 4 * cm, A4[1] - 4.4 * cm,
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_cover_page),
        PageTemplate(id="body",  frames=[body_frame],  onPage=_body_page),
    ])

    flow = _build_flowables(title, subtitle, meta, abstract, sections, footer_text)
    # Switch to 'body' template after the cover PageBreak
    flow = [NextPageTemplate("body")] + flow

    doc.build(flow)
    _normalize_metadata(out, title)
    return out


def _normalize_metadata(pdf_path: Path, title: str) -> None:
    """Strip ReportLab-specific Producer/Creator + force PDF version 1.3
    so generated papers match the canonical corpus fingerprint."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return  # best-effort; leave as-is if pypdf missing
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter(clone_from=reader)
    # Clear metadata fields we want absent to match reference
    writer.add_metadata({
        "/Producer": "",
        "/Creator": "",
        "/Title": title,
        "/Author": "bad-antics",
    })
    with open(pdf_path, "wb") as fh:
        writer.write(fh)


if __name__ == "__main__":
    # Smoke test
    render_paper(
        "/tmp/_lateralus_template_smoke.pdf",
        title="Template Smoke Test",
        subtitle="Verifying the canonical ReportLab template renders cleanly",
        meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
        abstract="A tiny paper to verify the template emits an A4 Helvetica document.",
        sections=[
            ("1. Introduction", [
                "The Lateralus canonical paper template renders papers at A4 size using Helvetica for body and headings and Courier for code blocks.",
                ("code", "fn main() {\n    println(\"hello, lateralus\")\n}"),
                "This smoke test confirms paragraph, code, and heading rendering.",
            ]),
            ("2. Lists", [
                ("list", ["First item", "Second item", "Third item"]),
            ]),
        ],
    )
    print("ok: /tmp/_lateralus_template_smoke.pdf")
