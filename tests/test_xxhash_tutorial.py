"""
Regression test for examples/xxhash_tutorial.ltl and stdlib/xxhash.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces the canonical
XXH64 / FNV-1a test vectors (cross-checked against an independent reference
implementation of the xxHash spec below).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PINNED_LINE = (
    "PINNED_VECTORS: xxh64_empty=17241709254077376921 "
    "xxh64_a=15154266338359012955 "
    "xxh64_abc=4952883123889572249 "
    "xxh64_abc_seed1=13738734796240226568 "
    "xxh64_hello=1836616885408546661 "
    "xxh64_long=9869445744007518376 "
    "fnv_empty=14695981039346656037 "
    "fnv_a=12638187200555641996 "
    "fnv_lateralus=18229159603426106184"
)


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


def test_xxhash_tutorial_execution():
    res = _run_cli("run", str(REPO_ROOT / "examples" / "xxhash_tutorial.ltl"))
    stdout = res.stdout

    assert "=== LATERALUS STDLIB XXHASH TUTORIAL ===" in stdout

    # Step 1 — canonical spec vectors, seed 0
    assert "xxh64('')    = 17241709254077376921" in stdout  # 0xEF46DB3751D8E999
    assert "xxh64('a')   = 15154266338359012955" in stdout  # 0xD24EC4F1A98C6E5B
    assert "xxh64('abc') = 4952883123889572249" in stdout   # 0x44BC2CF5AD770999

    # Step 2 — tail paths and the >= 32 byte stripe loop
    assert "xxh64('Hello, xxHash!') = 1836616885408546661" in stdout
    assert "xxh64(72-byte string)   = 9869445744007518376" in stdout
    assert "hash64([97, 98, 99]) == hash64_str('abc'): True" in stdout

    # Step 3 — seeds move the input to a different hash space
    assert "xxh64('abc', seed=1) = 13738734796240226568" in stdout
    assert "seeds differ: True" in stdout

    # Step 4 — FNV-1a: empty input is exactly the offset basis
    assert "fnv1a('')          = 14695981039346656037" in stdout  # 0xCBF29CE484222325
    assert "fnv1a('a')         = 12638187200555641996" in stdout  # 0xAF63DC4C8601EC8C
    assert "fnv1a('lateralus') = 18229159603426106184" in stdout

    # Step 5 — determinism / avalanche sanity for cache keys
    assert "key('GET /users/42') twice, identical: True" in stdout
    assert "key('GET /users/43') differs:          True" in stdout

    assert PINNED_LINE in stdout


def test_xxhash_tutorial_typecheck():
    res = _run_cli("check", str(REPO_ROOT / "examples" / "xxhash_tutorial.ltl"))
    assert "OK" in res.stdout


# ── Independent XXH64 reference (from the official xxHash spec) ─────
# Used to prove the pinned vectors above are the spec values, not just
# whatever the tutorial program happens to print.

_MASK = 0xFFFFFFFFFFFFFFFF
_P1, _P2, _P3, _P4, _P5 = (
    0x9E3779B185EBCA87,
    0xC2B2AE3D27D4EB4F,
    0x165667B19E3779F9,
    0x85EBCA77C2B2AE63,
    0x27D4EB2F165667C5,
)


def _rotl(x: int, r: int) -> int:
    return ((x << r) | (x >> (64 - r))) & _MASK


def _round(acc: int, inp: int) -> int:
    acc = (acc + inp * _P2) & _MASK
    return (_rotl(acc, 31) * _P1) & _MASK


def _merge(acc: int, val: int) -> int:
    acc ^= _round(0, val)
    return (acc * _P1 + _P4) & _MASK


def _xxh64(data: bytes, seed: int = 0) -> int:
    n = len(data)
    i = 0
    if n >= 32:
        v1 = (seed + _P1 + _P2) & _MASK
        v2 = (seed + _P2) & _MASK
        v3 = seed & _MASK
        v4 = (seed - _P1) & _MASK
        while i + 32 <= n:
            v1 = _round(v1, int.from_bytes(data[i : i + 8], "little"))
            v2 = _round(v2, int.from_bytes(data[i + 8 : i + 16], "little"))
            v3 = _round(v3, int.from_bytes(data[i + 16 : i + 24], "little"))
            v4 = _round(v4, int.from_bytes(data[i + 24 : i + 32], "little"))
            i += 32
        h = (_rotl(v1, 1) + _rotl(v2, 7) + _rotl(v3, 12) + _rotl(v4, 18)) & _MASK
        h = _merge(h, v1)
        h = _merge(h, v2)
        h = _merge(h, v3)
        h = _merge(h, v4)
    else:
        h = (seed + _P5) & _MASK
    h = (h + n) & _MASK
    while i + 8 <= n:
        h = _rotl(h ^ _round(0, int.from_bytes(data[i : i + 8], "little")), 27)
        h = (h * _P1 + _P4) & _MASK
        i += 8
    if i + 4 <= n:
        h ^= (int.from_bytes(data[i : i + 4], "little") * _P1) & _MASK
        h = _rotl(h, 23)
        h = (h * _P2 + _P3) & _MASK
        i += 4
    while i < n:
        h ^= (data[i] * _P5) & _MASK
        h = (_rotl(h, 11) * _P1) & _MASK
        i += 1
    h ^= h >> 33
    h = (h * _P2) & _MASK
    h ^= h >> 29
    h = (h * _P3) & _MASK
    h ^= h >> 32
    return h


def _fnv1a(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h = ((h ^ b) * 0x100000001B3) & _MASK
    return h


def test_xxhash_pinned_vectors_match_spec():
    # Every value pinned by the tutorial must equal the spec reference.
    assert _xxh64(b"") == 17241709254077376921
    assert _xxh64(b"a") == 15154266338359012955
    assert _xxh64(b"abc") == 4952883123889572249
    assert _xxh64(b"abc", seed=1) == 13738734796240226568
    assert _xxh64(b"Hello, xxHash!") == 1836616885408546661
    assert _xxh64(b"lateralus" * 8) == 9869445744007518376
    assert _fnv1a(b"") == 14695981039346656037
    assert _fnv1a(b"a") == 12638187200555641996
    assert _fnv1a(b"lateralus") == 18229159603426106184


if __name__ == "__main__":
    test_xxhash_tutorial_execution()
    test_xxhash_tutorial_typecheck()
    test_xxhash_pinned_vectors_match_spec()
    print("PASS: 3/3 tests passed successfully")
