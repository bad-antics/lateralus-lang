"""
tests/test_v18_features.py — Lateralus v1.8 Metaprogramming Tests
═══════════════════════════════════════════════════════════════════════════
Covers:
  • const fn — compile-time function evaluation
  • macro / macro!() — syntactic macro declaration & invocation
  • comptime { } — compile-time block evaluation
  • @derive(Trait, ...) — auto-generated trait implementations
  • reflect!(Type) — compile-time type introspection
  • quote { } — AST quoting
  • AST nodes — ConstFnDecl, MacroDecl, MacroInvocation, etc.
  • Integration — v18_showcase.ltl, all examples compile
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import textwrap

import pytest

from lateralus_lang.ast_nodes import (
    ConstFnDecl, MacroDecl, MacroInvocation, CompTimeBlock,
    DeriveAttr, ReflectExpr, QuoteExpr, UnquoteExpr, SourceSpan,
)
from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.lexer import Lexer, TK
from lateralus_lang.parser import Parser

# Helpers
def _compile(src: str) -> object:
    return Compiler().compile_source(textwrap.dedent(src).strip(),
                                     target=Target.PYTHON, filename="test.ltl")

def _parse(src: str):
    tokens = Lexer(textwrap.dedent(src).strip()).tokenize()
    return Parser(tokens).parse()


# ═══════════════════════════════════════════════════════════════════════
# Lexer — new keywords
# ═══════════════════════════════════════════════════════════════════════

class TestLexerKeywords:
    """Verify v1.8 keywords tokenize correctly."""

    def test_macro_keyword(self):
        toks = Lexer("macro").tokenize()
        assert toks[0].kind == TK.KW_MACRO

    def test_comptime_keyword(self):
        toks = Lexer("comptime").tokenize()
        assert toks[0].kind == TK.KW_COMPTIME

    def test_derive_keyword(self):
        toks = Lexer("derive").tokenize()
        assert toks[0].kind == TK.KW_DERIVE

    def test_reflect_keyword(self):
        toks = Lexer("reflect").tokenize()
        assert toks[0].kind == TK.KW_REFLECT


# ═══════════════════════════════════════════════════════════════════════
# AST Nodes
# ═══════════════════════════════════════════════════════════════════════

class TestASTNodes:
    """Verify v1.8 AST node construction."""

    def test_const_fn_decl(self):
        node = ConstFnDecl(span=None, name="sq", params=[])
        assert node.name == "sq"
        assert node.is_pub is False

    def test_macro_decl(self):
        node = MacroDecl(span=None, name="log", params=["msg"])
        assert node.name == "log"
        assert node.params == ["msg"]

    def test_macro_invocation(self):
        node = MacroInvocation(span=None, name="vec", args=[])
        assert node.name == "vec"

    def test_comptime_block(self):
        node = CompTimeBlock(span=None)
        assert node.body is None

    def test_derive_attr(self):
        node = DeriveAttr(span=None, traits=["Debug", "Clone"])
        assert "Debug" in node.traits
        assert len(node.traits) == 2

    def test_reflect_expr(self):
        node = ReflectExpr(span=None, target="Point")
        assert node.target == "Point"

    def test_quote_expr(self):
        node = QuoteExpr(span=None)
        assert node.body is None

    def test_unquote_expr(self):
        node = UnquoteExpr(span=None)
        assert node.expr is None


# ═══════════════════════════════════════════════════════════════════════
# Parser — const fn
# ═══════════════════════════════════════════════════════════════════════

class TestParserConstFn:
    """const fn parsing."""

    def test_basic_const_fn(self):
        tree = _parse("const fn square(x: int) -> int { return x * x }")
        assert isinstance(tree.body[0], ConstFnDecl)
        assert tree.body[0].name == "square"

    def test_const_fn_no_params(self):
        tree = _parse("const fn pi() -> float { return 3.14159 }")
        assert isinstance(tree.body[0], ConstFnDecl)
        assert tree.body[0].name == "pi"
        assert tree.body[0].params == []

    def test_const_fn_multiple_params(self):
        tree = _parse("const fn add(a: int, b: int) -> int { return a + b }")
        node = tree.body[0]
        assert isinstance(node, ConstFnDecl)
        assert len(node.params) == 2


# ═══════════════════════════════════════════════════════════════════════
# Parser — macro
# ═══════════════════════════════════════════════════════════════════════

class TestParserMacro:
    """macro declaration and invocation parsing."""

    def test_macro_decl(self):
        tree = _parse("macro assert_eq!(a, b) { if a != b { throw \"fail\" } }")
        assert isinstance(tree.body[0], MacroDecl)
        assert tree.body[0].name == "assert_eq"
        assert tree.body[0].params == ["a", "b"]

    def test_macro_decl_no_params(self):
        tree = _parse("macro noop!() { pass }")
        assert isinstance(tree.body[0], MacroDecl)
        assert tree.body[0].params == []

    def test_macro_invocation(self):
        tree = _parse("let x = vec!(1, 2, 3)")
        invoc = tree.body[0].value
        assert isinstance(invoc, MacroInvocation)
        assert invoc.name == "vec"
        assert len(invoc.args) == 3

    def test_macro_invocation_no_args(self):
        tree = _parse("let x = timestamp!()")
        invoc = tree.body[0].value
        assert isinstance(invoc, MacroInvocation)
        assert invoc.name == "timestamp"
        assert invoc.args == []

    def test_macro_invocation_single_arg(self):
        tree = _parse('let x = stringify!("hello")')
        invoc = tree.body[0].value
        assert isinstance(invoc, MacroInvocation)
        assert invoc.name == "stringify"
        assert len(invoc.args) == 1


# ═══════════════════════════════════════════════════════════════════════
# Parser — comptime
# ═══════════════════════════════════════════════════════════════════════

class TestParserComptime:
    """comptime { } block parsing."""

    def test_comptime_block(self):
        tree = _parse("comptime { let x = 42 }")
        assert isinstance(tree.body[0], CompTimeBlock)

    def test_comptime_as_expression(self):
        tree = _parse("let val = comptime { 1 + 2 }")
        assert tree.body[0].value is not None

    def test_comptime_with_multiple_stmts(self):
        tree = _parse("comptime { let a = 1\nlet b = 2 }")
        assert isinstance(tree.body[0], CompTimeBlock)


# ═══════════════════════════════════════════════════════════════════════
# Parser — reflect!
# ═══════════════════════════════════════════════════════════════════════

class TestParserReflect:
    """reflect!(Type) expression parsing."""

    def test_reflect_basic(self):
        tree = _parse("let info = reflect!(Point)")
        assert isinstance(tree.body[0].value, ReflectExpr)
        assert tree.body[0].value.target == "Point"

    def test_reflect_in_expression(self):
        tree = _parse("println(reflect!(MyStruct))")
        # The reflect! is inside a call expression
        call = tree.body[0].expr
        assert isinstance(call.args[0], ReflectExpr)


# ═══════════════════════════════════════════════════════════════════════
# Parser — quote
# ═══════════════════════════════════════════════════════════════════════

class TestParserQuote:
    """quote { } expression parsing."""

    def test_quote_basic(self):
        tree = _parse("let ast = quote { 1 + 2 }")
        assert isinstance(tree.body[0].value, QuoteExpr)

    def test_quote_with_call(self):
        tree = _parse("let ast = quote { println(42) }")
        assert isinstance(tree.body[0].value, QuoteExpr)


# ═══════════════════════════════════════════════════════════════════════
# Parser — @derive decorator
# ═══════════════════════════════════════════════════════════════════════

class TestParserDerive:
    """@derive(Trait, ...) decorator parsing."""

    def test_derive_single_trait(self):
        tree = _parse("@derive(Debug)\nstruct Foo { x: int }")
        assert tree.body[0].decorators[0].name == "derive"
        assert len(tree.body[0].decorators[0].args) == 1

    def test_derive_multiple_traits(self):
        tree = _parse("@derive(Debug, Clone, Eq)\nstruct Foo { x: int }")
        d = tree.body[0].decorators[0]
        assert d.name == "derive"
        assert len(d.args) == 3

    def test_derive_on_enum(self):
        tree = _parse("@derive(Debug)\nenum Color { Red, Green, Blue }")
        assert tree.body[0].decorators[0].name == "derive"


# ═══════════════════════════════════════════════════════════════════════
# Codegen — const fn
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenConstFn:
    """const fn Python codegen."""

    def test_const_fn_compiles(self):
        r = _compile("const fn square(x: int) -> int { return x * x }")
        assert r.ok
        assert "def square" in r.python_src
        assert "_lru_cache" in r.python_src

    def test_const_fn_called(self):
        r = _compile("""
            const fn double(n: int) -> int { return n * 2 }
            let x = double(21)
        """)
        assert r.ok
        assert "def double" in r.python_src


# ═══════════════════════════════════════════════════════════════════════
# Codegen — macro
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenMacro:
    """Macro declaration and invocation codegen."""

    def test_macro_decl_emits_function(self):
        r = _compile('macro greet!(name) { println("Hello " + name) }')
        assert r.ok
        assert "_macro_greet" in r.python_src

    def test_macro_invocation_calls_function(self):
        r = _compile("""
            macro double!(x) { return x * 2 }
            let result = double!(5)
        """)
        assert r.ok
        assert "_macro_double(5)" in r.python_src

    def test_macro_no_args(self):
        r = _compile("""
            macro now!() { return 0 }
            let t = now!()
        """)
        assert r.ok
        assert "_macro_now()" in r.python_src


# ═══════════════════════════════════════════════════════════════════════
# Codegen — comptime
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenComptime:
    """comptime block codegen."""

    def test_comptime_emits_block(self):
        r = _compile("comptime { let x = 42 }")
        assert r.ok
        assert "comptime" in r.python_src  # marker comment

    def test_comptime_with_computation(self):
        r = _compile("comptime { let fib_10 = 55 }")
        assert r.ok


# ═══════════════════════════════════════════════════════════════════════
# Codegen — reflect!
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenReflect:
    """reflect!() expression codegen."""

    def test_reflect_emits_type_info(self):
        r = _compile("""
            struct Foo { a: int, b: str }
            let info = reflect!(Foo)
        """)
        assert r.ok
        assert '_type_info("Foo")' in r.python_src

    def test_reflect_in_call(self):
        r = _compile("""
            struct Bar { x: float }
            println(reflect!(Bar))
        """)
        assert r.ok
        assert '_type_info("Bar")' in r.python_src


# ═══════════════════════════════════════════════════════════════════════
# Codegen — @derive
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenDerive:
    """@derive auto-generates trait methods."""

    def test_derive_debug(self):
        r = _compile("@derive(Debug)\nstruct P { x: int, y: int }")
        assert r.ok
        assert "__repr__" in r.python_src

    def test_derive_clone(self):
        r = _compile("@derive(Clone)\nstruct P { x: int }")
        assert r.ok
        assert "def clone(self)" in r.python_src

    def test_derive_eq(self):
        r = _compile("@derive(Eq)\nstruct P { x: int }")
        assert r.ok
        assert "__eq__" in r.python_src

    def test_derive_hash(self):
        r = _compile("@derive(Hash)\nstruct P { x: int }")
        assert r.ok
        assert "__hash__" in r.python_src

    def test_derive_default(self):
        r = _compile("@derive(Default)\nstruct P { x: int, y: float }")
        assert r.ok
        assert "def default(cls)" in r.python_src

    def test_derive_serialize(self):
        r = _compile("@derive(Serialize)\nstruct P { x: int }")
        assert r.ok
        assert "def to_dict(self)" in r.python_src

    def test_derive_deserialize(self):
        r = _compile("@derive(Deserialize)\nstruct P { x: int }")
        assert r.ok
        assert "def from_dict(cls" in r.python_src

    def test_derive_display(self):
        r = _compile("@derive(Display)\nstruct P { x: int }")
        assert r.ok
        assert "__str__" in r.python_src

    def test_derive_multiple_traits(self):
        r = _compile("@derive(Debug, Clone, Eq, Hash)\nstruct P { x: int, y: int }")
        assert r.ok
        assert "__repr__" in r.python_src
        assert "clone" in r.python_src
        assert "__eq__" in r.python_src
        assert "__hash__" in r.python_src

    def test_derive_empty_struct(self):
        r = _compile("@derive(Debug, Clone)\nstruct Empty { }")
        assert r.ok
        assert "__repr__" in r.python_src

    def test_derive_all_seven(self):
        r = _compile("""
            @derive(Debug, Clone, Eq, Hash, Default, Serialize, Deserialize)
            struct Record { id: int, name: str, active: bool }
        """)
        assert r.ok
        src = r.python_src
        assert "__repr__" in src
        assert "clone" in src
        assert "__eq__" in src
        assert "__hash__" in src
        assert "default" in src
        assert "to_dict" in src
        assert "from_dict" in src


# ═══════════════════════════════════════════════════════════════════════
# Codegen — quote
# ═══════════════════════════════════════════════════════════════════════

class TestCodegenQuote:
    """quote { } expression codegen."""

    def test_quote_compiles(self):
        r = _compile("let ast = quote { 1 + 2 }")
        assert r.ok
        assert "__ast__" in r.python_src


# ═══════════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════════

class TestVersion:
    def test_version_is_1_8_0(self):
        import lateralus_lang
        assert lateralus_lang.__version__ == "2.5.1"


# ═══════════════════════════════════════════════════════════════════════
# Integration
# ═══════════════════════════════════════════════════════════════════════

class TestV18Integration:
    """End-to-end integration tests."""

    def test_v18_showcase_compiles(self):
        import pathlib
        showcase = pathlib.Path(__file__).parent.parent / "examples" / "v18_showcase.ltl"
        if showcase.exists():
            r = Compiler().compile_source(showcase.read_text(),
                                          target=Target.PYTHON,
                                          filename="v18_showcase.ltl")
            assert r.ok, f"v18_showcase failed: {r.errors[0].message if r.errors else '?'}"

    def test_all_examples_compile(self):
        """Verify ALL .ltl examples still compile after v1.8 changes."""
        import pathlib
        examples_dir = pathlib.Path(__file__).parent.parent / "examples"
        failures = []
        for ltl in sorted(examples_dir.glob("*.ltl")):
            r = Compiler().compile_source(ltl.read_text(),
                                          target=Target.PYTHON,
                                          filename=ltl.name)
            if not r.ok:
                failures.append(f"{ltl.name}: {r.errors[0].message}")
        assert not failures, "Example failures:\n" + "\n".join(failures)

    def test_const_fn_and_derive_together(self):
        """Test multiple v1.8 features in one source."""
        r = _compile("""
            const fn default_radius() -> float { return 1.0 }

            @derive(Debug, Clone, Eq)
            struct Circle {
                radius: float
            }

            let c = Circle { radius: 3.14 }
            let info = reflect!(Circle)
        """)
        assert r.ok

    def test_macro_and_comptime_together(self):
        """Test macro + comptime features together."""
        r = _compile("""
            macro dbg!(val) {
                println(val)
            }
            comptime {
                let version = "1.8.0"
            }
            dbg!("hello")
        """)
        assert r.ok
