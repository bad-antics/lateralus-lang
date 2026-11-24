"""
lateralus_lang/codegen/wasm_binary.py
Zero-dependency WebAssembly 1.0 binary (.wasm) encoder for WasmModule.

Encodes a WasmModule (imports, memory, globals, exports, functions, and data
segments) directly into a spec-compliant WebAssembly 1.0 binary byte stream
without requiring an external `wat2wasm` binary.
"""

from __future__ import annotations

import re
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wasm import WasmFunction, WasmModule

WASM_MAGIC = b"\x00asm"
WASM_VERSION = b"\x01\x00\x00\x00"

VALTYPE_CODES: dict[str, int] = {
    "i32": 0x7F,
    "i64": 0x7E,
    "f32": 0x7D,
    "f64": 0x7C,
}

BLOCKTYPE_VOID = 0x40

# Section IDs (W3C WebAssembly 1.0 Section 5.5.2)
SEC_TYPE = 1
SEC_IMPORT = 2
SEC_FUNCTION = 3
SEC_MEMORY = 5
SEC_GLOBAL = 6
SEC_EXPORT = 7
SEC_CODE = 10
SEC_DATA = 11

# Memory load/store opcodes -> (opcode, natural_align_log2)
MEMORY_OPCODES: dict[str, tuple[int, int]] = {
    "i32.load": (0x28, 2),
    "i64.load": (0x29, 3),
    "f32.load": (0x2A, 2),
    "f64.load": (0x2B, 3),
    "i32.load8_s": (0x2C, 0),
    "i32.load8_u": (0x2D, 0),
    "i32.load16_s": (0x2E, 1),
    "i32.load16_u": (0x2F, 1),
    "i64.load8_s": (0x30, 0),
    "i64.load8_u": (0x31, 0),
    "i64.load32_s": (0x34, 2),
    "i64.load32_u": (0x35, 2),
    "i32.store": (0x36, 2),
    "i64.store": (0x37, 3),
    "f32.store": (0x38, 2),
    "f64.store": (0x39, 3),
    "i32.store8": (0x3A, 0),
    "i32.store16": (0x3B, 1),
    "i64.store8": (0x3C, 0),
    "i64.store32": (0x3E, 2),
}

