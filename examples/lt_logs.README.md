# lt-logs — Log Triage Demo

**File:** [`lt_logs.ltl`](../lt_logs.ltl)
**Run:** `lateralus run examples/lt_logs.ltl`

A single-file, zero-dependency log-analysis CLI written in pure Lateralus.
It demonstrates the **observability lane** end-to-end:

1. Parses [logfmt](https://brandur.org/logfmt) lines (`key=value` with quoted strings + escapes)
2. Filters records by a minimum level (`warn`, `error`, …)
3. Groups by any key and counts frequencies
4. Renders a top-N table with unicode bar charts

## Sample output

```
lt-logs  —  parsed 10 structured log lines

== Top services (all levels) ==
  api           5    ██████████████████████████████
  web           2    ████████████
  auth          2    ████████████
  worker        1    ██████

Lines at level >= warn: 6

== Top problem services (warn+) ==
  api           4    ██████████████████████████████
  auth          2    ███████████████
```

## Why it matters

A typical "grep + awk + sort + uniq -c" log-triage pipeline in bash is
40+ lines of brittle shell. The Lateralus version is **one file, one
language, no external processes**, and the parser respects quoted
values and escape sequences the way a real logfmt parser should.

Swap `SAMPLE` for `file_read("/var/log/app.log")` and the same file
becomes a production triage tool.

## Extending

- Swap the frequency counter for a reservoir sampler (see
  [`stdlib/reservoir.ltl`](../../stdlib/reservoir.ltl))
- Add top-k by latency by sorting on `dur_ms` and dropping the `log_rank`
  filter
- Emit JSON by replacing `print_topn` with a `json_encode` call
- Stream from stdin once the runtime exposes `stdin_readline()`

## Related bounty

[`lt-logs-shipper` ($350)](../../BOUNTIES.md) — turn this demo into a
real CLI with file tailing, JSON output, and Prometheus push.
