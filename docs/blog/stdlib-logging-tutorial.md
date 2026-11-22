# Logging with `stdlib/logging.ltl`

`stdlib/logging.ltl` is structured logging in about 140 lines: six
severity levels, a minimum-level gate, an optional prefix, key-value
context, and conditional/assert helpers — no dependencies, no log
framework ceremony.

This tutorial covers the level model, gating semantics, the context
format, and the `log_if`/`log_assert` conveniences. Companion:
`examples/logging_tutorial.ltl`.

---

## The level model

```text
TRACE=0  DEBUG=1  INFO=2  WARN=3  ERROR=4  FATAL=5
```

A logger has a **minimum level**: messages below it are suppressed
entirely — not formatted, not printed. The companion starts at `INFO`
(2), so `trace`/`debug` calls return empty strings while `info`/`warn`/
`error` produce `[LEVEL] message` lines. Raising the gate to `ERROR`
late in the demo silences `info` again — the gate is read on every call,
so it's a runtime dial, not a compile-time filter.

## Line format

```text
[prefix] [LEVEL] message key=value key=value
```

- `[LEVEL]` — always present, uppercase name via `level_name`
- `[prefix]` — optional, prepended when `set_prefix` was used
- message — free text
- `key=value` pairs — appended by `log_ctx` from a `[[k,v],...]` list;
  pairs with fewer than 2 elements are skipped

The module also has ANSI color helpers (`level_color`) and a
`show_time` toggle for timestamps — the companion disables time so the
output is deterministic and pinnable.

## The helpers that matter

- **`log_ctx(level, msg, context)`** — structured logging without a
  framework: `log_ctx(INFO, "request handled", [["method","GET"],
  ["status","200"]])` → `[INFO] request handled method=GET status=200`.
  This is the logfmt-style output grep/jq can actually parse.
- **`log_if(condition, level, msg)`** — log only when the condition
  holds; cheaper than formatting-then-discarding at call sites that
  compute expensive messages.
- **`log_assert(condition, msg)`** — emits `FATAL Assertion failed: msg`
  when the condition fails. A logging-flavored `assert` that survives
  release builds (where real `assert` compiles out) — useful for
  invariants you want visible in production logs.

## A platform adaptation worth knowing

The module keeps config (`_log_level`, `_log_prefix`, `_log_show_time`)
in module-level mutable globals. Under the Python backend, functions
can't assign to globals — the write makes the name function-local and
you get `UnboundLocalError`. The companion therefore keeps config in a
`map` cell (`cfg["level"]`, mutated as `cfg["level"] = 1`, which *does*
work — map mutation isn't rebinding) and makes `_log` **return** the
formatted line instead of printing, so suppression is testable.

## Running the companion

```text
STEP 1 level gate (min=INFO=2):
[api] [INFO] info msg - shown
[api] [WARN] warn msg - shown
[api] [ERROR] error msg - shown
STEP 2 prefix + context:
[api] [INFO] request handled method=GET status=200 ms=42
[api] [WARN] slow query table=users rows=9000
STEP 3 conditional + assert:
[api] [INFO] cache hit
[api] [FATAL] Assertion failed: index out of range
STEP 4 lower the level to DEBUG:
[api] [DEBUG] now visible at DEBUG
STEP 5 raise to ERROR:
[api] [ERROR] only errors now
PINNED_VECTORS: gate=info+warn+error prefix=[api] ctx=method=GET+status=200+ms=42 assert=Assertion+failed debug_at_1=shown trace_at_1=hidden
```

`tests/test_logging_tutorial.py` pins the transcript — including the
*absence* assertions (suppressed messages must not appear), which is
what actually verifies the level gate.

## When to use it

**Use it** for service logging: severity-gated messages, structured
`key=value` context, prefix tagging per component, `log_assert` for
production-visible invariants.

**Don't expect** log rotation, async appenders, sampling, or OTLP export
— it's console logging with levels. For those, pair it with your own
sink or reach for `stdlib/tracing.ltl`/`stdlib/opentelemetry.ltl`. And
keep messages cheap: `log_if` exists precisely because formatting a
string you then suppress is wasted work.

That is `stdlib/logging.ltl`: six levels, one gate, key-value context,
and helpers that make the common cases one line.
