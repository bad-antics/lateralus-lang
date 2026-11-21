"""
Regression tests for stdlib/rope.ltl.

index() used the missing char_at() builtin — NameError on any random
access.  Uses slice() instead.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "rope.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_index_and_concat():
    ns = _load()
    r = ns["concat"](ns["from_str"]("ab"), ns["from_str"]("cd"))
    assert ns["to_str"](r) == "abcd"
    assert ns["index"](r, 0) == "a"
    assert ns["index"](r, 3) == "d"


def test_insert_delete_split():
    ns = _load()
    r = ns["from_str"]("hello world")
    r2 = ns["insert"](r, 5, " beautiful")
    assert ns["to_str"](r2) == "hello beautiful world"
    r3 = ns["delete"](r2, 0, 6)
    assert ns["to_str"](r3) == "beautiful world"
    parts = ns["split_at"](ns["from_str"]("hello world"), 5)
    assert ns["to_str"](parts[0]) == "hello"
    assert ns["to_str"](parts[1]) == " world"


def test_substr_and_rebalance():
    ns = _load()
    big = ns["from_str"]("x" * 200)
    assert ns["length"](big) == 200
    assert ns["substr"](big, 50, 60) == "x" * 10
    # concat parts back reproduces original
    parts = ns["split_at"](big, 100)
    assert ns["to_str"](ns["concat"](parts[0], parts[1])) == "x" * 200
