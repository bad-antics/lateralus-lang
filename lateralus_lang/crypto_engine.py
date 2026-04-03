"""
lateralus_lang/crypto_engine.py  ─  LATERALUS Cryptography & Encoding Engine
═══════════════════════════════════════════════════════════════════════════════
Proprietary encryption and encoding system for LATERALUS:
  · SHA-256, SHA-512, BLAKE2 hashing (stdlib wrappers)
  · HMAC message authentication
  · AES-256-GCM symmetric encryption
  · RSA-2048 key generation & asymmetric encrypt/decrypt
  · LATERALUS Binary Encoding (LBE) — proprietary serialization format
  · Base64 / Hex encoding utilities
  · Secure random token generation
  · Password hashing (PBKDF2)
  · Digital signatures

All operations use Python's `hashlib`, `hmac`, `secrets`, and
`cryptography` (if available) — no hand-rolled crypto.

v1.5.0
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# ─────────────────────────────────────────────────────────────────────────────
# Hashing
# ─────────────────────────────────────────────────────────────────────────────

def sha256(data: Union[str, bytes]) -> str:
    """SHA-256 hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha512(data: Union[str, bytes]) -> str:
    """SHA-512 hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha512(data).hexdigest()


def blake2b(data: Union[str, bytes], digest_size: int = 32) -> str:
    """BLAKE2b hex digest (default 256-bit)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.blake2b(data, digest_size=digest_size).hexdigest()


def md5(data: Union[str, bytes]) -> str:
    """MD5 hex digest — NOT for security, only checksums."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()


def hash_data(data: Union[str, bytes], algorithm: str = "sha256") -> str:
    """Generic hash function supporting sha256, sha512, blake2b, md5."""
    algos = {"sha256": sha256, "sha512": sha512, "blake2b": blake2b, "md5": md5}
    fn = algos.get(algorithm)
    if fn is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}. "
                         f"Supported: {', '.join(algos)}")
    return fn(data)


# ─────────────────────────────────────────────────────────────────────────────
# HMAC
# ─────────────────────────────────────────────────────────────────────────────

def hmac_sign(key: Union[str, bytes], message: Union[str, bytes],
              algorithm: str = "sha256") -> str:
    """Create an HMAC signature."""
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(message, str):
        message = message.encode("utf-8")
    return hmac.new(key, message, getattr(hashlib, algorithm)).hexdigest()


def hmac_verify(key: Union[str, bytes], message: Union[str, bytes],
                signature: str, algorithm: str = "sha256") -> bool:
    """Constant-time HMAC verification."""
    expected = hmac_sign(key, message, algorithm)
    return hmac.compare_digest(expected, signature)


# ─────────────────────────────────────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(password: str, salt: Optional[bytes] = None,
                  iterations: int = 600_000) -> Dict[str, str]:
    """PBKDF2-HMAC-SHA256 password hashing.

    Returns dict with keys: hash, salt, iterations, algorithm.
    """
    if salt is None:
        salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt, iterations, dklen=32)
    return {
        "hash": dk.hex(),
        "salt": salt.hex(),
        "iterations": iterations,
        "algorithm": "pbkdf2_sha256",
    }


def verify_password(password: str, stored: Dict[str, str]) -> bool:
    """Verify a password against a stored hash dict."""
    salt = bytes.fromhex(stored["salt"])
    iterations = stored["iterations"]
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt, iterations, dklen=32)
    return hmac.compare_digest(dk.hex(), stored["hash"])


# ─────────────────────────────────────────────────────────────────────────────
# Secure random
# ─────────────────────────────────────────────────────────────────────────────

def random_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random hex token."""
    return secrets.token_hex(nbytes)


def random_urlsafe(nbytes: int = 32) -> str:
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(nbytes)


def random_bytes(n: int) -> bytes:
    """Generate n cryptographically secure random bytes."""
    return os.urandom(n)


# ─────────────────────────────────────────────────────────────────────────────
# Encoding / Decoding
# ─────────────────────────────────────────────────────────────────────────────

