# ChaCha20 Stream Cipher with `stdlib/chacha20.ltl`

ChaCha20 is the stream cipher inside TLS 1.3, WireGuard, `age`, and
libsodium's default AEAD — 256-bit key, 96-bit nonce, 32-bit counter,
64-byte keystream blocks XORed with the data. `stdlib/chacha20.ltl`
implements the RFC 8439 primitive in about 100 lines of pure
Lateralus: quarter rounds, the block function, and the XOR
encrypt/decrypt (which is its own inverse).

This tutorial verifies the implementation against the RFC's own test
vectors — the strongest correctness evidence a crypto tutorial can
offer. Companion: `examples/chacha20_tutorial.ltl`.

> Scope note: Poly1305 and the AEAD construction are out of scope,
> matching the module. This is the raw stream primitive.

---

## The quarter round

ChaCha20's diffusion comes from the quarter round — the same ARX
(add-rotate-xor) shape as Salsa20:

```text
QR(a,b,c,d):
  a += b;  d ^= a;  d <<<= 16
  c += d;  b ^= c;  b <<<= 12
  a += b;  d ^= a;  d <<<=  8
  c += d;  b ^= c;  b <<<=  7
```

One round on the RFC's input `(0x11111111, 0x01020304, 0x9b8d6f43,
0x01234567)` yields `a=0xEA2A92F4` — byte-for-byte the value in RFC
8439 §2.1.1.

## The block function

`block(key, nonce, counter)` builds the 16-word state:

```text
"expand 32-byte k" (4 words) || key (8) || counter (1) || nonce (3)
```

then runs 20 rounds — 10 double-rounds of column + diagonal quarter
rounds — and adds the original state back (the feed-forward that makes
ChaCha20 non-involutive per block even though XOR is). Output is 16
little-endian u32 words = 64 keystream bytes.

With the RFC's key (`00..1f`), nonce (`00:00:00:09:00:00:00:4a:00:
00:00:00`), and counter 1, the keystream begins `10f1e7e4d13b5915…` —
the §2.3.2 vector, reproduced exactly.

## Encrypt = decrypt

`xor(key, nonce, initial_counter, data)` generates keystream blocks at
`counter, counter+1, …` and XORs each byte. Since XOR is self-inverse,
the same call decrypts. Note the counter starts at the caller's value —
RFC 8439 AEAD reserves block 0 for the Poly1305 key, so payloads
conventionally start at 1.

The §2.4.2 vector — "Ladies and Gentlemen of the class of '99…" under
the `00:00:00:00:00:00:00:4a:00:00:00:00` nonce — produces the
canonical `6e2e359a2568f980…` ciphertext, and the round-trip decrypt
returns the plaintext byte-for-byte.

## Running the tutorial

```bash
python -m lateralus_lang run examples/chacha20_tutorial.ltl
python -m lateralus_lang check examples/chacha20_tutorial.ltl
python -m pytest tests/test_chacha20_tutorial.py -x -q
```

The example inlines the module verbatim — `chacha20.ltl` is already
pure Lateralus with no external builtin dependencies, so no shims were
needed.
