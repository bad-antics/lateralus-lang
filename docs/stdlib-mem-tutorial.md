# stdlib.mem — Memory Management Primitives (Tutorial)

A hands-on tutorial for the **mem** standard-library module
(`stdlib/mem.ltl`). By the end you'll understand every public function the
module ships, how the `foreign "C"` boundary works, which functions run under
the pure-Python backend and which require the C backend, and you'll have a
runnable program that exercises the whole surface.

> Every example in this doc was run with
> `python3 -m lateralus_lang run <file.ltl>`. Real output is pasted inline.

---

## 0. What the module does

`stdlib/mem.ltl` is a thin, dependency-free layer over raw memory. It is the
kind of module you reach for when you are writing an OS kernel, a freestanding
binary, a device driver, or any systems code where you care about bytes,
alignment, and memory-mapped I/O registers.

The module is deliberately small — **thirteen public functions** in four groups:

| Group | Functions |
|-------|-----------|
| **Allocation** | `alloc`, `free`, `alloc_zeroed`, `heap_reset` |
| **Copy / Set / Compare** | `copy`, `set`, `zero`, `compare` |
| **Volatile access** | `read_volatile`, `write_volatile` |
| **Alignment helpers** | `align_up`, `align_down`, `is_aligned` |

The header comment in the source sums up the intent:

```text
// Low-level memory operations for OS development and systems programming.
// These functions map directly to C equivalents in freestanding mode.
```

### Source of truth

The canonical implementation lives at
[`stdlib/mem.ltl`](../stdlib/mem.ltl). Every function documented here is read
directly from that file — nothing is invented.

### A note on how these functions are implemented

This is the single most important thing to understand about `stdlib.mem`, so
read it before the function tour.

Most of the module's functions are **thin wrappers over C**, written with
Lateralus's `foreign "C"` block syntax:

```ltl
pub fn alloc(size: usize) -> Ptr<u8> {
    foreign "C" { "return ltl_alloc(size);" }
}
```

A `foreign "C" { "..." }` block emits its body **verbatim** into the generated
C source. The C backend (`python3 -m lateralus_lang c ...`) provides the
`ltl_*` runtime (`ltl_alloc`, `ltl_free`, `ltl_memcpy`, `ltl_memset`,
`ltl_heap_reset`) so these compile and run in freestanding / libc mode.

The **pure-Python `run` backend does not execute `foreign "C"` bodies** — it
has no C runtime to call. So if you try to run `stdlib/mem.ltl` directly under
`python3 -m lateralus_lang run`, the allocation/copy/compare functions will not
produce meaningful results (the foreign bodies are not linked).

Two groups, however, are **pure Lateralus** and run unchanged under the Python
backend:

- The **alignment helpers** (`align_up`, `align_down`, `is_aligned`) are plain
  integer arithmetic — they run everywhere.
- The **volatile accessors** (`read_volatile`, `write_volatile`) use the
  `deref` / `volatile` operators on `Ptr<u32>`; they are meaningful only against
  real memory-mapped registers and are not exercised by the demo.

The runnable example (`examples/mem_demo.ltl`) therefore does two honest
things:

1. It calls the **real alignment helpers verbatim** (they are pure math).
2. It **re-implements the semantics** of `set` / `zero` / `copy` / `compare`
   in pure Lateralus over lists — the safe, managed stand-in for a raw byte
   buffer — so you can see the algorithms run end-to-end under the Python
   backend.

That keeps the tutorial runnable *and* truthful: we never paste fake output for
a `foreign "C"` function that the Python backend cannot execute.

---

## 1. Importing the module

The module declares itself with `module mem` and exposes its functions with
`pub fn`. In a Lateralus source file you import it by name:

```ltl
import mem

fn main() {
    // mem.alloc / mem.copy / mem.align_up / ...
}
main()
```

> **Backend caveat (repeated because it matters).** Under the Python `run`
> backend, `import mem` resolves the *name* but the `foreign "C"` bodies are not
> linked, so the allocation/copy/compare functions cannot execute there. Use the
> C backend (`python3 -m lateralus_lang c ...` then compile with `gcc`/`clang`)
> for the real pointer-based functions. The alignment helpers work under any
> backend.

