"""
tests/test_blake2s_tutorial.py - Comprehensive verification for stdlib/blake2s.ltl
Tests RFC 7693 canonical test vectors (empty string, short string, Fox sentence),
keyed MAC calculation, variable digest truncation, and hex formatting.
"""
from pathlib import Path
import hashlib
from lateralus_lang.compiler import Compiler, Target

def test_blake2s_rfc7693_vectors():
    blake2s_src = Path("stdlib/blake2s.ltl").read_text(encoding="utf-8")
    driver = r"""
let h_empty = hash256([])
let hex_empty = to_hex(h_empty)

let h_abc = hash256_str("abc")
let hex_abc = to_hex(h_abc)

let h_fox = hash256_str("The quick brown fox jumps over the lazy dog")
let hex_fox = to_hex(h_fox)
"""
    c = Compiler()
    res = c.compile_source(blake2s_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["hex_empty"] == hashlib.blake2s(b"").hexdigest()
    assert ns["hex_abc"] == hashlib.blake2s(b"abc").hexdigest()
    assert ns["hex_fox"] == hashlib.blake2s(b"The quick brown fox jumps over the lazy dog").hexdigest()

def test_blake2s_keyed_and_truncation():
    blake2s_src = Path("stdlib/blake2s.ltl").read_text(encoding="utf-8")
    driver = r"""
let msg = [84, 104, 101, 32, 113, 117, 105, 99, 107]
let k = [107, 101, 121]
let h_keyed = hash(msg, k, 32)
let hex_keyed = to_hex(h_keyed)

let h_trunc = hash(msg, [], 16)
let hex_trunc = to_hex(h_trunc)
let trunc_len = len(h_trunc)
"""
    c = Compiler()
    res = c.compile_source(blake2s_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    expected_keyed = hashlib.blake2s(b"The quick", key=b"key").hexdigest()
    assert ns["hex_keyed"] == expected_keyed

    assert ns["trunc_len"] == 16
    assert len(ns["hex_trunc"]) == 32
    assert ns["hex_trunc"] == hashlib.blake2s(b"The quick", digest_size=16).hexdigest()
