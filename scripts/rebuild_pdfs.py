#!/usr/bin/env python3
"""
rebuild_pdfs.py — Rebuild ALL site PDFs with the exact style of pattern-matching-adts.pdf

For each PDF in docs/website/papers/pdf/:
  1. Extract raw text via pdftotext
  2. Parse title, subtitle, sections
  3. Pull the official abstract from papers/index.html
  4. Regenerate the PDF using the canonical Doc class (series="Lateralus Language",
     sections numbered from 1, correct colour palette)

Usage
-----
  python scripts/rebuild_pdfs.py              # rebuild every PDF
  python scripts/rebuild_pdfs.py --dry-run    # show parse results, no writes
  python scripts/rebuild_pdfs.py --pdf NAME   # rebuild one file (e.g. capability-based-security.pdf)

Requirements
------------
  pip install fpdf2
  sudo apt-get install poppler-utils    # for pdftotext
"""

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
PDF_DIR        = REPO_ROOT / "docs" / "website" / "papers" / "pdf"
PDF_BACKUP_DIR = REPO_ROOT / "docs" / "website" / "papers" / "pdf-backup"
HTML_PATH = REPO_ROOT / "docs" / "website" / "papers" / "index.html"

# ---------------------------------------------------------------------------
# Colour palette  (identical to paper_bot.py — DO NOT change)
# ---------------------------------------------------------------------------
YELLOW = (255, 214,   0)
CYAN   = ( 77, 208, 225)
WHITE  = (255, 255, 255)
GREY   = (180, 180, 180)
DARK   = ( 16,   0,  42)
RULE   = (100,  80, 140)
GREEN  = (180, 255, 180)
PURPLE = ( 24,   8,  54)

# ---------------------------------------------------------------------------
# Unicode → Latin-1 cleaner
# ---------------------------------------------------------------------------
_REPL = {
    "\u2014": "--", "\u2013": "-",
    "\u2019": "'",  "\u2018": "'",
    "\u201c": '"',  "\u201d": '"',
    "\u00b7": "*",  "\u25b8": ">",
    "\u00b0": " deg", "\u00d7": "x",
    "\u00ae": "(R)", "\u2122": "(TM)",
    "\u2192": "->", "\u2190": "<-",
    "\u21d2": "=>", "\u2026": "...",
    "\u2265": ">=", "\u2264": "<=",
    "\u2260": "!=", "\u00b1": "+/-",
    "\u03b1": "alpha", "\u03b2": "beta", "\u03bb": "lambda",
    "\u03bc": "mu",    "\u03c3": "sigma", "\u03c0": "pi",
    "\u221e": "inf",   "\u2208": "in",    "\u2209": "not in",
    "\u2282": "subset","\u2283": "supset","\u2229": "intersect",
    "\u222a": "union", "\u2200": "forall","\u2203": "exists",
    "\u22a2": "|-",    "\u22a8": "|=",
}

def _clean(s: str) -> str:
    for k, v in _REPL.items():
        s = s.replace(k, v)
    # strip remaining non-latin-1
    return re.sub(r"[^\x00-\xff]", "-", s)


# ---------------------------------------------------------------------------
# Abstract extraction from papers/index.html
# ---------------------------------------------------------------------------
def _load_abstracts() -> dict[str, str]:
    """Return {pdf_filename: abstract_text} from the site's papers index."""
    if not HTML_PATH.exists():
        print(f"  WARN: {HTML_PATH} not found — abstracts will be empty")
        return {}

    raw = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    abstracts: dict[str, str] = {}

    # Each paper card looks like:
    #   <a href="/papers/pdf/FILENAME.pdf?v=..." ...>
    #   ...
    #   <p class="paper-abstract"><strong>Abstract:</strong> TEXT</p>
    # Split on paper-card divs so each chunk contains exactly one card
    card_parts = re.split(r'<div class="paper-card"', raw)
    pdf_re2  = re.compile(r'href="/papers/pdf/([^"?]+\.pdf)')
    abs_re2  = re.compile(r'class="paper-abstract"[^>]*><strong>Abstract:</strong>\s*(.*?)</p>', re.DOTALL)
    for part in card_parts[1:]:
        pdf_m2 = pdf_re2.search(part)
        abs_m2 = abs_re2.search(part)
        if pdf_m2 and abs_m2:
            fname2    = pdf_m2.group(1)
            abstract2 = html.unescape(re.sub(r"<[^>]+>", " ", abs_m2.group(1))).strip()
            abstract2 = re.sub(r"\s+", " ", abstract2)
            abstracts[fname2] = abstract2
    return abstracts
    DEAD_card_re  = re.compile(
        r'href="/papers/pdf/([^"?]+\.pdf)[^"]*".*?'
        r'class="paper-abstract"[^>]*><strong>Abstract:</strong>\s*(.*?)</p>',
        re.DOTALL,
    )
    for m in card_re.finditer(raw):
        fname    = m.group(1)
        abstract = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        abstract = re.sub(r"\s+", " ", abstract)
        abstracts[fname] = abstract

    return abstracts


