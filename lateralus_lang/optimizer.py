"""
lateralus_lang/optimizer.py — Compilation optimizer for LATERALUS

Implements optimization passes on the IR/AST to improve generated code:
  - Constant folding
  - Dead code elimination
  - Dead branch elimination
  - Strength reduction
  - Algebraic simplification
  - Common subexpression elimination
  - Tail call optimization detection
  - Pipeline fusion
  - Function inlining analysis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# --- Optimization Level ------------------------------------------------

class OptLevel(Enum):
    O0 = 0  # No optimization
    O1 = 1  # Basic: constant folding, dead code
    O2 = 2  # Standard: + strength reduction, CSE
    O3 = 3  # Aggressive: + pipeline fusion, TCO


# --- Constant Folding --------------------------------------------------

# Operators that can be folded at compile time
FOLDABLE_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b if b != 0 else None,
    "//": lambda a, b: a // b if b != 0 else None,
    "%": lambda a, b: a % b if b != 0 else None,
    "**": lambda a, b: a ** b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
}

FOLDABLE_UNARY = {
    "-": lambda a: -a,
    "not": lambda a: not a,
    "!": lambda a: not a,
}

# Built-in pure functions that can be folded
PURE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "round": round,
}

PURE_MATH = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "floor": math.floor,
    "ceil": math.ceil,
}


@dataclass
class FoldResult:
    """Result of a constant-folding attempt."""
    folded: bool
    value: Any = None
    folded_count: int = 0


def try_fold_binary(op: str, left: Any, right: Any) -> FoldResult:
    """Attempt to fold a binary operation on two constants."""
    if op not in FOLDABLE_OPS:
        return FoldResult(folded=False)
    if not isinstance(left, (int, float, bool, str)):
        return FoldResult(folded=False)
    if not isinstance(right, (int, float, bool, str)):
        return FoldResult(folded=False)

    try:
        result = FOLDABLE_OPS[op](left, right)
        if result is None:
            return FoldResult(folded=False)
        return FoldResult(folded=True, value=result, folded_count=1)
    except (ArithmeticError, TypeError, ValueError):
        return FoldResult(folded=False)


def try_fold_unary(op: str, operand: Any) -> FoldResult:
    """Attempt to fold a unary operation on a constant."""
    if op not in FOLDABLE_UNARY:
        return FoldResult(folded=False)
    if not isinstance(operand, (int, float, bool)):
        return FoldResult(folded=False)

    try:
        result = FOLDABLE_UNARY[op](operand)
        return FoldResult(folded=True, value=result, folded_count=1)
    except (ArithmeticError, TypeError):
        return FoldResult(folded=False)


def try_fold_call(fn_name: str, args: List[Any]) -> FoldResult:
    """Attempt to fold a pure function call on constant arguments."""
    if fn_name in PURE_BUILTINS:
        fn = PURE_BUILTINS[fn_name]
    elif fn_name in PURE_MATH:
        fn = PURE_MATH[fn_name]
    else:
        return FoldResult(folded=False)

    # All arguments must be constants
    if not all(isinstance(a, (int, float, bool, str, list, tuple)) for a in args):
        return FoldResult(folded=False)

    try:
        result = fn(*args)
        return FoldResult(folded=True, value=result, folded_count=1)
    except Exception:
        return FoldResult(folded=False)


# --- Dead Code Elimination ---------------------------------------------

@dataclass
class DCEResult:
    """Result of dead code elimination."""
    eliminated: List[str] = field(default_factory=list)
    count: int = 0


def find_dead_variables(
    defined: Set[str],
    used: Set[str],
    protected: Optional[Set[str]] = None,
) -> Set[str]:
    """
    Find variables that are defined but never used.

    Args:
        defined: Set of variable names that are assigned
        used: Set of variable names that are read
        protected: Set of names that should never be eliminated (e.g., exports)
    """
    protected = protected or set()
    dead = defined - used - protected

    # Never eliminate special names
    special = {"_", "__", "self", "this", "main", "init", "__init__"}
    dead -= special

    return dead


def find_unreachable_after_return(statements: List[Any]) -> List[int]:
    """
    Find statement indices that come after an unconditional return/throw.
    Returns indices of unreachable statements.
    """
    unreachable = []
    found_terminator = False

    for i, stmt in enumerate(statements):
        if found_terminator:
            unreachable.append(i)
            continue

        # Check if this statement is a terminator
        stmt_type = type(stmt).__name__
        if stmt_type in ("ReturnStmt", "ThrowStmt"):
            found_terminator = True

    return unreachable


# --- Dead Branch Elimination -------------------------------------------

@dataclass
class DeadBranchResult:
    """Result of dead branch elimination."""
    branches_eliminated: int = 0
    conditions_simplified: int = 0


def evaluate_constant_condition(condition: Any) -> Optional[bool]:
    """
    Try to statically evaluate a condition to True or False.

    Returns True/False if the condition is statically known,
    or None if it cannot be determined.
    """
    if isinstance(condition, bool):
        return condition

    # Integer 0 is falsy, anything else truthy
    if isinstance(condition, int):
        return condition != 0

    # String: empty is falsy, non-empty truthy
    if isinstance(condition, str):
        return len(condition) > 0

    # None / null is falsy
    if condition is None:
        return False

    return None


def analyze_dead_branches(stmts: List[Any]) -> DeadBranchResult:
    """
    Analyze a statement list for dead branches (if-else with constant
    conditions).  Returns counts of branches that can be eliminated.

    An ``if true { A } else { B }`` can be replaced with just ``A``.
    An ``if false { A } else { B }`` can be replaced with just ``B``.
    """
    result = DeadBranchResult()

    for stmt in stmts:
        stype = type(stmt).__name__
        if stype == "IfStmt" and hasattr(stmt, "condition"):
            cond_type = type(stmt.condition).__name__
            if cond_type in ("BoolLiteral", "IntLiteral", "Literal"):
                val = getattr(stmt.condition, "value", None)
                static = evaluate_constant_condition(val)
                if static is not None:
                    result.branches_eliminated += 1
                    result.conditions_simplified += 1

    return result


def simplify_branch(condition_value: bool,
                    then_body: List[Any],
                    else_body: Optional[List[Any]]) -> List[Any]:
    """
    Given a statically-known condition, return the surviving branch.
    """
    if condition_value:
        return then_body
    else:
        return else_body if else_body else []


# --- Algebraic Simplification ------------------------------------------

@dataclass
class AlgebraicSimplification:
    """An algebraic identity that simplifies an expression."""
    pattern: str
    result: str
    description: str


ALGEBRAIC_IDENTITIES: List[AlgebraicSimplification] = [
    # Additive identities
    AlgebraicSimplification("x - x", "0", "Subtraction of self"),
    AlgebraicSimplification("x + (-x)", "0", "Addition with negation"),

    # Multiplicative identities
    AlgebraicSimplification("x / x", "1", "Division by self (guard x != 0)"),
    AlgebraicSimplification("x % x", "0", "Modulo by self (guard x != 0)"),

    # Bitwise identities
    AlgebraicSimplification("x & 0", "0", "AND with zero"),
    AlgebraicSimplification("x | 0", "x", "OR with zero"),
    AlgebraicSimplification("x ^ 0", "x", "XOR with zero"),
    AlgebraicSimplification("x & x", "x", "AND with self"),
    AlgebraicSimplification("x | x", "x", "OR with self"),
    AlgebraicSimplification("x ^ x", "0", "XOR with self"),

    # Shift identities
    AlgebraicSimplification("x << 0", "x", "Shift by zero"),
    AlgebraicSimplification("x >> 0", "x", "Shift by zero"),

    # Double negation
    AlgebraicSimplification("not not x", "x", "Double negation"),
    AlgebraicSimplification("-(-x)", "x", "Double arithmetic negation"),

    # Boolean identities
    AlgebraicSimplification("x and true", "x", "AND with true"),
    AlgebraicSimplification("x and false", "false", "AND with false"),
    AlgebraicSimplification("x or true", "true", "OR with true"),
    AlgebraicSimplification("x or false", "x", "OR with false"),
]


def apply_algebraic_simplification(
    op: str, left: Any, right: Any,
    same_operand: bool = False,
) -> Optional[Tuple[str, Any]]:
    """
    Try to apply algebraic simplification.

    Args:
        op: The binary operator
        left: Left operand (value or expression)
        right: Right operand (value or expression)
        same_operand: True if left and right refer to the same variable

    Returns:
        (result_kind, value) or None.
        result_kind is 'const' or 'identity'.
    """
    # x - x  →  0
    if op == "-" and same_operand:
        return ("const", 0)

    # x / x  →  1  (when x != 0)
    if op == "/" and same_operand:
        return ("const", 1)

    # x % x  →  0  (when x != 0)
    if op == "%" and same_operand:
        return ("const", 0)

    # x ^ x  →  0
    if op in ("^", "xor") and same_operand:
        return ("const", 0)

    # x & x  →  x
    if op in ("&", "and") and same_operand:
        return ("identity", left)

    # x | x  →  x
    if op in ("|", "or") and same_operand:
        return ("identity", left)

    # Bitwise with zero
    if op == "&" and (right == 0 or left == 0):
        return ("const", 0)
    if op == "|" and right == 0:
        return ("identity", left)
    if op == "|" and left == 0:
        return ("identity", right)
    if op in ("^", "xor") and right == 0:
        return ("identity", left)
    if op in ("^", "xor") and left == 0:
        return ("identity", right)

    # Shift by zero
    if op in ("<<", ">>") and right == 0:
        return ("identity", left)

    # Boolean with constants
    if op == "and" and right is False:
        return ("const", False)
    if op == "and" and right is True:
        return ("identity", left)
    if op == "or" and right is True:
        return ("const", True)
    if op == "or" and right is False:
        return ("identity", left)

    return None


# --- Function Inlining Analysis ----------------------------------------

@dataclass
class InlineCandidate:
    """A function identified as suitable for inlining."""
    fn_name: str
    body_size: int          # number of statements in body
    param_count: int        # number of parameters
    call_count: int         # how many times it's called
    has_side_effects: bool  # calls impure functions (println, etc.)
    is_recursive: bool      # calls itself
    score: float            # inlining benefit score (higher = better)

    @property
    def should_inline(self) -> bool:
        """Determine if inlining is beneficial."""
        if self.is_recursive:
            return False
        if self.body_size > 10:
            return False
        if self.call_count < 1:
            return False
        return self.score > 0.5


SIDE_EFFECT_FUNCTIONS = frozenset({
    "println", "print", "eprintln", "eprint",
    "write_file", "read_file", "append_file",
    "input", "sleep", "exit",
    "send", "recv", "connect",
})


def analyze_inline_candidate(
    fn_name: str,
    param_count: int,
    body_stmts: List[Any],
    call_count: int,
    called_functions: Set[str],
) -> InlineCandidate:
    """
    Analyze whether a function is a good candidate for inlining.

    Scoring heuristic:
      - Small body → higher score
      - More call sites → higher score (amortizes analysis cost)
      - Pure functions → higher score
      - Many parameters → lower score (register pressure)
    """
    body_size = len(body_stmts)
    has_side_effects = bool(called_functions & SIDE_EFFECT_FUNCTIONS)
    is_recursive = fn_name in called_functions

    # Score: higher is better for inlining
    score = 0.0

    # Size component (smaller = better)
    if body_size <= 1:
        score += 2.0
    elif body_size <= 3:
        score += 1.5
    elif body_size <= 5:
        score += 1.0
    elif body_size <= 10:
        score += 0.3
    else:
        score -= 1.0

    # Call frequency component
    if call_count >= 3:
        score += 1.0
    elif call_count >= 2:
        score += 0.5

    # Purity bonus
    if not has_side_effects:
        score += 0.5

    # Parameter penalty
    if param_count > 4:
        score -= 0.5

    # Recursive penalty (never inline recursive)
    if is_recursive:
        score -= 10.0

    return InlineCandidate(
        fn_name=fn_name,
        body_size=body_size,
        param_count=param_count,
        call_count=call_count,
        has_side_effects=has_side_effects,
        is_recursive=is_recursive,
        score=score,
    )


# --- Strength Reduction ------------------------------------------------

@dataclass
class StrengthReduction:
    """A strength reduction rule: replace expensive op with cheaper one."""
    pattern: str
    replacement: str
    condition: str = ""


STRENGTH_REDUCTIONS = [
    # Multiply by power of 2 → shift
    StrengthReduction("x * 2", "x << 1", "x is integer"),
    StrengthReduction("x * 4", "x << 2", "x is integer"),
    StrengthReduction("x * 8", "x << 3", "x is integer"),
    StrengthReduction("x * 16", "x << 4", "x is integer"),
    # Divide by power of 2 → shift
    StrengthReduction("x / 2", "x >> 1", "x is integer"),
    StrengthReduction("x / 4", "x >> 2", "x is integer"),
    # Modulo by power of 2 → bitwise and
    StrengthReduction("x % 2", "x & 1", "x is integer"),
    StrengthReduction("x % 4", "x & 3", "x is integer"),
    StrengthReduction("x % 8", "x & 7", "x is integer"),
    # Identity operations
    StrengthReduction("x * 1", "x"),
    StrengthReduction("x + 0", "x"),
    StrengthReduction("x - 0", "x"),
    StrengthReduction("x * 0", "0"),
    StrengthReduction("x ** 1", "x"),
    StrengthReduction("x ** 0", "1"),
    StrengthReduction("x ** 2", "x * x", "faster than pow"),
]


def apply_strength_reduction(op: str, left: Any, right: Any) -> Optional[Tuple[str, Any, Any]]:
    """
    Try to apply strength reduction to a binary operation.
    Returns (new_op, new_left, new_right) or None.
    """
    # x * 0 = 0
    if op == "*" and right == 0:
        return ("const", 0, None)
    if op == "*" and left == 0:
        return ("const", 0, None)

    # x * 1 = x
    if op == "*" and right == 1:
        return ("identity", left, None)
    if op == "*" and left == 1:
        return ("identity", right, None)

    # x + 0 = x
    if op == "+" and right == 0:
        return ("identity", left, None)
    if op == "+" and left == 0:
        return ("identity", right, None)

    # x - 0 = x
    if op == "-" and right == 0:
        return ("identity", left, None)

    # x ** 0 = 1
    if op == "**" and right == 0:
        return ("const", 1, None)

    # x ** 1 = x
    if op == "**" and right == 1:
        return ("identity", left, None)

    # x ** 2 = x * x (faster)
    if op == "**" and right == 2:
        return ("*", left, left)

    # Integer multiply by power of 2 → shift
    if op == "*" and isinstance(right, int) and right > 0 and (right & (right - 1)) == 0:
        shift = right.bit_length() - 1
        return ("<<", left, shift)

    return None


# --- Common Subexpression Elimination ----------------------------------

@dataclass
class CSEEntry:
    """A cached common subexpression."""
    expression: str
    temp_var: str
    uses: int = 0


class CSETracker:
    """Track common subexpressions for elimination."""

    def __init__(self):
        self._expressions: Dict[str, CSEEntry] = {}
        self._counter = 0

    def _next_temp(self) -> str:
        self._counter += 1
        return f"__cse_{self._counter}"

    def register(self, expr_key: str) -> Optional[str]:
        """
        Register an expression. If seen before, return the temp variable name.
        If new, return None (not worth extracting yet).
        """
        if expr_key in self._expressions:
            entry = self._expressions[expr_key]
            entry.uses += 1
            return entry.temp_var
        else:
            temp = self._next_temp()
            self._expressions[expr_key] = CSEEntry(
                expression=expr_key,
                temp_var=temp,
                uses=1,
            )
            return None

    def get_reusable(self) -> List[CSEEntry]:
        """Get expressions that appear more than once (worth extracting)."""
        return [e for e in self._expressions.values() if e.uses > 1]


# --- Tail Call Optimization Detection ----------------------------------

@dataclass
class TCOCandidate:
    """A function identified as a tail-call optimization candidate."""
    fn_name: str
    recursive_calls: int
    is_tail_recursive: bool
    can_be_loopified: bool


def detect_tail_recursion(fn_name: str, body_stmts: List[Any]) -> TCOCandidate:
    """
    Analyze a function body to determine if it's tail-recursive.

    A function is tail-recursive if:
    1. It calls itself
    2. The recursive call is in tail position (last expression before return)
    3. No operation is performed on the result of the recursive call
    """
    recursive_calls = 0
    is_tail = True
    can_loop = True

    def check_stmt(stmt, in_tail_position: bool) -> None:
        nonlocal recursive_calls, is_tail, can_loop

        stmt_type = type(stmt).__name__

        if stmt_type == "ReturnStmt":
            # Check if return value is a call to fn_name
            if hasattr(stmt, "value") and stmt.value is not None:
                val_type = type(stmt.value).__name__
                if val_type == "CallExpr":
                    if hasattr(stmt.value, "callee"):
                        callee = stmt.value.callee
                        if hasattr(callee, "name") and callee.name == fn_name:
                            recursive_calls += 1
                            if not in_tail_position:
                                is_tail = False
                        # Binary op on recursive result = not tail
                elif val_type == "BinaryExpr":
                    is_tail = False

        elif stmt_type == "IfStmt":
            # Both branches could contain tail calls
            if hasattr(stmt, "then_body"):
                for s in getattr(stmt, "then_body", []):
                    check_stmt(s, in_tail_position)
            if hasattr(stmt, "else_body"):
                for s in getattr(stmt, "else_body", []):
                    check_stmt(s, in_tail_position)

    for i, stmt in enumerate(body_stmts):
        is_last = (i == len(body_stmts) - 1)
        check_stmt(stmt, in_tail_position=is_last)

    return TCOCandidate(
        fn_name=fn_name,
        recursive_calls=recursive_calls,
        is_tail_recursive=is_tail and recursive_calls > 0,
        can_be_loopified=is_tail and recursive_calls > 0 and can_loop,
    )


# --- Pipeline Fusion ---------------------------------------------------

def can_fuse_pipeline(stages: List[str]) -> bool:
    """
    Determine if a pipeline's stages can be fused into a single pass.

    Fusable: map |> map, map |> filter, filter |> map
    Not fusable: sort |> map, reduce |> anything
    """
    fusable_pairs = {
        ("map", "map"),
        ("map", "filter"),
        ("filter", "map"),
        ("filter", "filter"),
    }

    for i in range(len(stages) - 1):
        if (stages[i], stages[i + 1]) not in fusable_pairs:
            return False

    return len(stages) >= 2


def describe_fusion(stages: List[str]) -> str:
    """Describe how a pipeline would be fused."""
    if not can_fuse_pipeline(stages):
        return "Cannot fuse: incompatible stages"

    # map |> map = single map with composed function
    # map |> filter = single loop with transform + predicate
    # filter |> map = single loop with predicate + transform
    # filter |> filter = single filter with combined predicate

    if all(s == "map" for s in stages):
        return f"Fuse {len(stages)} map stages into single composed map"
    elif all(s == "filter" for s in stages):
        return f"Fuse {len(stages)} filter stages into single combined filter"
    else:
        return f"Fuse {len(stages)} stages into single loop with transform+predicate"


# --- Optimization Report -----------------------------------------------

@dataclass
class OptimizationReport:
    """Summary of optimizations applied."""
    level: OptLevel
    constants_folded: int = 0
    dead_vars_eliminated: int = 0
    unreachable_stmts_removed: int = 0
    dead_branches_eliminated: int = 0
    strength_reductions: int = 0
    algebraic_simplifications: int = 0
    cse_extractions: int = 0
    tco_candidates: List[str] = field(default_factory=list)
    pipeline_fusions: int = 0
    inline_candidates: List[str] = field(default_factory=list)

    @property
    def total_optimizations(self) -> int:
        return (
            self.constants_folded
            + self.dead_vars_eliminated
            + self.unreachable_stmts_removed
            + self.dead_branches_eliminated
            + self.strength_reductions
            + self.algebraic_simplifications
            + self.cse_extractions
            + len(self.tco_candidates)
            + self.pipeline_fusions
            + len(self.inline_candidates)
        )

    def summary(self) -> str:
        lines = [
            f"Optimization Report (level: {self.level.name})",
            f"  Constants folded:          {self.constants_folded}",
            f"  Dead variables eliminated: {self.dead_vars_eliminated}",
            f"  Unreachable code removed:  {self.unreachable_stmts_removed}",
            f"  Dead branches eliminated:  {self.dead_branches_eliminated}",
            f"  Strength reductions:       {self.strength_reductions}",
            f"  Algebraic simplifications: {self.algebraic_simplifications}",
            f"  CSE extractions:           {self.cse_extractions}",
            f"  TCO candidates:            {len(self.tco_candidates)}",
            f"  Pipeline fusions:          {self.pipeline_fusions}",
            f"  Inline candidates:         {len(self.inline_candidates)}",
            f"  Total optimizations:       {self.total_optimizations}",
        ]
        if self.tco_candidates:
            lines.append(f"  TCO functions: {', '.join(self.tco_candidates)}")
        if self.inline_candidates:
            lines.append(f"  Inline functions: {', '.join(self.inline_candidates)}")
        return "\n".join(lines)


# --- Main Optimizer -----------------------------------------------------

class Optimizer:
    """
    The LATERALUS code optimizer.

    Applies optimization passes based on the selected optimization level.
    Works on IR-level representations.
    """

    def __init__(self, level: OptLevel = OptLevel.O1):
        self.level = level
        self.report = OptimizationReport(level=level)
        self._cse = CSETracker()

    def optimize_constant(self, op: str, left: Any, right: Any) -> Tuple[bool, Any]:
        """Try to constant-fold a binary expression."""
        if self.level.value < OptLevel.O1.value:
            return False, None

        result = try_fold_binary(op, left, right)
        if result.folded:
            self.report.constants_folded += result.folded_count
        return result.folded, result.value

    def optimize_unary(self, op: str, operand: Any) -> Tuple[bool, Any]:
        """Try to constant-fold a unary expression."""
        if self.level.value < OptLevel.O1.value:
            return False, None

        result = try_fold_unary(op, operand)
        if result.folded:
            self.report.constants_folded += result.folded_count
        return result.folded, result.value

    def optimize_call(self, fn_name: str, args: List[Any]) -> Tuple[bool, Any]:
        """Try to fold a pure function call."""
        if self.level.value < OptLevel.O1.value:
            return False, None

        result = try_fold_call(fn_name, args)
        if result.folded:
            self.report.constants_folded += result.folded_count
        return result.folded, result.value

    def optimize_strength(self, op: str, left: Any, right: Any) -> Optional[Tuple[str, Any, Any]]:
        """Try strength reduction on a binary operation."""
        if self.level.value < OptLevel.O2.value:
            return None

        result = apply_strength_reduction(op, left, right)
        if result is not None:
            self.report.strength_reductions += 1
        return result

    def track_expression(self, expr_key: str) -> Optional[str]:
        """Track an expression for CSE. Returns temp var name if reusable."""
        if self.level.value < OptLevel.O2.value:
            return None

        return self._cse.register(expr_key)

    def check_tail_recursion(self, fn_name: str, body: List[Any]) -> TCOCandidate:
        """Check if a function is tail-recursive."""
        candidate = detect_tail_recursion(fn_name, body)
        if candidate.is_tail_recursive:
            self.report.tco_candidates.append(fn_name)
        return candidate

    def check_pipeline_fusion(self, stages: List[str]) -> bool:
        """Check if pipeline stages can be fused."""
        if self.level.value < OptLevel.O3.value:
            return False

        if can_fuse_pipeline(stages):
            self.report.pipeline_fusions += 1
            return True
        return False

    def eliminate_dead_branches(self, stmts: List[Any]) -> DeadBranchResult:
        """Analyze and count dead branches in a statement list."""
        if self.level.value < OptLevel.O1.value:
            return DeadBranchResult()

        result = analyze_dead_branches(stmts)
        self.report.dead_branches_eliminated += result.branches_eliminated
        return result

    def optimize_algebraic(
        self, op: str, left: Any, right: Any, same_operand: bool = False
    ) -> Optional[Tuple[str, Any]]:
        """Try algebraic simplification on a binary expression."""
        if self.level.value < OptLevel.O2.value:
            return None

        result = apply_algebraic_simplification(op, left, right, same_operand)
        if result is not None:
            self.report.algebraic_simplifications += 1
        return result

    def analyze_inlining(
        self,
        fn_name: str,
        param_count: int,
        body_stmts: List[Any],
        call_count: int,
        called_functions: Set[str],
    ) -> InlineCandidate:
        """Analyze whether a function should be inlined."""
        if self.level.value < OptLevel.O3.value:
            return InlineCandidate(
                fn_name=fn_name, body_size=len(body_stmts),
                param_count=param_count, call_count=call_count,
                has_side_effects=False, is_recursive=False, score=0.0,
            )

        candidate = analyze_inline_candidate(
            fn_name, param_count, body_stmts, call_count, called_functions,
        )
        if candidate.should_inline:
            self.report.inline_candidates.append(fn_name)
        return candidate

    def finalize(self) -> OptimizationReport:
        """Finalize optimization and return report."""
        # Count CSE extractions
        self.report.cse_extractions = len(self._cse.get_reusable())
        return self.report
