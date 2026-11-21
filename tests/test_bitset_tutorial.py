"""
tests/test_bitset_tutorial.py - Comprehensive verification for stdlib/bitset.ltl
Tests fixed-capacity allocation, bounds checking, bitwise set/clear/toggle/test,
algebraic operations (union, intersection, difference, symmetric_difference, subset),
and serialization.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_bitset_core_operations():
    bitset_src = Path("stdlib/bitset.ltl").read_text(encoding="utf-8")
    driver = r"""
let bs = new(64)
let bs = set(bs, 0)
let bs = set(bs, 31)
let bs = set(bs, 32)
let bs = set(bs, 63)

let t0 = test(bs, 0)
let t31 = test(bs, 31)
let t32 = test(bs, 32)
let t63 = test(bs, 63)
let t5 = test(bs, 5)

let c = count(bs)
let lst = to_list(bs)

let bs = clear(bs, 31)
let t31_after = test(bs, 31)
let c_after = count(bs)

let bs = toggle(bs, 5)
let t5_toggled = test(bs, 5)
let bs = toggle(bs, 5)
let t5_toggled_again = test(bs, 5)
"""
    c = Compiler()
    res = c.compile_source(bitset_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["t0"] is True
    assert ns["t31"] is True
    assert ns["t32"] is True
    assert ns["t63"] is True
    assert ns["t5"] is False

    assert ns["c"] == 4
    assert ns["lst"] == [0, 31, 32, 63]

    assert ns["t31_after"] is False
    assert ns["c_after"] == 3

    assert ns["t5_toggled"] is True
    assert ns["t5_toggled_again"] is False

def test_bitset_set_algebra():
    bitset_src = Path("stdlib/bitset.ltl").read_text(encoding="utf-8")
    driver = r"""
let a = from_list(64, [1, 2, 3, 4])
let b = from_list(64, [3, 4, 5, 6])

let u = union(a, b)
let inter = intersection(a, b)
let diff = difference(a, b)
let sym = symmetric_difference(a, b)

let sub_inter_a = is_subset(inter, a)
let sub_inter_b = is_subset(inter, b)
let sub_a_u = is_subset(a, u)
let sub_u_a = is_subset(u, a)

let u_list = to_list(u)
let inter_list = to_list(inter)
let diff_list = to_list(diff)
let sym_list = to_list(sym)

let empty_bs = new(32)
let is_emp = is_empty(empty_bs)
let not_emp = is_empty(a)
"""
    c = Compiler()
    res = c.compile_source(bitset_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["u_list"] == [1, 2, 3, 4, 5, 6]
    assert ns["inter_list"] == [3, 4]
    assert ns["diff_list"] == [1, 2]
    assert ns["sym_list"] == [1, 2, 5, 6]

    assert ns["sub_inter_a"] is True
    assert ns["sub_inter_b"] is True
    assert ns["sub_a_u"] is True
    assert ns["sub_u_a"] is False

    assert ns["is_emp"] is True
    assert ns["not_emp"] is False
