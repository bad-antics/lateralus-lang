"""
Executable-specification regression tests.

Runs `lateralus verify tests/laws/stdlib_laws.ltl` and asserts every law
passes. This makes the @law feature part of CI — any future change that
violates a fundamental invariant (commutativity, associativity, De
Morgan, list reverse-involutive, etc.) will fail the test suite.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LAWS_FILE = REPO_ROOT / "tests" / "laws" / "stdlib_laws.ltl"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _run_verify(seed: int, trials: int = 100) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "lateralus_lang",
            "verify",
            str(LAWS_FILE),
            "--seed",
            str(seed),
            "--trials",
            str(trials),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


def test_stdlib_laws_file_exists():
    """Canonical law file must exist."""
    assert LAWS_FILE.exists(), f"missing: {LAWS_FILE}"


def test_stdlib_laws_pass_seed_42():
    """All 35 canonical stdlib laws pass with seed=42."""
    result = _run_verify(seed=42)
    assert result.returncode == 0, (
        f"`lateralus verify` exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "0 failed" in result.stdout, result.stdout
    assert "42 passed" in result.stdout, result.stdout
    # Boolean algebra laws auto-promote to exhaustive proofs
    assert "proved" in _strip_ansi(result.stdout).lower(), (
        f"expected at least one PROVED law, got:\n{result.stdout}"
    )


@pytest.mark.parametrize("seed", [0, 1, 7, 123, 9999])
def test_stdlib_laws_pass_multiple_seeds(seed: int):
    """Laws must hold under many different random seeds."""
    result = _run_verify(seed=seed, trials=50)
    assert result.returncode == 0, (
        f"seed={seed} failed\n"
        f"STDOUT:\n{result.stdout}"
    )
    assert "0 failed" in result.stdout, f"seed={seed}: {result.stdout}"


EXHAUSTIVE_ORACLE_FILE = REPO_ROOT / "tests" / "laws" / "exhaustive_and_oracle_laws.ltl"


def test_exhaustive_and_oracle_laws():
    """Verify the three novel law modes: auto-exhaustive, bounded-exhaustive, oracle."""
    assert EXHAUSTIVE_ORACLE_FILE.exists(), f"missing: {EXHAUSTIVE_ORACLE_FILE}"
    result = subprocess.run(
        [
            sys.executable, "-m", "lateralus_lang", "verify",
            str(EXHAUSTIVE_ORACLE_FILE), "--seed", "42",
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=60,
    )
    out = _strip_ansi(result.stdout)
    assert result.returncode == 0, out + result.stderr
    # All-bool laws are proved over 2^n cases
    assert "PROVED  and_commutative  (exhaustive: 4 cases)" in out
    assert "PROVED  de_morgan_1  (exhaustive: 4 cases)" in out
    # Bounded-int law: a, b ∈ [-5, 5] → 11² = 121 cases
    assert "PROVED  add_commutative_proved  (exhaustive: 121 cases)" in out
    # Bounded-int 3-arg: 9³ = 729 cases
    assert "PROVED  mul_distributes_over_add_proved  (exhaustive: 729 cases)" in out
    # Oracle (differential) law
    assert "fast_fact_matches_slow" in out
    assert "oracle" in out.lower()
    # Summary line shows both PROVED and oracle counts
    assert "5 proved" in out
    assert "1 oracle" in out
