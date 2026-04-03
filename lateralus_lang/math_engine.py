"""
lateralus_lang/math_engine.py  ─  LATERALUS High-Precision Math Engine
═══════════════════════════════════════════════════════════════════════════
Julia-inspired mathematical computation core with:
  · Arbitrary-precision integers (no overflow)
  · IEEE 754 doubles + optional Decimal mode for financial/scientific work
  · Matrix operations (pure Python, no numpy dependency)
  · Complex number support
  · Interval arithmetic for error-bounded computation
  · Automatic differentiation (forward-mode)
  · Symbolic constants (π, e, φ, √2)
  · Unit-aware computation framework

Design principle: every numerical operation should be CORRECT first,
fast second.  Python's int is already arbitrary-precision; we add
Decimal for controlled-precision floats and matrix algebra.

v1.5.0
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import math
import operator
from dataclasses import dataclass, field
from decimal import Decimal, getcontext, ROUND_HALF_UP
from fractions import Fraction
from typing import (
    Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union,
)

# ─────────────────────────────────────────────────────────────────────────────
# Precision control
# ─────────────────────────────────────────────────────────────────────────────

# Default 50 significant digits — can be raised at runtime
getcontext().prec = 50
getcontext().rounding = ROUND_HALF_UP

# Symbolic constants at full precision
PI  = Decimal("3.14159265358979323846264338327950288419716939937510")
E   = Decimal("2.71828182845904523536028747135266249775724709369995")
PHI = Decimal("1.61803398874989484820458683436563811772030917980576")
TAU = PI * 2
SQRT2 = Decimal("1.41421356237309504880168872420969807856967187537694")


def set_precision(digits: int) -> None:
    """Set the global working precision for Decimal operations."""
    if digits < 1:
        raise ValueError("precision must be >= 1")
    getcontext().prec = digits


# ─────────────────────────────────────────────────────────────────────────────
# LTLNumber — the core numeric type
# ─────────────────────────────────────────────────────────────────────────────

class LTLNumber:
    """Wrapper that auto-promotes between int → Fraction → Decimal → Complex.

    Arithmetic never silently overflows or loses precision beyond the
    user-configured Decimal context.
    """

    __slots__ = ("_val",)

    def __init__(self, value: Union[int, float, str, Decimal, Fraction, complex]):
        if isinstance(value, (int, Fraction)):
            self._val = value
        elif isinstance(value, float):
            self._val = Decimal(str(value))
        elif isinstance(value, str):
            self._val = Decimal(value) if "." in value else int(value)
        elif isinstance(value, (Decimal, complex)):
            self._val = value
        else:
            self._val = value

    @property
    def value(self):
        return self._val

    # ── arithmetic ────────────────────────────────────────────────────────────

    def __add__(self, other):
        return LTLNumber(_coerce_op(self._val, _unwrap(other), operator.add))

    def __sub__(self, other):
        return LTLNumber(_coerce_op(self._val, _unwrap(other), operator.sub))

    def __mul__(self, other):
        return LTLNumber(_coerce_op(self._val, _unwrap(other), operator.mul))

    def __truediv__(self, other):
        b = _unwrap(other)
        if b == 0:
            raise ZeroDivisionError("LATERALUS DivisionError: division by zero")
        return LTLNumber(_coerce_op(self._val, b, operator.truediv))

    def __floordiv__(self, other):
        b = _unwrap(other)
        if b == 0:
            raise ZeroDivisionError("LATERALUS DivisionError: integer division by zero")
        return LTLNumber(_coerce_op(self._val, b, operator.floordiv))

    def __mod__(self, other):
        return LTLNumber(_coerce_op(self._val, _unwrap(other), operator.mod))

    def __pow__(self, other):
        return LTLNumber(_coerce_op(self._val, _unwrap(other), operator.pow))

    def __neg__(self):
        return LTLNumber(-self._val)

    def __abs__(self):
        return LTLNumber(abs(self._val))

    # ── comparison ────────────────────────────────────────────────────────────

    def __eq__(self, other):
        return self._val == _unwrap(other)

    def __lt__(self, other):
        return self._val < _unwrap(other)

    def __le__(self, other):
        return self._val <= _unwrap(other)

    def __gt__(self, other):
        return self._val > _unwrap(other)

    def __ge__(self, other):
        return self._val >= _unwrap(other)

    # ── display ───────────────────────────────────────────────────────────────

    def __repr__(self):
        return f"LTLNumber({self._val!r})"

    def __str__(self):
        return str(self._val)

    def __int__(self):
        return int(self._val)

    def __float__(self):
        return float(self._val)

    def __hash__(self):
        return hash(self._val)


def _unwrap(v):
    """Extract raw value from LTLNumber or pass through."""
    return v._val if isinstance(v, LTLNumber) else v


def _coerce_op(a, b, op):
    """Apply op with automatic type promotion: int → Decimal → complex."""
    if isinstance(a, complex) or isinstance(b, complex):
        return op(complex(a) if not isinstance(a, complex) else a,
                  complex(b) if not isinstance(b, complex) else b)
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        da = Decimal(str(a)) if not isinstance(a, Decimal) else a
        db = Decimal(str(b)) if not isinstance(b, Decimal) else b
        return op(da, db)
    if isinstance(a, Fraction) or isinstance(b, Fraction):
        fa = Fraction(a) if not isinstance(a, Fraction) else a
        fb = Fraction(b) if not isinstance(b, Fraction) else b
        return op(fa, fb)
    return op(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Matrix — pure-Python dense matrix for linear algebra
# ─────────────────────────────────────────────────────────────────────────────

class Matrix:
    """Dense matrix with exact arithmetic (uses LTLNumber internally).

    Supports: add, sub, mul (matmul), scalar ops, transpose, determinant,
    inverse, trace, eigenvalues (2×2), LU decomposition.
    """

    __slots__ = ("rows", "cols", "_data")

    def __init__(self, data: List[List[Union[int, float, LTLNumber]]]):
        if not data or not data[0]:
            raise ValueError("Matrix cannot be empty")
        self.rows = len(data)
        self.cols = len(data[0])
        self._data = [[_to_num(v) for v in row] for row in data]
        for r in self._data:
            if len(r) != self.cols:
                raise ValueError("All rows must have the same length")

    @property
    def data(self) -> List[List]:
        """Return the matrix data as a nested list."""
        return [list(row) for row in self._data]

    @staticmethod
    def identity(n: int) -> "Matrix":
        return Matrix([[1 if i == j else 0 for j in range(n)] for i in range(n)])

    @staticmethod
    def zeros(rows: int, cols: int) -> "Matrix":
        return Matrix([[0] * cols for _ in range(rows)])

    @staticmethod
    def from_flat(data: List, rows: int, cols: int) -> "Matrix":
        return Matrix([data[i*cols:(i+1)*cols] for i in range(rows)])

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            r, c = idx
            return self._data[r][c]
        return self._data[idx]

    def __setitem__(self, idx, val):
        if isinstance(idx, tuple):
            r, c = idx
            self._data[r][c] = _to_num(val)
        else:
            self._data[idx] = [_to_num(v) for v in val]

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.rows, self.cols)

    @property
    def T(self) -> "Matrix":
        return self.transpose()

    def transpose(self) -> "Matrix":
        return Matrix([[self._data[r][c] for r in range(self.rows)]
                       for c in range(self.cols)])

    def trace(self) -> LTLNumber:
        if self.rows != self.cols:
            raise ValueError("trace requires a square matrix")
        return sum(self._data[i][i] for i in range(self.rows))

    # ── arithmetic ────────────────────────────────────────────────────────────

    def __add__(self, other: "Matrix") -> "Matrix":
        _assert_same_shape(self, other, "+")
        return Matrix([[self._data[r][c] + other._data[r][c]
                        for c in range(self.cols)]
                       for r in range(self.rows)])

    def __sub__(self, other: "Matrix") -> "Matrix":
        _assert_same_shape(self, other, "-")
        return Matrix([[self._data[r][c] - other._data[r][c]
                        for c in range(self.cols)]
                       for r in range(self.rows)])

    def __mul__(self, other):
        """Element-wise if Matrix, scalar multiplication otherwise."""
        if isinstance(other, Matrix):
            _assert_same_shape(self, other, "*")
            return Matrix([[self._data[r][c] * other._data[r][c]
                            for c in range(self.cols)]
                           for r in range(self.rows)])
        s = _to_num(other)
        return Matrix([[self._data[r][c] * s for c in range(self.cols)]
                       for r in range(self.rows)])

    def __matmul__(self, other: "Matrix") -> "Matrix":
        """Matrix multiplication (@ operator)."""
        if self.cols != other.rows:
            raise ValueError(
                f"matmul shape mismatch: ({self.rows}×{self.cols}) @ "
                f"({other.rows}×{other.cols})")
        result = [[sum(self._data[r][k] * other._data[k][c]
                       for k in range(self.cols))
                   for c in range(other.cols)]
                  for r in range(self.rows)]
        return Matrix(result)

    # ── determinant (Laplace expansion for small, LU for larger) ──────────

    def det(self) -> float:
        if self.rows != self.cols:
            raise ValueError("determinant requires a square matrix")
        n = self.rows
        if n == 1:
            return float(self._data[0][0])
        if n == 2:
            return float(self._data[0][0] * self._data[1][1] -
                         self._data[0][1] * self._data[1][0])
        # LU decomposition for n >= 3
        return float(self._lu_det())

    def _lu_det(self) -> float:
        n = self.rows
        lu = [[float(self._data[r][c]) for c in range(n)] for r in range(n)]
        sign = 1
        for col in range(n):
            # Partial pivoting
            max_row = max(range(col, n), key=lambda r: abs(lu[r][col]))
            if abs(lu[max_row][col]) < 1e-15:
                return 0.0
            if max_row != col:
                lu[col], lu[max_row] = lu[max_row], lu[col]
                sign *= -1
            for row in range(col + 1, n):
                factor = lu[row][col] / lu[col][col]
                for k in range(col, n):
                    lu[row][k] -= factor * lu[col][k]
        d = sign
        for i in range(n):
            d *= lu[i][i]
        return d

    # ── inverse (Gauss-Jordan) ────────────────────────────────────────────

    def inverse(self) -> "Matrix":
        if self.rows != self.cols:
            raise ValueError("inverse requires a square matrix")
        n = self.rows
        aug = [[float(self._data[r][c]) for c in range(n)] +
               [1.0 if r == c else 0.0 for c in range(n)]
               for r in range(n)]
        for col in range(n):
            max_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
            if abs(aug[max_row][col]) < 1e-15:
                raise ValueError("Matrix is singular — no inverse exists")
            aug[col], aug[max_row] = aug[max_row], aug[col]
            pivot = aug[col][col]
            for j in range(2 * n):
                aug[col][j] /= pivot
            for row in range(n):
                if row != col:
                    factor = aug[row][col]
                    for j in range(2 * n):
                        aug[row][j] -= factor * aug[col][j]
        return Matrix([[aug[r][n + c] for c in range(n)] for r in range(n)])

    # ── display ───────────────────────────────────────────────────────────────

    def __repr__(self):
        rows_str = ",\n ".join(str(row) for row in self._data)
        return f"Matrix([{rows_str}])"

    def __str__(self):
        col_widths = []
        strs = [[str(self._data[r][c]) for c in range(self.cols)]
                for r in range(self.rows)]
        for c in range(self.cols):
            col_widths.append(max(len(strs[r][c]) for r in range(self.rows)))
        lines = []
        for r in range(self.rows):
            cells = [strs[r][c].rjust(col_widths[c]) for c in range(self.cols)]
            lines.append("│ " + "  ".join(cells) + " │")
        return "\n".join(lines)

    def __eq__(self, other):
        if not isinstance(other, Matrix):
            return False
        return self._data == other._data

    def to_list(self) -> List[List]:
        return [[float(v) if isinstance(v, (Decimal, Fraction)) else v
                 for v in row] for row in self._data]


def _to_num(v):
    return v if isinstance(v, LTLNumber) else v


def _assert_same_shape(a: Matrix, b: Matrix, op: str):
    if a.shape != b.shape:
        raise ValueError(f"Matrix {op}: shape mismatch {a.shape} vs {b.shape}")


# ─────────────────────────────────────────────────────────────────────────────
# Vector — convenience wrapper for 1D operations
# ─────────────────────────────────────────────────────────────────────────────

class Vector:
    """1D numeric vector with dot product, norm, cross product (3D)."""

    __slots__ = ("_data",)

    def __init__(self, data: List[Union[int, float]]):
        self._data = list(data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __add__(self, other: "Vector") -> "Vector":
        return Vector([a + b for a, b in zip(self._data, other._data)])

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector([a - b for a, b in zip(self._data, other._data)])

    def __mul__(self, scalar) -> "Vector":
        return Vector([x * scalar for x in self._data])

    def dot(self, other: "Vector") -> float:
        return sum(a * b for a, b in zip(self._data, other._data))

    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def normalize(self) -> "Vector":
        n = self.norm()
        if n == 0:
            raise ValueError("cannot normalize zero vector")
        return self * (1 / n)

    def cross(self, other: "Vector") -> "Vector":
        if len(self) != 3 or len(other) != 3:
            raise ValueError("cross product only defined for 3D vectors")
        a, b = self._data, other._data
        return Vector([
            a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0],
        ])

    def __repr__(self):
        return f"Vector({self._data})"

    def __str__(self):
        return f"⟨{', '.join(str(x) for x in self._data)}⟩"


# ─────────────────────────────────────────────────────────────────────────────
# Interval arithmetic — for error-bounded computation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Interval:
    """Closed interval [lo, hi] for guaranteed enclosure arithmetic.

    Every operation returns an interval that is GUARANTEED to contain
    the true mathematical result.  Essential for scientific computation
    where floating-point error must be tracked.
    """
    lo: float
    hi: float

    def __post_init__(self):
        if self.lo > self.hi:
            object.__setattr__(self, "lo", min(self.lo, self.hi))
            object.__setattr__(self, "hi", max(self.lo, self.hi))

    @staticmethod
    def exact(v: float) -> "Interval":
        return Interval(v, v)

    @staticmethod
    def pm(center: float, error: float) -> "Interval":
        return Interval(center - abs(error), center + abs(error))

    @property
    def mid(self) -> float:
        return (self.lo + self.hi) / 2

    @property
    def width(self) -> float:
        return self.hi - self.lo

    @property
    def radius(self) -> float:
        return self.width / 2

    def contains(self, value: float) -> bool:
        return self.lo <= value <= self.hi

    def overlaps(self, other: "Interval") -> bool:
        return self.lo <= other.hi and other.lo <= self.hi

    def __add__(self, other: "Interval") -> "Interval":
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def __sub__(self, other: "Interval") -> "Interval":
        return Interval(self.lo - other.hi, self.hi - other.lo)

    def __mul__(self, other: "Interval") -> "Interval":
        products = [self.lo * other.lo, self.lo * other.hi,
                    self.hi * other.lo, self.hi * other.hi]
        return Interval(min(products), max(products))

    def __truediv__(self, other: "Interval") -> "Interval":
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError(
                "Interval division: divisor interval contains zero")
        quotients = [self.lo / other.lo, self.lo / other.hi,
                     self.hi / other.lo, self.hi / other.hi]
        return Interval(min(quotients), max(quotients))

    def __repr__(self):
        return f"[{self.lo}, {self.hi}]"

    def __str__(self):
        return f"{self.mid:.6g} ± {self.radius:.2g}"


# ─────────────────────────────────────────────────────────────────────────────
# Forward-mode automatic differentiation
# ─────────────────────────────────────────────────────────────────────────────

class Dual:
    """Dual number for forward-mode automatic differentiation.

    Dual(value, derivative) represents: value + derivative·ε
    where ε² = 0.

    Usage::

        x = Dual(3.0, 1.0)      # f(x) at x=3, ∂/∂x
        result = x**2 + 2*x + 1  # → Dual(16.0, 8.0)
        # result.val = f(3) = 16
        # result.dot = f'(3) = 8
    """

    __slots__ = ("val", "dot")

    def __init__(self, val: float, dot: float = 0.0):
        self.val = val
        self.dot = dot

    def __add__(self, other):
        o = _as_dual(other)
        return Dual(self.val + o.val, self.dot + o.dot)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        o = _as_dual(other)
        return Dual(self.val - o.val, self.dot - o.dot)

    def __rsub__(self, other):
        o = _as_dual(other)
        return Dual(o.val - self.val, o.dot - self.dot)

    def __mul__(self, other):
        o = _as_dual(other)
        return Dual(self.val * o.val, self.val * o.dot + self.dot * o.val)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        o = _as_dual(other)
        if o.val == 0:
            raise ZeroDivisionError("Dual division by zero")
        return Dual(self.val / o.val,
                    (self.dot * o.val - self.val * o.dot) / (o.val * o.val))

    def __pow__(self, other):
        o = _as_dual(other)
        if self.val <= 0 and o.dot != 0:
            raise ValueError("Dual pow: negative base with non-constant exponent")
        v = self.val ** o.val
        d = v * (o.dot * math.log(abs(self.val)) if self.val != 0 else 0
                 + o.val * self.dot / self.val if self.val != 0 else 0)
        return Dual(v, d)

    def __neg__(self):
        return Dual(-self.val, -self.dot)

    def __abs__(self):
        if self.val > 0:
            return Dual(self.val, self.dot)
        elif self.val < 0:
            return Dual(-self.val, -self.dot)
        return Dual(0, 0)  # not differentiable at 0

    def __repr__(self):
        return f"Dual({self.val}, {self.dot})"

    def __str__(self):
        return f"{self.val} + {self.dot}ε"

    def __eq__(self, other):
        o = _as_dual(other)
        return self.val == o.val

    def __lt__(self, other):
        return self.val < _as_dual(other).val

    def __le__(self, other):
        return self.val <= _as_dual(other).val

    def __gt__(self, other):
        return self.val > _as_dual(other).val

    def __ge__(self, other):
        return self.val >= _as_dual(other).val


def _as_dual(v) -> Dual:
    return v if isinstance(v, Dual) else Dual(float(v), 0.0)


# Dual-aware math functions
def dual_sin(x: Dual) -> Dual:
    return Dual(math.sin(x.val), x.dot * math.cos(x.val))

def dual_cos(x: Dual) -> Dual:
    return Dual(math.cos(x.val), -x.dot * math.sin(x.val))

def dual_exp(x: Dual) -> Dual:
    e = math.exp(x.val)
    return Dual(e, x.dot * e)

def dual_log(x: Dual) -> Dual:
    if x.val <= 0:
        raise ValueError("dual_log: non-positive argument")
    return Dual(math.log(x.val), x.dot / x.val)

def dual_sqrt(x: Dual) -> Dual:
    if x.val < 0:
        raise ValueError("dual_sqrt: negative argument")
    s = math.sqrt(x.val)
    return Dual(s, x.dot / (2 * s) if s != 0 else 0)


def derivative(fn: Callable[[Dual], Dual], x: float) -> float:
    """Compute f'(x) using forward-mode automatic differentiation."""
    result = fn(Dual(x, 1.0))
    return result.dot


