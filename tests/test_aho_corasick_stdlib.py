"""
Regression tests for stdlib/aho_corasick.ltl.

build/find_all/contains_any used char_at() at all three scan sites —
not a runtime builtin — so any scan died with NameError.  slice() is
used instead.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "aho_corasick.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


PATS = ["he", "she", "his", "hers"]


def test_find_all_ushers():
    ns = _load()
    auto = ns["build"](PATS)
    assert ns["find_all"](auto, "ushers") == [[1, 4], [0, 4], [3, 6]]
    assert ns["find_all_starts"](auto, "ushers") == [[1, 1], [0, 2], [3, 2]]


def test_contains_any():
    ns = _load()
    auto = ns["build"](PATS)
    assert ns["contains_any"](auto, "xxhishxx") is True
    assert ns["contains_any"](auto, "nothing") is False
    assert ns["contains_any"](auto, "nothing here") is True  # "he" inside "here"
    assert ns["contains_any"](auto, "aaaa") is False


def test_overlapping_patterns():
    ns = _load()
    auto = ns["build"](["a", "ab", "bab", "bc", "bca", "c", "caa"])
    assert ns["find_all_starts"](auto, "abc") == [[0, 0], [1, 0], [3, 1], [5, 2]]
