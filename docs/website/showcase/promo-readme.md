<div align="center">

# 🌀 Lateralus

### A Language That Spirals Outward

**Pipeline-driven • Type-inferred • Native-compiled**

[![Version](https://img.shields.io/badge/version-3.0.1-cyan?style=for-the-badge)](https://github.com/bad-antics/lateralus-lang)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Playground](https://img.shields.io/badge/Try-Playground-orange?style=for-the-badge)](https://lateralus.dev/playground/)

```
     ╭────────────────────────────────────────────────╮
     │                                                │
     │   users                                        │
     │       |> filter(u -> u.active)                │
     │       |> map(u -> u.email)                    │
     │       |> unique()                              │
     │       |> send_newsletter()                    │
     │                                                │
     ╰────────────────────────────────────────────────╯
```

[**Website**](https://lateralus.dev) • [**Docs**](https://github.com/bad-antics/lateralus-lang/wiki) • [**Playground**](https://lateralus.dev/playground/) • [**Discord**](#)

</div>

---

## ⚡ Quick Start

```bash
pip install lateralus-lang
```

```lateralus
// hello.ltl
fn main() {
    "Hello, Lateralus!" |> println()
}
```

```bash
lateralus run hello.ltl
# Hello, Lateralus!
```

---

## 🔥 Why Lateralus?

<table>
<tr>
<td width="50%">

### Before (Nested Calls)
```javascript
const result = take(
  sortBy(
    filter(
      map(users, u => u.name),
      n => n.length > 3
    ),
    n => n
  ),
  5
);
```

</td>
<td width="50%">

### After (Pipeline Flow)
```lateralus
let result = users
    |> map(u -> u.name)
    |> filter(n -> n.len() > 3)
    |> sort()
    |> take(5)
```

</td>
</tr>
</table>

**Read it like English. Write it in order. No nesting hell.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔗 **Pipeline Operators** | `|>` chains transformations naturally, left-to-right |
| 🎯 **Type Inference** | Hindley-Milner inference — minimal annotations needed |
| 🔄 **Pattern Matching** | Exhaustive matching with algebraic data types |
| ⚡ **Native Compilation** | LLVM backend → fast native binaries |
| 🚀 **Fast Builds** | Incremental compilation, sub-2-second rebuilds |
| 🔒 **Memory Safety** | Ownership semantics without the complexity |
| 📦 **Zero Runtime** | No VM, no GC, no dependencies |
| 🌐 **Async/Await** | First-class concurrency primitives |

---

## 📝 Code That Speaks

### Data Processing
```lateralus
fn analyze_sales(year: int) -> Report {
    read_csv("sales.csv")
        |> filter(r -> r.year == year)
        |> group_by(r -> r.region)
        |> map(|(region, sales)| {
            region: region,
            total: sales |> sum_by(s -> s.amount),
            count: sales.len()
        })
        |> sort_by(r -> r.total, desc: true)
        |> Report.from()
}
```

### Web Server
```lateralus
import net.http { serve, json }

fn main() {
    serve(":8080", {
        "/api/users" => |_| db.users |> filter(active) |> json(),
        "/api/user/:id" => |req| db.find(req.params.id) |> json()
    })
}
```

### Pattern Matching
```lateralus
fn describe(value: Json) -> str {
    match value {
        Json.Null        => "nothing"
        Json.Bool(b)     => "boolean: {b}"
        Json.Number(n)   => "number: {n}"
        Json.String(s)   => "string: {s}"
        Json.Array([])   => "empty array"
        Json.Array(arr)  => "array of {arr.len()} items"
        Json.Object(obj) => "object with {obj.len()} keys"
    }
}
```

---

## 🛠️ Ecosystem

| Tool | Purpose |
|------|---------|
| `lateralus` | Compiler, runner, REPL |
| `lateralus-lsp` | Language server for editors |
| `lateralus-fmt` | Code formatter |
| `lateralus-doc` | Documentation generator |
| `lateralus-test` | Built-in test framework |

**Editor Support**: [VS Code](https://marketplace.visualstudio.com/items?itemName=bad-antics.lateralus) • Neovim • Helix • Zed • Vim

---

## 📊 By the Numbers

- **2,400+** `.ltl` files in the wild
- **62** stdlib modules
- **1,976** passing tests
- **220** Rosetta Code solutions
- **25** tutorials
- **1** operating system (yes, [LateralusOS](https://lateralus.dev/os/))

---

## 🌐 Learn More

- 📖 [Documentation](https://github.com/bad-antics/lateralus-lang/wiki)
- ▶️ [Interactive Playground](https://lateralus.dev/playground/)
- 📚 [Tutorials](https://github.com/bad-antics/learn-lateralus)
- 📝 [Blog](https://lateralus.dev/blog/)
- 🔬 [Language Papers](https://lateralus.dev/papers/)

---

<div align="center">

*Spiral out. Keep going.*

**Made with 🖤 by [bad-antics](https://github.com/bad-antics)**

</div>
