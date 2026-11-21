"""
Regression tests for stdlib/hash.ltl.

Every function used char_code() (missing builtin -> NameError) except
combine() which used xor() (also missing) and '/' (float).  Now uses
ord(), '^', and int().  Values pinned against independent references.
"""
from __future__ import annotations

import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "hash.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_fnv1a_32_reference():
    ns = _load()
    # Independent FNV-1a 32 reference for "abc"
    h = 2166136261
    for ch in "abc":
        h ^= ord(ch)
        h = (h * 16777619) % 4294967296
    assert ns["fnv1a_32"]("abc") == h == 440920331
    assert ns["fnv1a_32"]("") == 2166136261


def test_djb2_reference():
    ns = _load()
    h = 5381
    for ch in "abc":
        h = (h * 33 + ord(ch)) % 4294967296
    assert ns["djb2"]("abc") == h == 193485963


def test_checksums():
    ns = _load()
    assert ns["checksum8"]("abc") == 38  # 97+98+99 = 294 % 256
    assert ns["adler32"]("abc") == zlib.adler32(b"abc") == 38600999
    # fletcher16 pinned (module's own mod-255 variant)
    assert ns["fletcher16"]("abc") == 19495


def test_combine_bucket_hash_list():
    ns = _load()
    # boost-style combine: h1 ^ (h2 + 2654435769 + h1*64 + h1/4)
    assert ns["combine"](1, 2) == (1 ^ (2 + 2654435769 + 64 + 0))
    assert ns["bucket"]("key", 10) == ns["fnv1a_32"]("key") % 10
    assert ns["hash_list"](["a", "b"]) == ns["combine"](
        ns["combine"](0, ns["fnv1a_32"]("a")), ns["fnv1a_32"]("b"))
