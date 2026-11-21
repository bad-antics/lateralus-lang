# Time and Duration Utilities with `stdlib/time.ltl`

Every program eventually needs a clock. `stdlib/time.ltl` is a thin,
honest wrapper over the `_time` builtin: `now`, `perf_counter`,
`sleep`, `format_iso`, `format_date`, and `elapsed_ms` for timing
blocks of work.

This tutorial exercises format_iso, format_date, elapsed_ms,
perf_counter and now. Companion: `examples/time_tutorial.ltl`.

---

## How it works

- `now()` → `_time.time()` — wall-clock Unix seconds (float)
- `perf_counter()` → `_time.perf_counter()` — monotonic-ish high
  resolution counter for measuring durations, unaffected by clock
  adjustments
- `format_iso(ts)` / `format_date(ts)` → `strftime` over
  `localtime(ts)` — **local** timezone, so pin `TZ=UTC` in tests for
  deterministic vectors
- `elapsed_ms(start)` → `(perf_counter() - start) * 1000.0`
- `sleep(seconds)` → `_time.sleep(seconds)` — not demoed (slow tests)

## Verified on a pinned vector

`format_iso(1700000000.0)` → `2023-11-14T22:13:20` and
`format_date` → `2023-11-14` under `TZ=UTC`. `elapsed_ms` around a
100k-iteration loop returns a positive float; `now()` is a Unix
timestamp past the pinned epoch.

## Notes

- Functions are inlined in the companion because `import stdlib.*`
  resolution is a known open bug (#260).
- No bugs found in `stdlib/time.ltl` itself — it parses clean and all
  five exported helpers behave as documented.

## Running the tutorial

```bash
TZ=UTC python -m lateralus_lang run examples/time_tutorial.ltl
python -m lateralus_lang check examples/time_tutorial.ltl
python -m pytest tests/test_time_tutorial.py -x -q
```
