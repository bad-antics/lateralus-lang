"""
tests/test_error_engine.py — Tests for the LATERALUS rich error diagnostics engine
"""
import pytest

from lateralus_lang.error_engine import (
    ErrorCode,
    ErrorCollector,
    LateralusCompileError,
    LateralusError,
    LateralusRuntimeError,
    Severity,
    SourceLocation,
    enhance_traceback,
    suggest_fix_for_type_mismatch,
    suggest_fix_for_undefined,
    suggest_similar,
)

# --- SourceLocation ---

class TestSourceLocation:
    def test_creation(self):
        loc = SourceLocation(file="test.ltl", line=10, column=5)
        assert loc.file == "test.ltl"
        assert loc.line == 10
        assert loc.column == 5

    def test_defaults(self):
        loc = SourceLocation(file="test.ltl", line=1)
        assert loc.column == 0
        assert loc.end_line is None
        assert loc.end_column is None

    def test_with_end(self):
        loc = SourceLocation(file="x.ltl", line=1, column=0, end_line=3, end_column=10)
        assert loc.end_line == 3
        assert loc.end_column == 10


# --- LateralusError ---

class TestLateralusError:
    def test_creation(self):
        err = LateralusError(
            code=ErrorCode.E1001,
            message="Unexpected character '@'",
            severity=Severity.ERROR,
        )
        assert err.code == ErrorCode.E1001
        assert "Unexpected" in err.message
        assert err.severity == Severity.ERROR

    def test_with_location(self):
        loc = SourceLocation(file="sample.ltl", line=5, column=3)
        err = LateralusError(
            code=ErrorCode.E2001,
            message="Unexpected token 'else'",
            severity=Severity.ERROR,
            location=loc,
        )
        assert err.location.line == 5

    def test_with_suggestions(self):
        err = LateralusError(
            code=ErrorCode.E4001,
            message="Undefined variable 'prnt'",
            severity=Severity.ERROR,
            suggestions=["Did you mean 'print'?"],
        )
        assert len(err.suggestions) == 1
        assert "print" in err.suggestions[0]

    def test_with_notes(self):
        err = LateralusError(
            code=ErrorCode.E3001,
            message="Type mismatch",
            severity=Severity.ERROR,
            notes=["Expected int, got string", "Try using int() to convert"],
        )
        assert len(err.notes) == 2

    def test_format_produces_output(self):
        loc = SourceLocation(file="test.ltl", line=3, column=5)
        err = LateralusError(
            code=ErrorCode.E1001,
            message="Unexpected character",
            severity=Severity.ERROR,
            location=loc,
            source_lines=["fn main() {", "    let x = 10", "    let y = @bad", "}"],
        )
        output = err.format(color=False)
        assert "E1001" in output
        assert "Unexpected character" in output

    def test_to_json(self):
        err = LateralusError(
            code=ErrorCode.E5001,
            message="Division by zero",
            severity=Severity.ERROR,
            location=SourceLocation(file="math.ltl", line=42, column=10),
        )
        j = err.to_json()
        assert j["code"] == "E5001"
        assert j["message"] == "Division by zero"
        assert j["severity"] == "error"
        assert j["location"]["file"] == "math.ltl"
        assert j["location"]["line"] == 42

    def test_severity_warning(self):
        err = LateralusError(
            code=ErrorCode.E4002,
            message="Unused variable 'temp'",
            severity=Severity.WARNING,
        )
        assert err.severity == Severity.WARNING


# --- Suggestion Engine ---

class TestSuggestionEngine:
    def test_suggest_similar_exact(self):
        candidates = ["print", "println", "input", "len"]
        results = suggest_similar("prnt", candidates)
        assert "print" in results

    def test_suggest_similar_close(self):
        candidates = ["append", "extend", "insert", "remove"]
        results = suggest_similar("apend", candidates)
        assert "append" in results

    def test_suggest_similar_no_match(self):
        candidates = ["alpha", "beta", "gamma"]
        results = suggest_similar("zzzzzzzzz", candidates)
        assert len(results) == 0

    def test_suggest_fix_for_undefined(self):
        scope = {"println", "print", "len", "range"}
        builtins = {"input", "type", "str", "int"}
        suggestions = suggest_fix_for_undefined("prntln", scope, builtins)
        assert any("println" in s for s in suggestions)

    def test_suggest_fix_for_type_mismatch_int_str(self):
        suggestions = suggest_fix_for_type_mismatch("int", "str")
        assert any("int(" in s for s in suggestions)

    def test_suggest_fix_for_type_mismatch_str_int(self):
        suggestions = suggest_fix_for_type_mismatch("str", "int")
        assert any("str(" in s for s in suggestions)

    def test_suggest_fix_for_type_mismatch_float_int(self):
        suggestions = suggest_fix_for_type_mismatch("float", "int")
        assert any("float(" in s for s in suggestions)


