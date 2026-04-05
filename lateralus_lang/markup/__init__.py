"""
lateralus_lang/markup/__init__.py  -  LTLM (Lateralus Markup Language)
===========================================================================
A hybrid Markdown + semantic-block format with executable .ltl code blocks,
math support, admonitions, theorems, cross-references, and citations.

File extension: .ltlm

Structure
---------
  ---
  title: My Document
  author: LATERALUS
  version: 1.0
  ---

  # Heading

  Regular **Markdown** text with $inline math$.

  ```ltl
  let x = 42
  io.println("Hello from LATERALUS!")
  ```

  ::: note
  Important information here.
  :::

Exports
-------
  NodeKind          — enum of AST node types
  Node              — AST node with kind/text/attrs/children
  LTLMLParser       — parser class
  LTLMLRenderer     — HTML renderer class
  parse_ltlml(src)  → Node (document)
  render_ltlml(src) → str  (HTML)
  compile_ltlml_file(input, output) → str (path)
===========================================================================
"""
from __future__ import annotations

import re
import html as _html
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# AST — Node Kinds
# -----------------------------------------------------------------------------

class NodeKind(Enum):
    """All possible node types in an LTLM document AST."""
    DOCUMENT       = auto()
    FRONTMATTER    = auto()
    HEADING        = auto()
    PARAGRAPH      = auto()
    TEXT           = auto()
    BOLD           = auto()
    ITALIC         = auto()
    CODE_INLINE    = auto()
    CODE_BLOCK     = auto()
    MATH_INLINE    = auto()
    MATH_BLOCK     = auto()
    LINK           = auto()
    IMAGE          = auto()
    UNORDERED_LIST = auto()
    ORDERED_LIST   = auto()
    LIST_ITEM      = auto()
    BLOCKQUOTE     = auto()
    HR             = auto()
    TABLE          = auto()
    TABLE_ROW      = auto()
    ADMONITION     = auto()
    THEOREM        = auto()
    CROSSREF       = auto()
    CITATION       = auto()


# -----------------------------------------------------------------------------
# AST — Node
# -----------------------------------------------------------------------------

@dataclass
class Node:
    """Universal AST node for LTLM documents."""
    kind: NodeKind
    text: str = ""
    attrs: Dict[str, Any] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Inline Parser  (bold, italic, code, math, links, images, refs, cites)
# -----------------------------------------------------------------------------

# Ordered by specificity — longer / more specific patterns first.
_INLINE_PATTERNS: List[tuple] = [
    (re.compile(r'\*\*(.+?)\*\*'),                       NodeKind.BOLD),
    (re.compile(r'__(.+?)__'),                            NodeKind.BOLD),
    (re.compile(r'(?<!\w)_(.+?)_(?!\w)'),                 NodeKind.ITALIC),
    (re.compile(r'`(.+?)`'),                              NodeKind.CODE_INLINE),
    (re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)'),  NodeKind.MATH_INLINE),
    (re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),             NodeKind.IMAGE),
    (re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),              NodeKind.LINK),
    (re.compile(r'@ref\{([^}]+)\}'),                      NodeKind.CROSSREF),
    (re.compile(r'@cite\{([^}]+)\}'),                     NodeKind.CITATION),
]


def _parse_inline(text: str) -> List[Node]:
    """Parse inline formatting in *text* and return a flat list of child nodes."""
    nodes: List[Node] = []
    pos = 0

    while pos < len(text):
        best_match = None
        best_kind: Optional[NodeKind] = None
        best_start = len(text)

        for pattern, kind in _INLINE_PATTERNS:
            m = pattern.search(text, pos)
            if m and m.start() < best_start:
                best_match = m
                best_kind = kind
                best_start = m.start()

        if best_match is None:
            tail = text[pos:]
            if tail:
                nodes.append(Node(kind=NodeKind.TEXT, text=tail))
            break

        # Plain text before the match
        if best_start > pos:
            nodes.append(Node(kind=NodeKind.TEXT, text=text[pos:best_start]))

        # Build the appropriate node
        if best_kind == NodeKind.IMAGE:
            nodes.append(Node(
                kind=NodeKind.IMAGE,
                text=best_match.group(1),
                attrs={"alt": best_match.group(1), "src": best_match.group(2)},
            ))
        elif best_kind == NodeKind.LINK:
            nodes.append(Node(
                kind=NodeKind.LINK,
                text=best_match.group(1),
                attrs={"href": best_match.group(2)},
            ))
        elif best_kind == NodeKind.CROSSREF:
            nodes.append(Node(
                kind=NodeKind.CROSSREF,
                text=best_match.group(1),
                attrs={"label": best_match.group(1)},
            ))
        elif best_kind == NodeKind.CITATION:
            nodes.append(Node(
                kind=NodeKind.CITATION,
                text=best_match.group(1),
                attrs={"key": best_match.group(1)},
            ))
        else:
            nodes.append(Node(kind=best_kind, text=best_match.group(1)))

        pos = best_match.end()

    return nodes


