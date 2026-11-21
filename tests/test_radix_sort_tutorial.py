"""
tests/test_radix_sort_tutorial.py - Tests for stdlib/radix_sort.ltl
Verifies u32, i32, string radix sorts, counting sort, and edge cases.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_radix_sort_u32_and_i32():
    radix_src = Path("stdlib/radix_sort.ltl").read_text(encoding="utf-8")
    driver = """
let u_arr = [170, 45, 75, 90, 802, 24, 2, 66]
let u_sorted = radix_sort_u32(u_arr)

let i_arr = [10, -5, 0, -20, 15, -1]
let i_sorted = radix_sort_i32(i_arr)

let empty_u = radix_sort_u32([])
let single_u = radix_sort_u32([42])
"""
    c = Compiler()
    res = c.compile_source(radix_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["u_sorted"] == [2, 24, 45, 66, 75, 90, 170, 802]
    assert ns["i_sorted"] == [-20, -5, -1, 0, 10, 15]
    assert ns["empty_u"] == []
    assert ns["single_u"] == [42]

def test_radix_sort_str_and_counting():
    radix_src = Path("stdlib/radix_sort.ltl").read_text(encoding="utf-8")
    driver = """
let strings = ["zebra", "apple", "banana", "ant", "app"]
let str_sorted = radix_sort_str(strings)

let counts = [3, 1, 4, 1, 5, 9, 2, 6]
let counted = counting_sort(counts, 10)
"""
    c = Compiler()
    res = c.compile_source(radix_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["str_sorted"] == ["ant", "app", "apple", "banana", "zebra"]
    assert ns["counted"] == [1, 1, 2, 3, 4, 5, 6, 9]
