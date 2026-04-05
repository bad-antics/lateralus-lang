"""
tests/test_v20_features.py  -  v2.0 Self-Hosting Feature Test Suite
===========================================================================
Tests for LATERALUS v2.0 features:
  · Bootstrap: All 5 bootstrap files compile with production compiler
  · Grammar: EBNF spec updated for v1.6–v1.9 constructs
  · AST: v1.6 (select, nursery, async-for), v1.8 (macro, comptime),
         v1.9 (foreign, extern) parse correctly
  · Showcase: v2.0 showcase compiles without errors
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.lexer import lex, TK
from lateralus_lang.parser import parse, ParseError
from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.ast_nodes import (
    Program, FnDecl, LetDecl, StructDecl, EnumDecl, ExprStmt,
    MatchStmt, ForStmt, WhileStmt, IfStmt, ReturnStmt,
    ForeignBlock, SelectStmt, NurseryBlock, AsyncForStmt,
    MacroDecl, CompTimeBlock, ExternDecl,
)


# --- Helpers -----------------------------------------------------------------

ROOT = pathlib.Path(__file__).parent.parent

def compile_ok(src, target=Target.PYTHON, filename="<test>"):
    """Return True if source compiles without errors."""
    r = Compiler().compile_source(src, target=target, filename=filename)
    return r.ok

def compile_result(src, target=Target.PYTHON, filename="<test>"):
    return Compiler().compile_source(src, target=target, filename=filename)

def ast(src):
    return parse(src, "<test>")

def compile_file(path, target=Target.PYTHON):
    """Compile a .ltl file from the project root."""
    full = ROOT / path
    src = full.read_text()
    return Compiler().compile_source(src, target=target, filename=full.name)


# ===========================================================================
# 1. Bootstrap Compilation Tests
# ===========================================================================

class TestBootstrapCompilation:
    """All 5 bootstrap .ltl files must compile with the production compiler."""

    def test_bootstrap_lexer_compiles(self):
        r = compile_file("bootstrap/v2_lexer.ltl")
        assert r.ok, f"v2_lexer.ltl: {r.errors[0].message if r.errors else 'unknown'}"

    def test_bootstrap_parser_compiles(self):
        r = compile_file("bootstrap/v2_parser.ltl")
        assert r.ok, f"v2_parser.ltl: {r.errors[0].message if r.errors else 'unknown'}"

    def test_bootstrap_codegen_compiles(self):
        r = compile_file("bootstrap/v2_codegen.ltl")
        assert r.ok, f"v2_codegen.ltl: {r.errors[0].message if r.errors else 'unknown'}"

    def test_bootstrap_ir_codegen_compiles(self):
        r = compile_file("bootstrap/v2_ir_codegen.ltl")
        assert r.ok, f"v2_ir_codegen.ltl: {r.errors[0].message if r.errors else 'unknown'}"

    def test_bootstrap_python_codegen_compiles(self):
        r = compile_file("bootstrap/v2_python_codegen.ltl")
        assert r.ok, f"v2_python_codegen.ltl: {r.errors[0].message if r.errors else 'unknown'}"

    def test_all_bootstrap_files_present(self):
        bootstrap_dir = ROOT / "bootstrap"
        expected = [
            "v2_lexer.ltl", "v2_parser.ltl", "v2_codegen.ltl",
            "v2_ir_codegen.ltl", "v2_python_codegen.ltl",
        ]
        for name in expected:
            assert (bootstrap_dir / name).exists(), f"Missing bootstrap file: {name}"


# ===========================================================================
# 2. v1.6 Concurrency Parsing Tests
# ===========================================================================

class TestV16Parsing:
    """v1.6 structured concurrency constructs parse correctly."""

    def test_select_stmt_parses(self):
        src = """
select {
    msg from ch => {
        println(msg)
    }
    _ => {
        println("default")
    }
}
"""
        p = ast(src)
        assert any(isinstance(n, SelectStmt) for n in p.body)

    def test_nursery_block_parses(self):
        src = """
nursery {
    spawn task1()
    spawn task2()
}
"""
        p = ast(src)
        assert any(isinstance(n, NurseryBlock) for n in p.body)

    def test_async_for_parses(self):
        src = """
