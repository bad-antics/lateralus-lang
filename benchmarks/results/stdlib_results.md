# Stdlib micro-benchmark results

Second chapter of the speed story: the first set (`fib`, `sieve`, `mandelbrot`,
`binary_trees`, `nbody`) measures raw compute. These five measure real
workloads — hashing, compression, stream cipher, multi-pattern search, integer
sorting — at the sizes a user would actually push through them.

Measurements taken 2026-11-23 on macOS 27.0.1 / Apple M2 / 8 GB,
Python 3.12.14, Node 24.x, gcc -O2. Best of 3 wall-clock runs, one process per
workload. Lateralus ran through `python -m lateralus_lang run`.

## Workloads

| # | Workload | Input |
|---|---|---|
| 1 | `xxhash64` | 2 MB pseudo-random bytes |
| 2 | `lz4` compress + decompress round-trip | 4 MB pseudo-random bytes |
| 3 | `chacha20` keystream | 1 MB, RFC 8439 key/nonce |
| 4 | `aho_corasick` | 1,000 patterns over 1 MB of text |
| 5 | `radix_sort_u32` | 100,000 u32 keys |

Inputs come from a shared XorShift32 generator with fixed seeds, implemented
identically in all three languages, so the digests below are directly
comparable.

## Wall time

| Workload | Lateralus (interp) | Python | Node |
|---|---|---|---|
| `xxhash64` 2 MB | **0.65 s** (incl. ~0.15 s startup) | 0.35 s | 0.22 s |
| `lz4` round-trip | **256 KB in 59.15 s**; 4 MB does not finish — see scaling below | 2.21 s @ 4 MB | 0.29 s @ 4 MB |
| `chacha20` 1 MB | **1.81 s** | 1.31 s | 0.06 s |
| `aho_corasick` 1 MB / 1k patterns | **521 s**, 751 matches (run outside the CLI's 60 s cap) | 0.34 s | 0.10 s |
| `radix_sort_u32` 100k | **0.64 s** (incl. ~0.15 s startup) | 0.13 s | 0.04 s |

Throughput for the one workload that does run end to end:
**2 MiB / 0.65 s ≈ 3.2 MB/s** including input generation, which is in line with
the ~5–10 MB/s noted in `stdlib/xxhash.ltl`'s own header.

### chacha20: the module exists twice, and one copy is Rust

`std/crypto/chacha20.ltl` (216 lines) is Rust pseudo-code and does not parse.
`stdlib/chacha20.ltl` (100 lines) is real Lateralus and runs. The assembler now
takes the stdlib copy:

```python
"chacha20": [ROOT / "stdlib" / "chacha20.ltl"],
```

1 MB of data from the shared XorShift32 stream (seed `0x0BADF00D`), RFC 8439 key
`00..1f` and nonce `00..0b`, counter starting at 1:

```
Lateralus 32aa25005fe5f3a9:b1bffb37   1.81 s
Python    32aa25005fe5f3a9:b1bffb37
```

Byte-identical, first eight ciphertext bytes and an adler32 over the whole
megabyte.

One caveat: the driver drives `block()` directly and XORs into a preallocated
list rather than calling `xor()`, because `xor()` appends with
`out = out + [...]` per byte and is quadratic at megabyte scale — the same
pattern as `lz4` and `xxhash64`.

### aho_corasick: two blockers, both real

1. **`stdlib/aho_corasick.ltl` cannot run as shipped.** It calls `char_at(text, i)`
   in `build`, `find_all` and `find_all_starts`, but `char_at` is neither a
   builtin nor defined anywhere in `stdlib/`. The driver defines it
   (`fn char_at(s: str, i: int) -> str { return s[i] }`) so the workload can run
   at all; the module itself needs that helper.
2. **`lateralus run` kills anything over 60 s.** `compiler.py` runs the
   transpiled script with `subprocess.run(..., timeout=60)` and no flag to raise
   it, so a 1 MB scan cannot be measured through the CLI at all — it dies with
   `Script execution timed out (60s)`. The numbers below come from transpiling
   to Python and running the result directly, which is the only way to get a
   number past the cap.

Correctness at both sizes, against the Python reference with the same seeds:

| Text | Lateralus | Python |
|---|---|---|
| 64 KB | 750 matches, 2.32 s | 750 matches |
| 1 MB | **751 matches, 521 s** | 751 matches |

The 1 MB number is 220× the 64 KB time for 16× the input, i.e. the automaton
builder is quadratic: `ac_new_node()` appends with `gm = gm + [{}]` once per
node, so a 1,000-pattern automaton pays that cost thousands of times. The scan
itself is linear; the build is not.

### lz4: why the Lateralus column is 256 KB, not 4 MB

`stdlib/lz4.ltl` appends to its output with `out = out + [...]`, once per literal
byte and once per match, so the interpreter's cost is quadratic in the input.
Measured on this machine with the same driver, seed and digest:

| Input | Wall time | Growth |
|---|---|---|
| 64 KB | 3.91 s | — |
| 128 KB | 14.55 s | 3.7× |
| 256 KB | 59.15 s | 4.1× |

Four megabytes is 16× the 256 KB input, so quadratic scaling puts it near
**4 hours** — not a measurement anyone will reproduce. At 256 KB the digest is
`ok:262144:656b0b76:263173`, which is byte-identical to the Python reference at
the same size, so the implementation is correct; it is the output-building
pattern that does not scale. Preallocating the output and assigning by index is
the fix, and the same pattern change took `xxhash64` from 28 s to 0.65 s at
2 MB.

## Correctness (all three languages agree where they run)

```
xxhash       1673070f3eb5acc9                     (2 MB)         all three agree
lz4          ok:262144:656b0b76:263173            (256 KB)       Python agrees
chacha20     32aa25005fe5f3a9:b1bffb37            (1 MB)         Python agrees
aho_corasick 751                                 (1 MB / 1k)    Python agrees
radix_sort   000017df:ffffe0a8:5301c95d           (100k keys)    Python agrees
```

Lateralus produces `1617644453214137545` for workload 1, which is
`0x1673070f3eb5acc9` — identical to Python and Node.
Workload 5 prints `000017df:ffffe0a8:5301c95d` in all three languages, so the
radix sort agrees on the first key, the last key, and an adler32 over the whole
sorted buffer.

Cross-language agreement alone is weak evidence, so the implementations are
pinned to published vectors instead:

- `xxh64("")` = `ef46db3751d8e999`
- `xxh64("abc")` = `44bc2cf5ad770999`
- `xxh64("Nobody inspects the spammish repetition")` = `fbcea83c8a378bf1`
- `adler32("Wikipedia")` = `11e60398`
- ChaCha20 block against RFC 8439 §2.4.2 — asserted at startup in both
  `stdlib_bench.py` and `stdlib_bench.js`, so a regression fails the run instead
  of quietly changing a number.

Two real defects were found while pinning these:

1. The Python LZ4 bucket hash did not wrap to 32 bits, so it picked different
   candidates than the JS crawler and produced a 27-byte-larger block.
2. The ChaCha20 state had the nonce in the wrong words (words 16–18 instead of
   13–15), which silently ignored the nonce entirely.

## Blockers hit while finishing the Lateralus side

These are reported rather than papered over, because each one is a real gap a
contributor would hit:

1. **`std/crypto/chacha20.ltl` is not Lateralus source.** It is Rust pseudo-code
   (`const CONSTANTS: [u32; 4]`, `fn quarter_round(state: &mut [u32; 16], …)`)
   and does not parse: `ParseError: expected type name (got LBRACKET '[')`.
   Resolved for this benchmark by assembling from `stdlib/chacha20.ltl`, which
   *is* a real LTL implementation of the same primitive — but the two files
   disagree about which one is canonical, and `std/crypto/` is the one a reader
   will open first.
2. **The C99 backend cannot compile `list`.** `lateralus c` on any module that
   takes a `list` parameter emits `static int64_t read_u64_le(list buf, …)`,
   and `gcc` then fails with `unknown type name 'list'`, so the
   `lateralus-c99` column from the first benchmark set has no counterpart here.
3. **Naive list building is quadratic.** `xs = xs + [b]` per byte makes 256 KB
   take 28 s of interpreter time while the hashing itself takes 0.36 s —
   a 78× overhead that looks like a language-performance problem and is really a
   library-pattern problem. Preallocating with `[0] * n` and assigning by index
   brings 2 MB down to 0.65 s. Worth a note in the docs.

## Reproducing

```bash
python3 benchmarks/reference/stdlib_bench.py all
node    benchmarks/reference/stdlib_bench.js  all
diff <(python3 benchmarks/reference/stdlib_bench.py all) \
     <(node    benchmarks/reference/stdlib_bench.js  all)   # must be empty

python3 tools/assemble_stdlib_micro.py xxhash > build/stdlib_micro_xxhash.ltl
python3 -m lateralus_lang run build/stdlib_micro_xxhash.ltl
```
