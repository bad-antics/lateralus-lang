"""
Regression test for examples/quic_tutorial.ltl (stdlib/quic tutorial companion).
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


def test_quic_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "quic_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB QUIC TUTORIAL ===" in out
    assert "63 -> 1 bytes, roundtrip=True" in out
    assert "1073741824 -> 8 bytes, roundtrip=True" in out
    assert "long:  form=1 fixed=1 type=0 (Initial=0)" in out
    assert "short: form=0 fixed=1 spin=0 key_phase=1" in out
    assert "type=0 version=1 length=50" in out
    assert "dcid=[1, 2, 3, 4, 5, 6, 7, 8] scid=[9, 10] token=[]" in out
    assert "payload_offset=19" in out
    assert "spin=0 key_phase=1 dcid=[11, 22, 33, 44, 55, 66, 77, 88]" in out
    assert "payload_offset=9" in out
    assert "PADDING=0x00 PING=0x01 ACK=0x02 CRYPTO=0x06 STREAM base=0x08 CONN_CLOSE=0x1C" in out
    assert "stream(off,len,fin)=0x0F stream(fin only)=0x09" in out
    assert "PINNED_VECTORS: vi63=1B vi64=2B vi16k=4B vi1g=8B hdr=11000011 type0 spinhdr=01000101 dcid=1..8 payloadoff=19 tag_stream_all=0x0f tag_stream_fin=0x09" in out


def test_quic_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "quic_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
