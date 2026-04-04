# LATERALUS

> **A programming language that spirals outward — from simple ideas to profound compositions.**

[![Version](https://img.shields.io/badge/version-2.5.0-6699ff.svg)](#)
[![Tests](https://img.shields.io/badge/tests-1%2C976%20passing-00cc66.svg)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-ffcc00.svg)](#)
[![Zero Dependencies](https://img.shields.io/badge/deps-zero-ff6699.svg)](#)

LATERALUS combines pipeline-driven data flow, algebraic data types, Hindley-Milner
type inference, and built-in scientific/crypto engines into a language built for
**scientists**, **security researchers**, and **software engineers**.

Ships two tightly-coupled languages and a full compiler / VM stack:

| Extension | Name | Purpose |
|-----------|------|---------|
| `.ltl`    | Lateralus Script | High-level scripting with pipelines, ADTs, pattern matching, async/await |
| `.ltasm`  | Lateralus Assembly | Low-level register+stack assembly targeting the LTasm VM |

---

## Quick Start

```bash
# Install (editable, zero external deps)
pip install -e .

# Run a program
lateralus run examples/hello.ltl

# Transpile to Python
lateralus py examples/fibonacci.ltl -o fib.py

# Transpile to C99
lateralus c examples/fibonacci.ltl -o fib.c

# Transpile to freestanding C (no libc, for OS/embedded)
lateralus c examples/fibonacci.ltl --freestanding -o fib.c

# Assemble .ltasm
lateralus asm examples/hello.ltasm -o hello.ltbc

# Interactive REPL
lateralus repl

# Type-check only
lateralus check myfile.ltl
```

Or via Python module:

```bash
python -m lateralus_lang run examples/v15_showcase.ltl
python -m lateralus_lang repl
```


### VS Code Extension

Install the Lateralus extension for syntax highlighting, snippets, and language support:

```bash
# From marketplace
code --install-extension lateralus.lateralus-lang

# Or install from .vsix
cd vscode-lateralus && npx vsce package && code --install-extension lateralus-lang-2.5.1.vsix
```

---

## What's New in v2.4

### VM Disassembler & Enhanced Tooling (v2.4)

- **VM Disassembler** — Full bytecode-to-assembly decompiler with round-trip verification
- **4 New CLI Subcommands**: `bench`, `profile`, `disasm`, `clean`
- **Enhanced REPL**: `:save`, `:doc` (51 builtins), `:profile` per-phase timing
- **3 New Optimizer Passes**: Dead branch elimination, algebraic simplification (20 identities), function inlining analysis
- **7 New Stdlib Modules** (total: 59): `heap`, `deque`, `trie`, `ini`, `arena`, `pool`, `lru`
- **207 New Tests** (total: 1,976 passing)

### Result & Option Types

```ltl
fn safe_divide(a: float, b: float) -> Result<float, str> {
    if b == 0.0 { return Result::Err("division by zero") }
    return Result::Ok(a / b)
}

fn find_user(id: int) -> Option<User> {
    if id in users { return Option::Some(users[id]) }
    return Option::None
}
```

### Match Expressions (8 Pattern Types)

```ltl
let label = match result {
    Result::Ok(v) if v > 100  => "high: " + str(v),
    Result::Ok(v)              => "ok: " + str(v),
    Result::Err(msg)           => "error: " + msg,
}
```

Supports: literal, variable, wildcard, constructor, guard, range, or-pattern, and nested patterns.

### Hindley-Milner Type Inference

```ltl
let x = 42              // inferred: int
let y = x + 1           // inferred: int
let z = sqrt(float(x))  // inferred: float
```

Full Robinson unification with occurs check.

---

## Language Overview

### Variables & Constants

```ltl
let name   = "Lateralus"          // type inferred (str)
let count: int  = 0
const PI: float = 3.14159
```

### Functions

```ltl
fn add(x: int, y: int) -> int {
    return x + y
}

async fn fetch(url: str) -> str {
    let resp = await net.get(url)
    return resp.body
}

pub fn greet(name: str) {
    io.println("Hello, " + name + "!")
}
```

### Pipeline Operators

```ltl
// Standard pipeline
let result = [1, 2, 3, 4, 5]
    |> filter((x) => x % 2 == 0)
    |> map((x) => x ** 2)
    |> sum()

// Bind pipeline (monadic chaining)
let output = get_data()
    |>= validate()
    |>= transform()
    |>= save()
```

### Pattern Matching

```ltl
match status_code {
    200       => println("OK"),
    404       => println("Not Found"),
    500..599  => println("Server Error"),
    _         => println("Unknown"),
}
```

### Error Handling

```ltl
try {
    let data = load_config("app.toml")
    process(data)
} recover FileNotFound(e) {
    println("Config missing: " + e.message)
} recover ParseError(e) {
    println("Bad config: " + e.message)
} recover * (e) {
    println("Unexpected: " + e.message)
} ensure {
    cleanup()
}
```

### Comprehensions (v1.4+)

```ltl
let squares  = [x ** 2 for x in range(10)]
let evens    = [x for x in data if x % 2 == 0]
let pairs    = {k: v for k, v in entries if v > 0}
```

### Loops

```ltl
for item in collection {
    process(item)
}

while condition {
    step()
}
```

### Lambdas & Closures

```ltl
let double = (x: int) => x * 2
let nums   = [1, 2, 3] |> map((n) => n * n)
```

---

## Assembly Language — LTasm (.ltasm)

```asm
; Lateralus Assembly — hello world
.section code
.global _start

_start:
    PUSH_STR  0          ; push string table index 0
    CALL      println    ; built-in I/O syscall
    PUSH_IMM  0          ; exit code
    EXIT

.section data
.string "Hello from LTasm!"
```

### ISA Summary (102 opcodes)

| Category      | Opcodes |
|---------------|---------|
| Stack         | `PUSH_IMM`, `PUSH_STR`, `POP`, `DUP`, `SWAP`, `ROT` |
| Arithmetic    | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG`, `POW` |
| Bitwise       | `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR`, `SAR` |
| Comparison    | `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` |
| Control Flow  | `JMP`, `JZ`, `JNZ`, `JL`, `JLE`, `JG`, `JGE`, `CALL`, `RET`, `HALT` |
| Registers     | `STORE_REG`, `LOAD_REG` (r0–r15) |
| Memory/Heap   | `ALLOC`, `FREE`, `LOAD_HEAP`, `STORE_HEAP` |
| Type coercion | `TO_INT`, `TO_FLOAT`, `TO_STR`, `TO_BOOL` |
| I/O           | `PRINT`, `PRINTLN`, `INPUT` |
| Error         | `TRY_BEGIN`, `TRY_END`, `THROW`, `RETHROW` |
| Concurrency   | `SPAWN`, `YIELD`, `AWAIT` |

---

## Built-in Engines

### 🔬 Science Engine
- CODATA physical constants (c, h, k_B, N_A, ...)
- ODE solvers (RK4)
- FFT & power spectral density
- Statistics (mean, std, regression, correlation)
- Matrix algebra & linear systems

### 🔒 Crypto Engine
- SHA-256, SHA-512, BLAKE2b
- AES-256-GCM encrypt/decrypt
- HMAC authentication
- Password hashing (PBKDF2)
- Constant-time comparison

### ⚙️ Math Engine
- Arbitrary-precision arithmetic
- Complex numbers
- Polynomials & interpolation
- Numerical integration (Simpson, trapezoidal)
- Combinatorics & number theory

---

## Compiler Pipeline

```
Source (.ltl)
    │
    ▼ Lexer           → Token stream
    │
    ▼ Parser          → AST (ast_nodes.py)
    │
    ▼ SemanticAnalyzer → IR Module (three-address code)
    │
    ├──▶ BytecodeGenerator → Bytecode (.ltbc)
    │         └──▶ VM  → execute
    │
    ├──▶ PythonTranspiler  → .py (Python 3.10+)
    │
    └──▶ CTranspiler       → .c  (hosted or freestanding)
```

Assembly pipeline:

```
Source (.ltasm)
    │
    ▼ Assembler (two-pass)
    │
    └──▶ Bytecode (.ltbc) → VM
```

---

## Project Structure

```
lateralus-lang/
├── lateralus_lang/         Python implementation
│   ├── ast_nodes.py        AST node hierarchy (106 node types)
│   ├── lexer.py            Tokenizer (.ltl + .ltasm)
│   ├── parser.py           Recursive-descent parser
│   ├── type_system.py      HM type inference engine
│   ├── ir.py               Three-address IR + semantic analysis
│   ├── compiler.py         Master pipeline orchestrator
│   ├── math_engine.py      Arbitrary-precision math
│   ├── science.py          Scientific computing
│   ├── crypto_engine.py    Cryptographic primitives
│   ├── codegen/
│   │   ├── bytecode.py     IR → LTasm bytecode
│   │   ├── python.py       AST → Python 3 transpiler
│   │   └── c.py            AST → C99 transpiler (hosted + freestanding)
│   ├── vm/
│   │   ├── opcodes.py      Full ISA (102 opcodes)
│   │   ├── assembler.py    .ltasm → Bytecode (two-pass)
│   │   └── vm.py           Stack VM executor
│   └── errors/
│       ├── handler.py      Error types, DNA fingerprinting
│       └── bridge.py       Integration bridge
├── stdlib/                 59 standard library modules (.ltl)
├── examples/               38 example programs (.ltl + .ltasm)
├── tests/                  1,976 tests (pytest)
├── docs/                   Documentation + website
├── bootstrap/              Self-hosting compiler sources
├── vscode-lateralus/       VS Code / VSCodium extension
├── lateralus-os/           LateralusOS — bare-metal OS (Multiboot2, x86_64)
│                           1.8MB kernel, double-buffered GUI desktop,
│                           animated wallpaper (Fibonacci spirals, stars),
│                           functional terminal (55+ commands), RAM filesystem,
│                           /proc + /dev virtual filesystems, PC speaker audio,
│                           cooperative scheduler, Alt+Tab, window animations,
│                           start menu, context menu, desktop icons, system
│                           monitor, PS/2 mouse, IPv4/ARP/UDP/ICMP/DHCP
│                           network stack, built-in apps (ltlc, chat, edit, pkg)
└── pyproject.toml
```

---

## Tooling

| Tool | Command |
|------|---------|
| Run program | `lateralus run file.ltl` |
| REPL | `lateralus repl` |
| Transpile to Python | `lateralus py file.ltl -o out.py` |
| Type check | `lateralus check file.ltl` |
| Format code | `lateralus fmt file.ltl` |
| Lint | `lateralus lint file.ltl` |
| Assemble | `lateralus asm file.ltasm -o out.ltbc` |
| LSP server | `lateralus lsp` |
| DAP debugger | `lateralus dap` |
| Package manager | `ltlpkg init my-project` |
| Benchmark | `lateralus bench` |
| Profile | `lateralus profile file.ltl` |
| Disassemble | `lateralus disasm file.ltbc` |
| Clean | `lateralus clean` |
| Notebook | `.ltlnb` files in VS Code |

---

## Website

**[bad-antics.github.io/lateralus](https://bad-antics.github.io/lateralus/)** — landing page with interactive code samples, feature comparison, and ecosystem directory.

---

## Ecosystem

Lateralus has a growing ecosystem of 22+ repositories:

| Repository | Description |
|-----------|-------------|
| [lateralus-lang](https://github.com/bad-antics/lateralus-lang) | Compiler, VM, stdlib, REPL (this repo) |
| [lateralus-compiler](https://github.com/bad-antics/lateralus-compiler) | Lexer, parser, AST, IR, codegen |
| [lateralus-grammar](https://github.com/bad-antics/lateralus-grammar) | TextMate grammars + 14 code samples |
| [lateralus-tutorials](https://github.com/bad-antics/lateralus-tutorials) | 25 chapters: basics to web servers |
| [lateralus-cookbook](https://github.com/bad-antics/lateralus-cookbook) | Recipes: strings, IO, concurrency, patterns |
| [lateralus-exercises](https://github.com/bad-antics/lateralus-exercises) | Practice problems by topic |
| [lateralus-koans](https://github.com/bad-antics/lateralus-koans) | Learn by fixing failing tests |
| [lateralus-rosetta](https://github.com/bad-antics/lateralus-rosetta) | 220 Rosetta Code solutions |
| [lateralus-euler](https://github.com/bad-antics/lateralus-euler) | 250 Project Euler solutions |
| [lateralus-benchmarks](https://github.com/bad-antics/lateralus-benchmarks) | 30 performance benchmarks |
| [lateralus-snippets](https://github.com/bad-antics/lateralus-snippets) | Copy-paste utility snippets |
| [lateralus-patterns](https://github.com/bad-antics/lateralus-patterns) | 51 design patterns (GoF + concurrency) |
| [lateralus-web](https://github.com/bad-antics/lateralus-web) | HTTP, routing, WebSocket, ORM, GraphQL |
| [lateralus-crypto](https://github.com/bad-antics/lateralus-crypto) | Hashing, ciphers, signatures |
| [lateralus-networking](https://github.com/bad-antics/lateralus-networking) | TCP/UDP, DNS, HTTP client |
| [lateralus-ml](https://github.com/bad-antics/lateralus-ml) | ML algorithms from scratch |
| [lateralus-science](https://github.com/bad-antics/lateralus-science) | Scientific computing toolkit |
| [lateralus-games](https://github.com/bad-antics/lateralus-games) | Game implementations |
| [lateralus-data-structures](https://github.com/bad-antics/lateralus-data-structures) | Trees, graphs, heaps, tries |
| [lateralus-algorithms](https://github.com/bad-antics/lateralus-algorithms) | Sorting, searching, DP, greedy |
| [lateralus-interview](https://github.com/bad-antics/lateralus-interview) | Interview prep problems |
| [lateralus-aoc](https://github.com/bad-antics/lateralus-aoc) | Advent of Code solutions |

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific suite
pytest tests/test_parser.py -v
pytest tests/test_type_system.py -v
pytest tests/test_v15_features.py -v

# Quick summary
pytest tests/ --tb=short -q
```

---

## Version

**LATERALUS v2.5.0**
Created and maintained by **bad-antics**
License: Proprietary — LATERALUS Research

*Spiral outward. Build something beautiful.*
