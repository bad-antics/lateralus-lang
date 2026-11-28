2. Code Patch / Fix

**File: `docs/blog/stdlib-influx-line-tutorial.md`**
```markdown
# InfluxDB Line Protocol in Lateralus

The `stdlib.influx_line` module provides utilities for serializing and parsing data in the InfluxDB Line Protocol format. This is essential for exporting time-series telemetry to InfluxDB-compatible backends.

## Line Protocol Structure
A valid line consists of:
1. **Measurement**: The name of the metric (e.g., `cpu`).
2. **Tags**: Key-value pairs for indexing (e.g., `host=server01,region=us-east`).
3. **Fields**: Typed metric values (e.g., `usage=0.75i`).
4. **Timestamp** (Optional): Nanosecond UNIX timestamp.

## Escaping Rules
- **Measurement**: Escape spaces, commas, and equals signs.
- **Tag Keys/Values**: Escape spaces, commas, and equals signs.
- **String Fields**: Escape backslashes and double quotes.

## Usage Example
```lateralus
import stdlib.influx_line

let line = influx_line.line(
    measurement: "cpu",
    tags: { "host": "server01", "region": "us-east" },
    fields: { "usage": 0.75, "core": 1 },
    timestamp: 1609459200000000000
)

// Output: cpu,host=server01,region=us-east usage=0.75,core=1i 1609459200000000000
```

## Parsing
Use `influx_line.parse_line` to convert a line back into a structured map:
```lateralus
let parsed = influx_line.parse_line("cpu,host=server01 usage=0.75 1609459200000000000")
// { measurement: "cpu", tags: { "host": "server01" }, fields: { "usage": 0.75 }, timestamp: 1609459200000000000 }
```
```

**File: `examples/influx_line_tutorial.ltl`**
```lateralus
import stdlib.influx_line
import stdlib.io

// Example: Exporting CPU telemetry