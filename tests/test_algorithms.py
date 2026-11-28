"""
tests/test_algorithms.py — Tests for lateralus_lang.algorithms
"""
import math
import pytest
from lateralus_lang.algorithms import gcd, lcm, is_prime, primes_up_to, fibonacci_sequence, power_mod


def test_gcd_basic():
    assert gcd(48, 18) == 6
    assert gcd(10, 0) == 10
    assert gcd(0, 10) == 10
    assert gcd(0, 0) == 0
    assert gcd(-48, 18) == 6


def test_lcm_basic():
    assert lcm(4, 6) == 12
    assert lcm(21, 6) == 42
    assert lcm(-4, 6) == 12
    assert lcm(4, -6) == 12
    assert lcm(-4, -6) == 12


def test_lcm_zero_boundary():
    # Fixes issue #810: lcm(0, 0) previously raised ZeroDivisionError
    assert lcm(0, 0) == 0
    assert lcm(0, 5) == 0
    assert lcm(5, 0) == 0
    assert lcm(0, -5) == 0
    assert lcm(-5, 0) == 0


def test_lcm_against_math_lcm_range():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert lcm(a, b) == math.lcm(a, b), f"Mismatch for lcm({a}, {b})"


def test_is_prime():
    assert not is_prime(0)
    assert not is_prime(1)
    assert is_prime(2)
    assert is_prime(3)
    assert not is_prime(4)
    assert is_prime(17)
    assert not is_prime(18)


def test_primes_up_to():
    assert primes_up_to(10) == [2, 3, 5, 7]
    assert primes_up_to(1) == []


def test_fibonacci_sequence():
    assert fibonacci_sequence(0) == []
    assert fibonacci_sequence(1) == [0]
    assert fibonacci_sequence(5) == [0, 1, 1, 2, 3]


def test_power_mod():
    assert power_mod(2, 10, 1000) == 24
