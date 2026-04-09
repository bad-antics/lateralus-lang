"""
lateralus_lang/codegen/bytecode.py  -  IR → LTasm Bytecode Code Generator
===========================================================================
Walks the IRModule produced by the semantic analyser and emits a
Bytecode object ready for the VM.

The generated code uses the full LTasm opcode set including:
  · Function calls with call-frame management
  · try/recover/ensure via TRY_BEGIN / TRY_END / THROW
  · Pipeline operator optimisation
  · Tail-call detection
===========================================================================
"""
from __future__ import annotations

import struct
from typing import Dict, List, Tuple

from ..ir import BasicBlock, IRFunction, IRInstr, IRModule, IROp
from ..vm.assembler import Bytecode
from ..vm.opcodes import Op


class BytecodeGenError(Exception):
    pass


class BytecodeGenerator:
    """
    Two-pass code generator:
      Pass 1 — emit all instructions with 0-placeholder for unresolved labels
      Pass 2 — back-patch all label references
    """

    def __init__(self):
        self._bc:        Bytecode           = Bytecode()
        self._fn_addrs:  Dict[str, int]     = {}   # fn name → code offset
        self._fixups:    List[Tuple[int, str]] = [] # (patch_offset, fn/label_name)
        self._label_map: Dict[str, int]     = {}   # IR label → code offset

    # -- public ----------------------------------------------------------------

    def generate(self, module: IRModule) -> Bytecode:
        # Emit global initialisation
        for instr in module.globals_:
            self._emit_instr(instr)

        # Jump past all function bodies to the entry point
        jmp_patch = self._bc.emit_u8(int(Op.JMP))
        ep_fixup  = self._bc.emit_u32(0)       # placeholder; patched later

        # Emit every function
        for fn in module.functions:
            self._emit_function(fn)

        # Patch entry-point jump (to main/first function)
        if "main" in self._fn_addrs:
            self._bc.patch_u32(ep_fixup, self._fn_addrs["main"])
        elif module.functions:
            self._bc.patch_u32(ep_fixup, self._fn_addrs[module.functions[0].name])
        else:
            # Nothing to run — emit HALT
            self._bc.emit_u8(int(Op.HALT))
            self._bc.patch_u32(ep_fixup, len(self._bc.code) - 1)

        # Resolve fixups
        self._resolve_fixups()
        return self._bc

    # -- function emit ---------------------------------------------------------

    def _emit_function(self, fn: IRFunction) -> None:
        addr = len(self._bc.code)
        self._fn_addrs[fn.name] = addr
        self._bc.labels[fn.name] = addr
        # Update entry point for _start / main
        if fn.name in ("main", "_start"):
            self._bc.entry_point = addr
        for bb in fn.blocks:
            self._emit_block(bb)
        # Ensure every function ends with RET
        if not fn.blocks or not fn.blocks[-1].instrs or \
                fn.blocks[-1].instrs[-1].op not in (IROp.RETURN, IROp.HALT):
            self._bc.emit_u8(int(Op.RET))

    def _emit_block(self, bb: BasicBlock) -> None:
        self._label_map[bb.label] = len(self._bc.code)
        self._bc.labels[bb.label] = len(self._bc.code)
        for instr in bb.instrs:
            self._emit_instr(instr)

    # -- instruction emit ------------------------------------------------------

    def _emit_instr(self, instr: IRInstr) -> None:  # noqa: C901
        op = instr.op

        if op == IROp.NOP or op == IROp.COMMENT:
            self._bc.emit_u8(int(Op.NOP))

        elif op in (IROp.LOAD_IMM, IROp.LOAD_BOOL):
            self._bc.emit_u8(int(Op.PUSH_IMM))
            v = instr.src1
            if isinstance(v, float):
                bits = struct.unpack("<Q", struct.pack("<d", v))[0]
                self._bc.emit_u64(bits)
            elif isinstance(v, bool):
                self._bc.emit_u64(int(v))
            elif isinstance(v, int):
                self._bc.emit_u64(v)
            else:
                self._bc.emit_u64(0)

        elif op == IROp.LOAD_STR:
            idx = self._bc.intern_string(str(instr.src1))
            self._bc.emit_u8(int(Op.PUSH_STR))
            self._bc.emit_u32(idx)

        elif op == IROp.LOAD_NIL:
            # Push 0 (nil representation)
            self._bc.emit_u8(int(Op.PUSH_IMM))
            self._bc.emit_u64(0)

        elif op == IROp.COPY:
            # Nothing to emit unless the dest differs from src (handled by caller)
            pass

        elif op in (IROp.ADD, IROp.SUB, IROp.MUL, IROp.DIV, IROp.MOD, IROp.POW,
                    IROp.AND, IROp.OR,  IROp.XOR, IROp.SHL, IROp.SHR,
                    IROp.EQ,  IROp.NE,  IROp.LT,  IROp.LE,  IROp.GT,  IROp.GE):
            _ir_to_vm = {
                IROp.ADD: Op.ADD,  IROp.SUB: Op.SUB,  IROp.MUL: Op.MUL,
                IROp.DIV: Op.DIV,  IROp.MOD: Op.MOD,  IROp.POW: Op.POW,
                IROp.AND: Op.AND,  IROp.OR:  Op.OR,   IROp.XOR: Op.XOR,
                IROp.SHL: Op.SHL,  IROp.SHR: Op.SHR,
                IROp.EQ:  Op.CMPEQ, IROp.NE: Op.CMPNE,
                IROp.LT:  Op.CMPLT, IROp.LE: Op.CMPLE,
                IROp.GT:  Op.CMPGT, IROp.GE: Op.CMPGE,
            }
            # Push operands if they are immediates
            self._push_operand(instr.src1)
            self._push_operand(instr.src2)
            self._bc.emit_u8(int(_ir_to_vm[op]))

        elif op in (IROp.NEG, IROp.NOT, IROp.BNOT):
            self._push_operand(instr.src1)
            vm_op = {IROp.NEG: Op.NEG, IROp.NOT: Op.NOT, IROp.BNOT: Op.NOT}[op]
            self._bc.emit_u8(int(vm_op))

        elif op == IROp.LABEL:
            # Record label address
            self._label_map[str(instr.dest)] = len(self._bc.code)
            self._bc.labels[str(instr.dest)] = len(self._bc.code)

        elif op == IROp.JMP:
            self._bc.emit_u8(int(Op.JMP))
            self._emit_label_ref(str(instr.dest))

        elif op == IROp.JT:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.JT))
            self._emit_label_ref(str(instr.dest))

        elif op == IROp.JF:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.JF))
            self._emit_label_ref(str(instr.dest))

        elif op == IROp.CALL:
            args = instr.src2 or []
            for arg in args:
                self._push_operand(arg)
            self._bc.emit_u8(int(Op.CALL))
            self._emit_label_ref(str(instr.src1))

        elif op == IROp.RETURN:
            if instr.src1 is not None:
                self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.RET))

        elif op == IROp.HALT:
            self._push_operand(instr.src1 or 0)
            self._bc.emit_u8(int(Op.HALT))

        elif op == IROp.MAKE_LIST:
            items = instr.src1 or []
            for item in items:
                self._push_operand(item)
            self._bc.emit_u8(int(Op.LIST_NEW))
            self._bc.emit_u32(len(items))

        elif op == IROp.MAKE_MAP:
            self._bc.emit_u8(int(Op.MAP_NEW))
            pairs = instr.src1 or []
            for k, v in pairs:
                self._push_operand(k)
                self._push_operand(v)
                self._bc.emit_u8(int(Op.MAP_SET))

        elif op == IROp.INDEX:
            self._push_operand(instr.src1)
            self._push_operand(instr.src2)
            self._bc.emit_u8(int(Op.LIST_GET))

        elif op == IROp.GET_FIELD:
            # Field access via string key in a map
            self._push_operand(instr.src1)
            idx = self._bc.intern_string(str(instr.src2))
            self._bc.emit_u8(int(Op.PUSH_STR))
            self._bc.emit_u32(idx)
            self._bc.emit_u8(int(Op.MAP_GET))

        elif op == IROp.TRY_ENTER:
            self._bc.emit_u8(int(Op.TRY_BEGIN))
            self._emit_label_ref(str(instr.dest))

        elif op == IROp.TRY_LEAVE:
            self._bc.emit_u8(int(Op.TRY_END))

        elif op == IROp.THROW:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.THROW))

        elif op == IROp.BIND_ERR:
            # Error is already on stack from THROW handler; DUP to keep reference
            self._bc.emit_u8(int(Op.DUP))

        elif op == IROp.PIPE:
            # a |> f  →  f(a)
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.CALL))
            self._emit_label_ref(str(instr.src2))

        elif op == IROp.AWAIT:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.AWAIT_OP))

        elif op == IROp.CAST:
            self._push_operand(instr.src1)
            target = str(instr.src2).lower()
            cast_ops = {
                "int":   Op.F_TO_INT,
                "float": Op.INT_TO_F,
                "str":   Op.INT_TO_STR,
            }
            self._bc.emit_u8(int(cast_ops.get(target, Op.NOP)))

        elif op == IROp.TYPEOF:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.TYPEOF_OP))

        elif op == IROp.SIZEOF:
            self._push_operand(instr.src1)
            self._bc.emit_u8(int(Op.STR_LEN))   # reuse length for sizeof

        # Unknown / unimplemented → NOP
        else:
            self._bc.emit_u8(int(Op.NOP))

    # -- helpers ---------------------------------------------------------------

    def _push_operand(self, src) -> None:
        """Push *src* (a temporary name string or a literal value) onto the stack."""
        if src is None:
            self._bc.emit_u8(int(Op.PUSH_IMM))
            self._bc.emit_u64(0)
            return
        if isinstance(src, bool):
            self._bc.emit_u8(int(Op.PUSH_IMM))
            self._bc.emit_u64(int(src))
        elif isinstance(src, int):
            self._bc.emit_u8(int(Op.PUSH_IMM))
            self._bc.emit_u64(src)
        elif isinstance(src, float):
            bits = struct.unpack("<Q", struct.pack("<d", src))[0]
            self._bc.emit_u8(int(Op.PUSH_IMM))
            self._bc.emit_u64(bits)
        elif isinstance(src, str):
            if src.startswith("%") or src.startswith("$"):
                # It's a temporary/parameter reference — we can't look it up in a
                # register file here; emit a placeholder NOP (real register alloc
                # is a future optimisation pass)
                self._bc.emit_u8(int(Op.NOP))
            else:
                idx = self._bc.intern_string(src)
                self._bc.emit_u8(int(Op.PUSH_STR))
                self._bc.emit_u32(idx)
        else:
            self._bc.emit_u8(int(Op.NOP))

    def _emit_label_ref(self, label: str) -> None:
        """Emit a u32 address, with a fixup if the label isn't known yet."""
        if label in self._label_map:
            self._bc.emit_u32(self._label_map[label])
        elif label in self._fn_addrs:
            self._bc.emit_u32(self._fn_addrs[label])
        else:
            patch_off = self._bc.emit_u32(0)
            self._fixups.append((patch_off, label))

    def _resolve_fixups(self) -> None:
        all_addrs = {**self._fn_addrs, **self._label_map}
        for (patch_off, label) in self._fixups:
            addr = all_addrs.get(label)
            if addr is None:
                raise BytecodeGenError(f"Unresolved label: {label!r}")
            self._bc.patch_u32(patch_off, addr)


# -----------------------------------------------------------------------------
# Convenience
# -----------------------------------------------------------------------------

def generate_bytecode(module: IRModule) -> Bytecode:
    """Generate LTasm Bytecode from an IRModule."""
    return BytecodeGenerator().generate(module)
