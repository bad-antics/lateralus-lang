"""
tests/test_type_system.py — Tests for the LATERALUS type system
"""
import pytest
from lateralus_lang.type_system import (
    LTLType, PrimitiveType, FunctionType, ListType, MapType, TupleType,
    UnionType, OptionalType, TypeVar, StructType, InterfaceType,
    INT, FLOAT, STR, BOOL, NONE, ANY, NEVER, VOID, NUMBER,
    TypeEnvironment, TypeInferencer, TypeChecker,
    parse_type_annotation, TypeKind,
)


# --- Primitive Types ---------------------------------------------------

class TestPrimitiveTypes:
    def test_int(self):
        assert INT.name == "int"
        assert INT.kind == TypeKind.PRIMITIVE
        assert INT.is_numeric()

    def test_float(self):
        assert FLOAT.name == "float"
        assert FLOAT.is_numeric()

    def test_str(self):
        assert STR.name == "str"
        assert not STR.is_numeric()

    def test_bool(self):
        assert BOOL.name == "bool"

    def test_none(self):
        assert NONE.name == "none"

    def test_equality(self):
        assert INT == PrimitiveType("int")
        assert INT != FLOAT

    def test_int_to_float_promotion(self):
        assert FLOAT.is_assignable_from(INT)

    def test_float_not_to_int(self):
        assert not INT.is_assignable_from(FLOAT)

    def test_any_to_str(self):
        # Anything is assignable to str (via implicit conversion)
        assert STR.is_assignable_from(INT)
        assert STR.is_assignable_from(FLOAT)
        assert STR.is_assignable_from(BOOL)


# --- Function Types ---------------------------------------------------

class TestFunctionTypes:
    def test_creation(self):
        fn = FunctionType([INT, STR], BOOL)
        assert fn.arity == 2
        assert fn.return_type == BOOL

    def test_name(self):
        fn = FunctionType([INT], STR)
        assert str(fn) == "(int) -> str"

    def test_assignable_same(self):
        fn1 = FunctionType([INT], STR)
        fn2 = FunctionType([INT], STR)
        assert fn1.is_assignable_from(fn2)

    def test_arity_mismatch(self):
        fn1 = FunctionType([INT], STR)
        fn2 = FunctionType([INT, INT], STR)
        assert not fn1.is_assignable_from(fn2)


# --- List Types --------------------------------------------------------

class TestListTypes:
    def test_creation(self):
        lt = ListType(INT)
        assert lt.element_type == INT
        assert str(lt) == "list[int]"

    def test_assignable_same(self):
        assert ListType(INT).is_assignable_from(ListType(INT))

    def test_assignable_promotion(self):
        # list[float] should accept list[int]
        assert ListType(FLOAT).is_assignable_from(ListType(INT))

    def test_not_assignable_different(self):
        assert not ListType(INT).is_assignable_from(ListType(STR))


# --- Map Types ---------------------------------------------------------

class TestMapTypes:
    def test_creation(self):
        mt = MapType(STR, INT)
        assert str(mt) == "map[str, int]"

    def test_assignable(self):
        assert MapType(STR, INT).is_assignable_from(MapType(STR, INT))

    def test_not_assignable(self):
        assert not MapType(STR, INT).is_assignable_from(MapType(INT, STR))


# --- Tuple Types -------------------------------------------------------

class TestTupleTypes:
    def test_creation(self):
        tt = TupleType([INT, STR, BOOL])
        assert str(tt) == "(int, str, bool)"

    def test_assignable(self):
        assert TupleType([INT, STR]).is_assignable_from(TupleType([INT, STR]))

    def test_length_mismatch(self):
        assert not TupleType([INT]).is_assignable_from(TupleType([INT, STR]))


# --- Union Types -------------------------------------------------------

