# `stdlib.yaml` — YAML 1.2 Parser and Emitter

The `stdlib.yaml` module provides lightweight, pure-Lateralus parsing and serialization for a YAML 1.2 subset, including block mappings, block sequences, plain scalars (integers, floats, booleans, strings, nulls), and comments.

---

## Functions

### `parse(text: str) -> any`
Parses a YAML document string into Lateralus data structures (`map`, `list`, or scalar).

```lateralus
import stdlib.yaml as yaml

let config = yaml.parse("server:\n  port: 8080\n  host: localhost")
// config["server"]["port"] == 8080
```

### `dump(val: any) -> str` (also aliased as `stringify` and `emit_yaml`)
Serializes Lateralus data structures into a formatted YAML string.

```lateralus
import stdlib.yaml as yaml

let data = {
    "app": "gateway",
    "replicas": 3,
    "active": true
}
let yaml_text = yaml.dump(data)
// app: gateway
// replicas: 3
// active: true
```

---

## Pipeline Usage

Like all Lateralus standard library modules, `yaml` is designed for ergonomic forward-pipelining (`|>`):

```lateralus
import io
import stdlib.yaml as yaml

fn get_port(config: map) -> int {
    return config["server"]["port"]
}

fn main() {
    let port = io.read_file("config.yml")
        |> yaml.parse()
        |> get_port()

    io.println("Server running on port: " + str(port))
}
```

---

## Round-Trip Guarantee

Any valid YAML mapping or sequence serialized with `dump()` parses back to an equivalent data structure:

```lateralus
let original = {"service": "auth", "port": 4000}
let serialized = yaml.dump(original)
let reloaded = yaml.parse(serialized)

assert reloaded["service"] == original["service"]
assert reloaded["port"] == original["port"]
```