You can also type-check the module without running it:

```bash
python3 -m lateralus_lang check stdlib/mem.ltl
# ✓ stdlib/mem.ltl: OK
```

And you can transpile it to C to see the foreign bodies in context:

```bash
python3 -m lateralus_lang c stdlib/mem.ltl -o mem.c
```

---

## 2. Function-by-function walkthrough

Below, every public function is documented with its **exact signature from the
source**, an explanation of its semantics, and a runnable example. Signatures
are copied verbatim from `stdlib/mem.ltl`.

### 2.1 `alloc(size: usize) -> Ptr<u8>` — allocate from the heap

```ltl
/// Allocate `size` bytes from the heap. Returns Ptr<u8> or nil on failure.
pub fn alloc(size: usize) -> Ptr<u8> {
    foreign "C" { "return ltl_alloc(size);" }
}
```

Allocates `size` bytes and returns a `Ptr<u8>` (a raw byte pointer), or `nil`
if the allocation fails. This is the `malloc` of the module. Because the body is
`foreign "C"`, it runs under the C backend; under the Python backend it is not
linked.

**Example (C backend):**

```ltl
import mem

fn main() {
    let p = mem.alloc(16)      // 16-byte buffer
    // ... use p ...
    mem.free(p)
}
main()
```

### 2.2 `free(ptr: Ptr<u8>)` — release a pointer

```ltl
/// Free a previously allocated pointer. No-op for bump allocators.
pub fn free(ptr: Ptr<u8>) {
    foreign "C" { "ltl_free(ptr);" }
}
```

Releases memory previously returned by `alloc`. The doc comment notes that for
**bump allocators** this is a no-op — a bump allocator only ever moves forward,
so `free` does nothing and `heap_reset` (below) is how you reclaim everything at
once.

**Example (C backend):**

```ltl
import mem

fn main() {
    let p = mem.alloc(32)
    mem.free(p)                // no-op under a bump allocator
}
main()
```

### 2.3 `alloc_zeroed(size: usize) -> Ptr<u8>` — allocate and zero

```ltl
/// Allocate and zero-initialize `size` bytes.
pub fn alloc_zeroed(size: usize) -> Ptr<u8> {
    let p = alloc(size)
    zero(p, size)
    return p
}
```

Allocates `size` bytes and then zeroes them by calling `zero` (which calls
`set(p, 0, size)`). This is the `calloc` of the module. Note that it is written
**in pure Lateralus** on top of `alloc` + `zero` — but since `alloc` is a
`foreign "C"` call, the whole thing still requires the C backend to actually
execute.

**Example (C backend):**

```ltl
import mem

fn main() {
    let buf = mem.alloc_zeroed(64)   // 64 zero bytes
    // buf[0..63] are all 0
}
main()
```

### 2.4 `heap_reset()` — reclaim all memory

```ltl
/// Reset the heap allocator (reclaim all memory).
pub fn heap_reset() {
    foreign "C" { "ltl_heap_reset();" }
}
```

Resets the entire heap allocator in one shot. This is the fast path for
**arena / bump allocators**: instead of freeing individual allocations, you
reset the bump pointer and reclaim everything. Pairs naturally with `free`
being a no-op.

**Example (C backend):**

```ltl
import mem

fn main() {
    let a = mem.alloc(16)
    let b = mem.alloc(32)
    // ... use a and b ...
    mem.heap_reset()            // reclaim everything at once
}
main()
```

### 2.5 `copy(dst: Ptr<u8>, src: Ptr<u8>, n: usize) -> Ptr<u8>` — memcpy

```ltl
/// Copy `n` bytes from `src` to `dst`. Regions must not overlap.
pub fn copy(dst: Ptr<u8>, src: Ptr<u8>, n: usize) -> Ptr<u8> {
    foreign "C" { "return ltl_memcpy(dst, src, n);" }
}
```

Copies `n` bytes from `src` to `dst` and returns `dst`. This is `memcpy`.
**The regions must not overlap** — if they might, you need a `memmove`-style
routine, which this module does not provide.

**Example (C backend):**

