# Cloud-Native Observability with Lateralus `stdlib/metrics.ltl` (Prometheus Exposition)

Modern production services require real-time introspection into error rates, latency distributions, and system resource saturation. Standardized by the Cloud Native Computing Foundation (CNCF), the **Prometheus Text Exposition Format** is the industry standard for metrics scraping.

Lateralus ships with an in-process metrics engine in `stdlib/metrics.ltl`, supporting multi-dimensional labels, Counters, Gauges, and Histograms with zero third-party dependencies.

---

## 1. The Prometheus Metric Models

`stdlib/metrics.ltl` supports three foundational metric families:

### 1. Counter (`metrics_inc`)
Monotonically increasing cumulative counters. Used for counting discreet events such as total requests received or error counts. Prometheus calculates request-per-second rates using the `rate()` function:

$$\text{QPS} = \text{rate}(\text{http\_requests\_total}[5\text{m}])$$

### 2. Gauge (`metrics_set_value`)
Instantaneous value snapshots that can fluctuate arbitrarily up or down. Used for measuring pool utilization, memory footprints, and active TCP sessions.

### 3. Histogram (`metrics_observe`)
Samples observations into cumulative configurable buckets ($\le \text{bucket}_k$), alongside the total observation count and aggregate sum. Used for tracking response time distributions and calculating $P_{50}, P_{90}, P_{99}$ percentiles via `histogram_quantile`.

---

## 2. Text Exposition Format Specification

Rendered metrics follow the canonical Prometheus line protocol:

```prometheus
# HELP http_requests_total Cumulative HTTP requests received
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 10.0
http_requests_total{method="POST",status="500"} 1.0

# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{handler="checkout",le="0.05"} 1
http_request_duration_seconds_bucket{handler="checkout",le="0.25"} 2
http_request_duration_seconds_bucket{handler="checkout",le="+Inf"} 3
http_request_duration_seconds_sum{handler="checkout"} 0.975
http_request_duration_seconds_count{handler="checkout"} 3
```

---

## 3. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `metrics_new_registry` | `() -> map` | Allocates an isolated metric registry holding multiple metric families. |
| `metrics_register_counter` | `(reg: map, name: str, help: str)` | Registers a new Counter family. |
| `metrics_register_gauge` | `(reg: map, name: str, help: str)` | Registers a new Gauge family. |
| `metrics_register_histogram`| `(reg: map, name: str, help: str, buckets: list)` | Registers a new Histogram family with bucket thresholds. |
| `metrics_inc` | `(reg: map, name: str, labels: map, by: float)` | Increments a Counter series by `by`. |
| `metrics_set_value` | `(reg: map, name: str, labels: map, v: float)` | Sets the instantaneous value of a Gauge series. |
| `metrics_observe` | `(reg: map, name: str, labels: map, v: float)` | Records a floating-point sample into a Histogram. |
| `metrics_render_prometheus` | `(reg: map) -> str` | Serializes the registry to text exposition for `/metrics` scraping. |

---

## 4. Practical Implementation: Exposing `/metrics`

```lateralus
import metrics

pub fn main() {
    let reg = metrics_new_registry()

    // 1. Setup metrics
    metrics_register_counter(reg, "jobs_processed_total", "Completed job count")
    let latency_bounds = [0.01, 0.05, 0.1, 0.5]
    metrics_register_histogram(reg, "job_duration_seconds", "Job runtime", latency_bounds)

    // 2. Track jobs
    let labels = {}
    labels["queue"] = "priority"
    metrics_inc(reg, "jobs_processed_total", labels, 1.0)
    metrics_observe(reg, "job_duration_seconds", labels, 0.042)

    // 3. Render for HTTP scrape handler
    let payload = metrics_render_prometheus(reg)
}
```

---

## 5. Verification & Test Suite

The test suite in `tests/stdlib_metrics_tutorial.ltl` validates:
- Metric family registration and label fingerprinting.
- Strict monotonicity of Counters and Gauge point mutations.
- Histogram cumulative bucket dispersion and `+Inf` overflow counting.
- Compliant Prometheus `# HELP` and `# TYPE` header rendering.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_metrics_tutorial.ltl
python -m lateralus_lang check examples/metrics_tutorial.ltl
```
