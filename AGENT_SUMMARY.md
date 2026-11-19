# Agent Summary — issue #222

**Scope note:** this issue is a contributor *inquiry*, not a bug report. Only part of
it is answerable from the repository. I fixed the part that is a genuine, verifiable
repo defect and deliberately left the maintainer/legal questions alone. See
"Left unanswered" below.

## Root cause

The reporter's two repo-answerable complaints both trace to self-contradictions in
`BOUNTIES.md`:

1. **"My issue search did not surface a tutorial claim for that module."**
   `BOUNTIES.md:133` told micro-bounty claimants to "Drop them in `BOUNTIES-LOG.md`
   when claimed", but that file has **never existed** in the repository — confirmed
   with `git log --all --diff-filter=A -- BOUNTIES-LOG.md` (empty) and a repo-wide
   grep showing exactly one reference, the instruction itself. Meanwhile
   `BOUNTIES.md:10-11` defines a different mechanism for the larger bounties: open
   an issue titled `[bounty] <name>`. Two conflicting claim mechanisms, one of them
   pointing into the void, so micro-bounty claims had no discoverable home. A
   contributor searching the issue tracker for a claim would correctly find nothing
   and still not know whether the topic was taken.

2. **"Clarify the weekly micro-bounty payment wording versus the 14-days-after-merge rule."**
   `BOUNTIES.md:133` said "we'll review and pay weekly"; rule 5 said "Payment is in
   14 days of merge." These are mutually exclusive payment terms for the same work.

## Fix

One file, two hunks, documentation only (`BOUNTIES.md`):

- Replaced the `BOUNTIES-LOG.md` instruction with the mechanism the document already
  defines for every other bounty — open an issue titled `[bounty] <name>` before
  starting — so claim status is visible in an issue-tracker search, which is exactly
  what the reporter tried.
- Made rule 5 the single payment term ("Payment is sent within 14 days of merge.
  This applies to every bounty, including the recurring micro-bounties"), and
  narrowed the micro-bounty line to what it can non-contradictorily promise: weekly
  *review*.

Reasoning on which timing wins: rule 5 is the general, numbered term under "Rules in
a nutshell" and governs all bounties; "pay weekly" was a trailing clause on a bullet
list scoped to one section. Harmonizing to rule 5 preserves the stated general
policy rather than inventing a new one. "in 14 days" was also reworded to "within
14 days" — the natural reading, and the ambiguity the reporter asked about.

No new files, no new process, no dependency or config changes.

## Verification

- `python -m pytest tests/ -q` → **26 failed, 2033 passed, 3 skipped**.
- Confirmed pre-existing, not caused by this change: stashed the edit, re-ran on a
  clean tree, got the **identical** 26 failed / 2033 passed / 3 skipped. The failures
  are in law/mutation/stdlib-compile suites (`test_stdlib_laws`, `test_law_*`,
  `test_mutation_tester`, `test_v18/v19/v23_features`) and are unrelated to
  documentation. The change is markdown-only and cannot affect them.
- `grep -rn "BOUNTIES-LOG" --include=*.md .` → no remaining dangling reference.
- Checked compliance with the repo's mandatory no-box-drawing policy
  (`CONTRIBUTING.md`): scanned U+2500–U+257F in `BOUNTIES.md` → none.
- `git diff` confirmed scoped to the two intended hunks, with no line-ending churn.

## Left unanswered (deliberate)

Three of the reporter's questions are **not determinable from the repository** and I
did not invent answers for them. They need a maintainer reply on the issue:

- **Is the $25 currently payable / is the topic assigned?** Depends on sponsor
  revenue and the issue tracker's live state, neither visible here.
- **Does disclosed AI-assisted work qualify?** The repo has **no** AI-assistance
  policy anywhere — grep for `ai-assisted`/`llm`/`copilot` across the docs returns
  only unrelated GrugBot marketing copy. This is an unwritten policy decision, not a
  documentation bug I can fix.
- **Can a mainland-China resident receive fiat via Ko-fi/PayPal, and at what fees?**
  A third-party-processor compliance question. I cannot and should not answer it.

## Concerns for a reviewer

- **This fix does not answer the issue.** It removes the documentation defects that
  *caused* two of the five questions. The issue should stay open until a maintainer
  answers the payability, AI-policy, and payment-rail questions directly.
- **Ko-Fi is advertised with no account behind it.** `BOUNTIES.md:3-4` offers "GitHub
  Sponsors, Ko-Fi, or BTC/LN", but `.github/FUNDING.yml` contains only
  `github: bad-antics` and a custom lateralus.dev link — no `ko_fi:` entry, and no
  Ko-fi handle appears anywhere in the repo. PayPal is never mentioned by the project
  at all; the reporter introduced that term. I left this untouched because a Ko-fi
  account may exist off-repo and I can't verify either way, but it is likely the
  next thing to correct and is directly relevant to the reporter's question.
- **An alternative fix was available:** create `BOUNTIES-LOG.md` and keep the
  two-track process. I chose consolidation instead because it adds no new process and
  matches the mechanism the document already leads with — but if maintainers
  intended a separate ledger, this hunk should be reverted in favor of adding
  that file.
- The commit is not signed off; rule 2 requires `git commit -s` for bounty
  submissions. Add `-s` on amend if this is submitted as a bounty claim.
