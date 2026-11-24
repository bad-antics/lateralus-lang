# Tutorial: Working with Raw Pointers and Memory Alignment in Lateralus (`stdlib.ptr`)

The `stdlib.ptr` module provides safe abstractions, arithmetic utilities, memory alignment helpers, and typed read/write primitives for low-level systems programming in Lateralus. While Lateralus is memory-safe by default, systems tasks such as OS kernel development, foreign function interfacing (FFI), custom allocators, and memory-mapped I/O (MMIO) require direct address calculation.

This tutorial covers:
1. **Pointer Lifecycle & Null Checks**: `null()`, `is_null()`, and `is_valid()`
2. **Pointer Arithmetic & Distance**: `offset()`, `offset_elements()`, and `diff()`
3. **Power-of-Two Memory Alignment**: `align_up()`, `align_down()`, and `is_aligned()`
4. **Typed Memory Access**: `read_u8` / `write_u8`, `read_u16` / `write_u16`, `read_u32` / `write_u32`, and `read_u64` / `write_u64`
5. **Memory-Mapped I/O (MMIO)**: Volatile reads and writes that cannot be optimized away
6. **Block Operations**: `write_bytes()`, `zero()`, and `copy_nonoverlapping()`

---

## 1. Pointer Lifecycle & Null Checks

Pointers in Lateralus are represented by `Ptr<T>`. A null pointer points to address `0`.

```lateralus
import ptr

// Initialize a null pointer
let p = ptr.null()

if ptr.is_null(p) {
    println("Pointer is null (unassigned)")
}

// Check validity
let heap_buf = ptr.offset(p, 0x1000)
if ptr.is_valid(heap_buf) {
    println("Pointer is valid (non-null)")
}
```

---

## 2. Pointer Arithmetic & Distance

Pointer offsets operate in byte units or element counts:

```lateralus
import ptr

let base = ptr.offset(ptr.null(), 1024)

// Offset by 64 bytes
let p64 = ptr.offset(base, 64)

// Offset by 4 elements of 8 bytes (e.g. u64 array indexing)
let p_elem = ptr.offset_elements(base, 4, 8)

// Compute distance between pointers
let distance = ptr.diff(p_elem, base)
assert distance == 32
```

---

## 3. Memory Alignment

Hardware DMA, cache lines, and SIMD registers require pointers to be aligned to powers of two (e.g., 4-byte, 8-byte, 16-byte, or 64-byte boundaries).

```lateralus
import ptr

let unaligned = ptr.offset(ptr.null(), 13)

// Align up to next 4-byte boundary: 13 -> 16
let a_up = ptr.align_up(unaligned, 4)

// Align down to previous 4-byte boundary: 13 -> 12
let a_down = ptr.align_down(unaligned, 4)

// Verify alignment
assert ptr.is_aligned(a_up, 4) == true
assert ptr.is_aligned(unaligned, 4) == false
```

---

## 4. Typed Read and Write Access

Writing or reading through raw pointers is performed inside `unsafe` primitives:

```lateralus
import ptr

let buffer = ptr.offset(ptr.null(), 0x2000)

// Write and read single 8-bit unsigned integer
ptr.write_u8(buffer, 0x5A)
let val8 = ptr.read_u8(buffer)
assert val8 == 0x5A

// Write and read 32-bit integer (e.g., header magic)
let header = ptr.offset(buffer, 4)
ptr.write_u32(header, 0xDEADBEEF)
let val32 = ptr.read_u32(header)
assert val32 == 0xDEADBEEF
```

---

## 5. Volatile MMIO Access

For device registers and hardware peripherals, compiler reordering or dead-store elimination must be prevented using volatile semantics:

```lateralus
import ptr

let uart_tx = ptr.offset(ptr.null(), 0x3F201000)

// Volatile write to UART transmit register
ptr.write_volatile_u32(uart_tx, 0x41) // 'A'

// Volatile read from UART status register
let status = ptr.read_volatile_u32(uart_tx)
```

---

## 6. Block Operations: Fill, Zero, and Copy

Batch memory operations map directly to optimized `memset` and `memcpy` equivalents:

```lateralus
import ptr

let src = ptr.offset(ptr.null(), 0x4000)
let dst = ptr.offset(ptr.null(), 0x5000)

// Fill 16 bytes with 0xFF pattern
ptr.write_bytes(src, 0xFF, 16)

// Zero initialize destination buffer
ptr.zero(dst, 16)

// Copy 16 elements (1 byte each) non-overlapping
ptr.copy_nonoverlapping(dst, src, 16, 1)

assert ptr.read_u8(dst) == 0xFF
```

---

## Canonical Test Vectors

| Operation | Input Address | Parameter | Result Address / Value |
|---|---|---|---|
| `null()` | - | - | `0` |
| `offset(100, 28)` | `100` | `+28` | `128` |
| `offset_elements(100, 5, 8)` | `100` | `5 * 8` | `140` |
| `diff(250, 100)` | `250`, `100` | - | `150` |
| `align_up(13, 4)` | `13` | `4` | `16` |
| `align_down(13, 4)` | `13` | `4` | `12` |
| `align_up(64, 64)` | `64` | `64` | `64` |
| `is_aligned(64, 64)` | `64` | `64` | `true` |
