"""
LATERALUS Scientific Computing Library
Julia-inspired scientific computing for LATERALUS.

Provides:
  - Physical constants (CODATA 2018)
  - Unit system with dimensional analysis
  - ODE solvers (Euler, RK4)
  - FFT (Cooley-Tukey)
  - Signal processing basics
  - Statistical distributions
"""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Callable

# --- Physical Constants (CODATA 2018) ---------------------------------

CONSTANTS = {
    # Fundamental
    "c": 299_792_458.0,               # speed of light [m/s]
    "h": 6.62607015e-34,              # Planck constant [J·s]
    "hbar": 1.054571817e-34,          # reduced Planck [J·s]
    "G": 6.67430e-11,                 # gravitational constant [m³/(kg·s²)]
    "e": 1.602176634e-19,             # elementary charge [C]
    "k_B": 1.380649e-23,              # Boltzmann constant [J/K]
    "N_A": 6.02214076e23,             # Avogadro number [1/mol]
    "R": 8.314462618,                 # gas constant [J/(mol·K)]
    "sigma": 5.670374419e-8,          # Stefan-Boltzmann [W/(m²·K⁴)]
    "epsilon_0": 8.8541878128e-12,    # vacuum permittivity [F/m]
    "mu_0": 1.25663706212e-6,         # vacuum permeability [H/m]

    # Particle masses
    "m_e": 9.1093837015e-31,          # electron mass [kg]
    "m_p": 1.67262192369e-27,         # proton mass [kg]
    "m_n": 1.67492749804e-27,         # neutron mass [kg]

    # Astronomical
    "AU": 1.495978707e11,             # astronomical unit [m]
    "ly": 9.4607304725808e15,         # light-year [m]
    "pc": 3.0856775814913673e16,      # parsec [m]
    "M_sun": 1.989e30,               # solar mass [kg]
    "R_sun": 6.957e8,                # solar radius [m]
    "L_sun": 3.828e26,               # solar luminosity [W]
    "M_earth": 5.972e24,             # Earth mass [kg]
    "R_earth": 6.371e6,              # Earth radius [m]
    "g": 9.80665,                     # standard gravity [m/s²]
}


# --- Unit System -------------------------------------------------------

@dataclass(frozen=True)
class Dimension:
    """SI dimension vector [length, mass, time, current, temperature, amount, luminosity]."""
    L: int = 0  # length (meter)
    M: int = 0  # mass (kilogram)
    T: int = 0  # time (second)
    I: int = 0  # current (ampere)
    Θ: int = 0  # temperature (kelvin)
    N: int = 0  # amount (mole)
    J: int = 0  # luminosity (candela)

    def __mul__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            self.L + other.L, self.M + other.M, self.T + other.T,
            self.I + other.I, self.Θ + other.Θ, self.N + other.N, self.J + other.J,
        )

    def __truediv__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            self.L - other.L, self.M - other.M, self.T - other.T,
            self.I - other.I, self.Θ - other.Θ, self.N - other.N, self.J - other.J,
        )

    def __pow__(self, n: int) -> "Dimension":
        return Dimension(
            self.L * n, self.M * n, self.T * n,
            self.I * n, self.Θ * n, self.N * n, self.J * n,
        )

    @property
    def is_dimensionless(self) -> bool:
        return all(v == 0 for v in (self.L, self.M, self.T, self.I, self.Θ, self.N, self.J))

    def __str__(self) -> str:
        parts = []
        names = ["m", "kg", "s", "A", "K", "mol", "cd"]
        values = [self.L, self.M, self.T, self.I, self.Θ, self.N, self.J]
        for name, val in zip(names, values):
            if val == 1:
                parts.append(name)
            elif val != 0:
                parts.append(f"{name}^{val}")
        return "·".join(parts) if parts else "dimensionless"


# Common dimensions
DIMENSIONLESS = Dimension()
METER = Dimension(L=1)
KILOGRAM = Dimension(M=1)
SECOND = Dimension(T=1)
AMPERE = Dimension(I=1)
KELVIN = Dimension(Θ=1)
MOLE = Dimension(N=1)
NEWTON = Dimension(L=1, M=1, T=-2)
JOULE = Dimension(L=2, M=1, T=-2)
WATT = Dimension(L=2, M=1, T=-3)
PASCAL = Dimension(L=-1, M=1, T=-2)
VELOCITY = Dimension(L=1, T=-1)
ACCELERATION = Dimension(L=1, T=-2)


