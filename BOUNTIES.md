# Lateralus Bounties

> First-come, first-merged. One bounty per person per quarter. Payment via
> GitHub Sponsors, Ko-Fi, or BTC/LN — contributor's choice.

Bounties are paid from the project's sponsor revenue. They exist to get
real work done on the fringes where the core maintainers don't have
bandwidth, not to replace good contributions made for love.

If you want to claim a bounty, open an issue titled `[bounty] <name>` on
the repo before you start so we can mark it taken.

---

## 🟢 Currently open

### `[bounty] benchmark-ingest` — $250
Extend `benchmarks/run_benchmarks.py` to drop `import xxhash` / `import
lz4` / `import chacha20` / `import aho_corasick` modules into a combined
source file and run five new micro-benchmarks:

1. xxhash64 over 2 MB of data
2. lz4 compress + decompress round-trip of 4 MB
3. chacha20 encrypt 1 MB
4. aho_corasick search of 1,000 patterns in 1 MB of text
5. radix_sort_u32 on 100,000 keys

Matching Python + Node reference implementations, same inputs, same
expected outputs. Results committed as `benchmarks/results/stdlib_results.md`.

**Why:** gives the speed story its second chapter. The existing
fib/sieve/mandelbrot numbers show raw compute speed; these show
real-workload codec and crypto speed.

### `[bounty] playground-gallery` — $200
Wire up `docs/website/playground/` to load pre-made examples from a
dropdown. Seed with one entry per Spiral Wave (currently waves 5–10)
plus the existing basics. Each entry is the full `examples/spiral_*.ltl`
source ready to run.

**Why:** every visitor gets an in-browser "wow" without reading the repo.

### `[bounty] lsp-hover-signatures` — $300
Lateralus already ships an LSP (`lateralus lsp`). Extend the hover
provider so that hovering a stdlib function name shows its signature
plus the first docstring line. The signatures can be parsed from
`stdlib/*.ltl` at startup; no extra data files needed.

**Why:** makes the language feel "real" in VSCode — autocomplete +
inline docs is the baseline expectation for any stdlib-heavy language.

### `[bounty] rosetta-20` — $150
Add Lateralus solutions to 20 tasks on [rosettacode.org](https://rosettacode.org)
covering the lanes we're strongest in (hashes, codecs, formats, search).
Tasks go under `examples/rosetta/` in the repo with a README mapping
each to its Rosetta URL.

**Why:** free discoverability. Rosetta Code is indexed by every
programming-language aggregator on the internet.

### `[bounty] aoc-2024-all-25` — $500
Solve all 25 Advent of Code 2024 problems in idiomatic Lateralus,
under `examples/advent_of_code/2024/`, one file per day, with test
inputs and expected outputs as `@test` blocks. No solutions that
rely on external data files — inputs pasted as multi-line strings
so `lateralus test` self-verifies.

**Why:** AoC solutions are one of the most-searched "languages in
X" artefacts on GitHub. 25 of them in one commit is a calling card.

### `[bounty] package-registry-mvp` — $400
Scaffold a simple package registry in `tools/registry/`:

- A static directory on S3 / R2 that serves tarballs and `index.json`.
- A `lateralus publish` subcommand that reads `lateralus.toml`, packs
  the project, and uploads to a configured registry URL.
- A `lateralus add <name>` subcommand that fetches + unpacks into a
  workspace's `vendor/` directory.

The registry itself can be a plain CloudFlare Pages / S3 bucket —
no server needed. Must include reproducible SHA-256 pinning.

**Why:** ecosystem velocity. Third-party packages can only exist once
there's a place to put them.

### `[bounty] lt-logs-shipper` — $350
Implement `apps/lt_logs.ltl` as a CLI that:

- Reads log lines from stdin (any of: logfmt, JSON, syslog RFC 5424)
- Filters with a small DSL (regex, field-equals, aho-corasick match)
- Batches matched lines into 1-minute rollups
- Emits rollups as either Parquet or compressed-JSON-lines
- Optionally encrypts rollups with ChaCha20-Poly1305 if `--key` provided

Every capability wires to an existing stdlib module. Ships as a single
`.ltl` file compilable to a native binary via `lateralus c`.

**Why:** the killer demo. "Here's one binary that replaces five
tools in your observability stack, and the source fits in a screen."

### `[bounty] vscode-extension-polish` — $200
The VSCode extension exists but is bare-bones. Add:

- Syntax highlighting for all dialect keywords (`match`, `nursery`,
  `select`, `async for`, `@law`, `@bench`, `@test`, `#[derive]`)
- Snippet completions for the top 20 stdlib modules (one per module
  showing a typical call pattern)
- A status-bar button that runs the current file through
  `lateralus run` and shows output in the OUTPUT pane

**Why:** every editor adoption lowers the onboarding friction by 10×.

### `[bounty] wasm-playground-live` — $300
The current playground runs Python-transpiled code server-side. Switch
to running the WASM backend (`lateralus wasm`) in-browser so code never
leaves the user's machine. Needs a browser-friendly runtime shim that
maps host calls (println, http_get) to JS.

**Why:** playground instantly works offline, is cheaper to host, and
demonstrates the WASM backend actually works end to end.

---

## 🔵 Recurring micro-bounties

- **$25** — write a blog post tutorial for any single stdlib module
  (must include a runnable example and a pinned test vector)
- **$25** — port any idiomatic 50-line Python/Go/Rust program to
  Lateralus (must compile with `lateralus c` and beat the original
  on wall time)
- **$10** — open a high-signal bug report with a minimal reproducer

Drop them in `BOUNTIES-LOG.md` when claimed; we'll review and pay weekly.

---

## Rules in a nutshell

1. Original work, MIT-licensed, your own copyright.
2. Signed-off commits (`git commit -s`) so we know it's yours.
3. Test coverage matches the style of the lane you're working in
   (see `tests/stdlib_spiral_wave_*.ltl` for the bar).
4. We have the right to refuse a submission, but not without a
   written reason on the PR. First-submitted-first-reviewed.
5. Payment is in 14 days of merge.

Questions: open an issue or email `bounties@lateralus.dev`.
