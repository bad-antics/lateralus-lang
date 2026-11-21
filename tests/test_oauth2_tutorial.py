"""
Regression test for examples/oauth2_tutorial.ltl (stdlib/oauth2 tutorial companion).
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


def test_oauth2_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "oauth2_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB OAUTH2 TUTORIAL ===" in out
    assert "pct(\"a b&c=d\")=a%20b%26c%3Dd" in out
    assert "pct(\"~ok-._\")=~ok-._" in out
    assert "form=grant_type=authorization_code&code=abc%20123" in out
    assert "challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM" in out
    assert "matches RFC7636=True" in out
    assert "url=https://auth.example.com/authorize?response_type=code" in out
    assert "code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM" in out
    assert "code_challenge_method=S256" in out
    assert "grant_type=authorization_code&code=auth-code-1" in out
    assert "code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" in out
    assert "refresh=grant_type=refresh_token&refresh_token=rt-9" in out
    assert "revoke=token=at-9" in out
    assert "at=eyJ... type=bearer expires=3600" in out
    assert "unknown key kept? False" in out
    assert "state ok=True bad=False" in out
    assert "PINNED_VECTORS: pct=a%20b%26c%3Dd" in out


def test_oauth2_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "oauth2_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
