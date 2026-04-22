#!/usr/bin/env python3
"""
paper_bot.py -- Autonomous section-by-section paper writer.

Strategy to avoid token/word limits
-------------------------------------
Each call to the Anthropic API generates EXACTLY ONE section (~350-500 words).
Completed sections are cached immediately to  cache/<slug>/<section_idx>.txt
so the run can be safely interrupted and resumed.  A final assembly pass builds
the full PDF using the same Doc class used by build_all_pdfs.py.

Usage
-----
  # Write a paper from an outline file (calls the API):
  python scripts/paper_bot.py outlines/my_paper.yaml

  # Preview sections without calling the API (inspect prompts):
  python scripts/paper_bot.py outlines/my_paper.yaml --dry-run

  # Regenerate a specific section (discard its cache entry):
  python scripts/paper_bot.py outlines/my_paper.yaml --regen 3

  # Only rebuild the PDF from whatever is cached (no new API calls):
  python scripts/paper_bot.py outlines/my_paper.yaml --pdf-only

  # Print the full assembled text without building a PDF:
  python scripts/paper_bot.py outlines/my_paper.yaml --text-only

Environment
-----------
  ANTHROPIC_API_KEY   -- required unless --dry-run / --pdf-only / --text-only

Dependencies
------------
  pip install anthropic fpdf2 pyyaml
"""

import argparse
import json
import os
import re
import sys
import textwrap
import time
import unicodedata
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT  = Path(__file__).parent.parent
PDF_DIR    = REPO_ROOT / "docs" / "website" / "papers" / "pdf"
CACHE_ROOT = REPO_ROOT / "scripts" / "paper_bot_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Unicode → Latin-1 normaliser (same as build_all_pdfs.py)
# ---------------------------------------------------------------------------
_REPLACEMENTS = {
    "\u2014": "--", "\u2013": "-",
    "\u2019": "'",  "\u2018": "'",
    "\u201c": '"',  "\u201d": '"',
    "\u00b7": "*",  "\u25b8": ">",
    "\u00b0": " deg", "\u00d7": "x",
    "\u00ae": "(R)", "\u2122": "(TM)",
    "\u2192": "->", "\u2190": "<-",
    "\u21d2": "=>", "\u2026": "...",
}

def _clean(s: str) -> str:
    for k, v in _REPLACEMENTS.items():
        s = s.replace(k, v)
    return re.sub(r"[^\x00-\xff]", "-", s)


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


# ---------------------------------------------------------------------------
# Anthropic API wrapper (section-level calls only)
# ---------------------------------------------------------------------------
_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None:
        try:
            import anthropic  # noqa: PLC0415
        except ImportError:
            sys.exit("ERROR: 'anthropic' package not installed.  Run:  pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            sys.exit(
                "ERROR: ANTHROPIC_API_KEY environment variable not set.\n"
                "       Export your key or use --dry-run / --pdf-only."
            )
        _CLIENT = anthropic.Anthropic(api_key=api_key)
    return _CLIENT


