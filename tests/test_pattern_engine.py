"""
tests/test_pattern_engine.py
Tests for lateralus_lang.pattern_engine — structural pattern matching
"""

import os
import sys
from dataclasses import dataclass

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lateralus_lang.pattern_engine import (
    MATCH_FAILURE,
    MATCH_SUCCESS,
    ExhaustivenessChecker,
    MatchExpr,
    MatchResult,
    Pattern,
    PatternKind,
    get_pattern_builtins,
    match_pattern,
    parse_pattern,
)

# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------

class TestMatchResult:
    def test_success_is_truthy(self):
        assert bool(MatchResult(True)) is True

    def test_failure_is_falsy(self):
        assert bool(MatchResult(False)) is False

    def test_bindings_default_empty(self):
        r = MatchResult(True)
        assert r.bindings == {}

    def test_bindings_stored(self):
        r = MatchResult(True, {"x": 42})
        assert r.bindings["x"] == 42

    def test_merge_both_success(self):
        r1 = MatchResult(True, {"a": 1})
        r2 = MatchResult(True, {"b": 2})
        merged = r1.merge(r2)
        assert merged.matched
        assert merged.bindings == {"a": 1, "b": 2}

    def test_merge_one_failure(self):
        r1 = MatchResult(True, {"a": 1})
        r2 = MatchResult(False)
        assert not r1.merge(r2).matched

    def test_match_success_singleton(self):
        assert MATCH_SUCCESS.matched is True
        assert MATCH_FAILURE.matched is False


# ---------------------------------------------------------------------------
# Literal patterns
# ---------------------------------------------------------------------------

class TestLiteralPattern:
    def test_integer_match(self):
        p = Pattern.literal(42)
        assert match_pattern(42, p).matched

    def test_integer_no_match(self):
        p = Pattern.literal(42)
        assert not match_pattern(43, p).matched

    def test_string_match(self):
        p = Pattern.literal("hello")
        assert match_pattern("hello", p).matched

    def test_string_no_match(self):
        p = Pattern.literal("hello")
        assert not match_pattern("world", p).matched

    def test_bool_match(self):
        assert match_pattern(True, Pattern.literal(True)).matched
        assert not match_pattern(False, Pattern.literal(True)).matched

    def test_none_literal(self):
        assert match_pattern(None, Pattern.literal(None)).matched

    def test_type_strict(self):
        # int 1 should not match bool True even though 1 == True in Python
        p = Pattern.literal(1)
        assert not match_pattern(True, p).matched


# ---------------------------------------------------------------------------
# Wildcard and binding
# ---------------------------------------------------------------------------

class TestWildcardBinding:
    def test_wildcard_matches_anything(self):
        p = Pattern.wildcard()
        for v in [42, "str", None, [], {}, True, 3.14]:
            assert match_pattern(v, p).matched

    def test_wildcard_no_bindings(self):
        r = match_pattern(99, Pattern.wildcard())
        assert r.bindings == {}

    def test_binding_captures_value(self):
        p = Pattern.binding("x")
        r = match_pattern(42, p)
        assert r.matched
        assert r.bindings["x"] == 42

    def test_binding_any_value(self):
        p = Pattern.binding("val")
        for v in ["hello", 42, None, [1, 2, 3]]:
            r = match_pattern(v, p)
            assert r.matched
            assert r.bindings["val"] == v


# ---------------------------------------------------------------------------
# None check
# ---------------------------------------------------------------------------

class TestNoneCheck:
    def test_none_matches(self):
        assert match_pattern(None, Pattern.none_check()).matched

    def test_zero_does_not_match(self):
        assert not match_pattern(0, Pattern.none_check()).matched

    def test_empty_string_does_not_match(self):
        assert not match_pattern("", Pattern.none_check()).matched


# ---------------------------------------------------------------------------
# Type patterns
# ---------------------------------------------------------------------------

class TestTypePattern:
    def test_int_type(self):
        assert match_pattern(42, Pattern.type_pat("int")).matched
        assert not match_pattern("42", Pattern.type_pat("int")).matched

    def test_float_type(self):
        assert match_pattern(3.14, Pattern.type_pat("float")).matched
        assert not match_pattern(3, Pattern.type_pat("float")).matched

    def test_str_type(self):
        assert match_pattern("hello", Pattern.type_pat("str")).matched
        assert not match_pattern(42, Pattern.type_pat("str")).matched

    def test_bool_type(self):
        assert match_pattern(True, Pattern.type_pat("bool")).matched
        assert not match_pattern(1, Pattern.type_pat("bool")).matched

    def test_list_type(self):
        assert match_pattern([1, 2, 3], Pattern.type_pat("list")).matched
        assert not match_pattern((1, 2), Pattern.type_pat("list")).matched

    def test_dict_type(self):
        assert match_pattern({"a": 1}, Pattern.type_pat("dict")).matched
        assert not match_pattern([1], Pattern.type_pat("dict")).matched

    def test_any_type(self):
        p = Pattern.type_pat("any")
        for v in [1, "str", None, [], {}]:
            assert match_pattern(v, p).matched


