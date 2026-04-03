"""
Tests for the LATERALUS scientific computing library.
"""
import math
import pytest

from lateralus_lang.science import (
    CONSTANTS, Dimension, Quantity,
    meters, kilograms, seconds, newtons, joules, kelvin,
    euler_step, rk4_step, solve_ode, solve_ode_system,
    fft, ifft, power_spectrum, moving_average, convolve,
    normal_pdf, normal_cdf, poisson_pmf, exponential_pdf, binomial_pmf,
    lagrange_interpolate,
    METER, KILOGRAM, SECOND, NEWTON, JOULE, VELOCITY,
)


class TestConstants:
    def test_speed_of_light(self):
        assert CONSTANTS["c"] == 299_792_458.0

    def test_planck(self):
        assert abs(CONSTANTS["h"] - 6.626e-34) < 1e-36

    def test_boltzmann(self):
        assert abs(CONSTANTS["k_B"] - 1.381e-23) < 1e-25

    def test_avogadro(self):
        assert abs(CONSTANTS["N_A"] - 6.022e23) < 1e20

    def test_elementary_charge(self):
        assert abs(CONSTANTS["e"] - 1.602e-19) < 1e-21


class TestDimension:
    def test_multiplication(self):
        d = METER * SECOND
        assert d.L == 1
        assert d.T == 1

    def test_division(self):
        d = METER / SECOND
        assert d.L == 1
        assert d.T == -1

    def test_power(self):
        d = METER ** 2
        assert d.L == 2

    def test_is_dimensionless(self):
        assert Dimension().is_dimensionless
        assert not METER.is_dimensionless

    def test_velocity_dimension(self):
        assert VELOCITY == METER / SECOND

    def test_newton_dimension(self):
        # F = m·a = kg·m/s²
        expected = KILOGRAM * METER / (SECOND ** 2)
        assert NEWTON == expected

    def test_str(self):
        s = str(VELOCITY)
        assert "m" in s
        assert "s" in s


class TestQuantity:
    def test_add(self):
        a = meters(3)
        b = meters(4)
        c = a + b
        assert c.value == 7
        assert c.dimension == METER

    def test_add_dimension_mismatch(self):
        with pytest.raises(ValueError):
            meters(1) + seconds(1)

    def test_multiply(self):
        m = kilograms(10)
        a = Quantity(9.81, METER / (SECOND ** 2))
        f = m * a
        assert abs(f.value - 98.1) < 1e-10
        assert f.dimension == NEWTON

    def test_scalar_multiply(self):
        q = meters(5) * 3
        assert q.value == 15

    def test_divide(self):
        d = meters(100)
        t = seconds(10)
        v = d / t
        assert v.value == 10
        assert v.dimension == VELOCITY

    def test_power(self):
        a = meters(3)
        area = a ** 2
        assert area.value == 9
        assert area.dimension.L == 2

    def test_repr(self):
        q = meters(42)
        assert "42" in repr(q)
        assert "m" in repr(q)


class TestODESolvers:
    def test_euler_constant(self):
        # dy/dt = 1, y(0) = 0 => y(t) = t
        y1 = euler_step(lambda t, y: 1, 0, 0, 0.1)
        assert abs(y1 - 0.1) < 1e-10

    def test_rk4_exponential(self):
        # dy/dt = y, y(0) = 1 => y(t) = e^t
        ts, ys = solve_ode(lambda t, y: y, 1.0, (0, 1), 100, "rk4")
        assert abs(ys[-1] - math.e) < 1e-6

    def test_euler_exponential(self):
        ts, ys = solve_ode(lambda t, y: y, 1.0, (0, 1), 1000, "euler")
        assert abs(ys[-1] - math.e) < 0.01

    def test_rk4_more_accurate(self):
        # RK4 should be more accurate than Euler for the same step count
        _, ys_rk4 = solve_ode(lambda t, y: y, 1.0, (0, 1), 100, "rk4")
        _, ys_euler = solve_ode(lambda t, y: y, 1.0, (0, 1), 100, "euler")
        assert abs(ys_rk4[-1] - math.e) < abs(ys_euler[-1] - math.e)

    def test_solve_system(self):
        # Simple harmonic oscillator: y'' + y = 0
        # Convert to system: y1' = y2, y2' = -y1
        def f(t, y):
            return [y[1], -y[0]]

        ts, ys = solve_ode_system(f, [1.0, 0.0], (0, 2 * math.pi), 1000)
        # After one full period, should return close to initial conditions
        assert abs(ys[-1][0] - 1.0) < 0.01
        assert abs(ys[-1][1] - 0.0) < 0.01

    def test_solve_ode_returns_correct_length(self):
        ts, ys = solve_ode(lambda t, y: 0, 0, (0, 1), 50)
        assert len(ts) == 51
        assert len(ys) == 51


