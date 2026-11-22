"""
Regression test for examples/parquet_tutorial.ltl (stdlib/parquet tutorial companion).
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


def test_parquet_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "parquet_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB PARQUET TUTORIAL ===" in out
    assert "enc_plain=0 enc_rle=3 enc_rle_dict=8" in out
    assert "comp_uncompressed=0 comp_snappy=1 comp_zstd=6" in out
    assert "type_int64=2 type_byte_array=6 type_fixed_len_byte_array=7" in out
    assert "magic=[80,65,82,49]" in out
    assert "file_len=20 expect=20" in out
    assert "footer_len=3" in out
    assert "footer_offset=9" in out
    assert "roundtrip=True" in out
    assert "bad_magic_rejected=True" in out
    assert "len3=[3,0,0,0]" in out
    assert "len300=[44,1,0,0]" in out
    assert "zz_i32(1)=2 zz_i32(-1)=1 zz_i32(64)=128" in out
    assert "uvarint(0)=[0]" in out
    assert "uvarint(127)=[127]" in out
    assert "uvarint(300)=[172,2]" in out
    assert "varint_i32(-2)=[3]" in out
    assert "varint_i32(150)=[172,2]" in out
    assert "binary[3]=[3,65,66,67]" in out
    assert "string_ab=[2,97,98]" in out
    assert "page num_values=1000 enc=2 def_enc=3 rep_enc=4" in out
    assert "PINNED_VECTORS: magic=80,65,82,49 file_len=20 footer_len=3 footer_off=9" in out


def test_parquet_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "parquet_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
