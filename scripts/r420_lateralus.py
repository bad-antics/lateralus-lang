#!/usr/bin/env python3
"""
r420_lateralus.py — Continuous Lateralus language file generator

Runs forever, asking Ollama to produce .ltl source files and .ltlml
docs/blog posts/papers in bad-antics style.  Writes into:

  output/lateralus/examples/   — runnable .ltl example programs
  output/lateralus/stdlib/     — stdlib module .ltl files
  output/lateralus/docs/blog/  — .ltlml blog posts
  output/lateralus/docs/papers/— .ltlml research papers

Pure stdlib — zero pip deps.
"""

import json
import os
import random
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_URL   = os.getenv("OLLAMA_URL",    "http://localhost:11434")
MODEL        = os.getenv("R420_MODEL",    "hailmary-precise:latest")
OUTPUT_DIR   = Path(os.getenv("R420_OUTPUT", str(Path(__file__).parent / "output")))
GEN_INTERVAL = int(os.getenv("LTL_INTERVAL", "120"))   # seconds between generations
GEN_TIMEOUT  = int(os.getenv("LTL_TIMEOUT",  "180"))   # max seconds per Ollama call
MAX_FILES    = int(os.getenv("MAX_FILES",     "1000"))

LATERALUS_DIR = OUTPUT_DIR / "lateralus"

# ── Lateralus syntax primer (injected into every system prompt) ───────────────

LTL_SYNTAX_PRIMER = """
You are writing code in the Lateralus programming language (.ltl files).
Lateralus syntax rules — follow these EXACTLY:

IMPORTS:        import math / import strings / import crypto / import io
FUNCTIONS:      fn name(arg: type, arg2: type) -> return_type { ... }
ASYNC FNS:      async fn name(arg: type) -> type { ... }
VARIABLES:      let x = value   /   let x: int = 0
TYPES:          int  float  str  bool  list  map  none
RETURN:         return expr
IF/ELSE:        if cond { } else if cond { } else { }
WHILE:          while cond { }
FOR:            for item in collection { }
RANGE:          range(0, n)  /  range(n)
PIPELINE:       value |> fn()  |> fn2()     (left-to-right composition)
NULL-PIPE:      value |? fn()               (short-circuit on none)
LAMBDAS:        fn(x) { x * 2 }   or   fn(x) x * 2
MAP/FILTER:     list |> map(fn(x) { ... }) |> filter(fn(x) { ... })
STRING FMT:     "Hello {name}!"   (curly-brace interpolation)
LISTS:          [1, 2, 3]   list + [item]   slice(list, from, to)
MAPS:           {}   m["key"] = val   keys(m)   contains(keys(m), k)
MATCH:          match expr { pattern => expr, _ => expr }
STRUCTS:        struct Name { field: type }
DECORATORS:     @memo  @test  @deprecated("msg")
ERRORS:         Result type — Ok(val) / Err(msg) — or let r = try_op() catch e { }
YIELD:          fn gen() { while true { yield value } }
SPAWN:          let handle = spawn task_fn(args)
GENERICS:       fn name<T>(x: T) -> T { }
BUILTINS:       len()  str()  int()  float()  push()  pop()  sort()  reverse()
                min()  max()  abs()  sqrt()  floor()  ceil()  round()
                contains()  keys()  values()  split()  join()  trim()
                sha256()  hmac_sign()  to_base64()  from_base64()
                println()  print()  io.println()

COMMENT STYLE:
  Section header: // ─── Section Name ────────────────────────────────────────
  File header:    // ═══════════════════════════════════════════════════════════
                  // LATERALUS — Title
                  // Description line
                  // ═══════════════════════════════════════════════════════════
  Inline:         // comment

OUTPUT FORMAT — return ONLY the raw .ltl file contents.
No markdown fences. No explanation. Just the code file.
"""

