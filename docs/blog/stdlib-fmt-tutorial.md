# Formatting with `stdlib/fmt.ltl`

`stdlib/fmt.ltl` is the printf-family module: `{}` placeholder
substitution (`sprintf`/`printf`), specifier-driven `format()`
(`"05d"`, `".2f"`, `"x"`), padding/alignment (`pad_left`,
`pad_right`, `center`), base conversion (`hex`, `bin`, `oct`),
`repeat`/`join`, and an auto-width `table` renderer for rows of
cells. ~200 lines.

Companion: `examples/fmt_tutorial.ltl`.

---

## `sprintf` — the `{}` protocol

Scans the template; on `{}` it appends `str(args[arg_idx])` and
advances. Extra `{}`s with no remaining args are emitted literally —
verified: `sprintf("missing {} args {} {}", ["only"])` →
`missing only args {} {}`. No positional or format-spec support —
it's `str()` substitution only.

## Padding and alignment

- `pad_left/right(s, width, fill)` — loop-prepend/append until
  `len == width`; no truncation if `s` is already wider.
- `center(s, width, fill)` — `left = diff/2`, `right = diff-left`
  (extra char goes right on odd diffs).

## Base conversion

`hex(n, upper)`, `bin(n)`, `oct(n)` all share one shape: repeated
`val % base` prepend + `val / base` until zero, `-` prefix for
negatives, `"0"` for zero. Verified: `hex(255)="ff"`,
`hex(-255)="-ff"`, `bin(42)="101010"`, `oct(42)="52"`, `bin(-5)="-101"`.

## `table(rows, sep)`

Two passes: first compute each column's max `len(str(cell))`, then
pad every cell right and join with the separator. Verified output:

```text
Name  | Age
Alice | 30
Bo    | 4
```

## ⚠️ Runtime-shim gaps found (worked around)

1. **`__builtin_format` doesn't exist** in the Python shim —
   `format(value, spec)` can't run; `sprintf` covers the demo need.
2. **Float division strikes again**: upstream `hex`/`bin`/`oct` do
   `val = val / 16` → float → `chars[val % 16]` raises
   `TypeError` (float index). `center`'s `diff / 2` → float `n` in
   `range()` also breaks. Tutorial uses `int(...)` throughout —
   fourth confirmed instance of the `/`-is-float bug family.
3. **`{}` literals can't appear in source strings** — the codegen
   f-string chokes on them; templates built via `chr(123)`/`chr(125)`.
4. `let mut`, ternary `?:`, `for x in range(...)` are module-file
   conveniences; the companion uses `let` + `while`.

## When to use it

**Use it** for log lines, CLI tables, aligned reports, hex dumps —
anywhere `{}` substitution or fixed-width columns beat raw `+`.

**Don't expect** printf `%`-style specs in `sprintf` (that's
`format()`'s job, pending the builtin), Unicode width-aware
padding, or `{:.2f}` precision — this module is deliberately small.

That is `stdlib/fmt.ltl`: the little formatter that makes Lateralus
output readable.
