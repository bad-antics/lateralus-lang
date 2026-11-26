# -*- coding: utf-8 -*-
"""
Lateralus Standard Library - Math Engine
"""

import math
from typing import Sequence, Union

Number = Union[int, float]

def mean(data: Sequence[Number]) -> float:
    """Return the sample arithmetic mean of data."""
    if not data:
        raise ValueError("mean requires at least one data point")
    
    # If all elements are identical, the mean is equal to that element.
    # This prevents intermediate overflow (e.g. sum([1e308, 1e308]) -> inf).
    first = data[0]
    if all(x == first for x in data):
        return float(first)
    
    return sum(data) / len(data)