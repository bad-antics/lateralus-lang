# I/O Helpers with `stdlib/io.ltl` — and an Honest Status Report

`stdlib/io.ltl` mixes three layers: console helpers (`read_line`,
`prompt`, `read_int`, `read_float`), file operations
(`read_file`/`write_file`/`append_file`/`file_exists`/`lines_of`)
dispatched through `_host_*` compiler intrinsics, and pure string
helpers (`split_lines`, `basename`, `dirname`, `path_join`,
`extension`, `print_table`).

This tutorial covers what actually runs today — and documents two
helpers that are **incomplete upstream**.

Companion: `examples/io_tutorial.ltl`.

---

## What works

### `split_lines(s)`

Hand-rolled `\n` splitter — no empty trailing element when the text
ends with a newline. Verified: `"alpha\nbeta\ngamma"` → 3 lines;
`"one\ntwo\n"` → 2 lines.

### `basename(path)`

Scans for the last `/` or `\` and returns what follows. Verified:
`/var/log/app.log` → `app.log`, `C:\temp\x.bin` → `x.bin`,
`no-slash.txt` → `no-slash.txt`.

### `path_join(base, name)`

Appends `/` only when `base` doesn't already end in a separator.
Verified: `("/var/log","app.log")` → `/var/log/app.log`,
`("/var/log/","x")` → `/var/log/x`, `("","name")` → `name`.

## ⚠️ Two helpers are incomplete upstream

The module's own comments admit it — both functions locate the
right index and then return the wrong slice:

```text
dirname("/var/log/app.log")
  upstream -> "/var/log/app.log"   (returns the WHOLE path;
             comment: "requires str slicing")
  fixed    -> "/var/log"

extension("app.log")
  upstream -> "app.log"            (returns the basename;
             comment: "requires str slicing")
  fixed    -> ".log"   ("x.tar.gz" -> ".gz", "noext" -> "")
```

The tutorial implements both versions side-by-side so the bug is
visible in the output, not just asserted in prose. One-line fixes:
`slice(path, 0, last_slash)` and `slice(b, dot_idx, len(b))` —
flagged as small-fix bounty candidates (two birds, one PR).

## File ops — compiler intrinsics

`read_file`/`write_file`/`append_file`/`file_exists`/`lines_of`
dispatch to `_host_read_file`/`_host_write_file`/`_host_file_exists`,
which the Python transpiler resolves to host `open()`/`pathlib`.
They can't be exercised from a portable `ltlc run` example — noted
here so nobody expects a demo that can't exist yet.

## When to use it

**Use it** for `split_lines`/`basename`/`path_join` today; treat
`dirname`/`extension` as broken until the slicing TODOs land; use
the file ops only in compiled programs where the host intrinsics
are wired.

**Don't expect** stdin prompting to work headless, cross-platform
separator normalization beyond `/`+`\`, or `..`/`.` path resolution
— `path_join` is string concat, not a path algebra.

That is `stdlib/io.ltl`: half a path library, two honest TODOs,
and a clear map of what the runtime can and can't do yet.
