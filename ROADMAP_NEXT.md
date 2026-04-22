# Lateralus: Roadmap to a Real Programming Language

> **Status**: v3.1.0 — PyPI + VS Code Marketplace + 4/5 native benchmarks live
> **Last updated**: 2026-04-21
> **Author**: bad-antics

This document is the honest plan for turning Lateralus from "published toolchain
with 1976 passing tests" into something people actually use in production.

It is deliberately *not* aspirational. Every tier lists concrete acceptance
criteria, rough effort estimates, and the specific files or subsystems involved.
If a tier doesn't ship, the language doesn't advance.

---

## Where We Are: v3.1.0 (April 2026)

| Capability                          | Status |
|-------------------------------------|--------|
| Lexer / Parser / AST                | ✅ Stable, 1976 tests |
| Hindley–Milner type inference       | ✅ With row polymorphism, ADTs |
| Tree-walking interpreter            | ✅ Reference semantics |
| VM bytecode + disassembler          | ✅ |
| Python codegen target               | ✅ |
| C99 codegen target                  | 🟡 3/5 benchmarks native |
| WASM codegen target                 | 🟡 Basic ops, no stdlib |
| Freestanding C (LateralusOS)        | ✅ Boots in QEMU |
| LSP server (completion, refs, etc.) | ✅ Published |
| DAP debugger                        | ✅ Basic stepping |
| Formatter / Linter                  | ✅ |
| Package manager (`lateralus pkg`)   | 🟡 Local only, no registry |
| PyPI distribution                   | ✅ `pip install lateralus-lang` |
| VS Code Marketplace                 | ✅ `lateralus.lateralus-lang` |
| Linguist classification             | 🟡 PR staged, not yet submitted |
| Production users                    | ❌ Zero known |

Honest summary: **tier-1 infrastructure is live. Tier-2 (credibility) is the
next frontier.**

---

## Tier 2: Credibility (v3.2 — v3.5, Q3 2026)

**Goal**: Someone other than the author ships a non-trivial program in
Lateralus. This is the single biggest signal of "real language" status.

### v3.2 — C Backend Feature Parity (June 2026)

**Acceptance**: All 5 benchmarks compile via `lateralus c && gcc -O2`.
**Effort**: ~2 weeks.

- [x] **`@law` — first-class executable specifications** (landed v3.2-dev)
      — `@law fn foo(xs: list[int]) -> bool { ... }` + `lateralus verify`.
      Generators auto-derived from declared types; counter-examples
      iteratively shrunk. No mainstream language has this as a language
      primitive (QuickCheck/Hypothesis require per-type instances/strategies).
      Files: [lateralus_lang/law_runner.py](lateralus_lang/law_runner.py),
      [lateralus_lang/codegen/python.py](lateralus_lang/codegen/python.py),
      [lateralus_lang/__main__.py](lateralus_lang/__main__.py).
- [ ] **`any`-typed returns with mixed primitive/struct variants**
      (unblocks `binary_trees`)
  - Current source: `fn make(d: int) -> any { if d == 0 { return 0 }
    return Tree{...} }` — sentinel primitive + struct in one return type
  - Needs: extend `ltl_value_t` with a `LTL_PTR` tag for owned struct
    pointers; auto-box `return 0` → `ltl_box_int(0)` and
    `return Tree{...}` → `ltl_box_ptr(malloc(Tree))` when the function's
    declared return type is `ltl_value_t`; coerce `any == int` via tag check;
    lower `any.field` via tag-dispatched unbox
  - File: [lateralus_lang/codegen/c.py](lateralus_lang/codegen/c.py) —
    `_visit_ReturnStmt`, `_expr_BinOp` (`==`/`!=`), `_expr_FieldExpr`
- [x] **Typed C-array lowering for homogeneous numeric list literals**
      (unblocked `nbody` in v3.1) — `let xs = [0.0, 4.84, ...]` now compiles
      to `double xs[N] = {...}` with native indexing
- [ ] **Typed `for x in list` without boxing** when element type is known
- [ ] **Fold constant list sizes** so `[0] * 1024` emits stack `int64_t buf[1024]`
      where provable

### v3.3 — Package Registry (August 2026)

**Acceptance**: `lateralus pkg add math-ext` downloads and resolves a real
third-party package. At least 5 seed packages published.
**Effort**: ~6 weeks.

- [ ] Registry service (pick one: static S3-backed JSON + HTTP; or GitHub as
      backend; or hosted registry). Static JSON is simplest and appropriate for
      the scale of a new language.
