# LATERALUS v3.2.0-dev — `@law` Executable Specifications

> *Spiral outward. Build something beautiful.*

**Status:** In development
**Author:** bad-antics
**License:** MIT

---

## What no other mainstream language has

Lateralus v3.2 introduces **`@law` — first-class executable specifications**.
A boolean-returning function tagged `@law` is registered by the compiler as a
property test. Generators are **auto-derived from the declared parameter types**.
No typeclass instances. No per-parameter strategies. No boilerplate.

```lateralus
@law
fn addition_commutative(a: int, b: int) -> bool {
    return a + b == b + a
}

@law
fn reverse_involutive(xs: list) -> bool {
    return list_reverse(list_reverse(xs)) == xs
}
```

```bash
$ lateralus verify examples/laws_demo.ltl --seed 42
  ✓  addition_commutative  (100 trials)
  ✓  reverse_involutive  (100 trials)
  ...
  16 passed  0 failed  0 skipped
```

When a law fails, the runner **shrinks** the input to a minimal counter-example:

```
✗  all_positive  (failed on trial 1)
   counter-example: x=0
```

### Why this is novel

| Tool | Cost to test `foo(xs: list[int], n: int)` |
|------|------|
| Haskell QuickCheck | Write `Arbitrary [Int]` + `Arbitrary Int` instances |
| Python Hypothesis | `@given(st.lists(st.integers()), st.integers())` |
| Idris / Lean | Write a formal proof |
| **Lateralus** | `@law` — that's the entire contract |

Lateralus owns the type system end-to-end, so the compiler already knows how to
materialize `list[int]` without being told twice. The specification **is** the
code.

### CLI

```
lateralus verify <file> [--trials N] [--seed S]
```

### Supported types (auto-generated)

`int`, `float`, `bool`, `str`, `list`, `list[T]`, `map`, `map[K,V]`, `any`.
User-defined types are gracefully skipped with a reason; future releases will
derive structural generators for records.

### Shrinking

- Integers / floats: halve magnitudes, try 0, try ±1
- Strings: empty, one char, drop last char
- Lists: drop each element; recursively shrink inner values by inferred element type
- Maps: drop each key; try empty

Up to 100 shrinking steps per failed trial.

---

# LATERALUS v3.1.0 — PyPI, Marketplace & C Backend Perf

> *Spiral outward. Build something beautiful.*

**Release Date:** 2026-04-21
**Author:** bad-antics
**License:** MIT

---

## TL;DR

Lateralus is now installable via a single command:

```bash
pip install lateralus-lang
```

The VS Code extension is published to the Marketplace (`lateralus.lateralus-lang`),
and the C99 backend now produces native binaries that beat CPython by **~80×** on
fib and **~30×** on mandelbrot — byte-identical output, 16 KB stripped binaries,
no external runtime.

## Highlights

### 📦 Distribution

