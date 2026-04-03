"""
lateralus_lang/type_system.py — Type system for LATERALUS

Provides the foundation for static type analysis, type inference,
and runtime type checking. Inspired by Julia's type dispatch system
and Rust's algebraic data types.

This module defines:
  - Core type representations (LTLType hierarchy)
  - Type inference engine
  - Type compatibility checking
  - Generic type parameters
  - Union types and Optional
  - Function signature types
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, FrozenSet
from enum import Enum, auto
import itertools


# ─── Type Kind ─────────────────────────────────────────────────────────

class TypeKind(Enum):
    """Categories of types in LATERALUS."""
    PRIMITIVE = auto()
    FUNCTION = auto()
    STRUCT = auto()
    INTERFACE = auto()
    LIST = auto()
    MAP = auto()
    TUPLE = auto()
    UNION = auto()
    OPTIONAL = auto()
    GENERIC = auto()
    TYPEVAR = auto()
    NEVER = auto()
    ANY = auto()
    VOID = auto()
    GRADUAL = auto()     # v1.5: gradual typing boundary


# ─── Core Type Classes ─────────────────────────────────────────────────

@dataclass(frozen=True)
class LTLType:
    """Base class for all LATERALUS types."""
    kind: TypeKind
    name: str

    def is_numeric(self) -> bool:
        return self.name in ("int", "float", "number", "complex")

    def is_assignable_from(self, other: LTLType) -> bool:
        """Check if a value of type `other` can be assigned to this type."""
        if self == other:
            return True
        if self.kind == TypeKind.ANY:
            return True
        if other.kind == TypeKind.NEVER:
            return True
        return False

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class PrimitiveType(LTLType):
    """Primitive types: int, float, str, bool, none."""

    def __init__(self, name: str):
        object.__setattr__(self, "kind", TypeKind.PRIMITIVE)
        object.__setattr__(self, "name", name)

    def is_assignable_from(self, other: LTLType) -> bool:
        if super().is_assignable_from(other):
            return True
        # Number promotion: int -> float
        if self.name == "float" and isinstance(other, PrimitiveType) and other.name == "int":
            return True
        # Anything -> str (via implicit conversion)
        if self.name == "str":
            return True
        return False


@dataclass(frozen=True)
class FunctionType(LTLType):
    """Function type with parameter types and return type."""
    param_types: Tuple[LTLType, ...]
    return_type: LTLType
    param_names: Tuple[str, ...] = ()

    def __init__(self, param_types: List[LTLType], return_type: LTLType,
                 param_names: Optional[List[str]] = None):
        object.__setattr__(self, "kind", TypeKind.FUNCTION)
        sig = ", ".join(str(t) for t in param_types)
        object.__setattr__(self, "name", f"({sig}) -> {return_type}")
        object.__setattr__(self, "param_types", tuple(param_types))
        object.__setattr__(self, "return_type", return_type)
        object.__setattr__(self, "param_names", tuple(param_names or []))

    @property
    def arity(self) -> int:
        return len(self.param_types)

    def is_assignable_from(self, other: LTLType) -> bool:
        if not isinstance(other, FunctionType):
            return False
        if self.arity != other.arity:
            return False
        # Contravariant in parameter types
        for self_p, other_p in zip(self.param_types, other.param_types):
            if not other_p.is_assignable_from(self_p):
                return False
        # Covariant in return type
        return self.return_type.is_assignable_from(other.return_type)


@dataclass(frozen=True)
class ListType(LTLType):
    """List type: list[T]"""
    element_type: LTLType

    def __init__(self, element_type: LTLType):
        object.__setattr__(self, "kind", TypeKind.LIST)
        object.__setattr__(self, "name", f"list[{element_type}]")
        object.__setattr__(self, "element_type", element_type)

    def is_assignable_from(self, other: LTLType) -> bool:
        if not isinstance(other, ListType):
            return False
        return self.element_type.is_assignable_from(other.element_type)


@dataclass(frozen=True)
class MapType(LTLType):
    """Map type: map[K, V]"""
    key_type: LTLType
    value_type: LTLType

    def __init__(self, key_type: LTLType, value_type: LTLType):
        object.__setattr__(self, "kind", TypeKind.MAP)
        object.__setattr__(self, "name", f"map[{key_type}, {value_type}]")
        object.__setattr__(self, "key_type", key_type)
        object.__setattr__(self, "value_type", value_type)

    def is_assignable_from(self, other: LTLType) -> bool:
        if not isinstance(other, MapType):
            return False
        return (self.key_type.is_assignable_from(other.key_type) and
                self.value_type.is_assignable_from(other.value_type))


@dataclass(frozen=True)
class TupleType(LTLType):
    """Tuple type: (T1, T2, ...)"""
    element_types: Tuple[LTLType, ...]

    def __init__(self, element_types: List[LTLType]):
        object.__setattr__(self, "kind", TypeKind.TUPLE)
        elems = ", ".join(str(t) for t in element_types)
        object.__setattr__(self, "name", f"({elems})")
        object.__setattr__(self, "element_types", tuple(element_types))

    def is_assignable_from(self, other: LTLType) -> bool:
        if not isinstance(other, TupleType):
            return False
        if len(self.element_types) != len(other.element_types):
            return False
        return all(
            s.is_assignable_from(o)
            for s, o in zip(self.element_types, other.element_types)
        )


@dataclass(frozen=True)
class UnionType(LTLType):
    """Union type: T1 | T2 | ..."""
    types: FrozenSet[LTLType]

    def __init__(self, types: List[LTLType]):
        # Flatten nested unions
        flat = set()
        for t in types:
            if isinstance(t, UnionType):
                flat |= t.types
            else:
                flat.add(t)

        object.__setattr__(self, "kind", TypeKind.UNION)
        names = " | ".join(sorted(str(t) for t in flat))
        object.__setattr__(self, "name", names)
        object.__setattr__(self, "types", frozenset(flat))

    def is_assignable_from(self, other: LTLType) -> bool:
        if isinstance(other, UnionType):
            return all(self.is_assignable_from(t) for t in other.types)
        return other in self.types


@dataclass(frozen=True)
class OptionalType(LTLType):
    """Optional type: T? (sugar for T | none)"""
    inner_type: LTLType

    def __init__(self, inner_type: LTLType):
        object.__setattr__(self, "kind", TypeKind.OPTIONAL)
        object.__setattr__(self, "name", f"{inner_type}?")
        object.__setattr__(self, "inner_type", inner_type)

    def is_assignable_from(self, other: LTLType) -> bool:
        if isinstance(other, PrimitiveType) and other.name == "none":
            return True
        return self.inner_type.is_assignable_from(other)


@dataclass(frozen=True)
class TypeVar(LTLType):
    """Type variable for generics: T, U, etc."""
    constraint: Optional[LTLType] = None

    def __init__(self, name: str, constraint: Optional[LTLType] = None):
        object.__setattr__(self, "kind", TypeKind.TYPEVAR)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "constraint", constraint)

    def is_assignable_from(self, other: LTLType) -> bool:
        if self.constraint is not None:
            return self.constraint.is_assignable_from(other)
        return True  # Unconstrained type var accepts anything


@dataclass(frozen=True)
class StructType(LTLType):
    """Struct type with named fields."""
    fields: Tuple[Tuple[str, LTLType], ...]
    methods: Tuple[Tuple[str, FunctionType], ...] = ()

    def __init__(self, name: str, fields: List[Tuple[str, LTLType]],
                 methods: Optional[List[Tuple[str, FunctionType]]] = None):
        object.__setattr__(self, "kind", TypeKind.STRUCT)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "fields", tuple(fields))
        object.__setattr__(self, "methods", tuple(methods or []))

    def field_type(self, field_name: str) -> Optional[LTLType]:
        for name, typ in self.fields:
            if name == field_name:
                return typ
        return None

    def method_type(self, method_name: str) -> Optional[FunctionType]:
        for name, typ in self.methods:
            if name == method_name:
                return typ
        return None

    def is_assignable_from(self, other: LTLType) -> bool:
        if not isinstance(other, StructType):
            return False
        # Structural typing: other must have all our fields with compatible types
        for field_name, field_type in self.fields:
            other_type = other.field_type(field_name)
            if other_type is None:
                return False
            if not field_type.is_assignable_from(other_type):
                return False
        return True


@dataclass(frozen=True)
class InterfaceType(LTLType):
    """Interface type — structural contract."""
    methods_required: Tuple[Tuple[str, FunctionType], ...]

    def __init__(self, name: str, methods: List[Tuple[str, FunctionType]]):
        object.__setattr__(self, "kind", TypeKind.INTERFACE)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "methods_required", tuple(methods))

    def is_satisfied_by(self, struct: StructType) -> bool:
        """Check if a struct satisfies this interface."""
        for method_name, method_type in self.methods_required:
            actual = struct.method_type(method_name)
            if actual is None:
                return False
            if not method_type.is_assignable_from(actual):
                return False
        return True


@dataclass(frozen=True)
class GradualType(LTLType):
    """Gradual type boundary — typed/untyped interop (v1.5).

    A GradualType wraps a *known* static type and allows it to interact
    with dynamically-typed (``any``) code without raising type errors.
    Assignment is always permitted in either direction: typed → gradual
    and gradual → typed.  At runtime the value carries enough tag info
    for the VM to check.

    Semantics (following Siek & Taha 2006):
        - ``GradualType(T)`` is consistent with ``T`` **and** with ``any``
        - Two GradualTypes are consistent iff their inner types are
          assignable in at least one direction
        - A GradualType never *rejects* at compile time — any mismatch
          is deferred to a runtime cast (inserted by the codegen layer)
    """
    inner: LTLType

    def __init__(self, inner: LTLType):
        label = f"~{inner}" if inner.kind != TypeKind.ANY else "~any"
        object.__setattr__(self, "kind", TypeKind.GRADUAL)
        object.__setattr__(self, "name", label)
        object.__setattr__(self, "inner", inner)

    def is_assignable_from(self, other: LTLType) -> bool:
        """Gradual types accept anything — mismatches become runtime casts."""
        return True

    def is_consistent_with(self, other: LTLType) -> bool:
        """Gradual consistency (symmetric)."""
        if other.kind == TypeKind.ANY or self.inner.kind == TypeKind.ANY:
            return True
        if isinstance(other, GradualType):
            return (self.inner.is_assignable_from(other.inner) or
                    other.inner.is_assignable_from(self.inner))
        return (self.inner.is_assignable_from(other) or
                other.is_assignable_from(self.inner))


# ─── v1.6: Pointer type ───────────────────────────────────────────────

@dataclass(frozen=True)
class PtrType(LTLType):
    """Raw pointer type: Ptr<T> — for low-level / OS work.

    Ptr<u8> represents a raw, unmanaged pointer to a byte.
    Only valid inside ``unsafe`` blocks.
    """
    pointee: LTLType

    def __init__(self, pointee: LTLType):
        object.__setattr__(self, "kind", TypeKind.PRIMITIVE)
        object.__setattr__(self, "name", f"Ptr<{pointee}>")
        object.__setattr__(self, "pointee", pointee)

    def is_assignable_from(self, other: LTLType) -> bool:
        if isinstance(other, PtrType):
            # Ptr<T> accepts Ptr<T> or Ptr<u8> (void* equivalent)
            if other.pointee.name == "u8":
                return True
            return self.pointee.is_assignable_from(other.pointee)
        return super().is_assignable_from(other)


# ─── Built-in Type Constants ───────────────────────────────────────────

INT = PrimitiveType("int")
FLOAT = PrimitiveType("float")
STR = PrimitiveType("str")
BOOL = PrimitiveType("bool")
NONE = PrimitiveType("none")
ANY = LTLType(kind=TypeKind.ANY, name="any")
NEVER = LTLType(kind=TypeKind.NEVER, name="never")
VOID = LTLType(kind=TypeKind.VOID, name="void")
NUMBER = UnionType([INT, FLOAT])
DYNAMIC = GradualType(ANY)         # v1.5: fully-dynamic gradual boundary

# v1.6: Fixed-width integer types for OS / low-level work
U8  = PrimitiveType("u8")
U16 = PrimitiveType("u16")
U32 = PrimitiveType("u32")
U64 = PrimitiveType("u64")
I8  = PrimitiveType("i8")
I16 = PrimitiveType("i16")
I32 = PrimitiveType("i32")
I64 = PrimitiveType("i64")
USIZE = PrimitiveType("usize")
ISIZE = PrimitiveType("isize")
BYTE = PrimitiveType("byte")    # alias for u8

# Mapping of all fixed-width type names to their type objects
FIXED_WIDTH_TYPES: Dict[str, LTLType] = {
    "u8": U8, "u16": U16, "u32": U32, "u64": U64,
    "i8": I8, "i16": I16, "i32": I32, "i64": I64,
    "usize": USIZE, "isize": ISIZE, "byte": BYTE,
}


# ─── Type Environment ──────────────────────────────────────────────────

class TypeEnvironment:
    """
    A scoped type environment for type checking.
    Supports nested scopes with parent lookup.
    """

    def __init__(self, parent: Optional[TypeEnvironment] = None):
        self.parent = parent
        self._bindings: Dict[str, LTLType] = {}
        self._type_defs: Dict[str, LTLType] = {}

    def define(self, name: str, typ: LTLType):
        """Define a variable with a type in the current scope."""
        self._bindings[name] = typ

    def lookup(self, name: str) -> Optional[LTLType]:
        """Look up a variable's type, checking parent scopes."""
        if name in self._bindings:
            return self._bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def define_type(self, name: str, typ: LTLType):
        """Register a type definition (struct, interface, alias)."""
        self._type_defs[name] = typ

    def lookup_type(self, name: str) -> Optional[LTLType]:
        """Look up a type definition."""
        if name in self._type_defs:
            return self._type_defs[name]
        if self.parent:
            return self.parent.lookup_type(name)
        return None

    def child_scope(self) -> TypeEnvironment:
        """Create a child scope."""
        return TypeEnvironment(parent=self)

    def all_bindings(self) -> Dict[str, LTLType]:
        """Get all bindings including parent scopes."""
        result = {}
        if self.parent:
            result.update(self.parent.all_bindings())
        result.update(self._bindings)
        return result


