"""
Regression test for examples/resp_tutorial.ltl (stdlib/resp tutorial companion).
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


def test_resp_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "resp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB RESP TUTORIAL ===" in out
    assert "simple: +OK\\r\\n" in out
    assert "int:    :42\\r\\n" in out
    assert "bulk:   $5\\r\\nhello\\r\\n" in out
    assert "nulls:  $-1\\r\\n*-1\\r\\n_\\r\\n" in out
    assert "bool:   #t\\r\\n#f\\r\\n" in out
    assert "double: ,3.14\\r\\n" in out
    assert "*3\\r\\n$3\\r\\nSET\\r\\n$3\\r\\nfoo\\r\\n$3\\r\\nbar\\r\\n" in out
    assert "+OK -> simple:OK next=5" in out
    assert ":42 -> 42 next=5" in out
    assert "$5 hello -> hello next=11" in out
    assert "$-1 null -> None next=5" in out
    assert "_ null3 -> nil next=3" in out
    assert "#t bool -> True next=4" in out
    assert ",3.14 dbl -> 3.14 next=7" in out
    assert "*2 array -> [GET, foo] next=22" in out
    assert "%1 map -> {'foo': 42} next=18" in out
    assert "~2 set -> [{'kind': 'simple', 'value': 'a'}, {'kind': 'simple', 'value': 'b'}] next=12" in out
    assert "truncated -> None next=5" in out
    assert "PINNED_VECTORS: cmd=*3|$3|SET|$3|foo|$3|bar simple=simple:OK int=42 bulk=hello nullbulk=None null3=nil bool=True dbl=3.14 arr=[GET,foo] map=foo:42 set=kindmaps trunc=None" in out


def test_resp_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "resp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
