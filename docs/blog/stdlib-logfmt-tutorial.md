# Structured Logging with Logfmt in Lateralus

In high-throughput distributed systems, structured logging is critical for observability, debugging, and metric extraction. While JSON logging is widespread, it can be verbose and difficult to inspect in terminal pipelines using standard UNIX utilities like `grep`, `awk`, and `ripgrep`.

**Logfmt**, popularized by Heroku and Go ecosystems (e.g. `go-kit`), formats log events into clean `key=value` pairs on a single line:

```text
ts=2026-11-21T11:00:00Z level=info msg="hello world" job=42 empty=""
```

In this tutorial, we will explore `stdlib/logfmt.ltl`, the Lateralus Standard Library module for emitting and parsing logfmt streams.

---

## The Logfmt Format Specification

A logfmt record consists of space-separated `key=value` pairs:

1. **Bare Keys & Values**: If a value contains alphanumeric characters without spaces, equals signs, or quotes, it is rendered as a bare token:
   ```text
   level=info
   job=42
   ```

2. **Quoting Requirements**: A value **must** be enclosed in double quotes (`"..."`) if:
   - It contains whitespace (e.g. `msg="hello world"`).
   - It contains an equals sign `=` (e.g. `filter="status=active"`).
   - It contains a double quote `"` (e.g. `quote="she said \"hi\""`).
   - It is an empty string `""` (e.g. `empty=""`).

3. **Escaping Inside Quotes**: Inside a quoted value, any embedded backslashes (`\`) or double quotes (`"`) are escaped with a backslash (`\\` and `\"`).

---

## The Lateralus Standard Library: `stdlib/logfmt.ltl`

The module exposes three primary functions:

```lateralus
pub fn format_value(v: str) -> str
pub fn encode(pairs: list) -> str
pub fn parse(line: str) -> list
pub fn encode_map(m: map) -> str
```

### Value Formatting & Quoting Logic

The emitter checks whether each string requires quotation:

```lateralus
fn needs_quoting(v: str) -> bool {
    if len(v) == 0 { return true }
    let i = 0
    while i < len(v) {
        let c = char_at(v, i)
        if c == " " || c == "=" || c == "\"" { return true }
        i = i + 1
    }
    return false
}

pub fn format_value(v: str) -> str {
    if needs_quoting(v) {
        return "\"" + escape_quoted(v) + "\""
    }
    return v
}
```

---

## Runnable Example: `examples/logfmt_tutorial.ltl`

Here is a complete, executable demonstration showing emission and round-trip parsing:

```lateralus
// Helper string primitives
fn char_at(s: str, i: int) -> str { return slice(s, i, i + 1) }

// [Logfmt encoder and parser implementation]

fn main() {
    print("=== LATERALUS STDLIB LOGFMT TUTORIAL ===")

    // 1. Define structured key-value pairs
    let pairs = [
        ["level", "info"],
        ["msg", "hello world"],
        ["job", "42"],
        ["empty", ""]
    ]

    // 2. Encode to logfmt wire format
    let line = encode(pairs)
    print("STEP 1: Encoded logfmt line:")
    print(line)

    // 3. Parse logfmt line back into structured pairs
    let parsed = parse(line)
    print("STEP 2: Round-trip parsed key-value pairs (count=" + str(len(parsed)) + "):")
    let i = 0
    while i < len(parsed) {
        let p = parsed[i]
        print("  " + p[0] + " -> " + p[1])
        i = i + 1
    }

    print("PINNED_VECTORS: line='" + line + "' pairs_count=" + str(len(parsed)))
}

main()
```

### Execution & Pinned Output

Run the example using the Lateralus runtime:

```bash
lateralus run examples/logfmt_tutorial.ltl
```

Expected output:

```text
=== LATERALUS STDLIB LOGFMT TUTORIAL ===
STEP 1: Encoded logfmt line:
level=info msg="hello world" job=42 empty=""
STEP 2: Round-trip parsed key-value pairs (count=4):
  level -> info
  msg -> hello world
  job -> 42
  empty -> 
PINNED_VECTORS: line='level=info msg="hello world" job=42 empty=""' pairs_count=4
```

Notice:
1. `level=info` and `job=42` remain compact and bare.
2. `msg="hello world"` is cleanly quoted because of the whitespace.
3. `empty=""` is preserved as an explicit empty string.
4. Parsing correctly reconstructs all 4 key-value pairs in original order.

---

## Conclusion

With `stdlib/logfmt.ltl`, Lateralus applications can stream grep-friendly, human-readable structured logs across terminal pipelines, Loki ingesters, or container aggregators without external dependencies.
