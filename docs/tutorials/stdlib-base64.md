# Base64 Encoding and Decoding with `stdlib.base64`

The `stdlib.base64` module provides RFC 4648 compliant Base64 encoding and decoding for Lateralus. It supports standard dictionary encoding with `=` padding, URL-safe variants (`-` and `_` substitutions), payload validation, and pre-allocation buffer length estimation.

---

## 1. Standard Base64 Encoding and Decoding

Convert raw text strings to and from standard Base64 representation:

```lateralus
import base64

// Encode to standard base64 string
let encoded = base64.encode("Hello, World!")
// encoded == "SGVsbG8sIFdvcmxkIQ=="

// Decode back to plaintext
let original = base64.decode(encoded)
// original == "Hello, World!"
```

The encoder partitions 3-byte binary chunks into 4 6-bit sextets, applying canonical `=` padding for remainder offsets.

---

## 2. URL-Safe Base64

Standard Base64 strings contain `+` and `/` characters, which have special meanings in URLs, query strings, and filenames. The `encode_url` and `decode_url` functions replace them with `-` and `_`:

```lateralus
let raw_query = "user?id=10&token=+secret/key"

// URL-safe encoding (+ -> -, / -> _)
let safe_token = base64.encode_url(raw_query)

// Decode back to original string
let recovered = base64.decode_url(safe_token)
// recovered == raw_query
```

---

## 3. String Validation and Length Calculations

Validate incoming base64 data and compute expected output buffer lengths without performing full conversions:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`is_valid(s)`** | `(str) -> bool` | Checks if string has length multiple of 4 and contains valid Base64 characters. |
| **`encoded_length(n)`** | `(int) -> int` | Returns the expected Base64 encoded string length for `n` raw bytes. |
| **`decoded_length(s)`** | `(str) -> int` | Returns the raw byte length of the decoded payload accounting for padding. |

### Example Verification:

```lateralus
let valid_str = "YWJj" // "abc"
let is_ok = base64.is_valid(valid_str) // true

let invalid_str = "invalid!@"
let is_bad = base64.is_valid(invalid_str) // false

// Predict encoded size
let raw_len = 10
let expected_enc_len = base64.encoded_length(raw_len) // 16

// Predict decoded payload size
let dec_size = base64.decoded_length("SGVsbG8=") // 5 ("Hello")
```