# Zero-immediate opcodes
SIMPLE_OPCODES: dict[str, bytes] = {
    "unreachable": b"\x00",
    "nop": b"\x01",
    "return": b"\x0f",
    "drop": b"\x1a",
    "select": b"\x1b",
    "memory.size": b"\x3f\x00",
    "memory.grow": b"\x40\x00",
    # i32 comparison & numeric
    "i32.eqz": b"\x45",
    "i32.eq": b"\x46",
    "i32.ne": b"\x47",
    "i32.lt_s": b"\x48",
    "i32.lt_u": b"\x49",
    "i32.gt_s": b"\x4a",
    "i32.gt_u": b"\x4b",
    "i32.le_s": b"\x4c",
    "i32.le_u": b"\x4d",
    "i32.ge_s": b"\x4e",
    "i32.ge_u": b"\x4f",
    "i32.clz": b"\x67",
    "i32.ctz": b"\x68",
    "i32.popcnt": b"\x69",
    "i32.add": b"\x6a",
    "i32.sub": b"\x6b",
    "i32.mul": b"\x6c",
    "i32.div_s": b"\x6d",
    "i32.div_u": b"\x6e",
    "i32.rem_s": b"\x6f",
    "i32.rem_u": b"\x70",
    "i32.and": b"\x71",
    "i32.or": b"\x72",
    "i32.xor": b"\x73",
    "i32.shl": b"\x74",
    "i32.shr_s": b"\x75",
    "i32.shr_u": b"\x76",
    # i64 comparison & numeric
    "i64.eqz": b"\x50",
    "i64.eq": b"\x51",
    "i64.ne": b"\x52",
    "i64.lt_s": b"\x53",
    "i64.lt_u": b"\x54",
    "i64.gt_s": b"\x55",
    "i64.gt_u": b"\x56",
    "i64.le_s": b"\x57",
    "i64.le_u": b"\x58",
    "i64.ge_s": b"\x59",
    "i64.ge_u": b"\x5a",
    "i64.clz": b"\x79",
    "i64.ctz": b"\x7a",
    "i64.popcnt": b"\x7b",
    "i64.add": b"\x7c",
    "i64.sub": b"\x7d",
    "i64.mul": b"\x7e",
    "i64.div_s": b"\x7f",
    "i64.div_u": b"\x80",
    "i64.rem_s": b"\x81",
    "i64.rem_u": b"\x82",
    "i64.and": b"\x83",
    "i64.or": b"\x84",
    "i64.xor": b"\x85",
    "i64.shl": b"\x86",
    "i64.shr_s": b"\x87",
    "i64.shr_u": b"\x88",
    # f64 comparison & numeric
    "f64.eq": b"\x61",
    "f64.ne": b"\x62",
    "f64.lt": b"\x63",
    "f64.gt": b"\x64",
    "f64.le": b"\x65",
    "f64.ge": b"\x66",
    "f64.abs": b"\x99",
    "f64.neg": b"\x9a",
    "f64.ceil": b"\x9b",
    "f64.floor": b"\x9c",
    "f64.trunc": b"\x9d",
    "f64.nearest": b"\x9e",
    "f64.sqrt": b"\x9f",
    "f64.add": b"\xa0",
    "f64.sub": b"\xa1",
    "f64.mul": b"\xa2",
    "f64.div": b"\xa3",
    "f64.min": b"\xa4",
    "f64.max": b"\xa5",
    # Conversions
    "i32.wrap_i64": b"\xa7",
    "i32.trunc_f32_s": b"\xa8",
    "i32.trunc_f32_u": b"\xa9",
    "i32.trunc_f64_s": b"\xaa",
    "i32.trunc_f64_u": b"\xab",
    "i64.extend_i32_s": b"\xac",
    "i64.extend_i32_u": b"\xad",
    "i64.trunc_f32_s": b"\xae",
    "i64.trunc_f32_u": b"\xaf",
    "i64.trunc_f64_s": b"\xb0",
    "i64.trunc_f64_u": b"\xb1",
    "f32.convert_i32_s": b"\xb2",
    "f32.convert_i32_u": b"\xb3",
    "f32.convert_i64_s": b"\xb4",
    "f32.convert_i64_u": b"\xb5",
    "f32.demote_f64": b"\xb6",
    "f64.convert_i32_s": b"\xb7",
    "f64.convert_i32_u": b"\xb8",
    "f64.convert_i64_s": b"\xb9",
    "f64.convert_i64_u": b"\xba",
    "f64.promote_f32": b"\xbb",
    "i32.reinterpret_f32": b"\xbc",
    "i64.reinterpret_f64": b"\xbd",
    "f32.reinterpret_i32": b"\xbe",
    "f64.reinterpret_i64": b"\xbf",
}


class WasmBinaryError(ValueError):
    """Raised when a WAT/IR construct cannot be encoded into binary WASM."""


def encode_uleb128(value: int) -> bytes:
    """Encode a non-negative integer as unsigned LEB128."""
    if value < 0:
        raise WasmBinaryError(f"ULEB128 requires non-negative value, got {value}")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            byte |= 0x80
        out.append(byte)
        if value == 0:
            break
    return bytes(out)


def encode_sleb128(value: int, bits: int = 64) -> bytes:
    """Encode a signed integer (wrapped to `bits` width) as signed LEB128."""
    mask = (1 << bits) - 1
    sign_bit = 1 << (bits - 1)
    value = value & mask
    if value & sign_bit:
        value -= 1 << bits

    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and (byte & 0x40) == 0) or (
            value == -1 and (byte & 0x40) != 0
        )
        if not done:
            byte |= 0x80
        out.append(byte)
        if done:
            break
    return bytes(out)


def encode_name(text: str) -> bytes:
    """Encode a UTF-8 name prefixed with its byte length."""
    raw = text.encode("utf-8")
    return encode_uleb128(len(raw)) + raw