# -----------------------------------------------------------------------------
# Block-level regex helpers
# -----------------------------------------------------------------------------

_RE_FM_FENCE      = re.compile(r'^---\s*$')
_RE_HEADING       = re.compile(r'^(#{1,6})\s+(.+)$')
_RE_CODE_FENCE    = re.compile(r'^```(\w*)\s*$')
_RE_MATH_FENCE    = re.compile(r'^\$\$\s*$')
_RE_HR            = re.compile(r'^(---+|\*\*\*+|___+)\s*$')
_RE_BLOCKQUOTE    = re.compile(r'^>\s?(.*)')
_RE_OL_ITEM       = re.compile(r'^\d+\.\s+(.+)')
_RE_UL_ITEM       = re.compile(r'^[-*+]\s+(.+)')
_RE_TABLE_ROW     = re.compile(r'^\|(.+)\|\s*$')
_RE_TABLE_SEP     = re.compile(r'^\|[-:| ]+\|\s*$')
_RE_ADM_START     = re.compile(r'^:::\s*(\w+)(?:\s+(.+))?\s*$')
_RE_ADM_END       = re.compile(r'^:::\s*$')
_RE_YAML_KV       = re.compile(r'^(\w[\w.-]*)\s*:\s*(.+)')

_THEOREM_TYPES = frozenset({
    "theorem", "lemma", "proof", "corollary",
    "definition", "proposition", "axiom",
})


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

