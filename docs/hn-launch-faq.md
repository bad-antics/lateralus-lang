# Show HN Launch-Day FAQ

> Prepared Q&A for the Lateralus v3.1.0 Show HN post. Keep this tab open during the launch — answer fast, answer honestly, link to code.

---

## Category 1: "Why another language?"

### Q: Why not just use Elixir / F# / Haskell / ReScript / Gleam — they all have pipelines.
Pipelines are table stakes at this point, agreed. The differentiator is what's *around* the pipeline:

- Pipeline type inference propagates through `|>` stages without annotation noise
- Effect system (`IO`, `Async`, `Unsafe`) is tracked at the pipeline stage boundary, not just at function signatures
- Structured concurrency is built into the semantics — a `spawn` inside a pipeline stage is scoped to that stage's nursery
- Four codegen targets share one IR, so library authors write once

Is that enough to leave your current stack? Probably not today. It's enough to try it on a side project.

### Q: What niche does this actually fill?
Data-heavy application code where:
1. You want static types but not a type theory dissertation
2. Most of your logic is `source → transform → transform → sink`
3. You want concurrency without callback/promise soup
4. You eventually need to ship a native binary or a WASM blob

If you're writing kernels, DSP, or anything perf-critical today, C99 backend is the path — but the native C99 emitter is still maturing.

### Q: Isn't this just another hobby language?
Fair question. Evidence it's more than that:
- 3+ years of development
- ~2k passing tests, self-hosted lexer/parser/formatter
- 62 stdlib modules, 58 research papers on the theory
- A companion bare-metal OS written in it (reboot-to-desktop works)
- Real package on PyPI + VS Code Marketplace extension
- Reproducible cross-language benchmarks committed to the repo

Whether that crosses your threshold for "serious" is up to you.

---

## Category 2: Performance

### Q: Your benchmarks show Lateralus is 10× slower than Python on sieve. That's bad.
The *tree-walking interpreter* is slow, yes. The *C99 backend* now covers three of five benchmarks with ~30–60× speedups over CPython: ~60× on `fib`, ~30× on `sieve`, ~30× on `mandelbrot`. All numbers are in the repo's benchmark harness, reproducible with one command.

The full story:
- `lateralus run foo.ltl` → correctness-first tree-walker in Python, ~2k LoC. Slow by design.
- `lateralus c foo.ltl -o foo.c && gcc -O2 foo.c` → 16 KB native binary. Competitive with hand-written C.

Currently the C99 backend covers 4 of our 5 benchmarks end-to-end (fib, sieve, mandelbrot, nbody). The last one (`binary_trees`) uses `fn make(d) -> any` returning either an `int` sentinel or a `Tree` struct — `any`-typed returns with mixed primitive/struct variants need a proper dynamic-value-representation design pass in the typed codegen path, which is tracked on the v3.2 roadmap. Rather than omit it or fake numbers, the harness skips and reports "—".

LLVM backend is the v4.0 target and will close the remaining gaps.

### Q: What's the GC?
Reference interpreter uses Python's reference counting + cycle collector. The C99 backend currently uses Boehm-style conservative GC. LLVM backend will move to precise tracing with generational + incremental collection. Zero unsafe code in user programs unless they opt in with `@foreign` or an `unsafe` block.

### Q: How big is the binary?
C99 backend emits ~80–200 KB stripped executables for typical programs. No runtime dependency chain beyond libc. The freestanding mode (used by LateralusOS) has zero runtime — it's ~12 KB of kernel glue.

---

## Category 3: Type System

### Q: Is it fully inferred or do I need annotations?
Hindley–Milner everywhere except public module boundaries, where we require them for stable APIs. Same spirit as Haskell's `-Wmissing-signatures` but enforced.

### Q: Do you have dependent types / row types / linear types?
No dependent types (deliberate — we want fast type checking for IDE responsiveness). Row polymorphism is used internally for record types. Linear types are on the v4 roadmap for resource safety, scoped to effect handlers.

### Q: Sum types?
Yes, `enum` with payloads. Pattern matching is exhaustive-checked.

```lateralus
enum Result {
    Ok(any),
    Err(str),
}

match outcome {
    Ok(value) => process(value),
    Err(msg)  => log(msg),
}
```

---

## Category 4: Concurrency

### Q: Async/await or goroutines?
Both, unified. `async fn` / `await` for cooperative work, `spawn` for parallel tasks. All scoped to nurseries — no orphaned tasks, no `Promise.all` boilerplate, no select soup.

```lateralus
nursery {
    spawn worker_a()
    spawn worker_b()
    let c = await long_query()
}  // all three finish or all three are cancelled
```

### Q: Is spawn pre-emptive or cooperative?
Cooperative by default. The runtime has a work-stealing scheduler for `@parallel`-marked pipeline stages. No function-coloring problem because `async` is an effect, not a type constructor.

---

## Category 5: Compilation Targets

### Q: Why C99 and not C11?
Portability to the weirdest embedded toolchains. LateralusOS bootloader runs on freestanding C99 with zero libc.

### Q: What's the WASM story?
Emits WASM via a direct backend (not via Emscripten). Binary sizes are ~60% smaller than equivalent Rust+wasm-bindgen output because we skip the JS glue layer. The REPL on lateralus.dev runs fully in-browser via this path.

### Q: JS target — is it readable?
Yes, intentionally. We emit modern ES2022 with source maps. The intent is that polyglot projects can hand-audit the JS output or drop it into a Node service without adopting a separate runtime.

### Q: No JVM target?
Not yet. Would be a clean fit (pipelines map well to stream operators) but we're finishing LLVM first.

---

## Category 6: Tooling

### Q: LSP?
Yes, in-tree, covers completion, go-to-definition, references, hover, rename, code actions, diagnostics, formatting. DAP server for debugging. Both ship with the VS Code extension.

### Q: Package manager?
Yes, `ltl pkg`. Uses lockfiles, content-addressed store, reproducible builds. Registry mirrors on S3.

### Q: REPL?
Two of them: a plain readline REPL and an enhanced one with syntax highlighting, multi-line editing, and live type display.

---

## Category 7: The OS Question

### Q: You wrote an OS in this? Why?
Three reasons:
1. Stress-test the language — if the compiler can emit code that boots on bare metal, the FFI and freestanding modes are real
2. Dogfood the C99 backend — LateralusOS is compiled entirely through it
3. It's fun

LateralusOS boots to a framebuffer desktop in QEMU. Not a daily driver.

### Q: Does it have drivers?
VGA framebuffer, keyboard, mouse, serial, timer. No networking, no storage. It's a proof of concept, not a competitor to Linux.

---

## Category 8: The Honest Questions

### Q: Who's paying for this?
Nobody. Self-funded. That's why the v3.2 LLVM work is on nights/weekends.

### Q: If you got hit by a bus?
Bootstrap compiler is self-hosted. All docs, papers, grammar, and stdlib are in the public repo. The specification is frozen per-release. Someone else could pick it up.

### Q: What's the biggest design regret?
The syntax for type annotations on generic parameters. The current `list[int]` works but `List[int]` would have aligned better with how stdlib types are capitalized elsewhere in the ecosystem. Hard to change now without breaking every example.

### Q: What's the thing you're most proud of?
That the 58 research papers actually line up with the implementation. You can read the pipeline-type paper, open the type-inference source file, and the algorithm names match. That took discipline.

---

## Closing Line

If you try it and hit anything confusing, the issue tracker is the place — I read every one. Thanks for taking a look.
