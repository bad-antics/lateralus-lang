"""
Regression test for examples/filepath_tutorial.ltl (stdlib/filepath tutorial companion).
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


def test_filepath_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "filepath_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB FILEPATH TUTORIAL ===" in out
    assert "dirname=/home/user" in out
    assert "dirname_rel=." in out
    assert "basename=file.txt" in out
    assert "ext=.gz" in out
    assert "ext_none=" in out
    assert "stem=archive.tar" in out
    assert "join=/home/user/file.txt" in out
    assert "join2=a/b/c" in out
    assert "norm1=/a/c/d" in out
    assert "norm2=c" in out
    assert "norm3=../x/y" in out
    assert "abs=True" in out
    assert "has_ext=True" in out
    assert "with_ext=/a/b/file.py" in out
    assert "with_ext_rel=file.py" in out
    assert "PINNED_VECTORS: dirname_home" in out


def test_filepath_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "filepath_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
