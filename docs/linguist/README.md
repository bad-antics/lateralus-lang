# Linguist Language Addition: Lateralus

This directory is the staging area for our upstream pull request to
[github/linguist](https://github.com/github-linguist/linguist) adding
**Lateralus** as a recognised programming language.

## Acceptance criteria (github-linguist/linguist CONTRIBUTING.md)

Linguist accepts a new language when it meets **all** of the following.
Status as of 2026-04-21:

| Requirement                                                  | Status | Evidence |
|--------------------------------------------------------------|--------|----------|
| Used in ≥ 200 unique `:user/:repo` repositories on GitHub    | ⏳ in progress | see `repo-search.md` — current count: **77** |
| TextMate grammar (or tree-sitter) with stable scope name     | ✅ done | `source.ltl`, shipped in [`lateralus.lateralus-lang` v3.1.0](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang) |
| File extension registered                                    | ✅ done | `.ltl` (plus `.ltasm`, `.ltlm`, `.ltlml`, `.ltlcfg`, `.ltlnb`) |
| Representative samples (≥ 10, ideally ≥ 20 non-trivial)      | ✅ done (ideal hit) | `samples/` — **20 files, 3,733 LoC, 15+ domains, 20/20 compile cleanly** |
| No ambiguity with existing languages on that extension       | ✅ done | `.ltl` is unclaimed in `languages.yml` |
| Grammar licensed MIT/Apache-2.0/similar                      | ✅ done | MIT |
| Follows Linguist PR checklist                                | ✅ done | see `pr-checklist.md` |

## The ≥ 200 repo bar

This is the only remaining gate. Our growth plan:

1. **Seed** — 30+ first-party `bad-antics/lateralus-*` repos (already live)
2. **Templates** — `cargo-generate`-style project templates published
3. **Library ecosystem** — stdlib + examples + grammar + LSP each public
4. **Third-party adoption** — tracked via the GitHub search query
   `language:Lateralus OR extension:ltl` once Linguist recognises it
   (bootstrapped via our own `.gitattributes`)
5. **Tutorials & showcases** — blog posts, YouTube screencasts, HN/r/prog

Counter script: `scripts/count-ltl-repos.sh` (hits the GitHub search
API once per hour, writes `repo-count.json`).

## Bridging the gap before merge

Every `bad-antics/*` repository that contains `.ltl` files carries a
`.gitattributes` entry:

    *.ltl linguist-language=Lateralus
    *.ltl linguist-detectable=true

GitHub's language bar on each repo will then display "Lateralus" even
before Linguist upstream merges — which also seeds the visibility loop.
After merge, these overrides stay put as a belt-and-braces fallback.

## Files in this package

- `meta/languages-yml-entry.yml` — proposed `languages.yml` patch
- `meta/heuristics-yml-entry.yml` — disambiguation heuristics (none needed; `.ltl` is unique)
- `samples/*.ltl` — 20 representative samples for Linguist's bayesian classifier
- `grammar_repo/` — contents staged for `bad-antics/lateralus-grammar`
- `pr-checklist.md` — Linguist PR body
- `repo-search.md` — current discoverable-repo inventory

## Files NOT in this package (lives elsewhere)

- `vscode-lateralus/` — full VS Code extension (already published)
- `lateralus-grammar` repo — the external submodule target

## Timeline

- 2026-04-20: grammar, samples, PR body staged
- 2026-04-21: `bad-antics/lateralus-grammar` repo published
- 2026-04-21: `.gitattributes` rolled out to all 30 `lateralus-*` repos
- 2026-05..: community adoption drive; file PR when repo count ≥ 200
