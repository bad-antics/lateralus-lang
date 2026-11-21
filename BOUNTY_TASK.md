# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/79
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] bug-report: semver.compare reverses numeric prerelease precedence

### Lateralus version

3.2.0 (main 23c757ab564d685dc8701fe0846bc109cd3166e3)

### Python version

Python 3.12.14

### Operating System

Linux

### Component

Standard Library

### Bug description

## Bounty claim and bug report

Submitting this reproducible correctness bug for the **$10 high-signal bug-report micro-bounty** advertised in [BOUNTIES.md](https://github.com/bad-antics/lateralus-lang/blob/23c757ab564d685dc8701fe0846bc109cd3166e3/BOUNTIES.md). This is the claim/report itself, before undertaking a production fix. Please confirm acceptance and any BOUNTIES-LOG.md follow-up needed; no payment or assignment is assumed.

Prepared and executed with OpenAI Codex assistance under this GitHub account.

## Problem

`stdlib/semver.ltl` documents Semantic Versioning 2.0.0 but `compare()` compares whole prerelease strings lexicographically. It therefore reverses numeric identifier ordering: `1.0.0-beta.2` sorts **above** `1.0.0-beta.11`.

It also fails the numeric-versus-nonnumeric rule: the valid prerelease identifier `1` must sort below the valid nonnumeric identifier `-`, even though ASCII comparison gives the opposite result.

This affects `lt`, `gt`, `lte`, and `gte`, which delegate to `compare`. Consumers using these helpers to choose the newest prerelease can choose the older version.

## Environment

- Upstream main: `23c757ab564d685dc8701fe0846bc109cd3166e3`
- Lateralus 3.2.0
- Python 3.12.14
- Linux x86_64
- No third-party dependencies required for this reproduction.

## Minimal reproduction

Run from the repository root:

```sh
python - <<'PY'
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

result = Compiler().compile_source(
    Path("stdlib/semver.ltl").read_text(),
    target=Target.PYTHON,
)
assert result.ok
namespace = {"__name__": "semver_repro"}
exec(result.python_src, namespace)

# Documented version-list representation:
# [major, minor, patch, prerelease_str, build_str].
print(namespace["compare"](
    [1, 0, 0, "beta.2", ""],
    [1, 0, 0, "beta.11", ""],
))
PY
```

**Actual:** `1`. **Expected:** `-1`.

This compiles and runs the actual, unmodified stdlib module with the project's Python backend; it does not reimplement the comparator in Python. It passes documented version lists directly, so it tests comparison independently of parsing/import resolution. No native C, JavaScript or VM behavior is claimed.

## Extended reproduction

Replace the final print above with:

```python
cases = [
    ("beta.2", "beta.11", -1),
    ("beta.11", "beta.2", 1),
    ("alpha.9", "alpha.10", -1),
    ("1", "-", -1),
    ("alpha", "alpha.1", -1),
    ("alpha.1", "alpha.beta", -1),
    ("beta", "beta.2", -1),
    ("rc.1", "", -1),
    ("", "rc.1", 1),
    ("beta.2", "beta.2", 0),
]
for a, b, expected in cases:
    actual = namespace["compare"]([1, 0, 0, a, ""], [1, 0, 0, b, ""])
    print(
        f'{"PASS" if actual == expected else "FAIL"} '
        f'{a!r} vs {b!r}: got={actual}, expected={expected}'
    )
```

Observed output:

```text
FAIL 'beta.2' vs 'beta.11': got=1, expected=-1
FAIL 'beta.11' vs 'beta.2': got=-1, expected=1
FAIL 'alpha.9' vs 'alpha.10': got=1, expected=-1
FAIL '1' vs '-': got=1, expected=-1
PASS 'alpha' vs 'alpha.1': got=-1, expected=-1
PASS 'alpha.1' vs 'alpha.beta': got=-1, expected=-1
PASS 'beta' vs 'beta.2': got=-1, expected=-1
PASS 'rc.1' vs '': got=-1, expected=-1
PASS '' vs 'rc.1': got=1, expected=1
PASS 'beta.2' vs 'beta.2': got=0, expected=0
```

Result: **6 passing controls and 4 failures**.

## Expected rule and root cause

[SemVer 2.0.0 section 11](https://semver.org/#spec-item-11) compares dot-separated prerelease identifiers individually: numeric identifiers numerically, numeric below nonnumeric, nonnumeric lexically, then length if all shared identifiers match. Its published ordering explicitly places beta.2 before beta.11.

The branch beginning `// Both have pre-release, compare lexicographically` compares `a_pre` and `b_pre` as entire strings instead. A correction should split on dots and apply the per-identifier rules while retaining the current stable-release and major/minor/patch behavior.

A repository-wide issue/PR search for `semver` returned no matches at submission preparation time. This report concerns prerelease comparison only, not parser validation or version-range semantics.


### Reproduction code

```lateralus
See the executable Python-backend harness in the description. It compiles the unmodified stdlib/semver.ltl and calls compare([1, 0, 0, "beta.2", ""], [1, 0, 0, "beta.11", ""]).
```

### Expected behavior

Return -1: beta.2 precedes beta.11 under SemVer 2.0.0 section 11. Numeric prerelease identifiers must be compared numerically.

### Actual behavior

```shell
Returns 1. The full observed output in the description shows four failures and six passing controls.
```

### Additional context

_No response_

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
- git commit -m "fix: [bounty] bug-report: semver.compare reverses numeric prerelease preceden"
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