class TestUnionTypes:
    def test_creation(self):
        u = UnionType([INT, STR])
        assert INT in u.types
        assert STR in u.types

    def test_assignable_member(self):
        u = UnionType([INT, STR])
        assert u.is_assignable_from(INT)
        assert u.is_assignable_from(STR)

    def test_not_assignable_non_member(self):
        u = UnionType([INT, STR])
        assert not u.is_assignable_from(BOOL)

    def test_flatten_nested(self):
        inner = UnionType([INT, STR])
        outer = UnionType([inner, BOOL])
        assert INT in outer.types
        assert STR in outer.types
        assert BOOL in outer.types

    def test_number_is_union(self):
        assert NUMBER.is_assignable_from(INT)
        assert NUMBER.is_assignable_from(FLOAT)


# --- Optional Types ---------------------------------------------------

class TestOptionalTypes:
    def test_creation(self):
        opt = OptionalType(INT)
        assert str(opt) == "int?"

    def test_accepts_inner(self):
        opt = OptionalType(INT)
        assert opt.is_assignable_from(INT)

    def test_accepts_none(self):
        opt = OptionalType(INT)
        assert opt.is_assignable_from(NONE)

    def test_rejects_wrong_type(self):
        opt = OptionalType(INT)
        assert not opt.is_assignable_from(STR)


# --- Type Variables ----------------------------------------------------

class TestTypeVar:
    def test_unconstrained(self):
        tv = TypeVar("T")
        assert tv.is_assignable_from(INT)
        assert tv.is_assignable_from(STR)

    def test_constrained(self):
        tv = TypeVar("N", constraint=NUMBER)
        assert tv.is_assignable_from(INT)
        assert tv.is_assignable_from(FLOAT)


# --- Struct Types ------------------------------------------------------

class TestStructTypes:
    def test_creation(self):
        s = StructType("Point", [("x", FLOAT), ("y", FLOAT)])
        assert s.name == "Point"
        assert s.field_type("x") == FLOAT

    def test_field_lookup(self):
        s = StructType("User", [("name", STR), ("age", INT)])
        assert s.field_type("name") == STR
        assert s.field_type("age") == INT
        assert s.field_type("email") is None

    def test_structural_typing(self):
        s1 = StructType("A", [("x", INT), ("y", INT)])
        s2 = StructType("B", [("x", INT), ("y", INT), ("z", INT)])
        # s1 should accept s2 (s2 has all fields of s1)
        assert s1.is_assignable_from(s2)

    def test_structural_typing_missing_field(self):
        s1 = StructType("A", [("x", INT), ("y", INT)])
        s2 = StructType("B", [("x", INT)])
        assert not s1.is_assignable_from(s2)


# --- Interface Types --------------------------------------------------

class TestInterfaceTypes:
    def test_satisfied(self):
        iface = InterfaceType("Printable", [
            ("to_string", FunctionType([], STR)),
        ])
        struct = StructType("MyObj", [], [
            ("to_string", FunctionType([], STR)),
        ])
        assert iface.is_satisfied_by(struct)

    def test_not_satisfied(self):
        iface = InterfaceType("Printable", [
            ("to_string", FunctionType([], STR)),
        ])
        struct = StructType("MyObj", [])
        assert not iface.is_satisfied_by(struct)


# --- Type Environment --------------------------------------------------

class TestTypeEnvironment:
    def test_define_and_lookup(self):
        env = TypeEnvironment()
        env.define("x", INT)
        assert env.lookup("x") == INT

    def test_undefined(self):
        env = TypeEnvironment()
        assert env.lookup("nonexistent") is None

    def test_parent_scope(self):
        parent = TypeEnvironment()
        parent.define("x", INT)
        child = parent.child_scope()
        assert child.lookup("x") == INT

    def test_child_shadows_parent(self):
        parent = TypeEnvironment()
        parent.define("x", INT)
        child = parent.child_scope()
        child.define("x", FLOAT)
        assert child.lookup("x") == FLOAT
        assert parent.lookup("x") == INT

    def test_type_definitions(self):
        env = TypeEnvironment()
        point = StructType("Point", [("x", FLOAT), ("y", FLOAT)])
        env.define_type("Point", point)
        assert env.lookup_type("Point") == point


