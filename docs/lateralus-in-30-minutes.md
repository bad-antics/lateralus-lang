# Lateralus in 30 minutes

A pragmatic, hands-on tour of Lateralus. By the end you'll have written real programs:
a CLI greeter, a CSV summariser, a tiny parser, and a BM25 search query — using only
the standard library and `python3 -m lateralus_lang run file.ltl`.

> Total reading + typing time: ~30 minutes. No prior Lateralus knowledge assumed.

---

## 0. Setup (1 min)

```bash
git clone https://github.com/bad-antics/lateralus-lang
cd lateralus-lang
python3 -m lateralus_lang run examples/spiral_hello.ltl
```

Every example below saves as `*.ltl` and runs the same way.

---

## 1. Hello, world (1 min)

```ltl
println("hello, lateralus")
```

Run it: `python3 -m lateralus_lang run hello.ltl` →

```
hello, lateralus
```

That's it. No `main`, no module headers required — top-level statements just execute.

---

## 2. Variables, types, control flow (3 min)

```ltl
let name = "world"
let mut count = 0

while count < 3 {
    println("hi, " + name + " #" + str(count))
    count = count + 1
}

if count == 3 {
    println("done")
} else {
    println("unexpected")
}
```

Notes:

- `let` is immutable, `let mut` is mutable.
- Type annotations (`let n: int = 0`) are optional but supported.
- `+` concatenates strings; use `str(x)` to coerce numbers.
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`. Logic: `&&`, `||`, `!`.

---

## 3. Functions (3 min)

```ltl
fn greet(who: str) -> str {
    return "hello, " + who
}

fn add(a: int, b: int) -> int {
    return a + b
}

println(greet("antics"))
println(str(add(2, 40)))
```

- `fn name(args) -> ReturnType { ... }` is the canonical form.
- Return type can be `void` (or omitted in many contexts).
- Recursion works fine; tail-call optimisation is not guaranteed.

**Idiom — keep helpers at top level.** Deeply nested `fn`-inside-`fn` can confuse
the parser. Prefer pulling helpers out to module scope.

---

## 4. Lists and dicts (3 min)

```ltl
let xs = [1, 2, 3]
xs = xs + [4]
println(str(len(xs)))           // 4
println(str(xs[2]))             // 3

let dict = {"alice": 30, "bob": 25}
dict["carol"] = 40
println(str(dict["alice"]))     // 30
```

Common list ops: `len(xs)`, append via `xs = xs + [v]`, indexed access `xs[i]` and assignment `xs[i] = v`.
Common dict ops: `d[k]`, `d[k] = v`, `len(d)`. Iterate with `for k in keys(d)` if
the runtime exposes it; otherwise build keys manually as you insert.

**Idiom — module-scope mutable state.** A bare `let mut COUNT = 0` at module scope
won't propagate into functions. Use a 1-element list as a *cell*:

```ltl
let COUNT = [0]

fn bump() { COUNT[0] = COUNT[0] + 1 }

bump(); bump(); println(str(COUNT[0]))   // 2
```

This pattern shows up everywhere in the stdlib — see [`stdlib/ranking.ltl`](../stdlib/ranking.ltl).

---

## 5. Strings (3 min)

```ltl
let s = "lateralus"
println(slice(s, 0, 4))              // "late"
println(str(len(s)))                 // 9

// chr() / ord() for explicit characters
let nl = chr(10)
let lbrace = chr(123)                // "{"  — see idiom below

// Build a string by accumulator
let mut buf = ""
let mut i = 0
while i < len(s) {
    buf = slice(s, i, i + 1) + buf
    i = i + 1
}
println(buf)                          // "sularetal"
```

**Idiom — special characters via `chr()`.** Bare `"{"` or `"["` literals can break
codegen in some contexts. Use `chr(123)`, `chr(125)`, `chr(91)`, `chr(93)`,
`chr(34)`, `chr(92)` for `{`, `}`, `[`, `]`, `"`, `\`. See
[`examples/rosetta/json_mini.ltl`](../examples/rosetta/json_mini.ltl) for a working parser.

---

## 6. CLI greeter (3 min)

Save as `greet.ltl`:

```ltl
fn greet(name: str, loud: bool) -> str {
    let msg = "hello, " + name
    if loud { return msg + "!" }
    return msg
}

println(greet("antics", true))
println(greet("world", false))
```

Run: `python3 -m lateralus_lang run greet.ltl` →

```
hello, antics!
hello, world
```

---

## 7. CSV summariser (4 min)

Lateralus has no built-in CSV module here, but splitting text is one loop. Save as
`csv_sum.ltl`:

```ltl
let DATA = "name,score\nalice,42\nbob,17\ncarol,73\ndave,8"

fn split_lines(s: str) -> list {
    let out = []
    let buf = ""
    let i = 0
    while i < len(s) {
        let c = slice(s, i, i + 1)
        if c == "\n" { out = out + [buf]; buf = "" }
        else { buf = buf + c }
        i = i + 1
    }
    if len(buf) > 0 { out = out + [buf] }
    return out
}

fn split_comma(s: str) -> list {
    let out = []
    let buf = ""
    let i = 0
    while i < len(s) {
        let c = slice(s, i, i + 1)
        if c == "," { out = out + [buf]; buf = "" }
        else { buf = buf + c }
        i = i + 1
    }
    out = out + [buf]
    return out
}

let lines = split_lines(DATA)
let mut total = 0
let mut n = 0
let mut row = 1                      // skip header
while row < len(lines) {
    let cells = split_comma(lines[row])
    total = total + int(cells[1])
    n = n + 1
    row = row + 1
}

println("rows: " + str(n))
println("sum:  " + str(total))
println("avg:  " + str(total / n))
```

Output:

```
rows: 4
sum:  140
avg:  35.0
```

You now have a generic loader for any line-oriented dataset.

---

## 8. A tiny parser (5 min)

Recursive-descent parsers are the hardest thing most beginners write. Lateralus
keeps them readable by holding parser state in a list-cell.

Save as `parse_int_list.ltl`:

```ltl
// Parse "[1, 2, 30, 400]" into a list of ints.
let STATE = ["", 0]   // [source, position]

fn peek() -> str {
    if STATE[1] >= len(STATE[0]) { return "" }
    return slice(STATE[0], STATE[1], STATE[1] + 1)
}

fn advance() -> str {
    let c = peek(); STATE[1] = STATE[1] + 1; return c
}

fn skip_ws() {
    while STATE[1] < len(STATE[0]) {
        let c = peek()
        if c == " " || c == "\t" { STATE[1] = STATE[1] + 1 } else { return }
    }
}

fn is_digit(c: str) -> bool { return c >= "0" && c <= "9" }

fn parse_int() -> int {
    skip_ws()
    let buf = ""
    while is_digit(peek()) { buf = buf + advance() }
    return int(buf)
}

fn parse_list() -> list {
    skip_ws()
    advance()                        // consume "["
    let out = []
    skip_ws()
    if peek() == "]" { advance(); return out }
    out = out + [parse_int()]
    skip_ws()
    while peek() == "," {
        advance(); skip_ws()
        out = out + [parse_int()]
        skip_ws()
    }
    advance()                        // consume "]"
    return out
}

STATE[0] = "[1, 2, 30, 400]"
STATE[1] = 0
let xs = parse_list()
let i = 0
while i < len(xs) { println(str(xs[i])); i = i + 1 }
```

Output: `1`, `2`, `30`, `400`.

You've now built the core scaffold every JSON / config / DSL parser in the
standard library uses.

---

## 9. Real search: BM25 in 60 lines (5 min)

The Wave 11 stdlib module [`stdlib/ranking.ltl`](../stdlib/ranking.ltl) ships
BM25, TF-IDF, and cosine similarity. The end-to-end demo is
[`examples/spiral_ranking.ltl`](../examples/spiral_ranking.ltl) — open it and
note three things:

1. The same `tokenize` loop you wrote above (lowercase + alphanumeric only).
2. A `df` dict mapping each term to the number of documents containing it.
3. The BM25 score: `idf(term) * tf*(k1+1) / (tf + k1*(1 - b + b*dl/avgdl))`.

Run it:

```bash
python3 -m lateralus_lang run examples/spiral_ranking.ltl
```

You'll see four queries each return ranked top-K hits over a 7-document corpus.
That's a real search engine in pure Lateralus, no FFI.

---

## 10. Where to go next (2 min)

- **[CHEATSHEET.md](../CHEATSHEET.md)** — every syntactic form on one page.
- **[`stdlib/`](../stdlib/)** — 139 modules: crypto, parquet, search, graphs,
  ranking, observability, network, …
- **[`examples/advent_of_code/`](../examples/advent_of_code/)** — daily puzzle
  solutions, idiomatic Lateralus.
- **[`examples/rosetta/`](../examples/rosetta/)** — classic algorithms ported
  cleanly: knapsack, n-queens, topological sort, Huffman, JSON parser.
- **[`examples/lt_logs.ltl`](../examples/lt_logs.ltl)** and
  **[`examples/lt_trace.ltl`](../examples/lt_trace.ltl)** — production-shaped
  observability tooling in <300 lines each.
- **[BOUNTIES.md](../BOUNTIES.md)** — open contribution targets if you want to
  extend the stdlib.

You've now seen variables, control flow, functions, collections, strings,
recursive parsing, and applied IR — the whole working surface. The rest is just
more of the same patterns at scale.

Welcome to Lateralus.
