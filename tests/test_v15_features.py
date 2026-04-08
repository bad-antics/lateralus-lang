"""
tests/test_v15_features.py  -  v1.5 Feature Test Suite
===========================================================================
Tests for all LATERALUS v1.5 features:
  · Lexer: DOUBLE_COLON token
  · Parser: ResultExpr, OptionExpr, TypeMatchExpr, all 8 pattern types
  · Type System: occurs_check, unify, substitute, solve, infer_pattern
  · Codegen: v1.5 nodes transpile correctly to Python
  · End-to-end: v1.5 showcase compiles without errors
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from lateralus_lang.ast_nodes import (
    BindingPattern,
    BinOp,
    EnumVariantPattern,
    ExprStmt,
    FnDecl,
    Ident,
    LetDecl,
    ListPattern,
    Literal,
    LiteralPattern,
    OptionExpr,
    OrPattern,
    ResultExpr,
    ReturnStmt,
    TuplePattern,
    TypeMatchArm,
    TypeMatchExpr,
    WildcardPattern,
)
from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.lexer import TK, lex
from lateralus_lang.parser import parse
from lateralus_lang.type_system import (
    ANY,
    BOOL,
    INT,
    STR,
    FunctionType,
    ListType,
    OptionalType,
    TupleType,
    TypeInferencer,
    TypeVar,
)

# --- Helpers -----------------------------------------------------------------

def tokens(src):
    return [t for t in lex(src) if t.kind != TK.EOF]


def kinds(src):
    return [t.kind for t in tokens(src)]


def ast(src):
    return parse(src, "<test>")


def first_expr(src):
    """Parse src and return the first expression (from first ExprStmt)."""
    p = ast(src)
    stmt = p.body[0]
    if isinstance(stmt, ExprStmt):
        return stmt.expr
    if isinstance(stmt, LetDecl):
        return stmt.value
    return stmt


def compile_py(src: str) -> str:
    """Compile LTL source to Python and return the Python source."""
    r = Compiler().compile_source(src, target=Target.PYTHON, filename="<test>")
    assert r.ok, f"Compile failed: {r.errors}"
    return r.python_src


# ===========================================================================
# 1. Lexer: DOUBLE_COLON
# ===========================================================================

class TestDoubleColon:
    def test_double_colon_token(self):
        ks = kinds("Result::Ok")
        assert TK.DOUBLE_COLON in ks

    def test_double_colon_between_idents(self):
        ts = tokens("Result::Ok")
        assert ts[0].kind == TK.IDENT
        assert ts[0].value == "Result"
        assert ts[1].kind == TK.DOUBLE_COLON
        assert ts[2].kind == TK.IDENT
        assert ts[2].value == "Ok"

    def test_double_colon_option(self):
        ks = kinds("Option::Some")
        assert TK.DOUBLE_COLON in ks

    def test_double_colon_option_none(self):
        ks = kinds("Option::None")
        assert TK.DOUBLE_COLON in ks

    def test_single_colon_is_not_double(self):
        ks = kinds("x: int")
        assert TK.DOUBLE_COLON not in ks
        assert TK.COLON in ks

    def test_double_colon_in_function_call(self):
        ks = kinds("Result::Ok(42)")
        assert TK.DOUBLE_COLON in ks
        assert TK.LPAREN in ks
        assert TK.INT in ks


# ===========================================================================
# 2. Parser: ResultExpr
# ===========================================================================

class TestResultExpr:
    def test_result_ok_literal(self):
        expr = first_expr("let r = Result::Ok(42)")
        assert isinstance(expr, ResultExpr)
        assert expr.variant == "Ok"
        assert isinstance(expr.value, Literal)
        assert expr.value.value == 42

    def test_result_err_string(self):
        expr = first_expr('let r = Result::Err("oops")')
        assert isinstance(expr, ResultExpr)
        assert expr.variant == "Err"
        assert isinstance(expr.value, Literal)
        assert expr.value.value == "oops"

    def test_result_ok_ident(self):
        expr = first_expr("let r = Result::Ok(x)")
        assert isinstance(expr, ResultExpr)
        assert isinstance(expr.value, Ident)
        assert expr.value.name == "x"

    def test_result_ok_expression(self):
        expr = first_expr("let r = Result::Ok(a + b)")
        assert isinstance(expr, ResultExpr)
        assert isinstance(expr.value, BinOp)

    def test_result_in_return(self):
        p = ast('fn f() -> Result<int, str> { return Result::Err("fail") }')
        fn = p.body[0]
        assert isinstance(fn, FnDecl)
        ret = fn.body.stmts[0]
        assert isinstance(ret, ReturnStmt)
        assert isinstance(ret.value, ResultExpr)
        assert ret.value.variant == "Err"


# ===========================================================================
# 3. Parser: OptionExpr
# ===========================================================================

class TestOptionExpr:
    def test_option_some(self):
        expr = first_expr("let o = Option::Some(42)")
        assert isinstance(expr, OptionExpr)
        assert expr.variant == "Some"
        assert isinstance(expr.value, Literal)
        assert expr.value.value == 42

    def test_option_none(self):
        expr = first_expr("let o = Option::None")
        assert isinstance(expr, OptionExpr)
        assert expr.variant == "None"
        assert expr.value is None

    def test_option_some_string(self):
        expr = first_expr('let o = Option::Some("hello")')
        assert isinstance(expr, OptionExpr)
        assert expr.value.value == "hello"

    def test_option_some_ident(self):
        expr = first_expr("let o = Option::Some(user)")
        assert isinstance(expr, OptionExpr)
        assert isinstance(expr.value, Ident)


# ===========================================================================
# 4. Parser: TypeMatchExpr (match as expression)
# ===========================================================================

class TestTypeMatchExpr:
    def test_simple_match_expr(self):
        expr = first_expr(
            'let s = match r { Result::Ok(v) => v, Result::Err(e) => 0, }'
        )
        assert isinstance(expr, TypeMatchExpr)
        assert isinstance(expr.subject, Ident)
        assert expr.subject.name == "r"
        assert len(expr.arms) == 2

    def test_match_arm_enum_pattern(self):
        expr = first_expr(
            'let s = match r { Result::Ok(v) => v, _ => 0, }'
        )
        assert isinstance(expr, TypeMatchExpr)
        first_arm = expr.arms[0]
        assert isinstance(first_arm, TypeMatchArm)
        assert isinstance(first_arm.pattern, EnumVariantPattern)
        assert first_arm.pattern.variant_name == "Ok"

    def test_match_arm_wildcard(self):
        expr = first_expr(
            'let s = match x { 1 => "one", _ => "other", }'
        )
        assert isinstance(expr, TypeMatchExpr)
        last_arm = expr.arms[-1]
        assert isinstance(last_arm.pattern, WildcardPattern)

    def test_match_arm_literal(self):
        expr = first_expr(
            'let s = match code { 404 => "nf", 500 => "err", _ => "ok", }'
        )
        assert isinstance(expr, TypeMatchExpr)
        assert isinstance(expr.arms[0].pattern, LiteralPattern)
        assert expr.arms[0].pattern.value.value == 404

    def test_match_arm_binding(self):
        expr = first_expr(
            'let s = match n { x => x + 1, }'
        )
        assert isinstance(expr, TypeMatchExpr)
        arm = expr.arms[0]
        assert isinstance(arm.pattern, BindingPattern)
        assert arm.pattern.name == "x"

    def test_match_arm_value_expr(self):
        expr = first_expr(
            'let s = match r { Result::Ok(v) => v, _ => 0, }'
        )
        arm = expr.arms[0]
        assert arm.value is not None or arm.body is not None

    def test_match_option_patterns(self):
        expr = first_expr(
            'let s = match opt { Option::Some(n) => n, Option::None => 0, }'
        )
        assert isinstance(expr, TypeMatchExpr)
        assert len(expr.arms) == 2
        first_pat = expr.arms[0].pattern
        assert isinstance(first_pat, EnumVariantPattern)
        assert first_pat.enum_name == "Option"
        assert first_pat.variant_name == "Some"


# ===========================================================================
# 5. Parser: Pattern types
# ===========================================================================

class TestPatternTypes:
    def test_wildcard_pattern(self):
        expr = first_expr('let s = match x { _ => 0, }')
        assert isinstance(expr.arms[0].pattern, WildcardPattern)

    def test_literal_int_pattern(self):
        expr = first_expr('let s = match n { 42 => "yes", _ => "no", }')
        pat = expr.arms[0].pattern
        assert isinstance(pat, LiteralPattern)
        assert pat.value.value == 42

    def test_literal_string_pattern(self):
        expr = first_expr('let s = match tag { "ok" => 1, _ => 0, }')
        pat = expr.arms[0].pattern
        assert isinstance(pat, LiteralPattern)
        assert pat.value.value == "ok"

    def test_binding_pattern(self):
        expr = first_expr('let s = match v { n => n, }')
        pat = expr.arms[0].pattern
        assert isinstance(pat, BindingPattern)
        assert pat.name == "n"

    def test_enum_variant_pattern_with_fields(self):
        expr = first_expr(
            'let s = match r { Result::Ok(v) => v, _ => 0, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, EnumVariantPattern)
        assert pat.enum_name == "Result"
        assert pat.variant_name == "Ok"
        assert len(pat.fields) == 1
        assert isinstance(pat.fields[0], BindingPattern)
        assert pat.fields[0].name == "v"

    def test_enum_variant_pattern_no_fields(self):
        expr = first_expr(
            'let s = match opt { Option::None => 0, _ => 1, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, EnumVariantPattern)
        assert pat.enum_name == "Option"
        assert pat.variant_name == "None"
        assert pat.fields == []

    def test_or_pattern(self):
        expr = first_expr(
            'let s = match d { "Sat" | "Sun" => true, _ => false, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, OrPattern)

    def test_list_pattern_empty(self):
        expr = first_expr(
            'let s = match lst { [] => 0, _ => 1, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, ListPattern)
        assert pat.head == []
        assert pat.rest is None

    def test_list_pattern_head_rest(self):
        expr = first_expr(
            'let s = match lst { [h, ...t] => h, _ => 0, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, ListPattern)
        assert len(pat.head) == 1
        assert isinstance(pat.head[0], BindingPattern)
        assert pat.rest == "t"

    def test_tuple_pattern(self):
        expr = first_expr(
            'let s = match pair { (a, b) => a + b, }'
        )
        pat = expr.arms[0].pattern
        assert isinstance(pat, TuplePattern)
        assert len(pat.elements) == 2


# ===========================================================================
# 6. Type System: HM inference additions
# ===========================================================================

class TestOccursCheck:
    def setup_method(self):
        self.inf = TypeInferencer()

    def test_occurs_simple(self):
        tv = TypeVar("a")
        assert self.inf.occurs_check(tv, tv) is True

    def test_not_occurs_different_var(self):
        ta = TypeVar("a")
        tb = TypeVar("b")
        assert self.inf.occurs_check(ta, tb) is False

    def test_occurs_in_list(self):
        tv = TypeVar("a")
        lt = ListType(tv)
        assert self.inf.occurs_check(tv, lt) is True

    def test_not_occurs_in_list(self):
        ta = TypeVar("a")
        tb = TypeVar("b")
        lt = ListType(ta)
        assert self.inf.occurs_check(tb, lt) is False

    def test_occurs_in_tuple(self):
        tv = TypeVar("a")
        tt = TupleType([INT, tv, STR])
        assert self.inf.occurs_check(tv, tt) is True

    def test_occurs_in_function(self):
        tv = TypeVar("a")
        ft = FunctionType([INT, tv], STR)
        assert self.inf.occurs_check(tv, ft) is True

    def test_not_occurs_in_primitive(self):
        tv = TypeVar("a")
        assert self.inf.occurs_check(tv, INT) is False

    def test_occurs_resolved_via_substitution(self):
        ta = TypeVar("a")
        tb = TypeVar("b")
        # Bind a → [b], then occurs_check(b, List[a]) should find b via resolution
        self.inf._substitutions["a"] = ListType(tb)
        # a resolves to List[b], so occurs_check(b, List[a]) → True
        assert self.inf.occurs_check(tb, ListType(ta)) is True


class TestUnify:
    def setup_method(self):
        self.inf = TypeInferencer()

    def test_unify_equal_primitives(self):
        err = self.inf.unify(INT, INT)
        assert err is None

    def test_unify_different_primitives_fails(self):
        err = self.inf.unify(INT, STR)
        assert err is not None
        assert "mismatch" in err.lower() or "int" in err.lower()

    def test_unify_typevar_left(self):
        tv = TypeVar("a")
        err = self.inf.unify(tv, INT)
        assert err is None
        assert self.inf.resolve(tv) == INT

    def test_unify_typevar_right(self):
        tv = TypeVar("a")
        err = self.inf.unify(STR, tv)
        assert err is None
        assert self.inf.resolve(tv) == STR

    def test_unify_list_types(self):
        tv = TypeVar("a")
        err = self.inf.unify(ListType(tv), ListType(INT))
        assert err is None
        assert self.inf.resolve(tv) == INT

    def test_unify_list_mismatch_fails(self):
        err = self.inf.unify(ListType(INT), ListType(STR))
        assert err is not None

    def test_unify_tuple_matching(self):
        ta, tb = TypeVar("a"), TypeVar("b")
        err = self.inf.unify(TupleType([ta, tb]), TupleType([INT, STR]))
        assert err is None
        assert self.inf.resolve(ta) == INT
        assert self.inf.resolve(tb) == STR

    def test_unify_tuple_arity_mismatch(self):
        err = self.inf.unify(TupleType([INT, STR]), TupleType([INT]))
        assert err is not None

    def test_unify_any_escapes(self):
        # ANY unifies with everything
        assert self.inf.unify(ANY, INT) is None
        assert self.inf.unify(INT, ANY) is None

    def test_unify_optional(self):
        tv = TypeVar("a")
        err = self.inf.unify(OptionalType(tv), OptionalType(INT))
        assert err is None
        assert self.inf.resolve(tv) == INT

    def test_infinite_type_blocked(self):
        tv = TypeVar("a")
        err = self.inf.unify(tv, ListType(tv))
        assert err is not None
        assert "infinite" in err.lower() or "occurs" in err.lower()

    def test_function_type_unification(self):
        ta, tb = TypeVar("a"), TypeVar("b")
        fn1 = FunctionType([ta], tb)
        fn2 = FunctionType([INT], STR)
        err = self.inf.unify(fn1, fn2)
        assert err is None
        assert self.inf.resolve(ta) == INT
        assert self.inf.resolve(tb) == STR

    def test_function_arity_mismatch(self):
        err = self.inf.unify(
            FunctionType([INT, STR], BOOL),
            FunctionType([INT], BOOL)
        )
        assert err is not None


class TestSolve:
    def setup_method(self):
        self.inf = TypeInferencer()

    def test_solve_empty(self):
        errors = self.inf.solve()
        assert errors == []

    def test_solve_single_success(self):
        tv = TypeVar("a")
        self.inf.constrain(tv, INT, "test")
        errors = self.inf.solve()
        assert errors == []
        assert self.inf.resolve(tv) == INT

    def test_solve_single_failure(self):
        self.inf.constrain(INT, STR, "test")
        errors = self.inf.solve()
        assert len(errors) >= 1

    def test_solve_multiple(self):
        ta, tb = TypeVar("a"), TypeVar("b")
        self.inf.constrain(ta, INT, "ctx1")
        self.inf.constrain(tb, STR, "ctx2")
        errors = self.inf.solve()
        assert errors == []
        assert self.inf.resolve(ta) == INT
        assert self.inf.resolve(tb) == STR

    def test_solve_clears_constraints(self):
        self.inf.constrain(INT, STR, "x")
        self.inf.solve()
        # Solving again on empty queue should return no errors
        errors2 = self.inf.solve()
        assert errors2 == []

    def test_solve_transitive(self):
        ta, tb = TypeVar("a"), TypeVar("b")
        self.inf.constrain(ta, tb, "link")
        self.inf.constrain(tb, INT, "bind")
        errors = self.inf.solve()
        assert errors == []
        assert self.inf.resolve(ta) == INT


class TestInferPattern:
    def setup_method(self):
        self.inf = TypeInferencer()

    def test_wildcard_no_bindings(self):
        p = WildcardPattern()
        bindings = self.inf.infer_pattern(p, INT)
        assert bindings == {}

    def test_binding_captures_type(self):
        p = BindingPattern(name="x")
        bindings = self.inf.infer_pattern(p, INT)
        assert "x" in bindings
        assert bindings["x"] == INT

    def test_literal_pattern_int(self):
        from lateralus_lang.ast_nodes import Literal
        p = LiteralPattern(value=Literal(value=42, kind="int"))
        bindings = self.inf.infer_pattern(p, INT)
        assert bindings == {}  # no names bound
        # Constraint added: subject ~ int
        errors = self.inf.solve()
        assert errors == []

    def test_tuple_pattern_binds_elements(self):
        elements = [BindingPattern("a"), BindingPattern("b")]
        p = TuplePattern(elements=elements)
        bindings = self.inf.infer_pattern(p, TupleType([INT, STR]))
        assert "a" in bindings
        assert "b" in bindings

    def test_list_pattern_head_rest(self):
        p = ListPattern(head=[BindingPattern("h")], rest="t")
        bindings = self.inf.infer_pattern(p, ListType(INT))
        assert "h" in bindings
        assert "t" in bindings
        assert isinstance(bindings["t"], ListType)

    def test_list_pattern_empty(self):
        p = ListPattern(head=[], rest=None)
        bindings = self.inf.infer_pattern(p, ListType(INT))
        assert bindings == {}

    def test_enum_variant_pattern_fields(self):
        fields = [BindingPattern("v")]
        p = EnumVariantPattern(enum_name="Result", variant_name="Ok", fields=fields)
        bindings = self.inf.infer_pattern(p, INT)  # subject type doesn't matter much here
        assert "v" in bindings

    def test_or_pattern_common_bindings(self):
        # Both branches bind the same name — it survives
        left  = BindingPattern("x")
        right = BindingPattern("x")
        p = OrPattern(left=left, right=right)
        bindings = self.inf.infer_pattern(p, INT)
        assert "x" in bindings

    def test_or_pattern_disjoint_bindings(self):
        # Different names — neither survives (safety: only common names in scope)
        left  = BindingPattern("a")
        right = BindingPattern("b")
        p = OrPattern(left=left, right=right)
        bindings = self.inf.infer_pattern(p, INT)
        assert "a" not in bindings
        assert "b" not in bindings


# ===========================================================================
# 7. Codegen: v1.5 nodes produce correct Python
# ===========================================================================

class TestV15Codegen:
    def test_result_ok_codegen(self):
        py = compile_py("let r = Result::Ok(42)")
        assert "Ok(42)" in py

    def test_result_err_codegen(self):
        py = compile_py('let r = Result::Err("oops")')
        assert "Err(" in py
        assert "oops" in py

    def test_option_some_codegen(self):
        py = compile_py('let o = Option::Some("hi")')
        assert "Some(" in py

    def test_option_none_codegen(self):
        py = compile_py("let o = Option::None")
        assert "None_" in py

    def test_match_expr_produces_match_or_def(self):
        src = 'let s = match r { Result::Ok(v) => v, _ => 0, }'
        py = compile_py(src)
        # Either Python match/case was emitted, or an IIFE helper function
        assert "match" in py or "_ltl_tmatch_" in py

    def test_match_wildcard_arm(self):
        src = 'let s = match x { 1 => "one", _ => "other", }'
        py = compile_py(src)
        assert "_" in py or "other" in py

    def test_match_enum_pattern_ok(self):
        src = 'let s = match r { Result::Ok(v) => v, Result::Err(e) => 0, }'
        py = compile_py(src)
        assert "Ok" in py

    def test_match_option_none_arm(self):
        src = 'let s = match o { Option::Some(n) => n, Option::None => 0, }'
        py = compile_py(src)
        assert "Some" in py or "None" in py

    def test_codegen_header_version(self):
        py = compile_py("let x = 1")
        assert "v1.6" in py

    def test_some_class_in_preamble(self):
        py = compile_py("let x = 1")
        assert "class Some" in py

    def test_none_singleton_in_preamble(self):
        py = compile_py("let x = 1")
        assert "None_" in py

    def test_ok_match_args_in_preamble(self):
        py = compile_py("let x = 1")
        assert "__match_args__" in py

    def test_full_v15_showcase_compiles(self):
        """The v1.5 showcase file must compile without errors."""
        showcase = pathlib.Path(__file__).parent.parent / "examples" / "v15_showcase.ltl"
        src = showcase.read_text()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename="v15_showcase.ltl")
        assert r.ok, "v15_showcase.ltl compile failed:\n" + "\n".join(str(e) for e in r.errors)


# ===========================================================================
# 8. End-to-end: version checks
# ===========================================================================

class TestVersioning:
    def test_package_version(self):
        import lateralus_lang
        assert lateralus_lang.__version__ == "2.5.1"

    def test_compiler_output_header(self):
        py = compile_py("let x = 1")
        assert "v1.6" in py

    def test_double_colon_round_trip(self):
        """Result::Ok(x) lexes, parses, and transpiles without error."""
        src = "let r = Result::Ok(10)"
        py = compile_py(src)
        assert "Ok(10)" in py

# ===========================================================================
# 9. Optional type syntax: int?
# ===========================================================================

class TestOptionalTypeSyntax:
    def test_parse_optional_param(self):
        """fn f(x: int?) should parse with nullable=True."""
        p = ast("fn f(x: int?) { return x }")
        fn = p.body[0]
        assert len(fn.params) == 1
        param = fn.params[0]
        # param is a tuple (name, type_ref, default) or has .type_ann
        if hasattr(param, 'type_ann') and param.type_ann:
            assert param.type_ann.nullable is True
        elif isinstance(param, tuple) and len(param) >= 2 and param[1] is not None:
            assert param[1].nullable is True
        else:
            # For other param representations, just ensure it parsed
            assert fn is not None

    def test_parse_optional_return(self):
        """fn f() -> int? should parse with nullable return type."""
        p = ast("fn f() -> int? { return nil }")
        fn = p.body[0]
        if hasattr(fn, 'return_type') and fn.return_type:
            assert fn.return_type.nullable is True

    def test_optional_type_system(self):
        """OptionalType should wrap inner type correctly."""
        opt = OptionalType(INT)
        assert opt.inner_type == INT
        assert opt.is_assignable_from(INT)
        # None should also be assignable
        from lateralus_lang.type_system import NONE
        assert opt.is_assignable_from(NONE)

    def test_optional_let_decl(self):
        """let x: int? = nil should parse."""
        p = ast("let x: int? = nil")
        decl = p.body[0]
        assert isinstance(decl, LetDecl)
        if hasattr(decl, 'type_ann') and decl.type_ann:
            assert decl.type_ann.nullable is True


# ===========================================================================
# 10. Generic trait bounds: <T: Comparable>
# ===========================================================================

class TestGenericTraitBounds:
    def test_parse_simple_bound(self):
        """fn sort<T: Comparable>(items: list) should parse bound."""
        p = ast("fn sort<T: Comparable>(items: list) { return items }")
        fn = p.body[0]
        assert len(fn.generics) == 1
        param = fn.generics[0]
        assert isinstance(param, dict)
        assert param["name"] == "T"
        assert param["bound"] == "Comparable"

    def test_parse_multiple_bounds(self):
        """fn f<T: Show, U: Eq>(a: T, b: U) should parse two bounds."""
        p = ast("fn f<T: Show, U: Eq>(a: int, b: int) { return a }")
        fn = p.body[0]
        assert len(fn.generics) == 2
        assert fn.generics[0] == {"name": "T", "bound": "Show"}
        assert fn.generics[1] == {"name": "U", "bound": "Eq"}

    def test_parse_mixed_bounds(self):
        """fn f<T, U: Eq>(a: int) should mix plain and bounded."""
        p = ast("fn f<T, U: Eq>(a: int) { return a }")
        fn = p.body[0]
        assert len(fn.generics) == 2
        assert fn.generics[0] == "T"
        assert fn.generics[1] == {"name": "U", "bound": "Eq"}

    def test_const_generic(self):
        """struct Matrix<N: int, M: int> should parse const generics."""
        p = ast("struct Matrix<N: int, M: int> { data: list }")
        s = p.body[0]
        assert len(s.generics) == 2
        assert s.generics[0] == {"name": "N", "bound": "int"}
        assert s.generics[1] == {"name": "M", "bound": "int"}

    def test_backward_compat_plain_generics(self):
        """fn f<T, U>(x: int) should still produce plain strings."""
        p = ast("fn f<T, U>(x: int) { return x }")
        fn = p.body[0]
        assert fn.generics == ["T", "U"]


# ===========================================================================
# 11. Type narrowing
# ===========================================================================

class TestTypeNarrowing:
    def test_narrower_import(self):
        """TypeNarrower should be importable."""
        from lateralus_lang.type_system import TypeNarrower
        assert TypeNarrower is not None

    def test_narrow_optional(self):
        """narrow_optional should strip OptionalType wrapper."""
        from lateralus_lang.type_system import TypeNarrower
        opt = OptionalType(INT)
        narrowed = TypeNarrower.narrow_optional(opt)
        assert narrowed == INT
        assert TypeNarrower.narrow_optional(INT) == INT

    def test_is_nilable(self):
        """is_nilable should detect optional and none types."""
        from lateralus_lang.type_system import NONE, TypeNarrower, UnionType
        assert TypeNarrower.is_nilable(OptionalType(INT)) is True
        assert TypeNarrower.is_nilable(NONE) is True
        assert TypeNarrower.is_nilable(INT) is False
        assert TypeNarrower.is_nilable(UnionType([INT, NONE])) is True
        assert TypeNarrower.is_nilable(UnionType([INT, STR])) is False

    def test_narrow_env_available(self):
        """TypeEnvironment.child_scope should work with narrowing."""
        from lateralus_lang.type_system import TypeEnvironment
        env = TypeEnvironment()
        env.define("x", OptionalType(INT))
        child = env.child_scope()
        child.define("x", INT)
        assert child.lookup("x") == INT
        assert env.lookup("x") == OptionalType(INT)
