# Poly1305 One-Time MACs with `stdlib/poly1305.ltl`

Poly1305 is the message-authentication half of ChaCha20-Poly1305 — the
AEAD construction that protects most of the world's TLS 1.3 traffic. It
takes a 256-bit one-time key `r || s` and a message, and produces a
16-byte tag an attacker can't forge.

`stdlib/poly1305.ltl` implements it in about 80 lines of pure arithmetic
— no bignum library, because Lateralus ints are already arbitrary
precision. This tutorial walks the algorithm and pins it against the
RFC 8439 test vectors. Companion: `examples/poly1305_tutorial.ltl`.

---

## The key: `r || s`, and why clamping matters

The 32-byte key splits in half:

- **`r`** (first 16 bytes) — the multiplier. Before use it must be
  *clamped*: certain bits are forced to zero so `r` has special form
  that makes the security proof work. RFC 8439 §2.5.1 clears the top
  four bits of `r3/r7/r11/r15` and the bottom two bits of
  `r4/r8/r12` — equivalently `r &= 0x0ffffffc0ffffffc0ffffffc0fffffff`.
- **`s`** (last 16 bytes) — a one-time pad added at the end.

The clamp is the kind of detail that's easy to skip and impossible to
notice until your tags don't match anyone else's — which is exactly why
the tutorial demonstrates it (STEP 5: an all-`0xff` `r` clamps down to
`21267647620597763993911028882763415551`).

## The accumulator: arithmetic mod 2¹³⁰−5

The core is a polynomial evaluation in the finite field mod
`p = 2^130 − 5` — a prime chosen because reduction is cheap (fold the
top bits back with a couple of adds). For each 16-byte block:

```text
n_i = little-endian(block) with a 1 bit appended (the 0x01 pad byte)
acc = (acc + n_i) * r  (mod p)
```

The `0x01` byte appended after each block (even the last, zero-padded)
is what makes Poly1305 a *polynomial* MAC rather than a plain hash —
it encodes block boundaries unambiguously.

Finally `tag = (acc + s) mod 2^128`, emitted little-endian.

## Verify: constant-time comparison

`verify(tag_a, tag_b)` doesn't use `==` — it ORs together all byte
differences and checks for zero at the end. Early-exit comparison leaks
*which byte* differed through timing; constant-time comparison doesn't.
It's six lines and it's the difference between a MAC and a MAC that
leaks.

## The one-time rule

The key must be fresh per message — reusing `(r, s)` across two messages
lets an attacker recover `r` and forge tags for *any* message (the
classic two-time pad break). In practice `r` and the first half of `s`
come from a stream cipher (ChaCha20 block 0); the module doc says this
plainly: "MUST use a fresh key per message."

## Running the companion

```text
STEP 1 RFC8439 vector 1:
  a8061dc1305136c6c22b8baf0c0127a9
STEP 2 RFC8439 vector 2:
  1020e8c25c2d34db3d2154327530594a
STEP 3 empty message, zero key:
  00000000000000000000000000000000
STEP 4 verify round-trip:
  verify(good)=True verify(bad)=False
STEP 5 clamping demo — r high nibble forced down:
  clamped r = 21267647620597763993911028882763415551
```

Both STEP 1 and STEP 2 reproduce the RFC 8439 §2.5.2 test vectors
byte-for-byte — the strongest possible pin for a crypto primitive. I
verified them independently against a Python reference implementation
after catching my own initially-misremembered vector-2 expectation.
`tests/test_poly1305_tutorial.py` pins the transcript.

## When to use it

**Use it** as a building block: implement or audit an AEAD mode,
understand what Poly1305 contributes (integrity + authenticity, not
confidentiality), or verify a ChaCha20-Poly1305 implementation against
known vectors.

**Don't use it** directly for message authentication — the one-time key
requirement makes it unusable standalone. And don't use it for
anything secret-adjacent without a careful review: this is a teaching
implementation, not a audited crypto library. For production, use a
vetted AEAD construction.

That is `stdlib/poly1305.ltl`: clamping, a 130-bit prime, one pad byte
per block, and test vectors that prove it interoperates with the RFC.
