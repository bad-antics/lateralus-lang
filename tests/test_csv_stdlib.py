"""
Regression tests for stdlib/csv.ltl.

split()/trim()/has_key()/replace() are not runtime builtins — parse,
parse_dict, and generate_dict all raised NameError. Now uses
str_split()/str_trim()/map_has()/str_replace().
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "csv.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_parse_matches_python_csv():
    ns = _load()
    text = 'a,"b,c"\n"x""y",z\nplain,1\n'
    assert ns["parse"](text, ",") == list(csv.reader(io.StringIO(text)))


def test_parse_dict_and_generate_dict():
    ns = _load()
    rows = ns["parse_dict"]("name,age\nAlice,30\nBob,25\n", ",")
    assert rows == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
    out = ns["generate_dict"]([{"x": "1", "y": "2"}], ["x", "y"], ",")
    assert out == "x,y\n1,2\n"
    # missing key -> empty field
    assert ns["generate_dict"]([{"x": "1"}], ["x", "y"], ",") == "x,y\n1,\n"


def test_generate_round_trip_with_quoting():
    ns = _load()
    rows = [["a", "b,c", 'x"y'], ["1", "2", "3"]]
    out = ns["generate"](rows, ",")
    assert out == 'a,"b,c","x""y"\n1,2,3\n'
    assert ns["parse"](out, ",") == rows
    # custom delimiter round-trips quoted delimiter inside field
    assert ns["parse"](ns["generate"]([["a;b", "c"]], ";"), ";") == [["a;b", "c"]]
