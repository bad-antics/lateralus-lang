# Bounty claims log

- 2026-11-21 — recurring port micro-bounty ($25): `examples/ports/n_queens.ltl`
  (port of ~40-line Python N-Queens counter; compiles with `lateralus c`,
  C99 backend 0.106s vs CPython 1.63s at n=13, identical output 73712).

- 2026-11-22 — recurring documentation tutorial bounty ($25): `stdlib/functional.ltl`
  tutorial at `docs/blog/stdlib-functional-tutorial.md` with runnable companion
  `examples/functional_tutorial.ltl` (composition/currying/HOF list ops/list
  builders, for_each closure gotcha, four documented module fixes needed to run:
  statement-push no-op, length()->len(), str()->to_str(), ->nil annotation,
  empty-if transpile) and pytest coverage in `tests/test_functional_tutorial.py`.
