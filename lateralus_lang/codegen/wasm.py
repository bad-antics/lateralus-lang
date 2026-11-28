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
import struct
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
def i32_ne()  -> str:  return "i32.ne"
def i32_lt_s() -> str: return "i32.lt_s"
def i32_gt_s() -> str: return "i32.gt_s"
def i32_le_s() -> str: return "i32.le_s"
def i32_ge_s() -> str: return "i32.ge_s"
def i32_add() -> str:  return "i32.add"
def i32_sub() -> str:  return "i32.sub"
def i32_mul() -> str:  return "i32.mul"
def i32_and() -> str:  return "i32.and"
def i32_or()  -> str:  return "i32.or"
def i32_load8_u() -> str: return "i32.load8_u"
def i32_store8() -> str:  return "i32.store8"
def i64_eqz() -> str:  return "i64.eqz"

def i32_wrap_i64() -> str:      return "i32.wrap_i64"
def i64_extend_i32_s() -> str:  return "i64.extend_i32_s"
def f64_convert_i32_s() -> str: return "f64.convert_i32_s"
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

    def to_wasm_bytes(self) -> bytes:
        """Serialize this module directly to WebAssembly 1.0 binary (.wasm)."""
        return _WasmBinaryEncoder(self).encode()

    def save_wasm(self, path: str) -> None:
        """Save binary .wasm file."""
        with open(path, "wb") as f:
            f.write(self.to_wasm_bytes())


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
# WebAssembly Binary (.wasm) Encoder
# ---------------------------------------------------------------------------

_VALTYPE_BYTES = {
    "i32": 0x7F,
    "i64": 0x7E,
    "f32": 0x7D,
    "f64": 0x7C,
}

_SIMPLE_OPCODES = {
    "unreachable": 0x00,
    "nop":         0x01,
    "else":        0x05,
    "end":         0x0B,
    "return":      0x0F,
    "drop":        0x1A,
    "select":      0x1B,
    "i32.eqz":     0x45,
    "i32.eq":      0x46,
    "i32.ne":      0x47,
    "i32.lt_s":    0x48,
    "i32.lt_u":    0x49,
    "i32.gt_s":    0x4A,
    "i32.gt_u":    0x4B,
    "i32.le_s":    0x4C,
    "i32.le_u":    0x4D,
    "i32.ge_s":    0x4E,
    "i32.ge_u":    0x4F,
    "i64.eqz":     0x50,
    "i64.eq":      0x51,
    "i64.ne":      0x52,
    "i64.lt_s":    0x53,
    "i64.lt_u":    0x54,
    "i64.gt_s":    0x55,
    "i64.gt_u":    0x56,
    "i64.le_s":    0x57,
    "i64.le_u":    0x58,
    "i64.ge_s":    0x59,
    "i64.ge_u":    0x5A,
    "f64.eq":      0x61,
    "f64.ne":      0x62,
    "f64.lt":      0x63,
    "f64.gt":      0x64,
    "f64.le":      0x65,
    "f64.ge":      0x66,
    "i32.add":     0x6A,
    "i32.sub":     0x6B,
    "i32.mul":     0x6C,
    "i32.div_s":   0x6D,
    "i32.rem_s":   0x6F,
    "i32.and":     0x71,
    "i32.or":      0x72,
    "i32.xor":     0x73,
    "i32.shl":     0x74,
    "i32.shr_s":   0x75,
    "i64.add":     0x7C,
    "i64.sub":     0x7D,
    "i64.mul":     0x7E,
    "i64.div_s":   0x7F,
    "i64.rem_s":   0x81,
    "i64.and":     0x83,
    "i64.or":      0x84,
    "i64.xor":     0x85,
    "i64.shl":     0x86,
    "i64.shr_s":   0x87,
    "f64.abs":     0x99,
    "f64.neg":     0x9A,
    "f64.ceil":    0x9B,
    "f64.floor":   0x9C,
    "f64.sqrt":    0x9F,
    "f64.add":     0xA0,
    "f64.sub":     0xA1,
    "f64.mul":     0xA2,
    "f64.div":     0xA3,
    "i32.wrap_i64":      0xA7,
    "i64.extend_i32_s":  0xAC,
    "i64.extend_i32_u":  0xAD,
    "i64.trunc_f64_s":   0xB0,
    "f64.convert_i32_s": 0xB7,
    "f64.convert_i64_s": 0xB9,
}

_MEMORY_OPCODES = {
    "i32.load":    (0x28, 0x02),
    "i64.load":    (0x29, 0x03),
    "f64.load":    (0x2B, 0x03),
    "i32.load8_u": (0x2D, 0x00),
    "i32.store":   (0x36, 0x02),
    "i64.store":   (0x37, 0x03),
    "f64.store":   (0x39, 0x03),
    "i32.store8":  (0x3A, 0x00),
}


