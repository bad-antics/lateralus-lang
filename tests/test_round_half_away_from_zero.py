"""Round to nearest, ties away from zero.

Regression test for the divergence reported in the $10 recurring bug-report
bounty: the Python backend used the builtin ``round`` (ties-to-even), while the
C backend maps ``round`` to C ``round()`` (ties away from zero) and
``stdlib/math.ltl::round_val`` was documented as ``floor(x + 0.5)``.

All three surfaces must agree, and ``round_val`` must also be correct for
negative ties (``floor(x + 0.5)`` is not).
"""
from __future__ import annotations

import math

import pytest

from lateralus_lang.math_engine import MATH_BUILTINS


round_lang = MATH_BUILTINS["round"]


def round_val_reference(x: float) -> int:
    """Mirror of stdlib/math.ltl::round_val."""
    return -math.floor(-x + 0.5) if x < 0.0 else math.floor(x + 0.5)


@pytest.mark.parametrize(
    "x, expected",
    [
        (0.5, 1), (1.5, 2), (2.5, 3), (3.5, 4),
        (-0.5, -1), (-1.5, -2), (-2.5, -3), (-3.5, -4),
        (0.4, 0), (0.6, 1), (-0.4, 0), (-0.6, -1),
        (2.0, 2), (-2.0, -2), (0.0, 0),
    ],
)
def test_round_ties_away_from_zero(x, expected):
    assert round_lang(x) == expected


@pytest.mark.parametrize("x", [0.5, 1.5, 2.5, -0.5, -1.5, -2.5, 7.5, -7.5])
def test_backend_matches_stdlib_round_val(x):
    """Python backend and stdlib/math.ltl::round_val must agree on ties."""
    assert round_lang(x) == round_val_reference(x)


@pytest.mark.parametrize("x", [0.5, 1.5, 2.5, -0.5, -1.5, -2.5])
def test_not_bankers_rounding(x):
    """Guard against reintroducing Python's ties-to-even builtin."""
    assert round_lang(x) != round(x)


def test_ndigits():
    assert round_lang(1.25, 1) == pytest.approx(1.3)
    assert round_lang(-1.25, 1) == pytest.approx(-1.3)
    assert round_lang(2.5, 0) == 3
