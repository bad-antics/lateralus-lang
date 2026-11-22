"""
Regression test for examples/math_tutorial.ltl (stdlib/math tutorial companion).
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


def test_math_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "math_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB MATH TUTORIAL ===" in out
    assert "hypot=5.0" in out
    assert "gcd=6" in out
    assert "lcm=12.0" in out
    assert "is_prime97=True" in out
    assert "isqrt99=9" in out
    assert "fib10=55" in out
    assert "fact5=120" in out
    assert "sqrt2=1.414213562373095" in out
    assert "sqrt99=9.9498743710662" in out
    assert "sin_pi/2=1.0" in out
    assert "ln_e=0.9999999999999255" in out
    assert "log2_8=3.0" in out
    assert "PINNED_VECTORS: hypot5" in out


def test_math_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "math_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
