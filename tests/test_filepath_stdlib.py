"""
Regression tests for stdlib/filepath.ltl.

substring()/split() are not runtime builtins — the module could not
compile to runnable Python (NameError at runtime, and the comment-only
if body in normalize() produced an IndentationError).  Now uses
slice()/str_split() and pass.
"""
from __future__ import annotations

import posixpath
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "filepath.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_dirname_basename_extension_stem():
    ns = _load()
    assert ns["dirname"]("/home/user/file.txt") == "/home/user"
    assert ns["basename"]("/home/user/file.txt") == "file.txt"
    assert ns["extension"]("file.tar.gz") == ".gz"
    assert ns["stem"]("file.tar.gz") == "file.tar"


def test_join_path():
    ns = _load()
    assert ns["join_path"](["/home", "user", "f.txt"]) == "/home/user/f.txt"
    assert ns["join_path"](["a", "b"]) == "a/b"


def test_normalize_matches_posixpath():
    ns = _load()
    for p in ["/a/./b/../c//d", "./x/../y", "/", "a/b/", "../up", "/a/b/c"]:
        assert ns["normalize"](p) == posixpath.normpath(p), p


def test_queries():
    ns = _load()
    assert ns["is_absolute"]("/x") is True
    assert ns["is_absolute"]("x") is False
    assert ns["is_relative"]("x/y") is True
    assert ns["has_extension"]("f.txt", ".txt") is True
    assert ns["has_extension"]("f.txt", ".gz") is False
    assert ns["with_extension"]("file.ltl", ".py") == "file.py"
