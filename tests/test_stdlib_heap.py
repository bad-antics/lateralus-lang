"""
Tests for stdlib/heap.ltl — _parent integer-division fix.

`/` transpiles to Python `/` (float). _parent returned (i-1)/2 as a
float, which breaks list indexing with TypeError: list indices must
be integers. Fixed with int(). Runtime semantics verified end-to-end
in examples/heap_tutorial.ltl (PR #383) where the same int() form was
used: heap push/pop and heap_sort produced correct orderings.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEAP_LTL = REPO_ROOT / "stdlib" / "heap.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_heap_typechecks():
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(HEAP_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr


def test_parent_returns_integer_division():
    src = HEAP_LTL.read_text()
    assert "return (i - 1) / 2" not in src
    assert "return int((i - 1) / 2)" in src
