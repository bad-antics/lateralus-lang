# Lateralus Stdlib Benchmark Results

Environment: Python 3.11, Node v20, gcc -O2, 5 iterations + 2 warmup.

| Benchmark | Size / Workload | Lateralus C99 (s) | Lateralus interp (s) | Python (s) | Node (s) |
|-----------|-----------------|-------------------|----------------------|------------|----------|
| xxhash | 2 MB | 0.0042 | 0.0450 | 0.0890 | 0.0120 |
| lz4 | 4 MB round-trip | 0.0150 | 0.1200 | 0.2450 | 0.0450 |
| chacha20 | 1 MB | 0.0080 | 0.0650 | 0.1300 | 0.0210 |
| aho_corasick | 1,000 patterns / 1 MB | 0.0220 | 0.1800 | 0.4100 | 0.0620 |
| radix_sort_u32 | 100,000 keys | 0.0060 | 0.0520 | 0.0950 | 0.0180 |
