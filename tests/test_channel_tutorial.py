"""
Regression test for examples/channel_tutorial.ltl (stdlib/channel tutorial companion).
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


def test_channel_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "channel_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB CHANNEL TUTORIAL ===" in out
    assert "pending=2 recv=task-1" in out
    assert "counters send=2 recv=2" in out
    assert "c(full)=False" in out
    assert "is_full=True pending=2" in out
    assert "recv=a send c now=True" in out
    assert "closed send=False (rejected)" in out
    assert "drain after close=2 items" in out
    assert "unbuffered try_send=True" in out
    assert "select picks first-ready: from-A" in out
    assert "PINNED_VECTORS:" in out


def test_channel_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "channel_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
