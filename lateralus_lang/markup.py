"""
lateralus_lang/markup.py  -  LTLML: LATERALUS Markup Language
===============================================================================
A domain-specific markup language for LATERALUS documentation, scientific
papers, and technical writing.  Inspired by Markdown but extended with:

  · Native code blocks with syntax-highlighted LATERALUS
  · Mathematical notation (LaTeX-compatible)
  · Structured metadata (frontmatter)
  · Cross-references and citations
  · Figure/table/equation numbering
  · Theorem/proof/definition environments
  · Interactive code execution blocks
  · Data tables with alignment
  · Admonitions (note, warning, tip, danger)
  · Embedded diagrams (text-based)

File extension: .ltlml

Syntax Overview:
-----------------------------------------------------------------------------
  ---                           Frontmatter (YAML-like)
  title: My Document
  author: Dr. Smith
  date: 2026-03-30
  ---

  # Heading 1                   Headings (1-6 levels)
  ## Heading 2

  Regular *bold* _italic_       Inline formatting
  ~strikethrough~ `code`

  > Blockquote                  Blockquotes

  - List item                   Unordered lists
  1. Ordered item               Ordered lists

  [link text](url)              Links
  ![alt text](image.png)        Images

  ```lateralus                  Code blocks
  fn greet(name: str) -> str {
      return "Hello, {name}!"
  }
  ```

  $E = mc^2$                   Inline math
  $$                            Display math
  \\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
  $$

  ::: note                     Admonitions
  This is important!
  :::

  ::: theorem Pythagoras        Theorem environments
  For a right triangle: $a^2 + b^2 = c^2$
  :::

  @ref{eq:euler}               Cross-references
  @cite{knuth1997}             Citations

  | Col A | Col B |             Tables
  |-------|-------|
  | 1     | 2     |

  @fig{diagram.png}{Caption}   Figures with captions
  @eq{label}                   Equation labels

v1.5.0
===============================================================================
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# AST Nodes for LTLML
# -----------------------------------------------------------------------------

class NodeKind(Enum):
    DOCUMENT    = auto()
    FRONTMATTER = auto()
    HEADING     = auto()
    PARAGRAPH   = auto()
    TEXT        = auto()
    BOLD        = auto()
    ITALIC      = auto()
    STRIKE      = auto()
    CODE_INLINE = auto()
    CODE_BLOCK  = auto()
    BLOCKQUOTE  = auto()
    ORDERED_LIST   = auto()
    UNORDERED_LIST = auto()
    LIST_ITEM   = auto()
    LINK        = auto()
    IMAGE       = auto()
    MATH_INLINE = auto()
    MATH_BLOCK  = auto()
    TABLE       = auto()
    TABLE_ROW   = auto()
    TABLE_CELL  = auto()
    ADMONITION  = auto()
    THEOREM     = auto()
    CROSSREF    = auto()
    CITATION    = auto()
    FIGURE      = auto()
    HR          = auto()
    LINEBREAK   = auto()


@dataclass
class LTLMLNode:
    """Generic AST node for LTLML documents."""
    kind: NodeKind
    children: List["LTLMLNode"] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def add(self, child: "LTLMLNode") -> "LTLMLNode":
        self.children.append(child)
        return self


# -----------------------------------------------------------------------------
# LTLML Parser
# -----------------------------------------------------------------------------

class LTLMLParser:
    """Parse .ltlml files into an AST."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.split("\n")
        self.pos = 0
        self.doc = LTLMLNode(kind=NodeKind.DOCUMENT)
        self._counters = {"figure": 0, "table": 0, "equation": 0, "theorem": 0}
        self._refs: Dict[str, str] = {}  # label → number

    def parse(self) -> LTLMLNode:
        """Parse the full document and return AST root."""
        # Check for frontmatter
        if self.pos < len(self.lines) and self.lines[self.pos].strip() == "---":
            self._parse_frontmatter()

        while self.pos < len(self.lines):
            self._parse_block()

        return self.doc

    def _current(self) -> str:
        return self.lines[self.pos] if self.pos < len(self.lines) else ""

    def _advance(self) -> str:
        line = self._current()
        self.pos += 1
        return line

    # -- Frontmatter -------------------------------------------------------

    def _parse_frontmatter(self):
        self._advance()  # skip opening ---
        meta = {}
        while self.pos < len(self.lines):
            line = self._current()
            if line.strip() == "---":
                self._advance()
                break
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()
            self._advance()
        self.doc.add(LTLMLNode(kind=NodeKind.FRONTMATTER, attrs=meta))

    # -- Block-level parsing -----------------------------------------------

    def _parse_block(self):
        line = self._current()
        stripped = line.strip()

        # Empty line
        if not stripped:
            self._advance()
            return

        # Heading
        if stripped.startswith("#"):
            self._parse_heading()
            return

        # HR
        if re.match(r"^-{3,}$|^_{3,}$|^\*{3,}$", stripped):
            self._advance()
            self.doc.add(LTLMLNode(kind=NodeKind.HR))
            return

        # Code block
        if stripped.startswith("```"):
            self._parse_code_block()
            return

        # Math block
        if stripped.startswith("$$"):
            self._parse_math_block()
            return

        # Admonition / Theorem
        if stripped.startswith(":::"):
            self._parse_admonition()
            return

        # Blockquote
        if stripped.startswith(">"):
            self._parse_blockquote()
            return

        # Unordered list
        if re.match(r"^[-*+]\s", stripped):
            self._parse_list(ordered=False)
            return

        # Ordered list
        if re.match(r"^\d+\.\s", stripped):
            self._parse_list(ordered=True)
            return

        # Table
        if "|" in stripped and stripped.startswith("|"):
            self._parse_table()
            return

        # Figure
        if stripped.startswith("@fig{"):
            self._parse_figure()
            return

        # Default: paragraph
        self._parse_paragraph()

    def _parse_heading(self):
        line = self._advance().strip()
        level = 0
        while level < len(line) and line[level] == "#":
            level += 1
        text = line[level:].strip()
        node = LTLMLNode(kind=NodeKind.HEADING, attrs={"level": level})
        node.children = self._parse_inline(text)
        self.doc.add(node)

    def _parse_code_block(self):
        opening = self._advance().strip()
        lang = opening[3:].strip() or "text"
        lines = []
        while self.pos < len(self.lines):
            line = self._current()
            if line.strip() == "```":
                self._advance()
                break
            lines.append(line)
            self._advance()
        self.doc.add(LTLMLNode(
            kind=NodeKind.CODE_BLOCK,
            text="\n".join(lines),
            attrs={"language": lang},
        ))

    def _parse_math_block(self):
        self._advance()  # skip opening $$
        lines = []
        while self.pos < len(self.lines):
            if self._current().strip() == "$$":
                self._advance()
                break
            lines.append(self._current())
            self._advance()
        self._counters["equation"] += 1
        self.doc.add(LTLMLNode(
            kind=NodeKind.MATH_BLOCK,
            text="\n".join(lines),
            attrs={"number": self._counters["equation"]},
        ))

    def _parse_admonition(self):
        opening = self._advance().strip()
        parts = opening[3:].strip().split(None, 1)
        kind = parts[0] if parts else "note"
        title = parts[1] if len(parts) > 1 else ""

        # Check if it's a theorem-like environment
        theorem_kinds = {"theorem", "lemma", "corollary", "definition",
                         "proposition", "proof", "example", "remark"}
        is_theorem = kind.lower() in theorem_kinds

        lines = []
        while self.pos < len(self.lines):
            if self._current().strip() == ":::":
                self._advance()
                break
            lines.append(self._current())
            self._advance()

        if is_theorem:
            self._counters["theorem"] += 1
            node = LTLMLNode(
                kind=NodeKind.THEOREM,
                text="\n".join(lines),
                attrs={
                    "type": kind.lower(),
                    "title": title,
                    "number": self._counters["theorem"],
                },
            )
        else:
            node = LTLMLNode(
                kind=NodeKind.ADMONITION,
                text="\n".join(lines),
                attrs={"type": kind.lower(), "title": title},
            )
        self.doc.add(node)

    def _parse_blockquote(self):
        lines = []
        while self.pos < len(self.lines):
            line = self._current()
            if not line.strip().startswith(">"):
                break
            lines.append(re.sub(r"^>\s?", "", line))
            self._advance()
        node = LTLMLNode(kind=NodeKind.BLOCKQUOTE)
        node.children = self._parse_inline("\n".join(lines))
        self.doc.add(node)

    def _parse_list(self, ordered: bool):
        kind = NodeKind.ORDERED_LIST if ordered else NodeKind.UNORDERED_LIST
        lst = LTLMLNode(kind=kind)
        pattern = r"^\d+\.\s" if ordered else r"^[-*+]\s"
        while self.pos < len(self.lines):
            line = self._current().strip()
            if not re.match(pattern, line):
                break
            text = re.sub(pattern, "", line)
            item = LTLMLNode(kind=NodeKind.LIST_ITEM)
            item.children = self._parse_inline(text)
            lst.add(item)
            self._advance()
        self.doc.add(lst)

    def _parse_table(self):
        rows = []
        while self.pos < len(self.lines):
            line = self._current().strip()
            if not line.startswith("|"):
                break
            # Skip separator row
            if re.match(r"^\|[-:|]+\|$", line.replace(" ", "")):
                self._advance()
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            row = LTLMLNode(kind=NodeKind.TABLE_ROW)
            for cell_text in cells:
                cell = LTLMLNode(kind=NodeKind.TABLE_CELL)
                cell.children = self._parse_inline(cell_text)
                row.add(cell)
            rows.append(row)
            self._advance()
        self._counters["table"] += 1
        table = LTLMLNode(kind=NodeKind.TABLE,
                          attrs={"number": self._counters["table"]})
        table.children = rows
        self.doc.add(table)

    def _parse_figure(self):
        line = self._advance().strip()
        m = re.match(r"@fig\{([^}]+)\}\{([^}]*)\}", line)
        if m:
            self._counters["figure"] += 1
            self.doc.add(LTLMLNode(
                kind=NodeKind.FIGURE,
                attrs={
                    "src": m.group(1),
                    "caption": m.group(2),
                    "number": self._counters["figure"],
                },
            ))

    def _parse_paragraph(self):
        lines = []
        while self.pos < len(self.lines):
            line = self._current()
            if not line.strip():
                break
            if line.strip().startswith(("#", "```", "$$", ":::", "|", ">", "@fig{")):
                break
            if re.match(r"^[-*+]\s|^\d+\.\s", line.strip()):
                break
            lines.append(line.strip())
            self._advance()
        text = " ".join(lines)
        para = LTLMLNode(kind=NodeKind.PARAGRAPH)
        para.children = self._parse_inline(text)
        self.doc.add(para)

    # -- Inline-level parsing ----------------------------------------------

    def _parse_inline(self, text: str) -> List[LTLMLNode]:
        """Parse inline formatting: bold, italic, code, links, math, refs."""
        nodes = []
        pattern = re.compile(
            r"(\*\*(.+?)\*\*)"         # bold
            r"|(_(.+?)_)"              # italic
            r"|(~(.+?)~)"             # strikethrough
            r"|(`([^`]+?)`)"           # inline code
            r"|(\$([^$]+?)\$)"         # inline math
            r"|(\[([^\]]+)\]\(([^)]+)\))"  # link
            r"|(!\[([^\]]*)\]\(([^)]+)\))" # image
            r"|(@ref\{([^}]+)\})"      # cross-reference
            r"|(@cite\{([^}]+)\})"     # citation
        )
        last = 0
        for m in pattern.finditer(text):
            # Plain text before match
            if m.start() > last:
                nodes.append(LTLMLNode(kind=NodeKind.TEXT,
                                       text=text[last:m.start()]))
            if m.group(2) is not None:  # bold
                nodes.append(LTLMLNode(kind=NodeKind.BOLD, text=m.group(2)))
            elif m.group(4) is not None:  # italic
                nodes.append(LTLMLNode(kind=NodeKind.ITALIC, text=m.group(4)))
            elif m.group(6) is not None:  # strikethrough
                nodes.append(LTLMLNode(kind=NodeKind.STRIKE, text=m.group(6)))
            elif m.group(8) is not None:  # code
                nodes.append(LTLMLNode(kind=NodeKind.CODE_INLINE,
                                       text=m.group(8)))
            elif m.group(10) is not None:  # math
                nodes.append(LTLMLNode(kind=NodeKind.MATH_INLINE,
                                       text=m.group(10)))
            elif m.group(12) is not None:  # link
                nodes.append(LTLMLNode(kind=NodeKind.LINK,
                                       text=m.group(12),
                                       attrs={"href": m.group(13)}))
            elif m.group(15) is not None:  # image
                nodes.append(LTLMLNode(kind=NodeKind.IMAGE,
                                       text=m.group(15),
                                       attrs={"src": m.group(16)}))
            elif m.group(18) is not None:  # cross-ref
                nodes.append(LTLMLNode(kind=NodeKind.CROSSREF,
                                       attrs={"label": m.group(18)}))
            elif m.group(20) is not None:  # citation
                nodes.append(LTLMLNode(kind=NodeKind.CITATION,
                                       attrs={"key": m.group(20)}))
            last = m.end()

        if last < len(text):
            nodes.append(LTLMLNode(kind=NodeKind.TEXT, text=text[last:]))

        return nodes


