# Mastering CBOR (RFC 8949) in Lateralus: Compact Binary Object Representation & Golden Vectors

In constrained environments—such as IoT edge devices, blockchain transaction ledgers (e.g., Cardano, Solana), and cryptographic authentication protocols (FIDO2, WebAuthn, COSE)—JSON and text-based formats impose crippling bandwidth and parsing overheads.

**CBOR (Concise Binary Object Representation, RFC 8949)** provides a binary alternative that mirrors JSON's dynamic data model while dramatically reducing serialized byte counts and eliminating string allocation costs during deserialization.

In this tutorial, we demonstrate how to construct, encode, and validate RFC 8949 CBOR payloads natively in Lateralus.

---

## 1. Architectural Anatomy: The 8 Major Types

Every CBOR data item begins with an initial byte containing two fields:
- **Major Type (Bits 7..5)**: Defines the semantic kind of the item (0 through 7).
- **Additional Information (Bits 4..0)**: Direct value for small scalars ($0 \dots 23$), or a length descriptor flag ($24 \dots 31$).

| Major Type | Kind | Initial Byte Range | Description |
| :--- | :--- | :--- | :--- |
| **0** | Unsigned Integer | `0x00..0x1b` | Non-negative integers $0 \dots 2^{64}-1$ |
| **1** | Negative Integer | `0x20..0x3b` | Negative integers $-1 - n$ ($ -1 \dots -2^{64}$) |
| **2** | Byte String | `0x40..0x5b` | Arbitrary raw octet sequences |
| **3** | Text String | `0x60..0x7b` | UTF-8 validated text strings |
| **4** | Array | `0x80..0x9b` | Ordered lists of data items |
| **5** | Map | `0xa0..0xbb` | Key-value mapping pairs |
| **6** | Semantic Tag | `0xc0..0xdb` | Optional tags (timestamps, bignums, UUIDs) |
| **7** | Simple / Float | `0xe0..0xfb` | Booleans (`0xf4`/`0xf5`), Null (`0xf6`), Floats |

---

## 2. Encoding Small Integers and Negative Values

Values between $0$ and $23$ are encoded directly within the lower 5 bits of the initial byte:

```lateralus
// Major type 0: Unsigned int
fn encode_small_uint(val: int) -> string {
    if val >= 0 && val <= 23 {
        return byte_to_hex(val);
    }
    return "";
}

// Major type 1: Negative int encoded as -1 - val
fn encode_small_nint(val: int) -> string {
    let pos = -1 - val;
    if pos >= 0 && pos <= 23 {
        return byte_to_hex(32 + pos); // 0x20 offset
    }
    return "";
}
```

For instance:
- `0` encodes as `0x00`
- `10` encodes as `0x0a`
- `-1` encodes as `0x20`
- `-10` encodes as `0x29`

---

## 3. Composing Composite Arrays and Maps

Arrays and maps use their initial byte to specify item counts:
- An empty array `[]` has length 0: `(4 << 5) | 0` = `0x80`.
- An array of 3 elements: `(4 << 5) | 3` = `0x83`, immediately followed by the contiguous serialized elements.
- An empty map `{}` has length 0: `(5 << 5) | 0` = `0xa0`.

---

## 4. Telemetry Real-World Example

Consider an edge sensor reporting device ID `12`, subzero temperature `-5°C`, and an active alert flag `true`:
- JSON: `{"device_id":12,"temperature":-5,"alert":true}` (45 bytes)
- CBOR Array Payload: `83` (array of 3) `0c` (12) `24` (-5) `f5` (true) = **4 bytes!**
- **Over 91% reduction in payload volume!**

See the complete runnable implementation in `examples/cbor_tutorial.ltl`.

---

## 5. Verification Against RFC 8949 Golden Vectors

We assert compliance against official RFC 8949 Appendix A test vectors:
- **Executable Example**: `examples/cbor_tutorial.ltl`
- **Unit Test Vectors**: `tests/stdlib_cbor_tutorial.ltl`

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/cbor_tutorial.ltl
python -m lateralus_lang check tests/stdlib_cbor_tutorial.ltl
pytest tests/test_compiler.py
```
