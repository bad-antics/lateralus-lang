import unittest
from lateralus_lang.math_engine import Vector


class TestVectorDimensions(unittest.TestCase):
    def test_mismatched_dimensions_raise_value_error(self):
        cases = [
            ([1, 2, 100], [10]),
            ([10], [1, 2, 100]),
            ([1, 2, 100], []),
            ([], [1, 2, 100]),
        ]
        for left, right in cases:
            a, b = Vector(left), Vector(right)
            with self.assertRaises(ValueError):
                _ = a + b
            with self.assertRaises(ValueError):
                _ = a - b
            with self.assertRaises(ValueError):
                _ = a.dot(b)

    def test_equal_dimensions_preserved(self):
        a = Vector([1, 2, 3])
        b = Vector([4, 5, 6])
        self.assertEqual((a + b)._data, [5, 7, 9])
        self.assertEqual((a - b)._data, [-3, -3, -3])
        self.assertEqual(a.dot(b), 32)

    def test_empty_vectors_preserved(self):
        a = Vector([])
        b = Vector([])
        self.assertEqual((a + b)._data, [])
        self.assertEqual((a - b)._data, [])
        self.assertEqual(a.dot(b), 0)


if __name__ == "__main__":
    unittest.main()
