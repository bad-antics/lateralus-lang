"""Regression tests for issue #810: lcm(0, 0) must return 0, not raise ZeroDivisionError."""
import math

from lateralus_lang.algorithms import lcm


def test_lcm_zero_zero():
    assert lcm(0, 0) == 0


def test_lcm_zero_nonzero():
    assert lcm(0, 5) == 0
    assert lcm(5, 0) == 0


def test_lcm_basic():
    assert lcm(4, 6) == 12


def test_lcm_matches_math_lcm():
    for a in range(-8, 9):
        for b in range(-8, 9):
            assert lcm(a, b) == math.lcm(a, b), (a, b)