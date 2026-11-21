"""
Regression tests for stdlib/strings.ltl.

str_reverse() called split(s, "") which maps to Python's str.split("")
→ ValueError on any input. Now collects chars via slice().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "strings.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_str_reverse():
    ns = _load()
    assert ns["str_reverse"]("hello") == "olleh"
    assert ns["str_reverse"]("abc123") == "321cba"
    assert ns["str_reverse"]("") == ""
    assert ns["str_reverse"]("a") == "a"


def test_case_and_trim():
    ns = _load()
    assert ns["upper"]("AbC") == "ABC"
    assert ns["lower"]("AbC") == "abc"
    assert ns["trim"]("  x  ") == "x"
    assert ns["ltrim"]("\t x") == "x"
    assert ns["rtrim"]("x \n") == "x"


def test_predicates_and_search():
    ns = _load()
    assert ns["contains"]("hello", "ell") is True
    assert ns["starts_with"]("hello", "he") is True
    assert ns["ends_with"]("hello", "lo") is True
    assert ns["index_of"]("hello", "ll") == 2
    assert ns["count"]("hello", "l") == 2
    assert ns["is_digits"]("123") is True
    assert ns["is_digits"]("12a") is False
    assert ns["is_digits"]("") is False


def test_transform_and_format():
    ns = _load()
    assert ns["replace"]("aaa", "a", "b") == "bbb"
    assert ns["split"]("a,b,c", ",") == ["a", "b", "c"]
    assert ns["join"](["a", "b"], "-") == "a-b"
    assert ns["repeat_str"]("ab", 3) == "ababab"
    assert ns["pad_left"]("7", 3, "0") == "007"
    assert ns["pad_right"]("7", 3, "0") == "700"
    assert ns["format_int"](42, 5) == "00042"
