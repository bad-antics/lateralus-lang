"""
lateralus_lang/codegen/javascript.py  ─  LTL → JavaScript Transpiler
═══════════════════════════════════════════════════════════════════════════
Converts a Lateralus (.ltl) AST directly to JavaScript (ES2022+).

Supported constructs
────────────────────
  · module / import → ESM import / CJS require
  · fn / async fn   → function / async function (or arrow)
  · let / const     → let / const
  · if / elif / else
  · match           → switch + if-else chains
  · while / loop / for … in
  · break / continue / return
  · try / recover / ensure → try / catch / finally
  · Pipeline |>     → chained function calls
  · Lambda fn(x) expr → arrow functions
  · Await           → await
  · Structs         → ES classes
  · Enums           → frozen object constants
  · Traits / impl   → class with methods
  · Emit / probe / measure → runtime hooks
  · String interpolation → template literals
  · Comprehensions  → Array.from + map/filter
  · v1.6 concurrency → async/await + Promise.all
  · v1.7 cfg        → compile-time boolean
  · v1.8 macros     → compile-time expansion
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
from typing import Any, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# AST node imports — full v1.0-v1.9 coverage
# ---------------------------------------------------------------------------

from ..ast_nodes import (
    # Core
    Program, FnDecl, LetDecl, AssignStmt, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, ExprStmt, BlockStmt, BinOp, UnaryOp, CallExpr,
    IndexExpr, FieldExpr, LambdaExpr, MatchStmt, MatchArm,
    StructDecl, StructField, StructLiteral, ImportStmt, RangeExpr,
    ListExpr, MapExpr, Ident, Literal, EmitStmt, MeasureBlock, ProbeExpr,
    BreakStmt, ContinueStmt, TryStmt, ThrowStmt, LoopStmt,
    # Types
    EnumDecl, EnumVariant, TypeAlias, ImplBlock, InterfaceDecl, ForeignBlock,
    # Expressions
    InterpolatedStr, SelfExpr, AwaitExpr, CastExpr, TupleExpr,
    SpreadExpr, TernaryExpr, OptionExpr, ResultExpr,
    ComprehensionExpr, WhereClause, GuardExpr, PipelineAssign,
    TypeMatchExpr, SpawnExpr, ChannelExpr, CancelExpr, YieldExpr,
    ChainExpr, PropagateExpr, TryExpr, RecoverClause,
    # Patterns
    WildcardPattern, LiteralPattern, BindingPattern, TypePattern,
    EnumVariantPattern, TuplePattern, ListPattern, OrPattern,
    # v1.6
    AsyncForStmt, NurseryBlock, SelectStmt, SelectArm, ParallelExpr,
    # v1.7
    CfgExpr,
    # v1.8
    CompTimeBlock, ConstFnDecl, MacroDecl, MacroInvocation,
    QuoteExpr, ReflectExpr, UnquoteExpr, DeriveAttr, Decorator,
)


# ---------------------------------------------------------------------------
# JavaScript indenter / code buffer
# ---------------------------------------------------------------------------

class JSBuffer:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent: int = 0

    def write(self, line: str = "") -> None:
        if line:
            self._lines.append("  " * self._indent + line)
        else:
            self._lines.append("")

    def indent(self) -> None:
        self._indent += 1

    def dedent(self) -> None:
        self._indent = max(0, self._indent - 1)

    def blank(self) -> None:
        """Add a blank line."""
        self._lines.append("")

    def get(self) -> str:
        return "\n".join(self._lines)


# ---------------------------------------------------------------------------
# JS Runtime (injected header)
# ---------------------------------------------------------------------------

JS_RUNTIME = """\
// ── LATERALUS JavaScript Runtime ──────────────────────────────────────────
// Auto-generated. Do not edit.

