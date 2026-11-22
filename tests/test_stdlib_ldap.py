"""
Tests for stdlib/ldap.ltl — BER length/integer encoding fixes.

`/` transpiles to Python `/` (float). enc_len used n/256 & n/65536
(float & int → TypeError) and enc_integer looped `n = n / 256`
(float never reaches exactly 0 → runaway loop + wrong bytes).
All divisions now wrapped in int(). BER vector semantics verified
end-to-end in examples/ldap_tutorial.ltl (PR #364).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LDAP_LTL = REPO_ROOT / "stdlib" / "ldap.ltl"


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_stdlib_ldap_typechecks():
    res = subprocess.run(
        [sys.executable, "bin/ltlc", "check", str(LDAP_LTL)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env())
    assert res.returncode == 0, res.stdout + res.stderr


def test_ldap_divisions_are_integer_cast():
    src = LDAP_LTL.read_text()
    assert "0x82, (n / 256)" not in src
    assert "0x83, (n / 65536)" not in src
    assert "n = n / 256" not in src
    assert "int(n / 256)" in src
    assert "int(n / 65536)" in src
