# RFC 3629 UTF-8 Validation and Multi-Byte Unicode Decoding in Lateralus: Bit Patterns, Security Hazards, and Overlong Rejection

In 1992, Ken Thompson and Rob Pike designed UTF-8 to provide a backward-compatible, variable-width encoding for Unicode without the endianness complexities or null-byte hazards of UTF-16 and UTF-32. Today, UTF-8 encodes over 98% of the World Wide Web and acts as the universal wire format for network protocols, JSON payloads, and systems programming IPC.

However, naive UTF-8 parsers that decode bits without strict validation introduce severe security vulnerabilities—most notably **overlong sequence bypasses** (such as encoding `../` or `\0` in multi-byte forms to slip past firewall path-traversal filters).

In this tutorial, we implement, benchmark, and mathematically verify an RFC 3629 compliant UTF-8 validation and decoding engine in Lateralus.

---

## 1. RFC 3629 Bit Pattern Specification

UTF-8 encodes Unicode scalar values $U \in [0x0000, 0x10FFFF]$ into sequences of 1 to 4 octets:

| Codepoint Range | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Bits |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `U+0000..U+007F` | `0xxxxxxx` | — | — | — | 7 |
| `U+0080..U+07FF` | `110xxxxx` | `10xxxxxx` | — | — | 11 |
| `U+0800..U+FFFF` | `1110xxxx` | `10xxxxxx` | `10xxxxxx` | — | 16 |
| `U+10000..U+10FFFF` | `11110xxx` | `10xxxxxx` | `10xxxxxx` | `10xxxxxx` | 21 |

### Critical Security Invariants

1. **Overlong Encodings are Strictly Forbidden**: A character must be encoded using the shortest possible byte sequence. For instance, encoding ASCII `'A'` (`0x41`) as `0xC1 0x81` is invalid and must be rejected immediately.
2. **Surrogate Pair Code Points are Invalid**: Values in the interval $[0xD800, 0xDFFF]$ (55296 to 57343) are reserved for UTF-16 surrogate pairs and cannot appear in valid UTF-8 streams.
3. **Upper Bound**: Values strictly exceeding $U+10FFFF$ (1,114,111) are out of Unicode bounds.

---

## 2. Invariant Verification: Continuation & Boundary Checks

Every trailing byte in a multi-byte sequence must satisfy the continuation condition:

$$(\text{byte} \ \& \ 0xC0) == 0x80$$

In Lateralus, our validator extracts and asserts this bit mask:

```lateralus
if (b1 & 192) != 128 { return []; } // Rejects corrupted byte stream!
```

Furthermore, codepoints must fall within their canonical range:
- 2-byte: $\text{codepoint} \ge 128$
- 3-byte: $\text{codepoint} \ge 2048$ and $\text{codepoint} \notin [55296, 57343]$
- 4-byte: $65536 \le \text{codepoint} \le 1114111$

---

## 3. The Lateralus Implementation

### 3.1 Scalar Value Encoder

```lateralus
fn utf8_encode_codepoint(cp: int) -> list {
    if cp < 128 {
        return [cp];
    }
    if cp < 2048 {
        let b0 = 192 | (cp >> 6);
        let b1 = 128 | (cp & 63);
        return [b0, b1];
    }
    if cp < 65536 {
        let b0 = 224 | (cp >> 12);
        let b1 = 128 | ((cp >> 6) & 63);
        let b2 = 128 | (cp & 63);
        return [b0, b1, b2];
    }
    let b0 = 240 | (cp >> 18);
    let b1 = 128 | ((cp >> 12) & 63);
    let b2 = 128 | ((cp >> 6) & 63);
    let b3 = 128 | (cp & 63);
    return [b0, b1, b2, b3];
}
```

### 3.2 Secure Stream Validator and Decoder

```lateralus
fn utf8_validate_and_decode(bytes: list) -> list {
    let mut codepoints = [];
    let mut i = 0;
    let n = len(bytes);

    while i < n {
        let b0 = bytes[i];
        if (b0 & 128) == 0 {
            codepoints = codepoints + [b0];
            i = i + 1;
        } else if (b0 & 224) == 192 {
            if i + 1 >= n { return []; }
            let b1 = bytes[i + 1];
            if (b1 & 192) != 128 { return []; }
            let cp = ((b0 & 31) << 6) | (b1 & 63);
            if cp < 128 { return []; } // Reject overlong
            codepoints = codepoints + [cp];
            i = i + 2;
        } else if (b0 & 240) == 224 {
            if i + 2 >= n { return []; }
            let b1 = bytes[i + 1];
            let b2 = bytes[i + 2];
            if (b1 & 192) != 128 || (b2 & 192) != 128 { return []; }
            let cp = ((b0 & 15) << 12) | ((b1 & 63) << 6) | (b2 & 63);
            if cp < 2048 { return []; }
            if cp >= 55296 && cp <= 57343 { return []; }
            codepoints = codepoints + [cp];
            i = i + 3;
        } else if (b0 & 248) == 240 {
            if i + 3 >= n { return []; }
            let b1 = bytes[i + 1];
            let b2 = bytes[i + 2];
            let b3 = bytes[i + 3];
            if (b1 & 192) != 128 || (b2 & 192) != 128 || (b3 & 192) != 128 { return []; }
            let cp = ((b0 & 7) << 18) | ((b1 & 63) << 12) | ((b2 & 63) << 6) | (b3 & 63);
            if cp < 65536 || cp > 1114111 { return []; }
            codepoints = codepoints + [cp];
            i = i + 4;
        } else {
            return [];
        }
    }
    return codepoints;
}
```

---

## 4. Verification and Execution

Run the compiler checks and validation test suite:

```powershell
# 1. Run the interactive tutorial example
lateralus_lang run examples/utf8_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_utf8_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus RFC 3629 UTF-8 Validation & Decoder Demo ===
Serialized UTF-8 Byte Array: [72, 105, 32, 226, 130, 172, 32, 240, 159, 154, 128]
Total Encoded Bytes: 11 bytes (vs 24 bytes in 32-bit UCS-4)
Decoded Unicode Codepoints: [72, 105, 32, 8364, 32, 128640]
Security Defense: Successfully rejected overlong payload [0xC1, 0x81]

UTF-8 validator and decoding engine verified 100% faithful!
```

---

## 5. Summary

Strict RFC 3629 compliance is non-negotiable in production systems. By validating bit patterns, continuation prefixes, and rejecting overlong and surrogate sequences, Lateralus programs can safely ingest untrusted external text without security vulnerability.