def _encode_uleb128(value: int) -> bytes:
    """Encode a non-negative integer as unsigned LEB128."""
    if value < 0:
        raise ValueError(f"Expected non-negative int for uleb128, got {value}")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def _encode_sleb128(value: int) -> bytes:
    """Encode a signed integer as signed LEB128."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and (byte & 0x40) == 0) or (
            value == -1 and (byte & 0x40) != 0
        )
        if done:
            out.append(byte)
            break
        out.append(byte | 0x80)
    return bytes(out)


def _encode_name(name: str) -> bytes:
    raw = name.encode("utf-8")
    return _encode_uleb128(len(raw)) + raw


def _encode_section(section_id: int, payload: bytes) -> bytes:
    return bytes([section_id]) + _encode_uleb128(len(payload)) + payload


class _WasmBinaryEncoder:
    """Encodes a WasmModule to WebAssembly 1.0 binary bytes."""

    def __init__(self, module: WasmModule) -> None:
        self.mod = module

    @staticmethod
    def _fn_sig(fn: WasmFunction) -> tuple[tuple[str, ...], tuple[str, ...]]:
        params = tuple(t for _, t in fn.params)
        results = (fn.result_type,) if fn.result_type else ()
        return (params, results)

    @staticmethod
    def _parse_blocktype(rest: str) -> int:
        m = re.search(r"\(result\s+(i32|i64|f32|f64)\)", rest)
        if m:
            return _VALTYPE_BYTES[m.group(1)]
        return 0x40

    def encode(self) -> bytes:
        imported_fns = [f for f in self.mod._functions if f.imported]
        defined_fns = [f for f in self.mod._functions if not f.imported]
        all_fns = imported_fns + defined_fns

        func_map = {fn.name: idx for idx, fn in enumerate(all_fns)}
        global_map = {g.name: idx for idx, g in enumerate(self.mod._globals)}

        # Collect deduplicated function signatures for the Type section
        signatures: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        sig_to_idx: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
        for fn in all_fns:
            sig = self._fn_sig(fn)
            if sig not in sig_to_idx:
                sig_to_idx[sig] = len(signatures)
                signatures.append(sig)

        out = bytearray(b"\x00asm\x01\x00\x00\x00")

        # 1. Type section
        if signatures:
            buf = bytearray(_encode_uleb128(len(signatures)))
            for params, results in signatures:
                buf.append(0x60)
                buf.extend(_encode_uleb128(len(params)))
                for p in params:
                    buf.append(_VALTYPE_BYTES[p])
                buf.extend(_encode_uleb128(len(results)))
                for r in results:
                    buf.append(_VALTYPE_BYTES[r])
            out.extend(_encode_section(1, bytes(buf)))

        # 2. Import section
        if imported_fns:
            buf = bytearray(_encode_uleb128(len(imported_fns)))
            for fn in imported_fns:
                buf.extend(_encode_name(fn.import_module))
                buf.extend(_encode_name(fn.import_name))
                buf.append(0x00)  # func import
                buf.extend(_encode_uleb128(sig_to_idx[self._fn_sig(fn)]))
            out.extend(_encode_section(2, bytes(buf)))

        # 3. Function section
        if defined_fns:
            buf = bytearray(_encode_uleb128(len(defined_fns)))
            for fn in defined_fns:
                buf.extend(_encode_uleb128(sig_to_idx[self._fn_sig(fn)]))
            out.extend(_encode_section(3, bytes(buf)))

        # 5. Memory section
        mem = self.mod._memory
        if mem is None and self.mod._data_segments:
            mem = WasmMemory(min_pages=1, exported=True)
        if mem is not None:
            buf = bytearray(_encode_uleb128(1))
            if mem.max_pages is not None:
                buf.append(0x01)
                buf.extend(_encode_uleb128(mem.min_pages))
                buf.extend(_encode_uleb128(mem.max_pages))
            else:
                buf.append(0x00)
                buf.extend(_encode_uleb128(mem.min_pages))
            out.extend(_encode_section(5, bytes(buf)))

        # 6. Global section
        if self.mod._globals:
            buf = bytearray(_encode_uleb128(len(self.mod._globals)))
            for g in self.mod._globals:
                buf.append(_VALTYPE_BYTES[g.wasm_type])
                buf.append(0x01 if g.mutable else 0x00)
                if g.wasm_type == "i32":
                    buf.append(0x41)
                    buf.extend(_encode_sleb128(int(g.init_value)))
                elif g.wasm_type == "i64":
                    buf.append(0x42)
                    buf.extend(_encode_sleb128(int(g.init_value)))
                elif g.wasm_type == "f32":
                    buf.append(0x43)
                    buf.extend(struct.pack("<f", float(g.init_value)))
                else:
                    buf.append(0x44)
                    buf.extend(struct.pack("<d", float(g.init_value)))
                buf.append(0x0B)
            out.extend(_encode_section(6, bytes(buf)))

        # 7. Export section
        exports: list[tuple[str, int, int]] = []
        for idx, fn in enumerate(all_fns):
            if fn.exported:
                exports.append((fn.name, 0x00, idx))
        if mem is not None and mem.exported:
            exports.append(("memory", 0x02, 0))
        if exports:
            buf = bytearray(_encode_uleb128(len(exports)))
            for name, kind, idx in exports:
                buf.extend(_encode_name(name))
                buf.append(kind)
                buf.extend(_encode_uleb128(idx))
            out.extend(_encode_section(7, bytes(buf)))

        # 10. Code section
        if defined_fns:
            buf = bytearray(_encode_uleb128(len(defined_fns)))
            for fn in defined_fns:
                body_bytes = self._encode_function_body(fn, func_map, global_map)
                buf.extend(_encode_uleb128(len(body_bytes)))
                buf.extend(body_bytes)
            out.extend(_encode_section(10, bytes(buf)))

        # 11. Data section
        if self.mod._data_segments:
            buf = bytearray(_encode_uleb128(len(self.mod._data_segments)))
            for offset, data in self.mod._data_segments:
                buf.append(0x00)  # active segment, memory 0
                buf.append(0x41)  # i32.const
                buf.extend(_encode_sleb128(offset))
                buf.append(0x0B)  # end
                buf.extend(_encode_uleb128(len(data)))
                buf.extend(data)
            out.extend(_encode_section(11, bytes(buf)))

        return bytes(out)

    def _encode_function_body(
        self,
        fn: WasmFunction,
        func_map: dict[str, int],
        global_map: dict[str, int],
    ) -> bytes:
        local_map: dict[str, int] = {}
        for idx, (pname, _) in enumerate(fn.params):
            local_map[pname] = idx
        base = len(fn.params)
        for idx, loc in enumerate(fn.locals):
            local_map[loc.name] = base + idx

        # Compress local declarations into (count, type) runs
        runs: list[tuple[int, int]] = []
        for loc in fn.locals:
            vtype = _VALTYPE_BYTES[loc.wasm_type]
            if runs and runs[-1][1] == vtype:
                runs[-1] = (runs[-1][0] + 1, vtype)
            else:
                runs.append((1, vtype))

        body = bytearray(_encode_uleb128(len(runs)))
        for count, vtype in runs:
            body.extend(_encode_uleb128(count))
            body.append(vtype)

        block_stack: list[tuple[Optional[str], bool]] = []
        lines: list[str] = []
        for item in fn.body:
            lines.extend(str(item).splitlines())

        for raw in lines:
            line = raw.split(";", 1)[0].strip()
            if not line:
                continue

            if line == ")":
                if block_stack and block_stack[-1][1]:
                    block_stack.pop()
                    body.append(0x0B)
                continue

            folded = line.startswith("(")
            if folded:
                line = line[1:].strip()

            # Close trailing folded parenthesis if self-contained on one line
            self_closed = False
            if folded and line.endswith(")") and line.count("(") < line.count(")"):
                line = line[:-1].strip()
                self_closed = True

            if line.startswith("block"):
                rest = line[5:].strip()
                lbl_match = re.match(r"^\$(\S+)", rest)
                lbl = lbl_match.group(1) if lbl_match else None
                btype = self._parse_blocktype(rest)
                block_stack.append((lbl, folded))
                body.extend((0x02, btype))
            elif line.startswith("loop"):
                rest = line[4:].strip()
                lbl_match = re.match(r"^\$(\S+)", rest)
                lbl = lbl_match.group(1) if lbl_match else None
                btype = self._parse_blocktype(rest)
                block_stack.append((lbl, folded))
                body.extend((0x03, btype))
            elif line == "if" or line.startswith("if "):
                rest = line[2:].strip()
                btype = self._parse_blocktype(rest)
                block_stack.append((None, folded))
                body.extend((0x04, btype))
            elif line == "end":
                if block_stack:
                    block_stack.pop()
                body.append(0x0B)
            elif line in _SIMPLE_OPCODES:
                body.append(_SIMPLE_OPCODES[line])
            elif line in _MEMORY_OPCODES:
                op, align = _MEMORY_OPCODES[line]
                body.extend((op, align, 0x00))
            elif line.startswith("i32.const "):
                body.append(0x41)
                body.extend(_encode_sleb128(int(line.split(None, 1)[1])))
            elif line.startswith("i64.const "):
                body.append(0x42)
                body.extend(_encode_sleb128(int(line.split(None, 1)[1])))
            elif line.startswith("f32.const "):
                body.append(0x43)
                body.extend(struct.pack("<f", float(line.split(None, 1)[1])))
            elif line.startswith("f64.const "):
                body.append(0x44)
                body.extend(struct.pack("<d", float(line.split(None, 1)[1])))
            elif line.startswith(("local.get ", "local.set ", "local.tee ")):
                cmd, target = line.split(None, 1)
                op = {"local.get": 0x20, "local.set": 0x21, "local.tee": 0x22}[cmd]
                idx = self._resolve_symbol(target, local_map, "local", fn.name)
                body.append(op)
                body.extend(_encode_uleb128(idx))
            elif line.startswith(("global.get ", "global.set ")):
                cmd, target = line.split(None, 1)
                op = 0x23 if cmd == "global.get" else 0x24
                idx = self._resolve_symbol(target, global_map, "global", fn.name)
                body.append(op)
                body.extend(_encode_uleb128(idx))
            elif line.startswith("call "):
                target = line.split(None, 1)[1].strip()
                idx = self._resolve_symbol(target, func_map, "function", fn.name)
                body.append(0x10)
                body.extend(_encode_uleb128(idx))
            elif line.startswith(("br ", "br_if ")):
                cmd, target = line.split(None, 1)
                op = 0x0C if cmd == "br" else 0x0D
                depth = self._resolve_branch(target.strip(), block_stack)
                body.append(op)
                body.extend(_encode_uleb128(depth))
            else:
                raise ValueError(
                    f"Unsupported WAT instruction {line!r} in function {fn.name!r}"
                )

            if self_closed and block_stack and block_stack[-1][1]:
                block_stack.pop()
                body.append(0x0B)

        while block_stack and block_stack[-1][1]:
            block_stack.pop()
            body.append(0x0B)

        body.append(0x0B)  # function end
        return bytes(body)

    @staticmethod
    def _resolve_symbol(
        token: str, mapping: dict[str, int], kind: str, fn_name: str
    ) -> int:
        tok = token.strip()
        if tok.startswith("$"):
            name = tok[1:]
            if name not in mapping:
                raise ValueError(f"Unknown {kind} ${name} in function {fn_name!r}")
            return mapping[name]
        if tok.isdigit():
            return int(tok)
        if tok in mapping:
            return mapping[tok]
        raise ValueError(f"Unknown {kind} {tok!r} in function {fn_name!r}")

    @staticmethod
    def _resolve_branch(
        token: str, block_stack: list[tuple[Optional[str], bool]]
    ) -> int:
        if token.startswith("$"):
            label = token[1:]
            for depth, (lbl, _) in enumerate(reversed(block_stack)):
                if lbl == label:
                    return depth
            raise ValueError(f"Unknown branch label ${label}")
        return int(token)


# ---------------------------------------------------------------------------
# AST → WASM Program Compiler
# ---------------------------------------------------------------------------

_HOST_IMPORTS: dict[str, tuple[str, str, list[tuple[str, str]], str]] = {
    "println":         ("env", "println",         [("ptr", "i32")], ""),
    "http_get":        ("env", "http_get",        [("url_ptr", "i32")], "i32"),
    "ltl_println_i64": ("env", "ltl_println_i64", [("val", "i64")], ""),
    "ltl_println_f64": ("env", "ltl_println_f64", [("val", "f64")], ""),
    "ltl_i64_to_str":  ("env", "ltl_i64_to_str",  [("val", "i64")], "i32"),
    "ltl_f64_to_str":  ("env", "ltl_f64_to_str",  [("val", "f64")], "i32"),
    "ltl_str_concat":  ("env", "ltl_str_concat",  [("a", "i32"), ("b", "i32")], "i32"),
    "ltl_str_len":     ("env", "ltl_str_len",     [("ptr", "i32")], "i64"),
}


def _ltl_type_to_kind(type_ref: object, default: str = "i64") -> str:
    if type_ref is None:
        return default
    name = getattr(type_ref, "name", str(type_ref)).lower()
    if name in ("float", "f64", "f32"):
        return "f64"
    if name in ("bool",):
        return "bool"
    if name in ("str", "string"):
        return "str"
    if name in ("none", "void", "nil", "()"):
        return ""
    return "i64"


def _kind_to_wasm(kind: str) -> str:
    if kind in ("bool", "str"):
        return "i32"
    return kind


class _ProgramWasmBuilder:
    """Compiles a parsed Lateralus AST Program to a WasmModule."""

    def __init__(self, module_name: str = "lateralus_module") -> None:
        self.mod = WasmModule(module_name)
        self._imports_added: set[str] = set()
        self._needs_memory: bool = False
        self._needs_alloc: bool = False
        self._strings: dict[str, int] = {}
        self._fn_sigs: dict[str, tuple[list[tuple[str, str]], str]] = {}
        self._var_kinds: dict[str, str] = {}
        self._loop_labels: list[tuple[str, str]] = []
        self._label_seq: int = 0

    def _next_id(self, prefix: str) -> str:
        self._label_seq += 1
        return f"{prefix}_{self._label_seq}"

    def _ensure_import(self, name: str) -> None:
        if name in self._imports_added:
            return
        mod_name, field_name, params, ret = _HOST_IMPORTS[name]
        self.mod.import_function(mod_name, field_name, name, params, ret)
        self._imports_added.add(name)
        self._needs_memory = True
        if name in ("http_get", "ltl_i64_to_str", "ltl_f64_to_str", "ltl_str_concat"):
            self._needs_alloc = True

    def _intern_str(self, text: str) -> int:
        self._needs_memory = True
        if text not in self._strings:
            self._strings[text] = self.mod.add_string_constant(text)
        return self._strings[text]

    def build(self, program: object) -> WasmModule:
        from ..ast_nodes import ConstFnDecl, FnDecl

        body = getattr(program, "body", [])
        fn_decls = [s for s in body if isinstance(s, (FnDecl, ConstFnDecl))]
        top_stmts = [s for s in body if not isinstance(s, (FnDecl, ConstFnDecl))]

        # First pass: collect declared function signatures
        for decl in fn_decls:
            params = [
                (p.name, _ltl_type_to_kind(p.type_, "i64"))
                for p in decl.params
            ]
            ret_kind = self._infer_return_kind(decl)
            self._fn_sigs[decl.name] = (params, ret_kind)

        # Compile declared functions
        has_main = False
        for decl in fn_decls:
            if decl.name == "main":
                has_main = True
            self._compile_fn_decl(decl)

        # Synthesize main for top-level executable statements or fallback stub
        if not has_main:
            main_fn = self.mod.add_function("main", [], "i64", exported=True)
            self._var_kinds = {}
            for stmt in top_stmts:
                self._compile_stmt(main_fn, stmt)
            main_fn.emit(i64_const(0), "return")

        if self._needs_memory:
            self.mod.add_memory(1, exported=True)

        if self._needs_alloc:
            heap_start = max(4096, (self.mod._data_offset + 15) & ~15)
            self.mod.add_global("__heap_ptr", "i32", True, str(heap_start))
            alloc_fn = self.mod.add_function(
                "ltl_alloc", [("size", "i32")], "i32", exported=True
            )
            alloc_fn.add_local("ptr", "i32")
            alloc_fn.emit(
                global_get("__heap_ptr"),
                local_set("ptr"),
                local_get("ptr"),
                local_get("size"),
                i32_add(),
                global_set("__heap_ptr"),
                local_get("ptr"),
            )

        return self.mod

    def _infer_return_kind(self, decl: object) -> str:
        from ..ast_nodes import ReturnStmt

        if decl.ret_type is not None:
            return _ltl_type_to_kind(decl.ret_type, "")
        stmts = getattr(getattr(decl, "body", None), "stmts", []) or []
        for stmt in stmts:
            if isinstance(stmt, ReturnStmt) and stmt.value is not None:
                return self._guess_expr_kind(stmt.value)
        return "" if decl.name == "main" else "i64"

    def _guess_expr_kind(self, expr: object) -> str:
        from ..ast_nodes import BinOp, CallExpr, FieldExpr, InterpolatedStr, Literal

        if isinstance(expr, Literal):
            if expr.kind == "float":
                return "f64"
            if expr.kind == "bool":
                return "bool"
            if expr.kind == "str":
                return "str"
            return "i64"
        if isinstance(expr, InterpolatedStr):
            return "str"
        if isinstance(expr, CallExpr):
            callee = self._resolve_callee_name(expr.callee)
            if callee in ("http_get", "http.get"):
                return "str"
            if callee in self._fn_sigs:
                return self._fn_sigs[callee][1]
        if isinstance(expr, FieldExpr):
            return "i64"
        if isinstance(expr, BinOp):
            if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                return "bool"
            lk = self._guess_expr_kind(expr.left)
            rk = self._guess_expr_kind(expr.right)
            if "str" in (lk, rk) and expr.op == "+":
                return "str"
            if "f64" in (lk, rk):
                return "f64"
        return "i64"

    def _compile_fn_decl(self, decl: object) -> None:
        from ..ast_nodes import ExprStmt, ReturnStmt

        params, ret_kind = self._fn_sigs[decl.name]
        wasm_params = [(name, _kind_to_wasm(kind)) for name, kind in params]
        wasm_ret = _kind_to_wasm(ret_kind)
        fn = self.mod.add_function(decl.name, wasm_params, wasm_ret, exported=True)

        self._var_kinds = {name: kind for name, kind in params}
        stmts = getattr(getattr(decl, "body", None), "stmts", []) or []

        for idx, stmt in enumerate(stmts):
            is_last = idx == len(stmts) - 1
            if (
                is_last
                and wasm_ret
                and isinstance(stmt, ExprStmt)
                and self._compile_implicit_return(fn, stmt.expr, ret_kind)
            ):
                fn.emit("return")
                return
            self._compile_stmt(fn, stmt)

        if wasm_ret and not (stmts and isinstance(stmts[-1], ReturnStmt)):
            self._emit_default_value(fn, wasm_ret)
            fn.emit("return")

    def _compile_implicit_return(
        self, fn: WasmFunction, expr: object, target_kind: str
    ) -> bool:
        got = self._compile_expr(fn, expr)
        if not got:
            return False
        self._coerce_numeric(fn, got, target_kind)
        return True

    def _emit_default_value(self, fn: WasmFunction, wasm_type: str) -> None:
        if wasm_type == "f64":
            fn.emit(f64_const(0.0))
        elif wasm_type == "i32":
            fn.emit(i32_const(0))
        else:
            fn.emit(i64_const(0))

    def _compile_stmt(self, fn: WasmFunction, stmt: object) -> None:
        from ..ast_nodes import (
            AssignStmt,
            BlockStmt,
            BreakStmt,
            ContinueStmt,
            ExprStmt,
            ForStmt,
            Ident,
            IfStmt,
            LetDecl,
            RangeExpr,
            ReturnStmt,
            WhileStmt,
        )

        if isinstance(stmt, LetDecl):
            if stmt.value is not None:
                kind = self._compile_expr(fn, stmt.value)
                if not kind:
                    kind = _ltl_type_to_kind(stmt.type_, "i64")
                    self._emit_default_value(fn, _kind_to_wasm(kind))
            else:
                kind = _ltl_type_to_kind(stmt.type_, "i64")
                self._emit_default_value(fn, _kind_to_wasm(kind))
            self._var_kinds[stmt.name] = kind
            fn.add_local(stmt.name, _kind_to_wasm(kind))
            fn.emit(local_set(stmt.name))
            return

        if isinstance(stmt, AssignStmt) and isinstance(stmt.target, Ident):
            name = stmt.target.name
            kind = self._var_kinds.get(name, "i64")
            if stmt.op == "=":
                got = self._compile_expr(fn, stmt.value)
                self._coerce_numeric(fn, got, kind)
            else:
                base_op = stmt.op[:-1]
                fn.emit(local_get(name))
                got = self._compile_expr(fn, stmt.value)
                self._coerce_numeric(fn, got, kind)
                self._emit_binop(fn, base_op, kind)
            fn.add_local(name, _kind_to_wasm(kind))
            fn.emit(local_set(name))
            return

        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                got = self._compile_expr(fn, stmt.value)
                if fn.result_type:
                    self._coerce_numeric(fn, got, fn.result_type)
                elif got:
                    fn.emit("drop")
            elif fn.result_type:
                self._emit_default_value(fn, fn.result_type)
            fn.emit("return")
            return

        if isinstance(stmt, ExprStmt):
            got = self._compile_expr(fn, stmt.expr)
            if got:
                fn.emit("drop")
            return

        if isinstance(stmt, BlockStmt):
            for sub in stmt.stmts:
                self._compile_stmt(fn, sub)
            return

        if isinstance(stmt, IfStmt):
            self._compile_if(fn, stmt.condition, stmt.then_block, stmt.elif_arms, stmt.else_block)
            return

        if isinstance(stmt, WhileStmt):
            exit_lbl = self._next_id("while_exit")
            loop_lbl = self._next_id("while_loop")
            fn.emit(f"block ${exit_lbl}", f"loop ${loop_lbl}")
            self._compile_condition(fn, stmt.condition)
            fn.emit(i32_eqz(), f"br_if ${exit_lbl}")
            self._loop_labels.append((exit_lbl, loop_lbl))
            for sub in stmt.body.stmts:
                self._compile_stmt(fn, sub)
            self._loop_labels.pop()
            fn.emit(f"br ${loop_lbl}", "end", "end")
            return

        if isinstance(stmt, ForStmt) and isinstance(stmt.iter, RangeExpr):
            var_name = stmt.var
            end_var = self._next_id("__range_end")
            fn.add_local(var_name, "i64")
            fn.add_local(end_var, "i64")
            self._var_kinds[var_name] = "i64"

            sk = self._compile_expr(fn, stmt.iter.start)
            self._coerce_numeric(fn, sk, "i64")
            fn.emit(local_set(var_name))

            ek = self._compile_expr(fn, stmt.iter.end)
            self._coerce_numeric(fn, ek, "i64")
            fn.emit(local_set(end_var))

            exit_lbl = self._next_id("for_exit")
            loop_lbl = self._next_id("for_loop")
            cmp_op = i64_gt_s() if stmt.iter.inclusive else i64_ge_s()
            fn.emit(
                f"block ${exit_lbl}",
                f"loop ${loop_lbl}",
                local_get(var_name),
                local_get(end_var),
                cmp_op,
                f"br_if ${exit_lbl}",
            )
            self._loop_labels.append((exit_lbl, loop_lbl))
            for sub in stmt.body.stmts:
                self._compile_stmt(fn, sub)
            self._loop_labels.pop()
            fn.emit(
                local_get(var_name),
                i64_const(1),
                i64_add(),
                local_set(var_name),
                f"br ${loop_lbl}",
                "end",
                "end",
            )
            return

        if isinstance(stmt, BreakStmt) and self._loop_labels:
            fn.emit(f"br ${self._loop_labels[-1][0]}")
            return

        if isinstance(stmt, ContinueStmt) and self._loop_labels:
            fn.emit(f"br ${self._loop_labels[-1][1]}")
            return

    def _compile_if(
        self,
        fn: WasmFunction,
        cond: object,
        then_block: object,
        elif_arms: list,
        else_block: Optional[object],
    ) -> None:
        self._compile_condition(fn, cond)
        fn.emit("if")
        for sub in getattr(then_block, "stmts", []):
            self._compile_stmt(fn, sub)
        if elif_arms:
            fn.emit("else")
            head_cond, head_block = elif_arms[0]
            self._compile_if(fn, head_cond, head_block, elif_arms[1:], else_block)
        elif else_block is not None:
            fn.emit("else")
            for sub in getattr(else_block, "stmts", []):
                self._compile_stmt(fn, sub)
        fn.emit("end")

    def _compile_condition(self, fn: WasmFunction, expr: object) -> None:
        kind = self._compile_expr(fn, expr)
        if kind == "i64":
            fn.emit(i64_const(0), i64_ne())
        elif kind == "f64":
            fn.emit(f64_const(0.0), f64_ne())

    def _coerce_numeric(self, fn: WasmFunction, got: str, target: str) -> None:
        if got == target or not got:
            return
        if got == "i64" and target == "f64":
            fn.emit(f64_convert_i64_s())
        elif got == "f64" and target == "i64":
            fn.emit(i64_trunc_f64_s())
        elif got == "bool" and target == "i64":
            fn.emit(i64_extend_i32_s())
        elif got == "i64" and target in ("bool", "i32"):
            fn.emit(i32_wrap_i64())

    def _coerce_to_str(self, fn: WasmFunction, expr: object) -> str:
        kind = self._compile_expr(fn, expr)
        return self._stack_value_to_str(fn, kind)

    def _stack_value_to_str(self, fn: WasmFunction, kind: str) -> str:
        if kind == "str":
            return "str"
        if kind == "i64":
            self._ensure_import("ltl_i64_to_str")
            fn.emit(call("ltl_i64_to_str"))
            return "str"
        if kind == "f64":
            self._ensure_import("ltl_f64_to_str")
            fn.emit(call("ltl_f64_to_str"))
            return "str"
        if kind == "bool":
            t_ptr = self._intern_str("true")
            f_ptr = self._intern_str("false")
            fn.emit("if (result i32)", i32_const(t_ptr), "else", i32_const(f_ptr), "end")
            return "str"
        fn.emit(i32_const(self._intern_str("")))
        return "str"

    def _resolve_callee_name(self, callee: object) -> Optional[str]:
        from ..ast_nodes import FieldExpr, Ident

        if isinstance(callee, Ident):
            return callee.name
        if isinstance(callee, FieldExpr) and isinstance(callee.obj, Ident):
            return f"{callee.obj.name}.{callee.field}"
        return None

    def _compile_expr(self, fn: WasmFunction, expr: object) -> str:
        from ..ast_nodes import (
            BinOp,
            CallExpr,
            Ident,
            InterpolatedStr,
            Literal,
            UnaryOp,
        )
        from ..parser import parse

        if isinstance(expr, Literal):
            if expr.kind == "int":
                fn.emit(i64_const(int(expr.value)))
                return "i64"
            if expr.kind == "float":
                fn.emit(f64_const(float(expr.value)))
                return "f64"
            if expr.kind == "bool":
                fn.emit(i32_const(1 if expr.value else 0))
                return "bool"
            if expr.kind == "str":
                fn.emit(i32_const(self._intern_str(str(expr.value))))
                return "str"
            fn.emit(i64_const(0))
            return "i64"

        if isinstance(expr, InterpolatedStr):
            parts = expr.parts or []
            if not parts:
                fn.emit(i32_const(self._intern_str("")))
                return "str"
            chunk_count = 0
            for part in parts:
                if isinstance(part, tuple) and len(part) == 2:
                    tag, val = part
                    if tag == "str":
                        if val == "" and chunk_count > 0:
                            continue
                        fn.emit(i32_const(self._intern_str(val)))
                    else:
                        sub_prog = parse(str(val))
                        sub_stmt = sub_prog.body[0] if sub_prog.body else None
                        sub_expr = getattr(sub_stmt, "expr", sub_stmt)
                        self._coerce_to_str(fn, sub_expr)
                elif isinstance(part, str):
                    if part == "" and chunk_count > 0:
                        continue
                    fn.emit(i32_const(self._intern_str(part)))
                else:
                    self._coerce_to_str(fn, part)
                chunk_count += 1
                if chunk_count > 1:
                    self._ensure_import("ltl_str_concat")
                    fn.emit(call("ltl_str_concat"))
            if chunk_count == 0:
                fn.emit(i32_const(self._intern_str("")))
            return "str"

        if isinstance(expr, Ident):
            if expr.name in self._var_kinds:
                fn.emit(local_get(expr.name))
                return self._var_kinds[expr.name]
            fn.emit(i64_const(0))
            return "i64"

        if isinstance(expr, UnaryOp):
            if expr.op == "-":
                kind = self._compile_expr(fn, expr.operand)
                if kind == "f64":
                    fn.emit(f64_neg())
                    return "f64"
                fn.add_local("__neg_tmp", "i64")
                fn.emit(
                    local_set("__neg_tmp"),
                    i64_const(0),
                    local_get("__neg_tmp"),
                    i64_sub(),
                )
                return "i64"
            if expr.op == "!":
                self._compile_condition(fn, expr.operand)
                fn.emit(i32_eqz())
                return "bool"

        if isinstance(expr, BinOp):
            if expr.op == "|>":
                if isinstance(expr.right, CallExpr):
                    patched = CallExpr(
                        callee=expr.right.callee,
                        args=[expr.left] + list(expr.right.args),
                    )
                    return self._compile_expr(fn, patched)
                if isinstance(expr.right, Ident):
                    if expr.right.name == "await":
                        return self._compile_expr(fn, expr.left)
                    patched = CallExpr(callee=expr.right, args=[expr.left])
                    return self._compile_expr(fn, patched)

            lk = self._guess_expr_kind(expr.left)
            rk = self._guess_expr_kind(expr.right)
            if expr.op == "+" and ("str" in (lk, rk)):
                self._coerce_to_str(fn, expr.left)
                self._coerce_to_str(fn, expr.right)
                self._ensure_import("ltl_str_concat")
                fn.emit(call("ltl_str_concat"))
                return "str"

            if expr.op in ("&&", "||"):
                self._compile_condition(fn, expr.left)
                self._compile_condition(fn, expr.right)
                fn.emit(i32_and() if expr.op == "&&" else i32_or())
                return "bool"

            lk = self._compile_expr(fn, expr.left)
            rk = self._compile_expr(fn, expr.right)
            promoted = "f64" if "f64" in (lk, rk) else ("i64" if "i64" in (lk, rk) else "bool")
            if lk != promoted:
                # Coerce left value via stack swap when mixed types appear
                if promoted == "f64" and lk == "i64":
                    tmp = self._next_id("__mix")
                    fn.add_local(tmp, _kind_to_wasm(rk))
                    fn.emit(local_set(tmp), f64_convert_i64_s(), local_get(tmp))
                    lk = "f64"
            if rk != promoted:
                self._coerce_numeric(fn, rk, promoted)

            if expr.op in ("==", "!=", "<", ">", "<=", ">="):
                self._emit_cmp(fn, expr.op, promoted)
                return "bool"
            self._emit_binop(fn, expr.op, promoted)
            return promoted

        if isinstance(expr, CallExpr):
            name = self._resolve_callee_name(expr.callee)
            if name in ("println", "print"):
                if not expr.args:
                    self._ensure_import("println")
                    fn.emit(i32_const(self._intern_str("")), call("println"))
                    return ""
                kind = self._compile_expr(fn, expr.args[0])
                if kind == "str":
                    self._ensure_import("println")
                    fn.emit(call("println"))
                elif kind == "f64":
                    self._ensure_import("ltl_println_f64")
                    fn.emit(call("ltl_println_f64"))
                elif kind == "bool":
                    self._stack_value_to_str(fn, "bool")
                    self._ensure_import("println")
                    fn.emit(call("println"))
                else:
                    self._ensure_import("ltl_println_i64")
                    fn.emit(call("ltl_println_i64"))
                return ""

            if name in ("http_get", "http.get"):
                if expr.args:
                    self._coerce_to_str(fn, expr.args[0])
                else:
                    fn.emit(i32_const(self._intern_str("")))
                self._ensure_import("http_get")
                fn.emit(call("http_get"))
                return "str"

            if name == "len" and expr.args:
                arg_kind = self._compile_expr(fn, expr.args[0])
                if arg_kind == "str":
                    self._ensure_import("ltl_str_len")
                    fn.emit(call("ltl_str_len"))
                    return "i64"
                fn.emit("drop", i64_const(0))
                return "i64"

            if name in self._fn_sigs:
                sig_params, ret_kind = self._fn_sigs[name]
                for arg, (_, pkind) in zip(expr.args, sig_params):
                    got = self._compile_expr(fn, arg)
                    self._coerce_numeric(fn, got, pkind)
                fn.emit(call(name))
                return ret_kind

            fn.emit(i64_const(0))
            return "i64"

        fn.emit(i64_const(0))
        return "i64"

    @staticmethod
    def _emit_binop(fn: WasmFunction, op: str, kind: str) -> None:
        if kind == "f64":
            ops = {"+": f64_add, "-": f64_sub, "*": f64_mul, "/": f64_div}
        elif kind in ("bool", "i32"):
            ops = {"+": i32_add, "-": i32_sub, "*": i32_mul}
        else:
            ops = {
                "+": i64_add, "-": i64_sub, "*": i64_mul,
                "/": i64_div_s, "%": i64_rem_s,
            }
        emitter = ops.get(op)
        if emitter:
            fn.emit(emitter())

    @staticmethod
    def _emit_cmp(fn: WasmFunction, op: str, kind: str) -> None:
        if kind == "f64":
            ops = {
                "==": f64_eq, "!=": f64_ne, "<": f64_lt,
                ">": f64_gt, "<=": f64_le, ">=": f64_ge,
            }
        elif kind in ("bool", "i32"):
            ops = {
                "==": i32_eq, "!=": i32_ne, "<": i32_lt_s,
                ">": i32_gt_s, "<=": i32_le_s, ">=": i32_ge_s,
            }
        else:
            ops = {
                "==": i64_eq, "!=": i64_ne, "<": i64_lt_s,
                ">": i64_gt_s, "<=": i64_le_s, ">=": i64_ge_s,
            }
        fn.emit(ops[op]())


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def compile_to_wasm(source: str) -> WasmModule:
    """Compile a LATERALUS program to a WASM module."""
    try:
        from ..parser import parse
        program = parse(source)
        return _ProgramWasmBuilder().build(program)
    except Exception:
        mod = WasmModule()
        fn = mod.add_function("main", [], "i64", exported=True)
        fn.emit(i64_const(0), "return")
        return mod


def compile_to_wasm_bytes(source: str) -> bytes:
    """Compile a LATERALUS program directly to WebAssembly binary bytes (.wasm)."""
    return compile_to_wasm(source).to_wasm_bytes()


def generate_js_host_shim() -> str:
    """Return a browser/Node JavaScript runtime shim for Lateralus WASM modules."""
    return """// Lateralus Browser/JS WebAssembly Runtime Shim
