"""Regression coverage for Vector operations with incompatible dimensions."""
import unittest

from lateralus_lang.math_engine import Vector


class VectorDimensionTests(unittest.TestCase):
    mismatches = (([1, 2, 100], [10]), ([10], [1, 2, 100]), ([1], []), ([], [1]))

    def test_add_rejects_mismatched_dimensions(self):
        for left, right in self.mismatches:
            with self.subTest(left=left, right=right):
                with self.assertRaisesRegex(ValueError, "dimension"):
                    Vector(left) + Vector(right)

    def test_subtract_rejects_mismatched_dimensions(self):
        for left, right in self.mismatches:
            with self.subTest(left=left, right=right):
                with self.assertRaisesRegex(ValueError, "dimension"):
                    Vector(left) - Vector(right)

    def test_dot_rejects_mismatched_dimensions(self):
        for left, right in self.mismatches:
            with self.subTest(left=left, right=right):
                with self.assertRaisesRegex(ValueError, "dimension"):
                    Vector(left).dot(Vector(right))

    def test_equal_dimension_addition(self):
        result = Vector([1, 2, 3]) + Vector([4, 5, 6])
        self.assertEqual(list(result), [5, 7, 9])

    def test_equal_dimension_subtraction(self):
        result = Vector([1, 2, 3]) - Vector([4, 5, 6])
        self.assertEqual(list(result), [-3, -3, -3])

    def test_equal_dimension_dot_product(self):
        self.assertEqual(Vector([1, 2, 3]).dot(Vector([4, 5, 6])), 32)

    def test_empty_addition_is_preserved(self):
        self.assertEqual(list(Vector([]) + Vector([])), [])

    def test_empty_subtraction_is_preserved(self):
        self.assertEqual(list(Vector([]) - Vector([])), [])

    def test_empty_dot_product_is_preserved(self):
        self.assertEqual(Vector([]).dot(Vector([])), 0)


if __name__ == "__main__":
    unittest.main()
