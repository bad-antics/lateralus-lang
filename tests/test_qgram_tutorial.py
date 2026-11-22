"""
Regression test for examples/qgram_tutorial.ltl (stdlib/qgram tutorial companion).
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


def test_qgram_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "qgram_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB QGRAM TUTORIAL ===" in out
    assert "q2_hello=['\\x01h', 'he', 'el', 'll', 'lo', 'o\\x01']" in out
    assert "q0=[]" in out
    assert "ov_same=7" in out
    assert "ov_sim=2" in out
    assert "ov_far=0" in out
    assert "jac_same=1.0" in out
    assert "jac_sim=0.15384615384615385" in out
    assert "jac_far=0.0" in out
    assert "cat_grams=[0, 1]" in out
    assert "ranked=[[0, 3], [1, 2]]" in out
    assert "ranked_bark=[[2, 3]]" in out
    assert "ranked_none=[]" in out
    assert "PINNED_VECTORS: q2_hello_padded" in out


def test_qgram_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "qgram_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