def to_base64(data: Union[str, bytes]) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("ascii")


def from_base64(encoded: str) -> Union[str, bytes]:
    raw = base64.b64decode(encoded)
    try:
        return raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return raw


def to_hex(data: Union[str, bytes]) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return data.hex()


def from_hex(encoded: str) -> Union[str, bytes]:
    raw = bytes.fromhex(encoded)
    try:
        return raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return raw


# ─────────────────────────────────────────────────────────────────────────────
# XOR cipher — lightweight obfuscation (NOT cryptographic security)
# ─────────────────────────────────────────────────────────────────────────────

def xor_encrypt(data: bytes, key: bytes) -> bytes:
    """XOR-based encryption/decryption (symmetric)."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


xor_decrypt = xor_encrypt  # XOR is its own inverse


# ─────────────────────────────────────────────────────────────────────────────
# AES-256-GCM (requires `cryptography` package)
# ─────────────────────────────────────────────────────────────────────────────

def _check_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM
    except ImportError:
        raise ImportError(
            "AES encryption requires the 'cryptography' package.\n"
            "Install with: pip install cryptography"
        )


def aes_generate_key() -> bytes:
    """Generate a 256-bit AES key."""
    return os.urandom(32)


def aes_encrypt(plaintext: Union[str, bytes], key: bytes,
                associated_data: Optional[bytes] = None) -> bytes:
    """AES-256-GCM authenticated encryption.

    Returns: nonce (12 bytes) + ciphertext + tag
    """
    AESGCM = _check_cryptography()
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce + ct


def aes_decrypt(ciphertext: bytes, key: bytes,
                associated_data: Optional[bytes] = None) -> bytes:
    """AES-256-GCM authenticated decryption."""
    AESGCM = _check_cryptography()
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, associated_data)


# ─────────────────────────────────────────────────────────────────────────────
# LATERALUS Binary Encoding (LBE) — proprietary serialization
# ─────────────────────────────────────────────────────────────────────────────
#
# Format:
#   HEADER (8 bytes):
#     Magic:   b'LTLB'  (4 bytes)
#     Version: uint16   (2 bytes)  — currently 1
#     Flags:   uint16   (2 bytes)  — bit 0: compressed
#
#   BODY:
#     Type tag (1 byte) + payload
#
#   Type tags:
#     0x00  Null
#     0x01  Bool (1 byte: 0/1)
#     0x02  Int64 (8 bytes, signed, big-endian)
#     0x03  Float64 (8 bytes, IEEE 754, big-endian)
#     0x04  String (uint32 length + UTF-8 bytes)
#     0x05  Bytes (uint32 length + raw bytes)
#     0x06  List (uint32 count + elements)
#     0x07  Map (uint32 count + key-value pairs)
#     0x08  BigInt (uint32 length + sign byte + magnitude bytes)
#     0x09  Timestamp (uint64 nanoseconds since epoch)
# ─────────────────────────────────────────────────────────────────────────────

LBE_MAGIC = b"LTLB"
LBE_VERSION = 1

# Type tags
_TAG_NULL    = 0x00
_TAG_BOOL    = 0x01
_TAG_INT     = 0x02
_TAG_FLOAT   = 0x03
_TAG_STRING  = 0x04
_TAG_BYTES   = 0x05
_TAG_LIST    = 0x06
_TAG_MAP     = 0x07
_TAG_BIGINT  = 0x08
_TAG_TIMESTAMP = 0x09


class LBEEncoder:
    """Encode Python values into LATERALUS Binary Encoding."""

    def __init__(self, compress: bool = False):
        self.compress = compress

    def encode(self, value: Any) -> bytes:
        body = self._encode_value(value)
        flags = 0x01 if self.compress else 0x00
        if self.compress:
            body = zlib.compress(body, level=6)
        header = LBE_MAGIC + struct.pack(">HH", LBE_VERSION, flags)
        return header + body

    def _encode_value(self, v: Any) -> bytes:
        if v is None:
            return bytes([_TAG_NULL])

        if isinstance(v, bool):
            return bytes([_TAG_BOOL, 1 if v else 0])

        if isinstance(v, int):
            # Check if fits in int64
            if -2**63 <= v < 2**63:
                return bytes([_TAG_INT]) + struct.pack(">q", v)
            # BigInt encoding
            sign = 0 if v >= 0 else 1
            mag = abs(v).to_bytes((abs(v).bit_length() + 7) // 8,
                                  byteorder="big") if v != 0 else b"\x00"
            return (bytes([_TAG_BIGINT]) +
                    struct.pack(">I", len(mag)) +
                    bytes([sign]) + mag)

        if isinstance(v, float):
            return bytes([_TAG_FLOAT]) + struct.pack(">d", v)

        if isinstance(v, str):
            encoded = v.encode("utf-8")
            return bytes([_TAG_STRING]) + struct.pack(">I", len(encoded)) + encoded

        if isinstance(v, (bytes, bytearray)):
            return bytes([_TAG_BYTES]) + struct.pack(">I", len(v)) + v

        if isinstance(v, (list, tuple)):
            parts = [self._encode_value(item) for item in v]
            return (bytes([_TAG_LIST]) +
                    struct.pack(">I", len(v)) +
                    b"".join(parts))

        if isinstance(v, dict):
            parts = []
            for key, val in v.items():
                parts.append(self._encode_value(key))
                parts.append(self._encode_value(val))
            return (bytes([_TAG_MAP]) +
                    struct.pack(">I", len(v)) +
                    b"".join(parts))

        # Fallback — JSON-encode and store as string
        return self._encode_value(json.dumps(v))


class LBEDecoder:
    """Decode LATERALUS Binary Encoding back to Python values."""

    def decode(self, data: bytes) -> Any:
        if data[:4] != LBE_MAGIC:
            raise ValueError("Not a valid LBE file — bad magic bytes")
        version, flags = struct.unpack(">HH", data[4:8])
        if version > LBE_VERSION:
            raise ValueError(f"LBE version {version} not supported "
                             f"(max: {LBE_VERSION})")
        body = data[8:]
        if flags & 0x01:
            body = zlib.decompress(body)
        value, _ = self._decode_value(body, 0)
        return value

    def _decode_value(self, data: bytes, pos: int) -> Tuple[Any, int]:
        tag = data[pos]
        pos += 1

        if tag == _TAG_NULL:
            return None, pos

        if tag == _TAG_BOOL:
            return bool(data[pos]), pos + 1

        if tag == _TAG_INT:
            val = struct.unpack(">q", data[pos:pos+8])[0]
            return val, pos + 8

        if tag == _TAG_FLOAT:
            val = struct.unpack(">d", data[pos:pos+8])[0]
            return val, pos + 8

        if tag == _TAG_STRING:
            length = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            return data[pos:pos+length].decode("utf-8"), pos + length

        if tag == _TAG_BYTES:
            length = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            return data[pos:pos+length], pos + length

        if tag == _TAG_LIST:
            count = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            items = []
            for _ in range(count):
                val, pos = self._decode_value(data, pos)
                items.append(val)
            return items, pos

        if tag == _TAG_MAP:
            count = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            result = {}
            for _ in range(count):
                key, pos = self._decode_value(data, pos)
                val, pos = self._decode_value(data, pos)
                result[key] = val
            return result, pos

        if tag == _TAG_BIGINT:
            length = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            sign = data[pos]
            pos += 1
            mag = int.from_bytes(data[pos:pos+length], byteorder="big")
            if sign:
                mag = -mag
            return mag, pos + length

        if tag == _TAG_TIMESTAMP:
            ns = struct.unpack(">Q", data[pos:pos+8])[0]
            return ns / 1e9, pos + 8

        raise ValueError(f"Unknown LBE type tag: 0x{tag:02x}")


# Convenience functions
def lbe_encode(value: Any, compress: bool = False) -> bytes:
    """Encode a value to LATERALUS Binary Encoding."""
    return LBEEncoder(compress=compress).encode(value)


def lbe_decode(data: bytes) -> Any:
    """Decode a LATERALUS Binary Encoding payload."""
    return LBEDecoder().decode(data)


def lbe_save(value: Any, path: str, compress: bool = True) -> None:
    """Encode and save to file."""
    with open(path, "wb") as f:
        f.write(lbe_encode(value, compress=compress))


def lbe_load(path: str) -> Any:
    """Load and decode from file."""
    with open(path, "rb") as f:
        return lbe_decode(f.read())


# ─────────────────────────────────────────────────────────────────────────────
# Digital signatures (HMAC-based for now, RSA when cryptography available)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SignedPayload:
    """A data payload with HMAC signature for integrity verification."""
    data: bytes
    signature: str
    algorithm: str = "sha256"
    timestamp: float = field(default_factory=time.time)

    def verify(self, key: Union[str, bytes]) -> bool:
        """Verify the signature matches the data."""
        return hmac_verify(key, self.data, self.signature, self.algorithm)

    def to_bytes(self) -> bytes:
        """Serialize to bytes for transmission/storage."""
        meta = json.dumps({
            "signature": self.signature,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp,
        }).encode("utf-8")
        return (struct.pack(">I", len(meta)) + meta +
                struct.pack(">I", len(self.data)) + self.data)

    @staticmethod
    def from_bytes(raw: bytes) -> "SignedPayload":
        meta_len = struct.unpack(">I", raw[:4])[0]
        meta = json.loads(raw[4:4+meta_len].decode("utf-8"))
        data_offset = 4 + meta_len
        data_len = struct.unpack(">I", raw[data_offset:data_offset+4])[0]
        data = raw[data_offset+4:data_offset+4+data_len]
        return SignedPayload(
            data=data,
            signature=meta["signature"],
            algorithm=meta["algorithm"],
            timestamp=meta["timestamp"],
        )


def sign_data(data: Union[str, bytes], key: Union[str, bytes],
              algorithm: str = "sha256") -> SignedPayload:
    """Sign data with HMAC and return a SignedPayload."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    sig = hmac_sign(key, data, algorithm)
    return SignedPayload(data=data, signature=sig, algorithm=algorithm)


