"""
Lateralus Pattern Engine
Python implementation of pattern matching semantics for the Lateralus language.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class MatchResult:
    """Result of a pattern match operation."""
    def __init__(self, success: bool, bindings: Optional[Dict[str, Any]] = None):
        self.success = success
        self.bindings = dict(bindings) if bindings is not None else {}

    def __repr__(self) -> str:
        return f"MatchResult(success={self.success}, bindings={self.bindings})"


# Singleton-like constants should not be mutated or shared destructively.
# Instead, return fresh instances or copies where appropriate.
MATCH_FAILURE = MatchResult(success=False)


class Pattern:
    """Base class for patterns in Lateralus."""

    @staticmethod
    def wildcard() -> "WildcardPattern":
        return WildcardPattern()

    @staticmethod
    def literal(value: Any) -> "LiteralPattern":
        return LiteralPattern(value)

    @staticmethod
    def variable(name: str) -> "VariablePattern":
        return VariablePattern(name)

    @staticmethod
    def as_pat(inner: "Pattern", name: str) -> "AsPattern":
        return AsPattern(inner, name)

    @staticmethod
    def range_pat(start: Any, end: Any, inclusive: bool = True) -> "RangePattern":
        return RangePattern(start, end, inclusive)

    @staticmethod
    def guard(inner: "Pattern", condition: Callable[[Any, Dict[str, Any]], bool]) -> "GuardPattern":
        return GuardPattern(inner, condition)

    def match(self, value: Any) -> MatchResult:
        raise NotImplementedError("Subclasses must implement match().")


class WildcardPattern(Pattern):
    def match(self, value: Any) -> MatchResult:
        return MatchResult(success=True, bindings={})


class LiteralPattern(Pattern):
    def __init__(self, expected: Any):
        self.expected = expected

    def match(self, value: Any) -> MatchResult:
        if value == self.expected:
            return MatchResult(success=True, bindings={})
        return MATCH_FAILURE


class VariablePattern(Pattern):
    def __init__(self, name: str):
        self.name = name

    def match(self, value: Any) -> MatchResult:
        return MatchResult(success=True, bindings={self.name: value})


class AsPattern(Pattern):
    def __init__(self, inner: Pattern, name: str):
        self.inner = inner
        self.name = name

    def match(self, value: Any) -> MatchResult:
        res = self.inner.match(value)
        if res.success:
            bindings = dict(res.bindings)
            bindings[self.name] = value
            return MatchResult(success=True, bindings=bindings)
        return MATCH_FAILURE


class RangePattern(Pattern):
    def __init__(self, start: Any, end: Any, inclusive: bool = True):
        self.start = start
        self.end = end
        self.inclusive = inclusive

    def match(self, value: Any) -> MatchResult:
        if self.inclusive:
            in_range = self.start <= value <= self.end
        else:
            in_range = self.start <= value < self.end