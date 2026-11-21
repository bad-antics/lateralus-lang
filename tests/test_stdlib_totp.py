"""
Tests for stdlib/totp.ltl — TOTP counter/_u64_be integer division.

`/` transpiles to Python `/` (float). `now / step_s` produced a float
counter fed into _u64_be, whose `n / (1 << (i*8)) & 255` then raised
TypeError (float & int). All divisions wrapped in int(); RFC 6238
vectors verified end-to-end in examples/totp_tutorial.ltl (PR #372).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOTP_LTL = REPO_ROOT / "stdlib" / "totp.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_totp_typechecks():
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(TOTP_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr


def test_totp_divisions_are_integer_cast():
    src = TOTP_LTL.read_text()
    assert "let counter = now / step_s" not in src
    assert "b[7 - i] = (n /" not in src
    assert src.count("int(now / step_s)") == 2
    assert "int(n / (1 << (i * 8))) & 255" in src
