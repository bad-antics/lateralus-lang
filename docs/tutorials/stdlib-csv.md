# Parsing and Generating Tabular Data with `stdlib.csv`

The `stdlib.csv` module provides standard RFC 4180 compliant parsing and serialization for comma-separated values (CSV) and delimited text formats. It handles embedded delimiters, escaped double-quotes, whitespace trimming, header-mapped record extraction, and custom separators (semicolons, tabs, pipes).

---

## 1. Raw Row Parsing

Parse delimited text into a list of row lists:

```lateralus
import csv

let text = "id,name,role\n1,Alice,Engineer\n2,Bob,Architect\n"
let rows = csv.parse(text, ",")

// rows[0] == ["id", "name", "role"]
// rows[1] == ["1", "Alice", "Engineer"]
// rows[2] == ["2", "Bob", "Architect"]
```

---

## 2. Header-Based Dictionary Extraction

When the first line contains column headers, `parse_dict` transforms the rows into structured key-value maps:

```lateralus
let data = "title,salary\nDeveloper,95000\nDesigner,85000\n"
let records = csv.parse_dict(data, ",")

for item in records {
    println("Role: " + item["title"] + " earns " + item["salary"])
}
```

---

## 3. RFC 4180 Quoting and Escaped Fields

The parser handles complex nested fields:
- **Embedded delimiters:** Values enclosed in quotes like `"New York, NY"` are preserved as a single field.
- **Escaped quotes:** Double-quote characters escaped as `""` inside quotes are decoded into literal `"` characters.

```lateralus
let tricky = "id,location\n101,\"London, \"\"HQ\"\", UK\"\n"
let rows = csv.parse(tricky, ",")
// rows[1][1] == 'London, "HQ", UK'
```

---

## 4. Generating CSV and Custom Delimiters

Export matrix rows or structured dictionary records into formatted CSV text:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`generate(rows, delim)`** | `(list, str) -> str` | Generates delimited text from a 2D list of row strings. |
| **`generate_dict(records, headers, delim)`** | `(list, list, str) -> str` | Generates delimited text with a header row from a list of maps. |

```lateralus
let headers = ["user", "active"]

let mut u1 = map_new()
u1["user"] = "john_doe"
u1["active"] = "true"

let csv_output = csv.generate_dict([u1], headers, ",")
// Output:
// user,active
// john_doe,true
```

---

## 5. End-to-End Example: Data Pipeline Pipeline

```lateralus
import csv

fn main() {
    let raw_payload = "product,qty,notes\nWidget A,45,Standard stock\nWidget B,12,\"Fragile, handle with care\"\n"
    
    // Parse records
    let items = csv.parse_dict(raw_payload, ",")
    
    for row in items {
        println("Processing " + row["product"] + " (" + row["qty"] + " units): " + row["notes"])
    }
}
```
