"""Regression test for the collections import collision reported in #879."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_import_collections_uses_lateralus_stdlib(tmp_path: Path) -> None:
    source = """
import collections

fn main() -> int {
    let s = collections.Stack()
    s.push(7)
    println(s.peek())
    println(s.size())
    return 0
}
"""
    program = tmp_path / "collections_import.ltl"
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
    assert result.stdout.splitlines()[-2:] == ["7", "1"]
