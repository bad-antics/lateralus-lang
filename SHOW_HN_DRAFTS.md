# Show HN Drafts — Ready to Post

## Post 1: Lateralus Language

**Title:** Show HN: Lateralus – A pipeline-native programming language targeting C99/LLVM/JS/WASM

**URL:** https://lateralus.dev

**Text (for text post option):**
I've been building Lateralus, a statically-typed programming language where pipelines are first-class citizens. The core idea: data transformations should compose naturally through typed pipeline stages.

Key features:
- Pipeline operators: `data |> transform() |> filter(predicate) |> collect()`
- Algebraic data types with pattern matching
- Hindley-Milner type inference with pipeline extensions
- Multiple compilation targets: C99, LLVM IR, JavaScript, WebAssembly
- Effect system tracking IO/Async/Unsafe
- Structured concurrency (nursery model)
- 62 standard library modules, 1,976 tests
- Self-hosted compiler components
- Even a bare-metal OS written in it (LateralusOS)

Install: `pip install lateralus-lang`

Paper: https://github.com/bad-antics/lateralus-lang-paper

The language is at v2.4 now. Working on LLVM native backend, dependent types, and GPU compute for v3.0.

Would love feedback on the pipeline composition model — is this something you'd want in your daily driver language?

---

## Post 2: GrugBot420

**Title:** Show HN: GrugBot420 – Neuromorphic LLM routing in Julia using spiking neural networks

**URL:** https://github.com/grug-group420/grugbot420

**Text:**
GrugBot420 uses biologically-inspired spiking neural networks (Leaky Integrate-and-Fire neurons with STDP learning) to route queries to the most appropriate LLM backend. Instead of static routing rules, the system learns which model handles which task best.

Architecture: 4 cognitive lobes (Broca/language, Hippocampus/memory, Prefrontal/reasoning, Motor/action) that mirror brain regions. Written in pure Julia using multiple dispatch — zero external dependencies.

Paper: https://github.com/grug-group420/grugbot420-paper

Results: 15-23% improvement on multi-step reasoning vs single-model baselines, 40% latency reduction.

---

## Post 3: LogReaper

**Title:** Show HN: LogReaper – DFIR log analysis with automated IOC extraction

**URL:** https://github.com/bad-antics/nullsec-logreaper

**Text:**
I built LogReaper for incident responders who need fast IOC extraction from heterogeneous log sources. It processes syslog, auth logs, Windows Event logs, and cloud audit logs — extracting IPs, domains, hashes, and building attack timelines automatically.

Think of it as the gap between raw `grep` and a full SIEM deployment.

---

## Posting Schedule

| Day | Post | Subreddit/Platform |
|-----|------|-------------------|
| Mon | Lateralus | Hacker News (Show HN) |
| Wed | Lateralus | r/ProgrammingLanguages |
| Fri | GrugBot420 | r/Julia |
| Next Mon | LogReaper | r/netsec |
| Next Wed | GrugBot420 | Hacker News (Show HN) |
| Next Fri | LogReaper | r/dfir |
| Week 3 Mon | BlackFlag ECU | r/CarHacking |
| Week 3 Wed | Lateralus | r/compilers |

**Best times:** Tuesday–Thursday, 9-11am ET for HN. Monday–Wednesday for Reddit.
