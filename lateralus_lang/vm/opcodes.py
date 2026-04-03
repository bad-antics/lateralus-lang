"""
lateralus_lang/vm/opcodes.py  ─  LATERALUS Assembly Opcode Definitions
═══════════════════════════════════════════════════════════════════════════
The Lateralus Assembly Language (.ltasm) targets the LTasm virtual machine
— a register-assisted, stack-based bytecode VM.

Register file
─────────────
  r0–r15   general-purpose (64-bit)
  sp       stack pointer        (auto-managed)
  pc       program counter      (auto-managed)
  flags    condition flags: Z (zero) C (carry) N (negative) O (overflow)

Instruction encoding (variable width, little-endian)
──────────────────────────────────────────────────────
  [1 byte opcode][optional operand bytes]

Operand encoding helpers
  - imm8 / imm16 / imm32 / imm64
  - reg  (1 byte: 0–15)
  - mem  (4 bytes: absolute address in data segment)
  - str  (4 bytes: index into string table)
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from enum import IntEnum


class Op(IntEnum):
    # ── Stack manipulation ────────────────────────────────────────────────────
    NOP        = 0x00   # no-op
    PUSH_IMM   = 0x01   # PUSH  <imm64>   — push literal int/float
    PUSH_STR   = 0x02   # PUSH  <str_idx> — push string from string table
    PUSH_REG   = 0x03   # PUSH  r<n>      — push register value
    POP        = 0x04   # POP             — discard top
    POP_REG    = 0x05   # POP   r<n>      — pop into register
    DUP        = 0x06   # DUP             — duplicate top
    DUP2       = 0x07   # DUP2            — duplicate top two
    SWAP       = 0x08   # SWAP            — swap top two

    # ── Arithmetic ────────────────────────────────────────────────────────────
    ADD        = 0x10   # pop b, pop a → push a+b
    SUB        = 0x11   # pop b, pop a → push a-b
    MUL        = 0x12   # pop b, pop a → push a*b
    DIV        = 0x13   # pop b, pop a → push a/b  (int or float)
    MOD        = 0x14   # pop b, pop a → push a%b
    POW        = 0x15   # pop b, pop a → push a**b
    NEG        = 0x16   # pop a         → push -a
    INC        = 0x17   # pop a         → push a+1
    DEC        = 0x18   # pop a         → push a-1
    FADD       = 0x19   # float add
    FSUB       = 0x1A   # float sub
    FMUL       = 0x1B   # float mul
    FDIV       = 0x1C   # float div

    # ── Bitwise ───────────────────────────────────────────────────────────────
    AND        = 0x20
    OR         = 0x21
    XOR        = 0x22
    NOT        = 0x23
    SHL        = 0x24   # shift left  (pop count, pop value)
    SHR        = 0x25   # shift right

    # ── Comparison ────────────────────────────────────────────────────────────
    CMP        = 0x30   # pop b, pop a → sets flags, pushes 0/1
    CMPEQ      = 0x31   # push (a == b)
    CMPNE      = 0x32   # push (a != b)
    CMPLT      = 0x33   # push (a <  b)
    CMPLE      = 0x34   # push (a <= b)
    CMPGT      = 0x35   # push (a >  b)
    CMPGE      = 0x36   # push (a >= b)

    # ── Control flow ──────────────────────────────────────────────────────────
    JMP        = 0x40   # JMP  <addr32>   — unconditional
    JT         = 0x41   # JT   <addr32>   — jump if top truthy (pop)
    JF         = 0x42   # JF   <addr32>   — jump if top falsy  (pop)
    JZ         = 0x43   # JZ   <addr32>   — jump if Z flag set
    JNZ        = 0x44   # JNZ  <addr32>
    CALL       = 0x45   # CALL <addr32>   — push pc+5, jump to addr
    RET        = 0x46   # RET             — pop return address → pc
    CALL_REG   = 0x47   # CALL_REG r<n>   — call address in register
    TAIL_CALL  = 0x48   # TAIL_CALL <addr32> — tail-call optimised
    HALT       = 0x49   # stop execution, top of stack = exit value

    # ── Memory / registers ────────────────────────────────────────────────────
    LOAD       = 0x50   # LOAD  r<n>, <addr32> — memory → register
    STORE      = 0x51   # STORE r<n>, <addr32> — register → memory
    LOAD_IDX   = 0x52   # LOAD_IDX r<dst>, r<base>, r<idx>
    STORE_IDX  = 0x53   # STORE_IDX r<base>, r<idx>, r<src>
    MOV        = 0x54   # MOV   r<dst>, r<src>
    MOV_IMM    = 0x55   # MOV   r<dst>, <imm64>
    LEA        = 0x56   # LEA   r<dst>, <label>  — load effective address

    # ── Heap / GC ─────────────────────────────────────────────────────────────
    ALLOC      = 0x60   # ALLOC r<dst>, <size_imm> — heap allocation
    FREE       = 0x61   # FREE  r<src>
    GCPAUSE    = 0x62   # hint the GC to run
    SIZEOF_OP  = 0x63   # SIZEOF_OP r<dst>, r<src>  — runtime size of object

    # ── Type coercion ─────────────────────────────────────────────────────────
    INT_TO_F   = 0x70   # int → float
    F_TO_INT   = 0x71   # float → int (truncate)
    INT_TO_STR = 0x72
    F_TO_STR   = 0x73
    STR_TO_INT = 0x74
    STR_TO_F   = 0x75
    TYPEOF_OP  = 0x76   # push type string of top

    # ── String / collection ops ───────────────────────────────────────────────
    STR_CAT    = 0x80   # concatenate two strings
    STR_LEN    = 0x81   # push length of string
    STR_SLICE  = 0x82   # STR_SLICE (str, start, end) → str
    LIST_NEW   = 0x83   # LIST_NEW <count> — pop count items → new list
    LIST_PUSH  = 0x84
    LIST_POP   = 0x85
    LIST_LEN   = 0x86
    LIST_GET   = 0x87   # pop index, pop list → push item
    LIST_SET   = 0x88   # pop value, pop index, pop list
    MAP_NEW    = 0x89
    MAP_GET    = 0x8A
    MAP_SET    = 0x8B
    MAP_HAS    = 0x8C
    MAP_DEL    = 0x8D
    MAP_KEYS   = 0x8E

    # ── I/O ───────────────────────────────────────────────────────────────────
    PRINT      = 0x90   # print top (no newline)
    PRINTLN    = 0x91   # print top + newline
    READ_LINE  = 0x92   # push input line
    READ_INT   = 0x93
    READ_FLOAT = 0x94
    FLUSH      = 0x95

    # ── System / FFI ──────────────────────────────────────────────────────────
    SYSCALL    = 0xA0   # SYSCALL <syscall_id_imm8> — host system call
    FOREIGN    = 0xA1   # FOREIGN <func_name_str_idx> — call native via FFI
    SPAWN      = 0xA2   # spawn lightweight coroutine, push coroutine handle
    AWAIT_OP   = 0xA3   # await coroutine handle on top
    YIELD      = 0xA4   # yield from current coroutine
    SLEEP      = 0xA5   # SLEEP (ms on stack)

    # ── Error handling ────────────────────────────────────────────────────────
    TRY_BEGIN  = 0xB0   # TRY_BEGIN <recover_addr32> — push error frame
    TRY_END    = 0xB1   # pop error frame (normal exit)
    THROW      = 0xB2   # THROW — pop error object, unwind stack
    THROW_STR  = 0xB3   # THROW_STR <str_idx> — throw string error
    ENSURE_BEG = 0xB4   # mark ensure block start
    ENSURE_END = 0xB5   # mark ensure block end
    RETHROW    = 0xB6   # re-throw current error

    # ── Debug ─────────────────────────────────────────────────────────────────
    BREAKPOINT = 0xF0   # debugger breakpoint
    TRACE      = 0xF1   # TRACE <str_idx> — emit trace message
    ASSERT     = 0xF2   # ASSERT — pop bool, throw if false
    DUMP_STACK = 0xF3   # print VM stack (debug)
    DUMP_REGS  = 0xF4   # print registers

    # ── Short aliases (test-friendly names) ───────────────────────────────────
    EQ        = 0x31   # alias for CMPEQ
    NE        = 0x32   # alias for CMPNE
    LT        = 0x33   # alias for CMPLT
    LE        = 0x34   # alias for CMPLE
    GT        = 0x35   # alias for CMPGT
    GE        = 0x36   # alias for CMPGE
    LOAD_REG  = 0x03   # alias for PUSH_REG  (push register value onto stack)
    STORE_REG = 0x05   # alias for POP_REG   (pop top into register)


# ─────────────────────────────────────────────────────────────────────────────
# Opcode metadata (name, operand schema, description)
# ─────────────────────────────────────────────────────────────────────────────

_NONE  = ()          # no operands
_IMM64 = ("imm64",)
_IMM32 = ("imm32",)
_IMM8  = ("imm8",)
_REG   = ("reg",)
_STR   = ("str_idx",)
_R_A32 = ("reg", "addr32")
_R_R   = ("reg", "reg")
_R_R_R = ("reg", "reg", "reg")
_R_I64 = ("reg", "imm64")

OPCODE_META: dict[Op, tuple] = {
    Op.NOP:        (_NONE,  "No operation"),
    Op.PUSH_IMM:   (_IMM64, "Push 64-bit immediate onto stack"),
    Op.PUSH_STR:   (_STR,   "Push string from string table"),
    Op.PUSH_REG:   (_REG,   "Push register value onto stack"),
    Op.POP:        (_NONE,  "Discard top of stack"),
    Op.POP_REG:    (_REG,   "Pop stack top into register"),
    Op.DUP:        (_NONE,  "Duplicate stack top"),
    Op.DUP2:       (_NONE,  "Duplicate top two stack items"),
    Op.SWAP:       (_NONE,  "Swap top two stack items"),
    Op.ADD:        (_NONE,  "Integer add"),
    Op.SUB:        (_NONE,  "Integer subtract"),
    Op.MUL:        (_NONE,  "Integer multiply"),
    Op.DIV:        (_NONE,  "Integer divide"),
    Op.MOD:        (_NONE,  "Integer modulo"),
    Op.POW:        (_NONE,  "Power (a**b)"),
    Op.NEG:        (_NONE,  "Negate top"),
    Op.INC:        (_NONE,  "Increment top"),
    Op.DEC:        (_NONE,  "Decrement top"),
    Op.FADD:       (_NONE,  "Float add"),
    Op.FSUB:       (_NONE,  "Float sub"),
    Op.FMUL:       (_NONE,  "Float mul"),
    Op.FDIV:       (_NONE,  "Float div"),
    Op.AND:        (_NONE,  "Bitwise AND"),
    Op.OR:         (_NONE,  "Bitwise OR"),
    Op.XOR:        (_NONE,  "Bitwise XOR"),
    Op.NOT:        (_NONE,  "Bitwise NOT"),
    Op.SHL:        (_NONE,  "Shift left"),
    Op.SHR:        (_NONE,  "Shift right"),
    Op.CMP:        (_NONE,  "Compare and set flags"),
    Op.CMPEQ:      (_NONE,  "Push (a == b)"),
    Op.CMPNE:      (_NONE,  "Push (a != b)"),
    Op.CMPLT:      (_NONE,  "Push (a < b)"),
    Op.CMPLE:      (_NONE,  "Push (a <= b)"),
    Op.CMPGT:      (_NONE,  "Push (a > b)"),
    Op.CMPGE:      (_NONE,  "Push (a >= b)"),
    Op.JMP:        (_IMM32, "Unconditional jump"),
    Op.JT:         (_IMM32, "Jump if truthy"),
    Op.JF:         (_IMM32, "Jump if falsy"),
    Op.JZ:         (_IMM32, "Jump if Z flag"),
    Op.JNZ:        (_IMM32, "Jump if not Z flag"),
    Op.CALL:       (_IMM32, "Call function at address"),
    Op.RET:        (_NONE,  "Return from function"),
    Op.CALL_REG:   (_REG,   "Call address in register"),
    Op.TAIL_CALL:  (_IMM32, "Tail-call optimised call"),
    Op.HALT:       (_NONE,  "Halt execution"),
    Op.LOAD:       (_R_A32, "Load from memory into register"),
    Op.STORE:      (_R_A32, "Store register to memory"),
    Op.LOAD_IDX:   (_R_R_R, "Load indexed"),
    Op.STORE_IDX:  (_R_R_R, "Store indexed"),
    Op.MOV:        (_R_R,   "Move register to register"),
    Op.MOV_IMM:    (_R_I64, "Load immediate into register"),
    Op.LEA:        (_R_A32, "Load effective address"),
    Op.ALLOC:      (("reg", "imm32"), "Heap allocate N bytes"),
    Op.FREE:       (_REG,   "Free heap object"),
    Op.GCPAUSE:    (_NONE,  "GC hint"),
    Op.SIZEOF_OP:  (_R_R,   "Size of object"),
    Op.INT_TO_F:   (_NONE,  "Convert int to float"),
    Op.F_TO_INT:   (_NONE,  "Convert float to int"),
    Op.INT_TO_STR: (_NONE,  "Convert int to string"),
    Op.F_TO_STR:   (_NONE,  "Convert float to string"),
    Op.STR_TO_INT: (_NONE,  "Convert string to int"),
    Op.STR_TO_F:   (_NONE,  "Convert string to float"),
    Op.TYPEOF_OP:  (_NONE,  "Push type string of top"),
    Op.STR_CAT:    (_NONE,  "Concatenate strings"),
    Op.STR_LEN:    (_NONE,  "Push string length"),
    Op.STR_SLICE:  (_NONE,  "Slice string"),
    Op.LIST_NEW:   (_IMM32, "New list from N stack items"),
    Op.LIST_PUSH:  (_NONE,  "Append to list"),
    Op.LIST_POP:   (_NONE,  "Pop from list"),
    Op.LIST_LEN:   (_NONE,  "Push list length"),
    Op.LIST_GET:   (_NONE,  "Get list item by index"),
    Op.LIST_SET:   (_NONE,  "Set list item"),
    Op.MAP_NEW:    (_NONE,  "New empty map"),
    Op.MAP_GET:    (_NONE,  "Get map value"),
    Op.MAP_SET:    (_NONE,  "Set map value"),
    Op.MAP_HAS:    (_NONE,  "Check map key"),
    Op.MAP_DEL:    (_NONE,  "Delete map key"),
    Op.MAP_KEYS:   (_NONE,  "Push list of map keys"),
    Op.PRINT:      (_NONE,  "Print top (no newline)"),
    Op.PRINTLN:    (_NONE,  "Print top with newline"),
    Op.READ_LINE:  (_NONE,  "Push input line"),
    Op.READ_INT:   (_NONE,  "Push input as integer"),
    Op.READ_FLOAT: (_NONE,  "Push input as float"),
    Op.FLUSH:      (_NONE,  "Flush output"),
    Op.SYSCALL:    (_IMM8,  "System call"),
    Op.FOREIGN:    (_STR,   "Foreign function call"),
    Op.SPAWN:      (_NONE,  "Spawn coroutine"),
    Op.AWAIT_OP:   (_NONE,  "Await coroutine"),
    Op.YIELD:      (_NONE,  "Yield from coroutine"),
    Op.SLEEP:      (_NONE,  "Sleep ms"),
    Op.TRY_BEGIN:  (_IMM32, "Start try/recover frame"),
    Op.TRY_END:    (_NONE,  "End try frame"),
    Op.THROW:      (_NONE,  "Throw error object"),
    Op.THROW_STR:  (_STR,   "Throw string error"),
    Op.ENSURE_BEG: (_NONE,  "Begin ensure block"),
    Op.ENSURE_END: (_NONE,  "End ensure block"),
    Op.RETHROW:    (_NONE,  "Re-throw current error"),
    Op.BREAKPOINT: (_NONE,  "Debugger breakpoint"),
    Op.TRACE:      (_STR,   "Emit trace message"),
    Op.ASSERT:     (_NONE,  "Assert top is truthy"),
    Op.DUMP_STACK: (_NONE,  "Dump stack (debug)"),
    Op.DUMP_REGS:  (_NONE,  "Dump registers (debug)"),
}

# Reverse lookup: mnemonic string → Op
MNEMONIC_MAP: dict[str, Op] = {op.name: op for op in Op}
# Also add common aliases used in .ltasm source
MNEMONIC_MAP.update({
    "PUSH":     Op.PUSH_IMM,
    "PUSH.REG": Op.PUSH_REG,
    "PUSH.STR": Op.PUSH_STR,
    "JLE":      Op.CMPLE,     # convenience alias
    "JGE":      Op.CMPGE,
    "CALL.REG": Op.CALL_REG,
    "MOV.IMM":  Op.MOV_IMM,
})
