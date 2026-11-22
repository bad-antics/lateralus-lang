"""
Regression tests for stdlib/roaring.ltl.

union()/to_list() called try_int(), which is not a runtime builtin —
both crashed with NameError on multi-container bitmaps.  Keys are
canonical int-strings by construction, so to_int() is used instead.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "roaring.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_add_has_cardinality():
    ns = _load()
    b = ns["new_bitmap"]()
    for v in [1, 5, 70000, 5]:
        b = ns["add"](b, v)
    assert ns["has"](b, 1) is True
    assert ns["has"](b, 70000) is True
    assert ns["has"](b, 2) is False
    assert ns["cardinality"](b) == 3  # 5 deduplicated


def test_union_and_to_list_multicontainer():
    ns = _load()
    a = ns["new_bitmap"]()
    for v in [1, 5, 70000]:
        a = ns["add"](a, v)
    b = ns["new_bitmap"]()
    for v in [9, 70000, 100000]:
        b = ns["add"](b, v)
    u = ns["union"](a, b)
    assert ns["cardinality"](u) == 5
    assert ns["to_list"](u) == sorted(ns["to_list"](u))
    assert set(ns["to_list"](u)) == {1, 5, 9, 70000, 100000}


def test_to_list_single_container():
    ns = _load()
    b = ns["new_bitmap"]()
    for v in [3, 1, 2]:
        b = ns["add"](b, v)
    assert ns["to_list"](b) == [1, 2, 3]
