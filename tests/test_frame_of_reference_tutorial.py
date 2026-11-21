"""
Regression test for examples/frame_of_reference_tutorial.ltl.
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


def test_for_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "frame_of_reference_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB FRAME-OF-REFERENCE TUTORIAL ===" in out
    assert "ref=100" in out
    assert "deltas=[0, 1, 5, 10, 15]" in out
    assert "bit_width=4" in out
    assert "roundtrip=True" in out
    assert "neg_rt=True" in out
    assert "dod_rt=True" in out
    assert "dec_55=[5]" in out
    assert "BUG_dod_55_lossy" in out


def test_for_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "frame_of_reference_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
