# AGENT_SUMMARY.md

**Issue:** [#79](https://github.com/bad-antics/lateralus-lang/issues/79) — `semver.compare` reverses numeric prerelease precedence
**Commit:** `41f1903` — `fix: [bounty] bug-report: semver.compare reverses numeric prerelease preceden`
**Files changed:** 2 (`stdlib/semver.ltl`, `tests/test_semver.py`)

---

## Root cause

`stdlib/semver.ltl` documents Semantic Versioning 2.0.0, but `compare()` handled the
pre-release segment by comparing the two tags as **whole strings**:

```lateralus
// Both have pre-release, compare lexicographically
if a_pre < b_pre { return -1 }
if a_pre > b_pre { return 1 }
return 0
```

SemVer 2.0.0 [section 11](https://semver.org/#spec-item-11) requires the pre-release tag to be
split on dots and compared **identifier by identifier**, with three rules the string comparison
violated:

1. **Numeric identifiers compare numerically.** Lexicographically `"2" > "11"`, so
   `1.0.0-beta.2` sorted *above* `1.0.0-beta.11` — the spec's own published example of the
   opposite ordering. Same for `alpha.9` vs `alpha.10`.
2. **Numeric identifiers rank below non-numeric ones.** `-` (0x2D) sorts below `1` (0x31) in
   ASCII, so the valid identifier `1` compared *above* the valid identifier `-`.
3. (Rule 3, "more identifiers wins when the shared ones are equal," happened to fall out of
   string comparison correctly for the common cases, so it was not visibly broken.)

Because `lt`, `gt`, `lte`, `gte`, and `eq` all delegate to `compare()`, every one of them
inherited the reversal. A consumer picking "the newest pre-release" could pick the oldest.

## Fix

Replaced the whole-string comparison in `compare()` with a single delegating call and added three
private (non-`pub`) helpers above it, so the module's public API is unchanged:

- `is_numeric_ident(s)` — true when `s` is non-empty and all ASCII digits.
- `compare_prerelease_ident(a, b)` — one identifier: numeric/numeric compares as integers;
  numeric vs non-numeric returns numeric-lower; otherwise lexical (ASCII).
- `compare_prerelease(a_pre, b_pre)` — walks both tags in lockstep, slicing out one
  dot-separated identifier per side, short-circuiting on the first non-zero identifier
  comparison; when the shared identifiers all match, the tag with identifiers remaining wins.

Everything else in `compare()` is untouched: the `major.minor.patch` ladder, the
"stable outranks pre-release" rules, and the both-empty equality case.

### Notable implementation constraint

The natural implementation is `split(a_pre, ".")`, but **`split` is not available in the Python
backend** — it is absent from the generated shim preamble, so any call to it raises
`NameError: name 'split' is not defined` at runtime. (This is pre-existing and affects
`semver.parse` too; see Concerns.) The scan is therefore written with `len`, `slice`, and
character indexing — exactly the primitives `parse()` already uses — which keeps the fix working
on the Python backend and on the harness in the issue report.

Two cosmetic choices exist only to keep linter output byte-identical to before the change:
the local is named `ident_cmp` (not `c`, which tripped `shadowed-variable`) and a doc comment
says "pre-release tags" (not "strings", whose substring accidentally silenced the pre-existing
`unused-import` warning via the linter's substring heuristic).

## Verification

**1. The issue's own extended reproduction** — compiles the unmodified `stdlib/semver.ltl` through
the Python backend and calls `compare` on documented version lists. Was 6 pass / 4 fail; now:

```
PASS 'beta.2' vs 'beta.11'   PASS 'beta.11' vs 'beta.2'   PASS 'alpha.9' vs 'alpha.10'
PASS '1' vs '-'              PASS 'alpha' vs 'alpha.1'    PASS 'alpha.1' vs 'alpha.beta'
PASS 'beta' vs 'beta.2'      PASS 'rc.1' vs ''            PASS '' vs 'rc.1'
PASS 'beta.2' vs 'beta.2'
```

**2. New regression test** `tests/test_semver.py` — 87 tests, all passing:

```sh
python -m pytest tests/test_semver.py -q     # 87 passed
```

It compiles the real stdlib module (no reimplementation) and covers all 55 ordered pairs of the
spec's published precedence chain (`1.0.0-alpha` → `2.0.0`) in both directions, reflexivity,
19 targeted edge cases (multi-digit numerics, `1` vs `-`, ASCII case `A` vs `a`, the
extra-identifier rule, pre-release vs stable, core-version dominance), `compare` used as a
`cmp_to_key` sort key, and `lt`/`gt`/`lte`/`gte`/`eq` delegation.

**Confirmed the test actually guards the bug:** reverting only `stdlib/semver.ltl` to `HEAD` and
re-running gives **10 failed, 77 passed**; with the fix, 87 passed.

**3. Full suite — no regressions.** Captured the failure set before and after:

| | passed | failed |
|---|---|---|
| baseline (`HEAD` semver, no new test) | 2033 | 26 |
| with fix | 2120 | 26 |

`diff` of the two sorted `FAILED` lists is **empty** — the same 26 pre-existing failures, none
touched by this change. They are Windows-environment issues unrelated to semver: `cp1252`
`UnicodeDecodeError`/`UnicodeEncodeError` on non-ASCII sources (`test_law_*`,
`test_v23_features::TestRegressionStdlib`, `TestRegressionExamples`), plus `test_stdlib_laws`,
`test_mutation_tester`, and `test_v19_features::TestFFI` (missing build artifact).

**4. All backends still compile** `stdlib/semver.ltl`: `PYTHON`, `JAVASCRIPT`, `C`, `WASM`, and
`CHECK` all report `ok=True`. The `BYTECODE` target fails with `Unresolved label: 'len'` — verified
**identical before and after** the change (by compiling `git show HEAD:stdlib/semver.ltl`), so it
is pre-existing and unrelated.

**5. Linter output unchanged** — identical 2 issues on the original and patched file
(`shadowed-variable` L57, `unused-import` L6), both pre-existing.

## Concerns for a reviewer

1. **I staged 2 files, not `git add -A`.** The process in `BOUNTY_TASK.md` says `git add -A`, but
   this working tree arrived with **735 pre-existing modified files** that are pure CRLF/encoding
   churn from the Windows checkout (e.g. `examples/showcase.ltl` shows 258 insertions / 258
   deletions with no content change). `git add -A` would have buried a 77-line fix in that noise
   and broken "one logical change, one commit," so I staged only `stdlib/semver.ltl` and
   `tests/test_semver.py`. The 735 files remain uncommitted and untouched.

2. **`semver.parse()` is broken on the Python backend, and I did not fix it.** It calls
   `split(s, ".")` and `index_of(s, "+")`; neither resolves — `import strings` compiles to
   `strings = _builtins` and does not bring `index_of` into scope, and `split` has no shim at all
   (`str_split` exists, but `split` does not). This is out of scope for issue #79, which is
   explicitly about comparison only, and is why the issue's harness passes version *lists*
   directly rather than parsing. Worth a separate issue.

3. **Leading zeros are treated as numeric.** `"01"` is an *invalid* numeric identifier under
   SemVer (section 9 forbids leading zeros), but `is_numeric_ident("01")` returns true, so it
   compares numerically as `1`. The spec gives no precedence rule for invalid input, this matches
   what most implementations do, and `compare()` performs no validation anywhere else — so I chose
   not to add validation inside a comparison bug fix.

4. **Build metadata is still ignored in comparison**, which is correct per SemVer section 10
   ("build metadata MUST be ignored when determining version precedence") and unchanged here.

5. **Only the Python backend was executed.** The JS/C/WASM backends were verified to *compile*
   but not run; doing so needs `node`/`gcc` toolchains. The helpers use only `len`, `slice`,
   string indexing, `int()`, `while`, and `&&`/`||` — all already used by `parse()` and
   `stdlib/strings.ltl`, so no new primitive surface is introduced.
