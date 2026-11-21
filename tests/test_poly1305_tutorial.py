"""
Regression test for examples/poly1305_tutorial.ltl (stdlib/poly1305 tutorial companion).
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


def test_poly1305_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "poly1305_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env(), timeout=180)
    out = res.stdout
    assert "=== LATERALUS STDLIB POLY1305 TUTORIAL ===" in out
    assert "a8061dc1305136c6c22b8baf0c0127a9" in out
    assert "1020e8c25c2d34db3d2154327530594a" in out
    assert "00000000000000000000000000000000" in out
    assert "verify(good)=True verify(bad)=False" in out
    assert "PINNED_VECTORS: v1=a8061dc1305136c6c22b8baf0c0127a9 v2=1020e8c25c2d34db3d2154327530594a empty=00000000000000000000000000000000 verify=true/false" in out


def test_poly1305_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "poly1305_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
