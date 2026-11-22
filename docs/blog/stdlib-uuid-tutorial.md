# Distributed Identity Generation with Lateralus `stdlib/uuid.ltl` (RFC 4122)

In distributed architectures, microservices, and asynchronous event streams, coordinating a single centralized database sequence to generate auto-incrementing primary keys introduces write bottlenecks and single points of failure.

A **Universally Unique Identifier (UUID)**, standardized under **RFC 4122**, provides a 128-bit globally unique identifier that can be generated independently by distributed worker nodes without inter-node coordination or locks. The probability of generating a duplicate UUID v4 is negligible (approximately $10^{-15}$ across billions of entries).

Lateralus includes an RFC 4122 compliant module in `stdlib/uuid.ltl`.

---

## 1. 128-Bit Structure & Formatting

A canonical UUID is rendered as 32 hexadecimal digits displayed in five groups separated by hyphens (8-4-4-4-12, total 36 characters):

$$\texttt{xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx}$$

1. **Version ($M$, digit 13)**: Identifies the algorithm used. For UUID v4 (random generation), this digit is strictly `4`.
2. **Variant ($N$, digit 17)**: Encodes the RFC 4122 layout variant (bits `10xx_2`, representing one of `[8, 9, a, b]`).
3. **Entropy**: Contains 122 bits of cryptographic randomness.

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `uuid_uuid4` | `() -> str` | Generates a random RFC 4122 UUID v4 string. |
| `uuid_nil_uuid` | `() -> str` | Returns the canonical Nil UUID (`"00000000-0000-0000-0000-000000000000"`). |
| `uuid_is_valid` | `(s: str) -> bool` | Checks 36-char length and hyphen positions (indices 8, 13, 18, 23). |
| `uuid_version` | `(s: str) -> int` | Extracts the version number (1–5, or 0 if invalid). |
| `uuid_equals` | `(a: str, b: str) -> bool` | Constant case-insensitive comparison across heterogeneous databases. |
| `uuid_compact` | `(s: str) -> str` | Strips hyphens to produce a compact 32-character hex representation. |
| `uuid_expand` | `(s: str) -> str` | Re-inserts standard hyphens into a 32-character compact hex string. |

---

## 3. Storage Optimization & Case-Insensitive Equality

### Compact Form for High-Volume Storage
Standard 36-character UUID strings add 4 bytes of hyphen overhead per row. `uuid_compact` strips dashes for compact raw indexing, while `uuid_expand` restores canonical display:

```lateralus
import uuid

let original = "550e8400-e29b-41d4-a716-446655440000"
let compact_id = uuid_compact(original) // "550e8400e29b41d4a716446655440000" (32 chars)
let restored = uuid_expand(compact_id)   // "550e8400-e29b-41d4-a716-446655440000"
```

### Heterogeneous Database Casing
Some databases (like PostgreSQL) store UUIDs in lowercase, whereas legacy Windows/COM runtimes generate uppercase. `uuid_equals` normalizes casing:

```lateralus
let is_same = uuid_equals("550e8400-e29b-41d4-a716-446655440000", "550E8400-E29B-41D4-A716-446655440000")
// Returns true
```

---

## 4. Standard Namespaces (RFC 4122 Section 4.3)

`stdlib/uuid.ltl` predefines standard namespace constants used when deriving deterministic UUIDs (v3/v5) from string names:

```lateralus
pub const NAMESPACE_DNS  = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
pub const NAMESPACE_URL  = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
pub const NAMESPACE_OID  = "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
pub const NAMESPACE_X500 = "6ba7b814-9dad-11d1-80b4-00c04fd430c8"
```

---

## 5. Verification & Test Suite

The test suite in `tests/stdlib_uuid_tutorial.ltl` verifies:
- Validation of nil and random UUIDs.
- Version extraction from canonical strings.
- Reversible compact/expand transformations.
- Complete case-insensitive equality across uppercase/lowercase inputs.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_uuid_tutorial.ltl
python -m lateralus_lang check examples/uuid_tutorial.ltl
```