# ---------------------------------------------------------------------------
# Range patterns
# ---------------------------------------------------------------------------

class TestRangePattern:
    def test_inclusive_range(self):
        p = Pattern.range_pat(1, 10)
        assert match_pattern(1, p).matched
        assert match_pattern(5, p).matched
        assert match_pattern(10, p).matched
        assert not match_pattern(0, p).matched
        assert not match_pattern(11, p).matched

    def test_exclusive_range(self):
        p = Pattern.range_pat(1, 10, inclusive=False)
        assert match_pattern(1, p).matched
        assert match_pattern(9, p).matched
        assert not match_pattern(10, p).matched
        assert not match_pattern(0, p).matched

    def test_float_range(self):
        p = Pattern.range_pat(0.0, 1.0)
        assert match_pattern(0.5, p).matched
        assert not match_pattern(1.5, p).matched


# ---------------------------------------------------------------------------
# List patterns
# ---------------------------------------------------------------------------

class TestListPattern:
    def test_empty_list(self):
        p = Pattern.list_pat()
        assert match_pattern([], p).matched
        assert not match_pattern([1], p).matched

    def test_fixed_list(self):
        p = Pattern.list_pat(Pattern.literal(1), Pattern.literal(2), Pattern.literal(3))
        assert match_pattern([1, 2, 3], p).matched
        assert not match_pattern([1, 2, 4], p).matched
        assert not match_pattern([1, 2], p).matched

    def test_list_with_bindings(self):
        p = Pattern.list_pat(Pattern.binding("head"), Pattern.binding("second"))
        r = match_pattern([10, 20], p)
        assert r.matched
        assert r.bindings["head"] == 10
        assert r.bindings["second"] == 20

    def test_list_with_rest(self):
        p = Pattern.list_pat(Pattern.binding("head"), rest="tail")
        r = match_pattern([1, 2, 3, 4], p)
        assert r.matched
        assert r.bindings["head"] == 1
        assert r.bindings["tail"] == [2, 3, 4]

    def test_list_with_wildcard_rest(self):
        p = Pattern.list_pat(Pattern.binding("first"), rest="_")
        r = match_pattern([99, 100, 101], p)
        assert r.matched
        assert r.bindings["first"] == 99

    def test_list_too_short(self):
        p = Pattern.list_pat(Pattern.binding("a"), Pattern.binding("b"), Pattern.binding("c"))
        assert not match_pattern([1, 2], p).matched


# ---------------------------------------------------------------------------
# Tuple patterns
# ---------------------------------------------------------------------------

class TestTuplePattern:
    def test_tuple_match(self):
        p = Pattern.tuple_pat(Pattern.literal(1), Pattern.literal(2))
        assert match_pattern((1, 2), p).matched

    def test_tuple_no_match(self):
        p = Pattern.tuple_pat(Pattern.literal(1), Pattern.literal(2))
        assert not match_pattern((1, 3), p).matched

    def test_tuple_with_bindings(self):
        p = Pattern.tuple_pat(Pattern.binding("x"), Pattern.binding("y"))
        r = match_pattern((10, 20), p)
        assert r.matched
        assert r.bindings == {"x": 10, "y": 20}

    def test_tuple_wrong_length(self):
        p = Pattern.tuple_pat(Pattern.binding("x"), Pattern.binding("y"))
        assert not match_pattern((1, 2, 3), p).matched


# ---------------------------------------------------------------------------
# Struct patterns
# ---------------------------------------------------------------------------

class TestStructPattern:
    def test_dict_struct(self):
        p = Pattern.struct("", {"name": Pattern.literal("Alice"), "age": Pattern.binding("age")})
        r = match_pattern({"name": "Alice", "age": 30}, p)
        assert r.matched
        assert r.bindings["age"] == 30

    def test_struct_missing_field(self):
        p = Pattern.struct("", {"x": Pattern.binding("x"), "y": Pattern.binding("y")})
        assert not match_pattern({"x": 1}, p).matched

    def test_dataclass_struct(self):
        @dataclass
        class Point:
            x: float
            y: float

        p = Pattern.struct("Point", {"x": Pattern.binding("px"), "y": Pattern.binding("py")})
        r = match_pattern(Point(3.0, 4.0), p)
        assert r.matched
        assert r.bindings["px"] == 3.0
        assert r.bindings["py"] == 4.0


