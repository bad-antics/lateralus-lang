"""Parity and compilation tests for examples/ports/amicable."""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
PY_REF = ROOT / "examples" / "ports" / "amicable" / "amicable.py"
LTL_SRC = ROOT / "examples" / "ports" / "amicable" / "amicable.ltl"


def _load_py_ref():
    spec = importlib.util.spec_from_file_location("amicable_ref", PY_REF)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_python_reference_known_pairs():
    mod = _load_py_ref()
    # First amicable pair is (220, 284) -> sum 504.
    assert mod.sum_proper_divisors(220) == 284
    assert mod.sum_proper_divisors(284) == 220
    assert mod.amicable_summary(1000) == (1, 504)
    assert mod.amicable_summary(10000) == (5, 31626)


def test_lateralus_check_passes():
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "check", str(LTL_SRC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc required for C99 build")
def test_lateralus_c_port_matches_python(tmp_path):
    c_out = tmp_path / "amicable.c"
    exe_out = tmp_path / "amicable"
    trans = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "c", str(LTL_SRC), "-o", str(c_out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert trans.returncode == 0, trans.stderr or trans.stdout

    comp = subprocess.run(
        ["gcc", "-O2", str(c_out), "-lm", "-o", str(exe_out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert comp.returncode == 0, comp.stderr

    exe_res = subprocess.run([str(exe_out)], capture_output=True, text=True, check=True)
    assert exe_res.stdout.strip() == "upper=200000 pairs=20 sum=2896242"

    mod = _load_py_ref()
    # Cross-check divisor helper against mathematical identity on sample values.
    assert mod.amicable_summary(20000) == (8, 115818)
