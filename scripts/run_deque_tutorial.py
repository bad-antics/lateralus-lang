"""Run the actual deque module through the Lateralus parser and Python backend.

The Python backend does not resolve `import deque` to stdlib/deque.ltl.
Combining the unmodified module and example makes that boundary explicit.
No Python replacement implementation or fabricated module output is used.
"""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lateralus_lang.parser import parse
from lateralus_lang.codegen.python import transpile_to_python


def run_example():
    module = (ROOT / "stdlib/deque.ltl").read_text(encoding="utf-8")
    example = (ROOT / "examples/deque_work_queue.ltl").read_text(encoding="utf-8")
    generated = transpile_to_python(parse(module + "\n" + example))
    output = io.StringIO()
    with redirect_stdout(output):
        exec(compile(generated, "<deque-tutorial-generated>", "exec"), {})
    return output.getvalue()


def verify():
    actual = run_example().replace("\r\n", "\n")
    expected = (ROOT / "examples/deque_work_queue.expected.txt").read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(f"Deque vector mismatch\nExpected:\n{expected}\nActual:\n{actual}")
    return actual


if __name__ == "__main__":
    print(verify(), end="")
