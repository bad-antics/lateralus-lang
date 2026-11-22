# Hardened Password Storage with Lateralus `stdlib/argon2.ltl` (RFC 9106)

Storing user credentials requires deliberate cryptographic friction. Traditional cryptographic hashes (such as SHA-256 or SHA-512) are designed to execute quickly, allowing attackers with commodity GPU clusters or custom ASICs to compute billions of guesses per second during offline dictionary attacks.

Winner of the international Password Hashing Competition (PHC) and standardized under **RFC 9106**, **Argon2id** is the state of the art in password protection. It combines memory-hardness (rendering specialized GPU cracking economically unviable) with data-independent memory access (mitigating cache-timing side channels).

Lateralus includes a pure, RFC 9106 compliant implementation in `stdlib/argon2.ltl`.

---

## 1. Mathematical Architecture & Parameter Anatomy

Argon2id configures security via three interdependent dimensions:

$$m \text{ (Memory Cost)}, \quad t \text{ (Time Iterations)}, \quad p \text{ (Parallelism Lanes)}$$

1. **Memory ($m$)**: Memory footprint in kibibytes ($1 \text{ KiB} = 1024 \text{ bytes}$). For example, $m=65536$ allocates $64\text{ MiB}$ of RAM per hash evaluation. An adversary attempting to crack 1,000 passwords concurrently requires $64\text{ GiB}$ of dedicated high-speed memory.
2. **Time ($t$)**: Number of passes over the memory matrix.
3. **Parallelism ($p$)**: Number of independent execution lanes.

### PHC Standard String Format
Serialized hashes follow the Password Hashing Competition (PHC) string format:

$$\texttt{\$argon2id\$v=19\$m=65536,t=3,p=1\$<salt>\$<hash>}$$

All parameters, salts, and output digests are self-contained, ensuring future upgrades remain backwards-compatible with historical records.

---

## 2. API Reference & Parameter Profiles

| Function | Signature | Target Execution | Description |
| :--- | :--- | :--- | :--- |
| `argon2_profile_interactive` | `() -> map` | $\approx 50\text{ ms}$ ($m=64\text{MB}, t=3, p=1$) | Tuned for low-latency web login sessions. |
| `argon2_profile_sensitive` | `() -> map` | $\approx 500\text{ ms}$ ($m=256\text{MB}, t=4, p=1$) | Tuned for administrative vaults & banking. |
| `argon2_profile_kdf` | `() -> map` | Variable ($m=128\text{MB}, t=3, p=1$) | Tuned for volume encryption key derivation. |
| `argon2_hash` | `(pw: str, prof: map) -> str` | N/A | Hashes password with random 16-byte salt into PHC string. |
| `argon2_verify` | `(pw: str, phc: str) -> bool` | Constant-time | Verifies password against stored PHC string. |
| `argon2_needs_rehash` | `(phc: str, des: map) -> bool` | Instantaneous | Checks if stored hash parameters are weaker than desired profile. |

---

## 3. Practical Example: Progressive Zero-Downtime Rehash

When elevating security policies (e.g., upgrading from $64\text{MB}$ to $256\text{MB}$ memory cost), requiring all users to reset their passwords causes massive friction. 

With `argon2_needs_rehash`, databases are upgraded **transparently during legitimate user logins**:

```lateralus
import argon2

pub fn authenticate_user(raw_password: str, stored_phc: str) -> bool {
    // 1. Constant-time verification
    if not argon2_verify(raw_password, stored_phc) {
        return false // Invalid credentials
    }

    // 2. Progressive security escalation check
    let elevated_policy = argon2_profile_sensitive()
    if argon2_needs_rehash(stored_phc, elevated_policy) {
        let new_phc = argon2_hash(raw_password, elevated_policy)
        database_update_password_hash(new_phc)
    }

    return true
}
```

---

## 4. Verification & Test Suite

The test suite in `tests/stdlib_argon2_tutorial.ltl` verifies:
- Roundtrip hash generation and constant-time equality validation.
- Complete rejection of invalid passwords.
- PHC format serialization and parsing integrity.
- Parameter boundary comparisons in `needs_rehash`.

Run tests locally:
```bash
python -m lateralus_lang check tests/stdlib_argon2_tutorial.ltl
python -m lateralus_lang check examples/argon2_tutorial.ltl
```