LTLML_SYNTAX_PRIMER = """
You are writing a .ltlml document for the Lateralus language website.

FORMAT: The file is a full HTML document. Follow this structure EXACTLY:

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TITLE HERE</title>
  <link rel="stylesheet" href="../ltlml.css">
</head>
<body>
  <nav class="ltlml-nav">
    <span class="nav-brand">LATERALUS</span>
    <a href="../index.ltlml">Home</a>
    <a href="../tutorial.ltlml">Tutorial</a>
    <a href="../cookbook.ltlml">Cookbook</a>
    <a href="../language-spec.ltlml">Spec</a>
    <a href="../quick-reference.ltlml">Quick Ref</a>
    <a href="../architecture.ltlml">Architecture</a>
  </nav>
  <div id="ltlml-render" class="ltlml-document"></div>
  <script id="ltlml-source" type="text/ltlml">
---
title: "TITLE"
author: bad-antics
date: DATE
abstract: ONE SENTENCE ABSTRACT
---

# Main Title

## Section 1

Body text here. Be direct and technical. First-person plural voice ("we", "our").
Short paragraphs. No fluff.

```lateralus
// code examples go here in fenced blocks
fn example(x: int) -> int {
    return x * 2
}
```

Inline code uses `backticks`.

## Section 2

More content.

  </script>
</body>
</html>

WRITING STYLE:
- Author: bad-antics (lowercase)
- Voice: direct, technical, first-person plural, slightly opinionated
- Short punchy paragraphs
- Real code examples in ```lateralus fenced blocks
- No marketing language — be honest about tradeoffs
- Lateralus syntax for ALL code examples (not Python/JS/etc)

OUTPUT FORMAT — return ONLY the raw .ltlml file. No explanation. No markdown wrapper.
"""

# ── Generation topics ──────────────────────────────────────────────────────────