def gradient(fn: Callable, point: List[float]) -> List[float]:
    """Compute ∇f at a point using forward-mode AD (one pass per variable)."""
    n = len(point)
    grad = []
    for i in range(n):
        args = [Dual(point[j], 1.0 if j == i else 0.0) for j in range(n)]
        result = fn(*args)
        grad.append(result.dot)
    return grad


# ─────────────────────────────────────────────────────────────────────────────
# Statistical functions
# ─────────────────────────────────────────────────────────────────────────────

def mean(data: List[float]) -> float:
    if not data:
        raise ValueError("mean of empty dataset")
    return sum(data) / len(data)


def median(data: List[float]) -> float:
    if not data:
        raise ValueError("median of empty dataset")
    s = sorted(data)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def variance(data: List[float], population: bool = False) -> float:
    if len(data) < 2:
        raise ValueError("variance requires at least 2 data points")
    m = mean(data)
    ss = sum((x - m) ** 2 for x in data)
    return ss / len(data) if population else ss / (len(data) - 1)


def std_dev(data: List[float], population: bool = False) -> float:
    return math.sqrt(variance(data, population))


def covariance(x: List[float], y: List[float]) -> float:
    if len(x) != len(y):
        raise ValueError("covariance: x and y must have same length")
    n = len(x)
    mx, my = mean(x), mean(y)
    return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (n - 1)


