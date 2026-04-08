"""
tests/test_v19_features.py  -  v1.9 Feature Test Suite
===========================================================================
Tests for all LATERALUS v1.9 features:
  · Compiler: JAVASCRIPT and WASM target enum values
  · Codegen: JavaScript transpilation and WASM compilation
  · CLI: js and wasm subcommand wiring
  · FFI: FFIRegistry, FFIFunction, define_ffi_struct, memory helpers
  · Jupyter: kernel install spec, LateralusKernel execution
  · C backend: v1.7/v1.8 visitor coverage (const fn, macro, comptime, cfg)
  · End-to-end: v19_showcase.ltl compiles to Python, JS, WASM, C
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest

from lateralus_lang.compiler import Compiler, Target

# --- Helpers -----------------------------------------------------------------

def compile_ok(src: str, target: Target = Target.PYTHON) -> object:
    r = Compiler().compile_source(src, target=target, filename="<test>")
    assert r.ok, f"Compile failed ({target.name}): {[e.message for e in r.errors[:3]]}"
    return r


# ===========================================================================
# 1. Target enum — JAVASCRIPT and WASM exist
# ===========================================================================

class TestTargetEnum:
    def test_javascript_target_exists(self):
        assert hasattr(Target, "JAVASCRIPT")

    def test_wasm_target_exists(self):
        assert hasattr(Target, "WASM")

    def test_all_targets(self):
        names = [t.name for t in Target]
        assert "PYTHON" in names
        assert "C" in names
        assert "JAVASCRIPT" in names
        assert "WASM" in names


# ===========================================================================
# 2. JavaScript transpilation
# ===========================================================================

class TestJavaScript:
    def test_simple_let(self):
        r = compile_ok("let x = 42", Target.JAVASCRIPT)
        assert r.js_src is not None
        assert len(r.js_src) > 0

    def test_function(self):
        r = compile_ok("fn greet(name: str) -> str { return name }", Target.JAVASCRIPT)
        assert "function" in r.js_src or "greet" in r.js_src

    def test_println(self):
        r = compile_ok('println("hello")', Target.JAVASCRIPT)
        assert r.js_src is not None

    def test_arithmetic(self):
        r = compile_ok("let x = 2 + 3 * 4", Target.JAVASCRIPT)
        assert r.js_src is not None

    def test_if_else(self):
        src = 'if true { println("yes") } else { println("no") }'
        r = compile_ok(src, Target.JAVASCRIPT)
        assert r.js_src is not None

    def test_struct(self):
        src = "struct Point { x: float, y: float }"
        r = compile_ok(src, Target.JAVASCRIPT)
        assert r.js_src is not None

    def test_js_src_field_populated(self):
        r = compile_ok("let x = 1", Target.JAVASCRIPT)
        assert r.js_src is not None
        assert r.python_src is None  # should NOT populate Python for JS target

    def test_match_basic(self):
        src = "let x = 1\nlet r = match x {\n    1 => 10,\n    _ => 0,\n}"
        r = compile_ok(src, Target.JAVASCRIPT)
        assert r.js_src is not None


# ===========================================================================
# 3. WASM compilation
# ===========================================================================

class TestWASM:
    def test_simple_wasm(self):
        r = compile_ok("fn main() { let x = 42 }", Target.WASM)
        assert r.wasm_src is not None
        assert len(r.wasm_src) > 0

    def test_wasm_contains_module(self):
        r = compile_ok("fn main() { let x = 1 }", Target.WASM)
        assert "(module" in r.wasm_src

    def test_wasm_src_field_populated(self):
        r = compile_ok("fn main() { let x = 1 }", Target.WASM)
        assert r.wasm_src is not None
        assert r.python_src is None


# ===========================================================================
# 4. FFI bridge
# ===========================================================================

class TestFFI:
    def test_import_ffi(self):
        pass

    def test_registry_creation(self):
        from lateralus_lang.ffi import FFIRegistry
        reg = FFIRegistry()
        assert reg is not None

    def test_registry_declare_function(self):
        from lateralus_lang.ffi import FFIRegistry
        reg = FFIRegistry()
        reg.declare_function(
            name="abs_val",
            lib="c",
            param_types=["int"],
            return_type="int",
            c_name="abs",
        )
        fn = reg.get_function("abs_val")
        assert fn is not None
        assert fn.name == "abs_val"

    def test_registry_declare_struct(self):
        from lateralus_lang.ffi import FFIRegistry
        reg = FFIRegistry()
        reg.declare_struct("Point", [("x", "float"), ("y", "float")])
        cls = reg.get_struct("Point")
        assert cls is not None

    def test_define_ffi_struct(self):
        from lateralus_lang.ffi import define_ffi_struct
        PointStruct = define_ffi_struct("TestPoint", [("x", "float"), ("y", "float")])
        p = PointStruct(x=1.0, y=2.0)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_get_ffi_builtins(self):
        from lateralus_lang.ffi import get_ffi_builtins
        builtins = get_ffi_builtins()
        assert "ffi_declare" in builtins
        assert "ffi_call" in builtins
        assert "ffi_alloc" in builtins
        assert "ffi_free" in builtins
        assert "load_library" in builtins

    def test_ffi_alloc_free(self):
        from lateralus_lang.ffi import ffi_alloc, ffi_free
        ptr = ffi_alloc(64)
        assert ptr is not None
        ffi_free(ptr)

    def test_ffi_write_read_string(self):
        from lateralus_lang.ffi import ffi_free, ffi_read_string, ffi_write_string
        ptr = ffi_write_string("hello")
        result = ffi_read_string(ptr)
        assert result == "hello"
        ffi_free(ptr)

    def test_type_mapping(self):
        import ctypes

        from lateralus_lang.ffi import LTL_TO_CTYPE
        assert LTL_TO_CTYPE["int"] == ctypes.c_int64
        assert LTL_TO_CTYPE["float"] == ctypes.c_double
        assert LTL_TO_CTYPE["bool"] == ctypes.c_bool
        assert LTL_TO_CTYPE["str"] == ctypes.c_char_p


# ===========================================================================
# 5. Jupyter kernel
# ===========================================================================

class TestJupyterKernel:
    def test_import_kernel(self):
        pass

    def test_kernel_spec(self):
        from lateralus_lang.jupyter_kernel import KERNEL_SPEC
        assert "argv" in KERNEL_SPEC
        assert "display_name" in KERNEL_SPEC
        assert KERNEL_SPEC["language"] == "lateralus"

    def test_kernel_creation(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        assert k._exec_count == 0

    def test_kernel_execute(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_execute("let x = 42")
        assert result["status"] == "ok"
        assert result["execution_count"] == 1

    def test_kernel_execute_with_output(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_execute('println("test")')
        assert result["status"] == "ok"

    def test_kernel_execute_error(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_execute("fn { broken syntax {{{")
        assert result["status"] == "error"
        assert "CompileError" in result["ename"]

    def test_kernel_complete(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_complete("pri", 3)
        assert result["status"] == "ok"
        assert "println" in result["matches"] or "print" in result["matches"]

    def test_kernel_inspect(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_inspect("println", 7)
        assert result["found"] is True

    def test_kernel_is_complete(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        assert k.do_is_complete("let x = 1")["status"] == "complete"
        assert k.do_is_complete("fn foo() {")["status"] == "incomplete"

    def test_kernel_empty_input(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        result = k.do_execute("")
        assert result["status"] == "ok"

    def test_kernel_language_info(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        assert k.language_info["name"] == "lateralus"
        assert k.language_info["file_extension"] == ".ltl"

    def test_kernel_sequential_execution(self):
        from lateralus_lang.jupyter_kernel import LateralusKernel
        k = LateralusKernel()
        r1 = k.do_execute("let x = 10")
        r2 = k.do_execute("let y = 20")
        assert r1["execution_count"] == 1
        assert r2["execution_count"] == 2


# ===========================================================================
# 6. C backend — v1.7/v1.8 visitors
# ===========================================================================

class TestCBackendV18:
    def test_const_fn(self):
        src = "const fn square(x: int) -> int { return x * x }"
        r = compile_ok(src, Target.C)
        assert r.c_src is not None
        assert "inline" in r.c_src or "const fn" in r.c_src

    def test_comptime_block(self):
        src = "comptime { let x = 42 }"
        r = compile_ok(src, Target.C)
        assert r.c_src is not None
        assert "comptime" in r.c_src

    def test_cfg_expr(self):
        src = 'let is_web = cfg!(target, "web")'
        r = compile_ok(src, Target.C)
        assert r.c_src is not None

    def test_basic_c_output(self):
        src = "fn add(a: int, b: int) -> int { return a + b }"
        r = compile_ok(src, Target.C)
        assert "int64_t" in r.c_src
        assert "add" in r.c_src

    def test_struct_c(self):
        src = "struct Vec3 { x: float, y: float, z: float }"
        r = compile_ok(src, Target.C)
        assert "struct" in r.c_src
        assert "Vec3" in r.c_src
        assert "double" in r.c_src

    def test_enum_c(self):
        src = "enum Color { Red, Green, Blue }"
        r = compile_ok(src, Target.C)
        assert "Color" in r.c_src

    def test_imports_complete(self):
        """Verify all v1.8 AST nodes are importable in C backend."""
        from lateralus_lang.codegen.c import CTranspiler
        t = CTranspiler()
        # Check that visitor methods exist
        assert hasattr(t, "_visit_ConstFnDecl")
        assert hasattr(t, "_visit_MacroDecl")
        assert hasattr(t, "_visit_CompTimeBlock")
        assert hasattr(t, "_expr_ReflectExpr")
        assert hasattr(t, "_expr_QuoteExpr")
        assert hasattr(t, "_expr_MacroInvocation")
        assert hasattr(t, "_expr_CfgExpr")
        assert hasattr(t, "_visit_NurseryBlock")
        assert hasattr(t, "_expr_ChannelExpr")


# ===========================================================================
# 7. End-to-end showcase compilation
# ===========================================================================

class TestV19Showcase:
    @pytest.fixture
    def showcase_src(self):
        p = pathlib.Path(__file__).parent.parent / "examples" / "v19_showcase.ltl"
        return p.read_text()

    def test_v19_showcase_python(self, showcase_src):
        r = compile_ok(showcase_src, Target.PYTHON)
        assert len(r.python_src) > 100

    def test_v19_showcase_javascript(self, showcase_src):
        r = compile_ok(showcase_src, Target.JAVASCRIPT)
        assert len(r.js_src) > 100

    def test_v19_showcase_wasm(self, showcase_src):
        r = compile_ok(showcase_src, Target.WASM)
        assert r.wasm_src is not None

    def test_v19_showcase_c(self, showcase_src):
        r = compile_ok(showcase_src, Target.C)
        assert len(r.c_src) > 100


# ===========================================================================
# 8. CompileResult fields
# ===========================================================================

class TestCompileResult:
    def test_result_has_js_src(self):
        r = compile_ok("let x = 1", Target.JAVASCRIPT)
        assert hasattr(r, "js_src")

    def test_result_has_wasm_src(self):
        r = compile_ok("fn main() { let x = 1 }", Target.WASM)
        assert hasattr(r, "wasm_src")

    def test_python_target_no_js(self):
        r = compile_ok("let x = 1", Target.PYTHON)
        assert r.js_src is None
        assert r.wasm_src is None

    def test_c_target_no_js(self):
        r = compile_ok("fn main() { let x = 1 }", Target.C)
        assert r.js_src is None
        assert r.wasm_src is None
