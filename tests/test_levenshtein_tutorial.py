"""
Regression test for examples/levenshtein_tutorial.ltl (stdlib/levenshtein tutorial companion).
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


def test_levenshtein_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "levenshtein_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LEVENSHTEIN TUTORIAL ===" in out
    assert "kitten->sitting = 3" in out
    assert "flaw->lawn      = 2" in out
    assert "abc->abd        = 1" in out
    assert "''->abc         = 3" in out
    assert "kitten/sitting k=2 -> 3" in out
    assert "kitten/sitting k=3 -> 3" in out
    assert "abc/xyz k=1     -> 2" in out
    assert "len-diff>k      -> 3" in out
    assert "0.5714285714285714" in out
    assert "lev ca->abc     = 3" in out
    assert "damerau ca->abc = 3" in out
    assert "damerau ab->ba  = 1" in out
    assert "PINNED_VECTORS:" in out


def test_levenshtein_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "levenshtein_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
