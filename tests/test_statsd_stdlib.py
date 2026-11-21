"""
Regression tests for stdlib/statsd.ltl.

parse_line()/parse_tags_str() used index_of, split, and char_at — none
are runtime builtins — so parsing any metric line died with NameError.
Self-contained _index_of/_split helpers and slice() are used instead.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "statsd.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_metric_builders():
    ns = _load()
    assert ns["counter"]("http.requests", 10, "0.5", [["host", "api"]]) == \
        "http.requests:10|c|@0.5|#host:api"
    assert ns["gauge"]("temp", "21.5", [["unit", "c"]]) == \
        "temp:21.5|g|#unit:c"
    assert ns["timer"]("db.query", "12ms", "", []) == "db.query:12ms|ms"


def test_parse_line_roundtrip():
    ns = _load()
    line = ns["counter"]("http.requests", 10, "0.5",
                        [["host", "api"], ["dc", "us"]])
    m = ns["parse_line"](line)
    assert m["name"] == "http.requests"
    assert m["value"] == "10"
    assert m["kind"] == "c"
    assert m["rate"] == "0.5"
    assert m["tags"] == [["host", "api"], ["dc", "us"]]


def test_parse_line_malformed():
    ns = _load()
    assert ns["parse_line"]("no colon here") is None
    assert ns["parse_line"]("name:") is None  # missing |kind part
