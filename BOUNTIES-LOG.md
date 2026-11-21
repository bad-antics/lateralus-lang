# Bounty claims log

- 2026-11-21 — recurring documentation tutorial bounty ($25): `stdlib/base64.ltl`
  tutorial at `docs/blog/stdlib-base64-tutorial.md` with runnable companion
  `examples/base64_tutorial.ltl` (RFC 4648 vectors, round-trips, URL-safe,
  is_valid, lengths) and pytest coverage in `tests/test_base64_tutorial.py`.
  Documents three runtime defects: missing char_code builtin, float `/`
  breaking sextet/byte math and int return types.