# ---------------------------------------------------------------------------
# Guard patterns
# ---------------------------------------------------------------------------

class TestGuardPattern:
    def test_guard_passes(self):
        p = Pattern.guard(Pattern.binding("n"), lambda v, b: v > 0)
        r = match_pattern(5, p)
        assert r.matched
        assert r.bindings["n"] == 5

    def test_guard_fails(self):
        p = Pattern.guard(Pattern.binding("n"), lambda v, b: v > 0)
        assert not match_pattern(-1, p).matched

    def test_guard_uses_bindings(self):
        p = Pattern.guard(
            Pattern.list_pat(Pattern.binding("a"), Pattern.binding("b")),
            lambda v, b: b["a"] < b["b"]
        )
        assert match_pattern([1, 5], p).matched
        assert not match_pattern([5, 1], p).matched


# ---------------------------------------------------------------------------
# OR patterns
# ---------------------------------------------------------------------------

class TestOrPattern:
    def test_or_first_match(self):
        p = Pattern.or_pat(Pattern.literal(1), Pattern.literal(2), Pattern.literal(3))
        assert match_pattern(1, p).matched
        assert match_pattern(2, p).matched
        assert match_pattern(3, p).matched
        assert not match_pattern(4, p).matched

    def test_or_captures_from_first_matching(self):
        p = Pattern.or_pat(Pattern.binding("x"), Pattern.literal(99))
        r = match_pattern(42, p)
        assert r.matched
        assert r.bindings.get("x") == 42


# ---------------------------------------------------------------------------
# AND patterns
# ---------------------------------------------------------------------------

class TestAndPattern:
    def test_and_both_match(self):
        p = Pattern.and_pat(
            Pattern.type_pat("int"),
            Pattern.range_pat(0, 100)
        )
        assert match_pattern(50, p).matched
        assert not match_pattern(150, p).matched
        assert not match_pattern("50", p).matched

    def test_and_collects_bindings(self):
        p = Pattern.and_pat(
            Pattern.binding("x"),
            Pattern.range_pat(1, 10)
        )
        r = match_pattern(5, p)
        assert r.matched
        assert r.bindings["x"] == 5


# ---------------------------------------------------------------------------
# As patterns
# ---------------------------------------------------------------------------

class TestAsPattern:
    def test_as_captures_whole_value(self):
        p = Pattern.as_pat(
            Pattern.list_pat(Pattern.binding("head"), rest="tail"),
            "whole"
        )
        r = match_pattern([1, 2, 3], p)
        assert r.matched
        assert r.bindings["whole"] == [1, 2, 3]
        assert r.bindings["head"] == 1

    def test_as_fails_if_inner_fails(self):
        p = Pattern.as_pat(Pattern.literal(42), "val")
        assert not match_pattern(99, p).matched


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestRegexPattern:
    def test_regex_match(self):
        p = Pattern.regex_pat(r"^\d{3}-\d{4}$")
        assert match_pattern("555-1234", p).matched
        assert not match_pattern("555-12", p).matched

    def test_regex_named_groups(self):
        p = Pattern.regex_pat(r"(?P<year>\d{4})-(?P<month>\d{2})")
        r = match_pattern("2024-03", p)
        assert r.matched
        assert r.bindings.get("year") == "2024"
        assert r.bindings.get("month") == "03"

    def test_regex_non_string(self):
        p = Pattern.regex_pat(r"\d+")
        assert not match_pattern(42, p).matched


# ---------------------------------------------------------------------------
# MatchExpr
# ---------------------------------------------------------------------------

