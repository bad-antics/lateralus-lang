"""
Regression test for examples/heap_tutorial.ltl (stdlib/heap tutorial companion).
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


def test_heap_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "heap_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB HEAP TUTORIAL ===" in out
    assert "heap array=1,2,3,5,9,8" in out
    assert "peek=1 size=6" in out
    assert "pop order=1,2,3,5,8,9" in out
    assert "push_pop(5) -> popped=5 heap0=10" in out
    assert "push_pop(99) -> popped=10" in out
    assert "replace(1) -> old_min=4 new peek=1" in out
    assert "n_smallest(3)=1,7,13" in out
    assert "merged peek=1 size=4" in out
    assert "sort([9,4,7,1,3])=1,3,4,7,9" in out
    assert "PINNED_VECTORS:" in out


def test_heap_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "heap_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
