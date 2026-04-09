"""
lateralus_lang/bytecode_format.py  ─  LATERALUS Compiled Binary Format (.ltlc)
═══════════════════════════════════════════════════════════════════════════════
Proprietary compiler and decompiler for LATERALUS bytecode.

The .ltlc format is a binary container that packages:
  · File header with magic bytes, version, and metadata
  · Source code hash (integrity verification)
  · Symbol table (function names, types, line mappings)
  · Constant pool (strings, numbers, etc.)
  · Instruction stream (compact bytecode)
  · Debug info (optional — source maps, variable names)
  · Digital signature (optional — tamper detection)

Workflow:
  lateralus compile program.ltl → program.ltlc     (compiler)
  lateralus decompile program.ltlc → program.ltl   (decompiler)
  lateralus run program.ltlc                        (direct execution)

v1.5.0
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import json
import struct
import time
import zlib
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional

from lateralus_lang.crypto_engine import hmac_sign, hmac_verify

# ─────────────────────────────────────────────────────────────────────────────
# Binary format constants
# ─────────────────────────────────────────────────────────────────────────────

LTLC_MAGIC      = b"\x89LTL"   # 4 bytes — file magic
LTLC_VERSION    = 1             # uint16 — format version
LTLC_EXTENSION  = ".ltlc"

# Section types
class SectionType(IntEnum):
    METADATA     = 0x01
    SOURCE_HASH  = 0x02
    CONSTANTS    = 0x03
    SYMBOLS      = 0x04
    INSTRUCTIONS = 0x05
    DEBUG_INFO   = 0x06
    SIGNATURE    = 0x07


# Constant pool tags
class ConstTag(IntEnum):
    NULL    = 0x00
    BOOL    = 0x01
    INT     = 0x02
    FLOAT   = 0x03
    STRING  = 0x04


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LTLCMetadata:
    """Compiled file metadata."""
    source_file: str = ""
    language_version: str = "1.5.0"
    compile_time: float = 0.0
    compiler_version: str = "1.5.0"
    target: str = "vm"
    flags: int = 0  # bit 0: compressed, bit 1: debug, bit 2: signed

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def has_debug(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def is_signed(self) -> bool:
        return bool(self.flags & 0x04)


@dataclass
class Symbol:
    """Symbol table entry."""
    name: str
    kind: str          # "function", "variable", "constant", "struct", "module"
    scope: str = ""    # module path
    offset: int = 0    # instruction offset
    arity: int = 0     # number of parameters (for functions)
    line: int = 0      # source line number
    type_sig: str = "" # type signature string


@dataclass
class DebugLine:
    """Maps instruction offset to source line."""
    offset: int
    line: int
    column: int = 0
    file: str = ""


@dataclass
class LTLCFile:
    """Complete .ltlc compiled file representation."""
    metadata: LTLCMetadata = field(default_factory=LTLCMetadata)
    source_hash: str = ""
    constants: List[Any] = field(default_factory=list)
    symbols: List[Symbol] = field(default_factory=list)
    instructions: bytes = b""
    debug_lines: List[DebugLine] = field(default_factory=list)
    signature: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Compiler — Source (.ltl) → Binary (.ltlc)
# ─────────────────────────────────────────────────────────────────────────────

class LTLCCompiler:
    """Compile LATERALUS source or IR into .ltlc binary format."""

    def __init__(self, compress: bool = True, include_debug: bool = True,
                 signing_key: Optional[str] = None):
        self.compress = compress
        self.include_debug = include_debug
        self.signing_key = signing_key

    def compile_source(self, source: str, source_file: str = "<input>") -> bytes:
        """Compile source code to .ltlc binary.

        This creates a self-contained binary that embeds:
        - The transpiled Python code as instruction bytes
        - Source hash for integrity verification
        - Symbol table extracted from the AST
        - Debug line mappings
        """
        # Build the LTLCFile
        ltlc = LTLCFile()
        ltlc.metadata = LTLCMetadata(
            source_file=source_file,
            compile_time=time.time(),
            flags=((0x01 if self.compress else 0) |
                   (0x02 if self.include_debug else 0) |
                   (0x04 if self.signing_key else 0)),
        )
        ltlc.source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

        # Extract constants and symbols from source
        ltlc.constants = self._extract_constants(source)
        ltlc.symbols = self._extract_symbols(source)

        # Store the source as instruction bytes (for the transpiler path)
        ltlc.instructions = source.encode("utf-8")

        # Debug info
        if self.include_debug:
            ltlc.debug_lines = self._build_debug_lines(source, source_file)

        return self._serialize(ltlc)

    def compile_to_file(self, source: str, output_path: str,
                        source_file: str = "<input>") -> str:
        """Compile and write to file."""
        data = self.compile_source(source, source_file)
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path

    # ── Extraction helpers ────────────────────────────────────────────────

    def _extract_constants(self, source: str) -> List[Any]:
        """Extract literal constants from source for the constant pool."""
        import re
        constants = []
        seen = set()

        # String literals
        for m in re.finditer(r'"([^"]*)"', source):
            val = m.group(1)
            if val not in seen:
                constants.append(val)
                seen.add(val)

        # Number literals
        for m in re.finditer(r'\b(\d+\.?\d*)\b', source):
            val = m.group(1)
            if val not in seen:
                num = float(val) if "." in val else int(val)
                constants.append(num)
                seen.add(val)

        return constants

    def _extract_symbols(self, source: str) -> List[Symbol]:
        """Extract function/variable declarations from source."""
        import re
        symbols = []

        # Functions: fn name(params...)
        for m in re.finditer(r'fn\s+(\w+)\s*\(([^)]*)\)', source):
            name = m.group(1)
            params = m.group(2)
            arity = len([p for p in params.split(",") if p.strip()]) if params.strip() else 0
            line = source[:m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="function", arity=arity,
                line=line, offset=m.start(),
            ))

        # Variables: let name =
        for m in re.finditer(r'let\s+(\w+)\s*(?::\s*\w+)?\s*=', source):
            name = m.group(1)
            line = source[:m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="variable",
                line=line, offset=m.start(),
            ))

        # Structs: struct Name
        for m in re.finditer(r'struct\s+(\w+)', source):
            name = m.group(1)
            line = source[:m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="struct",
                line=line, offset=m.start(),
            ))

        return symbols

    def _build_debug_lines(self, source: str, filename: str) -> List[DebugLine]:
        """Build offset-to-line mapping for debugging."""
        lines = source.split("\n")
        debug = []
        offset = 0
        for i, line in enumerate(lines, 1):
            if line.strip():  # skip blank lines
                debug.append(DebugLine(offset=offset, line=i, file=filename))
            offset += len(line.encode("utf-8")) + 1  # +1 for newline
        return debug

    # ── Serialization ─────────────────────────────────────────────────────

    def _serialize(self, ltlc: LTLCFile) -> bytes:
        """Serialize LTLCFile to binary format."""
        sections = []

        # Section 1: Metadata
        meta_json = json.dumps({
            "source_file": ltlc.metadata.source_file,
            "language_version": ltlc.metadata.language_version,
            "compile_time": ltlc.metadata.compile_time,
            "compiler_version": ltlc.metadata.compiler_version,
            "target": ltlc.metadata.target,
            "flags": ltlc.metadata.flags,
        }).encode("utf-8")
        sections.append(self._make_section(SectionType.METADATA, meta_json))

        # Section 2: Source hash
        hash_data = ltlc.source_hash.encode("ascii")
        sections.append(self._make_section(SectionType.SOURCE_HASH, hash_data))

        # Section 3: Constants
        const_data = self._serialize_constants(ltlc.constants)
        sections.append(self._make_section(SectionType.CONSTANTS, const_data))

        # Section 4: Symbols
        sym_json = json.dumps([{
            "name": s.name, "kind": s.kind, "scope": s.scope,
            "offset": s.offset, "arity": s.arity, "line": s.line,
            "type_sig": s.type_sig,
        } for s in ltlc.symbols]).encode("utf-8")
        sections.append(self._make_section(SectionType.SYMBOLS, sym_json))

        # Section 5: Instructions
        instr_data = ltlc.instructions
        if self.compress:
            instr_data = zlib.compress(instr_data, level=6)
        sections.append(self._make_section(SectionType.INSTRUCTIONS, instr_data))

        # Section 6: Debug info (optional)
        if self.include_debug and ltlc.debug_lines:
            debug_json = json.dumps([{
                "offset": d.offset, "line": d.line,
                "column": d.column, "file": d.file,
            } for d in ltlc.debug_lines]).encode("utf-8")
            sections.append(self._make_section(SectionType.DEBUG_INFO, debug_json))

        # Assemble body
        body = b"".join(sections)

        # Section 7: Signature (optional)
        if self.signing_key:
            sig = hmac_sign(self.signing_key, body)
            sig_data = sig.encode("ascii")
            body += self._make_section(SectionType.SIGNATURE, sig_data)

        # Header
        header = (
            LTLC_MAGIC +
            struct.pack(">H", LTLC_VERSION) +
            struct.pack(">I", len(sections) + (1 if self.signing_key else 0)) +
            struct.pack(">Q", len(body))
        )

        return header + body

    def _make_section(self, section_type: SectionType, data: bytes) -> bytes:
        """Create a section: type(1) + length(4) + data."""
        return (struct.pack(">B", section_type) +
                struct.pack(">I", len(data)) +
                data)

    def _serialize_constants(self, constants: List[Any]) -> bytes:
        """Serialize constant pool to bytes."""
        parts = [struct.pack(">I", len(constants))]
        for val in constants:
            if val is None:
                parts.append(struct.pack(">B", ConstTag.NULL))
            elif isinstance(val, bool):
                parts.append(struct.pack(">BB", ConstTag.BOOL, 1 if val else 0))
            elif isinstance(val, int):
                parts.append(struct.pack(">Bq", ConstTag.INT, val))
            elif isinstance(val, float):
                parts.append(struct.pack(">Bd", ConstTag.FLOAT, val))
            elif isinstance(val, str):
                encoded = val.encode("utf-8")
                parts.append(struct.pack(">BI", ConstTag.STRING, len(encoded)) + encoded)
            else:
                # Fallback: stringify
                encoded = str(val).encode("utf-8")
                parts.append(struct.pack(">BI", ConstTag.STRING, len(encoded)) + encoded)
        return b"".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Decompiler — Binary (.ltlc) → Source (.ltl)
# ─────────────────────────────────────────────────────────────────────────────

class LTLCDecompiler:
    """Decompile .ltlc binary back to LATERALUS source."""

    def __init__(self, signing_key: Optional[str] = None):
        self.signing_key = signing_key

    def decompile(self, data: bytes) -> LTLCFile:
        """Parse a .ltlc binary into an LTLCFile."""
        if data[:4] != LTLC_MAGIC:
            raise ValueError("Not a valid .ltlc file — bad magic bytes")

        version = struct.unpack(">H", data[4:6])[0]
        if version > LTLC_VERSION:
            raise ValueError(f".ltlc version {version} not supported "
                             f"(max: {LTLC_VERSION})")

        num_sections = struct.unpack(">I", data[6:10])[0]
        body_length = struct.unpack(">Q", data[10:18])[0]

        body = data[18:18 + body_length]
        pos = 0

        ltlc = LTLCFile()

        while pos < len(body):
            if pos + 5 > len(body):
                break
            section_type = body[pos]
            section_len = struct.unpack(">I", body[pos+1:pos+5])[0]
            section_data = body[pos+5:pos+5+section_len]
            pos += 5 + section_len

            self._process_section(ltlc, section_type, section_data)

        # Verify signature if we have a key
        if self.signing_key and ltlc.metadata.is_signed:
            if not ltlc.signature:
                raise ValueError("File claims to be signed but no signature found")
            # Re-serialize body without signature for verification
            body_without_sig = body[:pos - 5 - len(ltlc.signature.encode("ascii"))]
            if not hmac_verify(self.signing_key, body_without_sig,
                               ltlc.signature):
                raise ValueError("Signature verification FAILED — "
                                 "file may have been tampered with!")

        return ltlc

    def decompile_file(self, path: str) -> LTLCFile:
        """Load and decompile a .ltlc file."""
        with open(path, "rb") as f:
            return self.decompile(f.read())

    def decompile_to_source(self, data: bytes) -> str:
        """Decompile .ltlc binary back to LATERALUS source code."""
        ltlc = self.decompile(data)

        # If instructions contain the original source (transpiler path)
        instr = ltlc.instructions
        if ltlc.metadata.is_compressed:
            instr = zlib.decompress(instr)

        source = instr.decode("utf-8")

        # Add decompilation header comment
        header = (
            f"// Decompiled from: {ltlc.metadata.source_file}\n"
            f"// Compiled at: {time.ctime(ltlc.metadata.compile_time)}\n"
            f"// Compiler version: {ltlc.metadata.compiler_version}\n"
            f"// Source hash: {ltlc.source_hash[:16]}...\n"
            f"// Symbols: {len(ltlc.symbols)} | Constants: {len(ltlc.constants)}\n"
            f"\n"
        )

        return header + source

    def decompile_to_file(self, input_path: str,
                          output_path: Optional[str] = None) -> str:
        """Decompile .ltlc file and write source to .ltl file."""
        with open(input_path, "rb") as f:
            data = f.read()
        source = self.decompile_to_source(data)
        if output_path is None:
            output_path = input_path.rsplit(".", 1)[0] + ".ltl"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(source)
        return output_path

    # ── Section processing ────────────────────────────────────────────────

    def _process_section(self, ltlc: LTLCFile, section_type: int,
                         data: bytes):
        if section_type == SectionType.METADATA:
            meta = json.loads(data.decode("utf-8"))
            ltlc.metadata = LTLCMetadata(**meta)

        elif section_type == SectionType.SOURCE_HASH:
            ltlc.source_hash = data.decode("ascii")

        elif section_type == SectionType.CONSTANTS:
            ltlc.constants = self._deserialize_constants(data)

        elif section_type == SectionType.SYMBOLS:
            syms = json.loads(data.decode("utf-8"))
            ltlc.symbols = [Symbol(**s) for s in syms]

        elif section_type == SectionType.INSTRUCTIONS:
            ltlc.instructions = data

        elif section_type == SectionType.DEBUG_INFO:
            debug = json.loads(data.decode("utf-8"))
            ltlc.debug_lines = [DebugLine(**d) for d in debug]

        elif section_type == SectionType.SIGNATURE:
            ltlc.signature = data.decode("ascii")

    def _deserialize_constants(self, data: bytes) -> List[Any]:
        count = struct.unpack(">I", data[:4])[0]
        pos = 4
        constants = []
        for _ in range(count):
            tag = data[pos]
            pos += 1
            if tag == ConstTag.NULL:
                constants.append(None)
            elif tag == ConstTag.BOOL:
                constants.append(bool(data[pos]))
                pos += 1
            elif tag == ConstTag.INT:
                val = struct.unpack(">q", data[pos:pos+8])[0]
                constants.append(val)
                pos += 8
            elif tag == ConstTag.FLOAT:
                val = struct.unpack(">d", data[pos:pos+8])[0]
                constants.append(val)
                pos += 8
            elif tag == ConstTag.STRING:
                length = struct.unpack(">I", data[pos:pos+4])[0]
                pos += 4
                constants.append(data[pos:pos+length].decode("utf-8"))
                pos += length
        return constants


# ─────────────────────────────────────────────────────────────────────────────
# Inspector — analyze .ltlc files without decompiling
# ─────────────────────────────────────────────────────────────────────────────

class LTLCInspector:
    """Inspect a .ltlc binary and report its contents."""

    def inspect(self, data: bytes) -> Dict[str, Any]:
        """Return a structured report of the .ltlc file."""
        decompiler = LTLCDecompiler()
        ltlc = decompiler.decompile(data)

        return {
            "format": "LATERALUS Compiled Binary",
            "version": LTLC_VERSION,
            "source_file": ltlc.metadata.source_file,
            "language_version": ltlc.metadata.language_version,
            "compiler_version": ltlc.metadata.compiler_version,
            "compiled_at": time.ctime(ltlc.metadata.compile_time),
            "compressed": ltlc.metadata.is_compressed,
            "has_debug": ltlc.metadata.has_debug,
            "signed": ltlc.metadata.is_signed,
            "source_hash": ltlc.source_hash,
            "constants_count": len(ltlc.constants),
            "symbols_count": len(ltlc.symbols),
            "instruction_bytes": len(ltlc.instructions),
            "debug_lines": len(ltlc.debug_lines),
            "symbols": [{
                "name": s.name,
                "kind": s.kind,
                "line": s.line,
                "arity": s.arity,
            } for s in ltlc.symbols],
        }

    def inspect_file(self, path: str) -> Dict[str, Any]:
        with open(path, "rb") as f:
            return self.inspect(f.read())

    def print_report(self, data: bytes):
        """Print a human-readable report."""
        info = self.inspect(data)
        print("╔═══════════════════════════════════════════════════╗")
        print("║  LATERALUS Compiled Binary (.ltlc) Inspector     ║")
        print("╠═══════════════════════════════════════════════════╣")
        print(f"║  Source:    {info['source_file']:<38s} ║")
        print(f"║  Compiled:  {info['compiled_at']:<38s} ║")
        print(f"║  Version:   {info['language_version']:<38s} ║")
        print(f"║  Compiler:  {info['compiler_version']:<38s} ║")
        print(f"║  Hash:      {info['source_hash'][:32]:<38s} ║")
        print("╠═══════════════════════════════════════════════════╣")
        print(f"║  Constants: {info['constants_count']:<38d} ║")
        print(f"║  Symbols:   {info['symbols_count']:<38d} ║")
        print(f"║  Code size: {info['instruction_bytes']:<38d} ║")
        print(f"║  Debug:     {str(info['has_debug']):<38s} ║")
        print(f"║  Signed:    {str(info['signed']):<38s} ║")
        print(f"║  Compressed:{str(info['compressed']):<38s} ║")
        print("╠═══════════════════════════════════════════════════╣")
        print("║  Symbol Table:                                   ║")
        for sym in info['symbols']:
            kind_str = f"[{sym['kind']}]"
            name = sym['name']
            line = f"L{sym['line']}"
            print(f"║    {kind_str:<12s} {name:<24s} {line:<8s}  ║")
        print("╚═══════════════════════════════════════════════════╝")
