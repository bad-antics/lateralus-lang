# High-Speed Cryptographic Hashing with `stdlib.blake2s`

The `stdlib.blake2s` module provides a pure Lateralus implementation of **BLAKE2s (RFC 7693)**, the 32-bit-word optimized variant of the BLAKE2 cryptographic hash family. Designed to be faster than MD5 and SHA-2 on 32-bit platforms and a core building block for BLAKE3, it offers 256-bit security, keyed MAC capabilities, and variable-length digests.

---

## 1. Quick Start: Hashing Strings and Bytes

Hash raw text strings or byte arrays into 256-bit (32-byte) cryptographic digests:

```lateralus
import blake2s

// Hash a UTF-8 string directly
let digest = blake2s.hash256_str("The quick brown fox jumps over the lazy dog")

// Convert the 32-byte list to lowercase hexadecimal
let hex_hash = blake2s.to_hex(digest)
// hex_hash == "606beeec743ccbeff6cbcdf5d5302aa855c256c29b88c8ed331ea1a6bf3c8812"

// Hash an explicit byte array
let bytes = [97, 98, 99] // "abc"
let abc_digest = blake2s.hash256(bytes)
let abc_hex = blake2s.to_hex(abc_digest)
// abc_hex == "508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"
```

---

## 2. Keyed Hashing (MAC Mode)

BLAKE2s supports native keyed hashing without the performance overhead or vulnerability risks of traditional HMAC constructions:

```lateralus
let message = [84, 104, 101, 32, 113, 117, 105, 99, 107] // "The quick"
let key = [107, 101, 121]                                 // "key"

// Generate a 32-byte Message Authentication Code
let mac = blake2s.hash(message, key, 32)
let mac_hex = blake2s.to_hex(mac)
// mac_hex == "34443d236fc52afe817b747aeedd54493eaa81faec583ecd373b18e1e1892fec"
```

Keys up to 32 bytes are supported per RFC 7693.

---

## 3. Variable Digest Sizes

Generate truncated digests between 1 and 32 bytes for compact fingerprints:

```lateralus
// Produce a compact 16-byte (128-bit) fingerprint
let short_digest = blake2s.hash(bytes, [], 16)
let short_hex = blake2s.to_hex(short_digest)
```

---

## 4. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`hash256_str(s)`** | `(str) -> list` | Computes a 32-byte BLAKE2s digest from a UTF-8 string. |
| **`hash256(msg)`** | `(list) -> list` | Computes a 32-byte BLAKE2s digest from a byte integer list. |
| **`hash(msg, key, digest_len)`** | `(list, list, int) -> list` | Computes a BLAKE2s digest with optional key (pass `[]` for unkeyed) and custom length `1..32`. |
| **`to_hex(digest)`** | `(list) -> str` | Formats a byte list into a canonical lowercase hexadecimal string. |