# --- ErrorCollector ---

class TestErrorCollector:
    def test_empty_collector(self):
        ec = ErrorCollector()
        assert not ec.has_errors()
        assert ec.error_count() == 0

    def test_add_error(self):
        ec = ErrorCollector()
        ec.error(ErrorCode.E1001, "Bad character", SourceLocation("t.ltl", 1))
        assert ec.has_errors()
        assert ec.error_count() == 1

    def test_add_warning(self):
        ec = ErrorCollector()
        ec.warning(ErrorCode.E4002, "Unused variable", SourceLocation("t.ltl", 5))
        assert not ec.has_errors()
        assert ec.warning_count() == 1

    def test_mixed_errors_warnings(self):
        ec = ErrorCollector()
        ec.error(ErrorCode.E1001, "Bad char", SourceLocation("t.ltl", 1))
        ec.warning(ErrorCode.E4002, "Unused", SourceLocation("t.ltl", 5))
        ec.error(ErrorCode.E2001, "Unexpected token", SourceLocation("t.ltl", 10))
        assert ec.error_count() == 2
        assert ec.warning_count() == 1

    def test_format_all(self):
        ec = ErrorCollector()
        ec.error(ErrorCode.E5001, "Division by zero", SourceLocation("m.ltl", 3))
        output = ec.format_all(color=False)
        assert "E5001" in output
        assert "Division by zero" in output

    def test_to_json(self):
        ec = ErrorCollector()
        ec.error(ErrorCode.E1001, "Bad", SourceLocation("t.ltl", 1))
        j = ec.to_json()
        assert j["error_count"] == 1
        assert len(j["errors"]) == 1

    def test_raise_if_errors(self):
        ec = ErrorCollector()
        ec.error(ErrorCode.E2001, "Syntax error", SourceLocation("t.ltl", 1))
        with pytest.raises(LateralusCompileError):
            ec.raise_if_errors()

    def test_no_raise_if_no_errors(self):
        ec = ErrorCollector()
        ec.warning(ErrorCode.E4002, "Unused", SourceLocation("t.ltl", 5))
        ec.raise_if_errors()  # Should not raise


# --- Exception Classes ---

class TestExceptionClasses:
    def test_compile_error(self):
        err = LateralusCompileError("Compilation failed", errors=[])
        assert "Compilation failed" in str(err)
        assert hasattr(err, "errors")

    def test_runtime_error(self):
        err = LateralusRuntimeError("Runtime fault", error=None)
        assert "Runtime fault" in str(err)
        assert hasattr(err, "error")


# --- enhance_traceback ---

class TestEnhanceTraceback:
    def test_zero_division(self):
        source = "let x = 10 / 0"
        try:
            eval("10 / 0")
        except ZeroDivisionError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E5001

    def test_name_error(self):
        source = "println(undefined_var)"
        try:
            eval("undefined_var_xyz")
        except NameError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E4001

    def test_type_error(self):
        source = 'let x = "hello" + 5'
        try:
            eval('"hello" + 5')
        except TypeError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E3001

    def test_index_error(self):
        source = "let x = items[99]"
        try:
            [][99]
        except IndexError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E5003

    def test_key_error(self):
        source = 'let x = data["missing"]'
        try:
            {}["missing"]
        except KeyError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E5004

    def test_unknown_exception(self):
        source = "some code"
        try:
            raise RuntimeError("something broke")
        except RuntimeError as exc:
            result = enhance_traceback(exc, source, "test.ltl")
            assert result is not None
            assert result.code == ErrorCode.E5005


# --- ErrorCode Coverage ---

class TestErrorCodes:
    def test_all_codes_have_descriptions(self):
        for code in ErrorCode:
            assert code.value.startswith("E")
            assert len(code.value) == 5

    def test_lexer_codes(self):
        assert ErrorCode.E1001.value == "E1001"
        assert ErrorCode.E1002.value == "E1002"

    def test_parser_codes(self):
        assert ErrorCode.E2001.value == "E2001"

    def test_type_codes(self):
        assert ErrorCode.E3001.value == "E3001"

    def test_name_codes(self):
        assert ErrorCode.E4001.value == "E4001"

    def test_runtime_codes(self):
        assert ErrorCode.E5001.value == "E5001"

    def test_io_codes(self):
        assert ErrorCode.E6001.value == "E6001"

    def test_compiler_codes(self):
        assert ErrorCode.E7001.value == "E7001"
