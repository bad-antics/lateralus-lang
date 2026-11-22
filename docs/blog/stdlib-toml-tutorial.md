# Declarative Application Configuration with Lateralus `stdlib/toml.ltl` (TOML 1.0)

Configuration files bridge human developers with production runtime engines. While JSON is ubiquitous, it lacks comments and demands strict trailing-comma syntax. YAML supports comments but suffers from ambiguous indentation rules and silent type coercions (such as parsing `NO` as `false`).

**TOML** (Tom's Obvious, Minimal Language) is designed to map unambiguously to hash tables with a clear, minimal syntax. Standardized under **TOML 1.0**, it is the configuration format of choice for Cargo (`Cargo.toml`), pyproject (`pyproject.toml`), and containerd.

Lateralus includes a lightweight, zero-dependency TOML parser in `stdlib/toml.ltl`.

---

## 1. Syntax Mechanics & Data Models

A TOML document parses directly into nested hash tables containing five core types:

1. **Key/Value Pairs**: `key = "value"`, `port = 8080`, `active = true`.
2. **Inline Arrays**: `tags = ["web", "api", "v1"]`.
3. **Tables (`[table_name]`)**: Create dedicated sub-tables. Sub-tables can be deeply nested using dotted syntax:
   ```toml
   [database.credentials]
   username = "db_admin"
   ```
4. **Arrays of Tables (`[[items]]`)**: Appends a new dictionary entry to a named array each time the header appears. Ideal for configuring repeated endpoints, middleware, or plugins.

---

## 2. Robust State-Machine Parsing

Naive regex-based parsers frequently corrupt configuration when strings contain syntax characters. `stdlib/toml.ltl` employs state-machine tokenizers:

- **String-Aware Comment Stripping (`strip_comment`)**: Lines like `title = "Release #1" # comment` track quote boundaries (`"` or `'`), ensuring internal `#` signs are preserved as string content while trailing comments are cleanly stripped.
- **Dotted Path Splitting (`split_path`)**: Deeply nested tables like `[a.b.c]` recursively construct and traverse intermediate dictionaries.

---

## 3. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `toml_parse` | `(text: str) -> map` | Parses a complete TOML 1.0 document into a nested dictionary structure. |
| `toml_open_table` | `(root: map, path: str) -> map` | Traverses/creates intermediate tables for dotted paths. |
| `toml_open_array_table` | `(root: map, path: str) -> map` | Appends a new table entry into an array-of-tables structure. |

---

## 4. Practical Implementation: Microservice Routing

```lateralus
import toml

pub fn main() {
    let raw_config = "
    [service]
    name = \"gateway\"
    port = 8080

    [[routes]]
    path = \"/auth\"
    secure = true

    [[routes]]
    path = \"/health\"
    secure = false
    "

    let config = toml_parse(raw_config)

    let svc = config["service"]
    print("Starting service: " + svc["name"] + " on port " + str(svc["port"]))

    let routes = config["routes"]
    print("Loaded " + str(len(routes)) + " route definitions.")
}
```

---

## 5. Verification & Test Vectors

The test suite in `tests/stdlib_toml_tutorial.ltl` exercises:
- Basic scalar types (strings, integers, booleans, inline arrays).
- Comment stripping with embedded hashtag characters.
- Deeply nested table navigation.
- Array-of-tables (`[[table]]`) instantiation.

Run the test suite locally:
```bash
python -m lateralus_lang check tests/stdlib_toml_tutorial.ltl
python -m lateralus_lang check examples/toml_tutorial.ltl
```
