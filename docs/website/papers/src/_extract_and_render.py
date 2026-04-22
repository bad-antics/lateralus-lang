#!/usr/bin/env python3
"""Extract content from existing non-canonical PDFs and re-render in canonical style.

Uses PyMuPDF (fitz) to read font-tagged spans so we can distinguish:
  * Title     (Helvetica-Bold, large)
  * Subtitle  (Helvetica, medium)
  * Headings  (Helvetica-Bold, ~12-14pt)
  * Body      (Helvetica, ~10pt)
  * Code      (Courier* fonts)

The output is fed into ``_lateralus_template.render_paper`` which produces a
PDF matching the canonical style of ``memory-safety-ownership.pdf``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from _lateralus_template import render_paper

PDF_DIR = Path(__file__).resolve().parent.parent / "pdf"
ARCHIVE_DIR = Path(__file__).resolve().parents[4] / "archive" / "canonical-theme-reference" / "papers"

# ---------- page filtering helpers ---------------------------------------

FOOTER_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+\s*[\*\|·]"),
    re.compile(r"^\s*Page\s+\d+\s*$"),
    re.compile(r"^\s*\|\>\s*LATERALUS"),
    re.compile(r"bad-antics\s*[\*\|·]"),
    re.compile(r"^\s*lateralus\.dev\s*$"),
    re.compile(r"^\s*Lateralus Language\s*$"),
    re.compile(r"^\s*Lateralus:?\s*A Pipeline-Native"),
    re.compile(r"^\s*Types as Capabilities"),
]


def _is_footer(text: str) -> bool:
    return any(p.search(text) for p in FOOTER_PATTERNS)


# ---------- extraction ---------------------------------------------------

def _page_blocks(page):
    """Return list of blocks; each block is list of (kind, text) items, preserving line structure."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        items = []
        for line in block["lines"]:
            # Assemble the full line text from its spans; classify by dominant font
            line_text = "".join(s["text"] for s in line["spans"]).rstrip()
            if not line_text.strip():
                continue
            # Dominant font: longest span wins
            dom = max(line["spans"], key=lambda s: len(s["text"]))
            span = {
                "text": line_text,
                "font": dom["font"],
                "size": round(dom["size"], 1),
                "y": round(line["spans"][0]["bbox"][1], 1),
            }
            items.append((span, line_text))
        if items:
            out.append(items)
    return out


def _classify(span) -> str:
    font = span["font"]
    size = span["size"]
    if "Courier" in font or "Mono" in font:
        return "code"
    if ("Bold" in font or "Black" in font) and size >= 18:
        return "title"
    if ("Bold" in font or "Black" in font) and size >= 11.5:
        return "heading"
    if size >= 12.5 and "Bold" not in font:
        return "subtitle"
    return "body"


HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)[\.\)]?\s+([A-Z][^\n]{2,120})\s*$")
SUB_HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9\-\s,:/']{3,100}$")


