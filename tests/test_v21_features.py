"""
tests/test_v21_features.py  -  v2.1 Codegen & Runtime Improvements Test Suite
===========================================================================
Tests for LATERALUS v2.1 features:
  · Block lambda codegen: fn(x) { expr } → inline lambda
  · Multi-statement block lambda hoisting
  · Interface codegen (ABC generation)
  · Type annotation mapping (fn→callable, map→dict)
  · Pipeline + lambda composition
  · join / sqrt / math stdlib shims
  · v21 showcase compiles and runs
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.codegen.python import PythonTranspiler

# --- Helpers -----------------------------------------------------------------

ROOT = pathlib.Path(__file__).parent.parent


def compile_ok(src, target=Target.PYTHON, filename="<test>"):
    """Return True if source compiles without errors."""
    r = Compiler().compile_source(src, target=target, filename=filename)
    return r.ok


def compile_result(src, target=Target.PYTHON, filename="<test>"):
    return Compiler().compile_source(src, target=target, filename=filename)


def python_src(src, filename="<test>"):
    """Compile LTL source and return the Python transpilation."""
    r = Compiler().compile_source(src, target=Target.PYTHON, filename=filename)
    assert r.ok, f"Compile failed: {r.errors}"
    return r.python_src


def run_ltl(src):
    """Compile and execute LTL source, return captured stdout."""
    import io
    import contextlib
    py = python_src(src)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(py, {"__name__": "__main__"})
    return buf.getvalue()


def compile_file(path, target=Target.PYTHON):
    """Compile a .ltl file from the project root."""
    full = ROOT / path
    src = full.read_text()
    return Compiler().compile_source(src, target=target, filename=full.name)


# ===========================================================================
# 1. BLOCK LAMBDA CODEGEN
# ===========================================================================

class TestBlockLambdaCodegen:
    """Block lambdas fn(x) { expr } should generate proper Python."""

    def test_single_expr_block_lambda(self):
        """fn(x) { x * 2 } should become lambda x: (x * 2)."""
        src = 'let double = map([1,2,3], fn(x) { x * 2 })\nprintln(str(double))'
        py = python_src(src)
        assert "lambda x: (x * 2)" in py
        assert "block lambda" not in py

    def test_single_expr_block_lambda_runs(self):
        """Block lambda in map should produce correct results."""
        out = run_ltl('let r = map([1,2,3], fn(x) { x * x })\nprintln(str(r))')
        assert "[1, 4, 9]" in out

    def test_filter_block_lambda(self):
        """Block lambda in filter works correctly."""
        out = run_ltl('let r = filter([1,2,3,4,5], fn(x) { x > 3 })\nprintln(str(r))')
        assert "[4, 5]" in out

    def test_multi_stmt_block_lambda_hoisted(self):
        """Multi-statement block lambdas get hoisted to named functions."""
        src = '''
fn apply(f: fn, x: int) -> int { return f(x) }
let r = apply(fn(n) {
    let a = n * 2
    return a + 1
}, 5)
println(str(r))
'''
        py = python_src(src)
        assert "_ltl_lambda_" in py
        assert "block lambda" not in py

    def test_multi_stmt_lambda_runs(self):
        """Multi-statement block lambda executes correctly."""
        src = '''
fn apply(f: fn, x: int) -> int { return f(x) }
let r = apply(fn(n) {
    let a = n * 2
    return a + 1
}, 5)
println(str(r))
'''
        out = run_ltl(src)
        assert "11" in out

    def test_hoisted_lambda_before_usage(self):
        """Hoisted lambda def appears before the line that uses it."""
        src = '''
fn apply(f: fn, x: int) -> int { return f(x) }
let r = apply(fn(n) {
    let a = n + 10
    return a
}, 5)
'''
        py = python_src(src)
        lines = py.split("\n")
        def_line = None
        use_line = None
        for i, l in enumerate(lines):
            if "_ltl_lambda_" in l and l.strip().startswith("def "):
                def_line = i
            if "_ltl_lambda_" in l and "apply(" in l:
                use_line = i
        if def_line is not None and use_line is not None:
            assert def_line < use_line, "Hoisted lambda must be defined before use"

    def test_pipeline_with_block_lambda(self):
        """Pipeline operator with block lambdas."""
        out = run_ltl('''
let r = [1,2,3,4,5]
    |> map(fn(x) { x * x })
    |> filter(fn(x) { x > 5 })
    |> sum()
println(str(r))
''')
        assert "50" in out


# ===========================================================================
# 2. INTERFACE / TRAIT CODEGEN
# ===========================================================================

class TestInterfaceCodegen:
    """interface Foo { fn bar(self) -> str } should generate Python ABCs."""

    def test_interface_compiles(self):
        src = '''
interface Drawable {
    fn draw(self) -> str
}
struct Box {
    width: int
}
impl Drawable for Box {
    fn draw(self) -> str {
        return "Box(" + str(self.width) + ")"
    }
}
'''
        assert compile_ok(src)

    def test_interface_generates_abc(self):
        """Interface should generate a class inheriting from _ABC."""
        src = '''
interface Greetable {
    fn greet(self) -> str
}
'''
        py = python_src(src)
        assert "class Greetable(_ABC):" in py
        assert "@_abstractmethod" in py

    def test_impl_methods_injected_into_struct(self):
        """impl methods should appear inside the struct's Python class."""
        src = '''
struct Greeter { name: str }
impl Greeter {
    fn hello(self) -> str {
        return "Hi " + self.name
    }
}
'''
        py = python_src(src)
        assert "class Greeter:" in py
        assert "def hello(self):" in py

    def test_interface_impl_runs(self):
        """Interface + impl should work at runtime."""
        out = run_ltl('''
interface Showable {
    fn show(self) -> str
}
struct Item { name: str, qty: int }
impl Showable for Item {
    fn show(self) -> str {
        return self.name + " x" + str(self.qty)
    }
}
let item = Item { name: "Widget", qty: 42 }
println(item.show())
''')
        assert "Widget x42" in out


