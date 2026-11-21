# Edit Distance with `stdlib/levenshtein.ltl`

`stdlib/levenshtein.ltl` implements four flavours of string edit
distance in ~150 lines of pure Lateralus:

- **`distance(a, b)`** — classic Wagner-Fischer DP, O(nm) time but
  only O(min(n,m)) space by keeping two rolling rows, and it swaps
  arguments so the shorter string drives the row width.
- **`bounded(a, b, k)`** — same DP but early-exits with `k+1` as soon
  as a row's minimum exceeds the bound; also rejects immediately when
  `|len(a)-len(b)| > k`.
- **`similarity(a, b)`** — `1.0 - distance / max(len)`, a normalized
  score in `[0.0, 1.0]`.
- **`damerau(a, b)`** — adds adjacent transposition via a full
  (n+1)×(m+1) matrix.

Companion: `examples/levenshtein_tutorial.ltl`.

---

## How the DP works

`distance` builds `prev` = `[0,1,2,…,n]` (distance from prefixes of
`a` to the empty string), then for each char of `b` builds `curr`:

```text
curr[k] = min( curr[k-1] + 1,   // deletion
               prev[k]   + 1,   // insertion
               prev[k-1] + cost)// substitution (0 if chars equal)
```

`char_at(a, i)` reads one character; the tutorial supplies a local
`slice`-based helper because the `char_at` builtin isn't emitted by
the current Python shim (same gap hit in the tar tutorial).

## `bounded` — the early-exit trick

Two cheap rejects before doing any DP:

1. `abs_diff(n, m) > k` → `k+1` (length alone proves it)
2. After each row, `row_min > k` → `k+1` (the whole frontier is
   already too far)

This is what you want inside a "did the user maybe mean this word?"
loop over a dictionary — most candidates die on the length check.

## `damerau` — OSA, not true DL

Worth being precise: the transposition term
`dp[p-2][q-2] + 1` makes this the **Optimal String Alignment**
variant — each substring may be edited at most once. The canonical
counterexample proves the difference:

```text
distance("ca", "abc")  = 3   (plain Levenshtein)
damerau ("ca", "abc")  = 3   (OSA — transpose can't combine
                              with the needed insertion)
true Damerau-Levenshtein would be 2
```

For typo correction OSA is fine; for phylogenetics or music
alignment where repeated edits overlap, you'd need the full
unrestricted Damerau recurrence.

## Verified results

```text
kitten→sitting = 3     flaw→lawn = 2     abc→abd = 1
""→abc = 3             abc→"" = 3        same→same = 0
bounded: k=2 → 3, k=3 → 3 (early-exit sentinel k+1)
         abc/xyz k=1 → 2, "a"/"abcdef" k=2 → 3
similarity: kitten/sitting = 0.5714285714285714
            abc/abc = 1.0   abc/xyz = 0.0
transposition: ab→ba = 1 (single swap)
```

`tests/test_levenshtein_tutorial.py` pins every value.

## When to use it

**Use it** for spell-check candidate ranking, fuzzy config-key
matching, diff-ish "how different are these two strings" metrics,
and as a clean DP teaching example (rolling rows, banded early
exit, full-matrix variant).

**Don't expect** Unicode normalization (it's code-unit based via
`char_at`), token-aware distance, or the unrestricted Damerau
variant — see the OSA note above.

That is `stdlib/levenshtein.ltl`: three distances and a similarity
score, all verifiable against textbook vectors.
