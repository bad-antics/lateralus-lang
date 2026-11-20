# Bounty Fix

**Reward:** $10.00
**Issue:** https://github.com/bad-antics/lateralus-lang/issues/245
**Repo:** https://github.com/bad-antics/lateralus-lang

---

## Issue

[bounty] bug-report: C backend _emit_main_wrapper guard is a tautology - scripts without fn main() call an undefined ltl_main()

## Lateralus version
3.2.0 (HEAD `4cb9147d4cd565a3d0fc22a190ed18f14077412f`)

## Python version
3.12.10

## Operating System
Windows 11 (codegen only — platform independent)

## Component
`lateralus_lang/codegen/c.py` — `_emit_main_wrapper` (lines 1732–1743) and the
top-level statement branch (line 638)

## Bug description

`_emit_main_wrapper` guards the `ltl_main();` call with this condition:

```python
# lateralus_lang/codegen/c.py:1732-1743
def _emit_main_wrapper(self):
    w = self._w
    w.line()
    w.comment("═══ Entry Point ═══")
    w.block_open("int main(int argc, char *argv[])")
    if "main" in self._functions or "ltl_main" in [
            self._mangle("main")]:
        w.line("ltl_main();")
    else:
        w.comment("No main() found — nothing to run")
    w.line("return 0;")
    w.block_close()
```

The second half of the condition is a **tautology**: `_mangle("main")` returns
`"ltl_main"` (because `"main"` is in the `C_KEYWORDS` set at line 587), so the
expression is `"ltl_main" in ["ltl_main"]`, which is always `True`.

Consequently the `else` branch — `/* No main() found — nothing to run */` — is
unreachable dead code, and `ltl_main();` is emitted **unconditionally**. For a
program that does not define `fn main()`, `ltl_main` is never declared and never
defined, so the generated translation unit references an undefined symbol.

This is compounded by line 638, which silently drops executable top-level
statements:

```python
# lateralus_lang/codegen/c.py:638
w.comment("top-level expr (skipped in C — handled by main)")
```

Nothing actually handles them ("handled by main" is not true — the statements are
discarded). So a script written with top-level statements produces C that both
(a) does nothing and (b) does not link.

## Reproduction code

`repro.ltl` (top-level statements — the form `lateralus run` accepts):

```lateralus
println(1 + 1)
println("hello")
```

```
$ PYTHONPATH=. python -m lateralus_lang run repro.ltl
2
hello

$ PYTHONPATH=. python -m lateralus_lang c repro.ltl
Transpiled -> repro.c
```

## Expected behavior

`repro.c` compiles and prints `2` / `hello` — i.e. either the top-level statements
are emitted into a synthesized entry function, or the transpiler reports that the C
target requires an explicit `fn main()`.

At minimum, if no entry point exists the emitted `main()` should be the documented
`/* No main() found — nothing to run */` stub, not a call to an undefined function.

## Actual behavior

`repro.c` contains, at the end:

```c
/* ═══ Entry Point ═══ */
int main(int argc, char *argv[]) {
    ltl_main();
    return 0;
}
```

and every top-level statement has been replaced by a comment:

```c
/* top-level expr (skipped in C — handled by main) */
/* top-level expr (skipped in C — handled by main) */
```

`ltl_main` occurs **exactly once** in the whole file — the call site. There is no
forward declaration and no definition:

```
$ grep -n ltl_main repro.c
202:    ltl_main();
```

So the translation unit references an undeclared/undefined function: C99+ rejects the
implicit declaration, and any C89 build fails at link time with
`undefined reference to 'ltl_main'`.

For contrast, the same source with an explicit entry point works fine — `fn main()`
plus a trailing `main()` call produces a proper forward declaration at line 185, a
definition at 192, and the call at 200:

```lateralus
fn main() {
    println(1 + 1)
}
main()
```

```c
static ltl_value_t ltl_main(void);          /* line 185 */
static ltl_value_t ltl_main(void) {         /* line 192 */
    ...
}
int main(int argc, char *argv[]) {          /* line 199 */
    ltl_main();
    return 0;
}
```

The Python backend handles the top-level form correctly (it prints `2` / `hello`), so
the two backends disagree about the same input.

## Additional context

**Why the tautology is easy to miss:** `"x" in [expr]` reads like a membership test
against a collection, but here the right-hand side is a one-element list built from a
single mangled name. It compiles, lints clean, and always evaluates to `True`.

**Suggested fix (guard):**

```diff
--- a/lateralus_lang/codegen/c.py
+++ b/lateralus_lang/codegen/c.py
-        if "main" in self._functions or "ltl_main" in [
-                self._mangle("main")]:
+        if "main" in self._functions:
             w.line("ltl_main();")
         else:
             w.comment("No main() found — nothing to run")
```

`_mangle` maps `"main"` → `"ltl_main"` injectively (it is the only keyword that gets a
prefix without a collision), so testing the original name in `self._functions` is
sufficient and keeps the emitted call spelled correctly.

**Suggested fix (top-level statements):** the natural approach is to route them
through the same path the Python backend uses — synthesize a body (e.g.
`static void ltl_toplevel(void)`) that the entry point calls after `ltl_main()` when
one exists, or instead of it when it does not — and drop the misleading
`"handled by main"` comment. If supporting scripts without `main()` is out of scope
for the C target, emitting a clear diagnostic
(`error: the C target requires an explicit fn main()`) is preferable to silently
producing a file that cannot build.

**Scope check:** the split is purely "does the script define `fn main()`". Top-level
statements are accepted by the parser and executed by the Python backend, so this only
shows up when the C target is selected.

## Bounty

Could you confirm whether this qualifies for the published US$10 bug-report bounty
(minimal reproduction + root-cause analysis above)? Happy to open the PR for the
guard fix — it is a one-line change and I can add a regression test that transpiles a
`main`-less script and asserts the entry point either exists or is a documented stub.


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
- git commit -m "fix: [bounty] bug-report: C backend _emit_main_wrapper guard is a tautology -"
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
