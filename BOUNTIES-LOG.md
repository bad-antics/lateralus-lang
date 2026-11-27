# Bounties Log

Claims against the recurring micro-bounties in `BOUNTIES.md`. Entries are
original work, MIT-licensed, copyright the contributor.

## $25 — stdlib module tutorial

| Module | Deliverable | Claimed by | Date | Status |
|---|---|---|---|---|
| `stdlib.signals` | `docs/blog/signals-moving-average-transients.ltlml` + `examples/signals_moving_average.ltl` | Zwk-tech | 2026-11-27 | Submitted (issue #1075) |

### Notes

- **issue #1075** — tutorial for `stdlib.signals.moving_average`: why a transient
  at the start of a clip reads as a decaying `6, 3, 2` ramp while one in the
  middle reads as a flat `2, 2, 2` plateau, explained via the `min(i + 1, w)`
  denominator. Runnable example pinned to `[0.0, 0.0, 2.0, 2.0, 2.0, 0.0]`
  and `[6.0, 3.0, 2.0, 0.0]`.
- The runnable example is self-contained (moving_average reimplemented in plain
  Lateralus) so it runs on the Python backend without stdlib-import inlining.
  Its three `@test` vectors pass.
- MIT licensed, original work.