@dataclass
class Quantity:
    """A physical quantity with units."""
    value: float
    dimension: Dimension
    unit_name: str = ""

    def __add__(self, other: "Quantity") -> "Quantity":
        if self.dimension != other.dimension:
            raise ValueError(f"Cannot add {self.dimension} and {other.dimension}")
        return Quantity(self.value + other.value, self.dimension)

    def __sub__(self, other: "Quantity") -> "Quantity":
        if self.dimension != other.dimension:
            raise ValueError(f"Cannot subtract {self.dimension} from {other.dimension}")
        return Quantity(self.value - other.value, self.dimension)

    def __mul__(self, other):
        if isinstance(other, Quantity):
            return Quantity(self.value * other.value, self.dimension * other.dimension)
        return Quantity(self.value * other, self.dimension)

    def __rmul__(self, other):
        return Quantity(self.value * other, self.dimension)

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            return Quantity(self.value / other.value, self.dimension / other.dimension)
        return Quantity(self.value / other, self.dimension)

    def __pow__(self, n):
        return Quantity(self.value ** n, self.dimension ** n)

    def __repr__(self):
        if self.unit_name:
            return f"{self.value} {self.unit_name}"
        return f"{self.value} [{self.dimension}]"

    def to(self, factor: float, unit_name: str = "") -> "Quantity":
        """Convert to different units."""
        return Quantity(self.value * factor, self.dimension, unit_name)


# Convenience constructors
def meters(v: float) -> Quantity: return Quantity(v, METER, "m")
def kilograms(v: float) -> Quantity: return Quantity(v, KILOGRAM, "kg")
def seconds(v: float) -> Quantity: return Quantity(v, SECOND, "s")
def newtons(v: float) -> Quantity: return Quantity(v, NEWTON, "N")
def joules(v: float) -> Quantity: return Quantity(v, JOULE, "J")
def watts(v: float) -> Quantity: return Quantity(v, WATT, "W")
def kelvin(v: float) -> Quantity: return Quantity(v, KELVIN, "K")


# --- ODE Solvers -------------------------------------------------------

def euler_step(f: Callable, t: float, y: float, h: float) -> float:
    """Single Euler step: y_{n+1} = y_n + h * f(t_n, y_n)"""
    return y + h * f(t, y)


def rk4_step(f: Callable, t: float, y: float, h: float) -> float:
    """Single RK4 step."""
    k1 = f(t, y)
    k2 = f(t + h/2, y + h*k1/2)
    k3 = f(t + h/2, y + h*k2/2)
    k4 = f(t + h, y + h*k3)
    return y + (h/6) * (k1 + 2*k2 + 2*k3 + k4)


def solve_ode(f: Callable, y0: float, t_span: tuple[float, float],
              n_steps: int = 100, method: str = "rk4") -> tuple[list[float], list[float]]:
    """
    Solve an ODE: dy/dt = f(t, y), y(t0) = y0

    Args:
        f: Right-hand side function f(t, y)
        y0: Initial condition
        t_span: (t_start, t_end)
        n_steps: Number of steps
        method: "euler" or "rk4"

    Returns:
        (t_values, y_values)
    """
    t0, t1 = t_span
    h = (t1 - t0) / n_steps

    ts = [t0]
    ys = [y0]

    step_fn = rk4_step if method == "rk4" else euler_step

    t, y = t0, y0
    for _ in range(n_steps):
        y = step_fn(f, t, y, h)
        t += h
        ts.append(t)
        ys.append(y)

    return ts, ys


def solve_ode_system(f: Callable, y0: list[float], t_span: tuple[float, float],
                     n_steps: int = 100) -> tuple[list[float], list[list[float]]]:
    """
    Solve a system of ODEs using RK4.
    f(t, y) -> list of derivatives
    y0: list of initial conditions
    """
    t0, t1 = t_span
    h = (t1 - t0) / n_steps
    dim = len(y0)

    ts = [t0]
    ys = [list(y0)]

    t = t0
    y = list(y0)

    for _ in range(n_steps):
        k1 = f(t, y)
        k2 = f(t + h/2, [y[i] + h*k1[i]/2 for i in range(dim)])
        k3 = f(t + h/2, [y[i] + h*k2[i]/2 for i in range(dim)])
        k4 = f(t + h, [y[i] + h*k3[i] for i in range(dim)])

        y = [y[i] + (h/6) * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i]) for i in range(dim)]
        t += h

        ts.append(t)
        ys.append(list(y))

    return ts, ys


# --- FFT (Cooley-Tukey) -----------------------------------------------

