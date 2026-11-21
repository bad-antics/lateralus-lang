"""
Tests for stdlib/strings.ltl — str_reverse fix.

str_reverse used split(s, "") which maps to Python's s.split("") and
raises ValueError: empty separator under the runtime shim. Fixed by
building the char list with slice() — semantics verified end-to-end
in examples/strings_tutorial.ltl (PR #378).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STR_LTL = REPO_ROOT / "stdlib" / "strings.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_strings_typechecks():
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(STR_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr


def test_str_reverse_avoids_empty_separator_split():
    src = STR_LTL.read_text()
    assert 'split(s, "")' not in src
    assert "slice(s, i, i + 1)" in src
