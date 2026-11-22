# Bounty claims log

- 2026-11-21 — recurring documentation tutorial bounty ($25): `stdlib/ranking.ltl`
  tutorial at `docs/blog/stdlib-ranking-tutorial.md` with runnable companion
  `examples/ranking_tutorial.ltl` (tokenize/term_freq, build_index,
  BM25 rank, TF-IDF cosine) and pytest coverage in
  `tests/test_ranking_tutorial.py`. Documents fatal `int(c)` crash in
  ascii_lower (worked around by removing dead line).
