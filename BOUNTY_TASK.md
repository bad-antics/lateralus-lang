# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/242
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] bug-report: Dual.__pow__ returns 0.0 for every constant-exponent derivative (derivative/gradient silently wrong)

### Lateralus version

3.2.0 (commit 4cb9147d4cd565a3d0fc22a190ed18f14077412f)

### Python version

CPython 3.12.10

### Operating System

Windows 11 (10.0.26200)

### Component

Standard Library, `math_engine` — forward-mode automatic differentiation (`Dual`)

### Bug description

`Dual.__pow__` returns a **wrong derivative** (no exception) for every power with a constant exponent. `derivative(lambda x: x**2, 3.0)` returns `0.0` instead of `6.0`, and `gradient(lambda a, b: a**2 + b**2, [3.0, 4.0])` returns `[0.0, 0.0]` instead of `[6.0, 8.0]`.

The cause is operator precedence in this expression (`math_engine.py`, `Dual.__pow__`):

```python
v = self.val ** o.val
d = v * (o.dot * math.log(abs(self.val)) if self.val != 0 else 0
         + o.val * self.dot / self.val if self.val != 0 else 0)
return Dual(v, d)
```

A conditional expression binds looser than `+`, so this parses as:

```python
d = v * (
        (o.dot * math.log(abs(self.val)))
        if self.val != 0
        else ((0 + o.val * self.dot / self.val) if self.val != 0 else 0)
    )
```

For any non-zero base — every ordinary call — only the first branch is evaluated and the term `o.val * self.dot / self.val` is never computed. With a constant exponent `o.dot == 0`, the derivative therefore collapses to exactly `0.0`.

The class docstring documents the behaviour that is not delivered:

```python
x = Dual(3.0, 1.0)      # f(x) at x=3, ∂/∂x
result = x**2 + 2*x + 1  # → Dual(16.0, 8.0)
```

### Reproduction code

```python
from lateralus_lang.math_engine import Dual, derivative, gradient

print(derivative(lambda x: x**2, 3.0))
print(derivative(lambda x: x**3, 3.0))
print(gradient(lambda a, b: a**2 + b**2, [3.0, 4.0]))
```

### Expected behavior

```text
6.0
27.0
[6.0, 8.0]
```

`d/dx x**n = n * x**(n-1)`, so at `x = 3`: `x**2 -> 6`, `x**3 -> 27`, `x**0.5 -> 0.2886751345948129`.

The documented example should match the docstring:

```python
x = Dual(3.0, 1.0)
print(x**2 + 2*x + 1)   # Dual(16.0, 8.0)
```

### Actual behavior

```text
0.0
0.0
[0.0, 0.0]
```

| expression | expected | actual |
| --- | --- | --- |
| `derivative(lambda x: x**2, 3.0)` | `6.0` | `0.0` |
| `derivative(lambda x: x**3, 3.0)` | `27.0` | `0.0` |
| `derivative(lambda x: x**0.5, 3.0)` | `0.2886751345948129` | `0.0` |
| `gradient(lambda a, b: a**2 + b**2, [3.0, 4.0])` | `[6.0, 8.0]` | `[0.0, 0.0]` |
| `(Dual(3.0, 1.0)**2) + 2*Dual(3.0, 1.0) + 1` | `Dual(16.0, 8.0)` | `Dual(16.0, 2.0)` |

The value (`.val`) is always correct; only the derivative (`.dot`) is wrong, which is why this fails silently.

Controls that do work, which isolate the fault to `__pow__` rather than to the AD plumbing:

```python
derivative(lambda x: x * x, 3.0)        # 6.0     correct
derivative(lambda x: 2 * x + 1, 3.0)    # 2.0     correct
Dual(3.0, 1.0) ** Dual(2.0, 1.0)        # 9.0 + 9.887510598012987ε   correct
```

The third case works because a non-constant exponent takes the first branch, where `o.dot != 0` makes the surviving term non-zero.

### Suggested fix

Parenthesise each conditional so both terms are added (minimal diff):

```python
    def __pow__(self, other):
        o = _as_dual(other)
        if self.val <= 0 and o.dot != 0:
            raise ValueError("Dual pow: negative base with non-constant exponent")
        v = self.val ** o.val
        d = v * ((o.dot * math.log(abs(self.val)) if self.val != 0 else 0)
                 + (o.val * self.dot / self.val if self.val != 0 else 0))
        return Dual(v, d)
```

Measured after the change:

| expression | result |
| --- | --- |
| `derivative(lambda x: x**2, 3.0)` | `6.0` |
| `derivative(lambda x: x**3, 3.0)` | `27.0` |
| `derivative(lambda x: x**0.5, 3.0)` | `0.2886751345948129` |
| `derivative(lambda x: x**x, 3.0)` | `56.66253179403897` (= `27 * (log 3 + 1)`) |
| `derivative(lambda x: x**0, 3.0)` | `0.0` |
| `derivative(lambda x: x**1, 3.0)` | `1.0` |
| `x**2 + 2*x + 1` at `x = Dual(3.0, 1.0)` | `Dual(16.0, 8.0)` |
| `gradient(lambda a, b: a**2 + b**2, [3.0, 4.0])` | `[6.0, 8.0]` |

### Additional context

This also degrades `newton_raphson` in the same module: its default differentiation path calls `derivative(...)` (line 736), gets `0.0`, and then falls through to `if fpx == 0: fpx = _numerical_deriv(f, x)` (lines 740-741). Newton-Raphson still converges because of that fallback, but it silently runs on central differences instead of the advertised automatic differentiation, and loses the accuracy the AD path is there for.

No `.ltl` counterpart of `Dual` exists in `bootstrap/`, so I believe the fix is confined to `lateralus_lang/math_engine.py`.

Searching the repository for `Dual`, `derivative`, `gradient`, `autodiff` and `__pow__` returns no other issue or pull request at this commit, so I believe this is unreported.

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
- git commit -m "fix: [bounty] bug-report: Dual.__pow__ returns 0.0 for every constant-exponen"
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
