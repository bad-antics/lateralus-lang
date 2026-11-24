# stdlib.spiral — Spiral Matrix Generation (Tutorial)

A hands-on tutorial for the **Spiral Wave** standard-library module
(`stdlib/spiral_wave.ltl`). By the end you'll have built an N×N matrix filled
with `1..N*N` in clockwise spiral order, printed it, and computed a
deterministic checksum over it — all in pure Lateralus.

> Every example in this doc was run with
> `python3 -m lateralus_lang run <file.ltl>`. Real output is pasted inline.

---

## 0. What the module does

The Spiral Wave module builds a square matrix and fills it with the integers
`1 .. N*N` in **clockwise spiral order**, starting at the top-left corner and
spiralling inward. For `N = 5` the result is:

```
  1  2  3  4  5
 16 17 18 19  6
 15 24 25 20  7
 14 23 22 21  8
 13 12 11 10  9
```

It's a compact, dependency-free example of nested-loop index arithmetic — a
good size to type in by hand and a useful fixture for learning the language.
(Note: the `tests/stdlib_spiral_wave_*.ltl` files are unrelated — despite the
name they exercise other stdlib modules such as argon2, kafka_wire, and xxhash,
not this spiral matrix.)

### Source of truth

The canonical implementation lives at
[`stdlib/spiral_wave.ltl`](../stdlib/spiral_wave.ltl). It defines four
functions:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `spiral_zeros` | `spiral_zeros(n: int) -> list` | Build an `n×n` matrix of zeros. |
| `spiral_build` | `spiral_build(n: int) -> list` | Fill an `n×n` matrix with `1..n*n` in clockwise spiral order. |
| `spiral_print` | `spiral_print(m: list)` | Pretty-print a square matrix with aligned columns. |
| `spiral_checksum` | `spiral_checksum(m: list) -> int` | Deterministic weighted checksum: `sum(value * (1 + row + col))`. |

> **Note on imports.** The functions in `stdlib/spiral_wave.ltl` are plain
> top-level `fn` definitions (not `pub fn`), and the Python `run` backend does
> not yet expose a `stdlib.spiral_wave` import shim. The idiomatic way to use
> them today is to **copy the function definitions into your own program** (as
> the runnable example below does) or to run the module file directly:
>
> ```bash
> python3 -m lateralus_lang run stdlib/spiral_wave.ltl
> ```

---

## 1. Running the bundled module directly

The module ships with a `main()` that builds and prints the N=5 spiral. Run it
straight from the repo root:

```bash
python3 -m lateralus_lang run stdlib/spiral_wave.ltl
```

Real output:

```
=== Spiral Matrix (N=5) ===
  1  2  3  4  5
 16 17 18 19  6
 15 24 25 20  7
 14 23 22 21  8
 13 12 11 10  9
Checksum (sum of value*(1+row+col)): 1665
```

---

## 2. Function-by-function walkthrough

### 2.1 `spiral_zeros(n)` — the empty canvas

Builds an `n×n` matrix (a list of `n` rows, each a list of `n` zeros). Lateralus
lists are built by concatenation, so each cell is appended with `row = row + [0]`.

```ltl
fn spiral_zeros(n: int) -> list {
    let m = []
    for i in range(n) {
        let row = []
        for j in range(n) {
            row = row + [0]
        }
        m = m + [row]
    }
    return m
}
```

`spiral_zeros(3)` produces `[[0,0,0],[0,0,0],[0,0,0]]`.

### 2.2 `spiral_build(n)` — the spiral fill

This is the heart of the module. It keeps four "walls" — `top`, `bottom`,
`left`, `right` — and walks them inward in four sweeps per loop:

1. **Left → right** across the top row, then move `top` down.
2. **Top → bottom** down the right column, then move `right` left.
3. **Right → left** across the bottom row (guarded by `top <= bottom`), then move `bottom` up.
4. **Bottom → top** up the left column (guarded by `left <= right`), then move `left` right.

A single counter `val` is incremented as each cell is written, so the matrix is
filled `1, 2, 3, …` in spiral order.

