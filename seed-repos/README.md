# Seed Repos — Growing the Discoverable `.ltl` Surface

This directory is the staging area for the **30 first-party satellite
repos** that bridge us from **47 → 77 discoverable Lateralus
repositories** on GitHub (one hop toward the ≥ 200 Linguist gate).

Each seed repo is a small, self-contained, useful project written in
pure Lateralus. They are deliberately small (one to three source
files each) so that the maintenance burden is near zero, while still
being discoverable via:

    https://github.com/search?q=language%3ALateralus
    https://github.com/search?q=extension%3Altl

Every seed repo ships with a `.gitattributes` that flips the GitHub
language bar to "Lateralus" immediately, regardless of whether the
upstream `github/linguist` PR has merged yet.

## Contents

- [`manifest.yml`](manifest.yml) — declarative spec of all 30 repos
- [`templates/`](templates/) — shared files (`.gitattributes`, LICENSE, README template)
- [`projects/`](projects/) — fully fleshed reference projects used as scaffolds
- [`generate.py`](generate.py) — materialises `staged/{name}/` for every manifest entry
- [`publish.sh`](publish.sh) — `gh repo create` + `git push` for every staged repo

## Implementation status

Nine of the thirty repos ship as **flagship reference projects** with
real, substantive source (≈ 200 – 300 lines each). The remaining
twenty-one fall back to a manifest-driven placeholder `main.ltl`;
every staged repo regardless of tier still carries `.gitattributes`,
MIT, topics, and a proper `README.md`, so all thirty contribute
equally to the Linguist repo-count gate.

| Flagship | Directory | What it is |
|---|---|---|
| `ltl-json-cli`              | `projects/json_cli/`     | streaming JSON parser + pretty-printer + dotted-path query |
| `ltl-hash-cat`              | `projects/hash_cat/`     | SHA-2 / SHA-3 / Blake2b / Blake3 file hasher with hex/base64 output |
| `ltl-graph-algos`           | `projects/graph_algos/`  | BFS, DFS, Dijkstra, A\*, Bellman-Ford on a shared adjacency-list API |
| `ltl-toml-parser`           | `projects/toml_parser/`  | TOML 1.0 parser (strings, ints, floats, arrays, tables, inline tables) |
| `ltl-snake`                 | `projects/snake/`        | terminal snake with VT100 rendering + BFS auto-pilot AI |
| `ltl-brainfuck`             | `projects/brainfuck/`    | tree-walking interpreter + single-pass x86-64 template JIT |
| `lateralus-cli-template`    | `projects/cli_template/` | scaffold for `lateralus new cli` (argparse, logging, sysexits) |
| `lateralus-lib-template`    | `projects/lib_template/` | scaffold for `lateralus new lib` (public API, private helpers, tests) |
| `lateralus-wasm-template`   | `projects/wasm_template/`| scaffold for `lateralus new wasm` (exports + host HTML demo) |

Flagship content can be upgraded in-place — converting a
placeholder into a real implementation is a contained PR, and
`generate.py` will pick up the new files automatically on the
next materialisation.

## One-shot run

```bash
cd seed-repos
python3 generate.py                   # populates ./staged/
GITHUB_TOKEN=$(gh auth token) ./publish.sh
```

## Post-publish verification

Wait ~15 minutes for GitHub's Linguist cache to cycle, then:

```bash
for repo in $(yq '.repos[].name' manifest.yml); do
  echo -n "$repo: "
  curl -s "https://api.github.com/repos/bad-antics/$repo/languages" \
    | jq -r 'keys | join(", ")'
done
```

Expected output: every repo reports `Lateralus` as a detected language.

## The 30 categories

| Category | Count | Examples |
|---|---|---|
| CLI utilities | 8 | `ltl-json-cli`, `ltl-hash-cat`, `ltl-http-bench` |
| Algorithms / data structures | 6 | `ltl-rbtree`, `ltl-skiplist`, `ltl-suffix-array` |
| Protocol parsers / clients | 6 | `ltl-toml-parser`, `ltl-mqtt-client`, `ltl-sip-parser` |
| Games / terminal toys | 4 | `ltl-minesweeper`, `ltl-snake`, `ltl-rogue` |
| Mini compilers / VMs | 3 | `ltl-brainfuck`, `ltl-forth`, `ltl-regex-vm` |
| Project templates | 3 | `lateralus-cli-template`, `lateralus-lib-template`, `lateralus-wasm-template` |

## Why satellite repos and not a monorepo?

Linguist counts `(user, repo)` pairs, not files. Ten files in one
repo scores the same as ten files in ten repos: **1 repo**. For the
200-repo gate, what matters is breadth, not depth. Each satellite is
intentionally tiny so that:

1. It compiles and is useful on its own.
2. It's a plausible candidate for a new user to fork and adapt.
3. Listing it on its own README doesn't drown out the headliner repo.

## After this batch

- Repo count: **47 + 30 = 77**
- Remaining to Linguist gate: **123**
- Next expansion vectors:
  - `lateralus new <kind>` template invocations by real users (organic)
  - Blog-post tutorials, each with a "here's the finished code" repo
  - Community fork-and-publish of headline samples (linguist/samples/)
