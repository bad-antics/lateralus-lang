"""
Regression test for examples/dict_encoding_tutorial.ltl (stdlib/dict_encoding tutorial companion).
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


def test_dict_encoding_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "dict_encoding_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB DICT_ENCODING TUTORIAL ===" in out
    assert "STEP 1 dict: red,green,blue,yellow" in out
    assert "STEP 2 indices: 0,1,0,2,1,0,3,2" in out
    assert "STEP 3 cardinality = 4" in out
    assert "STEP 4 bit_width = 2" in out
    assert "STEP 5 round-trip equal: True" in out
    assert "STEP 6 int dict: 10,20,30" in out
    assert "STEP 8 single card=1 width=1" in out
    assert "STEP 9 empty card=0 indices=[]" in out
    assert "PINNED_VECTORS: dict=red,green,blue,yellow idx=0,1,0,2,1,0,3,2 card=4 width=2 rt=true nums=10,20,30 nidx=0,1,0,2,1,0 single=1/1" in out


def test_dict_encoding_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "dict_encoding_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
