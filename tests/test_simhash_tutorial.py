"""
Regression test for examples/simhash_tutorial.ltl and stdlib/simhash.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned vectors.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_simhash_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "simhash_tutorial.ltl"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    stdout = res.stdout

    assert "=== LATERALUS STDLIB SIMHASH TUTORIAL ===" in stdout
    assert "STEP 1: Document Tokenization" in stdout
    assert "doc_a tokens count: 9" in stdout
    assert "STEP 2: Computing 64-bit Locality-Sensitive Fingerprints" in stdout
    assert "fp_a = 14607312263354641902" in stdout
    assert "fp_b = 14607312263354641902" in stdout
    assert "fp_c = 14912431120926964047" in stdout
    assert "fp_d = 10207751738674989474" in stdout
    assert "STEP 3: Pairwise Hamming Distances & Cosine Similarities" in stdout
    assert "Hamming Distance: 0 bits" in stdout
    assert "Hamming Distance: 11 bits" in stdout
    assert "Hamming Distance: 28 bits" in stdout
    assert "Near-Duplicate: True" in stdout
    assert "PINNED_VECTORS: exact_dist=0 near_dist=11 far_dist=28" in stdout


def test_simhash_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "simhash_tutorial.ltl"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "OK" in res.stdout


def test_simhash_invariants():
    # Mathematical invariant check: identity, symmetry, triangle bounds
    def hamming(a: int, b: int) -> int:
        return bin(a ^ b).count("1")

    fp_a = 14607312263354641902
    fp_b = 14607312263354641902
    fp_c = 14912431120926964047
    fp_d = 10207751738674989474

    # Identity
    assert hamming(fp_a, fp_a) == 0
    assert hamming(fp_a, fp_b) == 0

    # Symmetry
    assert hamming(fp_a, fp_c) == hamming(fp_c, fp_a) == 11
    assert hamming(fp_a, fp_d) == hamming(fp_d, fp_a) == 28

    # Triangle inequality: d(A, D) <= d(A, C) + d(C, D)
    d_ac = hamming(fp_a, fp_c)
    d_cd = hamming(fp_c, fp_d)
    d_ad = hamming(fp_a, fp_d)
    assert d_ad <= d_ac + d_cd


if __name__ == "__main__":
    test_simhash_tutorial_execution()
    test_simhash_tutorial_typecheck()
    test_simhash_invariants()
    print("PASS: 3/3 tests passed successfully")
