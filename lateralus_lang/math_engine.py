import math as _math


def _real_cbrt(x):
    """Real-valued cube root that is correct for negative inputs.

    Uses math.cbrt when available (Python 3.11+); otherwise falls back to a
    sign-preserving implementation. Never returns a complex number.
    """
    x = float(x)

    # Preserve nan, +/-inf and signed zero unchanged.
    if x != x or x in (_math.inf, -_math.inf) or x == 0.0:
        return x

    native = getattr(_math, "cbrt", None)
    if native is not None:
        return native(x)

    # Fallback: compute on the magnitude, then restore the sign.
    r = _math.copysign(abs(x) ** (1.0 / 3.0), x)
    # One Newton-Raphson step refines r so exact cubes come out exact.
    r = r - (r * r * r - x) / (3.0 * r * r)
    return r


# In MATH_BUILTINS, replace the old fractional-power entry:
#     "cbrt": lambda x: x ** (1 / 3),
# with:
#     "cbrt": _real_cbrt,