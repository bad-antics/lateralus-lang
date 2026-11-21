"""
Regression test for examples/linalg_tutorial.ltl (stdlib/linalg tutorial companion).
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


def test_linalg_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "linalg_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LINALG TUTORIAL ===" in out
    assert "STEP 1 add=[5.0, 7.0, 9.0] sub=[3.0, 3.0, 3.0]" in out
    assert "STEP 2 dot=32.0" in out
    assert "STEP 2 cross i^j=[0.0, 0.0, 1.0]" in out
    assert "STEP 3 |v|=5.0 normalized=[0.6000000000000001, 0.8]" in out
    assert "STEP 3 angle i,j=1.5707963267948966" in out
    assert "STEP 3 proj [3,4] onto [1,0]=[3.0, 0.0]" in out
    assert "STEP 4 A+B=[6.0, 8.0] ; [10.0, 12.0]" in out
    assert "STEP 4 A*B=[19.0, 22.0] ; [43.0, 50.0]" in out
    assert "STEP 4 trace(A)=5.0 det2(A)=-2.0" in out
    assert "STEP 5 det3(diag 2,3,4)=24.0" in out
    assert "STEP 6 solve [[3,1],[1,2]] x = [9,8] -> [2.0, 3.0]" in out
    assert "PINNED_VECTORS: dot=32.0 cross=0.0,0.0,1.0 mag=5.0 norm=0.6000000000000001,0.8 angle=1.5707963267948966 proj=3.0,0.0 det2=-2.0 det3=24.0 sol=2.0,3.0" in out


def test_linalg_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "linalg_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
