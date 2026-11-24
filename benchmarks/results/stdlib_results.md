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
| `lz4` 4 MB round-trip | not run — see blockers | 2.21 s | 0.29 s |
| `chacha20` 1 MB | not run — see blockers | 1.31 s | 0.06 s |
| `aho_corasick` 1 MB / 1k patterns | not run — see blockers | 0.34 s | 0.10 s |
| `radix_sort_u32` 100k | **0.64 s** (incl. ~0.15 s startup) | 0.13 s | 0.04 s |

Throughput for the one workload that does run end to end:
**2 MiB / 0.65 s ≈ 3.2 MB/s** including input generation, which is in line with
the ~5–10 MB/s noted in `stdlib/xxhash.ltl`'s own header.

## Correctness (all three languages agree where they run)

```
xxhash 1673070f3eb5acc9
lz4 ok:4194304:45d451f4:4210753
chacha20 32aa25005fe5f3a9:b1bffb37
aho_corasick 751
radix_sort_u32 000017df:ffffe0a8:5301c95d
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
   and does not parse:
   `ParseError: expected type name (got LBRACKET '[')` at line 4. Workload 3
   needs a real LTL port before it can run here.
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
