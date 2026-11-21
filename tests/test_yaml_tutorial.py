"""
Regression test for examples/yaml_tutorial.ltl (stdlib/yaml tutorial companion).
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


def test_yaml_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "yaml_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB YAML TUTORIAL ===" in out
    assert "comment: key: value" in out
    assert 'quoted_hash: k: "a#b"' in out
    assert "empty=None" in out
    assert "int=42" in out
    assert "neg_int=-7" in out
    assert "dquoted=hi there" in out
    assert "name=demo" in out
    assert "count=3" in out
    assert "enabled=True" in out
    assert "note_is_nil=True" in out
    assert "host=localhost" in out
    assert "port=8080" in out
    assert "tls=False" in out
    assert "item0=alpha" in out
    assert "item1=42" in out
    assert "item2=True" in out
    assert "item3_nil=True" in out
    assert "u0_name=alice" in out
    assert "u0_role=admin" in out
    assert "u1_name=bob" in out
    assert "u1_role=user" in out
    assert "PINNED_VECTORS: flat name=demo count=3 enabled=true" in out


def test_yaml_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "yaml_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
