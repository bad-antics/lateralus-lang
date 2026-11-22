# Mastering CRC-32 in Lateralus: IEEE 802.3 Polynomials, Galois Arithmetic, and Frame Check Sequences

Data transmission across physical mediums—such as Ethernet cables, Wi-Fi radio frequencies, SATA disks, and compression formats (ZIP, GZIP, PNG)—inevitably encounters electromagnetic noise, bit flips, and packet loss.

**CRC-32 (Cyclic Redundancy Check, 32-bit)** is the global standard for detecting accidental alterations to raw data. Defined in **IEEE 802.3**, it evaluates binary messages as polynomials over the Galois Field $GF(2)$, computing a compact 32-bit remainder that provides near-certain detection of burst errors up to 32 bits in length.

In this tutorial, we demonstrate how to implement, optimize, and test CRC-32 natively in Lateralus.

---

## 1. Mathematical Blueprint: The IEEE 802.3 Polynomial

In $GF(2)$, addition and subtraction are identical to bitwise XOR (`^`), and multiplication corresponds to AND (`&`).

The canonical IEEE 802.3 CRC-32 generator polynomial is:

$$P(x) = x^{32} + x^{26} + x^{23} + x^{22} + x^{16} + x^{12} + x^{11} + x^{10} + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1$$

In hardware and software implementations, processing bits from Least Significant Bit (LSB) first allows shifting right. The reversed (reflected) polynomial representation is:

$$\text{Polynomial} = \mathtt{0xEDB88320} \quad (3,988,292,384_{10})$$

---

## 2. Bitwise Reduction Pipeline

For each byte entering the stream:
1. XOR the incoming byte with the lowest 8 bits of the current 32-bit CRC register.
2. For each of the 8 bits:
   - If the LSB is $1$, shift right by $1$ and XOR with `0xEDB88320`.
   - If the LSB is $0$, simply shift right by $1$.

```lateralus
fn crc32_step(crc_in: int, byte_val: int) -> int {
    let mut c = crc_in ^ byte_val;
    let poly = 3988292384; // 0xEDB88320
    let mut i = 0;
    while i < 8 {
        if (c & 1) != 0 {
            c = (c >> 1) ^ poly;
        } else {
            c = c >> 1;
        }
        i = i + 1;
    }
    return c;
}
```

Initial state begins at `0xFFFFFFFF` ($4,294,967,295$), and the final remainder is XORed with `0xFFFFFFFF` prior to return.

---

## 3. Real-World Frame Check Sequence (Ethernet & Networking)

Network interfaces append the 4-byte CRC-32 checksum to every transmitted packet frame. Upon receipt, the receiver re-evaluates the payload. If electrical interference corrupted even a single bit, the calculated checksum deviates, triggering immediate packet rejection.

See `examples/crc32_tutorial.ltl` for a demonstration detecting wire-level corruption.

---

## 4. End-to-End Verification with International Golden Vectors

We assert compliance against canonical IEEE 802.3 test vectors:
- **Empty payload (`""`)**: Resolves to `0x00000000` (`0`).
- **Canonical standard vector (`"123456789"`)**: Evaluates to `0xCBF43926` ($3,421,780,262_{10}$).

Run the compiler checks and test suites:
```bash
python -m lateralus_lang check examples/crc32_tutorial.ltl
python -m lateralus_lang check tests/stdlib_crc32_tutorial.ltl
pytest tests/test_compiler.py
```
