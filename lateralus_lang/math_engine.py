from typing import Sequence, Union, SupportsFloat

Number = Union[int, float, SupportsFloat]

def median(data: Sequence[Number]) -> float:
    """Compute the median of a sequence of numbers."""
    if not data:
        raise ValueError("median() arg is an empty sequence")
    
    s = sorted(data)
    n = len(s)
    
    if n % 2 == 1:
        return float(s[n // 2])
    else:
        left = s[n // 2 - 1]
        right = s[n // 2]
        
        # Try standard addition first to preserve precision (e.g. subnormals)
        try:
            val = (float(left) + float(right)) / 2.0
        except OverflowError:
            val = float('inf') if (float(left) > 0 or float(right) > 0) else float('-inf')
            
        # If result is infinite but both inputs are finite, use alternative computation
        if (val == float('inf') or val == float('-inf')):
            f_left = float(left)
            f_right = float(right)
            if f_left != float('inf') and f_left != float('-inf') and f_right != float('inf') and f_right != float('-inf'):
                return (f_left / 2.0) + (f_right / 2.0)
                
        return val