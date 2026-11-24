import unittest
from lateralus_lang.pattern_engine import match_pattern, Pattern, PatternKind


class TestAsPatternNoLeak(unittest.TestCase):
    def test_as_pattern_does_not_leak_across_matches(self):
        as_pat = Pattern(PatternKind.AS, children=[Pattern.wildcard()], name="x")
        wild_pat = Pattern.wildcard()

        r1 = match_pattern(42, as_pat)
        self.assertTrue(r1.matched)
        self.assertEqual(r1.bindings, {"x": 42})

        r2 = match_pattern(99, wild_pat)
        self.assertTrue(r2.matched)
        self.assertEqual(r2.bindings, {})

        as_pat2 = Pattern(PatternKind.AS, children=[Pattern.wildcard()], name="y")
        r3 = match_pattern(7, as_pat2)
        self.assertTrue(r3.matched)
        self.assertEqual(r3.bindings, {"y": 7})
        self.assertEqual(r1.bindings, {"x": 42})


if __name__ == "__main__":
    unittest.main()
