"""
Regression test for examples/simhash_tutorial.ltl (stdlib/simhash tutorial companion).
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


def test_simhash_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "simhash_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB SIMHASH TUTORIAL ===" in out
    assert "f1=14607312263354641902" in out
    assert "deterministic=True" in out
    assert "h12=0" in out
    assert "h13=35" in out
    assert "sim12=1.0" in out
    assert "sim13=0.453125" in out
    assert "sim_self=1.0" in out
    assert "nd_punct=True" in out
    assert "nd_far=False" in out
    assert "dup_pair=0" in out
    assert "diff_pair=35" in out
    assert "PINNED_VECTORS: deterministic" in out


def test_simhash_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "simhash_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
