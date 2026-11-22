"""Behaviour checks against the unmodified stdlib, not a Python substitute."""
from pathlib import Path
import runpy
from lateralus_lang.parser import parse
from lateralus_lang.codegen.python import transpile_to_python

ROOT = Path(__file__).resolve().parents[1]


def module_functions():
    source = (ROOT / "stdlib/deque.ltl").read_text(encoding="utf-8")
    namespace = {}
    exec(compile(transpile_to_python(parse(source)), "<actual-deque>", "exec"), namespace)
    return namespace


def test_deque_tutorial_pinned_output():
    runner = runpy.run_path(str(ROOT / "scripts/run_deque_tutorial.py"))
    assert len(runner["verify"]().splitlines()) == 10


def test_empty_pops_and_out_of_range_access():
    d = module_functions()
    assert d["pop_front"]([]) == [None, []]
    assert d["pop_back"]([]) == [None, []]
    assert d["at"]([20, 30], -1) is None
    assert d["at"]([20, 30], 2) is None


def test_rotation_wrap_and_inverse():
    d = module_functions()
    original = [10, 20, 30, 40]
    assert d["rotate_left"](original, 5) == [20, 30, 40, 10]
    assert d["rotate_right"](original, 5) == [40, 10, 20, 30]
    assert d["rotate_right"](d["rotate_left"](original, 5), 5) == original
    assert d["rotate_left"]([], 5) == []
    assert d["rotate_right"]([], 5) == []


def test_returned_queue_must_be_reassigned():
    d = module_functions()
    original = [20, 30]
    after = d["push_front"](original, 10)
    assert original == [20, 30]
    assert after == [10, 20, 30]
    value, remaining = d["pop_front"](after)
    assert value == 10
    assert remaining == original


def test_zero_rotation_and_clear():
    d = module_functions()
    assert d["rotate_right"]([10, 20], 0) == [10, 20]
    assert d["clear"]([10, 20]) == []
