# InfluxDB Line Protocol: Invariants, Character Escaping, and Ingestion Parsing in Lateralus

## 1. Introduction & Theoretical Foundations

In modern telemetry infrastructure, Internet of Things (IoT) monitoring, and distributed observability platforms (such as InfluxDB, Telegraf, QuestDB, and VictoriaMetrics), high-frequency metric collection requires an ingestion format with negligible parsing overhead and minimal wire bloat.

While general-purpose serialization formats (such as JSON or XML) impose heavy string parsing, delimiter scanning, and type-reflection penalties, the **InfluxDB Line Protocol** is a purpose-built, human-readable text format optimized for zero-copy streaming over HTTP POST, TCP sockets, and UDP datagrams. It represents a single measurement point as a single newline-delimited text line containing dimensions, metrics, and timestamps.

Lateralus provides complete serialization, character escaping, and parsing capabilities for the InfluxDB Line Protocol in `stdlib/influx_line.ltl`.

---

## 2. Protocol Grammar & Structural Taxonomy

An InfluxDB Line Protocol point conforms to the following formal grammar:
$$\text{measurement}[,\text{tag\_key}=\text{tag\_value},\dots]\quad \text{field\_key}=\text{field\_value}[,\dots]\quad [\text{timestamp}]$$

A valid line consists of four discrete components separated by whitespace:
1. **Measurement**: A string identifying the metric table or domain (e.g., `cpu`, `disk_io`, `weather_station`).
2. **Tag Set (Optional)**: A comma-separated list of key-value pairs representing dimensional metadata.
3. **Field Set (Mandatory)**: A comma-separated list of key-value pairs representing the actual payload metrics.
4. **Timestamp (Optional)**: An integer representing Unix epoch time (conventionally nanosecond precision). If omitted, the server assigns its local ingestion wall-clock time.

### Semantic Distinction: Tags vs. Fields
| Property | Tag Set (`tag=val`) | Field Set (`field=val`) |
| :--- | :--- | :--- |
| **Indexing** | Fully indexed in the Time-Series Index (TSI). | Unindexed; stored directly in columnar data files (TSM). |
| **Cardinality** | Low-to-medium cardinality (e.g. `host`, `region`). | High or continuous cardinality (e.g. `temperature`, `cpu_pct`). |
| **Data Types** | Always string identifiers. | Strongly typed: `int`, `float`, `bool`, or `string`. |
| **Query Semantics** | Fast filtering (`WHERE host = 'server-01'`) & grouping (`GROUP BY region`). | Aggregation calculations (`AVG(cpu_pct)`, `SUM(bytes)`). |

---

## 3. Character Escaping Specifications & Type Encodings

Because delimiters (spaces, commas, and equal signs) dictate the grammar, literal occurrences of these characters inside identifiers require backslash escaping (`\`):

### Identifier Escaping Rules
- **Measurement**: Must escape spaces (`\ `) and commas (`\,`).
- **Tag Keys & Tag Values**: Must escape spaces (`\ `), commas (`\,`), and equal signs (`\=`).
- **Field Keys**: Must escape spaces (`\ `), commas (`\,`), and equal signs (`\=`).

### Field Value Typing Invariants
In the field set, literal values must preserve their exact data types to prevent schema corruption:
1. **Float**: Formatted as unquoted decimal numbers (e.g. `42.85`, `0.64`).
2. **Integer**: Suffix with an `i` character (e.g. `1250i`, `42i`). Without the `i` suffix, InfluxDB stores the number as a 64-bit float, preventing integer bitwise operations.
3. **Boolean**: Represented as `true` or `false` (case-insensitive `t`/`f` also supported).
4. **String**: Must be enclosed in double quotes (`"..."`). Inner double quotes (`\"`) and backslashes (`\\`) must be escaped.

Lateralus provides dedicated formatting helpers to guarantee proper encoding:
```lateralus
pub fn field_int(v: int) -> str    { return str(v) + "i" }
pub fn field_float(v: str) -> str  { return v }
pub fn field_bool(v: bool) -> str  { if v { return "true" } return "false" }
pub fn field_string(v: str) -> str { return "\"" + escape_string_field(v) + "\"" }
```

---

## 4. Parser Architecture & State Machine

`stdlib/influx_line.ltl` implements a single-pass streaming parser:
1. **Measurement Phase**: Scans from index 0 until the first unescaped comma or space via `scan_unescaped(line, 0, ", ")`. Unescapes backslash sequences.
2. **Tag Parsing Phase**: If followed by a comma, iterates over key-value pairs delimited by `=` and `,` until an unescaped space is encountered.
3. **Field Parsing Phase**: Iterates over fields delimited by `=`. If a value starts with `"`, scans forward to the unescaped closing quote, allowing commas and spaces inside string fields.
4. **Timestamp Phase**: If a trailing space exists, parses the remainder as a 64-bit integer timestamp.

Returns a structured map:
```lateralus
{
    "measurement": "cpu",
    "tags": [["host", "server01"]],
    "fields": [["usage", "0.64"], ["count", "3i"]],
    "timestamp": 1700000000000000000
}
```

---

## 5. Lateralus `stdlib/influx_line.ltl` API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `line(measurement, tags, fields, timestamp_ns)` | `(str, list, list, int) -> str` | Serializes a point to line protocol format. Pass `timestamp_ns <= 0` to omit timestamp. |
| `parse_line(line: str)` | `(str) -> map` | Parses a line protocol string into `{measurement, tags, fields, timestamp}` or `nil`. |
| `field_int(v: int)` | `(int) -> str` | Formats integer with trailing `i` suffix (e.g. `42i`). |
| `field_float(v: str)` | `(str) -> str` | Formats float string. |
| `field_bool(v: bool)` | `(bool) -> str` | Formats boolean as `"true"` or `"false"`. |
| `field_string(v: str)` | `(str) -> str` | Wraps string in quotes and escapes inner double quotes and backslashes. |

---

## 6. Practical Implementation & Verification

### Executing the Runnable Example
A complete telemetry generation and parsing demonstration is provided in `examples/influx_line_tutorial.ltl`:
```shell
$ python -m lateralus_lang check examples/influx_line_tutorial.ltl
✓ examples/influx_line_tutorial.ltl: OK
```

The example demonstrates:
- Composing system telemetry with mixed-type fields (float CPU pct, integer goroutines, boolean health status, quoted status messages).
- Escaping tricky identifiers containing spaces, commas, and equal signs (`mount point=/var/lib=storage`).
- Parsing points back into structured maps and verifying data fidelity.

### Pinned Golden Test Vectors
The companion test suite `tests/stdlib_influx_line_tutorial.ltl` verifies:
- Minimal points without tags or timestamps (`heartbeat status=1i`).
- Points with multi-tag sets and nanosecond timestamps.
- Escaped identifiers with spaces, commas, and equal signs.
- String fields containing embedded double quotes (`error_msg="disk alert: \"drive almost full\""`).
- Formatting helpers for integer, float, boolean, and string values.

Validate the test suite with the Lateralus compiler:
```shell
$ python -m lateralus_lang check tests/stdlib_influx_line_tutorial.ltl
✓ tests/stdlib_influx_line_tutorial.ltl: OK
```
