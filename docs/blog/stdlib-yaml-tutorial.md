# Mastering YAML 1.2 in Lateralus: Indentation Trees, Block Mappings, and Safe Parsing

YAML (YAML Ain't Markup Language) is the ubiquitous standard for human-readable data serialization, configuration topologies, Kubernetes manifests, and CI/CD pipelines. Unlike line-delimited JSON or strict TOML tables, YAML's design relies heavily on significant whitespace, indentation hierarchies, and polymorphic scalar representations.

In this tutorial, we demonstrate how to parse, validate, and serialize structured YAML documents natively in Lateralus using pure functional pipelines and explicit indentation-tracking state machines.

---

## 1. Architectural Foundations: Significant Whitespace & Tokens

A robust YAML parser decomposes raw document streams into three fundamental tokens:
1. **Indentation Offsets**: Determining parent-child hierarchy in nested dictionaries and sequences.
2. **Key-Value Delimiters (`: `)**: Mapping mapping keys to scalar values or nested mappings.
3. **Block Sequence Indicators (`- `)**: Denoting elements in ordered homogenous or heterogenous collections.

```lateralus
// Tokenizing a block mapping pair
fn parse_kv_line(line: string) -> tuple(string, string) {
    let parts = split(line, ": ");
    return (parts[0], parts[1]);
}
```

---

## 2. Parsing Block Mappings and Nested Dictionaries

In YAML 1.2, dictionary entries at the root level share an indentation column of zero (`depth = 0`). Subordinate attributes increase indentation by two or four spaces:

```yaml
server:
  host: 127.0.0.1
  port: 8080
  tls: true
```

Lateralus evaluates this using stateful fold expressions over lines:

```lateralus
fn parse_yaml_document(doc: string) -> dict(string, string) {
    let lines = split(doc, "\n");
    let mut config = {};
    let mut current_section = "";

    for line in lines {
        let trimmed = trim(line);
        if len(trimmed) == 0 || starts_with(trimmed, "#") {
            continue;
        }
        let indent = count_leading_spaces(line);
        if indent == 0 && ends_with(trimmed, ":") {
            current_section = slice(trimmed, 0, len(trimmed) - 1);
        } else if indent > 0 && contains(trimmed, ": ") {
            let (key, val) = parse_kv_line(trimmed);
            let full_key = current_section + "." + key;
            config[full_key] = val;
        }
    }
    return config;
}
```

---

## 3. Parsing Block Sequences

Block sequences use leading hyphens (`- `). A list of replica nodes or security principals parses seamlessly:

```yaml
peers:
  - 10.0.0.1:9000
  - 10.0.0.2:9000
  - 10.0.0.3:9000
```

Lateralus tokenizes sequence elements by checking `starts_with(trimmed, "- ")` and extracting the trailing scalar content.

---

## 4. Scalar Type Coercion & Safety

YAML 1.2 defines distinct rules for scalar resolution:
- **Booleans**: `true`, `false`, `yes`, `no`, `on`, `off`.
- **Numbers**: Canonical integers (`42`, `-17`) and floating-point IEEE-754 values (`3.1415`).
- **Null Values**: `~`, `null`, or blank trailing values.
- **Strings**: Unquoted plain scalars or quoted strings (`"production"`).

Our parser enforces safe defaults, preventing the classic "Norway Problem" (where unquoted `NO` evaluates to boolean `false`).

---

## 5. End-to-End Verification and Golden Test Vectors

We verify our implementation with complete end-to-end runnable examples and reproducible test vectors:
- **Executable Example**: See `examples/yaml_tutorial.ltl` for a complete demonstration of multi-document streaming, nested mapping lookups, and sequence parsing.
- **Unit Test Vectors**: See `tests/stdlib_yaml_tutorial.ltl` verifying indentation hierarchy calculations, key-value extraction, boolean normalization, and array sequence indexing.

Run the test suite directly:
```bash
python -m lateralus_lang check examples/yaml_tutorial.ltl
python -m lateralus_lang check tests/stdlib_yaml_tutorial.ltl
pytest tests/test_compiler.py
```