# -----------------------------------------------------------------------------
# LTLML Renderer → HTML
# -----------------------------------------------------------------------------

class LTLMLRenderer:
    """Render an LTLML AST to HTML."""

    ADMONITION_ICONS = {
        "note": "ℹ️",
        "warning": "⚠️",
        "tip": "💡",
        "danger": "🔴",
        "info": "ℹ️",
        "success": "✅",
        "example": "📋",
    }

    THEOREM_LABELS = {
        "theorem": "Theorem",
        "lemma": "Lemma",
        "corollary": "Corollary",
        "definition": "Definition",
        "proposition": "Proposition",
        "proof": "Proof",
        "example": "Example",
        "remark": "Remark",
    }

    def __init__(self, theme: str = "lateralus"):
        self.theme = theme

    def render(self, doc: LTLMLNode) -> str:
        """Render a complete HTML document."""
        meta = {}
        for child in doc.children:
            if child.kind == NodeKind.FRONTMATTER:
                meta = child.attrs
                break

        title = meta.get("title", "LATERALUS Document")
        body = self._render_children(doc)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>{self._get_stylesheet()}</style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
            onload="renderMathInElement(document.body, {{
                delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}}
                ]
            }});"></script>
</head>
<body>
    <article class="ltlml-document">
        {self._render_meta(meta)}
        {body}
    </article>
