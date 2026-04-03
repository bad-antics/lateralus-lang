# LATERALUS v1.3.0 Changelog

> Created and maintained by **bad-antics**

All notable changes to the LATERALUS programming language.

## [1.3.0] — 2025-01-20

### Language Features
- throw / try-as-expression: First-class error handling
- emit / probe / measure: Event-driven programming primitives with EventBus
- Optional pipeline |?: Safe None propagation
- Boolean keywords: and, or, not
- pass statement for empty blocks
- 10 exception type aliases

### Decorators
- @memo: Automatic memoization
- @test: Mark test functions
- @typed: Runtime type checking

### Built-in Functions (30+ new)
- Core, Collections, Strings, Math, Introspection categories

### New Engine Subsystems
- Math Engine: Julia-inspired arbitrary precision, matrices, vectors, intervals, AD
- Crypto Engine: SHA-256/512, BLAKE2b, HMAC, PBKDF2, AES-256-GCM, LBE encoding
- LTLML Markup: Full .ltlml parser with HTML renderer
- Bytecode Format: Proprietary .ltlc compiler/decompiler/inspector
- Error Engine: 35 error codes, rich diagnostics, did-you-mean suggestions

### New Standard Library
- science.ltl: Physical constants, unit conversions, orbital mechanics
- optimize.ltl: Root finding, integration, minimization, interpolation
- functional.ltl: Composition, currying, higher-order functions

### CLI Extensions
- compile, decompile, inspect, doc, engines, hash, bench commands

### Documentation
- Language specification, blog post, academic design paper in LTLML
- 3 new example programs (math, crypto, science demos)

### Testing
- 167 core tests + ~190 new engine tests
