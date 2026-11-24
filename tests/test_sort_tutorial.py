"""
Regression test for examples/sort_tutorial.ltl (stdlib/sort tutorial companion).
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


def test_sort_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "sort_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB SORT TUTORIAL ===" in out
    assert "STEP 1: is_sorted(input) = false" in out
    assert "STEP 2: quicksort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in out
    assert "STEP 3: mergesort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in out
    assert "STEP 4: insertion_sort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in out
    assert "STEP 5: selection_sort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in out
    assert "STEP 6: is_sorted(quicksort) = true" in out
    assert "STEP 7: count_inversions(input) = 25" in out
    assert "STEP 8: binary_search(quicksort, 7) = 7" in out
    assert "STEP 8b: binary_search(quicksort, 42) = -1" in out
    assert "STEP 9: nsmallest(input, 3): [0, 1, 2]" in out
    assert "STEP 10: nlargest(input, 3): [7, 8, 9]" in out
    assert "STEP 11: words by length: [fig, pear, kiwi, plum, banana]" in out
    assert "PINNED_VECTORS: sorted=[0,1,2,3,4,5,6,7,8,9] inversions=25 binsearch_7=7 binsearch_42=-1" in out


def test_sort_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "sort_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