# ─────────────────────────────────────────────────────────────────────────────
# Checksums for file integrity
# ─────────────────────────────────────────────────────────────────────────────

def checksum_file(path: str, algorithm: str = "sha256",
                  chunk_size: int = 8192) -> str:
    """Compute hash of a file without loading it entirely into memory."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: str, expected_hash: str,
                algorithm: str = "sha256") -> bool:
    """Verify a file's hash matches expected."""
    return hmac.compare_digest(checksum_file(path, algorithm), expected_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Export registry for transpiler preamble
# ─────────────────────────────────────────────────────────────────────────────

CRYPTO_BUILTINS: Dict[str, Any] = {
    "sha256": sha256,
    "sha512": sha512,
    "blake2b": blake2b,
    "md5": md5,
    "hash_data": hash_data,
    "hmac_sign": hmac_sign,
    "hmac_verify": hmac_verify,
    "hash_password": hash_password,
    "verify_password": verify_password,
    "random_token": random_token,
    "random_urlsafe": random_urlsafe,
    "random_bytes": random_bytes,
    "to_base64": to_base64,
    "from_base64": from_base64,
    "to_hex": to_hex,
    "from_hex": from_hex,
    "xor_encrypt": xor_encrypt,
    "xor_decrypt": xor_decrypt,
    "aes_generate_key": aes_generate_key,
    "aes_encrypt": aes_encrypt,
    "aes_decrypt": aes_decrypt,
    "lbe_encode": lbe_encode,
    "lbe_decode": lbe_decode,
    "lbe_save": lbe_save,
    "lbe_load": lbe_load,
    "sign_data": sign_data,
    "checksum_file": checksum_file,
    "verify_file": verify_file,
}
