# Lateralus Benchmarks

Cross-language micro-benchmarks comparing Lateralus against CPython and
Node.js on five canonical workloads.

## Structure

    benchmarks/
      src/              Lateralus source (.ltl) — one per benchmark
      reference/        Python + JavaScript reference implementations
      results/          results.json + results.md (generated)
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
     covers 4 of 5 benchmarks (`fib`, `sieve`, `mandelbrot`, `nbody`)
     end-to-end with byte-identical output to the interpreter and Node.js.
     The last one (`binary_trees`) uses `fn make(d) -> any` returning either
     an `int` sentinel or a `Tree` struct — `any`-typed returns with mixed
     primitive/struct variants aren't supported by the typed C codegen yet.
     It's skipped rather than faked.
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
