"""
tests/test_issue_196_primes_and_sliding_window.py

Verifies:
1) primes_up_to(0) -> [] and primes_up_to(negative) -> [] without IndexError
2) sliding_window(_, <= 0) raises ValueError("window size must be a positive integer") in Python API
3) stdlib/algorithms.ltl defensive guards for primes_up_to and sliding_window
"""
from pathlib import Path

import pytest

from lateralus_lang.algorithms import primes_up_to, sliding_window


def test_primes_up_to_edge_cases():
    assert primes_up_to(0) == []
    assert primes_up_to(1) == []
    assert primes_up_to(-1) == []
    assert primes_up_to(-5) == []
    assert primes_up_to(10) == [2, 3, 5, 7]


def test_sliding_window_invalid_size():
    with pytest.raises(ValueError, match="window size must be a positive integer"):
        sliding_window([1, 2, 3], 0)

    with pytest.raises(ValueError, match="window size must be a positive integer"):
        sliding_window([1, 2, 3], -2)


def test_sliding_window_valid():
    assert sliding_window([1, 2, 3, 4], 2) == [[1, 2], [2, 3], [3, 4]]
    assert sliding_window([1, 2], 3) == []


def test_stdlib_ltl_defensive_guards():
    stdlib_path = Path(__file__).resolve().parent.parent / "stdlib" / "algorithms.ltl"
    code = stdlib_path.read_text(encoding="utf-8")
    assert "if size <= 0 { return [] }" in code
    assert "if n < 2 { return [] }" in code
