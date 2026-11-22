# Distributed Tracing with `stdlib/tracing.ltl`

`stdlib/tracing.ltl` implements OpenTelemetry-style distributed tracing
in about 130 lines: tracers, spans, sampling decisions, attributes and
events — and the W3C `traceparent` header format that lets a trace cross
process and network boundaries.

This tutorial covers the span lifecycle, how sampling propagates from
root to children, the wire format, and how to plug in your own exporter.
Companion: `examples/tracing_tutorial.ltl`.

---

## The model: tracer, span, context

Everything is plain maps — no classes, no runtime magic:

```text
tracer = { service, exporter, sampler }
span   = { ctx, name, kind, start_ns, end_ns,
          attributes, events, status, status_msg, tracer }
ctx    = { trace_id, span_id, parent, sampled }
```

- **`trace_id`** identifies the whole distributed trace (16 bytes → 32
  hex chars). All spans in one trace share it.
- **`span_id`** identifies this span (8 bytes → 16 hex chars). A child's
  `parent` field stores its parent's `span_id` — that's the edge in the
  trace tree.
- **`sampled`** is the sampling decision, propagated root → descendants.

`new_tracer(service, exporter, sampler)` binds the three things every
span needs: who you are, where finished spans go, and whether to keep
them. `always_sample`/`never_sample` are the trivial samplers; write
your own for head/rate sampling.

## Span lifecycle

```text
span = start(tracer, name, parent, kind, attrs)
set_attr(span, k, v)          -- add attributes anytime
add_event(span, name, attrs)  -- timestamped point-in-time annotations
end_ok(span)                  -- status="ok", emit, return exporter output
end_error(span, msg)          -- status="error" + message, emit
```

`start` with `parent = nil` mints a fresh `trace_id` and asks the
tracer's sampler whether to record. `start` with a parent **inherits**
`trace_id`, sets `parent = parent.span_id`, and inherits `sampled` —
children of an unsampled root are unsampled too, which is what keeps
trace volume proportional to your sampling rate.

`emit_span` is the gate: unsampled spans return early and never reach
the exporter. In the module the exporter is a side-effecting function;
the companion makes it *return* a string so output is testable.

## `traceparent`: crossing the wire boundary

The W3C header is four dash-separated fields:

```text
00-{trace-id}-{span-id}-{flags}
```

`traceparent(ctx)` renders it (`00` version, `01` flags when sampled);
`parse_traceparent(h)` validates version `00` and exactly four fields,
extracting `trace_id`, `span_id`, and `sampled = (flags & 1)`. Anything
malformed returns `nil` — propagate nothing rather than propagate garbage.

This is the piece that makes tracing *distributed*: serialize the
current span's context into an HTTP header, and the downstream service
parses it and parents its spans to yours.

## Determinism in the companion

The real module draws `trace_id`/`span_id` from `crypto_rand_bytes` —
unpinnable. The companion uses a deterministic counter (`next_id`) so
the transcript is byte-stable, and documents the substitution. IDs are
still structurally correct: 32-hex trace IDs, 16-hex span IDs, correct
parent links.

## Running the companion

```text
STEP 1 root span:
  name=GET /users kind=server trace=7411411852151296301310 span=141185215129 parent= sampled=True status=unset events=0 attrs=2
STEP 2 child span inherits trace_id:
  name=db.query kind=client trace=7411411852151296301310 span=5215129630 parent=141185215129 sampled=True ...
  same trace: True
  parent link: True
STEP 3 attrs/events/status:
  root end_ok -> ... status=ok events=0 attrs=2
  child end_error -> ... status=error events=1 attrs=1
STEP 4 sampling:
  never_sample root sampled=False
  end_ok emits: <not sampled>
  child inherits sampled=False
STEP 5 traceparent round-trip:
  traceparent: 00-7411411852151296301310-141185215129-01
  parsed trace_id match: True
PINNED_VECTORS: trace=7411411852151296301310 span=141185215129 child=5215129630 tp=00-7411411852151296301310-141185215129-01 roundtrip=true bad=nil sampled_child=false
```

`tests/test_tracing_tutorial.py` pins the whole transcript — the
deterministic IDs make this a real regression test: if span-context
propagation or traceparent parsing breaks, the vectors fail.

## When to use it

**Use it** when you need request-flow visibility across services:
propagate `traceparent` in HTTP headers, parent spans to incoming
contexts, export finished spans to Jaeger/Zipkin/OTel collectors via
your `exporter` function.

**Don't expect** baggage propagation, span links, exemplar support, or
OTLP wire encoding — the module is the span model + traceparent codec,
deliberately. `parse_traceparent` accepts only version `00` (the only
widely deployed version) — future versions return `nil` rather than
misparsing.

That is `stdlib/tracing.ltl`: spans as maps, sampling as inheritance,
and a header format that survives the network.
