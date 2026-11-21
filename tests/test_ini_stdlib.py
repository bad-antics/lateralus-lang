"""
Regression tests for stdlib/ini.ltl.

split()/trim()/index_of()/substr()/starts_with()/ends_with() are not
runtime builtins — parse() and everything downstream raised NameError.
Now uses str_split()/str_trim()/_index_of()/slice()/
str_starts_with()/str_ends_with().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

INI = """; comment
[server]
host = example.com
port = 8080
debug = true
quoted = "hi there"

[db]
name = mydb
"""


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "ini.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_parse_sections_and_typed_getters():
    ns = _load()
    cfg = ns["parse"](INI)
    assert ns["sections"](cfg) == ["db", "default", "server"]
    assert ns["get"](cfg, "server", "host", "?") == "example.com"
    assert ns["get_int"](cfg, "server", "port", 0) == 8080
    assert ns["get_bool"](cfg, "server", "debug", False) is True
    assert ns["get_float"](cfg, "server", "port", 0.0) == 8080.0
    assert ns["get"](cfg, "server", "quoted", "?") == "hi there"
    assert ns["get"](cfg, "server", "missing", "DEF") == "DEF"


def test_queries_and_mutation():
    ns = _load()
    cfg = ns["parse"](INI)
    assert ns["has_key"](cfg, "server", "host") is True
    assert ns["has_key"](cfg, "server", "nope") is False
    assert ns["has_section"](cfg, "db") is True
    assert ns["section_keys"](cfg, "server") == ["debug", "host", "port", "quoted"]

    cfg2 = ns["set"](cfg, "server", "newkey", "v1")
    assert ns["get"](cfg2, "server", "newkey", "?") == "v1"
    cfg3 = ns["delete"](cfg2, "server", "newkey")
    assert ns["get"](cfg3, "server", "newkey", "GONE") == "GONE"


def test_merge_and_to_string():
    ns = _load()
    cfg = ns["parse"](INI)
    merged = ns["merge"](cfg, ns["parse"]("[server]\nextra = world\n"))
    assert ns["get"](merged, "server", "extra", "?") == "world"
    assert ns["get"](merged, "server", "host", "?") == "example.com"
    text = ns["to_string"](cfg)
    assert "[server]" in text and "host = example.com" in text