EXAMPLE_TOPICS = [
    # data structures
    ("linked_list",       "Implement a singly linked list with push, pop, insert, delete, and reverse operations"),
    ("doubly_linked_list","Implement a doubly linked list with bidirectional traversal and O(1) head/tail operations"),
    ("binary_search_tree","Implement a BST with insert, search, delete, in-order traversal, and height calculation"),
    ("avl_tree",          "Implement a self-balancing AVL tree with rotations, insert, delete, and balance factor tracking"),
    ("trie",              "Implement a trie (prefix tree) for string storage, autocomplete, and prefix counting"),
    ("bloom_filter",      "Implement a probabilistic Bloom filter with configurable hash count and false-positive rate"),
    ("lru_cache",         "Implement an LRU cache using a doubly linked list + hash map with configurable capacity"),
    ("ring_buffer",       "Implement a fixed-size ring buffer with overflow detection and producer/consumer semantics"),
    ("skip_list",         "Implement a probabilistic skip list with O(log n) search, insert, and delete"),
    ("union_find",        "Implement a union-find (disjoint set) with path compression and union by rank"),
    # algorithms
    ("sorting_suite",     "Implement quicksort, mergesort, heapsort, and timsort with benchmarking harness"),
    ("string_search",     "Implement KMP, Boyer-Moore, and Rabin-Karp string search algorithms with comparison"),
    ("compression_rle",   "Implement run-length encoding and decoding with binary and text mode support"),
    ("huffman_coding",    "Implement Huffman coding for lossless text compression with encode/decode pipeline"),
    ("matrix_ops",        "Implement matrix multiplication, transpose, determinant, LU decomposition, and eigenvalue estimation"),
    ("fft_demo",          "Implement a Cooley-Tukey FFT with power spectrum, windowing, and frequency peak detection"),
    # network / mesh / radio
    ("mesh_router",       "Implement an AODV-inspired mesh routing protocol with route discovery, maintenance, and RREQ/RREP/RERR packet types"),
    ("packet_codec",      "Implement a binary packet codec for a LoRa mesh frame: frame delimiter, length, CRC16, payload encoding/decoding"),
    ("lora_simulator",    "Simulate LoRa radio channel with path loss, spreading factor, bandwidth, SNR, and link budget calculation"),
    ("mesh_flood",        "Implement controlled flooding in a mesh network with TTL, sequence numbers, and duplicate suppression"),
    ("reed_solomon_fec",  "Implement a simplified Reed-Solomon forward error correction encoder and decoder for noisy channels"),
    ("protocol_state_machine","Implement a connection state machine for a mesh node: INIT, HELLO, LINKED, ROUTING, TEARDOWN states"),
    # crypto / security
    ("chacha20",          "Implement ChaCha20 stream cipher quarter-round and full encryption/decryption in pure Lateralus"),
    ("poly1305",          "Implement Poly1305 MAC authentication with key clamping and tag verification"),
    ("key_exchange",      "Implement a simplified Diffie-Hellman key exchange simulation with modular exponentiation"),
    ("merkle_tree",       "Implement a Merkle tree for data integrity verification with proof generation and validation"),
    ("password_hash",     "Implement PBKDF2 key derivation simulation with salting, stretching, and constant-time comparison"),
    ("zero_knowledge_demo","Implement a simplified zero-knowledge proof demo (Schnorr identification protocol)"),
    # AI / inference
    ("perceptron",        "Implement a multi-layer perceptron with backpropagation from scratch, including train/predict pipeline"),
    ("k_means",           "Implement k-means clustering with Euclidean distance, centroid update, and convergence detection"),
    ("decision_tree",     "Implement a decision tree classifier with Gini impurity, recursive splitting, and pruning"),
    ("naive_bayes",       "Implement a Naive Bayes text classifier with Laplace smoothing and log-probability scoring"),
    ("gradient_descent",  "Implement stochastic and mini-batch gradient descent for linear and logistic regression"),
    # systems / monitoring
    ("process_monitor",   "Implement a process monitoring system that tracks CPU, memory, open file descriptors, and uptime"),
    ("rate_limiter",      "Implement token bucket and leaky bucket rate limiters with configurable burst and refill rates"),
    ("event_bus",         "Implement a pub/sub event bus with typed channels, async dispatch, and backpressure handling"),
    ("task_scheduler",    "Implement a cron-style task scheduler with interval, daily, weekly triggers and missed-run recovery"),
    ("circuit_breaker",   "Implement a circuit breaker with CLOSED, OPEN, HALF-OPEN states, failure threshold, and timeout"),

    # ── v2: data structures ──
    ("b_tree",            "Implement a B-tree of configurable order with insert, search, split, and in-order traversal"),
    ("red_black_tree",    "Implement a red-black tree with color-flip rotations, insert, delete, and validation of RB invariants"),
    ("segment_tree",      "Implement a segment tree for range sum, range min, range max queries with lazy propagation"),
    ("fenwick_tree",      "Implement a Fenwick (binary indexed) tree for prefix sums and point updates in O(log n)"),
    ("hash_table",        "Implement an open-addressing hash table with linear probing, Robin Hood hashing, resize, and load factor tracking"),
    ("priority_queue",    "Implement a min-heap priority queue with insert, extract_min, decrease_key, and heapify"),
    ("persistent_list",   "Implement an immutable persistent singly-linked list with structural sharing for functional programming"),
    ("graph_adjacency",   "Implement an adjacency-list graph with BFS, DFS, topological sort, and cycle detection"),
    ("sparse_matrix",     "Implement a sparse matrix using compressed row storage with add, multiply, and transpose"),
    # ── v2: algorithms ──
    ("dijkstra",          "Implement Dijkstra's shortest path algorithm on a weighted directed graph with priority queue"),
    ("a_star",            "Implement A* pathfinding on a 2D grid with Manhattan heuristic and path reconstruction"),
    ("bellman_ford",      "Implement Bellman-Ford shortest paths with negative edge detection and path reconstruction"),
    ("topological_sort",  "Implement Kahn's and DFS-based topological sorting with cycle detection for DAGs"),
    ("convex_hull",       "Implement Graham scan and Andrew's monotone chain for computing 2D convex hulls"),
    ("flood_fill",        "Implement iterative flood fill for a 2D grid with stack-based and scan-line variants"),
    ("knapsack",          "Implement 0/1 knapsack with dynamic programming, memoization, and item backtracking"),
    ("levenshtein",       "Implement Levenshtein edit distance with backtrace to produce the actual edit sequence"),
    ("minimax",           "Implement minimax with alpha-beta pruning for a simple tic-tac-toe game engine"),
    ("regex_engine",      "Implement a basic regex engine supporting ., *, +, ?, character classes, and alternation via NFA"),
    ("sudoku_solver",     "Implement a constraint-propagation + backtracking Sudoku solver with pretty-print"),
    ("genetic_algorithm", "Implement a genetic algorithm framework with selection, crossover, mutation, and fitness-proportionate selection"),
    # ── v2: network / systems ──
    ("dns_resolver",      "Implement a recursive DNS resolver that builds query packets, parses responses, and follows CNAME chains"),
    ("http_parser",       "Implement an HTTP/1.1 request and response parser with chunked transfer encoding support"),
    ("tcp_state_machine", "Implement the TCP state machine (SYN, SYN-ACK, ESTABLISHED, FIN-WAIT, etc.) with timeout transitions"),
    ("load_balancer",     "Implement round-robin, least-connections, and weighted load balancing algorithms for a server pool"),
    ("syslog_parser",     "Implement an RFC 5424 syslog message parser with structured data, severity, and facility extraction"),
    ("ping_tracer",       "Implement ICMP echo request/reply simulation with TTL decrement and traceroute-style hop tracking"),
    ("arp_cache",         "Implement an ARP cache with request/reply handling, timeout eviction, and gratuitous ARP detection"),
    # ── v2: crypto / security ──
    ("aes_sbox",          "Implement AES S-box and inverse S-box computation with the SubBytes, ShiftRows, and MixColumns steps"),
    ("hmac_impl",         "Implement HMAC from scratch using SHA-256 with inner/outer padding and constant-time comparison"),
    ("totp",              "Implement TOTP (RFC 6238) one-time password generation with HMAC-SHA1, time step, and validation window"),
    ("xor_cipher",        "Implement repeating-key XOR encryption with automatic key-length detection via Hamming distance"),
    ("certificate_chain", "Implement X.509-style certificate chain validation with issuer matching, expiry checks, and trust anchor"),
    ("srp_auth",          "Implement a simplified Secure Remote Password (SRP-6a) authentication handshake"),
    # ── v2: AI / ML ──
    ("linear_regression", "Implement ordinary least squares linear regression with gradient descent, R-squared, and residual plots"),
    ("random_forest",     "Implement a random forest classifier with bootstrap sampling, feature bagging, and majority voting"),
    ("word2vec",          "Implement a simplified Word2Vec skip-gram model with negative sampling and cosine similarity search"),
    ("markov_chain",      "Implement a Markov chain text generator with configurable n-gram order and sentence generation"),
    ("q_learning",        "Implement Q-learning for a grid-world agent with epsilon-greedy exploration and convergence tracking"),
    ("knn_classifier",    "Implement k-nearest neighbors classification with distance weighting, cross-validation, and confusion matrix"),
    # ── v2: games / simulations ──
    ("raycast_2d",        "Implement a 2D raycaster for a simple FPS-style renderer with wall height projection and texture mapping"),
    ("particle_system",   "Implement a particle system with emitters, forces (gravity, wind), lifetime, and fade-out rendering"),
    ("cellular_automata", "Implement 1D and 2D cellular automata (Rule 30, Rule 110, Wireworld) with step and render"),
    ("l_system",          "Implement L-system string rewriting with turtle graphics interpretation for fractal generation"),
    ("ecs_framework",     "Implement an entity-component-system framework with archetype storage, system scheduling, and queries"),
    ("chess_engine",      "Implement a chess move generator with legal move validation, check detection, and basic evaluation function"),
]

