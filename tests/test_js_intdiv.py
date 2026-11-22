"""
Tests for JavaScript backend integer division.

JS `/` is always true division; the VM's Op.DIV floors int/int.
The transpiler emitted bare `/` for BinOp and `/=` for AugAssign,
so `7 / 2` produced 3.5 in generated JS — breaking list indices and
bit ops. Both now route through __ltl.div mirroring VM semantics.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from lateralus_lang.codegen.javascript import JS_RUNTIME, transpile_to_js


def _js(src: str) -> str:
    return transpile_to_js(src)


def test_js_prelude_has_div_helper():
    assert "div: (a, b) =>" in JS_RUNTIME
    assert "Number.isInteger" in JS_RUNTIME
    assert "Math.floor" in JS_RUNTIME


def test_binop_div_routes_through_helper():
    js = _js("fn main() { let a = 7 / 2 }")
    assert "__ltl.div(7, 2)" in js


def test_augassign_div_routes_through_helper():
    js = _js("fn main() { let mut d = 20\n d /= 8 }")
    assert "d = __ltl.div(d, 8)" in js


def test_node_execution_floors_int_division():
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node not available")
    js = _js(
        "fn main() {\n"
        "  let a = 7 / 2\n"
        "  let mut d = 20\n"
        "  d /= 8\n"
        "  println(str(a) + \",\" + str(d))\n"
        "}\n"
        "main()\n")
    out = subprocess.run([node, "-e", js], capture_output=True,
                         text=True, timeout=10)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "3,2"
