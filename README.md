# Lateralus Programming Language

> **🌐 Official home: [lateralus.dev](https://lateralus.dev)** — docs, playground, downloads, papers, and package registry.

<p align="center">
  <a href="https://lateralus.dev"><strong>Website</strong></a> •
  <a href="https://lateralus.dev/docs/"><strong>Docs</strong></a> •
  <a href="https://lateralus.dev/playground/"><strong>Playground</strong></a> •
  <a href="https://lateralus.dev/download/"><strong>Download</strong></a> •
  <a href="https://lateralus.dev/papers/"><strong>Papers</strong></a> •
  <a href="https://lateralus.dev/blog/"><strong>Blog</strong></a>
</p>

## Install

| Platform / registry | Command |
|---|---|
| **PyPI** (canonical) | `pip install lateralus-lang` |
| **npm** (Node shim)  | `npm install -g lateralus-cli lateralus-lsp` |
| **Homebrew** (macOS / Linuxbrew) | `brew tap bad-antics/lateralus && brew install lateralus-lang` |
| **Docker / GHCR**    | `docker run --rm -v "$PWD:/src" -w /src ghcr.io/bad-antics/lateralus-lang:latest` |
| **One-liner**        | `curl -fsSL https://lateralus.dev/install.sh \| sh` |
| **VS Code**          | [marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang) |
| **Open VSX** (VSCodium / Cursor) | [open-vsx.org/extension/lateralus/lateralus-lang](https://open-vsx.org/extension/lateralus/lateralus-lang) |
| **Bootable ISO**     | [GitHub release v3.2.0](https://github.com/bad-antics/lateralus-lang/releases/tag/v3.2.0) → `lateralus-os.iso` |

Distro packaging manifests (Arch AUR, Snap, Flatpak) live in [packaging/](packaging/README.md).

---

## One language. Three lanes.

Lateralus is built for the jobs that usually need three languages:

1. **Observability** — structured logs, metrics, traces, in one binary.
2. **Analytics** — Parquet, Arrow IPC, SIMD-ready columnar ops shipped in the stdlib.
3. **Secure-by-default** — ChaCha20-Poly1305, X25519, BLAKE3, Argon2id — no OpenSSL, no surprises.

➡ **[Niche page](https://lateralus.dev/niche/)** · **[Stdlib vs Python/Go/Rust/Node](https://lateralus.dev/compare/)** · **[One-page cheatsheet](CHEATSHEET.md)** · **[Open bounties →](BOUNTIES.md)**

### Speed snapshot

Pure Lateralus → C99 backend vs CPython 3.13 (lower is better):

| Benchmark   | Lateralus (C) | CPython 3.13 | Speedup |
|-------------|---------------|--------------|---------|
| fib(35)     | 0.004 s       | 0.240 s      | ~60×    |
| sieve(1e6)  | 0.020 s       | 0.600 s      | ~30×    |
| mandelbrot  | 0.110 s       | 3.300 s      | ~30×    |
| n-body 5k   | 0.080 s       | 3.200 s      | ~40×    |

See [`benchmarks/`](benchmarks/) to reproduce.

---

Lateralus is a systems programming language built for performance, safety, and expressive pipelines. It combines Rust-inspired ownership semantics with first-class pipeline operators, pattern matching, and a rich standard library.

## Features

- Ownership and borrowing with compile-time lifetime checks
- First-class pipeline operators for data transformation
- Algebraic types with exhaustive pattern matching
- Async/await with structured concurrency
- Traits and generics with monomorphization
- Zero-cost abstractions compiling to native code
- Built-in test runner with assertion support
- Multiple backends: native, C, WASM, JavaScript, Python

## Quick Start

```
ltl run examples/hello.ltl
```

Write your first program:

```lateralus
fn main() {
    let names = ["Alice", "Bob", "Carol"]
    names
        |> filter(|n| n.len() > 3)
        |> map(|n| format!("Hello, {}!", n))
        |> for_each(|msg| print(msg))
}
```

## Project Structure

- std/ — Standard library modules (collections, io, sync, crypto, etc.)
- stdlib/ — Extended standard library
- examples/ — Example programs and showcases
- bootstrap/ — Self-hosting compiler components
- lateralus_lang/ — Python reference implementation
- lateralus-os/ — Experimental operating system
- vscode-lateralus/ — VS Code extension with syntax highlighting
- docs/ — Language specification, tutorials, and papers
- tests/ — Test suite

## Standard Library Highlights

Collections: HashMap, BTreeMap, Vec, LinkedList, BinaryHeap, Trie, SkipList, LRU Cache, BloomFilter

Concurrency: threads, async executors, channels, mutexes, rwlocks, barriers, semaphores

Networking: TCP/UDP sockets, HTTP client/server, WebSocket, DNS, firewall

Cryptography: AES, ChaCha20, SHA-256, SHA-3, BLAKE3, RSA, ECDSA, X25519, TLS, Noise Protocol

IO: buffered readers/writers, file system, path manipulation, file watching

Formatting: Display/Debug traits, padding, alignment, numeric bases

Time: Duration, Instant, Stopwatch, Deadline

## Building from Source

```
git clone https://github.com/bad-antics/lateralus-lang.git
cd lateralus-lang
make build
make test
```

## Documentation

- Language Spec: docs/language-spec.ltlml
- Tutorial: docs/tutorial.ltlml
- Cookbook: docs/cookbook.ltlml
- Grammar: docs/grammar.ebnf
- Blog: docs/blog/

## License

MIT — see LICENSE for details.

---

<p align="center">
  <sub>Made with care at <a href="https://lateralus.dev">lateralus.dev</a></sub>
</p>
