# Bounty claims log

- 2026-11-21 — recurring port micro-bounty ($25): `examples/ports/n_queens.ltl`
  (port of ~40-line Python N-Queens counter; compiles with `lateralus c`,
  C99 backend 0.106s vs CPython 1.63s at n=13, identical output 73712).

- 2026-11-22 — recurring documentation tutorial bounty ($25): `stdlib/iter.ltl`
  tutorial at `docs/blog/stdlib-iter-tutorial.md` with runnable companion
  `examples/iter_tutorial.ltl` (iterator-as-tagged-map representation,
  all constructors/transforms/terminals, flat_map list contract,
  lambda closure scoping gotcha) and pytest coverage in
  `tests/test_iter_tutorial.py`.
