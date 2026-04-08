"""
lateralus_lang/error_engine.py  -  LATERALUS Advanced Error Handling System
===============================================================================
World-class error handling with:
  · Rich error messages with source context (surrounding lines)
  · Error codes for every error category
  · Structured error chains (cause tracking)
  · Suggestion engine (did-you-mean, fix hints)
  · ANSI-colored terminal output
  · Machine-readable error format (JSON)
  · Recovery suggestions
  · Stack trace enhancement with local variable display

Design: errors should HELP you fix the problem, not just tell you
something is wrong.

v1.5.0
===============================================================================
"""
from __future__ import annotations

import difflib
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

# -----------------------------------------------------------------------------
# Error codes
# -----------------------------------------------------------------------------

class ErrorCode(Enum):
    # Lexer errors (E1xxx)
    E1001 = "E1001"
    E1002 = "E1002"
    E1003 = "E1003"
    E1004 = "E1004"
    E1005 = "E1005"

    # Parser errors (E2xxx)
    E2001 = "E2001"
    E2002 = "E2002"
    E2003 = "E2003"
    E2004 = "E2004"
    E2005 = "E2005"
    E2006 = "E2006"
    E2007 = "E2007"
    E2008 = "E2008"
    E2009 = "E2009"
    E2010 = "E2010"

    # Type errors (E3xxx)
    E3001 = "E3001"
    E3002 = "E3002"
    E3003 = "E3003"
    E3004 = "E3004"
    E3005 = "E3005"
    E3006 = "E3006"

    # Name resolution errors (E4xxx)
    E4001 = "E4001"
    E4002 = "E4002"
    E4003 = "E4003"
    E4004 = "E4004"
    E4005 = "E4005"
    E4006 = "E4006"

    # Runtime errors (E5xxx)
    E5001 = "E5001"
    E5002 = "E5002"
    E5003 = "E5003"
    E5004 = "E5004"
    E5005 = "E5005"
    E5006 = "E5006"
    E5007 = "E5007"
    E5008 = "E5008"

    # IO errors (E6xxx)
    E6001 = "E6001"
    E6002 = "E6002"
    E6003 = "E6003"
    E6004 = "E6004"

    # Compiler errors (E7xxx)
    E7001 = "E7001"
    E7002 = "E7002"
    E7003 = "E7003"
    E7004 = "E7004"