class TestMatchExpr:
    def test_first_matching_arm(self):
        result = (MatchExpr(0)
                  .arm(Pattern.literal(0), lambda b: "zero")
                  .arm(Pattern.range_pat(1, 9), lambda b: "small")
                  .arm(Pattern.wildcard(), lambda b: "other")
                  .execute())
        assert result == "zero"

    def test_fallthrough_to_second(self):
        result = (MatchExpr(5)
                  .arm(Pattern.literal(0), lambda b: "zero")
                  .arm(Pattern.range_pat(1, 9), lambda b: "small")
                  .arm(Pattern.wildcard(), lambda b: "other")
                  .execute())
        assert result == "small"

    def test_bindings_passed_to_body(self):
        result = (MatchExpr([1, 2, 3])
                  .arm(Pattern.list_pat(Pattern.binding("h"), rest="t"),
                       lambda b: b["h"] * 100 + len(b["t"]))
                  .execute())
        assert result == 102  # 1 * 100 + 2

    def test_default_arm(self):
        result = (MatchExpr(999)
                  .arm(Pattern.literal(0), lambda b: "zero")
                  .default(lambda: "default")
                  .execute())
        assert result == "default"

    def test_no_match_raises(self):
        with pytest.raises(ValueError, match="Non-exhaustive"):
            MatchExpr(42).arm(Pattern.literal(0), lambda b: "zero").execute()


# ---------------------------------------------------------------------------
# Pattern parser
# ---------------------------------------------------------------------------

class TestPatternParser:
    def test_parse_wildcard(self):
        p = parse_pattern("_")
        assert p.kind == PatternKind.WILDCARD

    def test_parse_integer(self):
        p = parse_pattern("42")
        assert p.kind == PatternKind.LITERAL
        assert p.value == 42

    def test_parse_string(self):
        p = parse_pattern('"hello"')
        assert p.kind == PatternKind.LITERAL
        assert p.value == "hello"

    def test_parse_true(self):
        p = parse_pattern("True")
        assert p.kind == PatternKind.LITERAL
        assert p.value is True

    def test_parse_none(self):
        p = parse_pattern("None")
        assert p.kind == PatternKind.NONE_CHECK

    def test_parse_binding(self):
        p = parse_pattern("name")
        assert p.kind == PatternKind.BINDING
        assert p.name == "name"

    def test_parse_range_inclusive(self):
        p = parse_pattern("1..10")
        assert p.kind == PatternKind.RANGE
        start, end, inclusive = p.value
        assert start == 1
        assert end == 10
        assert inclusive is True

    def test_parse_range_exclusive(self):
        p = parse_pattern("1..<10")
        assert p.kind == PatternKind.RANGE
        _, _, inclusive = p.value
        assert inclusive is False

    def test_parse_list(self):
        p = parse_pattern("[a, b, *rest]")
        assert p.kind == PatternKind.LIST
        assert len(p.children) == 2
        assert p.extra.get("rest") == "rest"

    def test_parse_or(self):
        p = parse_pattern("1|2|3")
        assert p.kind == PatternKind.OR
        assert len(p.children) == 3

    def test_parse_type(self):
        p = parse_pattern("int")
        assert p.kind == PatternKind.TYPE
        assert p.name == "int"

    def test_parse_struct(self):
        p = parse_pattern("Point{x, y}")
        assert p.kind == PatternKind.STRUCT
        assert p.name == "Point"


# ---------------------------------------------------------------------------
# Exhaustiveness checker
# ---------------------------------------------------------------------------

class TestExhaustivenessChecker:
    def test_wildcard_is_exhaustive(self):
        checker = ExhaustivenessChecker()
        patterns = [Pattern.literal(1), Pattern.wildcard()]
        is_ex, warnings = checker.check(patterns, "int")
        assert is_ex

    def test_binding_is_exhaustive(self):
        checker = ExhaustivenessChecker()
        patterns = [Pattern.binding("x")]
        is_ex, _ = checker.check(patterns, "int")
        assert is_ex

    def test_non_exhaustive_without_wildcard(self):
        checker = ExhaustivenessChecker()
        patterns = [Pattern.literal(1), Pattern.literal(2)]
        is_ex, warnings = checker.check(patterns, "int")
        assert not is_ex
        assert len(warnings) > 0

    def test_type_cover_is_exhaustive(self):
        checker = ExhaustivenessChecker()
        patterns = [Pattern.type_pat("int")]
        is_ex, _ = checker.check(patterns, "int")
        assert is_ex


# ---------------------------------------------------------------------------
# Builtins
# ---------------------------------------------------------------------------

class TestBuiltins:
    def test_get_pattern_builtins(self):
        builtins = get_pattern_builtins()
        assert "Pattern" in builtins
        assert "MatchExpr" in builtins
        assert "match_pattern" in builtins
        assert "parse_pattern" in builtins

    def test_pattern_factory_in_builtins(self):
        builtins = get_pattern_builtins()
        p = builtins["Pattern"].wildcard()
        assert p.kind == PatternKind.WILDCARD
