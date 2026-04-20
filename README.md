# Lateralus Programming Language

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