class LTLMLParser:
    """Parse LTLM source text into a ``Node`` tree."""

    # ------------------------------------------------------------------
    @staticmethod
    def _preprocess_block_format(source: str) -> str:
        """Convert {block} curly-brace format to Markdown so the parser works.

        Handles: {document}, {h1}-{h6}, {p}, {code}, {math}, {toc},
                 {note}, {warning}, {tip}, {separator}, {list}, {blockquote},
                 {table}, {theorem}, {image}.
        """
        # Quick check: does this look like block format?
        if '{document' not in source and '{h1 ' not in source and '{p' not in source:
            return source  # Already Markdown

        lines = source.split('\n')
        out: List[str] = []
        i = 0
        n = len(lines)

        def _collect_block(start_idx: int) -> tuple:
            """Collect lines from a { block until matching }, returning (content, end_idx).
            Handles nested braces and single-line blocks like {h1 Title}."""
            first_line = lines[start_idx]

            # Single-line block: {h1 Title}
            if first_line.rstrip().endswith('}'):
                brace_depth = 0
                for ch in first_line:
                    if ch == '{':
                        brace_depth += 1
                    elif ch == '}':
                        brace_depth -= 1
                if brace_depth == 0:
                    # Find the content after the tag
                    inner = first_line.strip()
                    # Remove leading { and trailing }
                    inner = inner[1:-1].strip()
                    # Remove the tag name
                    parts = inner.split(None, 1)
                    content = parts[1] if len(parts) > 1 else ''
                    return content, start_idx + 1

            # Multi-line block
            depth = 0
            body_lines = []
            j = start_idx
            first = True
            while j < n:
                ln = lines[j]
                for ch in ln:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                if first:
                    first = False
                else:
                    if depth <= 0:
                        # Don't include the closing brace line
                        body_lines.append(ln.rstrip().rstrip('}').rstrip())
                        return '\n'.join(body_lines).strip(), j + 1
                    body_lines.append(ln)
                j += 1
            return '\n'.join(body_lines).strip(), j

        while i < n:
            line = lines[i].strip()

            # {document ...}
            if line.startswith('{document'):
                content, i = _collect_block(i)
                # Convert to --- frontmatter
                out.append('---')
                for fmline in content.split('\n'):
                    fmline = fmline.strip()
                    if fmline and ':' in fmline:
                        out.append(fmline)
                out.append('---')
                out.append('')
                continue

            # {h1 Title} through {h6 Title}
            hm = re.match(r'\{h([1-6])\s+', line)
            if hm:
                level = int(hm.group(1))
                content, i = _collect_block(i)
                out.append('#' * level + ' ' + content)
                out.append('')
                continue

            # {p ...}
            if line.startswith('{p'):
                content, i = _collect_block(i)
                out.append(content)
                out.append('')
                continue

            # {code lang="xxx" ...}
            if line.startswith('{code'):
                # Extract language attribute
                lang_match = re.search(r'lang(?:uage)?="(\w+)"', line)
                lang = lang_match.group(1) if lang_match else ''
                content, i = _collect_block(i)
                out.append(f'```{lang}')
                out.append(content)
                out.append('```')
                out.append('')
                continue

            # {math ...}
            if line.startswith('{math'):
                content, i = _collect_block(i)
                out.append('$$')
                out.append(content)
                out.append('$$')
                out.append('')
                continue

            # {toc} — generate table of contents marker
            if line.startswith('{toc'):
                i += 1
                out.append('')  # Will be handled by renderer
                continue

            # {separator}
            if line.startswith('{separator'):
                i += 1
                out.append('---')
                out.append('')
                continue

            # {note ...}, {warning ...}, {tip ...}, {important ...}, {danger ...}, {info ...}
            adm_match = re.match(r'\{(note|warning|tip|important|danger|info)', line)
            if adm_match:
                adm_type = adm_match.group(1)
                content, i = _collect_block(i)
                out.append(f'::: {adm_type}')
                out.append(content)
                out.append(':::')
                out.append('')
                continue

            # {theorem ...}, {lemma ...}, {proof ...}
            thm_match = re.match(r'\{(theorem|lemma|proof|corollary|definition|proposition|axiom)', line)
            if thm_match:
                thm_type = thm_match.group(1)
                content, i = _collect_block(i)
                out.append(f'::: {thm_type}')
                out.append(content)
                out.append(':::')
                out.append('')
                continue

            # {list ...}
            if line.startswith('{list'):
                content, i = _collect_block(i)
                for item_line in content.split('\n'):
                    item_line = item_line.strip()
                    if item_line.startswith('{item'):
                        # Extract item text
                        im = re.match(r'\{item\s*(.*?)(?:\}|$)', item_line)
                        if im:
                            text = im.group(1).rstrip('}').strip()
                            out.append(f'- {text}')
                    elif item_line and not item_line.startswith('}'):
                        out.append(f'- {item_line}')
                out.append('')
                continue

            # {blockquote ...}
            if line.startswith('{blockquote') or line.startswith('{quote'):
                content, i = _collect_block(i)
                for bq_line in content.split('\n'):
                    out.append(f'> {bq_line}')
                out.append('')
                continue

            # {table ...}
            if line.startswith('{table'):
                content, i = _collect_block(i)
                # Pass through — table parsing is complex, just include as text
                out.append(content)
                out.append('')
                continue

            # {image src="..." alt="..."}
            if line.startswith('{image'):
                src_m = re.search(r'src="([^"]+)"', line)
                alt_m = re.search(r'alt="([^"]*)"', line)
                src = src_m.group(1) if src_m else ''
                alt = alt_m.group(1) if alt_m else ''
                i += 1
                out.append(f'![{alt}]({src})')
                out.append('')
                continue

            # Skip empty lines or closing braces
            if line == '}' or line == '':
                i += 1
                continue

            # Pass through any other content
            out.append(lines[i])
            i += 1

        return '\n'.join(out)

    # ------------------------------------------------------------------
    def parse(self, source: str) -> Node:
        source = self._preprocess_block_format(source)
        lines = source.split('\n')
        doc = Node(kind=NodeKind.DOCUMENT)
        n = len(lines)
        i = 0

        # -- front-matter (--- fences, YAML-style key: value) ---------
        if i < n and _RE_FM_FENCE.match(lines[i]):
            i += 1
            attrs: Dict[str, str] = {}
            while i < n and not _RE_FM_FENCE.match(lines[i]):
                m = _RE_YAML_KV.match(lines[i].strip())
                if m:
                    val = m.group(2).strip()
                    if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                        val = val[1:-1]
                    attrs[m.group(1)] = val
                i += 1
            if i < n:
                i += 1                       # skip closing ---
            doc.children.append(Node(kind=NodeKind.FRONTMATTER, attrs=attrs))

        # -- body blocks ----------------------------------------------
        text_buf: List[str] = []

        def flush_text():
            nonlocal text_buf
            content = '\n'.join(text_buf).strip()
            if content:
                for para in re.split(r'\n\s*\n', content):
                    para = para.strip()
                    if para:
                        p = Node(kind=NodeKind.PARAGRAPH, text=para,
                                 children=_parse_inline(para))
                        doc.children.append(p)
            text_buf = []

        while i < n:
            line = lines[i]

            # -- fenced code block ```lang … ``` ----------------------
            m = _RE_CODE_FENCE.match(line)
            if m:
                flush_text()
                lang = m.group(1)
                code_lines: List[str] = []
                i += 1
                while i < n and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < n:
                    i += 1
                doc.children.append(Node(
                    kind=NodeKind.CODE_BLOCK,
                    text='\n'.join(code_lines),
                    attrs={"language": lang},
                ))
                continue

            # -- math block $$ … $$ -----------------------------------
            if _RE_MATH_FENCE.match(line):
                flush_text()
                math_lines: List[str] = []
                i += 1
                while i < n and not _RE_MATH_FENCE.match(lines[i]):
                    math_lines.append(lines[i])
                    i += 1
                if i < n:
                    i += 1
                doc.children.append(Node(
                    kind=NodeKind.MATH_BLOCK,
                    text='\n'.join(math_lines),
                ))
                continue

            # -- admonition / theorem  ::: type [title] … ::: --------
            m = _RE_ADM_START.match(line)
            if m:
                flush_text()
                adm_type = m.group(1)
                adm_title = (m.group(2) or "").strip()
                body_lines: List[str] = []
                i += 1
                while i < n and not _RE_ADM_END.match(lines[i]):
                    body_lines.append(lines[i])
                    i += 1
                if i < n:
                    i += 1
                kind = NodeKind.THEOREM if adm_type in _THEOREM_TYPES else NodeKind.ADMONITION
                a: Dict[str, str] = {"type": adm_type}
                if adm_title:
                    a["title"] = adm_title
                doc.children.append(Node(kind=kind, text='\n'.join(body_lines), attrs=a))
                continue

            # -- heading  # … ###### ---------------------------------
            m = _RE_HEADING.match(line)
            if m:
                flush_text()
                level = len(m.group(1))
                h_text = m.group(2).strip()
                doc.children.append(Node(
                    kind=NodeKind.HEADING,
                    attrs={"level": level},
                    children=_parse_inline(h_text),
                ))
                i += 1
                continue

            # -- horizontal rule  ---  ***  ___ ----------------------
            if _RE_HR.match(line):
                flush_text()
                doc.children.append(Node(kind=NodeKind.HR))
                i += 1
                continue

            # -- table  | … | ----------------------------------------
            if _RE_TABLE_ROW.match(line):
                flush_text()
                headers = [c.strip() for c in line.strip().strip('|').split('|')]
                i += 1
                if i < n and _RE_TABLE_SEP.match(lines[i]):
                    i += 1
                rows: List[List[str]] = []
                while i < n and _RE_TABLE_ROW.match(lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                    i += 1
                table = Node(kind=NodeKind.TABLE)
                # header row
                hrow = Node(kind=NodeKind.TABLE_ROW)
                for h in headers:
                    hrow.children.append(Node(kind=NodeKind.TEXT, text=h))
                table.children.append(hrow)
                # data rows
                for row in rows:
                    rnode = Node(kind=NodeKind.TABLE_ROW)
                    for cell in row:
                        rnode.children.append(Node(kind=NodeKind.TEXT, text=cell))
                    table.children.append(rnode)
                doc.children.append(table)
                continue

            # -- blockquote  > … -------------------------------------
            m = _RE_BLOCKQUOTE.match(line)
            if m:
                flush_text()
                bq_lines = [m.group(1)]
                i += 1
                while i < n:
                    m2 = _RE_BLOCKQUOTE.match(lines[i])
                    if m2:
                        bq_lines.append(m2.group(1))
                        i += 1
                    else:
                        break
                bq_text = '\n'.join(bq_lines)
                doc.children.append(Node(
                    kind=NodeKind.BLOCKQUOTE,
                    text=bq_text,
                    children=_parse_inline(bq_text),
                ))
                continue

            # -- ordered list  1. … ----------------------------------
            m = _RE_OL_ITEM.match(line)
            if m:
                flush_text()
                ol = Node(kind=NodeKind.ORDERED_LIST)
                ol.children.append(Node(kind=NodeKind.LIST_ITEM, text=m.group(1)))
                i += 1
                while i < n:
                    m2 = _RE_OL_ITEM.match(lines[i])
                    if m2:
                        ol.children.append(Node(kind=NodeKind.LIST_ITEM, text=m2.group(1)))
                        i += 1
                    else:
                        break
                doc.children.append(ol)
                continue

            # -- unordered list  - / * / + … -------------------------
            m = _RE_UL_ITEM.match(line)
            if m:
                flush_text()
                ul = Node(kind=NodeKind.UNORDERED_LIST)
                ul.children.append(Node(kind=NodeKind.LIST_ITEM, text=m.group(1)))
                i += 1
                while i < n:
                    m2 = _RE_UL_ITEM.match(lines[i])
                    if m2:
                        ul.children.append(Node(kind=NodeKind.LIST_ITEM, text=m2.group(1)))
                        i += 1
                    else:
                        break
                doc.children.append(ul)
                continue

            # -- regular text (accumulate) ----------------------------
            text_buf.append(line)
            i += 1

        flush_text()
        return doc


# -----------------------------------------------------------------------------
# Inline Markdown → HTML  (used by the renderer)
# -----------------------------------------------------------------------------

def _inline_to_html(text: str) -> str:
    """Convert inline Markdown/LTLM formatting to HTML."""
    t = _html.escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'__(.+?)__', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    t = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)',
               r'<span class="math-inline">$$\1$$</span>', t)
    t = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    # Rewrite .ltlml links → .html so pages resolve in browsers
    t = re.sub(r'href="([^"]*)\.ltlml"', r'href="\1.html"', t)
    t = re.sub(r'@ref\{([^}]+)\}', r'<a class="crossref" href="#\1">\1</a>', t)
    t = re.sub(r'@cite\{([^}]+)\}', r'<cite>[\1]</cite>', t)
    return t


