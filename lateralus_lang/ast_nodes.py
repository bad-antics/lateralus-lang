"""
lateralus_lang/ast_nodes.py  ─  LATERALUS Language AST Node Definitions
═══════════════════════════════════════════════════════════════════════════
All Abstract Syntax Tree nodes for the Lateralus scripting language (.ltl).

Node hierarchy
──────────────
  Node (base)
  ├── Program
  ├── Module
  ├── Stmt
  │   ├── FnDecl / AsyncFnDecl
  │   ├── LetDecl
  │   ├── ReturnStmt
  │   ├── IfStmt / MatchStmt
  │   ├── WhileStmt / ForStmt / LoopStmt
  │   ├── TryStmt  (try / recover / ensure)
  │   ├── ImportStmt
  │   ├── ExprStmt
  │   └── BlockStmt
  └── Expr
      ├── Literal  (int, float, str, bool, nil)
      ├── Ident
      ├── BinOp  (arithmetic, logical, comparison, pipeline |>)
      ├── UnaryOp
      ├── CallExpr
      ├── IndexExpr
      ├── FieldExpr
      ├── LambdaExpr
      ├── ListExpr / MapExpr
      ├── AwaitExpr
      └── CastExpr      ├── TypeMatchExpr           (v1.5 — ADT / type pattern matching)
      ├── ResultExpr              (v1.5 — Result::Ok / Result::Err constructors)
      └── OptionExpr              (v1.5 — Option::Some / Option::None constructors)

  Pattern (v1.5 — used inside TypeMatchArm)
      ├── WildcardPattern         (_)
      ├── LiteralPattern          (42, "str", true)
      ├── BindingPattern          (x — captures value as variable)
      ├── TypePattern             (SomeType(a, b))
      ├── EnumVariantPattern      (Result::Ok(v), Option::Some(v))
      ├── TuplePattern            ((a, b, c))
      ├── ListPattern             ([head, ...tail])
      └── OrPattern               (pat1 | pat2)
Every node carries a SourceSpan for precise error reporting.
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Source location
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SourceSpan:
    file:   str
    line:   int
    col:    int
    end_line: int = 0
    end_col:  int = 0

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"

    @staticmethod
    def unknown(file: str = "<unknown>") -> "SourceSpan":
        return SourceSpan(file, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Type annotations
# ─────────────────────────────────────────────────────────────────────────────

class PrimitiveType(Enum):
    INT    = "int"
    FLOAT  = "float"
    STR    = "str"
    BOOL   = "bool"
    BYTE   = "byte"
    NIL    = "nil"
    ANY    = "any"
    VOID   = "void"


@dataclass
class TypeRef:
    """Represents a type annotation in source."""
    name:       str
    params:     List["TypeRef"]  = field(default_factory=list)   # generic params
    nullable:   bool             = False
    span:       Optional[SourceSpan] = None

    def __str__(self) -> str:
        base = self.name
        if self.params:
            base += f"<{', '.join(str(p) for p in self.params)}>"
        if self.nullable:
            base += "?"
        return base


# ─────────────────────────────────────────────────────────────────────────────
# Base Node
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class Node:
    span: SourceSpan = field(default_factory=lambda: SourceSpan("<unknown>", 0, 0))

    def accept(self, visitor: "ASTVisitor") -> Any:
        method = f"visit_{type(self).__name__}"
        fn = getattr(visitor, method, visitor.generic_visit)
        return fn(self)


# ─────────────────────────────────────────────────────────────────────────────
# Top-level
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Program(Node):
    module:   Optional[str]      = None
    imports:  List["ImportStmt"] = field(default_factory=list)
    body:     List["Stmt"]       = field(default_factory=list)
    source_file: str             = "<unknown>"


@dataclass
class ImportStmt(Node):
    path:    str                       # e.g. "io", "math", "polyglot.julia"
    alias:   Optional[str]    = None
    items:   List[str]        = field(default_factory=list)  # selective import


# ─────────────────────────────────────────────────────────────────────────────
# Statements
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Stmt(Node):
    pass


@dataclass
class BlockStmt(Stmt):
    stmts: List[Stmt] = field(default_factory=list)


@dataclass
class Param:
    name:    str
    type_:   Optional[TypeRef]
    default: Optional["Expr"]  = None
    span:    Optional[SourceSpan] = None
    vararg:  bool = False


@dataclass
class FnDecl(Stmt):
    name:       str
    params:     List[Param]         = field(default_factory=list)
    ret_type:   Optional[TypeRef]   = None
    body:       Optional[BlockStmt] = None
    generics:   List                = field(default_factory=list)
    is_async:   bool                = False
    is_pub:     bool                = False
    decorators: List["Decorator"]   = field(default_factory=list)


@dataclass
class LetDecl(Stmt):
    name:      str
    type_:     Optional[TypeRef]  = None
    value:     Optional["Expr"]   = None
    mutable:   bool               = True
    is_const:  bool               = False


@dataclass
class ReturnStmt(Stmt):
    value: Optional["Expr"] = None


@dataclass
class IfStmt(Stmt):
    condition:   "Expr"
    then_block:  BlockStmt
    elif_arms:   List[Tuple["Expr", BlockStmt]] = field(default_factory=list)
    else_block:  Optional[BlockStmt]            = None


@dataclass
class MatchArm:
    pattern:  "Expr"        # literal, range, or wildcard Ident("_")
    guard:    Optional["Expr"] = None
    body:     Optional[BlockStmt] = None
    value:    Optional["Expr"]    = None   # shorthand arm: pattern => expr


@dataclass
class MatchStmt(Stmt):
    subject: "Expr"
    arms:    List[MatchArm] = field(default_factory=list)


@dataclass
class WhileStmt(Stmt):
    condition: "Expr"
    body:      BlockStmt


@dataclass
class LoopStmt(Stmt):
    body: BlockStmt


@dataclass
class ForStmt(Stmt):
    var:    str
    iter:   "Expr"
    body:   BlockStmt


@dataclass
class BreakStmt(Stmt):
    label: Optional[str]    = None   # labelled break:        break @loop_name
    value: Optional["Expr"] = None   # loop-expression value: break computed_val


@dataclass
class ContinueStmt(Stmt):
    label: Optional[str] = None      # labelled continue: continue @loop_name


@dataclass
class RecoverClause:
    error_type: Optional[str]     # None → catch-all "*"
    binding:    Optional[str]
    body:       BlockStmt
    span:       Optional[SourceSpan] = None


@dataclass
class TryStmt(Stmt):
    """
    try { … }
    recover ErrorType(e) { … }
    recover * (e)        { … }
    ensure               { … }
    """
    body:       BlockStmt
    recoveries: List[RecoverClause]  = field(default_factory=list)
    ensure:     Optional[BlockStmt]  = None


@dataclass
class ExprStmt(Stmt):
    expr: "Expr"


@dataclass
class AssignStmt(Stmt):
    target: "Expr"
    op:     str       # "=", "+=", "-=", "*=", "/=", "|>="
    value:  "Expr"


# ─────────────────────────────────────────────────────────────────────────────
# Expressions
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class Expr(Node):
    inferred_type: Optional[TypeRef] = field(default=None, compare=False, repr=False)


@dataclass
class Literal(Expr):
    value: Any
    kind:  str    # "int" | "float" | "str" | "bool" | "nil"


@dataclass
class Ident(Expr):
    name: str


@dataclass
class BinOp(Expr):
    op:    str    # "+", "-", "*", "/", "%", "**", "|>",
                  # "==", "!=", "<", ">", "<=", ">=",
                  # "&&", "||", "&", "|", "^", "<<", ">>"
    left:  Expr
    right: Expr


@dataclass
class UnaryOp(Expr):
    op:      str    # "-", "!", "~", "typeof", "sizeof"
    operand: Expr


@dataclass
class CallExpr(Expr):
    callee:  Expr
    args:    List[Expr]             = field(default_factory=list)
    kwargs:  List[Tuple[str, Expr]] = field(default_factory=list)


@dataclass
class IndexExpr(Expr):
    obj:   Expr
    index: Expr


@dataclass
class FieldExpr(Expr):
    obj:   Expr
    field: str


@dataclass
class LambdaExpr(Expr):
    params:   List[Param]
    ret_type: Optional[TypeRef] = None
    body:     Optional["Expr"]  = None         # short form: fn(x) x * 2
    block:    Optional[BlockStmt] = None       # long form:  fn(x) { … }
    is_async: bool = False


@dataclass
class ListExpr(Expr):
    elements: List[Expr] = field(default_factory=list)


@dataclass
class MapExpr(Expr):
    pairs: List[Tuple[Expr, Expr]] = field(default_factory=list)


@dataclass
class TupleExpr(Expr):
    elements: List[Expr] = field(default_factory=list)


@dataclass
class AwaitExpr(Expr):
    value: Expr


@dataclass
class CastExpr(Expr):
    value:    Expr
    target:   TypeRef


@dataclass
class RangeExpr(Expr):
    start:     Expr
    end:       Expr
    inclusive: bool = True   # 1..10 (inclusive) vs 1..<10 (exclusive)


@dataclass
class InterpolatedStr(Expr):
    """String interpolation: "Hello {name}!" """
    parts: List[Any]   # alternating str literals and Expr


# ─────────────────────────────────────────────────────────────────────────────
# v1.1 – Struct / Enum / Impl / Interface / Type-alias / Decorator  (NEW)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StructField:
    """A single field inside a struct declaration."""
    name:    str
    type_:   Optional[TypeRef]
    default: Optional["Expr"]   = None
    span:    Optional[SourceSpan] = None


@dataclass
class StructDecl(Stmt):
    """
    struct Point { x: int, y: int }
    pub struct Foo<T> : Drawable { ... }
    """
    name:       str
    fields:     List[StructField]   = field(default_factory=list)
    generics:   List[str]           = field(default_factory=list)
    interfaces: List[str]           = field(default_factory=list)
    is_pub:     bool                = False
    decorators: List["Decorator"]   = field(default_factory=list)


@dataclass
class EnumVariant:
    """One variant in an enum declaration."""
    name:   str
    fields: List[StructField]   = field(default_factory=list)   # tuple/record variant
    value:  Optional["Expr"]    = None                          # explicit discriminant
    span:   Optional[SourceSpan] = None


@dataclass
class EnumDecl(Stmt):
    """
    enum Color { Red, Green, Blue }
    enum Result<T, E> { Ok(T), Err(E) }
    """
    name:       str
    variants:   List[EnumVariant]  = field(default_factory=list)
    generics:   List[str]          = field(default_factory=list)
    is_pub:     bool               = False
    decorators: List["Decorator"]  = field(default_factory=list)


@dataclass
class TypeAlias(Stmt):
    """type Callback = fn(int) -> str"""
    name:     str
    target:   TypeRef
    generics: List[str] = field(default_factory=list)
    is_pub:   bool      = False


@dataclass
class ImplBlock(Stmt):
    """
    impl Point { fn new(self, x: int, y: int) -> Point { … } }
    impl Drawable for Shape { fn draw(self) { … } }
    """
    type_name: str
    interface: Optional[str]   = None   # 'for Interface' clause
    methods:   List[FnDecl]    = field(default_factory=list)
    generics:  List[str]       = field(default_factory=list)


@dataclass
class InterfaceDecl(Stmt):
    """
    interface Drawable { fn draw(self) }
    pub interface Serializable<T> { fn serialize(self) -> str }
    """
    name:     str
    extends:  List[str]    = field(default_factory=list)
    methods:  List[FnDecl] = field(default_factory=list)
    generics: List[str]    = field(default_factory=list)
    is_pub:   bool         = False


@dataclass
class StructLiteral(Expr):
    """Point { x: 1, y: 2 }  — struct instantiation syntax."""
    name:   str
    fields: List[Tuple[str, "Expr"]] = field(default_factory=list)


@dataclass
class SelfExpr(Expr):
    """The `self` keyword inside a method body."""
    pass


@dataclass
class Decorator(Node):
    """@inline  or  @derive(Debug, Clone)  before a declaration."""
    name: str
    args: List["Expr"]  = field(default_factory=list)
    kwargs: List[Tuple[str, "Expr"]] = field(default_factory=list)


@dataclass
class YieldExpr(Expr):
    """yield value  — inside a generator / coroutine."""
    value: Optional["Expr"] = None


@dataclass
class SpawnExpr(Expr):
    """spawn fn_call  — launch a concurrent task."""
    call: "Expr" = None


# v1.2 – Polyglot / Foreign block  (NEW)

@dataclass
class ForeignParam:
    """A single name: expr binding passed into a foreign block."""
    name:  str
    value: "Expr"


@dataclass
class ForeignBlock(Stmt):
    """
    foreign "<lang>" (<params>) { "<source>" }

    Executes <source> in the named external runtime, passing <params> as
    a JSON object.  The result is a PolyResult-like mapping.

    Example::

        foreign "julia" (n: limit) {
            "using Primes; params=JSON.parse(readline()); println(collect(primes(params[\\"n\\"])))"
        }
    """
    lang:    str
    source:  str
    params:  List[ForeignParam] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# v1.3 nodes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ThrowStmt(Stmt):
    """throw <expr>  — raise an exception.

    Example::

        throw ValueError("index out of bounds")
    """
    value: "Expr"


@dataclass
class TryExpr(Expr):
    """try { body } recover EType(e) { ... } [ensure { ... }]  as an expression.

    Example::

        let result = try { risky() } recover Error(e) { default_val }
    """
    body:       "BlockStmt"
    recoveries: List["RecoverClause"]
    ensure:     Optional["BlockStmt"]


@dataclass
class EmitStmt(Stmt):
    """emit <event_name>(<args...>)  — publish an event on the built-in EventBus.

    Example::

        emit data_ready(result, timestamp)
    """
    event:  str
    args:   List["Expr"] = field(default_factory=list)


@dataclass
class ProbeExpr(Expr):
    """probe <expr>  — runtime introspection: returns a dict with type, value, size.

    Example::

        let info = probe my_list
        // → { "type": "list", "value": [...], "len": 5 }
    """
    value: "Expr"


@dataclass
class MeasureBlock(Stmt):
    """measure { <body> }  — time a block, bind result to an optional name.

    Example::

        measure "sort" {
            let sorted = big_list |> sort
        }
        // prints: [measure] sort: 1.23 ms
    """
    label:  Optional[str]
    body:   "BlockStmt"


# ─────────────────────────────────────────────────────────────────────────────
# Visitor base
# ─────────────────────────────────────────────────────────────────────────────

class ASTVisitor:
    """Visitor base — override visit_<ClassName> for specific nodes."""

    def generic_visit(self, node: Node) -> Any:
        """Called for any node that has no explicit visitor method."""
        for val in vars(node).values():
            if isinstance(val, Node):
                val.accept(self)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, Node):
                        item.accept(self)
        return None

    def visit_Program(self, node: Program) -> Any:              return self.generic_visit(node)
    def visit_ImportStmt(self, node: ImportStmt) -> Any:        return self.generic_visit(node)
    def visit_FnDecl(self, node: FnDecl) -> Any:                return self.generic_visit(node)
    def visit_LetDecl(self, node: LetDecl) -> Any:              return self.generic_visit(node)
    def visit_ReturnStmt(self, node: ReturnStmt) -> Any:        return self.generic_visit(node)
    def visit_IfStmt(self, node: IfStmt) -> Any:                return self.generic_visit(node)
    def visit_MatchStmt(self, node: MatchStmt) -> Any:          return self.generic_visit(node)
    def visit_WhileStmt(self, node: WhileStmt) -> Any:          return self.generic_visit(node)
    def visit_LoopStmt(self, node: LoopStmt) -> Any:            return self.generic_visit(node)
    def visit_ForStmt(self, node: ForStmt) -> Any:              return self.generic_visit(node)
    def visit_TryStmt(self, node: TryStmt) -> Any:              return self.generic_visit(node)
    def visit_ExprStmt(self, node: ExprStmt) -> Any:            return self.generic_visit(node)
    def visit_AssignStmt(self, node: AssignStmt) -> Any:        return self.generic_visit(node)
    def visit_BlockStmt(self, node: BlockStmt) -> Any:          return self.generic_visit(node)
    def visit_BreakStmt(self, node: BreakStmt) -> Any:          return None
    def visit_ContinueStmt(self, node: ContinueStmt) -> Any:    return None
    def visit_Literal(self, node: Literal) -> Any:              return self.generic_visit(node)
    def visit_Ident(self, node: Ident) -> Any:                  return self.generic_visit(node)
    def visit_BinOp(self, node: BinOp) -> Any:                  return self.generic_visit(node)
    def visit_UnaryOp(self, node: UnaryOp) -> Any:              return self.generic_visit(node)
    def visit_CallExpr(self, node: CallExpr) -> Any:            return self.generic_visit(node)
    def visit_IndexExpr(self, node: IndexExpr) -> Any:          return self.generic_visit(node)
    def visit_FieldExpr(self, node: FieldExpr) -> Any:          return self.generic_visit(node)
    def visit_LambdaExpr(self, node: LambdaExpr) -> Any:        return self.generic_visit(node)
    def visit_ListExpr(self, node: ListExpr) -> Any:            return self.generic_visit(node)
    def visit_MapExpr(self, node: MapExpr) -> Any:              return self.generic_visit(node)
    def visit_TupleExpr(self, node: TupleExpr) -> Any:          return self.generic_visit(node)
    def visit_AwaitExpr(self, node: AwaitExpr) -> Any:          return self.generic_visit(node)
    def visit_CastExpr(self, node: CastExpr) -> Any:            return self.generic_visit(node)
    def visit_RangeExpr(self, node: RangeExpr) -> Any:          return self.generic_visit(node)
    def visit_InterpolatedStr(self, node: InterpolatedStr) -> Any: return self.generic_visit(node)

    # v1.1 visitors
    def visit_StructDecl(self, node: "StructDecl") -> Any:       return self.generic_visit(node)
    def visit_EnumDecl(self, node: "EnumDecl") -> Any:           return self.generic_visit(node)
    def visit_TypeAlias(self, node: "TypeAlias") -> Any:         return self.generic_visit(node)
    def visit_ImplBlock(self, node: "ImplBlock") -> Any:         return self.generic_visit(node)
    def visit_InterfaceDecl(self, node: "InterfaceDecl") -> Any: return self.generic_visit(node)
    def visit_StructLiteral(self, node: "StructLiteral") -> Any: return self.generic_visit(node)
    def visit_SelfExpr(self, node: "SelfExpr") -> Any:           return self.generic_visit(node)
    def visit_Decorator(self, node: "Decorator") -> Any:         return self.generic_visit(node)
    def visit_YieldExpr(self, node: "YieldExpr") -> Any:         return self.generic_visit(node)
    def visit_SpawnExpr(self, node: "SpawnExpr") -> Any:         return self.generic_visit(node)
    # v1.2 visitors
    def visit_ForeignBlock(self, node: "ForeignBlock") -> Any:   return self.generic_visit(node)
    # v1.3 visitors
    def visit_ThrowStmt(self, node: "ThrowStmt") -> Any:         return self.generic_visit(node)
    def visit_TryExpr(self, node: "TryExpr") -> Any:             return self.generic_visit(node)
    def visit_EmitStmt(self, node: "EmitStmt") -> Any:           return self.generic_visit(node)
    def visit_ProbeExpr(self, node: "ProbeExpr") -> Any:         return self.generic_visit(node)
    def visit_MeasureBlock(self, node: "MeasureBlock") -> Any:   return self.generic_visit(node)
    # v1.4 visitors
    def visit_ChainExpr(self, node: "ChainExpr") -> Any:           return self.generic_visit(node)
    def visit_PropagateExpr(self, node: "PropagateExpr") -> Any:   return self.generic_visit(node)
    def visit_ComprehensionExpr(self, node: "ComprehensionExpr") -> Any: return self.generic_visit(node)
    def visit_GuardExpr(self, node: "GuardExpr") -> Any:           return self.generic_visit(node)
    def visit_WhereClause(self, node: "WhereClause") -> Any:       return self.generic_visit(node)
    def visit_PipelineAssign(self, node: "PipelineAssign") -> Any: return self.generic_visit(node)
    def visit_SpreadExpr(self, node: "SpreadExpr") -> Any:         return self.generic_visit(node)
    def visit_TernaryExpr(self, node: "TernaryExpr") -> Any:       return self.generic_visit(node)
    # v1.5 visitors
    def visit_TypeMatchExpr(self, node: "TypeMatchExpr") -> Any:   return self.generic_visit(node)
    def visit_ResultExpr(self, node: "ResultExpr") -> Any:         return self.generic_visit(node)
    def visit_OptionExpr(self, node: "OptionExpr") -> Any:         return self.generic_visit(node)
    def visit_WildcardPattern(self, node: "WildcardPattern") -> Any: return None
    def visit_LiteralPattern(self, node: "LiteralPattern") -> Any:   return self.generic_visit(node)
    def visit_BindingPattern(self, node: "BindingPattern") -> Any:   return None
    def visit_TypePattern(self, node: "TypePattern") -> Any:         return self.generic_visit(node)
    def visit_EnumVariantPattern(self, node: "EnumVariantPattern") -> Any: return self.generic_visit(node)
    def visit_TuplePattern(self, node: "TuplePattern") -> Any:       return self.generic_visit(node)
    def visit_ListPattern(self, node: "ListPattern") -> Any:         return self.generic_visit(node)
    def visit_OrPattern(self, node: "OrPattern") -> Any:             return self.generic_visit(node)
    # v1.6 low-level visitors
    def visit_UnsafeBlock(self, node: "UnsafeBlock") -> Any:         return self.generic_visit(node)
    def visit_ExternDecl(self, node: "ExternDecl") -> Any:           return self.generic_visit(node)
    def visit_InlineAsm(self, node: "InlineAsm") -> Any:             return self.generic_visit(node)
    def visit_VolatileExpr(self, node: "VolatileExpr") -> Any:       return self.generic_visit(node)
    def visit_StaticDecl(self, node: "StaticDecl") -> Any:           return self.generic_visit(node)
    def visit_AddrOfExpr(self, node: "AddrOfExpr") -> Any:           return self.generic_visit(node)
    def visit_DerefExpr(self, node: "DerefExpr") -> Any:             return self.generic_visit(node)
    def visit_AlignofExpr(self, node: "AlignofExpr") -> Any:         return self.generic_visit(node)
    def visit_OffsetofExpr(self, node: "OffsetofExpr") -> Any:       return self.generic_visit(node)


# ─────────────────────────────────────────────────────────────────────────────
# v1.4 nodes — Error chaining, propagation, comprehensions, guards, where
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChainExpr(Expr):
    """error.caused_by(cause) — chain errors together.

    Example::

        let wrapped = ChainExpr(LtlError("high-level"), original_err)
        // → LtlError("high-level", cause=original_err)
    """
    error: "Expr"
    cause: "Expr"


@dataclass
class PropagateExpr(Expr):
    """expr? — propagate errors upward (Result unwrap-or-return).

    Example::

        let val = risky_call()?   // returns Err early if risky_call fails
    """
    value: "Expr"


@dataclass
class ComprehensionExpr(Expr):
    """[expr for var in iter if condition] — list/set/map comprehension.

    Example::

        let squares = [x * x for x in range(10) if x > 3]
    """
    expr:      "Expr"
    var:       str
    iter:      "Expr"
    condition: Optional["Expr"] = None
    kind:      str = "list"   # "list" | "set" | "map"


@dataclass
class GuardExpr(Expr):
    """guard condition else { fallback } — guard clause.

    Example::

        guard x > 0 else { return -1 }
    """
    condition: "Expr"
    else_body: "BlockStmt"


@dataclass
class WhereClause(Expr):
    """expr where { bindings } — local scoped bindings.

    Example::

        let area = width * height where {
            let width = 10
            let height = 20
        }
    """
    expr:     "Expr"
    bindings: "BlockStmt"


@dataclass
class PipelineAssign(Stmt):
    """target |>= expr — pipeline assignment (sugar).

    Example::

        data |>= transform |> validate
    """
    target: "Expr"
    value:  "Expr"


@dataclass
class SpreadExpr(Expr):
    """...expr — spread/splat operator.

    Example::

        let merged = [...list1, ...list2, extra]
    """
    value: "Expr"


@dataclass
class TernaryExpr(Expr):
    """condition ? then_val : else_val — ternary expression.

    Example::

        let result = x > 0 ? x : -x
    """
    condition: "Expr"
    then_val:  "Expr"
    else_val:  "Expr"


# ─────────────────────────────────────────────────────────────────────────────
# v1.5 nodes — ADTs, type pattern matching, Result/Option
# ─────────────────────────────────────────────────────────────────────────────

# ── Patterns ─────────────────────────────────────────────────────────────────

@dataclass
class WildcardPattern(Node):
    """_ — matches anything and discards the value.

    Example::

        match value { _ => "don't care" }
    """
    pass


@dataclass
class LiteralPattern(Node):
    """Match against a literal value.

    Example::

        match code { 0 => "ok", 404 => "not found", _ => "other" }
    """
    value: "Literal"


@dataclass
class BindingPattern(Node):
    """Named capture — bind the matched value to a variable.

    Example::

        match opt { Option::Some(n) => n + 1, _ => 0 }
        #                       ^ BindingPattern("n")
    """
    name: str


@dataclass
class TypePattern(Node):
    """Match and destructure a struct-typed value.

    Example::

        match point { Point(x, y) => x + y }
    """
    type_name: str
    fields:    List["Node"] = field(default_factory=list)  # Pattern nodes


@dataclass
class EnumVariantPattern(Node):
    """Match an ADT enum variant (qualified with `::` separator).

    Example::

        match result {
            Result::Ok(v)  => println("got {v}"),
            Result::Err(e) => println("error: {e}"),
        }
    """
    enum_name:    str
    variant_name: str
    fields:       List["Node"] = field(default_factory=list)  # Pattern nodes


@dataclass
class TuplePattern(Node):
    """Destructure a tuple value.

    Example::

        match pair { (0, y) => y, (x, 0) => x, (x, y) => x + y }
    """
    elements: List["Node"] = field(default_factory=list)  # Pattern nodes


@dataclass
class ListPattern(Node):
    """Head/tail list destructuring.

    Example::

        match lst { [head, ...tail] => head, [] => nil }
    """
    head:    List["Node"] = field(default_factory=list)  # leading patterns
    rest:    Optional[str] = None                        # rest binding name


@dataclass
class OrPattern(Node):
    """Alternative patterns — match if either branch matches.

    Example::

        match x { 1 | 2 | 3 => "small", _ => "large" }
    """
    left:  "Node"
    right: "Node"


# ── TypeMatchArm & TypeMatchExpr ─────────────────────────────────────────────

@dataclass
class TypeMatchArm:
    """A single arm inside a type match expression.

    Fields:
        pattern  — any Pattern node (WildcardPattern, EnumVariantPattern, etc.)
        guard    — optional 'if <expr>' guard
        body     — block body { ... } for multi-statement arms
        value    — single expression value for shorthand arms (=> expr)
    """
    pattern: "Node"
    guard:   Optional["Expr"]   = None
    body:    Optional[BlockStmt] = None
    value:   Optional["Expr"]   = None


@dataclass
class TypeMatchExpr(Expr):
    """Full match expression — supports value and type patterns (v1.5).

    Example::

        let label = match result {
            Result::Ok(v)  => "success: {v}",
            Result::Err(e) => "failure: {e}",
            _              => "unknown",
        }
    """
    subject: "Expr"
    arms:    List[TypeMatchArm] = field(default_factory=list)


# ── Result / Option constructors ─────────────────────────────────────────────

@dataclass
class ResultExpr(Expr):
    """Result::Ok(value) or Result::Err(error) constructor.

    Example::

        fn safe_div(a: float, b: float) -> Result<float, str> {
            if b == 0.0 { return Result::Err("division by zero") }
            return Result::Ok(a / b)
        }
    """
    variant: str   # "Ok" | "Err"
    value:   "Expr"


@dataclass
class OptionExpr(Expr):
    """Option::Some(value) or Option::None constructor.

    Example::

        fn find_user(id: int) -> Option<str> {
            if id == 1 { return Option::Some("Alice") }
            return Option::None
        }
    """
    variant: str            # "Some" | "None"
    value:   Optional["Expr"] = None  # None only for Option::None


# ─────────────────────────────────────────────────────────────────────────────
# v1.6 nodes — Low-level / OS-dev constructs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UnsafeBlock(Stmt):
    """unsafe { ... } — unchecked block allowing raw pointer ops.

    Example::

        unsafe {
            let ptr = addr_of(buffer)
            deref(ptr) = 0xFF
        }
    """
    body: BlockStmt


@dataclass
class ExternDecl(Stmt):
    """extern fn declaration — links to an external symbol.

    Example::

        extern fn memcpy(dest: Ptr<u8>, src: Ptr<u8>, n: usize) -> Ptr<u8>
        extern fn outb(port: u16, val: u8)
    """
    name:        str
    params:      List["Param"]
    return_type: Optional[str] = None
    abi:         str = "C"     # calling convention


@dataclass
class InlineAsm(Expr):
    """asm { "instruction" } — inline assembly block.

    Example::

        unsafe {
            asm {
                "mov $0x3F8, %dx"
                "out %al, %dx"
            }
        }
    """
    template:    str                       # asm template string
    outputs:     List[str] = field(default_factory=list)
    inputs:      List[str] = field(default_factory=list)
    clobbers:    List[str] = field(default_factory=list)


@dataclass
class VolatileExpr(Expr):
    """volatile(expr) — force non-elided memory access.

    Example::

        let status = volatile(mmio_reg)
    """
    operand: "Expr"


@dataclass
class StaticDecl(Stmt):
    """static [mut] NAME: Type = value — module-level variable.

    Example::

        static mut COUNTER: u32 = 0
        static MAGIC: u32 = 0xDEADBEEF
    """
    name:     str
    type_ann: Optional[str] = None
    value:    Optional["Expr"] = None
    mutable:  bool = False


@dataclass
class AddrOfExpr(Expr):
    """addr_of(expr) — take address of a value, yielding Ptr<T>.

    Example::

        let p: Ptr<int> = addr_of(x)
    """
    operand: "Expr"


@dataclass
class DerefExpr(Expr):
    """deref(ptr) — dereference a pointer, yielding the pointee.

    Example::

        let val = deref(p)
    """
    operand: "Expr"


@dataclass
class AlignofExpr(Expr):
    """alignof(Type) — alignment of a type in bytes.

    Example::

        let a = alignof(u64)   // → 8
    """
    type_name: str


@dataclass
class OffsetofExpr(Expr):
    """offsetof(Struct, field) — byte offset of a field in a struct.

    Example::

        let off = offsetof(Point, y)   // byte offset of field y
    """
    struct_name: str
    field_name:  str


# ─────────────────────────────────────────────────────────────────────────────
# v1.6 – Concurrency & Async  (NEW)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SelectArm:
    """One arm of a select statement.

    Forms:
        recv:    msg from ch => { ... }
        send:    send(ch, val) => { ... }
        timeout: after <ms> => { ... }
        default: _ => { ... }
    """
    kind:     str                          # "recv", "send", "timeout", "default"
    channel:  Optional["Expr"]   = None    # channel expr (recv/send)
    binding:  Optional[str]      = None    # variable name (recv)
    value:    Optional["Expr"]   = None    # value expr (send) or ms (timeout)
    body:     Optional[BlockStmt] = None
    span:     Optional[SourceSpan] = None


@dataclass
class SelectStmt(Stmt):
    """select { arm1, arm2, ... } — channel multiplexing.

    Example::

        select {
            msg from inbox => { println(msg) }
            send(outbox, data) => { println("sent") }
            after 1000 => { println("timeout") }
            _ => { println("default") }
        }
    """
    arms: List[SelectArm] = field(default_factory=list)


@dataclass
class ChannelExpr(Expr):
    """channel<T>(capacity) — create a typed channel.

    Example::

        let ch = channel<int>(10)
        let unbuf = channel<str>()
    """
    elem_type: Optional[TypeRef] = None
    capacity:  Optional["Expr"]  = None


@dataclass
class NurseryBlock(Stmt):
    """nursery { spawn t1(); spawn t2() } — structured concurrency.

    All spawned tasks must complete (or fail) before the nursery
    exits.  If any child fails the nursery cancels the siblings.

    Example::

        nursery {
            spawn fetch("url1")
            spawn fetch("url2")
        }
    """
    body: Optional[BlockStmt] = None
    name: Optional[str] = None        # optional nursery label


@dataclass
class CancelExpr(Expr):
    """cancel_token() — create a cancellation token.

    Example::

        let token = cancel_token()
        spawn with token { long_work() }
        token.cancel()
    """
    pass


@dataclass
class AsyncForStmt(Stmt):
    """async for x in stream { ... } — iterate over an async stream.

    Example::

        async for msg in subscribe("events") {
            println(msg)
        }
    """
    var:    str
    iter:   "Expr"
    body:   Optional[BlockStmt] = None


@dataclass
class ParallelExpr(Expr):
    """parallel_map / parallel_filter / parallel_reduce — parallel combinators.

    Example::

        let results = parallel_map(items, fn(x) { compute(x) })
        let big = parallel_filter(items, fn(x) { x > 100 })
    """
    kind:  str           # "map", "filter", "reduce"
    items: "Expr"
    func:  "Expr"
    init:  Optional["Expr"] = None   # initial value for reduce


# ─────────────────────────────────────────────────────────────────────────────
# v1.7 – Package Manager & Build System
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CfgAttr(Node):
    """@cfg(key = "value") — conditional compilation attribute.

    If the condition is false, the decorated item is stripped from the AST
    before code generation.

    Example::

        @cfg(target = "web")
        fn render_canvas() { ... }

        @cfg(feature = "crypto")
        import crypto
    """
    key:   str                    # e.g. "target", "feature", "os", "profile"
    value: str                    # e.g. "web", "crypto", "linux", "release"


@dataclass
class CfgExpr(Expr):
    """cfg!(key = "value") — compile-time boolean expression.

    Example::

        if cfg!(target = "web") {
            println("Running in browser")
        }
    """
    key:   str
    value: str


# ─────────────────────────────────────────────────────────────────────────────
# v1.8 — Metaprogramming
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConstFnDecl(Stmt):
    """const fn name(...) -> T { body }

    A function evaluated entirely at compile time.  The compiler
    constant-folds the body and inlines the result at every call site.
    """
    name:     str
    params:   List[Any]           # Param nodes
    ret_type: Optional[Any] = None
    body:     Optional[Any] = None
    generics: List[str]     = field(default_factory=list)
    is_pub:   bool          = False


@dataclass
class MacroDecl(Stmt):
    """macro name!(...) { body }

    Declares a syntactic macro.  The body is a template that receives the
    caller's arguments as AST fragments and produces new AST.
    """
    name:   str
    params: List[str]       = field(default_factory=list)
    body:   Optional[Any]   = None
    is_pub: bool            = False


@dataclass
class MacroInvocation(Expr):
    """name!(args) — invoke a declared macro.

    During compilation the macro expander replaces this node with the
    expanded AST produced by the macro's body.
    """
    name: str
    args: List["Expr"] = field(default_factory=list)


@dataclass
class CompTimeBlock(Stmt):
    """comptime { stmts }

    A block that is evaluated at compile time.  Side effects (println, etc.)
    run during compilation; the block's final expression (if any) is inlined
    as a constant.
    """
    body: Optional[Any] = None   # Block


@dataclass
class DeriveAttr(Node):
    """@derive(Trait1, Trait2, ...)

    Instructs the compiler to auto-generate trait implementations for a
    struct or enum.  Supported traits: Debug, Clone, Eq, Hash, Serialize,
    Deserialize, Default, Display.
    """
    traits: List[str] = field(default_factory=list)


@dataclass
class ReflectExpr(Expr):
    """reflect!(TypeName) — compile-time type introspection.

    Returns a TypeInfo literal containing the type's fields, methods,
    variants, and implemented traits.
    """
    target: str       # type name to reflect on


@dataclass
class QuoteExpr(Expr):
    """quote { expr } — capture an expression as an AST fragment.

    Used inside macro bodies to build AST programmatically.
    """
    body: Optional[Any] = None


@dataclass
class UnquoteExpr(Expr):
    """$ident or ${expr} — splice a value into a quoted AST fragment.

    Only valid inside a quote { } block.
    """
    expr: Optional["Expr"] = None