class TestFFT:
    def test_identity(self):
        signal = [1, 0, 0, 0]
        result = fft([complex(x) for x in signal])
        assert len(result) == 4
        # DC component should be 1
        assert abs(result[0] - 1) < 1e-10

    def test_constant_signal(self):
        signal = [1, 1, 1, 1]
        result = fft([complex(x) for x in signal])
        assert abs(result[0] - 4) < 1e-10
        for i in range(1, 4):
            assert abs(result[i]) < 1e-10

    def test_inverse(self):
        signal = [1, 2, 3, 4]
        transformed = fft([complex(x) for x in signal])
        recovered = ifft(transformed)
        for i in range(4):
            assert abs(recovered[i].real - signal[i]) < 1e-10

    def test_power_spectrum(self):
        signal = [math.sin(2 * math.pi * k / 8) for k in range(8)]
        ps = power_spectrum(signal)
        assert len(ps) == 4
        # Should have peak at frequency 1
        assert ps[1] > ps[0]

    def test_parseval(self):
        # Energy in time domain should equal energy in frequency domain
        signal = [1, 2, 3, 4, 5, 6, 7, 8]
        n = len(signal)
        time_energy = sum(x ** 2 for x in signal)
        freq = fft([complex(x) for x in signal])
        freq_energy = sum(abs(x) ** 2 for x in freq) / n
        assert abs(time_energy - freq_energy) < 1e-8


class TestSignalProcessing:
    def test_moving_average(self):
        data = [1, 2, 3, 4, 5]
        result = moving_average(data, 3)
        assert len(result) == 5
        assert result[0] == 1.0  # Only one value
        assert abs(result[2] - 2.0) < 1e-10  # Average of 1,2,3

    def test_convolve_identity(self):
        signal = [1, 2, 3]
        kernel = [1]
        result = convolve(signal, kernel)
        assert result == [1, 2, 3]

    def test_convolve_shift(self):
        signal = [1, 0, 0, 0]
        kernel = [0, 1]
        result = convolve(signal, kernel)
        assert result[0] == 0
        assert result[1] == 1


class TestDistributions:
    def test_normal_pdf_peak(self):
        # Peak at mu
        assert normal_pdf(0) > normal_pdf(1)
        assert normal_pdf(0) > normal_pdf(-1)

    def test_normal_pdf_symmetric(self):
        assert abs(normal_pdf(1) - normal_pdf(-1)) < 1e-15

    def test_normal_cdf_half(self):
        assert abs(normal_cdf(0) - 0.5) < 1e-10

    def test_normal_cdf_bounds(self):
        assert normal_cdf(-10) < 0.001
        assert normal_cdf(10) > 0.999

    def test_poisson_pmf(self):
        # P(X=0) when λ=1 should be e^(-1)
        assert abs(poisson_pmf(0, 1) - math.exp(-1)) < 1e-10

    def test_exponential_pdf(self):
        assert exponential_pdf(0, 1) == 1.0
        assert exponential_pdf(-1, 1) == 0.0

    def test_binomial_pmf(self):
        # Fair coin, n=2, P(X=1) = 0.5
        assert abs(binomial_pmf(1, 2, 0.5) - 0.5) < 1e-10

    def test_binomial_sum_to_one(self):
        total = sum(binomial_pmf(k, 10, 0.3) for k in range(11))
        assert abs(total - 1.0) < 1e-10


class TestInterpolation:
    def test_lagrange_exact(self):
        # Interpolate through known points of y = x^2
        points = [(0, 0), (1, 1), (2, 4)]
        assert abs(lagrange_interpolate(points, 1.5) - 2.25) < 1e-10

    def test_lagrange_linear(self):
        points = [(0, 0), (1, 1)]
        assert abs(lagrange_interpolate(points, 0.5) - 0.5) < 1e-10

    def test_lagrange_single_point(self):
        points = [(3, 7)]
        assert lagrange_interpolate(points, 3) == 7
