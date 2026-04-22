# Why Lateralus?

> *"Spiral out, keep going."*

## The Problem with Today's Languages

| You Want | But You Get |
|----------|-------------|
| **Type safety** | Rust's 10-minute compile times |
| **Expressiveness** | Python's runtime type errors |
| **Performance** | Go's verbose error handling |
| **Modern features** | C++'s footguns everywhere |

## Lateralus: The Sweet Spot

```
                    Expressiveness
                         ↑
                         │
            Python  ●    │    ● Lateralus
                         │         ↗
            TypeScript ● │      ↗
                         │   ↗
                    ─────┼─────────→ Performance
                         │   ↘
                 Java  ● │      ↘
                         │         ↘
                    C  ● │           ● Rust
                         │
```

## One Feature That Changes Everything: Pipelines

### Before (JavaScript)
```javascript
const result = take(
  sortBy(
    filter(
      map(users, u => u.name),
      n => n.startsWith('A')
    ),
    n => n.length
  ),
  5
);
```

### After (Lateralus)
```lateralus
let result = users
    |> map(u -> u.name)
    |> filter(n -> n.starts_with("A"))
    |> sort_by(n -> n.len())
    |> take(5)
```

**Read it like English. Write it in order. No nesting hell.**

---

## Real Code Comparisons

### HTTP Server

<table>
<tr><th>Go (47 lines)</th><th>Lateralus (12 lines)</th></tr>
<tr>
<td>

```go
package main

import (
    "encoding/json"
    "net/http"
)

type User struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func main() {
    http.HandleFunc("/users", func(w http.ResponseWriter, r *http.Request) {
        if r.Method != "GET" {
            http.Error(w, "Method not allowed", 405)
            return
        }
        users := []User{
            {Name: "Alice", Email: "alice@example.com"},
        }
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(users)
    })
    http.ListenAndServe(":8080", nil)
}
```

</td>
<td>

```lateralus
import net.http { serve, json }

fn main() {
    serve(":8080", {
        "/users" => |req| {
            let users = [
                { name: "Alice", email: "alice@example.com" }
            ]
            json(users)
        }
    })
}
```

</td>
</tr>
</table>

### Error Handling

<table>
<tr><th>Rust (verbose)</th><th>Lateralus (elegant)</th></tr>
<tr>
<td>

```rust
fn process_file(path: &str) -> Result<String, Error> {
    let contents = fs::read_to_string(path)?;
    let parsed: Config = serde_json::from_str(&contents)?;
    let validated = validate(parsed)?;
    Ok(format!("Loaded: {}", validated.name))
}
```

</td>
<td>

```lateralus
fn process_file(path: str) -> Result<str> {
    read_file(path)
        |> json.parse<Config>()
        |> validate()
        |> map(c -> "Loaded: {c.name}")
}
```

</td>
</tr>
</table>

### Pattern Matching

```lateralus
// Exhaustive, expressive, beautiful
fn describe(value: Json) -> str {
    match value {
        Json.Null           => "nothing"
        Json.Bool(true)     => "yes"
        Json.Bool(false)    => "no"
        Json.Number(n)      => "number: {n}"
        Json.String(s)      => "text: {s}"
        Json.Array([])      => "empty list"
        Json.Array([x, ..]) => "list starting with {x}"
        Json.Object(map)    => "object with {map.len()} keys"
    }
}
```

---

## What Makes Lateralus Different

### 🔗 Pipeline-First Design
Not an afterthought. The entire stdlib is designed around `|>`.

### ⚡ Fast Compilation
Incremental compilation with LLVM. Most projects build in under 2 seconds.

### 🎯 Inference That Works
Hindley-Milner type inference. Write `let x = 42`, get `Int`. No annotations needed 90% of the time.

### 🔄 First-Class Async
```lateralus
async fn fetch_all(urls: [str]) -> [Response] {
    urls |> map(fetch) |> await_all()
}
```

### 📦 Zero Dependencies
The compiler is a single binary. No runtime, no garbage collector, no VM.

### 🛡️ Memory Safe
Ownership semantics like Rust, but with escape hatches that don't require a PhD.

---

## Who Is Lateralus For?

- **Data engineers** tired of Python's type chaos
- **Systems programmers** who want Rust's safety without the compile times
- **Security researchers** who need fast, auditable code
- **Scientists** who want expressiveness AND performance
- **Anyone** who's ever said "why can't I just pipe this?"

---

## Get Started in 30 Seconds

```bash
pip install lateralus-lang
```

```lateralus
// hello.ltl
fn main() {
    "Hello, Lateralus!"
        |> println()
}
```

```bash
lateralus run hello.ltl
# Hello, Lateralus!
```

---

## The Ecosystem

| Tool | Description |
|------|-------------|
| `lateralus` | Compiler & runner |
| `lateralus-lsp` | Language server for any editor |
| `lateralus-fmt` | Code formatter |
| `lateralus-doc` | Documentation generator |
| `lateralus-test` | Built-in test framework |

**Editor Support**: VS Code, Neovim, Helix, Zed, Sublime, Vim

---

## Links

- 🌐 [lateralus.dev](https://lateralus.dev)
- 📦 [GitHub](https://github.com/bad-antics/lateralus-lang)
- 📚 [Wiki](https://github.com/bad-antics/lateralus-lang/wiki)
- ▶️ [Playground](https://lateralus.dev/playground/)

---

*Built by bad-antics. MIT Licensed.*