# ─── Type Narrowing ────────────────────────────────────────────────────

class TypeNarrower:
    """
    Flow-sensitive type narrowing for conditional branches.

    Analyzes guard conditions (e.g., `if x != nil`, `if type_of(x) == "int"`)
    and produces a narrowed TypeEnvironment for the true/false branches.

    This enables the compiler to understand that after `if x != nil`,
    the variable `x` cannot be `none` inside the `if` body.
    """

    @staticmethod
    def narrow_from_condition(env: TypeEnvironment,
                              condition) -> Tuple[TypeEnvironment, TypeEnvironment]:
        """
        Given a condition expression node, return (true_env, false_env).

        Both environments are child scopes of `env` with narrowed bindings.
        Unrecognized conditions return the original env for both branches.
        """
        true_env = env.child_scope()
        false_env = env.child_scope()

        TypeNarrower._analyze(condition, env, true_env, false_env)
        return true_env, false_env

    @staticmethod
    def _analyze(cond, env: TypeEnvironment,
                 true_env: TypeEnvironment, false_env: TypeEnvironment):
        """Dispatch narrowing based on condition shape."""
        cond_type = type(cond).__name__

        # x != nil  →  true branch: x is non-optional
        if cond_type == "BinaryOp" and getattr(cond, "op", "") == "!=":
            TypeNarrower._narrow_nil_check(cond, env, true_env, false_env, negated=False)

        # x == nil  →  false branch: x is non-optional
        elif cond_type == "BinaryOp" and getattr(cond, "op", "") == "==":
            TypeNarrower._narrow_nil_check(cond, env, true_env, false_env, negated=True)

        # type_of(x) == "int"  →  true branch: x is int
        elif cond_type == "BinaryOp" and getattr(cond, "op", "") == "==":
            TypeNarrower._narrow_typeof(cond, env, true_env, false_env)

        # !expr → swap branches
        elif cond_type == "UnaryOp" and getattr(cond, "op", "") in ("!", "not"):
            TypeNarrower._analyze(cond.operand, env, false_env, true_env)

        # expr && expr → both narrow the true branch
        elif cond_type == "BinaryOp" and getattr(cond, "op", "") in ("&&", "and"):
            TypeNarrower._analyze(cond.left, env, true_env, false_env)
            TypeNarrower._analyze(cond.right, env, true_env, false_env)

        # expr || expr → both narrow the false branch
        elif cond_type == "BinaryOp" and getattr(cond, "op", "") in ("||", "or"):
            TypeNarrower._analyze(cond.left, env, true_env, false_env)
            TypeNarrower._analyze(cond.right, env, true_env, false_env)

    @staticmethod
    def _narrow_nil_check(cond, env: TypeEnvironment,
                          true_env: TypeEnvironment,
                          false_env: TypeEnvironment,
                          negated: bool):
        """Handle `x != nil` or `x == nil` patterns."""
        left = cond.left
        right = cond.right

        # Determine which side is the variable and which is nil
        var_name = None
        if getattr(right, "__class__", None).__name__ == "NilLiteral" or \
           (hasattr(right, "value") and right.value is None):
            if hasattr(left, "name"):
                var_name = left.name
        elif getattr(left, "__class__", None).__name__ == "NilLiteral" or \
             (hasattr(left, "value") and left.value is None):
            if hasattr(right, "name"):
                var_name = right.name

        if var_name is None:
            return

        current_type = env.lookup(var_name)
        if current_type is None:
            return

        # If the current type is Optional, narrow to the inner type
        if isinstance(current_type, OptionalType):
            non_nil_type = current_type.inner_type
        else:
            non_nil_type = current_type

        if negated:
            # x == nil → true branch keeps optional, false branch narrows
            false_env.define(var_name, non_nil_type)
        else:
            # x != nil → true branch narrows, false branch is None
            true_env.define(var_name, non_nil_type)
            false_env.define(var_name, NONE)

    @staticmethod
    def _narrow_typeof(cond, env: TypeEnvironment,
                       true_env: TypeEnvironment,
                       false_env: TypeEnvironment):
        """Handle `type_of(x) == "int"` patterns."""
        left = cond.left
        right = cond.right

        # Check for type_of(var) == "typename"
        if getattr(left, "__class__", None).__name__ == "CallExpr":
            if hasattr(left, "callee") and hasattr(left.callee, "name") and \
               left.callee.name == "type_of" and len(getattr(left, "args", [])) == 1:
                arg = left.args[0]
                if hasattr(arg, "name") and hasattr(right, "value") and isinstance(right.value, str):
                    var_name = arg.name
                    type_name = right.value
                    narrowed = _TYPE_MAP_NARROW.get(type_name)
                    if narrowed:
                        true_env.define(var_name, narrowed)

    @staticmethod
    def narrow_optional(typ: LTLType) -> LTLType:
        """Strip the Optional wrapper from a type, if present."""
        if isinstance(typ, OptionalType):
            return typ.inner_type
        return typ

    @staticmethod
    def is_nilable(typ: LTLType) -> bool:
        """Check whether a type could be nil."""
        if isinstance(typ, OptionalType):
            return True
        if isinstance(typ, UnionType):
            return any(t.name == "none" for t in typ.types)
        return typ.name == "none"


