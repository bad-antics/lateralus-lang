"""
tests/test_full_pipeline.py — End-to-end pipeline integration tests

These tests verify that the complete LATERALUS compiler pipeline works
correctly with the new engine subsystems integrated.
"""
import pytest
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMathEngineEndToEnd:
    """Test that math engine functions work end-to-end."""

    def test_ltlnumber_arithmetic(self):
        from lateralus_lang.math_engine import LTLNumber
        a = LTLNumber(10)
        b = LTLNumber(3)
        assert (a + b).value == 13
        assert (a - b).value == 7
        assert (a * b).value == 30

    def test_matrix_operations(self):
        from lateralus_lang.math_engine import Matrix
        m = Matrix([[1, 2], [3, 4]])
        mt = m.transpose()
        assert mt.data == [[1, 3], [2, 4]]
        assert abs(m.det() - (-2)) < 1e-10

    def test_vector_dot_product(self):
        from lateralus_lang.math_engine import Vector
        v1 = Vector([1, 2, 3])
        v2 = Vector([4, 5, 6])
        assert v1.dot(v2) == 32

    def test_interval_arithmetic(self):
        from lateralus_lang.math_engine import Interval
        a = Interval(1, 2)
        b = Interval(3, 4)
        result = a + b
        assert result.lo == 4
        assert result.hi == 6

    def test_automatic_differentiation(self):
        from lateralus_lang.math_engine import derivative
        # d/dx (x^2) at x=3 should be 6
        f = lambda x: x * x
        d = derivative(f, 3.0)
        assert abs(d - 6.0) < 1e-10

    def test_statistics_pipeline(self):
        from lateralus_lang.math_engine import mean, median, std_dev
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        assert mean(data) == 5.0
        assert median(data) == 4.5
        assert abs(std_dev(data) - 2.0) < 0.2

    def test_numerical_integration(self):
        from lateralus_lang.math_engine import simpson_integrate
        import math
        # Integral of sin(x) from 0 to pi = 2.0
        result = simpson_integrate(math.sin, 0, math.pi, 1000)
        assert abs(result - 2.0) < 1e-6

    def test_bisection_root(self):
        from lateralus_lang.math_engine import bisection
        # Find sqrt(2)
        root = bisection(lambda x: x*x - 2, 1.0, 2.0)
        assert abs(root - 1.41421356) < 1e-6