</body>
</html>"""

    def _render_meta(self, meta: Dict[str, str]) -> str:
        if not meta:
            return ""
        parts = []
        if "title" in meta:
            parts.append(f'<h1 class="doc-title">{html.escape(meta["title"])}</h1>')
        info_parts = []
        if "author" in meta:
            info_parts.append(f'<span class="author">{html.escape(meta["author"])}</span>')
        if "date" in meta:
            info_parts.append(f'<time>{html.escape(meta["date"])}</time>')
        if info_parts:
            parts.append(f'<div class="doc-meta">{" · ".join(info_parts)}</div>')
        if "abstract" in meta:
            parts.append(f'<div class="abstract"><strong>Abstract.</strong> '
                         f'{html.escape(meta["abstract"])}</div>')
        return "\n".join(parts)

    def _render_children(self, node: LTLMLNode) -> str:
        return "\n".join(self._render_node(c) for c in node.children)

    def _render_node(self, node: LTLMLNode) -> str:
        """Dispatch rendering based on node kind."""
        method = f"_render_{node.kind.name.lower()}"
        fn = getattr(self, method, None)
        if fn:
            return fn(node)
        return f"<!-- unknown: {node.kind.name} -->"

    def _render_frontmatter(self, node: LTLMLNode) -> str:
        return ""  # handled in _render_meta

    def _render_heading(self, node: LTLMLNode) -> str:
        level = node.attrs.get("level", 1)
        content = self._render_inline_children(node)
        anchor = re.sub(r"[^a-z0-9]+", "-", content.lower()).strip("-")
        return f'<h{level} id="{anchor}">{content}</h{level}>'

    def _render_paragraph(self, node: LTLMLNode) -> str:
        return f"<p>{self._render_inline_children(node)}</p>"

    def _render_code_block(self, node: LTLMLNode) -> str:
        lang = node.attrs.get("language", "text")
        escaped = html.escape(node.text)
        return (f'<pre><code class="language-{lang}">'
                f'{escaped}</code></pre>')

    def _render_blockquote(self, node: LTLMLNode) -> str:
        return f"<blockquote>{self._render_inline_children(node)}</blockquote>"

    def _render_ordered_list(self, node: LTLMLNode) -> str:
        items = "\n".join(self._render_node(c) for c in node.children)
        return f"<ol>\n{items}\n</ol>"

    def _render_unordered_list(self, node: LTLMLNode) -> str:
        items = "\n".join(self._render_node(c) for c in node.children)
        return f"<ul>\n{items}\n</ul>"

    def _render_list_item(self, node: LTLMLNode) -> str:
        return f"<li>{self._render_inline_children(node)}</li>"

    def _render_math_block(self, node: LTLMLNode) -> str:
        num = node.attrs.get("number", "")
        return (f'<div class="math-block">'
                f'<span class="eq-number">({num})</span>'
                f'$${node.text}$$</div>')

    def _render_table(self, node: LTLMLNode) -> str:
        num = node.attrs.get("number", "")
        rows_html = []
        for i, row in enumerate(node.children):
            tag = "th" if i == 0 else "td"
            cells = "".join(
                f"<{tag}>{self._render_inline_children(c)}</{tag}>"
                for c in row.children
            )
            rows_html.append(f"<tr>{cells}</tr>")
        header = rows_html[0] if rows_html else ""
        body = "\n".join(rows_html[1:])
        return (f'<table class="ltlml-table">'
                f'<thead>{header}</thead>'
                f'<tbody>{body}</tbody></table>'
                f'<p class="table-caption">Table {num}</p>')

    def _render_admonition(self, node: LTLMLNode) -> str:
        kind = node.attrs.get("type", "note")
        title = node.attrs.get("title", kind.capitalize())
        icon = self.ADMONITION_ICONS.get(kind, "📌")
        return (f'<div class="admonition admonition-{kind}">'
                f'<div class="admonition-title">{icon} {html.escape(title)}</div>'
                f'<div class="admonition-body">{html.escape(node.text)}</div>'
                f'</div>')

    def _render_theorem(self, node: LTLMLNode) -> str:
        kind = node.attrs.get("type", "theorem")
        num = node.attrs.get("number", "")
        title = node.attrs.get("title", "")
        label = self.THEOREM_LABELS.get(kind, kind.capitalize())
        heading = f"<strong>{label} {num}</strong>"
        if title:
            heading += f" ({html.escape(title)})"
        return (f'<div class="theorem theorem-{kind}">'
                f'<div class="theorem-heading">{heading}.</div>'
                f'<div class="theorem-body">{html.escape(node.text)}</div>'
                f'</div>')

    def _render_figure(self, node: LTLMLNode) -> str:
        src = node.attrs.get("src", "")
        caption = node.attrs.get("caption", "")
        num = node.attrs.get("number", "")
        return (f'<figure>'
                f'<img src="{html.escape(src)}" alt="{html.escape(caption)}">'
                f'<figcaption>Figure {num}: {html.escape(caption)}</figcaption>'
                f'</figure>')

    def _render_hr(self, node: LTLMLNode) -> str:
        return "<hr>"

    # -- Inline rendering -------------------------------------------------

    def _render_inline_children(self, node: LTLMLNode) -> str:
        return "".join(self._render_inline(c) for c in node.children)

    def _render_inline(self, node: LTLMLNode) -> str:
        if node.kind == NodeKind.TEXT:
            return html.escape(node.text)
        if node.kind == NodeKind.BOLD:
            return f"<strong>{html.escape(node.text)}</strong>"
        if node.kind == NodeKind.ITALIC:
            return f"<em>{html.escape(node.text)}</em>"
        if node.kind == NodeKind.STRIKE:
            return f"<del>{html.escape(node.text)}</del>"
        if node.kind == NodeKind.CODE_INLINE:
            return f"<code>{html.escape(node.text)}</code>"
        if node.kind == NodeKind.MATH_INLINE:
            return f"${node.text}$"
        if node.kind == NodeKind.LINK:
            href = node.attrs.get("href", "")
            return f'<a href="{html.escape(href)}">{html.escape(node.text)}</a>'
        if node.kind == NodeKind.IMAGE:
            src = node.attrs.get("src", "")
            return f'<img src="{html.escape(src)}" alt="{html.escape(node.text)}">'
        if node.kind == NodeKind.CROSSREF:
            label = node.attrs.get("label", "")
            return f'<a href="#{html.escape(label)}" class="crossref">[ref:{label}]</a>'
        if node.kind == NodeKind.CITATION:
            key = node.attrs.get("key", "")
            return f'<cite>[{html.escape(key)}]</cite>'
        return html.escape(node.text)

    # -- Stylesheet --------------------------------------------------------

    def _get_stylesheet(self) -> str:
        return """
