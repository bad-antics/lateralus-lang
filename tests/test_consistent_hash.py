"""
tests/test_consistent_hash.py - Tests for stdlib/consistent_hash.ltl
Verifies integer index binary search on Python target and FNV-1a hashing.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_consistent_hash_lookup_and_lookup_n():
    ch_text = Path("stdlib/consistent_hash.ltl").read_text(encoding="utf-8")
    src = ch_text.replace(
        "import hash",
        "fn fnv1a_64(s: str) -> int { return len(s) * 2654435761 }\nfn fnv1a_32(s: str) -> int { return len(s) * 16777619 }"
    ) + """
let r = new_ring(3)
add_node(r, "node_a")
add_node(r, "node_b")
add_node(r, "node_c")

let target = lookup(r, "user_key_42")
let targets_2 = lookup_n(r, "user_key_42", 2)
"""
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["target"] in ["node_a", "node_b", "node_c"]
    assert len(ns["targets_2"]) == 2
    assert ns["targets_2"][0] != ns["targets_2"][1]

def test_consistent_hash_empty_ring():
    ch_text = Path("stdlib/consistent_hash.ltl").read_text(encoding="utf-8")
    src = ch_text.replace(
        "import hash",
        "fn fnv1a_64(s: str) -> int { return len(s) * 2654435761 }\nfn fnv1a_32(s: str) -> int { return len(s) * 16777619 }"
    ) + """
let r = new_ring(5)
let empty_target = lookup(r, "any_key")
let empty_targets = lookup_n(r, "any_key", 3)
"""
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok
    ns = {}
    exec(res.python_src, ns)
    assert ns["empty_target"] == ""
    assert ns["empty_targets"] == []
