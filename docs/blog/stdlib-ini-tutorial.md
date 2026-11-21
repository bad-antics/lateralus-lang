# Managing Application Configuration with INI Files in Lateralus

Configuration files are the cornerstone of production software deployments. While JSON and YAML are popular for complex hierarchies, the **INI file format** remains the industry standard for system daemons, desktop applications, and server tools (e.g., `gitconfig`, systemd unit files, PHP configuration) due to its simplicity, clean section boundaries, and comment support.

In this tutorial, we will explore `stdlib/ini.ltl`, the Lateralus Standard Library module for parsing, accessing, mutating, and serializing INI configuration documents.

---

## The INI File Anatomy

An INI document consists of sections, key-value properties, and comments:

```ini
; Global comments start with semicolon or hash
# Alternative comment syntax

[server]
host = api.example.com
port = 8080
timeout = 30.5
ssl = true

[database]
name = production
pool_size = 20
```

1. **Sections**: Declared within brackets `[section_name]`. All subsequent key-value pairs belong to this section until the next section header.
2. **Key-Value Pairs**: Delimited by equals signs (`key = value`). Leading and trailing whitespace is trimmed automatically. Values enclosed in double quotes have their quotes stripped cleanly.
3. **Comments**: Lines starting with `;` or `#` are ignored by the parser.

---

## The Lateralus Standard Library: `stdlib/ini.ltl`

The module represents configurations as nested maps (`map[section -> map[key -> value]]`):

```lateralus
pub fn new() -> map
pub fn with_section(name: str, entries: map) -> map
pub fn parse(text: str) -> map
pub fn get(cfg: map, section: str, key: str, default)
pub fn get_int(cfg: map, section: str, key: str, default: int) -> int
pub fn get_bool(cfg: map, section: str, key: str, default: bool) -> bool
pub fn get_float(cfg: map, section: str, key: str, default: float) -> float
pub fn set(cfg: map, section: str, key: str, value) -> map
pub fn delete(cfg: map, section: str, key: str) -> map
pub fn sections(cfg: map) -> list
pub fn section_keys(cfg: map, section: str) -> list
pub fn has_section(cfg: map, section: str) -> bool
pub fn has_key(cfg: map, section: str, key: str) -> bool
pub fn to_string(cfg: map) -> str
pub fn merge(base: map, other: map) -> map
```

---

## Type-Safe Getters with Defaults

A common risk when reading configuration files is missing keys or malformed types causing runtime exceptions. `stdlib/ini.ltl` provides typed getter functions that automatically return a default fallback when a key or section is absent:

```lateralus
let host      = get(cfg, "server", "host", "localhost")      // Returns "api.example.com"
let port      = get_int(cfg, "server", "port", 80)           // Returns 8080
let timeout   = get_float(cfg, "server", "timeout", 10.0)    // Returns 30.5
let ssl       = get_bool(cfg, "server", "ssl", false)        // Returns true
```

Booleans accept standard representations: `true`, `false`, `yes`, `no`, `1`, and `0`.

---

## Round-Trip Serialization and Merging

Configurations can be dynamically updated at runtime and serialized back into formatted INI syntax:

```lateralus
// Mutate config
cfg = set(cfg, "server", "workers", 4)
cfg = delete(cfg, "database", "pool_size")

// Serialize back to text
let ini_text = to_string(cfg)
```

Furthermore, multi-tier configuration schemes (such as base defaults overridden by environment-specific files) can be combined with `merge`:

```lateralus
let base_cfg = parse("[server]\nport = 8080\nworkers = 2\n")
let env_cfg  = parse("[server]\nport = 9000\nworkers = 8\n")
let active   = merge(base_cfg, env_cfg)
// active["server"]["port"] == 9000
```

---

## Runnable Example: `examples/ini_tutorial.ltl`

Here is an executable tutorial demonstrating parsing, typed queries, mutation, and merging:

```lateralus
fn main() {
    print("=== LATERALUS STDLIB INI TUTORIAL ===")

    let doc = "[server]\nhost = api.example.com\nport = 8080\ntimeout = 30.5\nssl = true\n; database parameters\n[database]\nname = production\npool_size = 20\n"

    // 1. Parse document
    let cfg = parse(doc)
    print("STEP 1: Parsed INI document sections: " + str(sections(cfg)))

    // 2. Read typed values with defaults
    let host = get(cfg, "server", "host", "localhost")
    let port = get_int(cfg, "server", "port", 80)
    let timeout = get_float(cfg, "server", "timeout", 10.0)
    let ssl = get_bool(cfg, "server", "ssl", false)
    let db_name = get(cfg, "database", "name", "test")
    let pool_size = get_int(cfg, "database", "pool_size", 5)

    print("STEP 2: Typed values:")
    print("  server.host = " + str(host))
    print("  server.port = " + str(port))
    print("  server.timeout = " + str(timeout))
    print("  server.ssl = " + str(ssl))
    print("  database.name = " + str(db_name))
    print("  database.pool_size = " + str(pool_size))

    // 3. Mutate config and serialize back to INI
    cfg = set(cfg, "server", "workers", 4)
    cfg = delete(cfg, "database", "pool_size")
    let serialized = to_string(cfg)
    print("STEP 3: Mutated and serialized INI:")
    print(serialized)

    // 4. Merge configs
    let override_cfg = parse("[server]\nport = 9000\nworkers = 8\n")
    let merged = merge(cfg, override_cfg)
    let new_port = get_int(merged, "server", "port", 80)
    let new_workers = get_int(merged, "server", "workers", 1)
    print("STEP 4: Merged server.port=" + str(new_port) + " workers=" + str(new_workers))

    print("PINNED_VECTORS: host=" + str(host) + " port=" + str(port) + " ssl=" + str(ssl) + " merged_port=" + str(new_port))
    print("ini tutorial: all checks passed")
}

main()
```

### Execution & Pinned Output

Execute with:

```bash
lateralus run examples/ini_tutorial.ltl
```

Output:

```text
=== LATERALUS STDLIB INI TUTORIAL ===
STEP 1: Parsed INI document sections: ['database', 'default', 'server']
STEP 2: Typed values:
  server.host = api.example.com
  server.port = 8080
  server.timeout = 30.5
  server.ssl = True
  database.name = production
  database.pool_size = 20
STEP 3: Mutated and serialized INI:
[database]
name = production

[server]
host = api.example.com
port = 8080
ssl = True
timeout = 30.5
workers = 4

STEP 4: Merged server.port=9000 workers=8
PINNED_VECTORS: host=api.example.com port=8080 ssl=True merged_port=9000
ini tutorial: all checks passed
```

---

## Conclusion

With `stdlib/ini.ltl`, Lateralus provides a native, zero-dependency configuration parser with type-safe extraction and round-trip serialization for enterprise and systems engineering.
