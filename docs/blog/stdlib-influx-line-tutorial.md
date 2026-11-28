# High-Throughput Time-Series Ingestion: InfluxDB Line Protocol in Lateralus (`stdlib/influx_line.ltl`)

Modern observability platforms, distributed tracing pipelines, and IoT sensor arrays rely on standardized, text-based wire protocols that can be streamed directly into time-series databases with zero overhead.

Among these, the **InfluxDB Line Protocol** has become the de facto industry standard for high-throughput metrics ingestion (used by InfluxDB, QuestDB, VictoriaMetrics, and Telegraf).

Lateralus ships with a zero-dependency, streaming implementation in `stdlib/influx_line.ltl`. This tutorial explores the architecture of the Line Protocol, its exact grammar and escaping rules, typed field formatting, serialization, and high-fidelity parsing.

---

## 1. Anatomy of InfluxDB Line Protocol

A valid InfluxDB Line Protocol record consists of four distinct components arranged in a strict single-line format:

```text
measurement[,tag_key=tag_value,...] field_key=field_value[,field_key=field_value,...] [timestamp_ns]
```

### Components Breakdown:
1. **Measurement (`str`)**:
   - The name of the metric or table (e.g., `cpu_usage`, `disk_io`, `temperature`).
2. **Tag Set (`list` of `[key, value]`)**:
   - Key-value metadata indexed by the database for rapid filtering and grouping.
   - **Crucial Rule**: Tags should be sorted alphabetically by key for optimal compression and write performance in InfluxDB engines (TSM / InfluxDB 3.0 IOx).
3. **Field Set (`list` of `[key, formatted_value]`)**:
   - The actual measurements or payload data. Fields are unindexed and typed (floats, integers, booleans, strings).
   - At least one field is required per line.
4. **Timestamp (`int`, optional)**:
   - UNIX timestamp in nanosecond precision. If omitted or `<= 0`, the ingestion server assigns the server's current arrival time.

### Visual Example:
```text
cpu,host=server01,region=us-west usage_user=42.85,processes=16i,active=true 1795363200000000000
│   └──────────────┬──────────────┘ └──────────────────┬─────────────────┘ └────────┬──────────┘
│                  │                                   │                            │
Measurement     Tag Set (indexed)                   Field Set (typed)          Nanosecond Timestamp
```

---

## 2. Escaping Rules and Character Disambiguation

Because Line Protocol uses commas `,`, spaces ` `, and equals signs `=` as structural token delimiters, literal instances of these characters inside identifiers must be strictly escaped with backslashes (`\`):

| Element | Escaped Characters | Function in Lateralus |
| :--- | :--- | :--- |
| **Measurement** | Comma (`,`), Space (` `) | `escape_measurement` |
| **Tag Keys & Values** | Comma (`,`), Equals (`=`), Space (` `) | `escape_ident` |
| **Field Keys** | Comma (`,`), Equals (`=`), Space (` `) | `escape_ident` |
| **Field String Values** | Double Quote (`"`), Backslash (`\`) | `escape_string_field` |

### Why String Fields Are Different:
String field values in InfluxDB Line Protocol are wrapped in double quotes (e.g., `message="disk full"`). Therefore, spaces, commas, and equals signs inside quotes do **not** need escaping, but internal quotes (`\"`) and backslashes (`\\`) must be escaped.

---

## 3. Typed Field Encoding in Lateralus

In Line Protocol, values are type-inferred based on their trailing tokens and delimiters:

```lateralus
import influx_line

// Integer: must have trailing 'i'
let i = influx_line.field_int(42)          // -> "42i"

// String: wrapped in quotes with internal quotes escaped
let s = influx_line.field_string("OK")     // -> "\"OK\""

// Float: bare decimal number
let f = influx_line.field_float("99.95")   // -> "99.95"

// Boolean: "true" or "false"
let b = influx_line.field_bool(true)       // -> "true"
```

---

## 4. API Reference: `stdlib/influx_line.ltl`

### `influx_line.line(measurement: str, tags: list, fields: list, timestamp_ns: int) -> str`
Serializes a telemetry record into a single InfluxDB Line Protocol string.
* `measurement`: The metric name.
* `tags`: List of `[key, value]` pairs (strings).
* `fields`: List of `[key, formatted_value]` pairs.
* `timestamp_ns`: Unix epoch nanoseconds (`int`). If `<= 0`, the timestamp is omitted.

### `influx_line.parse_line(line: str) -> map`
Parses an unescaped or escaped Line Protocol record into a structured map:
* `parsed["measurement"]`: The decoded measurement string.
* `parsed["tags"]`: List of `[k, v]` strings.
* `parsed["fields"]`: List of `[k, raw_value_string]`.
* `parsed["timestamp"]`: Integer nanosecond timestamp (or `0` if not present).
* Returns `nil` if the line is malformed.

---

## 5. End-to-End Example: Telemetry Exporter

Here is a practical Lateralus program demonstrating metrics serialization and roundtrip parsing (`examples/influx_line_tutorial.ltl`):

```lateralus
import influx_line

fn main() {
    // 1. Metric configuration
    let measurement = "system_load"
    let tags = [
        ["cluster", "production-eu"],
        ["host", "worker-01"]
    ]

    // 2. Metrics payload with appropriate types
    let fields = [
        ["cpu_pct", influx_line.field_float("76.4")],
        ["threads", influx_line.field_int(256)],
        ["healthy", influx_line.field_bool(true)],
        ["status", influx_line.field_string("All systems nominal")]
    ]

    // 3. Emit line with nanosecond timestamp
    let ts = 1795363200000000000
    let record = influx_line.line(measurement, tags, fields, ts)

    print("Emitted Line:")
    print(record)

    // 4. Parse back into structured map
    let parsed = influx_line.parse_line(record)
    print("Decoded measurement: " + parsed["measurement"])
    print("Decoded timestamp: " + str(parsed["timestamp"]))
}
```

Output:
```text
Emitted Line:
system_load,cluster=production-eu,host=worker-01 cpu_pct=76.4,threads=256i,healthy=true,status="All systems nominal" 1795363200000000000
Decoded measurement: system_load
Decoded timestamp: 1795363200000000000
```

---

## 6. Verifying Invariants with Pinned Test Vectors

The test suite in `tests/stdlib_influx_line_tutorial.ltl` enforces 5 pinned invariants:

1. **`test_line_basic_serialization`**: Strict delimiter spacing and comma placement.
2. **`test_field_type_formatting`**: Integer suffixation (`i`), booleans (`true`/`false`), and quotes.
3. **`test_escaping_mechanics`**: Complex escaping with commas in measurements, spaces in tags, and backslashes in fields.
4. **`test_parse_line_roundtrip`**: Bidirectional decoding integrity.
5. **`test_omit_timestamp_and_malformed`**: Validation of headless records and rejection of malformed lines.

Run the test suite with:
```bash
python3 -m lateralus_lang run tests/stdlib_influx_line_tutorial.ltl
```

---

## 7. Performance Best Practices

1. **Pre-sort Tags**: Always sort your tag keys lexicographically before building lines (`cluster`, `env`, `host`). InfluxDB engines shard and partition time series by the combined tag set; consistent ordering prevents server-side string reallocations.
2. **Nanosecond Timestamps**: Always pass true nanosecond precision timestamps when available (`ts > 0`) to preserve ordering across distributed nodes.
3. **Batch Writing**: In high-throughput production environments, aggregate 500–5,000 serialized lines separated by `\n` into single HTTP POST payloads to `/api/v2/write`.
