"""
tests/test_compiler.py  -  End-to-end compiler pipeline tests
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest

from lateralus_lang.compiler import Compiler, CompileResult, Target


@pytest.fixture
def compiler():
    return Compiler()


def check(src: str, target=Target.PYTHON) -> CompileResult:
    return Compiler().compile_source(src, target=target, filename="<test>")


# --- Compilation success guard -------------------------------------------------

class TestBasicCompilation:
    def test_empty_source(self):
        r = check("")
        assert r.ok

    def test_hello_world_python(self):
        r = check('fn main() { io.println("hello") }')
        assert r.ok
        assert r.python_src is not None

    def test_let_decl_check(self):
        r = check("let x = 10", target=Target.CHECK)
        assert r.ok

    def test_function_decl(self):
        r = check("fn add(a: int, b: int) -> int { return a + b }")
        assert r.ok


# --- Python transpiler output --------------------------------------------------

class TestPythonTranspiler:
    def test_let_becomes_assignment(self):
        r = check("let x = 42")
        assert r.ok
        assert "x = 42" in r.python_src

    def test_fn_becomes_def(self):
        r = check("fn greet(name: str) { }")
        assert r.ok
        assert "def greet" in r.python_src

    def test_return_statement(self):
        r = check("fn id(x: int) -> int { return x }")
        assert r.ok
        assert "return" in r.python_src

    def test_if_else(self):
        r = check("if x > 0 { } else { }")
        assert r.ok
        assert "if" in r.python_src
        assert "else" in r.python_src

    def test_while_loop(self):
        r = check("while i < 10 { i += 1 }")
        assert r.ok
        assert "while" in r.python_src

    def test_for_loop(self):
        r = check("for item in items { }")
        assert r.ok
        assert "for" in r.python_src
        assert "in" in r.python_src

    def test_pipeline_operator(self):
        r = check("let y = x |> double")
        assert r.ok
        # pipeline should expand to a call
        assert "double" in r.python_src

    def test_optional_pipeline_bytecode(self):
        # `a |? f` must not fall through to ADD in the IR (issue #447):
        # nil -> nil, otherwise f(a). Verified end-to-end on the VM.
        from lateralus_lang.vm.vm import VM
        src = ("fn inc(x: int) -> int { return x + 1 }\n"
               "fn add2(x: int, y: int) -> int { return x + y }\n"
               "fn main() -> int { return EXPR }")
        for expr, want in [("5 |? inc", 6), ("nil |? inc", 0),
                           ("41 |? inc", 42), ("5 |? add2(10)", 15),
                           ("nil |? add2(10)", 0)]:
            r = Compiler().compile_source(src.replace("EXPR", expr),
                                          target=Target.BYTECODE, filename="<test>")
            assert r.ok, (expr, r.errors)
            vm = VM(r.bytecode)
            vm.run()
            assert vm.stack[-1] == want, (expr, vm.stack)

    def test_try_recover_becomes_try_except(self):
        r = check("try { } recover IOError(e) { }")
        assert r.ok
        assert "try" in r.python_src
        assert "except" in r.python_src

    def test_string_literal(self):
        r = check('let s = "hello world"')
        assert r.ok
        assert '"hello world"' in r.python_src or "'hello world'" in r.python_src

    def test_bool_literal(self):
        r = check("let flag = true")
        assert r.ok
        assert "True" in r.python_src

    def test_nil_becomes_none(self):
        r = check("let n = nil")
        assert r.ok
        assert "None" in r.python_src


# --- Error reporting ----------------------------------------------------------

class TestErrorReporting:
    def test_syntax_error_not_ok(self):
        r = check("fn { bad syntax !!!")
        assert not r.ok
        assert len(r.errors) > 0

    def test_errors_have_messages(self):
        r = check("@@@@")
        assert not r.ok
        for err in r.errors:
            assert err.message

    def test_compile_result_summary_on_success(self):
        r = check("let x = 1")
        s = r.summary()
        assert "OK" in s or "ok" in s.lower()

    def test_compile_result_summary_on_error(self):
        r = check("$$$invalid$$$")
        s = r.summary()
        assert "error" in s.lower() or "fail" in s.lower()


# --- Target: CHECK (lex + parse + semantic only) -------------------------------

class TestCheckTarget:
    def test_valid_code_ok(self):
        r = check("fn add(a: int, b: int) -> int { return a + b }", Target.CHECK)
        assert r.ok
        assert r.python_src is None
        assert r.bytecode  is None

    def test_invalid_code_not_ok(self):
        r = check("let = ", Target.CHECK)
        assert not r.ok


# --- Assembly target ----------------------------------------------------------

class TestAssemblyTarget:
    def test_assemble_simple(self):
        asm = ".section code\n_start:\n  PUSH_IMM 1\n  HALT\n"
        r = Compiler().compile_source(asm, target=Target.ASSEMBLE, filename="t.ltasm")
        assert r.ok
        assert r.bytecode is not None

    def test_assemble_bad_opcode(self):
        asm = ".section code\n_start:\n  FAKEOPCODE\n  HALT\n"
        r = Compiler().compile_source(asm, target=Target.ASSEMBLE, filename="t.ltasm")
        assert not r.ok


# --- CompileResult helpers ----------------------------------------------------

class TestCompileResult:
    def test_result_ok_flag(self):
        r = CompileResult(ok=True)
        assert r.ok

    def test_result_elapsed_non_negative(self):
        r = check("let x = 0")
        assert r.elapsed_ms >= 0

    def test_result_error_list_empty_on_success(self):
        r = check("fn f() { }")
        assert r.errors == [] or all(e.severity.value == "warning" for e in r.errors)
