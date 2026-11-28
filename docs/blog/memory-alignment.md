# Round an offset with `stdlib/mem.ltl`

Suppose a 13-byte header occupies offsets 0 through 12. An 8-byte alignment requirement means the next field can start at offset 16, leaving three bytes of padding. To find the start of the 8-byte block containing offset 13, round down to 8.

```lateralus
let next_field = align_up(13, 8)      // 16
let block_start = align_down(13, 8)   // 8
let on_boundary = is_aligned(13, 8)    // false
```

The three helpers take a nonnegative byte address or offset and a **positive power of two** for the alignment. Use values such as 1, 2, 4, 8, and 16. An address already on a boundary is returned unchanged by `align_up` and `align_down`. Alignment 1 leaves every address unchanged. Keep the rounded result and the intermediate sum in `align_up` within the range of `usize` when using fixed-width targets.

For alignment 8, the low three bits of a valid address are zero. `align_down` clears those bits. `align_up` adds 7 before clearing them, which advances a nonaligned address to the next boundary and preserves a boundary address. `is_aligned` checks the low bits without rounding.

## Run the example

From the repository root, run this with Python 3.10 or later.

```bash
python -m examples.mem_alignment
```

The example reads the three function definitions from [`stdlib/mem.ltl`](../../stdlib/mem.ltl) and runs them with the Python backend. It selects only the numeric helpers so the example works without a native allocator or memory-mapped I/O.

The example checks these fixed vectors before printing the result.

| Offset | Alignment | Down | Up | Aligned |
| ---: | ---: | ---: | ---: | :--- |
| 0 | 8 | 0 | 0 | true |
| 13 | 8 | 8 | 16 | false |
| 16 | 8 | 16 | 16 | true |
| 17 | 8 | 16 | 24 | false |
| 13 | 1 | 13 | 13 | true |
