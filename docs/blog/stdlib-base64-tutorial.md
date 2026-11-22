# Base64 Encoding with `stdlib/base64.ltl`

Base64 turns binary data into ASCII-safe text — everywhere from data
URLs to HTTP headers. `stdlib/base64.ltl` implements RFC 4648 encoding
and decoding in pure Lateralus, plus URL-safe variants and validators.

This tutorial verifies the implementation against the RFC 4648 test
vectors. Companion: `examples/base64_tutorial.ltl`.

---

## API

- `encode(data)` / `decode(encoded)` — standard alphabet with `=` padding
- `encode_url` / `decode_url` — `+`→`-`, `/`→`_` for URL contexts
- `is_valid(s)` — alphabet + length check
- `encoded_length(n)` / `decoded_length(s)` — size math

## Bugs found while building the tutorial

The module as shipped **cannot run** — three defects, all worked around
in the inlined copy and flagged for a module fix PR:

1. `char_code()` is not a runtime builtin (`NameError`) — replaced with
   `ord()`.
2. `/` yields float in Lateralus, so sextet math like `b0 / 4` produced
   floats that cannot index `CHARS` and `chr()` rejects — rewritten with
   `>>` / `%` integer ops.
3. `encoded_length` returned `((n + 2) / 3) * 4` — a float despite the
   `-> int` annotation — rewritten as an integer loop.

## Verified vectors

All seven RFC 4648 vectors pass (`""`→`""`, `"f"`→`"Zg=="`, …,
`"foobar"`→`"Zm9vYmFy"`), decode round-trips all inputs,
`encode_url(">>>")` → `"Pj4-"` (exercises the `+`→`-` path), and
`is_valid` rejects bad alphabet and bad length.

## Running the tutorial

```bash
python -m lateralus_lang run examples/base64_tutorial.ltl
python -m lateralus_lang check examples/base64_tutorial.ltl
python -m pytest tests/test_base64_tutorial.py -x -q
```
