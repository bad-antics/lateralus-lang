# Generating and Managing Identifiers with `stdlib.uuid`

The `stdlib.uuid` module provides standardized Universal Unique Identifier (UUID) generation, parsing, validation, and serialization routines. Compliant with RFC 4122, it provides essential primitives for generating distributed primary keys, session tokens, request correlation identifiers, and compact storage formats.

---

## 1. UUID v4 Generation

Generate cryptographically random UUID v4 identifiers or nil UUIDs:

```lateralus
import uuid

// Generate a random UUID v4 string
let id = uuid.uuid4()
// Example: "f47ac10b-58cc-4372-a567-0e02b2c3d479"

// Generate a canonical Nil UUID (all zeros)
let empty = uuid.nil_uuid()
// "00000000-0000-0000-0000-000000000000"
```

---

## 2. Validation & Version Inspection

Verify formatting and extract the RFC 4122 variant version:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`is_valid(s)`** | `str -> bool` | Checks if a string conforms to the 8-4-4-4-12 hyphenated hex pattern. |
| **`version(s)`** | `str -> int` | Extracts the UUID version number (1–5). Returns `0` if invalid or nil. |

```lateralus
let token = "c9a646d3-9c61-4cd9-bc19-4702b8006e78"

if uuid.is_valid(token) {
    let ver = uuid.version(token)
    println("Valid UUID version: " + to_str(ver)) // Output: 4
}
```

---

## 3. Serialization: Standard vs. Compact Formats

Databases and binary protocols often prefer storing UUIDs without hyphens (32-character hex):

- **`compact(s)`**: Strips hyphens from a 36-character UUID string.
- **`expand(s)`**: Restores standard 8-4-4-4-12 hyphenation from a 32-character compact string.
- **`equals(a, b)`**: Performs case-insensitive UUID equality comparison.

```lateralus
let full = "550e8400-e29b-41d4-a716-446655440000"

// Convert to 32-char hex storage key
let key = uuid.compact(full)
// key == "550e8400e29b41d4a716446655440000"

// Expand back to RFC 4122 standard display
let display = uuid.expand(key)

// Case-insensitive verification
let matches = uuid.equals(display, "550E8400-E29B-41D4-A716-446655440000") // true
```

---

## 4. Standard Namespace Constants

Pre-defined UUID constants are exported for namespace-based deterministic hashing:

- `NAMESPACE_DNS`: `"6ba7b810-9dad-11d1-80b4-00c04fd430c8"`
- `NAMESPACE_URL`: `"6ba7b811-9dad-11d1-80b4-00c04fd430c8"`
- `NAMESPACE_OID`: `"6ba7b812-9dad-11d1-80b4-00c04fd430c8"`
- `NAMESPACE_X500`: `"6ba7b814-9dad-11d1-80b4-00c04fd430c8"`

---

## 5. End-to-End Example: Distributed Session Store

```lateralus
import uuid

fn create_session(user_id: int) -> map {
    let raw_uuid = uuid.uuid4()
    return {
        "user_id": user_id,
        "token": raw_uuid,
        "db_key": uuid.compact(raw_uuid)
    }
}

fn authenticate(incoming_token: str) -> bool {
    if !uuid.is_valid(incoming_token) {
        return false
    }
    return uuid.version(incoming_token) == 4
}

fn main() {
    let session = create_session(101)
    println("Session Token: " + session["token"])
    println("Database Key:  " + session["db_key"])
    
    if authenticate(session["token"]) {
        println("Authentication passed: Valid v4 Session ID")
    }
}
```
