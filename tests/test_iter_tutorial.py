"""
Regression test for examples/iter_tutorial.ltl (stdlib/iter tutorial companion).
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


def test_iter_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "iter_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB ITER TUTORIAL ===" in out
    assert "range_iter(1,6) => [1, 2, 3, 4, 5]" in out
    assert "range_step(9,0,-3) => [9, 6, 3]" in out
    assert "1..10 map*2 filter%4==0 => [4, 8, 12, 16, 20]" in out
    assert "flat_map squares => [1, 2, 4, 5, 9, 10]" in out
    assert "zip(1..4, 10..13) => [[1, 10], [2, 11], [3, 12]]" in out
    assert "unique => [3, 1, 2]" in out
    assert "chunks(1..7,3) => [[1, 2, 3], [4, 5, 6], [7]]" in out
    assert "windows(1..5,3) => [[1, 2, 3], [2, 3, 4], [3, 4, 5]]" in out
    assert "sum(1..10) => 55" in out
    assert "product(1..5) => 120" in out
    assert "fold concat => abc" in out
    assert "find even>6 => {'_tag': 'Some', 'value': 8, 'is_some': True}" in out
    assert "position first odd>7 => 8" in out
    assert "for_each sum of squares => 14" in out
    assert "to_map squares => {1: 1, 2: 4, 3: 9}" in out
    assert ("PINNED_VECTORS: sum_1_10=55 prod_1_5=120 chunks_1_7_s3=3 "
            "windows_1_5_s3=3 unique_3313213=3 zip_min=2") in out


def test_iter_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "iter_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