# ===========================================================================
# 3. TYPE ANNOTATION MAPPING
# ===========================================================================

class TestTypeAnnotationMapping:
    """Lateralus types should map to valid Python types in annotations."""

    def test_fn_type_maps_to_callable(self):
        """fn type annotation → callable."""
        src = 'fn apply(f: fn, x: int) -> int { return f(x) }'
        py = python_src(src)
        assert "f: callable" in py

    def test_map_type_maps_to_dict(self):
        """map type annotation → dict."""
        src = 'fn foo(data: map) { println(str(data)) }'
        py = python_src(src)
        assert "data: dict" in py

    def test_basic_types_unchanged(self):
        """int, str, float, bool pass through unchanged."""
        src = 'fn foo(a: int, b: str, c: float, d: bool) { return a }'
        py = python_src(src)
        assert "a: int" in py
        assert "b: str" in py
        assert "c: float" in py
        assert "d: bool" in py

    def test_let_type_annotation(self):
        """Let declarations with types get mapped too."""
        src = 'let x: int = 5'
        py = python_src(src)
        assert "x: int = 5" in py


# ===========================================================================
# 4. STDLIB SHIMS
# ===========================================================================

class TestStdlibShims:
    """Runtime shims for join, sqrt, math functions."""

    def test_join_shim(self):
        """join(list, sep) should work."""
        out = run_ltl('let r = join(["a","b","c"], ", ")\nprintln(r)')
        assert "a, b, c" in out

    def test_sqrt_shim(self):
        """sqrt should be available."""
        out = run_ltl('println(str(sqrt(16.0)))')
        assert "4.0" in out

    def test_math_functions(self):
        """sin, cos, floor, ceil should be available."""
        out = run_ltl('''
println(str(floor(3.7)))
println(str(ceil(3.2)))
''')
        assert "3" in out
        assert "4" in out

    def test_chr_ord_shims(self):
        """chr and ord should be available."""
        out = run_ltl('println(chr(65))\nprintln(str(ord("A")))')
        assert "A" in out
        assert "65" in out

    def test_keys_values_shims(self):
        """keys and values for dicts."""
        # {} is an empty block in Lateralus, not a dict — use map_new()
        src = 'let m = map_new()\nm["x"] = 1\nm["y"] = 2\nprintln(str(sorted(keys(m))))'
        out = run_ltl(src)
        assert "x" in out and "y" in out


