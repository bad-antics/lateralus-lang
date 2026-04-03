"""
lateralus_lang/vm/disassembler.py  ─  LATERALUS Bytecode Disassembler
═══════════════════════════════════════════════════════════════════════════
Converts a Bytecode object (or raw bytes) back into human-readable
.ltasm assembly text.

Usage
─────
    from lateralus_lang.vm.disassembler import disassemble
    from lateralus_lang.vm import assemble

    bc = assemble(source)
    text = disassemble(bc)
    print(text)

Output format matches .ltasm syntax so it can be round-tripped back
through the assembler (modulo label names — we synthesise L0, L1, …).
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import struct
from io import StringIO
from typing import Dict, List, Optional, Set, Tuple

from .opcodes import Op, OPCODE_META
from .assembler import Bytecode


# ─────────────────────────────────────────────────────────────────────────────
# Operand decoders
# ─────────────────────────────────────────────────────────────────────────────

def _read_u8(code: bytes | bytearray, off: int) -> Tuple[int, int]:
    """Read 1-byte unsigned int.  Returns (value, new_offset)."""
    if off >= len(code):
        raise DisassemblerError(f"Unexpected end of bytecode at offset {off}")
    return code[off], off + 1


def _read_u32(code: bytes | bytearray, off: int) -> Tuple[int, int]:
    """Read 4-byte big-endian unsigned int."""
    if off + 4 > len(code):
        raise DisassemblerError(f"Unexpected end of bytecode at offset {off}")
    val = struct.unpack_from(">I", code, off)[0]
    return val, off + 4


def _read_u64(code: bytes | bytearray, off: int) -> Tuple[int, int]:
    """Read 8-byte big-endian unsigned int."""
    if off + 8 > len(code):
        raise DisassemblerError(f"Unexpected end of bytecode at offset {off}")
    val = struct.unpack_from(">Q", code, off)[0]
    return val, off + 8


def _u64_to_float(bits: int) -> float:
    """Re-interpret 64-bit unsigned int as IEEE-754 double."""
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


# ─────────────────────────────────────────────────────────────────────────────
# Error
# ─────────────────────────────────────────────────────────────────────────────

class DisassemblerError(Exception):
    """Raised on malformed bytecode during disassembly."""


# ─────────────────────────────────────────────────────────────────────────────
# Reverse label map
# ─────────────────────────────────────────────────────────────────────────────

def _build_reverse_labels(bc: Bytecode) -> Dict[int, str]:
    """Map code-offset → label name from the Bytecode label table."""
    rev: Dict[int, str] = {}
    for name, off in bc.labels.items():
        # Prefer shorter / earlier names when two labels share an offset
        if off not in rev or len(name) < len(rev[off]):
            rev[off] = name
    return rev


# ─────────────────────────────────────────────────────────────────────────────
# First pass: collect jump targets so we can synthesise labels
# ─────────────────────────────────────────────────────────────────────────────

def _collect_jump_targets(code: bytes | bytearray) -> Set[int]:
    """Scan bytecode and return the set of target offsets from jumps/calls."""
    targets: Set[int] = set()
    off = 0
    while off < len(code):
        opcode = code[off]
        off += 1
        try:
            op = Op(opcode)
        except ValueError:
            # Unknown opcode — skip (best effort)
            continue
        schema = OPCODE_META.get(op, ((), ""))[0]
        for kind in schema:
            if kind == "imm64":
                _, off = _read_u64(code, off)
            elif kind in ("imm32", "addr32"):
                val, off = _read_u32(code, off)
                # If this is a jump/call instruction, record the target
                if op in _BRANCH_OPS:
                    targets.add(val)
            elif kind == "imm8":
                _, off = _read_u8(code, off)
            elif kind == "reg":
                _, off = _read_u8(code, off)
            elif kind == "str_idx":
                _, off = _read_u32(code, off)
    return targets


# Opcodes that use addr32/imm32 as branch targets
_BRANCH_OPS = frozenset({
    Op.JMP, Op.JT, Op.JF, Op.JZ, Op.JNZ,
    Op.CALL, Op.TAIL_CALL, Op.TRY_BEGIN,
})


# ─────────────────────────────────────────────────────────────────────────────
# Register names
# ─────────────────────────────────────────────────────────────────────────────

_REG_NAMES = {i: f"r{i}" for i in range(16)}


# ─────────────────────────────────────────────────────────────────────────────
# Main disassembler
# ─────────────────────────────────────────────────────────────────────────────

def disassemble(bc: Bytecode, *, show_hex: bool = False,
                show_offsets: bool = True) -> str:
    """
    Disassemble *bc* into .ltasm text.

    Parameters
    ----------
    bc : Bytecode
        Assembled bytecode object.
    show_hex : bool
        If True, show raw hex bytes alongside each instruction.
    show_offsets : bool
        If True, prefix each line with the byte offset.

    Returns
    -------
    str
        Human-readable .ltasm text.
    """
    code = bc.code
    strings = bc.string_table
    labels_rev = _build_reverse_labels(bc)
    jump_targets = _collect_jump_targets(code)

    # Build label map: offset → label name
    # Merge existing labels with synthesised ones for jump targets
    label_map: Dict[int, str] = dict(labels_rev)
    synth_counter = 0
    for target in sorted(jump_targets):
        if target not in label_map:
            label_map[target] = f"L{synth_counter}"
            synth_counter += 1

    out = StringIO()

    # ── Header ────────────────────────────────────────────────────────────
    out.write("; ── Lateralus VM Disassembly ──\n")
    out.write(f"; Code size:     {len(code)} bytes\n")
    out.write(f"; Strings:       {len(strings)}\n")
    out.write(f"; Entry point:   0x{bc.entry_point:04X}\n")
    if bc.data_segment:
        out.write(f"; Data segment:  {len(bc.data_segment)} bytes\n")
    out.write("\n")

    # ── String table ──────────────────────────────────────────────────────
    if strings:
        out.write(".section data\n")
        for i, s in enumerate(strings):
            escaped = s.replace("\\", "\\\\").replace('"', '\\"')
            escaped = escaped.replace("\n", "\\n").replace("\t", "\\t")
            out.write(f"  .string \"{escaped}\"    ; str[{i}]\n")
        out.write("\n")

    # ── Code section ──────────────────────────────────────────────────────
    out.write(".section code\n")

    # Mark entry
    entry_label = label_map.get(bc.entry_point)
    if entry_label:
        out.write(f".global {entry_label}\n")
    out.write("\n")

    off = 0
    while off < len(code):
        instr_off = off

        # Emit label if this offset has one
        if off in label_map:
            out.write(f"\n{label_map[off]}:\n")

        # Read opcode
        opcode_byte = code[off]
        off += 1

        try:
            op = Op(opcode_byte)
        except ValueError:
            # Unknown opcode — emit as raw byte
            line = _fmt_offset(instr_off, show_offsets)
            line += f"  .byte 0x{opcode_byte:02X}    ; <unknown opcode>"
            out.write(line + "\n")
            continue

        schema = OPCODE_META.get(op, ((), ""))[0]
        desc   = OPCODE_META.get(op, ((), ""))[1]
        operand_strs: List[str] = []

        # Decode operands
        for kind in schema:
            if kind == "imm64":
                val, off = _read_u64(code, off)
                # Try to detect float-encoded values
                fval = _u64_to_float(val)
                if op in (Op.PUSH_IMM, Op.MOV_IMM) and _looks_like_float(val):
                    operand_strs.append(f"{fval}")
                elif val > 0xFFFF:
                    operand_strs.append(f"0x{val:X}")
                else:
                    operand_strs.append(str(val))

            elif kind in ("imm32", "addr32"):
                val, off = _read_u32(code, off)
                if op in _BRANCH_OPS and val in label_map:
                    operand_strs.append(f".{label_map[val]}")
                elif kind == "addr32" and val in label_map:
                    operand_strs.append(f".{label_map[val]}")
                else:
                    operand_strs.append(str(val))

            elif kind == "imm8":
                val, off = _read_u8(code, off)
                operand_strs.append(str(val))

            elif kind == "reg":
                val, off = _read_u8(code, off)
                operand_strs.append(_REG_NAMES.get(val, f"r{val}"))

            elif kind == "str_idx":
                val, off = _read_u32(code, off)
                if val < len(strings):
                    s = strings[val]
                    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
                    escaped = escaped.replace("\n", "\\n").replace("\t", "\\t")
                    operand_strs.append(f'"{escaped}"')
                else:
                    operand_strs.append(f"str[{val}]")

        # Format the instruction line
        mnemonic = op.name
        line = _fmt_offset(instr_off, show_offsets)

        if show_hex:
            raw_bytes = code[instr_off:off]
            hex_str = " ".join(f"{b:02X}" for b in raw_bytes)
            line += f"  {hex_str:<24s}  "

        line += f"  {mnemonic:<14s}"
        if operand_strs:
            line += "  " + ", ".join(operand_strs)
        if desc:
            pad = max(0, 50 - len(line))
            line += " " * pad + f"; {desc}"

        out.write(line + "\n")

    # ── Data segment ──────────────────────────────────────────────────────
    if bc.data_segment:
        out.write("\n.section data\n")
        for i in range(0, len(bc.data_segment), 16):
            chunk = bc.data_segment[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            out.write(f"  ; {i:04X}: {hex_part:<48s}  |{ascii_part}|\n")

    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_offset(off: int, show: bool) -> str:
    return f"  {off:04X}:" if show else ""


def _looks_like_float(bits: int) -> bool:
    """
    Heuristic: if the 64-bit value, when interpreted as IEEE-754 double,
    produces a "nice" float (not NaN/Inf, not a huge integer), it's likely
    a float literal.  Otherwise treat as integer.
    """
    if bits == 0:
        return False  # 0 is more likely integer 0
    try:
        f = struct.unpack("<d", struct.pack("<Q", bits))[0]
    except struct.error:
        return False
    import math
    if math.isnan(f) or math.isinf(f):
        return False
    # If the int value itself is small (<65536) it's likely an integer
    if bits <= 0xFFFF:
        return False
    # If the float form is a "round-ish" number, probably a float
    if abs(f) < 1e18 and f != 0.0:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: disassemble a single instruction
# ─────────────────────────────────────────────────────────────────────────────

def disassemble_instruction(code: bytes | bytearray, offset: int,
                            string_table: Optional[List[str]] = None
                            ) -> Tuple[str, int]:
    """
    Disassemble one instruction at *offset*.

    Returns
    -------
    (text, next_offset) : Tuple[str, int]
        The textual representation and the offset of the next instruction.
    """
    strings = string_table or []
    opcode_byte = code[offset]
    off = offset + 1

    try:
        op = Op(opcode_byte)
    except ValueError:
        return f".byte 0x{opcode_byte:02X}", off

    schema = OPCODE_META.get(op, ((), ""))[0]
    parts = [op.name]

    for kind in schema:
        if kind == "imm64":
            val, off = _read_u64(code, off)
            parts.append(f"0x{val:X}" if val > 0xFFFF else str(val))
        elif kind in ("imm32", "addr32"):
            val, off = _read_u32(code, off)
            parts.append(f"0x{val:04X}")
        elif kind == "imm8":
            val, off = _read_u8(code, off)
            parts.append(str(val))
        elif kind == "reg":
            val, off = _read_u8(code, off)
            parts.append(_REG_NAMES.get(val, f"r{val}"))
        elif kind == "str_idx":
            val, off = _read_u32(code, off)
            if val < len(strings):
                parts.append(f'"{strings[val]}"')
            else:
                parts.append(f"str[{val}]")

    return " ".join(parts), off


# ─────────────────────────────────────────────────────────────────────────────
# Instruction length calculator
# ─────────────────────────────────────────────────────────────────────────────

def instruction_length(op: Op) -> int:
    """Return the byte length of a complete instruction for *op*."""
    schema = OPCODE_META.get(op, ((), ""))[0]
    length = 1  # opcode byte
    for kind in schema:
        if kind == "imm64":
            length += 8
        elif kind in ("imm32", "addr32", "str_idx"):
            length += 4
        elif kind in ("imm8", "reg"):
            length += 1
    return length
