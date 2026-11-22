"""
Regression test for examples/strings_tutorial.ltl (stdlib/strings tutorial companion).
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


def test_strings_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "strings_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB STRINGS TUTORIAL ===" in out
    assert "trim=[Hello, Lateralus!]" in out
    assert "index_of 'brown'=10" in out
    assert "count 'o'=2" in out
    assert "join='|' -> alpha|beta|gamma|delta" in out
    assert "repeat ab x3 = ababab" in out
    assert "pad_left 7 -> 00007" in out
    assert "reversed = sularetal" in out
    assert "'12a' digits=False" in out
    assert "format_int(42,6) = 000042" in out
    assert "PINNED_VECTORS:" in out


def test_strings_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "strings_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
