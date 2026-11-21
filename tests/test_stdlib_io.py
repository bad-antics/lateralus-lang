"""
Tests for stdlib/io.ltl — path helper fixes.

The module's file ops dispatch to _host_* compiler intrinsics and its
console helpers need stdin, so coverage here is: (1) the file must
parse/type-check under ltlc (it previously failed on list[str]
generics), and (2) the dirname/extension slicing fixes are pinned by
source inspection plus the runnable companion in
examples/io_tutorial.ltl.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IO_LTL = REPO_ROOT / "stdlib" / "io.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_io_typechecks():
    """stdlib/io.ltl must parse — list[str] generics broke ltlc check."""
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(IO_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout


def test_dirname_returns_directory_component():
    src = IO_LTL.read_text()
    assert 'return slice(path, 0, last_slash)' in src
    assert 'if last_slash == 0 { return "/" }' in src
    # the old bug returned the whole path
    assert "return path  // sliced" not in src


def test_extension_returns_suffix_with_dot():
    src = IO_LTL.read_text()
    assert "return slice(b, dot_idx, len(b))" in src
    assert "return b  // sliced" not in src
