"""
tests/test_engines.py — Integration tests for the unified engine interface
"""
import pytest
from lateralus_lang.engines import (
    math, crypto, markup, bytecode, errors,
    get_all_builtins, get_preamble_code,
    engine_status, ENGINE_VERSIONS,
)


class TestLazyLoading:
    def test_math_engine_loads(self):
        m = math()
        assert hasattr(m, "LTLNumber")
        assert hasattr(m, "Matrix")
        assert hasattr(m, "Vector")
        assert hasattr(m, "derivative")

    def test_crypto_engine_loads(self):
        c = crypto()
        assert hasattr(c, "sha256")
        assert hasattr(c, "hmac_sign")
        assert hasattr(c, "lbe_encode")

    def test_markup_engine_loads(self):
        mk = markup()
        assert hasattr(mk, "parse_ltlml")
        assert hasattr(mk, "render_ltlml")

    def test_bytecode_engine_loads(self):
        bc = bytecode()
        assert hasattr(bc, "LTLCCompiler")
        assert hasattr(bc, "LTLCDecompiler")
        assert hasattr(bc, "LTLCInspector")

    def test_error_engine_loads(self):
        ee = errors()
        assert hasattr(ee, "ErrorCode")
        assert hasattr(ee, "ErrorCollector")
        assert hasattr(ee, "enhance_traceback")

    def test_cached_on_second_call(self):
        m1 = math()
        m2 = math()
        assert m1 is m2


class TestAllBuiltins:
    def test_returns_dict(self):
        builtins = get_all_builtins()
        assert isinstance(builtins, dict)
        assert len(builtins) > 30

    def test_math_builtins_present(self):
        b = get_all_builtins()
        assert "Matrix" in b
        assert "Vector" in b
        assert "mean" in b
        assert "derivative" in b

    def test_crypto_builtins_present(self):
        b = get_all_builtins()
        assert "sha256" in b
        assert "hmac_sign" in b
        assert "to_base64" in b

    def test_constants_present(self):
        b = get_all_builtins()
        assert "PI" in b
        assert "E" in b
        assert "PHI" in b


class TestPreambleCode:
    def test_preamble_is_string(self):
        code = get_preamble_code()
        assert isinstance(code, str)
        assert len(code) > 100

    def test_preamble_contains_imports(self):
        code = get_preamble_code()
        assert "from lateralus_lang.math_engine import" in code
        assert "from lateralus_lang.crypto_engine import" in code
        assert "from lateralus_lang.error_engine import" in code

    def test_preamble_is_valid_python(self):
        code = get_preamble_code()
        # Should compile without syntax errors
        compile(code, "<preamble>", "exec")

    def test_preamble_executes(self):
        code = get_preamble_code()
        ns = {}
        exec(code, ns)
        # After exec, math builtins should be available
        assert "Matrix" in ns
        assert "sha256" in ns


class TestEngineStatus:
    def test_status_returns_dict(self):
        status = engine_status()
        assert isinstance(status, dict)

    def test_all_engines_listed(self):
        status = engine_status()
        for name in ENGINE_VERSIONS:
            assert name in status

    def test_engines_available(self):
        status = engine_status()
        for name, info in status.items():
            assert info["available"], f"Engine {name} should be available"


class TestCrossEngineIntegration:
    def test_math_then_crypto(self):
        """Compute a value with math engine, then hash it with crypto."""
        m = math()
        c = crypto()

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        avg = m.mean(values)
        hashed = c.sha256(str(avg))
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex digest

    def test_matrix_serialize_lbe(self):
        """Create a matrix, extract data, serialize with LBE."""
        m = math()
        c = crypto()

        mat = m.Matrix([[1, 2], [3, 4]])
        data = mat.data  # list of lists
        encoded = c.lbe_encode(data)
        decoded = c.lbe_decode(encoded)
        assert decoded == data

    def test_error_with_math_context(self):
        """Create an error with math-related context."""
        ee = errors()

        loc = ee.SourceLocation(file="algebra.ltl", line=10, column=5)
        err = ee.LateralusError(
            code=ee.ErrorCode.E3001,
            message="Cannot multiply Matrix(2x2) with Matrix(3x3): shape mismatch",
            severity=ee.Severity.ERROR,
            location=loc,
            suggestions=["Ensure matrices have compatible shapes for multiplication"],
        )
        output = err.format(color=False)
        assert "shape mismatch" in output

    def test_compile_and_inspect(self):
        """Compile source to .ltlc and inspect the result."""
        bc = bytecode()

        source = '''
fn fibonacci(n: int) -> int {
    if n <= 1 { return n }
    return fibonacci(n - 1) + fibonacci(n - 2)
}
let result = fibonacci(10)
'''
        compiler = bc.LTLCCompiler(compress=True, include_debug=True)
        data = compiler.compile_source(source, "fib.ltl")

        inspector = bc.LTLCInspector()
        report = inspector.inspect(data)
        assert report["source_file"] == "fib.ltl"
        assert any(s["name"] == "fibonacci" for s in report["symbols"])

    def test_markup_render(self):
        """Parse and render a simple LTLML document."""
        mk = markup()

        source = """---
title: Test Document
author: LATERALUS
---

# Hello World

This is a **test** with _markup_.

```python
print("hello")
```
"""
        html = mk.render_ltlml(source)
        assert "<h1" in html
        assert "<strong>" in html or "<b>" in html
        assert "<em>" in html or "<i>" in html
        assert "print" in html
