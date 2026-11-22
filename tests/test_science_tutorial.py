"""
Regression test for examples/science_tutorial.ltl (stdlib/science tutorial companion).
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


def test_science_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "science_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB SCIENCE TUTORIAL ===" in out
    assert "c2f_100=212.0" in out
    assert "f2c_32=0.0" in out
    assert "c2k_0=273.15" in out
    assert "m2ft_1=3.28084" in out
    assert "j2ev_1.6e-19=1.0" in out
    assert "mass_energy_1kg=8.987551787368176e+16" in out
    assert "photon_1hz=6.62607015e-34" in out
    assert "orbit_v_earth=7909.680821529872" in out
    assert "escape_v_earth=11185.97789184991" in out
    assert "gas_p=101388.19036190625" in out
    assert "bb_peak_sun=5.015181645898235e-07" in out
    assert "PINNED_VECTORS: c2f212" in out


def test_science_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "science_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
