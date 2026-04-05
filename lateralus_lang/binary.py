"""
lateralus_lang/binary.py  -  LTLC Binary Format (Proprietary)
===========================================================================
Serializes / deserializes compiled Lateralus programs to/from the
proprietary .ltlc binary format.

Format Structure
----------------
  HEADER  (32 bytes)
    Magic:       b"LTLC"                 (4 bytes)
    Version:     u16 major, u16 minor    (4 bytes)
    Flags:       u32                     (4 bytes)
    Timestamp:   u64 unix epoch          (8 bytes)
    AST Size:    u64                     (8 bytes)
    Checksum:    u32 CRC-32              (4 bytes)

  METADATA  (variable)
    Source filename length: u32
    Source filename: UTF-8 bytes
    Module name length: u32
    Module name: UTF-8 bytes

  AST PAYLOAD  (compressed)
    zlib-compressed pickle of the AST Program node

The decompiler reads this format back and reconstructs readable .ltl
source from the AST.

Usage
-----
  ltlc compile hello.ltl -o hello.ltlc   # compile
  ltlc decompile hello.ltlc              # decompile back to .ltl
===========================================================================
"""
from __future__ import annotations

import hashlib
import pickle
import struct
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .ast_nodes import (
    AssignStmt, BinOp, BlockStmt, BreakStmt, CallExpr, CastExpr,
    ContinueStmt, Decorator, EmitStmt, EnumDecl, ExprStmt, FieldExpr,
    FnDecl, ForeignBlock, ForStmt, Ident, IfStmt, ImplBlock, ImportStmt,
    IndexExpr, InterfaceDecl, InterpolatedStr, LambdaExpr, LetDecl,
    ListExpr, Literal, LoopStmt, MapExpr, MatchArm, MatchStmt,
    MeasureBlock, Param, ProbeExpr, Program, RangeExpr, RecoverClause,
    ReturnStmt, SelfExpr, SpawnExpr, StructDecl, StructLiteral,
    ThrowStmt, TryExpr, TryStmt, TupleExpr, TypeAlias, UnaryOp,
    WhileStmt, YieldExpr,
)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MAGIC = b"LTLC"
FORMAT_VERSION_MAJOR = 1
FORMAT_VERSION_MINOR = 4
FLAG_COMPRESSED = 0x01
FLAG_HAS_SOURCE = 0x02
HEADER_SIZE = 32


# -----------------------------------------------------------------------------
# Compiler  (AST → .ltlc binary)
# -----------------------------------------------------------------------------

