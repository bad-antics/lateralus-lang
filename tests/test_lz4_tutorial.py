"""
Regression test for examples/lz4_tutorial.ltl (stdlib/lz4 tutorial companion).
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


def test_lz4_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "lz4_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LZ4 TUTORIAL ===" in out
    assert "in=2B compressed=206869" in out
    assert "round-trip=True" in out
    assert "in=900B -> out=60B" in out
    assert "ratio=15x" in out
    assert "f01074686520717569636b2062726f776e20666f78206a756d7073206f766572201f00916c617a7920646f672e0e000f" in out
    assert "in=200B -> out=202B" in out
    assert "300 x 'A': 300B -> 12B" in out
    assert "PINNED_VECTORS: tiny=206869" in out


def test_lz4_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "lz4_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