STDLIB_TOPICS = [
    ("arena",      "Memory arena allocator — bump pointer, reset, and pool allocation for temporary data"),
    ("retry",      "Retry logic with exponential backoff, jitter, max attempts, and configurable error predicates"),
    ("validation", "Input validation framework — schema, type coercion, range checks, regex, custom validators"),
    ("diff",       "Myers diff algorithm for computing edit distance and line-level diffs between two strings"),
    ("parsec",     "Parser combinator library — sequence, choice, many, optional, token, satisfy, label"),
    ("bitpack",    "Bit-level packing and unpacking for compact binary serialization of small integers"),
    ("interval",   "Interval arithmetic — interval addition, multiplication, containment, overlap, union, intersection"),
    ("statistics", "Descriptive statistics — mean, median, mode, variance, std dev, percentiles, IQR, z-score"),
    ("serialize",  "Binary serialization — encode/decode structs to byte arrays with versioned schema support"),
    ("pool",       "Object pooling — acquire, release, auto-expand, eviction policy, and pool health metrics"),

    ("bigint",     "Arbitrary-precision integer arithmetic — add, sub, mul, div, mod, pow, comparison, string conversion"),
    ("rope",       "Rope data structure for efficient large string manipulation — concat, split, insert, delete, rebalance"),
    ("glob",       "Glob pattern matching — *, ?, **, character classes, brace expansion, case-insensitive mode"),
    ("promise",    "Promise/future abstraction — resolve, reject, then, catch, all, race, timeout, cancellation"),
    ("graph",      "Graph data structure — adjacency list, BFS, DFS, shortest path, MST, connected components"),
    ("crc",        "CRC computation — CRC-8, CRC-16, CRC-32 with configurable polynomials, lookup table generation"),
    ("rational",   "Rational number arithmetic — add, sub, mul, div, simplify, to_float, from_float, comparison"),
    ("geom",       "2D geometry — Point, Line, Circle, Polygon, intersection, distance, area, convex hull"),
    ("fsm",        "Finite state machine — states, transitions, guards, actions, event dispatch, serialization"),
    ("compress",   "Compression utilities — RLE, LZ77, Huffman, deflate-lite for small payloads"),
    ("bencode",    "Bencoding encoder/decoder for BitTorrent-style data — strings, ints, lists, dicts"),
    ("calendar",   "Calendar utilities — day-of-week, leap year, date arithmetic, ISO week number, month name"),
    ("matrix",     "Dense matrix operations — add, mul, transpose, inverse, determinant, eigenvalues, LU decomposition"),
    ("units",      "Physical unit conversion — length, mass, temperature, time, volume, with compile-time dimension checking"),
    ("mime",       "MIME type detection — file extension mapping, magic bytes sniffing, content-type header generation"),
]

