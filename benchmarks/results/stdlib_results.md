# Lateralus stdlib Micro-Benchmark Results

Python 3.14.3 · Node v25.8.0 · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters + 1 warmup

## Inputs & expected outputs

| Benchmark | Workload | Expected output (all backends) |
|-----------|----------|-------------------------------|
| stdlib_xxhash | xxhash64 over 2 MiB (seed 0) | `4289610906924000822` |
| stdlib_lz4 | lz4 compress + decompress round-trip of 4 MiB | `1121525033861120` |
| stdlib_chacha20 | chacha20 encrypt 1 MiB (RFC 8439) | `70152198213509` |
| stdlib_aho_corasick | aho-corasick search, 1,000 patterns in ~1 MiB text | `1000` |
| stdlib_radix_sort | radix_sort_u32 on 100,000 keys | `14316716090336674650` |

## Results

| Benchmark | Backend | Median (ms) | Min (ms) | Notes |
|-----------|---------|-------------|----------|-------|
| stdlib_xxhash | lateralus | 341.2 | 316.7 | xxhash64 over 2 MiB (seed 0) · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_xxhash | lateralus-c99 | — | — | C99 build failed · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_xxhash | python | 99.3 | 97.9 | xxhash64 over 2 MiB (seed 0) · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_xxhash | node | 82.8 | 82.5 | xxhash64 over 2 MiB (seed 0) · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_lz4 | lateralus | — | — | not run at 4 MiB: stdlib lz4 uses O(n^2) list append (64 KiB round-trip ~1.9 s; 4 MiB would take hours) · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_lz4 | lateralus-c99 | — | — | C99 build failed · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_lz4 | python | 1066.3 | 1058.7 | lz4 compress + decompress round-trip of 4 MiB · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_lz4 | node | 174.6 | 171.4 | lz4 compress + decompress round-trip of 4 MiB · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_chacha20 | lateralus | — | — | not run at 1 MiB: stdlib chacha20.xor uses O(n^2) list append (64 KiB encrypt ~2.2 s; 1 MiB would take hours) · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_chacha20 | lateralus-c99 | — | — | C99 build failed · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_chacha20 | python | 981.2 | 975.5 | chacha20 encrypt 1 MiB (RFC 8439) · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_chacha20 | node | 64.3 | 64.2 | chacha20 encrypt 1 MiB (RFC 8439) · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_aho_corasick | lateralus | 363.7 | 342.7 | aho-corasick search, 1,000 patterns in ~1 MiB text · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_aho_corasick | lateralus-c99 | — | — | C99 build failed · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_aho_corasick | python | 284.0 | 283.8 | aho-corasick search, 1,000 patterns in ~1 MiB text · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_aho_corasick | node | 369.9 | 369.1 | aho-corasick search, 1,000 patterns in ~1 MiB text · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_radix_sort | lateralus | 448.4 | 447.3 | radix_sort_u32 on 100,000 keys · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_radix_sort | lateralus-c99 | — | — | C99 build failed · macOS · 26.5.2 · arch=arm64 · Apple M4 |
| stdlib_radix_sort | python | 41.4 | 40.9 | radix_sort_u32 on 100,000 keys · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |
| stdlib_radix_sort | node | 51.2 | 51.2 | radix_sort_u32 on 100,000 keys · macOS · 26.5.2 · arch=arm64 · Apple M4 · 3 iters |

## Notes

- `lateralus` = transpile-to-Python interpreter (`lateralus run`); `lateralus-c99` = transpile-to-C99 + `gcc -O2`; `python` / `node` = references in `benchmarks/reference/`.
- Timings are full-process wall time, including interpreter startup and (for `lateralus`) transpilation; input generation is negligible.
- `lateralus-c99` cannot compile the stdlib `.ltl` modules (the C99 backend does not support the list-typed / arbitrary-precision stdlib dialect), so every gcc row is `C99 build failed`.
- `stdlib_lz4` and `stdlib_chacha20` were not run on the Lateralus interpreter at full size: the stdlib implementations append to lists one element at a time (`list + [x]`), which is O(n^2) in the transpile-to-Python backend. Reduced-size Lateralus sanity runs: lz4 64 KiB round-trip ~1.9 s, chacha20 64 KiB encrypt ~2.2 s. Python + Node ran at the full 4 MiB / 1 MiB.