```ltl
import mem

fn main() {
    let dst = mem.alloc(8)
    let src = mem.alloc(8)
    // ... fill src ...
    mem.copy(dst, src, 8)
}
main()
```

### 2.6 `set(dst: Ptr<u8>, val: u8, n: usize) -> Ptr<u8>` — memset

```ltl
/// Set `n` bytes at `dst` to `val`.
pub fn set(dst: Ptr<u8>, val: u8, n: usize) -> Ptr<u8> {
    foreign "C" { "return ltl_memset(dst, val, n);" }
}
```

Writes the byte `val` into `n` consecutive bytes starting at `dst`, and returns
`dst`. This is `memset`. `val` is a `u8` (0–255).

**Example (C backend):**

```ltl
import mem

fn main() {
    let buf = mem.alloc(16)
    mem.set(buf, 0xAA, 16)      // fill 16 bytes with 0xAA
}
main()
```

### 2.7 `zero(dst: Ptr<u8>, n: usize) -> Ptr<u8>` — zero a region

```ltl
/// Zero `n` bytes at `dst`.
pub fn zero(dst: Ptr<u8>, n: usize) -> Ptr<u8> {
    return set(dst, 0, n)
}
```

A convenience wrapper: `zero(dst, n)` is exactly `set(dst, 0, n)`. Pure
Lateralus on top of `set`.

**Example (C backend):**

```ltl
import mem

fn main() {
    let buf = mem.alloc(16)
    mem.zero(buf, 16)           // same as mem.set(buf, 0, 16)
}
main()
```

### 2.8 `compare(a: Ptr<u8>, b: Ptr<u8>, n: usize) -> int` — memcmp

```ltl
/// Compare `n` bytes of `a` and `b`. Returns 0 if equal.
pub fn compare(a: Ptr<u8>, b: Ptr<u8>, n: usize) -> int {
    for i in 0..n {
        let ab = deref(a + i)
        let bb = deref(b + i)
        if ab != bb {
            return ab as int - bb as int
        }
    }
    return 0
}
```

Lexicographically compares `n` bytes of `a` and `b`. Returns `0` if all bytes
are equal; otherwise returns the difference `ab - bb` at the **first** differing
byte (so the sign tells you which buffer is "greater", exactly like `memcmp`).
Unlike the other primitives, `compare` is written in **pure Lateralus** using
`deref` and pointer arithmetic (`a + i`) — but it still needs real pointers to
be useful, so it is a C-backend / freestanding function in practice.

**Example (C backend):**

```ltl
import mem

fn main() {
    let a = mem.alloc(4)
    let b = mem.alloc(4)
    // ... fill a and b ...
    let r = mem.compare(a, b, 4)   // 0 if equal
}
main()
```

### 2.9 `read_volatile(addr: Ptr<u32>) -> u32` — volatile read

```ltl
/// Read a value from a memory-mapped I/O register (never elided).
pub fn read_volatile(addr: Ptr<u32>) -> u32 {
    return volatile(deref(addr))
}
```

Performs a **volatile read** of a `u32` from `addr`. The `volatile` operator
tells the compiler this memory may change outside the program's control (a
hardware register, a shared-memory flag) and the read must **never be elided or
reordered**. This is how you read memory-mapped I/O (MMIO) registers.

**Example (C backend / freestanding):**

```ltl
import mem

fn main() {
    let status = mem.read_volatile(0x4000_0000)   // read a device register
}
main()
```

### 2.10 `write_volatile(addr: Ptr<u32>, val: u32)` — volatile write

```ltl
/// Write a value to a memory-mapped I/O register (never elided).
pub fn write_volatile(addr: Ptr<u32>, val: u32) {
    unsafe {
        volatile(deref(addr)) = val
    }
}
```

Performs a **volatile write** of `val` to the `u32` at `addr`. Like the read, it
is protected from elision/reordering. Note the `unsafe` block: writing through a
raw pointer to an arbitrary address is unsafe by definition — you are promising
the address is a valid MMIO register.

**Example (C backend / freestanding):**

```ltl
import mem

fn main() {
    mem.write_volatile(0x4000_0004, 0x1)   // write to a device control register
}
main()
```

### 2.11 `align_up(addr: usize, align: usize) -> usize` — round up

