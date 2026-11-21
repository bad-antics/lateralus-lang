# Semantic Versioning in Lateralus with `stdlib.semver`

The `stdlib.semver` module provides comprehensive parsing, validation, comparison, and manipulation of semantic versions strictly adhering to the [Semantic Versioning 2.0.0 Specification](https://semver.org/). It powers package managers, CLI release tooling, build verification, and runtime dependency resolution.

---

## 1. Version Parsing & Deconstruction

Versions are parsed into structured 5-element tuples: `[major, minor, patch, prerelease, build]`.

The parser automatically normalizes leading `v` or `V` prefixes and handles hyphenated pre-release tags and plus-prefixed build metadata:

```lateralus
import semver

let v = semver.parse("v2.1.0-rc.2+linux.arm64")

let maj = semver.major(v)       // 2
let min = semver.minor(v)       // 1
let pat = semver.patch(v)       // 0
let pre = semver.prerelease(v)  // "rc.2"
let bld = semver.build_meta(v)  // "linux.arm64"

let stable = semver.is_stable(v)          // false
let is_pre = semver.is_prerelease(v)      // true
```

---

## 2. Version Comparison & Precedence

Comparisons follow SemVer 2.0.0 precedence rules:

1. `major`, `minor`, and `patch` are compared numerically.
2. When numbers match, a **pre-release version has lower precedence than a normal release** (e.g., `1.0.0-alpha < 1.0.0`).
3. Build metadata is ignored when determining version precedence.

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`compare(a, b)`** | `(list, list) -> int` | Returns `-1` if $a < b$, `0` if $a == b$, `1` if $a > b$. |
| **`lt(a, b)`** | `(list, list) -> bool` | Checks if $a < b$. |
| **`gt(a, b)`** | `(list, list) -> bool` | Checks if $a > b$. |
| **`eq(a, b)`** | `(list, list) -> bool` | Checks equality (ignoring build metadata). |
| **`lte(a, b)` / `gte(a, b)`** | `(list, list) -> bool` | Inclusive inequalities. |

```lateralus
let v1 = semver.parse("1.0.0-beta")
let v2 = semver.parse("1.0.0")

if semver.lt(v1, v2) {
    println("Pre-release is strictly lower precedence than stable release.")
}
```

---

## 3. Automated Release Bumping

Easily increment version components following semantic conventions:

- **`bump_major(v)`**: Increments `major` by 1 and resets `minor` and `patch` to 0. Clears tags.
- **`bump_minor(v)`**: Increments `minor` by 1 and resets `patch` to 0. Clears tags.
- **`bump_patch(v)`**: Increments `patch` by 1. Clears tags.
- **`with_prerelease(v, tag)`**: Replaces the pre-release tag.
- **`with_build(v, meta)`**: Replaces the build metadata tag.

```lateralus
let current = semver.parse("1.4.2")

let next_patch = semver.bump_patch(current) // 1.4.3
let next_minor = semver.bump_minor(current) // 1.5.0
let next_major = semver.bump_major(current) // 2.0.0
```

---

## 4. Range Satisfaction (Caret & Tilde)

- **`satisfies_caret(v, major, minor)`**: Verifies non-breaking semver compatibility (`^major.minor`).
  - Matches same major version and minor $\ge$ requirement.
- **`satisfies_tilde(v, major, minor)`**: Verifies patch-level compatibility (`~major.minor`).
  - Matches exact major and minor, allowing any patch.

```lateralus
let pkg = semver.parse("1.4.9")

// Check ^1.2 compatibility (allows 1.2.0 through 1.x.x)
let ok_caret = semver.satisfies_caret(pkg, 1, 2) // true

// Check ~1.4 compatibility (allows 1.4.0 through 1.4.x)
let ok_tilde = semver.satisfies_tilde(pkg, 1, 4) // true
```

---

## 5. End-to-End Example: Release Automation Script

```lateralus
import semver

fn prepare_release(tag: str, bump: str) -> str {
    let parsed = semver.parse(tag)
    let bumped = parsed
    
    if bump == "major" {
        bumped = semver.bump_major(parsed)
    } else if bump == "minor" {
        bumped = semver.bump_minor(parsed)
    } else {
        bumped = semver.bump_patch(parsed)
    }
    
    return semver.to_string(bumped)
}

fn main() {
    let current_version = "v1.2.3"
    let next_version = prepare_release(current_version, "minor")
    println("Next release candidate: " + next_version)
    // Output: Next release candidate: 1.3.0
}
```
