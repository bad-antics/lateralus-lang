# Bounties Log

Claims against the recurring micro-bounties in `BOUNTIES.md`. Entries are
original work, MIT-licensed, copyright the contributor.

## $25 — stdlib module tutorial

| Module | Deliverable | Claimed by | Date | Status |
|---|---|---|---|---|
| `stdlib.grugbot.thesaurus` | `docs/blog/thesaurus-synonym-filtering.ltlml` + `examples/thesaurus_synonyms.ltl` | Zwk-tech | 2026-11-27 | Submitted (issue #1030) |

### Notes

- **issue #1030** — tutorial for `stdlib.grugbot.thesaurus`: synonym lookup and
  negative-inhibition filtering, with a runnable example pinned to the expected
  output `["quick", "rapid"]`.
- The runnable example is self-contained (the relevant slice of the module is
  inlined) so it runs on the Python backend without stdlib-import inlining.
  Its two `@test` vectors pass; running it prints `['quick', 'rapid']`.
- MIT licensed, original work.
