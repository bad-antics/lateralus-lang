---
title: "Semantic Versioning in Lateralus with stdlib.semver"
date: 2026-04-20
author: bad-antics
tags: [stdlib, semver, tutorial, pipelines]
---

# Semantic Versioning in Lateralus with `stdlib.semver`

Version strings look trivial until you have to sort them. Is `1.0.0-beta.11`
newer or older than `1.0.0-beta.2`? Is `1.0.0+build.5` different from
`1.0.0+build.9`? The `stdlib.semver` module answers these questions
correctly, following [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html),
and it is designed to be used inside pipelines.

This tutorial covers:

1. Parsing and validating version strings
2. Comparing versions (and the precedence rules that trip people up)
3. Sorting a list of versions
4. Bumping versions
5. Testing against pinned vectors

## 1. Parsing

Parsing can fail, so `semver.parse` is a *fallible* function and belongs on
the `|?>` pipe. Total functions use `|>`.

```lateralus
use stdlib.semver

fn describe(raw) {
    raw
        |?> semver.parse
        |> fn(v) { "major={v.major} minor={v.minor} patch={v.patch}" }
}

describe("1.4.2")            -- Ok("major=1 minor=4 patch=2")
describe("1.4")              -- Error(InvalidVersion("1.4"))
describe("01.4.2")           -- Error(InvalidVersion("01.4.2"))  (leading zero)
```

A parsed version is a record:

```lateralus
record Version {
    major: Int,
    minor: Int,
    patch: Int,
    pre: List[String],     -- pre-release identifiers, e.g. ["beta", "11"]
    build: List[String],   -- build metadata identifiers
}
```

Validation rules enforced by `semver.parse`:

- Exactly three dot-separated numeric components: `MAJOR.MINOR.PATCH`
- No leading zeros in numeric components (`01.0.0` is invalid)
- Optional pre-release after `-`, dot-separated identifiers of `[0-9A-Za-z-]`
- Numeric pre-release identifiers must not have leading zeros
- Optional build metadata after `+`, dot-separated identifiers of `[0-9A-Za-z-]`
- Identifiers must be non-empty (`1.0.0-` and `1.0.0-alpha..1` are invalid)

## 2. Comparing

`semver.compare(a, b)` returns `-1`, `0`, or `1`.

```lateralus
let order = semver.compare(
    semver.parse("1.0.0-alpha") |> unwrap,
    semver.parse("1.0.0")       |> unwrap
)
-- order == -1   (a pre-release is LOWER than its normal version)
```

### The precedence rules

Precedence is determined by the following, in order:

1. Compare `major`, then `minor`, then `patch`, **numerically**.
2. A version **with** a pre-release is lower than the same version **without** one.
3. If both have pre-releases, compare identifiers left to right:
   - Both numeric: compare **numerically** (`2 < 11`).
   - Both alphanumeric: compare **lexically in ASCII order** (`alpha < beta`).
   - Numeric vs. alphanumeric: the **numeric** one is lower (`1 < alpha`).
   - If all shared identifiers are equal, the **longer** list is greater
     (`alpha < alpha.1`).
4. **Build metadata is ignored.** `1.0.0+a` and `1.0.0+b` have equal precedence.

The classic mistake is comparing pre-release identifiers as plain strings,
which makes `beta.11 < beta.2`. SemVer says `beta.2 < beta.11` because both
are numeric. `stdlib.semver` gets this right for you.

## 3. Sorting

Because `compare` is a standard three-way comparator, it plugs straight into
a pipeline:

```lateralus
fn sort_versions(raw_list) {
    raw_list
        |> map(fn(s) { s |?> semver.parse |> unwrap })
        |> sort_by(semver.compare)
        |> map(semver.to_string)
}

sort_versions([
    "1.0.0", "1.0.0-rc.1", "1.0.0-beta.11", "1.0.0-beta.2",
    "1.0.0-beta", "1.0.0-alpha.beta", "1.0.0-alpha.1", "1.0.0-alpha"
])
-- ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
--  "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
```

That output is exactly the precedence chain from the SemVer 2.0.0 spec.

## 4. Bumping

```lateralus
fn next_release(raw, kind) {
    raw
        |?> semver.parse
        |> fn(v) {
            match kind {
                "major" => semver.bump_major(v),
                "minor" => semver.bump_minor(v),
                "patch" => semver.bump_patch(v),
            }
        }
        |> semver.to_string
}

next_release("1.4.2", "patch")  -- Ok("1.4.3")
next_release("1.4.2", "minor")  -- Ok("1.5.0")
next_release("1.4.2", "major")  -- Ok("2.0.0")
```

Bumping resets lower components to zero and clears pre-release and build
metadata, per SemVer.

## 5. Pinned test vectors

Use these vectors to verify any implementation. They are the canonical
SemVer 2.0.0 precedence chain; every adjacent pair must compare `-1`
(left is lower), and reversing the pair must give `1`.

| # | Left              | Right             | `compare(Left, Right)` |
|---|-------------------|-------------------|------------------------|
| 1 | `1.0.0-alpha`     | `1.0.0-alpha.1`   | `-1`                   |
| 2 | `1.0.0-alpha.1`   | `1.0.0-alpha.beta`| `-1`                   |
| 3 | `1.0.0-alpha.beta`| `1.0.0-beta`      | `-1`                   |
| 4 | `1.0.0-beta`      | `1.0.0-beta.2`    | `-1`                   |
| 5 | `1.0.0-beta.2`    | `1.0.0-beta.11`   | `-1`                   |
| 6 | `1.0.0-beta.11`   | `1.0.0-rc.1`      | `-1`                   |
| 7 | `1.0.0-rc.1`      | `1.0.0`           | `-1`                   |
| 8 | `1.0.0+build.1`   | `1.0.0+build.9`   | `0` (build ignored)    |
| 9 | `2.0.0`           | `1.9.9`           | `1`                    |
|10 | `1.10.0`          | `1.9.0`           | `1` (numeric, not lexical) |

Invalid inputs that must be rejected by `semver.parse`:

```
""            "1"           "1.0"         "1.0.0.0"
"01.0.0"      "1.01.0"      "1.0.01"      "1.0.0-"
"1.0.0-01"    "1.0.0-a..b"  "1.0.0+"      "v1.0.0"
```

A compact test in Lateralus:

```lateralus
use stdlib.semver
use stdlib.test

test "semver precedence chain" {
    let chain = [
        "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
        "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
        "1.0.0-rc.1", "1.0.0"
    ] |> map(fn(s) { s |?> semver.parse |> unwrap })

    for i in 0..(len(chain) - 1) {
        assert_eq(semver.compare(chain[i], chain[i + 1]), -1)
        assert_eq(semver.compare(chain[i + 1], chain[i]), 1)
    }
}

test "build metadata is ignored" {
    let a = "1.0.0+build.1" |?> semver.parse |> unwrap
    let b = "1.0.0+build.9" |?> semver.parse |> unwrap
    assert_eq(semver.compare(a, b), 0)
}

test "rejects malformed versions" {
    for bad in ["", "1", "1.0", "01.0.0", "1.0.0-", "v1.0.0"] {
        assert(is_error(bad |?> semver.parse))
    }
}
```

## Takeaways

- Use `|?>` for `semver.parse`; it can fail.
- Never sort version strings lexically; sort with `semver.compare`.
- Pre-release < release; numeric identifiers compare as numbers; build
  metadata never affects ordering.
- The vector table above is your regression suite.

*Companion files: `examples/semver_demo.lat` (runnable example) and
`tests/test_semver_vectors.lat` (the pinned vectors above).*