"""Verify the stdlib/bitset.ltl integer-division fix, tutorial example, and multi-word set invariants."""
import subprocess
import sys
from pathlib import Path
import pytest
from lateralus_lang.compiler import Compiler, Target

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def bitset():
    src = (ROOT / "stdlib/bitset.ltl").read_text(encoding="utf-8")
    res = Compiler().compile_source(src, target=Target.PYTHON)
    assert res.ok, res.errors
    ns = {"__name__": "bitset_tutorial_test"}
    exec(res.python_src, ns)
    return ns

def test_rbac_example_matches_pinned_vector():
    res = subprocess.run([sys.executable, "scripts/run_bitset_tutorial.py"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    assert res.stdout == (ROOT / "examples/bitset_rbac.expected.txt").read_text(encoding="utf-8")

def test_multiword_set_clear_toggle_and_bounds(bitset):
    bs = bitset["from_list"](64, [0, 31, 32, 63])
    assert bitset["to_list"](bs) == [0, 31, 32, 63]
    assert bitset["count"](bs) == 4
    bs = bitset["set"](bs, -1)
    bs = bitset["set"](bs, 64)
    assert bitset["test"](bs, 64) is False
    bs = bitset["toggle"](bs, 31)
    assert bitset["to_list"](bs) == [0, 32, 63]
    bs = bitset["clear"](bs, 32)
    assert bitset["to_list"](bs) == [0, 63]

def test_set_algebra_across_word_boundary(bitset):
    a = bitset["from_list"](64, [1, 33, 50])
    b = bitset["from_list"](64, [33, 60])
    assert bitset["to_list"](bitset["union"](a, b)) == [1, 33, 50, 60]
    assert bitset["to_list"](bitset["intersection"](a, b)) == [33]
    assert bitset["to_list"](bitset["difference"](a, b)) == [1, 50]
    assert bitset["to_list"](bitset["symmetric_difference"](a, b)) == [1, 50, 60]
    assert bitset["is_subset"](bitset["intersection"](a, b), a) is True
