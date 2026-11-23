# Lateralus stdlib micro-benchmarks (issue #865)

Python 3.13.5 · Node v22.23.3 · profile=verify · 3 iters + 1 warmup

Five workloads, one digest line each (identical across backends):

| Backend | median (s) | min (s) |
|---------|-----------|---------|
| lateralus | 2.1890 | 1.7040 |
| python | 0.3911 | 0.2106 |
| node | 0.3091 | 0.2834 |

Digest output (byte-identical across Lateralus / CPython / Node):

```
xxhash a41217695b9daa10
lz4 ok:2048:e4db04a9:2057
chacha20 97833df5645258de:98463a16
aho_corasick 91
radix_sort_u32 002d551e:ffea57ad:895db197
```

Correctness: **OK** (all backends agree)

