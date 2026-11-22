# Fuzzy Matching with `stdlib/qgram.ltl`

Q-gram indexes turn approximate string matching into set overlap: split
texts into overlapping n-grams, index them inverted, and rank by shared
grams — a cheap prefilter before expensive edit-distance DP.

`stdlib/qgram.ltl` implements q-grams, Jaccard similarity, an inverted
index, and ranked queries. Companion: `examples/qgram_tutorial.ltl`.

---

## API

- `qgrams(text, q)` — overlapping q-grams, padded with `\x01` so edge
  grams are indexed (`q<=0` → `[]`)
- `overlap(a, b, q)` — count of shared grams
- `jaccard(a, b, q)` — set-based Jaccard similarity in `[0,1]`
- `build_index(docs, q)` — `{qgram → [doc_ids]}` inverted index
- `query(index, text, q)` — `[doc_id, score]` sorted desc (insertion
  sort; doc ids deduplicated per query gram)

## Verified behavior

- `"kitten"` vs `"sitting"` (q=2): overlap 2, Jaccard ≈ 0.154 — the
  classic fuzzy-pair example behaves sensibly.
- Index + query rank docs by shared-gram count; no-match → `[]`.

## Bug found while building the tutorial

`int_of()` (used by `query` to key numeric doc ids) calls `char_at`,
which is not a runtime builtin → `NameError` on any query that scores
docs. Inlined copy uses `slice(s, i, i+1)`. Flagged for a module fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/qgram_tutorial.ltl
python -m lateralus_lang check examples/qgram_tutorial.ltl
python -m pytest tests/test_qgram_tutorial.py -x -q
```
