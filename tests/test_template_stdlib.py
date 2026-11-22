"""
Regression tests for stdlib/template.ltl.

trim()/replace() are not runtime builtins — render/render_default/
extract_vars/render_safe raised NameError. Now uses
str_trim()/str_replace(). (The `import strings` is unused — no
qualified calls — so it was left in place.)
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "template.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_render_and_default():
    ns = _load()
    assert ns["render"]("Hello <<name>>! You are <<age>>.", {"name": "World", "age": 30}) == "Hello World! You are 30."
    # missing var left as-is
    assert ns["render"]("Hi <<x>>", {}) == "Hi <<x>>"
    assert ns["render_default"]("Hi <<x>>", {}, "DEF") == "Hi DEF"
    # whitespace inside delimiters is trimmed
    assert ns["render"]("<< name >>", {"name": "ok"}) == "ok"


def test_compile_extract_vars():
    ns = _load()
    assert ns["render_template"](ns["compile"]("A <<v>> B"), {"v": "!"}) == "A ! B"
    assert ns["extract_vars"]("<<a>> x <<b>> <<a>>") == ["a", "b"]
    assert ns["extract_vars"]("no vars") == []


def test_list_rendering():
    ns = _load()
    assert ns["render_each"]("<<item>>;", ["a", "b"], "item") == "a;b;"
    assert ns["render_join"]("<<n>>", ["x", "y"], "n", "|") == "x|y"
    assert ns["render_numbered"]("<<i>>:<<v>>", ["a", "b"], "v", "i") == "1:a\n2:b"


def test_escape_and_safe():
    ns = _load()
    assert ns["escape_html"]('<b>&"x"</b>') == "&lt;b&gt;&amp;\"x\"&lt;/b&gt;"
    assert ns["render_safe"]("<<v>>", {"v": "<i>"}) == "&lt;i&gt;"
