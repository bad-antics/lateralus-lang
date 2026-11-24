"""
lateralus_lang/codegen/wasm.py
LATERALUS -> WebAssembly (.wat text & .wasm binary) Compiler Target

Compiles LATERALUS programs and IR into WebAssembly modules that emit both
human-readable WebAssembly Text Format (.wat) and spec-compliant WebAssembly 1.0
binary bytecode (.wasm) with zero external toolchain dependencies.

Supports:
  - Integer (i64), floating-point (f64), boolean (i32), and UTF-8 string (i32) types
  - Functions (including recursion) with typed parameters and returns
  - Local variables, mutable assignments (+=, -=, *=, /=), and constants
  - Control flow: if/elif/else, while, loop, for-in ranges/lists, break/continue, match
  - Pipeline operator |> lowered to direct WASM call chains
  - String concatenation, equality, interpolation, and numeric/boolean formatting
  - Heap-allocated lists and structs in linear memory
  - Browser/host runtime imports (`env.println`, `env.print`, `env.http_get`)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ..ast_nodes import (
    AssignStmt,
    AwaitExpr,
    BinOp,
    BlockStmt,
    BreakStmt,
    CallExpr,
    CastExpr,
    ConstFnDecl,
    ContinueStmt,
    Expr,
    ExprStmt,
    FieldExpr,
    FnDecl,
    ForStmt,
    Ident,
    IfStmt,
    ImplBlock,
    ImportStmt,
    IndexExpr,
    InterpolatedStr,
    LetDecl,
    ListExpr,
    Literal,
    LiteralPattern,
    LoopStmt,
    MatchStmt,
    OrPattern,
    PipelineAssign,
    Program,
    RangeExpr,
    ReturnStmt,
    SelfExpr,
    Stmt,
    StructDecl,
    StructLiteral,
    TernaryExpr,
    TupleExpr,
    TypeMatchExpr,
    TypeRef,
    UnaryOp,
    WhileStmt,
    WildcardPattern,
)
from .wasm_binary import encode_wasm_module

# ---------------------------------------------------------------------------
# WAT type system
# ---------------------------------------------------------------------------


class WasmType:
    """Maps LATERALUS types to WebAssembly value types."""

    I32 = "i32"
    I64 = "i64"
    F32 = "f32"
    F64 = "f64"
    NONE = ""  # void

    LTL_MAP = {
        "int": "i64",
        "Int": "i64",
        "i64": "i64",
        "i32": "i64",
        "float": "f64",
        "Float": "f64",
        "f64": "f64",
        "bool": "i32",
        "Bool": "i32",
        "str": "i32",
        "String": "i32",
        "None": "",
        "void": "",
        "()": "",
        "any": "i64",
    }

    @classmethod
    def from_ltl(cls, ltl_type: str) -> str:
        """Convert a LATERALUS type name into its WASM value type."""
        return cls.LTL_MAP.get(ltl_type, "i64")


# ---------------------------------------------------------------------------
# WAT instruction builders
# ---------------------------------------------------------------------------


def i64_const(n: int) -> str:
    return f"i64.const {n}"


def f64_const(v: float) -> str:
    return f"f64.const {v}"


def i32_const(n: int) -> str:
    return f"i32.const {n}"


def local_get(name: str) -> str:
    return f"local.get ${name}"


def local_set(name: str) -> str:
    return f"local.set ${name}"


def local_tee(name: str) -> str:
    return f"local.tee ${name}"


def global_get(name: str) -> str:
    return f"global.get ${name}"


def global_set(name: str) -> str:
    return f"global.set ${name}"


def call(name: str) -> str:
    return f"call ${name}"


def call_indirect(type_idx: int) -> str:
    return f"call_indirect (type {type_idx})"


def i64_add() -> str: return "i64.add"
def i64_sub() -> str: return "i64.sub"
def i64_mul() -> str: return "i64.mul"
def i64_div_s() -> str: return "i64.div_s"
def i64_rem_s() -> str: return "i64.rem_s"
def i64_eq() -> str: return "i64.eq"
def i64_ne() -> str: return "i64.ne"
def i64_lt_s() -> str: return "i64.lt_s"
def i64_gt_s() -> str: return "i64.gt_s"
def i64_le_s() -> str: return "i64.le_s"
def i64_ge_s() -> str: return "i64.ge_s"
def i64_and() -> str: return "i64.and"
def i64_or() -> str: return "i64.or"
def i64_xor() -> str: return "i64.xor"
def i64_shl() -> str: return "i64.shl"
def i64_shr_s() -> str: return "i64.shr_s"

def f64_add() -> str: return "f64.add"
def f64_sub() -> str: return "f64.sub"
def f64_mul() -> str: return "f64.mul"
def f64_div() -> str: return "f64.div"
def f64_sqrt() -> str: return "f64.sqrt"
def f64_abs() -> str: return "f64.abs"
def f64_neg() -> str: return "f64.neg"
def f64_ceil() -> str: return "f64.ceil"
def f64_floor() -> str: return "f64.floor"
def f64_eq() -> str: return "f64.eq"
def f64_ne() -> str: return "f64.ne"
def f64_lt() -> str: return "f64.lt"
def f64_gt() -> str: return "f64.gt"
def f64_le() -> str: return "f64.le"
def f64_ge() -> str: return "f64.ge"

def i32_eqz() -> str: return "i32.eqz"
def i32_eq() -> str: return "i32.eq"

def f64_convert_i64_s() -> str: return "f64.convert_i64_s"
def i64_trunc_f64_s() -> str: return "i64.trunc_f64_s"


# ---------------------------------------------------------------------------
# WAT / WASM module builder
# ---------------------------------------------------------------------------


@dataclass
class WasmLocal:
    """Local variable declaration inside a WASM function."""

    name: str
    wasm_type: str


@dataclass
class WasmFunction:
    """Represents either an imported host function or a defined WASM function."""

    name: str
    params: list[tuple[str, str]]
    result_type: str
    locals: list[WasmLocal] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    exported: bool = False
    imported: bool = False
    import_module: str = ""
    import_name: str = ""

    def add_local(self, name: str, wasm_type: str) -> None:
        if any(p == name for p, _ in self.params):
            return
        if not any(loc.name == name for loc in self.locals):
            self.locals.append(WasmLocal(name, wasm_type))

    def emit(self, *instructions: str) -> None:
        self.body.extend(instructions)

    def to_wat(self, indent: int = 2) -> str:
        pad = " " * indent
        lines: list[str] = []

        if self.imported:
            imp = f'(import "{self.import_module}" "{self.import_name}" '
            params_s = " ".join(f"(param ${n} {t})" for n, t in self.params)
            result_s = f"(result {self.result_type})" if self.result_type else ""
            sep = " " if params_s and result_s else ""
            inner = f" {params_s}{sep}{result_s}" if (params_s or result_s) else ""
            lines.append(f"{pad}{imp}(func ${self.name}{inner}))")
            return "\n".join(lines)

        export_clause = f'(export "{self.name}") ' if self.exported else ""
        params_s = " ".join(f"(param ${n} {t})" for n, t in self.params)
        result_s = f"(result {self.result_type})" if self.result_type else ""
        sig_parts = [p for p in (params_s, result_s) if p]
        sig_tail = (" " + " ".join(sig_parts)) if sig_parts else ""
        lines.append(f"{pad}(func ${self.name} {export_clause}{sig_tail}".rstrip())

        for loc in self.locals:
            lines.append(f"{pad}  (local ${loc.name} {loc.wasm_type})")

        for instr in self.body:
            for sub in instr.splitlines():
                if sub.strip():
                    lines.append(f"{pad}  {sub}")

        lines.append(f"{pad})")
        return "\n".join(lines)


@dataclass
class WasmMemory:
    """Linear memory descriptor."""

    min_pages: int = 1
    max_pages: Optional[int] = None
    exported: bool = True

    def to_wat(self, indent: int = 2) -> str:
        pad = " " * indent
        export = '(export "memory") ' if self.exported else ""
        max_str = f" {self.max_pages}" if self.max_pages else ""
        return f"{pad}(memory {export}{self.min_pages}{max_str})"


@dataclass
class WasmGlobal:
    """Module-level WASM global."""

    name: str
    wasm_type: str
    mutable: bool
    init_value: str

    def to_wat(self, indent: int = 2) -> str:
        pad = " " * indent
        mut = f"(mut {self.wasm_type})" if self.mutable else self.wasm_type
        return f"{pad}(global ${self.name} {mut} ({self.wasm_type}.const {self.init_value}))"


class WasmModule:
    """
    Builds a WebAssembly module capable of serializing to both WAT (.wat)
    and binary WebAssembly 1.0 (.wasm).
    """

    def __init__(self, name: str = "lateralus_module") -> None:
        self.name = name
        self._functions: list[WasmFunction] = []
        self._memory: Optional[WasmMemory] = None
        self._globals: list[WasmGlobal] = []
        self._data_segments: list[tuple[int, bytes]] = []
        self._data_offset: int = 64
        self._string_pool: dict[str, int] = {}
        self._type_section: list[str] = []

    def add_memory(
        self,
        min_pages: int = 1,
        exported: bool = True,
        max_pages: Optional[int] = None,
    ) -> WasmMemory:
        self._memory = WasmMemory(
            min_pages=min_pages,
            max_pages=max_pages,
            exported=exported,
        )
        return self._memory

    def add_global(self, name: str, wasm_type: str, mutable: bool, init: str) -> WasmGlobal:
        g = WasmGlobal(name, wasm_type, mutable, init)
        self._globals.append(g)
        return g

    def add_function(
        self,
        name: str,
        params: list[tuple[str, str]],
        result_type: str,
        exported: bool = False,
    ) -> WasmFunction:
        fn = WasmFunction(
            name=name,
            params=params,
            result_type=result_type,
            exported=exported,
        )
        self._functions.append(fn)
        return fn

    def import_function(
        self,
        module: str,
        field_name: str,
        local_name: str,
        params: list[tuple[str, str]],
        result_type: str,
    ) -> WasmFunction:
        for existing in self._functions:
            if existing.imported and existing.name == local_name:
                return existing
        fn = WasmFunction(
            name=local_name,
            params=params,
            result_type=result_type,
            imported=True,
            import_module=module,
            import_name=field_name,
        )
        import_count = sum(1 for f in self._functions if f.imported)
        self._functions.insert(import_count, fn)
        return fn

    def add_string_constant(self, s: str) -> int:
        """Intern a null-terminated UTF-8 string in linear memory and return its offset."""
        if s in self._string_pool:
            return self._string_pool[s]
        data = s.encode("utf-8") + b"\x00"
        ptr = self._data_offset
        self._data_segments.append((ptr, data))
        self._data_offset = (self._data_offset + len(data) + 3) & ~3
        self._string_pool[s] = ptr
        return ptr

    def to_wat(self) -> str:
        """Serialize the module as WebAssembly Text Format (.wat)."""
        lines: list[str] = [f"(module ;; {self.name}"]

        for fn in self._functions:
            if fn.imported:
                lines.append(fn.to_wat())

        if self._memory:
            lines.append(self._memory.to_wat())

        for g in self._globals:
            lines.append(g.to_wat())

        for offset, data in self._data_segments:
            escaped = "".join(f"\\{b:02x}" for b in data)
            lines.append(f'  (data (i32.const {offset}) "{escaped}")')

        for fn in self._functions:
            if not fn.imported:
                lines.append(fn.to_wat())

        lines.append(")")
        return "\n".join(lines)

    def to_bytes(self) -> bytes:
        """Serialize the module directly into WebAssembly 1.0 binary (.wasm) bytes."""
        return encode_wasm_module(self)

    def save(self, path: str) -> None:
        """Save WAT text file (or binary .wasm if path ends with `.wasm`)."""
        if path.lower().endswith(".wasm"):
            self.save_binary(path)
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_wat())

    def save_binary(self, path: str) -> None:
        """Save WebAssembly 1.0 binary (.wasm) file."""
        with open(path, "wb") as f:
            f.write(self.to_bytes())


# ---------------------------------------------------------------------------
# LATERALUS IR -> WASM compiler (three-address IR API)
# ---------------------------------------------------------------------------


class WasmCompiler:
    """Compiles LATERALUS IR dicts or arithmetic expressions into WAT/WASM."""

    def __init__(self) -> None:
        self._module = WasmModule()
        self._current_fn: Optional[WasmFunction] = None
        self._local_types: dict[str, str] = {}
        self._label_counter = 0

        self._module.import_function(
            "env", "ltl_println_i64", "ltl_println_i64", [("val", "i64")], ""
        )
        self._module.import_function(
            "env", "ltl_println_f64", "ltl_println_f64", [("val", "f64")], ""
        )

    def _new_label(self) -> str:
        self._label_counter += 1
        return f"block_{self._label_counter}"

    def compile_ir(self, ir_instructions: list[dict[str, Any]]) -> WasmModule:
        """Compile a list of IR instruction dictionaries into a WasmModule."""
        for instr in ir_instructions:
            self._emit_ir(instr)
        return self._module

    def _emit_ir(self, instr: dict[str, Any]) -> None:
        op = instr.get("op", "")

        if op == "fn_begin":
            name = instr["name"]
            params = [(p, WasmType.from_ltl(t)) for p, t in instr.get("params", [])]
            ret = WasmType.from_ltl(instr.get("return_type", "None"))
            exported = instr.get("exported", False)
            self._current_fn = self._module.add_function(name, params, ret, exported)

        elif op == "fn_end":
            self._current_fn = None

        elif op == "const":
            if self._current_fn is None:
                return
            dest = instr["dest"]
            val = instr["value"]
            wtype = instr.get("wasm_type", "i64")
            self._current_fn.add_local(dest, wtype)
            if wtype == "f64":
                self._current_fn.emit(f64_const(float(val)), local_set(dest))
            else:
                self._current_fn.emit(i64_const(int(val)), local_set(dest))

        elif op in ("add", "sub", "mul", "div"):
            if self._current_fn is None:
                return
            dest = instr["dest"]
            a, b = instr["left"], instr["right"]
            wtype = instr.get("wasm_type", "i64")
            self._current_fn.add_local(dest, wtype)

            if wtype == "f64":
                ops_map = {
                    "add": f64_add,
                    "sub": f64_sub,
                    "mul": f64_mul,
                    "div": f64_div,
                }
            else:
                ops_map = {
                    "add": i64_add,
                    "sub": i64_sub,
                    "mul": i64_mul,
                    "div": i64_div_s,
                }

            self._current_fn.emit(
                local_get(a),
                local_get(b),
                ops_map[op](),
                local_set(dest),
            )

        elif op == "return":
            if self._current_fn is None:
                return
            val = instr.get("value")
            if val:
                self._current_fn.emit(local_get(val))
            self._current_fn.emit("return")

    def compile_expression_to_wat(self, expr: str) -> str:
        """Compile a simple numeric LATERALUS expression to WAT instructions."""
        return self._compile_arith_expr(expr.strip())

    def _compile_arith_expr(self, expr: str) -> str:
        expr = expr.strip()

        if re.match(r"^-?\d+\.\d+$", expr):
            return f64_const(float(expr))

        if re.match(r"^-?\d+$", expr):
            return i64_const(int(expr))

        if re.match(r"^\w+$", expr):
            return local_get(expr)

        if "**" in expr:
            parts = expr.rsplit("**", 1)
            left = self._compile_arith_expr(parts[0])
            right = self._compile_arith_expr(parts[1])
            return f";; pow({left}, {right}) ;; [use call $ltl_pow]"

        if expr.startswith("(") and expr.endswith(")"):
            return self._compile_arith_expr(expr[1:-1])

        for op, emit_fn in [
            ("+", i64_add),
            ("-", i64_sub),
            ("*", i64_mul),
            ("/", i64_div_s),
        ]:
            idx = _find_binary_op(expr, op)
            if idx >= 0:
                left_expr = self._compile_arith_expr(expr[:idx])
                right_expr = self._compile_arith_expr(expr[idx + len(op) :])
                return f"{left_expr}\n{right_expr}\n{emit_fn()}"

        return f";; unhandled: {expr}"


def _find_binary_op(expr: str, op: str) -> int:
    """Find the position of a binary operator at zero nesting depth."""
    depth = 0
    for i in range(len(expr) - 1, -1, -1):
        c = expr[i]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            depth -= 1
        elif depth == 0 and expr[i : i + len(op)] == op:
            return i
    return -1


# ---------------------------------------------------------------------------
# Full LATERALUS AST -> WASM compiler
# ---------------------------------------------------------------------------


@dataclass
class _FnSig:
    wasm_name: str
    param_types: list[str]  # semantic types: int, float, bool, str, list:*, struct:*
    ret_type: str           # semantic type or "void"


@dataclass
class _StructLayout:
    name: str
    fields: list[tuple[str, str]]  # (field_name, semantic_type)

    def offset_of(self, field_name: str) -> tuple[int, str]:
        for idx, (fname, ftype) in enumerate(self.fields):
            if fname == field_name:
                return idx * 8, ftype
        raise ValueError(f"Struct '{self.name}' has no field '{field_name}'")


def _sem_to_wasm(sem_type: str) -> str:
    """Map an internal semantic type tag to its WASM storage type."""
    if sem_type == "void":
        return ""
    if sem_type == "float":
        return "f64"
    if sem_type in ("bool", "str") or sem_type.startswith(("list:", "struct:")):
        return "i32"
    return "i64"


def _typeref_to_sem(tref: Optional[TypeRef]) -> str:
    if tref is None:
        return "int"
    n = tref.name
    if n in ("int", "Int", "i64", "i32", "u32", "u64", "usize"):
        return "int"
    if n in ("float", "Float", "f64", "f32"):
        return "float"
    if n in ("bool", "Bool"):
        return "bool"
    if n in ("str", "String"):
        return "str"
    if n in ("None", "void", "()"):
        return "void"
    if n in ("list", "List", "Vec"):
        inner = _typeref_to_sem(tref.params[0]) if tref.params else "int"
        return f"list:{inner}"
    return f"struct:{n}"


class LateralusWasmGenerator:
    """
    Compiles a parsed LATERALUS `Program` AST into a self-contained `WasmModule`
    with linear-memory string/array/struct helpers and host I/O imports.
    """

    def __init__(self, module_name: str = "lateralus_module") -> None:
        self.mod = WasmModule(module_name)
        self.mod.add_memory(min_pages=2, exported=True)

        # Standard browser/CLI host runtime bridge imports
        self.mod.import_function(
            "env", "println", "println", [("ptr", "i32"), ("len", "i32")], ""
        )
        self.mod.import_function(
            "env", "print", "print", [("ptr", "i32"), ("len", "i32")], ""
        )
        self.mod.import_function(
            "env",
            "http_get",
            "http_get",
            [
                ("url_ptr", "i32"),
                ("url_len", "i32"),
                ("out_ptr", "i32"),
                ("out_cap", "i32"),
            ],
            "i32",
        )

        self._heap_global = self.mod.add_global("__heap_ptr", "i32", True, "4096")

        # Intern core runtime string literals up front
        self._ptr_empty = self.mod.add_string_constant("")
        self._ptr_zero = self.mod.add_string_constant("0")
        self._ptr_min_i64 = self.mod.add_string_constant("-9223372036854775808")
        self._ptr_true = self.mod.add_string_constant("true")
        self._ptr_false = self.mod.add_string_constant("false")
        self._ptr_dot = self.mod.add_string_constant(".")
        self._ptr_minus = self.mod.add_string_constant("-")

        self._fn_sigs: dict[str, _FnSig] = {}
        self._structs: dict[str, _StructLayout] = {}
        self._constants: dict[str, tuple[Any, str]] = {}

        self._cur_fn: Optional[WasmFunction] = None
        self._cur_ret_sem: str = "void"
        self._locals_sem: dict[str, str] = {}
        self._loop_stack: list[tuple[str, str]] = []  # (break_lbl, continue_lbl)
        self._id_seq = 0

        self._emit_runtime_helpers()

    def _uid(self, prefix: str = "t") -> str:
        self._id_seq += 1
        return f"__{prefix}_{self._id_seq}"

    # -- Embedded WASM linear-memory runtime helpers ------------------------

    def _emit_runtime_helpers(self) -> None:
        # $__alloc(size: i32) -> i32 (8-byte aligned bump allocator with memory.grow)
        alloc = self.mod.add_function("__alloc", [("size", "i32")], "i32")
        alloc.add_local("ptr", "i32")
        alloc.add_local("aligned", "i32")
        alloc.add_local("next_ptr", "i32")
        alloc.emit(
            "local.get $size",
            "i32.const 7",
            "i32.add",
            "i32.const -8",
            "i32.and",
            "local.set $aligned",
            "global.get $__heap_ptr",
            "local.set $ptr",
            "local.get $ptr",
            "local.get $aligned",
            "i32.add",
            "local.set $next_ptr",
            "block $grow_done",
            "loop $grow_loop",
            "local.get $next_ptr",
            "memory.size",
            "i32.const 65536",
            "i32.mul",
            "i32.le_u",
            "br_if $grow_done",
            "i32.const 2",
            "memory.grow",
            "drop",
            "br $grow_loop",
            "end",
            "end",
            "local.get $next_ptr",
            "global.set $__heap_ptr",
            "local.get $ptr",
        )

        # $__strlen(ptr: i32) -> i32
        strlen = self.mod.add_function("__strlen", [("ptr", "i32")], "i32")
        strlen.add_local("len", "i32")
        strlen.emit(
            "i32.const 0",
            "local.set $len",
            "block $done",
            "loop $scan",
            "local.get $ptr",
            "local.get $len",
            "i32.add",
            "i32.load8_u",
            "i32.eqz",
            "br_if $done",
            "local.get $len",
            "i32.const 1",
            "i32.add",
            "local.set $len",
            "br $scan",
            "end",
            "end",
            "local.get $len",
        )

        # $__memcpy(dst: i32, src: i32, n: i32)
        memcpy = self.mod.add_function(
            "__memcpy", [("dst", "i32"), ("src", "i32"), ("n", "i32")], ""
        )
        memcpy.add_local("i", "i32")
        memcpy.emit(
            "i32.const 0",
            "local.set $i",
            "block $done",
            "loop $copy",
            "local.get $i",
            "local.get $n",
            "i32.ge_u",
            "br_if $done",
            "local.get $dst",
            "local.get $i",
            "i32.add",
            "local.get $src",
            "local.get $i",
            "i32.add",
            "i32.load8_u",
            "i32.store8",
            "local.get $i",
            "i32.const 1",
            "i32.add",
            "local.set $i",
            "br $copy",
            "end",
            "end",
        )

        # $__str_concat(a: i32, b: i32) -> i32
        concat = self.mod.add_function(
            "__str_concat", [("a", "i32"), ("b", "i32")], "i32"
        )
        concat.add_local("la", "i32")
        concat.add_local("lb", "i32")
        concat.add_local("out", "i32")
        concat.emit(
            "local.get $a",
            "call $__strlen",
            "local.set $la",
            "local.get $b",
            "call $__strlen",
            "local.set $lb",
            "local.get $la",
            "local.get $lb",
            "i32.add",
            "i32.const 1",
            "i32.add",
            "call $__alloc",
            "local.set $out",
            "local.get $out",
            "local.get $a",
            "local.get $la",
            "call $__memcpy",
            "local.get $out",
            "local.get $la",
            "i32.add",
            "local.get $b",
            "local.get $lb",
            "call $__memcpy",
            "local.get $out",
            "local.get $la",
            "i32.add",
            "local.get $lb",
            "i32.add",
            "i32.const 0",
            "i32.store8",
            "local.get $out",
        )

        # $__str_eq(a: i32, b: i32) -> i32
        streq = self.mod.add_function("__str_eq", [("a", "i32"), ("b", "i32")], "i32")
        streq.add_local("la", "i32")
        streq.add_local("lb", "i32")
        streq.add_local("i", "i32")
        streq.emit(
            "local.get $a",
            "call $__strlen",
            "local.set $la",
            "local.get $b",
            "call $__strlen",
            "local.set $lb",
            "local.get $la",
            "local.get $lb",
            "i32.ne",
            "if",
            "i32.const 0",
            "return",
            "end",
            "i32.const 0",
            "local.set $i",
            "block $done",
            "loop $cmp",
            "local.get $i",
            "local.get $la",
            "i32.ge_u",
            "br_if $done",
            "local.get $a",
            "local.get $i",
            "i32.add",
            "i32.load8_u",
            "local.get $b",
            "local.get $i",
            "i32.add",
            "i32.load8_u",
            "i32.ne",
            "if",
            "i32.const 0",
            "return",
            "end",
            "local.get $i",
            "i32.const 1",
            "i32.add",
            "local.set $i",
            "br $cmp",
            "end",
            "end",
            "i32.const 1",
        )

        # $__i64_to_str(val: i64) -> i32
        itos = self.mod.add_function("__i64_to_str", [("val", "i64")], "i32")
        itos.add_local("buf", "i32")
        itos.add_local("pos", "i32")
        itos.add_local("neg", "i32")
        itos.add_local("v", "i64")
        itos.emit(
            "local.get $val",
            "i64.eqz",
            "if",
            f"i32.const {self._ptr_zero}",
            "return",
            "end",
            "local.get $val",
            "i64.const -9223372036854775808",
            "i64.eq",
            "if",
            f"i32.const {self._ptr_min_i64}",
            "return",
            "end",
            "i32.const 32",
            "call $__alloc",
            "local.set $buf",
            "local.get $buf",
            "i32.const 31",
            "i32.add",
            "i32.const 0",
            "i32.store8",
            "i32.const 30",
            "local.set $pos",
            "local.get $val",
            "i64.const 0",
            "i64.lt_s",
            "if",
            "i32.const 1",
            "local.set $neg",
            "i64.const 0",
            "local.get $val",
            "i64.sub",
            "local.set $v",
            "else",
            "i32.const 0",
            "local.set $neg",
            "local.get $val",
            "local.set $v",
            "end",
            "block $digits_done",
            "loop $digits",
            "local.get $buf",
            "local.get $pos",
            "i32.add",
            "local.get $v",
            "i64.const 10",
            "i64.rem_s",
            "i32.wrap_i64",
            "i32.const 48",
            "i32.add",
            "i32.store8",
            "local.get $pos",
            "i32.const 1",
            "i32.sub",
            "local.set $pos",
            "local.get $v",
            "i64.const 10",
            "i64.div_s",
            "local.tee $v",
            "i64.eqz",
            "br_if $digits_done",
            "br $digits",
            "end",
            "end",
            "local.get $neg",
            "if",
            "local.get $buf",
            "local.get $pos",
            "i32.add",
            "i32.const 45",
            "i32.store8",
            "local.get $pos",
            "i32.const 1",
            "i32.sub",
            "local.set $pos",
            "end",
            "local.get $buf",
            "local.get $pos",
            "i32.add",
            "i32.const 1",
            "i32.add",
        )

        # $__f64_to_str(val: f64) -> i32  (2 decimal places, sign-preserving)
        ftos = self.mod.add_function("__f64_to_str", [("val", "f64")], "i32")
        ftos.add_local("abs_v", "f64")
        ftos.add_local("ipart", "i64")
        ftos.add_local("fpart", "i64")
        ftos.add_local("res", "i32")
        ftos.add_local("fstr", "i32")
        ftos.emit(
            "local.get $val",
            "f64.abs",
            "local.set $abs_v",
            "local.get $abs_v",
            "i64.trunc_f64_s",
            "local.set $ipart",
            "local.get $abs_v",
            "local.get $ipart",
            "f64.convert_i64_s",
            "f64.sub",
            "f64.const 100.0",
            "f64.mul",
            "f64.nearest",
            "i64.trunc_f64_s",
            "local.set $fpart",
            "local.get $fpart",
            "i64.const 100",
            "i64.ge_s",
            "if",
            "local.get $ipart",
            "i64.const 1",
            "i64.add",
            "local.set $ipart",
            "local.get $fpart",
            "i64.const 100",
            "i64.sub",
            "local.set $fpart",
            "end",
            "local.get $ipart",
            "call $__i64_to_str",
            f"i32.const {self._ptr_dot}",
            "call $__str_concat",
            "local.set $res",
            "local.get $fpart",
            "i64.const 10",
            "i64.lt_s",
            "if",
            "local.get $res",
            f"i32.const {self._ptr_zero}",
            "call $__str_concat",
            "local.set $res",
            "end",
            "local.get $fpart",
            "call $__i64_to_str",
            "local.set $fstr",
            "local.get $res",
            "local.get $fstr",
            "call $__str_concat",
            "local.set $res",
            "local.get $val",
            "f64.const 0.0",
            "f64.lt",
            "if",
            f"i32.const {self._ptr_minus}",
            "local.get $res",
            "call $__str_concat",
            "local.set $res",
            "end",
            "local.get $res",
        )

        # $__bool_to_str(val: i32) -> i32
        btos = self.mod.add_function("__bool_to_str", [("val", "i32")], "i32")
        btos.emit(
            "local.get $val",
            "if (result i32)",
            f"i32.const {self._ptr_true}",
            "else",
            f"i32.const {self._ptr_false}",
            "end",
        )

        # $__println_str(ptr: i32)
        pln = self.mod.add_function("__println_str", [("ptr", "i32")], "")
        pln.emit(
            "local.get $ptr",
            "local.get $ptr",
            "call $__strlen",
            "call $println",
        )

        # $__print_str(ptr: i32)
        prn = self.mod.add_function("__print_str", [("ptr", "i32")], "")
        prn.emit(
            "local.get $ptr",
            "local.get $ptr",
            "call $__strlen",
            "call $print",
        )

        # $__http_get_str(url_ptr: i32) -> i32
        hget = self.mod.add_function("__http_get_str", [("url_ptr", "i32")], "i32")
        hget.add_local("buf", "i32")
        hget.add_local("n", "i32")
        hget.emit(
            "i32.const 16384",
            "call $__alloc",
            "local.set $buf",
            "local.get $url_ptr",
            "local.get $url_ptr",
            "call $__strlen",
            "local.get $buf",
            "i32.const 16383",
            "call $http_get",
            "local.set $n",
            "local.get $n",
            "i32.const 0",
            "i32.lt_s",
            "if",
            "i32.const 0",
            "local.set $n",
            "end",
            "local.get $n",
            "i32.const 16383",
            "i32.gt_s",
            "if",
            "i32.const 16383",
            "local.set $n",
            "end",
            "local.get $buf",
            "local.get $n",
            "i32.add",
            "i32.const 0",
            "i32.store8",
            "local.get $buf",
        )

        # $__pow_i64(base: i64, exp: i64) -> i64
        powi = self.mod.add_function(
            "__pow_i64", [("base", "i64"), ("exp", "i64")], "i64"
        )
        powi.add_local("acc", "i64")
        powi.add_local("e", "i64")
        powi.emit(
            "i64.const 1",
            "local.set $acc",
            "local.get $exp",
            "local.set $e",
            "block $done",
            "loop $mul_loop",
            "local.get $e",
            "i64.const 0",
            "i64.le_s",
            "br_if $done",
            "local.get $acc",
            "local.get $base",
            "i64.mul",
            "local.set $acc",
            "local.get $e",
            "i64.const 1",
            "i64.sub",
            "local.set $e",
            "br $mul_loop",
            "end",
            "end",
            "local.get $acc",
        )

    # -- Top-level program compilation --------------------------------------

    def compile_program(self, prog: Program) -> WasmModule:
        top_stmts: list[Stmt] = []
        fn_decls: list[tuple[str, FnDecl]] = []

        # Pass 1: register structs, impl methods, functions, and top-level constants
        for stmt in prog.body:
            if isinstance(stmt, ImportStmt):
                continue
            if isinstance(stmt, StructDecl):
                fields = [(f.name, _typeref_to_sem(f.type_)) for f in stmt.fields]
                self._structs[stmt.name] = _StructLayout(stmt.name, fields)
            elif isinstance(stmt, ImplBlock):
                for m in stmt.methods:
                    mangled = f"{stmt.type_name}__{m.name}"
                    self._register_fn_sig(mangled, m, owner_struct=stmt.type_name)
                    fn_decls.append((mangled, m))
            elif isinstance(stmt, (FnDecl, ConstFnDecl)):
                decl = self._coerce_fn_decl(stmt)
                self._register_fn_sig(decl.name, decl)
                fn_decls.append((decl.name, decl))
            else:
                top_stmts.append(stmt)

        # Pass 2: compile all declared functions
        for wasm_name, decl in fn_decls:
            owner = wasm_name.split("__", 1)[0] if "__" in wasm_name else None
            self._compile_fn_decl(wasm_name, decl, owner_struct=owner)

        # Pass 3: synthesize or expose `main() -> i64`
        has_user_main = "main" in self._fn_sigs
        filtered_top: list[Stmt] = []
        for s in top_stmts:
            if (
                has_user_main
                and isinstance(s, ExprStmt)
                and isinstance(s.expr, CallExpr)
                and isinstance(s.expr.callee, Ident)
                and s.expr.callee.name == "main"
            ):
                continue
            filtered_top.append(s)

        if not has_user_main:
            main_fn = self.mod.add_function("main", [], "i64", exported=True)
            self._cur_fn = main_fn
            self._cur_ret_sem = "int"
            self._locals_sem = {}
            for s in filtered_top:
                self._compile_stmt(s)
            main_fn.emit("i64.const 0")
            self._cur_fn = None
        elif filtered_top:
            # Execute top-level init statements before delegating to user main
            entry_fn = self.mod.add_function("_start", [], "i64", exported=True)
            self._cur_fn = entry_fn
            self._cur_ret_sem = "int"
            self._locals_sem = {}
            for s in filtered_top:
                self._compile_stmt(s)
            user_sig = self._fn_sigs["main"]
            entry_fn.emit("call $main")
            if user_sig.ret_type == "void":
                entry_fn.emit("i64.const 0")
            elif _sem_to_wasm(user_sig.ret_type) != "i64":
                entry_fn.emit("drop", "i64.const 0")
            self._cur_fn = None

        # Ensure heap starts cleanly past all static string data segments
        heap_start = max(4096, (self.mod._data_offset + 63) & ~63)
        self._heap_global.init_value = str(heap_start)
        return self.mod

    def _coerce_fn_decl(self, node: FnDecl | ConstFnDecl) -> FnDecl:
        if isinstance(node, FnDecl):
            return node
        return FnDecl(
            name=node.name,
            params=node.params,
            ret_type=node.ret_type,
            body=node.body,
            span=node.span,
        )

    def _infer_fn_ret_sem(self, decl: FnDecl, param_sems: dict[str, str]) -> str:
        if decl.ret_type is not None:
            return _typeref_to_sem(decl.ret_type)
        # Inspect return statements when return annotation is omitted
        if decl.body:
            for s in decl.body.stmts:
                if isinstance(s, ReturnStmt) and s.value is not None:
                    return self._guess_expr_sem(s.value, param_sems)
        return "void"

    def _guess_expr_sem(self, expr: Expr, env: dict[str, str]) -> str:
        if isinstance(expr, Literal):
            if expr.kind == "float":
                return "float"
            if expr.kind == "bool":
                return "bool"
            if expr.kind == "str":
                return "str"
            return "int"
        if isinstance(expr, InterpolatedStr):
            return "str"
        if isinstance(expr, Ident):
            return env.get(expr.name, "int")
        if isinstance(expr, CastExpr):
            return _typeref_to_sem(expr.target)
        if isinstance(expr, BinOp):
            if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||", "and", "or"):
                return "bool"
            lt = self._guess_expr_sem(expr.left, env)
            rt = self._guess_expr_sem(expr.right, env)
            if lt == "str" or rt == "str":
                return "str"
            if lt == "float" or rt == "float":
                return "float"
        return "int"

    def _register_fn_sig(
        self, wasm_name: str, decl: FnDecl, owner_struct: Optional[str] = None
    ) -> None:
        param_types: list[str] = []
        param_map: dict[str, str] = {}
        for p in decl.params:
            if p.name == "self" and owner_struct:
                p_sem = f"struct:{owner_struct}"
            else:
                p_sem = _typeref_to_sem(p.type_)
            param_types.append(p_sem)
            param_map[p.name] = p_sem

        ret_sem = self._infer_fn_ret_sem(decl, param_map)
        if wasm_name == "main" and ret_sem == "void":
            ret_sem = "int"
        self._fn_sigs[wasm_name] = _FnSig(wasm_name, param_types, ret_sem)

    def _compile_fn_decl(
        self, wasm_name: str, decl: FnDecl, owner_struct: Optional[str] = None
    ) -> None:
        sig = self._fn_sigs[wasm_name]
        w_params: list[tuple[str, str]] = []
        self._locals_sem = {}
        for p, p_sem in zip(decl.params, sig.param_types):
            w_params.append((p.name, _sem_to_wasm(p_sem)))
            self._locals_sem[p.name] = p_sem

        exported = "__" not in wasm_name
        w_ret = _sem_to_wasm(sig.ret_type)
        fn = self.mod.add_function(wasm_name, w_params, w_ret, exported=exported)

        self._cur_fn = fn
        self._cur_ret_sem = sig.ret_type
        self._loop_stack = []

        if decl.body is not None:
            stmts = decl.body.stmts
            for idx, s in enumerate(stmts):
                is_last = idx == len(stmts) - 1
                if is_last and sig.ret_type != "void" and isinstance(s, ExprStmt):
                    val_sem = self._compile_expr(s.expr)
                    if val_sem == "void":
                        self._emit_default_value(sig.ret_type)
                    else:
                        self._coerce_stack(val_sem, sig.ret_type)
                    fn.emit("return")
                else:
                    self._compile_stmt(s)

        if sig.ret_type != "void":
            self._emit_default_value(sig.ret_type)

        self._cur_fn = None

    def _emit_default_value(self, sem_type: str) -> None:
        assert self._cur_fn is not None
        wt = _sem_to_wasm(sem_type)
        if wt == "f64":
            self._cur_fn.emit("f64.const 0.0")
        elif wt == "i32":
            if sem_type == "str":
                self._cur_fn.emit(f"i32.const {self._ptr_empty}")
            else:
                self._cur_fn.emit("i32.const 0")
        elif wt == "i64":
            self._cur_fn.emit("i64.const 0")

    def _coerce_stack(self, actual: str, target: str) -> str:
        """Convert value currently on top of the WASM stack from `actual` to `target`."""
        assert self._cur_fn is not None
        if actual == target:
            return target
        if target == "str":
            self._convert_to_str(actual)
            return "str"
        if actual == "int" and target == "float":
            self._cur_fn.emit("f64.convert_i64_s")
            return "float"
        if actual == "float" and target == "int":
            self._cur_fn.emit("i64.trunc_f64_s")
            return "int"
        if actual == "bool" and target == "int":
            self._cur_fn.emit("i64.extend_i32_u")
            return "int"
        if actual == "int" and target == "bool":
            self._cur_fn.emit("i64.const 0", "i64.ne")
            return "bool"
        return target

    def _convert_to_str(self, sem_type: str) -> None:
        assert self._cur_fn is not None
        if sem_type == "str":
            return
        if sem_type == "float":
            self._cur_fn.emit("call $__f64_to_str")
        elif sem_type == "bool":
            self._cur_fn.emit("call $__bool_to_str")
        else:
            if _sem_to_wasm(sem_type) == "i32":
                self._cur_fn.emit("i64.extend_i32_s")
            self._cur_fn.emit("call $__i64_to_str")

    def _ensure_bool_i32(self, sem_type: str) -> None:
        assert self._cur_fn is not None
        if sem_type == "bool":
            return
        wt = _sem_to_wasm(sem_type)
        if wt == "i64":
            self._cur_fn.emit("i64.const 0", "i64.ne")
        elif wt == "f64":
            self._cur_fn.emit("f64.const 0.0", "f64.ne")
        elif sem_type == "str":
            self._cur_fn.emit("call $__strlen", "i32.const 0", "i32.gt_u")

    # -- Statement compilation ----------------------------------------------

    def _compile_stmt(self, stmt: Stmt) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn

        if isinstance(stmt, BlockStmt):
            for sub in stmt.stmts:
                self._compile_stmt(sub)
            return

        if isinstance(stmt, LetDecl):
            target_sem = _typeref_to_sem(stmt.type_) if stmt.type_ else None
            if stmt.value is not None:
                val_sem = self._compile_expr(stmt.value)
                if target_sem and target_sem != val_sem:
                    val_sem = self._coerce_stack(val_sem, target_sem)
            else:
                val_sem = target_sem or "int"
                self._emit_default_value(val_sem)

            fn.add_local(stmt.name, _sem_to_wasm(val_sem))
            self._locals_sem[stmt.name] = val_sem
            fn.emit(f"local.set ${stmt.name}")
            return

        if isinstance(stmt, AssignStmt):
            self._compile_assign(stmt.target, stmt.op, stmt.value)
            return

        if isinstance(stmt, PipelineAssign):
            piped = BinOp(op="|>", left=stmt.target, right=stmt.value, span=stmt.span)
            self._compile_assign(stmt.target, "=", piped)
            return

        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None and self._cur_ret_sem != "void":
                v_sem = self._compile_expr(stmt.value)
                self._coerce_stack(v_sem, self._cur_ret_sem)
            elif stmt.value is not None:
                v_sem = self._compile_expr(stmt.value)
                if v_sem != "void":
                    fn.emit("drop")
            elif self._cur_ret_sem != "void":
                self._emit_default_value(self._cur_ret_sem)
            fn.emit("return")
            return

        if isinstance(stmt, IfStmt):
            c_sem = self._compile_expr(stmt.condition)
            self._ensure_bool_i32(c_sem)
            fn.emit("if")
            self._compile_stmt(stmt.then_block)
            # Chain elif arms as nested else-if blocks
            for elif_cond, elif_body in stmt.elif_arms:
                fn.emit("else")
                ec_sem = self._compile_expr(elif_cond)
                self._ensure_bool_i32(ec_sem)
                fn.emit("if")
                self._compile_stmt(elif_body)
            if stmt.else_block is not None:
                fn.emit("else")
                self._compile_stmt(stmt.else_block)
            for _ in stmt.elif_arms:
                fn.emit("end")
            fn.emit("end")
            return

        if isinstance(stmt, WhileStmt):
            brk = self._uid("while_brk")
            cnt = self._uid("while_cnt")
            self._loop_stack.append((brk, cnt))
            fn.emit(f"block ${brk}", f"loop ${cnt}")
            c_sem = self._compile_expr(stmt.condition)
            self._ensure_bool_i32(c_sem)
            fn.emit("i32.eqz", f"br_if ${brk}")
            self._compile_stmt(stmt.body)
            fn.emit(f"br ${cnt}", "end", "end")
            self._loop_stack.pop()
            return

        if isinstance(stmt, LoopStmt):
            brk = self._uid("loop_brk")
            cnt = self._uid("loop_cnt")
            self._loop_stack.append((brk, cnt))
            fn.emit(f"block ${brk}", f"loop ${cnt}")
            self._compile_stmt(stmt.body)
            fn.emit(f"br ${cnt}", "end", "end")
            self._loop_stack.pop()
            return

        if isinstance(stmt, ForStmt):
            self._compile_for(stmt)
            return

        if isinstance(stmt, BreakStmt):
            if self._loop_stack:
                fn.emit(f"br ${self._loop_stack[-1][0]}")
            return

        if isinstance(stmt, ContinueStmt):
            if self._loop_stack:
                fn.emit(f"br ${self._loop_stack[-1][1]}")
            return

        if isinstance(stmt, MatchStmt):
            self._compile_match_stmt(stmt)
            return

        if isinstance(stmt, ExprStmt):
            res_sem = self._compile_expr(stmt.expr)
            if res_sem != "void":
                fn.emit("drop")
            return

    def _compile_assign(self, target: Expr, op: str, value: Expr) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn

        if isinstance(target, Ident):
            name = target.name
            cur_sem = self._locals_sem.get(name, "int")
            if op == "=":
                v_sem = self._compile_expr(value)
                if name not in self._locals_sem:
                    fn.add_local(name, _sem_to_wasm(v_sem))
                    self._locals_sem[name] = v_sem
                else:
                    self._coerce_stack(v_sem, cur_sem)
                fn.emit(f"local.set ${name}")
                return

            # Compound assignment: +=, -=, *=, /=
            bin_op = op[:-1]
            synthesized = BinOp(op=bin_op, left=target, right=value, span=target.span)
            v_sem = self._compile_expr(synthesized)
            self._coerce_stack(v_sem, cur_sem)
            fn.emit(f"local.set ${name}")
            return

        if isinstance(target, IndexExpr) and isinstance(target.obj, Ident):
            arr_sem = self._compile_expr(target.obj)
            elem_sem = arr_sem.split(":", 1)[1] if ":" in arr_sem else "int"
            arr_tmp = self._uid("arr")
            idx_tmp = self._uid("idx")
            val_tmp = self._uid("val")
            fn.add_local(arr_tmp, "i32")
            fn.add_local(idx_tmp, "i32")
            fn.add_local(val_tmp, _sem_to_wasm(elem_sem))
            fn.emit(f"local.set ${arr_tmp}")
            idx_sem = self._compile_expr(target.index)
            self._coerce_stack(idx_sem, "int")
            fn.emit("i32.wrap_i64", f"local.set ${idx_tmp}")
            v_sem = self._compile_expr(value)
            self._coerce_stack(v_sem, elem_sem)
            fn.emit(f"local.set ${val_tmp}")
            fn.emit(
                f"local.get ${arr_tmp}",
                "i32.const 8",
                "i32.add",
                f"local.get ${idx_tmp}",
                "i32.const 8",
                "i32.mul",
                "i32.add",
                f"local.get ${val_tmp}",
            )
            wt = _sem_to_wasm(elem_sem)
            fn.emit(f"{wt}.store")

    def _compile_for(self, stmt: ForStmt) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn
        brk = self._uid("for_brk")
        cnt = self._uid("for_cnt")

        # Range iteration: `for i in start..end` or `for i in range(...)`
        range_bounds = self._extract_range_bounds(stmt.iter)
        if range_bounds is not None:
            start_expr, end_expr, inclusive = range_bounds
            end_tmp = self._uid("end")
            fn.add_local(stmt.var, "i64")
            fn.add_local(end_tmp, "i64")
            self._locals_sem[stmt.var] = "int"

            s_sem = self._compile_expr(start_expr)
            self._coerce_stack(s_sem, "int")
            fn.emit(f"local.set ${stmt.var}")

            e_sem = self._compile_expr(end_expr)
            self._coerce_stack(e_sem, "int")
            fn.emit(f"local.set ${end_tmp}")

            self._loop_stack.append((brk, cnt))
            fn.emit(f"block ${brk}", f"loop ${cnt}")
            fn.emit(f"local.get ${stmt.var}", f"local.get ${end_tmp}")
            fn.emit("i64.gt_s" if inclusive else "i64.ge_s")
            fn.emit(f"br_if ${brk}")

            self._compile_stmt(stmt.body)

            fn.emit(
                f"local.get ${stmt.var}",
                "i64.const 1",
                "i64.add",
                f"local.set ${stmt.var}",
                f"br ${cnt}",
                "end",
                "end",
            )
            self._loop_stack.pop()
            return

        # Heap list iteration: `for item in list_expr`
        list_sem = self._compile_expr(stmt.iter)
        elem_sem = list_sem.split(":", 1)[1] if ":" in list_sem else "int"
        elem_wt = _sem_to_wasm(elem_sem)
        arr_tmp = self._uid("for_arr")
        len_tmp = self._uid("for_len")
        idx_tmp = self._uid("for_idx")

        fn.add_local(arr_tmp, "i32")
        fn.add_local(len_tmp, "i32")
        fn.add_local(idx_tmp, "i32")
        fn.add_local(stmt.var, elem_wt)
        self._locals_sem[stmt.var] = elem_sem

        fn.emit(
            f"local.tee ${arr_tmp}",
            "i32.load",
            f"local.set ${len_tmp}",
            "i32.const 0",
            f"local.set ${idx_tmp}",
        )

        self._loop_stack.append((brk, cnt))
        fn.emit(
            f"block ${brk}",
            f"loop ${cnt}",
            f"local.get ${idx_tmp}",
            f"local.get ${len_tmp}",
            "i32.ge_s",
            f"br_if ${brk}",
            f"local.get ${arr_tmp}",
            "i32.const 8",
            "i32.add",
            f"local.get ${idx_tmp}",
            "i32.const 8",
            "i32.mul",
            "i32.add",
            f"{elem_wt}.load",
            f"local.set ${stmt.var}",
        )
        self._compile_stmt(stmt.body)
        fn.emit(
            f"local.get ${idx_tmp}",
            "i32.const 1",
            "i32.add",
            f"local.set ${idx_tmp}",
            f"br ${cnt}",
            "end",
            "end",
        )
        self._loop_stack.pop()

    def _extract_range_bounds(
        self, expr: Expr
    ) -> Optional[tuple[Expr, Expr, bool]]:
        if isinstance(expr, RangeExpr):
            return expr.start, expr.end, expr.inclusive
        if (
            isinstance(expr, CallExpr)
            and isinstance(expr.callee, Ident)
            and expr.callee.name == "range"
        ):
            if len(expr.args) == 1:
                zero = Literal(value=0, kind="int", span=expr.span)
                return zero, expr.args[0], False
            if len(expr.args) >= 2:
                return expr.args[0], expr.args[1], False
        return None

    def _compile_match_stmt(self, stmt: MatchStmt) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn
        subj_sem = self._compile_expr(stmt.subject)
        subj_tmp = self._uid("match_subj")
        fn.add_local(subj_tmp, _sem_to_wasm(subj_sem))
        fn.emit(f"local.set ${subj_tmp}")

        done_lbl = self._uid("match_done")
        fn.emit(f"block ${done_lbl}")
        for arm in stmt.arms:
            self._emit_pattern_check(arm.pattern, subj_tmp, subj_sem)
            if arm.guard is not None:
                fn.emit("if")
                g_sem = self._compile_expr(arm.guard)
                self._ensure_bool_i32(g_sem)
                fn.emit("if")
                self._emit_arm_action(arm.body, arm.value)
                fn.emit(f"br ${done_lbl}", "end", "end")
            else:
                fn.emit("if")
                self._emit_arm_action(arm.body, arm.value)
                fn.emit(f"br ${done_lbl}", "end")
        fn.emit("end")

    def _emit_arm_action(
        self, body: Optional[BlockStmt], value: Optional[Expr]
    ) -> None:
        assert self._cur_fn is not None
        if body is not None:
            self._compile_stmt(body)
        elif value is not None:
            v_sem = self._compile_expr(value)
            if v_sem != "void":
                self._cur_fn.emit("drop")

    def _emit_pattern_check(
        self, pat: Any, subj_tmp: str, subj_sem: str
    ) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn

        if isinstance(pat, WildcardPattern) or (
            isinstance(pat, Ident) and pat.name == "_"
        ):
            fn.emit("i32.const 1")
            return

        if isinstance(pat, Ident):
            # Variable binding pattern captures the subject and always matches
            fn.add_local(pat.name, _sem_to_wasm(subj_sem))
            self._locals_sem[pat.name] = subj_sem
            fn.emit(f"local.get ${subj_tmp}", f"local.set ${pat.name}", "i32.const 1")
            return

        if isinstance(pat, OrPattern):
            self._emit_pattern_check(pat.left, subj_tmp, subj_sem)
            self._emit_pattern_check(pat.right, subj_tmp, subj_sem)
            fn.emit("i32.or")
            return

        lit = pat.value if isinstance(pat, LiteralPattern) else pat
        if isinstance(lit, Expr):
            fn.emit(f"local.get ${subj_tmp}")
            p_sem = self._compile_expr(lit)
            self._coerce_stack(p_sem, subj_sem)
            if subj_sem == "str":
                fn.emit("call $__str_eq")
            elif subj_sem == "float":
                fn.emit("f64.eq")
            elif subj_sem == "bool":
                fn.emit("i32.eq")
            else:
                fn.emit("i64.eq")
            return

        fn.emit("i32.const 1")

    # -- Expression compilation ---------------------------------------------

    def _compile_expr(self, expr: Expr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn

        if isinstance(expr, Literal):
            if expr.kind == "float":
                fn.emit(f64_const(float(expr.value)))
                return "float"
            if expr.kind == "bool":
                fn.emit(i32_const(1 if expr.value else 0))
                return "bool"
            if expr.kind == "str":
                ptr = self.mod.add_string_constant(str(expr.value))
                fn.emit(i32_const(ptr))
                return "str"
            if expr.kind == "nil":
                fn.emit(i64_const(0))
                return "int"
            fn.emit(i64_const(int(expr.value)))
            return "int"

        if isinstance(expr, InterpolatedStr):
            from ..parser import parse as _parse_sub

            emitted_any = False
            for part in expr.parts:
                if isinstance(part, tuple) and len(part) == 2:
                    p_kind, p_val = part
                    if p_kind == "str":
                        if p_val == "":
                            continue
                        ptr = self.mod.add_string_constant(str(p_val))
                        fn.emit(i32_const(ptr))
                    elif isinstance(p_val, Expr):
                        p_sem = self._compile_expr(p_val)
                        self._convert_to_str(p_sem)
                    else:
                        sub_prog = _parse_sub(str(p_val), "<interp>")
                        if sub_prog.body and isinstance(sub_prog.body[0], ExprStmt):
                            p_sem = self._compile_expr(sub_prog.body[0].expr)
                            self._convert_to_str(p_sem)
                        else:
                            fn.emit(i32_const(self._ptr_empty))
                elif isinstance(part, str):
                    if part == "":
                        continue
                    ptr = self.mod.add_string_constant(part)
                    fn.emit(i32_const(ptr))
                else:
                    p_sem = self._compile_expr(part)
                    self._convert_to_str(p_sem)

                if emitted_any:
                    fn.emit("call $__str_concat")
                emitted_any = True

            if not emitted_any:
                fn.emit(i32_const(self._ptr_empty))
            return "str"

        if isinstance(expr, (Ident, SelfExpr)):
            name = "self" if isinstance(expr, SelfExpr) else expr.name
            if name in self._locals_sem:
                fn.emit(f"local.get ${name}")
                return self._locals_sem[name]
            if name in self._constants:
                c_val, c_sem = self._constants[name]
                return self._compile_expr(
                    Literal(value=c_val, kind=c_sem, span=expr.span)
                )
            fn.emit("i64.const 0")
            return "int"

        if isinstance(expr, AwaitExpr):
            return self._compile_expr(expr.value)

        if isinstance(expr, CastExpr):
            v_sem = self._compile_expr(expr.value)
            target_sem = _typeref_to_sem(expr.target)
            return self._coerce_stack(v_sem, target_sem)

        if isinstance(expr, UnaryOp):
            v_sem = self._compile_expr(expr.operand)
            if expr.op == "-":
                if v_sem == "float":
                    fn.emit("f64.neg")
                    return "float"
                tmp = self._uid("neg")
                fn.add_local(tmp, "i64")
                fn.emit(f"local.set ${tmp}", "i64.const 0", f"local.get ${tmp}", "i64.sub")
                return "int"
            if expr.op in ("!", "not"):
                self._ensure_bool_i32(v_sem)
                fn.emit("i32.eqz")
                return "bool"
            return v_sem

        if isinstance(expr, TernaryExpr):
            c_sem = self._compile_expr(expr.condition)
            self._ensure_bool_i32(c_sem)
            then_guess = self._guess_expr_sem(expr.then_val, self._locals_sem)
            res_wt = _sem_to_wasm(then_guess)
            fn.emit(f"if (result {res_wt})" if res_wt else "if")
            t_sem = self._compile_expr(expr.then_val)
            self._coerce_stack(t_sem, then_guess)
            fn.emit("else")
            e_sem = self._compile_expr(expr.else_val)
            self._coerce_stack(e_sem, then_guess)
            fn.emit("end")
            return then_guess

        if isinstance(expr, TypeMatchExpr):
            return self._compile_type_match_expr(expr)

        if isinstance(expr, BinOp):
            return self._compile_binop(expr)

        if isinstance(expr, CallExpr):
            return self._compile_call(expr)

        if isinstance(expr, ListExpr):
            return self._compile_list(expr)

        if isinstance(expr, TupleExpr):
            return self._compile_list(ListExpr(elements=expr.elements, span=expr.span))

        if isinstance(expr, IndexExpr):
            return self._compile_index(expr)

        if isinstance(expr, StructLiteral):
            return self._compile_struct_literal(expr)

        if isinstance(expr, FieldExpr):
            return self._compile_field_access(expr)

        fn.emit("i64.const 0")
        return "int"

    def _compile_type_match_expr(self, expr: TypeMatchExpr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        subj_sem = self._compile_expr(expr.subject)
        subj_tmp = self._uid("tmatch_s")
        fn.add_local(subj_tmp, _sem_to_wasm(subj_sem))
        fn.emit(f"local.set ${subj_tmp}")

        res_sem = "int"
        for arm in expr.arms:
            if arm.value is not None:
                res_sem = self._guess_expr_sem(arm.value, self._locals_sem)
                break
        res_tmp = self._uid("tmatch_r")
        fn.add_local(res_tmp, _sem_to_wasm(res_sem))
        self._emit_default_value(res_sem)
        fn.emit(f"local.set ${res_tmp}")

        done_lbl = self._uid("tmatch_done")
        fn.emit(f"block ${done_lbl}")
        for arm in expr.arms:
            self._emit_pattern_check(arm.pattern, subj_tmp, subj_sem)
            if arm.guard is not None:
                fn.emit("if")
                g_sem = self._compile_expr(arm.guard)
                self._ensure_bool_i32(g_sem)
                fn.emit("if")
                self._emit_match_expr_arm(arm, res_tmp, res_sem)
                fn.emit(f"br ${done_lbl}", "end", "end")
            else:
                fn.emit("if")
                self._emit_match_expr_arm(arm, res_tmp, res_sem)
                fn.emit(f"br ${done_lbl}", "end")
        fn.emit("end", f"local.get ${res_tmp}")
        return res_sem

    def _emit_match_expr_arm(self, arm: Any, res_tmp: str, res_sem: str) -> None:
        assert self._cur_fn is not None
        fn = self._cur_fn
        if arm.value is not None:
            v_sem = self._compile_expr(arm.value)
            self._coerce_stack(v_sem, res_sem)
            fn.emit(f"local.set ${res_tmp}")
        elif arm.body is not None:
            stmts = arm.body.stmts
            for idx, s in enumerate(stmts):
                if idx == len(stmts) - 1 and isinstance(s, ExprStmt):
                    v_sem = self._compile_expr(s.expr)
                    self._coerce_stack(v_sem, res_sem)
                    fn.emit(f"local.set ${res_tmp}")
                else:
                    self._compile_stmt(s)

    def _compile_binop(self, expr: BinOp) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn

        # Pipeline: `x |> f` or `x |> f(a, b)`
        if expr.op == "|>":
            if isinstance(expr.right, CallExpr):
                call_node = CallExpr(
                    callee=expr.right.callee,
                    args=[expr.left, *expr.right.args],
                    kwargs=expr.right.kwargs,
                    span=expr.span,
                )
                return self._compile_call(call_node)
            call_node = CallExpr(callee=expr.right, args=[expr.left], span=expr.span)
            return self._compile_call(call_node)

        # Short-circuit logical operators
        if expr.op in ("&&", "and"):
            l_sem = self._compile_expr(expr.left)
            self._ensure_bool_i32(l_sem)
            fn.emit("if (result i32)")
            r_sem = self._compile_expr(expr.right)
            self._ensure_bool_i32(r_sem)
            fn.emit("else", "i32.const 0", "end")
            return "bool"

        if expr.op in ("||", "or"):
            l_sem = self._compile_expr(expr.left)
            self._ensure_bool_i32(l_sem)
            fn.emit("if (result i32)", "i32.const 1", "else")
            r_sem = self._compile_expr(expr.right)
            self._ensure_bool_i32(r_sem)
            fn.emit("end")
            return "bool"

        l_guess = self._guess_expr_sem(expr.left, self._locals_sem)
        r_guess = self._guess_expr_sem(expr.right, self._locals_sem)

        # String concatenation or string comparison
        if expr.op == "+" and (l_guess == "str" or r_guess == "str"):
            l_sem = self._compile_expr(expr.left)
            self._convert_to_str(l_sem)
            r_sem = self._compile_expr(expr.right)
            self._convert_to_str(r_sem)
            fn.emit("call $__str_concat")
            return "str"

        if expr.op in ("==", "!=") and (l_guess == "str" or r_guess == "str"):
            l_sem = self._compile_expr(expr.left)
            self._convert_to_str(l_sem)
            r_sem = self._compile_expr(expr.right)
            self._convert_to_str(r_sem)
            fn.emit("call $__str_eq")
            if expr.op == "!=":
                fn.emit("i32.eqz")
            return "bool"

        # Numeric / boolean binary operation
        use_float = l_guess == "float" or r_guess == "float"
        if use_float:
            l_sem = self._compile_expr(expr.left)
            self._coerce_stack(l_sem, "float")
            r_sem = self._compile_expr(expr.right)
            self._coerce_stack(r_sem, "float")
            f_ops = {
                "+": "f64.add",
                "-": "f64.sub",
                "*": "f64.mul",
                "/": "f64.div",
                "==": "f64.eq",
                "!=": "f64.ne",
                "<": "f64.lt",
                ">": "f64.gt",
                "<=": "f64.le",
                ">=": "f64.ge",
            }
            fn.emit(f_ops.get(expr.op, "f64.add"))
            return "bool" if expr.op in ("==", "!=", "<", ">", "<=", ">=") else "float"

        l_sem = self._compile_expr(expr.left)
        self._coerce_stack(l_sem, "int")
        r_sem = self._compile_expr(expr.right)
        self._coerce_stack(r_sem, "int")

        if expr.op == "**":
            fn.emit("call $__pow_i64")
            return "int"

        i_ops = {
            "+": "i64.add",
            "-": "i64.sub",
            "*": "i64.mul",
            "/": "i64.div_s",
            "%": "i64.rem_s",
            "&": "i64.and",
            "|": "i64.or",
            "^": "i64.xor",
            "<<": "i64.shl",
            ">>": "i64.shr_s",
            "==": "i64.eq",
            "!=": "i64.ne",
            "<": "i64.lt_s",
            ">": "i64.gt_s",
            "<=": "i64.le_s",
            ">=": "i64.ge_s",
        }
        fn.emit(i_ops.get(expr.op, "i64.add"))
        return "bool" if expr.op in ("==", "!=", "<", ">", "<=", ">=") else "int"

    def _compile_call(self, expr: CallExpr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn

        # Extract qualified/method call names: io.println, http.get, Vec2.new, obj.method
        callee_name = ""
        receiver: Optional[Expr] = None
        if isinstance(expr.callee, Ident):
            callee_name = expr.callee.name
        elif isinstance(expr.callee, FieldExpr):
            if isinstance(expr.callee.obj, Ident) and expr.callee.obj.name in (
                "io",
                "std",
                "math",
                "http",
            ):
                callee_name = f"{expr.callee.obj.name}.{expr.callee.field}"
            elif (
                isinstance(expr.callee.obj, Ident)
                and f"{expr.callee.obj.name}__{expr.callee.field}" in self._fn_sigs
            ):
                callee_name = f"{expr.callee.obj.name}__{expr.callee.field}"
            else:
                receiver = expr.callee.obj
                callee_name = expr.callee.field

        # Struct instance method call (`p.sum()` -> `Pair__sum(p)`) takes priority
        # over collection builtins of the same name (`sum`, `len`).
        if receiver is not None:
            r_guess = self._guess_expr_sem(receiver, self._locals_sem)
            if r_guess.startswith("struct:"):
                sname = r_guess.split(":", 1)[1]
                mangled = f"{sname}__{callee_name}"
                if mangled in self._fn_sigs:
                    return self._emit_direct_call(
                        mangled, [receiver, *expr.args]
                    )

        # Host I/O: println / print
        if callee_name in ("println", "io.println", "print", "io.print"):
            helper = (
                "$__println_str"
                if callee_name in ("println", "io.println")
                else "$__print_str"
            )
            if not expr.args:
                fn.emit(f"i32.const {self._ptr_empty}", f"call {helper}")
                return "void"
            for idx, arg in enumerate(expr.args):
                if idx > 0:
                    sp = self.mod.add_string_constant(" ")
                    fn.emit(f"i32.const {sp}")
                a_sem = self._compile_expr(arg)
                self._convert_to_str(a_sem)
                if idx > 0:
                    fn.emit("call $__str_concat")
            fn.emit(f"call {helper}")
            return "void"

        # Host HTTP bridge: http_get(url) / http.get(url)
        if callee_name in ("http_get", "http.get"):
            if expr.args:
                u_sem = self._compile_expr(expr.args[0])
                self._convert_to_str(u_sem)
            else:
                fn.emit(f"i32.const {self._ptr_empty}")
            fn.emit("call $__http_get_str")
            return "str"

        # Built-in conversions & math/collection intrinsics
        if callee_name in ("str", "to_string") and expr.args:
            a_sem = self._compile_expr(expr.args[0])
            self._convert_to_str(a_sem)
            return "str"

        if callee_name == "int" and expr.args:
            a_sem = self._compile_expr(expr.args[0])
            return self._coerce_stack(a_sem, "int")

        if callee_name == "float" and expr.args:
            a_sem = self._compile_expr(expr.args[0])
            return self._coerce_stack(a_sem, "float")

        if callee_name == "len":
            target_arg = receiver if receiver is not None else expr.args[0]
            t_sem = self._compile_expr(target_arg)
            if t_sem == "str":
                fn.emit("call $__strlen", "i64.extend_i32_u")
            elif t_sem.startswith("list:"):
                fn.emit("i32.load", "i64.extend_i32_s")
            else:
                if _sem_to_wasm(t_sem) != "":
                    fn.emit("drop")
                fn.emit("i64.const 0")
            return "int"

        if callee_name in ("sqrt", "math.sqrt") and (receiver or expr.args):
            arg = receiver if receiver is not None else expr.args[0]
            a_sem = self._compile_expr(arg)
            self._coerce_stack(a_sem, "float")
            fn.emit("f64.sqrt")
            return "float"

        if callee_name in ("abs", "math.abs") and (receiver or expr.args):
            arg = receiver if receiver is not None else expr.args[0]
            a_sem = self._compile_expr(arg)
            if a_sem == "float":
                fn.emit("f64.abs")
                return "float"
            tmp = self._uid("abs")
            fn.add_local(tmp, "i64")
            fn.emit(
                f"local.tee ${tmp}",
                "i64.const 0",
                "i64.lt_s",
                "if (result i64)",
                "i64.const 0",
                f"local.get ${tmp}",
                "i64.sub",
                "else",
                f"local.get ${tmp}",
                "end",
            )
            return "int"

        if callee_name in ("floor", "math.floor", "ceil", "math.ceil") and (
            receiver or expr.args
        ):
            arg = receiver if receiver is not None else expr.args[0]
            a_sem = self._compile_expr(arg)
            self._coerce_stack(a_sem, "float")
            fn.emit("f64.floor" if "floor" in callee_name else "f64.ceil")
            return "float"

        if callee_name == "sum" and (receiver or expr.args):
            arg = receiver if receiver is not None else expr.args[0]
            return self._compile_list_sum(arg)

        # User-defined function call (including pipelined struct method fallback)
        if callee_name in self._fn_sigs:
            return self._emit_direct_call(callee_name, expr.args)

        if expr.args:
            first_guess = self._guess_expr_sem(expr.args[0], self._locals_sem)
            if first_guess.startswith("struct:"):
                sname = first_guess.split(":", 1)[1]
                mangled = f"{sname}__{callee_name}"
                if mangled in self._fn_sigs:
                    return self._emit_direct_call(mangled, expr.args)

        for arg in expr.args:
            s = self._compile_expr(arg)
            if s != "void":
                fn.emit("drop")
        fn.emit("i64.const 0")
        return "int"

    def _emit_direct_call(self, fn_name: str, args: list[Expr]) -> str:
        assert self._cur_fn is not None
        sig = self._fn_sigs[fn_name]
        for idx, param_sem in enumerate(sig.param_types):
            if idx < len(args):
                a_sem = self._compile_expr(args[idx])
                self._coerce_stack(a_sem, param_sem)
            else:
                self._emit_default_value(param_sem)
        self._cur_fn.emit(f"call ${sig.wasm_name}")
        return sig.ret_type

    def _compile_list(self, expr: ListExpr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        elem_sem = "int"
        if expr.elements:
            elem_sem = self._guess_expr_sem(expr.elements[0], self._locals_sem)
        elem_wt = _sem_to_wasm(elem_sem)
        count = len(expr.elements)
        byte_size = 8 + count * 8

        ptr_tmp = self._uid("list_ptr")
        fn.add_local(ptr_tmp, "i32")
        fn.emit(
            f"i32.const {byte_size}",
            "call $__alloc",
            f"local.tee ${ptr_tmp}",
            f"i32.const {count}",
            "i32.store",
            f"local.get ${ptr_tmp}",
            "i32.const 4",
            "i32.add",
            f"i32.const {count}",
            "i32.store",
        )
        for idx, item in enumerate(expr.elements):
            fn.emit(f"local.get ${ptr_tmp}", f"i32.const {8 + idx * 8}", "i32.add")
            v_sem = self._compile_expr(item)
            self._coerce_stack(v_sem, elem_sem)
            fn.emit(f"{elem_wt}.store")

        fn.emit(f"local.get ${ptr_tmp}")
        return f"list:{elem_sem}"

    def _compile_list_sum(self, list_expr: Expr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        l_sem = self._compile_expr(list_expr)
        elem_sem = l_sem.split(":", 1)[1] if ":" in l_sem else "int"
        is_flt = elem_sem == "float"
        acc_wt = "f64" if is_flt else "i64"

        arr_tmp = self._uid("sum_arr")
        len_tmp = self._uid("sum_len")
        idx_tmp = self._uid("sum_i")
        acc_tmp = self._uid("sum_acc")
        brk = self._uid("sum_brk")
        lp = self._uid("sum_lp")

        fn.add_local(arr_tmp, "i32")
        fn.add_local(len_tmp, "i32")
        fn.add_local(idx_tmp, "i32")
        fn.add_local(acc_tmp, acc_wt)

        fn.emit(
            f"local.tee ${arr_tmp}",
            "i32.load",
            f"local.set ${len_tmp}",
            "i32.const 0",
            f"local.set ${idx_tmp}",
            "f64.const 0.0" if is_flt else "i64.const 0",
            f"local.set ${acc_tmp}",
            f"block ${brk}",
            f"loop ${lp}",
            f"local.get ${idx_tmp}",
            f"local.get ${len_tmp}",
            "i32.ge_s",
            f"br_if ${brk}",
            f"local.get ${acc_tmp}",
            f"local.get ${arr_tmp}",
            "i32.const 8",
            "i32.add",
            f"local.get ${idx_tmp}",
            "i32.const 8",
            "i32.mul",
            "i32.add",
            f"{acc_wt}.load",
            f"{acc_wt}.add",
            f"local.set ${acc_tmp}",
            f"local.get ${idx_tmp}",
            "i32.const 1",
            "i32.add",
            f"local.set ${idx_tmp}",
            f"br ${lp}",
            "end",
            "end",
            f"local.get ${acc_tmp}",
        )
        return "float" if is_flt else "int"

    def _compile_index(self, expr: IndexExpr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        obj_sem = self._compile_expr(expr.obj)
        elem_sem = obj_sem.split(":", 1)[1] if ":" in obj_sem else "int"
        elem_wt = _sem_to_wasm(elem_sem)

        arr_tmp = self._uid("idx_arr")
        fn.add_local(arr_tmp, "i32")
        fn.emit(f"local.set ${arr_tmp}")
        idx_sem = self._compile_expr(expr.index)
        self._coerce_stack(idx_sem, "int")
        fn.emit(
            "i32.wrap_i64",
            "i32.const 8",
            "i32.mul",
            "i32.const 8",
            "i32.add",
            f"local.get ${arr_tmp}",
            "i32.add",
            f"{elem_wt}.load",
        )
        return elem_sem

    def _compile_struct_literal(self, expr: StructLiteral) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        layout = self._structs.get(expr.name)
        if layout is None:
            fields = [
                (fname, self._guess_expr_sem(fexpr, self._locals_sem))
                for fname, fexpr in expr.fields
            ]
            layout = _StructLayout(expr.name, fields)
            self._structs[expr.name] = layout

        ptr_tmp = self._uid("struct_ptr")
        fn.add_local(ptr_tmp, "i32")
        fn.emit(
            f"i32.const {max(8, len(layout.fields) * 8)}",
            "call $__alloc",
            f"local.set ${ptr_tmp}",
        )
        provided = dict(expr.fields)
        for idx, (fname, fsem) in enumerate(layout.fields):
            fn.emit(f"local.get ${ptr_tmp}", f"i32.const {idx * 8}", "i32.add")
            if fname in provided:
                v_sem = self._compile_expr(provided[fname])
                self._coerce_stack(v_sem, fsem)
            else:
                self._emit_default_value(fsem)
            fn.emit(f"{_sem_to_wasm(fsem)}.store")

        fn.emit(f"local.get ${ptr_tmp}")
        return f"struct:{expr.name}"

    def _compile_field_access(self, expr: FieldExpr) -> str:
        assert self._cur_fn is not None
        fn = self._cur_fn
        if isinstance(expr.obj, Ident) and expr.obj.name in ("math", "Math"):
            if expr.field.lower() == "pi":
                fn.emit("f64.const 3.141592653589793")
                return "float"
            if expr.field.lower() == "e":
                fn.emit("f64.const 2.718281828459045")
                return "float"

        obj_sem = self._compile_expr(expr.obj)
        if obj_sem.startswith("struct:"):
            sname = obj_sem.split(":", 1)[1]
            layout = self._structs.get(sname)
            if layout is not None:
                offset, fsem = layout.offset_of(expr.field)
                if offset > 0:
                    fn.emit(f"i32.const {offset}", "i32.add")
                fn.emit(f"{_sem_to_wasm(fsem)}.load")
                return fsem

        fn.emit("drop", "i64.const 0")
        return "int"


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------


def compile_to_wasm(source: str, module_name: str = "lateralus_module") -> WasmModule:
    """Parse and compile a LATERALUS source string into a `WasmModule`."""
    from ..parser import parse

    ast = parse(source, "<wasm>")
    gen = LateralusWasmGenerator(module_name=module_name)
    return gen.compile_program(ast)


def compile_to_wasm_bytes(
    source: str, module_name: str = "lateralus_module"
) -> bytes:
    """Compile LATERALUS source directly into WebAssembly 1.0 `.wasm` bytes."""
    return compile_to_wasm(source, module_name=module_name).to_bytes()


def expression_to_wat(expr: str) -> str:
    """Compile a LATERALUS expression to WAT instructions."""
    c = WasmCompiler()
    return c.compile_expression_to_wat(expr)


def get_wasm_builtins() -> dict[str, Any]:
    return {
        "WasmModule": WasmModule,
        "WasmCompiler": WasmCompiler,
        "compile_to_wasm": compile_to_wasm,
        "compile_to_wasm_bytes": compile_to_wasm_bytes,
        "expression_to_wat": expression_to_wat,
    }
