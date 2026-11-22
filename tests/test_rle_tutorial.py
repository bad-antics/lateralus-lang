"""
Regression test for examples/rle_tutorial.ltl (stdlib/run_length tutorial companion).
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


def test_rle_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "rle_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB RUN-LENGTH TUTORIAL ===" in out
    assert "pairs=4 -> 7,3 ..." in out
    assert "p0=[7,3] plast=[1,1]" in out
    assert "decode len=10 equal=True" in out
    assert "packed=[7,3,3,2,9,4,1,1]" in out
    assert "decode_packed equal=True" in out
    assert "empty pairs len=0" in out
    assert "alternating pairs=4 (worst case)" in out
    assert "alt round-trip=True" in out
    assert "800.0 per-mille" in out
    assert "1000.0 per-mille" in out
    assert "PINNED_VECTORS:" in out


def test_rle_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "rle_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
