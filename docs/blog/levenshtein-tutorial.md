# Suggest spelling corrections with Lateralus's Levenshtein module

A search box receives `aple`. Should it suggest `apple`, `maple`, or `banana`?
Edit distance gives us a simple way to filter a small candidate list. This
tutorial uses the actual [standard-library module](../../stdlib/levenshtein.ltl)
to build that filter and verify it against fixed expected results.

## Run the example

From a checkout of this repository, using Python 3.10 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_levenshtein_tutorial.py
python -m pytest tests/test_levenshtein_tutorial.py -q
```

Expected example output:

```text
18 pinned checks passed
Suggestions for aple (at most 2 edits):
apple: 1
maple: 1
apply: 2
```

The runnable [example](../../examples/levenshtein_tutorial.ltl) contains both
the assertions and the suggestion loop. A failed assertion makes the runner
exit unsuccessfully; the printed success line is reached only after all
18 assertions pass.

### Why there is a runner

In the current Python backend, `import stdlib.levenshtein` is emitted as a
comment rather than loading `stdlib/levenshtein.ltl`. The backend also lacks
the `char_at` helper used by this module. Consequently, running the example
alone with `lateralus run` will not resolve its functions.

The [small runner](../../scripts/run_levenshtein_tutorial.py) joins the
checked-out module source and the example, then runs the combined source
through `Compiler.run_source` with its default Python target. The example
provides this compatibility helper using the existing `slice` builtin:

```text
fn char_at(text: str, index: int) -> str {
    return slice(text, index, index + 1)
}
```

No distance algorithm is copied or replaced. Changes to the actual library
are exercised each time the runner executes. This recipe is for the Python
backend; it does not establish support for C, WASM, or bytecode execution.

## Count ordinary edits with `distance`

`distance(a, b)` counts the minimum number of single-character insertions,
deletions, and substitutions required to transform `a` into `b`. Every
operation costs one.

Our pinned vector is `distance("kitten", "sitting") == 3`. One sequence is:

1. Substitute `k` with `s`: `kitten` becomes `sitten`.
2. Substitute `e` with `i`: `sitten` becomes `sittin`.
3. Insert `g`: `sittin` becomes `sitting`.

The example checks that result, its reverse, identical strings, empty
strings, and `distance("flaw", "lawn") == 2`. These expected values are
literal assertions, independent of the implementation's output.

## Filter candidates with `bounded`

Often we only care whether a candidate is close enough. For a nonnegative
integer limit `k`, `bounded(a, b, k)` returns the distance when it is at most
`k`; a result greater than `k` means the candidate should be rejected.

```text
let query = "aple"
let candidates = ["apple", "maple", "apply", "banana"]
let limit = 2
let i = 0
while i < len(candidates) {
    let candidate = candidates[i]
    let edits = bounded(query, candidate, limit)
    if edits <= limit {
        print(candidate + ": " + str(edits))
    }
    i = i + 1
}
```

`apple` and `maple` each need one insertion. `apply` needs an insertion and
a substitution. `banana` is rejected. The loop preserves candidate order;
it does not rank by frequency or choose a correction automatically.

Use `result > k` for rejection. Do not interpret an above-limit result as
the exact distance, or assume every rejected result equals `k + 1`: the
implementation can finish its last row and return a larger value. Its
length-difference and row-minimum checks can exit early, but its inner loop
still traverses the full row. Despite the module's "banded" comment, this
implementation is not restricted to a width-`k` band.

## Compare normalized similarity

`similarity(a, b)` computes `1 - distance(a, b) / max(len(a), len(b))`.
Two empty strings have similarity `1.0`. The pinned `kitten`/`sitting` pair
has similarity `4/7`, approximately `0.571429`; the example checks it with
a floating-point tolerance of `0.000001`.

This is a length-normalized character score, not a probability that two
words mean the same thing. A threshold appropriate for long labels may
be too permissive for short identifiers.

## Treat adjacent transpositions separately

`distance("ca", "ac")` is `2`, while `damerau("ca", "ac")` is `1`:
the latter permits an adjacent transposition as one edit.

The module's `damerau` function implements the restricted variant, also
called optimal string alignment. It is not unrestricted Damerau-Levenshtein
distance. For example, this implementation returns `3` for `"CA"` to
`"ABC"`; unrestricted distance would be `2` (transpose, then insert `B`).
Both the simple swap and the distinguishing case are pinned in the example.

## Bound the application, too

Start with short inputs and a small candidate list. Row construction uses
list concatenation, which copies lists under the Python backend, so abstract
dynamic-programming complexity alone does not describe this implementation's
cost. This tutorial makes no throughput or speedup claim.

Comparisons are case-sensitive and do not normalize Unicode. On this backend,
string slicing operates on Python Unicode code points, not user-perceived
grapheme clusters. Decide whether to normalize and case-fold inputs before
using the score in an application. Keep that preprocessing consistent for
queries and candidates.

The complete example is a deterministic starting point: the library supplies
the scoring functions, the threshold determines which candidates survive,
and the pinned checks make the documented behavior reproducible.