# ===========================================================================
# 5. PIPELINE COMPOSITION
# ===========================================================================

class TestPipelineComposition:
    """Pipeline operator |> with various functions."""

    def test_map_filter_sum(self):
        """Chained map → filter → sum pipeline."""
        out = run_ltl('''
let r = [1,2,3,4,5]
    |> map(fn(x) { x * x })
    |> filter(fn(x) { x > 5 })
    |> sum()
println(str(r))
''')
        assert "50" in out

    def test_pipeline_with_len(self):
        """Pipeline result into len."""
        out = run_ltl('''
let r = [10, 20, 30, 40, 50]
    |> filter(fn(x) { x > 25 })
println(str(len(r)))
''')
        assert "3" in out

    def test_nested_pipeline(self):
        """Multiple pipeline stages."""
        out = run_ltl('''
let data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
let evens = data |> filter(fn(x) { x % 2 == 0 })
let doubled = evens |> map(fn(x) { x * 2 })
let total = doubled |> sum()
println(str(total))
''')
        assert "60" in out  # 2*2 + 4*2 + 6*2 + 8*2 + 10*2 = 60


# ===========================================================================
# 6. MEASURE BLOCK
# ===========================================================================

class TestMeasureBlock:
    """measure "label" { ... } should execute and print timing."""

    def test_measure_compiles(self):
        src = '''
measure "test_perf" {
    let x = 1 + 2
    println(str(x))
}
'''
        assert compile_ok(src)

    def test_measure_runs(self):
        """Measure block executes body and prints timing."""
        out = run_ltl('''
measure "addition" {
    let x = 1 + 2
    println(str(x))
}
''')
        assert "3" in out
        assert "addition" in out


# ===========================================================================
# 7. V21 SHOWCASE
# ===========================================================================

class TestV21Showcase:
    """The v21_showcase.ltl file should compile and execute."""

    def test_v21_showcase_compiles(self):
        r = compile_file("examples/v21_showcase.ltl")
        assert r.ok, f"v21_showcase.ltl failed to compile: {[e.message for e in r.errors[:3]]}"

    def test_v21_showcase_runs(self):
        r = compile_file("examples/v21_showcase.ltl")
        assert r.ok
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(r.python_src, {"__name__": "__main__"})
        out = buf.getvalue()
        # Verify key output sections
        assert "Lateralus v2.1" in out
        assert "Sensor readings:" in out
        assert "Pipeline demo:" in out
        assert "Metaprogramming demo:" in out
        assert "Fibonacci" in out
        assert "Result type demo:" in out
        assert "Performance demo:" in out
        assert "Iterator demo:" in out
        assert "Cryptography demo:" in out
        assert "Matrix operations demo:" in out
        assert "State machine demo:" in out
        assert "All demos complete" in out

    def test_v21_showcase_compiles_to_js(self):
        r = compile_file("examples/v21_showcase.ltl", target=Target.JAVASCRIPT)
        assert r.ok, f"JS compile failed: {[e.message for e in r.errors[:3]]}"

    def test_v21_showcase_compiles_to_c(self):
        r = compile_file("examples/v21_showcase.ltl", target=Target.C)
        assert r.ok, f"C compile failed: {[e.message for e in r.errors[:3]]}"


# ===========================================================================
# 8. ENUM CODEGEN
# ===========================================================================

class TestEnumCodegen:
    """Enum declarations should compile correctly."""

    def test_simple_enum_compiles(self):
        src = '''
enum Color {
    Red
    Green
    Blue
}
'''
        assert compile_ok(src)

    def test_enum_with_data_compiles(self):
        src = '''
enum Shape {
    Circle(radius: float)
    Rectangle(width: float, height: float)
}
'''
        assert compile_ok(src)

    def test_simple_enum_runs(self):
        """Simple enum values can be compared."""
        out = run_ltl('''
enum Direction {
    North
    South
    East
    West
}
let d = Direction.North
if d == Direction.North {
    println("Going north")
}
''')
        assert "Going north" in out
