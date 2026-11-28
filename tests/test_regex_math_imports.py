import subprocess
import sys
from lateralus_lang.compiler import Compiler, Target


def test_regex_import_and_find_first(tmp_path):
    src = """
import stdlib.regex as regex
fn main() {
    println(regex.find_first("[a-z]+-[0-9]+", "jobs: sync-104, build-7"))
}
"""
    f = tmp_path / "test_regex.ltl"
    f.write_text(src, encoding="utf-8")
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok
    assert res.python_src is not None
    assert "regex = _regex" in res.python_src


def test_regex_execution_end_to_end(tmp_path):
    src = """
import stdlib.regex as regex
fn main() {
    println(regex.find_first("[a-z]+-[0-9]+", "jobs: sync-104, build-7"))
    println(regex.find_all("[a-z]+-[0-9]+", "jobs: sync-104, build-7"))
}
"""
    f = tmp_path / "test_regex_exec.ltl"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "sync-104" in proc.stdout
    assert "build-7" in proc.stdout


def test_math_module_attributes(tmp_path):
    src = """
import math
fn main() -> int {
    println(math.sqrt(16.0))
    println(math.TAU)
    println(math.lerp(0.0, 10.0, 0.5))
    println(math.fibonacci(10))
    return 0
}
"""
    f = tmp_path / "test_math_attrs.ltl"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "4.0" in proc.stdout
    assert "6.2831853" in proc.stdout
    assert "5.0" in proc.stdout
    assert "55" in proc.stdout


def test_from_import_regex(tmp_path):
    src = """
from stdlib.regex import find_first
fn main() {
    println(find_first("[0-9]+", "cost: 100 USD"))
}
"""
    f = tmp_path / "test_from_regex.ltl"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "100" in proc.stdout
