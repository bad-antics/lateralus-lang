"""
Regression tests for stdlib/logfmt.ltl.

char_at() is not a runtime builtin — needs_quoting/escape_quoted/parse
all raised NameError. Now uses slice().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "logfmt.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_encode_quotes_when_needed():
    ns = _load()
    assert ns["format_value"]("plain") == "plain"
    assert ns["format_value"]("a b") == '"a b"'
    assert ns["format_value"]("a=b") == '"a=b"'
    assert ns["format_value"]('say "hi"') == '"say \\"hi\\""'
    assert ns["format_value"]("") == '""'


def test_parse_logfmt_line():
    ns = _load()
    pairs = ns["parse"]('ts=2026-04-24T12:34:56Z level=info msg="hello world" user=42 flag')
    assert pairs == [
        ["ts", "2026-04-24T12:34:56Z"],
        ["level", "info"],
        ["msg", "hello world"],
        ["user", "42"],
        ["flag", ""],
    ]


def test_round_trip_escapes():
    ns = _load()
    pairs = [["a", "x y"], ["b", "p=q"], ["c", 'say "hi"'], ["d", "back\\slash"], ["e", ""]]
    line = ns["encode"](pairs)
    assert line == 'a="x y" b="p=q" c="say \\"hi\\"" d=back\\slash e=""'
    assert ns["parse"](line) == pairs


def test_encode_map():
    ns = _load()
    assert ns["encode_map"]({"x": "1", "y": "a b"}) == 'x=1 y="a b"'
