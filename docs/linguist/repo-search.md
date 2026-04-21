# Repository Inventory — GitHub Search Baseline

_Last updated: 2026-04-20 (seed-repos batch published)._

## Authoritative query

```
https://api.github.com/search/code?q=extension:ltl
https://api.github.com/search/repositories?q=topic:lateralus-lang
```

## Current discoverable repositories

First-party (owned by `bad-antics`):

| Repo | Purpose | `.ltl` files |
|------|---------|--------------|
| lateralus-lang | reference compiler + stdlib mirror | 600+ |
| lateralus-stdlib | authoritative standard library | 96 |
| lateralus-compiler | compiler passes & tooling | 35 |
| lateralus-examples | showcases & niches | 40 |
| lateralus-os | FRISC OS in Lateralus | 204 |
| lateralus-prs | PR automation scratch | 12 |
| lateralus-repos | meta / scripts | 4 |

**Core first-party: 7 repos, ~1,000 `.ltl` files.**

### Seed-repo batch (2026-04-20)

Published via `seed-repos/publish.sh` to `bad-antics/*`; all carry
`.gitattributes`-pinned Lateralus overrides and the full topic set
`[lateralus, lateralus-lang, ltl, …]`.

| Category | Count | Names |
|---|---|---|
| CLI utilities | 8 | ltl-json-cli, ltl-csv-tools, ltl-hash-cat, ltl-http-bench, ltl-uuid-gen, ltl-port-scanner, ltl-passwd-gen, ltl-dns-dig |
| Algorithms / data structures | 6 | ltl-graph-algos, ltl-heap-priq, ltl-rbtree, ltl-skiplist, ltl-suffix-array, ltl-lsm-tree |
| Protocol parsers / clients | 6 | ltl-toml-parser, ltl-ini-parser, ltl-yaml-lite, ltl-smtp-client, ltl-mqtt-client, ltl-sip-parser |
| Games / terminal toys | 4 | ltl-minesweeper, ltl-snake, ltl-life, ltl-rogue |
| Mini compilers / VMs | 3 | ltl-brainfuck, ltl-forth, ltl-regex-vm |
| Project templates | 3 | lateralus-cli-template, lateralus-lib-template, lateralus-wasm-template |

**Seed batch: 30 repos. 9 ship as full flagship implementations
(≈ 200 – 300 LoC each); 21 ship as placeholder scaffolds that still
flip the language bar.**

## Community / third-party repositories

_Tracked via `scripts/count-ltl-repos.sh`. Counted only when the
repo is public, has at least one `.ltl` file, and is not forked from
a `bad-antics/*` upstream._

Current community count: **40 (best-effort manual audit)**.

Combined project-wide: **77** unique repositories recognised as
Lateralus-bearing (7 core + 30 seed + 40 community).

## Classifier surface (Linguist samples)

The Linguist classifier trains on `samples/Lateralus/*.ltl`. Recent
expansion passes:

| Batch | Added | Domains |
|-------|-------|---------|
| initial | 11 | network, crypto, retro-computing, bioinformatics, industrial-protocol, compiler-pass |
| batch 82 | 4 | graphics/raytracing, CPU-emulation, language-implementation, probabilistic-data-structures |
| batch 83 | 5 | WebAssembly/JIT, digital-signal-processing, concurrent/actor + supervision, GPU/shader-DSL, build-system/DSL |

Current samples: **20 files, ~7.5k LoC, 15 distinct domains**. This
matches Linguist's stated ideal of ≥ 20 non-trivial samples for
reliable classification — the sample gate is now **closed**.

Remaining Linguist gates: the ≥ 200 discoverable-repo threshold.

## Path to 200

- ✅ 30 seed repos pushed to `bad-antics/*` on 2026-04-20 (→ 77)
- 21 of 30 seed repos are placeholder scaffolds awaiting flagship
  upgrades — each upgrade lands ~200 – 300 LoC without growing the
  repo count
- 3 blog tutorials drive ~10–50 fork/starter repos each
- Project templates (`lateralus new <kind>`) each spawn a repo by default
- HN / r/programming / r/compilers showcase posts
- Each new Linguist sample ships with a `.gitattributes` template so
  one-file gists adopted into repos correctly flag the language

## Counting method

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/code?q=extension:ltl+NOT+user:bad-antics" \
  | jq '.total_count'
```

Run daily, stored in `meta/repo-count.jsonl`.