def extract_paper(pdf_path: Path) -> dict:
    """Parse a PDF preserving paragraph structure via block boundaries."""
    doc = fitz.open(pdf_path)

    title = ""
    subtitle = ""
    abstract = ""
    keywords = ""
    sections: List[Tuple[str, list]] = []
    state = {"current_section": None}  # use dict to avoid nonlocal issues

    def _push_para(text: str):
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        if state["current_section"] is None:
            # pre-section content goes to abstract/keywords
            nonlocal abstract, keywords
            if text.lower().startswith("keywords:"):
                keywords = text[len("keywords:"):].strip(" :")
            elif not abstract:
                abstract = text
            else:
                # Further pre-section paragraphs: append to abstract
                abstract = (abstract + "\n\n" + text).strip()
        else:
            state["current_section"][1].append(text)

    def _push_code(text: str):
        text = text.rstrip()
        if not text.strip():
            return
        if state["current_section"] is None:
            # orphan code before first section — create an Overview section
            state["current_section"] = ("Overview", [])
            sections.append(state["current_section"])
        state["current_section"][1].append(("code", text))

    def _push_heading(text: str):
        text = text.strip()
        # Dedupe consecutive identical headings (page breaks can cause repeats)
        if sections and sections[-1][0].strip() == text and not sections[-1][1]:
            return
        state["current_section"] = (text, [])
        sections.append(state["current_section"])

    for page in doc:
        for block in _page_blocks(page):
            # Determine block kind from first non-footer line
            block_lines = []
            block_kind = None
            block_code_lines = []
            for span, text in block:
                if _is_footer(text):
                    continue
                kind = _classify(span)
                block_lines.append((kind, text, span))

            if not block_lines:
                continue

            # Capture title/subtitle at top of document
            if not title:
                for kind, text, span in block_lines:
                    if kind == "title":
                        title = text.strip()
                        break
            if title and not subtitle:
                for kind, text, span in block_lines:
                    if kind == "subtitle" and text.strip() != title:
                        subtitle = text.strip()
                        break

            # Classify block by majority content
            code_count = sum(1 for k, _, _ in block_lines if k == "code")
            heading_count = sum(1 for k, _, _ in block_lines if k == "heading")
            is_code_block = code_count >= len(block_lines) * 0.5 and code_count >= 1

            if is_code_block:
                code_text = "\n".join(text for _, text, _ in block_lines)
                _push_code(code_text)
                continue

            # Non-code block: scan for headings within, and accumulate body text per para.
            # We treat a block as a single paragraph UNLESS it contains a heading-style line,
            # in which case that line splits the paragraph.
            buf: List[str] = []
            for kind, text, span in block_lines:
                stripped = text.strip()
                if stripped == title or stripped == subtitle:
                    continue
                is_heading_line = (
                    kind == "heading"
                    or HEADING_RE.match(stripped) is not None
                )
                if is_heading_line and len(stripped) <= 120:
                    if buf:
                        _push_para(" ".join(buf))
                        buf = []
                    _push_heading(stripped)
                else:
                    buf.append(text)
            if buf:
                _push_para(" ".join(buf))

    doc.close()
    return {
        "title": title,
        "subtitle": subtitle,
        "abstract": abstract,
        "keywords": keywords,
        "sections": sections,
    }


# ---------- render helper ------------------------------------------------

def render_from_pdf(pdf_path: Path, out_dir: Path | None = None):
    data = extract_paper(pdf_path)
    out = (out_dir or PDF_DIR) / pdf_path.name
    title = data["title"] or pdf_path.stem.replace("-", " ").title()
    subtitle = data["subtitle"] or ""
    abstract = data["abstract"] or ""
    if data["keywords"]:
        abstract = (abstract + f"\n\nKeywords: {data['keywords']}").strip()

    # Keep extractor-produced paragraphs as-is (block boundaries already
    # reflect author intent). Only split if a single body paragraph exceeds
    # 2500 chars, which usually indicates a block the PDF merged spuriously.
    sections = []
    for title_s, items in data["sections"]:
        new_items = []
        for it in items:
            if isinstance(it, tuple):
                new_items.append(it)
                continue
            if len(it) <= 2500:
                new_items.append(it)
                continue
            sentences = re.split(r"(?<=[\.\!\?])\s+(?=[A-Z])", it)
            para = []
            size = 0
            for s in sentences:
                para.append(s)
                size += len(s)
                if size > 1200:
                    new_items.append(" ".join(para).strip())
                    para = []
                    size = 0
            if para:
                new_items.append(" ".join(para).strip())
        sections.append((title_s, new_items))

    render_paper(
        out_path=str(out),
        title=title,
        subtitle=subtitle,
        meta="bad-antics · April 2026 · Lateralus Language Research",
        abstract=abstract,
        sections=sections,
    )
    return out


def _resolve_source(name: str) -> Path | None:
    """Prefer archived original (full content); fall back to current pdf/."""
    arc = ARCHIVE_DIR / name
    if arc.exists():
        return arc
    cur = PDF_DIR / name
    if cur.exists():
        return cur
    return None


# ---------- CLI ----------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    names: List[str] = []
    if args:
        names = args
    else:
        for line in sys.stdin:
            s = line.strip()
            if s:
                names.append(s)

    ok = fail = skip = 0
    for name in names:
        src = _resolve_source(name)
        if src is None:
            print(f"SKIP (no source): {name}")
            skip += 1
            continue
        try:
            render_from_pdf(src)
            origin = "archive" if ARCHIVE_DIR in src.parents else "pdf"
            print(f"OK ({origin}): {name}")
            ok += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            fail += 1
    print(f"--- {ok} ok, {fail} fail, {skip} skip ---")