BLOG_TOPICS = [
    ("pipelines-are-not-sugar",
     "Why the |> pipeline operator in Lateralus is a first-class design choice, not syntactic sugar. "
     "Contrast with method chaining, monads, and Unix pipes. Show real examples where it changes how you think about code."),
    ("error-handling-without-exceptions",
     "How Lateralus treats errors as structured data using Result types and error codes E1001-E7004. "
     "Why exceptions are the wrong model for systems code. Real examples of error chains and context propagation."),
    ("type-system-v15",
     "Deep dive into the Lateralus v1.5 gradual type system — inference, refinement types, and the any escape hatch. "
     "When to annotate and when to let inference do the work."),
    ("writing-a-mesh-protocol-in-ltl",
     "Building a LoRa mesh routing protocol entirely in Lateralus. "
     "Cover packet framing, AODV route discovery, and why Lateralus's binary primitives make this cleaner than Python."),
    ("self-modifying-pipelines",
     "Using higher-order pipelines in Lateralus — pipelines that transform other pipelines, "
     "lazy evaluation chains, and memoized computation graphs."),
    ("lateralus-for-ctf",
     "Using Lateralus for CTF challenges and security research. "
     "Built-in crypto, XOR pipelines, binary parsing, and why no-dependency tooling matters in competition environments."),
    ("async-without-callbacks",
     "How Lateralus's async/await + spawn model eliminates callback hell. "
     "Compare to Python asyncio, JavaScript Promises, and Go goroutines with concrete examples."),
    ("stdlib-design-philosophy",
     "Why the Lateralus stdlib is small and opinionated. "
     "Covering what's in core vs optional modules, the no-ecosystem-lock-in stance, and stdlib design tradeoffs."),
    ("polyglot-bridge-deep-dive",
     "The Lateralus foreign block system — calling Python, Julia, and R code with zero serialization overhead. "
     "When to use it, when not to, and how the ABI bridge works."),
    ("building-lateralusos",
     "Progress report on LateralusOS — an operating system whose userspace is written in Lateralus. "
     "Kernel interface, init system, and what it means to dog-food your language at the OS layer."),

    ("match-expressions-deep-dive",
     "Pattern matching in Lateralus — exhaustiveness checking, nested destructuring, guard clauses, "
     "and how match compiles to efficient code. Compare with Rust match, Elixir case, and OCaml pattern matching."),
    ("from-python-to-lateralus",
     "A practical guide for Python developers learning Lateralus. "
     "Cover the familiar (for loops, functions) and the different (pipelines, Result types, structs vs classes)."),
    ("lateralus-concurrency-model",
     "How Lateralus handles concurrency with nurseries, channels, and spawn — "
     "and why we chose structured concurrency over goroutines and async/await."),
    ("the-c-backend-story",
     "Why Lateralus has a C transpiler backend and what it enables — "
     "embedded targets, LateralusOS, and performance-critical inner loops without leaving the language."),
    ("designing-the-vm",
     "Inside the Lateralus bytecode VM — stack architecture, opcode design, "
     "constant folding, and why we went with a register-less design."),
    ("macros-without-madness",
     "Lateralus procedural macros — quote, unquote, AST transformation, "
     "and why compile-time code generation doesn't have to be a footgun."),
    ("package-manager-from-scratch",
     "Building lateralus.toml — semver resolution, dependency graphs, cycle detection, "
     "and the design decisions behind the Lateralus package manager."),
    ("wasm-and-js-targets",
     "Compiling Lateralus to WebAssembly and JavaScript — "
     "what works, what doesn't, and how we handle the impedance mismatch."),
    ("ffi-bridge-patterns",
     "Patterns for calling C, Python, and Julia from Lateralus — "
     "load_library, FFIFunction, memory management, and when to use foreign blocks instead."),
    ("testing-a-language",
     "How we test Lateralus itself — 1,976 tests, snapshot testing, property-based testing, "
     "and the CI pipeline that keeps the compiler honest."),
    ("lateralus-on-bare-metal",
     "Running Lateralus programs on LateralusOS without any OS underneath — "
     "the syscall interface, memory model, and what it takes to go freestanding."),
    ("generators-and-lazy-eval",
     "Yield, generators, and lazy evaluation in Lateralus — "
     "how they work under the hood and when to reach for them over eager pipelines."),
]

