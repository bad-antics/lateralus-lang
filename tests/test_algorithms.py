"""
tests/test_algorithms.py -- Tests for lateralus_lang.algorithms
"""
import math
import pytest

from lateralus_lang.algorithms import (
    gcd,
    lcm,
    is_prime,
    primes_up_to,
    fibonacci_sequence,
    power_mod,
)


class TestLCM:
    def test_lcm_zeros(self):
        """lcm(0, 0), lcm(0, 5), lcm(5, 0) should return 0, matching math.lcm."""
        assert lcm(0, 0) == 0
        assert lcm(0, 5) == 0
        assert lcm(5, 0) == 0
        assert lcm(0, -5) == 0
        assert lcm(-5, 0) == 0

    def test_lcm_regular_pairs(self):
        """Regular pairs match expected least common multiple."""
        assert lcm(4, 6) == 12
        assert lcm(21, 6) == 42
        assert lcm(8, 9) == 72
        assert lcm(1, 1) == 1
        assert lcm(7, 13) == 91
        assert lcm(12, 18) == 36

    def test_lcm_negative_numbers(self):
        """lcm with negative integers matches math.lcm."""
        assert lcm(-4, 6) == 12
        assert lcm(4, -6) == 12
        assert lcm(-4, -6) == 12
        assert lcm(-21, 6) == 42
        assert lcm(21, -6) == 42

    def test_lcm_matches_math_lcm_exhaustive(self):
        """lcm matches math.lcm for integer pairs [-20, 20]."""
        for a in range(-20, 21):
            for b in range(-20, 21):
                assert lcm(a, b) == math.lcm(a, b)


class TestOtherMathAlgorithms:
    def test_gcd(self):
        assert gcd(0, 0) == 0
        assert gcd(54, 24) == 6
        assert gcd(-54, 24) == 6

    def test_is_prime(self):
        assert not is_prime(0)
        assert not is_prime(1)
        assert is_prime(2)
        assert is_prime(3)
        assert not is_prime(4)
        assert is_prime(17)

    def test_primes_up_to(self):
        assert primes_up_to(10) == [2, 3, 5, 7]

    def test_fibonacci_sequence(self):
        assert fibonacci_sequence(5) == [0, 1, 1, 2, 3]

    def test_power_mod(self):
        assert power_mod(2, 10, 1000) == 24