def encode_vec(items: list[bytes]) -> bytes:
    """Encode a WebAssembly vector (count + concatenated elements)."""
    return encode_uleb128(len(items)) + b"".join(items)


def encode_section(section_id: int, payload: bytes) -> bytes:
    """Wrap a non-empty section payload with its ID and ULEB128 byte length."""
    return bytes([section_id]) + encode_uleb128(len(payload)) + payload


def _encode_valtype(wtype: str) -> int:
    code = VALTYPE_CODES.get(wtype)
    if code is None:
        raise WasmBinaryError(f"Unsupported WASM value type: {wtype!r}")
    return code


def _parse_blocktype(tokens: list[str]) -> tuple[int, str | None]:
    """Parse optional `$label` and `(result <type>)` from block/loop/if header."""
    label: str | None = None
    result_code = BLOCKTYPE_VOID
    joined = " ".join(tokens)

    res_match = re.search(r"\(\s*result\s+(i32|i64|f32|f64)\s*\)", joined)
    if res_match:
        result_code = _encode_valtype(res_match.group(1))
        joined = joined[: res_match.start()] + joined[res_match.end() :]

    for tok in joined.split():
        if tok.startswith("$"):
            label = tok[1:]
            break

    return result_code, label


def _resolve_index(token: str, table: dict[str, int], kind: str) -> int:
    clean = token.strip()
    if clean.startswith("$"):
        name = clean[1:]
        if name not in table:
            raise WasmBinaryError(f"Unknown {kind} '${name}'")
        return table[name]
    if clean.isdigit():
        return int(clean)
    if clean in table:
        return table[clean]
    raise WasmBinaryError(f"Invalid {kind} reference: {token!r}")


def _resolve_branch_depth(token: str, label_stack: list[str | None]) -> int:
    clean = token.strip()
    if clean.isdigit():
        return int(clean)
    if clean.startswith("$"):
        target = clean[1:]
        for idx in range(len(label_stack) - 1, -1, -1):
            if label_stack[idx] == target:
                return len(label_stack) - 1 - idx
        raise WasmBinaryError(f"Unknown branch label '${target}'")
    raise WasmBinaryError(f"Invalid branch target: {token!r}")


