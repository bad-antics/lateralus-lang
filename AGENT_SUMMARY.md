# Bounty #244 — `Interval(1, -1)` drops the positive endpoint

## Root cause

`Interval` is a frozen dataclass, so `__post_init__` normalized reversed
endpoints via `object.__setattr__` (`lateralus_lang/math_engine.py:455`):

```python
if self.lo > self.hi:
    object.__setattr__(self, "lo", min(self.lo, self.hi))
    object.__setattr__(self, "hi", max(self.lo, self.hi))
```

The two writes are sequential, and the second one re-reads `self.lo` *after*
the first write has already clobbered it. For `Interval(1, -1)`:

1. `lo = min(1, -1) = -1` — the original `lo` value `1` is now gone.
2. `hi = max(self.lo, self.hi) = max(-1, -1) = -1` — reads the new `lo`.

Result: `[-1, -1]` instead of `[-1, 1]`. The upper endpoint is silently
discarded, which is a soundness break for an enclosure-arithmetic type: the
returned interval no longer contains the values the caller specified.

The division symptom follows from that. `__truediv__` guards with
`other.lo <= 0 <= other.hi`; the collapsed `[-1, -1]` no longer straddles
zero, so `Interval.exact(1) / Interval(1, -1)` returned `[-1.0, -1.0]` where
`Interval.exact(1) / Interval(-1, 1)` correctly raised `ZeroDivisionError`.
Every derived property was affected the same way — `width`, `mid`, `radius`,
`contains`, `overlaps`, and all the arithmetic operators read the corrupted
endpoints.

Only intervals constructed with `lo > hi` were affected; the `if` guard means
correctly-ordered construction never entered the buggy branch, which is why
the existing tests passed.

## Fix

`lateralus_lang/math_engine.py` — bind the original pair to locals before
either write, so `max` can't observe the mutated field:

```python
if self.lo > self.hi:
    lo, hi = self.lo, self.hi
    object.__setattr__(self, "lo", min(lo, hi))
    object.__setattr__(self, "hi", max(lo, hi))
```

This is exactly the fix the issue suggests. Three lines, same branch, no
behavior change for already-ordered intervals. I deliberately did not
restructure `__post_init__` (e.g. to always normalize unconditionally, or to
validate NaN endpoints) — out of scope for this bounty.

`tests/test_math_engine.py` — added `TestInterval::test_reversed_endpoints_are_normalized`,
which pins both the endpoint normalization and the division guard that the
issue reports.

Grepped for other copies of this pattern: `class Interval` and
`min(self.lo, self.hi)` each appear exactly once in the repo, so there is no
duplicated implementation to fix alongside it.

## Verification

The issue's reproducer now gives identical output for both orderings:

```
$ python - <<'PY'
from lateralus_lang.math_engine import Interval
for bounds in [(-1, 1), (1, -1)]:
    divisor = Interval(*bounds)
    print(repr(divisor), divisor.contains(0))
    try:
        print(repr(Interval.exact(1) / divisor))
    except ZeroDivisionError as error:
        print(type(error).__name__, str(error))
PY
[-1, 1] True
ZeroDivisionError Interval division: divisor interval contains zero
[-1, 1] True
ZeroDivisionError Interval division: divisor interval contains zero
```

Other spot checks: `Interval(2, -3)` → `[-3, 2]` (width `5`, mid `-0.5`),
`Interval(4, 1) * Interval(3, 2)` → `[2, 12]`, `Interval(5, 5)` → `[5, 5]`.

- `python -m pytest tests/test_math_engine.py -q` → **43 passed**.
- `python -m ruff check` on both changed files → **All checks passed**.
- Full suite: `python -m pytest -q` → **2034 passed, 3 skipped, 26 failed**.

Those 26 failures are pre-existing and unrelated. I confirmed this by
`git stash`-ing the change and re-running the same ten test files: the
identical 26 fail on the untouched tree. They are environmental — Windows
`cp1252` `UnicodeEncodeError` on emitted Unicode (`test_law_relate`,
`test_law_triangulate`), and a missing C toolchain / `FileNotFoundError` for
the codegen and FFI tests (`test_v19_features`, `test_v23_features`). None
touch `math_engine`.

## Concerns

- Ran on Python 3.14 / Windows, not the issue reporter's CPython 3.12 on
  macOS. The fix is plain Python with no platform- or version-sensitive
  behavior, and the reproducer output matches the expected result, so I don't
  consider this a risk — but the 26 pre-existing failures above are a local
  environment artifact and should be green in CI.
- Anything previously relying on the collapsed-interval behavior changes:
  dividing by a reversed interval that spans zero now raises
  `ZeroDivisionError` instead of returning a wrong-but-quiet result. That is
  the point of the bounty, but it is technically a behavior change for such
  callers.
- `__post_init__` still does nothing about NaN endpoints — `NaN` comparisons
  are always false, so `Interval(float('nan'), 0)` skips normalization
  entirely. Pre-existing and unrelated to this issue; flagging it, not fixing
  it here.
- `BOUNTY_TASK.md` is left untracked, as it was at the start. The commit
  contains only the two source changes.
