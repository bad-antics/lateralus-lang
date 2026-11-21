# Idiomatic ports

Recurring micro-bounty ($25): port an idiomatic ~50-line Python/Go/Rust
program to Lateralus. Each entry keeps the original source next to the
`.ltl` port plus the verification numbers.

## mandelbrot

- Original: `mandelbrot.py` — Mandelbrot escape-time renderer printing one
  iteration count per pixel (~50 lines).
- Port: `mandelbrot.ltl` — same algorithm, no external deps.
- Verified 2026-11-21: `lateralus c` + `gcc -O2` output is byte-identical
  to CPython (80,000 lines diffed); interpreter semantics verified on a
  reduced 20x10 grid.
- Wall time: C99 backend **0.069s** vs CPython **2.05s** — the port beats
  the original by ~30x.
- Note: `lateralus run` at full 400x200 size exceeds the 60s interpreter
  budget; the shipped size is tuned for the C backend per the bounty rules.
