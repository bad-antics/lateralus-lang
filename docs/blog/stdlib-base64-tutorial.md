# Binary Data Serialization with Lateralus `stdlib/base64.ltl` (RFC 4648)

Modern distributed architectures routinely transmit binary payloads—cryptographic hashes, serialized tokens, encrypted ciphertext, and image bytes—over text-based protocols like HTTP, WebSockets, JSON-RPC, and SMTP. Raw binary data contains null bytes (`0x00`) and control sequences that corrupt text-oriented parsers.

**Base64** solves this by encoding arbitrary binary sequences into an ASCII alphabet that is guaranteed to survive transport. Standardized under **RFC 4648**, Lateralus provides a zero-dependency implementation in `stdlib/base64.ltl` supporting both canonical Base64 and the URL-safe variant.

---

## 1. Encoding Mechanics & Sextet Alignment

Base64 works by grouping input bytes into 24-bit blocks ($3 \times 8$ bits) and splitting them into four 6-bit integers ($4 \times 6$ bits), known as **sextets**. Each sextet maps to one character in the 64-symbol index table:

```
Index:  0 ... 25    26 ... 51   52 ... 61   62   63
Symbol: A ... Z     a  ... z    0  ... 9    +    /
```

### Padding Rules
When the input length is not an exact multiple of 3 bytes, padding characters (`=`) are appended to preserve 4-character alignment:

| Input Modulo ($N \pmod 3$) | Unused Bits | Padding Appended | Output Example |
| :--- | :--- | :--- | :--- |
| **0 bytes** (e.g. `"foo"`) | 0 bits | No padding | `"Zm9v"` |
| **1 byte** (e.g. `"f"`) | 4 bits | `==` (2 padding chars) | `"Zg=="` |
| **2 bytes** (e.g. `"fo"`) | 2 bits | `=` (1 padding char) | `"Zm8="` |

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `base64_encode` | `(data: str) -> str` | Encodes arbitrary text/bytes into standard RFC 4648 Base64. |
| `base64_decode` | `(encoded: str) -> str` | Decodes a Base64 string back into raw bytes/characters. |
| `base64_encode_url` | `(data: str) -> str` | Encodes using URL-safe substitution (`+` $\to$ `-`, `/` $\to$ `_`). |
| `base64_decode_url` | `(encoded: str) -> str` | Decodes a URL-safe Base64 string. |
| `base64_is_valid` | `(s: str) -> bool` | Validates that string length is a multiple of 4 and chars are valid. |
| `base64_encoded_length` | `(n: int) -> int` | Exact formula `((n + 2) / 3) * 4` for output buffer allocation. |
| `base64_decoded_length` | `(encoded: str) -> int` | Computes expected payload size by inspecting trailing padding. |

---

## 3. Practical Example: HTTP Auth & URL-safe Tokens

### HTTP Basic Authentication
Constructing standard authorization headers:

```lateralus
import base64

let auth_payload = "alice:super_secret_token"
let token = base64_encode(auth_payload)
let header = "Authorization: Basic " + token
// Output: Authorization: Basic YWxpY2U6c3VwZXJfc2VjcmV0X3Rva2Vu
```

### URL-Safe Variant (RFC 4648 Section 5)
Standard Base64 characters `+` and `/` carry special meanings in URL queries (spaces and path delimiters). The URL-safe alphabet substitutes them:

$$\text{'+'} \longrightarrow \text{'-'}, \quad \text{'/'} \longrightarrow \text{'\_'}$$

```lateralus
let sensitive_state = base64_encode_url("session_token_data")
let restored = base64_decode_url(sensitive_state)
```

---

## 4. Verification & RFC 4648 Section 10 Test Vectors

The test suite in `tests/stdlib_base64_tutorial.ltl` checks every vector specified in RFC 4648 Section 10:

```
BASE64("") = ""
BASE64("f") = "Zg=="
BASE64("fo") = "Zm8="
BASE64("foo") = "Zm9v"
BASE64("foob") = "Zm9vYg=="
BASE64("fooba") = "Zm9vYmE="
BASE64("foobar") = "Zm9vYmFy"
```

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_base64_tutorial.ltl
python -m lateralus_lang check examples/base64_tutorial.ltl
```
