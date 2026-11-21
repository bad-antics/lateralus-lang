"""
tests/test_suffix_array_tutorial.py - Tests for stdlib/suffix_array.ltl
Verifies canonical "banana" suffix array and LCP vectors, empty strings, and repeated characters.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_suffix_array_banana_vectors():
    sa_src = Path("stdlib/suffix_array.ltl").read_text(encoding="utf-8")
    driver = """
let word = "banana"
let sa = build(word)
let l = lcp(word, sa)
let rep = longest_repeated(word)
let pos_ana = search(word, sa, "ana")
let pos_ban = search(word, sa, "ban")
let pos_none = search(word, sa, "xyz")
"""
    c = Compiler()
    res = c.compile_source(sa_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["sa"] == [5, 3, 1, 0, 4, 2]
    assert ns["l"] == [0, 1, 3, 0, 0, 2]
    assert ns["rep"] == "ana"
    assert ns["pos_ana"] in [1, 3]
    assert ns["pos_ban"] == 0
    assert ns["pos_none"] == -1

def test_suffix_array_edge_cases():
    sa_src = Path("stdlib/suffix_array.ltl").read_text(encoding="utf-8")
    driver = """
let empty_sa = build("")
let empty_lcp = lcp("", empty_sa)
let empty_rep = longest_repeated("")

let rep_sa = build("aaaa")
let rep_lcp = lcp("aaaa", rep_sa)
let rep_str = longest_repeated("aaaa")
"""
    c = Compiler()
    res = c.compile_source(sa_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["empty_sa"] == []
    assert ns["empty_lcp"] == []
    assert ns["empty_rep"] == ""
    assert ns["rep_sa"] == [3, 2, 1, 0]
    assert ns["rep_lcp"] == [0, 1, 2, 3]
    assert ns["rep_str"] == "aaa"
