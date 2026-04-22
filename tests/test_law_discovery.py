"""Tests for v3.2 automatic law discovery (`lateralus discover`)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip(s: str) -> str:
    return _ANSI.sub("", s)


@pytest.fixture
def demo_src(tmp_path):
    p = tmp_path / "demo.ltl"
    p.write_text(
        "fn add(a: int, b: int) -> int { return a + b }\n"
        "fn mul(a: int, b: int) -> int { return a * b }\n"
        "fn negate(x: int) -> int { return -x }\n"
        "fn abs_val(x: int) -> int { if x < 0 { return -x } return x }\n"
        "fn max2(a: int, b: int) -> int { if a > b { return a } return b }\n"
    )
    return p


# ────────────────────────────────────────────────────────────────────
# Unit tests
# ────────────────────────────────────────────────────────────────────

def test_discovers_commutativity_of_add(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("add", "commutative") in kinds
    assert ("mul", "commutative") in kinds


def test_discovers_associativity(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("add", "associative") in kinds
    assert ("mul", "associative") in kinds
    assert ("max2", "associative") in kinds


def test_discovers_identity_constants(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    # add has 0 as two-sided identity
    assert ("add", "identity_left_0") in kinds
    assert ("add", "identity_right_0") in kinds
    # mul has 1 as two-sided identity and 0 as absorber
    assert ("mul", "identity_left_1") in kinds
    assert ("mul", "absorb_0_left") in kinds
    assert ("mul", "absorb_0_right") in kinds


def test_discovers_involutive_and_odd_for_negate(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("negate", "involutive") in kinds
    assert ("negate", "odd") in kinds


def test_discovers_unary_idempotence_for_abs(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("abs_val", "idempotent_unary") in kinds


def test_discovers_binary_idempotence_for_max(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("max2", "idempotent_binary") in kinds


def test_discovers_distributivity(demo_src):
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(demo_src, trials=40, seed=42, verbose=False)
    # mul distributes over add
    assert any(l.pattern == "distributive" and l.fn_name == "mul" and l.co_fn == "add"
               for l in rep.laws)


def test_rejects_trivially_identity_function(tmp_path):
    """A function that just returns its input should NOT be flagged as
    idempotent (would be trivially so for every function f where f=id)."""
    p = tmp_path / "id_fn.ltl"
    p.write_text("fn id_int(x: int) -> int { return x }\n")
    from lateralus_lang.law_discovery import discover_laws
    rep = discover_laws(p, trials=40, seed=42, verbose=False)
    kinds = {(l.fn_name, l.pattern) for l in rep.laws}
    assert ("id_int", "idempotent_unary") not in kinds


# ────────────────────────────────────────────────────────────────────
# Round-trip: discovered source is valid and verifies
# ────────────────────────────────────────────────────────────────────

def test_roundtrip_discover_then_verify(demo_src, tmp_path):
    out_laws = tmp_path / "laws.ltl"
    combined = tmp_path / "combined.ltl"

    r = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "discover",
         str(demo_src), "--seed", "42", "-o", str(out_laws)],
        capture_output=True, text=True, timeout=60, cwd=str(REPO),
    )
    assert r.returncode == 0, _strip(r.stdout + r.stderr)
    assert out_laws.exists()

    combined.write_text(demo_src.read_text() + "\n" + out_laws.read_text())

    v = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "verify",
         str(combined), "--seed", "99"],   # different seed!
        capture_output=True, text=True, timeout=60, cwd=str(REPO),
    )
    out = _strip(v.stdout)
    assert v.returncode == 0, out
    assert "0 failed" in out
    # Must have discovered at least 10 laws
    m = re.search(r"(\d+) passed", out)
    assert m and int(m.group(1)) >= 10


# ────────────────────────────────────────────────────────────────────
# CLI smoke test
# ────────────────────────────────────────────────────────────────────

def test_cli_discover_reports_count(demo_src):
    r = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "discover",
         str(demo_src), "--seed", "42"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO),
    )
    out = _strip(r.stdout)
    assert r.returncode == 0, out
    assert "Discovered" in out
    m = re.search(r"Discovered (\d+) law", out)
    assert m, out
    assert int(m.group(1)) >= 10
