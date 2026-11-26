"""Lateralus Standard Library - Scientific Computing & Units.

Provides dimensioned quantities, unit conversions, and physical constants.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Union


class Dimension:
    """Represents physical dimensions (Mass, Length, Time, etc.)."""

    def __init__(self, name: str, base_units: str, exponents: Dict[str, int]):
        self.name = name
        self.base_units = base_units
        self.exponents = exponents  # e.g., {"m": 1, "s": -2} for acceleration

    def __repr__(self) -> str:
        parts = []
        for unit, exp in sorted(self.exponents.items()):
            if exp == 1:
                parts.append(unit)
            elif exp != 0:
                parts.append(f"{unit}^{exp}")
        return " ".join(parts) if parts else "dimensionless"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Dimension):
            return False
        return self.exponents == other.exponents


# Common Dimensions
DIM_DIMENSIONLESS = Dimension("dimensionless", "", {})
DIM_LENGTH = Dimension("length", "m", {"m": 1})
DIM_MASS = Dimension("mass", "kg", {"kg": 1})
DIM_TIME = Dimension("time", "s", {"s": 1})
DIM_CURRENT = Dimension("electric current", "A", {"A": 1})
DIM_TEMPERATURE = Dimension("temperature", "K", {"K": 1})
DIM_AMOUNT = Dimension("amount of substance", "mol", {"mol": 1})
DIM_LUMINOUS_INTENSITY = Dimension("luminous intensity", "cd", {"cd": 1})
DIM_AREA = Dimension("area", "m^2", {"m": 2})
DIM_VOLUME = Dimension("volume", "m^3", {"m": 3})
DIM_VELOCITY = Dimension("velocity", "m/s", {"m": 1, "s": -1})
DIM_ACCELERATION = Dimension("acceleration", "m/s^2", {"m": 1, "s": -2})
DIM_FORCE = Dimension("force", "N", {"kg": 1, "m": 1, "s": -2})
DIM_ENERGY = Dimension("energy", "J", {"kg": 1, "m": 2, "s": -2})
DIM_POWER = Dimension("power", "W", {"kg": 1, "m": 2, "s": -3})


class Quantity:
    """A numerical value with an associated physical dimension and unit."""

    def __init__(self, value: float, dimension: Dimension, unit_str: str = "", scale: float = 1.0):
        # Store the canonical base value internally.
        # value is given in terms of unit_str with given scale relative to base unit.
        self._base_value = value * scale
        self.dimension = dimension
        self.unit_str = unit_str or dimension.base_units
        self._scale = scale

    @property
    def value(self) -> float:
        """Return the value scaled to the current display unit."""
        if self._scale == 0.0:
            return self._base_value
        return self._base_value / self._scale

    def to(self, display_value: float, unit_str: str, scale: Optional[float] = None) -> Quantity:
        """Return a new Quantity with the same physical base measurement,
        but formatted/scaled to a new display unit.
        
        The underlying base value remains invariant, but the display representation
        is updated to `display_value` and `unit_str`.
        """
        # Determine the scale factor for the new unit string if not explicitly provided
        if scale is None:
            scale = self._infer_scale(unit_str, self.dimension)
            
        # The physical base value for this quantity is determined by the provided display_value and its scale
        new_base_value = display_value * scale
        
        q = Quantity.__new__(Quantity)
        q._base_value = new_base_value
        q.dimension = self.dimension
        q.unit_str = unit_str
        q._scale = scale
        return q

    def _infer_scale(self, unit_str: str, dimension: Dimension) -> float:
        """Infer scale factor relative to base unit."""
        if unit_str == dimension.base_units:
            return 1.0
        # Common metric prefixes / conversions
        prefixes = {
            "n": 1e-9,
            "u": 1e-6,
            "m": 1e-3,
            "c": 1e-2,
            "d": 1e-1,
            "h": 1e2,
            "k": 1e3,
            "M": 1e6,
            "G": 1e9,
        }
        if len(unit_str) > 1 and unit_str[0] in prefixes and unit_str[1:] == dimension.base_units:
            return prefixes[unit_str[0]]
        # If it's just the base unit or unknown, default to 1.0 or check if unit equals base
        return 1.0

    def __repr__(self) -> str:
        val = self.value
        if val.is_integer():
            val_str = str(int(val))
        else:
            val_str = str(val)
        if not self.unit_str:
            return f"{val_str} [{self.dimension}]"
        return f"{val_str} {self.unit_str}"

    def __add__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            raise TypeError("Can only add Quantity to Quantity")
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} + {other.dimension}")
        # Add using base values to ensure consistency across mixed display units
        new_base = self._base_value + other._base_value
        return Quantity(new_base, self.dimension, self.unit_str, self._scale)

    def __sub__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            raise TypeError("Can only subtract Quantity from Quantity")
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} - {other.dimension}")
        # Subtract using base values
        new_base = self._base_value - other._base_value
        return Quantity(new_base, self.dimension, self.unit_str, self._scale)

    def __mul__(self, other: Union[Quantity, float, int]) -> Quantity:
        if isinstance(other, (int, float)):
            return Quantity(self._base_value * other, self.dimension, self.unit_str, self._scale)
        elif isinstance(other, Quantity):
            # Combine dimensions and scales
            new_exponents = dict(self.dimension.exponents)
            for u, exp in other.dimension.exponents.items():
                new_exponents[u] = new_exponents.get(u, 0) + exp
            
            # Filter out zero exponents
            new_exponents = {u: exp for u, exp in new_exponents.items() if exp != 0}
            
            # Determine new dimension name / base
            dim_name = "compound"
            base_units_parts = []
            for u, exp in sorted(new_exponents.items()):
                if exp == 1:
                    base_units_parts.append(u)
                else:
                    base_units_parts.append(f"{u}^{exp}")
            base_units = " ".join(base_units_parts)
            new_dim = Dimension(dim_name, base_units, new_exponents)
            
            new_base = self._base_value * other._base_value
            return Quantity(new_base, new_dim, base_units, 1.0)
        raise TypeError("Invalid multiplier for Quantity")

    def __rmul__(self, other: Union[float, int]) -> Quantity:
        return self.__mul__(other)

    def __truediv__(self, other: Union[Quantity, float, int]) -> Quantity:
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Division by zero")
            return Quantity(self._base_value / other, self.dimension, self.unit_str, self._scale)
        elif isinstance(other, Quantity):
            if other._base_value == 0:
                raise ZeroDivisionError("Division by zero")
            if self.dimension == other.dimension:
                # Same dimension division yields dimensionless ratio
                ratio = self._base_value / other._base_value
                return Quantity(ratio, DIM_DIMENSIONLESS, "", 1.0)
            
            new_exponents = dict(self.dimension.exponents)
            for u, exp in other.dimension.exponents.items():
                new_exponents[u] = new_exponents.get(u, 0) - exp
            
            new_exponents = {u: exp for u, exp in new_exponents.items() if exp != 0}
            base_units_parts = []
            for u, exp in sorted(new_exponents.items()):
                if exp == 1:
                    base_units_parts.append(u)
                else:
                    base_units_parts.append(f"{u}^{exp}")
            base_units = " ".join(base_units_parts)
            new_dim = Dimension("compound", base_units, new_exponents)
            
            new_base = self._base_value / other._base_value
            return Quantity(new_base, new_dim, base_units, 1.0)
        raise TypeError("Invalid divisor for Quantity")


# --- Convenience Constructors ---

def meters(v: float) -> Quantity:
    return Quantity(v, DIM_LENGTH, "m", 1.0)

def centimeters(v: float) -> Quantity:
    return Quantity(v, DIM_LENGTH, "cm", 1e-2)

def kilometers(v: float) -> Quantity:
    return Quantity(v, DIM_LENGTH, "km", 1e3)

def kilograms(v: float) -> Quantity:
    return Quantity(v, DIM_MASS, "kg", 1.0)

def grams(v: float) -> Quantity:
    return Quantity(v, DIM_MASS, "g", 1e-3)

def seconds(v: float) -> Quantity:
    return Quantity(v, DIM_TIME, "s", 1.0)

def milliseconds(v: float) -> Quantity:
    return Quantity(v, DIM_TIME, "ms", 1e-3)

def Newtons(v: float) -> Quantity:
    return Quantity(v, DIM_FORCE, "N", 1.0)

def Joules(v: float) -> Quantity:
    return Quantity(v, DIM_ENERGY, "J", 1.0)

def Watts(v: float) -> Quantity:
    return Quantity(v, DIM_POWER, "W", 1.0)