PAPER_TOPICS = [
    ("mesh-protocol-formal-spec",
     "A formal specification of the NullSec LoRa mesh protocol implemented in Lateralus. "
     "Cover packet grammar in EBNF, state machine transitions, security properties, and performance model."),
    ("pipeline-calculus",
     "A formal treatment of the Lateralus pipeline operator as a category-theoretic composition. "
     "Define pipe semantics, associativity, identity, and derive optimization rules."),
    ("gradual-typing-lateralus",
     "A formal account of the Lateralus v1.5 gradual type system. "
     "Type inference algorithm, refinement predicates, blame tracking, and soundness argument."),
    ("lateralus-vs-elixir-pipes",
     "Empirical comparison of pipeline-oriented programming in Lateralus, Elixir, and F#. "
     "Expressiveness metrics, performance benchmarks, and readability study methodology."),
    ("zero-dependency-crypto-in-ltl",
     "Design and implementation of the Lateralus built-in cryptographic library. "
     "ChaCha20-Poly1305, BLAKE2b, HMAC, PBKDF2 — correctness proofs and side-channel considerations."),

    ("lateralus-vm-architecture",
     "Formal specification of the Lateralus bytecode VM — "
     "instruction encoding, stack semantics, operand types, and operational semantics."),
    ("structured-concurrency-semantics",
     "A formal treatment of Lateralus nurseries and cancellation tokens — "
     "causal ordering, failure propagation, and the relationship to trio's nursery model."),
    ("self-hosting-bootstrap",
     "Bootstrapping a self-hosting compiler — "
     "the chicken-and-egg problem, our 5-module bootstrap strategy, and verification methodology."),
    ("c-transpilation-correctness",
     "Proving semantic equivalence between Lateralus source and generated C code — "
     "type mapping, control flow translation, and memory safety guarantees."),
    ("error-dna-fingerprinting",
     "The Lateralus error DNA system — "
     "how we compute unique error fingerprints, the E-code taxonomy, and structured error propagation."),
]

# ── Prompt builders ────────────────────────────────────────────────────────────

def build_example_prompt(slug: str, description: str) -> tuple[str, str]:
    system = LTL_SYNTAX_PRIMER
    user = (
        f"Write a complete, well-commented Lateralus (.ltl) example file "
        f"with the filename '{slug}.ltl'.\n\n"
        f"Topic: {description}\n\n"
        f"Requirements:\n"
        f"- Start with the box-drawing file header comment (═══ style)\n"
        f"- Use section dividers (─── style) to organize the code\n"
        f"- Include import statements for any needed stdlib modules\n"
        f"- Write multiple helper functions before a main() function\n"
        f"- Use the pipeline |> operator wherever it makes the code cleaner\n"
        f"- Include a complete working main() with printed output\n"
        f"- Call main() at the end of the file\n"
        f"- Minimum 80 lines of real code\n"
        f"- NO markdown fences, NO explanation — just the raw .ltl file"
    )
    return system, user

