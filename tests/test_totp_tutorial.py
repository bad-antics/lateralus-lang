"""
Regression test for examples/totp_tutorial.ltl (stdlib/totp tutorial companion).
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


def test_totp_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "totp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB TOTP TUTORIAL ===" in out
    assert "sha256(\"\")=e3b0c44298fc1c149afbf4c8996fb924" in out
    assert "sha256(\"abc\")=ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in out
    assert "hotp(counter=7,8)=67579288" in out
    assert "hotp(counter=4,8)=25480556" in out
    assert "T=59 -> 32247374" in out
    assert "T=1111111109 -> 34756375" in out
    assert "T=1234567890 -> 42829826" in out
    assert "T=2000000000 -> 78428693" in out
    assert "T=20000000000 -> 24142410" in out
    assert "exact=True" in out
    assert "drift=1: True" in out
    assert "wrong=False" in out
    assert "otpauth://totp/Example:alice%40example.com" in out
    assert "secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ" in out
    assert "PINNED_VECTORS: sha256abc=ba7816bf" in out


def test_totp_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "totp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
