"""
Regression tests for stdlib/hkdf.ltl.

The previous revision called `crypto_hmac()`, which is not defined
anywhere in the repo — the module could not run.  This revision is
self-contained (pure-Lateralus SHA-256/HMAC over byte lists) and is
verified here against the official RFC 5869 test vectors.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

RFC5869_TC1_OKM = (
    "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
    "34007208d5b887185865"
)
RFC5869_TC1_PRK = (
    "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
)
RFC5869_TC2_OKM = (
    "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c"
    "59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71"
    "cc30c58179ec3e87c14c01d5c1f3434f1d87"
)


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "hkdf.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def _hex(bs: list) -> str:
    return "".join(f"{b:02x}" for b in bs)


def test_hkdf_rfc5869_test_case_1():
    ns = _load()
    ikm = [0x0B] * 22
    salt = list(range(13))
    info = list(range(0xF0, 0xFA))
    prk = ns["extract"](salt, ikm)
    assert _hex(prk) == RFC5869_TC1_PRK
    okm = ns["derive_key"](salt, ikm, info, 42)
    assert _hex(okm) == RFC5869_TC1_OKM
    assert len(okm) == 42


def test_hkdf_rfc5869_test_case_2():
    ns = _load()
    ikm = list(range(80))
    salt = [(i + 0x60) % 256 for i in range(80)]
    info = [(i + 0xB0) % 256 for i in range(80)]
    okm = ns["derive_key"](salt, ikm, info, 82)
    assert _hex(okm) == RFC5869_TC2_OKM
    assert len(okm) == 82


def test_hkdf_edge_cases():
    ns = _load()
    ikm = [0x0B] * 22
    salt = list(range(13))
    info = list(range(0xF0, 0xFA))
    # empty salt -> HASHLEN zero bytes per RFC 5869
    assert len(ns["derive_key"]([], ikm, info, 16)) == 16
    # empty info
    assert len(ns["derive_key"](salt, ikm, [], 32)) == 32
    # n = 255 blocks is the max (255 * 32 = 8160 bytes)
    assert len(ns["expand"](ns["extract"](salt, ikm), info, 8160)) == 8160
    # n > 255 -> empty per RFC 5869
    assert ns["expand"](ns["extract"](salt, ikm), info, 8192) == []
    # derive_many
    many = ns["derive_many"](ns["extract"](salt, ikm), [0xAA], 16, 3)
    assert len(many) == 3 and all(len(k) == 16 for k in many)
