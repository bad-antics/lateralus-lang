"""
Regression test for examples/stack_tutorial.ltl (stdlib/stack tutorial companion).
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


def test_stack_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "stack_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB STACK TUTORIAL ===" in out
    assert "stack=a,b,c top=c" in out
    assert "pop -> c rest=a,b" in out
    assert "peek now=b" in out
    assert "from_list=[10,20,30] top=30" in out
    assert "contains 20=True contains 99=False" in out
    assert "swap_top 1,3,2" in out
    assert "dup [1,2] -> 1,2,2" in out
    assert "drop 2 of [1,2,3,4] -> 1,2" in out
    assert "fold([1,2,3,4], +) = 10" in out
    assert "fold(stack[5,6], init=100) = 111" in out
    assert "PINNED_VECTORS:" in out


def test_stack_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "stack_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
