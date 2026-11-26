"""Executable conformance tests for stdlib/base64.ltl.

The existing stdlib tests only check that base64.ltl compiles. These tests
append a small assertion driver to the real module source, execute it through
the Python backend, and also run the shipped example.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from lateralus_lang.compiler import Compiler, Target


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "stdlib" / "base64.ltl"
EXAMPLE = ROOT / "examples" / "base64_vectors.ltl"

DRIVER = r'''
fn main() {
    assert_eq(encode(""), "")
    assert_eq(encode("f"), "Zg==")
    assert_eq(encode("fo"), "Zm8=")
    assert_eq(encode("foo"), "Zm9v")
    assert_eq(encode("foob"), "Zm9vYg==")
    assert_eq(encode("fooba"), "Zm9vYmE=")
    assert_eq(encode("foobar"), "Zm9vYmFy")

    assert_eq(decode(""), "")
    assert_eq(decode("Zg=="), "f")
    assert_eq(decode("Zm8="), "fo")
    assert_eq(decode("Zm9v"), "foo")
    assert_eq(decode("Zm9vYg=="), "foob")
    assert_eq(decode("Zm9vYmE="), "fooba")
    assert_eq(decode("Zm9vYmFy"), "foobar")

    assert_eq(decode(encode("hello, world")), "hello, world")
    assert_eq(decode(encode("a+b/c?")), "a+b/c?")
    assert_eq(decode(encode("Lateralus")), "Lateralus")

    assert_eq(encode_url("a+b/c?"), "YStiL2M_")
    assert_eq(decode_url("YStiL2M_"), "a+b/c?")

    assert_eq(is_valid(""), true)
    assert_eq(is_valid("Zg=="), true)
    assert_eq(is_valid("===="), false)
    assert_eq(is_valid("Zg=A"), false)

    assert_eq(encoded_length(5), 8)
    assert_eq(decoded_length("Zm9vYmFy"), 6)
    println("base64 ok")
}

main()
'''


def _python_env() -> dict[str, str]:
    env = os.environ.copy()
    old_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + old_path if old_path else "")
    return env


def test_base64_stdlib_runs_and_matches_rfc4648(tmp_path: Path) -> None:
    """Execute the real module source, not a copied or parsed variant."""
    source = MODULE.read_text(encoding="utf-8") + "\n" + DRIVER
    result = Compiler().compile_source(
        source,
        target=Target.PYTHON,
        filename="base64.ltl",
    )
    assert result.ok, [error.message for error in result.errors]
    assert result.python_src

    script = tmp_path / "base64_check.py"
    script.write_text(result.python_src, encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        env=_python_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "base64 ok" in proc.stdout


def test_base64_example_runs() -> None:
    """The bounty requires a runnable example with pinned vectors."""
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(EXAMPLE)],
        cwd=str(ROOT),
        env=_python_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "pass=27 fail=0" in proc.stdout
