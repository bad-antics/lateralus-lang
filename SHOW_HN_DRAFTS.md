# Show HN Drafts — Ready to Post

## Post 1: Lateralus Language (v3.2.0 — refreshed 2026-04-26)

**Title:** Show HN: Lateralus – Pipeline-native language with multi-target codegen and its own OS

_(Backup title if first reads as too broad: "Show HN: Lateralus – I built a programming language and an OS that runs natively in it")_

**URL:** https://lateralus.dev

**Text (for text post option):**
I built a pipeline-native programming language and a bare-metal operating system that runs in it. The language has been in public development for 3+ years; it's now at v3.2.0, statically typed, and ships a working compiler with four backends.

The core bet: most real code is sequential transforms over data, so the language should make that the natural shape — not a library bolted onto OOP.

Where it is today (v3.2.0, April 2026):
- Pipeline operators: `data |> filter(pred) |> map(f) |> reduce(+, 0)`
- Algebraic data types, pattern matching, Hindley–Milner inference
- Four compilation targets: C99, JavaScript, WebAssembly, Python (reference)
- Effect system tracking IO / Async / Unsafe
- Structured concurrency (nursery model), `async`/`await`, `spawn`
- 62 stdlib modules, ~2k tests, self-hosted lexer + parser + formatter
- Bare-metal companion OS written in Lateralus (LateralusOS, in-tree)
- 58 canonical research papers on the theory (linked below)

Install (all five registries, all up to date as of v3.2.0):
- `pip install lateralus-lang` — PyPI
- `code --install-extension lateralus.lateralus-lang` — VS Code Marketplace
- Same ID on **Open VSX** for VSCodium / Cursor / Gitpod / code-server users
- `docker run --rm -v "$PWD:/src" -w /src ghcr.io/bad-antics/lateralus-lang:3.2.0 run hello.ltl` — container
- `npm install lateralus-grammar` — TextMate grammar (for tooling integrators)

Launch FAQ (please skim before commenting; I tried to anticipate your question): https://github.com/bad-antics/lateralus-lang/blob/main/docs/hn-launch-faq.md

Reproducible cross-language benchmarks (5 iters + 2 warmup, same machine, Python 3.13 / Node 20 / gcc -O2):

| Benchmark | Lateralus C99 | Lateralus interp | Python | Node |
|-----------|---------------|------------------|--------|------|
| fib(35) | **0.004s** | 0.474s | 0.236s | 0.110s |
| sieve(50k) | **0.001s** | 0.272s | 0.025s | 0.091s |
| mandelbrot(150×100) | **0.003s** | 0.325s | 0.084s | 0.095s |
| nbody(5000 steps) | **0.001s** | 0.277s | 0.036s | 0.095s |
| binary_trees(12) | — | 0.274s | 0.023s | 0.090s |

Where the C99 backend covers the workload end-to-end it's ~30–60× faster than CPython — numbers with no hand-tuning beyond `gcc -O2`. On sieve, the native binary is **~300× faster than the Lateralus interpreter**; on nbody it's **~450×**. One benchmark (`binary_trees`) doesn't go through C99 yet because the source uses `fn make(d) -> any` returning either an `int` sentinel or a `Tree` struct, and `any`-typed returns with mixed primitive/struct variants aren't supported by the typed C codegen yet. Rather than fake that number, the harness skips it; the gap is tracked on the v3.2 roadmap.

All backends produce byte-identical output; the sole non-match is CPython drifting by 1 ULP in the last digit of nbody (`-14073.193837907827` vs `-14073.193837907826`) due to its own FP rounding — our C99 output matches the Lateralus interpreter and Node.js exactly.

Paper index: https://github.com/bad-antics/lateralus-papers
Source: https://github.com/bad-antics/lateralus-lang
Benchmarks: https://github.com/bad-antics/lateralus-lang/tree/main/benchmarks

Happy to answer questions on the pipeline type system, the effect tracker, or why anyone would write an OS in a language this young.

---

## Post 2: GrugBot420

**Title:** Show HN: GrugBot420 – Neuromorphic LLM routing in Julia using spiking neural networks

**URL:** https://github.com/grug-group420/grugbot420

**Text:**
GrugBot420 uses biologically-inspired spiking neural networks (Leaky Integrate-and-Fire neurons with STDP learning) to route queries across multiple LLM backends. Instead of static if/else routing rules or a supervised classifier, the network learns which model to dispatch to from live feedback.

Architecture: 4 cognitive "lobes" that loosely mirror brain regions:
- Broca (language parsing / intent extraction)
- Hippocampus (short-term context + retrieval)
- Prefrontal (reasoning depth estimation)
- Motor (dispatch + response assembly)

Written in pure Julia using multiple dispatch. No Python bridge, no PyTorch, no CUDA glue — zero external ML dependencies. The whole thing is <3k LoC.

Paper (arXiv-style, in-repo): https://github.com/grug-group420/grugbot420-paper
Benchmarks + methodology: see `benchmarks/` in the main repo

Honest caveats up front:
- Results are on our internal benchmark set; not a replacement for MMLU/HELM
- Requires at least 2 backend LLMs to make the routing meaningful
- The biologically-inspired framing is a design lens, not a scientific claim — LIF neurons here are a mechanism, not a brain model

Happy to talk about the STDP learning rule choice or why we picked Julia over Python.

---

## Post 3: LogReaper

**Title:** Show HN: LogReaper – DFIR log analysis with automated IOC extraction

**URL:** https://github.com/bad-antics/nullsec-logreaper

**Text:**
I built LogReaper for incident responders who need fast IOC extraction from heterogeneous log sources without standing up a full SIEM. It processes:

- Linux syslog, auth.log, kern.log
- Windows Event Logs (evtx)
- Cloud audit trails (CloudTrail, Azure Activity, GCP Audit)
- Web server access + error logs (nginx, apache, caddy)

Extracts: IPv4/IPv6 addresses, domains (with TLD validation), URLs, file hashes (MD5/SHA1/SHA256), email addresses, CVE IDs, MITRE ATT&CK technique references, and base64/hex-encoded payloads.

Outputs: STIX 2.1 bundles, MISP JSON, plain CSV, or Markdown timeline reports ready for the incident ticket.

The gap it fills: between raw `grep | sort | uniq` and a $200k/year SIEM subscription. Think of it as `jq` for DFIR logs — composable, scriptable, reproducible.

Source: https://github.com/bad-antics/nullsec-logreaper

Common workflow we optimised for: IR team gets a ~2 GB log tarball at 3am, needs IOCs in a ticket in 10 minutes. LogReaper handles that in one command.

---

## Posting Schedule

> Updated 2026-04-21 for v3.1.0 launch week. Best HN slot: Tue/Wed 9–11am ET.

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
