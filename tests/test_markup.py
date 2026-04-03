"""
tests/test_markup.py — Tests for the LTLML Markup Language
"""
import pytest
from lateralus_lang.markup import (
    LTLMLParser, LTLMLRenderer, NodeKind,
    parse_ltlml, render_ltlml,
)


class TestLTLMLParser:
    def test_frontmatter(self):
        doc = parse_ltlml("---\ntitle: Test\nauthor: Smith\n---\n")
        fm = doc.children[0]
        assert fm.kind == NodeKind.FRONTMATTER
        assert fm.attrs["title"] == "Test"
        assert fm.attrs["author"] == "Smith"

    def test_heading(self):
        doc = parse_ltlml("# Hello World")
        h = doc.children[0]
        assert h.kind == NodeKind.HEADING
        assert h.attrs["level"] == 1
        assert h.children[0].text == "Hello World"

    def test_heading_levels(self):
        doc = parse_ltlml("## Level 2\n### Level 3")
        assert doc.children[0].attrs["level"] == 2
        assert doc.children[1].attrs["level"] == 3

    def test_paragraph(self):
        doc = parse_ltlml("This is a paragraph.\nWith two lines.")
        p = doc.children[0]
        assert p.kind == NodeKind.PARAGRAPH

    def test_bold(self):
        doc = parse_ltlml("This is **bold** text.")
        p = doc.children[0]
        bold = [c for c in p.children if c.kind == NodeKind.BOLD]
        assert len(bold) == 1
        assert bold[0].text == "bold"

    def test_italic(self):
        doc = parse_ltlml("This is _italic_ text.")
        p = doc.children[0]
        italic = [c for c in p.children if c.kind == NodeKind.ITALIC]
        assert len(italic) == 1
        assert italic[0].text == "italic"

    def test_inline_code(self):
        doc = parse_ltlml("Use `println` here.")
        p = doc.children[0]
        code = [c for c in p.children if c.kind == NodeKind.CODE_INLINE]
        assert len(code) == 1
        assert code[0].text == "println"

    def test_code_block(self):
        source = "```lateralus\nfn main() {\n    println(\"hi\")\n}\n```"
        doc = parse_ltlml(source)
        cb = doc.children[0]
        assert cb.kind == NodeKind.CODE_BLOCK
        assert cb.attrs["language"] == "lateralus"
        assert "fn main()" in cb.text

    def test_math_inline(self):
        doc = parse_ltlml("The formula $E = mc^2$ is famous.")
        p = doc.children[0]
        math = [c for c in p.children if c.kind == NodeKind.MATH_INLINE]
        assert len(math) == 1
        assert math[0].text == "E = mc^2"

    def test_math_block(self):
        source = "$$\nx^2 + y^2 = r^2\n$$"
        doc = parse_ltlml(source)
        mb = doc.children[0]
        assert mb.kind == NodeKind.MATH_BLOCK
        assert "x^2" in mb.text

    def test_link(self):
        doc = parse_ltlml("[Click here](https://example.com)")
        p = doc.children[0]
        link = [c for c in p.children if c.kind == NodeKind.LINK]
        assert len(link) == 1
        assert link[0].text == "Click here"
        assert link[0].attrs["href"] == "https://example.com"

    def test_image(self):
        doc = parse_ltlml("![Alt text](image.png)")
        p = doc.children[0]
        img = [c for c in p.children if c.kind == NodeKind.IMAGE]
        assert len(img) == 1
        assert img[0].attrs["src"] == "image.png"

    def test_unordered_list(self):
        doc = parse_ltlml("- Item 1\n- Item 2\n- Item 3")
        lst = doc.children[0]
        assert lst.kind == NodeKind.UNORDERED_LIST
        assert len(lst.children) == 3

    def test_ordered_list(self):
        doc = parse_ltlml("1. First\n2. Second\n3. Third")
        lst = doc.children[0]
        assert lst.kind == NodeKind.ORDERED_LIST
        assert len(lst.children) == 3

    def test_blockquote(self):
        doc = parse_ltlml("> This is quoted\n> text here")
        bq = doc.children[0]
        assert bq.kind == NodeKind.BLOCKQUOTE

    def test_hr(self):
        doc = parse_ltlml("---")
        # Note: --- at start is frontmatter delimiter, need content before
        doc = parse_ltlml("Text\n\n---")
        hr = [c for c in doc.children if c.kind == NodeKind.HR]
        assert len(hr) == 1

    def test_table(self):
        source = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        doc = parse_ltlml(source)
        table = doc.children[0]
        assert table.kind == NodeKind.TABLE
        assert len(table.children) == 3  # header + 2 rows

    def test_admonition(self):
        source = "::: warning\nBe careful!\n:::"
        doc = parse_ltlml(source)
        adm = doc.children[0]
        assert adm.kind == NodeKind.ADMONITION
        assert adm.attrs["type"] == "warning"

    def test_theorem(self):
        source = "::: theorem Pythagoras\na^2 + b^2 = c^2\n:::"
        doc = parse_ltlml(source)
        thm = doc.children[0]
        assert thm.kind == NodeKind.THEOREM
        assert thm.attrs["type"] == "theorem"
        assert thm.attrs["title"] == "Pythagoras"

    def test_crossref(self):
        doc = parse_ltlml("See @ref{eq:euler} for details.")
        p = doc.children[0]
        refs = [c for c in p.children if c.kind == NodeKind.CROSSREF]
        assert len(refs) == 1
        assert refs[0].attrs["label"] == "eq:euler"

    def test_citation(self):
        doc = parse_ltlml("As shown in @cite{knuth1997}.")
        p = doc.children[0]
        cites = [c for c in p.children if c.kind == NodeKind.CITATION]
        assert len(cites) == 1
        assert cites[0].attrs["key"] == "knuth1997"


