"""
tests/test_algorithms.py — Tests for standard library algorithms
"""
import pytest
from lateralus_lang.algorithms import chunk, interleave, primes_up_to, sliding_window
from lateralus_lang.compiler import Compiler, Target


def test_chunk_positive():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk([1, 2, 3], 1) == [[1], [2], [3]]
    assert chunk([1, 2, 3], 5) == [[1, 2, 3]]


def test_chunk_size_zero_or_negative_raises_value_error():
    with pytest.raises(ValueError, match="chunk size must be a positive integer"):
        chunk([1, 2, 3], 0)
    with pytest.raises(ValueError, match="chunk size must be a positive integer"):
        chunk([1, 2, 3], -1)


def test_chunk_ltl_stdlib_guard():
    src = """
fn chunk(arr: list, size: int) -> list {
    if size <= 0 {
        return []
    }
    let result = []
    let i = 0
    while i < len(arr) {
        let end = min(i + size, len(arr))
        result = result + [slice(arr, i, end)]
        i = i + size
    }
    return result
}

fn test_chunk_zero() -> list {
    return chunk([1, 2, 3], 0)
}
"""
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok
    ns = {}
    exec(r.python_src, ns)
    assert ns["test_chunk_zero"]() == []
