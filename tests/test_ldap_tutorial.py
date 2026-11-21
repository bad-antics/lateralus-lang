"""
Regression test for examples/ldap_tutorial.ltl (stdlib/ldap tutorial companion).
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


def test_ldap_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "ldap_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB LDAP TUTORIAL ===" in out
    assert "enc_len(5)=05 enc_len(200)=81c8" in out
    assert "enc_integer(0)=020100" in out
    assert "enc_integer(127)=02017f" in out
    assert "enc_integer(128)=02020080" in out
    assert "enc_boolean(true)=0101ff" in out
    assert "enc_octet_string(\"cn\")=0402636e" in out
    assert "enc_enumerated(2)=0a0102" in out
    assert "tag=0x04 next=8 total=8" in out
    assert "value bytes=7569643d3432" in out
    assert "len=41 hex=302702010160220201030415636e3d61646d696e2c64633d65782c64633d636f6d8006733363726574" in out
    assert "parsed id=1 op_tag=0x60" in out
    assert "parsed id=7 op_tag=0x63" in out
    assert "hex=30050201094200" in out
    assert "PINNED_VECTORS: len5=05 len200=81c8" in out


def test_ldap_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "ldap_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
