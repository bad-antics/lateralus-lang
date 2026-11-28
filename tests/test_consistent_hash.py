"""
tests/test_consistent_hash.py - Regression test for consistent_hash binary search midpoints (fixes #919)
"""
import sys
import types
import pytest
from lateralus_lang.lexer import Lexer
from lateralus_lang.parser import Parser
from lateralus_lang.codegen.python import transpile_to_python

def test_consistent_hash_transpile_and_odd_midpoint_lookup():
    sys.modules['hash'] = types.ModuleType('hash')

    def hash_fnv1a_64(s):
        h = 0xcbf29ce484222325
        for b in (s.encode('utf-8') if isinstance(s, str) else bytes(s)):
            h ^= b
            h = (h * 0x100000001b3) & 0xffffffffffffffff
        return h

    import builtins
    builtins.hash_fnv1a_64 = hash_fnv1a_64

    with open('stdlib/consistent_hash.ltl') as f:
        src = f.read()

    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    py_code = transpile_to_python(program)

    ch_mod = types.ModuleType('consistent_hash')
    exec(py_code, ch_mod.__dict__)

    # Test ring with 3 nodes x 3 vnodes = 9 points (odd count, produces fractional midpoints with /)
    ring = ch_mod.new_ring(3)
    ch_mod.add_node(ring, 'server-alpha')
    ch_mod.add_node(ring, 'server-beta')
    ch_mod.add_node(ring, 'server-gamma')

    assert ch_mod.ring_size(ring) == 9

    # Look up multiple keys ensuring odd midpoints never raise TypeError
    for i in range(100):
        key = f"cache_key_user_{i}"
        node = ch_mod.lookup(ring, key)
        assert node in ['server-alpha', 'server-beta', 'server-gamma']

    # Test lookup_n
    replicas = ch_mod.lookup_n(ring, "partition_key", 2)
    assert len(replicas) == 2
    assert replicas[0] != replicas[1]