def generate_section(
    paper_meta: dict,
    section: dict,
    section_index: int,
    total_sections: int,
    retries: int = 3,
) -> str:
    """
    Call the Anthropic API to generate ONE section.

    Keeps prompts tight so output is 350-500 words -- well within token limits.
    """
    client = _get_client()

    title      = paper_meta["title"]
    audience   = paper_meta.get("audience", "technical readers familiar with compilers and programming language design")
    style      = paper_meta.get("style",    "academic / technical, clear and direct, minimal jargon")
    lang_ctx   = paper_meta.get("language_context", "")

    sec_title  = section["title"]
    key_points = section.get("key_points", [])
    target_len = section.get("words", 400)
    sec_number = f"{section_index + 1}/{total_sections}"

    def _kp_str(kp) -> str:
        if isinstance(kp, dict):
            # YAML parsed "Key: value" as a dict -- flatten back to string
            return ": ".join(f"{k}: {v}" for k, v in kp.items())
        return str(kp)

    kp_block = ""
    if key_points:
        kp_block = "Key points to cover:\n" + "\n".join(f"  - {_kp_str(kp)}" for kp in key_points)

    system = textwrap.dedent(f"""\
        You are a technical writer producing a section of a research paper.

        Paper title : {title}
        Audience    : {audience}
        Style       : {style}
        {("Language/project context: " + lang_ctx) if lang_ctx else ""}

        Rules:
        - Write ONLY the body of the section.  Do NOT include the section heading.
        - Target length: {target_len} words (350-550 words maximum).
        - No bullet lists unless specifically requested.  Prefer flowing prose.
        - Avoid filler phrases such as "it is worth noting" or "in conclusion".
        - When citing code patterns, use short inline examples (3-8 lines) wrapped in
          triple backticks with the language identifier.
        - Do not start with "In this section" or refer to section numbers.
        - Finish with a natural sentence that does not announce the next section.
    """)

    user = textwrap.dedent(f"""\
        Section {sec_number} of the paper: "{sec_title}"

        {kp_block}

        Write the body text now.
    """)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.messages.create(
                model   = paper_meta.get("model", "claude-opus-4-5"),
                max_tokens = 900,
                messages   = [{"role": "user", "content": user}],
                system     = system,
            )
            return resp.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            wait = 2 ** attempt
            print(f"    API error (attempt {attempt}/{retries}): {exc}  -- retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"All {retries} API attempts failed: {last_err}")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def _cache_dir(paper_meta: dict) -> Path:
    slug = slugify(paper_meta["title"])
    d = CACHE_ROOT / slug
    d.mkdir(parents=True, exist_ok=True)
    # Write a copy of the meta so humans can inspect it later
    meta_path = d / "_meta.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps(paper_meta, indent=2, ensure_ascii=False))
    return d


def _section_cache_path(cache_dir: Path, idx: int, section: dict) -> Path:
    slug = slugify(section["title"])
    return cache_dir / f"{idx:02d}_{slug}.txt"


def _load_cached_section(path: Path) -> str | None:
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def _save_cached_section(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Abstract generator (single dedicated call)
# ---------------------------------------------------------------------------
def generate_abstract(paper_meta: dict, section_titles: list[str], retries: int = 3) -> str:
    client = _get_client()

    title    = paper_meta["title"]
    subtitle = paper_meta.get("subtitle", "")
    keywords = paper_meta.get("keywords", "")
    lang_ctx = paper_meta.get("language_context", "")

    sections_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(section_titles))

    system = textwrap.dedent(f"""\
        You are a technical writer.  Write a concise academic abstract (120-160 words).
        {("Language/project context: " + lang_ctx) if lang_ctx else ""}
        Rules:
        - One paragraph only.
        - Summarise the problem, approach, and key results.
        - Do not list section numbers or say "this paper is organised as follows".
        - Avoid first-person ("we present" is acceptable).
    """)

    user = textwrap.dedent(f"""\
        Paper title    : {title}
        {"Subtitle       : " + subtitle if subtitle else ""}
        {"Keywords       : " + keywords if keywords else ""}
        Sections covered:
        {sections_list}

        Write the abstract now.
    """)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.messages.create(
                model      = paper_meta.get("model", "claude-opus-4-5"),
                max_tokens = 400,
                messages   = [{"role": "user", "content": user}],
                system     = system,
            )
            return resp.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Abstract generation failed: {last_err}")


# ---------------------------------------------------------------------------
# PDF builder  (uses the Doc class from build_all_pdfs.py)
# ---------------------------------------------------------------------------
def _build_pdf(paper_meta: dict, assembled: dict[int, str], output_path: Path) -> None:
    """
    assembled: {section_index: body_text}

    Sections that contain a line starting with ``` are treated as code blocks.
    Everything else is prose (p) or a note if the line starts with "NOTE:".
    """
    try:
        from fpdf import FPDF, XPos, YPos  # noqa: PLC0415
    except ImportError:
        sys.exit("ERROR: fpdf2 not installed.  Run:  pip install fpdf2")

    # ----- colour palette (same as build_all_pdfs.py) -----
    YELLOW = (255, 214, 0)
    CYAN   = (77,  208, 225)
    WHITE  = (255, 255, 255)
    GREY   = (180, 180, 180)
    DARK   = (16,   0,  42)
    RULE   = (100,  80, 140)
    GREEN  = (180, 255, 180)
    PURPLE = (24,   8,  54)

    class Doc(FPDF):
        lm, rm = 18, 18

        def __init__(self, title, subtitle, meta, series="RESEARCH PAPERS"):
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

        def cover(self, abstract, kw=""):
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
            self.cell(0, 6, self.series + "  --  TECHNICAL DOCUMENTATION", align="L")
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
                "bad-antics  *  April 2026  *  lateralus.dev/papers",
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
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*CYAN)
            self.ln(5)
            self.cell(0, 8, _clean(t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(*RULE)
            self.set_line_width(0.35)
            self.line(self.lm, self.get_y(), self.w - self.rm, self.get_y())
            self.ln(3)

        def h2(self, t):
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*YELLOW)
            self.ln(3)
            self.cell(0, 6, _clean(t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

        def p(self, t):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(*WHITE)
            self.multi_cell(self.w - self.lm - self.rm, 5.2, _clean(t))
            self.ln(2)

        def code(self, src, label=""):
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

        def note(self, t):
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

    # ---- parse section body text into doc calls ----
    def _render_body(doc: Doc, body: str, section_number: str, section_title: str) -> None:
        """
        Parse the AI-generated body text and emit h1/h2/code/note/p calls.

        Fenced code blocks (```...```) become doc.code().
        Lines starting with "NOTE:" become doc.note().
        Lines starting with "##" become doc.h2().
        Everything else is doc.p() after merging consecutive prose lines.
        """
        doc.h1(f"{section_number}  {section_title}")

        CODE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
        NOTE_RE = re.compile(r"^NOTE:\s*(.+)", re.IGNORECASE)
        H2_RE   = re.compile(r"^##\s*(.+)")

        # Split into chunks: either a code block or plain text
        segments: list[tuple[str, str]] = []  # (type, content)
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

            # Process text line-by-line
            prose_buf: list[str] = []

            def flush_prose():
                text = " ".join(prose_buf).strip()
                if text:
                    doc.p(text)
                prose_buf.clear()

            for line in content.splitlines():
                stripped = line.strip()
                if not stripped:
                    flush_prose()
                    continue
                note_m = NOTE_RE.match(stripped)
                h2_m   = H2_RE.match(stripped)
                if note_m:
                    flush_prose()
                    doc.note(note_m.group(1))
                elif h2_m:
                    flush_prose()
                    doc.h2(h2_m.group(1))
                else:
                    prose_buf.append(stripped)

            flush_prose()

    # ---- assemble the document ----
    d = Doc(
        title    = paper_meta["title"],
        subtitle = paper_meta.get("subtitle", ""),
        meta     = paper_meta.get("meta", "bad-antics  *  April 2026  *  lateralus.dev"),
        series   = paper_meta.get("series", "RESEARCH PAPERS"),
    )

    abstract = assembled.get("abstract", paper_meta.get("abstract", ""))
    keywords = paper_meta.get("keywords", "")
    d.cover(abstract, kw=keywords)

    sections = paper_meta["sections"]
    for idx, section in enumerate(sections):
        body = assembled.get(idx, "")
        if not body:
            body = f"[Section {idx+1} content not yet generated]"
        sec_num = f"{idx + 1}."
        d.add_page()
        _render_body(d, body, sec_num, section["title"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    d.output(str(output_path))
    sz = output_path.stat().st_size
    print(f"  PDF saved: {output_path}  ({d.page_no()} pages, {sz // 1024} KB)")


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------
def run(
    outline_path: Path,
    dry_run:     bool = False,
    pdf_only:    bool = False,
    text_only:   bool = False,
    regen_idx:   int | None = None,
    slow_mode:   bool = False,
) -> None:

    with outline_path.open(encoding="utf-8") as f:
        paper = yaml.safe_load(f)

    title    = paper["title"]
    sections = paper["sections"]
    slug     = slugify(title)
    cache    = _cache_dir(paper)

    output_name = paper.get("output_filename", f"{slug}.pdf")
    output_path = PDF_DIR / output_name

    print(f"\n{'='*62}")
    print(f"  Paper Bot  --  {title}")
    print(f"  Sections  : {len(sections)}")
    print(f"  Cache dir : {cache}")
    print(f"  Output    : {output_path}")
    print(f"{'='*62}\n")

    assembled: dict = {}

    # ---- Abstract ----
    abstract_path = cache / "00_abstract.txt"
    if regen_idx == -1 and abstract_path.exists():
        abstract_path.unlink()

    cached_abstract = _load_cached_section(abstract_path)

    if cached_abstract:
        print("  [cache] abstract")
        assembled["abstract"] = cached_abstract
    elif dry_run or pdf_only:
        assembled["abstract"] = paper.get("abstract", "(Abstract will be generated by the API.)")
    else:
        print("  [gen]   abstract ... ", end="", flush=True)
        abstract = generate_abstract(paper, [s["title"] for s in sections])
        _save_cached_section(abstract_path, abstract)
        assembled["abstract"] = abstract
        print("done")

    # ---- Sections ----
    for idx, section in enumerate(sections):
        sec_path = _section_cache_path(cache, idx, section)

        if regen_idx == idx and sec_path.exists():
            sec_path.unlink()

        cached = _load_cached_section(sec_path)

        if cached:
            print(f"  [cache] {idx+1:02d}. {section['title']}")
            assembled[idx] = cached
        elif dry_run or pdf_only:
            print(f"  [skip]  {idx+1:02d}. {section['title']}")
            assembled[idx] = f"[DRY-RUN: {section['title']}]"
        else:
            print(f"  [gen]   {idx+1:02d}. {section['title']} ... ", end="", flush=True)
            body = generate_section(paper, section, idx, len(sections))
            _save_cached_section(sec_path, body)
            assembled[idx] = body
            print("done")
            sleep_s = 4.0 if slow_mode else 0.4
            time.sleep(sleep_s)   # gentle rate-limit buffer

    # ---- Output ----
    if text_only:
        print("\n" + "="*62)
        print(assembled.get("abstract", ""))
        for idx, section in enumerate(sections):
            print(f"\n{'='*62}")
            print(f"  {idx+1}. {section['title']}")
            print("="*62)
            print(assembled.get(idx, ""))
        return

    if dry_run:
        print("\n[dry-run] No PDF built and no API calls made.")
        print("  Sections that would be generated:")
        for idx, section in enumerate(sections):
            kp = section.get("key_points", [])
            print(f"  {idx+1:02d}. {section['title']}  ({section.get('words', 400)} words)")
            def _kp_s(k) -> str:
                return ": ".join(f"{a}: {b}" for a, b in k.items()) if isinstance(k, dict) else str(k)
            for kp_item in kp[:3]:
                print(f"       - {_kp_s(kp_item)}")
        return

    _build_pdf(paper, assembled, output_path)

    print("\nDone. To regenerate a section:")
    print(f"  python scripts/paper_bot.py {outline_path} --regen <N>")
    print("To rebuild the PDF without new API calls:")
    print(f"  python scripts/paper_bot.py {outline_path} --pdf-only")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="paper_bot",
        description="Section-by-section AI paper writer that avoids token limits.",
    )
    parser.add_argument("outline", help="Path to a YAML outline file")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be generated without calling the API",
    )
    parser.add_argument(
        "--pdf-only", action="store_true",
        help="Skip all API calls, build PDF from cached sections only",
    )
    parser.add_argument(
        "--text-only", action="store_true",
        help="Print assembled text to stdout, no PDF",
    )
    parser.add_argument(
        "--regen", type=int, metavar="N", default=None,
        help="Re-generate section N (1-based) by discarding its cache entry",
    )
    parser.add_argument(
        "--slow", action="store_true",
        help="Add 4s between API calls (use on laptop to save resources)",
    )
    args = parser.parse_args()

    outline_path = Path(args.outline)
    if not outline_path.exists():
        sys.exit(f"ERROR: Outline file not found: {outline_path}")

    regen = (args.regen - 1) if args.regen is not None else None  # convert to 0-based

    run(
        outline_path = outline_path,
        dry_run      = args.dry_run,
        pdf_only     = args.pdf_only,
        text_only    = args.text_only,
        regen_idx    = regen,
        slow_mode    = args.slow,
    )


if __name__ == "__main__":
    main()
