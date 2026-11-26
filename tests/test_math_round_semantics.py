"""
Lateralus math engine -- math builtins exposed to the Python backend.

NOTE: This file contains the corrected round() semantics. The rounding
function is defined here and wired into MATH_BUILTINS so that the Python
backend agrees with the C backend (C round(), half away from zero) and
stdlib/math.ltl (round_val).
"""
from __future__ import annotations

import math


def _ltl_round(x, ndigits=None):
    """Round half away from zero, matching C round() and stdlib round_val.

    - Python's built-in round() uses banker's rounding (ties to even), which
      makes round(2.5) == 2. C round(2.5) == 3 and floor(2.5 + 0.5) == 3.
    - With ``ndigits`` omitted, returns an int (like Lateralus round_val).
    - With ``ndigits`` given, returns a float rounded to that many decimals
      using the same half-away-from-zero rule.
    """
    if isinstance(x, bool):
        x = int(x)

    if ndigits is None:
        if isinstance(x, int):
            return x
        x = float(x)
        # inf / nan cannot be converted to int; leave them unchanged.
        if math.isinf(x) or math.isnan(x):
            return x
        # Already integral (also covers huge magnitudes where +0.5 is lossy).
        if abs(x) >= 2.0 ** 52:
            return int(x)
        return int(math.copysign(math.floor(abs(x) + 0.5), x))

    # ndigits provided: scale, round half away from zero, unscale.
    if isinstance(x, int) and ndigits >= 0:
        return x
    x = float(x)
    if math.isinf(x) or math.isnan(x):
        return x
    factor = 10.0 ** ndigits
    scaled = x * factor
    if math.isinf(scaled) or math.isnan(scaled):
        return x
    if abs(scaled) >= 2.0 ** 52:
        return x
    return math.copysign(math.floor(abs(scaled) + 0.5), scaled) / factor


# Existing builtins are preserved; only "round" is rebound to the fixed impl.
MATH_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
    "sqrt": math.sqrt,
    "pow": pow,
    "round": _ltl_round,
}
import math

from lateralus_lang.math_engine import MATH_BUILTINS


def test_round_half_positive_goes_up():
    assert MATH_BUILTINS["round"](2.5) == 3
    assert MATH_BUILTINS["round"](0.5) == 1
    assert MATH_BUILTINS["round"](1.5) == 2


def test_round_half_negative_away_from_zero():
    assert MATH_BUILTINS["round"](-2.5) == -3
    assert MATH_BUILTINS["round"](-0.5) == -1


def test_round_non_ties_unchanged():
    assert MATH_BUILTINS["round"](2.6) == 3
    assert MATH_BUILTINS["round"](2.4) == 2
    assert MATH_BUILTINS["round"](-2.6) == -3
    assert MATH_BUILTINS["round"](-2.4) == -2


def test_round_returns_int():
    assert isinstance(MATH_BUILTINS["round"](2.5), int)
    assert MATH_BUILTINS["round"](7) == 7


def test_round_non_finite_passthrough():
    assert math.isinf(MATH_BUILTINS["round"](float("inf")))
    assert math.isnan(MATH_BUILTINS["round"](float("nan")))