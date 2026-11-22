"""
Regression test for examples/tracing_tutorial.ltl (stdlib/tracing tutorial companion).
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


def test_tracing_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "tracing_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB TRACING TUTORIAL ===" in out
    assert "name=GET /users kind=server trace=7411411852151296301310 span=141185215129" in out
    assert "name=db.query kind=client trace=7411411852151296301310 span=5215129630 parent=141185215129" in out
    assert "same trace: True" in out and "parent link: True" in out
    assert "status=error events=1 attrs=1" in out
    assert "never_sample root sampled=False" in out
    assert "end_ok emits: <not sampled>" in out
    assert "child inherits sampled=False" in out
    assert "traceparent: 00-7411411852151296301310-141185215129-01" in out
    assert "parsed trace_id match: True" in out
    assert "bad header 'garbage' -> True" in out
    assert "PINNED_VECTORS: trace=7411411852151296301310 span=141185215129 child=5215129630 tp=00-7411411852151296301310-141185215129-01 roundtrip=true bad=nil sampled_child=false" in out


def test_tracing_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "tracing_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
