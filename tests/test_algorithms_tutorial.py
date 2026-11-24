"""
tests/test_algorithms_tutorial.py - Tests for stdlib/algorithms.ltl
Verifies sorting, searching, prime generation, deduplication, and edge cases.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_algorithms_sort_and_search():
    alg_src = Path("stdlib/algorithms.ltl").read_text(encoding="utf-8")
    driver = """
let data = [5, 2, 8, 1, 9, 3]
let sorted_arr = merge_sort(data)

let idx1 = binary_search(sorted_arr, 1)
let idx8 = binary_search(sorted_arr, 8)
let idx_missing = binary_search(sorted_arr, 100)

let empty_sort = merge_sort([])
let single_sort = merge_sort([42])
let empty_search = binary_search([], 5)
"""
    c = Compiler()
    res = c.compile_source(alg_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["sorted_arr"] == [1, 2, 3, 5, 8, 9]
    assert ns["idx1"] == 0
    assert ns["idx8"] == 4
    assert ns["idx_missing"] == -1
    assert ns["empty_sort"] == []
    assert ns["single_sort"] == [42]
    assert ns["empty_search"] == -1

def test_algorithms_primes_and_math():
    alg_src = Path("stdlib/algorithms.ltl").read_text(encoding="utf-8")
    driver = """
let p = primes_up_to(25)
let g = gcd(54, 24)
let l = lcm(12, 18)
let fibs = fibonacci_sequence(6)
let deduplicated = unique([1, 1, 2, 3, 3, 3, 4])
"""
    c = Compiler()
    res = c.compile_source(alg_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["p"] == [2, 3, 5, 7, 11, 13, 17, 19, 23]
    assert ns["g"] == 6
    assert ns["l"] == 36
    assert ns["fibs"] == [0, 1, 1, 2, 3, 5]
    assert ns["deduplicated"] == [1, 2, 3, 4]
