# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/244
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] Interval(1, -1) drops the positive endpoint and permits division across zero

On Lateralus 3.2.0 at ed5b9eabd18f4ebdb0eaa8c765b7812f7c393ca3, reversing the endpoints of a nonempty interval discards its upper bound. This changes the result of dividing by an interval that contains zero. Reproduced with CPython 3.12.14 on macOS 26.5.2 (arm64).

```python
from lateralus_lang.math_engine import Interval

for bounds in [(-1, 1), (1, -1)]:
    divisor = Interval(*bounds)
    print(repr(divisor), divisor.contains(0))
    try:
        print(repr(Interval.exact(1) / divisor))
    except ZeroDivisionError as error:
        print(type(error).__name__, str(error))
```

Actual output:

```text
[-1, 1] True
ZeroDivisionError Interval division: divisor interval contains zero
[-1, -1] False
[-1.0, -1.0]
```

Both orders should produce the closed interval `[-1, 1]` and raise the same exception on division. In [Interval.__post_init__](https://github.com/bad-antics/lateralus-lang/blob/ed5b9eabd18f4ebdb0eaa8c765b7812f7c393ca3/lateralus_lang/math_engine.py#L455-L458), the first write overwrites the old upper endpoint before the second write reads it. Saving the original pair before either assignment preserves both values.

Submitted with AI assistance under the recurring $10 reproducible bug-report bounty in [BOUNTIES.md](https://github.com/bad-antics/lateralus-lang/blob/ed5b9eabd18f4ebdb0eaa8c765b7812f7c393ca3/BOUNTIES.md).


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
- git commit -m "fix: [bounty] Interval(1, -1) drops the positive endpoint and permits divisio"
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
