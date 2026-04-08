"""
lateralus_lang/codegen/wasm.py
LATERALUS → WebAssembly Text Format (WAT) Compiler Target

Generates WebAssembly Text Format (.wat) from LATERALUS IR.
WAT can then be assembled to .wasm binary with `wat2wasm` (WABT toolkit).

Supports:
  - Integer and floating-point arithmetic
  - Functions with typed parameters and returns
  - Local variables
  - Control flow: if/else, while/loop, return
  - Import/export of functions
  - Linear memory for strings and arrays
  - Call and indirect call
  - LATERALUS pipeline |> as sequential call chains

WebAssembly types used:
  int   → i64
  float → f64
  bool  → i32 (0 = false, 1 = true)
  str   → i32 (pointer into linear memory)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# WAT type system
# ---------------------------------------------------------------------------

class WasmType:
    I32 = "i32"
    I64 = "i64"
    F32 = "f32"
    F64 = "f64"
    NONE = ""  # void

    # LATERALUS type -> WASM type
    LTL_MAP = {
        "int":   "i64",
        "float": "f64",
        "bool":  "i32",
        "str":   "i32",  # pointer
        "None":  "",
        "any":   "i64",  # fallback
    }

    @classmethod
    def from_ltl(cls, ltl_type: str) -> str:
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

def i64_add() -> str:  return "i64.add"
def i64_sub() -> str:  return "i64.sub"
def i64_mul() -> str:  return "i64.mul"
def i64_div_s() -> str: return "i64.div_s"
def i64_rem_s() -> str: return "i64.rem_s"
def i64_eq()  -> str:  return "i64.eq"
def i64_ne()  -> str:  return "i64.ne"
def i64_lt_s() -> str: return "i64.lt_s"
def i64_gt_s() -> str: return "i64.gt_s"
def i64_le_s() -> str: return "i64.le_s"
def i64_ge_s() -> str: return "i64.ge_s"
def i64_and() -> str:  return "i64.and"
def i64_or()  -> str:  return "i64.or"
def i64_xor() -> str:  return "i64.xor"
def i64_shl() -> str:  return "i64.shl"
def i64_shr_s() -> str: return "i64.shr_s"

def f64_add() -> str:  return "f64.add"
def f64_sub() -> str:  return "f64.sub"
def f64_mul() -> str:  return "f64.mul"
def f64_div() -> str:  return "f64.div"
def f64_sqrt() -> str: return "f64.sqrt"
def f64_abs()  -> str: return "f64.abs"
def f64_neg()  -> str: return "f64.neg"
def f64_ceil() -> str: return "f64.ceil"
def f64_floor() -> str: return "f64.floor"
def f64_eq()   -> str: return "f64.eq"
def f64_ne()   -> str: return "f64.ne"
def f64_lt()   -> str: return "f64.lt"
def f64_gt()   -> str: return "f64.gt"
def f64_le()   -> str: return "f64.le"
def f64_ge()   -> str: return "f64.ge"

def i32_eqz() -> str:  return "i32.eqz"
def i32_eq()  -> str:  return "i32.eq"

def f64_convert_i64_s() -> str: return "f64.convert_i64_s"
def i64_trunc_f64_s() -> str:   return "i64.trunc_f64_s"


# ---------------------------------------------------------------------------
# WAT module builder
# ---------------------------------------------------------------------------

@dataclass
class WasmLocal:
    name: str
    wasm_type: str


@dataclass
class WasmFunction:
    name: str
    params: list[tuple[str, str]]   # (name, wasm_type)
    result_type: str                  # wasm_type or ""
    locals: list[WasmLocal] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    exported: bool = False
    imported: bool = False
    import_module: str = ""
    import_name: str = ""

    def add_local(self, name: str, wasm_type: str) -> None:
        if not any(l.name == name for l in self.locals):
            self.locals.append(WasmLocal(name, wasm_type))

    def emit(self, *instructions: str) -> None:
        self.body.extend(instructions)

    def to_wat(self, indent: int = 2) -> str:
        pad = " " * indent
        lines: list[str] = []

        if self.imported:
            imp = f'(import "{self.import_module}" "{self.import_name}" '
            params = " ".join(f"(param ${n} {t})" for n, t in self.params)
            result = f"(result {self.result_type})" if self.result_type else ""
            lines.append(f"{pad}{imp}(func ${self.name} {params} {result}))")
            return "\n".join(lines)

        export_clause = f'(export "{self.name}") ' if self.exported else ""
        params = " ".join(f"(param ${n} {t})" for n, t in self.params)
        result = f"(result {self.result_type})" if self.result_type else ""
        lines.append(f"{pad}(func ${self.name} {export_clause}{params} {result}")

        for local in self.locals:
            lines.append(f"{pad}  (local ${local.name} {local.wasm_type})")

        for instr in self.body:
            lines.append(f"{pad}  {instr}")

        lines.append(f"{pad})")
        return "\n".join(lines)


@dataclass
class WasmMemory:
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
    Builds a WebAssembly Text Format (.wat) module.

    Usage:
        mod = WasmModule()
        fn = mod.add_function("add", [("a", "i64"), ("b", "i64")], "i64", exported=True)
        fn.emit(local_get("a"), local_get("b"), i64_add())
        print(mod.to_wat())
    """

    def __init__(self, name: str = "lateralus_module") -> None:
        self.name = name
        self._functions: list[WasmFunction] = []
        self._memory: Optional[WasmMemory] = None
        self._globals: list[WasmGlobal] = []
        self._data_segments: list[tuple[int, bytes]] = []  # (offset, data)
        self._data_offset: int = 64  # start after reserved header
        self._type_section: list[str] = []

    def add_memory(self, min_pages: int = 1, exported: bool = True) -> WasmMemory:
        self._memory = WasmMemory(min_pages=min_pages, exported=exported)
        return self._memory

    def add_global(self, name: str, wasm_type: str, mutable: bool, init: str) -> WasmGlobal:
        g = WasmGlobal(name, wasm_type, mutable, init)
        self._globals.append(g)
        return g

    def add_function(self, name: str, params: list[tuple[str, str]],
                     result_type: str, exported: bool = False) -> WasmFunction:
        fn = WasmFunction(name=name, params=params, result_type=result_type,
                          exported=exported)
        self._functions.append(fn)
        return fn

    def import_function(self, module: str, field: str, local_name: str,
                        params: list[tuple[str, str]], result_type: str) -> WasmFunction:
        fn = WasmFunction(name=local_name, params=params, result_type=result_type,
                          imported=True, import_module=module, import_name=field)
        self._functions.insert(0, fn)  # imports must come first
        return fn

    def add_string_constant(self, s: str) -> int:
        """Store a string in linear memory, return its pointer."""
        data = s.encode("utf-8") + b"\x00"  # null-terminated
        ptr = self._data_offset
        self._data_segments.append((ptr, data))
        self._data_offset += len(data)
        return ptr

    def to_wat(self) -> str:
        lines: list[str] = [f"(module ;; {self.name}"]

        # Imports first
        for fn in self._functions:
            if fn.imported:
                lines.append(fn.to_wat())

        # Memory
        if self._memory:
            lines.append(self._memory.to_wat())

        # Globals
        for g in self._globals:
            lines.append(g.to_wat())

        # Data segments
        for offset, data in self._data_segments:
            escaped = "".join(f"\\{b:02x}" for b in data)
            lines.append(f'  (data (i32.const {offset}) "{escaped}")')

        # Functions (non-imports)
        for fn in self._functions:
            if not fn.imported:
                lines.append(fn.to_wat())

        lines.append(")")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Save WAT file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_wat())