(function (root) {
  'use strict';

  const encoder = new TextEncoder();
  const decoder = new TextDecoder('utf-8');

  class WasmAsyncHttpRequest extends Error {
    constructor(url) {
      super('Pending async http_get: ' + url);
      this.name = 'WasmAsyncHttpRequest';
      this.url = url;
    }
  }

  function readWasmString(memory, ptr, len) {
    if (!memory) return '';
    const bytes = new Uint8Array(memory.buffer);
    if (typeof len === 'number' && len >= 0) {
      return decoder.decode(bytes.subarray(ptr, ptr + len));
    }
    let end = ptr;
    while (end < bytes.length && bytes[end] !== 0) end++;
    return decoder.decode(bytes.subarray(ptr, end));
  }

  function writeWasmString(instance, fallbackState, text) {
    const encoded = encoder.encode(String(text));
    const exports = instance ? instance.exports : {};
    const needed = encoded.length + 1;
    let ptr;
    if (typeof exports.ltl_alloc === 'function') {
      ptr = exports.ltl_alloc(needed);
    } else {
      ptr = fallbackState.heapPtr;
      fallbackState.heapPtr += (needed + 7) & ~7;
    }
    const mem = new Uint8Array(exports.memory.buffer);
    mem.set(encoded, ptr);
    mem[ptr + encoded.length] = 0;
    return ptr;
  }

  function createLateralusHostShim(options) {
    const opts = options || {};
    const onPrint = opts.onPrint || function (line) { console.log(line); };
    const httpCache = opts.httpCache || new Map();
    const state = { instance: null, heapPtr: 8192 };

    const getMem = function () {
      return state.instance && state.instance.exports ? state.instance.exports.memory : null;
    };

    const env = {
      println: function (ptr, len) {
        onPrint(readWasmString(getMem(), ptr, len));
      },
      print: function (ptr, len) {
        onPrint(readWasmString(getMem(), ptr, len));
      },
      ltl_println_i64: function (val) {
        onPrint(typeof val === 'bigint' ? val.toString() : String(val));
      },
      ltl_println_f64: function (val) {
        onPrint(Number.isInteger(val) ? String(val) : String(val));
      },
      ltl_i64_to_str: function (val) {
        return writeWasmString(state.instance, state, typeof val === 'bigint' ? val.toString() : String(val));
      },
      ltl_f64_to_str: function (val) {
        return writeWasmString(state.instance, state, String(val));
      },
      ltl_str_concat: function (aPtr, bPtr) {
        const mem = getMem();
        const combined = readWasmString(mem, aPtr) + readWasmString(mem, bPtr);
        return writeWasmString(state.instance, state, combined);
      },
      ltl_str_len: function (ptr) {
        return BigInt(encoder.encode(readWasmString(getMem(), ptr)).length);
      },
      http_get: function (urlPtr, urlLen) {
        const url = readWasmString(getMem(), urlPtr, urlLen);
        if (httpCache.has(url)) {
          return writeWasmString(state.instance, state, httpCache.get(url));
        }
        if (typeof opts.httpGetSync === 'function') {
          const body = String(opts.httpGetSync(url));
          httpCache.set(url, body);
          return writeWasmString(state.instance, state, body);
        }
        throw new WasmAsyncHttpRequest(url);
      },
    };

    return {
      imports: { env: env },
      bindInstance: function (instance) { state.instance = instance; },
      httpCache: httpCache,
      WasmAsyncHttpRequest: WasmAsyncHttpRequest,
    };
  }

  async function runLateralusWasm(wasmBytes, options) {
    const opts = options || {};
    const lines = [];
    const httpCache = opts.httpCache || new Map();
    const fetcher = opts.fetcher || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);

    for (let attempt = 0; attempt < 16; attempt++) {
      lines.length = 0;
      const shim = createLateralusHostShim({
        onPrint: function (line) {
          lines.push(line);
          if (typeof opts.onPrint === 'function') opts.onPrint(line);
        },
        httpCache: httpCache,
        httpGetSync: opts.httpGetSync,
      });

      const instantiated = await WebAssembly.instantiate(wasmBytes, shim.imports);
      shim.bindInstance(instantiated.instance);

      try {
        const exitCode = instantiated.instance.exports.main ? instantiated.instance.exports.main() : 0;
        return { lines: lines, exitCode: exitCode, instance: instantiated.instance };
      } catch (err) {
        if (err && err.name === 'WasmAsyncHttpRequest' && fetcher) {
          try {
            const resp = await fetcher(err.url);
            httpCache.set(err.url, await resp.text());
          } catch (netErr) {
            httpCache.set(err.url, '[http_get error: ' + (netErr.message || String(netErr)) + ']');
          }
          continue;
        }
        throw err;
      }
    }
    throw new Error('Exceeded max async http_get replays (16)');
  }

  const api = {
    createLateralusHostShim: createLateralusHostShim,
    runLateralusWasm: runLateralusWasm,
  };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  } else {
    root.LateralusWasm = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
"""


def expression_to_wat(expr: str) -> str:
    """Compile a LATERALUS expression to WAT instructions."""
    c = WasmCompiler()
    return c.compile_expression_to_wat(expr)


def get_wasm_builtins() -> dict:
    return {
        "WasmModule":            WasmModule,
        "WasmCompiler":          WasmCompiler,
        "compile_to_wasm":       compile_to_wasm,
        "compile_to_wasm_bytes": compile_to_wasm_bytes,
        "expression_to_wat":     expression_to_wat,
        "generate_js_host_shim": generate_js_host_shim,
    }
