"""
Regression test for examples/set_tutorial.ltl (stdlib/set tutorial companion).
Asserts the executable tutorial runs cleanly and produces exact pinned vectors.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_set_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "set_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB SET TUTORIAL ===" in out
    assert "A = from_list([4,1,3,2,2,4]): [1, 2, 3, 4]" in out
    assert "B = from_list([6,3,5,4]): [3, 4, 5, 6]" in out
    assert "STEP 2: add(A, 9): [1, 2, 3, 4, 9]" in out
    assert "STEP 3: union(A,B): [1, 2, 3, 4, 5, 6]" in out
    assert "STEP 4: intersection(A,B): [3, 4]" in out
    assert "STEP 5: difference(A,B): [1, 2]" in out
    assert "STEP 6: symmetric_difference(A,B): [1, 2, 5, 6]" in out
    assert "STEP 7: is_subset([1,2],A) = true" in out
    assert "STEP 7b: is_subset(B,A) = false" in out
    assert "STEP 8: is_disjoint(A,[7,8]) = true" in out
    assert "STEP 8b: is_disjoint(A,B) = false" in out
    assert "STEP 9: equals(from_list([4,3,2,1]),A) = true" in out
    assert "STEP 10: map_set(A, x*10): [10, 20, 30, 40]" in out
    assert "STEP 11: filter_set(A, even): [2, 4]" in out
    assert "STEP 12: power_set([1,2]) has 4 subsets" in out
    assert "  subset 3: [1, 2]" in out
    assert "PINNED_VECTORS: A=[1,2,3,4] union=[1,2,3,4,5,6] inter=[3,4] diff=[1,2] symdiff=[1,2,5,6] powerset_size=4" in out


def test_set_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "set_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
