"""
Regression test for examples/datetime_tutorial.ltl (stdlib/datetime tutorial companion).
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


def test_datetime_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "datetime_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB DATETIME TUTORIAL ===" in out
    assert "is_leap 2024=True 1900=False 2000=True" in out
    assert "days_in_month(2023,2)=28 (2024,2)=29" in out
    assert "day_of_year(2024,3,1)=61" in out
    assert "2024-01-01 = Monday" in out
    assert "2024-12-25 = Wednesday" in out
    assert "2000-01-01 = Saturday" in out
    assert "datetime=2024-01-01T09:30:00Z" in out
    assert "2024-01-31 +1 = 2024-02-01" in out
    assert "2024-12-31 +1 = 2025-01-01" in out
    assert "2024-03-01 -1 = 2024-02-29" in out
    assert "diff_days(2024-01-01 -> 2024-12-31)=365" in out
    assert "PINNED_VECTORS:" in out


def test_datetime_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "datetime_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
