"""
Regression test for examples/functional_tutorial.ltl (stdlib/functional tutorial companion).
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


def test_functional_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "functional_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB FUNCTIONAL TUTORIAL ===" in out
    assert "compose(dbl,inc)(5) => 12" in out
    assert "pipe [inc,dbl,inc](5) => 13" in out
    assert "flip(sub)(3,10) => 7" in out
    assert "curry2(add)(5)(3) => 8" in out
    assert "partial(add,10)(7) => 17" in out
    assert "flat_map squares => [1, 4, 9]" in out
    assert "scan +1 from 0 => [0, 1, 3, 6, 10]" in out
    assert "zip_with add => [11, 22, 33]" in out
    assert "zip_with short => [11, 22]" in out
    assert "take_while <4 => [1, 2, 3]" in out
    assert "drop_while <3 => [3, 4, 5]" in out
    assert "find first even => 2" in out
    assert "count_by even => 2" in out
    assert "group_by parity => {'1': [1, 3, 5], '0': [2, 4]}" in out
    assert "partition even -> [yes,no] => [[2, 4], [1, 3, 5]]" in out
    assert "frequencies => {'a': 3, 'b': 2, 'c': 1}" in out
    assert "for_each sum via map => 10" in out
    assert ("PINNED_VECTORS: compose=12 pipe=13 zipmin=33 group_n=2 "
            "freq_a=3 scan=[0,1,3,6,10]") in out


def test_functional_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "functional_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
