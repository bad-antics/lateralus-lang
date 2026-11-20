# AGENT_SUMMARY — issue #229: `chi_squared_pdf` OverflowError

## Root cause

`lateralus_lang/science.py:369` evaluated the chi-squared density entirely in the
linear domain:

```python
return (x ** (half_k - 1) * math.exp(-x / 2)) / (2 ** half_k * math.gamma(half_k))
```

Both the numerator and the denominator can exceed the float range even when the
quotient — the actual density — is an ordinary float. Two independent paths:

1. `math.gamma(half_k)` raises `OverflowError: math range error` once
   `half_k >= 172`, i.e. `k >= 344` (`math.gamma(171) = 7.257e+306` is the last
   representable value).
2. `x ** (half_k - 1)` raises `OverflowError: (34, 'Result too large')` for large
   `x` at moderate `k` (e.g. `x = 1e6, k = 200`).

At the mode of the distribution, `x = k - 2`, the density is only `O(1/sqrt(k))`,
so the function raised instead of returning a perfectly representable number.
Reproduced on this commit before the change:

```
(98.0, 100)    -> 0.028447456653125966   ok
(198.0, 200)   -> 0.02003073596566471    ok
(398.0, 400)   -> OverflowError (34, 'Result too large')
(998.0, 1000)  -> OverflowError (34, 'Result too large')
(1.0, 344)     -> OverflowError math range error
(1e6, 200)     -> OverflowError (34, 'Result too large')
```

## Fix

`lateralus_lang/science.py` — evaluate the density in log space and exponentiate
once, using `math.lgamma` in place of `math.gamma`. No intermediate value leaves
float range, because the log-domain sum is the log of the final result:

```python
return math.exp(
    (half_k - 1) * math.log(x)
    - x / 2
    - half_k * math.log(2)
    - math.lgamma(half_k)
)
```

This is the fix suggested in the issue. The `x <= 0 -> 0.0` guard is untouched,
so `math.log(x)` is only reached for `x > 0`. Cases whose true density is below
the smallest subnormal now return `0.0` via `math.exp` underflow instead of
raising — consistent with the pre-existing behaviour of `chi_squared_pdf(1.0, 343)`,
which already returned `0.0`.

`tests/test_science.py` — added three regression tests to `TestDistributions`:
the `k = 2` closed form plus the `x <= 0` guard, the four mode values from the
issue's exact table (relative tolerance `1e-11`), and the former second-path
overflow inputs now returning `0.0`.

Two files changed, 8 insertions in the library. No refactoring, no new
dependencies, no config changes.

## Verification

Values match the issue's exact table, cross-checked here against independent
`Decimal`(60-digit)/`factorial` arithmetic:

| call | returned | exact | rel. error |
| --- | --- | --- | --- |
| `(998.0, 1000)` | `0.008928063487747537` | `0.008928063487744038` | `3.9e-13` |
| `(398.0, 400)` | `0.014134214138364125` | `0.014134214138366241` | `1.5e-13` |
| `(198.0, 200)` | `0.020030735965663835` | `0.020030735965664705` | `4.4e-14` |
| `(98.0, 100)` | `0.028447456653125765` | `0.028447456653125969` | `7.2e-15` |
| `(10.0, 10)` | `0.0877336848839255` | `0.08773368488392536` | `1.6e-15` |

Former overflow inputs: `(1.0, 344) -> 0.0`, `(1e6, 200) -> 0.0`,
`(10000.0, 300) -> 0.0`. Guards: `(0.0, 3) -> 0.0`, `(-1.0, 3) -> 0.0`.
Midpoint-rule integration as a sanity check on normalisation:
`k = 5` over `(0, 60]` gives `1.0000000000571`, and `k = 1000` over `(800, 1200]`
gives `0.99998693`.

Commands run from the repo root:

```sh
python -m pytest tests/test_science.py -q     # 47 passed (44 before, +3 new)
ruff check lateralus_lang/science.py tests/test_science.py   # All checks passed
python -m pytest tests/ -q                    # 26 failed, 2036 passed, 3 skipped
```

The 26 failures are pre-existing. I captured the `FAILED` lines with the change
stashed and unstashed and diffed them — the two sets are byte-identical (they are
`.ltl` compile/FFI/law-engine tests unrelated to `science.py`). Full suite passes
go from 2033 to 2036, exactly the three added tests. Local run used CPython 3.14;
CI covers 3.10–3.13 and the change uses only long-stable `math` functions.

## Concerns for a reviewer

- **Last-digit drift on the small-`k` path.** Log-space evaluation changes the
  rounding of already-working inputs in the last 1–2 ULP (e.g. `(98.0, 100)`
  moves from `...125966` to `...125765`, both ~`1e-14` relative from exact; the
  new value is *closer* to exact for `(10.0, 10)` and marginally farther for
  `(98.0, 100)`). No existing test asserted on `chi_squared_pdf`, and nothing
  else in the repo calls it, so nothing breaks — but any downstream exact-equality
  comparison would see a different final digit. The issue's expected-value table
  is quoted to full precision and my tests use a relative tolerance of `1e-11`
  rather than exact equality for that reason.
- **Negative odd `k` degenerates differently.** For `k < 0` with `half_k`
  non-integral (e.g. `k = -1`), `math.gamma` returned a negative value while
  `math.lgamma` returns `log|gamma|`, dropping the sign — so the result flips
  positive. These inputs are outside the chi-squared domain (`k >= 1`), the
  function has never validated `k`, and the issue does not raise it; I left the
  input-validation question alone to keep the change minimal. `k = 0` still
  raises `ValueError: math domain error`, same as before.
- **Not changed: the `.ltl` counterpart.** `bootstrap/v2_science.ltl:437` has a
  parallel `chi_squared_pdf` built on a Stirling `gamma_approx`. As the issue
  notes, it does not hit this overflow, so I left it untouched; its numerical
  accuracy is unaudited here.
- **Sibling bugs still open.** `poisson_pmf` (`lam ** k`, #226) and
  `binomial_pmf` (`math.comb`, #227) in the same file have the same family of
  overflow, and are untouched here — separate issues, separate root causes.
- **Bounty bookkeeping.** The reporter asks how to record the claim and notes
  `BOUNTIES.md` points at an absent `BOUNTIES-LOG.md`. That is a maintainer
  decision, not a code change; I did not create or modify either file.
