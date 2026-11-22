# String Utilities with `stdlib/strings.ltl`

`stdlib/strings.ltl` is the everyday string toolbox: case
conversion, whitespace trimming, substring search, splitting and
joining, padding, reversal, digit checks, and zero-padded integer
formatting. Most functions are thin, correct wrappers over builtin
string ops; a handful (`ltrim`, `rtrim`, `repeat_str`, `pad_left`,
`pad_right`, `str_reverse`, `is_digits`, `format_int`) are implemented
in pure Lateralus — good reading for anyone learning the language.

Companion: `examples/strings_tutorial.ltl`.

---

## The API surface

| Group | Functions |
|---|---|
| Case | `upper`, `lower` |
| Trimming | `trim`, `ltrim`, `rtrim` — trims space/tab/newline |
| Predicates | `contains`, `starts_with`, `ends_with`, `is_digits` |
| Search | `index_of` (via `s.find`), `count` (via `s.count`) |
| Transform | `replace`, `split`, `join`, `repeat_str`, `str_reverse` |
| Padding/format | `pad_left`, `pad_right`, `format_int` |

## Pure-Lateralus implementations worth reading

- **`ltrim`/`rtrim`** — manual index walk over `' '`, `'\t'`, `'\n'`
  then a single `slice`. No regex needed.
- **`pad_left`/`pad_right`** — `while len(result) < width` prepend or
  append the fill char. O(width) string builds; fine for labels,
  log columns, fixed-width dumps.
- **`is_digits`** — lexicographic char compare `c < "0" || c > "9"`.
  Empty string returns `false` — matches most validation needs.
- **`format_int(n, width)`** — `pad_left(to_str(n), width, "0")`,
  i.e. zero-padded numbers like `000042`.

## Verified results

```text
str_trim("  Hello, Lateralus!  ")  -> "Hello, Lateralus!"
"the quick brown fox".find("brown") -> 10 ; .count("o") -> 2
str_split("alpha,beta,gamma,delta", ",") -> 4 parts
str_join(parts, "|") -> "alpha|beta|gamma|delta"
repeat "ab" x3 -> "ababab" ; pad_left("7",5,"0") -> "00007"
reverse("lateralus") -> "sularetal"
is_digits("007") -> true ; is_digits("12a") -> false
format_int(42, 6) -> "000042"
```

`tests/test_strings_tutorial.py` pins all of the above.

## Known upstream issue (documented, worked around)

`str_reverse` is **broken under the Python runtime shim**:

```text
str_reverse -> split(s, "") -> str_split -> s.split("")
             -> ValueError: empty separator
```

Python's `str.split` rejects an empty separator, and the shim maps
`str_split` directly onto it. The tutorial reverses by indexing
chars manually instead. A one-line upstream fix would special-case
`sep == ""` to `list(s)` before reversing — flagged as a candidate
small-fix bounty.

## When to use it

**Use it** for log formatting, CLI output alignment, CSV field
splitting, and input validation — anywhere you need predictable
string shaping without pulling in a regex engine.

**Don't expect** Unicode-aware case folding (`str_upper` is
ASCII-oriented under the shim), grapheme-cluster-safe reversal, or
locale-aware trimming — this module trims only space/tab/newline.

That is `stdlib/strings.ltl`: the small, dependable string layer
every other stdlib module builds on.
