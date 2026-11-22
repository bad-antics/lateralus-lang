"""
Regression test for examples/time_tutorial.ltl.
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
    env["TZ"] = "UTC"  # localtime() output is pinned to UTC for vectors
    return env


def test_time_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "time_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB TIME TUTORIAL ===" in out
    assert "iso=2023-11-14T22:13:20" in out
    assert "date=2023-11-14" in out
    assert "now_positive=True" in out
    assert "loop_acc=4999950000" in out
    assert "elapsed_ms_positive=True" in out
    assert "deadline=2023-11-14T23:13:20" in out


def test_time_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "time_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
