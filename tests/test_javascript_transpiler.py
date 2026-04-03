"""
tests/test_javascript_transpiler.py
Tests for lateralus_lang.codegen.javascript — JS/ES2022+ transpiler (v2.0)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lateralus_lang.codegen.javascript import (
    JavaScriptTranspiler, JSBuffer, transpile_to_js,
    get_js_transpiler_builtins, JS_RUNTIME
)


# ---------------------------------------------------------------------------
# JSBuffer
# ---------------------------------------------------------------------------

class TestJSBuffer:
    def test_write_line(self):
        buf = JSBuffer()
        buf.write("const x = 1;")
        assert "const x = 1;" in buf.get()

    def test_indent(self):
        buf = JSBuffer()
        buf.write("if (true) {")
        buf.indent()
        buf.write("console.log('hi');")
        buf.dedent()
        buf.write("}")
        code = buf.get()
        assert "console.log" in code

    def test_blank_line(self):
        buf = JSBuffer()
        buf.write("const a = 1;")
        buf.blank()
        buf.write("const b = 2;")
        code = buf.get()
        assert "\n\n" in code or code.count("\n") >= 2

    def test_get_returns_string(self):
        buf = JSBuffer()
        buf.write("// comment")
        assert isinstance(buf.get(), str)


# ---------------------------------------------------------------------------
# Runtime header
# ---------------------------------------------------------------------------

class TestRuntimeHeader:
    def test_runtime_is_string(self):
        assert isinstance(JS_RUNTIME, str)

    def test_runtime_has_ltl_namespace(self):
        assert "__ltl" in JS_RUNTIME or "ltl" in JS_RUNTIME.lower()

    def test_runtime_has_pipe_function(self):
        assert "pipe" in JS_RUNTIME.lower() or "|>" in JS_RUNTIME

    def test_runtime_has_range(self):
        assert "range" in JS_RUNTIME.lower()

    def test_runtime_has_println(self):
        assert "println" in JS_RUNTIME.lower() or "console.log" in JS_RUNTIME

    def test_runtime_has_math_constants(self):
        assert "PI" in JS_RUNTIME or "Math.PI" in JS_RUNTIME


# ---------------------------------------------------------------------------
# Pattern-based transpilation (via AST)
# ---------------------------------------------------------------------------

class TestPatternTranspilation:
    def setup_method(self):
        self.t = JavaScriptTranspiler(include_runtime=False)

    def test_let_declaration(self):
        code = self.t.transpile_string("let x = 42")
        assert "let x" in code or "const x" in code
        assert "42" in code

    def test_mut_declaration(self):
        code = self.t.transpile_string("let mut x = 10")
        assert "let x" in code
        assert "10" in code

    def test_println(self):
        code = self.t.transpile_string('println("hello")')
        assert "println" in code
        assert "hello" in code

    def test_return_statement(self):
        code = self.t.transpile_string("fn f() { return 42 }")
        assert "return 42" in code

    def test_fn_declaration(self):
        code = self.t.transpile_string("fn add(a: int, b: int) -> int { return a + b }")
        assert "function" in code or "=>" in code
        assert "add" in code

    def test_import_statement(self):
        code = self.t.transpile_string("import math")
        assert "import" in code or "require" in code or "math" in code

    def test_struct_declaration(self):
        code = self.t.transpile_string("struct Point { x: float, y: float }")
        assert "Point" in code
        assert "class" in code or "function" in code or "Point" in code

    def test_if_expression(self):
        code = self.t.transpile_string('if true { println("pos") }')
        assert "if" in code

    def test_for_loop(self):
        code = self.t.transpile_string("for i in range(10) { println(i) }")
        assert "for" in code


# ---------------------------------------------------------------------------
# Expression translation (via full transpilation)
# ---------------------------------------------------------------------------

class TestExpressionTranslation:
    def _eval(self, src):
        return transpile_to_js(src, include_runtime=False)

    def test_boolean_true(self):
        out = self._eval("let x = true")
        assert "true" in out

    def test_boolean_false(self):
        out = self._eval("let x = false")
        assert "false" in out

    def test_pipeline_basic(self):
        out = self._eval("let r = [1,2,3] |> filter(fn(x) { x > 0 })")
        assert "filter" in out

    def test_optional_pipeline(self):
        out = self._eval("let x = 5\nlet r = x |? str")
        assert "null" in out or "str" in out

    def test_exponentiation(self):
        out = self._eval("let r = 2 ** 10")
        assert "**" in out

    def test_equality_operator(self):
        out = self._eval("let r = 1 == 2")
        assert "===" in out or "==" in out

    def test_inequality_operator(self):
        out = self._eval("let r = 1 != 2")
        assert "!=" in out

    def test_lambda_arrow(self):
        out = self._eval("let f = fn(x) { x * 2 }")
        assert "=>" in out or "function" in out


# ---------------------------------------------------------------------------
# Parameter stripping (via full function transpilation)
# ---------------------------------------------------------------------------

class TestParamTranslation:
    def test_typed_params_stripped(self):
        out = transpile_to_js("fn f(a: int, b: float) { return a }", include_runtime=False)
        assert "int" not in out
        assert "float" not in out
        assert "a" in out
        assert "b" in out

    def test_return_type_stripped(self):
        out = transpile_to_js("fn f(x: str) -> str { return x }", include_runtime=False)
        assert "-> str" not in out
        assert "x" in out

    def test_untyped_params_unchanged(self):
        out = transpile_to_js("fn f(x, y, z) { return x }", include_runtime=False)
        assert "x" in out
        assert "y" in out
        assert "z" in out

    def test_default_values_preserved(self):
        out = transpile_to_js("fn f(x: int = 0) { return x }", include_runtime=False)
        assert "0" in out


# ---------------------------------------------------------------------------
# Full transpilation
# ---------------------------------------------------------------------------

class TestFullTranspilation:
    def test_hello_world(self):
        source = 'println("Hello, World!")'
        js = transpile_to_js(source)
        assert isinstance(js, str)
        assert len(js) > 0
        assert "Hello, World!" in js or "console.log" in js

    def test_transpile_empty_source(self):
        js = transpile_to_js("")
        assert isinstance(js, str)

    def test_transpile_comment(self):
        js = transpile_to_js("// this is a comment")
        assert isinstance(js, str)

    def test_transpile_includes_runtime(self):
        js = transpile_to_js("let x = 1")
        # Output should include the runtime header
        assert len(js) > 50  # runtime is substantial

    def test_transpile_returns_string(self):
        result = transpile_to_js("let answer = 42")
        assert isinstance(result, str)

    def test_transpile_math_operations(self):
        source = "let result = 2 ** 10"
        js = transpile_to_js(source)
        assert "result" in js
        assert "10" in js

    def test_transpile_multiline(self):
        source = """let x = 1