def _encode_function_body(
    fn: WasmFunction,
    func_indices: dict[str, int],
    global_indices: dict[str, int],
) -> bytes:
    """Assemble local declarations and instructions of a WasmFunction."""
    local_indices: dict[str, int] = {}
    for pname, _ in fn.params:
        local_indices[pname] = len(local_indices)
    for loc in fn.locals:
        local_indices[loc.name] = len(local_indices)

    # Compress consecutive locals of identical type
    local_groups: list[bytes] = []
    if fn.locals:
        run_type = fn.locals[0].wasm_type
        run_count = 1
        for loc in fn.locals[1:]:
            if loc.wasm_type == run_type:
                run_count += 1
            else:
                local_groups.append(
                    encode_uleb128(run_count) + bytes([_encode_valtype(run_type)])
                )
                run_type = loc.wasm_type
                run_count = 1
        local_groups.append(
            encode_uleb128(run_count) + bytes([_encode_valtype(run_type)])
        )

    raw_lines: list[str] = []
    for entry in fn.body:
        for sub in entry.splitlines():
            stripped = sub.split(";;", 1)[0].strip()
            if stripped:
                raw_lines.append(stripped)

    code = bytearray()
    label_stack: list[str | None] = []

    if not raw_lines and fn.result_type:
        # Ensure empty typed functions remain valid WebAssembly modules
        if fn.result_type == "i64":
            raw_lines.append("i64.const 0")
        elif fn.result_type == "f64":
            raw_lines.append("f64.const 0.0")
        elif fn.result_type == "f32":
            raw_lines.append("f32.const 0.0")
        else:
            raw_lines.append("i32.const 0")

    for line in raw_lines:
        if line == ")" or line == "end":
            if not label_stack:
                raise WasmBinaryError(
                    f"Unmatched '{line}' in function '{fn.name}'"
                )
            label_stack.pop()
            code.append(0x0B)
            continue

        if line == "else":
            code.append(0x05)
            continue

        # Normalize leading '(' used by folded block/loop/if headers
        working = line[1:].strip() if line.startswith("(") else line
        parts = working.split()
        op = parts[0]
        rest = parts[1:]

        if op in ("block", "loop", "if"):
            bt, lbl = _parse_blocktype(rest)
            label_stack.append(lbl)
            opcode = 0x02 if op == "block" else (0x03 if op == "loop" else 0x04)
            code.append(opcode)
            code.append(bt)
            continue

        if op in ("br", "br_if"):
            if not rest:
                raise WasmBinaryError(f"Missing target for {op} in '{fn.name}'")
            depth = _resolve_branch_depth(rest[0], label_stack)
            code.append(0x0C if op == "br" else 0x0D)
            code.extend(encode_uleb128(depth))
            continue

        if op == "i32.const":
            code.append(0x41)
            code.extend(encode_sleb128(int(rest[0], 0), bits=32))
            continue

        if op == "i64.const":
            code.append(0x42)
            code.extend(encode_sleb128(int(rest[0], 0), bits=64))
            continue

        if op == "f32.const":
            code.append(0x43)
            code.extend(struct.pack("<f", float(rest[0])))
            continue

        if op == "f64.const":
            code.append(0x44)
            code.extend(struct.pack("<d", float(rest[0])))
            continue

        if op in ("local.get", "local.set", "local.tee"):
            idx = _resolve_index(rest[0], local_indices, "local")
            op_byte = (
                0x20 if op == "local.get" else (0x21 if op == "local.set" else 0x22)
            )
            code.append(op_byte)
            code.extend(encode_uleb128(idx))
            continue

        if op in ("global.get", "global.set"):
            idx = _resolve_index(rest[0], global_indices, "global")
            code.append(0x23 if op == "global.get" else 0x24)
            code.extend(encode_uleb128(idx))
            continue

        if op == "call":
            idx = _resolve_index(rest[0], func_indices, "function")
            code.append(0x10)
            code.extend(encode_uleb128(idx))
            continue

        if op in MEMORY_OPCODES:
            mem_op, default_align = MEMORY_OPCODES[op]
            offset = 0
            align = default_align
            for arg in rest:
                if arg.startswith("offset="):
                    offset = int(arg.split("=", 1)[1], 0)
                elif arg.startswith("align="):
                    raw_align = int(arg.split("=", 1)[1], 0)
                    align = max(0, raw_align.bit_length() - 1) if raw_align > 0 else 0
            code.append(mem_op)
            code.extend(encode_uleb128(align))
            code.extend(encode_uleb128(offset))
            continue

        simple = SIMPLE_OPCODES.get(op)
        if simple is not None:
            code.extend(simple)
            continue

        raise WasmBinaryError(
            f"Unsupported WASM instruction {line!r} in function '{fn.name}'"
        )

    if label_stack:
        raise WasmBinaryError(
            f"Unclosed structured control block(s) {label_stack!r} in '{fn.name}'"
        )

    code.append(0x0B)  # function body end
    body_bytes = encode_vec(local_groups) + bytes(code)
    return encode_uleb128(len(body_bytes)) + body_bytes


