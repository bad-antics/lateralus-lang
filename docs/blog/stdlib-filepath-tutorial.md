# Path Manipulation with `stdlib/filepath.ltl`

Every tool that touches files needs path math: split dir/base, strip or
swap extensions, join components, and normalize `.`/`..` segments.
`stdlib/filepath.ltl` implements the common subset in pure string ops.

This tutorial exercises the full API. Companion:
`examples/filepath_tutorial.ltl`.

---

## API

- **Components:** `dirname`, `basename`, `extension` (last dot only),
  `stem`
- **Construction:** `join_path(parts)` — strips duplicate slashes
- **Normalization:** `normalize` — collapses `//`, resolves `.` and
  `..` (keeps leading `..` for relative paths that escape)
- **Queries:** `is_absolute`, `is_relative`, `has_extension`,
  `with_extension`

## Bugs found while building the tutorial

The module needed three runtime workarounds, all inlined and flagged
for a module fix PR:

1. `substring()` → `slice()` (the runtime builtin is `slice`)
2. `split()` is not a runtime builtin → local `_split` helper added
3. `normalize`'s `if part == "." || part == ""` branch contained only a
   comment — transpiles to an empty Python `if` → `IndentationError`;
   a no-op statement fills the branch

## Running the tutorial

```bash
python -m lateralus_lang run examples/filepath_tutorial.ltl
python -m lateralus_lang check examples/filepath_tutorial.ltl
python -m pytest tests/test_filepath_tutorial.py -x -q
```
