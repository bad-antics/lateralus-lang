"""
Regression test for examples/mqtt5_tutorial.ltl (stdlib/mqtt5 tutorial companion).
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


def test_mqtt5_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "mqtt5_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB MQTT5 TUTORIAL ===" in out
    assert "128 -> 8001" in out
    assert "16383 -> ff7f" in out
    assert "2097151 -> ffff7f" in out
    assert "dec(300)=300 next=2" in out
    assert "utf8(\"MQTT\")=00044d515454" in out
    assert "dec_utf8=sensors/temp next=14" in out
    assert "prop_u8(session-expiry,30)=111e" in out
    assert "prop_utf8(content-type,json)=0300046a736f6e" in out
    assert "prop_user(tenant,acme)=26000674656e616e74000461636d65" in out
    assert "len=45 hex=102b00044d51545405c2003c09210a0300046a736f6e00066465762d30310005616c6963650006733363726574" in out
    assert "hex=322a0014686f6d652f6c6976696e67726f6f6d2f74656d70002a0d03000a746578742f706c61696e32312e35" in out
    assert "sub hex=821c000700000b686f6d652f2b2f74656d70010008616c657274732f2302" in out
    assert "pingreq=c000" in out
    assert "disconnect(0x00)=e0020000" in out
    assert "pkt1 type=12 consumed=2" in out
    assert "pkt2 type=3 flags=2 remaining=42" in out
    assert "truncated -> True" in out
    assert "PINNED_VECTORS: vi128=8001" in out


def test_mqtt5_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "mqtt5_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
