"""
Regression test for examples/queue_tutorial.ltl (stdlib/queue tutorial companion).
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


def test_queue_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "queue_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB QUEUE TUTORIAL ===" in out
    assert "q=['a', 'b', 'c']" in out
    assert "front=a" in out
    assert "pop_front=a rest=['b', 'c']" in out
    assert "pop3=c" in out
    assert "empty_now=True" in out
    assert "pop_empty_val=None" in out
    assert "after_push_front=[0, 1, 2, 3]" in out
    assert "pop_back=3 rest=[0, 1, 2]" in out
    assert "reversed=[6, 2, 9, 5, 1, 4, 1, 5]" in out
    assert "evens=[4, 2, 6]" in out
    assert "drained=[5, 1, 4] remaining=[1, 5, 9, 2, 6]" in out
    assert "str=Queue([1, 2, 3])" in out
    assert "PINNED_VECTORS: fifo_abc" in out


def test_queue_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "queue_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
