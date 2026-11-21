"""
Regression test for examples/io_tutorial.ltl (stdlib/io tutorial companion).
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


def test_io_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "io_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB IO TUTORIAL ===" in out
    assert "-> 3 lines" in out
    assert "trailing newline -> 2 lines" in out
    assert "app.log -> app.log" in out
    assert "x.bin" in out
    assert "('/var/log','app.log') -> /var/log/app.log" in out
    assert "upstream('/var/log/app.log') = [/var/log/app.log]" in out
    assert "fixed   ('/var/log/app.log') = [/var/log]" in out
    assert "fixed   ('plain.txt')        = [.]" in out
    assert "upstream('app.log') = [app.log]" in out
    assert "fixed   ('app.log') = [.log]" in out
    assert "fixed   ('x.tar.gz')= [.gz]" in out
    assert "PINNED_VECTORS:" in out


def test_io_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "io_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
