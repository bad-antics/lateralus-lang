"""
Regression test for examples/encoding_tutorial.ltl (stdlib/encoding tutorial companion).
Asserts the executable tutorial runs cleanly and produces exact pinned vectors.
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


def test_encoding_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "encoding_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB ENCODING TUTORIAL ===" in out
    assert "STEP 1: hex_encode = 68656c6c6f" in out
    assert "STEP 1: hex_decode round-trip: [104, 101, 108, 108, 111]" in out
    assert "STEP 2: base64_encode('hello') = aGVsbG8=" in out
    assert "STEP 2: base64_encode('Hello') = SGVsbG8=" in out
    assert "STEP 2: base64_decode('aGVsbG8='): [104, 101, 108, 108, 111]" in out
    assert "STEP 2c: base64_decode('SGVsbG8=') = 'Hello': [72, 101, 108, 108, 111]" in out
    assert "STEP 2b: base64_decode('aGVsbG8gd29ybGQ=') -> 'hello world': [104, 101, 108, 108, 111, 32, 119, 111, 114, 108, 100]" in out
    assert "STEP 3: url_encode('a b&c=d') = a%20b%26c%3Dd" in out
    assert "STEP 3: url_encode('100% sure?') = 100%25%20sure%3F" in out
    assert "STEP 3: url_decode round-trip = a b&c=d" in out
    assert "STEP 3b: url_decode('a+b%20c') = 'a b c'" in out
    assert "STEP 4: base64_encode([0]) = 'AA=='" in out
    assert "STEP 4: base64_encode([255,255,255]) = '////'" in out
    assert "PINNED_VECTORS: hex=68656c6c6f b64=aGVsbG8= b64Hello=SGVsbG8= b64world=aGVsbG8gd29ybGQ= url=a%20b%26c%3Dd" in out


def test_encoding_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "encoding_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
