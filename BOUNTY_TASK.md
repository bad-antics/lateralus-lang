# Bounty Fix

**Reward:** $25.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/222
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] stdlib.strings tutorial — availability and payment inquiry

Hello maintainers,

I am interested in the recurring $25 stdlib tutorial listed in BOUNTIES.md, focusing on stdlib.strings. My issue search did not surface a tutorial claim for that module; please correct me if it is already assigned.

Proposed scope: a short tutorial with a runnable example against a pinned revision, expected outputs and boundary checks. No implementation or test results are being claimed.

Could you confirm whether this topic is available and the $25 sponsor-funded reward is currently payable; whether disclosed AI-assisted work with review and tests qualifies; and whether an individual resident and verified in mainland China can receive fiat payment through Ko-fi/PayPal, including any fees or onboarding requirements?

Please also clarify the weekly micro-bounty payment wording versus the general 14-days-after-merge rule.

This is an availability inquiry, not acceptance of a contract or a delivery commitment. I will wait for confirmation before substantial work or submitting a deliverable. Thank you.

---

## Process

### 1. Orient yourself first
Before touching any code:
- Read the README and any relevant docs
- Run: find . -type f | grep -v node_modules | grep -v .git | grep -v dist | head -60
- Grep for the key terms from the issue title to find the relevant files
- Read the files around the bug — understand what's currently happening

### 2. Find and read the tests
- Look for test files near the relevant code (*.test.ts, *.spec.js, __tests__, etc.)
- Read them — they tell you what behavior is expected
- Understand what a passing fix looks like before writing a line

### 3. Implement the fix
- Make the MINIMAL change that fixes the issue — nothing more
- Do not refactor, rename, reorganize, or clean up unrelated code
- Do not add dependencies unless the issue explicitly requires it
- Do not modify config files (package.json, tsconfig.json, etc.) unless that IS the fix
- One logical change, one commit

### 4. Verify
- Run the test suite: check package.json scripts for "test", "lint", "typecheck"
  Common commands: npm test, yarn test, pnpm test, pytest, go test ./..., cargo test
- If TypeScript is present: npx tsc --noEmit
- Fix any test failures your change caused — if a test was wrong before, update it

### 5. Commit and document
- git add -A
- git commit -m "fix: [bounty] stdlib.strings tutorial — availability and payment inquiry"
- Write AGENT_SUMMARY.md with:
  - Root cause: what was wrong and why
  - Fix: what you changed and the reasoning
  - Verification: how to confirm it works
  - Concerns: anything a reviewer should know

---

## Stop conditions

If ANY of these are true, write "UNCERTAIN: [reason]" at the top of AGENT_SUMMARY.md, make NO code changes, and stop:
- The fix requires changing more than ~5 files
- You cannot determine what the correct behavior should be
- The issue requires a database migration, API key, or external service
- You find 3+ open PRs already attempting this fix (high competition)
- The repo is not in a language/framework you can reason about confidently

A clean UNCERTAIN is better than a bad PR.
