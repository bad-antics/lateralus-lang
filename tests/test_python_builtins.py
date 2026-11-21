"""
Regression tests for stdlib-facing builtins in the Python codegen
prelude: char_at, char_code, index_of, split, substring, xor, try_int.
These names are used across ~38 stdlib/*.ltl files but were previously
undefined at runtime (NameError).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

LTL_SRC = """
fn main() {
    print(char_at("abc", 1))
    print(char_code("A"))
    print(index_of("hello", "ll"))
    print(index_of("hello", "z"))
    print(split("a,b,c", ","))
    print(split("ab", ""))
    print(substring("hello", 1, 4))
    print(xor(5, 3))
    print(try_int("42", 0))
    print(try_int("zz", 7))
    return 0
}
"""

EXPECTED = [
    "b",        # char_at
    "65",       # char_code
    "2",        # index_of hit
    "-1",       # index_of miss
    "['a', 'b', 'c']",  # split with sep
    "['a', 'b']",       # split with empty sep -> chars
    "ell",      # substring
    "6",        # xor
    "42",       # try_int ok
    "7",        # try_int fallback
]


@pytest.fixture()
def builtin_ltl(tmp_path):
    p = tmp_path / "builtin_probe.ltl"
    p.write_text(LTL_SRC)
    return p


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_new_builtins_execute(builtin_ltl):
    res = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(builtin_ltl)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        check=True, env=_env(),
    )
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    for expected in EXPECTED:
        assert expected in lines, f"missing {expected!r} in {lines}"


def test_stdlib_hash_fnv1a_uses_new_builtins():
    """stdlib/hash.ltl fnv1a_32 calls char_code + xor; verify end-to-end."""
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(str(REPO_ROOT / "stdlib" / "hash.ltl"), target=Target.PYTHON)
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness executes generated code
    # Reference FNV-1a 32 of "abc"
    h = 2166136261
    for ch in "abc":
        h ^= ord(ch)
        h = (h * 16777619) % 4294967296
    assert ns["fnv1a_32"]("abc") == h
