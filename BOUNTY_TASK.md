# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/227
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] bug-report: binomial_pmf overflows for 550 successes in 1,100 trials

### Lateralus version

3.2.0, commit `4cb9147d4cd565a3d0fc22a190ed18f14077412f`

### Python version and platform

Reproduced with CPython 3.13.5 and 3.14.0 on macOS arm64.

### Component

Standard Library, Python scientific computing API.

### Bug description

`binomial_pmf(550, 1100, 0.5)` raises `OverflowError` for a valid binomial distribution. This is the probability of exactly 550 heads in 1,100 fair coin flips. The result is about 2.4% and fits in a float.

### Reproduction

Run from the repository root.

```sh
python3 -c 'from lateralus_lang.science import binomial_pmf; print(binomial_pmf(550, 1100, 0.5))'
```

### Expected behavior

Return approximately `0.024051657768231812`. For a fair coin, the exact probability is the binomial coefficient divided by 2 raised to the number of trials. This gives a reference without intermediate floating-point arithmetic.

```python
from fractions import Fraction
from math import comb

print(float(Fraction(comb(1100, 550), 2**1100)))
```

### Actual behavior

```text
OverflowError: int too large to convert to float
```

The [implementation](https://github.com/bad-antics/lateralus-lang/blob/4cb9147d4cd565a3d0fc22a190ed18f14077412f/lateralus_lang/science.py#L364-L366) multiplies the large integer from `math.comb` by a float. That converts the integer to a float before either probability factor can scale it down. A smaller control, `binomial_pmf(500, 1000, 0.5)`, returns the expected `0.0252250181783608`.

This report concerns the binomial implementation. [#226](https://github.com/bad-antics/lateralus-lang/issues/226) concerns a separate overflow in the Poisson implementation.

### Bounty

This AI-assisted report was verified locally with both Python versions above. Could you confirm whether it qualifies for the published $10 bug-report bounty and how you would like the claim recorded? `BOUNTIES.md` refers to `BOUNTIES-LOG.md`, which is absent from this revision.


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
- git commit -m "fix: [bounty] bug-report: binomial_pmf overflows for 550 successes in 1,100 t"
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
