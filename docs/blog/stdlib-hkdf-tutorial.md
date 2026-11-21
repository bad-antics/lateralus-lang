# HKDF in Lateralus

`stdlib/hkdf.ltl` implements HMAC-based key derivation (RFC 5869). It turns one
shared secret into one or more keys of arbitrary length, which is the standard
first step for TLS 1.3, WireGuard, Noise and age handshakes.

## Extract and expand

HKDF is two steps:

- **Extract** mixes a salt and an input keying material into a
  pseudorandom key (PRK): `PRK = HMAC(salt, ikm)`.
- **Expand** stretches that PRK into output of any requested length by
  chaining HMAC calls: `T(i) = HMAC(prk, T(i-1) || info || i)`, and the
  output key material is the first `length` bytes of `T(1) || T(2) || ...`.

The `info` parameter is optional context: it is not secret, and it lets two
callers derive different keys from the same PRK without talking to each other.

## The stdlib API

```lateralus
extract(salt: list, ikm: list) -> list
expand(prk: list, info: list, length: int) -> list
derive_key(salt: list, ikm: list, info: list, length: int) -> list
derive_many(prk: list, base_info: list, key_len: int, n_keys: int) -> list
```

`extract` treats an empty salt as `HASHLEN` zero bytes, per RFC 5869.
`expand` refuses to produce more than 255 blocks (8160 bytes for SHA-256) and
returns an empty list beyond that. `derive_key` is the one-shot extract plus
expand. `derive_many` derives `n_keys` independent keys of `key_len` bytes
each from a single PRK, giving each key the info `base_info || key_index`.

## Pinned test vectors

The companion example prints two RFC 5869 (SHA-256) vectors, and
`tests/test_hkdf_tutorial.py` asserts them exactly:

| Vector | PRK | OKM |
|---|---|---|
| Test Case 1 | `077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5` | `3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865` |
| Test Case 2 | `06a6b88c5853361a06104c9ceb35b45cef760014904671014a193f40c15fc244` | `b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71cc30c58179ec3e87c14c01d5c1f3434f1d87` |

Test Case 1 derives 42 bytes, Test Case 2 derives 82 bytes, so the second
vector exercises the multi-block chaining path.

## Honest note about the example

The runnable example in `examples/hkdf_tutorial.ltl` mirrors the module's
semantics using `crypto.hmac_sign` (via `import crypto`) together with
`hex_decode` / `hex_encode`, rather than calling the module directly. The
module's own HMAC primitive, `crypto_hmac`, is not wired into the Python
backend yet, so `import hkdf` does not run today. The example reproduces the
documented `extract` / `expand` / `derive_key` / `derive_many` behaviour on the
primitives that do work, and it pins the RFC vectors so the module can be
wired up later without silently changing the output.

## Verify it

```text
python -m lateralus_lang check examples/hkdf_tutorial.ltl
python -m lateralus_lang run examples/hkdf_tutorial.ltl
```