# ---------------------------------------------------------------------------
# pdftotext extractor
# ---------------------------------------------------------------------------
def _extract_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout


# ---------------------------------------------------------------------------
# PDF text parser → (title, subtitle, sections)
# ---------------------------------------------------------------------------
_NOISE = re.compile(
    r"^\s*(\|> LATERALUS.*|Page\s+\d+.*lateralus\.dev.*|\d+\s*\*\s*.*lateralus\.dev.*"
    r"|lateralus\.dev\s*\*.*|bad-antics\s*\*.*|Lateralus Language(\s*--|$).*|RESEARCH PAPERS.*"
    r"|TECHNICAL DOCUMENTATION.*|bad-antics\s+\*\s+April.*|ABSTRACT)\s*$",
    re.IGNORECASE,
)

_SEC_RE = re.compile(r"^\s*(\d+)[\.\s]\s*(.+)$")


def _is_noise(line: str) -> bool:
    return bool(_NOISE.match(line))


def _join_broken_lines(lines: list[str]) -> list[str]:
    """
    pdftotext with -layout sometimes splits a word across two lines:
        "...annotate"
        "d by the programmer"
    Join them back if the next line is very short (looks like a word fragment).
    """
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (out and line and len(line) <= 3 and not line[0].isupper()
                and out[-1] and not out[-1].endswith((".", ":", ";"," "))):
            out[-1] = out[-1] + line.strip()
        else:
            out.append(line)
        i += 1
    return out


def parse_pdf_text(raw: str) -> tuple[str, str, list[tuple[str, str]]]:
    """
    Returns (title, subtitle, [(sec_title, body), ...])
    """
    raw_lines = raw.splitlines()
    raw_lines = _join_broken_lines(raw_lines)

    # strip pdftotext form-feed chars
    lines = [ln.rstrip() for ln in raw_lines if "\x0c" not in ln]

    # Pull title (first non-empty, non-noise line) and subtitle (second)
    # Also scan for subtitles embedded in "|> LATERALUS  <subtitle>" layout lines
    title    = ""
    subtitle = ""
    title_idx = 0
    _LATERALUS_PREFIX = re.compile(r"^\s*\|>\s*LATERALUS\s{3,}", re.IGNORECASE)
    subtitle_candidate = ""   # subtitle extracted from combined header line
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue
        # Check for "|> LATERALUS   <trailing>" — extract trailing as subtitle candidate
        if _LATERALUS_PREFIX.match(stripped):
            trailing = _LATERALUS_PREFIX.sub("", stripped).strip()
            # Ignore common noise trailers
            if (trailing and not subtitle_candidate
                    and not re.match(r"lateralus\.dev|bad-antics", trailing, re.I)):
                subtitle_candidate = trailing
            continue
        if _is_noise(stripped):
            continue
        if not title:
            title = stripped
            title_idx = i
        elif not subtitle and stripped != title:
            subtitle = stripped
            break

    # If subtitle looks like a line-wrapped continuation of the title
    # (single word), merge and re-read the actual subtitle
    old_title_base = ""   # original first line of the split title
    old_frag       = ""   # the wrapped word (second line)
    if subtitle and len(subtitle.split()) == 1 and subtitle[0].isupper():
        old_title_base = title
        old_frag = subtitle   # the wrapped word
        title = (title + " " + subtitle).strip()
        subtitle = ""
        # find actual subtitle: next non-noise line after skipping title fragments
        for ln in lines[title_idx:]:
            stripped = ln.strip()
            if not stripped or _is_noise(stripped) or _LATERALUS_PREFIX.match(stripped):
                continue
            if stripped == title or stripped == old_frag or stripped == old_title_base:
                continue
            subtitle = stripped
            break

    # If the subtitle looks like abstract body content (long sentence) but we have
    # a subtitle_candidate extracted from the "|> LATERALUS  <subtitle>" header line, prefer it
    if (subtitle_candidate
            and subtitle
            and len(subtitle.split()) > 8
            and not _is_noise(subtitle_candidate)):
        subtitle = subtitle_candidate

    # Build a clean body (strip title, subtitle, noise, page headers)
    body_lines: list[str] = []
    seen_title_once = False
    _strip_set = {title, old_title_base, old_frag} - {""}
    for ln in lines[title_idx:]:
        s = ln.strip()
        if not s:
            body_lines.append("")
            continue
        if _is_noise(s):
            continue
        # skip all forms of the title (full, base fragment, wrapped word)
        if s in _strip_set:
            if not seen_title_once:
                seen_title_once = True
            continue
        if s == subtitle and seen_title_once:
            continue
        body_lines.append(s)

    # Remove runs of more than 2 blank lines
    cleaned: list[str] = []
    blank_run = 0
    for ln in body_lines:
        if ln == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(ln)

    body_text = "\n".join(cleaned).strip()

    # Split into sections on "N. Title" or "N.  Title" patterns
    # We match at the start of a line (after stripping leading digits/punct noise)
    sec_split = re.split(r"\n(?=\s*\d+[\.\s]\s+\S)", body_text)

    sections: list[tuple[str, str]] = []
    for chunk in sec_split:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Check if the FIRST line is a section header
        first_line = chunk.splitlines()[0].strip() if chunk.splitlines() else ""
        m = _SEC_RE.match(first_line)
        if m:
            sec_title = m.group(2).strip()
            # Skip redundant "Introduction to <PaperTitle>" first-sections
            # from the bad-batch generation, but only if there are more sections
            body = "\n".join(chunk.splitlines()[1:]).strip()
            sections.append((sec_title, body))
        else:
            # No section header — treat as a preamble section
            if sections:
                # append to previous section
                sections[-1] = (sections[-1][0], sections[-1][1] + "\n\n" + chunk)
            else:
                # It's abstract-like text at the start (old-style PDFs)
                # We'll handle separately below
                sections.append(("Introduction", chunk))

    return title, subtitle, sections


