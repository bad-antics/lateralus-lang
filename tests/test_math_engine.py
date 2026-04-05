"""
tests/test_math_engine.py — Tests for the LATERALUS Math Engine
"""
import math
import pytest
from lateralus_lang.math_engine import (
    LTLNumber, Matrix, Vector, Interval, Dual,
    dual_sin, dual_cos, dual_exp, dual_log, dual_sqrt,
    derivative, gradient,
    mean, median, variance, std_dev, correlation, linear_regression,
    newton_raphson, bisection, trapezoidal_integrate, simpson_integrate,
    set_precision,
)


# -------------------------------------------------------------------------
# LTLNumber
# -------------------------------------------------------------------------

class TestLTLNumber:
    def test_int_arithmetic(self):
        a = LTLNumber(10)
        b = LTLNumber(3)
        assert int(a + b) == 13
        assert int(a - b) == 7
        assert int(a * b) == 30

    def test_float_arithmetic(self):
        a = LTLNumber(1.5)
        b = LTLNumber(2.5)
        assert float(a + b) == pytest.approx(4.0)

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            LTLNumber(1) / LTLNumber(0)

    def test_comparison(self):
        assert LTLNumber(5) > LTLNumber(3)
        assert LTLNumber(3) < LTLNumber(5)
        assert LTLNumber(4) == LTLNumber(4)

    def test_negative(self):
        assert int(-LTLNumber(5)) == -5

    def test_power(self):
        assert int(LTLNumber(2) ** LTLNumber(10)) == 1024


# -------------------------------------------------------------------------
# Matrix
# -------------------------------------------------------------------------

class TestMatrix:
    def test_creation(self):
        m = Matrix([[1, 2], [3, 4]])
        assert m.shape == (2, 2)
        assert m[0][0] == 1
        assert m[1][1] == 4

    def test_identity(self):
        I = Matrix.identity(3)
        assert I[0][0] == 1
        assert I[0][1] == 0
        assert I[2][2] == 1

    def test_add(self):
        a = Matrix([[1, 2], [3, 4]])
        b = Matrix([[5, 6], [7, 8]])
        c = a + b
        assert c[0][0] == 6
        assert c[1][1] == 12

    def test_matmul(self):
        a = Matrix([[1, 2], [3, 4]])
        b = Matrix([[5, 6], [7, 8]])
        c = a @ b
        assert c[0][0] == 19  # 1*5 + 2*7
        assert c[0][1] == 22  # 1*6 + 2*8
        assert c[1][0] == 43  # 3*5 + 4*7
        assert c[1][1] == 50  # 3*6 + 4*8

    def test_transpose(self):
        m = Matrix([[1, 2, 3], [4, 5, 6]])
        t = m.T
        assert t.shape == (3, 2)
        assert t[0][0] == 1
        assert t[2][1] == 6

    def test_det_2x2(self):
        m = Matrix([[1, 2], [3, 4]])
        assert m.det() == pytest.approx(-2.0)

    def test_det_3x3(self):
        m = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 0]])
        assert m.det() == pytest.approx(27.0)

    def test_trace(self):
        m = Matrix([[1, 0], [0, 5]])
        assert m.trace() == 6

    def test_inverse(self):
        m = Matrix([[1, 2], [3, 4]])
        inv = m.inverse()
        product = m @ inv
        assert product[0][0] == pytest.approx(1.0, abs=1e-10)
        assert product[0][1] == pytest.approx(0.0, abs=1e-10)
        assert product[1][0] == pytest.approx(0.0, abs=1e-10)
        assert product[1][1] == pytest.approx(1.0, abs=1e-10)

    def test_singular_inverse(self):
        m = Matrix([[1, 2], [2, 4]])
        with pytest.raises(ValueError, match="singular"):
            m.inverse()

    def test_shape_mismatch(self):
        a = Matrix([[1, 2]])
        b = Matrix([[1], [2], [3]])
        with pytest.raises(ValueError, match="shape"):
            a + b


# -------------------------------------------------------------------------
# Vector
# -------------------------------------------------------------------------

class TestVector:
    def test_dot_product(self):
        a = Vector([1, 2, 3])
        b = Vector([4, 5, 6])
        assert a.dot(b) == 32  # 4 + 10 + 18

    def test_norm(self):
        v = Vector([3, 4])
        assert v.norm() == pytest.approx(5.0)

    def test_cross_product(self):
        i = Vector([1, 0, 0])
        j = Vector([0, 1, 0])
        k = i.cross(j)
        assert k[0] == 0
        assert k[1] == 0
        assert k[2] == 1

    def test_normalize(self):
        v = Vector([3, 4])
        n = v.normalize()
        assert n.norm() == pytest.approx(1.0)


