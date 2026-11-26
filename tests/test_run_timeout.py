"""
tests/test_run_timeout.py  -  the wall-clock cap on `lateralus run`

The cap used to be a literal 60 inside Compiler._run_python. These tests pin the
three ways to change it: the constructor argument, the CLI flag, and the
LATERALUS_RUN_TIMEOUT environment variable. Each case runs a script that
deliberately outlives a 1 second budget, so the tests stay fast.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Compiler._run_python spawns a subprocess to run the transpiled script, so the
# child needs to be able to import lateralus_lang. pytest inserts the rootdir
# into its own sys.path, not into PYTHONPATH.
os.environ["PYTHONPATH"] = os.pathsep.join(
    [str(ROOT)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
)

import pytest

from lateralus_lang.compiler import DEFAULT_RUN_TIMEOUT, Compiler

SLOW = """
fn main() -> int {
    let i = 0
    while i < 400000000 { i = i + 1 }
    println(str(i))
    return 0
}
"""


def _times_out(compiler: Compiler) -> bool:
    result = compiler.run_source(SLOW, filename="<timeout-test>")
    return (not result.ok) and any("timed out" in str(e) for e in result.errors)


def test_default_is_sixty_seconds():
    assert DEFAULT_RUN_TIMEOUT == 60.0
    assert Compiler().run_timeout == 60.0


def test_explicit_timeout_is_used():
    assert _times_out(Compiler(run_timeout=1))


def test_zero_disables_the_cap(monkeypatch):
    monkeypatch.delenv("LATERALUS_RUN_TIMEOUT", raising=False)
    assert Compiler(run_timeout=0).run_timeout is None


def test_environment_variable_is_honoured(monkeypatch):
    monkeypatch.setenv("LATERALUS_RUN_TIMEOUT", "1")
    assert Compiler().run_timeout == 1.0
    assert _times_out(Compiler())


def test_explicit_argument_beats_environment(monkeypatch):
    monkeypatch.setenv("LATERALUS_RUN_TIMEOUT", "1")
    assert Compiler(run_timeout=900).run_timeout == 900.0


def test_bad_environment_value_is_ignored(monkeypatch):
    monkeypatch.setenv("LATERALUS_RUN_TIMEOUT", "not-a-number")
    assert Compiler().run_timeout == DEFAULT_RUN_TIMEOUT


def test_error_message_explains_the_flag():
    result = Compiler(run_timeout=1).run_source(SLOW, filename="<timeout-test>")
    assert not result.ok
    message = " ".join(str(e) for e in result.errors)
    assert "--timeout" in message
