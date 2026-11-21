"""
Regression test for examples/stomp_tutorial.ltl (stdlib/stomp tutorial companion).
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


def test_stomp_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "stomp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB STOMP TUTORIAL ===" in out
    assert "esc: a\\cb\\\\c\\nd\\re" in out
    assert "round-trip equal: True" in out
    assert "SEND\\ndestination:/queue/orders\\ncontent-type:text/plain\\ncontent-length:8\\n\\norder-42<NUL>" in out
    assert "CONNECT\\naccept-version:1.2\\nhost:broker.example.com\\nlogin:alice\\npasscode:s3cret\\nheart-beat:0,0\\n\\n<NUL>" in out
    assert "command=MESSAGE body=hello world consumed=99" in out
    assert "headers=4 first=destination=/queue/orders" in out
    assert "after 3 newlines: command=MESSAGE" in out
    assert "missing NUL -> True" in out
    assert "BEGIN\\ntransaction:tx-1\\n\\n<NUL>" in out
    assert "COMMIT\\ntransaction:tx-1\\n\\n<NUL>" in out
    assert "PINNED_VECTORS: esc=a\\c\\\\n\\rd roundtrip=true send=SEND+dest+len+NUL conn=CONNECT+accept-version parse=MESSAGE+007+11+consumed hb_skip=3 inc=nil" in out


def test_stomp_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "stomp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
