"""
Regression test for examples/arena_tutorial.ltl (stdlib/arena tutorial companion).
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


def test_arena_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "arena_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB ARENA TUTORIAL ===" in out
    assert "STEP 1 ids: 0,1,2 (capacity 3 fills block 0)" in out
    assert "STEP 1 4th alloc -> id 3 (spills to block 1)" in out
    assert "STEP 2 after set: get(id2) = BETA" in out
    assert "STEP 3 alloc_many ids = [4,5,6] total=7" in out
    assert "STEP 3 to_list = [alpha, BETA, gamma, delta, x, y, z]" in out
    assert "STEP 4 stats: total=7 blocks=3 cap=9 remaining=2 usage=0.7777777777777778" in out
    assert "STEP 5 after reset: total=0 blocks=1 get(old id1)=None" in out
    assert "PINNED_VECTORS: ids=0,1,2,3 spill=block1 set=BETA many=4,5,6 total=7 blocks=3 usage=0.7777777777777778 reset_total=0" in out


def test_arena_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "arena_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