```ltl
fn spiral_build(n: int) -> list {
    let m = spiral_zeros(n)
    let top = 0
    let bottom = n - 1
    let left = 0
    let right = n - 1
    let val = 1

    while top <= bottom && left <= right {
        // left -> right along the top row
        let c = left
        while c <= right {
            m[top][c] = val
            val = val + 1
            c = c + 1
        }
        top = top + 1

        // top -> bottom down the right column
        let r = top
        while r <= bottom {
            m[r][right] = val
            val = val + 1
            r = r + 1
        }
        right = right - 1

        // right -> left along the bottom row
        if top <= bottom {
            let c2 = right
            while c2 >= left {
                m[bottom][c2] = val
                val = val + 1
                c2 = c2 - 1
            }
            bottom = bottom - 1
        }

        // bottom -> top up the left column
        if left <= right {
            let r2 = bottom
            while r2 >= top {
                m[r2][left] = val
                val = val + 1
                r2 = r2 - 1
            }
            left = left + 1
        }
    }

    return m
}
```

The `if top <= bottom` / `if left <= right` guards are what make **odd-sized**
spirals (which have a single centre cell) terminate correctly without
double-writing the middle.

### 2.3 `spiral_print(m)` — aligned pretty-printing

Walks the matrix row by row and right-pads each cell so columns line up:
single-digit cells get two leading spaces, double-digit cells get one.

```ltl
fn spiral_print(m: list) {
    let n = len(m)
    let i = 0
    while i < n {
        let line = ""
        let j = 0
        while j < n {
            let cell = m[i][j]
            let pad = ""
            if cell < 10 {
                pad = "  "
            } else {
                pad = " "
            }
            line = line + pad + str(cell)
            j = j + 1
        }
        println(line)
        i = i + 1
    }
}
```

### 2.4 `spiral_checksum(m)` — a deterministic fingerprint

Computes `sum over all cells of value * (1 + row + col)`. Because the spiral
layout is deterministic, this checksum is a stable fingerprint of the matrix —
handy for tests. For `N = 5` it equals **1665**.

```ltl
fn spiral_checksum(m: list) -> int {
    let n = len(m)
    let total = 0
    let i = 0
    while i < n {
        let j = 0
        while j < n {
            total = total + m[i][j] * (1 + i + j)
            j = j + 1
        }
        i = i + 1
    }
    return total
}
```

---

## 3. A complete, runnable example

Save this as `examples/spiral_wave_demo.ltl` (it is committed in the repo). It
includes all four functions plus a `main()` that exercises each one: it prints
the raw zero canvas from `spiral_zeros`, builds and prints a 4×4 spiral with
`spiral_build` + `spiral_print`, and prints regression checksums from
`spiral_checksum` for N=1, N=4, N=5.

```ltl
// =======================================================================
// examples/spiral_wave_demo.ltl
// A complete, runnable tour of the stdlib.spiral wave (stdlib/spiral_wave.ltl).
// Run with:  python3 -m lateralus_lang run examples/spiral_wave_demo.ltl
// =======================================================================

// Build an n×n matrix of zeros.
fn spiral_zeros(n: int) -> list {
    let m = []
    for i in range(n) {
        let row = []
        for j in range(n) {
            row = row + [0]
        }
        m = m + [row]
    }
    return m
}

// Fill an n×n matrix with 1..n*n in clockwise spiral order.
fn spiral_build(n: int) -> list {
    let m = spiral_zeros(n)
    let top = 0
    let bottom = n - 1
    let left = 0
    let right = n - 1
    let val = 1

    while top <= bottom && left <= right {
        let c = left
        while c <= right {
            m[top][c] = val
            val = val + 1
            c = c + 1
        }
        top = top + 1

        let r = top
        while r <= bottom {
            m[r][right] = val
            val = val + 1
            r = r + 1
        }
        right = right - 1

        if top <= bottom {
            let c2 = right
            while c2 >= left {
                m[bottom][c2] = val
                val = val + 1
                c2 = c2 - 1
            }
            bottom = bottom - 1
        }

        if left <= right {
            let r2 = bottom
            while r2 >= top {
                m[r2][left] = val
                val = val + 1
                r2 = r2 - 1
            }
            left = left + 1
        }
    }

    return m
}

// Pretty-print a square matrix with aligned columns.
fn spiral_print(m: list) {
    let n = len(m)
    let i = 0
    while i < n {
        let line = ""
        let j = 0
        while j < n {
            let cell = m[i][j]
            let pad = ""
            if cell < 10 {
                pad = "  "
            } else {
                pad = " "
            }
            line = line + pad + str(cell)
            j = j + 1
        }
        println(line)
        i = i + 1
    }
}

// Deterministic weighted checksum: sum of value * (1 + row + col).
fn spiral_checksum(m: list) -> int {
    let n = len(m)
    let total = 0
    let i = 0
    while i < n {
        let j = 0
        while j < n {
            total = total + m[i][j] * (1 + i + j)
            j = j + 1
        }
        i = i + 1
    }
    return total
}

fn main() {
    // 1) Show the raw zero canvas before filling.
    println("--- spiral_zeros(3) ---")
    spiral_print(spiral_zeros(3))

    // 2) Build and print a 4x4 spiral.
    println("--- spiral_build(4) ---")
    let m4 = spiral_build(4)
    spiral_print(m4)

    // 3) Checksums across sizes act as a regression fingerprint.
    println("--- checksums ---")
    println("N=1: " + str(spiral_checksum(spiral_build(1))))
    println("N=4: " + str(spiral_checksum(m4)))
    println("N=5: " + str(spiral_checksum(spiral_build(5))))
}

main()
```

