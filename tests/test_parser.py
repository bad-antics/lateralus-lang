"""
tests/test_parser.py  -  Parser unit tests
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.parser  import parse, ParseError
from lateralus_lang.ast_nodes import (
    Program, FnDecl, LetDecl, IfStmt, TryStmt, ReturnStmt, Literal, Ident,
    BinOp, CallExpr, WhileStmt, ForStmt, MatchStmt,
)


def ast(src):
    return parse(src, "<test>")


class TestProgram:
    def test_empty(self):
        p = ast("")
        assert isinstance(p, Program)
        assert p.body == []

    def test_module(self):
        p = ast("module mymod")
        assert p.module == "mymod"


class TestImport:
    def test_simple_import(self):
        p = ast("import io")
        assert len(p.imports) == 1
        assert p.imports[0].path == "io"

    def test_dotted_import(self):
        p = ast("import stdlib.math")
        assert p.imports[0].path == "stdlib.math"

    def test_aliased_import(self):
        p = ast("import io as stdio")
        assert p.imports[0].alias == "stdio"


class TestFnDecl:
    def test_simple_fn(self):
        p = ast("fn add(x: int, y: int) -> int { return x + y }")
        assert isinstance(p.body[0], FnDecl)
        fn = p.body[0]
        assert fn.name == "add"
        assert len(fn.params) == 2
        assert fn.ret_type.name == "int"

    def test_async_fn(self):
        p = ast("async fn fetch() { }")
        assert p.body[0].is_async is True

    def test_pub_fn(self):
        p = ast("pub fn greet() { }")
        assert p.body[0].is_pub is True

    def test_empty_fn_body(self):
        p = ast("fn nothing() { }")
        assert p.body[0].body.stmts == []


class TestLetDecl:
    def test_let_with_value(self):
        p = ast("let x = 42")
        stmt = p.body[0]
        assert isinstance(stmt, LetDecl)
        assert stmt.name == "x"
        assert isinstance(stmt.value, Literal)
        assert stmt.value.value == 42

    def test_let_with_type(self):
        p = ast("let name: str = \"hello\"")
        stmt = p.body[0]
        assert stmt.type_.name == "str"

    def test_const(self):
        p = ast("const PI: float = 3.14")
        stmt = p.body[0]
        assert stmt.is_const is True


class TestIfStmt:
    def test_simple_if(self):
        p = ast("if x > 0 { return 1 }")
        stmt = p.body[0]
        assert isinstance(stmt, IfStmt)

    def test_if_else(self):
        p = ast("if a { } else { }")
        stmt = p.body[0]
        assert stmt.else_block is not None

    def test_if_elif_else(self):
        p = ast("if a { } elif b { } else { }")
        stmt = p.body[0]
        assert len(stmt.elif_arms) == 1

    def test_else_if_syntax(self):
        """'else if' should be parsed identically to 'elif'."""
        p = ast("if a { } else if b { } else { }")
        stmt = p.body[0]
        assert len(stmt.elif_arms) == 1
        assert stmt.else_block is not None

    def test_else_if_chain(self):
        """Multiple 'else if' arms in a chain."""
        p = ast("if a { } else if b { } else if c { } else { }")
        stmt = p.body[0]
        assert len(stmt.elif_arms) == 2
        assert stmt.else_block is not None

    def test_mixed_elif_else_if(self):
        """Mix of 'elif' and 'else if' in the same chain."""
        p = ast("if a { } elif b { } else if c { } else { }")
        stmt = p.body[0]
        assert len(stmt.elif_arms) == 2

    def test_else_if_no_else(self):
        """'else if' without a trailing else block."""
        p = ast("if a { } else if b { }")
        stmt = p.body[0]
        assert len(stmt.elif_arms) == 1
        assert stmt.else_block is None


class TestTryStmt:
    def test_try_recover(self):
        p = ast("try { } recover MyError(e) { }")
        stmt = p.body[0]
        assert isinstance(stmt, TryStmt)
        assert stmt.recoveries[0].error_type == "MyError"
        assert stmt.recoveries[0].binding    == "e"

    def test_try_catch_all(self):
        p = ast("try { } recover * (e) { }")
        stmt = p.body[0]
        assert stmt.recoveries[0].error_type is None

    def test_try_ensure(self):
        p = ast("try { } ensure { }")
        stmt = p.body[0]
        assert stmt.ensure is not None


class TestExpressions:
    def test_binop_precedence(self):
        p = ast("let x = 2 + 3 * 4")
        # Should parse as 2 + (3 * 4)
        expr = p.body[0].value
        assert isinstance(expr, BinOp)
        assert expr.op == "+"
        assert isinstance(expr.right, BinOp)
        assert expr.right.op == "*"

    def test_pipeline(self):
        p = ast("let r = x |> f")
        expr = p.body[0].value
        assert isinstance(expr, BinOp)
        assert expr.op == "|>"

    def test_call_expr(self):
        p = ast("foo(1, 2, 3)")
        stmt = p.body[0]
        assert isinstance(stmt.expr, CallExpr)
        assert len(stmt.expr.args) == 3

    def test_field_access(self):
        p = ast("io.println(\"hi\")")
        stmt = p.body[0]
        # callee is a FieldExpr
        from lateralus_lang.ast_nodes import FieldExpr
        assert isinstance(stmt.expr.callee, FieldExpr)


class TestLoops:
    def test_while(self):
        p = ast("while i < 10 { i += 1 }")
        assert isinstance(p.body[0], WhileStmt)

    def test_for_in(self):
        p = ast("for x in items { }")
        stmt = p.body[0]
        assert isinstance(stmt, ForStmt)
        assert stmt.var == "x"


class TestMatchStmt:
    def test_match(self):
        p = ast('match x { 0 => "zero", 1 => "one", _ => "other" }')
        stmt = p.body[0]
        assert isinstance(stmt, MatchStmt)
        assert len(stmt.arms) == 3