# -------------------------------------------------------------------------
# Interval arithmetic
# -------------------------------------------------------------------------

class TestInterval:
    def test_add(self):
        a = Interval(1, 2)
        b = Interval(3, 4)
        c = a + b
        assert c.lo == 4
        assert c.hi == 6

    def test_mul(self):
        a = Interval(-1, 2)
        b = Interval(3, 4)
        c = a * b
        assert c.lo == -4
        assert c.hi == 8

    def test_contains(self):
        a = Interval(1, 5)
        assert a.contains(3)
        assert not a.contains(6)

    def test_div_by_zero(self):
        a = Interval(1, 2)
        b = Interval(-1, 1)
        with pytest.raises(ZeroDivisionError):
            a / b

    def test_pm(self):
        a = Interval.pm(10.0, 0.5)
        assert a.lo == 9.5
        assert a.hi == 10.5
        assert a.mid == pytest.approx(10.0)


# -------------------------------------------------------------------------
# Automatic differentiation
# -------------------------------------------------------------------------

class TestDual:
    def test_add(self):
        a = Dual(3, 1)
        b = Dual(4, 0)
        c = a + b
        assert c.val == 7
        assert c.dot == 1

    def test_mul(self):
        # d/dx(x * x) at x=3 = 2*3 = 6
        x = Dual(3, 1)
        result = x * x
        assert result.val == 9
        assert result.dot == 6

    def test_polynomial(self):
        # f(x) = x² + 2x + 1, f'(x) = 2x + 2
        # f'(3) = 8
        x = Dual(3.0, 1.0)
        result = x * x + 2 * x + 1
        assert result.val == pytest.approx(16.0)
        assert result.dot == pytest.approx(8.0)

    def test_derivative_function(self):
        # d/dx(x³) at x=2 = 12
        def f(x):
            return x * x * x
        assert derivative(f, 2.0) == pytest.approx(12.0)

    def test_dual_sin(self):
        # d/dx(sin(x)) = cos(x)
        x = Dual(0.0, 1.0)
        result = dual_sin(x)
        assert result.val == pytest.approx(0.0)
        assert result.dot == pytest.approx(1.0)  # cos(0) = 1

    def test_dual_exp(self):
        # d/dx(exp(x)) = exp(x)
        x = Dual(1.0, 1.0)
        result = dual_exp(x)
        assert result.val == pytest.approx(math.e)
        assert result.dot == pytest.approx(math.e)


# -------------------------------------------------------------------------
# Statistics
# -------------------------------------------------------------------------

class TestStatistics:
    def test_mean(self):
        assert mean([1, 2, 3, 4, 5]) == pytest.approx(3.0)

    def test_median_odd(self):
        assert median([1, 3, 5]) == 3

    def test_median_even(self):
        assert median([1, 2, 3, 4]) == pytest.approx(2.5)

    def test_variance(self):
        assert variance([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(4.571, abs=0.01)

    def test_std_dev(self):
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        assert std_dev(data) == pytest.approx(math.sqrt(variance(data)))

    def test_correlation_perfect(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert correlation(x, y) == pytest.approx(1.0)

    def test_linear_regression(self):
        x = [1, 2, 3, 4, 5]
        y = [2.1, 3.9, 6.2, 7.8, 10.1]
        slope, intercept = linear_regression(x, y)
        assert slope == pytest.approx(2.0, abs=0.1)
        assert intercept == pytest.approx(0.0, abs=0.5)


# -------------------------------------------------------------------------
# Numerical methods
# -------------------------------------------------------------------------

class TestNumericalMethods:
    def test_bisection_sqrt2(self):
        result = bisection(lambda x: x*x - 2, 1, 2)
        assert result == pytest.approx(math.sqrt(2), abs=1e-10)

    def test_trapezoidal(self):
        # ∫₀¹ x² dx = 1/3
        result = trapezoidal_integrate(lambda x: x*x, 0, 1, 10000)
        assert result == pytest.approx(1/3, abs=1e-4)

    def test_simpson(self):
        # ∫₀^π sin(x) dx = 2
        result = simpson_integrate(math.sin, 0, math.pi, 1000)
        assert result == pytest.approx(2.0, abs=1e-8)
