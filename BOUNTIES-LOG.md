# Bounties Log

Claims for the recurring micro-bounties in [BOUNTIES.md](BOUNTIES.md). One row
per claim; append, don't rewrite. Payment is weekly, per BOUNTIES.md.

| Date | Bounty | Deliverable | Status |
|---|---|---|---|
| 2026-11-24 | $25 — blog post tutorial for a single stdlib module | `docs/blog/base64-from-scratch.ltlml` — stdlib/base64.ltl walkthrough, runnable example `examples/base64_vectors.ltl` (21 checks), pinned RFC 4648 §10 vectors | claimed |
| 2026-11-24 | $25 — port an idiomatic ~50-line program | `examples/ports/nbody.py` → `examples/ports/nbody.ltl` — N-body simulation, n = 500,000. Identical energies (`-4286150`, `-4285578`); C99 backend 0.05 s vs CPython 4.25 s (~85x). Needs #963 for the C backend to compile it. | claimed |