def encode_wasm_module(module: WasmModule) -> bytes:
    """Serialize a WasmModule into a complete WebAssembly 1.0 `.wasm` binary."""
    imports = [fn for fn in module._functions if fn.imported]
    defined = [fn for fn in module._functions if not fn.imported]

    # Deduplicate function type signatures: (param_types_tuple, result_type)
    sig_to_type_idx: dict[tuple[tuple[str, ...], str], int] = {}
    type_entries: list[bytes] = []

    def intern_signature(fn: WasmFunction) -> int:
        param_types = tuple(t for _, t in fn.params)
        key = (param_types, fn.result_type)
        if key in sig_to_type_idx:
            return sig_to_type_idx[key]
        p_bytes = [bytes([_encode_valtype(t)]) for t in param_types]
        r_bytes = (
            [bytes([_encode_valtype(fn.result_type)])] if fn.result_type else []
        )
        entry = b"\x60" + encode_vec(p_bytes) + encode_vec(r_bytes)
        idx = len(type_entries)
        type_entries.append(entry)
        sig_to_type_idx[key] = idx
        return idx

    func_indices: dict[str, int] = {}
    import_entries: list[bytes] = []
    for imp in imports:
        t_idx = intern_signature(imp)
        func_indices[imp.name] = len(func_indices)
        import_entries.append(
            encode_name(imp.import_module)
            + encode_name(imp.import_name)
            + b"\x00"
            + encode_uleb128(t_idx)
        )

    defined_type_indices: list[bytes] = []
    for fn in defined:
        t_idx = intern_signature(fn)
        func_indices[fn.name] = len(func_indices)
        defined_type_indices.append(encode_uleb128(t_idx))

    global_indices: dict[str, int] = {}
    global_entries: list[bytes] = []
    for g in module._globals:
        global_indices[g.name] = len(global_indices)
        vcode = _encode_valtype(g.wasm_type)
        mut_byte = 0x01 if g.mutable else 0x00
        if g.wasm_type == "i32":
            init_expr = b"\x41" + encode_sleb128(int(g.init_value, 0), 32) + b"\x0b"
        elif g.wasm_type == "i64":
            init_expr = b"\x42" + encode_sleb128(int(g.init_value, 0), 64) + b"\x0b"
        elif g.wasm_type == "f64":
            init_expr = b"\x44" + struct.pack("<d", float(g.init_value)) + b"\x0b"
        elif g.wasm_type == "f32":
            init_expr = b"\x43" + struct.pack("<f", float(g.init_value)) + b"\x0b"
        else:
            raise WasmBinaryError(f"Unsupported global type {g.wasm_type!r}")
        global_entries.append(bytes([vcode, mut_byte]) + init_expr)

    export_entries: list[bytes] = []
    if module._memory is not None and module._memory.exported:
        export_entries.append(encode_name("memory") + b"\x02" + encode_uleb128(0))
    for fn in defined:
        if fn.exported:
            export_entries.append(
                encode_name(fn.name)
                + b"\x00"
                + encode_uleb128(func_indices[fn.name])
            )

    code_entries: list[bytes] = [
        _encode_function_body(fn, func_indices, global_indices) for fn in defined
    ]

    data_entries: list[bytes] = []
    for offset, data in module._data_segments:
        init_offset = b"\x41" + encode_sleb128(offset, 32) + b"\x0b"
        data_entries.append(
            b"\x00" + init_offset + encode_uleb128(len(data)) + data
        )

    out = bytearray(WASM_MAGIC + WASM_VERSION)
    if type_entries:
        out.extend(encode_section(SEC_TYPE, encode_vec(type_entries)))
    if import_entries:
        out.extend(encode_section(SEC_IMPORT, encode_vec(import_entries)))
    if defined_type_indices:
        out.extend(encode_section(SEC_FUNCTION, encode_vec(defined_type_indices)))
    if module._memory is not None:
        mem = module._memory
        if mem.max_pages is not None:
            lim = (
                b"\x01"
                + encode_uleb128(mem.min_pages)
                + encode_uleb128(mem.max_pages)
            )
        else:
            lim = b"\x00" + encode_uleb128(mem.min_pages)
        out.extend(encode_section(SEC_MEMORY, encode_vec([lim])))
    if global_entries:
        out.extend(encode_section(SEC_GLOBAL, encode_vec(global_entries)))
    if export_entries:
        out.extend(encode_section(SEC_EXPORT, encode_vec(export_entries)))
    if code_entries:
        out.extend(encode_section(SEC_CODE, encode_vec(code_entries)))
    if data_entries:
        out.extend(encode_section(SEC_DATA, encode_vec(data_entries)))

    return bytes(out)