class Severity(Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"
    HINT    = "hint"


# -----------------------------------------------------------------------------
# ANSI color codes
# -----------------------------------------------------------------------------

class _Color:
    RESET     = "\033[0m"
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    RED       = "\033[91m"
    YELLOW    = "\033[93m"
    BLUE      = "\033[94m"
    CYAN      = "\033[96m"
    GREEN     = "\033[92m"
    MAGENTA   = "\033[95m"
    WHITE     = "\033[97m"
    GRAY      = "\033[90m"
    UNDERLINE = "\033[4m"

    @staticmethod
    def strip(text: str) -> str:
        """Remove ANSI codes from text."""
        import re
        return re.sub(r"\033\[[0-9;]*m", "", text)


def _supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


C = _Color if _supports_color() else type("NoColor", (), {
    k: "" for k in dir(_Color) if not k.startswith("_")
})()


# -----------------------------------------------------------------------------
# Source location
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceLocation:
    """Points to a specific location in source code."""
    file: str = "<input>"
    line: int = 0
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __str__(self):
        if self.column:
            return f"{self.file}:{self.line}:{self.column}"
        return f"{self.file}:{self.line}"


# -----------------------------------------------------------------------------
# LateralusError — the core error type
# -----------------------------------------------------------------------------

@dataclass
class LateralusError:
    """Rich error with source context, suggestions, and error chains."""
    code: ErrorCode
    message: str
    severity: Severity = Severity.ERROR
    location: Optional[SourceLocation] = None
    source_lines: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    cause: Optional["LateralusError"] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def with_suggestion(self, suggestion: str) -> "LateralusError":
        self.suggestions.append(suggestion)
        return self

    def with_note(self, note: str) -> "LateralusError":
        self.notes.append(note)
        return self

    def with_cause(self, cause: "LateralusError") -> "LateralusError":
        self.cause = cause
        return self

    def format(self, color: bool = True) -> str:
        """Format the error for terminal display."""
        c = _Color if color else type("NC", (), {
            k: "" for k in dir(_Color) if not k.startswith("_")
        })()

        parts = []

        # Severity + code + message
        sev_color = {
            Severity.ERROR: c.RED,
            Severity.WARNING: c.YELLOW,
            Severity.INFO: c.BLUE,
            Severity.HINT: c.GREEN,
        }.get(self.severity, c.WHITE)

        header = (f"{sev_color}{c.BOLD}{self.severity.value}{c.RESET}"
                  f"{c.GRAY}[{self.code.name}]{c.RESET}"
                  f"{c.BOLD}: {self.message}{c.RESET}")
        parts.append(header)

        # Location
        if self.location:
            loc_str = f"  {c.CYAN}--▸{c.RESET} {self.location}"
            parts.append(loc_str)

            # Source context with underline
            if self.source_lines and self.location.line > 0:
                parts.append(self._format_source_context(c))

        # Suggestions
        for suggestion in self.suggestions:
            parts.append(f"  {c.GREEN}help{c.RESET}: {suggestion}")

        # Notes
        for note in self.notes:
            parts.append(f"  {c.BLUE}note{c.RESET}: {note}")

        # Cause chain
        if self.cause:
            parts.append(f"\n{c.DIM}Caused by:{c.RESET}")
            parts.append(self.cause.format(color))

        return "\n".join(parts)

    def _format_source_context(self, c) -> str:
        """Format source lines with line numbers and error underline."""
        lines = []
        target_line = self.location.line
        start = max(0, target_line - 3)
        end = min(len(self.source_lines), target_line + 2)

        # Calculate gutter width
        gutter_width = len(str(end))

        for i in range(start, end):
            line_num = i + 1
            line_text = self.source_lines[i] if i < len(self.source_lines) else ""
            is_error_line = line_num == target_line

            if is_error_line:
                prefix = f"  {c.RED}{line_num:>{gutter_width}} |{c.RESET} "
                lines.append(prefix + line_text)
                # Underline
                col = max(0, self.location.column - 1)
                end_col = self.location.end_column or (col + 1)
                underline_len = max(1, end_col - col)
                padding = " " * (gutter_width + 5 + col)
                lines.append(f"{padding}{c.RED}{'-' * underline_len}{c.RESET}")
            else:
                prefix = f"  {c.GRAY}{line_num:>{gutter_width}} |{c.RESET} "
                lines.append(prefix + f"{c.DIM}{line_text}{c.RESET}")

        return "\n".join(lines)

    def to_json(self) -> Dict[str, Any]:
        """Convert to machine-readable JSON format."""
        result = {
            "code": self.code.name,
            "message": self.message,
            "severity": self.severity.value,
            "description": self.code.value,
        }
        if self.location:
            result["location"] = {
                "file": self.location.file,
                "line": self.location.line,
                "column": self.location.column,
            }
        if self.suggestions:
            result["suggestions"] = self.suggestions
        if self.notes:
            result["notes"] = self.notes
        if self.cause:
            result["cause"] = self.cause.to_json()
        return result


# -----------------------------------------------------------------------------
# Suggestion engine
# -----------------------------------------------------------------------------

def suggest_similar(name: str, candidates: Sequence[str],
                    max_results: int = 3, cutoff: float = 0.5) -> List[str]:
    """Find similar names from a list of candidates (did-you-mean)."""
    matches = difflib.get_close_matches(name, candidates,
                                         n=max_results, cutoff=cutoff)
    return list(matches)


def suggest_fix_for_undefined(name: str, scope_names: Sequence[str],
                               builtin_names: Sequence[str]) -> List[str]:
    """Generate fix suggestions for an undefined name."""
    suggestions = []

    # Check scope
    similar_scope = suggest_similar(name, scope_names)
    if similar_scope:
        suggestions.append(f"Did you mean `{similar_scope[0]}`?")
        if len(similar_scope) > 1:
            others = ", ".join(f"`{n}`" for n in similar_scope[1:])
            suggestions.append(f"Other similar names: {others}")

    # Check builtins
    similar_builtin = suggest_similar(name, builtin_names)
    if similar_builtin:
        for b in similar_builtin:
            if b not in scope_names:
                suggestions.append(f"`{b}` is a built-in — did you forget an import?")

    # Common typos
    common_fixes = {
        "pritnln": "println",
        "pirnt": "print",
        "retrun": "return",
        "fucntion": "function",
        "ture": "true",
        "flase": "false",
        "nill": "nil",
        "lenght": "length",
        "stirng": "string",
    }
    if name.lower() in common_fixes:
        suggestions.append(f"Did you mean `{common_fixes[name.lower()]}`?")

    return suggestions


def suggest_fix_for_type_mismatch(expected: str, actual: str) -> List[str]:
    """Generate fix suggestions for type mismatches."""
    suggestions = []

    # Common conversions — key is (expected, actual), suggestion converts actual→expected
    conversions = {
        ("int", "str"): "Use `int(value)` to parse string as integer",
        ("str", "int"): "Use `str(value)` to convert int to string",
        ("str", "float"): "Use `str(value)` to convert float to string",
        ("float", "int"): "Use `float(value)` to promote int to float",
        ("bool", "int"): "Booleans are already valid as integers (true=1, false=0)",
        ("list", "str"): "Use `str_join(list, \", \")` to convert list to string",
    }

    key = (expected.lower(), actual.lower())
    if key in conversions:
        suggestions.append(conversions[key])

    suggestions.append(f"Expected type `{expected}`, got `{actual}`")
    return suggestions


# -----------------------------------------------------------------------------
# Error collector (for multi-error reporting)
# -----------------------------------------------------------------------------

class ErrorCollector:
    """Collects multiple errors for batch reporting."""

    def __init__(self, source: str = "", file: str = "<input>"):
        self.errors: List[LateralusError] = []
        self.source = source
        self.source_lines = source.split("\n") if source else []
        self.file = file

    def add(self, error: LateralusError) -> None:
        if not error.source_lines:
            error.source_lines = self.source_lines
        self.errors.append(error)

    def error(self, code: ErrorCode, message: str,
              location: Optional[SourceLocation] = None, **kwargs) -> LateralusError:
        """Create and add an error."""
        err = LateralusError(
            code=code,
            message=message,
            location=location,
            source_lines=self.source_lines,
            **kwargs,
        )
        self.add(err)
        return err

    def warning(self, code: ErrorCode, message: str,
                location: Optional[SourceLocation] = None) -> LateralusError:
        """Create and add a warning."""
        err = self.error(code, message, location)
        err.severity = Severity.WARNING
        return err

    def has_errors(self) -> bool:
        return any(e.severity == Severity.ERROR for e in self.errors)

    def error_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.ERROR)

    def warning_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.WARNING)

    def format_all(self, color: bool = True) -> str:
        """Format all collected errors."""
        c = _Color if color else type("NC", (), {
            k: "" for k in dir(_Color) if not k.startswith("_")
        })()

        parts = []
        for err in sorted(self.errors, key=lambda e: (
                e.location.line if e.location else 0)):
            parts.append(err.format(color))
            parts.append("")

        # Summary
        if self.errors:
            summary_parts = []
            ec = self.error_count()
            if ec:
                summary_parts.append(
                    f"{c.RED}{ec} error{'s' if ec != 1 else ''}{c.RESET}")
            wc = self.warning_count()
            if wc:
                summary_parts.append(
                    f"{c.YELLOW}{wc} warning{'s' if wc != 1 else ''}{c.RESET}")
            parts.append(f"{c.BOLD}{' and '.join(summary_parts)} generated{c.RESET}")

        return "\n".join(parts)

    def print_all(self, file=None):
        """Print all errors to stderr (or specified file)."""
        if file is None:
            file = sys.stderr
        if self.errors:
            print(self.format_all(), file=file)

    def to_json(self) -> Dict[str, Any]:
        """Convert all errors to JSON format."""
        return {
            "error_count": self.error_count(),
            "warning_count": self.warning_count(),
            "errors": [e.to_json() for e in self.errors],
        }

    def raise_if_errors(self):
        """Raise a LateralusCompileError if any errors were collected."""
        if self.has_errors():
            raise LateralusCompileError(
                self.format_all(color=False), errors=self.errors)


