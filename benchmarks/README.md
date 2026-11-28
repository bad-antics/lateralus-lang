# Lateralus Benchmarks

Cross-language micro-benchmarks comparing Lateralus against CPython and
Node.js on ten workloads: five canonical compute benchmarks plus five
stdlib benchmarks (real-workload codec, crypto, and search speed).

## Structure

    benchmarks/
      src/              Lateralus source (.ltl) — one per benchmark
      reference/        Python + JavaScript reference implementations
      results/          results.json + results.md (generated)
                        + stdlib_results.md (stdlib benchmarks only)
      run_benchmarks.py Harness

Each benchmark is implemented **three times** with the same algorithm,
same constants, and same expected output. The harness verifies that all
three backends produce byte-identical output before recording timings.

## Benchmarks

| Name         | Workload                                   | Output  |
|--------------|--------------------------------------------|---------|
| fib          | naïve recursive Fibonacci(32)              | 2178309 |
| sieve        | Sieve of Eratosthenes up to 50,000         | 5133    |
| mandelbrot   | 150×100 grid, 255 max iterations           | 719122  |
| binary_trees | Allocate & traverse a depth-12 binary tree | 8191    |
| nbody        | 5-body gravitational sim, 5000 steps       | ≈ −14073.19 |

### Stdlib benchmarks

Real-workload codec, crypto, and search speed — the second chapter of the
speed story. Each uses deterministic inputs (a glibc LCG and a fixed
61-word list, same seeds in all three implementations) so the outputs are
reproducible and cross-checked byte-for-byte.

| Name         | Workload                                              | Output |
|--------------|-------------------------------------------------------|--------|
| xxhash64     | XXH64 over 2 MB of LCG bytes (seed 777)               | 16759434631272806465 |
| lz4_rt       | LZ4 compress + decompress round-trip of 4 MB of text (seed 12345) | `2165510 11572300857478106302 2001074385271547492` |
| chacha20     | ChaCha20 encrypt 1 MB of LCG bytes (seed 999), key 0..31, nonce 0, counter 1 | 10941187508525638281 |
| aho_corasick | Aho-Corasick: 1,000 patterns in 1 MB of text         | `26949 213 15 854 1048575 13354998 14056156306` |
| radix_sort_u32 | LSD radix sort of 100,000 u32 keys (seed 2024)      | `112674 … 255117 4294921298 … 4294949596 214657873537904` |

Output formats: `xxhash64` and `chacha20` print the XXH64 of the result;
`lz4_rt` prints `<compressed_len> <xxhash64(compressed)>
<xxhash64(decompressed)>` (the decompressed hash equals the hash of the
original text, proving the round-trip); `aho_corasick` prints
`<hit_count> <first_pid> <first_end> <last_pid> <last_end> <sum_pid>
<sum_end>`; `radix_sort_u32` prints `<first 5> <last 5> <sum>`.

Results for these five are also written to
[`results/stdlib_results.md`](./results/stdlib_results.md).

The combined source file is [`src/stdlib_bench.ltl`](./src/stdlib_bench.ltl):
a single program that imports all five stdlib modules and runs all five
workloads in one process (verified by `tests/test_stdlib_benchmarks.py`).
The five timed micro-benchmarks live in their own files so the harness can
time each one separately; `stdlib_bench.ltl` is the integration run.

## Running

    python3 benchmarks/run_benchmarks.py --iters 5 --warmup 2

Output is written to `benchmarks/results/results.json` and
`benchmarks/results/results.md`.

## Methodology & Caveats

- **Wall time** measured via `time.perf_counter()` wrapping
  `subprocess.run` — includes interpreter startup.
- 2 warmup runs + 5 measured runs per backend; **median** reported.
- Lateralus has **two execution paths** in the harness:
  1. `lateralus run file.ltl` — tree-walking interpreter (correctness-first,
     pays ~200 ms compile-every-run startup cost).
  2. `lateralus c file.ltl && gcc -O2` — **native C99 binary**. Today this
     covers 4 of 10 benchmarks (`fib`, `sieve`, `mandelbrot`, `nbody`)
     end-to-end with byte-identical output to the interpreter and Node.js.
     The last canonical one (`binary_trees`) uses `fn make(d) -> any`
     returning either an `int` sentinel or a `Tree` struct — `any`-typed
     returns with mixed primitive/struct variants aren't supported by the
     typed C codegen yet. It's skipped rather than faked.
     The five stdlib benchmarks are also skipped on the C99 path: the C
     codegen turns `import` into a comment (so the stdlib modules are
     undeclared) and cannot compile the `[0] * n` + index-assignment data
     generators. Both gaps are C-codegen work, out of scope for the
     benchmark-ingest bounty; the interpreter, Python, and Node paths all
     run and cross-check.
- On the workloads the C99 backend covers today, Lateralus is currently
  **~60× faster than CPython** (fib), **~30× faster than CPython** (sieve
  and mandelbrot), **~40× faster than CPython** (nbody). Those numbers are
  with `gcc -O2` and no further tuning — LLVM IR + typed-IR specialisation
  are on the v4.0 roadmap.
- All results are reproducible; contributions welcome.

## Honest Results (current)

C99 codegen produces tiny native binaries (16 KB stripped) that handily
beat CPython on compute-bound workloads. The tree-walking interpreter
remains 100×+ slower — that is expected behaviour for a ~2k-line reference
implementation written in Python for clarity, not speed. The roadmap for
closing the remaining gap is:

1. **C backend parity** — close the three gaps above (list-rep, enums,
   list-literal typing) so all five benchmarks run through C99
2. **Compile-and-cache** for the interpreter path
   (`~/.lateralus/cache/*.pyc`) — kills startup overhead
3. **IR-level const-folding & dead-code elim** — already partial in `lateralus_lang.ir`
4. **LLVM backend** — direct SSA, register allocation, full opt pipeline
5. **Typed-IR specialisation** for `int`/`float` hot loops

See [`results/results.md`](./results/results.md) for the latest table.
