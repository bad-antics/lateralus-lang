"""
tests/test_v12_features.py
──────────────────────────
Feature tests for v1.1 constructs (struct / enum / impl / interface /
decorator / yield / spawn / from-import / StructLiteral / InterpolatedStr)
and v1.2 constructs (foreign polyglot blocks / @foreign functions).

All tests operate through the public API:
    parse()               – test parsing only
    Compiler().compile_source()  – test parse + IR + transpile
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.parser  import parse, ParseError
from lateralus_lang.ast_nodes import (
    StructDecl, StructField, EnumDecl, EnumVariant, ImplBlock, InterfaceDecl,
    TypeAlias, StructLiteral, YieldExpr, SpawnExpr, ForeignBlock, ForeignParam,
    Decorator, FnDecl, ImportStmt, Literal, BinOp, InterpolatedStr,
)
from lateralus_lang.compiler import Compiler, Target


def ast(src):
    """Lex + parse src, return Program."""
    return parse(src, "<test>")


def check(src: str, target=Target.PYTHON):
    return Compiler().compile_source(src, target=target, filename="<test>")


# ═══════════════════════════════════════════════════════════════════════
#  STRUCT
# ═══════════════════════════════════════════════════════════════════════

class TestStructDecl:
    def test_empty_struct(self):
        p = ast("struct Empty {}")
        assert isinstance(p.body[0], StructDecl)
        assert p.body[0].name == "Empty"
        assert p.body[0].fields == []

    def test_struct_fields(self):
        p = ast("struct Point { x: int, y: int }")
        s = p.body[0]
        assert isinstance(s, StructDecl)
        assert len(s.fields) == 2
        assert s.fields[0].name == "x"
        assert s.fields[0].type_.name == "int"
        assert s.fields[1].name == "y"

    def test_struct_field_default(self):
        p = ast("struct Color { r: int = 0, g: int = 0, b: int = 255 }")
        s = p.body[0]
        assert s.fields[2].default is not None
        assert s.fields[2].default.value == 255

    def test_struct_with_generic_params(self):
        p = ast("struct Pair<T, U> { first: T, second: U }")
        s = p.body[0]
        assert s.name == "Pair"
        assert len(s.generics) == 2

    def test_struct_implements_interface(self):
        p = ast("struct Circle implements Shape { radius: float }")
        s = p.body[0]
        assert "Shape" in s.interfaces

    def test_struct_literal(self):
        p = ast("let p = Point { x: 1, y: 2 }")
        lit = p.body[0].value
        assert isinstance(lit, StructLiteral)
        assert lit.name == "Point"
        assert len(lit.fields) == 2

    def test_struct_literal_field_values(self):
        p = ast('let c = Color { r: 255, g: 128, b: 0 }')
        lit = p.body[0].value
        assert lit.fields[0][0] == "r"
        assert lit.fields[0][1].value == 255


# ═══════════════════════════════════════════════════════════════════════
#  ENUM
# ═══════════════════════════════════════════════════════════════════════

class TestEnumDecl:
    def test_simple_enum(self):
        p = ast("enum Direction { North, South, East, West }")
        e = p.body[0]
        assert isinstance(e, EnumDecl)
        assert e.name == "Direction"
        assert len(e.variants) == 4

    def test_enum_variant_names(self):
        p = ast("enum Status { Active, Inactive, Pending }")
        e = p.body[0]
        names = [v.name for v in e.variants]
        assert names == ["Active", "Inactive", "Pending"]

    def test_enum_with_values(self):
        p = ast("enum Code { Ok = 200, NotFound = 404, Error = 500 }")
        e = p.body[0]
        assert e.variants[0].value.value == 200
        assert e.variants[1].value.value == 404

    def test_enum_with_fields(self):
        p = ast("enum Shape { Circle { radius: float }, Rect { w: float, h: float } }")
        e = p.body[0]
        assert e.variants[0].name == "Circle"
        assert len(e.variants[0].fields) == 1
        assert e.variants[1].name == "Rect"
        assert len(e.variants[1].fields) == 2

    def test_enum_with_generic_params(self):
        p = ast("enum Option<T> { Some { value: T }, None }")
        e = p.body[0]
        assert len(e.generics) == 1
        assert e.generics[0] == "T"


# ═══════════════════════════════════════════════════════════════════════
#  IMPL BLOCK
# ═══════════════════════════════════════════════════════════════════════

class TestImplBlock:
    def test_simple_impl(self):
        p = ast("impl Circle { fn area(self) -> float { return 0.0 } }")
        impl = p.body[0]
        assert isinstance(impl, ImplBlock)
        assert impl.type_name == "Circle"

    def test_impl_method_count(self):
        p = ast("""
            impl Rectangle {
                fn area(self) -> float { return 0.0 }
                fn perimeter(self) -> float { return 0.0 }
            }
        """)
        impl = p.body[0]
        assert len(impl.methods) == 2

    def test_impl_method_name(self):
        p = ast("impl Point { fn distance(self, other: Point) -> float { return 0.0 } }")
        impl = p.body[0]
        assert impl.methods[0].name == "distance"

    def test_impl_for_interface(self):
        p = ast("impl Shape for Circle { fn area(self) -> float { return 0.0 } }")
        impl = p.body[0]
        assert impl.interface == "Shape"
        assert impl.type_name == "Circle"


# ═══════════════════════════════════════════════════════════════════════
#  INTERFACE
# ═══════════════════════════════════════════════════════════════════════

class TestInterfaceDecl:
    def test_empty_interface(self):
        p = ast("interface Drawable {}")
        iface = p.body[0]
        assert isinstance(iface, InterfaceDecl)
        assert iface.name == "Drawable"

    def test_interface_methods(self):
        p = ast("""
            interface Shape {
                fn area(self) -> float
                fn perimeter(self) -> float
            }
        """)
        iface = p.body[0]
        assert len(iface.methods) == 2
        assert iface.methods[0].name == "area"
        assert iface.methods[1].name == "perimeter"
        # Abstract methods have no body
        assert iface.methods[0].body is None

    def test_interface_extends(self):
        p = ast("interface Animal extends Living {}")
        iface = p.body[0]
        assert "Living" in iface.extends

    def test_interface_async_method(self):
        p = ast("interface Fetcher { async fn fetch(url: str) -> str }")
        iface = p.body[0]
        assert iface.methods[0].is_async is True
        assert iface.methods[0].body is None


# ═══════════════════════════════════════════════════════════════════════
#  TYPE ALIAS
# ═══════════════════════════════════════════════════════════════════════

class TestTypeAlias:
    def test_simple_alias(self):
        p = ast("type Point2D = Point")
        alias = p.body[0]
        assert isinstance(alias, TypeAlias)
        assert alias.name == "Point2D"
        assert alias.target.name == "Point"

    def test_alias_generic(self):
        p = ast("type NumList = List<int>")
        alias = p.body[0]
        assert alias.name == "NumList"


# ═══════════════════════════════════════════════════════════════════════
#  DECORATOR
# ═══════════════════════════════════════════════════════════════════════

class TestDecorators:
    def test_simple_decorator_on_struct(self):
        p = ast("@serializable struct Config { debug: bool }")
        s = p.body[0]
        assert isinstance(s, StructDecl)
        assert len(s.decorators) == 1
        assert s.decorators[0].name == "serializable"

    def test_decorator_with_args(self):
        p = ast('@deprecated("use NewPoint instead") struct OldPoint { x: int }')
        s = p.body[0]
        assert s.decorators[0].name == "deprecated"
        assert isinstance(s.decorators[0].args[0], Literal)

    def test_multiple_decorators(self):
        p = ast("""
            @serializable
            @loggable
            struct Config { debug: bool }
        """)
        s = p.body[0]
        assert len(s.decorators) == 2
        assert {d.name for d in s.decorators} == {"serializable", "loggable"}

    def test_decorator_on_fn(self):
        p = ast('@memoize fn fib(n: int) -> int { return n }')
        fn = p.body[0]
        assert isinstance(fn, FnDecl)
        assert len(fn.decorators) == 1
        assert fn.decorators[0].name == "memoize"

    def test_foreign_decorator_on_fn(self):
        p = ast('@foreign("julia") fn compute(n: int) -> float { "sqrt(n)" }')
        fn = p.body[0]
        assert isinstance(fn, FnDecl)
        assert fn.decorators[0].name == "foreign"
        assert fn.decorators[0].args[0].value == "julia"


# ═══════════════════════════════════════════════════════════════════════
#  FROM-IMPORT
# ═══════════════════════════════════════════════════════════════════════

class TestFromImport:
    def test_from_import_single(self):
        p = ast("from stdlib.math import sqrt")
        imp = p.imports[0]
        assert isinstance(imp, ImportStmt)
        assert imp.path == "stdlib.math"
        assert "sqrt" in imp.items

    def test_from_import_multiple(self):
        p = ast("from stdlib.strings import join, split, trim")
        imp = p.imports[0]
        assert imp.items == ["join", "split", "trim"]

    def test_from_import_braces(self):
        p = ast("from stdlib.collections import { head, tail, map }")
        imp = p.imports[0]
        assert "head" in imp.items
        assert "tail" in imp.items
        assert "map" in imp.items

    def test_from_import_with_alias(self):
        p = ast("from stdlib.math import PI as pi")
        imp = p.imports[0]
        assert imp.alias == "pi"


# ═══════════════════════════════════════════════════════════════════════
#  YIELD / SPAWN
# ═══════════════════════════════════════════════════════════════════════

class TestYieldAndSpawn:
    def test_yield_expr(self):
        p = ast("fn gen() { yield 42 }")
        from lateralus_lang.ast_nodes import ExprStmt
        stmt = p.body[0].body.stmts[0]
        assert isinstance(stmt, ExprStmt)
        assert isinstance(stmt.expr, YieldExpr)

    def test_yield_with_value(self):
        p = ast("fn gen() { yield x + 1 }")
        from lateralus_lang.ast_nodes import ExprStmt
        stmt = p.body[0].body.stmts[0]
        assert isinstance(stmt.expr.value, BinOp)
        assert stmt.expr.value.op == "+"

    def test_yield_nil(self):
        p = ast("fn gen() { yield }")
        from lateralus_lang.ast_nodes import ExprStmt
        stmt = p.body[0].body.stmts[0]
        assert stmt.expr.value is None

    def test_spawn_expr(self):
        p = ast("let task = spawn fetch(url)")
        val = p.body[0].value
        assert isinstance(val, SpawnExpr)


# ═══════════════════════════════════════════════════════════════════════
#  INTERPOLATED STRINGS
# ═══════════════════════════════════════════════════════════════════════

class TestInterpolatedStr:
    def test_interp_str_detected(self):
        p = ast('let msg = "Hello, ${name}!"')
        val = p.body[0].value
        assert isinstance(val, InterpolatedStr)

    def test_interp_str_parts(self):
        p = ast('let s = "Count: ${n}"')
        val = p.body[0].value
        assert isinstance(val, InterpolatedStr)
        # Should have at least a literal part and an expression part
        kinds = [kind for kind, _ in val.parts]
        assert "str" in kinds
        assert "expr" in kinds


# ═══════════════════════════════════════════════════════════════════════
#  FOREIGN BLOCK  (v1.2)
# ═══════════════════════════════════════════════════════════════════════

class TestForeignBlock:
    def test_simple_foreign_block(self):
        p = ast('foreign "julia" { "println(sqrt(2))" }')
        fb = p.body[0]
        assert isinstance(fb, ForeignBlock)
        assert fb.lang == "julia"
        assert "println" in fb.source

    def test_foreign_block_with_params(self):
        p = ast('foreign "julia" (n: limit) { "sqrt(n)" }')
        fb = p.body[0]
        assert len(fb.params) == 1
        assert fb.params[0].name == "n"

    def test_foreign_block_multiple_params(self):
        p = ast('foreign "rust" (x: width, y: height) { "x * y" }')
        fb = p.body[0]
        assert len(fb.params) == 2
        assert fb.params[0].name == "x"
        assert fb.params[1].name == "y"

    def test_foreign_block_c_runtime(self):
        p = ast('foreign "c" { "int main() { return 0; }" }')
        fb = p.body[0]
        assert fb.lang == "c"

    def test_foreign_block_in_fn(self):
        src = '''fn run_julia(n: int) -> float {
            foreign "julia" (val: n) { "sqrt(val)" }
        }'''
        p = ast(src)
        fn = p.body[0]
        assert isinstance(fn, FnDecl)
        assert isinstance(fn.body.stmts[0], ForeignBlock)


# ═══════════════════════════════════════════════════════════════════════
#  PYTHON TRANSPILER  – v1.1 constructs
# ═══════════════════════════════════════════════════════════════════════

class TestStructTranspiler:
    def test_struct_becomes_dataclass(self):
        r = check("struct Point { x: int, y: int }")
        assert r.ok
        assert "@_dataclass" in r.python_src
        assert "class Point" in r.python_src

    def test_struct_fields_in_class(self):
        r = check("struct Color { r: int = 255, g: int = 0, b: int = 0 }")
        assert r.ok
        assert "r: int" in r.python_src or "r:" in r.python_src

    def test_struct_with_impl_methods(self):
        src = """
            struct Circle { radius: float }
            impl Circle {
                fn area(self) -> float { return 3.14 }
            }
        """
        r = check(src)
        assert r.ok
        assert "def area" in r.python_src
        assert "@_dataclass" in r.python_src


class TestEnumTranspiler:
    def test_enum_becomes_enum_class(self):
        r = check("enum Direction { North, South, East, West }")
        assert r.ok
        assert "class Direction(_Enum)" in r.python_src

    def test_enum_variants_present(self):
        r = check("enum Status { Active, Inactive }")
        assert r.ok
        assert "Active" in r.python_src
        assert "Inactive" in r.python_src

    def test_enum_with_values(self):
        r = check("enum Code { Ok = 200, Error = 500 }")
        assert r.ok
        assert "200" in r.python_src
        assert "500" in r.python_src


class TestInterfaceTranspiler:
    def test_interface_becomes_abc(self):
        r = check("interface Shape { fn area(self) -> float }")
        assert r.ok
        assert "class Shape(_ABC)" in r.python_src

    def test_interface_methods_are_abstract(self):
        r = check("interface Drawable { fn draw(self) }")
        assert r.ok
        assert "@_abstractmethod" in r.python_src

    def test_interface_extends_abc(self):
        r = check("interface Animal extends Living {}")
        assert r.ok
        assert "Living" in r.python_src


class TestPipelineTranspiler:
    def test_single_pipeline(self):
        r = check("let y = x |> double")
        assert r.ok
        assert "double" in r.python_src

    def test_pipeline_becomes_call(self):
        r = check("let y = x |> double")
        assert r.ok
        # x |> double  →  double(x)
        assert "double(x)" in r.python_src

    def test_chained_pipeline(self):
        r = check("let z = x |> double |> negate")
        assert r.ok
        assert "negate" in r.python_src
        assert "double" in r.python_src


class TestInterpolatedStrTranspiler:
    def test_interp_str_becomes_fstring(self):
        r = check('let msg = "Hello, ${name}!"')
        assert r.ok
        assert 'f"' in r.python_src or "f'" in r.python_src

    def test_interp_str_with_expr(self):
        r = check('let s = "Value is ${x + 1}"')
        assert r.ok
        # f-string should contain the expression
        assert "x + 1" in r.python_src or "(x + 1)" in r.python_src


class TestYieldTranspiler:
    def test_yield_becomes_python_yield(self):
        r = check("fn counter() { yield 1 }")
        assert r.ok
        assert "(yield" in r.python_src or "yield " in r.python_src

    def test_spawn_becomes_ensure_future(self):
        r = check("let t = spawn fetch(url)")
        assert r.ok
        assert "ensure_future" in r.python_src


# ═══════════════════════════════════════════════════════════════════════
#  PYTHON TRANSPILER  – v1.2 foreign constructs
# ═══════════════════════════════════════════════════════════════════════

class TestForeignTranspiler:
    def test_foreign_block_transpiles(self):
        r = check('foreign "julia" { "println(1+1)" }')
        assert r.ok
        assert "_get_polyglot" in r.python_src
        assert "julia" in r.python_src

    def test_foreign_block_with_params_transpiles(self):
        r = check('foreign "rust" (x: n) { "x * 2" }')
        assert r.ok
        assert "rust" in r.python_src
        assert "_get_polyglot" in r.python_src

    def test_foreign_fn_decorator_transpiles(self):
        r = check('@foreign("julia") fn compute(n: int) -> float { "sqrt(n)" }')
        assert r.ok
        assert "def compute" in r.python_src
        assert "_get_polyglot" in r.python_src
        assert "julia" in r.python_src

    def test_foreign_fn_builds_params_dict(self):
        r = check('@foreign("julia") fn compute(n: int) -> float { "sqrt(n)" }')
        assert r.ok
        # Should contain params dict with the function param name
        assert '"n"' in r.python_src or "'n'" in r.python_src

    def test_foreign_fn_returns_result(self):
        r = check('@foreign("c") fn add(a: int, b: int) -> int { "a+b" }')
        assert r.ok
        assert "return" in r.python_src
        assert "_res" in r.python_src

    def test_polyglot_helper_in_header(self):
        r = check('let x = 1')
        assert r.ok
        assert "_get_polyglot" in r.python_src
