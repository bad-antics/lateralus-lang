"""
tests/test_js_backend.py  -  JavaScript Backend Tests
===========================================================================
Tests for the Lateralus → JavaScript (ES2022+) transpilation pipeline.
Covers the JavaScriptTranspiler, transpile_to_js API, and JS runtime.

v2.0
===========================================================================
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.codegen.javascript import (
    JavaScriptTranspiler,
    transpile_to_js,
    JSBuffer,
    JS_RUNTIME,
    BINARY_OPS,
    UNARY_OPS,
)


# ===============================================================================
# JSBuffer Tests
# ===============================================================================

class TestJSBuffer:
    """Test the JavaScript code buffer."""

    def test_empty_buffer(self):
        buf = JSBuffer()
        assert buf.get() == ""

    def test_write_line(self):
        buf = JSBuffer()
        buf.write("const x = 1;")
        assert buf.get() == "const x = 1;"

    def test_write_blank(self):
        buf = JSBuffer()
        buf.write("a")
        buf.blank()
        buf.write("b")
        assert buf.get() == "a\n\nb"

    def test_indent_dedent(self):
        buf = JSBuffer()
        buf.write("function f() {")
        buf.indent()
        buf.write("return 1;")
        buf.dedent()
        buf.write("}")
        result = buf.get()
        assert "  return 1;" in result
        assert result.endswith("}")

    def test_nested_indent(self):
        buf = JSBuffer()
        buf.indent()
        buf.indent()
        buf.write("deep;")
        assert "    deep;" in buf.get()

    def test_dedent_floor_zero(self):
        buf = JSBuffer()
        buf.dedent()  # should not go negative
        buf.write("x;")
        assert buf.get() == "x;"


# ===============================================================================
# Operator Mapping Tests
# ===============================================================================

class TestOperatorMapping:
    """Test LATERALUS → JavaScript operator mappings."""

    def test_equality_maps_to_strict(self):
        assert BINARY_OPS["=="] == "==="

    def test_inequality_maps_to_strict(self):
        assert BINARY_OPS["!="] == "!=="

    def test_arithmetic_preserved(self):
        assert BINARY_OPS["+"] == "+"
        assert BINARY_OPS["-"] == "-"
        assert BINARY_OPS["*"] == "*"
        assert BINARY_OPS["/"] == "/"
        assert BINARY_OPS["%"] == "%"

    def test_exponentiation(self):
        assert BINARY_OPS["**"] == "**"

    def test_comparison_preserved(self):
        assert BINARY_OPS["<"] == "<"
        assert BINARY_OPS[">"] == ">"
        assert BINARY_OPS["<="] == "<="
        assert BINARY_OPS[">="] == ">="

    def test_bitwise_preserved(self):
        assert BINARY_OPS["&"] == "&"
        assert BINARY_OPS["|"] == "|"
        assert BINARY_OPS["^"] == "^"
        assert BINARY_OPS["<<"] == "<<"
        assert BINARY_OPS[">>"] == ">>"

    def test_range_is_special(self):
        assert BINARY_OPS[".."] is None
        assert BINARY_OPS["..="] is None

    def test_unary_not(self):
        assert UNARY_OPS["not"] == "!"

    def test_unary_negate(self):
        assert UNARY_OPS["-"] == "-"


# ===============================================================================
# JS Runtime Tests
# ===============================================================================

class TestJSRuntime:
    """Test the embedded JavaScript runtime string."""

    def test_runtime_is_string(self):
        assert isinstance(JS_RUNTIME, str)

    def test_runtime_has_pipe(self):
        assert "pipe:" in JS_RUNTIME

    def test_runtime_has_println(self):
        assert "println" in JS_RUNTIME

    def test_runtime_has_range(self):
        assert "range:" in JS_RUNTIME

    def test_runtime_has_struct_helper(self):
        assert "struct:" in JS_RUNTIME

    def test_runtime_has_list_builtins(self):
        for fn in ["map:", "filter:", "reduce:", "sort:", "sum:", "flatten:"]:
            assert fn in JS_RUNTIME, f"Missing builtin: {fn}"

    def test_runtime_has_string_builtins(self):
        for fn in ["upper:", "lower:", "trim:", "split:", "join:"]:
            assert fn in JS_RUNTIME, f"Missing string builtin: {fn}"

    def test_runtime_has_math_constants(self):
        assert "PI:" in JS_RUNTIME
        assert "TAU:" in JS_RUNTIME

    def test_runtime_has_type_checks(self):
        assert "is_none:" in JS_RUNTIME
        assert "is_some:" in JS_RUNTIME

    def test_runtime_has_emit(self):
        assert "emit:" in JS_RUNTIME

    def test_runtime_has_probe(self):
        assert "probe:" in JS_RUNTIME

    def test_runtime_has_measure(self):
        assert "measure:" in JS_RUNTIME


# ===============================================================================
# JavaScriptTranspiler Tests
# ===============================================================================

class TestJavaScriptTranspiler:
    """Test the JavaScriptTranspiler class."""

    def test_create_transpiler(self):
        t = JavaScriptTranspiler()
        assert t.module_format == "esm"
        assert t.include_runtime is True

    def test_create_cjs_transpiler(self):
        t = JavaScriptTranspiler(module_format="cjs")
        assert t.module_format == "cjs"

    def test_create_without_runtime(self):
        t = JavaScriptTranspiler(include_runtime=False)
        assert t.include_runtime is False

    def test_transpile_empty(self):
        result = transpile_to_js("")
        assert isinstance(result, str)

    def test_transpile_comment(self):
        result = transpile_to_js("// hello world", include_runtime=False)
        # Comments may or may not be preserved in AST-based transpilation
        assert isinstance(result, str)

    def test_transpile_let(self):
        result = transpile_to_js("let x = 42", include_runtime=False)
        assert "const x = 42" in result or "let x = 42" in result

    def test_transpile_function(self):
        src = "fn greet(name: str) {\n    println(name)\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "function" in result or "=>" in result
        assert "greet" in result

    def test_transpile_return(self):
        src = "fn add(a: int, b: int) -> int {\n    return a + b\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "return" in result

    def test_transpile_preserves_arithmetic(self):
        result = transpile_to_js("let x = 1 + 2 * 3", include_runtime=False)
        assert "1" in result and "2" in result and "3" in result
        assert "+" in result and "*" in result

    def test_transpile_println(self):
        result = transpile_to_js('println("hello")', include_runtime=False)
        # println stays as println — the runtime provides it as console.log
        assert "println" in result

    def test_runtime_included_by_default(self):
        result = transpile_to_js("let x = 1")
        assert "__ltl" in result

    def test_runtime_excluded(self):
        result = transpile_to_js("let x = 1", include_runtime=False)
        assert "__ltl" not in result


# ===============================================================================
# AST-based Expression Tests
# ===============================================================================

class TestExpressionTranslation:
    """Test expression transpilation via full AST pipeline."""

    def _transpile(self, src: str) -> str:
        return transpile_to_js(src, include_runtime=False)

    def test_pipeline(self):
        result = self._transpile("let r = [1,2,3] |> filter(fn(x) { x > 1 })")
        assert "filter" in result

    def test_optional_pipeline(self):
        result = self._transpile("let x = 5\nlet r = x |? str")
        assert "null" in result or "str" in result

    def test_boolean_true(self):
        result = self._transpile("let x = true")
        assert "true" in result

    def test_boolean_false(self):
        result = self._transpile("let x = false")
        assert "false" in result

    def test_none_to_null(self):
        result = self._transpile("let x = None")
        assert "null" in result

    def test_lambda(self):
        result = self._transpile("let f = fn(x) { x + 1 }")
        assert "=>" in result

    def test_simple_value(self):
        result = self._transpile("let x = 42")
        assert "42" in result


# ===============================================================================
# Parameter Rendering Tests
# ===============================================================================

class TestParamTranslation:
    """Test parameter rendering strips type annotations."""

    def test_simple_param(self):
        result = transpile_to_js("fn f(x) { return x }", include_runtime=False)
        assert "function f(x)" in result

    def test_typed_param(self):
        result = transpile_to_js("fn f(x: int) { return x }", include_runtime=False)
        assert "int" not in result
        assert "x" in result

    def test_multiple_typed_params(self):
        result = transpile_to_js("fn f(x: int, y: str) { return x }", include_runtime=False)
        assert "x" in result
        assert "y" in result
        # Type annotations should be stripped
        assert ": int" not in result
        assert ": str" not in result

    def test_param_with_default(self):
        result = transpile_to_js("fn f(x: int = 0) { return x }", include_runtime=False)
        assert "x" in result
        assert "0" in result

    def test_empty_params(self):
        result = transpile_to_js("fn f() { return 1 }", include_runtime=False)
        assert "f()" in result


# ===============================================================================
# Statement Translation Tests
# ===============================================================================

class TestLineTranslation:
    """Test transpilation of various statement types."""

    def _transpile(self, src: str) -> str:
        return transpile_to_js(src, include_runtime=False)

    def test_comment_passthrough(self):
        # Comments within functions are preserved
        result = self._transpile("fn f() {\n    // test\n    return 1\n}")
        assert "return 1" in result

    def test_let_to_const(self):
        result = self._transpile("let x = 42")
        assert "const" in result
        assert "42" in result

    def test_fn_to_function(self):
        result = self._transpile("fn add(a: int, b: int) -> int {\n    return a + b\n}")
        assert "function" in result
        assert "add" in result

    def test_return_statement(self):
        result = self._transpile("fn f() -> int {\n    return 42\n}")
        assert "return" in result

    def test_println_to_runtime(self):
        result = self._transpile('println("hi")')
        assert "println" in result


# ===============================================================================
# Struct / Enum / Impl Tests
# ===============================================================================

class TestStructEnumImpl:
    """Test struct, enum, and impl transpilation."""

    def test_struct_to_class(self):
        result = transpile_to_js("struct Point { x: float, y: float }", include_runtime=False)
        assert "class Point" in result
        assert "constructor" in result
        assert "this.x" in result
        assert "this.y" in result

    def test_struct_has_type_tag(self):
        result = transpile_to_js("struct Foo { val: int }", include_runtime=False)
        assert '__type = "Foo"' in result

    def test_enum_to_frozen_object(self):
        result = transpile_to_js("enum Color {\n    Red,\n    Green,\n    Blue,\n}", include_runtime=False)
        assert "Object.freeze" in result
        assert '"Red"' in result
        assert '"Green"' in result
        assert '"Blue"' in result

    def test_enum_adt_variant(self):
        result = transpile_to_js("enum Shape {\n    Circle(radius: float),\n    Rect(w: float, h: float),\n}", include_runtime=False)
        assert "Circle:" in result
        assert "__variant" in result
        assert "radius" in result

    def test_impl_adds_prototype_methods(self):
        src = ("struct Vec { x: float, y: float }\n"
               "impl Vec {\n"
               "    fn length(self) -> float {\n"
               "        return sqrt(self.x * self.x + self.y * self.y)\n"
               "    }\n"
               "}")
        result = transpile_to_js(src, include_runtime=False)
        assert "Vec.prototype.length" in result
        assert "this.x" in result

    def test_struct_literal(self):
        src = "struct P { x: int, y: int }\nlet p = P{x: 1, y: 2}"
        result = transpile_to_js(src, include_runtime=False)
        assert "new P(1, 2)" in result

    def test_type_alias(self):
        result = transpile_to_js("pub type Score = int", include_runtime=False)
        assert "Score" in result
        assert "@typedef" in result


# ===============================================================================
# Control Flow Tests
# ===============================================================================

class TestControlFlow:
    """Test control flow transpilation."""

    def test_if_statement(self):
        src = "if true {\n    println(\"yes\")\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "if (true)" in result

    def test_if_else(self):
        src = "if false {\n    println(\"no\")\n} else {\n    println(\"yes\")\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "else" in result

    def test_while_loop(self):
        src = "fn f() {\n    let mut i = 0\n    while i < 10 {\n        i = i + 1\n    }\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "while" in result

    def test_for_loop(self):
        src = "for x in [1, 2, 3] {\n    println(x)\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "for (const x of" in result

    def test_match_expression(self):
        src = "let r = match 42 {\n    1 => \"one\",\n    42 => \"answer\",\n    _ => \"other\",\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "42" in result
        assert '"answer"' in result
        assert '"other"' in result

    def test_loop_stmt(self):
        src = "fn f() {\n    loop {\n        break\n    }\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "while (true)" in result
        assert "break" in result

    def test_break_and_continue(self):
        src = "fn f() {\n    while true {\n        if true {\n            break\n        }\n        continue\n    }\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "break" in result
        assert "continue" in result

    def test_guard(self):
        src = "fn f(x: int) {\n    guard x > 0 else {\n        return\n    }\n    println(x)\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "if (!" in result


# ===============================================================================
# Advanced Feature Tests
# ===============================================================================

class TestAdvancedFeatures:
    """Test advanced language feature transpilation."""

    def test_comprehension(self):
        src = "let sq = [x * x for x in [1,2,3]]"
        result = transpile_to_js(src, include_runtime=False)
        assert ".map(" in result

    def test_ternary_expression(self):
        src = "let x = true ? 1 : 0"
        result = transpile_to_js(src, include_runtime=False)
        assert "?" in result
        assert ":" in result

    def test_cast_expression(self):
        src = 'let x = 42 as str'
        result = transpile_to_js(src, include_runtime=False)
        assert "String" in result

    def test_string_interpolation(self):
        src = 'let name = "world"\nlet msg = "Hello ${name}"'
        result = transpile_to_js(src, include_runtime=False)
        assert "`" in result or "${" in result or "name" in result

    def test_import_esm(self):
        src = "import math"
        result = transpile_to_js(src, include_runtime=False)
        assert "import" in result
        assert "math" in result

    def test_import_cjs(self):
        t = JavaScriptTranspiler(module_format="cjs", include_runtime=False)
        result = t.transpile_string("import math")
        assert "require" in result
        assert "math" in result

    def test_spread(self):
        src = "let a = [1, 2]\nlet b = [...a, 3]"
        result = transpile_to_js(src, include_runtime=False)
        assert "..." in result

    def test_interface_decl(self):
        src = "trait Drawable {\n    fn draw(self) {\n        return\n    }\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "Drawable" in result

    def test_async_function(self):
        src = "async fn fetch_data() {\n    return 42\n}"
        result = transpile_to_js(src, include_runtime=False)
        assert "async" in result
        assert "function" in result

    def test_measure_block(self):
        src = 'fn f() {\n    measure "test" {\n        let x = 1\n    }\n}'
        result = transpile_to_js(src, include_runtime=False)
        assert "performance" in result or "measure" in result

    def test_emit_stmt(self):
        src = 'emit data_ready(42)'
        result = transpile_to_js(src, include_runtime=False)
        assert "emit" in result
        assert "data_ready" in result

    def test_pub_function(self):
        src = "pub fn greet() {\n    println(\"hi\")\n}"
        result = JavaScriptTranspiler(module_format="esm", include_runtime=False).transpile_string(src)
        assert "export" in result
        assert "function greet" in result

    def test_mutable_let(self):
        src = "let mut x = 0\nx = 1"
        result = transpile_to_js(src, include_runtime=False)
        assert "let x" in result


# ===============================================================================
# Integration Tests
# ===============================================================================

class TestJSIntegration:
    """Integration tests for full transpilation."""

    def test_fibonacci_transpiles(self):
        src = """fn fibonacci(n: int) -> int {
    if n <= 1 {
        return n
    }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

let result = fibonacci(10)
println(result)"""
        result = transpile_to_js(src, include_runtime=False)
        assert "fibonacci" in result
        assert "function" in result or "=>" in result

    def test_pipeline_transpiles(self):
        src = """let data = [1, 2, 3, 4, 5]
let result = data |> filter(fn(x) { x > 2 }) |> map(fn(x) { x * x })"""
        result = transpile_to_js(src, include_runtime=False)
        assert "filter" in result
        assert "map" in result

    def test_struct_transpiles(self):
        src = "struct Point { x: float, y: float }"
        result = transpile_to_js(src, include_runtime=False)
        assert "class" in result or "Point" in result

    def test_full_program_produces_valid_js(self):
        src = '''let x = 42
let name = "Lateralus"
println(name)'''
        result = transpile_to_js(src, include_runtime=False)
        assert "42" in result
        assert "Lateralus" in result

    def test_get_js_transpiler_builtins(self):
        from lateralus_lang.codegen.javascript import get_js_transpiler_builtins
        builtins = get_js_transpiler_builtins()
        assert "transpile_to_js" in builtins
        assert "JavaScriptTranspiler" in builtins
        assert "JS_RUNTIME" in builtins

    def test_full_showcase_transpiles(self):
        """Transpile a realistic multi-feature program."""
        src = """import strings

struct Person {
    name: str
    age: int
}

enum Color {
    Red,
    Green,
    Blue,
}

fn greet(p: Person) -> str {
    return "Hello, " + p.name
}

fn main() {
    let people = [
        Person{name: "Alice", age: 30},
        Person{name: "Bob", age: 25},
    ]

    for p in people {
        println(greet(p))
    }

    let ages = people |> map(fn(p) { p.age })
    let total = ages |> sum()
    println("Total age: " + str(total))

    let result = match 42 {
        1 => "one",
        42 => "the answer",
        _ => "other",
    }
    println(result)
}

main()"""
        result = transpile_to_js(src, include_runtime=False)
        assert "class Person" in result
        assert "Object.freeze" in result
        assert "function greet" in result
        assert "function main" in result
        assert "for (const" in result
