"""
Regression tests for stdlib/influx_line.ltl.

char_at()/index_of()/try_int() are not runtime builtins — every public
function raised NameError. Now uses slice()/_index_of()/_try_int().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "influx_line.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_field_formatters():
    ns = _load()
    assert ns["field_string"]("hello world") == '"hello world"'
    assert ns["field_string"]('a"b') == '"a\\"b"'
    assert ns["field_int"](42) == "42i"
    assert ns["field_float"]("1.5") == "1.5"
    assert ns["field_bool"](True) == "true"
    assert ns["field_bool"](False) == "false"


def test_line_and_parse_round_trip():
    ns = _load()
    line = ns["line"](
        "cpu",
        [["host", "web 01"], ["region", "us"]],
        [["usage", "12.5"], ["ok", "true"], ["note", '"hi, there"'], ["n", "7i"]],
        1234567890,
    )
    assert line == 'cpu,host=web\\ 01,region=us usage=12.5,ok=true,note="hi, there",n=7i 1234567890'
    m = ns["parse_line"](line)
    assert m["measurement"] == "cpu"
    assert m["tags"] == [["host", "web 01"], ["region", "us"]]
    assert m["fields"] == [["usage", "12.5"], ["ok", "true"], ["note", '"hi, there"'], ["n", "7i"]]
    assert m["timestamp"] == 1234567890


def test_parse_edge_cases():
    ns = _load()
    m = ns["parse_line"]("mem,host=a usage=50i 100")
    assert m["measurement"] == "mem"
    assert m["tags"] == [["host", "a"]]
    assert m["fields"] == [["usage", "50i"]]
    assert m["timestamp"] == 100
    assert ns["parse_line"]("justmeasurement") is None
    # no timestamp -> 0
    m2 = ns["parse_line"]("m f=1i")
    assert m2["timestamp"] == 0