# Type narrowing name → type map
_TYPE_MAP_NARROW = {
    "int": INT,
    "float": FLOAT,
    "str": STR,
    "bool": BOOL,
    "list": ListType(ANY),
    "map": MapType(STR, ANY),
}


# ─── Type Inference Engine ─────────────────────────────────────────────

class TypeInferencer:
    """
    Infers types for expressions and statements.
    Uses bidirectional type inference with constraint solving.
    """

    def __init__(self):
        self._constraints: List[Tuple[LTLType, LTLType, str]] = []
        self._substitutions: Dict[str, LTLType] = {}
        self._counter = 0

    def fresh_typevar(self, prefix: str = "T") -> TypeVar:
        """Generate a fresh type variable."""
        self._counter += 1
        return TypeVar(f"{prefix}{self._counter}")

    def constrain(self, expected: LTLType, actual: LTLType, context: str = ""):
        """Add a type constraint: expected = actual."""
        self._constraints.append((expected, actual, context))

    def infer_literal(self, value: Any) -> LTLType:
        """Infer the type of a literal value."""
        if isinstance(value, bool):
            return BOOL
        if isinstance(value, int):
            return INT
        if isinstance(value, float):
            return FLOAT
        if isinstance(value, str):
            return STR
        if value is None:
            return NONE
        if isinstance(value, list):
            if not value:
                return ListType(self.fresh_typevar("E"))
            elem_types = [self.infer_literal(v) for v in value]
            unified = self._unify_types(elem_types)
            return ListType(unified)
        if isinstance(value, dict):
            if not value:
                return MapType(self.fresh_typevar("K"), self.fresh_typevar("V"))
            key_types = [self.infer_literal(k) for k in value.keys()]
            val_types = [self.infer_literal(v) for v in value.values()]
            return MapType(self._unify_types(key_types), self._unify_types(val_types))
        return ANY

    def infer_binary(self, op: str, left: LTLType, right: LTLType) -> LTLType:
        """Infer the result type of a binary operation."""
        # Comparison operators always return bool
        if op in ("==", "!=", "<", ">", "<=", ">="):
            return BOOL

        # Boolean operators return bool
        if op in ("and", "or"):
            return BOOL

        # String concatenation
        if op == "+" and (left == STR or right == STR):
            return STR

        # Numeric operations
        if left.is_numeric() and right.is_numeric():
            if left == FLOAT or right == FLOAT:
                return FLOAT
            if op == "/":
                return FLOAT
            return INT

        return ANY

    def infer_unary(self, op: str, operand: LTLType) -> LTLType:
        """Infer the result type of a unary operation."""
        if op in ("not", "!"):
            return BOOL
        if op == "-" and operand.is_numeric():
            return operand
        return ANY

    def _unify_types(self, types: List[LTLType]) -> LTLType:
        """Find the most general type that covers all given types."""
        if not types:
            return ANY

        unique = list(set(types))
        if len(unique) == 1:
            return unique[0]

        # All numeric → widen to float
        if all(t.is_numeric() for t in unique):
            return FLOAT

        # Otherwise → union
        return UnionType(unique)

    def resolve(self, typ: LTLType) -> LTLType:
        """Resolve a type, substituting type variables."""
        if isinstance(typ, TypeVar) and typ.name in self._substitutions:
            return self.resolve(self._substitutions[typ.name])
        return typ

    # ── v1.5 Hindley-Milner unification ───────────────────────────────

    def occurs_check(self, var: "TypeVar", typ: LTLType) -> bool:
        """Return True if TypeVar *var* appears free in *typ*.
        Prevents creation of infinite recursive types during unification.
        """
        typ = self.resolve(typ)
        if isinstance(typ, TypeVar):
            return typ.name == var.name
        if isinstance(typ, ListType):
            return self.occurs_check(var, typ.element_type)
        if isinstance(typ, MapType):
            return (self.occurs_check(var, typ.key_type) or
                    self.occurs_check(var, typ.value_type))
        if isinstance(typ, TupleType):
            return any(self.occurs_check(var, t) for t in typ.element_types)
        if isinstance(typ, FunctionType):
            return (any(self.occurs_check(var, t) for t in typ.param_types) or
                    self.occurs_check(var, typ.return_type))
        if isinstance(typ, UnionType):
            return any(self.occurs_check(var, t) for t in typ.types)
        if isinstance(typ, OptionalType):
            return self.occurs_check(var, typ.inner_type)
        return False

    def unify(self, t1: LTLType, t2: LTLType, context: str = "") -> Optional[str]:
        """Robinson unification — returns an error string on failure, ``None`` on success.
        Mutates ``self._substitutions`` in place.

        Handles: TypeVar, primitive, List, Map, Tuple, FunctionType,
                 OptionalType, UnionType, and the ``ANY`` escape hatch.
        """
        t1 = self.resolve(t1)
        t2 = self.resolve(t2)

        # Trivially equal
        if t1 == t2:
            return None

        # ANY is the top type — accept all
        if t1 == ANY or t2 == ANY:
            return None

        # Bind unresolved type variable (left)
        if isinstance(t1, TypeVar):
            if self.occurs_check(t1, t2):
                return f"Infinite type: {t1.name} occurs in {t2}"
            self._substitutions[t1.name] = t2
            return None

        # Bind unresolved type variable (right)
        if isinstance(t2, TypeVar):
            if self.occurs_check(t2, t1):
                return f"Infinite type: {t2.name} occurs in {t1}"
            self._substitutions[t2.name] = t1
            return None

        # List<A> ~ List<B>
        if isinstance(t1, ListType) and isinstance(t2, ListType):
            return self.unify(t1.element_type, t2.element_type, context)

        # Map<K1,V1> ~ Map<K2,V2>
        if isinstance(t1, MapType) and isinstance(t2, MapType):
            kerr = self.unify(t1.key_type, t2.key_type, context)
            if kerr:
                return kerr
            return self.unify(t1.value_type, t2.value_type, context)

        # Tuple<A1,A2,...> ~ Tuple<B1,B2,...>
        if isinstance(t1, TupleType) and isinstance(t2, TupleType):
            if len(t1.element_types) != len(t2.element_types):
                return f"Tuple arity mismatch: {t1} vs {t2}"
            for e1, e2 in zip(t1.element_types, t2.element_types):
                err = self.unify(e1, e2, context)
                if err:
                    return err
            return None

        # (A1,...)->R1 ~ (B1,...)->R2
        if isinstance(t1, FunctionType) and isinstance(t2, FunctionType):
            if t1.arity != t2.arity:
                return (f"Function arity mismatch"
                        f"{' in ' + context if context else ''}: "
                        f"{t1} vs {t2}")
            for p1, p2 in zip(t1.param_types, t2.param_types):
                err = self.unify(p1, p2, context)
                if err:
                    return err
            return self.unify(t1.return_type, t2.return_type, context)

        # Optional<A> ~ Optional<B>
        if isinstance(t1, OptionalType) and isinstance(t2, OptionalType):
            return self.unify(t1.inner_type, t2.inner_type, context)

        # Nullable coercion: Optional<T> ~ T  (T is a subtype of T?)
        if isinstance(t1, OptionalType):
            return self.unify(t1.inner_type, t2, context)
        if isinstance(t2, OptionalType):
            return self.unify(t1, t2.inner_type, context)

        # Union widening: T ~ T1|T2 if T is a member
        if isinstance(t2, UnionType) and t1 in t2.types:
            return None
        if isinstance(t1, UnionType) and t2 in t1.types:
            return None

        ctx_suffix = f" in {context}" if context else ""
        return f"Type mismatch{ctx_suffix}: expected {t1}, got {t2}"

    def substitute(self, typ: LTLType,
                   subst: Optional[Dict[str, LTLType]] = None) -> LTLType:
        """Apply a substitution map to *typ*, resolving all type variables.
        Uses ``self._substitutions`` when *subst* is ``None``.
        """
        if subst is None:
            subst = self._substitutions
        if isinstance(typ, TypeVar):
            if typ.name in subst:
                return self.substitute(subst[typ.name], subst)
            return typ
        if isinstance(typ, ListType):
            return ListType(self.substitute(typ.element_type, subst))
        if isinstance(typ, MapType):
            return MapType(self.substitute(typ.key_type, subst),
                           self.substitute(typ.value_type, subst))
        if isinstance(typ, TupleType):
            return TupleType([self.substitute(t, subst)
                              for t in typ.element_types])
        if isinstance(typ, FunctionType):
            return FunctionType(
                [self.substitute(p, subst) for p in typ.param_types],
                self.substitute(typ.return_type, subst),
                typ.param_names,
            )
        if isinstance(typ, UnionType):
            return UnionType([self.substitute(t, subst) for t in typ.types])
        if isinstance(typ, OptionalType):
            return OptionalType(self.substitute(typ.inner_type, subst))
        return typ

    def solve(self) -> List[str]:
        """Process all accumulated constraints via unification.
        Returns a list of error messages — empty list means success.
        Populates (and extends) ``self._substitutions`` as a side-effect.
        After calling, the constraint queue is cleared.
        """
        errors: List[str] = []
        for expected, actual, context in self._constraints:
            err = self.unify(expected, actual, context)
            if err:
                errors.append(err)
        self._constraints.clear()
        return errors

    def infer_pattern(self, pattern: Any, subject: LTLType) -> Dict[str, LTLType]:
        """Infer variable bindings introduced by a match-arm pattern (v1.5).

        Returns a dict ``{name: inferred_type}`` for every binding name in the
        pattern.  Also adds appropriate unification constraints.
        """
        from lateralus_lang.ast_nodes import (
            WildcardPattern, LiteralPattern, BindingPattern,
            TypePattern, EnumVariantPattern, TuplePattern,
            ListPattern, OrPattern,
        )
        bindings: Dict[str, LTLType] = {}

        if isinstance(pattern, WildcardPattern):
            return bindings

        if isinstance(pattern, LiteralPattern):
            lit_type = self.infer_literal(pattern.value.value)
            self.constrain(subject, lit_type, "literal pattern")
            return bindings

        if isinstance(pattern, BindingPattern):
            bindings[pattern.name] = self.resolve(subject)
            return bindings

        if isinstance(pattern, TypePattern):
            # subject must be a struct of the given type name
            for i, sub_pat in enumerate(pattern.fields):
                field_tv = self.fresh_typevar(f"F{i}")
                bindings.update(self.infer_pattern(sub_pat, field_tv))
            return bindings

        if isinstance(pattern, EnumVariantPattern):
            # Each constructor argument gets a fresh type variable
            for i, sub_pat in enumerate(pattern.fields):
                field_tv = self.fresh_typevar(f"V{i}")
                bindings.update(self.infer_pattern(sub_pat, field_tv))
            return bindings

        if isinstance(pattern, TuplePattern):
            elem_types = [self.fresh_typevar(f"T{i}")
                          for i in range(len(pattern.elements))]
            self.constrain(subject,
                           TupleType(list(elem_types)),  # type: ignore[arg-type]
                           "tuple pattern")
            for sub_pat, elem_t in zip(pattern.elements, elem_types):
                bindings.update(self.infer_pattern(sub_pat, elem_t))
            return bindings

        if isinstance(pattern, ListPattern):
            elem_tv = self.fresh_typevar("E")
            self.constrain(subject, ListType(elem_tv), "list pattern")
            for sub_pat in pattern.head:
                bindings.update(self.infer_pattern(sub_pat, elem_tv))
            if pattern.rest:
                bindings[pattern.rest] = ListType(self.resolve(elem_tv))
            return bindings

        if isinstance(pattern, OrPattern):
            left  = self.infer_pattern(pattern.left,  subject)
            right = self.infer_pattern(pattern.right, subject)
            # Only names present in *both* branches are in scope after the arm
            common = {k: left[k] for k in left if k in right}
            bindings.update(common)
            return bindings

        return bindings


