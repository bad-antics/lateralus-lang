"""
Unit tests for algorithms edge-case fixes (Issues #194 and #196).
Tests chunk, sliding_window, and primes_up_to boundary behaviors in Python API.
"""

import pytest

from lateralus_lang.algorithms import chunk, primes_up_to, sliding_window


class TestAlgorithmsEdgeCases:
    def test_primes_up_to_zero_and_negative(self):
        # Issue #196: primes_up_to(0) and negative ranges should return empty list
        assert primes_up_to(0) == []
        assert primes_up_to(1) == []
        assert primes_up_to(-1) == []
        assert primes_up_to(-5) == []

    def test_primes_up_to_valid_ranges(self):
        assert primes_up_to(2) == [2]
        assert primes_up_to(10) == [2, 3, 5, 7]
        assert primes_up_to(20) == [2, 3, 5, 7, 11, 13, 17, 19]

    def test_sliding_window_zero_and_negative_size(self):
        # Issue #196: sliding_window with size <= 0 should raise ValueError
        with pytest.raises(ValueError, match="window size must be a positive integer"):
            sliding_window([1, 2, 3], 0)

        with pytest.raises(ValueError, match="window size must be a positive integer"):
            sliding_window([1, 2, 3], -1)

    def test_sliding_window_valid_size(self):
        assert sliding_window([1, 2, 3, 4], 2) == [[1, 2], [2, 3], [3, 4]]
        assert sliding_window([1, 2, 3], 3) == [[1, 2, 3]]
        assert sliding_window([1, 2], 5) == []

    def test_chunk_zero_and_negative_size(self):
        # Issue #194: chunk with size <= 0 should raise ValueError instead of raw range error
        with pytest.raises(ValueError, match="chunk size must be a positive integer"):
            chunk([1, 2, 3], 0)

        with pytest.raises(ValueError, match="chunk size must be a positive integer"):
            chunk([1, 2, 3], -2)

    def test_chunk_valid_size(self):
        assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
        assert chunk([], 3) == []