def fft(x: list[complex]) -> list[complex]:
    """Fast Fourier Transform (radix-2 Cooley-Tukey)."""
    n = len(x)
    if n <= 1:
        return list(x)

    if n & (n - 1) != 0:
        # Pad to next power of 2
        next_pow2 = 1
        while next_pow2 < n:
            next_pow2 <<= 1
        x = list(x) + [0] * (next_pow2 - n)
        n = next_pow2

    if n == 1:
        return list(x)

    even = fft(x[0::2])
    odd = fft(x[1::2])

    result = [0] * n
    for k in range(n // 2):
        w = cmath.exp(-2j * cmath.pi * k / n) * odd[k]
        result[k] = even[k] + w
        result[k + n // 2] = even[k] - w

    return result


def ifft(x: list[complex]) -> list[complex]:
    """Inverse FFT."""
    n = len(x)
    conjugated = [z.conjugate() for z in x]
    result = fft(conjugated)
    return [z.conjugate() / n for z in result]


def power_spectrum(x: list[float]) -> list[float]:
    """Compute the power spectrum of a real signal."""
    X = fft([complex(v) for v in x])
    return [abs(v) ** 2 for v in X[:len(X) // 2]]


# --- Signal Processing ------------------------------------------------

def moving_average(data: list[float], window: int) -> list[float]:
    """Simple moving average filter."""
    if window < 1:
        raise ValueError("Window must be >= 1")
    result = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        result.append(sum(data[start:i + 1]) / (i - start + 1))
    return result


def convolve(signal: list[float], kernel: list[float]) -> list[float]:
    """Linear convolution."""
    n = len(signal)
    m = len(kernel)
    result = [0.0] * (n + m - 1)
    for i in range(n):
        for j in range(m):
            result[i + j] += signal[i] * kernel[j]
    return result


def cross_correlate(x: list[float], y: list[float]) -> list[float]:
    """Cross-correlation of two signals."""
    return convolve(x, list(reversed(y)))


def downsample(data: list[float], factor: int) -> list[float]:
    """Downsample by integer factor."""
    return data[::factor]


def upsample(data: list[float], factor: int) -> list[float]:
    """Upsample by integer factor (zero-insert)."""
    result = []
    for v in data:
        result.append(v)
        result.extend([0.0] * (factor - 1))
    return result


# --- Statistical Distributions ----------------------------------------

def normal_pdf(x: float, mu: float = 0, sigma: float = 1) -> float:
    """Normal (Gaussian) probability density function."""
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))


def normal_cdf(x: float, mu: float = 0, sigma: float = 1) -> float:
    """Normal cumulative distribution function (via erf)."""
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def poisson_pmf(k: int, lam: float) -> float:
    """Poisson probability mass function."""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def exponential_pdf(x: float, lam: float = 1) -> float:
    """Exponential probability density function."""
    if x < 0:
        return 0.0
    return lam * math.exp(-lam * x)


def binomial_pmf(k: int, n: int, p: float) -> float:
    """Binomial probability mass function."""
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def chi_squared_pdf(x: float, k: int) -> float:
    """Chi-squared probability density function."""
    if x <= 0:
        return 0.0
    half_k = k / 2
    return (x ** (half_k - 1) * math.exp(-x / 2)) / (2 ** half_k * math.gamma(half_k))


# --- Interpolation ----------------------------------------------------

def lagrange_interpolate(points: list[tuple[float, float]], x: float) -> float:
    """Lagrange polynomial interpolation."""
    n = len(points)
    result = 0.0
    for i in range(n):
        xi, yi = points[i]
        basis = yi
        for j in range(n):
            if i != j:
                xj, _ = points[j]
                basis *= (x - xj) / (xi - xj)
        result += basis
    return result


def cubic_spline(points: list[tuple[float, float]], x: float) -> float:
    """Natural cubic spline interpolation (simplified)."""
    n = len(points)
    if n < 2:
        return points[0][1] if points else 0.0

    # Find the interval
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] * (1 - t) + ys[i + 1] * t

    # Extrapolate
    if x < xs[0]:
        return ys[0]
    return ys[-1]


# --- LATERALUS Integration --------------------------------------------

SCIENCE_BUILTINS = {
    # Constants
    "speed_of_light": lambda: CONSTANTS["c"],
    "planck_constant": lambda: CONSTANTS["h"],
    "boltzmann_constant": lambda: CONSTANTS["k_B"],
    "avogadro_number": lambda: CONSTANTS["N_A"],
    "gravitational_constant": lambda: CONSTANTS["G"],
    "elementary_charge": lambda: CONSTANTS["e"],
    "electron_mass": lambda: CONSTANTS["m_e"],
    "proton_mass": lambda: CONSTANTS["m_p"],

    # Distributions
    "normal_pdf": normal_pdf,
    "normal_cdf": normal_cdf,
    "poisson_pmf": poisson_pmf,
    "exponential_pdf": exponential_pdf,
    "binomial_pmf": binomial_pmf,

    # Signal processing
    "moving_average": moving_average,
    "fft": lambda x: [abs(v) for v in fft([complex(v) for v in x])],
    "power_spectrum": power_spectrum,

    # ODE
    "solve_ode_euler": lambda f, y0, t0, t1, n=100: solve_ode(f, y0, (t0, t1), n, "euler"),
    "solve_ode_rk4": lambda f, y0, t0, t1, n=100: solve_ode(f, y0, (t0, t1), n, "rk4"),

    # Interpolation
    "lagrange_interpolate": lagrange_interpolate,

    # Unit constructors
    "meters": meters,
    "kilograms": kilograms,
    "seconds": seconds,
    "newtons": newtons,
    "joules": joules,
    "watts": watts,
    "kelvin_unit": kelvin,
}
