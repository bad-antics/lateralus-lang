# Fast Cryptographic Hashing with BLAKE2s in Lateralus

*A practical walkthrough of using the 32-bit-optimized BLAKE2s (RFC 7693) standard library module in Lateralus.*

---

## What is BLAKE2s?

BLAKE2s is the 32-bit-word counterpart to BLAKE2b. While BLAKE2b is tuned for 64-bit architectures, BLAKE2s is specifically designed for 32-bit platforms, embedded devices, WebAssembly, and systems where memory footprint and 32-bit integer arithmetic dominate.

It is faster than MD5, SHA-1, and SHA-256 while providing equal or higher cryptographic strength than SHA-3.

## Standard Library API (`stdlib/blake2s.ltl`)

Lateralus provides a pure, zero-dependency one-shot implementation of RFC 7693:

```lateralus
import blake2s

// 1. One-shot 256-bit hash of a string
let digest = blake2s.hash256_str("Lateralus")

// 2. Unkeyed byte list hash
let bytes = [0x61, 0x62, 0x63] // "abc"
let hash_bytes = blake2s.hash256(bytes)

// 3. Keyed MAC hashing (keyed digest up to 32 bytes)
let key = [0x01, 0x02, 0x03, 0x04]
let mac = blake2s.hash(bytes, key, 32)
```

## RFC 7693 Pinned Test Vectors

To ensure byte-for-byte spec conformity, Lateralus pins the following standard test vectors:

| Input | Digest Length | BLAKE2s-256 Hex Digest |
| :--- | :---: | :--- |
| `""` (Empty string) | 32 bytes | `69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9` |
| `"abc"` | 32 bytes | `508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982` |
| `"The quick brown fox jumps over the lazy dog"` | 32 bytes | `606beeec743ccbeff6cbcdf5d5302aa855c256c29b88c8ed331ea1a6bf3c8812` |

## Runnable Example (`examples/tutorials/blake2s_demo.ltl`)

```lateralus
module examples.tutorials.blake2s_demo

import io
import blake2s

fn main() {
    let msg = "Hello Lateralus!"
    let digest = blake2s.hash256_str(msg)
    io.println("Computed 32-byte BLAKE2s digest for message.")
}
```

## Running the Verification Tests

```bash
python3 -m unittest tests/test_blake2s_tutorial.py
```
