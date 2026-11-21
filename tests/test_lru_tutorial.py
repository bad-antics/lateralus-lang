"""
Regression test for examples/lru_tutorial.ltl (stdlib/lru tutorial companion).
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


def test_lru_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "lru_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LRU TUTORIAL ===" in out
    assert "keys=['a', 'b', 'c']" in out
    assert "keys_after_get=['b', 'c', 'a']" in out
    assert "keys=['c', 'a', 'd']" in out
    assert "has_b=False" in out
    assert "keys2=['a', 'd', 'e']" in out
    assert "hits=1" in out
    assert "misses=2" in out
    assert "hit_rate=0.3333333333333333" in out
    assert "keys_after_has=['a', 'd', 'e']" in out
    assert "after_resize=['e']" in out
    assert "empty=True" in out
    assert "stats_hits_kept=0" in out
    assert "keys=['z', 'w']" in out
    assert "get_x=None" in out
    assert "PINNED_VECTORS: cap3" in out


def test_lru_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "lru_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
