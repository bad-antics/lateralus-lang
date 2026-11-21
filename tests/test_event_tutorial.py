"""
Regression test for examples/event_tutorial.ltl (stdlib/event tutorial companion).
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


def test_event_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "event_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB EVENT TUTORIAL ===" in out
    assert "names=['user.login', 'order.placed']" in out
    assert "login_handlers=3" in out
    assert "total=4" in out
    assert "has_listeners=True" in out
    assert "missing_count=0" in out
    assert "log1=['login:alice', 'audit:alice', 'welcome:alice']" in out
    assert "log2=['login:bob', 'audit:bob']" in out
    assert "login_handlers_after_once=2" in out
    assert "before=2" in out
    assert "after_off=1" in out
    assert "after_off_all=0" in out
    assert "filtered_names=['alpha', 'alphabet']" in out
    assert "dst_got=dst:hello" in out
    assert "names_after_reset=[]" in out
    assert "total_after_reset=0" in out
    assert "PINNED_VECTORS: login3 total4 once_fires_once" in out


def test_event_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "event_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
