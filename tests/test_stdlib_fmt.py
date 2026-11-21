"""
Tests for stdlib/fmt.ltl — center/hex/bin/oct integer division.

`/` transpiles to Python `/` (float). center's diff/2 produced a
float repeat count; hex/bin/oct looped `val = val / base` producing
floats → `chars[val % 16]` hit float list indexing TypeError and
the loop never terminated cleanly. All four divisions wrapped in
int(); vectors verified end-to-end in examples/fmt_tutorial.ltl
(PR #388).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FMT_LTL = REPO_ROOT / "stdlib" / "fmt.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_fmt_typechecks():
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(FMT_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr


def test_fmt_divisions_are_integer_cast():
    src = FMT_LTL.read_text()
    assert "let left = diff / 2" not in src
    assert "val = val / 16" not in src
    assert "val = val / 2\n" not in src
    assert "val = val / 8" not in src
    assert src.count("int(val /") == 3
    assert "int(diff / 2)" in src
