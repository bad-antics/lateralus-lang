# High-Throughput Stream Encryption with Lateralus `stdlib/chacha20.ltl` (RFC 8439)

Symmetric ciphers protect the confidentiality of packets traversing public networks. While AES remains standard, software implementations of AES without dedicated CPU hardware instructions (such as AES-NI) are susceptible to **cache-timing side-channel attacks**.

Designed by Daniel J. Bernstein and standardized under **RFC 8439** (formerly RFC 7539), **ChaCha20** is an ARX-based (Add-Rotate-Xor) stream cipher that delivers superior performance in software while operating in strict constant time across all microarchitectures. It is the default cipher in WireGuard, TLS 1.3, OpenSSH, and modern operating system entropy pools.

Lateralus includes an RFC 8439 compliant ChaCha20 implementation in `stdlib/chacha20.ltl`.

---

## 1. Mathematical Architecture & 4x4 State Matrix

ChaCha20 operates on a state represented as a $4 \times 4$ grid of 32-bit unsigned words (16 words total, 64 bytes):

$$\begin{pmatrix} c_0 & c_1 & c_2 & c_3 \\ k_0 & k_1 & k_2 & k_3 \\ k_4 & k_5 & k_6 & k_7 \\ t & n_0 & n_1 & n_2 \end{pmatrix}$$

1. **Constants ($c_0 \dots c_3$)**: Four 32-bit constants representing the ASCII string `"expand 32-byte k"` (`0x61707865`, `0x3320646e`, `0x79622d32`, `0x6b206574`).
2. **Key ($k_0 \dots k_7$)**: 256-bit secret key serialized as 8 little-endian 32-bit integers.
3. **Counter ($t$)**: 32-bit block counter, incremented for every 64-byte block processed.
4. **Nonce ($n_0 \dots n_2$)**: 96-bit initialization vector unique to each encrypted session.

### The Quarter-Round Permutation
The core mixing function operates on four words $(a, b, c, d)$ using modular addition, bitwise XOR, and cyclic bitwise rotations:

$$\begin{aligned}
a &\leftarrow (a + b) \pmod{2^{32}}, & d &\leftarrow (d \oplus a) \lll 16 \\
c &\leftarrow (c + d) \pmod{2^{32}}, & b &\leftarrow (b \oplus c) \lll 12 \\
a &\leftarrow (a + b) \pmod{2^{32}}, & d &\leftarrow (d \oplus a) \lll 8 \\
c &\leftarrow (c + d) \pmod{2^{32}}, & b &\leftarrow (b \oplus c) \lll 7
\end{aligned}$$

ChaCha20 performs **20 rounds** total: alternating 10 column rounds and 10 diagonal rounds. Finally, the working state is added word-by-word to the original input state to produce 64 bytes of pseudo-random keystream.

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `chacha20_block` | `(key: list, nonce: list, counter: int) -> list` | Generates a 64-byte keystream block for the specified counter. |
| `chacha20_xor` | `(key: list, nonce: list, counter: int, data: list) -> list` | Encrypts or decrypts arbitrary-length byte arrays via keystream XOR. |

---

## 3. Practical Example: Payload Encryption & Decryption

Because stream ciphers apply bitwise XOR ($\oplus$) against the keystream, encryption and decryption are mathematically identical operations:

$$\text{Ciphertext} = \text{Plaintext} \oplus \text{Keystream}$$
$$\text{Plaintext} = \text{Ciphertext} \oplus \text{Keystream}$$

```lateralus
import chacha20

pub fn main() {
    // 256-bit symmetric key
    let key = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
    ]

    // 96-bit nonce
    let nonce = [0, 0, 0, 0, 0, 0, 0, 74, 0, 0, 0, 0]
    let initial_counter = 1

    let message = [72, 69, 76, 76, 79] // 'HELLO'

    // Encrypt
    let encrypted = chacha20_xor(key, nonce, initial_counter, message)

    // Decrypt (same function and parameters)
    let restored = chacha20_xor(key, nonce, initial_counter, encrypted)
}
```

---

## 4. Security Critical: Nonce Management & Counter Allocation

- **Nonce Uniqueness**: You must **never reuse a Nonce** with the same Key. If two plaintexts $P_1, P_2$ are encrypted under the same Key and Nonce:
  $$C_1 \oplus C_2 = (P_1 \oplus K) \oplus (P_2 \oplus K) = P_1 \oplus P_2$$
  An eavesdropper can eliminate the key entirely and reconstruct both messages via frequency analysis.
- **Counter Offset in AEAD**: In AEAD constructions (like ChaCha20-Poly1305), **Block Counter 0** is reserved for generating the one-time Poly1305 authentication key. Payload data encryption must start at **Counter 1**.

---

## 5. Verification & Pinned RFC 8439 Test Vectors

The test suite in `tests/stdlib_chacha20_tutorial.ltl` validates `stdlib/chacha20.ltl` against the official RFC 8439 Section 2.3.2 test vectors:
- Pinned keystream output verification at `counter = 1`.
- Multi-block payload spanning round-trip integrity.

Run the test verification locally:
```bash
python -m lateralus_lang check tests/stdlib_chacha20_tutorial.ltl
python -m lateralus_lang check examples/chacha20_tutorial.ltl
```
