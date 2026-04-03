# LATERALUS v2.4.0 — Deep Internals, Optimizer & Stdlib Expansion

> *Spiral outward. Build something beautiful.*

**Release Date:** 2025-07-19
**Author:** bad-antics
**License:** Proprietary — LATERALUS Research

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
