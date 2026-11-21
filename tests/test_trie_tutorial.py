"""
tests/test_trie_tutorial.py - Tests for stdlib/trie.ltl
Verifies prefix search, exact matching, longest prefix matching, and insertion.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_trie_prefix_search_and_matching():
    trie_src = Path("stdlib/trie.ltl").read_text(encoding="utf-8")
    driver = """
let words = ["apple", "app", "application", "banana", "band"]
let t = from_words(words)

let app_candidates = keys_with_prefix(t, "app")
let ban_candidates = keys_with_prefix(t, "ban")
let missing = keys_with_prefix(t, "zoo")

let has_apple = has(t, "apple")
let has_appl = has(t, "appl")
let count_app = count_prefix(t, "app")
let longest_app = longest_prefix(t, "applications")
"""
    c = Compiler()
    res = c.compile_source(trie_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert sorted(ns["app_candidates"]) == ["app", "apple", "application"]
    assert sorted(ns["ban_candidates"]) == ["banana", "band"]
    assert ns["missing"] == []
    assert ns["has_apple"] is True
    assert ns["has_appl"] is False
    assert ns["count_app"] == 3
    assert ns["longest_app"] == "application"

def test_trie_incremental_insert_and_empty():
    trie_src = Path("stdlib/trie.ltl").read_text(encoding="utf-8")
    driver = """
let t = new()
let empty_check = is_empty(t)
insert(t, "route1", 100)
insert(t, "route2", 200)

let val1 = get(t, "route1")
let total_size = size(t)
"""
    c = Compiler()
    res = c.compile_source(trie_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["empty_check"] is True
    assert ns["val1"] == 100
    assert ns["total_size"] == 2