- **PyPI**: [pypi.org/project/lateralus-lang/3.1.0](https://pypi.org/project/lateralus-lang/3.1.0/)
- **VS Code Marketplace**: `lateralus.lateralus-lang@3.1.0` — syntax highlighting,
  LSP, debugger UI, 30+ snippets
- **Linguist submission staged** — 20 compiling code samples + TextMate grammar
  repo prepared in [docs/linguist/](docs/linguist/)

### ⚡ C Backend Performance Wins

| Benchmark       | Lateralus C99 | Lateralus interp | CPython  | Node.js  | Speedup vs CPython |
|-----------------|---------------|------------------|----------|----------|--------------------|
| fib(35)         | **0.004 s**   | 0.474 s          | 0.236 s  | 0.110 s  | ~60×               |
| sieve(50k)      | **0.001 s**   | 0.272 s          | 0.025 s  | 0.091 s  | ~30×               |
| mandelbrot      | **0.003 s**   | 0.325 s          | 0.084 s  | 0.095 s  | ~30×               |
| nbody(5k steps) | **0.001 s**   | 0.277 s          | 0.036 s  | 0.095 s  | ~40×               |

All outputs byte-identical across the Lateralus interpreter, our C99 backend,
and Node.js. (CPython differs from the reference implementations by a single
ULP on `nbody` due to its own FP rounding — tracked in the harness.) Native
binaries are **16 KB stripped** (`gcc -O2 -lm`), no Lateralus runtime dependency.

#### What changed in the C codegen
- **Polymorphic `println` / `print` dispatch** — type-inferred, so
  `println(int)`, `println(float)`, `println(bool)`, `println(string)` all
  produce correct C from user code that looks identical
- **Builtin cast functions** — `int(x)`, `float(x)`, `bool(x)`, `str(x)` now
  compile to native C casts or type-dispatched `ltl_*_to_str` calls
- **Typed C-array lowering for homogeneous numeric list literals** — e.g.
  `let xs = [0.0, 4.84, 8.34, 12.89, 15.37]` compiles to `double xs[5] = {...}`
  with native indexing, turning `xs[i] - xs[j]` into one subtraction instead
  of two tagged-union unboxes. This unblocked `nbody` at full precision (`%.17g`)
- **Math-builtin return-type inference** — `sqrt`, `pow`, `sin`, `log`, etc.
  now return `double` in the type table, so expressions like `sqrt(d2) * 0.01`
  stay fully native-typed through the inner loop

#### Honest caveat (tracked for v3.2)

One of the five benchmarks still goes through the interpreter only;
the C backend currently lacks:

- **`any`-typed return sites with mixed primitive/struct variants** (blocks
  `binary_trees`, which uses `fn make(d: int) -> any` returning either an
  `int` sentinel `0` or a `Tree { left, right }` struct)

This needs a proper design pass for dynamic value representation in typed
codegen, not a one-line fix. List-repetition (`[true] * (n+1)`), truthy
coercion from tagged values, and homogeneous-list arrays — previously blocking
`sieve` and `nbody` — were landed in v3.1. We ship the interpreter number for
`binary_trees` rather than fake the C-backend column. See
[benchmarks/README.md](benchmarks/README.md).

### 🔧 Packaging Fixes

- Removed stale "proprietary" wording that contradicted the MIT license
- Added project URLs: Homepage / Documentation / Papers / Repository / Issues / Changelog
- Expanded PyPI classifiers (Beta status, OSI-approved MIT, Python 3.13)
- `__init__.py` docstring now describes the real feature set (HM inference,
  ADTs, multi-target codegen) instead of placeholder text
- Synced `__version__` with `pyproject.toml` (drifted at 3.0.0 vs 3.0.1)

### 📚 Documentation

- All **58 research PDFs** rebuilt to canonical style (Helvetica family + Courier only)
- Block-level PyMuPDF extraction preserves original paragraph structure
- 0 page-count mismatches across 4,657 pages
- New [docs/hn-launch-faq.md](docs/hn-launch-faq.md) — 8-category Q&A covering
  perf, type system, concurrency, tooling, and honest design regrets

### 🧑‍💻 Developer Experience

- New [scripts/seed_repo_template/](scripts/seed_repo_template/) — one-command
  project bootstrap (`new-lateralus-project.sh <name>`). Ships with
  `.gitattributes` pre-configured to force `linguist-language=Lateralus`
- **1976 / 1976 tests passing**

### 🧪 Benchmark Harness

- New [benchmarks/](benchmarks/) directory — 4 backends × 5 workloads
- 2 warmup + 5 measured iterations per run, wall-clock median
- Graceful skip with logged reason when a backend can't compile a workload
  (no silent zero-filling)

---

## Historical Release Notes

---

# LATERALUS v2.4.0 — Deep Internals, Optimizer & Stdlib Expansion

**Release Date:** 2025-07-19
**Author:** bad-antics

---

## Highlights

### 🛠️ 4 New CLI Subcommands (total: 26)

| Command | Description |
|---------|-------------|
| `bench` | Run micro-benchmarks on compile/parse pipelines |
| `profile` | Profile compilation with per-phase timing breakdown |
| `disasm` | Disassemble `.ltbc` bytecode files to readable `.ltasm` |
| `clean` | Remove build artifacts, caches, and `__pycache__` directories |

### ⚙️ VM Disassembler (~300 lines)

Full bytecode-to-assembly decompiler with round-trip verification:
- `disassemble()` — Convert Bytecode objects to human-readable `.ltasm`
- `disassemble_instruction()` — Single-instruction decode with operand formatting
- Two-pass algorithm: jump target collection → labeled output generation

### 💻 Enhanced REPL — 3 New Commands (total: 14)

| Command | Description |
|---------|-------------|
| `:save <file>` | Save session history to a file |
| `:doc <topic>` | Look up docs for 51 builtins/keywords |
| `:profile` | Profile next expression with per-phase timing |

### 🧮 3 New Optimizer Passes (total: 10)

| Pass | Description |
|------|-------------|
| **Dead branch elimination** | Evaluates constant conditions, simplifies unreachable branches |
| **Algebraic simplification** | 20 identities: additive, multiplicative, bitwise, shift, boolean |
| **Function inlining analysis** | Scores candidates on size, frequency, purity, params, recursion |

### 📦 7 New Stdlib Modules (total: 59)

| Module | Purpose |
|--------|---------|
| `heap` | Binary min-heap: push, pop, peek, merge, heap_sort, n_smallest |
| `deque` | Double-ended queue: push/pop front/back, rotation, reverse |
| `trie` | Prefix trie: insert, get, has, prefix matching, longest prefix |
| `ini` | INI config parser/writer: sections, typed getters, merge |
| `arena` | Region-based memory allocator: block management, O(1) reset |
| `pool` | Object pool: acquire/release, bulk ops, drain, utilization stats |
| `lru` | LRU cache: get/put with eviction, hit/miss tracking, resize |

### 🧪 207 New Tests (total: 1,976)

| Suite | Tests | Coverage |
|-------|-------|----------|
| DAP server | 52 | All 15 DAP handlers |
| REPL | 47 | Basic + enhanced REPL, 9 test classes |
| VM expanded | 61 | Disassembler, round-trip, string ops, bitwise, assembler edges |
| Optimizer | 47 new (99 total) | Dead branches, algebraic identities, inline analysis |

---

## Previous Release

# LATERALUS v2.3.0 — Tooling Expansion, New Stdlib & OS Utilities

> *Spiral outward. Build something beautiful.*

**Release Date:** 2025-07-18
**Author:** bad-antics
**License:** Proprietary — LATERALUS Research

---

## Highlights

### 📦 6 New Stdlib Modules (total: 52)

| Module | Purpose |
|--------|---------|
| `sort` | Sorting algorithms (quicksort, mergesort, insertion, selection) + binary search, inversions |
| `set` | Set operations on lists: union, intersection, difference, power set, fold |
| `ringbuf` | Fixed-size circular buffer with push/pop/peek/drain |
| `semver` | Semantic Versioning 2.0.0 parsing, comparison, range satisfaction |
| `event` | Pub/sub event emitter with on/once/off/fire/pipe |
| `template` | String template engine with `<<name>>` delimiters and HTML escaping |

### 🔍 5 New Linter Rules (total: 21+)

| Rule | Severity | Description |
|------|----------|-------------|
| `constant-condition` | WARNING | `if true`, `if false`, `guard true` |
| `unused-import` | WARNING | Imported module never referenced |
| `deep-nesting` | INFO/WARN | 5+ indent levels (7+ = WARNING) |
| `string-concat-in-loop` | INFO | `+= "..."` inside for/while loops |
| `mutable-default` | WARNING | `fn(param = [])` or `fn(param = {})` |

### 🎨 Formatter Improvements

- **Trailing comma normalization** — Adds trailing commas before `}`, `]`, `)` closers
- **Blank line collapse** — Merges 3+ blank lines down to max 2

### 🧠 LSP Server Enhancements

| Feature | Description |
|---------|-------------|
| **Code Actions** | 4 quick-fix actions: var→let, remove semicolons, prefix unused vars, remove duplicate imports |
| **Rename Symbol** | Full-document word-boundary rename via `textDocument/rename` |
| **Prepare Rename** | Validates cursor position before rename, returns range and placeholder |

### 📝 3 New Examples (total: 37)

| Example | Description |
|---------|-------------|
| `v23_showcase.ltl` | Sorting, sets, ring buffers, semver, events, templates (~350 lines) |
| `game_of_life.ltl` | Conway's Game of Life with patterns and simulation (~200 lines) |
| `interpreter_demo.ltl` | Full arithmetic expression evaluator with tokenizer, parser, AST, interpreter, REPL (~310 lines) |

### 🖥️ LateralusOS — 7 New Shell Commands (total: 55+)

| Command | Description |
|---------|-------------|
| `top` | Task monitor with summary, uptime, per-task state/priority |
| `df` | Filesystem usage (ramfs, procfs, devfs) |
| `id` | Display user/group identity info |
| `seq [s] <e>` | Print number sequences |
| `tr <f> <t>` | Character transliteration |
| `rev <str>` | Reverse a string |
| `factor <n>` | Prime factorization |

---

## What's Changed (summary)

| Category | Details |
|----------|---------|
| **Language Version** | v2.3.0 |
| **Stdlib Modules** | 46 → 52 (+6 new) |
| **Linter Rules** | +5 new rules |
| **Formatter Phases** | 6 → 8 (+trailing comma, +blank collapse) |
| **LSP Handlers** | +3 (code actions, rename, prepare rename) |
| **OS Shell Commands** | 53 → 55+ (+7 new utilities) |
| **Tests** | 1,769 passing in ~5.2s |
| **Examples** | 34 → 37, all compiling cleanly (37/37) |
| **Health** | 44/44 files present, 12/12 modules importable |

---

## Install

```bash
pip install -e .
```

## Test

```bash
pytest tests/ -v --tb=short
# 1,769 passed in ~5.2s
```

## LateralusOS

```bash
cd lateralus-os
./build_and_boot.sh --test    # Headless boot test
./build_and_boot.sh --iso     # Build ISO only
./build_and_boot.sh --gui     # QEMU with GUI desktop
```

### New Shell Commands
```
top                     # Task monitor
df                      # Filesystem usage
id                      # User identity
seq 1 10                # Print 1..10
seq 5                   # Print 1..5
tr a b                  # Translate 'a' to 'b'
rev hello               # Print 'olleh'
factor 42               # Print '42: 2 3 7'
```

---

*Created by bad-antics — LATERALUS Research*
