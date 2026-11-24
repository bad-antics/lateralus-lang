# Argon2id Password Hashing & PHC Format Tutorial (`stdlib/argon2`)

The `stdlib/argon2` module provides password hashing and key derivation conforming to the [RFC 9106 Argon2 specification](https://datatracker.ietf.org/doc/html/rfc9106) with standardized Password Hashing Competition (PHC) string serialization.

Argon2id is the winner of the Password Hashing Competition and the current industry standard recommended by OWASP, IETF, and NIST for defending against GPU, ASIC, and side-channel cracking attacks through memory-hardness.

---

## 1. Parameter Profiles

Argon2id relies on three core cost parameters:
- `m`: Memory size in KiB.
- `t`: Iteration count (time cost).
- `p`: Parallelism degree (thread count).

Standard pre-configured profiles:
- `profile_interactive()`: Interactive web logins (~50 ms target on modern cores).
  - $m = 65536$ (64 MiB), $t = 3$, $p = 1$, hash length = 32 bytes.
- `profile_sensitive()`: Sensitive enterprise vaults & financial systems (~500 ms target).
  - $m = 262144$ (256 MiB), $t = 4$, $p = 1$, hash length = 32 bytes.
- `profile_kdf()`: Key derivation for disk and master key encryption.
  - $m = 131072$ (128 MiB), $t = 3$, $p = 1$, hash length = 32 bytes.

```lateralus
import stdlib.argon2

let prof = profile_interactive()
```

---

## 2. Password Hashing & Verification

### Hashing (`hash`)
Generates cryptographically random salt, computes the memory-hard Argon2id digest, and formats the output into a PHC-compliant string:

```lateralus
let phc_hash = hash("user_password_here", prof)
// "$argon2id$v=19$m=65536,t=3,p=1$<b64-salt>$<b64-hash>"
```

### Constant-Time Verification (`verify`)
Decodes the stored PHC string, recomputes the hash using the identical parameters and salt, and executes constant-time byte comparison (`crypto_ct_eq`) to mitigate timing side-channel attacks:

```lateralus
let is_valid = verify("user_password_here", phc_hash)
// is_valid == true
```

---

## 3. Upgrading & Rehash Policy (`needs_rehash`)

As hardware capabilities advance, security guidelines require increasing cost parameters. `needs_rehash` checks whether an existing stored hash was generated under weaker parameters than the system's current target:

```lateralus
let needs_upgrade = needs_rehash(phc_hash, profile_sensitive())
// Returns true if stored m < desired.m, t < desired.t, or p < desired.p
```

---

## 4. PHC String Serialization (`phc_encode` & `phc_decode`)

Converts between structured parameter maps and standard PHC format strings:

```lateralus
let encoded = phc_encode(prof, salt_bytes, hash_bytes)
let decoded = phc_decode(encoded)
// decoded["m"] == 65536
// decoded["t"] == 3
// decoded["p"] == 1
// decoded["salt"] == salt_bytes
// decoded["hash"] == hash_bytes
```

---

## Running Examples and Tests

Run the interactive tutorial:
```bash
lateralus run examples/argon2_tutorial.ltl
```

Run comprehensive unit tests:
```bash
pytest tests/test_argon2_tutorial.py -v
```
