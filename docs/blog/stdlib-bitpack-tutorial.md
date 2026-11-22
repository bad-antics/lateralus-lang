---
title: "Sub-Byte Integer Bitpacking: Fixed-Width Telemetry Compression & ZigZag Encoding in Lateralus"
description: "A deep-dive tutorial on stdlib/bitpack.ltl — packing signed and unsigned small integers into dense 32-bit words using ZigZag mapping, bitmask extraction, and SIMD-friendly columnar layout."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["bitpack", "compression", "bitwise", "binary-formats", "standard-library"]
---

# Sub-Byte Integer Bitpacking: Fixed-Width Telemetry Compression & ZigZag Encoding in Lateralus

Columnar analytics engines (Parquet, Arrow) and IoT telemetry links frequently transmit millions of small integers whose dynamic range fits in 4, 8, or 16 bits rather than full 64-bit machine words.

The **`stdlib/bitpack.ltl`** module provides deterministic bit-level packing, unpacking, bitset extraction, and signed ZigZag mapping to achieve up to **8× memory density** with $O(1)$ random-access unpacking.

---

## 1. Mathematical Formulation

### Unsigned Multi-Lane Word Packing
Four unsigned 8-bit integers $(b_0, b_1, b_2, b_3) \in [0, 255]^4$ pack into a single 32-bit word $W \in [0, 2^{32}-1]$ in little-endian lane order:

$$W = \sum_{i=0}^{3} (b_i \bmod 256) \cdot 256^i$$

Each lane $i \in \{0, 1, 2, 3\}$ is recovered in $O(1)$ time via division and radix modulus:

$$b_i = \left\lfloor \frac{W}{256^i} \right\rfloor \bmod 256$$

### Signed ZigZag Bijection ($\mathbb{Z} \to \mathbb{N}_0$)
Signed delta values $v \in [-128, 127]$ are mapped bijectively onto unsigned bytes $z \in [0, 255]$ so small negative and positive magnitudes both occupy low unsigned codes:

$$\text{zigzag}(v) = \begin{cases} 2v & \text{if } v \ge 0 \\ -2v - 1 & \text{if } v < 0 \end{cases}, \qquad \text{unzigzag}(z) = \begin{cases} z / 2 & \text{if } z \equiv 0 \pmod 2 \\ -(z + 1) / 2 & \text{if } z \equiv 1 \pmod 2 \end{cases}$$

---

## 2. Runnable Lateralus Implementation

From `examples/bitpack_tutorial.ltl`:

```ltl
pub fn zigzag_encode(v) {
    if v >= 0 { return v * 2 }
    return (-v * 2) - 1
}

pub fn zigzag_decode(z) {
    if (z % 2) == 0 { return z / 2 }
    return -((z + 1) / 2)
}

pub fn pack_u8x4(b0, b1, b2, b3) {
    return (b0 % 256) + ((b1 % 256) * 256) + ((b2 % 256) * 65536) + ((b3 % 256) * 16777216)
}

pub fn unpack_u8_lane(word, lane) {
    let shift = 1
    let i = 0
    while i < lane {
        shift = shift * 256
        i = i + 1
    }
    return (word / shift) % 256
}
```

---

## 3. Pinned Verification Vectors

| Operation | Input Vector | Packed Representation | Unpacked Round-Trip |
| :--- | :--- | :--- | :--- |
| `pack_u8x4(10, 20, 30, 40)` | `[10, 20, 30, 40]` | `673059850` (`0x281E140A`) | `[10, 20, 30, 40]` |
| `zigzag_encode(-1)` | `-1` | `1` | `-1` |
| `zigzag_encode(1)` | `1` | `2` | `1` |
| `zigzag_encode(-64)` | `-64` | `127` | `-64` |
