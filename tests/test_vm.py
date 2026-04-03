"""
tests/test_vm.py  ─  VM & assembler integration tests
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.vm.opcodes    import Op
from lateralus_lang.vm.assembler  import Bytecode, assemble
from lateralus_lang.vm.vm         import VM, VMError, ThrownError


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_bytecode(*ops_and_args: int) -> Bytecode:
    """Assemble a raw byte sequence into a Bytecode with default meta."""
    bc = Bytecode()
    for byte in ops_and_args:
        bc.code.append(byte & 0xFF)
    return bc


def _run(bc: Bytecode) -> VM:
    vm = VM(bc)
    vm.run()
    return vm


# ─── Stack operations ──────────────────────────────────────────────────────────

class TestStackOps:
    def test_push_pop_int(self):
        bc = Bytecode()
        bc.code.extend([Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 42, Op.HALT])
        vm = _run(bc)
        # HALT does not pop the stack; 42 remains as the top value
        assert vm.stack == [42]

    def test_push_then_pop(self):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 7,
            Op.POP,
            Op.HALT,
        ])
        vm = _run(bc)
        assert vm.stack == []

    def test_dup(self):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 5,
            Op.DUP,
            Op.HALT,
        ])
        vm = _run(bc)
        assert len(vm.stack) == 2
        assert vm.stack[-1] == 5

    def test_swap(self):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 1,
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 2,
            Op.SWAP,
            Op.HALT,
        ])
        vm = _run(bc)
        assert vm.stack == [2, 1]


# ─── Arithmetic ────────────────────────────────────────────────────────────────

class TestArithmetic:
    def _arith_result(self, op_byte):
        """Push 10, 3; apply op; return top of stack."""
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 10,
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 3,
            op_byte,
            Op.HALT,
        ])
        vm = _run(bc)
        return vm.stack[-1]

    def test_add(self):    assert self._arith_result(Op.ADD) == 13
    def test_sub(self):    assert self._arith_result(Op.SUB) == 7
    def test_mul(self):    assert self._arith_result(Op.MUL) == 30
    def test_div(self):    assert self._arith_result(Op.DIV) == 10 // 3
    def test_mod(self):    assert self._arith_result(Op.MOD) == 10 % 3

    def test_neg(self):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 5,
            Op.NEG,
            Op.HALT,
        ])
        vm = _run(bc)
        assert vm.stack[-1] == -5


# ─── Comparison ────────────────────────────────────────────────────────────────

class TestComparison:
    def _cmp(self, a, b, op):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, a,
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, b,
            op,
            Op.HALT,
        ])
        return _run(bc).stack[-1]

    def test_eq_true(self):   assert self._cmp(5, 5, Op.EQ)  == 1
    def test_eq_false(self):  assert self._cmp(5, 6, Op.EQ)  == 0
    def test_ne(self):        assert self._cmp(5, 6, Op.NE)  == 1
    def test_lt(self):        assert self._cmp(3, 5, Op.LT)  == 1
    def test_gt(self):        assert self._cmp(5, 3, Op.GT)  == 1
    def test_le_equal(self):  assert self._cmp(4, 4, Op.LE)  == 1
    def test_ge_larger(self): assert self._cmp(5, 3, Op.GE)  == 1


# ─── Registers ─────────────────────────────────────────────────────────────────

class TestRegisters:
    def test_store_load(self):
        bc = Bytecode()
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 99,
            Op.STORE_REG, 0,        # store into r0
            Op.LOAD_REG,  0,        # push r0 back
            Op.HALT,
        ])
        vm = _run(bc)
        assert vm.regs[0] == 99
        assert vm.stack[-1] == 99


# ─── Jump / Branch ──────────────────────────────────────────────────────────────

class TestControlFlow:
    def test_jmp_unconditional(self):
        bc = Bytecode()
        # JMP past PUSH_IMM 0xBB → only 0xAA on stack
        after_idx = 14  # byte position of the PUSH 0xAA
        bc.code.extend([
            Op.JMP,   (after_idx >> 24) & 0xFF, (after_idx >> 16) & 0xFF,
                      (after_idx >>  8) & 0xFF,  after_idx & 0xFF,
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 0xBB,   # skipped
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 0xAA,
            Op.HALT,
        ])
        vm = _run(bc)
        assert 0xBB not in vm.stack
        assert vm.stack[-1] == 0xAA

    def test_jz_taken(self):
        bc = Bytecode()
        target = 15
        bc.code.extend([
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 0,  # condition = 0 (falsy)
            Op.JZ, 0, 0, 0, target,
            Op.PUSH_IMM, 0, 0, 0, 0, 0, 0, 0, 1,  # skipped
            Op.HALT,
        ])
        vm = _run(bc)
        assert 1 not in vm.stack


# ─── Assembler ─────────────────────────────────────────────────────────────────

class TestAssembler:
    def test_assemble_halt(self):
        bc = assemble(".section code\n_start:\n  HALT\n", "<test>")
        assert bc.code[bc.entry_point] == Op.HALT

    def test_push_int_literal(self):
        bc = assemble(".section code\n_start:\n  PUSH_IMM 42\n  HALT\n", "<test>")
        vm = VM(bc)
        vm.run()
        assert vm.stack[-1] == 42

    def test_add_two_literals(self):
        src = """.section code
_start:
  PUSH_IMM 10
  PUSH_IMM 5
  ADD
  HALT
"""
        vm = VM(assemble(src, "<test>"))
        vm.run()
        assert vm.stack[-1] == 15

    def test_label_resolution(self):
        src = """.section code
_start:
  JMP end
  PUSH_IMM 0
end:
  PUSH_IMM 1
  HALT
"""
        vm = VM(assemble(src, "<test>"))
        vm.run()
        assert 0 not in vm.stack
        assert vm.stack[-1] == 1


# ─── Error Handling ─────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_throw_unhandled_raises(self):
        bc = Bytecode()
        # Push error message, then THROW
        msg_idx = len(bc.string_table)
        bc.string_table.append("oops")
        bc.code.extend([
            Op.PUSH_STR, (msg_idx >> 8) & 0xFF, msg_idx & 0xFF,
            Op.THROW,
            Op.HALT,
        ])
        vm = VM(bc)
        with pytest.raises(ThrownError):
            vm.run()

    def test_try_end_clears_frame(self):
        bc = Bytecode()
        after = 10
        bc.code.extend([
            Op.TRY_BEGIN, 0, 0, 0, after,
            Op.TRY_END,
            Op.HALT,
        ])
        vm = _run(bc)
        assert vm.error_stack == []
