"""
lateralus_lang/vm/assembler.py  -  LATERALUS Assembly (.ltasm) Assembler
===========================================================================
Converts .ltasm source text into a LTasm bytecode object (Bytecode).

.ltasm syntax
-------------
  ; comment
  .section  code | data | bss
  .global   label           — mark label as entry / export
  .string   "text"          — define string constant
  .byte     N               — define raw byte
  .word     N               — define 64-bit word
  .reserve  N               — reserve N bytes in bss

  label:                    — define a label (address anchor)
  MNEMONIC  [operand, ...]  — instruction

Operand types
-------------
  42          — integer immediate
  0xFF        — hex immediate
  3.14        — float immediate
  "hello"     — string (added to string table, str_idx emitted)
  r0 … r15   — register  (0–15)
  .label      — forward/backward label reference (4-byte address)
  #label      — same as .label but commonly used for jumps

Passes
------
  1  Scan source, collect labels, string table, build instruction list
  2  Resolve forward references, emit final bytecode
===========================================================================
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .opcodes import MNEMONIC_MAP, Op

# -----------------------------------------------------------------------------
# Bytecode object
# -----------------------------------------------------------------------------

@dataclass
class Bytecode:
    """Assembled LTasm bytecode ready for the VM."""
    code:          bytearray           = field(default_factory=bytearray)
    string_table:  List[str]           = field(default_factory=list)
    data_segment:  bytearray           = field(default_factory=bytearray)
    entry_point:   int                 = 0            # byte offset in code
    labels:        Dict[str, int]      = field(default_factory=dict)
    source_map:    Dict[int, Tuple[int, int]] = field(default_factory=dict)  # offset → (line, col)

    def intern_string(self, s: str) -> int:
        """Add string to table if not present; return its index."""
        try:
            return self.string_table.index(s)
        except ValueError:
            self.string_table.append(s)
            return len(self.string_table) - 1

    def emit_u8(self, v: int) -> int:
        off = len(self.code)
        self.code.append(v & 0xFF)
        return off

    def emit_u32(self, v: int) -> int:
        off = len(self.code)
        self.code += struct.pack(">I", v & 0xFFFF_FFFF)
        return off

    def emit_u64(self, v: int) -> int:
        off = len(self.code)
        self.code += struct.pack(">Q", v & 0xFFFF_FFFF_FFFF_FFFF)
        return off

    def emit_f64(self, v: float) -> int:
        off = len(self.code)
        self.code += struct.pack(">d", v)
        return off

    def patch_u32(self, offset: int, v: int) -> None:
        struct.pack_into(">I", self.code, offset, v & 0xFFFF_FFFF)


# -----------------------------------------------------------------------------
# Assembler error
# -----------------------------------------------------------------------------

class AssemblerError(Exception):
    def __init__(self, msg: str, file: str = "<asm>", line: int = 0):
        super().__init__(f"{file}:{line}: AssemblerError: {msg}")
        self.file, self.line = file, line


# -----------------------------------------------------------------------------
# Tokenizer (simple line-oriented)
# -----------------------------------------------------------------------------

_RE_LINE    = re.compile(r"""
    (?:;[^\n]*)          |    # comment
    ([A-Za-z_][A-Za-z0-9_.]*) |   # identifier / mnemonic
    (0[xX][0-9a-fA-F_]+) |   # hex
    (0[bB][01_]+)         |   # binary
    (-?\d+\.\d+(?:[eE][+-]?\d+)?) |  # float
    (-?\d+)               |   # integer
    "([^"\\]*(?:\\.[^"\\]*)*)" |  # string literal
    ([,:#.])              |   # delimiters
    \s+                       # whitespace (skip)
""", re.VERBOSE)

def _tokenize_line(line: str) -> List[str]:
    tokens = []
    for m in _RE_LINE.finditer(line):
        # Skip whitespace and pure comments
        g = m.group(0).strip()
        if not g or g.startswith(";"):
            continue
        tokens.append(g)
    return tokens


# -----------------------------------------------------------------------------
# Assembler
# -----------------------------------------------------------------------------

@dataclass
class _Instr:
    """Pending instruction before label resolution."""
    op:        Op
    operands:  List[Any]          # raw parsed values
    code_off:  int                # byte offset where this was emitted
    line:      int
    fixups:    List[Tuple[int, str]] = field(default_factory=list)
    # fixups: list of (byte_offset_in_code, label_name)


class Assembler:
    def __init__(self, source: str, filename: str = "<asm>"):
        self._src  = source
        self._file = filename

    def assemble(self) -> Bytecode:
        bc = Bytecode()
        labels: Dict[str, int] = {}      # label → code offset
        pending_fixups: List[Tuple[int, str, int]] = []
        # pending_fixups: (code_offset_of_u32, label_name, src_line)

        current_section = "code"
        global_labels: set = set()

        lines = self._src.splitlines()
        for lineno, raw_line in enumerate(lines, 1):
            toks = _tokenize_line(raw_line)
            if not toks:
                continue

            # Directives
            if toks[0].startswith("."):
                directive = toks[0].lower()

                if directive == ".section":
                    current_section = toks[1].lower() if len(toks) > 1 else "code"

                elif directive == ".global":
                    if len(toks) > 1:
                        global_labels.add(toks[1])

                elif directive == ".string":
                    s = self._parse_string_literal(toks[1], lineno)
                    bc.intern_string(s)

                elif directive == ".byte":
                    val = int(toks[1], 0)
                    if current_section == "data":
                        bc.data_segment.append(val & 0xFF)

                elif directive == ".word":
                    val = int(toks[1], 0)
                    if current_section == "data":
                        bc.data_segment += struct.pack("<Q", val)

                elif directive == ".reserve":
                    n = int(toks[1], 0)
                    if current_section in ("data", "bss"):
                        bc.data_segment += bytes(n)
                continue

            # Label definition:  "name:" OR "name" ":"  (colon may be
            # a separate token when the regex splits it)
            is_label = (toks[0].endswith(":") or
                        (len(toks) > 1 and toks[1] == ":"))
            if is_label:
                if toks[0].endswith(":"):
                    lbl  = toks[0][:-1]
                    toks = toks[1:]
                else:
                    lbl  = toks[0]
                    toks = toks[2:]   # skip name + ":"
                labels[lbl] = len(bc.code)
                bc.labels[lbl] = len(bc.code)
                if lbl in ("_start", "main"):
                    bc.entry_point = len(bc.code)
                if not toks:
                    continue

            # Instruction
            mnemonic = toks[0].upper()
            if mnemonic not in MNEMONIC_MAP:
                raise AssemblerError(f"Unknown mnemonic {mnemonic!r}", self._file, lineno)
            op = MNEMONIC_MAP[mnemonic]
            operands = toks[1:]   # still raw strings, comma-stripped

            # Remove commas
            operands = [o.rstrip(",").lstrip(",") for o in operands if o != ","]

            # Emit instruction
            bc.source_map[len(bc.code)] = (lineno, 0)
            bc.emit_u8(int(op))
            self._emit_operands(bc, op, operands, lineno, pending_fixups)

        # Resolve fixups
        for (code_off, label, src_line) in pending_fixups:
            if label not in labels:
                raise AssemblerError(f"Undefined label {label!r}", self._file, src_line)
            bc.patch_u32(code_off, labels[label])

        bc.labels = labels
        return bc

    # -- operand emitter -------------------------------------------------------

    def _emit_operands(self, bc: Bytecode, op: Op,
                       operands: List[str], lineno: int,
                       fixups: List) -> None:
        from .opcodes import OPCODE_META
        schema = OPCODE_META.get(op, ((), ""))[0]

        for i, kind in enumerate(schema):
            raw = operands[i] if i < len(operands) else "0"

            if kind == "imm64":
                if raw.startswith('"'):
                    # string as imm → intern + push str_idx as imm
                    s = self._parse_string_literal(raw, lineno)
                    bc.emit_u64(bc.intern_string(s))
                elif "." in raw and raw.replace(".", "").replace("-", "").replace("e", "").replace("E", "").replace("+", "").isdigit():
                    # float encoded as u64 bit pattern
                    import struct as _s
                    bits = _s.unpack("<Q", _s.pack("<d", float(raw)))[0]
                    bc.emit_u64(bits)
                else:
                    bc.emit_u64(int(raw, 0))

            elif kind == "imm32":
                if raw.startswith((".","#")):
                    label = raw.lstrip(".#")
                    off = bc.emit_u32(0)   # placeholder
                    fixups.append((off, label, lineno))
                elif raw[0].isalpha() or raw[0] == "_":
                    # Plain label name (forward/backward reference)
                    off = bc.emit_u32(0)
                    fixups.append((off, raw, lineno))
                else:
                    bc.emit_u32(int(raw, 0))

            elif kind == "imm8":
                bc.emit_u8(int(raw, 0))

            elif kind == "reg":
                reg_n = self._parse_reg(raw, lineno)
                bc.emit_u8(reg_n)

            elif kind == "addr32":
                # Treat .label, #label, or any bare identifier as a label ref
                if raw.startswith((".","#")):
                    label = raw.lstrip(".#")
                    off = bc.emit_u32(0)
                    fixups.append((off, label, lineno))
                elif raw[0].isalpha() or raw[0] == "_":
                    # Plain label name (e.g. "end", "_start", "loop_top")
                    off = bc.emit_u32(0)
                    fixups.append((off, raw, lineno))
                else:
                    bc.emit_u32(int(raw, 0))

            elif kind == "str_idx":
                s = self._parse_string_literal(raw, lineno) if raw.startswith('"') else raw
                bc.emit_u32(bc.intern_string(s))

    def _parse_reg(self, raw: str, lineno: int) -> int:
        raw = raw.strip().lower()
        if raw.startswith("r"):
            try:
                n = int(raw[1:])
                if 0 <= n <= 15:
                    return n
            except ValueError:
                pass
        raise AssemblerError(f"Invalid register {raw!r}", self._file, lineno)

    @staticmethod
    def _parse_string_literal(raw: str, lineno: int) -> str:
        raw = raw.strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        return raw.encode("raw_unicode_escape").decode("unicode_escape")


# -----------------------------------------------------------------------------
# Convenience
# -----------------------------------------------------------------------------

def assemble(source: str, filename: str = "<asm>") -> Bytecode:
    """Assemble .ltasm *source* and return Bytecode object."""
    return Assembler(source, filename).assemble()