# -----------------------------------------------------------------------------
# HTML Renderer
# -----------------------------------------------------------------------------

_LTLML_CSS = """\
<style>
:root {
  --ltl-bg: #0d1117; --ltl-fg: #c9d1d9; --ltl-accent: #58a6ff;
  --ltl-code-bg: #161b22; --ltl-border: #30363d;
  --ltl-heading: #f0f6fc; --ltl-link: #58a6ff;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body.ltl-bg {
  background: var(--ltl-bg); color: var(--ltl-fg);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; line-height: 1.7;
}
.ltlml-document { max-width: 900px; margin: 0 auto; }
h1,h2,h3,h4,h5,h6 {
  color: var(--ltl-heading); margin: 1.5em 0 .5em;
  border-bottom: 1px solid var(--ltl-border); padding-bottom: .3em;
}
h1 { font-size: 2em; } h2 { font-size: 1.5em; } h3 { font-size: 1.25em; }
p { margin: .8em 0; }
code {
  background: var(--ltl-code-bg); padding: .15em .4em;
  border-radius: 4px; font-size: .9em;
}
pre {
  background: var(--ltl-code-bg); border: 1px solid var(--ltl-border);
  border-radius: 8px; padding: 1em; overflow-x: auto; margin: 1em 0;
}
pre code { background: none; padding: 0; }
a { color: var(--ltl-link); text-decoration: none; }
a:hover { text-decoration: underline; }
blockquote {
  border-left: 4px solid var(--ltl-accent); padding: .5em 1em; margin: 1em 0;
  background: var(--ltl-code-bg); border-radius: 0 6px 6px 0;
}
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid var(--ltl-border); padding: .5em .8em; text-align: left; }
th { background: var(--ltl-code-bg); font-weight: 600; }
ul, ol { margin: .5em 0; padding-left: 2em; }
li { margin: .25em 0; }
hr { border: none; border-top: 1px solid var(--ltl-border); margin: 2em 0; }
.admonition {
  border-left: 4px solid var(--ltl-accent); background: var(--ltl-code-bg);
  padding: 1em; margin: 1em 0; border-radius: 0 6px 6px 0;
}
.admonition.warning { border-color: #d29922; }
.admonition.note    { border-color: #58a6ff; }
.admonition.info    { border-color: #3fb950; }
.admonition-title {
  font-weight: 600; text-transform: capitalize; margin-bottom: .5em;
}
.theorem {
  border: 1px solid var(--ltl-border); background: var(--ltl-code-bg);
  padding: 1em; margin: 1em 0; border-radius: 6px;
}
.theorem-title { font-weight: 700; font-style: italic; margin-bottom: .5em; }
.math-block { text-align: center; margin: 1.5em 0; padding: 1em; }
.ltl-badge {
  display: inline-block;
  background: linear-gradient(135deg, #238636, #1f6feb);
  color: #fff; padding: .15em .6em; border-radius: 12px;
  font-size: .75em; font-weight: 600; vertical-align: middle; margin-left: .5em;
}
.meta { color: #8b949e; font-size: .85em; margin-bottom: 2em; }
</style>
"""


