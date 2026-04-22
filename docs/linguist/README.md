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
- `grammar_repo/` — **full standalone repo** staged for `bad-antics/lateralus-grammar` (MIT, `package.json`, `syntaxes/lateralus.tmLanguage.json`, `CHANGELOG.md`, `.gitattributes`)
- `scripts/sync-grammar-repo.sh` — mirrors `vscode-lateralus/syntaxes/*` into `grammar_repo/` with sanity checks
- `scripts/publish-grammar-repo.sh` — one-shot publisher: initialises git in a temp dir, force-pushes to `github.com/bad-antics/lateralus-grammar`, optionally tags a version
- `scripts/prepare-linguist-pr.sh` — clones your linguist fork, adds the submodule, patches `languages.yml`, copies samples, regenerates `grammars.yml`, and commits — ready for `gh pr create`
- `scripts/count-ltl-repos.sh` — nightly poll of the `extension:ltl` API, writes `meta/repo-count.jsonl`
- `pr-checklist.md` — Linguist PR body
- `repo-search.md` — current discoverable-repo inventory

## End-to-end workflow when the 200-repo bar is cleared

```bash
# 1. Keep grammar_repo in sync with the canonical VS Code grammar.
./scripts/sync-grammar-repo.sh

# 2. Publish the grammar to its own public repo (first time: use --create).
./scripts/publish-grammar-repo.sh --create --tag v1.0.0

# 3. Fork github-linguist/linguist; clone next to this repo.
gh repo fork github-linguist/linguist --clone=true

# 4. Scaffold the PR branch: submodule, languages.yml, samples, licenses.
LINGUIST_DIR=../linguist ./scripts/prepare-linguist-pr.sh

# 5. Run Linguist's tests (ruby env required).
cd ../linguist && bundle install && bundle exec rake samples && bundle exec rspec

# 6. Open the PR with the prepared body.
gh pr create --base main --head add-lateralus \
   --title "Add Lateralus language support" \
   --body-file ../lateralus-lang/docs/linguist/pr-checklist.md
```

## Files NOT in this package (lives elsewhere)

- `vscode-lateralus/` — full VS Code extension (already published)
- `lateralus-grammar` repo — the external submodule target

## Timeline

- 2026-04-20: grammar, samples, PR body staged
- 2026-04-21: `bad-antics/lateralus-grammar` repo published
- 2026-04-21: `.gitattributes` rolled out to all 30 `lateralus-*` repos
- 2026-05..: community adoption drive; file PR when repo count ≥ 200