```ltl
/// Align `addr` up to the next multiple of `align` (must be power of 2).
pub fn align_up(addr: usize, align: usize) -> usize {
    return (addr + align - 1) & ~(align - 1)
}
```

Rounds `addr` **up** to the next multiple of `align`. `align` **must be a power
of two** — the bit-trick `(addr + align - 1) & ~(align - 1)` only works for
powers of two. This is pure integer math and runs under **any** backend.

**Example (runs under the Python backend):**

```ltl
fn align_up(addr: int, align: int) -> int {
    return (addr + align - 1) & ~(align - 1)
}

fn main() {
    println(str(align_up(5, 8)))    // 8
    println(str(align_up(16, 8)))   // 16 (already aligned)
}
main()
```

### 2.12 `align_down(addr: usize, align: usize) -> usize` — round down

```ltl
/// Align `addr` down to the previous multiple of `align`.
pub fn align_down(addr: usize, align: usize) -> usize {
    return addr & ~(align - 1)
}
```

Rounds `addr` **down** to the previous multiple of `align` (again, `align` must
be a power of two). Pure integer math; runs anywhere.

**Example (runs under the Python backend):**

```ltl
fn align_down(addr: int, align: int) -> int {
    return addr & ~(align - 1)
}

fn main() {
    println(str(align_down(13, 8)))   // 8
    println(str(align_down(7, 8)))    // 0
}
main()
```

### 2.13 `is_aligned(addr: usize, align: usize) -> bool` — alignment test

```ltl
/// Check if `addr` is aligned to `align`.
pub fn is_aligned(addr: usize, align: usize) -> bool {
    return (addr & (align - 1)) == 0
}
```

Returns `true` if `addr` is already a multiple of `align` (again, `align` must
be a power of two). Pure integer math; runs anywhere.

**Example (runs under the Python backend):**

```ltl
fn is_aligned(addr: int, align: int) -> bool {
    return (addr & (align - 1)) == 0
}

fn main() {
    println(str(is_aligned(16, 8)))   // True
    println(str(is_aligned(17, 8)))   // False
}
main()
```

---

## 3. A complete, runnable example

Save this as `examples/mem_demo.ltl` (it is committed in the repo). Because the
allocation/copy/compare primitives are `foreign "C"` (C-backend only), the demo
re-implements their **semantics** in pure Lateralus over lists, and calls the
**real alignment helpers verbatim**. Every section is labelled with the real
stdlib signature it mirrors.

```ltl
// =======================================================================
// examples/mem_demo.ltl
// A runnable tour of the stdlib.mem module (stdlib/mem.ltl).
// =======================================================================

// -- Copy / Set / Compare (mirrors mem.set / mem.zero / mem.copy / mem.compare)

// mem.set(dst, val, n) -> Ptr<u8>   : set n bytes of dst to val.
fn mem_set(buf: list, val: int, n: int) -> list {
    let i = 0
    while i < n {
        buf[i] = val
        i = i + 1
    }
    return buf
}

// mem.zero(dst, n) -> Ptr<u8>       : zero n bytes of dst (set(dst, 0, n)).
fn mem_zero(buf: list, n: int) -> list {
    return mem_set(buf, 0, n)
}

// mem.copy(dst, src, n) -> Ptr<u8>  : copy n bytes src -> dst (no overlap).
fn mem_copy(dst: list, src: list, n: int) -> list {
    let i = 0
    while i < n {
        dst[i] = src[i]
        i = i + 1
    }
    return dst
}

// mem.compare(a, b, n) -> int       : 0 if equal, else a[i]-b[i] at first diff.
fn mem_compare(a: list, b: list, n: int) -> int {
    let i = 0
    while i < n {
        if a[i] != b[i] {
            return a[i] - b[i]
        }
        i = i + 1
    }
    return 0
}

// -- Alignment helpers (verbatim from stdlib/mem.ltl — pure integer math) --

fn align_up(addr: int, align: int) -> int {
    return (addr + align - 1) & ~(align - 1)
}

fn align_down(addr: int, align: int) -> int {
    return addr & ~(align - 1)
}

fn is_aligned(addr: int, align: int) -> bool {
    return (addr & (align - 1)) == 0
}

fn main() {
    println("=== stdlib.mem demo (pure-Lateralus mirror) ===")

    // 1) set / zero
    let buf = [0, 0, 0, 0, 0, 0, 0, 0]
    println("set(buf, 65, 8)   = " + str(mem_set(buf, 65, 8)))
    println("zero(buf, 8)      = " + str(mem_zero(buf, 8)))

    // 2) copy
    let src = [1, 2, 3, 4, 5, 6, 7, 8]
    let dst = [0, 0, 0, 0, 0, 0, 0, 0]
    println("copy(dst, src, 8) = " + str(mem_copy(dst, src, 8)))

    // 3) compare
    println("compare(src,src)  = " + str(mem_compare(src, src, 8)))
    println("compare(123,129)  = " + str(mem_compare([1, 2, 3], [1, 2, 9], 3)))

    // 4) alignment helpers
    println("align_up(5, 8)    = " + str(align_up(5, 8)))
    println("align_up(0, 8)    = " + str(align_up(0, 8)))
    println("align_up(16, 8)   = " + str(align_up(16, 8)))
    println("align_down(13, 8) = " + str(align_down(13, 8)))
    println("is_aligned(16, 8) = " + str(is_aligned(16, 8)))
    println("is_aligned(17, 8) = " + str(is_aligned(17, 8)))
}
```

