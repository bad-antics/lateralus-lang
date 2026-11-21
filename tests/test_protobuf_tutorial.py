"""
Regression test for examples/protobuf_tutorial.ltl (stdlib/protobuf tutorial companion).
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


def test_protobuf_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "protobuf_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB PROTOBUF TUTORIAL ===" in out
    assert "varint(300)=ac02" in out
    assert "dec -> 300 next=2" in out
    assert "zz(-1)=1 zz_decode(1)=-1" in out
    assert "zz(-2)=3 zz_decode(3)=-2" in out
    assert "field 5 varint tag=28" in out
    assert "field 16 bytes tag=8201" in out
    assert "dec tag(300,bytes) -> fn=300 wt=2" in out
    assert "int32 f1=150=089601" in out
    assert "sint32 f2=-5=1009" in out
    assert "bool f3=true=1801" in out
    assert "string f4=\"hi\"=22026869" in out
    assert "fixed32 f5=0x01020304=2d04030201" in out
    assert "fixed64 f6=0x0102030405060708=310807060504030201" in out
    assert "msg len=25 hex=0a05616c696365102a180122070a03416e6e101e2d07000000" in out
    assert "f1=alice f2=42 f3=1" in out
    assert "nested f1=Ann f2=30" in out
    assert "field1 fn=9 val=1 next=2" in out
    assert "field2 fn=10 val=x next=5" in out
    assert "PINNED_VECTORS: varint300=ac02" in out


def test_protobuf_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "protobuf_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