# --- Type Inferencer ---------------------------------------------------

class TestTypeInferencer:
    def test_infer_int(self):
        inf = TypeInferencer()
        assert inf.infer_literal(42) == INT

    def test_infer_float(self):
        inf = TypeInferencer()
        assert inf.infer_literal(3.14) == FLOAT

    def test_infer_str(self):
        inf = TypeInferencer()
        assert inf.infer_literal("hello") == STR

    def test_infer_bool(self):
        inf = TypeInferencer()
        assert inf.infer_literal(True) == BOOL

    def test_infer_none(self):
        inf = TypeInferencer()
        assert inf.infer_literal(None) == NONE

    def test_infer_list(self):
        inf = TypeInferencer()
        t = inf.infer_literal([1, 2, 3])
        assert isinstance(t, ListType)
        assert t.element_type == INT

    def test_infer_binary_comparison(self):
        inf = TypeInferencer()
        assert inf.infer_binary("<", INT, INT) == BOOL

    def test_infer_binary_arithmetic(self):
        inf = TypeInferencer()
        assert inf.infer_binary("+", INT, INT) == INT
        assert inf.infer_binary("+", INT, FLOAT) == FLOAT

    def test_infer_binary_division(self):
        inf = TypeInferencer()
        assert inf.infer_binary("/", INT, INT) == FLOAT

    def test_infer_string_concat(self):
        inf = TypeInferencer()
        assert inf.infer_binary("+", STR, STR) == STR


# --- Type Checker ------------------------------------------------------

class TestTypeChecker:
    def test_valid_assignment(self):
        tc = TypeChecker()
        err = tc.check_assignment("x", INT, INT)
        assert err is None

    def test_invalid_assignment(self):
        tc = TypeChecker()
        err = tc.check_assignment("x", INT, FLOAT)
        assert err is not None

    def test_inferred_assignment(self):
        tc = TypeChecker()
        err = tc.check_assignment("x", None, FLOAT)
        assert err is None
        assert tc.env.lookup("x") == FLOAT

    def test_valid_call(self):
        tc = TypeChecker()
        ret, err = tc.check_call("len", [ListType(INT)])
        assert err is None
        assert ret == INT

    def test_unknown_function(self):
        tc = TypeChecker()
        ret, err = tc.check_call("nonexistent_fn", [INT])
        assert err is not None

    def test_arity_mismatch(self):
        tc = TypeChecker()
        ret, err = tc.check_call("println", [INT, STR])  # println takes 1 arg
        assert err is not None


# --- Parse Type Annotation --------------------------------------------

class TestParseTypeAnnotation:
    def test_primitive(self):
        assert parse_type_annotation("int") == INT
        assert parse_type_annotation("float") == FLOAT
        assert parse_type_annotation("str") == STR
        assert parse_type_annotation("bool") == BOOL

    def test_optional(self):
        t = parse_type_annotation("int?")
        assert isinstance(t, OptionalType)
        assert t.inner_type == INT

    def test_list(self):
        t = parse_type_annotation("list[str]")
        assert isinstance(t, ListType)
        assert t.element_type == STR

    def test_map(self):
        t = parse_type_annotation("map[str, int]")
        assert isinstance(t, MapType)
        assert t.key_type == STR
        assert t.value_type == INT

    def test_union(self):
        t = parse_type_annotation("int | str")
        assert isinstance(t, UnionType)

    def test_any(self):
        assert parse_type_annotation("any") == ANY

    def test_void(self):
        assert parse_type_annotation("void") == VOID

    def test_custom_type(self):
        t = parse_type_annotation("MyStruct")
        assert t.name == "MyStruct"
