"""Regression test for the documented type_of builtin."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_type_of_function_is_available(tmp_path: Path) -> None:
    source = """
fn main() -> int {
    println(type_of(5))
    return 0
}
"""
    program = tmp_path / "type_of.ltl"
    program.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(program)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "<class 'int'>"
