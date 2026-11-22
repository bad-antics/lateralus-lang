# CSP Channels with `stdlib/channel.ltl`

`stdlib/channel.ltl` implements Go-style channels as plain maps —
`{"buffer": [...], "capacity": n, "closed": bool, counters…}` —
with send/recv, non-blocking `try_*` variants, close semantics,
multi-channel `select`, fan-out/fan-in, pipelines, and stats.
~320 lines of pure Lateralus; blocking uses `yield()` busy-waits.

Companion: `examples/channel_tutorial.ltl` (uses the non-blocking
paths so it runs deterministically under `ltlc run`).

---

## The channel map

```text
{"type":"channel","buffer":[...],"capacity":N,
 "closed":bool,"send_count":n,"recv_count":n}
```

- **`channel_new(cap)`** — buffered channel; `unbuffered()` = cap 0.
- **`channel_send`** — appends; busy-waits via `yield()` when full
  (skipped in the demo — `try_send` used instead).
- **`channel_recv`** — pops front; returns `none` when closed+empty.
- **`try_send`/`try_recv`** — non-blocking versions, same logic minus
  the wait loops. This is what the tutorial exercises.
- **`channel_close`** — sets `closed`; sends rejected, buffered
  values still receivable (verified: drain after close = 2 items).
- **`has_data`/`is_full`/`pending`** — buffer introspection.
- **`select(channels)`** — polls in order, first non-empty channel
  wins, returns `{index, value, channel}`; `none` if all closed.
- **`fan_out`/`fan_in`/`pipeline`/`drain`/`collect`/`stats`** —
  composition helpers for worker pools and stream processing.

## Verified results

```text
cap-3 channel: 2 sends ok, pending=2, recv task-1/task-2 FIFO,
                counters send=2 recv=2
cap-2 channel: 3rd send rejected while full; after 1 recv, send ok
closed channel: send rejected; drain yields buffered 2; empty recv NONE
unbuffered (cap 0): try_send accepted (see note), is_full=True
select: first-ready channel wins — cA's "from-A" picked over cB
```

`tests/test_channel_tutorial.py` pins every value.

## ⚠️ Semantic notes worth knowing

1. **"Unbuffered" isn't truly synchronous in `try_send`** — the
   capacity check is `capacity > 0 && len(buffer) >= capacity`, so
   cap-0 channels accept into an unbounded buffer via `try_send`.
   True synchronous handoff needs the blocking `channel_send` +
   `yield()` path (needs a scheduler — not demoable headless).
2. **`select` is poll-order, not random** — lowest index with data
   always wins; fine for demos, not fair scheduling.
3. `none`/`yield()`/`clock_ms()`/`loop`/`for i in range`/`break` are
   runtime constructs the companion avoids; `select_timeout` uses
   `clock_ms` and is documented but not demoed.

## When to use it
##

**Use it** for producer/consumer queues, worker-pool fan-out,
request multiplexing (`select`), and stream pipelines — anywhere
CSP beats shared mutable state.

**Don't expect** kernel-grade scheduling, select randomness, or
true rendezvous semantics from the `try_*` path — this is a
 cooperative model that assumes `yield()`-capable tasks.

That is `stdlib/channel.ltl`: channels as data, close as a
poison-pill, select as ordered polling — concurrency primitives
you can hold in a map.
