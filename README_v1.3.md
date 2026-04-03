# LATERALUS

**A programming language designed for clarity, power, and discovery.**

LATERALUS combines pipeline-driven data flow, Julia-inspired mathematical elegance, and rich error diagnostics into a language built for scientists, engineers, and anyone who believes code should be as clear as the ideas it expresses.

## Features

- **Pipeline Operators** — Data flows naturally through `|>` chains
- **Optional Pipelines** — `|?` gracefully handles none values
- **Pattern Matching** — Expressive `match` expressions with guards
- **Structs** — Clean data modeling without boilerplate
- **Event System** — `emit`, `probe`, and `measure` for reactive programming
- **Mathematical Precision** — Arbitrary-precision arithmetic, auto-promotion
- **Scientific Computing** — Physical constants, ODE solvers, FFT, statistics
- **Cryptography** — SHA-256, BLAKE2b, AES-256-GCM, HMAC
- **Rich Errors** — Diagnostics with suggestions and fix hints
- **Type System** — Optional type annotations with inference
- **Self-Hosting** — Compiler bootstrap written in LATERALUS itself

## Quick Start

```bash
# Install
pip install -e .

# Run a program
lateralus run hello.ltl

# Start the REPL
lateralus repl

# Create a new project
ltlpkg init my-project
```

### Hello, World

```lateralus
fn main() {
    println("Hello, LATERALUS!")

    let result = [1, 2, 3, 4, 5]
        |> filter((x) => x % 2 == 0)
        |> map((x) => x ** 2)
        |> reduce((a, b) => a + b, 0)

    println("Sum of even squares: " + str(result))
}
```

## Ecosystem

| Component | Description |
|-----------|-------------|
| Compiler | Multi-target (Python transpiler + bytecode VM) |
| Math Engine | Matrices, vectors, AD, intervals, statistics |
| Crypto Engine | Hashing, encryption, HMAC, LBE encoding |
| Science Engine | Constants, ODE solvers, FFT, distributions |
| Markup Language | LTLML for documentation and publishing |
| LSP Server | Language server for IDE integration |
| Formatter | `ltlfmt` — automatic code formatting |
| Linter | `ltllint` — static analysis with suggestions |
| Debugger | Interactive breakpoint debugging + DAP |
| Package Manager | `ltlpkg` — dependency management |
| Profiler | Performance analysis and memory tracking |
| VS Code Extension | Syntax highlighting, snippets, language config |

## Standard Library

| Module | Contents |
|--------|----------|
| `math.ltl` | Trigonometry, logarithms, constants |
| `strings.ltl` | String manipulation |
| `collections.ltl` | List and map operations |
| `time.ltl` | Time and date utilities |
| `random.ltl` | Random number generation |
| `science.ltl` | Physical constants and conversions |
| `optimize.ltl` | Root finding, integration, minimization |
| `functional.ltl` | Higher-order functions, composition |
| `algorithms.ltl` | Sorting, searching, number theory |
| `data.ltl` | Stack, queue, set, priority queue, linked list |
| `matrix.ltl` | Matrix operations and linear algebra |
| `testing.ltl` | Assertions and test runner |
| `async.ltl` | Concurrency patterns |

## Documentation

- [Tutorial](docs/tutorial.ltlml) — Learn LATERALUS step by step
- [Language Specification](docs/language-spec.ltlml) — Complete syntax reference
- [Architecture](docs/architecture.ltlml) — How the compiler works
- [Quick Reference](docs/quick-reference.ltlml) — Cheat sheet
- [Formal Grammar](docs/grammar.ebnf) — EBNF specification

## Examples

| Example | Demonstrates |
|---------|-------------|
| `math_demo.ltl` | Mathematical computing |
| `graph_demo.ltl` | Graph algorithms and pipelines |
| `physics_sim.ltl` | N-body gravitational simulation |
| `statistics_demo.ltl` | Data analysis pipeline |
| `neural_network.ltl` | ML from scratch |
| `crypto_demo.ltl` | Cryptographic operations |
| `science_demo.ltl` | Scientific computing |

## Development

```bash
# Run all tests
make test

# Run specific suite
make test-math
make test-science
make test-tools

# Health check
make health

# Benchmarks
make bench

# Format code
make format

# Build documentation
python scripts/build_docs.py
```

## Project Structure

```
lateralus-lang/
    lateralus_lang/       # Python compiler implementation
    stdlib/               # Standard library (.ltl)
    tests/                # Test suites (~600+ tests)
    bootstrap/            # Self-hosting compiler (v2)
    editor/vscode/        # VS Code extension
    docs/                 # Documentation (.ltlml)
    examples/             # Example programs
    scripts/              # Build and maintenance tools
```

## Roadmap

| Version | Focus |
|---------|-------|
| **v1.3** | Ecosystem expansion (current) |
| v1.4 | JIT hints, TCO, async/await syntax |
| v1.5 | Generics, algebraic data types |
| v2.0 | Self-hosted compiler |

## Philosophy

> *"Black then white are all I see, in my infancy.
> Red and yellow then came to be, reaching out to me.
> Lets me see."*

LATERALUS is built on the idea that programming should spiral outward — from simple ideas to profound compositions. Every feature flows naturally into the next. There are no dead ends, only paths that haven't been explored yet.

## License

See LICENSE file.

---

*LATERALUS v1.3.0 — Spiraling Outward*  
*Created and maintained by bad-antics*
