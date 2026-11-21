"""
Regression test for examples/run_length_tutorial.ltl (stdlib/run_length tutorial companion).
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


def test_run_length_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "run_length_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB RUN_LENGTH TUTORIAL ===" in out
    assert "pairs=[[1, 3], [2, 2], [3, 4]]" in out
    assert "empty=[]" in out
    assert "single=[[7, 1]]" in out
    assert "roundtrip=True" in out
    assert "packed=[1,3,2,2,3,4]" in out
    assert "packed_roundtrip=True" in out
    assert "odd_tail_ignored=[5,5]" in out
    assert "orig10_pairs3=600.0" in out
    assert "orig9_pairs4=888.8888888888889" in out
    assert "orig0=1000" in out
    assert "orig8_pairs1=250.0" in out
    assert "pairs=[[0, 4], [1, 2], [0, 6]]" in out
    assert "ratio=500.0" in out
    assert "PINNED_VECTORS: pairs=[[1,3],[2,2],[3,4]]" in out


def test_run_length_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "run_length_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
