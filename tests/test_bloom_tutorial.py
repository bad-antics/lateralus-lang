"""
Regression test for examples/bloom_tutorial.ltl.
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


def test_bloom_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "bloom_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB BLOOM TUTORIAL ===" in out
    assert "p1pct_n100=[900, 9]" in out
    assert "p01pct_n100=[1200, 12]" in out
    assert "n0=[9, 9]" in out
    assert "count=3" in out
    assert "apple=True" in out
    assert "durian=False" in out
    assert "fill_ppt=93.75" in out
    assert "union_xy=TrueTrueTrue" in out
    assert "inter_has_x=False" in out
    assert "inter_has_y=True" in out
    assert "mismatch=None" in out
    assert "PINNED_VECTORS" in out


def test_bloom_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "bloom_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
