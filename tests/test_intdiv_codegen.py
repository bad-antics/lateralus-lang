"""
Tests for Python codegen integer division.

The VM's Op.DIV already does `a // b` for int/int and `a / b`
otherwise, but the Python transpiler emitted bare `/` for both BinOp
and AugAssign `/=`, so `7 / 2` produced 3.5 under `ltlc run` —
breaking list indices, bit ops, and loop counters across stdlib.
Fixed by routing both through _ltl_div which mirrors VM semantics.
"""
from __future__ import annotations

import contextlib
import io

from lateralus_lang import Compiler, Target


def run_ltl(src: str) -> str:
    r = Compiler().compile_source(src, target=Target.PYTHON, filename="<test>")
    assert r.ok, f"Compile failed: {r.errors}"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(r.python_src, {"__builtins__": __builtins__})
    return buf.getvalue()


def test_int_int_division_floors():
    out = run_ltl("fn main() { println(str(7 / 2)) }")
    assert out.strip() == "3"


def test_float_division_unchanged():
    out = run_ltl("fn main() { println(str(7.0 / 2)) }")
    assert out.strip() == "3.5"


def test_mixed_division_is_true_division():
    out = run_ltl("fn main() { println(str(7 / 2.0)) }")
    assert out.strip() == "3.5"


def test_augassign_division_floors():
    out = run_ltl("fn main() { let mut d = 20\n d /= 8\n println(str(d)) }")
    assert out.strip() == "2"


def test_division_result_usable_as_index():
    out = run_ltl(
        "fn main() { let a = [10, 20, 30]\n println(str(a[5 / 2])) }")
    assert out.strip() == "30"
