# Two-Factor Codes with `stdlib/totp.ltl`

TOTP — the 6–8 digit codes in every authenticator app — is HOTP
(RFC 4226) evaluated at `floor(time / step)`. The whole thing is one
HMAC-SHA256, a dynamic-truncation dance, and a modulo. Small enough
to audit line by line — which is exactly what `stdlib/totp.ltl`
gives you: ~85 lines implementing RFC 4226/6238 end to end,
Google-Authenticator compatible.

This tutorial goes deeper than usual: since the runtime exposes no
byte-exact HMAC, the companion implements **SHA-256 and HMAC-SHA256
in pure Lateralus** and verifies everything against independent
Python references.

Companion: `examples/totp_tutorial.ltl`.

---

## The algorithm

```text
counter = floor(unix_time / time_step)     # 30s default
hotp    = Truncate(HMAC-SHA256(secret, counter_as_u64be)) mod 10^digits
```

1. **Counter** — 8-byte big-endian. `_u64_be` in the module uses
   `n / (1 << k)` — float division under the Python backend — so the
   companion uses `int(n / ...)`. Same class of latent bug as
   `arena`/`ldap`; documented.
2. **HMAC-SHA256** — `crypto.hmac` in the module abstracts the hash;
   the companion inlines a pure-Lateralus SHA-256 (verified:
   `sha256("")` and `sha256("abc")` match FIPS digests exactly) plus
   standard HMAC padding (block size 64, ipad `0x36`, opad `0x5c`).
   This was necessary because the builtin `hmac_sha256` shim only
   accepts strings — arbitrary secret bytes would be mangled by
   UTF-8 encoding.
3. **Dynamic truncation** — `offset = h[19] & 0x0f`, then a 31-bit
   big-endian int from `h[offset..offset+3]` (`& 127` on the first
   byte kills the sign bit).
4. **Modulo** — `bin % 10^digits`, zero-padded to `digits`.

## The API

- `hotp(secret, counter, digits, algo)` — raw counter version
- `totp(secret, at, step_s, digits, algo)` — `at < 0` means "now"
- `verify(secret, code, at, step_s, digits, drift, algo)` — checks
  `±drift` counters with **constant-time** compare (`crypto.ct_eq`)
  for clock-skew tolerance
- `otpauth_uri(account, secret, issuer, digits, step_s, algo)` —
  provisioning URI for QR codes, with base32 secret + URL-encoded
  label/issuer
- `random_secret()` — 160-bit secret via `crypto.rand_bytes`
  (needs the crypto runtime; not exercised in the companion)

## Verified vectors

Secret `"12345678901234567890"` (ASCII), SHA-256, 8 digits — every
value below was cross-checked against an independent Python
`hmac`/`hashlib`/`struct` implementation:

```text
sha256("")  = e3b0c442…7852b855     (FIPS empty-string digest)
sha256("abc")= ba7816bf…f20015ad     (FIPS "abc" digest)
hotp(7)     = 67579288
hotp(4)     = 25480556
totp T=59        = 32247374
totp T=1111111109= 34756375
totp T=1234567890= 42829826
totp T=2000000000= 78428693
totp T=20000000000=24142410
verify: exact=True, drift=1=True, wrong=False
otpauth://totp/Example:alice%40example.com?secret=GEZDGNBVGY3TQOJQ…
```

## When to use it

**Use it** for TOTP/HOTP second factors, backup-code generation, or
as a compact, auditable example of HMAC + truncation + base32. The
pure-Lateralus SHA-256 in the companion is also reusable anywhere you
need byte-exact hashing the builtin shims can't provide.

**Don't expect** SHA-1/SHA-512 HMAC variants in the companion (the
stdlib takes an `algo` param; the companion implements SHA-256 only —
the most common TOTP choice), `random_secret`'s CSPRNG here, or QR
rendering — `otpauth_uri` produces the URI; rendering is yours.

That is `stdlib/totp.ltl`: RFC 4226/6238, authenticator-app
compatible, and small enough to audit in one sitting.
