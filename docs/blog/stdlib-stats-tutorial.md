# Descriptive Statistics and Regression with `stdlib/stats.ltl`

Every data pipeline ends at the same question: *what does this distribution
actually look like?* `stdlib/stats.ltl` answers it with the classical
descriptive statistics — mean, median, mode, variance, percentiles — plus
the two-variable tools (covariance, correlation, linear regression) that
tell you whether two signals move together.

This tutorial walks the whole module on one small dataset, then a bivariate
example, with every number pinned by a runnable companion script
(`examples/stats_tutorial.ltl`) and a pytest regression suite.

---

## Setup: one dataset, every statistic

We use the classic eight-point dataset:

```text
data = [2, 4, 4, 4, 5, 5, 7, 9]
```

Small enough to verify by hand, irregular enough to exercise every code
path — including the even-count median branch and a repeated mode.

### Central tendency

- **`mean(data)`** — arithmetic average. Throws `ValueError` on empty
  input rather than silently returning 0, which is the correct failure
  mode: a missing dataset and a dataset of zeros are not the same thing.
- **`median(data)`** — middle value of the sorted copy; for even `n` it
  averages the two central order statistics. Unlike the mean, the median
  is robust to outliers: adding a `1000` to our dataset moves the mean to
  ~131 but leaves the median at 4.5.
- **`mode(data)`** — most frequent value. The implementation is a
  straightforward O(n²) count-everything pass; perfectly fine for the
  small-to-medium series this module targets, and worth knowing before you
  point it at a million-row event stream.

### Spread and shape

- **`variance(data)`** — *sample* variance (denominator `n − 1`, Bessel's
  correction). Dividing by `n` would systematically underestimate spread
  when the data is a sample of a larger population.
- **`stddev(data)`** — square root of the sample variance, back in the
  data's own units.
- **`range_val(data)`** — `max − min` in a single pass.
- **`percentile(data, p)`** — linear-interpolation percentile (the same
  method as NumPy's default): the index `p/100 · (n−1)` is split into
  floor/ceil neighbours and blended by the fractional part.
- **`quartiles(data)` / `iqr(data)`** — Q1, median, Q3 and the interquartile
  range `Q3 − Q1`. The IQR is the spread of the middle 50% of the data —
  the basis of the box plot and of outlier fences (`Q1 − 1.5·IQR` to
  `Q3 + 1.5·IQR`).

For our dataset the quartiles are `4.0 / 4.5 / 5.5`, giving `IQR = 1.5` —
half the data lives inside a single unit of spread, which the mean alone
would never reveal.

---

## Two variables: covariance, correlation, regression

```text
x = [1, 2, 3, 4, 5]
y = [2, 4, 5, 4, 5]
```

- **`covariance(x, y)`** — average product of deviations from each mean,
  again with the `n − 1` sample correction. Sign tells direction,
  magnitude is in `x·y` units — hard to interpret across datasets.
- **`correlation(x, y)`** — covariance normalised by both standard
  deviations, yielding a unitless `[-1, 1]` coefficient. Our example gives
  `0.7746`: a strong positive linear relationship. The implementation
  guards the degenerate case (a constant input has zero variance) by
  returning `0.0` rather than dividing by zero.
- **`linear_regression(x, y)`** — returns `[slope, intercept]` of the
  ordinary-least-squares fit `ŷ = slope·x + intercept`. Here
  `slope = 0.6`, `intercept = 2.2`: each unit increase in `x` predicts
  `+0.6` in `y`, anchored at `2.2` when `x = 0`.

---

## Running the companion script

`examples/stats_tutorial.ltl` mirrors the module's algorithms
self-contained (stdlib import resolution is bypassed so the script runs
anywhere `lateralus run` works) and prints pinned output:

```text
=== LATERALUS STDLIB STATS TUTORIAL ===
DATA: 2, 4, 4, 4, 5, 5, 7, 9
STEP 1: mean(data) = 5.0
STEP 2: median(data) = 4.5
STEP 3: mode(data) = 4
STEP 4: variance(data) [sample] = 4.571428571428571
STEP 5: stddev(data) = 2.138089935299395
STEP 6: range_val(data) = 7
STEP 7: quartiles Q1/median/Q3 = 4.0 / 4.5 / 5.5
STEP 8: iqr(data) = 1.5
STEP 9: covariance(x,y) = 1.5
STEP 10: correlation(x,y) = 0.7745966692414834
STEP 11: linear_regression slope/intercept = 0.6 / 2.2
PINNED_VECTORS: mean=5.0 median=4.5 mode=4 var=4.571428571428571 sd=2.138089935299395 range=7 q1=4.0 q3=5.5 iqr=1.5 cov=1.5 corr=0.7745966692414834 slope=0.6 intercept=2.2
```

Every number is deterministic — the only floating-point nondeterminism
would come from `sqrt`/`floor`/`ceil`, which are IEEE-754 exact for these
inputs — so `tests/test_stats_tutorial.py` can assert the entire transcript
verbatim.

## Gotchas worth knowing

- **Sample vs population**: `variance`, `covariance` and everything built
  on them use `n − 1`. If your "sample" is actually the whole population,
  multiply by `(n − 1) / n` to convert.
- **Empty input throws**: `mean`, `median`, `mode`, `range_val` and
  `percentile` all raise `ValueError` on empty data — check `len(data)`
  upstream if your pipeline can produce empty series.
- **Mode ties**: `mode` returns the *first* value achieving the maximum
  count in scan order, not necessarily the smallest — with
  `[1, 2, 2, 1]` it returns `2`, not `1`.
- **Correlation ≠ causation**, and `|r| ≈ 1` doesn't imply linearity is the
  right model — check a scatter before trusting the slope.

That is `stdlib/stats.ltl` end to end: fourteen public functions, one
coherent toolkit, and a runnable script that pins every formula so you can
verify the module's behaviour against your own numbers.
