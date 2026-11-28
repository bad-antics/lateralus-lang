"""Pinned behavior vectors for stdlib.set."""
from pathlib import Path
import contextlib
import io

from lateralus_lang.compiler import Compiler, Target


ROOT = Path(__file__).parent.parent


def run_ltl(source: str) -> str:
    result = Compiler().compile_source(source, target=Target.PYTHON, filename="set_vectors.ltl")
    assert result.ok, [error.message for error in result.errors]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(result.python_src, {"__builtins__": __builtins__})
    return output.getvalue()


def test_set_vectors_are_sorted_and_deduplicated():
    source = (ROOT / "stdlib" / "set.ltl").read_text() + """
let languages = from_list(["Lateralus", "Python", "Lateralus", "C"])
let compiled = add(languages, "Wasm")
let shared = intersection(compiled, ["C", "Wasm", "C"])
let without_c = remove(compiled, "C")
println(languages)
println(compiled)
println(shared)
println(without_c)
println(equals([3, 1, 3, 2], [1, 2, 3]))
"""
    assert run_ltl(source) == (
        '["C", "Lateralus", "Python"]\n'
        '["C", "Lateralus", "Python", "Wasm"]\n'
        '["C", "Wasm"]\n'
        '["Lateralus", "Python", "Wasm"]\n'
        'true\n'
    )


def test_set_module_compiles():
    source = (ROOT / "stdlib" / "set.ltl").read_text()
    result = Compiler().compile_source(source, target=Target.PYTHON, filename="set.ltl")
    assert result.ok, [error.message for error in result.errors]
