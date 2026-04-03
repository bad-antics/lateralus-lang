"""lateralus_lang/vm/__init__.py"""
from .opcodes import Op, MNEMONIC_MAP, OPCODE_META
from .assembler import Bytecode, Assembler, AssemblerError, assemble
from .vm import VM, VMError, StackUnderflowError, DivisionByZeroError, ThrownError
from .disassembler import (
    disassemble, disassemble_instruction, instruction_length,
    DisassemblerError,
)

__all__ = [
    "Op", "MNEMONIC_MAP", "OPCODE_META",
    "Bytecode", "Assembler", "AssemblerError", "assemble",
    "VM", "VMError", "StackUnderflowError", "DivisionByZeroError", "ThrownError",
    "disassemble", "disassemble_instruction", "instruction_length",
    "DisassemblerError",
]