async for item in stream {
    println(item)
}
"""
        p = ast(src)
        assert any(isinstance(n, AsyncForStmt) for n in p.body)

    def test_select_with_timeout(self):
        src = """
select {
    msg from ch => { println(msg) }
    after 5000 => { println("timeout") }
}
"""
        p = ast(src)
        sel = [n for n in p.body if isinstance(n, SelectStmt)][0]
        assert len(sel.arms) == 2

    def test_select_with_send(self):
        src = """
select {
    send(ch, 42) => { println("sent") }
    _ => { println("default") }
}
"""
        p = ast(src)
        sel = [n for n in p.body if isinstance(n, SelectStmt)][0]
        assert sel.arms[0].kind == "send"


# ===========================================================================
# 3. v1.8 Metaprogramming Parsing Tests
# ===========================================================================

class TestV18Parsing:
    """v1.8 metaprogramming constructs parse correctly."""

    def test_macro_decl_parses(self):
        src = """
macro log!(msg) {
    println(msg)
}
"""
        p = ast(src)
        assert any(isinstance(n, MacroDecl) for n in p.body)

    def test_comptime_block_parses(self):
        src = """
comptime {
    let x = 1 + 2
}
"""
        p = ast(src)
        assert any(isinstance(n, CompTimeBlock) for n in p.body)

    def test_macro_with_multiple_params(self):
        src = """
