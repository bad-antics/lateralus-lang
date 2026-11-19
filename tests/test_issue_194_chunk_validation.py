"""
tests/test_issue_194_chunk_validation.py

Verifies size <= 0 validation for algorithms.chunk in both:
- Python API: raises ValueError("chunk size must be a positive integer")
- .ltl stdlib: returns [] instead of infinite looping
"""
from pathlib import Path

import pytest

from lateralus_lang.algorithms import chunk


def test_chunk_python_valid():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk([], 2) == []
    assert chunk([1, 2], 3) == [[1, 2]]


def test_chunk_python_invalid_size():
    with pytest.raises(ValueError, match="chunk size must be a positive integer"):
        chunk([1, 2, 3], 0)

    with pytest.raises(ValueError, match="chunk size must be a positive integer"):
        chunk([1, 2, 3], -1)


def test_chunk_ltl_stdlib_no_infinite_loop():
    stdlib_path = Path(__file__).resolve().parent.parent / "stdlib" / "algorithms.ltl"
    code = stdlib_path.read_text(encoding="utf-8")
    assert "if size <= 0 { return [] }" in code
