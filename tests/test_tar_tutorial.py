"""
Regression test for examples/tar_tutorial.ltl (stdlib/tar tutorial companion).
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


def test_tar_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "tar_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB TAR TUTORIAL ===" in out
    assert "archive bytes=3072" in out
    assert "hdr[0:32] hex=68656c6c6f2e747874" in out
    assert "magic@257=ustar" in out
    assert "entries=3" in out
    assert "e1 name=hello.txt size=6 mode(oct)=420 mtime=1700000000" in out
    assert "e1 bytes=hi tar" in out
    assert "e2 name=docs/ type=5" in out
    assert "e3 name=latest type=2 link=hello.txt" in out
    assert "total=3072" in out
    assert "PINNED_VECTORS: entries=3" in out


def test_tar_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "tar_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
