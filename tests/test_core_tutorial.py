"""
Regression test for examples/core_tutorial.ltl (stdlib/core tutorial companion).
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


def test_core_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "core_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB CORE TUTORIAL ===" in out
    assert "abs(-3.5)=3.5 abs(2.5)=2.5" in out
    assert "clamp(-1,0,10)=0.0 clamp(99,0,10)=10.0" in out
    assert "min(3,7)=3.0 max(3,7)=7.0" in out
    assert "counter=3" in out
    assert "map twice=2,4,6,8,10" in out
    assert "filter even=2,4" in out
    assert "reduce add=15.0" in out
    assert "sum=15.0" in out
    assert "join=foo-bar-baz" in out
    assert "range(2,6)=2,3,4,5" in out
    assert "PINNED_VECTORS:" in out


def test_core_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "core_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
