"""
Regression test for examples/pool_tutorial.ltl (stdlib/pool tutorial companion).
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


def test_pool_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "pool_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB POOL TUTORIAL ===" in out
    assert "STEP 1 acquire -> 30 (LIFO: last available first)" in out
    assert "STEP 2 release(20) then acquire -> 20" in out
    assert "STEP 3 add conn-D at max -> avail=3 in_use=0 total=3 max=3 created=3 (rejected)" in out
    assert "STEP 4 acquire_many(5) -> [10, None, None, None, None]" in out
    assert "STEP 4 stats: avail=0 in_use=3 total=3 max=0 created=3 is_empty=True" in out
    assert "STEP 5 drain -> [30, 20, 10] then stats: avail=0 in_use=0 total=0 max=0 created=3" in out
    assert "STEP 6 shrink to 2 -> avail=2 created=4" in out
    assert "PINNED_VECTORS: lifo=30,20 reuse=20 max3_add4_rejected drain=30,20,10 shrink_avail=2" in out


def test_pool_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "pool_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
