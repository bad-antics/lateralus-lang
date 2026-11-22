# Idiomatic ports

Recurring micro-bounty ($25): port an idiomatic ~50-line Python/Go/Rust
program to Lateralus. Each entry keeps the original source next to the
`.ltl` port plus the verification numbers.

## n_queens

- Original: `n_queens.py` — bitmask backtracking N-Queens counter (~40 lines).
- Port: `n_queens.ltl` — same algorithm, no external deps.
- Verified 2026-11-21: both print `73712` for n=13.
- Wall time: C99 backend (`lateralus c` + `gcc -O2`) **0.106s** vs CPython
  **1.63s** — the port beats the original.
