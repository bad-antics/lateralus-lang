"""
tests/test_crypto_engine.py — Tests for the LATERALUS Crypto Engine
"""
import pytest

from lateralus_lang.crypto_engine import (
    blake2b,
    from_base64,
    from_hex,
    hash_data,
    hash_password,
    hmac_sign,
    hmac_verify,
    lbe_decode,
    lbe_encode,
    md5,
    random_bytes,
    random_token,
    random_urlsafe,
    sha256,
    sha512,
    sign_data,
    to_base64,
    to_hex,
    verify_password,
    xor_decrypt,
    xor_encrypt,
)


class TestHashing:
    def test_sha256_known_value(self):
        # Known SHA-256 hash of empty string
        result = sha256("")
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_sha256_bytes(self):
        result = sha256(b"hello")
        assert len(result) == 64

    def test_sha512(self):
        result = sha512("test")
        assert len(result) == 128

    def test_blake2b(self):
        result = blake2b("test")
        assert len(result) == 64  # 32 bytes = 64 hex chars

    def test_md5(self):
        result = md5("hello")
        assert len(result) == 32

    def test_hash_data_dispatch(self):
        r1 = hash_data("test", "sha256")
        r2 = sha256("test")
        assert r1 == r2

    def test_hash_data_invalid_algo(self):
        with pytest.raises(ValueError, match="Unsupported"):
            hash_data("test", "sha3")


class TestHMAC:
    def test_sign_and_verify(self):
        key = "secret"
        msg = "important data"
        sig = hmac_sign(key, msg)
        assert hmac_verify(key, msg, sig)

    def test_verify_fails_on_tamper(self):
        key = "secret"
        sig = hmac_sign(key, "original")
        assert not hmac_verify(key, "tampered", sig)

    def test_bytes_key(self):
        key = b"binary-key"
        msg = b"binary-msg"
        sig = hmac_sign(key, msg)
        assert hmac_verify(key, msg, sig)


class TestPassword:
    def test_hash_and_verify(self):
        stored = hash_password("my-password")
        assert verify_password("my-password", stored)

    def test_wrong_password(self):
        stored = hash_password("correct")
        assert not verify_password("wrong", stored)

    def test_different_salts(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1["salt"] != h2["salt"]  # Different random salts
        assert h1["hash"] != h2["hash"]


class TestRandomTokens:
    def test_token_length(self):
        token = random_token(16)
        assert len(token) == 32  # 16 bytes = 32 hex chars

    def test_urlsafe(self):
        token = random_urlsafe(16)
        assert isinstance(token, str)
        # URL-safe tokens don't contain + or /
        assert "+" not in token

    def test_random_bytes(self):
        data = random_bytes(32)
        assert len(data) == 32
        assert isinstance(data, bytes)

    def test_uniqueness(self):
        tokens = {random_token(16) for _ in range(100)}
        assert len(tokens) == 100  # All unique


class TestEncoding:
    def test_base64_roundtrip(self):
        original = "Hello, LATERALUS!"
        encoded = to_base64(original)
        decoded = from_base64(encoded)
        assert decoded == original

    def test_hex_roundtrip(self):
        original = "test data"
        encoded = to_hex(original)
        decoded = from_hex(encoded)
        assert decoded == original

    def test_base64_bytes(self):
        data = b"\x00\x01\x02\xff"
        encoded = to_base64(data)
        decoded = from_base64(encoded)
        assert decoded == data


class TestXOR:
    def test_roundtrip(self):
        data = b"secret message"
        key = b"key123"
        encrypted = xor_encrypt(data, key)
        decrypted = xor_decrypt(encrypted, key)
        assert decrypted == data

    def test_different_key_fails(self):
        data = b"secret"
        encrypted = xor_encrypt(data, b"key1")
        decrypted = xor_decrypt(encrypted, b"key2")
        assert decrypted != data


class TestLBE:
    def test_null(self):
        assert lbe_decode(lbe_encode(None)) is None

    def test_bool(self):
        assert lbe_decode(lbe_encode(True)) is True
        assert lbe_decode(lbe_encode(False)) is False

    def test_int(self):
        assert lbe_decode(lbe_encode(42)) == 42
        assert lbe_decode(lbe_encode(-100)) == -100
        assert lbe_decode(lbe_encode(0)) == 0

    def test_float(self):
        result = lbe_decode(lbe_encode(3.14))
        assert abs(result - 3.14) < 1e-10

    def test_string(self):
        assert lbe_decode(lbe_encode("hello")) == "hello"
        assert lbe_decode(lbe_encode("")) == ""
        assert lbe_decode(lbe_encode("Unicode: 日本語")) == "Unicode: 日本語"

    def test_list(self):
        data = [1, "two", 3.0, True, None]
        assert lbe_decode(lbe_encode(data)) == data

    def test_nested_list(self):
        data = [[1, 2], [3, [4, 5]]]
        assert lbe_decode(lbe_encode(data)) == data

    def test_map(self):
        data = {"name": "LATERALUS", "version": 1, "active": True}
        assert lbe_decode(lbe_encode(data)) == data

    def test_compressed(self):
        data = {"key": "value" * 100}
        encoded = lbe_encode(data, compress=True)
        assert lbe_decode(encoded) == data

    def test_bigint(self):
        big = 2**128
        assert lbe_decode(lbe_encode(big)) == big

    def test_invalid_magic(self):
        with pytest.raises(ValueError, match="Not a valid LBE"):
            lbe_decode(b"INVALID DATA")


class TestSignedPayload:
    def test_sign_and_verify(self):
        key = "my-secret-key"
        payload = sign_data("important data", key)
        assert payload.verify(key)

    def test_tampered_fails(self):
        key = "my-secret-key"
        payload = sign_data("important data", key)
        payload.data = b"tampered"
        assert not payload.verify(key)

    def test_serialization_roundtrip(self):
        key = "test-key"
        original = sign_data("test data", key)
        serialized = original.to_bytes()
        restored = type(original).from_bytes(serialized)
        assert restored.verify(key)
        assert restored.data == original.data
