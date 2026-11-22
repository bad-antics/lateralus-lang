# Key Derivation with `stdlib/hkdf.ltl` — and a from-scratch SHA-256

HKDF (RFC 5869) turns a shared secret into one or more cryptographic
keys: **extract** (HMAC with salt → PRK) then **expand** (iterated
HMAC → OKM). Used by TLS 1.3, WireGuard, Noise, Signal.

This tutorial verifies HKDF against the **official RFC 5869 test
vectors** — but with a twist: the shipped module cannot run at all.

## The shipped module is broken

`stdlib/hkdf.ltl` calls `crypto_hmac(s, ikm)` — a function that is
**defined nowhere in the repository** (same class of bug as
`xxhash_hash64` in simhash). Even if it existed, `crypto.ltl`'s `hmac`
wraps string-based builtins that UTF-8-encode input, corrupting
arbitrary bytes ≥ 0x80 — which RFC vectors contain.

## What this tutorial does instead

Implements SHA-256, HMAC-SHA256, and HKDF **in pure Lateralus over
byte lists**, then verifies:

- SHA-256("") = `e3b0c442…` and SHA-256("abc") = `ba7816bf…`
- HMAC-SHA256 RFC 4231 case 1 = `b0344c61…`
- **HKDF RFC 5869 Test Case 1**: PRK `07770936…`, OKM(42)
  `3cb25f25…` — exact match
- **HKDF RFC 5869 Test Case 2**: OKM(82) `b11e398d…` — exact match
- Edge cases: empty salt/info, n=255 boundary (8160 bytes OK),
  n>255 → `[]`, `derive_many`

One real bug was caught and fixed during development: the message
schedule used the round-function σ1 (`_ssig1`) instead of the schedule
σ1 (`_bsig1`) — caught precisely because the RFC vectors didn't match.

## Running the tutorial

```bash
python -m lateralus_lang run examples/hkdf_tutorial.ltl
python -m lateralus_lang check examples/hkdf_tutorial.ltl
python -m pytest tests/test_hkdf_tutorial.py -x -q
```

Companion: `examples/hkdf_tutorial.ltl` (self-contained; no imports).
