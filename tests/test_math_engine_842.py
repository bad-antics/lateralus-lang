"""
tests/test_math_engine_842.py — Regression tests for issue #842.

Matrix.trace() and Matrix.__matmul__ use Python's built-in sum(), which starts
accumulating from int 0. When matrix entries are LTLNumber instances, the very
first addition is ``0 + LTLNumber(...)``. Without LTLNumber.__radd__ this raised
``TypeError: unsupported operand type(s) for +: 'int' and 'LTLNumber'``.

These tests pin the exact reproducer from the issue plus a plain-int control.
"""
from lateralus_lang.math_engine import LTLNumber, Matrix


def _ltl_matrix():
    return Matrix([[LTLNumber(1), LTLNumber(2)],
                   [LTLNumber(3), LTLNumber(4)]])


class TestIssue842:
    def test_trace_of_ltlnumber_matrix(self):
        a = _ltl_matrix()
        t = a.trace()
        # trace == 5, and the result is still an LTLNumber (type preserved).
        assert isinstance(t, LTLNumber)
        assert int(t) == 5
        assert t == 5

    def test_matmul_by_identity_preserves_ltlnumber_entries(self):
        a = _ltl_matrix()
        result = (a @ Matrix.identity(2)).to_list()
        assert [[int(v) for v in row] for row in result] == [[1, 2], [3, 4]]
        # LTLNumber entries are retained through matmul.
        for row in result:
            for v in row:
                assert isinstance(v, LTLNumber)

    def test_radd_with_plain_int(self):
        # Reflected addition: int + LTLNumber must promote, not raise.
        assert int(0 + LTLNumber(7)) == 7
        assert int(sum([LTLNumber(1), LTLNumber(2), LTLNumber(3)])) == 6

    def test_plain_int_matrix_control(self):
        # Control: plain-int matrices keep working exactly as before.
        m = Matrix([[1, 2], [3, 4]])
        assert m.trace() == 5
        assert (m @ Matrix.identity(2)).to_list() == [[1, 2], [3, 4]]