"""
tests/test_issue_193_consistent_hash.py  -  Regression tests for Issue #193
Verifies that stdlib/consistent_hash.ltl and stdlib/merkle.ltl compile and execute
without float division index crashes or undefined hash_fnv1a_64 on the Python target.
"""
from pathlib import Path

from lateralus_lang.compiler import Compiler, Target


def test_consistent_hash_issue_193_reproduction():
    """Verify original reproduction from Issue #193 works cleanly."""
    ch = Path("stdlib/consistent_hash.ltl").read_text(encoding="utf-8")
    src = (
        ch.replace(
            "import hash",
            "fn hash_fnv1a_64(s: str) -> int { return len(s) * 2654435761 }\n"
            "fn fnv1a_64(s: str) -> int { return len(s) * 2654435761 }",
        )
        + '\nlet r = new_ring(3)\nadd_node(r, "n1")\nlet target = lookup(r, "k1")\nassert_eq(target, "n1")\n'
    )
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, f"Compilation failed: {r.errors}"
    scope = {}
    exec(r.python_src, scope)
    assert scope.get("target") == "n1"


def test_consistent_hash_full_ring_python_target():
    """Verify consistent_hash ring with binary search lookup and lookup_n on Python target."""
    h_src = Path("stdlib/hash.ltl").read_text(encoding="utf-8")
    ch_src = Path("stdlib/consistent_hash.ltl").read_text(encoding="utf-8")
    full_src = (
        h_src
        + "\n"
        + ch_src.replace("import hash", "")
        + """
let r = new_ring(3)
assert_eq(node_count(r), 0)
add_node(r, "node-1")
add_node(r, "node-2")
add_node(r, "node-3")
assert_eq(node_count(r), 3)

let t1 = lookup(r, "user-session-100")
assert_true(len(t1) > 0)

let multi = lookup_n(r, "user-session-100", 2)
assert_eq(len(multi), 2)
assert_ne(multi[0], multi[1])

remove_node(r, "node-1")
assert_eq(node_count(r), 2)
"""
    )
    r = Compiler().compile_source(full_src, target=Target.PYTHON)
    assert r.ok, f"Compilation failed: {r.errors}"
    exec(r.python_src, {})


def test_merkle_proof_integer_division_python_target():
    """Verify merkle tree proof generation with idiv and char_at works on Python target."""
    h_src = Path("stdlib/hash.ltl").read_text(encoding="utf-8")
    m_src = Path("stdlib/merkle.ltl").read_text(encoding="utf-8")
    full_src = (
        h_src
        + "\n"
        + m_src.replace("import hash", "")
        + """
let leaves = ["leaf1", "leaf2", "leaf3", "leaf4"]
let tree = build_default(leaves)
let root = tree["root"]
let p = proof(tree, 1)
assert_true(len(root) > 0)
assert_true(len(p) > 0)
let valid = verify_default(root, "leaf2", p)
assert_true(valid)
"""
    )
    r = Compiler().compile_source(full_src, target=Target.PYTHON)
    assert r.ok, f"Compilation failed: {r.errors}"
    exec(r.python_src, {})


def test_hash_fnv1a_64_alias():
    """Verify hash.ltl exports both fnv1a_64 and hash_fnv1a_64."""
    h_src = Path("stdlib/hash.ltl").read_text(encoding="utf-8")
    full_src = (
        h_src
        + """
let h1 = fnv1a_64("test-string")
let h2 = hash_fnv1a_64("test-string")
assert_eq(h1, h2)
"""
    )
    r = Compiler().compile_source(full_src, target=Target.PYTHON)
    assert r.ok, f"Compilation failed: {r.errors}"
    exec(r.python_src, {})
