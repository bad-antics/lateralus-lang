"""
tests/test_bloom.py - Regression test for bloom filter bit_set / bit_test word index division (fixes #924)
"""
import sys
import types
import pytest
from lateralus_lang.lexer import Lexer
from lateralus_lang.parser import Parser
from lateralus_lang.codegen.python import transpile_to_python

def test_bloom_filter_transpile_and_bit_operations():
    # Setup mocks for hash functions expected by stdlib/bloom.ltl
    import builtins

    h_mod = types.ModuleType('hash')
    sys.modules['hash'] = h_mod

    def fnv1a_32(s):
        h = 0x811c9dc5
        for b in (s.encode('utf-8') if isinstance(s, str) else bytes(s)):
            h ^= b
            h = (h * 0x01000193) & 0xffffffff
        return h

    def fnv1a_64(s):
        h = 0xcbf29ce484222325
        for b in (s.encode('utf-8') if isinstance(s, str) else bytes(s)):
            h ^= b
            h = (h * 0x100000001b3) & 0xffffffffffffffff
        return h

    h_mod.fnv1a_32 = fnv1a_32
    h_mod.fnv1a_64 = fnv1a_64
    builtins.hash_fnv1a_32 = fnv1a_32
    builtins.hash_fnv1a_64 = fnv1a_64

    with open('stdlib/bloom.ltl') as f:
        src = f.read()

    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    py_code = transpile_to_python(program)

    bl_mod = types.ModuleType('bloom')
    exec(py_code, bl_mod.__dict__)

    # Test filter with 128 bits and 3 hashes (as in minimal reproducer #924)
    flt = bl_mod.new_filter(128, 3)
    positions = bl_mod.hash_positions(flt, "hello")
    # Positions: e.g. [43, 54, 65] which previously threw TypeError on 43 / 32
    assert len(positions) == 3

    # Add items - should never raise TypeError
    bl_mod.add(flt, "hello")
    bl_mod.add(flt, "world")
    bl_mod.add(flt, "lateralus")

    assert bl_mod.contains_key(flt, "hello") is True
    assert bl_mod.contains_key(flt, "world") is True
    assert bl_mod.contains_key(flt, "lateralus") is True

    # Test non-existent keys
    assert bl_mod.contains_key(flt, "non_existent_key_xyz_12345") is False

    # Test optimal params and 100 insertions
    opt = bl_mod.optimal_params(100, 10)
    large_flt = bl_mod.new_filter(opt[0], opt[1])
    for i in range(100):
        bl_mod.add(large_flt, f"user_key_{i}")

    for i in range(100):
        assert bl_mod.contains_key(large_flt, f"user_key_{i}") is True
