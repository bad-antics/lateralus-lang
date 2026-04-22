"""Tests for the v3.2 mutation tester (`lateralus verify --mutate`)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEMO = REPO / "tests" / "laws" / "mutation_demo.ltl"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip(s: str) -> str:
    return _ANSI.sub("", s)


@pytest.fixture(scope="module")
def demo_exists():
    assert DEMO.exists(), f"missing demo file: {DEMO}"
    return DEMO


# ────────────────────────────────────────────────────────────────────
# Unit tests for the mutator internals
# ────────────────────────────────────────────────────────────────────

def test_extract_user_fns_ignores_laws():
    from lateralus_lang.law_mutator import _extract_user_fns
    src = """
fn add(a: int, b: int) -> int { return a + b }
@law
fn add_commutative(a: int, b: int) -> bool {
    return add(a, b) == add(b, a)
}
// fn commented_out() {}
"""
    assert _extract_user_fns(src) == {"add"}


def test_generate_mutants_restricts_to_user_fns():
    from lateralus_lang.law_mutator import generate_mutants
    py = """
def preamble_fn():
    return 1 + 2
def user_fn(x):
    return x + 1
"""
    all_mut = generate_mutants(py)
    scoped = generate_mutants(py, user_fns={"user_fn"})
    assert len(scoped) < len(all_mut)
    assert all(m.line_no >= 4 for m in scoped)  # all mutants in user_fn body


def test_mutator_catches_obvious_bug_via_demo(demo_exists):
    """Sanity: at minimum, mutating `+` in `add` is caught by commutativity."""
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_mutator import (
        _extract_user_fns,
        _run_python,
        apply_mutant,
        generate_mutants,
    )
    from lateralus_lang.law_runner import emit_runner_tail
    src = demo_exists.read_text()
    result = Compiler().compile_source(
        src, target=Target.PYTHON, filename=demo_exists.name
    )
    assert result.ok
    user_fns = _extract_user_fns(src)
    full = result.python_src + "\n" + emit_runner_tail(trials=30, seed=42)
    mutants = generate_mutants(full, user_fns=user_fns)
    assert mutants, "no mutants generated"
    # Find at least one + → - mutant targeting the `add` function
    plus_to_minus = [m for m in mutants if m.rule_name == "+  →  -"]
    assert plus_to_minus, "expected a + → - mutant"
    # Apply and run — should be caught (non-zero exit)
    mutated = apply_mutant(full, plus_to_minus[0], user_fns=user_fns)
    assert mutated != full
    code, _out = _run_python(mutated, timeout=15.0)
    assert code != 0, "addition-breaking mutant should be caught by laws"


# ────────────────────────────────────────────────────────────────────
# End-to-end: `lateralus verify --mutate` CLI
# ────────────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_cli_mutate_reports_score(demo_exists):
    env_python = sys.executable
    proc = subprocess.run(
        [env_python, "-m", "lateralus_lang", "verify",
         str(demo_exists), "--mutate", "--seed", "42"],
        capture_output=True, text=True, timeout=300, cwd=str(REPO),
    )
    out = _strip(proc.stdout)
    # Must contain the mutation score banner
    assert "Mutation score:" in out
    # Must classify the demo's spec quality (≥ 80%)
    m = re.search(r"Mutation score:\s+(\d+\.\d+)%", out)
    assert m, f"no score parsed from:\n{out}"
    score = float(m.group(1))
    assert score >= 80.0, f"demo spec should be strong, got {score}%"
    # Must report exactly 5 user functions
    assert "User functions:  5" in out


def test_mutation_report_score_property():
    from lateralus_lang.law_mutator import Mutant, MutationReport
    r = MutationReport(total=10, caught=8)
    assert r.score == 0.8
    r2 = MutationReport(total=5, caught=3,
                        equivalents=[Mutant("x", "x", "y", 0, 1, "")])
    # 3 caught out of (5 - 1 equiv) = 4 testable
    assert r2.score == 0.75
    r3 = MutationReport(total=0)
    assert r3.score == 1.0
