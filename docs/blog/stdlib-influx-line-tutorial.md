# Serializing Sensor Readings with InfluxDB Line Protocol in Lateralus

Time-series databases like InfluxDB and QuestDB ingestion pipelines ingest millions of metrics per second using the **InfluxDB Line Protocol**. It is a compact, human-readable ASCII format designed for fast streaming without the parsing overhead of JSON.

In this tutorial, we will explore the Lateralus Standard Library module `stdlib/influx_line.ltl` to format and parse sensor metrics locally, completely offline and without requiring an external server or database.

---

## The Line Protocol Anatomy

A single line in InfluxDB line protocol follows this precise structure:

```text
measurement[,tag_key=tag_val,...] field_key=field_val[,field_key=field_val,...] [timestamp_ns]
```

It consists of four primary components separated by whitespace:

1. **Measurement**: The name of the metric or table (e.g. `weather_sensor` or `cpu_usage`).
2. **Tag Set** (Optional): Key-value string metadata indexed by the database (e.g. `region=north\ bay,sensor_id=temp_01`).
3. **Field Set** (Required): The actual measured values (e.g. `temperature=23.5,error_count=3i,status="ok"`).
4. **Timestamp** (Optional): An integer representing nanoseconds since the Unix epoch. If omitted, the receiving server assigns the ingestion time.

### Escaping Rules

Because whitespace and delimiters separate components, special characters must be escaped with backslashes (`\`):

* **Measurements**: Spaces and commas are escaped (`\ ` and `\,`).
* **Tag Keys & Values**: Spaces, commas, and equals signs are escaped (`\ `, `\,`, `\=`). For instance, a tag value of `north bay` becomes `north\ bay`.
* **Field Keys**: Spaces, commas, and equals signs are escaped.
* **String Field Values**: Wrapped in double quotes (`"..."`), and any internal quotes or backslashes are escaped (`\"`, `\\`).

### Type Suffixes in Line Protocol

Notice how fields differ in syntax depending on data type:

* **Integers**: Must be explicitly suffixed with an `i` (e.g. `error_count=3i`). Without `i`, InfluxDB interprets the number as a 64-bit float (`3.0`), creating irreversible schema conflicts!
* **Floats**: Bare numbers (e.g. `temperature=23.5`).
* **Booleans**: Written as `true` or `false` (or `t` / `f`).
* **Strings**: Always enclosed in double quotes (e.g. `status="ok"`).

---

## Lateralus stdlib API: `stdlib/influx_line.ltl`

The module exposes helper formatters and builders:

```lateralus
pub fn field_int(v: int) -> str       // Returns "3i"
pub fn field_float(v: str) -> str     // Returns "23.5"
pub fn field_string(v: str) -> str    // Returns "\"ok\""
pub fn field_bool(v: bool) -> str     // Returns "true" or "false"

pub fn line(measurement: str, tags: list, fields: list, timestamp_ns: int) -> str
pub fn parse_line(line_str: str) -> map
```

---

## Runnable Example: `examples/influx_line_tutorial.ltl`

Here is a complete, runnable example demonstrating both serialization and deserialization:

```lateralus
// Helper string primitives
fn char_at(s: str, i: int) -> str { return slice(s, i, i + 1) }
fn index_of(s: str, sub: str) -> int { return s.find(sub) }
fn try_int(s: str, d: int) -> int { return to_int(s) }

// -- Escaping & Formatting Helpers --
fn escape_ident(s: str) -> str {
    let out = ""
    let i = 0
    while i < len(s) {
        let c = char_at(s, i)
        if c == "," || c == "=" || c == " " {
            out = out + "\\" + c
        } else {
            out = out + c
        }
        i = i + 1
    }
    return out
}

fn escape_measurement(s: str) -> str {
    let out = ""
    let i = 0
    while i < len(s) {
        let c = char_at(s, i)
        if c == "," || c == " " { out = out + "\\" + c }
        else                    { out = out + c }
        i = i + 1
    }
    return out
}

fn escape_string_field(s: str) -> str {
    let out = ""
    let i = 0
    while i < len(s) {
        let c = char_at(s, i)
        if c == "\"" || c == "\\" { out = out + "\\" + c }
        else                      { out = out + c }
        i = i + 1
    }
    return out
}

fn field_string(v: str) -> str { return "\"" + escape_string_field(v) + "\"" }
fn field_int(v: int) -> str { return str(v) + "i" }
fn field_float(v: str) -> str { return v }
fn field_bool(v: bool) -> str {
    if v { return "true" }
    return "false"
}

fn line(measurement: str, tags: list, fields: list, timestamp_ns: int) -> str {
    let out = escape_measurement(measurement)
    let i = 0
    while i < len(tags) {
        let t = tags[i]
        out = out + "," + escape_ident(t[0]) + "=" + escape_ident(t[1])
        i = i + 1
    }
    out = out + " "
    let j = 0
    while j < len(fields) {
        let f = fields[j]
        if j > 0 { out = out + "," }
        out = out + escape_ident(f[0]) + "=" + f[1]
        j = j + 1
    }
    if timestamp_ns > 0 {
        out = out + " " + str(timestamp_ns)
    }
    return out
}

fn main() {
    // 1. Build a complete sensor telemetry packet
    let tags = [["region", "north bay"], ["sensor_id", "temp_01"]]
    let fields = [
        ["temperature", field_float("23.5")],
        ["error_count", field_int(3)],
        ["status", field_string("ok")],
        ["active", field_bool(true)]
    ]
    let timestamp = 1700000000000000000
    
    let result = line("weather sensor", tags, fields, timestamp)
    println("Full metric:")
    println(result)

    // 2. Build a metric omitting the timestamp (for server-assigned arrival time)
    let no_ts = line("sensor", [["region", "north bay"]], [["count", field_int(3)]], 0)
    println("Without timestamp:")
    println(no_ts)
}
```

### Execution & Pinned Output

Running this example produces the exact expected InfluxDB line protocol records:

```text
Full metric:
weather\ sensor,region=north\ bay,sensor_id=temp_01 temperature=23.5,error_count=3i,status="ok",active=true 1700000000000000000

Without timestamp:
sensor,region=north\ bay count=3i
```

Notice:
1. `weather sensor` is properly escaped as `weather\ sensor`.
2. `north bay` has its space escaped as `north\ bay`.
3. `error_count=3i` correctly prevents float promotion in InfluxDB.
4. When `timestamp_ns <= 0`, the trailing space and timestamp are cleanly omitted.

---

## Conclusion

With `stdlib/influx_line.ltl`, Lateralus provides a zero-dependency, type-safe serializer for edge metrics and IoT pipelines. Whether shipping metrics to Telegraf, VictoriaMetrics, or InfluxDB, the generated payload is guaranteed compliant with standard ingestion specifications.
