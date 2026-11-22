"""
Regression test for examples/aho_corasick_tutorial.ltl.
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


def test_ac_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "aho_corasick_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB AHO-CORASICK TUTORIAL ===" in out
    assert "nodes=10" in out
    assert "hits=[[1, 4], [0, 4], [3, 6]]" in out
    assert "starts=[[1, 1], [0, 2], [3, 2]]" in out
    assert "nomatch=[]" in out
    assert "contains_yes=True" in out
    assert "abc_hits=[[0, 0], [1, 0], [3, 1], [5, 2]]" in out
    assert "single=[[0, 1], [0, 3]]" in out
    assert "empty_text=[]" in out
    assert "PINNED_VECTORS: usheers_ushers" in out


def test_ac_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "aho_corasick_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
