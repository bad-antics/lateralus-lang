# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/229
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] bug-report: chi_squared_pdf raises OverflowError at the mode of the distribution for k >= 344

### Lateralus version

3.2.0 (commit 4cb9147d4cd565a3d0fc22a190ed18f14077412f)

### Python version

CPython 3.12.10

### Operating System

Windows 11 (10.0.26200)

### Component

Standard Library, Python scientific computing API (`lateralus_lang/science.py`)

### Bug description

`chi_squared_pdf` raises `OverflowError` for valid inputs whose density is an ordinary representable float — including **at the mode of the distribution**.

The implementation computes three factors in the linear domain:

```python
return (x ** (half_k - 1) * math.exp(-x / 2)) / (2 ** half_k * math.gamma(half_k))
```

Two independent factors overflow before the quotient brings the result back into range:

1. `math.gamma(half_k)` raises `OverflowError: math range error` once `half_k >= 172`, i.e. `k >= 344`. (`math.gamma(171) = 7.257415615307998e+306`; `math.gamma(172)` overflows.)
2. `x ** (half_k - 1)` overflows for large `x` at moderate `k`.

At the mode of a chi-squared distribution (`x = k - 2`) the density is only `O(1/sqrt(k))`, so both failures replace an ordinary float with an exception.

### Reproduction code

Run from the repository root.

```sh
python3 -c 'from lateralus_lang.science import chi_squared_pdf; print(chi_squared_pdf(998.0, 1000))'
```

```python
from lateralus_lang.science import chi_squared_pdf
print(chi_squared_pdf(998.0, 1000))
```

### Expected behavior

`0.008928063487744038`

Verified with exact integer arithmetic and `Decimal` at 60 digits. `k` is even in each case below, so `gamma(k/2)` is an exact integer factorial and no floating-point intermediate is needed:

```python
from decimal import Decimal, getcontext
from math import factorial

getcontext().prec = 60

def exact_chi2_pdf(x: int, k: int) -> Decimal:
    h = k // 2
    num = Decimal(x) ** (h - 1) * (-Decimal(x) / 2).exp()
    den = Decimal(2) ** h * Decimal(factorial(h - 1))
    return num / den

print(exact_chi2_pdf(998, 1000))
```

| call | expected |
| --- | --- |
| `chi_squared_pdf(998.0, 1000)` | `0.008928063487744038` |
| `chi_squared_pdf(398.0, 400)` | `0.014134214138366241` |
| `chi_squared_pdf(198.0, 200)` | `0.020030735965664705` |
| `chi_squared_pdf(98.0, 100)` | `0.028447456653125969` |

### Actual behavior

```text
OverflowError: (34, 'Result too large')
```

Controls on the same distribution that stay below the threshold return the expected value, which isolates the overflow to the intermediate factors rather than to the input domain:

```python
chi_squared_pdf(98.0, 100)   # 0.028447456653125966   correct
chi_squared_pdf(198.0, 200)  # 0.02003073596566471    correct
chi_squared_pdf(1.0, 343)    # 0.0                    correct (true value underflows)
chi_squared_pdf(1.0, 344)    # OverflowError: math range error
```

The threshold is exactly the `math.gamma` limit:

```text
math.gamma(171) = 7.257415615307998e+306
math.gamma(172) -> OverflowError: math range error
```

Second, independent overflow path through `x ** (half_k - 1)`:

```python
chi_squared_pdf(1e6, 200)    # OverflowError: (34, 'Result too large')
chi_squared_pdf(10000.0, 300)  # OverflowError: (34, 'Result too large')
```

### Suggested fix

Evaluate in log space, which removes both magnitudes:

```python
def chi_squared_pdf(x: float, k: int) -> float:
    """Chi-squared probability density function."""
    if x <= 0:
        return 0.0
    half_k = k / 2
    return math.exp(
        (half_k - 1) * math.log(x)
        - x / 2
        - half_k * math.log(2)
        - math.lgamma(half_k)
    )
```

Measured against the exact table above (relative error):

| call | value | rel. error |
| --- | --- | --- |
| `(998.0, 1000)` | `0.008928063487747537` | `3.9e-13` |
| `(398.0, 400)` | `0.014134214138364125` | `1.5e-13` |
| `(198.0, 200)` | `0.020030735965663835` | `4.4e-14` |
| `(98.0, 100)` | `0.028447456653125765` | `7.2e-15` |
| `(10.0, 10)` | `0.0877336848839255` | `1.6e-15` |

`x <= 0` still returns `0.0`, and `(1e6, 200)` / `(10000.0, 300)` now return `0.0` (correct — those densities are below the smallest subnormal) instead of raising.

### Additional context

This is the same family as #226 (`poisson_pmf`) and #227 (`binomial_pmf`), but a separate function and a separate root cause: `poisson_pmf` overflows on `lam ** k`, `binomial_pmf` on the `math.comb` integer conversion, while `chi_squared_pdf` overflows inside `math.gamma`. Neither existing issue mentions `chi_squared_pdf`, and searching the repository for `chi_squared` at this commit returns only the implementation and its `bootstrap/v2_science.ltl` counterpart, so I believe this is unreported.

The `.ltl` copy at `bootstrap/v2_science.ltl#L437` calls `gamma_approx` (Stirling) and therefore does not hit this overflow; I have not audited its numerical accuracy here.

This report was produced with AI assistance and every value above was reproduced locally against commit `4cb9147`.

### Bounty

Could you confirm whether this qualifies for the published US$10 bug-report bounty and how you would like the claim recorded? `BOUNTIES.md` refers to `BOUNTIES-LOG.md`, which is absent from this revision.


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
- git commit -m "fix: [bounty] bug-report: chi_squared_pdf raises OverflowError at the mode of"
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