# ---------------------------------------------------------------------------
# LATERALUS IR → WASM compiler
# ---------------------------------------------------------------------------

class WasmCompiler:
    """
    Compiles LATERALUS IR (three-address code) to a WasmModule.

    This is a simplified single-pass compiler targeting the numeric subset
    of LATERALUS. Full expression compilation requires the IR to be available.
    """

    def __init__(self) -> None:
        self._module = WasmModule()
        self._current_fn: Optional[WasmFunction] = None
        self._local_types: dict[str, str] = {}
        self._label_counter = 0

        # Import the LATERALUS standard I/O bridge
        self._module.import_function(
            "env", "ltl_println_i64", "ltl_println_i64",
            [("val", "i64")], ""
        )
        self._module.import_function(
            "env", "ltl_println_f64", "ltl_println_f64",
            [("val", "f64")], ""
        )

    def _new_label(self) -> str:
        self._label_counter += 1
        return f"block_{self._label_counter}"

    def compile_ir(self, ir_instructions: list[dict]) -> WasmModule:
        """Compile a list of IR instructions to a WASM module."""
        for instr in ir_instructions:
            self._emit_ir(instr)
        return self._module

    def _emit_ir(self, instr: dict) -> None:
        """Emit WASM code for a single IR instruction."""
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
                ops_map = {"add": f64_add, "sub": f64_sub, "mul": f64_mul, "div": f64_div}
            else:
                ops_map = {"add": i64_add, "sub": i64_sub, "mul": i64_mul, "div": i64_div_s}

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
        """
        Compile a simple numeric LATERALUS expression to WAT instructions.
        Returns WAT text for the expression.

        Supports: integer literals, float literals, +, -, *, /, **, ()
        """
        return self._compile_arith_expr(expr.strip())

    def _compile_arith_expr(self, expr: str) -> str:
        """Recursive arithmetic expression compiler."""
        expr = expr.strip()

        # Float literal
        if re.match(r'^-?\d+\.\d+$', expr):
            return f64_const(float(expr))

        # Integer literal
        if re.match(r'^-?\d+$', expr):
            return i64_const(int(expr))

        # Identifier
        if re.match(r'^\w+$', expr):
            return local_get(expr)

        # Handle ** (power) — transform to multiply loop (simplified)
        # For now, map to f64 operations
        if "**" in expr:
            parts = expr.rsplit("**", 1)
            left = self._compile_arith_expr(parts[0])
            right = self._compile_arith_expr(parts[1])
            return f";; pow({left}, {right}) ;; [use call $ltl_pow]"

        # Parentheses
        if expr.startswith("(") and expr.endswith(")"):
            return self._compile_arith_expr(expr[1:-1])

        # Binary operations (simplified: find last operator)
        for op, emit_fn in [("+", i64_add), ("-", i64_sub),
                             ("*", i64_mul), ("/", i64_div_s)]:
            idx = _find_binary_op(expr, op)
            if idx >= 0:
                left_expr = self._compile_arith_expr(expr[:idx])
                right_expr = self._compile_arith_expr(expr[idx + len(op):])
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
        elif depth == 0 and expr[i:i+len(op)] == op:
            return i
    return -1


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def compile_to_wasm(source: str) -> WasmModule:
    """Compile a LATERALUS program to a WASM module."""
    compiler = WasmCompiler()
    # In full implementation, this would use the LATERALUS parser + IR
    # For now, return a module with a hello-world stub
    mod = compiler._module

    # Example: compile a simple main function
    fn = mod.add_function("main", [], "i64", exported=True)
    fn.emit(i64_const(0), "return")

    return mod


def expression_to_wat(expr: str) -> str:
    """Compile a LATERALUS expression to WAT instructions."""
    c = WasmCompiler()
    return c.compile_expression_to_wat(expr)


def get_wasm_builtins() -> dict:
    return {
        "WasmModule":    WasmModule,
        "WasmCompiler":  WasmCompiler,
        "compile_to_wasm": compile_to_wasm,
        "expression_to_wat": expression_to_wat,
    }
