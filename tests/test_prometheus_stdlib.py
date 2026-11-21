"""
Regression tests for stdlib/prometheus.ltl.

char_at()/index_of()/split() are not runtime builtins — every public
function raised NameError. Now uses slice()/_index_of()/str_split().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "prometheus.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_emitters():
    ns = _load()
    assert ns["help_line"]("http_requests", "Total requests") == "# HELP http_requests Total requests\n"
    assert ns["type_line"]("http_requests", "counter") == "# TYPE http_requests counter\n"
    assert ns["sample_line"]("m", [["a", "1"]], "5") == 'm{a="1"} 5\n'
    assert ns["format_labels"]([["l", 'a"b\\c']]) == '{l="a\\"b\\\\c"}'
    samples = [ [[["loc", "us"]], "1.5"], [[], "2.0"] ]
    block = ns["metric_block"]("temp", "Temperature", "gauge", samples)
    assert 'temp{loc="us"} 1.5\n' in block and "temp 2.0\n" in block


def test_histogram_block():
    ns = _load()
    out = ns["histogram_block"]("lat", "Latency", [["handler", "api"]], [["0.1", "3"], ["+Inf", "5"]], "12.5", "5")
    assert 'lat_bucket{handler="api",le="0.1"} 3\n' in out
    assert 'lat_bucket{handler="api",le="+Inf"} 5\n' in out
    assert 'lat_sum{handler="api"} 12.5\n' in out
    assert 'lat_count{handler="api"} 5\n' in out
    assert "# TYPE lat histogram\n" in out


def test_parse_line_and_exposition():
    ns = _load()
    m = ns["parse_line"]('http_requests_total{method="GET",code="200"} 1027 1395066363000')
    assert m["metric"] == "http_requests_total"
    assert m["labels"] == [["method", "GET"], ["code", "200"]]
    assert m["value"] == "1027"
    assert ns["parse_line"]("# HELP x y") is None
    assert ns["parse_line"]("") is None
    doc = '# HELP x y\n# TYPE x counter\nhttp_requests_total{method="GET"} 5\n\nnode_cpu 0.5\n'
    rows = ns["parse_exposition"](doc)
    assert rows == [
        {"metric": "http_requests_total", "labels": [["method", "GET"]], "value": "5"},
        {"metric": "node_cpu", "labels": [], "value": "0.5"},
    ]
