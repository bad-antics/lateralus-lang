"""
Regression test for examples/rope_tutorial.ltl (stdlib/rope tutorial companion).
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


def test_rope_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "rope_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB ROPE TUTORIAL ===" in out
    assert "len=16" in out
    assert "str=hello rope world" in out
    assert "idx4=o" in out
    assert "idx6=r" in out
    assert "substr(6,11)=rope " in out
    assert "left=hello " in out
    assert "right=rope world" in out
    assert "str=hello fast rope world" in out
    assert "str=fast rope world" in out
    assert "len=288" in out
    assert "roundtrip=True" in out
    assert "PINNED_VECTORS: hello_rope_world len16" in out


def test_rope_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "rope_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
