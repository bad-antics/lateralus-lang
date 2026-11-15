"""
tests/test_wasm_backend.py  ─  WebAssembly Backend Tests
═══════════════════════════════════════════════════════════════════════════
Tests for the Lateralus → WebAssembly Text Format (WAT) pipeline.
Covers WasmModule, WasmCompiler, WAT generation, and expression compilation.

v1.5.1
═══════════════════════════════════════════════════════════════════════════
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from lateralus_lang.codegen.wasm import (
    WasmCompiler,
    WasmModule,
    WasmType,
    compile_to_wasm,
    compile_to_wasm_bytes,
    expression_to_wat,
    f64_const,
    generate_js_host_shim,
    global_get,
    i32_const,
    i64_const,
    local_get,
    local_set,
    local_tee,
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


# ═══════════════════════════════════════════════════════════════════════════════
# Binary Encoding, Host Shims, CLI & Playground Tests
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_wasm_sections(wasm_bytes: bytes) -> list[int]:
    """Decode top-level WebAssembly section IDs and validate framing."""
    assert wasm_bytes[:8] == b"\x00asm\x01\x00\x00\x00"
    pos = 8
    section_ids: list[int] = []
    while pos < len(wasm_bytes):
        sec_id = wasm_bytes[pos]
        pos += 1
        size = 0
        shift = 0
        while True:
            byte = wasm_bytes[pos]
            pos += 1
            size |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        assert pos + size <= len(wasm_bytes)
        pos += size
        section_ids.append(sec_id)
    assert pos == len(wasm_bytes)
    assert section_ids == sorted(section_ids)
    return section_ids


class TestWasmBinaryAndHostShims:
    """Test binary .wasm serialization, host call imports, and JS shims."""

    def test_println_and_http_get_imports(self):
        src = '''
fn main() {
    let body = http_get("https://example.com")
    println("resp={body}")
}
'''
        mod = compile_to_wasm(src)
        wat = mod.to_wat()
        assert '(import "env" "println"' in wat
        assert '(import "env" "http_get"' in wat
        assert '(export "ltl_alloc")' in wat
        assert '(export "memory")' in wat
        assert "(data (i32.const" in wat

    def test_http_dot_get_alias(self):
        src = '''
fn main() {
    let body = http.get("https://lateralus.dev/api/health")
    println(body)
}
'''
        wat = compile_to_wasm(src).to_wat()
        assert '(import "env" "http_get"' in wat
        assert '(import "env" "println"' in wat

    def test_to_wasm_bytes_valid_sections(self):
        src = '''
fn add(a: int, b: int) -> int {
    return a + b
}

fn main() {
    let sum = add(20, 22)
    let resp = http_get("https://example.com")
    if sum > 40 {
        println("sum={sum}, resp={resp}")
    } else {
        println("small")
    }
    for i in 0..2 {
        println(i)
    }
}
'''
        wasm_bytes = compile_to_wasm_bytes(src)
        sections = _parse_wasm_sections(wasm_bytes)
        assert sections == [1, 2, 3, 5, 6, 7, 10, 11]

    def test_manual_module_conditional_and_loop_to_wasm_bytes(self):
        mod = WasmModule("ctrl")
        fn_cond = mod.add_function("abs_val", [("x", "i64")], "i64", exported=True)
        fn_cond.emit(local_get("x"), i64_const(0), "i64.lt_s", "if (result i64)",
                     i64_const(0), local_get("x"), "i64.sub", "else", local_get("x"), "end")

        fn_loop = mod.add_function("count_to_ten", [], "i64", exported=True)
        fn_loop.add_local("i", "i64")
        fn_loop.emit(
            i64_const(0), local_set("i"),
            "(block $exit", "  (loop $loop",
            f"    {local_get('i')}", f"    {i64_const(10)}", "    i64.ge_s", "    br_if $exit",
            f"    {local_get('i')}", f"    {i64_const(1)}", "    i64.add", f"    {local_set('i')}",
            "    br $loop", "  )", ")", local_get("i"),
        )
        wasm_bytes = mod.to_wasm_bytes()
        sections = _parse_wasm_sections(wasm_bytes)
        assert 1 in sections and 3 in sections and 7 in sections and 10 in sections

    def test_generate_js_host_shim(self):
        shim = generate_js_host_shim()
        assert "createLateralusHostShim" in shim
        assert "runLateralusWasm" in shim
        assert "WebAssembly.instantiate" in shim
        assert "println" in shim
        assert "http_get" in shim
        assert "ltl_println_i64" in shim


class TestWasmCliAndPlayground:
    """Test CLI wasm flags and offline WebAssembly playground."""

    def test_cli_wasm_bin_and_shim(self, tmp_path):
        from lateralus_lang.__main__ import main

        ltl_file = tmp_path / "prog.ltl"
        ltl_file.write_text('fn main() {\n    println("hi wasm")\n}\n', encoding="utf-8")
        wasm_out = tmp_path / "prog.wasm"
        shim_out = tmp_path / "prog.runtime.js"

        rc = main(["wasm", str(ltl_file), "-o", str(wasm_out), "--shim", str(shim_out)])
        assert rc == 0
        raw = wasm_out.read_bytes()
        _parse_wasm_sections(raw)
        shim_text = shim_out.read_text(encoding="utf-8")
        assert "createLateralusHostShim" in shim_text
        assert "http_get" in shim_text

    def test_playground_uses_in_browser_wasm_offline(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        html = (root / "docs" / "website" / "playground" / "index.html").read_text(encoding="utf-8")
        assert "/api/run" not in html
        assert "compileLateralusToWasm" in html
        assert "createLateralusHostShim" in html
        assert "WebAssembly.instantiate" in html
        assert "http_get" in html
        assert "println" in html

        headers = (root / "docs" / "website" / "_headers").read_text(encoding="utf-8")
        assert "'wasm-unsafe-eval'" in headers
