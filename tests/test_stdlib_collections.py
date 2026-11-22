"""
Tests for stdlib/collections.ltl — `fn` is a reserved keyword and
cannot be used as a parameter name; the module failed to parse.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COLL_LTL = REPO_ROOT / "stdlib" / "collections.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_collections_typechecks():
    """stdlib/collections.ltl must parse — `fn` param names broke it."""
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(COLL_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout


def test_no_fn_keyword_as_param():
    src = COLL_LTL.read_text()
    # `fn` may appear as the lambda keyword but never as a bare param
    for bad in ("lst: list, fn)", "b: list, fn)", "init, fn)"):
        assert bad not in src, f"reserved `fn` still used as param: {bad}"


def test_group_by_guards_missing_keys():
    """groups[k] on a missing key raises KeyError under the shim —
    group_by must guard with contains(keys(...)) like ini.ltl."""
    src = COLL_LTL.read_text()
    assert "groups[k] == nil" not in src
    assert "contains(keys(groups), k)" in src
