# Metrics with `stdlib/metrics.ltl`

Counters, gauges, histograms, and Prometheus text exposition — the
`stdlib/metrics.ltl` module gives a Lateralus program an in-process
metrics registry in about 180 lines, no dependencies, no exposition
server required (you render the text yourself and serve it however you
like).

This tutorial covers the registry model, the three instrument kinds,
how labels become series fingerprints, histogram bucket semantics, and
the exact Prometheus output format. Companion:
`examples/metrics_tutorial.ltl`.

---

## The registry model

A registry is a nested map:

```text
reg["families"][name] = {
    name, help, kind,           # "counter" | "gauge" | "histogram"
    buckets,                    # histogram only: list[float]
    series: { fingerprint -> series }
}
```

Each *series* is one label-set's worth of state: `value` (counter/gauge),
`count`/`sum`/`bucket_counts` (histogram), plus the original `labels`
map for rendering. `register_*` creates the family once —
`ensure_family` is idempotent, so re-registering is safe.

## Three instruments

| Kind | Write API | Read API | Semantics |
|---|---|---|---|
| counter | `inc(reg, name, labels, by)` | rendered value | monotonically increasing; `by` defaults your increment |
| gauge | `set_value(reg, name, labels, v)` | rendered value | last write wins — gauges go up *and* down |
| histogram | `observe(reg, name, labels, v)` | `_bucket`/`_sum`/`_count` | counts observations into cumulative `le` buckets |

The counter/gauge distinction matters: `set_value` on a counter would
silently break rate() calculations in Prometheus; `inc` on a gauge can't
express a decrease. The module doesn't enforce this — it's on you.

## Labels → fingerprints → series

Labels are a map (`{"route": "/api", "method": "GET"}`). Before storage,
`fingerprint` sorts the keys and joins `k=v` pairs — so
`{route,method}` and `{method,route}` are the *same* series. That's the
difference between a fingerprint (identity, order-insensitive) and
`labels_fmt` (display, insertion order):

```text
fingerprint({route="/api",method="GET"})  ->  "method=GET,route=/api"   (sorted)
labels_fmt({route="/api",method="GET"})   ->  {route="/api",method="GET"} (as inserted)
```

`touch` lazily creates the series on first write — you never allocate
label combinations you don't use, which is what keeps cardinality (and
memory) bounded by reality rather than by config.

## Histogram buckets

`observe` places `v` into the *first* bucket where `v <= bucket[i]`,
incrementing that bucket's count; values above all buckets land in the
implicit `+Inf` slot (`bucket_counts[len(buckets)]`). Rendering emits
**cumulative** counts — each `le` line includes everything below it —
which is what Prometheus's `histogram_quantile` expects.

For buckets `[0.1, 0.5, 1.0]` and observations `0.05, 0.3, 2.0`:

```text
le="0.1"   -> 1     (only 0.05)
le="0.5"   -> 2     (0.05 + 0.3)
le="1.0"   -> 2     (nothing new)
le="+Inf"  -> 3     (everything, incl. 2.0)
sum = 2.35, count = 3
```

## The exposition format

`render_prometheus` emits the standard text format:

```text
# HELP request_latency_seconds Request latency
# TYPE request_latency_seconds histogram
request_latency_seconds_bucket{le="0.1"} 1
...
request_latency_seconds_sum 2.35
request_latency_seconds_count 3
```

`# HELP` only prints when help is non-empty; families iterate in
`keys()` order (insertion order under the hood — don't rely on sorted
output).

## A lexer quirk worth knowing

`{` and `}` inside string literals are treated as interpolation markers
by the Lateralus lexer — `"{"` alone is a parse error, and
`"{" + x + "}"` transpiles into a broken f-string. The companion works
around it with `chr(123)`/`chr(125)` in `labels_fmt`, with a comment
explaining why. If you hit a mysterious `f-string:` SyntaxError in
generated Python, check your string literals for braces first.

## Running the companion

```text
=== LATERALUS STDLIB METRICS TUTORIAL ===
STEP 1 families: http_requests_total,queue_depth,request_latency_seconds
STEP 2 counter series:  | method=GET,route=/api
STEP 3 gauge overwritten: last set_value wins (3.0)
STEP 4 histogram observed 0.05, 0.3, 2.0 into buckets [0.1,0.5,1.0]
STEP 5 prometheus output:
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total 2.0
http_requests_total{route="/api",method="GET"} 1.0
# HELP queue_depth Current queue depth
# TYPE queue_depth gauge
queue_depth 3.0
# HELP request_latency_seconds Request latency
# TYPE request_latency_seconds histogram
request_latency_seconds_bucket{le="0.1"} 1
request_latency_seconds_bucket{le="0.5"} 2
request_latency_seconds_bucket{le="1.0"} 2
request_latency_seconds_bucket{le="+Inf"} 3
request_latency_seconds_sum 2.35
request_latency_seconds_count 3
PINNED_VECTORS: families=http_requests_total,queue_depth,request_latency_seconds fp=method=GET,route=/api gauge=3.0 buckets=1,2,2,+Inf:3 sum=2.35 count=3 lbl=route=/api+method=GET
```

`tests/test_metrics_tutorial.py` pins the transcript line-for-line —
including the cumulative bucket counts, which are the easiest thing to
get subtly wrong (per-bucket vs cumulative).

## When to use it

**Use it** for in-process instrumentation: request counters, queue
depths, latency histograms, anything you'd `/metrics`-scrape. Pair it
with your HTTP layer to expose `render_prometheus(reg)` on a
`/metrics` route.

**Don't expect** what it doesn't have: no timers (`observe` takes the
value, you measure it), no summary quantiles (histograms give you
`histogram_quantile` server-side instead), no remote write, no unit
testing helpers. It's a registry and a renderer — deliberately small.

That is `stdlib/metrics.ltl`: three instruments, label fingerprints, and
a Prometheus exposition you can diff byte-for-byte.