class LTLMLRenderer:
    """Render an LTLM ``Node`` tree to HTML."""

    # ------------------------------------------------------------------
    def render(self, doc: Node) -> str:
        parts: List[str] = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="utf-8">',
        ]

        title = "LTLM Document"
        author = ""
        for child in doc.children:
            if child.kind == NodeKind.FRONTMATTER:
                title = child.attrs.get("title", title)
                author = child.attrs.get("author", "")
                break

        parts.append(f'<title>{_html.escape(title)}</title>')

        # KaTeX (included when any math is present)
        if self._has_math(doc):
            parts.append(
                '<link rel="stylesheet" '
                'href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">'
            )
            parts.append(
                '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js">'
                '</script>'
            )
            parts.append(
                '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/'
                'contrib/auto-render.min.js"></script>'
            )

        parts.append(_LTLML_CSS)
        parts.append('</head>')
        parts.append('<body class="ltl-bg">')
        parts.append('<div class="ltlml-document">')

        # Front-matter header
        if title != "LTLM Document" or author:
            parts.append(
                f'<h1>{_html.escape(title)}'
                f'<span class="ltl-badge">LTLM</span></h1>'
            )
            if author:
                parts.append(f'<p class="meta">Author: {_html.escape(author)}</p>')

        for child in doc.children:
            if child.kind == NodeKind.FRONTMATTER:
                continue
            parts.append(self._render_block(child))

        parts.append('</div>')

        if self._has_math(doc):
            parts.append(
                '<script>document.addEventListener("DOMContentLoaded",'
                'function(){renderMathInElement(document.body);});</script>'
            )

        parts.append('</body>')
        parts.append('</html>')
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    def _has_math(self, node: Node) -> bool:
        if node.kind in (NodeKind.MATH_BLOCK, NodeKind.MATH_INLINE):
            return True
        if '$' in node.text:
            return True
        return any(self._has_math(c) for c in node.children)

    # ------------------------------------------------------------------
    def _render_block(self, node: Node) -> str:
        kind = node.kind

        if kind == NodeKind.HEADING:
            level = node.attrs.get("level", 1)
            inner = node.children[0].text if node.children else ""
            return f'<h{level}>{_inline_to_html(inner)}</h{level}>'

        if kind == NodeKind.PARAGRAPH:
            return f'<p>{_inline_to_html(node.text)}</p>'

        if kind == NodeKind.CODE_BLOCK:
            lang = node.attrs.get("language", "")
            cls = f' class="language-{_html.escape(lang)}"' if lang else ''
            return f'<pre><code{cls}>{_html.escape(node.text)}</code></pre>'

        if kind == NodeKind.MATH_BLOCK:
            return f'<div class="math-block">$$\n{_html.escape(node.text)}\n$$</div>'

        if kind in (NodeKind.UNORDERED_LIST, NodeKind.ORDERED_LIST):
            tag = 'ol' if kind == NodeKind.ORDERED_LIST else 'ul'
            items = ''.join(
                f'<li>{_inline_to_html(c.text)}</li>' for c in node.children
            )
            return f'<{tag}>{items}</{tag}>'

        if kind == NodeKind.BLOCKQUOTE:
            return f'<blockquote><p>{_inline_to_html(node.text)}</p></blockquote>'

        if kind == NodeKind.TABLE:
            rows_html: List[str] = []
            for idx, row in enumerate(node.children):
                if idx == 0:
                    cells = ''.join(
                        f'<th>{_inline_to_html(c.text)}</th>' for c in row.children
                    )
                    rows_html.append(f'<thead><tr>{cells}</tr></thead>')
                else:
                    cells = ''.join(
                        f'<td>{_inline_to_html(c.text)}</td>' for c in row.children
                    )
                    rows_html.append(f'<tr>{cells}</tr>')
            thead = rows_html[0] if rows_html else ''
            tbody = ('<tbody>' + ''.join(rows_html[1:]) + '</tbody>'
                     if len(rows_html) > 1 else '')
            return f'<table>{thead}{tbody}</table>'

        if kind == NodeKind.HR:
            return '<hr>'

        if kind == NodeKind.ADMONITION:
            atype = _html.escape(node.attrs.get("type", "note"))
            atitle = node.attrs.get("title", atype)
            return (
                f'<div class="admonition {atype}">'
                f'<div class="admonition-title">{_html.escape(atitle)}</div>'
                f'<p>{_inline_to_html(node.text)}</p>'
                f'</div>'
            )

        if kind == NodeKind.THEOREM:
            ttype = node.attrs.get("type", "theorem")
            ttitle = node.attrs.get("title", "")
            display = ttype.capitalize()
            if ttitle:
                display += f' ({_html.escape(ttitle)})'
            return (
                f'<div class="theorem {_html.escape(ttype)}">'
                f'<div class="theorem-title">{display}</div>'
                f'<p>{_inline_to_html(node.text)}</p>'
                f'</div>'
            )

        return ''


