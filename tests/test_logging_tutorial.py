"""
Regression test for examples/logging_tutorial.ltl (stdlib/logging tutorial companion).
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


def test_logging_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "logging_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LOGGING TUTORIAL ===" in out
    assert "[api] [INFO] info msg - shown" in out
    assert "[api] [WARN] warn msg - shown" in out
    assert "[api] [ERROR] error msg - shown" in out
    assert "trace msg - suppressed" not in out
    assert "debug msg - suppressed" not in out
    assert "[api] [INFO] request handled method=GET status=200 ms=42" in out
    assert "[api] [WARN] slow query table=users rows=9000" in out
    assert "[api] [INFO] cache hit" in out
    assert "cache miss - suppressed" not in out
    assert "[api] [FATAL] Assertion failed: index out of range" in out
    assert "[api] [DEBUG] now visible at DEBUG" in out
    assert "still hidden at TRACE" not in out
    assert "info suppressed again" not in out
    assert "[api] [ERROR] only errors now" in out
    assert "PINNED_VECTORS: gate=info+warn+error prefix=[api] ctx=method=GET+status=200+ms=42 assert=Assertion+failed debug_at_1=shown trace_at_1=hidden" in out


def test_logging_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "logging_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
