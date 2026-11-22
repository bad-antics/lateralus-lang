# OTLP Payloads with `stdlib/opentelemetry.ltl`

OpenTelemetry's OTLP protocol is three JSON-shaped envelopes —
traces, metrics, logs — each nested as
`resource → scope → records`. You don't need the OTel SDK to emit
valid payloads: the shape is just maps and lists.
`stdlib/opentelemetry.ltl` builds those maps directly — span
constructors, attribute helpers, and the three top-level
`Export*ServiceRequest` wrappers — ready to serialize with
`stdlib/json.ltl` and POST to any OTLP/HTTP collector.

This tutorial builds one of each signal end to end. Companion:
`examples/opentelemetry_tutorial.ltl`.

---

## The envelope shape

Every signal follows the same nesting:

```text
{resourceSpans|resourceMetrics|resourceLogs: [
  {resource: {attributes: [...]},
   scopeSpans|scopeMetrics|scopeLogs: [
     {scope: {name, version}, spans|metrics|logRecords: [...]}]}]}
```

`resource` carries service identity (`service.name`,
`deployment.environment`); `instrumentation_scope` carries the
instrumenting library name/version. Attributes are
`{key, value:{stringValue|intValue|boolValue|doubleValue}}` — note
`intValue` and timestamps are **strings** in OTLP/JSON to preserve
64-bit precision.

## Traces

`span(trace_id, span_id, parent_id, name, kind, start_ns, end_ns,
attrs, status_code, status_msg)` builds one span:

- `traceId`/`spanId`/`parentSpanId` are hex strings (parent omitted
  when empty — root spans have none)
- `kind` uses the OTLP SpanKind enum: 1 internal, 2 server, 3 client,
  4 producer, 5 consumer
- `status` is always present with a `code` (0 unset, 1 ok, 2 error)
  plus optional `message`
- `startTimeUnixNano`/`endTimeUnixNano` are stringified nanoseconds

Wrap spans in `scope_spans` → `resource_spans` → `trace_request` and
you have a complete `ExportTraceServiceRequest` body.

## Metrics

- `number_data_point` — attributes + start/end nanos + `asDouble`
  (string-encoded double)
- `gauge` — a metric with an instant `dataPoints` list
- `sum_metric` — cumulative totals with `isMonotonic` and
  `aggregationTemporality` (1 delta, 2 cumulative)

Same envelope: `scope_metrics` → `resource_metrics` →
`metrics_request`.

## Logs

`log_record(time_ns, severity_number, severity_text, body, attrs,
trace_id, span_id)` — severity uses the OTLP SeverityNumber scale
(9 = INFO), `body` is a `{stringValue}` anyValue, and trace/span ids
link the record back to its trace when non-empty. Envelope:
`scope_logs` → `resource_logs` → `logs_request`.

## Verified shape

The companion emits a checkout service trace (`POST /pay` root +
`db.query` child with correct parentSpanId), an error span with
`status.code=2`/`"card declined"`, a gauge with two data points, a
monotonic sum, and an INFO log record carrying its trace id — all
navigable as nested maps.

`tests/test_opentelemetry_tutorial.py` pins the structure.

## When to use it

**Use it** to emit OTLP/HTTP telemetry without the OTel SDK — from a
Lateralus service, edge function, or batch exporter. Pair with
`stdlib/json.ltl` for serialization and `stdlib/http` for transport.

**Don't expect** the SDK's sampling, batching, or context propagation
— this module is payload construction only. Span-kind/status enums
are exposed as functions (`kind_server()`, `status_error()`) so call
sites stay readable.

That is `stdlib/opentelemetry.ltl`: telemetry as data — build the
maps, serialize, ship.
