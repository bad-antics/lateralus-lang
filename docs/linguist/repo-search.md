# Repository Inventory — GitHub Search Baseline

_Last updated: 2026-04-20._

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

**First-party total: 7 repos, ~1,000 `.ltl` files.**

## Community / third-party repositories

_Tracked via `scripts/count-ltl-repos.sh`. Counted only when the
repo is public, has at least one `.ltl` file, and is not forked from
a `bad-antics/*` upstream._

Current community count: **40 (best-effort manual audit)**.

Combined project-wide: **47** unique repositories recognised as
Lateralus-bearing at the time of this writing.

## Path to 200

- 30 unreleased internal repos scheduled for public push
- 3 blog tutorials drive ~10–50 fork/starter repos each
- Project templates (`lateralus new <kind>`) each spawn a repo by default
- HN / r/programming / r/compilers showcase posts

## Counting method

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/code?q=extension:ltl+NOT+user:bad-antics" \
  | jq '.total_count'
```

Run daily, stored in `meta/repo-count.jsonl`.
