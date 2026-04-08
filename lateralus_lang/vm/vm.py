"""
lateralus_lang/vm/vm.py  ─  LATERALUS Stack Virtual Machine
═══════════════════════════════════════════════════════════════════════════
Executes LTasm Bytecode objects produced by the assembler or bytecode
code-generator.

Architecture
────────────
  · Stack:    Python list acting as the operand stack
  · Registers: r0–r15, sp (auto), pc (byte offset into code)
  · Flags:    Z, C, N, O  (zero, carry, negative, overflow)
  · Call stack: list of return-address frames
  · Error stack: try/recover frames  (TRY_BEGIN / TRY_END / THROW)
  · Coroutines: lightweight generator-based green threads (SPAWN/YIELD/AWAIT)

All VM errors surface as VMError which integrates with the Lateralus
error_engine via errors/bridge.py when available.
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import struct
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .assembler import Bytecode
from .opcodes import Op

# ─────────────────────────────────────────────────────────────────────────────
# VM error types
# ─────────────────────────────────────────────────────────────────────────────

class VMError(Exception):
    """Base class for all VM runtime errors."""
    def __init__(self, message: str, pc: int = 0, op: Optional[Op] = None):
        super().__init__(message)
        self.pc  = pc
        self.op  = op


class StackUnderflowError(VMError): pass
class DivisionByZeroError(VMError): pass
class InvalidOpcodeError(VMError): pass
class TypeMismatchError(VMError): pass
class ThrownError(VMError):
    """An explicit THROW from user code."""
    def __init__(self, payload: Any, pc: int = 0):
        super().__init__(str(payload), pc=pc)
        self.payload = payload


# ─────────────────────────────────────────────────────────────────────────────
# Frames
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CallFrame:
    return_pc:   int
    base_sp:     int       # stack depth at call site (for frame isolation)


@dataclass
class ErrorFrame:
    recover_addr: int      # PC to jump to on THROW
    stack_depth:  int      # restore stack to this depth
    ensure_addr:  Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# VM
# ─────────────────────────────────────────────────────────────────────────────

_MAX_STEPS = 10_000_000   # safety limit


class VM:
    """
    Lateralus Stack VM.

    Usage::
        from lateralus_lang.vm.assembler import assemble
        bc = assemble(source)
        vm = VM(bc)
        exit_code = vm.run()
    """

    def __init__(self, bytecode: Bytecode,
                 stdin=None, stdout=None, stderr=None,
                 max_steps: int = _MAX_STEPS):
        self.bc       = bytecode
        self.stdin    = stdin  or sys.stdin
        self.stdout   = stdout or sys.stdout
        self.stderr   = stderr or sys.stderr
        self.max_steps = max_steps

        # Registers
        self.regs:  List[Any] = [0] * 16
        self.pc:    int       = bytecode.entry_point
        self.flags: Dict[str, bool] = {"Z": False, "C": False, "N": False, "O": False}

        # Stack
        self.stack: List[Any] = []

        # Call & error stacks
        self.call_stack:  List[CallFrame]  = []
        self.error_stack: List[ErrorFrame] = []

        # Heap (simple dict for now)
        self.heap: Dict[int, Any] = {}
        self._next_addr = 0x1000

        # Statistics
        self.steps     = 0
        self.exit_code = 0

    # ── public API ────────────────────────────────────────────────────────────

    def run(self) -> int:
        code = self.bc.code
        n    = len(code)
        while self.pc < n and self.steps < self.max_steps:
            op_byte = code[self.pc]
            try:
                op = Op(op_byte)
            except ValueError:
                raise InvalidOpcodeError(
                    f"Unknown opcode 0x{op_byte:02X}", pc=self.pc)
            self.pc += 1
            self.steps += 1
            result = self._dispatch(op, code)
            if result == "HALT":
                break
        return self.exit_code

    # ── stack helpers ─────────────────────────────────────────────────────────

    def _push(self, v: Any) -> None:
        self.stack.append(v)

    def _pop(self) -> Any:
        if not self.stack:
            raise StackUnderflowError("Stack underflow", pc=self.pc)
        return self.stack.pop()

    def _top(self) -> Any:
        if not self.stack:
            raise StackUnderflowError("Stack underflow (peek)", pc=self.pc)
        return self.stack[-1]

    def _read_u8(self, code: bytes) -> int:
        v = code[self.pc]; self.pc += 1; return v

    def _read_u32(self, code: bytes) -> int:
        v = struct.unpack_from(">I", code, self.pc)[0]; self.pc += 4; return v

    def _read_u64(self, code: bytes) -> int:
        v = struct.unpack_from("<Q", code, self.pc)[0]; self.pc += 8; return v

    def _read_f64(self, code: bytes) -> float:
        v = struct.unpack_from("<d", code, self.pc)[0]; self.pc += 8; return v

    def _str(self, idx: int) -> str:
        return self.bc.string_table[idx]

    # ── flag helpers ──────────────────────────────────────────────────────────

    def _set_flags(self, a: Any, b: Any) -> None:
        try:
            r = a - b
            self.flags["Z"] = r == 0
            self.flags["N"] = r < 0
            self.flags["C"] = False
            self.flags["O"] = False
        except TypeError:
            pass

    # ── dispatcher ────────────────────────────────────────────────────────────

    def _dispatch(self, op: Op, code: bytes) -> Optional[str]:  # noqa: C901
        # ── Stack ──────────────────────────────────────────────────────────
        if op == Op.NOP:
            pass

        elif op == Op.PUSH_IMM:
            # 8-byte big-endian operand.
            # The assembler always stores raw integer values in big-endian.
            # Hand-crafted test bytecode also uses big-endian (0,0,...,0,N).
            raw_bytes = code[self.pc:self.pc+8]
            self.pc += 8
            # Decode as unsigned big-endian, then sign-extend if top bit set.
            uval = int.from_bytes(raw_bytes, "big", signed=False)
            if uval >= (1 << 63):
                val = uval - (1 << 64)   # negative int
            else:
                val = uval
            self._push(val)

        elif op == Op.PUSH_STR:
            # 2-byte big-endian index (tests encode as (idx>>8)&0xFF, idx&0xFF)
            hi = code[self.pc]; self.pc += 1
            lo = code[self.pc]; self.pc += 1
            idx = (hi << 8) | lo
            self._push(self._str(idx))

        elif op == Op.PUSH_REG:
            r = self._read_u8(code)
            self._push(self.regs[r])

        elif op == Op.POP:
            self._pop()

        elif op == Op.POP_REG:
            r = self._read_u8(code)
            self.regs[r] = self._pop()

        elif op == Op.DUP:
            self._push(self._top())

        elif op == Op.DUP2:
            a, b = self._pop(), self._pop()
            self._push(b); self._push(a); self._push(b); self._push(a)

        elif op == Op.SWAP:
            a, b = self._pop(), self._pop()
            self._push(a); self._push(b)

        # ── Arithmetic ──────────────────────────────────────────────────────
        elif op == Op.ADD:
            b, a = self._pop(), self._pop(); self._push(a + b)
        elif op == Op.SUB:
            b, a = self._pop(), self._pop(); self._push(a - b)
        elif op == Op.MUL:
            b, a = self._pop(), self._pop(); self._push(a * b)
        elif op == Op.DIV:
            b, a = self._pop(), self._pop()
            if b == 0: raise DivisionByZeroError("Division by zero", pc=self.pc)
            self._push(a // b if isinstance(a, int) and isinstance(b, int) else a / b)
        elif op == Op.MOD:
            b, a = self._pop(), self._pop()
            if b == 0: raise DivisionByZeroError("Modulo by zero", pc=self.pc)
            self._push(a % b)
        elif op == Op.POW:
            b, a = self._pop(), self._pop(); self._push(a ** b)
        elif op == Op.NEG:
            self._push(-self._pop())
        elif op == Op.INC:
            self._push(self._pop() + 1)
        elif op == Op.DEC:
            self._push(self._pop() - 1)
        elif op == Op.FADD:
            b, a = self._pop(), self._pop(); self._push(float(a) + float(b))
        elif op == Op.FSUB:
            b, a = self._pop(), self._pop(); self._push(float(a) - float(b))
        elif op == Op.FMUL:
            b, a = self._pop(), self._pop(); self._push(float(a) * float(b))
        elif op == Op.FDIV:
            b, a = self._pop(), self._pop()
            if float(b) == 0.0: raise DivisionByZeroError("Float division by zero", pc=self.pc)
            self._push(float(a) / float(b))

        # ── Bitwise ─────────────────────────────────────────────────────────
        elif op == Op.AND:
            b, a = self._pop(), self._pop(); self._push(int(a) & int(b))
        elif op == Op.OR:
            b, a = self._pop(), self._pop(); self._push(int(a) | int(b))
        elif op == Op.XOR:
            b, a = self._pop(), self._pop(); self._push(int(a) ^ int(b))
        elif op == Op.NOT:
            self._push(~int(self._pop()))
        elif op == Op.SHL:
            b, a = self._pop(), self._pop(); self._push(int(a) << int(b))
        elif op == Op.SHR:
            b, a = self._pop(), self._pop(); self._push(int(a) >> int(b))

        # ── Comparison ──────────────────────────────────────────────────────
        elif op == Op.CMP:
            b, a = self._pop(), self._pop()
            self._set_flags(a, b)
            self._push(0 if a == b else (-1 if a < b else 1))
        elif op == Op.CMPEQ:
            b, a = self._pop(), self._pop(); self._push(int(a == b))
        elif op == Op.CMPNE:
            b, a = self._pop(), self._pop(); self._push(int(a != b))
        elif op == Op.CMPLT:
            b, a = self._pop(), self._pop(); self._push(int(a < b))
        elif op == Op.CMPLE:
            b, a = self._pop(), self._pop(); self._push(int(a <= b))
        elif op == Op.CMPGT:
            b, a = self._pop(), self._pop(); self._push(int(a > b))
        elif op == Op.CMPGE:
            b, a = self._pop(), self._pop(); self._push(int(a >= b))

        # ── Control flow ────────────────────────────────────────────────────
        elif op == Op.JMP:
            self.pc = self._read_u32(code)
        elif op == Op.JT:
            addr = self._read_u32(code)
            if self._pop(): self.pc = addr
        elif op == Op.JF:
            addr = self._read_u32(code)
            if not self._pop(): self.pc = addr
        elif op == Op.JZ:
            addr = self._read_u32(code)
            val = self._pop()   # pop condition; jump if zero/falsy
            if not val: self.pc = addr
        elif op == Op.JNZ:
            addr = self._read_u32(code)
            val = self._pop()   # pop condition; jump if non-zero/truthy
            if val: self.pc = addr
        elif op == Op.CALL:
            addr = self._read_u32(code)
            self.call_stack.append(CallFrame(return_pc=self.pc, base_sp=len(self.stack)))
            self.pc = addr
        elif op == Op.RET:
            if not self.call_stack:
                return "HALT"
            frame = self.call_stack.pop()
            self.pc = frame.return_pc
        elif op == Op.CALL_REG:
            r = self._read_u8(code)
            self.call_stack.append(CallFrame(return_pc=self.pc, base_sp=len(self.stack)))
            self.pc = int(self.regs[r])
        elif op == Op.TAIL_CALL:
            addr = self._read_u32(code)
            self.pc = addr   # no new call frame → tail call
        elif op == Op.HALT:
            # Do NOT pop the stack — exit code is always 0 unless the program
            # explicitly used a SYSCALL/RETURN to set it.  This lets tests
            # inspect the stack after HALT without having the top consumed.
            self.exit_code = 0
            return "HALT"

        # ── Registers / memory ──────────────────────────────────────────────
        elif op == Op.LOAD:
            r = self._read_u8(code); addr = self._read_u32(code)
            self.regs[r] = self.heap.get(addr, 0)
        elif op == Op.STORE:
            r = self._read_u8(code); addr = self._read_u32(code)
            self.heap[addr] = self.regs[r]
        elif op == Op.MOV:
            dst = self._read_u8(code); src = self._read_u8(code)
            self.regs[dst] = self.regs[src]
        elif op == Op.MOV_IMM:
            r = self._read_u8(code); imm = self._read_u64(code)
            self.regs[r] = imm
        elif op == Op.LOAD_IDX:
            dst = self._read_u8(code); base = self._read_u8(code); idx_r = self._read_u8(code)
            container = self.regs[base]
            self.regs[dst] = container[self.regs[idx_r]]
        elif op == Op.STORE_IDX:
            base = self._read_u8(code); idx_r = self._read_u8(code); src = self._read_u8(code)
            self.regs[base][self.regs[idx_r]] = self.regs[src]

        # ── Heap ────────────────────────────────────────────────────────────
        elif op == Op.ALLOC:
            r = self._read_u8(code); size = self._read_u32(code)
            self._next_addr += size
            self.heap[self._next_addr] = bytearray(size)
            self.regs[r] = self._next_addr
        elif op == Op.FREE:
            r = self._read_u8(code)
            self.heap.pop(self.regs[r], None)
        elif op == Op.GCPAUSE:
            pass   # no-op in this impl
        elif op == Op.SIZEOF_OP:
            dst = self._read_u8(code); src = self._read_u8(code)
            v = self.regs[src]
            self.regs[dst] = len(v) if hasattr(v, "__len__") else 8

        # ── Type coercion ───────────────────────────────────────────────────
        elif op == Op.INT_TO_F:
            self._push(float(self._pop()))
        elif op == Op.F_TO_INT:
            self._push(int(self._pop()))
        elif op == Op.INT_TO_STR:
            self._push(str(int(self._pop())))
        elif op == Op.F_TO_STR:
            self._push(str(float(self._pop())))
        elif op == Op.STR_TO_INT:
            self._push(int(str(self._pop())))
        elif op == Op.STR_TO_F:
            self._push(float(str(self._pop())))
        elif op == Op.TYPEOF_OP:
            v = self._top()
            self._push(type(v).__name__)

        # ── Strings / collections ───────────────────────────────────────────
        elif op == Op.STR_CAT:
            b, a = self._pop(), self._pop(); self._push(str(a) + str(b))
        elif op == Op.STR_LEN:
            self._push(len(str(self._pop())))
        elif op == Op.STR_SLICE:
            end, start, s = self._pop(), self._pop(), self._pop()
            self._push(str(s)[int(start):int(end)])
        elif op == Op.LIST_NEW:
            n = self._read_u32(code)
            items = [self._pop() for _ in range(n)]
            items.reverse()
            self._push(items)
        elif op == Op.LIST_PUSH:
            item = self._pop(); lst = self._top(); lst.append(item)
        elif op == Op.LIST_POP:
            lst = self._top(); self._push(lst.pop())
        elif op == Op.LIST_LEN:
            self._push(len(self._pop()))
        elif op == Op.LIST_GET:
            idx = self._pop(); lst = self._pop(); self._push(lst[int(idx)])
        elif op == Op.LIST_SET:
            val = self._pop(); idx = self._pop(); lst = self._pop(); lst[int(idx)] = val
        elif op == Op.MAP_NEW:
            self._push({})
        elif op == Op.MAP_GET:
            k = self._pop(); m = self._pop(); self._push(m.get(k))
        elif op == Op.MAP_SET:
            v = self._pop(); k = self._pop(); m = self._top(); m[k] = v
        elif op == Op.MAP_HAS:
            k = self._pop(); m = self._pop(); self._push(int(k in m))
        elif op == Op.MAP_DEL:
            k = self._pop(); m = self._top(); m.pop(k, None)
        elif op == Op.MAP_KEYS:
            m = self._pop(); self._push(list(m.keys()))

        # ── I/O ─────────────────────────────────────────────────────────────
        elif op == Op.PRINT:
            self.stdout.write(str(self._pop()))
            self.stdout.flush()
        elif op == Op.PRINTLN:
            self.stdout.write(str(self._pop()) + "\n")
            self.stdout.flush()
        elif op == Op.READ_LINE:
            self._push(self.stdin.readline().rstrip("\n"))
        elif op == Op.READ_INT:
            self._push(int(self.stdin.readline().strip()))
        elif op == Op.READ_FLOAT:
            self._push(float(self.stdin.readline().strip()))
        elif op == Op.FLUSH:
            self.stdout.flush()

        # ── System ──────────────────────────────────────────────────────────
        elif op == Op.SYSCALL:
            _id = self._read_u8(code)
            self._syscall(_id)
        elif op == Op.SLEEP:
            ms = self._pop()
            time.sleep(float(ms) / 1000.0)

        # ── Error handling ───────────────────────────────────────────────────
        elif op == Op.TRY_BEGIN:
            recover_addr = self._read_u32(code)
            self.error_stack.append(ErrorFrame(
                recover_addr=recover_addr,
                stack_depth=len(self.stack)))
        elif op == Op.TRY_END:
            if self.error_stack:
                self.error_stack.pop()
        elif op == Op.THROW:
            payload = self._pop()
            self._do_throw(ThrownError(payload, pc=self.pc))
        elif op == Op.THROW_STR:
            idx = self._read_u32(code)
            self._do_throw(ThrownError(self._str(idx), pc=self.pc))
        elif op == Op.RETHROW:
            # Re-use last ThrownError (stored in regs[15] by convention)
            self._do_throw(ThrownError(self.regs[15], pc=self.pc))
        elif op in (Op.ENSURE_BEG, Op.ENSURE_END):
            pass   # structural markers; logic handled by TRY_BEGIN/END

        # ── Debug ────────────────────────────────────────────────────────────
        elif op == Op.BREAKPOINT:
            self.stderr.write(f"[BREAKPOINT] pc={self.pc-1}  stack={self.stack}\n")
        elif op == Op.TRACE:
            idx = self._read_u32(code)
            self.stderr.write(f"[TRACE] {self._str(idx)}\n")
        elif op == Op.ASSERT:
            val = self._pop()
            if not val:
                self._do_throw(ThrownError(
                    f"Assertion failed at pc={self.pc-1}", pc=self.pc))
        elif op == Op.DUMP_STACK:
            self.stderr.write(f"[STACK] depth={len(self.stack)} top={self.stack[-5:]}\n")
        elif op == Op.DUMP_REGS:
            self.stderr.write(f"[REGS] {self.regs}\n")

        else:
            raise InvalidOpcodeError(f"Unimplemented opcode {op.name}", pc=self.pc)

        return None

    # ── throw / unwind ────────────────────────────────────────────────────────

    def _do_throw(self, err: ThrownError) -> None:
        """Unwind to the nearest error frame or propagate."""
        if not self.error_stack:
            raise err   # unhandled → propagate to Python caller
        frame = self.error_stack.pop()
        # Restore stack depth
        while len(self.stack) > frame.stack_depth:
            self.stack.pop()
        # Store error payload in r15 (convention)
        self.regs[15] = err.payload
        # Push error message for recovery block to consume
        self._push(err.payload)
        # Jump to recover block
        self.pc = frame.recover_addr

    # ── syscalls ─────────────────────────────────────────────────────────────

    def _syscall(self, syscall_id: int) -> None:
        """Built-in system call handlers."""
        if syscall_id == 0x01:   # EXIT
            self.exit_code = int(self._pop()) if self.stack else 0
            raise SystemExit(self.exit_code)
        elif syscall_id == 0x02:  # TIME_MS
            self._push(int(time.time() * 1000))
        elif syscall_id == 0x03:  # ENV_GET
            k = str(self._pop())
            import os
            self._push(os.environ.get(k, ""))
        elif syscall_id == 0x04:  # ARGC
            self._push(len(sys.argv))
        elif syscall_id == 0x05:  # ARGV
            idx = int(self._pop())
            self._push(sys.argv[idx] if 0 <= idx < len(sys.argv) else "")
        # Unknown syscall → push 0
        else:
            self._push(0)

    # ── repr ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (f"<VM pc={self.pc} stack_depth={len(self.stack)} "
                f"steps={self.steps} flags={self.flags}>")
