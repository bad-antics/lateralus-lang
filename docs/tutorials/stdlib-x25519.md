# Curve25519 Diffie-Hellman Key Exchange Tutorial (`stdlib/x25519`)

The `stdlib/x25519` module provides high-speed Diffie-Hellman key agreement over Curve25519 conforming to [RFC 7748](https://datatracker.ietf.org/doc/html/rfc7748).

Curve25519 is the state-of-the-art key exchange curve utilized across modern security protocols, including:
- **TLS 1.3** (ECDHE key agreement)
- **WireGuard** (cryptographic key exchange routing)
- **Signal Protocol** (end-to-end encrypted messaging sessions)
- **age** (file encryption tool)
- **SSH** (`curve25519-sha256`)

---

## Mathematical Architecture

Curve25519 is a Montgomery curve defined over the prime field $\mathbb{F}_{2^{255} - 19}$:
$$y^2 = x^3 + 486662x^2 + x$$

The Montgomery ladder algorithm computes scalar multiplication $k \cdot P$ using only the $x$-coordinate, bypassing projective $y$-coordinate transformations entirely and avoiding division during intermediate iterations.

Key parameters in `stdlib.x25519`:
- Prime field modulus: $P = 2^{255} - 19$ (`0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFED`)
- Montgomery curve constant: $A_{24} = (486662 - 2) / 4 = 121665$
- Generator base point: $u = 9$

---

## 1. Scalar Clamping (`clamp_scalar`)

Per RFC 7748 §5, scalar values must be clamped before point multiplication to protect against small-subgroup attacks and force the scalar to be a multiple of the cofactor 8:
- Clear lowest 3 bits: `scalar[0] & 248`
- Clear highest bit: `scalar[31] & 127`
- Set second highest bit: `scalar[31] | 64`

```lateralus
import stdlib.x25519

let raw_secret = [ /* 32 random bytes */ ]
let clamped = clamp_scalar(raw_secret)
```

---

## 2. Public Key Derivation (`derive_public`)

Derives the 32-byte public key by multiplying the private scalar by the curve base point ($u = 9$):

```lateralus
let alice_pub = derive_public(alice_priv)
// Returns 32-byte little-endian public key
```

---

## 3. End-to-End Key Agreement (`scalar_mult`)

When Alice and Bob want to establish an encrypted session:
1. Alice generates private scalar `alice_priv` and shares `alice_pub = derive_public(alice_priv)`.
2. Bob generates private scalar `bob_priv` and shares `bob_pub = derive_public(bob_priv)`.
3. Both derive the identical shared secret independently:
   - Alice computes: `shared = scalar_mult(alice_priv, bob_pub)`
   - Bob computes: `shared = scalar_mult(bob_priv, alice_pub)`

```lateralus
let shared_alice = scalar_mult(alice_priv, bob_pub)
let shared_bob   = scalar_mult(bob_priv, alice_pub)
// shared_alice == shared_bob
```

---

## Running Examples and Tests

Run the interactive tutorial:
```bash
lateralus run examples/x25519_tutorial.ltl
```

Run comprehensive unit tests:
```bash
pytest tests/test_x25519_tutorial.py -v
```