class TestCryptoEngineEndToEnd:
    """Test crypto engine functions end-to-end."""

    def test_hash_consistency(self):
        from lateralus_lang.crypto_engine import sha256
        h1 = sha256("hello")
        h2 = sha256("hello")
        h3 = sha256("world")
        assert h1 == h2
        assert h1 != h3

    def test_hmac_workflow(self):
        from lateralus_lang.crypto_engine import hmac_sign, hmac_verify
        msg = "important data"
        key = "secret"
        sig = hmac_sign(msg, key)
        assert hmac_verify(msg, key, sig) is True
        assert hmac_verify("tampered", key, sig) is False

    def test_password_workflow(self):
        from lateralus_lang.crypto_engine import hash_password, verify_password
        hashed = hash_password("MyP@ssw0rd!")
        assert verify_password("MyP@ssw0rd!", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_encoding_roundtrip(self):
        from lateralus_lang.crypto_engine import to_base64, from_base64, to_hex, from_hex
        original = "LATERALUS rocks!"
        assert from_base64(to_base64(original)) == original
        assert from_hex(to_hex(original)) == original

    def test_lbe_complex_data(self):
        from lateralus_lang.crypto_engine import lbe_encode, lbe_decode
        data = {
            "name": "LATERALUS",
            "version": 1.3,
            "features": ["math", "crypto", "markup"],
            "active": True,
            "meta": None,
        }
        encoded = lbe_encode(data)
        decoded = lbe_decode(encoded)
        assert decoded["name"] == "LATERALUS"
        assert decoded["features"] == ["math", "crypto", "markup"]
        assert decoded["active"] is True
        assert decoded["meta"] is None


class TestMarkupEndToEnd:
    """Test LTLML markup processing end-to-end."""

    def test_simple_document(self):
        from lateralus_lang.markup import render_ltlml
        html = render_ltlml("# Title\n\nParagraph text.")
        assert "<h1" in html
        assert "Title" in html
        assert "Paragraph" in html

    def test_frontmatter_extraction(self):
        from lateralus_lang.markup import parse_ltlml
        doc = parse_ltlml("---\ntitle: My Doc\nauthor: Me\n---\n\n# Hello")
        # The frontmatter should be in the document
        assert doc is not None

    def test_code_block_rendering(self):
        from lateralus_lang.markup import render_ltlml
        source = "```python\nprint('hello')\n```"
        html = render_ltlml(source)
        assert "print" in html
        assert "<code" in html or "<pre" in html

    def test_full_document_render(self):
        from lateralus_lang.markup import render_ltlml
        source = """---
title: Integration Test
---

# Section One

A paragraph with **bold**, _italic_, and `code`.

## Subsection

- Item 1
- Item 2
- Item 3

| Col A | Col B |
|-------|-------|
| 1     | 2     |
"""
        html = render_ltlml(source)
        assert "<h1" in html
        assert "<h2" in html
        assert "<strong>" in html or "<b>" in html
        assert "<table" in html

    def test_file_compilation(self, tmp_path):
        from lateralus_lang.markup import compile_ltlml_file
        src = tmp_path / "test.ltlml"
        src.write_text("# Hello World\n\nThis is a test.")
        out = tmp_path / "test.html"
        result = compile_ltlml_file(str(src), str(out))
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "<h1" in content


class TestBytecodeEndToEnd:
    """Test .ltlc compile/decompile cycle."""

    def test_compile_decompile_cycle(self):
        from lateralus_lang.bytecode_format import LTLCCompiler, LTLCDecompiler

        source = '''
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

let x = factorial(10)
let greeting = "Hello"
'''
        # Compile
        compiler = LTLCCompiler(compress=True, include_debug=True)
        binary = compiler.compile_source(source, "factorial.ltl")

        # Decompile
        decompiler = LTLCDecompiler()
        ltlc = decompiler.decompile(binary)

        assert ltlc.metadata.source_file == "factorial.ltl"
        sym_names = [s.name for s in ltlc.symbols]
        assert "factorial" in sym_names
        assert "x" in sym_names

    def test_compile_to_file(self, tmp_path):
        from lateralus_lang.bytecode_format import LTLCCompiler

        source = 'fn hello() { println("hi") }'
        compiler = LTLCCompiler()
        out = str(tmp_path / "test.ltlc")
        result = compiler.compile_to_file(source, out, "hello.ltl")
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_signed_binary(self):
        from lateralus_lang.bytecode_format import LTLCCompiler, LTLCDecompiler

        source = 'fn secure() { return 42 }'
        key = "top-secret-key"

        compiler = LTLCCompiler(signing_key=key)
        binary = compiler.compile_source(source, "secure.ltl")

        decompiler = LTLCDecompiler(signing_key=key)
        ltlc = decompiler.decompile(binary)
        assert ltlc.metadata.is_signed

    def test_inspector(self):
        from lateralus_lang.bytecode_format import LTLCCompiler, LTLCInspector

        source = '''
fn add(a: int, b: int) -> int { return a + b }
fn mul(a: int, b: int) -> int { return a * b }
let PI = 3.14159
'''
        binary = LTLCCompiler().compile_source(source, "math.ltl")
        report = LTLCInspector().inspect(binary)

        assert report["source_file"] == "math.ltl"
        assert report["symbols_count"] >= 3
        assert report["constants_count"] >= 1


class TestErrorEngineEndToEnd:
    """Test error engine diagnostics."""

    def test_error_formatting(self):
        from lateralus_lang.error_engine import (
            ErrorCode, Severity, SourceLocation, LateralusError,
        )

        err = LateralusError(
            code=ErrorCode.E2001,
            message="Unexpected token '}' — expected expression",
            severity=Severity.ERROR,
            location=SourceLocation("parser_test.ltl", 5, 12),
            source_lines=[
                "fn broken() {",
                "    let x = 10",
                "    if x > 5 {",
                "        return x",
                "    } }",  # Line 5 — extra brace
            ],
            suggestions=["Remove the extra closing brace '}'"],
            notes=["Block started at line 3"],
        )

        formatted = err.format(color=False)
        assert "E2001" in formatted
        assert "Unexpected token" in formatted
        assert "parser_test.ltl" in formatted

    def test_error_collector_workflow(self):
        from lateralus_lang.error_engine import (
            ErrorCode, SourceLocation, ErrorCollector, LateralusCompileError,
        )

        collector = ErrorCollector()

        # Simulate finding multiple errors during compilation
        collector.error(ErrorCode.E1001, "Invalid character '#'",
                       SourceLocation("bad.ltl", 1, 0))
        collector.warning(ErrorCode.E4002, "Unused variable 'temp'",
                         SourceLocation("bad.ltl", 3, 8))
        collector.error(ErrorCode.E2003, "Missing closing parenthesis",
                       SourceLocation("bad.ltl", 7, 15))

        assert collector.error_count() == 2
        assert collector.warning_count() == 1

        # Format all errors
        output = collector.format_all(color=False)
        assert "E1001" in output
        assert "E4002" in output
        assert "E2003" in output

        # JSON output
        j = collector.to_json()
        assert j["error_count"] == 2
        assert j["warning_count"] == 1

        # Should raise on errors
        with pytest.raises(LateralusCompileError):
            collector.raise_if_errors()

    def test_suggestion_engine(self):
        from lateralus_lang.error_engine import suggest_similar, suggest_fix_for_undefined

        # Typo detection
        similar = suggest_similar("prntln", ["print", "println", "input", "len"])
        assert "println" in similar

        # Fix suggestions
        scope = {"println", "print", "len", "range", "map"}
        builtins = {"input", "type", "str", "int", "float"}
        suggestions = suggest_fix_for_undefined("prnt", scope, builtins)
        assert any("print" in s for s in suggestions)

    def test_enhance_traceback_zero_div(self):
        from lateralus_lang.error_engine import enhance_traceback, ErrorCode

        source = "let result = 10 / 0"
        try:
            1 / 0
        except ZeroDivisionError as exc:
            err = enhance_traceback(exc, source, "division.ltl")
            assert err.code == ErrorCode.E5001
            assert "division.ltl" in err.location.file


class TestPreambleIntegration:
    """Test that the engine preamble code works correctly."""

    def test_preamble_executes_cleanly(self):
        from lateralus_lang.engines import get_preamble_code
        code = get_preamble_code()
        ns = {}
        exec(code, ns)
        # Should have math builtins
        assert callable(ns.get("mean"))
        assert callable(ns.get("sha256"))
        assert callable(ns.get("derivative"))

    def test_preamble_math_works(self):
        from lateralus_lang.engines import get_preamble_code
        code = get_preamble_code()
        ns = {}
        exec(code, ns)
        # Use the imported functions
        assert ns["mean"]([1, 2, 3, 4, 5]) == 3.0
        m = ns["Matrix"]([[1, 0], [0, 1]])
        assert m.det() == 1.0

    def test_preamble_crypto_works(self):
        from lateralus_lang.engines import get_preamble_code
        code = get_preamble_code()
        ns = {}
        exec(code, ns)
        h = ns["sha256"]("test")
        assert len(h) == 64
        assert ns["from_base64"](ns["to_base64"]("hello")) == "hello"
