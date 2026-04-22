"""Tests for the characterize (inductive law generalization) pillar."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

from lateralus_lang.law_generalizer import (
    _rename_var,
    characterize_file,
    try_characterize,
)

# ─── Helpers ─────────────────────────────────────────────────────────────

def test_rename_var_respects_word_boundaries():
    assert _rename_var("x > 0", "x", "n") == "n > 0"
    assert _rename_var("x + y", "x", "a") == "a + y"
    # Only whole-word matches:
    assert _rename_var("xy + x", "x", "a") == "xy + a"


# ─── Direct Python function characterization ────────────────────────────

def test_characterize_gt_zero():
    def is_positive(x: int) -> bool:
        return x > 0
    c = try_characterize(is_positive, trials=80)
    assert c is not None
    assert c.expr == "x > 0"
    assert c.return_kind == "bool"


def test_characterize_eq_zero():
    def is_zero(x: int) -> bool:
        return x == 0
    c = try_characterize(is_zero, trials=80)
    assert c is not None
    assert c.expr == "x == 0"


def test_characterize_even():
    def is_even(x: int) -> bool:
        return x % 2 == 0
    c = try_characterize(is_even, trials=80)
    assert c is not None
    assert c.expr == "x % 2 == 0"


def test_characterize_add():
    def add(x: int, y: int) -> int:
        return x + y
    c = try_characterize(add, trials=80)
    assert c is not None
    assert c.expr == "x + y"


def test_characterize_max_two_args():
    def max2(x: int, y: int) -> int:
        return x if x > y else y
    c = try_characterize(max2, trials=80)
    # `max2(x, y)` isn't in our 2-arg catalog by that symbolic form, so
    # expect either no match or one of {x, y} (which won't hold over all).
    # The test guarantees we don't emit an incorrect characterization.
    if c is not None:
        # If a match is claimed, it must actually hold on a fresh sample.
        import random
        rng = random.Random(99)
        for _ in range(100):
            a = rng.randint(-30, 30)
            b = rng.randint(-30, 30)
            expected = a if a > b else b
            # Evaluate claimed expression via eval using x,y bindings
            got = eval(c.expr.replace("?", " if ").replace(":", " else "),
                       {"x": a, "y": b})  # not robust for ternary; skip if claim is ternary
            assert got == expected, f"characterization {c.expr!r} broke at ({a},{b})"


def test_characterize_identity():
    def ident(x: int) -> int:
        return x
    c = try_characterize(ident, trials=60)
    assert c is not None
    assert c.expr == "x"


def test_characterize_constant_bool():
    def always_true(x: int) -> bool:
        return True
    c = try_characterize(always_true, trials=50)
    assert c is not None
    # Prefer non-trivial if any match; but `true` is legal final match.
    assert c.expr == "true"


def test_characterize_non_characterizable_returns_none():
    """A function with no closed-form match in the catalogue returns None."""
    def weirdo(x: int) -> int:
        # Nothing in our catalog matches this:
        return x * x * x + 7
    c = try_characterize(weirdo, trials=60)
    assert c is None


def test_characterize_unsupported_arity_returns_none():
    def triplet(x: int, y: int, z: int) -> int:
        return x + y + z
    c = try_characterize(triplet, trials=30)
    assert c is None  # arity > 2 not supported


def test_characterization_emits_valid_ltl():
    """The generated @law snippet must compile as Lateralus source."""
    def is_positive(x: int) -> bool:
        return x > 0
    c = try_characterize(is_positive, trials=50)
    assert c is not None

    source = (
        "fn is_positive(x: int) -> bool {\n"
        "    return x > 0\n"
        "}\n\n"
        + c.as_ltl_law() + "\n"
    )
    from lateralus_lang.compiler import Compiler, Target
    result = Compiler().compile_source(source, target=Target.PYTHON, filename="t.ltl")
    assert result.ok, (
        f"characterization didn't parse:\n"
        f"{[e.message for e in result.errors]}"
    )


# ─── File-level driver ───────────────────────────────────────────────────

_DEMO_LTL = """\
fn is_positive(x: int) -> bool {
    return x > 0
}

fn double(x: int) -> int {
    return x + x
}
"""


def test_characterize_file_finds_both(tmp_path: Path):
    f = tmp_path / "demo.ltl"
    f.write_text(_DEMO_LTL)
    out = tmp_path / "chars.ltl"

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = characterize_file(f, trials=50, seed=42, output=str(out))
    output = buf.getvalue()

    assert rc == 0
    assert "is_positive" in output and "x > 0" in output
    assert "double" in output
    assert out.exists()
    content = out.read_text()
    assert "@law" in content
    assert content.count("_characterized") == 2


def test_characterize_file_zero_matches(tmp_path: Path):
    """Function with no pattern match → rc == 1, no output file written."""
    f = tmp_path / "hard.ltl"
    f.write_text(
        "fn weirdo(x: int) -> int {\n"
        "    return x * x * x + 7\n"
        "}\n"
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = characterize_file(f, trials=40, seed=42)
    assert rc == 1
    assert "no closed-form match" in buf.getvalue()