Run it:

```bash
python3 -m lateralus_lang run examples/spiral_wave_demo.ltl
```

Real output:

```
--- spiral_zeros(3) ---
  0  0  0
  0  0  0
  0  0  0
--- spiral_build(4) ---
  1  2  3  4
 12 13 14  5
 11 16 15  6
 10  9  8  7
--- checksums ---
N=1: 1
N=4: 564
N=5: 1665
```

Notice how the demo exercises **all four** functions: `spiral_zeros` (the blank
canvas), `spiral_build` + `spiral_print` (the 4×4 spiral), and `spiral_checksum`
(the regression fingerprints).

---

## 5. Edge cases: the smallest spirals

The same four functions work for any `n >= 1`. The interesting cases are the
tiny ones, where the four-wall walk has to terminate gracefully:

- **N=1** — a single cell; the spiral is just `1`.
- **N=2** — the smallest *even* spiral; there is no centre cell, so the four
  sweeps meet cleanly.
- **N=3** — the smallest *odd* spiral with a single centre cell (`9`), which is
  exactly the case the `if top <= bottom` / `if left <= right` guards protect.

A second runnable program, `examples/spiral_wave_edge_cases.ltl` (committed in
the repo), prints all three:

```bash
python3 -m lateralus_lang run examples/spiral_wave_edge_cases.ltl
```

Real output:

```
--- N=1 ---
  1
checksum: 1
--- N=2 ---
  1  2
  4  3
checksum: 22
--- N=3 ---
  1  2  3
  8  9  4
  7  6  5
checksum: 143
```

Notice the N=2 fill order (`1 2 / 4 3`): after the top row `1 2` and the right
column `3`, the bottom row is swept right-to-left (`4`) and the left column is
empty because `left <= right` is already false — no double-write, no crash.

---

## 6. Playing with other sizes

The checksums double as a regression fingerprint — if you ever change the fill
order, these numbers move:

### Known checksums

| N | checksum |
|---|----------|
| 1 | 1 |
| 2 | 22 |
| 3 | 143 |
| 4 | 564 |
| 5 | 1665 |

These make handy assertions in your own tests — bake the expected number into a
`check(...)` call and you have a one-line regression guard on the fill order.

---

## 7. Key takeaways

- **Nested loops + four moving walls** is the whole trick behind a spiral fill.
- **Guard the bottom/left sweeps** (`if top <= bottom`, `if left <= right`) so
  odd-sized matrices don't overwrite their centre cell.
- Lateralus lists grow by concatenation (`xs = xs + [v]`) and index-assign with
  `m[i][j] = v`.
- `str(x)` coerces numbers to strings for `+` concatenation and `println`.
- The checksum `sum(value * (1 + row + col))` is a cheap, deterministic
  fingerprint of the layout — perfect for regression tests.

Happy spiralling!