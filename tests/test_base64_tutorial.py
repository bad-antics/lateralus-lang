"""
Regression test for examples/base64_tutorial.ltl (stdlib/base64 tutorial companion).
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


def test_base64_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "base64_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB BASE64 TUTORIAL ===" in out
    assert "all_vectors=True" in out
    assert "roundtrip_all=True" in out
    assert "dec=>>>" in out
    assert "rt=True" in out
    assert "valid_Zm9v=True" in out
    assert "valid_bang=False" in out
    assert "valid_short=False" in out
    assert "enc_len_1=4" in out
    assert "enc_len_4=8" in out
    assert "dec_len_Zg===1" in out
    assert "dec_len_Zm9v=3" in out
    assert "PINNED_VECTORS: rfc4648_7of7" in out


def test_base64_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "base64_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