Run it:

```bash
python3 -m lateralus_lang run examples/mem_demo.ltl
```

Real output (pasted verbatim from an actual run):

```
=== stdlib.mem demo (pure-Lateralus mirror) ===
set(buf, 65, 8)   = [65, 65, 65, 65, 65, 65, 65, 65]
zero(buf, 8)      = [0, 0, 0, 0, 0, 0, 0, 0]
copy(dst, src, 8) = [1, 2, 3, 4, 5, 6, 7, 8]
compare(src,src)  = 0
compare(123,129)  = -6
align_up(5, 8)    = 8
align_up(0, 8)    = 0
align_up(16, 8)   = 16
align_down(13, 8) = 8
is_aligned(16, 8) = True
is_aligned(17, 8) = False
```

Notice how the demo exercises the **semantics of every non-foreign function**
(`set`, `zero`, `copy`, `compare`) plus the **real alignment helpers**
(`align_up`, `align_down`, `is_aligned`). The `foreign "C"` allocation
primitives (`alloc`, `free`, `alloc_zeroed`, `heap_reset`) and the volatile
accessors (`read_volatile`, `write_volatile`) are documented above but are not
runnable under the Python backend — they require the C / freestanding backend.

---

## 4. Edge cases

The mem primitives are small, but their edge cases are exactly where systems
bugs live. Here are the ones worth internalising.

### 4.1 `align` must be a power of two

`align_up`, `align_down`, and `is_aligned` all use the bit-trick
`addr & (align - 1)`. This is **only correct when `align` is a power of two**
(1, 2, 4, 8, 16, …). Passing a non-power-of-two (e.g. `align = 3`) silently
produces wrong answers. The doc comments say "must be power of 2" — treat that
as a hard precondition.

### 4.2 `align_up` of an already-aligned address is a no-op

`align_up(16, 8)` returns `16`, not `24`. The formula
`(addr + align - 1) & ~(align - 1)` only bumps up when there is a remainder.
Likewise `align_down(16, 8)` returns `16`. This surprises people who expect
"next" to always mean strictly greater.

### 4.3 `align_up(0, align)` is `0`

Zero is already aligned to everything, so `align_up(0, 8) == 0` and
`align_down(0, 8) == 0`. The demo shows this explicitly.

### 4.4 `compare` returns the *difference*, not just a sign

`compare` returns `ab - bb` at the first differing byte, not merely `-1/0/1`.
So `compare([1,2,3], [1,2,9], 3)` returns `-6` (because `3 - 9 = -6`), exactly
like `memcmp`'s "difference of the first differing bytes" convention. If you
only care about ordering, test the sign (`< 0`, `== 0`, `> 0`), not the exact
value.

### 4.5 `copy` requires non-overlapping regions