@dataclass
class LTLCHeader:
    magic: bytes = MAGIC
    version_major: int = FORMAT_VERSION_MAJOR
    version_minor: int = FORMAT_VERSION_MINOR
    flags: int = FLAG_COMPRESSED
    timestamp: int = 0
    ast_size: int = 0
    checksum: int = 0

    def pack(self) -> bytes:
        return struct.pack(
            "<4sHHIQQI",
            self.magic,
            self.version_major,
            self.version_minor,
            self.flags,
            self.timestamp,
            self.ast_size,
            self.checksum,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "LTLCHeader":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Invalid LTLC file: header too short ({len(data)} bytes)")
        magic, vmaj, vmin, flags, ts, ast_sz, csum = struct.unpack(
            "<4sHHIQQI", data[:HEADER_SIZE]
        )
        if magic != MAGIC:
            raise ValueError(f"Not an LTLC file: bad magic {magic!r}")
        return cls(magic, vmaj, vmin, flags, ts, ast_sz, csum)


def compile_to_ltlc(program: Program, source_file: str = "<unknown>",
                    module_name: str = "") -> bytes:
    """Compile an AST Program to .ltlc binary format."""
    # Serialize AST
    ast_bytes = pickle.dumps(program, protocol=pickle.HIGHEST_PROTOCOL)
    compressed = zlib.compress(ast_bytes, level=9)

    # Build metadata
    src_name = source_file.encode("utf-8")
    mod_name = module_name.encode("utf-8")
    metadata = struct.pack("<I", len(src_name)) + src_name
    metadata += struct.pack("<I", len(mod_name)) + mod_name

    # Compute checksum over metadata + payload
    payload = metadata + compressed
    checksum = zlib.crc32(payload) & 0xFFFFFFFF

    header = LTLCHeader(
        flags=FLAG_COMPRESSED | FLAG_HAS_SOURCE,
        timestamp=int(time.time()),
        ast_size=len(compressed),
        checksum=checksum,
    )

    return header.pack() + payload


def decompile_from_ltlc(data: bytes) -> tuple:
    """Read an .ltlc binary and return (Program, source_file, module_name)."""
    header = LTLCHeader.unpack(data)
    pos = HEADER_SIZE

    # Read metadata
    src_len = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
    source_file = data[pos:pos+src_len].decode("utf-8"); pos += src_len
    mod_len = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
    module_name = data[pos:pos+mod_len].decode("utf-8"); pos += mod_len

    # Read compressed AST
    compressed = data[pos:pos+header.ast_size]

    # Verify checksum
    payload = data[HEADER_SIZE:pos+header.ast_size]
    actual_csum = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_csum != header.checksum:
        raise ValueError(
            f"LTLC checksum mismatch: expected {header.checksum:#010x}, "
            f"got {actual_csum:#010x}"
        )

    # Decompress and unpickle
    ast_bytes = zlib.decompress(compressed)
    program = pickle.loads(ast_bytes)

    return program, source_file, module_name


# -----------------------------------------------------------------------------
# Decompiler  (.ltlc → .ltl readable source)
# -----------------------------------------------------------------------------

class Decompiler:
    """Reconstruct readable .ltl source code from an AST Program."""

    def __init__(self, indent_size: int = 4):
        self._lines: list = []
        self._indent = 0
        self._indent_size = indent_size

    def decompile(self, program: Program) -> str:
        """Convert a Program AST back to .ltl source code."""
        self._lines = []
        self._indent = 0

        if program.module:
            self._line(f"module {program.module}")
            self._line("")

        for imp in program.imports:
            self._decompile_import(imp)
        if program.imports:
            self._line("")

        for stmt in program.body:
            self._decompile_stmt(stmt)

        return "\n".join(self._lines)

    # -- helpers -----------------------------------------------------------

    def _line(self, text: str = ""):
        if text:
            self._lines.append("    " * self._indent + text)
        else:
            self._lines.append("")

    def _push(self): self._indent += 1
    def _pop(self): self._indent -= 1

    # -- statements --------------------------------------------------------

    def _decompile_import(self, node: ImportStmt):
        if node.items:
            items = ", ".join(node.items)
            self._line(f"import {node.path} {{ {items} }}")
        elif node.alias:
            self._line(f"import {node.path} as {node.alias}")
        else:
            self._line(f"import {node.path}")

    def _decompile_stmt(self, node):
        if isinstance(node, FnDecl):
            self._decompile_fn(node)
        elif isinstance(node, LetDecl):
            val = f" = {self._expr(node.value)}" if node.value else ""
            typ = f": {node.type_}" if node.type_ else ""
            kw = "const" if node.is_const else "let"
            self._line(f"{kw} {node.name}{typ}{val}")
        elif isinstance(node, ReturnStmt):
            val = f" {self._expr(node.value)}" if node.value else ""
            self._line(f"return{val}")
        elif isinstance(node, IfStmt):
            self._line(f"if {self._expr(node.condition)} {{")
            self._push()
            self._decompile_block(node.then_block)
            self._pop()
            for cond, block in node.elif_arms:
                self._line(f"}} elif {self._expr(cond)} {{")
                self._push()
                self._decompile_block(block)
                self._pop()
            if node.else_block:
                self._line("} else {")
                self._push()
                self._decompile_block(node.else_block)
                self._pop()
            self._line("}")
        elif isinstance(node, MatchStmt):
            self._line(f"match {self._expr(node.subject)} {{")
            self._push()
            for arm in node.arms:
                guard = f" if {self._expr(arm.guard)}" if arm.guard else ""
                if arm.body:
                    self._line(f"{self._expr(arm.pattern)}{guard} => {{")
                    self._push()
                    self._decompile_block(arm.body)
                    self._pop()
                    self._line("}")
                elif arm.value:
                    self._line(f"{self._expr(arm.pattern)}{guard} => {self._expr(arm.value)}")
            self._pop()
            self._line("}")
        elif isinstance(node, WhileStmt):
            self._line(f"while {self._expr(node.condition)} {{")
            self._push()
            self._decompile_block(node.body)
            self._pop()
            self._line("}")
        elif isinstance(node, LoopStmt):
            self._line("loop {")
            self._push()
            self._decompile_block(node.body)
            self._pop()
            self._line("}")
        elif isinstance(node, ForStmt):
            self._line(f"for {node.var} in {self._expr(node.iter)} {{")
            self._push()
            self._decompile_block(node.body)
            self._pop()
            self._line("}")
        elif isinstance(node, BreakStmt):
            self._line("break")
        elif isinstance(node, ContinueStmt):
            self._line("continue")
        elif isinstance(node, TryStmt):
            self._line("try {")
            self._push()
            self._decompile_block(node.body)
            self._pop()
            for clause in node.recoveries:
                typ = clause.error_type or "*"
                bind = f"({clause.binding})" if clause.binding else ""
                self._line(f"}} recover {typ}{bind} {{")
                self._push()
                self._decompile_block(clause.body)
                self._pop()
            if node.ensure:
                self._line("} ensure {")
                self._push()
                self._decompile_block(node.ensure)
                self._pop()
            self._line("}")
        elif isinstance(node, ThrowStmt):
            self._line(f"throw {self._expr(node.value)}")
        elif isinstance(node, EmitStmt):
            args = ", ".join(self._expr(a) for a in node.args)
            self._line(f"emit {node.event}({args})")
        elif isinstance(node, MeasureBlock):
            label = f' "{node.label}"' if node.label else ""
            self._line(f"measure{label} {{")
            self._push()
            self._decompile_block(node.body)
            self._pop()
            self._line("}")
        elif isinstance(node, StructDecl):
            for d in (node.decorators or []):
                self._line(f"@{d.name}")
            ifaces = f" : {', '.join(node.interfaces)}" if node.interfaces else ""
            pub = "pub " if node.is_pub else ""
            self._line(f"{pub}struct {node.name}{ifaces} {{")
            self._push()
            for f in node.fields:
                typ = f": {f.type_}" if f.type_ else ""
                default = f" = {self._expr(f.default)}" if f.default else ""
                self._line(f"{f.name}{typ}{default}")
            self._pop()
            self._line("}")
        elif isinstance(node, EnumDecl):
            self._line(f"enum {node.name} {{")
            self._push()
            for v in node.variants:
                if v.value:
                    self._line(f"{v.name} = {self._expr(v.value)}")
                else:
                    self._line(v.name)
            self._pop()
            self._line("}")
        elif isinstance(node, ImplBlock):
            iface = f" for {node.interface}" if node.interface else ""
            self._line(f"impl {node.type_name}{iface} {{")
            self._push()
            for m in node.methods:
                self._decompile_fn(m)
            self._pop()
            self._line("}")
        elif isinstance(node, InterfaceDecl):
            self._line(f"interface {node.name} {{")
            self._push()
            for m in node.methods:
                params = self._render_params(m.params)
                ret = f" -> {m.ret_type}" if m.ret_type else ""
                self._line(f"fn {m.name}({params}){ret}")
            self._pop()
            self._line("}")
        elif isinstance(node, TypeAlias):
            self._line(f"type {node.name} = {node.target}")
        elif isinstance(node, ExprStmt):
            self._line(self._expr(node.expr))
        elif isinstance(node, AssignStmt):
            self._line(f"{self._expr(node.target)} {node.op} {self._expr(node.value)}")
        elif isinstance(node, BlockStmt):
            self._decompile_block(node)
        elif isinstance(node, ForeignBlock):
            params = ", ".join(f"{p.name}: {self._expr(p.value)}" for p in node.params)
            self._line(f'foreign "{node.lang}" ({params}) {{')
            self._push()
            self._line(f'"{node.source}"')
            self._pop()
            self._line("}")
        else:
            self._line(f"// [decompiler: unhandled {type(node).__name__}]")

    def _decompile_fn(self, node: FnDecl):
        for d in (node.decorators or []):
            args = "(" + ", ".join(self._expr(a) for a in d.args) + ")" if d.args else ""
            self._line(f"@{d.name}{args}")
        params = self._render_params(node.params)
        ret = f" -> {node.ret_type}" if node.ret_type else ""
        kw = "async fn" if node.is_async else "fn"
        pub = "pub " if node.is_pub else ""
        self._line(f"{pub}{kw} {node.name}({params}){ret} {{")
        self._push()
        if node.body:
            self._decompile_block(node.body)
        self._pop()
        self._line("}")
        self._line("")

    def _decompile_block(self, block: BlockStmt):
        for s in block.stmts:
            self._decompile_stmt(s)

    def _render_params(self, params) -> str:
        parts = []
        for p in params:
            s = p.name
            if p.type_:
                s += f": {p.type_}"
            if p.default:
                s += f" = {self._expr(p.default)}"
            parts.append(s)
        return ", ".join(parts)

    # -- expressions -------------------------------------------------------

    def _expr(self, node) -> str:
        if node is None:
            return "nil"
        if isinstance(node, Literal):
            if node.kind == "nil": return "nil"
            if node.kind == "bool": return "true" if node.value else "false"
            if node.kind == "str": return repr(node.value)
            return str(node.value)
        if isinstance(node, Ident):
            return node.name
        if isinstance(node, BinOp):
            return f"{self._expr(node.left)} {node.op} {self._expr(node.right)}"
        if isinstance(node, UnaryOp):
            return f"{node.op}{self._expr(node.operand)}"
        if isinstance(node, CallExpr):
            args = ", ".join(self._expr(a) for a in node.args)
            kwargs = ", ".join(f"{k}: {self._expr(v)}" for k, v in node.kwargs)
            all_args = ", ".join(filter(None, [args, kwargs]))
            return f"{self._expr(node.callee)}({all_args})"
        if isinstance(node, IndexExpr):
            return f"{self._expr(node.obj)}[{self._expr(node.index)}]"
        if isinstance(node, FieldExpr):
            return f"{self._expr(node.obj)}.{node.field}"
        if isinstance(node, LambdaExpr):
            params = self._render_params(node.params)
            if node.body:
                return f"fn({params}) {self._expr(node.body)}"
            return f"fn({params}) {{ ... }}"
        if isinstance(node, ListExpr):
            return f"[{', '.join(self._expr(e) for e in node.elements)}]"
        if isinstance(node, MapExpr):
            pairs = ", ".join(f"{self._expr(k)}: {self._expr(v)}" for k, v in node.pairs)
            return "{" + pairs + "}"
        if isinstance(node, TupleExpr):
            return f"({', '.join(self._expr(e) for e in node.elements)})"
        if isinstance(node, RangeExpr):
            op = ".." if node.inclusive else "..<"
            return f"{self._expr(node.start)}{op}{self._expr(node.end)}"
        if isinstance(node, InterpolatedStr):
            parts = []
            for kind, val in node.parts:
                if kind == "str":
                    parts.append(val)
                else:
                    parts.append("{" + val + "}")
            return '"' + "".join(parts) + '"'
        if isinstance(node, SelfExpr):
            return "self"
        if isinstance(node, StructLiteral):
            fields = ", ".join(f"{k}: {self._expr(v)}" for k, v in node.fields)
            return f"{node.name} {{ {fields} }}"
        if isinstance(node, CastExpr):
            return f"{self._expr(node.value)} as {node.target}"
        if isinstance(node, ProbeExpr):
            return f"probe {self._expr(node.value)}"
        if isinstance(node, SpawnExpr):
            return f"spawn {self._expr(node.call)}"
        if isinstance(node, YieldExpr):
            val = f" {self._expr(node.value)}" if node.value else ""
            return f"yield{val}"
        return str(node)


# -----------------------------------------------------------------------------
# File I/O helpers
# -----------------------------------------------------------------------------

def compile_file_to_ltlc(ltl_path: str, output_path: Optional[str] = None) -> str:
    """Parse a .ltl file and compile it to .ltlc binary. Returns output path."""
    from .lexer import lex
    from .parser import parse

    source = Path(ltl_path).read_text(encoding="utf-8")
    program = parse(source, ltl_path)
    binary = compile_to_ltlc(program, ltl_path, program.module or "")

    out = output_path or str(Path(ltl_path).with_suffix(".ltlc"))
    Path(out).write_bytes(binary)
    return out


def decompile_ltlc_to_source(ltlc_path: str) -> str:
    """Read a .ltlc file and decompile to .ltl source code."""
    data = Path(ltlc_path).read_bytes()
    program, source_file, module_name = decompile_from_ltlc(data)
    return Decompiler().decompile(program)


def ltlc_info(ltlc_path: str) -> dict:
    """Read .ltlc header and return metadata."""
    data = Path(ltlc_path).read_bytes()
    header = LTLCHeader.unpack(data)

    pos = HEADER_SIZE
    src_len = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
    source_file = data[pos:pos+src_len].decode("utf-8"); pos += src_len
    mod_len = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
    module_name = data[pos:pos+mod_len].decode("utf-8")

    return {
        "format": f"LTLC v{header.version_major}.{header.version_minor}",
        "flags": header.flags,
        "timestamp": header.timestamp,
        "ast_size_compressed": header.ast_size,
        "checksum": f"{header.checksum:#010x}",
        "source_file": source_file,
        "module_name": module_name,
        "file_size": len(data),
    }
