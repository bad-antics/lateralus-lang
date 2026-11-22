# Mastering ZeroMQ Z85 (RFC 32) in Lateralus: Escaping-Free Binary Framing and Golden Vectors

Binary serialization formats (such as raw ECDH public keys, Curve25519 tokens, and binary frames) frequently need to be embedded in JSON payloads, configuration files, source code literals, or command-line parameters.

While **Base64** is standard, it incurs a $33.3\%$ storage penalty (3 bytes into 4 ASCII characters) and frequently requires padding characters (`=`) and URL-escaping (`+` and `/`).

**ZeroMQ Z85 (RFC 32)** solves this:
- **Higher Density**: Packs 4 binary bytes into exactly 5 ASCII characters (a strict $25\%$ expansion ratio).
- **Zero Escaping**: Its 85-character alphabet explicitly avoids quotation marks (`"`, `'`) and backslashes (`\`), making it safe for immediate embedding in JSON, C/C++ literals, and XML strings.

In this tutorial, we implement RFC 32 Z85 encoding and decoding in Lateralus.

---

## 1. Mathematical Underpinnings: Base-85 Divmod

Because:
$$85^5 = 4,437,053,125 > 2^{32} = 4,294,967,296$$
any 32-bit unsigned integer $V \in [0, 2^{32}-1]$ can be uniquely represented by a sequence of 5 base-85 digits:

$$V = c_0 \cdot 85^4 + c_1 \cdot 85^3 + c_2 \cdot 85^2 + c_3 \cdot 85^1 + c_4 \cdot 85^0$$

where:
- $85^4 = 52,200,625$
- $85^3 = 614,125$
- $85^2 = 7,225$
- $85^1 = 85$
- $85^0 = 1$

```lateralus
fn encode_word(val: int) -> string {
    let mut v = val;
    let c0 = v / 52200625;
    v = v % 52200625;

    let c1 = v / 614125;
    v = v % 614125;

    let c2 = v / 7225;
    v = v % 7225;

    let c3 = v / 85;
    let c4 = v % 85;

    return z85_char(c0) + z85_char(c1) + z85_char(c2) + z85_char(c3) + z85_char(c4);
}
```

---

## 2. The 85-Character Alphabet

The character set spans index $0$ to $84$:
```
0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#
```
Notice that quotes, backslashes, commas, and semicolons are intentionally omitted to avoid string escaping conflicts across diverse programming languages.

---

## 3. Streaming and Curve25519 Key Representation

In ZeroMQ authentication protocols (such as CurveZMQ / ZAP), 32-byte public keys serialize to exactly 40 Z85 characters ($32 \times \frac{5}{4} = 40$), compared to 44 characters in Base64 (with padding).

See `examples/z85_tutorial.ltl` for wire-level frame formatting.

---

## 4. End-to-End Verification with Official Golden Vectors

RFC 32 establishes the canonical test vector:
- **Raw Hex Data (8 bytes)**: `0x86 0x4F 0xD2 0x6F 0xB5 0x59 0xF7 0x5B`
- **Canonical Z85 String (10 chars)**: `HelloWorld`

Our implementation verifies this invariant directly:
- **Executable Example**: `examples/z85_tutorial.ltl`
- **Unit Test Vectors**: `tests/stdlib_z85_tutorial.ltl`

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/z85_tutorial.ltl
python -m lateralus_lang check tests/stdlib_z85_tutorial.ltl
pytest tests/test_compiler.py
```
