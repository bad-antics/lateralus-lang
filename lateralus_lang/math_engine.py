from decimal import Decimal, getcontext
import operator

class LTLNumber:
    def __init__(self, value):
        if isinstance(value, Decimal):
            self.value = value
        elif isinstance(value, (int, float, str)):
            self.value = Decimal(str(value))
        else:
            raise TypeError(f"Cannot convert {type(value)} to LTLNumber")

    def __add__(self, other):
        return _coerce_op(operator.add, self, other)

    def __sub__(self, other):
        return _coerce_op(operator.sub, self, other)

    def __mul__(self, other):
        return _coerce_op(operator.mul, self, other)

    def __truediv__(self, other):
        if isinstance(other, LTLNumber):
            other_val = other.value
        else:
            try:
                other_val = Decimal(str(other))
            except Exception:
                return NotImplemented
        
        # Perform division directly using Decimal to avoid float intermediate,
        # preserving context precision and avoiding float OverflowError.
        return LTLNumber(self.value / other_val)

    def __floordiv__(self, other):
        return _coerce_op(operator.floordiv, self, other)

    def __mod__(self, other):
        return _coerce_op(operator.mod, self, other)

    def __pow__(self, other):
        return _coerce_op(operator.pow, self, other)

    def __repr__(self):
        return f"LTLNumber({repr(self.value)})"

    def __eq__(self, other):
        if isinstance(other, LTLNumber):
            return self.value == other.value
        try:
            return self.value == Decimal(str(other))
        except Exception:
            return False

def _coerce_op(op, a, b):
    if not isinstance(a, LTLNumber):
        a = LTLNumber(a)
    if not isinstance(b, LTLNumber):
        b = LTLNumber(b)
    
    # For operations other than truediv, maintain existing behavior or use decimal where applicable
    if op is operator.truediv:
        return LTLNumber(a.value / b.value)
    
    res = op(a.value, b.value)
    if isinstance(res, Decimal):
        return LTLNumber(res)
    return LTLNumber(str(res))