def build_stdlib_prompt(module: str, description: str) -> tuple[str, str]:
    system = LTL_SYNTAX_PRIMER
    user = (
        f"Write a Lateralus stdlib module file 'stdlib/{module}.ltl'.\n\n"
        f"Module purpose: {description}\n\n"
        f"Requirements:\n"
        f"- Begin with: -- stdlib/{module}.ltl\n"
        f"             -- LATERALUS {module.title()} Module\n"
        f"             -- (description)\n\n"
        f"             module {module.title()}\n"
        f"- Use struct definitions for data types\n"
        f"- Export a clean public API of functions\n"
        f"- Include docstring-style comments above each exported function\n"
        f"- Use double-dash -- for comments (stdlib convention)\n"
        f"- Cover edge cases and document complexity (O notation)\n"
        f"- Minimum 100 lines\n"
        f"- NO markdown fences — just the raw .ltl file"
    )
    return system, user

def build_blog_prompt(slug: str, description: str) -> tuple[str, str]:
    system = LTLML_SYNTAX_PRIMER
    user = (
        f"Write a Lateralus blog post as a .ltlml file.\n\n"
        f"Slug: {slug}\n"
        f"Topic: {description}\n\n"
        f"Requirements:\n"
        f"- Use today's date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
        f"- Author: bad-antics\n"
        f"- At least 4 sections with ##  headings\n"
        f"- At least 3 code examples in ```lateralus fenced blocks\n"
        f"- 600-900 words of body text\n"
        f"- Direct, technical, no fluff\n"
        f"- NO markdown wrapper around the HTML — output the raw .ltlml file"
    )
    return system, user

def build_paper_prompt(slug: str, description: str) -> tuple[str, str]:
    system = LTLML_SYNTAX_PRIMER
    user = (
        f"Write a Lateralus technical paper as a .ltlml file.\n\n"
        f"Slug: {slug}\n"
        f"Topic: {description}\n\n"
        f"Requirements:\n"
        f"- Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
        f"- Author: bad-antics\n"
        f"- Include: abstract, introduction, 4+ numbered sections, conclusion, references\n"
        f"- Use academic-but-accessible tone\n"
        f"- Lateralus code examples in ```lateralus fenced blocks\n"
        f"- Discuss formal properties, tradeoffs, and design rationale\n"
        f"- 900-1400 words\n"
        f"- NO markdown wrapper — output the raw .ltlml file"
    )
    return system, user

# ── Generation plan: rotating queue of what to produce next ───────────────────

def build_queue() -> list:
    """Return a shuffled list of (kind, slug, destpath, system, user) tuples."""
    items = []
    for slug, desc in EXAMPLE_TOPICS:
        s, u = build_example_prompt(slug, desc)
        items.append(("example", slug, LATERALUS_DIR / "examples" / f"{slug}.ltl", s, u))
    for slug, desc in STDLIB_TOPICS:
        s, u = build_stdlib_prompt(slug, desc)
        items.append(("stdlib", slug, LATERALUS_DIR / "stdlib" / f"{slug}.ltl", s, u))
    for slug, desc in BLOG_TOPICS:
        s, u = build_blog_prompt(slug, desc)
        items.append(("blog", slug, LATERALUS_DIR / "docs" / "blog" / f"{slug}.ltlml", s, u))
    for slug, desc in PAPER_TOPICS:
        s, u = build_paper_prompt(slug, desc)
        items.append(("paper", slug, LATERALUS_DIR / "docs" / "papers" / f"{slug}.ltlml", s, u))
    random.shuffle(items)
    return items

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg: str):
    print(f"[{now_iso()}] {msg}", flush=True)

def ollama_is_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False

# Minimum accepted content sizes — prevents writing empty stub files
MIN_LTL_BYTES   = 800
MIN_LTLML_BYTES = 1200

def _clean_fences(text: str) -> str:
    """Strip markdown code fences the model sometimes wraps output in."""
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$",            "", text, flags=re.MULTILINE)
    return text.strip()

