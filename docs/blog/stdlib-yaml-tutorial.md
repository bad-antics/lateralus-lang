# YAML 1.2 Subset Parsing with `stdlib/yaml.ltl`

YAML is the config format of Kubernetes, GitHub Actions, and most of
the infrastructure world — and its full spec is famously a tar pit.
`stdlib/yaml.ltl` takes the pragmatic route: a **YAML 1.2 subset**
covering block mappings, block sequences, plain scalars, and comments,
in about 160 lines of recursive descent.

This tutorial walks the pipeline from raw text to typed values.
Companion: `examples/yaml_tutorial.ltl`.

> Scope notes: anchors, aliases and merge keys are not resolved; flow
> style (`{a: 1}`, `[1,2]`) is not supported; `- key: value` inline
> maps inside sequences are not supported (use a bare `-` and indent).

---

## The pipeline

```text
raw text
  → normalise: split lines, strip comments, drop blanks
  → parse_block: dispatch on first token ("-" → seq, ":" → map, else scalar)
  → parse_seq / parse_map: consume lines at a fixed indent
  → scalarize: nil / bool / int / quoted-str / plain-str
```

Indentation *is* the structure: `parse_map` and `parse_seq` stop as
soon as a line's indent differs from the block they opened, returning
`[value, next_index]` so the caller resumes exactly where nesting ends.

## strip_comment — and a real bug it had

`strip_comment` scans for `#` while tracking quote state, so `#`
inside `"..."` or `'...'` survives. The module's original code ran the
in-string and not-in-string checks as two independent `if`s: when a
closing quote flipped `in_str` off, the second `if` re-processed the
same character — the quote reopened the string state and every later
`#` was swallowed as "inside quotes". The tutorial's inlined copy
restructures this into `if/else` and documents the fix; the stdlib
module itself still carries the bug (flagged for a future fix PR).

## scalarize

The leaf coercion is deliberately small: empty/`~`/`null` → `nil`,
`true`/`false` → bool, digit strings (optional leading `-`) → int,
single/double-quoted strings unwrapped, everything else stays a
string. Note `3.14` stays a **string** — the subset has no float
coercion.

## What the subset handles

```yaml
name: demo
count: 3
enabled: true
note: ~
server:
  host: localhost
  port: 8080
items:
  - alpha
  - 42
users:
  -
    name: alice
    role: admin
```

…producing nested maps/lists with typed scalars, exactly as the
tutorial's pinned output shows.

## Running the tutorial

```bash
python -m lateralus_lang run examples/yaml_tutorial.ltl
python -m lateralus_lang check examples/yaml_tutorial.ltl
python -m pytest tests/test_yaml_tutorial.py -x -q
```

The example is self-contained: module code inlined with local
`index_of`/`starts_with`/`trim`/`split_lines`/`try_int` helpers — the
module's `import strings` surface is not provided by the `run`
runtime prelude.
