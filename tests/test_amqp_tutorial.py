"""
Regression test for examples/amqp_tutorial.ltl (stdlib/amqp tutorial companion).
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


def test_amqp_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "amqp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB AMQP TUTORIAL ===" in out
    assert "hex=414d515000000901 len=8" in out
    assert "enc_u32(0x01020304)=01020304" in out
    assert "dec -> 16909060 consumed=4" in out
    assert "short_str len byte=10" in out
    assert "frame hex=01000100000005000a0028ffce" in out
    assert "parse: type=1 channel=1 payload=000a0028ff consumed=13" in out
    assert "truncated -> True" in out
    assert "PLAIN auth hex=006775657374006775657374" in out
    assert "tune-ok hex=000000020000003c" in out
    assert "open hex=012f0000" in out
    assert "total bytes=72" in out
    assert "frame1 type=1 payload=003c00280000066f7264657273096f726465722e6e657701" in out
    assert "frame2 type=2 header hex=003c0000000000000000000a0000" in out
    assert "frame3 type=3 body=68656c6c6f2d616d7170" in out
    assert "PINNED_VECTORS: ph=414d515000000901" in out


def test_amqp_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "amqp_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