def ollama_chat(system: str, user: str, timeout: int) -> dict:
    """Stream from /api/generate, accumulate tokens, return when done or timed out."""
    # Build a single combined prompt from system + user
    combined = f"{system}\n\n---\n\n{user}"
    payload = json.dumps({
        "model":  MODEL,
        "prompt": combined,
        "stream": True,
        "options": {
            "num_predict": 3000,
            "temperature": 0.82,
            "top_p":       0.93,
            "repeat_penalty": 1.1,
        },
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    chunks = []
    total_tokens = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw_line in r:
                if time.monotonic() - t0 > timeout:
                    break
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                token = obj.get("response", "")
                chunks.append(token)
                if obj.get("eval_count"):
                    total_tokens = obj["eval_count"]
                if obj.get("done"):
                    break
        elapsed = round(time.monotonic() - t0, 3)
        content = _clean_fences("".join(chunks))
        return {"ok": True, "content": content, "elapsed_s": elapsed, "tokens": total_tokens}
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e), "elapsed_s": round(time.monotonic() - t0, 3)}
    except Exception as e:
        return {"ok": False, "error": str(e), "elapsed_s": round(time.monotonic() - t0, 3)}

def write_session_log(event: dict):
    from datetime import date
    dest = OUTPUT_DIR / "sessions" / f"{date.today().isoformat()}.ndjson"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a") as f:
        f.write(json.dumps({"ts": now_iso(), **event}) + "\n")

# ── Main loop ─────────────────────────────────────────────────────────────────

class GracefulExit(Exception):
    pass

def _handle_signal(signum, frame):
    raise GracefulExit()

def run():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    for subdir in ("examples", "stdlib", "docs/blog", "docs/papers"):
        (LATERALUS_DIR / subdir).mkdir(parents=True, exist_ok=True)

    log(f"r420-lateralus started  model={MODEL}  interval={GEN_INTERVAL}s")
    log(f"  output → {LATERALUS_DIR}")

    queue = build_queue()
    qi = 0
    total_generated = 0

    try:
        while True:
            if not ollama_is_up():
                log("Ollama unreachable — waiting 30s")
                time.sleep(30)
                continue

            kind, slug, dest, system_prompt, user_prompt = queue[qi % len(queue)]
            qi += 1

            # Skip if already written — don't regenerate existing files
            if dest.exists():
                log(f"skip {kind}/{slug} (exists)")
                time.sleep(2)
                continue

            log(f"generating {kind}/{slug} → {dest.name}")
            result = ollama_chat(system_prompt, user_prompt, GEN_TIMEOUT)

            if result["ok"] and result["content"]:
                content = result["content"]
                # Quality gate — reject stub files that are just a header comment
                min_bytes = MIN_LTLML_BYTES if dest.suffix == ".ltlml" else MIN_LTL_BYTES
                ltl_ok  = dest.suffix != ".ltl"  or "fn " in content or "struct " in content
                size_ok = len(content.encode()) >= min_bytes
                if not size_ok or not ltl_ok:
                    log(f"  ✗ rejected — too short ({len(content.encode())}B < {min_bytes}B) "
                        f"or missing fn/struct")
                    write_session_log({"type": "lateralus_gen_reject", "kind": kind,
                                       "slug": slug, "bytes": len(content.encode()),
                                       "reason": "quality_gate"})
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content + "\n")
                    total_generated += 1
                    log(f"  ✓ wrote {dest.stat().st_size} bytes  "
                        f"{result['elapsed_s']}s  tokens={result.get('tokens','?')}  "
                        f"total={total_generated}")
                    write_session_log({
                        "type": "lateralus_gen",
                        "kind": kind,
                        "slug": slug,
                        "file": str(dest.relative_to(OUTPUT_DIR)),
                        "bytes": dest.stat().st_size,
                        "elapsed_s": result["elapsed_s"],
                        "tokens": result.get("tokens"),
                    })
            else:
                log(f"  ✗ {result.get('error', 'empty response')}")
                write_session_log({
                    "type": "lateralus_gen_fail",
                    "kind": kind,
                    "slug": slug,
                    "error": result.get("error", "empty"),
                })

            # Rebuild and reshuffle the queue once we've gone through everything
            if qi % len(queue) == 0:
                log(f"completed full cycle ({len(queue)} items) — reshuffling")
                queue = build_queue()

            log(f"  sleeping {GEN_INTERVAL}s")
            time.sleep(GEN_INTERVAL)

    except GracefulExit:
        log(f"r420-lateralus shutting down  total_generated={total_generated}")
        sys.exit(0)

if __name__ == "__main__":
    run()
