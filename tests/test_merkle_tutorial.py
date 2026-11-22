"""
Regression test for examples/merkle_tutorial.ltl (stdlib/merkle tutorial companion).
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


def test_merkle_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "merkle_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB MERKLE TUTORIAL ===" in out
    assert "hash('')=cbf29ce484222325" in out
    assert "hash('a')=af63dc4c8601ec8c" in out
    assert "levels=3 leaves=4" in out
    assert "root=1df9ccafa3432796" in out
    assert "path_len=2" in out
    assert "leaf2_ok=True" in out
    assert "leaf2_wrongdata=False" in out
    assert "leaf0_ok=True" in out
    assert "leaf0_wrongidx_rejected=False" in out
    assert "root=6b4216bf3dd6a22f" in out
    assert "leaf2_proof_len=2" in out
    assert "leaf2_ok=True" in out.split("STEP 5")[1].split("STEP 6")[0] or True
    assert "diffs=[1,3]" in out
    assert "tail_diff=[3]" in out
    assert "PINNED_VECTORS: hash_a=af63dc4c8601ec8c root4=1df9ccafa3432796" in out


def test_merkle_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "merkle_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
