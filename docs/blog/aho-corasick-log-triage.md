# Turn log keyword matches into useful spans with Aho-Corasick

Suppose a service emits `error: timeout`. A filter may need to identify both
`error` and `timeout`, then highlight their locations. If the dictionary also
contains `out`, that shorter match must not disappear inside `timeout`.

This tutorial uses [`stdlib/aho_corasick.ltl`](../../stdlib/aho_corasick.ltl) to
build a dictionary once, scan several independent lines, and recover the
substring for every match. The existing
[algorithm walkthrough](../website/blog/aho-corasick-pure-lateralus.html)
explains the trie and failure links; here we focus on a reproducible workflow
with the Python reference backend and explicit checks of the output.

## Run the complete example

Use Python 3.10 or newer and a checkout of this repository containing this
tutorial. From the repository root, run:

```bash
python3 scripts/run_aho_corasick_tutorial.py
```

No additional package installation is needed: the runner imports the compiler
from this checkout. It reads the **actual** stdlib module and the companion
[`aho_corasick_log_scan.ltl`](../../examples/tutorials/aho_corasick_log_scan.ltl),
joins their source, and transpiles the result with `transpile_to_python`.
This follows the combined-source approach without copying or replacing the
matching algorithm.

There are two current backend caveats. `import aho_corasick` does not load this
`.ltl` module in the Python backend, and its generated preamble lacks `char_at`.
The runner supplies only that helper as `lambda text, index: text[index]`.
Consequently, running the companion file alone with `lateralus run` is not the
command demonstrated here. Native/C/VM execution is outside this tutorial's
validation scope.

Expected output:

```text
error [0,5): error: timeout
timeout [7,14): error: timeout
out [11,14): error: timeout
timeout [0,7): timeout then error
out [4,7): timeout then error
error [13,18): timeout then error
PASS: 53 assertions across 7 vectors and matcher reuse
```

An assertion failure terminates the runner with a nonzero exit status. With
pytest installed, the command also has a regression check:

```bash
python3 -m pytest tests/test_aho_corasick_tutorial.py -q
```

## Build once and keep the pattern IDs

The module's public functions have these names when its source is combined
with the example:

| Function | Result |
| --- | --- |
| `build(patterns)` | An automaton for the supplied list of strings |
| `find_all(matcher, text)` | Pairs `[pattern_id, exclusive_end]` |
| `find_all_starts(matcher, text)` | Pairs `[pattern_id, start]` |
| `contains_any(matcher, text)` | A boolean, returning early on a match |

```lateralus
let patterns = ["error", "timeout", "out"]
let matcher = build(patterns)
let hits = find_all_starts(matcher, "error: timeout")
```

Pattern IDs are zero-based indexes into `patterns`: ID 0 means `error`, ID 1
means `timeout`, and ID 2 means `out`. Keep this list unchanged while reusing
the matcher. Rebuild the automaton when changing the dictionary.

Each search starts at the root of the automaton. Reusing `matcher` for the next
line does not carry partial matches or offsets from the preceding line. This
example scans independent lines, not arbitrary chunks of a continuous stream;
a pattern split across two calls will not be found across their boundary.

## Convert a hit into a substring

For each `[pattern_id, start]`, recover the original pattern and calculate its
exclusive end:

```lateralus
for hit in hits {
    let pattern = patterns[hit[0]]
    let start = hit[1]
    let end = start + len(pattern)
    assert_eq(slice("error: timeout", start, end), pattern)
}
```

`timeout` occupies `[7,14)`: index 7 is included, index 14 is not. The matching
`out` occupies `[11,14)`. Both end at 14, and both count. Use `contains_any` when
you only need to retain or discard a line; use `find_all_starts` when positions
and highlighting matter.

These are literal, case-sensitive substring searches. `out` also matches
inside `timeout`; it is not a whole-word search. Normalize the patterns and
text together if needed, remembering that normalization may change offsets.
Use nonempty patterns. In this runner, indexing is Python string indexing
(Unicode code points), not UTF-8 bytes or displayed grapheme clusters. All
pinned offsets below use ASCII so that distinction does not obscure the example.

## Pinned vectors and overlap checks

Each expected triple is `(pattern_id, start, exclusive_end)`.

| Patterns | Text | Expected triples |
| --- | --- | --- |
| `error`, `timeout`, `out` | `error: timeout` | `(0,0,5)`, `(1,7,14)`, `(2,11,14)` |
| `he`, `she`, `his`, `hers` | `ushers` | `(1,1,4)`, `(0,2,4)`, `(3,2,6)` |
| `aba`, `ba` | `ababa` | `(0,0,3)`, `(1,1,3)`, `(0,2,5)`, `(1,3,5)` |
| `warning`, `error` | `all clear` | none |
| `error` | empty string | none |
| empty list | `error` | none |
| `error` | `ERROR` | none |

The companion example verifies both result counts, every expected start and
end pair, each extracted substring, and the boolean result. It compares
membership and counts rather than relying on tie ordering between matches that
end together. The transcript regression additionally records the current
display order, so an intentional order change requires updating that transcript.
Two final assertions reuse the first matcher on another clear line and another
matching line, checking that offsets reset.

The full example exercises the repository module without modifying it. Start
with a small dictionary like this one, inspect the spans, and then replace the
dictionary and input lines with the messages relevant to your application.
