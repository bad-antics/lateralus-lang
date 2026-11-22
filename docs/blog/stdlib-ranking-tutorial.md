# Ranking Documents with `stdlib/ranking.ltl`

BM25 and TF-IDF are the ranking workhorses behind every search box.
`stdlib/ranking.ltl` implements them in pure Lateralus — tokenization,
term-frequency tables, a compact corpus index, BM25 scoring, and
cosine similarity over sparse vectors. No external index required.

This tutorial exercises the whole pipeline end to end. Companion:
`examples/ranking_tutorial.ltl`.

---

## Pipeline

1. **`tokenize(text)`** — ASCII-lowercases and splits on non-word chars
   via explicit A–Z tables (the language has no `ord`-based case fold).
2. **`term_freq(tokens)`** — returns parallel `[terms, counts]`.
3. **`build_index(docs)`** — per-doc TF tables, lengths, average doc
   length, and a document-frequency `[terms, df]` table.
4. **`idf_bm25` / `bm25_score` / `rank_bm25`** — Robertson BM25 with
   k1=1.5, b=0.75; `rank_bm25` returns `[doc_index, score]` sorted desc.
5. **`tfidf_vector` / `cosine_similarity`** — sparse-vector cosine via
   Newton's sqrt iteration.

## Observed behavior worth knowing

- `idf_bm25` uses a 12-term atanh Taylor series for `ln` — accurate to
  ~1e-9, fine for scoring.
- BM25's length normalization makes the *shorter* matching doc win:
  for query `"quick fox"` the tutorial's doc1 (7 tokens) outscores
  doc0 (9 tokens) — `ranked=[[1,0.92],[0,0.87],[2,0]]`.
- `cosine_similarity` returns `0.0` (not an error) for disjoint vectors.

## One real bug the tutorial works around

`ascii_lower()` ran `let n = int(c)` *before* its A–Z comparison table.
`int()` on any non-digit character raises `ValueError`, so **every**
call to `tokenize` crashed — the whole module was unusable. The inlined
copy drops the dead line (the result was never used). Module bug
flagged for a fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/ranking_tutorial.ltl
python -m lateralus_lang check examples/ranking_tutorial.ltl
python -m pytest tests/test_ranking_tutorial.py -x -q
```
