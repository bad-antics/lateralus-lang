"""
Regression test for examples/hkdf_tutorial.ltl.
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


def test_hkdf_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "hkdf_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB HKDF TUTORIAL" in out
    # SHA-256 known answers
    assert "empty=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in out
    assert "abc=ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in out
    # HMAC RFC 4231 case 1
    assert "rfc4231_1=b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7" in out
    # HKDF RFC 5869 test cases
    assert "prk=077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5" in out
    assert "okm=3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865" in out
    assert "okm_len=42" in out
    assert out.count("okm2=b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71cc30c58179ec3e87c14c01d5c1f3434f1d87") == 1
    assert "okm2_len=82" in out
    # edge cases
    assert "empty_salt_len=16" in out
    assert "empty_info_len=32" in out
    assert "n255_len=8160" in out
    assert "over255_len=0" in out
    assert "many_count=3" in out
    assert "PINNED_VECTORS" in out


def test_hkdf_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "hkdf_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