- [ ] Package manifest format (`lateralus.toml` — already spec'd, needs polish)
- [ ] Version resolution: SAT-based (cargo-style) or greedy (pip-style)
- [ ] Publisher auth + namespace reservation
- [ ] **Seed packages** authored by maintainer:
  - `ltl-http` — http client wrapping libcurl
  - `ltl-json` — parser + pretty printer (currently stdlib, split out)
  - `ltl-cli` — argparse-style CLI helper
  - `ltl-test` — richer test harness
  - `ltl-sql` — sqlite3 bindings

### v3.4 — Stable ABI for C Interop (October 2026)

**Acceptance**: Third-party C libraries usable from Lateralus without writing
C shims per call. At least one "wow" integration: SQLite, SDL2, or libcurl.
**Effort**: ~4 weeks.

- [ ] `@foreign(header="curl.h", lib="curl")` attribute → auto-generate bindings
- [ ] `extern "C" fn` declaration syntax (already parsed, needs codegen)
- [ ] `Ptr[T]` / `Slice[T]` types with safe lowering rules
- [ ] Document calling conventions + memory ownership rules

### v3.5 — First External Contributor (December 2026)

**Acceptance**: Merge a PR from someone not associated with the project that
lands real code (not typo fix). Measured by `git shortlog -sn` on master.
**Effort**: depends on bus traffic; gate is discoverability, not code.

- [ ] Good-first-issue labeling (~20 issues, scoped ≤ 2 hours each)
- [ ] Written contributor guide with "here's the compiler architecture" walkthrough
- [ ] Monthly release cadence (no feature vacuum between "shipped" and "next")

---

## Tier 3: Self-Hosting (v4.0, Q2 2027)

**Goal**: The Lateralus compiler is written in Lateralus. This is the
single biggest *technical* signal that a language is production-ready.

**Why self-hosting matters**:
1. Forces every feature to be good enough to build a compiler with
2. Doubles the test suite (anything that breaks the bootstrap breaks a user)
3. Removes Python as a dependency of the compiler itself
4. Makes the language "actual" — not a DSL on top of Python

### v4.0 — Bootstrap Compiler

**Acceptance**: `./configure && make` produces a working Lateralus compiler
with zero Python installed. The compiler can compile itself.
**Effort**: ~8 months.

- [ ] **Port the lexer** ([lateralus_lang/lexer.py](lateralus_lang/lexer.py), ~600 LoC)
      to Lateralus. File exists as [bootstrap/v2_lexer.ltl](bootstrap/v2_lexer.ltl) — audit + complete.
- [ ] **Port the parser** (~1800 LoC) — already started in [bootstrap/v2_parser.ltl](bootstrap/v2_parser.ltl)
- [ ] **Port the type checker** (~2500 LoC) — [bootstrap/v2_type_system.ltl](bootstrap/v2_type_system.ltl)
- [ ] **Port the C codegen** (~1600 LoC) — new file `bootstrap/v2_c_codegen.ltl`
- [ ] **Three-stage bootstrap**:
  1. Stage 0: Python compiler compiles `v2_*.ltl` → `ltlc0`
  2. Stage 1: `ltlc0` compiles `v2_*.ltl` → `ltlc1`
  3. Stage 2: `ltlc1` compiles `v2_*.ltl` → `ltlc2`
  4. Verify `ltlc1` and `ltlc2` are byte-identical
- [ ] CI runs full bootstrap on every commit
- [ ] Archive Python compiler as "reference implementation", stop shipping it

**This is the "real language" line.** Everything below is scaling, not
existence-proof.

---

## Tier 4: Serious Tooling (v4.1 — v4.5, 2027)

### v4.1 — LLVM Backend

**Acceptance**: `lateralus llvm` produces `.ll` files optimizable with `opt -O3`.
Benchmarks show +30% over C99 path on numerical code.
**Effort**: ~3 months.

- [ ] Typed SSA IR (one step up from the current untyped IR)
- [ ] LLVM C API binding via `@foreign`
- [ ] Support all targets LLVM supports (ARM, RISC-V, WASM, etc.)
- [ ] Incremental compilation with module hashing

### v4.2 — Incremental Type Checking

**Acceptance**: Editing one file in a 100k-LoC project rechecks in <200 ms.
**Effort**: ~2 months.

- [ ] Module-level caching of type environments
- [ ] Dependency tracking: which signatures does a definition use?
- [ ] Hot path in LSP server — currently full-file re-infers on every keystroke

### v4.3 — Proper GC (not Boehm)

**Acceptance**: Generational precise tracing GC, <5 ms pause at 1 GB heap.
**Effort**: ~4 months.

- [ ] Write barrier injection during codegen
- [ ] Read fence for concurrent marking
- [ ] Card-marking or remembered sets for young→old pointers
- [ ] Heap profiler with retention paths
- Alternative: **ownership + borrow checking** (Rust-style) — research-level
  effort, tracked as v5.x aspirational

### v4.4 — Build System

**Acceptance**: `lateralus build` does incremental compilation, parallel
module compilation, and produces both shared libs and executables.
**Effort**: ~1 month.

### v4.5 — Production Debugger

**Acceptance**: Step through optimized C/LLVM output back to Lateralus source
lines. Variable inspection. Conditional breakpoints. Works in VS Code via DAP.
**Effort**: ~2 months.

- [ ] Emit DWARF debug info in C and LLVM backends
- [ ] Source map covering all optimization passes
- [ ] Variable lifetime tracking for "optimized out" diagnostics

---

## Tier 5: Ecosystem (v5.0+, 2028)

**Goal**: People can write apps, not just algorithms.

### Domains to unlock (pick 2, not all)

**Web backend**
- [ ] Async runtime (green threads or poll-based, pick one)
- [ ] Production HTTP server (`ltl-hyper` or bindings to an existing one)
- [ ] ORM or query builder for PostgreSQL / SQLite
- [ ] Template engine
- [ ] Reference app: URL shortener or paste service in <1000 LoC

**Scientific computing** (our research papers hint at this)
- [ ] Numpy-equivalent: `ltl-array` with BLAS/LAPACK bindings
- [ ] DataFrame library matching pandas 80/20
- [ ] Plotting via SDL2 or web backend
- [ ] Jupyter kernel (partial work exists, needs polish)

**Systems**
- [ ] LateralusOS reaches user-mode programs (currently kernel-only)
- [ ] Syscall bindings for Linux/BSD via `@foreign`
- [ ] Shell scripting mode (`#!/usr/bin/env lateralus`)

### Long-term (aspirational, not scheduled)

- Stable 1.0 language spec frozen (no breaking changes)
- WebAssembly as first-class deploy target for browser apps
- Formal semantics (operational + denotational) published as a paper
- Certified compiler (Coq or Lean proofs of type-soundness + correctness
  of at least the C backend on a subset)
- Distribution through OS package managers (apt, brew, pacman, nix)

---

## What "Real Programming Language" Actually Means

There's no single test. The community-accepted signals are:

1. **Self-hosting** (v4.0 target) — compiler written in the language
2. **External contributors** (v3.5 target) — merged PRs from strangers
3. **Third-party production use** — someone ships a product with it
4. **GitHub Linguist recognition** (v3.2 target via pending PR) — `.ltl` files
   show up as "Lateralus" in repo statistics
5. **Conference talks / papers** — independent researchers cite it
6. **Book deal** — formal publisher greenlights a "Programming in Lateralus"
7. **Job listings** — someone else hires for Lateralus experience

We are currently 0/7 on external validation. PyPI publication and the
Marketplace extension are table stakes; they don't count.

**The next twelve months are about converting zero to one on signal #2 and
#3.** Everything else follows.

---

## Immediate Next Actions (next 4 weeks)

Ranked by leverage:

1. **Push `bad-antics/lateralus-grammar` public repo** so Linguist PR can go in.
   Blocks PyPI-visibility → GitHub-visibility handoff. User action required.
2. **File the Linguist PR** — 3-week review cycle, so start now.
3. **Ship v3.2 C-backend enum codegen** (2 weeks) — gets binary_trees benchmark
   to 4/5 native.
4. **Write `lateralus-by-example` book** — 20 short chapters (~100 LoC each),
   published as HTML + PDF. Seeds search traffic.
5. **Launch Show HN** — only *after* steps 1-4 so traffic lands on a more
   polished surface.

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| No external users ever | Medium | Fatal | Aggressive outreach, blog posts, conference talks |
| Self-hosting stalls | Medium | High | Already started (`bootstrap/v2_*.ltl`); timeboxed |
| Maintainer burnout | High | Fatal | Ship to 1.0-spec then slow down; onboard contributors before v4.0 |
| Rust / Zig / Gleam eat our niche | High | Medium | Lean into distinctive pitch (HM inference + pipelines + research provenance) |
| Breaking-change fatigue | Medium | High | Freeze language core at v3.5; all future changes additive |

---

## How to Track Progress

- Roadmap milestones are GitHub issues labeled `tier:N` on
  [github.com/bad-antics/lateralus-lang](https://github.com/bad-antics/lateralus-lang)
- Monthly release notes in [RELEASE_NOTES.md](RELEASE_NOTES.md) document what
  landed vs. what slipped
- Benchmark numbers in [benchmarks/results/results.md](benchmarks/results/results.md)
  regenerated per release
- "Real users" count maintained in `METRICS.md` (to be created) — GitHub
  dependents + known projects + crates.io-style download stats if a registry exists

---

*Spiral outward. Build something beautiful.*
