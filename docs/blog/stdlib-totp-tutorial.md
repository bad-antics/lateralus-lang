# RFC 6238 TOTP Two-Factor Authentication in Lateralus

`stdlib/totp.ltl` implements RFC 6238 Time-Based One-Time Passwords (TOTP) and RFC 4226 HMAC-Based One-Time Passwords (HOTP). It provides production-ready 2FA capabilities compatible with Google Authenticator, 1Password, and Authy.

---

## 🔐 The Canonical Test Vectors

To ensure cross-platform cryptographic compliance, the module's arithmetic is pinned directly against the standard test vectors defined in **RFC 6238 Appendix B** and **RFC 4226 Section 5.4**.

Using the standard 20-byte ASCII test secret:
```text
"12345678901234567890" (Hex: 3132333435363738393031323334353637383930)
```

| Timestamp ($T$) | Counter ($T / 30$) | 6-Digit TOTP Code | 8-Digit TOTP Code |
| :---: | :---: | :---: | :---: |
| `59` | `1` | `287082` | `94287082` |
| `1111111109` | `37037036` | `081804` | `07081804` |
| `1234567890` | `41152263` | `005924` | `89005924` |
| `2000000000` | `66666666` | `279037` | `69279037` |

These values are pinned in `tests/stdlib_totp_tutorial.ltl` to prevent regressions.

---

## 🛠️ Step-by-Step Usage

### 1. Generating a One-Time Code

```lateralus
import totp

let secret = bytes_of("12345678901234567890")
let step = 30       // Default time step (30 seconds)
let digits = 6     // Standard 6-digit code

// Generate code for a specific timestamp (or -1 for current system clock)
let code = totp_totp(secret, 1234567890, step, digits, "sha1")
assert code == "005924"
```

### 2. Verifying Codes with Clock-Skew Tolerance (`drift`)

Real-world client devices often experience minor network latency or clock skew. `totp_verify` accepts a `drift` parameter (in multiples of `step_s`):

```lateralus
let now = 1234567890

// Exact window verification (drift = 0)
let valid_exact = totp_verify(secret, "005924", now, 30, 6, 0, "sha1")
assert valid_exact == true

// Validating a code submitted 30 seconds late with drift tolerance = 1 (±30s)
let valid_late = totp_verify(secret, "005924", now + 30, 30, 6, 1, "sha1")
assert valid_late == true
```

### 3. Provisioning QR-Codes for Mobile Authenticators

To display a setup QR code in client apps (such as Google Authenticator), format the credentials as a standard `otpauth://` URI:

```lateralus
let uri = totp_otpauth_uri("alice@example.com", secret, "AcmeCorp", 6, 30, "SHA1")
// Result: otpauth://totp/AcmeCorp:alice%40example.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=AcmeCorp&algorithm=SHA1&digits=6&period=30
```

---

## 🧪 Verification

Verify the tutorial files and test vectors with the Lateralus compiler:

```bash
# Check syntax and semantics
python -m lateralus_lang check tests/stdlib_totp_tutorial.ltl
python -m lateralus_lang check examples/totp_tutorial.ltl

# Run full project test suite
pytest
```