# ---------------------------------------------------------------------------
# Doc class  (exact replica of paper_bot.py — the reference style)
# ---------------------------------------------------------------------------
def _make_doc_class():
    try:
        from fpdf import FPDF, XPos, YPos
    except ImportError:
        sys.exit("ERROR: fpdf2 not installed.  Run:  pip install fpdf2")

    class Doc(FPDF):
        lm, rm = 18, 18

        def __init__(self, title, subtitle, meta, series="Lateralus Language"):
            super().__init__()
            self.doc_title    = _clean(title)
            self.doc_subtitle = _clean(subtitle)
            self.doc_meta     = _clean(meta)
            self.series       = series
            self.set_margins(self.lm, 15, self.rm)
            self.set_auto_page_break(True, margin=24)
            self._pc = False

        def header(self):
            if not self._pc:
                return
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*YELLOW)
            self.set_xy(self.lm, 8)
            self.cell(80, 5, "|> LATERALUS", align="L")
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GREY)
            self.set_xy(self.lm, 8)
            self.cell(self.w - self.lm - self.rm, 5, self.doc_meta, align="R")
            self.set_draw_color(*RULE)
            self.set_line_width(0.4)
            self.line(self.lm, 15, self.w - self.rm, 15)
            self.ln(4)

        def footer(self):
            if not self._pc:
                return
            self.set_y(-15)
            self.set_draw_color(*RULE)
            self.set_line_width(0.3)
            self.line(self.lm, self.get_y() - 1, self.w - self.rm, self.get_y() - 1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GREY)
            self.cell(
                0, 8,
                f"Page {self.page_no()}  *  {self.doc_title[:55]}  *  lateralus.dev",
                align="C",
            )

        def cover(self, abstract: str, kw: str = ""):
            from fpdf import XPos, YPos
            self.add_page()
            self.set_fill_color(*DARK)
            self.rect(0, 0, self.w, 56, "F")
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*YELLOW)
            self.set_xy(self.lm, 11)
            self.cell(0, 7, "|> LATERALUS", align="L")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*GREY)
            self.set_xy(self.lm, 11)
            self.cell(0, 7, "lateralus.dev  *  bad-antics  *  2026", align="R")
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*CYAN)
            self.set_xy(self.lm, 21)
            self.cell(0, 6, self.series, align="L")
            self.set_draw_color(*CYAN)
            self.set_line_width(0.9)
            self.line(self.lm, 32, self.lm + 70, 32)
            self.set_font("Helvetica", "B", 17)
            self.set_text_color(*WHITE)
            self.set_xy(self.lm, 36)
            self.cell(0, 10, self.doc_title, align="L")
            self.set_y(62)
            self.set_font("Helvetica", "I", 11)
            self.set_text_color(*CYAN)
            self.cell(
                0, 8, self.doc_subtitle, align="L",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
            self.ln(2)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*GREY)
            self.cell(
                0, 6,
                "bad-antics  *  2026  *  lateralus.dev/papers",
                align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
            self.ln(6)
            self.set_draw_color(*RULE)
            self.set_line_width(0.4)
            self.line(self.lm, self.get_y(), self.w - self.rm, self.get_y())
            self.ln(5)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*YELLOW)
            self.cell(0, 6, "ABSTRACT", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)
            bw = self.w - self.lm - self.rm
            self.set_font("Helvetica", "", 10)
            lines = self.multi_cell(bw, 5, _clean(abstract), dry_run=True, output="LINES")
            bh = len(lines) * 5 + 12
            bx, by = self.get_x(), self.get_y()
            self.set_fill_color(*PURPLE)
            self.set_draw_color(*RULE)
            self.set_line_width(0.6)
            self.rect(bx - 3, by - 3, bw + 6, bh, "FD")
            self.set_xy(bx + 4, by + 4)
            self.set_text_color(*WHITE)
            self.multi_cell(bw - 8, 5, _clean(abstract))
            self.ln(5)
            self.set_draw_color(*RULE)
            self.line(self.lm, self.get_y(), self.w - self.rm, self.get_y())
            self.ln(4)
            if kw:
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*CYAN)
                self.cell(26, 5, "KEYWORDS")
                self.set_font("Helvetica", "", 8)
                self.set_text_color(*GREY)
                self.cell(0, 5, _clean(kw), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(4)
                self.set_draw_color(*RULE)
                self.line(self.lm, self.get_y(), self.w - self.rm, self.get_y())
                self.ln(4)
            self._pc = True

        def h1(self, t):
            from fpdf import XPos, YPos
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*CYAN)
            self.ln(5)
            self.cell(0, 8, _clean(t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(*RULE)
            self.set_line_width(0.35)
            self.line(self.lm, self.get_y(), self.w - self.rm, self.get_y())
            self.ln(3)

        def h2(self, t):
            from fpdf import XPos, YPos
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*YELLOW)
            self.ln(3)
            self.cell(0, 6, _clean(t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

        def p(self, t):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(*DARK)
            self.multi_cell(self.w - self.lm - self.rm, 5.2, _clean(t))
            self.ln(2)

        def code(self, src: str, label: str = ""):
            from fpdf import XPos, YPos
            if label:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(*GREY)
                self.cell(0, 5, _clean(label), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_font("Courier", "", 8.5)
            self.set_text_color(*GREEN)
            w = self.w - self.lm - self.rm
            lines = self.multi_cell(w - 8, 4.5, _clean(src), dry_run=True, output="LINES")
            bh = len(lines) * 4.5 + 9
            bx, by = self.get_x(), self.get_y()
            self.set_fill_color(*PURPLE)
            self.set_draw_color(*RULE)
            self.set_line_width(0.4)
            self.rect(bx - 2, by - 2, w + 4, bh, "FD")
            self.set_xy(bx + 3, by + 3)
            self.multi_cell(w - 4, 4.5, _clean(src))
            self.ln(4)

        def note(self, t: str):
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*YELLOW)
            w = self.w - self.lm - self.rm
            lines = self.multi_cell(
                w - 8, 4.8, _clean("NOTE: " + t), dry_run=True, output="LINES"
            )
            bh = len(lines) * 4.8 + 8
            bx, by = self.get_x(), self.get_y()
            self.set_fill_color(30, 18, 0)
            self.set_draw_color(140, 100, 0)
            self.set_line_width(0.4)
            self.rect(bx - 2, by - 2, w + 4, bh, "FD")
            self.set_xy(bx + 3, by + 3)
            self.multi_cell(w - 4, 4.8, _clean("NOTE: " + t))
            self.ln(3)

    return Doc


# ---------------------------------------------------------------------------
# Section body renderer
# ---------------------------------------------------------------------------
def _render_section(doc, sec_num: str, sec_title: str, body: str) -> None:
    CODE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
    NOTE_RE = re.compile(r"^NOTE:\s*(.+)", re.IGNORECASE)
    H2_RE   = re.compile(r"^##\s*(.+)")

    doc.h1(f"{sec_num}  {sec_title}")

    segments: list[tuple[str, str]] = []
    last = 0
    for m in CODE_RE.finditer(body):
        if m.start() > last:
            segments.append(("text", body[last:m.start()]))
        segments.append(("code", m.group(1).rstrip()))
        last = m.end()
    if last < len(body):
        segments.append(("text", body[last:]))

    for seg_type, content in segments:
        if seg_type == "code":
            doc.code(content)
            continue

        prose_buf: list[str] = []

        def flush():
            t = " ".join(prose_buf).strip()
            if t:
                doc.p(t)
            prose_buf.clear()

        for line in content.splitlines():
            s = line.strip()
            if not s:
                flush()
                continue
            if NOTE_RE.match(s):
                flush()
                doc.note(NOTE_RE.match(s).group(1))
            elif H2_RE.match(s):
                flush()
                doc.h2(H2_RE.match(s).group(1))
            else:
                prose_buf.append(s)
        flush()


# ---------------------------------------------------------------------------
# Build one PDF
# ---------------------------------------------------------------------------
def rebuild_one(
    pdf_path:  Path,
    abstracts: dict[str, str],
    dry_run:   bool = False,
) -> None:
    name = pdf_path.name
    print(f"\n  [{name}]")

    # Always parse from the current pdf/ file
    source_path = pdf_path

    raw_text = _extract_text(source_path)
    if not raw_text.strip():
        print("    SKIP: pdftotext returned empty output")
        return

    # Skip placeholder PDFs ("Full PDF Coming Soon")
    if "Full PDF Coming Soon" in raw_text or "coming soon" in raw_text.lower()[:500]:
        print("    SKIP: placeholder PDF")
        return

    title, subtitle, sections = parse_pdf_text(raw_text)

    if not title:
        print("    SKIP: could not parse title")
        return

    abstract = abstracts.get(name, "")
    if not abstract:
        # Try to pull from old-style PDFs where the first "Introduction" section
        # body looks like an abstract paragraph (short, no section markers)
        if sections and sections[0][0].lower() in ("introduction", "abstract"):
            first_body = sections[0][1]
            if (len(first_body.split()) < 200
                    and "lateralus" not in first_body[:30].lower()
                    and "|>" not in first_body[:30]):
                abstract = first_body
                sections = sections[1:]  # remove it from body sections

    if not abstract and sections:
        # Use first paragraph of first real section (up to ~60 words)
        first_real = next(
            (s[1] for s in sections
             if s[1].strip()
             and "|>" not in s[1][:20]
             and "lateralus" not in s[1][:20].lower()),
            ""
        )
        if first_real:
            words = first_real.split()
            abstract = " ".join(words[:60]) + ("..." if len(words) > 60 else "")

    if not abstract:
        abstract = f"Technical paper: {title}."

    print(f"    title    : {title}")
    print(f"    subtitle : {subtitle}")
    print(f"    sections : {len(sections)}")
    print(f"    abstract : {abstract[:80]}...")

    if dry_run:
        for i, (st, sb) in enumerate(sections):
            print(f"      {i+1:02d}. {st}  ({len(sb.split())} words)")
        return

    Doc = _make_doc_class()
    meta = "bad-antics  *  2026  *  lateralus.dev"
    d = Doc(
        title    = title,
        subtitle = subtitle,
        meta     = meta,
        series   = "Lateralus Language",
    )
    d.cover(abstract)

    for idx, (sec_title, body) in enumerate(sections):
        d.add_page()
        _render_section(d, f"{idx + 1}.", sec_title, body)

    d.output(str(pdf_path))
    sz = pdf_path.stat().st_size
    print(f"    -> saved  ({d.page_no()} pages, {sz // 1024} KB)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Rebuild all PDFs to match reference style")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no PDF output")
    parser.add_argument("--pdf",     metavar="NAME",       help="Rebuild one PDF by filename")
    args = parser.parse_args()

    # verify pdftotext is available
    r = subprocess.run(["which", "pdftotext"], capture_output=True)
    if r.returncode != 0:
        sys.exit("ERROR: pdftotext not found. Install:  sudo apt-get install poppler-utils")

    abstracts = _load_abstracts()
    print(f"  Loaded {len(abstracts)} abstracts from index.html")

    if args.pdf:
        target = PDF_DIR / args.pdf
        if not target.exists():
            sys.exit(f"ERROR: {target} not found")
        pdfs = [target]
    else:
        pdfs = sorted(PDF_DIR.glob("*.pdf"))

    print(f"  Rebuilding {len(pdfs)} PDF(s)...")

    ok = err = 0
    for pdf in pdfs:
        try:
            rebuild_one(pdf, abstracts, dry_run=args.dry_run)
            ok += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()
            err += 1

    print(f"\n  Done: {ok} rebuilt, {err} errors")


if __name__ == "__main__":
    main()
