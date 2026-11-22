"""
Regression test for examples/stats_tutorial.ltl (stdlib/stats tutorial companion).
Asserts the executable tutorial runs cleanly and produces exact pinned vectors.
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


def test_stats_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "stats_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB STATS TUTORIAL ===" in out
    assert "STEP 1: mean(data) = 5.0" in out
    assert "STEP 2: median(data) = 4.5" in out
    assert "STEP 3: mode(data) = 4" in out
    assert "STEP 4: variance(data) [sample] = 4.571428571428571" in out
    assert "STEP 5: stddev(data) = 2.138089935299395" in out
    assert "STEP 6: range_val(data) = 7" in out
    assert "STEP 7: quartiles Q1/median/Q3 = 4.0 / 4.5 / 5.5" in out
    assert "STEP 8: iqr(data) = 1.5" in out
    assert "STEP 9: covariance(x,y) = 1.5" in out
    assert "STEP 10: correlation(x,y) = 0.7745966692414834" in out
    assert "STEP 11: linear_regression slope/intercept = 0.6 / 2.2" in out
    assert "PINNED_VECTORS: mean=5.0 median=4.5 mode=4 var=4.571428571428571 sd=2.138089935299395 range=7 q1=4.0 q3=5.5 iqr=1.5 cov=1.5 corr=0.7745966692414834 slope=0.6 intercept=2.2" in out


def test_stats_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "stats_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
