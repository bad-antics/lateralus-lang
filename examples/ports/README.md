# Idiomatic ports

Recurring micro-bounty ($25): port an idiomatic ~50-line Python/Go/Rust
program to Lateralus. Each entry keeps the original source next to the
`.ltl` port plus the verification numbers.

## prime_sieve

- Original: `prime_sieve.py` — Sieve of Eratosthenes prime + twin-prime
  counter (~50 lines).
- Port: `prime_sieve.ltl` — same algorithm, no external deps.
- Verified 2026-11-21: both print `348513` then `32463` at n=5,000,000
  (interpreter check at n=100,000: `9592` / `1224`, matches CPython).
- Wall time: C99 backend (`lateralus c` + `gcc -O2`) **0.171s** vs CPython
  **0.602s** — the port beats the original.
- Note: `lateralus run` at n=5M exceeds the 60s interpreter budget; the
  shipped n is sized for the C backend per the bounty rules. Workarounds
  used for C99 codegen edges: `[true] * (n + 1)` for array init and
  `0 - 1` instead of unary `-1`.
