"""
Regression tests for stdlib/merkle.ltl.

`import hash` cannot resolve under the Python backend (stdlib imports
don't map to .ltl files), hash_fnv1a_64 was not an exported name,
char_at() is not a builtin, and `index / 2` produced a float index.
Now self-contained _fnv1a64 + slice() + idiv().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "merkle.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_build_root_and_hex():
    ns = _load()
    assert ns["to_hex64"](0) == "0000000000000000"
    assert ns["to_hex64"](255) == "00000000000000ff"
    t = ns["build_default"](["a", "b", "c", "d"])
    assert len(t["root"]) == 16
    assert t["root"] == ns["build_default"](["a", "b", "c", "d"])["root"]
    # order matters
    assert t["root"] != ns["build_default"](["a", "b", "c", "e"])["root"]


def test_inclusion_proofs_verify():
    ns = _load()
    items = ["a", "b", "c"]
    t = ns["build_default"](items)
    for i, leaf in enumerate(items):
        path = ns["proof"](t, i)
        assert ns["verify_default"](t["root"], leaf, path) is True
    # wrong leaf must fail
    path = ns["proof"](t, 0)
    assert ns["verify_default"](t["root"], "zzz", path) is False


def test_diff_leaves():
    ns = _load()
    a = ns["build_default"](["a", "b", "c"])
    b = ns["build_default"](["a", "x", "c"])
    assert ns["diff_leaves"](a, b) == [1]
    same = ns["build_default"](["a", "b"])
    assert ns["diff_leaves"](same, ns["build_default"](["a", "b", "c"])) == [2]
