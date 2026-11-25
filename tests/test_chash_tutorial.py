"""
Regression test for examples/chash_tutorial.ltl (stdlib/consistent_hash tutorial companion).
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


def test_chash_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "chash_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB CONSISTENT-HASH TUTORIAL ===" in out
    assert "points=12 nodes=cache-1,web-1,db-2" in out
    assert "sess-0000-x -> db-2" in out
    assert "sess-0004-x -> cache-1" in out
    assert "sess-0010-x -> web-1" in out
    assert "user:1 -> web-1" in out
    assert "user:1 -> web-1,cache-1,db-2" in out
    assert "keys on web-1 before: 37/100" in out
    assert "keys still on web-1: 0 (expect 0)" in out
    assert "user:1 owner was web-1 now cache-1" in out
    assert "PINNED_VECTORS:" in out


def test_chash_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "chash_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
