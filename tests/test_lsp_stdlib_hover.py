"""Tests for stdlib signature hover (lsp-hover-signatures bounty)."""
from lateralus_lang.lsp_server import (
    TextDocument, build_stdlib_index, get_hover, reset_stdlib_index,
)


def test_index_builds():
    reset_stdlib_index()
    idx = build_stdlib_index()
    assert isinstance(idx, dict)
    assert len(idx) > 0


def test_index_has_math_functions():
    idx = build_stdlib_index()
    assert "sqrt" in idx
    assert "detail" in idx["sqrt"]
    assert "fn sqrt" in idx["sqrt"]["detail"]


def test_hover_stdlib_function():
    reset_stdlib_index()
    doc = TextDocument("file:///t.ltl", "lateralus", 1, "sqrt(4.0)")
    hover = get_hover(doc, 0, 1)
    assert hover is not None
    value = hover["contents"]["value"]
    assert "fn sqrt" in value
    assert "```lateralus" in value


def test_hover_unknown_returns_none():
    reset_stdlib_index()
    doc = TextDocument("file:///t.ltl", "lateralus", 1, "nonexistent_fn_xyz(1)")
    assert get_hover(doc, 0, 2) is None


def test_hover_builtin_still_wins():
    reset_stdlib_index()
    doc = TextDocument("file:///t.ltl", "lateralus", 1, "println(1)")
    hover = get_hover(doc, 0, 1)
    assert hover is not None
    assert "println" in hover["contents"]["value"]
