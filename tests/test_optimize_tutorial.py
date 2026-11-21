"""
Regression test for examples/optimize_tutorial.ltl (stdlib/optimize tutorial companion).
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


def test_optimize_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "optimize_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env(), timeout=120)
    out = res.stdout
    assert "=== LATERALUS STDLIB OPTIMIZE TUTORIAL ===" in out
    assert "bisect   = 1.4142135623733338" in out
    assert "newton   = 1.4142135623730951" in out
    assert "secant   = 1.4142135623730954" in out
    assert "trapezoid n=100  = 0.33335000000000004" in out
    assert "simpson  n=100  = 0.3333333333333334" in out
    assert "forward = 6.000009999951316" in out
    assert "central = 6.000000000039306" in out
    assert "second  = 2.000000000279556" in out
    assert "golden_section = 1.9999999999999998" in out
    assert "grad_descent x0=5 lr=0.1 steps=50 = 7.136238463529802e-05" in out
    assert "lerp(0,10,0.3) = 3.0" in out
    assert "bilinear center = 7.5" in out
    assert "lagrange x^2 at 1.5 = 2.25" in out
    assert "= 1.414213562373095" in out
    assert "PINNED_VECTORS: bisect=1.4142135623733338 newton=1.4142135623730951 secant=1.4142135623730954 trap=0.33335000000000004 simp=0.3333333333333334 fwd=6.000009999951316 cent=6.000000000039306 d2=2.000000000279556 golden=1.9999999999999998 gd=7.136238463529802e-05 lagrange=2.25 babylon=1.414213562373095" in out


def test_optimize_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "optimize_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
