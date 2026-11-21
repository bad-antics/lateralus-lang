"""
Regression test for examples/graphql_tutorial.ltl (stdlib/graphql tutorial companion).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_graphql_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "graphql_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB GRAPHQL TUTORIAL ===" in out
    assert "query GetUser($id: ID!, $withPosts: Boolean = true) {" in out
    assert "  user(id: $id) {" in out
    assert "    name" in out
    assert "    posts {" in out
    assert "      title" in out
    assert "mutation UpdateUser {" in out
    assert "  upd: updateUser(input: {name: \"Ann\"}) {" in out
    assert "  20 tokens: query ... }" in out
    assert "  op=query name=Q" in out
    assert "  top fields=1 first=user" in out
    assert "  nested=1 leaf=name" in out
    assert "  alias=me field=viewer" in out
    assert "PINNED_VECTORS: build=query+GetUser+2vars" in out


def test_graphql_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "graphql_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
