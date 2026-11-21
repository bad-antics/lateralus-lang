"""
Regression test for examples/random_tutorial.ltl (stdlib/random tutorial companion).
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


def test_random_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "random_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB RANDOM TUTORIAL ===" in out
    assert "STEP 1 random() = 0.6394267984578837" in out
    assert "STEP 1 rand_int(1,10) x2 = 1, 5" in out
    assert "STEP 2 uniform(10,20) = 13.238327648331623" in out
    assert "STEP 2 uniform(-5,5) = -3.4915082607549808" in out
    assert "STEP 3 choice = blue" in out
    assert "STEP 3 choice(empty) = <empty>" in out
    assert "STEP 4 shuffle = [4,2,3,5,1] orig still = [1,2,3,4,5]" in out
    assert "STEP 5 sample([1..8],3) = [2,1,6]" in out
    assert "STEP 6 different seed -> rand_int(1,100) = 52" in out
    assert "PINNED_VECTORS: seed42_rand=0.6394267984578837 ints=1,5 uni=13.238327648331623,-3.4915082607549808 choice=blue sample=2,1,6 shuffle=4,2,3,5,1|1,2,3,4,5 seed99_1_100=52" in out


def test_random_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "random_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
