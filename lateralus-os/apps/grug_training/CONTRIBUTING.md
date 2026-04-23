# Contributing to grugbot420 training data

Grug is data-driven. To teach grug new tricks you do **not** need to
touch any C code — just edit the plain-text files in this directory and
rebuild the OS. The build invokes
[`tools/gen_grug_corpus.py`](../../tools/gen_grug_corpus.py) which
compiles them into `gui/grug_corpus.h` for the kernel to consume.

## Files

| File | What it teaches | Format |
|---|---|---|
| `wisdom.txt` | Random sayings emitted by `/wisdom` and as the unmatched-input fallback. | One quote per line. |
| `jokes.txt`  | Random response to `/joke` and inputs containing "joke" / "funny". | One joke per line. |
| `smoke.txt`  | Random response to `/smoke` and 420-related inputs. | One vibe per line. |
| `rules.txt`  | Keyword → response. Scanned **before** the hardcoded keyword ladder. | `kw1,kw2,kw3=>response text` |

Lines starting with `#` and blank lines are ignored everywhere.

## Style guide

- Stay in character: lowercase, simple verbs, third-person grug.
- Keep each line **≤ 78 characters** (terminal-friendly).
- No double-quotes inside lines (escaped automatically, but harder to read).
- Use ASCII only — the kernel framebuffer renders a subset of CP437.
- Rules use **case-insensitive substring match**; pick keywords that are
  unlikely to false-positive on common english words. Prefer specific
  terms (`postgres` ✅) over generic ones (`db` 👀).

## Testing

After editing:

```bash
python3 tools/gen_grug_corpus.py            # regenerate header
python3 -m pytest tests/test_gen_grug_corpus.py
./build_and_boot.sh --iso                    # full build
./build_and_boot.sh --gui                    # boot QEMU + grug
```

Inside the running OS type `/stats` to confirm grug picked up your
additions, then exercise the new keywords.

## Counts

Live counts are emitted on every kernel boot in the format
`[trained] {wisdom}w/{jokes}j/{smoke}s/{rules}r`.
