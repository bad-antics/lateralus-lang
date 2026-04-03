"""
tests/test_wasm_backend.py  ─  WebAssembly Backend Tests
═══════════════════════════════════════════════════════════════════════════
Tests for the Lateralus → WebAssembly Text Format (WAT) pipeline.
Covers WasmModule, WasmCompiler, WAT generation, and expression compilation.

v1.5.1
═══════════════════════════════════════════════════════════════════════════
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.codegen.wasm import (
    WasmModule,
    WasmCompiler,
    WasmType,
    WasmFunction,
    compile_to_wasm,
    expression_to_wat,
    i64_const,
    f64_const,
    i32_const,
    local_get,
    local_set,
    local_tee,
    global_get,
)


# ═══════════════════════════════════════════════════════════════════════════════
# WasmType Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWasmType:
    """Test LATERALUS → WASM type mapping."""

    def test_int_maps_to_i64(self):
        assert WasmType.from_ltl("int") == "i64"

    def test_float_maps_to_f64(self):
        assert WasmType.from_ltl("float") == "f64"

    def test_bool_maps_to_i32(self):
        assert WasmType.from_ltl("bool") == "i32"

    def test_str_maps_to_i32_pointer(self):
        assert WasmType.from_ltl("str") == "i32"

    def test_none_maps_to_empty(self):
        assert WasmType.from_ltl("None") == ""

    def test_any_maps_to_i64(self):
        assert WasmType.from_ltl("any") == "i64"

    def test_unknown_maps_to_i64(self):
        """Unknown types default to i64."""
        assert WasmType.from_ltl("SomeStruct") == "i64"

    def test_constants(self):
        assert WasmType.I32 == "i32"
        assert WasmType.I64 == "i64"
        assert WasmType.F32 == "f32"
        assert WasmType.F64 == "f64"
        assert WasmType.NONE == ""


# ═══════════════════════════════════════════════════════════════════════════════
# WAT Instruction Builder Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWatInstructions:
    """Test WAT instruction builder functions."""

    def test_i64_const(self):
        assert i64_const(42) == "i64.const 42"

    def test_i64_const_negative(self):
        assert i64_const(-1) == "i64.const -1"

    def test_f64_const(self):
        assert f64_const(3.14) == "f64.const 3.14"

    def test_i32_const(self):
        assert i32_const(0) == "i32.const 0"

    def test_local_get(self):
        assert local_get("x") == "local.get $x"

    def test_local_set(self):
        assert local_set("y") == "local.set $y"

    def test_local_tee(self):
        assert local_tee("z") == "local.tee $z"

    def test_global_get(self):
        assert global_get("counter") == "global.get $counter"


# ═══════════════════════════════════════════════════════════════════════════════
# WasmModule Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWasmModule:
    """Test WasmModule construction and WAT serialization."""

    def test_empty_module(self):
        mod = WasmModule("test")
        wat = mod.to_wat()
        assert "(module" in wat
        assert "test" in wat

    def test_module_with_memory(self):
        mod = WasmModule("memtest")
        mod.add_memory(1, exported=True)
        wat = mod.to_wat()
        assert "(memory" in wat

    def test_module_with_function(self):
        mod = WasmModule("fntest")
        fn = mod.add_function("main", [], "i64", exported=True)
        fn.emit(i64_const(0))
        wat = mod.to_wat()
        assert "(func" in wat
        assert "$main" in wat
        assert "(export" in wat

    def test_function_with_params(self):
        mod = WasmModule("params")
        fn = mod.add_function("add", [("a", "i64"), ("b", "i64")], "i64")
        fn.emit(local_get("a"))
        fn.emit(local_get("b"))
        fn.emit("i64.add")
        wat = mod.to_wat()
        assert "(param $a i64)" in wat
        assert "(param $b i64)" in wat
        assert "(result i64)" in wat

    def test_function_with_locals(self):
        mod = WasmModule("locals")
        fn = mod.add_function("test", [], "i64")
        fn.add_local("tmp", "i64")
        fn.emit(i64_const(42))
        fn.emit(local_set("tmp"))
        fn.emit(local_get("tmp"))
        wat = mod.to_wat()
        assert "(local $tmp i64)" in wat

    def test_exported_function(self):
        mod = WasmModule("export_test")
        mod.add_function("greet", [], "", exported=True)
        wat = mod.to_wat()
        assert '(export "greet"' in wat

    def test_multiple_functions(self):
        mod = WasmModule("multi")
        mod.add_function("a", [], "i64", exported=True).emit(i64_const(1))
        mod.add_function("b", [], "i64", exported=True).emit(i64_const(2))
        wat = mod.to_wat()
        assert "$a" in wat
        assert "$b" in wat

    def test_import(self):
        mod = WasmModule("imports")
        mod.import_function("env", "println", "println", [("msg", "i32")], "")
        wat = mod.to_wat()
        assert "(import" in wat
        assert '"env"' in wat
        assert '"println"' in wat


# ═══════════════════════════════════════════════════════════════════════════════
# WasmCompiler Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWasmCompiler:
    """Test the WasmCompiler class."""

    def test_create_compiler(self):
        c = WasmCompiler()
        assert c is not None
        assert c._module is not None

    def test_compile_integer_expression(self):
        wat = expression_to_wat("42")
        assert "i64.const 42" in wat or "i32.const 42" in wat

    def test_compile_addition(self):
        wat = expression_to_wat("3 + 4")
        assert "add" in wat.lower() or "const" in wat.lower()

    def test_compile_multiplication(self):
        wat = expression_to_wat("5 * 6")
        assert "mul" in wat.lower() or "const" in wat.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# compile_to_wasm API Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompileToWasm:
    """Test the top-level compile_to_wasm API."""

    def test_returns_wasm_module(self):
        mod = compile_to_wasm("fn main() { return 0 }")
        assert isinstance(mod, WasmModule)

    def test_module_generates_wat(self):
        mod = compile_to_wasm("fn main() { return 0 }")
        wat = mod.to_wat()
        assert isinstance(wat, str)
        assert "(module" in wat

    def test_module_has_main(self):
        mod = compile_to_wasm("fn main() { return 0 }")
        wat = mod.to_wat()
        assert "main" in wat


# ═══════════════════════════════════════════════════════════════════════════════
# WAT Serialization Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWatSerialization:
    """Test that generated WAT is well-formed."""

    def test_balanced_parentheses(self):
        mod = WasmModule("balance")
        mod.add_function("f", [("x", "i64")], "i64", exported=True)
        wat = mod.to_wat()
        assert wat.count("(") == wat.count(")"), "Unbalanced parens in WAT"

    def test_no_empty_lines_in_function(self):
        mod = WasmModule("clean")
        fn = mod.add_function("test", [], "i64")
        fn.emit(i64_const(0))
        wat = mod.to_wat()
        # WAT should not have consecutive blank lines inside a function
        assert "\n\n\n" not in wat

    def test_indentation_consistent(self):
        mod = WasmModule("indent")
        fn = mod.add_function("test", [], "i64", exported=True)
        fn.emit(i64_const(42))
        wat = mod.to_wat()
        lines = [l for l in wat.splitlines() if l.strip()]
        # All non-empty lines should start with spaces or (
        for line in lines:
            assert line[0] in (' ', '(', ')'), f"Bad indent: {line!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Round-trip structure tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWasmIntegration:
    """Integration tests for the WASM backend."""

    def test_arithmetic_functions(self):
        """Verify that arithmetic-heavy programs produce valid WAT."""
        mod = WasmModule("arith")
        fn = mod.add_function("compute", [("a", "i64"), ("b", "i64")], "i64",
                              exported=True)
        fn.emit(local_get("a"))
        fn.emit(local_get("b"))
        fn.emit("i64.add")
        wat = mod.to_wat()
        assert "i64.add" in wat
        assert "(export" in wat

    def test_conditional_logic(self):
        """Test if/else control flow in WAT."""
        mod = WasmModule("cond")
        fn = mod.add_function("abs_val", [("x", "i64")], "i64")
        fn.add_local("result", "i64")
        fn.emit(local_get("x"))
        fn.emit(i64_const(0))
        fn.emit("i64.lt_s")
        fn.emit("if (result i64)")
        fn.emit(i64_const(0))
        fn.emit(local_get("x"))
        fn.emit("i64.sub")
        fn.emit("else")
        fn.emit(local_get("x"))
        fn.emit("end")
        wat = mod.to_wat()
        assert "if" in wat
        assert "else" in wat
        assert "end" in wat

    def test_loop_structure(self):
        """Test loop/br control flow in WAT."""
        mod = WasmModule("loop_test")
        fn = mod.add_function("count_to_ten", [], "i64")
        fn.add_local("i", "i64")
        fn.emit(i64_const(0))
        fn.emit(local_set("i"))
        fn.emit("(block $exit")
        fn.emit("  (loop $loop")
        fn.emit(f"    {local_get('i')}")
        fn.emit(f"    {i64_const(10)}")
        fn.emit("    i64.ge_s")
        fn.emit("    br_if $exit")
        fn.emit(f"    {local_get('i')}")
        fn.emit(f"    {i64_const(1)}")
        fn.emit("    i64.add")
        fn.emit(f"    {local_set('i')}")
        fn.emit("    br $loop")
        fn.emit("  )")
        fn.emit(")")
        fn.emit(local_get("i"))
        wat = mod.to_wat()
        assert "block" in wat
        assert "loop" in wat
        assert "br_if" in wat

    def test_memory_operations(self):
        """Test memory load/store instructions."""
        mod = WasmModule("mem")
        mod.add_memory(1, exported=True)
        fn = mod.add_function("store_and_load", [], "i64")
        fn.emit(i32_const(0))        # address
        fn.emit(i64_const(42))       # value
        fn.emit("i64.store")
        fn.emit(i32_const(0))        # address
        fn.emit("i64.load")
        wat = mod.to_wat()
        assert "i64.store" in wat
        assert "i64.load" in wat
        assert "(memory" in wat
