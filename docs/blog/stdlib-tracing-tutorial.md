# Distributed Observability with Lateralus `stdlib/tracing.ltl` (W3C Trace Context)

When a single user interaction triggers cascading RPC calls across multiple microservices, relational databases, and asynchronous queues, debugging latency spikes or failures using isolated logs becomes impossible.

**Distributed Tracing**, standardized by the **W3C Trace Context** specification and **OpenTelemetry**, tracks the end-to-end execution path of requests across process boundaries. Lateralus provides a zero-dependency distributed tracing engine in `stdlib/tracing.ltl`.

---

## 1. W3C `traceparent` Wire Specification

To correlate spans across distributed HTTP and gRPC network boundaries, services propagate the W3C standard HTTP header:

$$\texttt{traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01}$$

The header consists of four hyphen-separated fields:

1. **Version (`00`)**: 2 hex characters representing the W3C specification version.
2. **Trace ID (`32 hex chars`, 16 bytes)**: Globally unique identifier shared by all spans within a single transaction tree.
3. **Parent ID / Span ID (`16 hex chars`, 8 bytes)**: The unique ID of the immediate calling span.
4. **Trace Flags (`2 hex chars`, 8 bits)**: `01` denotes the trace is sampled (recorded and exported); `00` denotes not sampled.

`stdlib/tracing.ltl` provides `parse_traceparent` and `traceparent` to serialize and parse this header without regex overhead.

---

## 2. Span Lifecycle & Context Inheritance

A **Span** represents a contiguous unit of work. Every child span:
- Inherits the exact same `trace_id` from its parent.
- Sets its `parent` pointer to the parent's `span_id`.
- Generates a new, cryptographically random `span_id`.
- Inherits the parent's `sampled` decision.

```
[Root Span: HTTP POST /checkout] (trace=abc, span=001, parent="")
   │
   ├──> [Child Span: ValidateCart] (trace=abc, span=002, parent=001)
   │
   └──> [Child Span: ProcessPayment] (trace=abc, span=003, parent=001)
           │
           └──> [Grandchild Span: Stripe RPC] (trace=abc, span=004, parent=003)
```

---

## 3. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `tracing_new_tracer` | `(service: str, exporter, sampler) -> map` | Initializes a tracer for a specific microservice. |
| `tracing_start` | `(tracer, name, parent, kind, attrs) -> map` | Starts a new Span (passing `nil` for root, or parent context map). |
| `tracing_set_attr` | `(span: map, k: str, v: any)` | Adds semantic key-value tags to the span. |
| `tracing_add_event` | `(span: map, event_name: str, attrs: map)` | Records a timestamped in-span operational event. |
| `tracing_end_ok` | `(span: map)` | Marks span as status `"ok"`, captures duration, and emits to exporter. |
| `tracing_end_error`| `(span: map, msg: str)` | Marks span with `"error"`, captures duration, and emits to exporter. |
| `tracing_duration_ns` | `(span: map) -> int` | Returns total elapsed nanoseconds between `start` and `end`. |
| `tracing_parse_traceparent` | `(h: str) -> map` | Parses W3C wire header into context map `{trace_id, span_id, sampled}`. |
| `tracing_traceparent` | `(ctx: map) -> str` | Formats context map into valid W3C wire header. |

---

## 4. Practical Example: Cross-Service Context Propagation

Propagating trace context from an API Gateway to a downstream Payment Service:

```lateralus
import tracing

// 1. Gateway creates root span
let gw_tracer = tracing_new_tracer("gateway", my_exporter, tracing_always_sample)
let root_span = tracing_start(gw_tracer, "POST /api/pay", nil, "server", {})

// 2. Inject into HTTP header
let header = tracing_traceparent(root_span["ctx"])

// 3. Downstream Payment Service extracts context
let extracted_ctx = tracing_parse_traceparent(header)
let pay_tracer = tracing_new_tracer("payment", my_exporter, tracing_always_sample)
let child_span = tracing_start(pay_tracer, "ChargeCard", extracted_ctx, "internal", {})

// Complete child and root
tracing_end_ok(child_span)
tracing_end_ok(root_span)
```

---

## 5. Verification & Test Suite

The test suite in `tests/stdlib_tracing_tutorial.ltl` verifies:
- Strict round-trip formatting and parsing of official W3C traceparent headers.
- Rejection of malformed versions and incomplete segments.
- Hierarchical context propagation across parent and child spans.
- Monotonic duration recording.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_tracing_tutorial.ltl
python -m lateralus_lang check examples/tracing_tutorial.ltl
```
