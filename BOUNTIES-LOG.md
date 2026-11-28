# BOUNTIES-LOG

Claims and payouts for the recurring micro-bounties in `BOUNTIES.md`.
Newest first.

## 2026-11-23 — $25 port: prime_count (xiaozhi-ops)

- **Bounty:** port any idiomatic 50-line Python/Go/Rust program to
  Lateralus (must compile with `lateralus c` and beat the original
  on wall time).
- **Work:** `examples/prime_count/` — `prime_count.py` (Python
  original, trial-division prime counting) ported to
  `prime_count.ltl`, plus `benchmark.py` and `README.md`.
- **Verification:** both programs print 78,498 primes below
  1,000,000. Benchmark (median of 5 runs, 2026-11-23): Python 5.31 s
  vs Lateralus compiled binary 0.253 s — **21.0x faster**.
- **Payment:** BTC/LN `pencil@coinos.io`
- **Status:** submitted, awaiting review.
- **Issue:** `[bounty] prime-count-port` (to be opened)
- **PR:** (to be opened)