macro assert_eq!(a, b) {
    if a != b {
        println("assertion failed")
    }
}
"""
        p = ast(src)
        m = [n for n in p.body if isinstance(n, MacroDecl)][0]
        assert m.name == "assert_eq"
        assert len(m.params) == 2


# ===========================================================================
# 4. v1.9 FFI Parsing Tests
# ===========================================================================

class TestV19Parsing:
    """v1.9 FFI constructs parse correctly."""

    def test_foreign_block_parses(self):
        src = '''
foreign "python" {
    "print('hello from python')"
}
'''
        p = ast(src)
        assert any(isinstance(n, ForeignBlock) for n in p.body)

    def test_foreign_with_params(self):
        src = '''
foreign "javascript" (x: 42, name: "test") {
    "console.log(x, name)"
}
'''
        p = ast(src)
        fb = [n for n in p.body if isinstance(n, ForeignBlock)][0]
        assert fb.lang == "javascript"
        assert len(fb.params) == 2

    def test_extern_decl_parses(self):
        src = "extern fn malloc(size: int) -> int"
        p = ast(src)
        assert any(isinstance(n, ExternDecl) for n in p.body)


# ===========================================================================
# 5. Grammar Spec Tests
# ===========================================================================

class TestGrammarSpec:
    """Verify grammar.ebnf is up-to-date for v2.0."""

    def test_grammar_exists(self):
        grammar = ROOT / "docs" / "grammar.ebnf"
        assert grammar.exists()

    def test_grammar_version(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "v2.0" in grammar

    def test_grammar_has_select(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "select_stmt" in grammar

    def test_grammar_has_nursery(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "nursery_block" in grammar

    def test_grammar_has_macro(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "macro_decl" in grammar

    def test_grammar_has_comptime(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "comptime_block" in grammar

    def test_grammar_has_foreign(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "foreign_block" in grammar

    def test_grammar_has_extern(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "extern_decl" in grammar

    def test_grammar_has_trait(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "trait_decl" in grammar

    def test_grammar_has_type_alias(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "type_alias" in grammar

    def test_grammar_has_channel_expr(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "channel_expr" in grammar

    def test_grammar_has_macro_invocation(self):
        grammar = (ROOT / "docs" / "grammar.ebnf").read_text()
        assert "macro_invocation" in grammar


# ===========================================================================
# 6. Showcase Compilation Tests
# ===========================================================================

class TestShowcaseCompilation:
    """All showcase examples must compile."""

    def test_v20_showcase_compiles(self):
        r = compile_file("examples/v20_showcase.ltl")
        assert r.ok, f"v20_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"

    def test_v19_showcase_compiles(self):
        r = compile_file("examples/v19_showcase.ltl")
        assert r.ok, f"v19_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"

    def test_v18_showcase_compiles(self):
        r = compile_file("examples/v18_showcase.ltl")
        assert r.ok, f"v18_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"

    def test_v17_showcase_compiles(self):
        r = compile_file("examples/v17_showcase.ltl")
        assert r.ok, f"v17_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"

    def test_v16_showcase_compiles(self):
        r = compile_file("examples/v16_showcase.ltl")
        assert r.ok, f"v16_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"

    def test_v15_showcase_compiles(self):
        r = compile_file("examples/v15_showcase.ltl")
        assert r.ok, f"v15_showcase.ltl failed: {r.errors[0].message if r.errors else '?'}"


# ===========================================================================
# 7. Multi-Target Compilation Tests
# ===========================================================================

class TestMultiTarget:
    """Basic programs compile to Python, C, and JavaScript targets."""

    BASIC_PROGRAM = "fn main() {\n    let x = 42\n    println(x)\n}\n"

    def test_python_target(self):
        r = compile_result(self.BASIC_PROGRAM, Target.PYTHON)
        assert r.ok, f"Python: {r.errors[0].message if r.errors else '?'}"

    def test_c_target(self):
        r = compile_result(self.BASIC_PROGRAM, Target.C)
        assert r.ok, f"C: {r.errors[0].message if r.errors else '?'}"

    def test_js_target(self):
        r = compile_result(self.BASIC_PROGRAM, Target.JAVASCRIPT)
        assert r.ok, f"JS: {r.errors[0].message if r.errors else '?'}"


# ===========================================================================
# 8. Bootstrap Parser Node Type Coverage
# ===========================================================================

class TestBootstrapParserCoverage:
    """Verify the bootstrap parser handles key constructs."""

    def test_struct_decl_compiles(self):
        src = "struct Token {\n    kind: str\n    value: str\n}\n"
        assert compile_ok(src)

    def test_enum_decl_compiles(self):
        src = "enum Color {\n    Red,\n    Green,\n    Blue,\n}\n"
        assert compile_ok(src)

    def test_match_stmt_compiles(self):
        src = "let x = 1\nlet r = match x {\n    1 => 10,\n    _ => 0,\n}\n"
        assert compile_ok(src)

    def test_lambda_expr_compiles(self):
        src = "let f = fn(x) { x + 1 }\n"
        assert compile_ok(src)

    def test_pipe_operator_compiles(self):
        src = "fn double(x: int) -> int { return x * 2 }\nlet r = 5 |> double\n"
        assert compile_ok(src)

    def test_spread_operator_compiles(self):
        src = "let a = [1, 2]\nlet b = [...a, 3, 4]\n"
        assert compile_ok(src)

    def test_trait_decl_compiles(self):
        src = "trait Printable {\n    fn to_str(self) -> str {\n        return \"\"\n    }\n}\n"
        assert compile_ok(src)

    def test_impl_block_compiles(self):
        src = """
struct Point {
    x: float
    y: float
}
impl Point {
    fn origin() -> Point {
        return Point { x: 0.0, y: 0.0 }
    }
}
"""
        assert compile_ok(src)

    def test_for_in_compiles(self):
        src = "for x in [1, 2, 3] {\n    println(x)\n}\n"
        assert compile_ok(src)

    def test_while_loop_compiles(self):
        src = "let mut i = 0\nwhile i < 10 {\n    i = i + 1\n}\n"
        assert compile_ok(src)

    def test_try_catch_compiles(self):
        src = "try {\n    let x = 1\n} catch e {\n    println(e)\n}\n"
        assert compile_ok(src)


# ===========================================================================
# 9. Lexer Keyword Coverage
# ===========================================================================

class TestLexerKeywords:
    """Verify all v1.6–v2.0 keywords are recognized by the lexer."""

    @pytest.mark.parametrize("kw", [
        "select", "nursery", "macro", "comptime",
        "foreign", "extern", "unsafe", "static",
        "spawn", "async", "await",
    ])
    def test_keyword_is_lexed(self, kw):
        tokens = lex(kw)
        tok = tokens[0]
        # Should be lexed as a keyword (KW_*), not IDENT
        assert tok.kind.name.startswith("KW_"), \
            f"'{kw}' lexed as {tok.kind.name}, expected KW_*"
