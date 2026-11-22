"""
Regression test for examples/chacha20_tutorial.ltl (stdlib/chacha20 tutorial companion).
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


def test_chacha20_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "chacha20_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB CHACHA20 TUTORIAL ===" in out
    assert "a=3928658676 b=3407673550 c=1166100270 d=1484899515" in out
    assert "first32=10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4e" in out
    assert "matches_rfc=True" in out
    assert "pt_len=114 ct_len=114" in out
    assert "ct_first32=6e2e359a2568f98041ba0728dd0d6981e97e7aec1d4360c20a27afccfd9fae0b" in out
    assert "roundtrip=True" in out
    assert "block1!=block2=True" in out
    assert "counter0_differs=True" in out
    assert "PINNED_VECTORS: qr_a=0xea2a92f4" in out
    assert "rfc_block=True rfc_enc=True roundtrip=True" in out


def test_chacha20_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "chacha20_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