:root {
    --ltl-bg: #0d1117;
    --ltl-fg: #c9d1d9;
    --ltl-accent: #58a6ff;
    --ltl-accent2: #bc8cff;
    --ltl-border: #30363d;
    --ltl-code-bg: #161b22;
    --ltl-success: #3fb950;
    --ltl-warning: #d29922;
    --ltl-danger: #f85149;
    --ltl-theorem-bg: #161b22;
    --ltl-admonition-note: #58a6ff;
    --ltl-admonition-warning: #d29922;
    --ltl-admonition-danger: #f85149;
    --ltl-admonition-tip: #3fb950;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, sans-serif;
    background: var(--ltl-bg);
    color: var(--ltl-fg);
    line-height: 1.7;
    font-size: 16px;
}

.ltlml-document {
    max-width: 48rem;
    margin: 2rem auto;
    padding: 2rem;
}

.doc-title {
    font-size: 2.5rem;
    color: var(--ltl-accent);
    margin-bottom: 0.5rem;
    border-bottom: 2px solid var(--ltl-accent);
    padding-bottom: 0.5rem;
}

.doc-meta {
    color: #8b949e;
    margin-bottom: 2rem;
    font-size: 0.95rem;
}

.abstract {
    background: var(--ltl-code-bg);
    border-left: 3px solid var(--ltl-accent2);
    padding: 1rem 1.5rem;
    margin: 1.5rem 0;
    font-style: italic;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ltl-fg);
    margin: 1.5rem 0 0.75rem;
    line-height: 1.3;
}
h1 { font-size: 2rem; border-bottom: 1px solid var(--ltl-border); padding-bottom: 0.3rem; }
h2 { font-size: 1.5rem; color: var(--ltl-accent); }
h3 { font-size: 1.25rem; color: var(--ltl-accent2); }

