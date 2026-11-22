"""
Regression test for examples/fmt_tutorial.ltl (stdlib/fmt tutorial companion).
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


def test_fmt_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "fmt_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB FMT TUTORIAL ===" in out
    assert "Hello, world!" in out
    assert "1 + 2 = 3" in out
    assert "missing only args" in out
    assert "pad_left  -> [00042]" in out
    assert "pad_right -> [hi....]" in out
    assert "center    -> [----hi----]" in out
    assert "join      -> a, b, c" in out
    assert "repeat    -> ababab" in out
    assert "hex(255)=ff hex(255,upper)=FF" in out
    assert "hex(-255)=-ff hex(0)=0" in out
    assert "bin(42)=101010 oct(42)=52" in out
    assert "bin(-5)=-101" in out
    assert "Alice | 30" in out
    assert "PINNED_VECTORS:" in out


def test_fmt_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "fmt_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
