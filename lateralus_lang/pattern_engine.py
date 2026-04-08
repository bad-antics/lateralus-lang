"""
lateralus_lang/pattern_engine.py
LATERALUS Pattern Matching Engine

Provides structural pattern matching beyond Python's `match` statement.
Supports:
  - Literal patterns:    42, "hello", True, None
  - Wildcard:            _
  - Binding:             name  (captures into variable)
  - Struct patterns:     Point { x: 0, y: _ }
  - List patterns:       [head, *tail]
  - Tuple patterns:      (a, b, c)
  - Range patterns:      1..10 (inclusive), 1..<10 (exclusive)
  - Guard patterns:      x if x > 0
  - OR patterns:         Red | Blue | Green
  - AND patterns:        x & int_guard
  - Type patterns:       int, float, str, bool, list
  - Regex patterns:      /^[A-Z]/
  - Deep path binding:   as-patterns: pattern @ name

The engine is used by the LATERALUS `match` expression compiler to implement
exhaustiveness checking and efficient decision trees.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Match result
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """Result of matching a value against a pattern."""
    matched: bool
    bindings: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.matched

    def merge(self, other: "MatchResult") -> "MatchResult":
        if not self.matched or not other.matched:
            return MatchResult(False)
        merged = {**self.bindings, **other.bindings}
        return MatchResult(True, merged)


MATCH_SUCCESS = MatchResult(True)
MATCH_FAILURE = MatchResult(False)


# ---------------------------------------------------------------------------
# Pattern kinds
# ---------------------------------------------------------------------------

class PatternKind(Enum):
    LITERAL    = auto()  # exact value
    WILDCARD   = auto()  # _  (matches anything, binds nothing)
    BINDING    = auto()  # name (matches anything, binds value)
    STRUCT     = auto()  # StructName { field: pattern, ... }
    LIST       = auto()  # [head, *tail] or [a, b, c]
    TUPLE      = auto()  # (a, b, c)
    RANGE      = auto()  # start..end or start..<end
    GUARD      = auto()  # pattern if predicate
    OR         = auto()  # pattern | pattern
    AND        = auto()  # pattern & pattern
    TYPE       = auto()  # int / float / str / list / dict
    REGEX      = auto()  # /regex/
    AS         = auto()  # pattern @ name
    NONE_CHECK = auto()  # None
    REST       = auto()  # *name (rest binding in list)


# ---------------------------------------------------------------------------
# Pattern nodes
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    kind: PatternKind
    value: Any = None
    children: list["Pattern"] = field(default_factory=list)
    name: str = ""
    extra: dict = field(default_factory=dict)

    # ---- Factories -------------------------------------------------------

    @staticmethod
    def literal(v: Any) -> "Pattern":
        return Pattern(PatternKind.LITERAL, value=v)

    @staticmethod
    def wildcard() -> "Pattern":
        return Pattern(PatternKind.WILDCARD)

    @staticmethod
    def binding(name: str) -> "Pattern":
        return Pattern(PatternKind.BINDING, name=name)

    @staticmethod
    def struct(type_name: str, fields: dict[str, "Pattern"]) -> "Pattern":
        return Pattern(PatternKind.STRUCT, name=type_name, extra={"fields": fields})

    @staticmethod
    def list_pat(*elements: "Pattern", rest: Optional[str] = None) -> "Pattern":
        return Pattern(PatternKind.LIST, children=list(elements), extra={"rest": rest})

    @staticmethod
    def tuple_pat(*elements: "Pattern") -> "Pattern":
        return Pattern(PatternKind.TUPLE, children=list(elements))

    @staticmethod
    def range_pat(start: Any, end: Any, inclusive: bool = True) -> "Pattern":
        return Pattern(PatternKind.RANGE, value=(start, end, inclusive))

    @staticmethod
    def guard(inner: "Pattern", predicate: Callable[[Any, dict], bool]) -> "Pattern":
        return Pattern(PatternKind.GUARD, children=[inner], extra={"pred": predicate})

    @staticmethod
    def or_pat(*alternatives: "Pattern") -> "Pattern":
        return Pattern(PatternKind.OR, children=list(alternatives))

    @staticmethod
    def and_pat(*patterns: "Pattern") -> "Pattern":
        return Pattern(PatternKind.AND, children=list(patterns))

    @staticmethod
    def type_pat(type_name: str) -> "Pattern":
        return Pattern(PatternKind.TYPE, name=type_name)

    @staticmethod
    def regex_pat(pattern: str) -> "Pattern":
        compiled = re.compile(pattern)
        return Pattern(PatternKind.REGEX, value=compiled)

    @staticmethod
    def as_pat(inner: "Pattern", name: str) -> "Pattern":
        return Pattern(PatternKind.AS, children=[inner], name=name)

    @staticmethod
    def none_check() -> "Pattern":
        return Pattern(PatternKind.NONE_CHECK)

    @staticmethod
    def rest(name: str = "_") -> "Pattern":
        return Pattern(PatternKind.REST, name=name)


# ---------------------------------------------------------------------------
# Pattern matcher
# ---------------------------------------------------------------------------

# Map from type name string to Python type
_TYPE_MAP: dict[str, type] = {
    "int":   int,
    "float": float,
    "str":   str,
    "bool":  bool,
    "list":  list,
    "dict":  dict,
    "tuple": tuple,
    "set":   set,
    "any":   object,
}


def match_pattern(value: Any, pattern: Pattern) -> MatchResult:
    """
    Match `value` against `pattern`.
    Returns a MatchResult with `matched` flag and `bindings` dict.
    """
    kind = pattern.kind

    # --- Literal ----------------------------------------------------------
    if kind == PatternKind.LITERAL:
        if value == pattern.value and type(value) is type(pattern.value):
            return MATCH_SUCCESS
        return MATCH_FAILURE

    # --- Wildcard ---------------------------------------------------------
    if kind == PatternKind.WILDCARD:
        return MATCH_SUCCESS

    # --- Binding ----------------------------------------------------------
    if kind == PatternKind.BINDING:
        return MatchResult(True, {pattern.name: value})

    # --- None check -------------------------------------------------------
    if kind == PatternKind.NONE_CHECK:
        return MatchResult(value is None)

    # --- Type pattern -----------------------------------------------------
    if kind == PatternKind.TYPE:
        expected = _TYPE_MAP.get(pattern.name)
        if expected is None:
            # Try as class name
            matched = type(value).__name__ == pattern.name
        else:
            matched = isinstance(value, expected)
        return MatchResult(matched)

    # --- Regex ------------------------------------------------------------
    if kind == PatternKind.REGEX:
        if not isinstance(value, str):
            return MATCH_FAILURE
        m = pattern.value.search(value)
        if m:
            groups = m.groupdict()
            return MatchResult(True, groups if groups else {})
        return MATCH_FAILURE

    # --- Range pattern ----------------------------------------------------
    if kind == PatternKind.RANGE:
        start, end, inclusive = pattern.value
        if value < start:
            return MATCH_FAILURE
        if inclusive and value > end:
            return MATCH_FAILURE
        if not inclusive and value >= end:
            return MATCH_FAILURE
        return MATCH_SUCCESS

    # --- Struct pattern ---------------------------------------------------
    if kind == PatternKind.STRUCT:
        type_name = pattern.name
        # Check type name if specified and not wildcard
        if type_name and type(value).__name__ != type_name:
            # Check for dataclass or namedtuple
            if not (hasattr(value, '__dataclass_fields__') or
                    hasattr(value, '_fields') or
                    hasattr(value, '__class__') and type(value).__name__ == type_name):
                return MATCH_FAILURE

        fields_pats: dict[str, Pattern] = pattern.extra.get("fields", {})
        bindings: dict[str, Any] = {}

        for field_name, field_pat in fields_pats.items():
            # Try attribute access, then dict access
            if hasattr(value, field_name):
                field_val = getattr(value, field_name)
            elif isinstance(value, dict) and field_name in value:
                field_val = value[field_name]
            else:
                return MATCH_FAILURE

            sub = match_pattern(field_val, field_pat)
            if not sub.matched:
                return MATCH_FAILURE
            bindings.update(sub.bindings)

        return MatchResult(True, bindings)

    # --- List pattern -----------------------------------------------------
    if kind == PatternKind.LIST:
        if not isinstance(value, (list, tuple)):
            return MATCH_FAILURE

        elements = pattern.children
        rest_name = pattern.extra.get("rest")
        bindings: dict[str, Any] = {}

        if rest_name is None:
            # Fixed length match
            if len(value) != len(elements):
                return MATCH_FAILURE
            for i, elem_pat in enumerate(elements):
                sub = match_pattern(value[i], elem_pat)
                if not sub.matched:
                    return MATCH_FAILURE
                bindings.update(sub.bindings)
        else:
            # Variable length: [head, ...rest]
            if len(value) < len(elements):
                return MATCH_FAILURE
            for i, elem_pat in enumerate(elements):
                sub = match_pattern(value[i], elem_pat)
                if not sub.matched:
                    return MATCH_FAILURE
                bindings.update(sub.bindings)
            # Bind rest
            if rest_name != "_":
                bindings[rest_name] = list(value[len(elements):])

        return MatchResult(True, bindings)

    # --- Tuple pattern ----------------------------------------------------
    if kind == PatternKind.TUPLE:
        if not isinstance(value, tuple):
            # Also allow list matching tuple pattern
            if not isinstance(value, (list, tuple)):
                return MATCH_FAILURE
        elements = pattern.children
        if len(value) != len(elements):
            return MATCH_FAILURE
        bindings: dict[str, Any] = {}
        for i, elem_pat in enumerate(elements):
            sub = match_pattern(value[i], elem_pat)
            if not sub.matched:
                return MATCH_FAILURE
            bindings.update(sub.bindings)
        return MatchResult(True, bindings)

    # --- Guard ------------------------------------------------------------
    if kind == PatternKind.GUARD:
        inner_result = match_pattern(value, pattern.children[0])
        if not inner_result.matched:
            return MATCH_FAILURE
        pred = pattern.extra["pred"]
        if pred(value, inner_result.bindings):
            return inner_result
        return MATCH_FAILURE

    # --- OR pattern -------------------------------------------------------
    if kind == PatternKind.OR:
        for alt in pattern.children:
            result = match_pattern(value, alt)
            if result.matched:
                return result
        return MATCH_FAILURE

    # --- AND pattern ------------------------------------------------------
    if kind == PatternKind.AND:
        bindings: dict[str, Any] = {}
        for sub_pat in pattern.children:
            result = match_pattern(value, sub_pat)
            if not result.matched:
                return MATCH_FAILURE
            bindings.update(result.bindings)
        return MatchResult(True, bindings)

    # --- As pattern -------------------------------------------------------
    if kind == PatternKind.AS:
        inner_result = match_pattern(value, pattern.children[0])
        if not inner_result.matched:
            return MATCH_FAILURE
        inner_result.bindings[pattern.name] = value
        return inner_result

    return MATCH_FAILURE


# ---------------------------------------------------------------------------
# Match statement helper
# ---------------------------------------------------------------------------

class MatchArm:
    """A single arm of a match expression: pattern + body."""
    def __init__(self, pattern: Pattern, body: Callable[[dict], Any]) -> None:
        self.pattern = pattern
        self.body = body


class MatchExpr:
    """
    Executes a match expression over a value.

    Usage:
        result = (MatchExpr(value)
            .arm(Pattern.literal(0), lambda _: "zero")
            .arm(Pattern.range_pat(1, 9), lambda b: f"small: {value}")
            .arm(Pattern.binding("n"), lambda b: f"other: {b['n']}")
            .execute()
        )
    """

    def __init__(self, value: Any) -> None:
        self._value = value
        self._arms: list[MatchArm] = []
        self._default: Optional[Callable] = None

    def arm(self, pattern: Pattern, body: Callable[[dict], Any]) -> "MatchExpr":
        self._arms.append(MatchArm(pattern, body))
        return self

    def default(self, body: Callable[[], Any]) -> "MatchExpr":
        self._default = body
        return self

    def execute(self) -> Any:
        for arm in self._arms:
            result = match_pattern(self._value, arm.pattern)
            if result.matched:
                return arm.body(result.bindings)
        if self._default:
            return self._default()
        raise ValueError(f"Non-exhaustive match: no arm matched {self._value!r}")


# ---------------------------------------------------------------------------
# Pattern parser (parses LATERALUS match syntax from strings)
# ---------------------------------------------------------------------------

class PatternParser:
    """
    Parses LATERALUS pattern syntax strings into Pattern objects.

    Syntax examples:
      "_"               → wildcard
      "42"              → literal(42)
      "\"hello\""       → literal("hello")
      "name"            → binding("name")
      "1..10"           → range(1, 10, inclusive=True)
      "1..<10"          → range(1, 10, inclusive=False)
      "int"             → type_pat("int")
      "[a, b, *rest]"   → list_pat(binding(a), binding(b), rest="rest")
      "Point{x, y}"     → struct("Point", {x: binding(x), y: binding(y)})
      "Red|Blue|Green"  → or_pat(...)
    """

    KNOWN_TYPES = {"int", "float", "str", "bool", "list", "dict", "tuple", "set", "any"}

    def __init__(self, source: str) -> None:
        self._source = source.strip()
        self._pos = 0

    @property
    def _rest(self) -> str:
        return self._source[self._pos:]

    def _peek(self) -> str:
        return self._source[self._pos] if self._pos < len(self._source) else ""

    def _advance(self, n: int = 1) -> str:
        chunk = self._source[self._pos:self._pos + n]
        self._pos += n
        return chunk

    def _skip_ws(self) -> None:
        while self._pos < len(self._source) and self._source[self._pos] in " \t":
            self._pos += 1

    def parse(self) -> Pattern:
        return self._parse_or()

    def _parse_or(self) -> Pattern:
        parts = [self._parse_and()]
        while self._rest.lstrip().startswith("|"):
            self._pos = self._source.index("|", self._pos) + 1
            self._skip_ws()
            parts.append(self._parse_and())
        if len(parts) == 1:
            return parts[0]
        return Pattern.or_pat(*parts)

    def _parse_and(self) -> Pattern:
        parts = [self._parse_as()]
        while self._rest.lstrip().startswith("&"):
            self._pos = self._source.index("&", self._pos) + 1
            self._skip_ws()
            parts.append(self._parse_as())
        if len(parts) == 1:
            return parts[0]
        return Pattern.and_pat(*parts)

    def _parse_as(self) -> Pattern:
        inner = self._parse_atom()
        self._skip_ws()
        if self._rest.startswith("@ "):
            self._advance(2)
            self._skip_ws()
            name = self._parse_ident()
            return Pattern.as_pat(inner, name)
        return inner

    def _parse_atom(self) -> Pattern:
        self._skip_ws()
        rest = self._rest

        # Wildcard
        if rest.startswith("_"):
            self._advance()
            return Pattern.wildcard()

        # None
        if rest.startswith("None"):
            self._advance(4)
            return Pattern.none_check()

        # True / False
        if rest.startswith("True"):
            self._advance(4)
            return Pattern.literal(True)
        if rest.startswith("False"):
            self._advance(5)
            return Pattern.literal(False)

        # String literal
        if rest.startswith('"') or rest.startswith("'"):
            return self._parse_string_literal()

        # Number (possibly range)
        if rest[0].isdigit() or (rest[0] == "-" and len(rest) > 1 and rest[1].isdigit()):
            return self._parse_number_or_range()

        # List pattern
        if rest.startswith("["):
            return self._parse_list()

        # Tuple pattern
        if rest.startswith("("):
            return self._parse_tuple()

        # Regex pattern
        if rest.startswith("/"):
            return self._parse_regex()

        # Identifier: type, struct, or binding
        if rest[0].isalpha() or rest[0] == "_":
            return self._parse_ident_pattern()

        # Fallback: wildcard
        return Pattern.wildcard()

    def _parse_string_literal(self) -> Pattern:
        quote = self._advance()
        buf = []
        while self._pos < len(self._source):
            c = self._advance()
            if c == "\\":
                c2 = self._advance()
                buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(c2, c2))
            elif c == quote:
                break
            else:
                buf.append(c)
        return Pattern.literal("".join(buf))

    def _parse_number_or_range(self) -> Pattern:
        start_pos = self._pos
        while self._pos < len(self._source) and (
            self._source[self._pos].isdigit() or self._source[self._pos] in ".-"
        ):
            self._pos += 1
            # Watch for ".." range
            if self._source[self._pos - 1] == "." and self._pos < len(self._source):
                if self._source[self._pos] == ".":
                    # It's a range
                    num_str = self._source[start_pos:self._pos - 1]
                    self._advance()  # consume second "."
                    inclusive = True
                    if self._peek() == "<":
                        self._advance()
                        inclusive = False
                    # Parse end number
                    end_start = self._pos
                    while self._pos < len(self._source) and (
                        self._source[self._pos].isdigit() or self._source[self._pos] == "."
                    ):
                        self._pos += 1
                    end_str = self._source[end_start:self._pos]
                    start_val = float(num_str) if "." in num_str else int(num_str)
                    end_val = float(end_str) if "." in end_str else int(end_str)
                    return Pattern.range_pat(start_val, end_val, inclusive)
                else:
                    pass  # single dot in float

        num_str = self._source[start_pos:self._pos]
        val = float(num_str) if "." in num_str else int(num_str)
        return Pattern.literal(val)

    def _parse_list(self) -> Pattern:
        self._advance()  # consume "["
        elements: list[Pattern] = []
        rest_name: Optional[str] = None
        while True:
            self._skip_ws()
            if self._rest.startswith("]"):
                self._advance()
                break
            if self._rest.startswith("*"):
                self._advance()
                self._skip_ws()
                rest_name = self._parse_ident()
                self._skip_ws()
                if self._rest.startswith(","):
                    self._advance()
                continue
            elements.append(self._parse_or())
            self._skip_ws()
            if self._rest.startswith(","):
                self._advance()
        return Pattern.list_pat(*elements, rest=rest_name)

    def _parse_tuple(self) -> Pattern:
        self._advance()  # consume "("
        elements: list[Pattern] = []
        while True:
            self._skip_ws()
            if self._rest.startswith(")"):
                self._advance()
                break
            elements.append(self._parse_or())
            self._skip_ws()
            if self._rest.startswith(","):
                self._advance()
        return Pattern.tuple_pat(*elements)

    def _parse_regex(self) -> Pattern:
        self._advance()  # consume "/"
        buf = []
        while self._pos < len(self._source):
            c = self._advance()
            if c == "\\":
                buf.append(c)
                buf.append(self._advance())
            elif c == "/":
                break
            else:
                buf.append(c)
        flags_str = ""
        while self._pos < len(self._source) and self._source[self._pos].isalpha():
            flags_str += self._advance()
        return Pattern.regex_pat("".join(buf))

    def _parse_ident(self) -> str:
        start = self._pos
        while self._pos < len(self._source) and (
            self._source[self._pos].isalnum() or self._source[self._pos] == "_"
        ):
            self._pos += 1
        return self._source[start:self._pos]

    def _parse_ident_pattern(self) -> Pattern:
        name = self._parse_ident()
        self._skip_ws()

        # Struct pattern: Name{...}
        if self._rest.startswith("{"):
            self._advance()  # consume "{"
            fields: dict[str, Pattern] = {}
            while True:
                self._skip_ws()
                if self._rest.startswith("}"):
                    self._advance()
                    break
                field_name = self._parse_ident()
                self._skip_ws()
                if self._rest.startswith(":"):
                    self._advance()
                    self._skip_ws()
                    field_pat = self._parse_or()
                else:
                    field_pat = Pattern.binding(field_name)
                fields[field_name] = field_pat
                self._skip_ws()
                if self._rest.startswith(","):
                    self._advance()
            return Pattern.struct(name, fields)

        # Known types
        if name in self.KNOWN_TYPES:
            return Pattern.type_pat(name)

        # Binding variable (lowercase)
        if name[0].islower() or name == "_":
            return Pattern.binding(name)

        # Uppercase: treat as type name / enum variant
        return Pattern.type_pat(name)


def parse_pattern(source: str) -> Pattern:
    """Parse a LATERALUS pattern string into a Pattern object."""
    return PatternParser(source).parse()


# ---------------------------------------------------------------------------
# Decision tree builder (for exhaustiveness checking)
# ---------------------------------------------------------------------------

class ExhaustivenessChecker:
    """
    Checks whether a list of patterns is exhaustive for a given type.
    Used by the LATERALUS compiler to emit warnings on non-exhaustive match.
    """

    def __init__(self) -> None:
        self._warnings: list[str] = []

    def check(self, patterns: list[Pattern], value_type: str) -> tuple[bool, list[str]]:
        """Return (is_exhaustive, warning_messages)."""
        self._warnings = []
        has_wildcard = any(
            p.kind in (PatternKind.WILDCARD, PatternKind.BINDING) for p in patterns
        )
        if has_wildcard:
            return True, []

        has_type_cover = any(
            p.kind == PatternKind.TYPE and p.name in (value_type, "any")
            for p in patterns
        )
        if has_type_cover:
            return True, []

        self._warnings.append(
            f"Non-exhaustive match: no wildcard or type cover for type '{value_type}'. "
            "Add a wildcard arm `_ => ...` to handle all remaining cases."
        )
        return False, self._warnings


# ---------------------------------------------------------------------------
# Runtime API
# ---------------------------------------------------------------------------

def get_pattern_builtins() -> dict:
    return {
        "Pattern":             Pattern,
        "MatchResult":         MatchResult,
        "MatchExpr":           MatchExpr,
        "match_pattern":       match_pattern,
        "parse_pattern":       parse_pattern,
        "ExhaustivenessCheck": ExhaustivenessChecker,
        "PatternKind":         PatternKind,
    }