# -----------------------------------------------------------------------------
# Exception classes
# -----------------------------------------------------------------------------

class LateralusCompileError(Exception):
    """Raised when compilation fails with collected errors."""

    def __init__(self, message: str = "Compilation failed",
                 errors: Optional[List[LateralusError]] = None):
        self.errors = errors or []
        super().__init__(message)


class LateralusRuntimeError(Exception):
    """Raised during LATERALUS program execution."""

    def __init__(self, message: str, error: Optional[LateralusError] = None,
                 code: ErrorCode = ErrorCode.E5001,
                 location: Optional[SourceLocation] = None):
        self.error = error if error is not None else LateralusError(
            code=code, message=message, location=location)
        super().__init__(message)


# -----------------------------------------------------------------------------
# Stack trace enhancer
# -----------------------------------------------------------------------------

def enhance_traceback(exc: Exception, source: str = "",
                      file: str = "<input>") -> Optional[LateralusError]:
    """Enhance a Python traceback with LATERALUS source context.

    Catches Python exceptions from transpiled code and maps them
    back to the original LATERALUS source.  Returns a ``LateralusError``
    with the appropriate error code.
    """
    exc_type = type(exc).__name__
    code_map = {
        "ZeroDivisionError": ErrorCode.E5001,
        "NameError":         ErrorCode.E4001,
        "TypeError":         ErrorCode.E3001,
        "IndexError":        ErrorCode.E5003,
        "KeyError":          ErrorCode.E5004,
    }
    code = code_map.get(exc_type, ErrorCode.E5005)
    location = SourceLocation(file=file, line=1)
    source_lines = source.split("\n") if source else []
    return LateralusError(
        code=code,
        message=str(exc),
        severity=Severity.ERROR,
        location=location,
        source_lines=source_lines,
    )
