# Low-Level Bit Manipulation with `stdlib.bitops`

The `stdlib.bitops` module provides fast, architecture-independent bit twiddling operations for systems programming, protocol parsers, cryptographic routines, and performance-critical algorithms in Lateralus.

---

## 1. Individual Bit Operations

Inspect and mutate specific bit positions (0-indexed from least significant bit):

```lateralus
import bitops

let value = 0

// Set bit 3 (value becomes 8)
let s = bitops.bit_set(value, 3)

// Test bit state (returns bool)
let is_set = bitops.bit_test(s, 3) // true

// Toggle bit 3 (turns it back to 0)
let toggled = bitops.bit_toggle(s, 3) // 0

// Explicitly clear a bit
let cleared = bitops.bit_clear(s, 3) // 0
```

---

## 2. Bitfield Extraction and Insertion

Extract and inject contiguous bitfields without manual bit-shifting boilerplate:

```lateralus
// Extract 4 bits starting at offset 2 (bits 2..5)
let packed = 0b10111100
let field = bitops.extract_bits(packed, 2, 4) // 0b1111 (15)

// Insert 0b1010 into bits 4..7 of a target value
let target = 0x00
let updated = bitops.insert_bits(target, 0b1010, 4, 4) // 0xA0
```

---

## 3. Bit Counting and Positions

Fast population count and zero-counting primitives:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`popcount(val)`** | `(u64) -> u32` | Counts set bits (population count / Hamming weight). |
| **`clz(val)`** | `(u64) -> u32` | Counts leading zeros from the most significant bit. |
| **`ctz(val)`** | `(u64) -> u32` | Counts trailing zeros from the least significant bit. |
| **`highest_bit(val)`** | `(u64) -> int` | Returns 0-based index of MSB set, or `-1` if zero. |
| **`lowest_bit(val)`** | `(u64) -> int` | Returns 0-based index of LSB set, or `-1` if zero. |

```lateralus
let mask = 0b00101100
let ones = bitops.popcount(mask)     // 3
let tz = bitops.ctz(mask)            // 2
let msb = bitops.highest_bit(mask)   // 5
```

---

## 4. Endianness and Byte Swapping

Convert between big-endian and little-endian byte orders:

```lateralus
let le16 = bitops.bswap16(0x1234) // 0x3412
let le32 = bitops.bswap32(0x12345678) // 0x78563412
let le64 = bitops.bswap64(0x0123456789ABCDEF) // 0xEFCDAB8967452301
```

---

## 5. Rotations and Power-of-Two Utilities

Bitwise circular rotations and fast power-of-two arithmetic:

```lateralus
// Circular bit rotation
let rotated_left = bitops.rotl32(0x80000000, 1) // 0x00000001
let rotated_right = bitops.rotr32(0x00000001, 1) // 0x80000000

// Power-of-two queries and rounding
let is_p2 = bitops.is_power_of_2(16) // true
let next_p2 = bitops.next_power_of_2(17) // 32
let log_val = bitops.log2(64) // 6
```