let y = 2
let z = x + y
println(z)"""
        js = transpile_to_js(source)
        assert "x" in js
        assert "y" in js
        assert "z" in js

    def test_module_format_esm(self):
        js = transpile_to_js("let x = 1", module_format="esm")
        assert isinstance(js, str)

    def test_module_format_cjs(self):
        js = transpile_to_js("let x = 1", module_format="cjs")
        assert isinstance(js, str)

    def test_module_format_iife(self):
        js = transpile_to_js("let x = 1", module_format="iife")
        assert isinstance(js, str)


# ---------------------------------------------------------------------------
# Operator mapping
# ---------------------------------------------------------------------------

class TestOperatorMapping:
    def test_binary_ops_dict_exists(self):
        from lateralus_lang.codegen.javascript import BINARY_OPS
        assert isinstance(BINARY_OPS, dict)
        assert "==" in BINARY_OPS
        assert BINARY_OPS["=="] == "==="

    def test_unary_ops_dict_exists(self):
        from lateralus_lang.codegen.javascript import UNARY_OPS
        assert isinstance(UNARY_OPS, dict)
        assert "not" in UNARY_OPS
        assert UNARY_OPS["not"] == "!"


# ---------------------------------------------------------------------------
# Builtins
# ---------------------------------------------------------------------------

class TestBuiltins:
    def test_get_js_transpiler_builtins(self):
        builtins = get_js_transpiler_builtins()
        assert "JavaScriptTranspiler" in builtins
        assert "transpile_to_js" in builtins
        assert callable(builtins["transpile_to_js"])

    def test_builtins_transpiler_is_class(self):
        builtins = get_js_transpiler_builtins()
        t = builtins["JavaScriptTranspiler"]()
        assert hasattr(t, "transpile_string")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_transpile_with_unicode(self):
        js = transpile_to_js('let msg = "héllo wörld"')
        assert isinstance(js, str)

    def test_transpile_with_numbers(self):
        js = transpile_to_js("let pi = 3.14159")
        assert "3.14159" in js

    def test_transpile_large_source(self):
        source = "\n".join(f"let var_{i} = {i}" for i in range(100))
        js = transpile_to_js(source)
        assert isinstance(js, str)
        assert len(js) > 0

    def test_transpile_nested_calls(self):
        source = "let result = map(filter(data, fn(x) { x > 0 }), fn(x) { x * 2 })"
        js = transpile_to_js(source)
        assert isinstance(js, str)