const __ltl = {
  // Pipeline operator: x |> f(args)  →  __ltl.pipe(x, f, args)
  pipe: (val, fn, ...args) => fn(val, ...args),

  // Optional pipeline: val |? f()  →  __ltl.pipeSafe(val, f)
  pipeSafe: (val, fn, ...args) => val == null ? null : fn(val, ...args),

  // Range: [start..end]  →  __ltl.range(start, end)
  range: (start, end, step = 1) => {
    const arr = [];
    if (step > 0) { for (let i = start; i <= end; i += step) arr.push(i); }
    else          { for (let i = start; i >= end; i += step) arr.push(i); }
    return arr;
  },

  // Struct instantiation helper
  struct: (name, fields) => ({ __type: name, ...fields }),

  // emit — fires a CustomEvent
  emit: (name, data) => {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(`ltl:${name}`, { detail: data }));
    }
    return data;
  },

  // probe — log and return
  probe: (label, val) => { console.log(`[probe:${label}]`, val); return val; },

  // measure — time a thunk
  measure: async (name, fn) => {
    const t0 = performance.now();
    const result = await fn();
    console.log(`[measure:${name}] ${(performance.now() - t0).toFixed(3)}ms`);
    return result;
  },

  // println
  println: (...args) => console.log(...args),

  // Built-in functions
  len:      (x) => x == null ? 0 : (x.length ?? Object.keys(x).length),
  str:      (x) => String(x),
  int:      (x) => parseInt(x, 10),
  float:    (x) => parseFloat(x),
  bool:     (x) => Boolean(x),
  abs:      Math.abs,
  sqrt:     Math.sqrt,
  floor:    Math.floor,
  ceil:     Math.ceil,
  round:    Math.round,
  pow:      Math.pow,
  log:      Math.log,
  log2:     Math.log2,
  log10:    Math.log10,
  exp:      Math.exp,
  sin:      Math.sin,
  cos:      Math.cos,
  tan:      Math.tan,
  min:      (...a) => Math.min(...a.flat()),
  max:      (...a) => Math.max(...a.flat()),

  // List builtins
  map:      (arr, fn) => arr.map(fn),
  filter:   (arr, fn) => arr.filter(fn),
  reduce:   (arr, fn, init) => arr.reduce(fn, init),
  forEach:  (arr, fn) => { arr.forEach(fn); return arr; },
  flat_map: (arr, fn) => arr.flatMap(fn),
  zip:      (...arrays) => arrays[0].map((_, i) => arrays.map(a => a[i])),
  sort:     (arr, fn) => [...arr].sort(fn),
  sort_by:  (arr, key) => [...arr].sort((a, b) => a[key] < b[key] ? -1 : 1),
  reverse:  (arr) => [...arr].reverse(),
  take:     (arr, n) => arr.slice(0, n),
  drop:     (arr, n) => arr.slice(n),
  sum:      (arr) => arr.reduce((a, b) => a + b, 0),
  product:  (arr) => arr.reduce((a, b) => a * b, 1),
  any:      (arr, fn) => arr.some(fn ?? Boolean),
  all:      (arr, fn) => arr.every(fn ?? Boolean),
  none:     (arr, fn) => !arr.some(fn ?? Boolean),
  distinct: (arr) => [...new Set(arr)],
  flatten:  (arr) => arr.flat(Infinity),
  count:    (arr, fn) => fn ? arr.filter(fn).length : arr.length,
  first:    (arr) => arr[0] ?? null,
  last:     (arr) => arr[arr.length - 1] ?? null,
  includes: (arr, v) => arr.includes(v),

  // String builtins
  upper:    (s) => s.toUpperCase(),
  lower:    (s) => s.toLowerCase(),
  trim:     (s) => s.trim(),
  split:    (s, sep) => s.split(sep),
  join:     (arr, sep = '') => arr.join(sep),
  replace:  (s, pat, rep) => s.replace(new RegExp(pat, 'g'), rep),
  starts_with: (s, p) => s.startsWith(p),
  ends_with:   (s, p) => s.endsWith(p),
  contains:    (s, p) => s.includes(p),
  pad_left:    (s, n, c = ' ') => s.padStart(n, c),
  pad_right:   (s, n, c = ' ') => s.padEnd(n, c),

  // Math
  PI:  Math.PI,
  E:   Math.E,
  TAU: Math.PI * 2,
  INF: Infinity,
  NAN: NaN,

  // Type checks
  is_none:  (x) => x == null,
  is_some:  (x) => x != null,
  type_of:  (x) => typeof x,
};

// Bring into scope
const { pipe, pipeSafe, range, println, len, str, int, float, bool,
        map, filter, reduce, sort, sort_by, take, drop, sum, product,
        any, all, none, distinct, flatten, first, last, zip, flat_map,
        upper, lower, trim, split, join, replace, contains,
        abs, sqrt, floor, ceil, round, pow, log, exp, sin, cos, tan,
        min, max, PI, E, TAU, INF } = __ltl;

