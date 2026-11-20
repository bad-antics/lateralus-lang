# AGENT_SUMMARY — issue #242: `Dual.__pow__` returns `0.0` for constant-exponent derivatives

**Commit:** `819706d` on branch `fix/bounty-242`
**Files changed:** `lateralus_lang/math_engine.py` (2 lines), `tests/test_math_engine.py` (+26 lines)

## Root cause

In `Dual.__pow__` (`lateralus_lang/math_engine.py:565`) the derivative term was written as:

```python
d = v * (o.dot * math.log(abs(self.val)) if self.val != 0 else 0
         + o.val * self.dot / self.val if self.val != 0 else 0)
```

A conditional expression binds looser than `+`, so Python parsed this as one nested
conditional, not a sum of two guarded terms:

```python
d = v * ((o.dot * math.log(abs(self.val)))
         if self.val != 0
         else ((0 + o.val * self.dot / self.val) if self.val != 0 else 0))
```

For any non-zero base — i.e. every ordinary call — only the first branch was evaluated, so
the `o.val * self.dot / self.val` term (the `n·xⁿ⁻¹·ẋ` part of the power rule) was never
computed. With a constant exponent `o.dot == 0`, leaving the derivative exactly `0.0`.
`.val` was always correct, which is why `derivative()`, `gradient()` and the class
docstring example failed silently rather than raising.

The dead `else` branch is also unreachable: it only runs when `self.val == 0`, and it
divides by `self.val`, so had precedence been different it would have raised
`ZeroDivisionError`. The correct reading is the one the author intended — two
independently guarded terms that are added.

## Fix

Parenthesised each conditional so both terms are summed (the minimal diff, matching the
reporter's suggested fix):

```python
d = v * ((o.dot * math.log(abs(self.val)) if self.val != 0 else 0)
         + (o.val * self.dot / self.val if self.val != 0 else 0))
```

Nothing else was touched — no refactor, no new dependencies, no config changes. The
existing `self.val <= 0 and o.dot != 0` guard still correctly rejects a negative base with
a non-constant exponent, and a negative base with a *constant* exponent now works
(`Dual(-2.0, 1.0) ** 3 → Dual(-8.0, 12.0)`), because `o.dot == 0` zeroes the `log` term.

I also added four regression tests to `TestDual` — the suite had **no** coverage of
`Dual.__pow__` at all (every AD test used `x * x`), which is how this shipped.

## Verification

Reproduced the bug at `4cb9147` before changing anything (`0.0`, `0.0`, `[0.0, 0.0]`), then
re-measured every row of the issue's expected table after the fix:

| expression | expected | measured |
| --- | --- | --- |
| `derivative(lambda x: x**2, 3.0)` | `6.0` | `6.0` |
| `derivative(lambda x: x**3, 3.0)` | `27.0` | `27.0` |
| `derivative(lambda x: x**0.5, 3.0)` | `0.2886751345948129` | `0.28867513459481287` |
| `derivative(lambda x: x**x, 3.0)` | `56.66253179403897` | `56.66253179403897` |
| `derivative(lambda x: x**0, 3.0)` | `0.0` | `0.0` |
| `derivative(lambda x: x**1, 3.0)` | `1.0` | `1.0` |
| `gradient(lambda a, b: a**2 + b**2, [3.0, 4.0])` | `[6.0, 8.0]` | `[6.0, 8.0]` |
| `x**2 + 2*x + 1` at `x = Dual(3.0, 1.0)` | `Dual(16.0, 8.0)` | `Dual(16.0, 8.0)` |

Reproduce with:

```bash
python -m pytest tests/test_math_engine.py -q          # 46 passed (4 new)
python -m pytest tests/test_math_engine.py -q -k pow   # the 4 regression tests
```

The new tests were confirmed to be genuine regression tests: stashing only the
`math_engine.py` hunk makes all four fail (`0.0 != 6.0` etc.); restoring it makes them pass.

Full suite: **2037 passed, 26 failed, 3 skipped**. I captured the `FAILED` list before and
after the change and diffed them — **byte-identical**, so all 26 failures are pre-existing
and unrelated (law/mutation-tester tooling, `.ltl` example compilation, FFI
`FileNotFound`, and Windows `cp1252` `UnicodeEncodeError`s). No lint/typecheck step applies
to this file (`make lint` runs the Lateralus linter over `stdlib/`, not Python).

## Concerns for a reviewer

1. **`x**0.5` differs from the report by 1 ULP** — `0.28867513459481287` vs the reported
   `0.2886751345948129`. Both are `1/(2√3)`; the difference is float association in
   `v * (n/x)` vs a directly-computed reference. The test asserts
   `pytest.approx(1 / (2 * math.sqrt(3)))`, so it is not platform-sensitive.
2. **One documented "control" value legitimately changes.** The issue lists
   `Dual(3.0, 1.0) ** Dual(2.0, 1.0) → 9.0 + 9.887510598012987ε` as a case that "works".
   It now returns `15.88751059801299ε`. The old value was the *partial* result (missing
   term); `9·(ln 3 + 2/3) = 15.8875…` is the correct total derivative. Expected, not a
   regression.
3. **`self.val == 0` is still a hard `0.0` derivative.** `Dual(0.0, 1.0) ** 1` returns
   `Dual(0.0, 0.0)` where the true derivative is `1.0`. This is the pre-existing
   `if self.val != 0 else 0` guard, present before and after; fixing it would mean
   special-casing the exponent at zero base, which is beyond the scope of this issue.
4. **`newton_raphson` is *not* fixed by this change.** The issue's "additional context"
   suggests it would start using AD. It will not: the lambda it passes to `derivative`
   (`math_engine.py:736-738`) builds `Dual(f(d.val), d.dot * _numerical_deriv(f, d.val))`
   itself, so it computes central differences regardless of `__pow__` and never routes
   `f` through dual arithmetic. `fpx` is now non-zero earlier, so the
   `if fpx == 0` fallback at line 741 is hit less often, but the numbers are the same
   either way. Making `newton_raphson` genuinely use AD is a separate change and I left
   it alone.
5. `BOUNTY_TASK.md` and this file are left **uncommitted** on purpose — the commit is the
   fix plus its tests only, so the branch is clean to PR upstream.
