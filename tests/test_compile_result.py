import pytest

from lateralus_lang.compiler import CompileResult, Target

def test_compile_result_code_property_python():
    result = CompileResult(
        ok=True,
        target=Target.PYTHON,
        source_file="example.ltl",
        python_src="print('hello')",
    )
    assert result.code == "print('hello')"

def test_compile_result_code_property_c():
    result = CompileResult(
        ok=True,
        target=Target.C,
        source_file="example.ltl",
        c_src="int main() { return 0; }",
    )
    assert result.code == "int main() { return 0; }"

def test_compile_result_code_property_none_for_bytecode():
    result = CompileResult(
        ok=True,
        target=Target.BYTECODE,
        source_file="example.ltl",
        bytecode=None,
    )
    assert result.code is None
