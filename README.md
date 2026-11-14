# Lateralus Programming Language

> **Fast, safe systems programming with pipelines built in.**

> **Lateralus is a pipeline-native programming language for building fast, expressive systems software without giving up modern type safety, concurrency, or portable code generation.**

> **🌐 Official home [lateralus.dev](https://lateralus.dev)** — documentation, playground, downloads, papers, and package registry.

<p align="center">
  <a href="https://lateralus.dev"><strong>Website</strong></a> •
  <a href="https://lateralus.dev/docs/"><strong>Docs</strong></a> •
  <a href="https://lateralus.dev/playground/"><strong>Playground</strong></a> •
  <a href="https://lateralus.dev/download/"><strong>Download</strong></a> •
  <a href="https://lateralus.dev/papers/"><strong>Papers</strong></a> •
  <a href="https://lateralus.dev/blog/"><strong>Blog</strong></a>
</p>

[![Status](https://img.shields.io/badge/status-active-success.svg)](https://github.com/bad-antics/lateralus-lang)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.2.1-orange.svg)](https://lateralus.dev)
[![Backends](https://img.shields.io/badge/backends-Native%20%7C%20C99%20%7C%20WASM%20%7C%20JS%20%7C%20Python-purple.svg)](https://lateralus.dev/docs)

**[⭐ Star](https://github.com/bad-antics/lateralus-lang)** • **[🍴 Fork](https://github.com/bad-antics/lateralus-lang/fork)** • **[🐛 Issues](https://github.com/bad-antics/lateralus-lang/issues)** • **[🤝 Pull Requests](https://github.com/bad-antics/lateralus-lang/pulls)**

---

## Table of Contents

* [Elevator Pitch](#elevator-pitch)
* [Overview](#overview)
* [Project Status](#project-status)
* [One Language. Three Lanes.](#one-language-three-lanes)
* [Speed Snapshot](#speed-snapshot)
* [Features](#features)
* [Installation](#installation)

  * [Installation Decision Guide](#installation-decision-guide)
  * [Supported Release Platforms](#supported-release-platforms)
  * [Installation Methods](#installation-methods)
* [Quick Start](#quick-start)
* [Language Example](#language-example)
* [Project Structure](#project-structure)
* [Standard Library Highlights](#standard-library-highlights)
* [Backends](#backends)
* [Building From Source](#building-from-source)
* [Maintainer Troubleshooting](#maintainer-troubleshooting)
* [Documentation](#documentation)
* [Contributing](#contributing)
* [Citation](#citation)
* [License](#license)

---

## Elevator Pitch

**Lateralus makes data flow the natural shape of systems code.**

Traditional systems languages are excellent at control flow and low-level performance, but higher-level data transformations can become buried beneath iterator chains, helper functions, framework code, or glue between multiple languages.

Lateralus puts the transformation itself at the center.

```lateralus
input
    |> parse()
    |> validate()
    |> transform()
    |> filter()
    |> emit()
```

The language combines

* **Pipeline-native syntax** for readable left-to-right data flow
* **Static typing and inference** for compile-time feedback
* **Pattern matching and algebraic data types** for explicit state handling
* **Async/await and structured concurrency** for concurrent systems
* **Multiple compilation targets** for native and portable deployment
* **A standard library aimed at real systems workloads**
* **Compiler, VM, LSP, editor tooling, and OS research in one ecosystem**

The goal is simple

> **Write systems software in one language, express transformations directly, and keep the path from source code to deployable software short.**

---

## Overview

Lateralus is a systems programming language built around performance, safety, and expressive pipelines.

The repository contains the language implementation, compiler infrastructure, runtime components, standard library, tooling, tests, benchmarks, editor integration, and LateralusOS research.

Lateralus is designed for

* High-performance systems programming
* Data pipelines and transformation-heavy applications
* Observability and infrastructure tooling
* Networking
* Cryptography
* Native applications
* WebAssembly applications
* Language and compiler research
* Operating-system experimentation
* Cross-platform development

---

## Project Status

**Current Version** `3.2.1`

**Development Status** Active development

The project is actively evolving across the compiler, standard library, tooling, backends, and operating-system work. Treat unreleased features and development builds as experimental.

| Area                | Status          |
| ------------------- | --------------- |
| Core language       | 🟢 Active       |
| Compiler            | 🟢 Active       |
| VM                  | 🟢 Active       |
| Native backend      | 🟢 Active       |
| C99 backend         | 🟢 Active       |
| WebAssembly backend | 🟢 Active       |
| JavaScript backend  | 🟢 Active       |
| Python backend      | 🟢 Active       |
| Standard library    | 🟢 Active       |
| Test suite          | 🟢 Active       |
| LSP                 | 🟢 Active       |
| VS Code integration | 🟢 Active       |
| Playground          | 🟢 Active       |
| Package tooling     | 🟢 Active       |
| LateralusOS         | 🟡 Experimental |
| Documentation       | 🟢 Active       |

### Release Stability

* **Tagged releases** are the preferred choice for reproducible deployments
* **Development builds** may contain incomplete or experimental functionality
* **Source builds** track the current repository state
* **Container tags** should be pinned when reproducibility matters
* **Platform support** depends on the release artifacts published for that version

For production use, prefer a versioned release instead of a development checkout or floating `latest` image.

---

## One Language. Three Lanes.

Lateralus is designed for workloads that often end up split between several languages.

### 🔭 Observability

Structured logs, metrics, traces, and infrastructure tooling can live in the same native application instead of requiring a separate scripting layer.

### 📊 Analytics

Pipeline-oriented processing, columnar data workflows, Parquet, Arrow IPC, and SIMD-friendly operations fit naturally into the language's data-flow model.

### 🔐 Secure by Default

Security-oriented functionality includes primitives and APIs for modern cryptography, networking, hashing, authentication, and secure systems development.

➡ **[Niche page](https://lateralus.dev/niche/)** • **[Stdlib comparison](https://lateralus.dev/compare/)** • **[Cheatsheet](CHEATSHEET.md)** • **[Development bounties](BOUNTIES.md)**

---

## Speed Snapshot

Pure Lateralus using the C99 backend compared with CPython 3.13.

| Benchmark    | Lateralus C | CPython 3.13 | Approx. Speedup |
| ------------ | ----------: | -----------: | --------------: |
| `fib(35)`    |     0.004 s |      0.240 s |            ~60× |
| `sieve(1e6)` |     0.020 s |      0.600 s |            ~30× |
| `mandelbrot` |     0.110 s |      3.300 s |            ~30× |
| `n-body 5k`  |     0.080 s |      3.200 s |            ~40× |

Lower is better.

See [`benchmarks/`](benchmarks/) for the benchmark suite and reproduction workflow.

> Benchmark numbers are workload- and environment-dependent. Use the repository benchmarks rather than treating the snapshot above as a universal performance claim.

---

## Features

* First-class pipeline operators
* Static typing and type inference
* Ownership and borrowing semantics
* Algebraic data types
* Exhaustive pattern matching
* Traits and generics
* Closures
* Async/await
* Structured concurrency
* Zero-cost abstractions
* Native compilation
* C99 code generation
* WebAssembly support
* JavaScript support
* Python reference/runtime support
* Bytecode and VM infrastructure
* Networking and HTTP
* Filesystem and stream I/O
* Cryptographic primitives
* Time and synchronization primitives
* Built-in testing infrastructure
* Language Server Protocol support
* VS Code integration
* Browser playground
* Package tooling
* Compiler and language research infrastructure

---

# Installation

## Installation Decision Guide

Choose the shortest path that matches your goal.

| Goal                            | Recommended Method     | Best For                       |
| ------------------------------- | ---------------------- | ------------------------------ |
| 🚀 **Try Lateralus locally**    | PyPI                   | Fastest general installation   |
| 🌐 **Try without installing**   | Playground             | Evaluation and experimentation |
| 🍎 **macOS development**        | Homebrew               | Native development workflow    |
| 🐧 **Linux development**        | Package or installer   | Native development             |
| 🪟 **Windows development**      | Native release or WSL2 | Windows users                  |
| 📦 **Containerized use**        | Docker / GHCR          | CI, isolation, reproducibility |
| 🌐 **Browser target**           | WebAssembly            | Web applications               |
| 🛠️ **Contribute to Lateralus** | Source build           | Compiler, stdlib, tooling work |
| 🔬 **Test unreleased changes**  | Source build           | Development and debugging      |
| 📚 **Editor integration**       | VS Code / Open VSX     | Language tooling               |

### Quick Choice

```text
Want to use Lateralus?
│
├── Just try it
│   ├── Browser ───────────────► Playground
│   └── Local machine ─────────► PyPI / Homebrew / Installer
│
├── Deploy it
│   ├── Container ──────────────► Docker / GHCR
│   └── Native binary ─────────► Release artifacts
│
├── Target the web ─────────────► WebAssembly
│
└── Work on Lateralus itself ──► Build from source
```

For production and CI, pin a release version rather than depending on a floating development build.

---

## Supported Release Platforms

| Platform                | Release Support   | Recommended Path                 |
| ----------------------- | ----------------- | -------------------------------- |
| **Linux x86_64**        | ✅ Supported       | Package, installer, or container |
| **Linux ARM64**         | ✅ Where published | Release artifact                 |
| **macOS x86_64**        | ✅ Where published | Homebrew or release artifact     |
| **macOS Apple Silicon** | ✅ Where published | Homebrew or release artifact     |
| **Windows x86_64**      | ✅ Supported       | Native release or WSL2           |
| **WebAssembly**         | ✅ Supported       | WASM distribution or playground  |
| **Other architectures** | ⚠️ Source build   | Build from source                |

> Release availability is artifact-dependent. Check the release assets for the exact version and platform you need.

---

## Installation Methods

| Method            | Command or Resource                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| **PyPI**          | `pip install lateralus-lang`                                                                                |
| **npm tooling**   | `npm install -g lateralus-cli lateralus-lsp`                                                                |
| **Homebrew**      | `brew tap bad-antics/lateralus && brew install lateralus-lang`                                              |
| **Docker / GHCR** | `docker run --rm -v "$PWD:/src" -w /src ghcr.io/bad-antics/lateralus-lang:latest`                           |
| **Installer**     | `curl -fsSL https://lateralus.dev/install.sh \| sh`                                                         |
| **VS Code**       | [Lateralus VS Code extension](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang) |
| **Open VSX**      | [Lateralus Open VSX extension](https://open-vsx.org/extension/lateralus/lateralus-lang)                     |
| **Bootable ISO**  | [Release artifacts](https://github.com/bad-antics/lateralus-lang/releases)                                  |

Distribution manifests for additional package systems live in [`packaging/`](packaging/).

---

## Quick Start

### Install

```bash
pip install lateralus-lang
```

### Verify

```bash
ltl --version
```

### Run an Example

```bash
ltl run examples/hello.ltl
```

### Try the Playground

Open the [Lateralus Playground](https://lateralus.dev/playground/) for a browser-based workflow.

### Run Tests

```bash
make test
```

---

## Language Example

```lateralus
fn main() {
    let names = ["Alice", "Bob", "Carol"]

    names
        |> filter(|n| n.len() > 3)
        |> map(|n| format!("Hello, {}!", n))
        |> for_each(|msg| print(msg))
}
```

The pipeline makes the transformation order explicit

```text
names
  → filter
  → map
  → for_each
```

---

## Project Structure

```text
lateralus-lang/
├── lateralus_lang/         # Python compiler, engines, tooling, and runtime
├── lateralus_lang/codegen/ # Code generators and compilation targets
├── lateralus_lang/vm/      # VM, assembler, and disassembler
├── std/                    # Core standard library
├── stdlib/                 # Extended Lateralus standard library
├── bootstrap/              # Self-hosting compiler components
├── examples/               # Example programs
├── tests/                  # Test suites
├── benchmarks/             # Benchmark workloads
├── scripts/                # Build, release, health, and maintenance scripts
├── docs/                   # Specifications, tutorials, papers, and website
├── packaging/              # Distribution manifests
├── vscode-lateralus/       # VS Code extension
├── editor/vscode/          # Editor integration
├── lateralus-os/           # Bare-metal OS research
├── tools/                  # Development and release tooling
├── Makefile                # Canonical development task interface
├── CHANGELOG.md            # Release history
├── ROADMAP.md              # Roadmap
├── CONTRIBUTING.md         # Contribution guide
├── SECURITY.md             # Security policy
├── CITATION.cff            # Citation metadata
└── LICENSE                 # MIT license
```

---

## Standard Library Highlights

### Collections

HashMap, BTreeMap, Vec, LinkedList, BinaryHeap, Trie, SkipList, LRU Cache, BloomFilter

### Concurrency

Threads, async executors, channels, mutexes, rwlocks, barriers, semaphores, and structured concurrency

### Networking

TCP/UDP sockets, HTTP client/server, WebSocket, DNS, and firewall functionality

### Cryptography

AES, ChaCha20-Poly1305, SHA-256, SHA-3, BLAKE3, RSA, ECDSA, X25519, TLS, Noise Protocol, and Argon2id

### I/O

Buffered readers and writers, filesystem APIs, path manipulation, file watching, and stream I/O

### Formatting

Display and Debug traits, padding, alignment, numeric bases, and structured formatting

### Time

Duration, Instant, Stopwatch, and Deadline

---

## Backends

| Backend           | Primary Use                                   |
| ----------------- | --------------------------------------------- |
| **Native**        | High-performance systems and applications     |
| **C99**           | Portable native compilation                   |
| **WebAssembly**   | Browser and WASM environments                 |
| **JavaScript**    | JavaScript-oriented environments              |
| **Python**        | Reference implementation and interoperability |
| **VM / Bytecode** | Runtime and language experimentation          |

---

## Building From Source

The repository root provides the canonical development interface through `Makefile`.

### Clone

```bash
git clone https://github.com/bad-antics/lateralus-lang.git
cd lateralus-lang
```

### Create a Development Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Verify

```bash
make version
```

### Run the Main Test Suite

```bash
make test
```

### Run the Full Engine Suite

```bash
make test-all
```

### Run Health Checks

```bash
make health
```

### Check Examples

```bash
make check
```

### Lint

```bash
make lint
```

### Format

```bash
make format
```

### Run Benchmarks

```bash
make bench
```

### Build Documentation

```bash
make docs
```

### Development Cycle

```bash
git pull
make test
make lint
make check
make health
```

The root `Makefile` exposes dedicated targets for testing, engine suites, C backend tests, linting, formatting, examples, benchmarks, health checks, documentation, packaging, and release workflows.

---

# Maintainer Troubleshooting

This section is intended for maintainers and contributors working from a source checkout.

## Start With a Health Check

Before debugging a complicated failure, run

```bash
make health
```

Then run the normal test suite

```bash
make test
```

The repository's health target invokes `scripts/health_check.py`, while the primary test target runs the repository's pytest suite.

---

## Environment Problems

### Check Python

```bash
python3 --version
python3 -m pip --version
```

Lateralus development tooling expects a modern Python environment. The contributor documentation currently specifies Python 3.10+ for development.

### Recreate the Virtual Environment

If imports or installed entry points behave unexpectedly

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Then verify

```bash
python -m lateralus_lang --version
```

---

## Stale Build or Cache State

If behavior does not match the current checkout, clean generated state

```bash
make clean
```

Then reinstall the development package

```bash
pip install -e ".[dev]"
```

Then rerun

```bash
make health
make test
```

The repository clean target removes Python caches, generated Lateralus compiler artifacts, pytest cache, build output, distribution output, package metadata, and benchmark output.

---

## Test Failures

### Run the Failing Test Directly

Instead of rerunning the entire suite

```bash
pytest tests/path/to/test_file.py -v --tb=short
```

### Run a Specific Test

```bash
pytest tests/path/to/test_file.py::test_name -v
```

### Run Core Tests

```bash
make test-core
```

### Run Engine Tests

```bash
make test-engines
```

### Run C Backend Tests

```bash
make test-c-backend
```

The Makefile provides separate targets for core, engine, tooling, science, math, type-system, and C backend testing.

---

## Compiler or Language Regression

When a compiler change breaks behavior, isolate the layer first

```text
Source
  ↓
Parser
  ↓
AST / semantic analysis
  ↓
Type system
  ↓
Compiler / code generation
  ↓
VM or target backend
  ↓
Runtime / output
```

Useful first checks

```bash
make test-core
make test-types
make test-c-backend
make test-engines
```

If only one backend fails while another succeeds, avoid changing shared language semantics until the backend-specific behavior has been isolated.

---

## Standard Library Failures

For a standard-library change

1. Reproduce the smallest failing program
2. Determine whether the failure is in the library or language runtime
3. Add or update a focused test
4. Run the relevant test suite
5. Run the full suite before merging

For a new built-in function, the contributor workflow calls for implementation, registration in the appropriate built-in table, tests, and language documentation.

---

## Linter or Formatter Problems

Run

```bash
make lint
```

and

```bash
make format
```

For Lateralus examples

```bash
make check
```

The canonical Makefile routes linting through the Lateralus linter and example checking through the language checker.

---

## Backend-Specific Problems

When debugging a backend regression, compare the same source program across targets.

```text
Same source
   ├── VM
   ├── C99
   ├── JavaScript
   ├── WebAssembly
   └── Python
```

If only one target diverges

* Preserve the source program as the minimal reproduction
* Capture the generated representation where applicable
* Compare runtime output
* Identify whether the problem is code generation or runtime behavior
* Add a backend-specific regression test

Avoid masking backend failures by weakening shared language tests.

---

## Documentation Build Failures

Run

```bash
make docs
```

If documentation generation fails

1. Identify the first failing `.ltlml` file
2. Validate the source markup
3. Check recent compiler or markup changes
4. Re-run the documentation target
5. Confirm generated output is not accidentally committed unless the repository expects it

The repository's documentation target compiles `.ltlml` files through the Lateralus markup tooling.

---

## VS Code Extension Problems

For a local development installation

```bash
make vscode-install
```

For a development symlink

```bash
make vscode-link
```

After changing the extension, reload VS Code.

To remove the local installation

```bash
make vscode-uninstall
```

These workflows are provided directly by the repository Makefile.

---

## Benchmark Regressions

Run the standard benchmark suite

```bash
make bench
```

For broader coverage

```bash
make bench-all
```

For machine-readable results

```bash
make bench-json
```

Do not treat a single noisy run as a regression. Compare repeated runs under the same environment and compiler configuration.

---

## Release Problems

Before preparing a release, run

```bash
make health
make test
make lint
make check
make docs
```

For a dry run

```bash
make release-dry-run
```

For the release workflow

```bash
make release
```

The repository exposes both release and dry-run targets through `scripts/release.sh`.

### Release Checklist

* [ ] Working tree is clean
* [ ] Version metadata is synchronized
* [ ] Tests pass
* [ ] Health check passes
* [ ] Lint passes
* [ ] Examples pass
* [ ] Documentation builds
* [ ] Benchmarks are reviewed where relevant
* [ ] Changelog is updated
* [ ] Release notes are reviewed
* [ ] Package artifacts are reproducible
* [ ] Release assets match supported platforms
* [ ] Versioned container/image references are updated
* [ ] Documentation points to the intended release
* [ ] Tag and release metadata are correct

---

## Dependency or Packaging Problems

If installation behaves differently from the source checkout, compare

```bash
python3 --version
python3 -m pip --version
python3 -m pip show lateralus-lang
python3 -m lateralus_lang --version
git rev-parse HEAD
git status --short
```

For local development, prefer the editable installation

```bash
pip install -e ".[dev]"
```

This avoids accidentally debugging an older globally installed copy of the project.

---

## Reproducibility Checklist

When reporting a maintainer-level failure, capture

```bash
git rev-parse HEAD
git status --short
python3 --version
python3 -m pip --version
uname -a
```

Then include

* Exact command executed
* Complete error output
* Minimal reproduction
* Expected behavior
* Actual behavior
* Whether the issue reproduces from a clean checkout
* Whether `make health` passes
* Whether the issue affects one backend or multiple backends

This matches the project's contributor guidance to include version, Python version, operating system, minimal reproduction, expected versus actual behavior, and full error output when reporting bugs.

---

## When to Stop Debugging and File an Issue

File an issue when

* The failure reproduces from a clean checkout
* The behavior is not explained by an existing documented limitation
* You have a minimal reproduction
* You have captured the environment and commit
* The failure persists after `make health` and the relevant focused tests

Do not hide reproducible failures behind local workarounds without documenting the underlying issue.

---

## Documentation

### Online

* [Website](https://lateralus.dev)
* [Documentation](https://lateralus.dev/docs/)
* [Playground](https://lateralus.dev/playground/)
* [Downloads](https://lateralus.dev/download/)
* [Papers](https://lateralus.dev/papers/)
* [Blog](https://lateralus.dev/blog/)
* [Comparison](https://lateralus.dev/compare/)
* [Niche](https://lateralus.dev/niche/)

### Repository

* [Language Specification](docs/language-spec.ltlml)
* [Tutorial](docs/tutorial.ltlml)
* [Cookbook](docs/cookbook.ltlml)
* [Grammar](docs/grammar.ebnf)
* [Architecture](docs/architecture.ltlml)
* [Blog](docs/blog/)
* [Cheatsheet](CHEATSHEET.md)
* [Bounties](BOUNTIES.md)
* [Changelog](CHANGELOG.md)
* [Roadmap](ROADMAP.md)
* [Contributing](CONTRIBUTING.md)
* [Security Policy](SECURITY.md)

---

## Contributing

1. ⭐ Star the repository
2. 🍴 Fork the repository
3. 📖 Read the documentation
4. 🔨 Build the project
5. 🧪 Run the relevant tests
6. 🧹 Run linting and formatting
7. 🩺 Run the health check
8. 🐛 Report reproducible bugs
9. 🤝 Submit focused pull requests

### Development Commands

```bash
make test
make test-all
make lint
make format
make check
make health
make bench
make docs
```

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md) for the complete contributor workflow. The repository's contributor guide also recommends conventional commit prefixes such as `feat`, `fix`, `docs`, `test`, `refactor`, and `perf`.

---

## Citation

If you use Lateralus in research, teaching, or production, please cite it.

GitHub uses [`CITATION.cff`](CITATION.cff) for repository citation metadata, while tagged releases are archived through Zenodo.

```bibtex
@software{lateralus_lang_2026,
  author    = {{bad-antics}},
  title     = {Lateralus: A Pipeline-Native Programming Language},
  year      = {2026},
  version   = {3.2.1},
  url       = {https://lateralus.dev},
  publisher = {Zenodo},
  note      = {Per-release DOIs minted via Zenodo GitHub integration}
}
```

For reproducible research, cite the specific release or DOI associated with the version used.

---

## License

MIT — see [`LICENSE`](LICENSE) for details.

---

<p align="center">
  <sub>Made with care at <a href="https://lateralus.dev">lateralus.dev</a></sub>
</p>
