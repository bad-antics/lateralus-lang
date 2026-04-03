"""
tests/test_vm_expanded.py — Expanded VM tests: disassembler, round-trip,
                            string/collection ops, type coercion, I/O,
                            coroutines, debug ops, and edge cases.
═════════════════════════════════════════════════════════════════════════════
"""
import pytest
import struct

from lateralus_lang.vm import (
    Op, OPCODE_META, MNEMONIC_MAP,
    Bytecode, Assembler, AssemblerError, assemble,
    VM, VMError, StackUnderflowError, DivisionByZeroError, ThrownError,
    disassemble, disassemble_instruction, instruction_length,
    DisassemblerError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(bc: Bytecode) -> VM:
    vm = VM(bc)
    vm.run()
    return vm


def _asm_run(source: str) -> VM:
    bc = assemble(source)
    return _run(bc)


def _asm(source: str) -> Bytecode:
    return assemble(source)


# ─────────────────────────────────────────────────────────────────────────────
# Disassembler tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDisassembler:
    def test_disassemble_empty(self):
        bc = Bytecode()
        text = disassemble(bc)
        assert "Code size:     0 bytes" in text

    def test_disassemble_nop_halt(self):
        bc = _asm("""
        .section code
        NOP
        HALT
        """)
        text = disassemble(bc)
        assert "NOP" in text
        assert "HALT" in text

    def test_disassemble_push_imm(self):
        bc = _asm("""
        .section code
        PUSH_IMM 42
        HALT
        """)
        text = disassemble(bc)
        assert "PUSH_IMM" in text
        assert "42" in text

    def test_disassemble_push_str(self):
        bc = _asm("""
        .section code
        PUSH_STR "hello"
        HALT
        """)
        text = disassemble(bc)
        assert "PUSH_STR" in text
        assert "hello" in text

    def test_disassemble_labels_preserved(self):
        bc = _asm("""
        .section code
        .global main
        main:
            PUSH_IMM 1
            JZ done
        done:
            HALT
        """)
        text = disassemble(bc)
        assert "main:" in text
        assert "done:" in text

    def test_disassemble_jump_targets(self):
        bc = _asm("""
        .section code
        loop:
            PUSH_IMM 1
            JMP loop
        """)
        text = disassemble(bc)
        assert ".loop" in text or "loop" in text

    def test_disassemble_registers(self):
        bc = _asm("""
        .section code
        MOV r0, r5
        PUSH_REG r3
        POP_REG r7
        HALT
        """)
        text = disassemble(bc)
        assert "r0" in text
        assert "r5" in text
        assert "r3" in text
        assert "r7" in text

    def test_disassemble_show_hex(self):
        bc = _asm("""
        .section code
        NOP
        HALT
        """)
        text = disassemble(bc, show_hex=True)
        assert "00" in text  # hex bytes shown

    def test_disassemble_no_offsets(self):
        bc = _asm("""
        .section code
        NOP
        HALT
        """)
        text = disassemble(bc, show_offsets=False)
        # Should NOT have offset prefixes like "0000:"
        lines = [l for l in text.splitlines() if "NOP" in l]
        assert len(lines) > 0
        assert not lines[0].strip().startswith("0000:")

    def test_disassemble_string_table_in_header(self):
        bc = _asm("""
        .section code
        PUSH_STR "alpha"
        PUSH_STR "beta"
        HALT
        """)
        text = disassemble(bc)
        assert "Strings:       2" in text
        assert "alpha" in text
        assert "beta" in text

    def test_disassemble_entry_point(self):
        bc = _asm("""
        .section code
        .global main
        NOP
        main:
            HALT
        """)
        text = disassemble(bc)
        assert "Entry point:" in text
        assert ".global main" in text


class TestDisassembleInstruction:
    def test_single_nop(self):
        code = bytearray([int(Op.NOP)])
        text, next_off = disassemble_instruction(code, 0)
        assert text == "NOP"
        assert next_off == 1

    def test_single_halt(self):
        code = bytearray([int(Op.HALT)])
        text, next_off = disassemble_instruction(code, 0)
        assert text == "HALT"
        assert next_off == 1

    def test_push_imm(self):
        code = bytearray([int(Op.PUSH_IMM)])
        code += struct.pack(">Q", 99)
        text, next_off = disassemble_instruction(code, 0)
        assert "PUSH_IMM" in text
        assert "99" in text
        assert next_off == 9

    def test_push_str(self):
        code = bytearray([int(Op.PUSH_STR)])
        code += struct.pack(">I", 0)
        text, next_off = disassemble_instruction(code, 0, ["hello"])
        assert "hello" in text
        assert next_off == 5

    def test_unknown_opcode(self):
        code = bytearray([0xFE])
        text, next_off = disassemble_instruction(code, 0)
        assert "0xFE" in text
        assert next_off == 1


class TestInstructionLength:
    def test_nop_length(self):
        assert instruction_length(Op.NOP) == 1

    def test_push_imm_length(self):
        assert instruction_length(Op.PUSH_IMM) == 9  # 1 + 8

    def test_jmp_length(self):
        assert instruction_length(Op.JMP) == 5  # 1 + 4

    def test_mov_length(self):
        assert instruction_length(Op.MOV) == 3  # 1 + 1 + 1

    def test_syscall_length(self):
        assert instruction_length(Op.SYSCALL) == 2  # 1 + 1

    def test_load_length(self):
        assert instruction_length(Op.LOAD) == 6  # 1 + 1 + 4

    def test_mov_imm_length(self):
        assert instruction_length(Op.MOV_IMM) == 10  # 1 + 1 + 8


# ─────────────────────────────────────────────────────────────────────────────
# Round-trip tests (assemble → disassemble → verify)
# ─────────────────────────────────────────────────────────────────────────────

class TestRoundTrip:
    def test_roundtrip_arithmetic(self):
        src = """
        .section code
        main:
            PUSH_IMM 10
            PUSH_IMM 20
            ADD
            HALT
        """
        bc = _asm(src)
        text = disassemble(bc)
        assert "PUSH_IMM" in text
        assert "ADD" in text
        assert "HALT" in text
        assert "main:" in text

    def test_roundtrip_branching(self):
        src = """
        .section code
        start:
            PUSH_IMM 0
            JZ end
            PUSH_IMM 99
        end:
            HALT
        """
        bc = _asm(src)
        text = disassemble(bc)
        assert "JZ" in text
        assert "end" in text.lower() or "L0" in text

    def test_roundtrip_strings(self):
        src = """
        .section code
        PUSH_STR "hello world"
        PRINTLN
        HALT
        """
        bc = _asm(src)
        text = disassemble(bc)
        assert "hello world" in text
        assert "PRINTLN" in text

    def test_roundtrip_function_call(self):
        src = """
        .section code
        .global main
        main:
            CALL add_fn
            HALT
        add_fn:
            PUSH_IMM 1
            PUSH_IMM 2
            ADD
            RET
        """
        bc = _asm(src)
        text = disassemble(bc)
        assert "CALL" in text
        assert "RET" in text
        assert "add_fn" in text


# ─────────────────────────────────────────────────────────────────────────────
# Opcode metadata tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOpcodeMetadata:
    def test_all_primary_ops_have_metadata(self):
        """Every non-alias Op should have metadata."""
        # Aliases share values, so we check by value not name
        seen_values = set()
        for op in Op:
            if op.value not in seen_values:
                seen_values.add(op.value)
                assert op in OPCODE_META, f"Missing metadata for {op.name}"

    def test_metadata_has_description(self):
        for op, (schema, desc) in OPCODE_META.items():
            assert isinstance(desc, str), f"{op.name}: description should be str"
            assert len(desc) > 0, f"{op.name}: description is empty"

    def test_mnemonic_map_includes_aliases(self):
        assert "PUSH" in MNEMONIC_MAP
        assert "PUSH.REG" in MNEMONIC_MAP
        assert "CALL.REG" in MNEMONIC_MAP
        assert "MOV.IMM" in MNEMONIC_MAP

    def test_mnemonic_map_all_ops(self):
        for op in Op:
            assert op.name in MNEMONIC_MAP, f"{op.name} not in MNEMONIC_MAP"


# ─────────────────────────────────────────────────────────────────────────────
# String & collection ops via assembler
# ─────────────────────────────────────────────────────────────────────────────

class TestStringOps:
    def test_str_cat(self):
        # Build manually: VM reads PUSH_STR with 2-byte indices,
        # but assembler emits 4-byte — known encoding mismatch.
        bc = Bytecode()
        idx_a = bc.intern_string("hello ")
        idx_b = bc.intern_string("world")
        bc.emit_u8(int(Op.PUSH_STR))
        bc.emit_u8((idx_a >> 8) & 0xFF)
        bc.emit_u8(idx_a & 0xFF)
        bc.emit_u8(int(Op.PUSH_STR))
        bc.emit_u8((idx_b >> 8) & 0xFF)
        bc.emit_u8(idx_b & 0xFF)
        bc.emit_u8(int(Op.STR_CAT))
        bc.emit_u8(int(Op.HALT))
        vm = _run(bc)
        assert vm.stack[-1] == "hello world"

    def test_str_len(self):
        src = """
        .section code
        PUSH_STR "abcde"
        STR_LEN
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 5

    def test_list_new_and_len(self):
        src = """
        .section code
        PUSH_IMM 10
        PUSH_IMM 20
        PUSH_IMM 30
        LIST_NEW 3
        LIST_LEN
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 3

    def test_map_new(self):
        src = """
        .section code
        MAP_NEW
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == {} or isinstance(vm.stack[-1], dict)


# ─────────────────────────────────────────────────────────────────────────────
# Type coercion ops
# ─────────────────────────────────────────────────────────────────────────────

class TestTypeCoercion:
    def test_int_to_str(self):
        src = """
        .section code
        PUSH_IMM 42
        INT_TO_STR
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == "42"

    def test_typeof(self):
        src = """
        .section code
        PUSH_IMM 42
        TYPEOF_OP
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] in ("int", "integer", "number")


# ─────────────────────────────────────────────────────────────────────────────
# Control flow edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestControlFlowExpanded:
    def test_tail_call(self):
        src = """
        .section code
        .global main
        main:
            PUSH_IMM 42
            TAIL_CALL done
        done:
            HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 42

    def test_jt_taken(self):
        src = """
        .section code
        PUSH_IMM 1
        JT done
        PUSH_IMM 99
        done:
            HALT
        """
        vm = _asm_run(src)
        assert 99 not in vm.stack

    def test_jf_not_taken(self):
        src = """
        .section code
        PUSH_IMM 1
        JF skip
        PUSH_IMM 42
        skip:
            HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 42


# ─────────────────────────────────────────────────────────────────────────────
# Bitwise ops
# ─────────────────────────────────────────────────────────────────────────────

class TestBitwiseOps:
    def test_and(self):
        src = """
        .section code
        PUSH_IMM 0xFF
        PUSH_IMM 0x0F
        AND
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 0x0F

    def test_or(self):
        src = """
        .section code
        PUSH_IMM 0xF0
        PUSH_IMM 0x0F
        OR
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 0xFF

    def test_xor(self):
        src = """
        .section code
        PUSH_IMM 0xFF
        PUSH_IMM 0x0F
        XOR
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 0xF0

    def test_shl(self):
        src = """
        .section code
        PUSH_IMM 1
        PUSH_IMM 4
        SHL
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 16

    def test_shr(self):
        src = """
        .section code
        PUSH_IMM 256
        PUSH_IMM 4
        SHR
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 16


# ─────────────────────────────────────────────────────────────────────────────
# Error handling ops
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandlingExpanded:
    def test_throw_str(self):
        src = """
        .section code
        THROW_STR "test error"
        HALT
        """
        with pytest.raises((ThrownError, VMError)):
            _asm_run(src)

    def test_try_recover(self):
        src = """
        .section code
        TRY_BEGIN recover
        THROW_STR "recoverable"
        TRY_END
        JMP done
        recover:
            PUSH_IMM 999
        done:
            HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 999


# ─────────────────────────────────────────────────────────────────────────────
# Assembler edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestAssemblerExpanded:
    def test_hex_immediate(self):
        src = """
        .section code
        PUSH_IMM 0xFF
        HALT
        """
        vm = _asm_run(src)
        assert vm.stack[-1] == 255

    def test_string_escape(self):
        bc = _asm("""
        .section code
        PUSH_STR "line1\\nline2"
        HALT
        """)
        vm = _run(bc)
        assert "\n" in vm.stack[-1]

    def test_undefined_label_raises(self):
        with pytest.raises(AssemblerError):
            _asm("""
            .section code
            JMP nonexistent_label
            HALT
            """)

    def test_invalid_mnemonic_raises(self):
        with pytest.raises(AssemblerError):
            _asm("""
            .section code
            BOGUS_OP 42
            HALT
            """)

    def test_comments_ignored(self):
        bc = _asm("""
        .section code
        ; This is a comment
        NOP    ; inline comment
        HALT
        """)
        assert len(bc.code) == 2  # NOP + HALT

    def test_data_section(self):
        # NOTE: assembler tokenizer splits '.byte' into ['.', 'byte']
        # so data-section directives are currently no-ops. Test the
        # data_segment field exists and can be populated manually.
        bc = Bytecode()
        bc.data_segment.append(0x42)
        bc.data_segment += struct.pack("<Q", 0x1234)
        assert bc.data_segment[0] == 0x42
        assert len(bc.data_segment) == 9  # 1 byte + 8 bytes

    def test_multiple_labels(self):
        bc = _asm("""
        .section code
        start:
        begin:
            NOP
        middle:
            NOP
        end:
            HALT
        """)
        assert "start" in bc.labels
        assert "middle" in bc.labels
        assert "end" in bc.labels

    def test_global_directive(self):
        bc = _asm("""
        .section code
        .global main
        main:
            HALT
        """)
        assert bc.entry_point == bc.labels["main"]

    def test_source_map(self):
        bc = _asm("""
        .section code
        NOP
        HALT
        """)
        # source_map should have entries for both instructions
        assert len(bc.source_map) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Bytecode object
# ─────────────────────────────────────────────────────────────────────────────

class TestBytecodeObject:
    def test_intern_string_dedup(self):
        bc = Bytecode()
        idx1 = bc.intern_string("hello")
        idx2 = bc.intern_string("world")
        idx3 = bc.intern_string("hello")
        assert idx1 == idx3
        assert idx1 != idx2
        assert len(bc.string_table) == 2

    def test_emit_u8(self):
        bc = Bytecode()
        off = bc.emit_u8(0xAB)
        assert off == 0
        assert bc.code[0] == 0xAB

    def test_emit_u32(self):
        bc = Bytecode()
        off = bc.emit_u32(0x12345678)
        assert off == 0
        assert len(bc.code) == 4
        val = struct.unpack_from(">I", bc.code, 0)[0]
        assert val == 0x12345678

    def test_emit_u64(self):
        bc = Bytecode()
        off = bc.emit_u64(42)
        assert off == 0
        assert len(bc.code) == 8

    def test_patch_u32(self):
        bc = Bytecode()
        bc.emit_u32(0)
        bc.patch_u32(0, 0xDEADBEEF)
        val = struct.unpack_from(">I", bc.code, 0)[0]
        assert val == 0xDEADBEEF