# ─── Type Checker ──────────────────────────────────────────────────────

@dataclass
class TypeError_:
    """A type checking error (note: named TypeError_ to avoid shadowing builtin)."""
    message: str
    expected: Optional[LTLType] = None
    actual: Optional[LTLType] = None
    location: Optional[str] = None


class TypeChecker:
    """
    Static type checker for LATERALUS programs.
    Walks the AST and checks type consistency.
    """

    def __init__(self):
        self.env = TypeEnvironment()
        self.inferencer = TypeInferencer()
        self.errors: List[TypeError_] = []

        # Register built-in function types
        self._register_builtins()

    def _register_builtins(self):
        """Register types for built-in functions."""
        builtins = {
            "print": FunctionType([ANY], VOID),
            "println": FunctionType([ANY], VOID),
            "len": FunctionType([ANY], INT),
            "str": FunctionType([ANY], STR),
            "int": FunctionType([ANY], INT),
            "float": FunctionType([ANY], FLOAT),
            "bool": FunctionType([ANY], BOOL),
            "type_of": FunctionType([ANY], STR),
            "range": FunctionType([INT, INT], ListType(INT)),
            "abs": FunctionType([NUMBER], NUMBER),
            "min": FunctionType([NUMBER, NUMBER], NUMBER),
            "max": FunctionType([NUMBER, NUMBER], NUMBER),
            "sum": FunctionType([ListType(NUMBER)], NUMBER),
            "sorted": FunctionType([ListType(ANY)], ListType(ANY)),
            "reversed": FunctionType([ListType(ANY)], ListType(ANY)),
            "map": FunctionType([FunctionType([ANY], ANY), ListType(ANY)], ListType(ANY)),
            "filter": FunctionType([FunctionType([ANY], BOOL), ListType(ANY)], ListType(ANY)),
            "reduce": FunctionType([FunctionType([ANY, ANY], ANY), ListType(ANY), ANY], ANY),
            # Math engine
            "mean": FunctionType([ListType(FLOAT)], FLOAT),
            "median": FunctionType([ListType(FLOAT)], FLOAT),
            "std_dev": FunctionType([ListType(FLOAT)], FLOAT),
            "sqrt": FunctionType([FLOAT], FLOAT),
            "sin": FunctionType([FLOAT], FLOAT),
            "cos": FunctionType([FLOAT], FLOAT),
            # Crypto engine
            "sha256": FunctionType([STR], STR),
            "sha512": FunctionType([STR], STR),
            "hmac_sign": FunctionType([STR, STR], STR),
            "hmac_verify": FunctionType([STR, STR, STR], BOOL),
            "to_base64": FunctionType([STR], STR),
            "from_base64": FunctionType([STR], STR),
            "random_token": FunctionType([INT], STR),
            # v1.6: Low-level / OS-dev builtins
            "addr_of": FunctionType([ANY], PtrType(U8)),
            "deref": FunctionType([PtrType(U8)], ANY),
            "sizeof": FunctionType([ANY], USIZE),
            "alignof": FunctionType([ANY], USIZE),
            "offsetof": FunctionType([ANY, STR], USIZE),
        }

        for name, typ in builtins.items():
            self.env.define(name, typ)

    def check_assignment(self, var_name: str, declared_type: Optional[LTLType],
                         value_type: LTLType) -> Optional[TypeError_]:
        """Check that an assignment is type-safe.

        Gradual typing: if either side is a GradualType the assignment
        is always accepted — the mismatch (if any) will be checked at
        runtime via an inserted cast.
        """
        if declared_type is None:
            # Type inference: accept whatever the value type is
            self.env.define(var_name, value_type)
            return None

        # Gradual types defer checking to runtime
        if isinstance(declared_type, GradualType) or isinstance(value_type, GradualType):
            self.env.define(var_name, declared_type)
            return None

        if not declared_type.is_assignable_from(value_type):
            err = TypeError_(
                message=f"Cannot assign {value_type} to variable '{var_name}' of type {declared_type}",
                expected=declared_type,
                actual=value_type,
            )
            self.errors.append(err)
            return err

        self.env.define(var_name, declared_type)
        return None

    def check_call(self, fn_name: str, arg_types: List[LTLType]) -> Tuple[Optional[LTLType], Optional[TypeError_]]:
        """Check a function call and return the result type."""
        fn_type = self.env.lookup(fn_name)

        if fn_type is None:
            err = TypeError_(
                message=f"Unknown function '{fn_name}'",
            )
            self.errors.append(err)
            return ANY, err

        if not isinstance(fn_type, FunctionType):
            err = TypeError_(
                message=f"'{fn_name}' is not callable (type: {fn_type})",
            )
            self.errors.append(err)
            return ANY, err

        if len(arg_types) != fn_type.arity:
            err = TypeError_(
                message=f"'{fn_name}' expects {fn_type.arity} arguments, got {len(arg_types)}",
            )
            self.errors.append(err)
            return fn_type.return_type, err

        # Check each argument
        for i, (expected, actual) in enumerate(zip(fn_type.param_types, arg_types)):
            if not expected.is_assignable_from(actual):
                param_name = fn_type.param_names[i] if i < len(fn_type.param_names) else f"arg{i}"
                err = TypeError_(
                    message=f"Argument '{param_name}' of '{fn_name}': expected {expected}, got {actual}",
                    expected=expected,
                    actual=actual,
                )
                self.errors.append(err)

        return fn_type.return_type, None

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def format_errors(self) -> str:
        lines = []
        for err in self.errors:
            msg = f"TypeError: {err.message}"
            if err.location:
                msg = f"{err.location}: {msg}"
            lines.append(msg)
        return "\n".join(lines)


