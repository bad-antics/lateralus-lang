"""
tests/test_algorithms.py — Tests for standard library algorithms
"""
import pytest
from lateralus_lang.algorithms import primes_up_to, sliding_window
from lateralus_lang.compiler import Compiler, Target


def test_primes_up_to():
    assert primes_up_to(10) == [2, 3, 5, 7]
    assert primes_up_to(2) == [2]
    assert primes_up_to(1) == []
    assert primes_up_to(0) == []
    assert primes_up_to(-5) == []


def test_sliding_window_normal():
    assert sliding_window([1, 2, 3, 4], 2) == [[1, 2], [2, 3], [3, 4]]
    assert sliding_window([1, 2, 3], 3) == [[1, 2, 3]]


def test_sliding_window_size_zero_or_negative():
    with pytest.raises(ValueError, match="window size must be a positive integer"):
        sliding_window([1, 2, 3], 0)
    with pytest.raises(ValueError, match="window size must be a positive integer"):
        sliding_window([1, 2, 3], -2)


def test_sliding_window_ltl():
    src = """
fn sliding_window(arr: list, size: int) -> list {
    if size <= 0 {
        return []
    }
    let result = []
    for i in range(len(arr) - size + 1) {
        result = result + [slice(arr, i, i + size)]
    }
    return result
}

fn test_window_zero() -> list {
    return sliding_window([1, 2, 3], 0)
}
"""
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok
    ns = {}
    exec(r.python_src, ns)
    assert ns["test_window_zero"]() == []