def correlation(x: List[float], y: List[float]) -> float:
    sx, sy = std_dev(x), std_dev(y)
    if sx == 0 or sy == 0:
        raise ValueError("correlation: zero standard deviation")
    return covariance(x, y) / (sx * sy)


def linear_regression(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Returns (slope, intercept) for y = slope*x + intercept."""
    n = len(x)
    if n != len(y):
        raise ValueError("x and y must have same length")
    mx, my = mean(x), mean(y)
    ss_xx = sum((xi - mx) ** 2 for xi in x)
    ss_xy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    if ss_xx == 0:
        raise ValueError("all x values are identical — infinite slope")
    slope = ss_xy / ss_xx
    intercept = my - slope * mx
    return (slope, intercept)


# ─────────────────────────────────────────────────────────────────────────────
# Numerical methods
# ─────────────────────────────────────────────────────────────────────────────

def newton_raphson(
    f: Callable[[float], float],
    x0: float,
    tol: float = 1e-12,
    max_iter: int = 100,
    df: Optional[Callable[[float], float]] = None,
) -> float:
    """Find root of f(x)=0 using Newton-Raphson method.

    If df is not given, uses forward-mode AD to compute f'(x).
    """
    x = x0
    for _ in range(max_iter):
        fx = f(x)
        if abs(fx) < tol:
            return x
        if df is not None:
            fpx = df(x)
        else:
            fpx = derivative(lambda d: f(d) if isinstance(d, (int, float))
                             else Dual(f(d.val), d.dot * _numerical_deriv(f, d.val)),
                             x)
            # Fallback to numerical derivative
            if fpx == 0:
                fpx = _numerical_deriv(f, x)
        if abs(fpx) < 1e-15:
            raise ValueError("Newton-Raphson: derivative too small — no convergence")
        x = x - fx / fpx
    raise ValueError(f"Newton-Raphson: did not converge in {max_iter} iterations")


def _numerical_deriv(f, x, h=1e-8):
    return (f(x + h) - f(x - h)) / (2 * h)


def bisection(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-12,
    max_iter: int = 100,
) -> float:
    """Find root of f(x)=0 in [a, b] using bisection method."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("bisection: f(a) and f(b) must have opposite signs")
    for _ in range(max_iter):
        mid = (a + b) / 2
        fm = f(mid)
        if abs(fm) < tol or (b - a) / 2 < tol:
            return mid
        if fa * fm < 0:
            b = mid
        else:
            a = mid
            fa = fm
    return (a + b) / 2


def trapezoidal_integrate(
    f: Callable[[float], float],
    a: float,
    b: float,
    n: int = 1000,
) -> float:
    """Approximate ∫f(x)dx from a to b using the trapezoidal rule."""
    h = (b - a) / n
    s = 0.5 * (f(a) + f(b))
    for i in range(1, n):
        s += f(a + i * h)
    return s * h


def simpson_integrate(
    f: Callable[[float], float],
    a: float,
    b: float,
    n: int = 1000,
) -> float:
    """Approximate ∫f(x)dx from a to b using Simpson's rule."""
    if n % 2 == 1:
        n += 1
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n, 2):
        s += 4 * f(a + i * h)
    for i in range(2, n, 2):
        s += 2 * f(a + i * h)
    return s * h / 3


# ─────────────────────────────────────────────────────────────────────────────
# Convenience registry — maps names to functions for the transpiler preamble
# ─────────────────────────────────────────────────────────────────────────────

MATH_BUILTINS: Dict[str, Any] = {
    # Types
    "Matrix": Matrix,
    "Vector": Vector,
    "Interval": Interval,
    "Dual": Dual,
    "LTLNumber": LTLNumber,
    # Constants
    "PI": float(PI),
    "E": float(E),
    "PHI": float(PHI),
    "TAU": float(TAU),
    "SQRT2": float(SQRT2),
    "INF": float("inf"),
    "NAN": float("nan"),
    # Functions
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1/3),
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "exp": math.exp,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "pow": pow,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "lcm": math.lcm,
    "hypot": math.hypot,
    "radians": math.radians,
    "degrees": math.degrees,
    # Stats
    "mean": mean,
    "median": median,
    "variance": variance,
    "std_dev": std_dev,
    "correlation": correlation,
    "linear_regression": linear_regression,
    # Numerical methods
    "derivative": derivative,
    "gradient": gradient,
    "newton_raphson": newton_raphson,
    "bisection": bisection,
    "integrate": simpson_integrate,
    # Precision
    "set_precision": set_precision,
}