class TestLTLMLRenderer:
    def test_renders_html(self):
        html = render_ltlml("# Hello\n\nWorld")
        assert "<html" in html
        assert "<h1" in html
        assert "Hello" in html

    def test_renders_title_from_frontmatter(self):
        html = render_ltlml("---\ntitle: My Title\n---\n# Content")
        assert "<title>My Title</title>" in html

    def test_renders_code_block(self):
        html = render_ltlml("```python\nprint('hi')\n```")
        assert "<pre>" in html
        assert "<code" in html
        assert "print" in html

    def test_renders_math(self):
        html = render_ltlml("$$\nx^2\n$$")
        assert "$$" in html
        assert "katex" in html.lower()

    def test_renders_admonition(self):
        html = render_ltlml("::: warning\nCareful!\n:::")
        assert "admonition" in html
        assert "warning" in html

    def test_renders_theorem(self):
        html = render_ltlml("::: theorem Test\nContent\n:::")
        assert "theorem" in html
        assert "Theorem" in html

    def test_renders_table(self):
        html = render_ltlml("| A | B |\n|---|---|\n| 1 | 2 |")
        assert "<table" in html
        assert "<th" in html
        assert "<td" in html

    def test_stylesheet_included(self):
        html = render_ltlml("# Test")
        assert "ltl-bg" in html
        assert "ltlml-document" in html

    def test_full_document(self):
        source = """---
title: Test Document
author: Test Author
---

# Introduction

This is **bold** and _italic_ text with `code`.

## Math

The equation $E = mc^2$ is famous.

$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$

::: note
This is important!
:::

```lateralus
fn main() {
    println("Hello!")
}
```

| Feature | Status |
|---------|--------|
| Parser  | Done   |
| Render  | Done   |
"""
        html = render_ltlml(source)
        assert "<html" in html
        assert "Test Document" in html
        assert "Test Author" in html
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<code>code</code>" in html
        assert "E = mc^2" in html
        assert "admonition" in html
        assert "<table" in html