# -----------------------------------------------------------------------------
# ANSI Terminal Renderer  (for `ltlc doc` without --html)
# -----------------------------------------------------------------------------

_RST  = '\033[0m'
_BOLD = '\033[1m'
_DIM  = '\033[2m'
_ITAL = '\033[3m'
_UL   = '\033[4m'
_BLUE = '\033[34m'
_CYAN = '\033[36m'
_GRN  = '\033[32m'
_YEL  = '\033[33m'
_MAG  = '\033[35m'
_BGCD = '\033[48;5;236m'


def _inline_to_ansi(text: str) -> str:
    t = re.sub(r'\*\*(.+?)\*\*', rf'{_BOLD}\1{_RST}', text)
    t = re.sub(r'__(.+?)__',     rf'{_BOLD}\1{_RST}', t)
    t = re.sub(r'(?<!\w)_(.+?)_(?!\w)', rf'{_ITAL}\1{_RST}', t)
    t = re.sub(r'`(.+?)`',       rf'{_CYAN}\1{_RST}', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', rf'{_UL}{_BLUE}\1{_RST} (\2)', t)
    return t


def _to_ansi(doc: Node) -> str:
    """Render *doc* to ANSI-coloured terminal output."""
    parts: List[str] = []

    for child in doc.children:
        if child.kind == NodeKind.FRONTMATTER:
            title = child.attrs.get("title", "")
            author = child.attrs.get("author", "")
            if title:
                parts.append(f'\n{_BOLD}{_CYAN}  {title}{_RST}')
            meta = []
            if author:
                meta.append(author)
            version = child.attrs.get("version", "")
            if version:
                meta.append(f'v{version}')
            if meta:
                parts.append(f'{_DIM}  {" · ".join(meta)}{_RST}')
            parts.append(f'{_DIM}  {"-" * 60}{_RST}\n')

        elif child.kind == NodeKind.HEADING:
            level = child.attrs.get("level", 1)
            text = child.children[0].text if child.children else ""
            prefix = '=' * level
            parts.append(f'\n{_BOLD}{_YEL}  {prefix} {_inline_to_ansi(text)}{_RST}\n')

        elif child.kind == NodeKind.PARAGRAPH:
            parts.append(f'  {_inline_to_ansi(child.text)}\n')

        elif child.kind == NodeKind.CODE_BLOCK:
            lang = child.attrs.get("language", "")
            tag = f'{_DIM}[{lang}]{_RST}' if lang else ''
            parts.append(f'\n  {_BGCD}{_GRN}  +{"-" * 56}+{_RST} {tag}')
            for ln in child.text.split('\n'):
                parts.append(f'  {_BGCD}{_GRN}  | {ln:<54} |{_RST}')
            parts.append(f'  {_BGCD}{_GRN}  +{"-" * 56}+{_RST}\n')

        elif child.kind == NodeKind.MATH_BLOCK:
            parts.append(f'\n  {_MAG}$$  {child.text}  $${_RST}\n')

        elif child.kind in (NodeKind.UNORDERED_LIST, NodeKind.ORDERED_LIST):
            for idx, item in enumerate(child.children):
                marker = f'{idx + 1}.' if child.kind == NodeKind.ORDERED_LIST else '•'
                parts.append(f'  {_DIM}{marker}{_RST} {_inline_to_ansi(item.text)}')
            parts.append('')

        elif child.kind == NodeKind.BLOCKQUOTE:
            for ln in child.text.split('\n'):
                parts.append(f'  {_DIM}|{_RST} {_ITAL}{_inline_to_ansi(ln)}{_RST}')
            parts.append('')

        elif child.kind == NodeKind.TABLE:
            widths: List[int] = []
            for row in child.children:
                for j, cell in enumerate(row.children):
                    while len(widths) <= j:
                        widths.append(0)
                    widths[j] = max(widths[j], len(cell.text))
            for idx, row in enumerate(child.children):
                cells = ' | '.join(
                    (row.children[j].text if j < len(row.children) else '').ljust(widths[j])
                    for j in range(len(widths))
                )
                if idx == 0:
                    parts.append(f'  {_BOLD}{cells}{_RST}')
                    parts.append(f'  {_DIM}{"-+-".join("-" * w for w in widths)}{_RST}')
                else:
                    parts.append(f'  {cells}')
            parts.append('')

        elif child.kind == NodeKind.HR:
            parts.append(f'  {_DIM}{"-" * 60}{_RST}\n')

        elif child.kind in (NodeKind.ADMONITION, NodeKind.THEOREM):
            atype = child.attrs.get("type", "note")
            atitle = child.attrs.get("title", "")
            label = atype.upper()
            if atitle:
                label += f': {atitle}'
            parts.append(f'  {_BOLD}{_YEL}[{label}]{_RST}')
            parts.append(f'  {_inline_to_ansi(child.text)}')
            parts.append('')

    return '\n'.join(parts)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

_default_parser   = LTLMLParser()
_default_renderer = LTLMLRenderer()


def parse_ltlml(source: str) -> Node:
    """Parse LTLM source into a document AST (``Node`` tree)."""
    return _default_parser.parse(source)


def render_ltlml(source: str) -> str:
    """Parse LTLM source and render it to a standalone HTML page."""
    doc = _default_parser.parse(source)
    return _default_renderer.render(doc)


def compile_ltlml_file(input_path: str, output_path: str) -> str:
    """Read an ``.ltlm`` file, render to HTML, write to *output_path*.

    Returns the resolved output path as a string.
    """
    source = Path(input_path).read_text(encoding='utf-8')
    html = render_ltlml(source)
    out = Path(output_path)
    out.write_text(html, encoding='utf-8')
    return str(out)


# -----------------------------------------------------------------------------
# Backward-compat aliases used by older internal callers
# -----------------------------------------------------------------------------

def parse(source: str) -> Node:
    """Alias for ``parse_ltlml``."""
    return parse_ltlml(source)


def to_html(doc: Node) -> str:
    """Render a parsed document node to HTML."""
    return _default_renderer.render(doc)


def to_ansi(doc: Node) -> str:
    """Render a parsed document node to ANSI terminal output."""
    return _to_ansi(doc)
