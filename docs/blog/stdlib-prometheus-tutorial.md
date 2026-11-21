# Prometheus Exposition with `stdlib/prometheus.ltl`

Every Prometheus-compatible monitoring stack — Prometheus itself,
VictoriaMetrics, Grafana Mimir, Thanos — scrapes the same thing: the
**text exposition format**. `# HELP`/`# TYPE` comment lines, sample
lines with `{label="value"}` selectors, histograms as `_bucket` series
with `le` labels. `stdlib/prometheus.ltl` emits and parses that format
in about 170 lines.

This complements `stdlib/metrics.ltl` (the in-process registry):
metrics collects the numbers, prometheus renders and reads the wire
format. This tutorial covers both directions. Companion:
`examples/prometheus_tutorial.ltl`.

---

## Labels: escaping is the whole game

Label values are double-quoted strings inside `{...}`, so three
characters need escaping: `\` → `\\`, `"` → `\"`, newline → `\n`.
`escape_label_value` walks the string once and rewrites exactly those.
Order matters less here than in HTML escaping (no `&`-first rule), but
the backslash escape must come first so `\\` doesn't get re-escaped.

`format_labels` takes `[[key, value], ...]` pairs — a list, not a map,
because **order is observable** in the output and Prometheus sorts
labels canonically anyway.

## Emitters: four primitives, everything else composes

```text
help_line(name, desc)      ->  # HELP name desc\n
type_line(name, kind)      ->  # TYPE name kind\n
sample_line(name, labels, value) ->  name{labels} value\n
metric_block(...)          ->  HELP + TYPE + N sample lines
histogram_block(...)       ->  HELP + TYPE histogram + le-bucket
                                series + _sum + _count
```

`metric_block` is the counter/gauge workhorse. `histogram_block`
takes `[le_string, count]` pairs and appends `le` as an extra label on
each `_bucket` line — note it *appends* to your labels, so
`request_duration_seconds_bucket{le="0.1"}` emerges naturally. The
cumulative-count convention (each `le` line counts everything ≤ that
bound) is the caller's responsibility — the module just renders what
you give it.

## The parser: line-oriented, comment-aware

`parse_line` handles one sample line: metric name up to `{` or space,
optional `{...}` label block parsed by `parse_labels` (with escape
*decoding* — `\n` back to newline, `\"` back to quote), then the value
up to the next space (leaving any trailing timestamp unparsed).

`parse_exposition` splits on `\n`, skips blank lines and `#` comments,
and collects every parseable sample into a list of
`{metric, labels, value}` maps.

Two graceful-degradation details: `parse_labels` returns what it
parsed so far on malformed input rather than throwing, and `parse_line`
returns `nil` for comment/blank lines — the parser never crashes on a
real-world exposition doc.

## Round-trip property

The emitters and parser are inverses at the line level: text produced
by `metric_block` parses back through `parse_exposition` to the same
metric/labels/value triples. The tutorial demonstrates this on a
two-sample counter and a `cpu_seconds{core="0",mode="idle"} 123.45`
line — label order in the parsed output matches input order.

## A lexer note

Curly braces inside string literals trigger the Lateralus f-string
interpolation lexer (see the metrics tutorial for the full story), so
the companion builds exposition text containing `{` via `chr(123)` /
`chr(125)` — the module itself uses the same trick (`chr(123)` for
`"{"`).

## Running the companion

```text
STEP 1 label escaping:
  {path="/a/b",code="200"}
  {msg="say \"hi\"\nnow"}
  empty: ''
STEP 2 metric block:
# HELP http_requests_total Total requests\n# TYPE http_requests_total counter\nhttp_requests_total{method="GET",code="200"} 1027\nhttp_requests_total{method="POST",code="500"} 3\n
STEP 3 histogram block:
# HELP request_duration_seconds Latency\n# TYPE request_duration_seconds histogram\nrequest_duration_seconds_bucket{le="0.1"} 10\nrequest_duration_seconds_bucket{le="0.5"} 25\nrequest_duration_seconds_bucket{le="+Inf"} 30\nrequest_duration_seconds_sum 12.5\nrequest_duration_seconds_count 30\n
STEP 4 parse exposition:
  parsed 2 samples
  h labels=[['method', 'GET']] value=42
  h labels=[['method', 'POST']] value=7
STEP 5 round-trip check:
  metric=cpu_seconds value=123.45 labels=2
PINNED_VECTORS: lbl=path-code-200 esc=quoted-newline blk=HELP-TYPE-2samples hist=buckets-sum-count parsed=2 rt=cpu_seconds-123.45
```

`tests/test_prometheus_tutorial.py` pins the escaped label output, the
literal `\n` sequences in rendered blocks, and the parse results —
including the two-label round trip.

## When to use it

**Use it** to expose a `/metrics` endpoint from a Lateralus service
(pair with `stdlib/metrics.ltl` for collection), to write a scrape
client or federation proxy, or to validate exposition text in tests.

**Don't expect** OpenMetrics extensions (info metrics, exemplars,
created-timestamps), native histogram support, or UTF-8 name
validation — this is classic Prometheus text format 0.0.4, which is
what 99% of scrapers still speak.

That is `stdlib/prometheus.ltl`: escaping rules, four emitters, a
forgiving parser, and a format every monitoring stack already speaks.
