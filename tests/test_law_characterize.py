"""Tests for the characterize (inductive law generalization) pillar."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

from lateralus_lang.law_generalizer import (
    _rename_var,
    _substitute_vars,
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


def test_substitute_vars_simultaneous_no_aliasing():
    """Swapping or reusing template names must not alias x -> y -> k."""
    assert _substitute_vars("x - y", {"x": "y", "y": "x"}) == "y - x"
    assert _substitute_vars("x * y", {"x": "y", "y": "k"}) == "y * k"
    assert _substitute_vars("xy + x - y", {"x": "y", "y": "x"}) == "xy + y - x"


def test_as_ltl_law_preserves_swapped_yx_parameters():
    """Regression: 2-arg functions with first parameter `y` must not collapse
    `(x - y)` into `(x - x)` or `(k * k)` during sequential renaming."""
    def sub_yx(y: int, x: int) -> int:
        return y - x

    def scale_yk(y: int, k: int) -> int:
        return y * k

    c_sub = try_characterize(sub_yx, trials=60)
    assert c_sub is not None
    assert "return sub_yx(y, x) == (y - x)" in c_sub.as_ltl_law()

    c_scale = try_characterize(scale_yk, trials=60)
    assert c_scale is not None
    assert "return scale_yk(y, k) == (y * k)" in c_scale.as_ltl_law()


def test_characterize_then_verify_swapped_yx_roundtrip(tmp_path: Path):
    """End-to-end: `characterize_file` output for `(y, x)` / `(y, k)` / `(y, n)`
    must pass `verify_file` with zero counterexamples."""
    import os
    import subprocess
    import sys

    src_file = tmp_path / "swapped.ltl"
    src_file.write_text(
        "fn sub_yx(y: int, x: int) -> int {\n"
        "    return y - x\n"
        "}\n\n"
        "fn scale_yk(y: int, k: int) -> int {\n"
        "    return y * k\n"
        "}\n\n"
        "fn gt_yn(y: int, n: int) -> bool {\n"
        "    return y > n\n"
        "}\n",
        encoding="utf-8",
    )
    laws_file = tmp_path / "laws.ltl"
    with contextlib.redirect_stdout(io.StringIO()):
        rc = characterize_file(src_file, trials=60, seed=42, output=str(laws_file))
    assert rc == 0

    combined = tmp_path / "combined.ltl"
    combined.write_text(
        src_file.read_text(encoding="utf-8") + "\n" + laws_file.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    repo_root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "verify", str(combined), "--seed", "42"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "3 passed  0 failed" in proc.stdout

