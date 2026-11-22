# Mastering Semantic Versioning 2.0.0 with Lateralus `stdlib/semver.ltl`

Modern package ecosystems like Cargo, npm, and Go rely on **Semantic Versioning 2.0.0** to convey API compatibility guarantees between software publishers and consumers. Without strict versioning semantics, upgrading dependencies risks breaking production applications.

Lateralus ships with a zero-dependency Semantic Versioning implementation in `stdlib/semver.ltl`. This tutorial covers parsing version strings, evaluating precedence rules, automating release increments, and filtering dependencies using caret (`^`) and tilde (`~`) ranges.

---

## 1. Anatomy of SemVer 2.0.0

A valid semantic version follows the grammar:

$$\text{MAJOR}.\text{MINOR}.\text{PATCH}[-\text{PRERELEASE}][+\text{BUILD}]$$

1. **MAJOR**: Incremented when you make incompatible API changes.
2. **MINOR**: Incremented when you add backwards-compatible functionality.
3. **PATCH**: Incremented when you make backwards-compatible bug fixes.
4. **PRERELEASE**: Optional identifier (`-alpha.1`, `-rc.2`) indicating unstable pre-releases.
5. **BUILD**: Optional build metadata (`+sha.5114f85`, `+build.42`) that describes compiler or target context.

`stdlib/semver.ltl` parses strings into a 5-element list: `[major, minor, patch, prerelease, build]`.

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `semver_parse` | `(version: str) -> list` | Parses a semver string (stripping optional leading `v`/`V`). |
| `semver_to_string` | `(v: list) -> str` | Converts a 5-element version tuple back to formatted string. |
| `semver_major` / `minor` / `patch` | `(v: list) -> int` | Accessors for the numerical components. |
| `semver_prerelease` / `build_meta` | `(v: list) -> str` | Accessors for pre-release tag and build identifier. |
| `semver_is_stable` | `(v: list) -> bool` | Returns `true` if `prerelease` is empty. |
| `semver_is_prerelease` | `(v: list) -> bool` | Returns `true` if a pre-release tag is present. |
| `semver_compare` | `(a: list, b: list) -> int` | Returns `-1` ($a < b$), `0` ($a == b$), or `1` ($a > b$). |
| `semver_lt` / `gt` / `eq` | `(a: list, b: list) -> bool` | Semantic ordering operators. |
| `semver_bump_major` | `(v: list) -> list` | Increments major, resets minor and patch to 0. |
| `semver_bump_minor` | `(v: list) -> list` | Increments minor, resets patch to 0. |
| `semver_bump_patch` | `(v: list) -> list` | Increments patch version. |
| `semver_satisfies_caret` | `(v: list, maj: int, min: int) -> bool` | Tests `^maj.min` compatibility. |
| `semver_satisfies_tilde` | `(v: list, maj: int, min: int) -> bool` | Tests `~maj.min` patch-level compatibility. |

---

## 3. Precedence Rules & Build Metadata Invariance

According to **SemVer 2.0.0 Specification Rule 11**:
- Precedence is determined by comparing major, minor, and patch in order.
- When numbers are equal, a pre-release version has **lower precedence** than a normal version:
  $$1.0.0\text{-alpha} < 1.0.0\text{-beta} < 1.0.0\text{-rc.1} < 1.0.0$$
- According to **Specification Rule 10**, build metadata is completely ignored in comparisons:
  $$1.0.0+20261122 == 1.0.0+build.42$$

Here is how Lateralus enforces these rules:

```lateralus
import semver

let rc = semver_parse("1.0.0-rc.1")
let release = semver_parse("1.0.0")

if semver_lt(rc, release) {
    print("Pre-release correctly ordered below stable release")
}

let b1 = semver_parse("1.0.0+build.1")
let b2 = semver_parse("1.0.0+build.2")
if semver_eq(b1, b2) {
    print("Build metadata is ignored during equality checks")
}
```

---

## 4. Range Satisfaction: Caret (`^`) vs Tilde (`~`)

When managing dependencies in custom toolchains or Lateralus package manifests:
- **Caret Range (`^1.2`)**: Compatible with any release that does not modify the left-most non-zero digit ($1.2.0 \le v < 2.0.0$).
- **Tilde Range (`~1.2`)**: Pins to patch-level updates only ($1.2.0 \le v < 1.3.0$).

```lateralus
let version = semver_parse("1.2.7")

// Accepts 1.2.x and 1.3.x, rejects 2.0.0
let ok_caret = semver_satisfies_caret(version, 1, 2)

// Accepts only 1.2.x, rejects 1.3.0
let ok_tilde = semver_satisfies_tilde(version, 1, 2)
```

---

## 5. Verification & Test Suite

The canonical test vectors are preserved in `tests/stdlib_semver_tutorial.ltl` and can be validated with:

```bash
python -m lateralus_lang check tests/stdlib_semver_tutorial.ltl
python -m lateralus_lang check examples/semver_tutorial.ltl
```
