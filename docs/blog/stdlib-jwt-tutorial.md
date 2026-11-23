# Stateless Authentication with Lateralus `stdlib/jwt.ltl` (RFC 7519)

In distributed microservices, stateful server sessions introduce database bottlenecks and replication latency. **JSON Web Tokens (JWT)**, standardized under **RFC 7519**, allow servers to issue cryptographically signed, tamper-proof assertions that clients attach to HTTP requests in `Authorization: Bearer <token>`.

Lateralus provides a hardened, zero-dependency JWT implementation in `stdlib/jwt.ltl`. It enforces constant-time signature verification, strictly rejects the notorious `alg: none` vulnerability, and supports clock-drift leeway.

---

## 1. JWS Compact Serialization Architecture

A compact JWT consists of three base64url-encoded parts separated by periods (`.`):

$$\text{Token} = \text{Header} \,.\, \text{Payload} \,.\, \text{Signature}$$

1. **Header**: Metadata specifying token type and cryptographic algorithm:
   ```json
   {"typ":"JWT","alg":"HS256"}
   ```
2. **Payload (Claims)**: JSON claims containing standard fields (`sub`, `exp`, `iat`, `aud`, `iss`) and custom application state.
3. **Signature**: Cryptographic HMAC computed over the ASCII signing input:
   $$\text{Signature} = \text{HMAC}(\text{Base64URL}(\text{Header}) \,||\, \text{"."} \,||\, \text{Base64URL}(\text{Payload}), \, \text{Key})$$

---

## 2. Hardened Security Design

### Constant-Time Signature Comparison
Naive string comparisons (`sig_got == sig_want`) terminate on the first mismatched byte, allowing attackers to incrementally deduce valid signatures via microsecond timing measurements. `stdlib/jwt.ltl` calls `crypto_ct_eq`, executing in strict constant time regardless of where discrepancies occur.

### Complete Rejection of `alg: none`
A widespread historical flaw in naive libraries occurs when attackers forge tokens with `{"alg":"none"}` to bypass signature verification entirely. `stdlib/jwt.ltl` resolves supported algorithms via `hmac_hash_for` (restricted strictly to `"HS256"`, `"HS384"`, and `"HS512"`), ensuring unsigned tokens are unconditionally rejected.

### Leeway Handling for Clock Skew
Clocks between distributed servers frequently drift by several seconds. Passing `opts["leeway_s"] = 10` allows legitimate tokens to be accepted even if server clocks have minor discrepancies.

---

## 3. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `jwt_issue` | `(sub: str, key: list, ttl_s: int, extra: map, alg: str) -> str` | Issues a token automatically populated with `iat`, `nbf`, and `exp`. |
| `jwt_sign_hmac` | `(claims: map, key: list, alg: str) -> str` | Signs arbitrary claims with the specified HMAC algorithm. |
| `jwt_verify_hmac` | `(token: str, key: list, alg: str, opts: map) -> list` | Verifies signature and claims. Returns `[true, claims]` or `[false, error]`. |
| `jwt_peek` | `(token: str) -> map` | Unsafely inspects header and claims without verification (for logging). |

---

## 4. Practical Implementation: Auth Middleware

```lateralus
import jwt

pub fn main() {
    let key = bytes_of("my-secret-signing-key-32b!")

    // 1. Issuance on login
    let extra = {}
    extra["role"] = "admin"
    let token = jwt_issue("user_42", key, 3600, extra, "HS256")

    // 2. Gateway verification
    let opts = {}
    opts["leeway_s"] = 5

    let result = jwt_verify_hmac(token, key, "HS256", opts)
    if result[0] {
        let claims = result[1]
        print("Authenticated user: " + claims["sub"])
    }
}
```

---

## 5. Verification & Test Suite

The test suite in `tests/stdlib_jwt_tutorial.ltl` validates:
- Cryptographic round-trip signature generation and verification.
- Tampered token rejection (`bad_signature`).
- Expiration enforcement (`expired`).
- Strict audience (`aud`) and issuer (`iss`) matching.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_jwt_tutorial.ltl
python -m lateralus_lang check examples/jwt_tutorial.ltl
```
