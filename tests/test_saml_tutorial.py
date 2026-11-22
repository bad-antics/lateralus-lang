"""
Regression test for examples/saml_tutorial.ltl (stdlib/saml tutorial companion).
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


def test_saml_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "saml_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB SAML TUTORIAL ===" in out
    assert "a&lt;b&gt;&amp;&quot;&apos;c" in out
    assert "has_id=True" in out
    assert "has_dest=True" in out
    assert "has_acs=True" in out
    assert "has_nameidpolicy=True" in out
    assert "starts=True" in out
    assert "has_samlrequest=True" in out
    assert "has_relay=True" in out
    assert "b64_prefix=PHNhbWxwOkF1dGhuUmVxdWVz" in out
    assert "form_action=True" in out
    assert "has_hidden=True" in out
    assert "has_noscript=True" in out
    assert "b64_starts=PHNhbWxwOkF1dGhu len=696" in out
    assert "is_logout=True" in out
    assert "has_nameid=True" in out
    assert "has_sessionindex=True" in out
    assert "id=r-1 in_response_to=_req-42" in out
    assert "name_id=alice@example.com" in out
    assert "is_success=True" in out
    assert "assertion_len=128" in out
    assert "PINNED_VECTORS: esc=a&lt;b&gt;&amp;&quot;&apos;c authn_id=_req-42 b64_prefix=PHNhbWxwOkF1" in out


def test_saml_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "saml_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