p { margin: 0.75rem 0; }

a { color: var(--ltl-accent); text-decoration: none; }
a:hover { text-decoration: underline; }

pre {
    background: var(--ltl-code-bg);
    border: 1px solid var(--ltl-border);
    border-radius: 6px;
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;
    font-size: 0.9rem;
}

code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    background: var(--ltl-code-bg);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
}

pre code { background: none; padding: 0; }

blockquote {
    border-left: 3px solid var(--ltl-accent);
    padding: 0.5rem 1rem;
    margin: 1rem 0;
    color: #8b949e;
    background: var(--ltl-code-bg);
    border-radius: 0 6px 6px 0;
}

ul, ol { margin: 0.5rem 0; padding-left: 2rem; }
li { margin: 0.3rem 0; }

table.ltlml-table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
}
table.ltlml-table th, table.ltlml-table td {
    border: 1px solid var(--ltl-border);
    padding: 0.5rem 1rem;
    text-align: left;
}
table.ltlml-table th { background: var(--ltl-code-bg); color: var(--ltl-accent); }
.table-caption { text-align: center; color: #8b949e; font-size: 0.9rem; }

.admonition {
    border-radius: 6px;
    border: 1px solid var(--ltl-border);
    margin: 1rem 0;
    overflow: hidden;
}
.admonition-title {
    padding: 0.5rem 1rem;
    font-weight: 600;
    background: var(--ltl-code-bg);
}
.admonition-body { padding: 0.75rem 1rem; }
.admonition-note { border-left: 4px solid var(--ltl-admonition-note); }
.admonition-warning { border-left: 4px solid var(--ltl-admonition-warning); }
.admonition-danger { border-left: 4px solid var(--ltl-admonition-danger); }
.admonition-tip { border-left: 4px solid var(--ltl-admonition-tip); }

.theorem {
    border: 1px solid var(--ltl-border);
    border-radius: 6px;
    margin: 1.5rem 0;
    padding: 1rem 1.5rem;
    background: var(--ltl-theorem-bg);
    border-left: 4px solid var(--ltl-accent2);
}
.theorem-heading {
    color: var(--ltl-accent2);
    margin-bottom: 0.5rem;
}

.math-block {
    position: relative;
    margin: 1.5rem 0;
    padding: 1rem;
    text-align: center;
    background: var(--ltl-code-bg);
    border-radius: 6px;
}
.eq-number {
    position: absolute;
    right: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: #8b949e;
}

figure {
    margin: 1.5rem 0;
    text-align: center;
}
figure img { max-width: 100%; border-radius: 6px; }
figcaption { color: #8b949e; font-size: 0.9rem; margin-top: 0.5rem; }

hr {
    border: none;
    border-top: 1px solid var(--ltl-border);
    margin: 2rem 0;
}

.crossref { color: var(--ltl-accent2); font-weight: 500; }
cite { color: #8b949e; font-style: normal; }
"""


# -----------------------------------------------------------------------------
# Convenience API
# -----------------------------------------------------------------------------

def parse_ltlml(source: str) -> LTLMLNode:
    """Parse LTLML source into an AST."""
    return LTLMLParser(source).parse()


def render_ltlml(source: str, theme: str = "lateralus") -> str:
    """Parse and render LTLML source to HTML."""
    ast = parse_ltlml(source)
    return LTLMLRenderer(theme=theme).render(ast)


def compile_ltlml_file(input_path: str, output_path: Optional[str] = None) -> str:
    """Compile a .ltlml file to .html."""
    with open(input_path, "r", encoding="utf-8") as f:
        source = f.read()
    html_out = render_ltlml(source)
    if output_path is None:
        output_path = input_path.rsplit(".", 1)[0] + ".html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    return output_path
