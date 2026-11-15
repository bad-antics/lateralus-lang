"""Tests for the stdlib surface used by the LSP hover provider."""
from __future__ import annotations

import pytest

from lateralus_lang.lsp_server import TextDocument, get_hover
from lateralus_lang.stdlib_index import StdlibIndex


@pytest.fixture
def stdlib_dir(tmp_path):
    root = tmp_path / "stdlib"
    root.mkdir()
    (root / "math.ltl").write_text(
        "module stdlib.math\n"
        "\n"
        "/// Add two numbers.\n"
        "pub fn add(a: float, b: float) -> float {\n"
        "    return a + b\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "util.ltl").write_text(
        "// -- Helpers -------------------------------------------------------\n"
        "//\n"
        "// Strip whitespace and quotes from a string.\n"
        "fn strip(value) {\n"
        "    return value\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "weird.ltl").write_text(
        "// =====================================================================\n"
        "// LATERALUS Standard Library — weird.ltl\n"
        "// =====================================================================\n"
        "// -- Fancy encode --------------------------------------------------\n"
        "//\n"
        "// -------------------------------------------------------------------\n"
        "fn encode(xs: list) -> map {\n"
        "    return {}\n"
        "}\n",
        encoding="utf-8",
    )
    return root


class TestStdlibIndexBuild:
    def test_empty_dir_yields_no_functions(self, tmp_path):
        assert len(StdlibIndex(tmp_path / "missing")) == 0

    def test_parses_public_doc_function(self, stdlib_dir):
        fn = StdlibIndex(stdlib_dir).lookup("add")
        assert fn is not None
        assert fn.signature == "fn add(a: float, b: float) -> float"
        assert fn.doc == "Add two numbers."
        assert fn.module == "stdlib.math"
        assert fn.is_public is True

    def test_module_defaults_to_file_stem_without_decl(self, stdlib_dir):
        assert StdlibIndex(stdlib_dir).lookup("strip").module == "util"

    def test_multiline_parameter_list(self, tmp_path):
        root = tmp_path / "stdlib"
        root.mkdir()
        (root / "stats.ltl").write_text(
            "module stdlib.stats\n"
            "\n"
            "fn calculate_data_point(\n"
            "    dp: int\n"
            ") -> float {\n"
            "    return 1.0\n"
            "}\n",
            encoding="utf-8",
        )
        fn = StdlibIndex(root).lookup("calculate_data_point")
        assert fn is not None
        assert fn.signature == "fn calculate_data_point(dp: int) -> float"

    def test_plain_comment_block_used_as_doc(self, stdlib_dir):
        fn = StdlibIndex(stdlib_dir).lookup("strip")
        assert fn is not None
        assert fn.doc == "Strip whitespace and quotes from a string."
        assert fn.doc_style == "line"

    def test_banners_and_exports_headers_are_not_docs(self, stdlib_dir):
        fn = StdlibIndex(stdlib_dir).lookup("encode")
        assert fn is not None
        assert fn.doc == ""


class TestStdlibLookup:
    def test_lookup_missing_name(self, tmp_path):
        index = StdlibIndex(tmp_path / "missing")
        assert index.lookup("nope") is None
        fn, related = index.lookup_with_related("nope")
        assert fn is None
        assert related == []

    def test_import_context_prefers_module(self, stdlib_dir):
        index = StdlibIndex(stdlib_dir)
        assert index.lookup("add", context="import stdlib.math").module == "stdlib.math"

    def test_related_lists_other_modules(self, tmp_path):
        root = tmp_path / "stdlib"
        root.mkdir()
        (root / "a.ltl").write_text("pub fn dup(a: int) -> int { return a }\n", encoding="utf-8")
        (root / "b.ltl").write_text("pub fn dup(a: int) -> int { return a }\n", encoding="utf-8")
        index = StdlibIndex(root)
        fn, related = index.lookup_with_related("dup")
        assert fn is not None
        assert related == ["b"]


class TestRealStdlibHover:
    def test_hover_stdlib_core_function(self):
        doc = TextDocument("file:///x.ltl", "lateralus", 1, "let c = clamp(1.0, 0.0, 2.0)")
        hover = get_hover(doc, 0, 8)
        assert hover is not None
        value = hover["contents"]["kind"]
        assert value == "markdown"
        text = hover["contents"]["value"]
        assert "fn clamp(x: float, lo: float, hi: float) -> float" in text
        assert "Clamp x to the range [lo, hi]" in text

    def test_hover_stdlib_function_signature_and_doc(self):
        from lateralus_lang.stdlib_index import lookup_stdlib_function

        fn = lookup_stdlib_function("abs")
        assert fn is not None
        assert fn.module == "stdlib.core"
        assert fn.doc == "Return the absolute value of a number"

    def test_hover_unknown_word_is_none(self):
        doc = TextDocument("file:///x.ltl", "lateralus", 1, "let zzz = 1")
        assert get_hover(doc, 0, 7) is None
