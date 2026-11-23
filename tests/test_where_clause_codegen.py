import subprocess
import sys
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_where_clause_transpilation(tmp_path):
    src = """
fn main() -> int {
    let norm = 10.0;
    let result = (1 * 2 + 3 * 4) / norm where {
        let a = 1; let b = 2; let c = 3; let d = 4
        let norm = 10.0
    };
    println(result);
    return 0;
}
"""
    c = Compiler()
    res = c.compile_source(src, target=Target.PYTHON)
    assert res.ok
    assert res.python_src is not None
    assert "_ltl_where_" in res.python_src
    assert "return (((1 * 2) + (3 * 4)) / norm)" in res.python_src


def test_where_clause_execution(tmp_path):
    src = """
fn main() -> int {
    let norm = 10.0;
    let result = (1 * 2 + 3 * 4) / norm where {
        let a = 1; let b = 2; let c = 3; let d = 4
        let norm = 10.0
    };
    println(result);
    return 0;
}
"""
    f = tmp_path / "test_where.ltl"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "1.4" in proc.stdout


def test_nested_where_clause(tmp_path):
    src = """
fn calc() -> int {
    let x = a + b where {
        let a = 10
        let b = 20
    };
    return x;
}
fn main() {
    println(calc());
}
"""
    f = tmp_path / "test_nested_where.ltl"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "30" in proc.stdout