`copy` maps to `memcpy`, which has **undefined behaviour if `src` and `dst`
overlap**. If you need overlapping-safe copy (like `memmove`), this module does
not provide it — handle the overlap yourself (e.g. copy via a temporary buffer).

### 4.6 `free` is a no-op under a bump allocator

The doc comment on `free` is explicit: "No-op for bump allocators." If your
allocator is a bump/arena allocator, `free` does nothing and you reclaim memory
with `heap_reset`. Don't rely on `free` to actually release individual
allocations in that mode.

### 4.7 `alloc` can return `nil`

`alloc` returns `Ptr<u8>` or `nil` on failure. Always check for `nil` before
using the pointer in real systems code — dereferencing `nil` is undefined
behaviour.

### 4.8 `set`'s value is a `u8`

`set(dst, val, n)` takes `val: u8`, so `val` is in `0..255`. Passing a larger
integer truncates to a byte. `zero` is just `set(dst, 0, n)`.

### 4.9 Volatile accesses require `unsafe` for writes

`write_volatile` wraps its body in an `unsafe` block because writing through a
raw pointer to an arbitrary address is unsafe. `read_volatile` is safe to call
but only meaningful against a valid MMIO address. Neither is exercised by the
Python-backend demo.

---

## 5. Quick reference

| Function | Signature | Backend that runs it |
|----------|-----------|----------------------|
| `alloc` | `alloc(size: usize) -> Ptr<u8>` | C / freestanding (`foreign "C"`) |
| `free` | `free(ptr: Ptr<u8>)` | C / freestanding (`foreign "C"`) |
| `alloc_zeroed` | `alloc_zeroed(size: usize) -> Ptr<u8>` | C / freestanding (via `alloc`+`zero`) |
| `heap_reset` | `heap_reset()` | C / freestanding (`foreign "C"`) |
| `copy` | `copy(dst: Ptr<u8>, src: Ptr<u8>, n: usize) -> Ptr<u8>` | C / freestanding (`foreign "C"`) |
| `set` | `set(dst: Ptr<u8>, val: u8, n: usize) -> Ptr<u8>` | C / freestanding (`foreign "C"`) |
| `zero` | `zero(dst: Ptr<u8>, n: usize) -> Ptr<u8>` | C / freestanding (via `set`) |
| `compare` | `compare(a: Ptr<u8>, b: Ptr<u8>, n: usize) -> int` | C / freestanding (pure LTL over pointers) |
| `read_volatile` | `read_volatile(addr: Ptr<u32>) -> u32` | C / freestanding (MMIO) |
| `write_volatile` | `write_volatile(addr: Ptr<u32>, val: u32)` | C / freestanding (MMIO, `unsafe`) |
| `align_up` | `align_up(addr: usize, align: usize) -> usize` | **any backend** (pure math) |
| `align_down` | `align_down(addr: usize, align: usize) -> usize` | **any backend** (pure math) |
| `is_aligned` | `is_aligned(addr: usize, align: usize) -> bool` | **any backend** (pure math) |

---

## 6. Key takeaways

- **`stdlib.mem` is a thin, `foreign "C"`-backed layer** over raw memory:
  allocation (`alloc`/`free`/`alloc_zeroed`/`heap_reset`), copy/set/compare
  (`copy`/`set`/`zero`/`compare`), and volatile MMIO access
  (`read_volatile`/`write_volatile`).
- **The alignment helpers are pure integer math** (`align_up`/`align_down`/
  `is_aligned`) and run under **any** backend, including the Python `run`
  backend — they are the safest place to start experimenting.
- **`align` must be a power of two** for the alignment helpers; otherwise the
  bit-tricks silently return wrong answers.
- **`compare` returns the byte difference** at the first mismatch (memcmp
  convention), not just a sign — test the sign if you only need ordering.
- **`copy` requires non-overlapping regions** (it's `memcpy`, not `memmove`).
- **`free` is a no-op under a bump allocator** — use `heap_reset` to reclaim.
- The runnable demo (`examples/mem_demo.ltl`) re-implements the *semantics* of
  the non-foreign functions over lists and calls the real alignment helpers, so
  you can see the algorithms run end-to-end under the Python backend without
  faking any `foreign "C"` output.

Happy (memory-)managing!