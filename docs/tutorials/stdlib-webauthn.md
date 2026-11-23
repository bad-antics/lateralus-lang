# W3C WebAuthn Server-Side Ceremonies Tutorial (`stdlib/webauthn`)

The `stdlib/webauthn` module provides server-side verification and option formatting conforming to the [W3C Web Authentication (WebAuthn) Level 2 & 3 specification](https://www.w3.org/TR/webauthn-3/).

WebAuthn ceremonies consist of two primary workflows:
1. **Registration Ceremony (`webauthn.create`)**:
   - The server issues creation options (relying party info, user identity, cryptographic challenge, supported algorithms).
   - The authenticator binds a newly generated public key pair to the credential ID and returns signed `clientDataJSON` and `authenticatorData`.
2. **Authentication Ceremony (`webauthn.get`)**:
   - The server issues an assertion request with allowed credential IDs and a cryptographic challenge.
   - The authenticator produces an assertion signature over the authenticator data and client data hash.
   - The server validates client parameters, parses authenticator flags and signature counter, detects replays, and verifies signatures.

---

## 1. Challenge & Options Issuance

### Registration Options (`new_registration_options`)
Constructs standard options for `navigator.credentials.create()`:

```lateralus
import stdlib.webauthn

let reg_opts = new_registration_options(
    "usr_001",
    "alice@example.com",
    "Alice Smith",
    "example.com",
    "Example Corp",
    "f4b8a2c4e6d8...", // cryptographically secure base64url challenge
    60000              // timeout in milliseconds
)
```

Generated properties:
- `rp`: Relying party ID and display name.
- `user`: User ID, username, and display name.
- `challenge`: Random base64url string.
- `pubKeyCredParams`: Standard COSE algorithm descriptors (ES256 `-7`, RS256 `-257`).
- `attestation`: `"none"` (privacy-preserving default).

### Authentication Options (`new_authentication_options`)
Constructs options for `navigator.credentials.get()`:

```lateralus
let auth_opts = new_authentication_options(
    "example.com",
    "a1b2c3d4e5...",
    ["cred_id_abc123", "cred_id_def456"],
    30000
)
```

---

## 2. Client Data Verification (`verify_client_data`)

Validates the decoded `clientDataJSON` payload returned by the browser:

```lateralus
let client_data = {}
client_data["type"] = "webauthn.get"
client_data["challenge"] = "a1b2c3d4e5..."
client_data["origin"] = "https://example.com"

let res = verify_client_data(
    client_data,
    "webauthn.get",
    "a1b2c3d4e5...",
    "https://example.com",
    ""
)
// res == [true, "ok"]
```

Validates:
- Presence of required fields (`type`, `challenge`, `origin`).
- Exact type match (`"webauthn.create"` vs `"webauthn.get"`).
- Exact challenge equality (prevents replay across sessions).
- Exact origin match (prevents cross-origin phishing attacks).
- Optional `tokenBinding.status` check.

---

## 3. Authenticator Data Parsing (`parse_authenticator_data`)

Parses raw authenticator data byte stream per WebAuthn §6.1:

```lateralus
let parsed = parse_authenticator_data(raw_bytes)
// parsed["ok"] == true
// parsed["rp_id_hash"] (32 bytes SHA-256 hash of rpId)
// parsed["flags"] (raw bitmask byte)
// parsed["flag_up"] (User Present: bit 0)
// parsed["flag_uv"] (User Verified: bit 2)
// parsed["flag_at"] (Attested Credential Data present: bit 6)
// parsed["flag_ed"] (Extension Data present: bit 7)
// parsed["sign_count"] (32-bit unsigned big-endian counter)
```

When `flag_at` is asserted (during registration), extracts:
- `aaguid`: 16-byte authenticator model identifier.
- `credential_id`: Unique credential ID byte array.
- `cose_public_key`: CBOR-encoded public key structure.

---

## 4. Counter Replay Detection (`check_counter`)

Guards against authenticator cloning or replayed signatures per WebAuthn §7.2:

```lateralus
let is_valid = check_counter(stored_counter, received_counter)
```

- When both counters are `0`, passes (for authenticators without counter support).
- Otherwise, strictly requires `received > stored` to prevent cloned credentials from replaying signed assertions.

---

## 5. End-to-End Authentication Shell (`verify_authentication`)

Orchestrates complete non-crypto ceremony validation:

```lateralus
let result = verify_authentication(
    client_data,
    expected_challenge,
    expected_origin,
    expected_rp_id_hash,
    auth_data_buf,
    stored_counter,
    pub_key,
    signed_msg,
    signature,
    verify_signature_callback
)
```

---

## Running Examples and Tests

Run the interactive tutorial:
```bash
lateralus run examples/webauthn_tutorial.ltl
```

Run comprehensive unit tests:
```bash
pytest tests/test_webauthn_tutorial.py -v
```