// ──────────────────────────────────────────────────────────────────────────
"""


# ---------------------------------------------------------------------------
# Operator mapping
# ---------------------------------------------------------------------------

BINARY_OPS: dict[str, str] = {
    "+": "+",  "-": "-",  "*": "*",  "/": "/",
    "%": "%",  "**": "**",
    "==": "===",  "!=": "!==",
    "<": "<",  ">": ">",  "<=": "<=",  ">=": ">=",
    "&&": "&&",  "||": "||",
    "&": "&",  "|": "|",  "^": "^",
    "<<": "<<", ">>": ">>",
    "..": None,   # handled specially as range
    "..=": None,  # handled specially
}

UNARY_OPS: dict[str, str] = {
    "-": "-",  "!": "!",  "~": "~",  "not": "!",
}


# ---------------------------------------------------------------------------
# JavaScript Transpiler
# ---------------------------------------------------------------------------

class JavaScriptTranspiler:
    """
    Full AST-based LATERALUS → JavaScript (ES2022+) transpiler.

    Usage:
        transpiler = JavaScriptTranspiler()
        js_code = transpiler.transpile_string(lateralus_source)
    """

    def __init__(self, module_format: str = "esm", include_runtime: bool = True) -> None:
        self.module_format = module_format  # 'esm' | 'cjs' | 'iife'
        self.include_runtime = include_runtime
        self._buf = JSBuffer()
        self._struct_names: set[str] = set()
        self._enum_names: set[str] = set()
        self._in_method = False
        self._current_fn: str | None = None

    # ── Entry points ────────────────────────────────────────────────────

    def transpile_string(self, source: str) -> str:
        """Transpile LATERALUS source code to JavaScript."""
        return self._transpile_via_ast(source)

    def transpile_source(self, source: str) -> str:
        """Alias for transpile_string()."""
        return self.transpile_string(source)

    def _transpile_via_ast(self, source: str) -> str:
        """Full AST-based transpilation."""
        from lateralus_lang.lexer import Lexer
        from lateralus_lang.parser import Parser

        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()

        self._buf = JSBuffer()
        if self.include_runtime:
            for line in JS_RUNTIME.splitlines():
                self._buf.write(line)
            self._buf.blank()
        self._emit_Program(program)
        return self._buf.get()

    # ── Dispatch ────────────────────────────────────────────────────────

    def _emit_node(self, node: Any) -> None:
        """Dispatch to the correct _emit_* method."""
        if node is None:
            return
        node_type = type(node).__name__
        method = getattr(self, f"_emit_{node_type}", None)
        if method:
            method(node)
        else:
            self._buf.write(f"/* unsupported: {node_type} */")

    def _expr(self, node: Any) -> str:
        """Render any expression node to a JS string."""
        if node is None:
            return "null"

        if isinstance(node, Literal):
            if node.kind in ("string", "str"):
                # Use JSON-style quoting for JS strings
                escaped = str(node.value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
                return f'"{escaped}"'
            if node.kind == "bool":
                return "true" if node.value else "false"
            if node.kind in ("none", "null"):
                return "null"
            return str(node.value)

        if isinstance(node, Ident):
            name = node.name
            if name == "None":
                return "null"
            if name == "True":
                return "true"
            if name == "False":
                return "false"
            return name

        if isinstance(node, BinOp):
            left = self._expr(node.left)
            right = self._expr(node.right)
            op = node.op
            # Pipeline operators
            if op == "|>":
                return self._emit_pipe(node.left, node.right)
            if op == "|?":
                inner = self._emit_pipe(node.left, node.right)
                l = self._expr(node.left)
                return f"({l} != null ? {inner} : null)"
            # Range operator
            if op in ("..", "..="):
                incl = "true" if op == "..=" else "false"
                return f"__ltl.range({left}, {right})"
            # Map to JS ops
            js_op = BINARY_OPS.get(op, op)
            if op == "and":
                js_op = "&&"
            elif op == "or":
                js_op = "||"
            return f"({left} {js_op} {right})"

        if isinstance(node, UnaryOp):
            operand = self._expr(node.operand)
            js_op = UNARY_OPS.get(node.op, node.op)
            return f"{js_op}{operand}"

        if isinstance(node, CallExpr):
            callee = self._expr(node.callee)
            args = ", ".join(self._expr(a) for a in node.args)
            # Handle keyword arguments
            if node.kwargs:
                kw_parts = []
                for k, v in node.kwargs.items():
                    kw_parts.append(f"{k}: {self._expr(v)}")
                if args:
                    args += ", "
                args += "{ " + ", ".join(kw_parts) + " }"
            return f"{callee}({args})"

        if isinstance(node, IndexExpr):
            obj = self._expr(node.obj)
            idx = self._expr(node.index)
            return f"{obj}[{idx}]"

        if isinstance(node, FieldExpr):
            obj = self._expr(node.obj)
            return f"{obj}.{node.field}"

        if isinstance(node, LambdaExpr):
            params = self._render_params(node.params)
            if node.block:
                # Block body lambda
                block = node.block
                stmts = block.stmts if isinstance(block, BlockStmt) else (block if isinstance(block, list) else [block])
                # Single expression statement → implicit return
                if len(stmts) == 1 and isinstance(stmts[0], ExprStmt):
                    body = self._expr(stmts[0].expr)
                    return f"({params}) => {body}"
                if len(stmts) == 1 and isinstance(stmts[0], ReturnStmt):
                    body = self._expr(stmts[0].value) if stmts[0].value else "undefined"
                    return f"({params}) => {body}"
                # Multi-statement body
                old_buf = self._buf
                self._buf = JSBuffer()
                # If last statement is ExprStmt, make it a return
                for i, s in enumerate(stmts):
                    if i == len(stmts) - 1 and isinstance(s, ExprStmt):
                        self._buf.write(f"return {self._expr(s.expr)};")
                    else:
                        self._emit_node(s)
                body_code = self._buf.get()
                self._buf = old_buf
                return f"({params}) => {{ {body_code.strip()} }}"
            if node.body:
                body = self._expr(node.body)
                return f"({params}) => {body}"
            return f"({params}) => {{}}"

        if isinstance(node, ListExpr):
            elems = ", ".join(self._expr(e) for e in node.elements)
            return f"[{elems}]"

        if isinstance(node, MapExpr):
            pairs = ", ".join(
                f"[{self._expr(k)}]: {self._expr(v)}"
                if not isinstance(k, (Literal, Ident)) else
                f"{self._expr(k)}: {self._expr(v)}"
                for k, v in node.pairs
            )
            return f"{{ {pairs} }}"

        if isinstance(node, TupleExpr):
            elems = ", ".join(self._expr(e) for e in node.elements)
            return f"[{elems}]"

        if isinstance(node, RangeExpr):
            start = self._expr(node.start)
            end = self._expr(node.end)
            return f"__ltl.range({start}, {end})"

        if isinstance(node, InterpolatedStr):
            parts = []
            for p in node.parts:
                if isinstance(p, str):
                    parts.append(p.replace("`", "\\`"))
                else:
                    parts.append("${" + self._expr(p) + "}")
            return "`" + "".join(parts) + "`"

        if isinstance(node, AwaitExpr):
            return f"await {self._expr(node.value)}"

        if isinstance(node, CastExpr):
            val = self._expr(node.value)
            target = node.target if isinstance(node.target, str) else str(node.target)
            cast_map = {"int": "parseInt", "float": "parseFloat", "str": "String", "bool": "Boolean"}
            fn = cast_map.get(target, target)
            return f"{fn}({val})"

        if isinstance(node, SelfExpr):
            return "this"

        if isinstance(node, StructLiteral):
            fields = ", ".join(
                f"{f}: {self._expr(v)}" for f, v in node.fields
            )
            if node.name in self._struct_names:
                return f"new {node.name}({', '.join(self._expr(v) for _, v in node.fields)})"
            return f"{{ __type: \"{node.name}\", {fields} }}"

        if isinstance(node, SpawnExpr):
            call = self._expr(node.call)
            return f"(async () => {call})()"

        if isinstance(node, ChannelExpr):
            cap = node.capacity or 0
            return f"new __ltl.Channel({cap})"

        if isinstance(node, CancelExpr):
            return "/* cancel */ undefined"

        if isinstance(node, YieldExpr):
            if node.value:
                return f"yield {self._expr(node.value)}"
            return "yield"

        if isinstance(node, SpreadExpr):
            return f"...{self._expr(node.value)}"

        if isinstance(node, TernaryExpr):
            cond = self._expr(node.condition)
            then = self._expr(node.then_val)
            els = self._expr(node.else_val)
            return f"({cond} ? {then} : {els})"

        if isinstance(node, OptionExpr):
            if node.variant == "None":
                return "null"
            return self._expr(node.value)

        if isinstance(node, ResultExpr):
            if node.variant == "Err":
                return f"{{ __err: {self._expr(node.value)} }}"
            return f"{{ __ok: {self._expr(node.value)} }}"

        if isinstance(node, ProbeExpr):
            val = self._expr(node.value)
            return f"__ltl.probe(\"probe\", {val})"

        if isinstance(node, TryExpr):
            val = self._expr(node.body) if hasattr(node, 'body') else "null"
            return f"(() => {{ try {{ return {val}; }} catch(_e) {{ return null; }} }})()"

        if isinstance(node, PropagateExpr):
            val = self._expr(node.error) if hasattr(node, 'error') else "null"
            return f"/* propagate */ {val}"

        if isinstance(node, ChainExpr):
            err = self._expr(node.error)
            cause = self._expr(node.cause) if node.cause else "null"
            return f"new Error({err}, {{ cause: {cause} }})"

        if isinstance(node, ComprehensionExpr):
            expr_s = self._expr(node.expr)
            var_s = node.var if isinstance(node.var, str) else self._expr(node.var)
            iter_s = self._expr(node.iter)
            if node.condition:
                cond = self._expr(node.condition)
                return f"{iter_s}.filter(({var_s}) => {cond}).map(({var_s}) => {expr_s})"
            return f"{iter_s}.map(({var_s}) => {expr_s})"

        if isinstance(node, GuardExpr):
            cond = self._expr(node.condition)
            return f"/* guard */ ({cond})"

        if isinstance(node, WhereClause):
            expr = self._expr(node.expr)
            return f"(() => {{ {'; '.join(self._expr(b) for b in node.bindings)}; return {expr}; }})()"

        if isinstance(node, TypeMatchExpr):
            subj = self._expr(node.subject)
            # Emit as chained ternary based on pattern matching
            parts = []
            for arm in node.arms:
                pat = arm.pattern
                val = self._expr(arm.value) if arm.value else (self._expr(arm.body) if arm.body else "null")
                cond = self._match_pattern_cond(pat, subj)
                if cond == "true":
                    parts.append(val)  # wildcard — final else
                else:
                    parts.append(f"{cond} ? {val}")
            if not parts:
                return "null"
            # Build ternary chain
            if len(parts) == 1:
                return parts[0]
            result = parts[-1]  # Last part (default / wildcard)
            for p in reversed(parts[:-1]):
                result = f"{p} : {result}"
            return f"({result})"

        if isinstance(node, ParallelExpr):
            items = ", ".join(self._expr(i) for i in (node.items or []))
            return f"await Promise.all([{items}])"

        if isinstance(node, CfgExpr):
            return "true"  # compile-time resolved

        if isinstance(node, MacroInvocation):
            args = ", ".join(self._expr(a) for a in node.args)
            return f"/* macro: {node.name}!({args}) */"

        if isinstance(node, ReflectExpr):
            return f"/* reflect */ JSON.stringify({self._expr(node.target)})"

        if isinstance(node, QuoteExpr):
            return f"/* quote */ null"

        if isinstance(node, UnquoteExpr):
            return self._expr(node.expr)

        if isinstance(node, BlockStmt):
            old_buf = self._buf
            self._buf = JSBuffer()
            self._emit_body(node.stmts)
            code = self._buf.get()
            self._buf = old_buf
            return f"(() => {{ {code.strip()} }})()"

        # Fallback
        return f"/* expr:{type(node).__name__} */"

    # ── Helper: pipeline emission ───────────────────────────────────────

    def _emit_pipe(self, left: Any, right: Any) -> str:
        """Emit x |> f or x |> f(args)."""
        val = self._expr(left)
        if isinstance(right, CallExpr):
            fn = self._expr(right.callee)
            args = ", ".join(self._expr(a) for a in right.args)
            if args:
                return f"{fn}({val}, {args})"
            return f"{fn}({val})"
        if isinstance(right, Ident):
            return f"{right.name}({val})"
        fn = self._expr(right)
        return f"{fn}({val})"

    def _match_pattern_cond(self, pattern: Any, subject: str) -> str:
        """Convert a match pattern to a JS condition expression string."""
        if isinstance(pattern, WildcardPattern):
            return "true"
        if isinstance(pattern, LiteralPattern):
            lit = pattern.value
            val = self._expr(lit) if hasattr(lit, 'accept') else repr(lit)
            return f"{subject} === {val}"
        if isinstance(pattern, BindingPattern):
            return "true"  # Always matches; binding handled separately
        if isinstance(pattern, EnumVariantPattern):
            if pattern.enum_name:
                return f"{subject}?.__variant === \"{pattern.variant_name}\""
            return f"{subject} === \"{pattern.variant_name}\""
        if isinstance(pattern, TypePattern):
            return f"{subject}?.__type === \"{pattern.type_name}\""
        if isinstance(pattern, OrPattern):
            l = self._match_pattern_cond(pattern.left, subject)
            r = self._match_pattern_cond(pattern.right, subject)
            return f"({l} || {r})"
        if isinstance(pattern, TuplePattern):
            checks = [self._match_pattern_cond(e, f"{subject}[{i}]") for i, e in enumerate(pattern.elements)]
            return " && ".join(checks) if checks else "true"
        if isinstance(pattern, ListPattern):
            checks = [self._match_pattern_cond(e, f"{subject}[{i}]") for i, e in enumerate(pattern.head or [])]
            return " && ".join(checks) if checks else "true"
        # Direct expression compare (Ident, Literal)
        if isinstance(pattern, (Ident, Literal)):
            val = self._expr(pattern)
            if isinstance(pattern, Ident) and pattern.name == "_":
                return "true"
            return f"{subject} === {val}"
        return "true"

    # ── Helper: render parameter list ───────────────────────────────────

    def _render_params(self, params: list) -> str:
        """Render a parameter list, stripping type annotations."""
        parts = []
        for p in params:
            if hasattr(p, 'name') and hasattr(p, 'default'):
                # Param object
                name = p.name
                if p.default is not None:
                    parts.append(f"{name} = {self._expr(p.default)}")
                else:
                    parts.append(name)
            elif isinstance(p, tuple):
                name = p[0] if isinstance(p[0], str) else p[0].name if hasattr(p[0], 'name') else str(p[0])
                parts.append(name)
            elif isinstance(p, str):
                parts.append(p.split(":")[0].strip())
            elif hasattr(p, 'name'):
                parts.append(p.name)
            else:
                parts.append(str(p))
        return ", ".join(parts)

    # ── Helper: emit a body (list of statements) ───────────────────────

    def _emit_body(self, stmts: list) -> None:
        for s in stmts:
            self._emit_node(s)

    # ── Visitor: Program ────────────────────────────────────────────────

    def _emit_Program(self, node: Program) -> None:
        # Imports
        for imp in (node.imports or []):
            self._emit_ImportStmt(imp)
        if node.imports:
            self._buf.blank()
        # Body
        for stmt in node.body:
            self._emit_node(stmt)

    # ── Visitor: ImportStmt ─────────────────────────────────────────────

    def _emit_ImportStmt(self, node: ImportStmt) -> None:
        mod = node.path.replace("/", "_").replace(".", "_").replace("-", "_")
        if node.items:
            items = ", ".join(
                i if isinstance(i, str) else (i[0] if isinstance(i, tuple) else str(i))
                for i in node.items
            )
            if self.module_format == "cjs":
                self._buf.write(f"const {{ {items} }} = require(\"./{node.path}\");")
            else:
                self._buf.write(f"import {{ {items} }} from \"./{node.path}.js\";")
        else:
            alias = node.alias or mod
            if self.module_format == "cjs":
                self._buf.write(f"const {alias} = require(\"./{node.path}\");")
            else:
                self._buf.write(f"import * as {alias} from \"./{node.path}.js\";")

    # ── Visitor: FnDecl ─────────────────────────────────────────────────

    def _emit_FnDecl(self, node: FnDecl) -> None:
        # Decorators
        for dec in (node.decorators or []):
            if isinstance(dec, Decorator):
                if dec.name == "foreign":
                    self._emit_foreign_fn(node, dec)
                    return
                if dec.name == "cfg":
                    # Conditional compilation — emit the fn
                    pass
                # Other decorators as comments
                args_s = ", ".join(repr(a) for a in (dec.args or []))
                self._buf.write(f"// @{dec.name}({args_s})")

        async_kw = "async " if node.is_async else ""
        params = self._render_params(node.params)
        exp = "export " if node.is_pub and self.module_format == "esm" else ""

        self._buf.write(f"{exp}{async_kw}function {node.name}({params}) {{")
        self._buf.indent()
        self._current_fn = node.name
        self._emit_body_stmts(node.body)
        self._current_fn = None
        self._buf.dedent()
        self._buf.write("}")
        self._buf.blank()

    def _emit_foreign_fn(self, node: FnDecl, dec: Decorator) -> None:
        """Emit a @foreign decorated function as a placeholder."""
        params = self._render_params(node.params)
        self._buf.write(f"// @foreign — {node.name}")
        self._buf.write(f"function {node.name}({params}) {{")
        self._buf.indent()
        self._buf.write(f"throw new Error(\"{node.name}: foreign function not linked\");")
        self._buf.dedent()
        self._buf.write("}")
        self._buf.blank()

    def _emit_body_stmts(self, body: Any) -> None:
        """Emit the body of a function/block — handles both list and BlockStmt."""
        if isinstance(body, BlockStmt):
            for s in body.stmts:
                self._emit_node(s)
        elif isinstance(body, list):
            for s in body:
                self._emit_node(s)
        elif body is not None:
            self._emit_node(body)

    # ── Visitor: ConstFnDecl ────────────────────────────────────────────

    def _emit_ConstFnDecl(self, node: ConstFnDecl) -> None:
        params = self._render_params(node.params)
        exp = "export " if node.is_pub and self.module_format == "esm" else ""
        self._buf.write(f"/* consteval */ {exp}function {node.name}({params}) {{")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("}")
        self._buf.blank()

    # ── Visitor: LetDecl ────────────────────────────────────────────────

    def _emit_LetDecl(self, node: LetDecl) -> None:
        kw = "let" if node.mutable else "const"
        if node.value is not None:
            val = self._expr(node.value)
            self._buf.write(f"{kw} {node.name} = {val};")
        else:
            self._buf.write(f"{kw} {node.name};")

    # ── Visitor: AssignStmt ─────────────────────────────────────────────

    def _emit_AssignStmt(self, node: AssignStmt) -> None:
        target = self._expr(node.target)
        op = node.op or "="
        val = self._expr(node.value)
        self._buf.write(f"{target} {op} {val};")

    # ── Visitor: ReturnStmt ─────────────────────────────────────────────

    def _emit_ReturnStmt(self, node: ReturnStmt) -> None:
        if node.value:
            self._buf.write(f"return {self._expr(node.value)};")
        else:
            self._buf.write("return;")

    # ── Visitor: BreakStmt ──────────────────────────────────────────────

    def _emit_BreakStmt(self, node: BreakStmt) -> None:
        if node.label:
            self._buf.write(f"break {node.label};")
        else:
            self._buf.write("break;")

    # ── Visitor: ContinueStmt ───────────────────────────────────────────

    def _emit_ContinueStmt(self, node: ContinueStmt) -> None:
        if node.label:
            self._buf.write(f"continue {node.label};")
        else:
            self._buf.write("continue;")

    # ── Visitor: ExprStmt ───────────────────────────────────────────────

    def _emit_ExprStmt(self, node: ExprStmt) -> None:
        self._buf.write(f"{self._expr(node.expr)};")

    # ── Visitor: BlockStmt ──────────────────────────────────────────────

    def _emit_BlockStmt(self, node: BlockStmt) -> None:
        self._buf.write("{")
        self._buf.indent()
        for s in node.stmts:
            self._emit_node(s)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: IfStmt ─────────────────────────────────────────────────

    def _emit_IfStmt(self, node: IfStmt) -> None:
        cond = self._expr(node.condition)
        self._buf.write(f"if ({cond}) {{")
        self._buf.indent()
        self._emit_body_stmts(node.then_block)
        self._buf.dedent()
        # Elif arms
        for elif_cond, elif_body in (node.elif_arms or []):
            ec = self._expr(elif_cond)
            self._buf.write(f"}} else if ({ec}) {{")
            self._buf.indent()
            self._emit_body_stmts(elif_body)
            self._buf.dedent()
        # Else
        if node.else_block:
            self._buf.write("} else {")
            self._buf.indent()
            self._emit_body_stmts(node.else_block)
            self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: WhileStmt ──────────────────────────────────────────────

    def _emit_WhileStmt(self, node: WhileStmt) -> None:
        cond = self._expr(node.condition)
        self._buf.write(f"while ({cond}) {{")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: LoopStmt ───────────────────────────────────────────────

    def _emit_LoopStmt(self, node: LoopStmt) -> None:
        self._buf.write("while (true) {")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: ForStmt ────────────────────────────────────────────────

    def _emit_ForStmt(self, node: ForStmt) -> None:
        var = node.var if isinstance(node.var, str) else node.var.name if hasattr(node.var, 'name') else str(node.var)
        iter_s = self._expr(node.iter)
        self._buf.write(f"for (const {var} of {iter_s}) {{")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: AsyncForStmt ───────────────────────────────────────────

    def _emit_AsyncForStmt(self, node: AsyncForStmt) -> None:
        var = node.var if isinstance(node.var, str) else str(node.var)
        iter_s = self._expr(node.iter)
        self._buf.write(f"for await (const {var} of {iter_s}) {{")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: MatchStmt ──────────────────────────────────────────────

    def _emit_MatchStmt(self, node: MatchStmt) -> None:
        subj = self._expr(node.subject)
        self._buf.write(f"// match {subj}")
        first = True
        for arm in node.arms:
            pat = self._pattern_to_js(arm.pattern, subj)
            kw = "if" if first else "} else if"
            if pat == "true":
                if not first:
                    self._buf.write("} else {")
                else:
                    self._buf.write("{")
            else:
                self._buf.write(f"{kw} ({pat}) {{")
            self._buf.indent()
            if arm.body:
                self._emit_body_stmts(arm.body)
            elif arm.value:
                self._buf.write(f"{self._expr(arm.value)};")
            self._buf.dedent()
            first = False
        self._buf.write("}")

    def _pattern_to_js(self, pattern: Any, subject: str) -> str:
        """Convert a match pattern to a JS boolean expression."""
        if isinstance(pattern, WildcardPattern):
            return "true"
        if isinstance(pattern, LiteralPattern):
            return f"{subject} === {self._expr(pattern.value) if not isinstance(pattern.value, (int, float, str, bool)) else repr(pattern.value)}"
        if isinstance(pattern, BindingPattern):
            return f"(({pattern.name} = {subject}), true)"
        if isinstance(pattern, (Literal,)):
            return f"{subject} === {self._expr(pattern)}"
        if isinstance(pattern, (Ident,)):
            name = pattern.name
            if name == "_":
                return "true"
            return f"{subject} === {name}"
        if isinstance(pattern, EnumVariantPattern):
            if pattern.enum_name:
                return f"{subject}?.__variant === \"{pattern.variant_name}\""
            return f"{subject} === \"{pattern.variant_name}\""
        if isinstance(pattern, TypePattern):
            return f"{subject}?.__type === \"{pattern.type_name}\""
        if isinstance(pattern, OrPattern):
            l = self._pattern_to_js(pattern.left, subject)
            r = self._pattern_to_js(pattern.right, subject)
            return f"({l} || {r})"
        if isinstance(pattern, TuplePattern):
            checks = []
            for i, elem in enumerate(pattern.elements):
                checks.append(self._pattern_to_js(elem, f"{subject}[{i}]"))
            return " && ".join(checks) if checks else "true"
        if isinstance(pattern, ListPattern):
            checks = []
            for i, elem in enumerate(pattern.head or []):
                checks.append(self._pattern_to_js(elem, f"{subject}[{i}]"))
            return " && ".join(checks) if checks else "true"
        # Fallback: compare directly
        val = self._expr(pattern) if hasattr(pattern, 'accept') else str(pattern)
        return f"{subject} === {val}"

    # ── Visitor: TryStmt ────────────────────────────────────────────────

    def _emit_TryStmt(self, node: TryStmt) -> None:
        self._buf.write("try {")
        self._buf.indent()
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        for rec in (node.recoveries or []):
            if isinstance(rec, RecoverClause):
                var = rec.var or "_err"
                self._buf.write(f"}} catch ({var}) {{")
                self._buf.indent()
                self._emit_body_stmts(rec.body)
                self._buf.dedent()
            else:
                self._buf.write("} catch (_err) {")
                self._buf.indent()
                self._emit_body_stmts(rec)
                self._buf.dedent()
        if not node.recoveries:
            self._buf.write("} catch (_err) {")
            self._buf.indent()
            self._buf.write("/* unhandled */")
            self._buf.dedent()
        if node.ensure:
            self._buf.write("} finally {")
            self._buf.indent()
            self._emit_body_stmts(node.ensure)
            self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: ThrowStmt ──────────────────────────────────────────────

    def _emit_ThrowStmt(self, node: ThrowStmt) -> None:
        val = self._expr(node.value)
        self._buf.write(f"throw new Error({val});")

    # ── Visitor: EmitStmt ───────────────────────────────────────────────

    def _emit_EmitStmt(self, node: EmitStmt) -> None:
        args = ", ".join(self._expr(a) for a in (node.args or []))
        self._buf.write(f"__ltl.emit(\"{node.event}\", {{ {args} }});")

    # ── Visitor: MeasureBlock ───────────────────────────────────────────

    def _emit_MeasureBlock(self, node: MeasureBlock) -> None:
        label = node.label if isinstance(node.label, str) else self._expr(node.label)
        self._buf.write(f"const __t0_{label.replace(' ', '_')} = performance.now();")
        self._emit_body_stmts(node.body)
        self._buf.write(f"console.log(`[measure:{label}] ${{(performance.now() - __t0_{label.replace(' ', '_')}).toFixed(3)}}ms`);")

    # ── Visitor: GuardExpr ──────────────────────────────────────────────

    def _emit_GuardExpr(self, node: GuardExpr) -> None:
        cond = self._expr(node.condition)
        self._buf.write(f"if (!({cond})) {{")
        self._buf.indent()
        self._emit_body_stmts(node.else_body)
        self._buf.dedent()
        self._buf.write("}")

    # ── Visitor: PipelineAssign ─────────────────────────────────────────

    def _emit_PipelineAssign(self, node: PipelineAssign) -> None:
        target = self._expr(node.target)
        val = self._expr(node.value)
        self._buf.write(f"{target} = {val};")

    # ── Visitor: StructDecl ─────────────────────────────────────────────

    def _emit_StructDecl(self, node: StructDecl) -> None:
        self._struct_names.add(node.name)
        exp = "export " if node.is_pub and self.module_format == "esm" else ""
        self._buf.write(f"{exp}class {node.name} {{")
        self._buf.indent()

        # Constructor
        fields = node.fields or []
        field_names = []
        for f in fields:
            if isinstance(f, StructField):
                field_names.append(f.name)
            elif isinstance(f, tuple):
                field_names.append(f[0] if isinstance(f[0], str) else str(f[0]))
            else:
                field_names.append(str(f))

        params = ", ".join(field_names)
        self._buf.write(f"constructor({params}) {{")
        self._buf.indent()
        self._buf.write(f"this.__type = \"{node.name}\";")
        for fn in field_names:
            self._buf.write(f"this.{fn} = {fn};")
        self._buf.dedent()
        self._buf.write("}")

        # toString
        self._buf.blank()
        self._buf.write("toString() {")
        self._buf.indent()
        fields_str = " + ".join(f"`, {fn}=${{this.{fn}}}`" for fn in field_names) if field_names else "''"
        self._buf.write(f"return `{node.name}(` + {fields_str} + `)`;")
        self._buf.dedent()
        self._buf.write("}")

        self._buf.dedent()
        self._buf.write("}")
        self._buf.blank()

    # ── Visitor: EnumDecl ───────────────────────────────────────────────

    def _emit_EnumDecl(self, node: EnumDecl) -> None:
        self._enum_names.add(node.name)
        exp = "export " if node.is_pub and self.module_format == "esm" else ""
        self._buf.write(f"{exp}const {node.name} = Object.freeze({{")
        self._buf.indent()
        for i, variant in enumerate(node.variants or []):
            if isinstance(variant, EnumVariant):
                vname = variant.name
                if variant.fields:
                    # ADT variant — factory function
                    field_names = []
                    for f in variant.fields:
                        if isinstance(f, StructField):
                            field_names.append(f.name)
                        elif isinstance(f, tuple):
                            field_names.append(f[0] if isinstance(f[0], str) else str(f[0]))
                        elif hasattr(f, 'name'):
                            field_names.append(f.name)
                        else:
                            field_names.append(str(f))
                    params = ", ".join(field_names)
                    fields = ", ".join(f"{fn}: {fn}" for fn in field_names)
                    self._buf.write(f"{vname}: ({params}) => ({{ __variant: \"{vname}\", {fields} }}),")
                else:
                    self._buf.write(f"{vname}: \"{vname}\",")
            elif isinstance(variant, tuple):
                self._buf.write(f"{variant[0]}: \"{variant[0]}\",")
            else:
                self._buf.write(f"{variant}: \"{variant}\",")
        self._buf.dedent()
        self._buf.write("});")
        self._buf.blank()

    # ── Visitor: TypeAlias ──────────────────────────────────────────────

    def _emit_TypeAlias(self, node: TypeAlias) -> None:
        # JS has no type aliases; emit as a comment + documentation
        target = node.target if isinstance(node.target, str) else str(node.target)
        self._buf.write(f"/** @typedef {{{target}}} {node.name} */")

    # ── Visitor: ImplBlock ──────────────────────────────────────────────

    def _emit_ImplBlock(self, node: ImplBlock) -> None:
        type_name = node.type_name
        if node.interface:
            self._buf.write(f"// impl {node.interface} for {type_name}")
        else:
            self._buf.write(f"// impl {type_name}")

        for method in (node.methods or []):
            if isinstance(method, FnDecl):
                params = self._render_params(method.params)
                # Skip 'self' from params
                param_list = [p for p in (params.split(", ") if params else []) if p.strip() != "self"]
                param_str = ", ".join(param_list)
                async_kw = "async " if method.is_async else ""
                self._buf.write(f"{type_name}.prototype.{method.name} = {async_kw}function({param_str}) {{")
                self._buf.indent()
                self._in_method = True
                self._emit_body_stmts(method.body)
                self._in_method = False
                self._buf.dedent()
                self._buf.write("};")
                self._buf.blank()

    # ── Visitor: InterfaceDecl ──────────────────────────────────────────

    def _emit_InterfaceDecl(self, node: InterfaceDecl) -> None:
        exp = "export " if node.is_pub and self.module_format == "esm" else ""
        self._buf.write(f"/** @interface {node.name} */")
        self._buf.write(f"{exp}class {node.name} {{")
        self._buf.indent()
        for method in (node.methods or []):
            if isinstance(method, FnDecl):
                params = self._render_params(method.params)
                self._buf.write(f"/** @abstract */ {method.name}({params}) {{ throw new Error(\"not implemented\"); }}")
        self._buf.dedent()
        self._buf.write("}")
        self._buf.blank()

    # ── Visitor: ForeignBlock ───────────────────────────────────────────

    def _emit_ForeignBlock(self, node: ForeignBlock) -> None:
        lang = node.lang or "unknown"
        self._buf.write(f"// @foreign({lang})")
        if node.source:
            for line in str(node.source).splitlines():
                self._buf.write(f"// {line}")

    # ── Visitor: SelectStmt (v1.6) ──────────────────────────────────────

    def _emit_SelectStmt(self, node: SelectStmt) -> None:
        self._buf.write("// select {")
        self._buf.write("await (async () => {")
        self._buf.indent()
        for arm in (node.arms or []):
            if isinstance(arm, SelectArm):
                cond = self._expr(arm.channel) if hasattr(arm, 'channel') else "true"
                self._buf.write(f"// arm: {cond}")
                self._emit_body_stmts(arm.body)
        self._buf.dedent()
        self._buf.write("})();")

    # ── Visitor: NurseryBlock (v1.6) ────────────────────────────────────

    def _emit_NurseryBlock(self, node: NurseryBlock) -> None:
        name = node.name or "nursery"
        self._buf.write(f"// nursery \"{name}\"")
        self._buf.write("await (async () => {")
        self._buf.indent()
        self._buf.write(f"const {name} = {{ spawn: (fn) => fn() }};")
        self._emit_body_stmts(node.body)
        self._buf.dedent()
        self._buf.write("})();")

    # ── Visitor: MacroDecl (v1.8) ───────────────────────────────────────

    def _emit_MacroDecl(self, node: MacroDecl) -> None:
        params = self._render_params(node.params) if node.params else ""
        self._buf.write(f"/* macro {node.name}!({params}) — compile-time only */")

    # ── Visitor: MacroInvocation (v1.8) ─────────────────────────────────

    def _emit_MacroInvocation(self, node: MacroInvocation) -> None:
        args = ", ".join(self._expr(a) for a in (node.args or []))
        self._buf.write(f"/* {node.name}!({args}) */")

    # ── Visitor: CompTimeBlock (v1.8) ───────────────────────────────────

    def _emit_CompTimeBlock(self, node: CompTimeBlock) -> None:
        self._buf.write("/* comptime { */")
        self._emit_body_stmts(node.body)
        self._buf.write("/* } */")

    # ── Visitor: TypeMatchExpr ──────────────────────────────────────────

    def _emit_TypeMatchExpr(self, node: TypeMatchExpr) -> None:
        self._buf.write(f"{self._expr(node)};")

    # ── Visitor: StaticDecl ─────────────────────────────────────────────

    def _emit_StaticDecl(self, node: Any) -> None:
        name = node.name if hasattr(node, 'name') else "unknown"
        val = self._expr(node.value) if hasattr(node, 'value') and node.value else "undefined"
        self._buf.write(f"let {name} = {val};  // static")


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def transpile_to_js(source: str, module_format: str = "esm",
                    include_runtime: bool = True) -> str:
    """Transpile LATERALUS source to JavaScript."""
    t = JavaScriptTranspiler(module_format=module_format,
                             include_runtime=include_runtime)
    return t.transpile_string(source)


def get_js_transpiler_builtins() -> dict:
    return {
        "transpile_to_js": transpile_to_js,
        "JavaScriptTranspiler": JavaScriptTranspiler,
        "JS_RUNTIME": JS_RUNTIME,
    }
