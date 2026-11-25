"""
Unit tests validating BLAKE2s pinned test vectors against RFC 7693.
"""
from lateralus_lang.crypto_engine import blake2s

def test_rfc7693_empty_string():
    expected = "69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9"
    assert blake2s("") == expected
    assert blake2s(b"") == expected

def test_rfc7693_abc():
    expected = "508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"
    assert blake2s("abc") == expected
    assert blake2s(b"abc") == expected

def test_rfc7693_fox():
    expected = "606beeec743ccbeff6cbcdf5d5302aa855c256c29b88c8ed331ea1a6bf3c8812"
    msg = "The quick brown fox jumps over the lazy dog"
    assert blake2s(msg) == expected

def test_blake2s_digest_sizes():
    # 16-byte (128-bit) truncation
    h16 = blake2s("abc", digest_size=16)
    assert len(h16) == 32 # 16 bytes = 32 hex chars
    # 32-byte (256-bit) standard
    h32 = blake2s("abc", digest_size=32)
    assert len(h32) == 64
