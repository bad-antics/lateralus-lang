"""
Regression test for examples/oidc_tutorial.ltl (stdlib/oidc tutorial companion).
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


def test_oidc_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "oidc_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB OIDC TUTORIAL ===" in out
    assert "issuer=https://idp.example.com auth=https://idp.example.com/auth" in out
    assert "unknown dropped=True" in out
    assert "scopes=openid,profile,email" in out
    assert "url=https://idp.example.com/auth?response_type=code" in out
    assert "nonce=nc-42" in out
    assert "token parts=3 len=237" in out
    assert "verify ok=True sub=user-1 nonce=nc-42" in out
    assert "wrong nonce -> False nonce mismatch" in out
    assert "wrong iss -> False iss mismatch" in out
    assert "far-future now -> False expired" in out
    assert "tampered -> False bad_signature" in out
    assert "at_hash=w-EIkXOFVbCf9km_xa1oAA len=22" in out
    assert "logout=https://idp.example.com/logout?id_token_hint=idt-hint" in out
    assert "PINNED_VECTORS: disco=issuer+authurl" in out


def test_oidc_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "oidc_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
