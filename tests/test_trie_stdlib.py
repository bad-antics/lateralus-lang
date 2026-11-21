"""
Regression tests for stdlib/trie.ltl.

substr() is not a runtime builtin — insert/get/has_prefix/keys_with_prefix/
longest_prefix all raised NameError. Now uses slice().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PAIRS = [["apple", 1], ["app", 2], ["banana", 3], ["band", 4]]


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "trie.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_insert_get_has():
    ns = _load()
    t = ns["from_pairs"](PAIRS)
    assert ns["get"](t, "apple") == 1
    assert ns["get"](t, "app") == 2
    assert ns["get"](t, "xyz") is None
    assert ns["has"](t, "banana") is True
    assert ns["has"](t, "ban") is False  # prefix only, not a key


def test_prefix_queries():
    ns = _load()
    t = ns["from_pairs"](PAIRS)
    assert ns["has_prefix"](t, "app") is True
    assert ns["has_prefix"](t, "ban") is True
    assert ns["has_prefix"](t, "z") is False
    assert sorted(ns["keys_with_prefix"](t, "ap")) == ["app", "apple"]
    assert ns["count_prefix"](t, "ba") == 2
    assert ns["longest_prefix"](t, "bandana") == "band"


def test_all_keys_size_from_words():
    ns = _load()
    t = ns["from_pairs"](PAIRS)
    assert sorted(ns["all_keys"](t)) == ["app", "apple", "banana", "band"]
    assert ns["size"](t) == 4
    w = ns["from_words"](["he", "she", "his", "hers"])
    assert ns["size"](w) == 4
    assert sorted(ns["keys_with_prefix"](w, "he")) == ["he", "hers"]
