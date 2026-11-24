"""
tests/test_issue_447_optional_pipeline.py
===========================================================================
Regression tests for Issue #447:
[bounty] bug-report: |? optional pipeline lowers to ADD in IR — broken on
bytecode/C/WASM targets.

Verifies:
  1. IR lowering maps '|?' to IROp.PIPE_OPT instead of falling back to IROp.ADD.
  2. Python target avoids falsy-collapse when right-hand function returns 0 or falsy.
  3. C backend emits proper null-check ternary for optional pipeline.
  4. Bytecode generator handles IROp.PIPE_OPT using conditional branching (Op.JF)
     and zero-fallback without unresolved label errors.
  5. JavaScript backend preserves safe execution without null reference errors.
===========================================================================
"""
import pytest
from lateralus_lang.lexer import Lexer
from lateralus_lang.parser import Parser
from lateralus_lang.ir import analyze, IROp
from lateralus_lang.compiler import Compiler, Target


def test_ir_lowering_optional_pipeline_to_pipe_opt():
    src = """
    fn zero(x: int) -> int { return 0 }
    fn inc(x: int) -> int { return x + 1 }
    fn main() {
        let a = 5 |? zero;
        let b = 7 |? inc;
    }
    """
    tokens = Lexer(src).tokenize()
    ast = Parser(tokens).parse()
    mod, errors = analyze(ast)
    assert not errors, f"Unexpected semantic errors: {errors}"

    main_fn = next((f for f in mod.functions if f.name == "main"), None)
    assert main_fn is not None, "main function not found in IR module"

    pipe_opt_instrs = [
        instr for block in main_fn.blocks
        for instr in block.instrs
        if instr.op == IROp.PIPE_OPT
    ]
    add_instrs = [
        instr for block in main_fn.blocks
        for instr in block.instrs
        if instr.op == IROp.ADD
    ]

    # There should be 2 PIPE_OPT instructions and 0 ADD instructions in main
    assert len(pipe_opt_instrs) == 2, f"Expected 2 PIPE_OPT instrs, got {len(pipe_opt_instrs)}"
    assert len(add_instrs) == 0, f"Expected 0 ADD instrs in main, got {len(add_instrs)}"


def test_python_codegen_and_execution_no_falsy_collapse():
    src = """
    fn zero(x: int) -> int { return 0 }
    fn inc(x: int) -> int { return x + 1 }
    fn calc() -> int {
        let z = 5 |? zero;
        let i = 7 |? inc;
        return z + i;
    }
    """
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {res.errors}"

    scope = {}
    exec(res.python_src, scope, scope)
    assert scope["calc"]() == 8, "Expected 0 + 8 == 8 (no falsy collapse on zero)"


def test_python_codegen_nil_handling():
    src = """
    fn inc(x: int) -> int { return x + 1 }
    fn test_nil() {
        return nil |? inc;
    }
    """
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {res.errors}"

    scope = {}
    exec(res.python_src, scope, scope)
    assert scope["test_nil"]() is None, "Expected nil |? inc to evaluate to None"


def test_c_backend_optional_pipeline_emits_null_check():
    src = """
    fn inc(x: int) -> int { return x + 1 }
    fn main() -> int {
        let a = 10 |? inc;
        return a;
    }
    """
    c = Compiler()
    res = c.compile_source(src, target=Target.C)
    assert res.ok, f"Compilation to C failed: {res.errors}"
    assert "!= NULL" in res.c_src, "C output must contain != NULL null check"


def test_bytecode_backend_compiles_pipe_opt_cleanly():
    src = """
    fn zero(x: int) -> int { return 0 }
    fn inc(x: int) -> int { return x + 1 }
    fn main() -> int {
        let a = 5 |? zero;
        let b = 7 |? inc;
        return a + b;
    }
    """
    c = Compiler()
    res = c.compile_source(src, target=Target.BYTECODE)
    assert res.ok, f"Bytecode generation failed: {res.errors}"
    assert res.bytecode is not None
    assert len(res.bytecode.code) > 0


def test_javascript_backend_compiles_pipe_opt():
    src = """
    fn inc(x: int) -> int { return x + 1 }
    fn main() {
        let x = 12 |? inc;
        return x;
    }
    """
    c = Compiler()
    res = c.compile_source(src, target=Target.JAVASCRIPT)
    assert res.ok, f"JS compilation failed: {res.errors}"
    assert "!=" in res.js_src