# ─── Helper: Parse type annotation string ──────────────────────────────

_TYPE_MAP = {
    "int": INT,
    "float": FLOAT,
    "str": STR,
    "string": STR,
    "bool": BOOL,
    "none": NONE,
    "any": ANY,
    "void": VOID,
    "never": NEVER,
}


def parse_type_annotation(annotation: str) -> LTLType:
    """Parse a type annotation string into an LTLType."""
    annotation = annotation.strip()

    # Check primitives
    if annotation in _TYPE_MAP:
        return _TYPE_MAP[annotation]

    # Gradual: ~T (typed/untyped interop boundary)
    if annotation.startswith("~"):
        inner = parse_type_annotation(annotation[1:])
        return GradualType(inner)

    # Optional: T?
    if annotation.endswith("?"):
        inner = parse_type_annotation(annotation[:-1])
        return OptionalType(inner)

    # List: list[T]
    if annotation.startswith("list[") and annotation.endswith("]"):
        inner = parse_type_annotation(annotation[5:-1])
        return ListType(inner)

    # Map: map[K, V]
    if annotation.startswith("map[") and annotation.endswith("]"):
        inner = annotation[4:-1]
        # Simple comma split (doesn't handle nested generics)
        parts = inner.split(",", 1)
        if len(parts) == 2:
            k = parse_type_annotation(parts[0])
            v = parse_type_annotation(parts[1])
            return MapType(k, v)

    # Union: T1 | T2
    if "|" in annotation:
        parts = [parse_type_annotation(p) for p in annotation.split("|")]
        return UnionType(parts)

    # Unknown type — treat as a named type reference
    return LTLType(kind=TypeKind.STRUCT, name=annotation)
