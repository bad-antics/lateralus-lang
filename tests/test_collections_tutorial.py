"""
Regression test for examples/collections_tutorial.ltl (stdlib/collections tutorial companion).
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


def test_collections_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "collections_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB COLLECTIONS TUTORIAL ===" in out
    assert "head=5 last=2" in out
    assert "take2=5,3 drop2=8,1,9,2" in out
    assert "prepend=0,5,3,8,1,9,2" in out
    assert "contains 8=True index_of 9=4" in out
    assert "count even=2" in out
    assert "flat_map double=1,2,2,4,3,6" in out
    assert "11,22,33" in out
    assert "chunk3=[5, 3, 8],[1, 9, 2]" in out
    assert "interleave=1,2,3,4,5" in out
    assert "yes=8,2 no=5,3,1,9" in out
    assert 'even=2,4,6 odd=1,3,5' in out
    assert "sum=28.0 product=24.0 max=9 min=1" in out
    assert "PINNED_VECTORS:" in out


def test_collections_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "collections_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
