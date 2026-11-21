# Tar Archives with `stdlib/tar.ltl`

The tar format is almost suspiciously simple: a sequence of 512-byte
headers, each followed by the file data padded to a 512 boundary,
terminated by two zero blocks. Fields are fixed offsets, numbers are
octal ASCII, and a checksum field ties it together.
`stdlib/tar.ltl` implements a complete ustar reader and writer in
~220 lines — entries as plain maps, bytes as byte lists.

This tutorial builds an archive, reads it back, and verifies every
field. Companion: `examples/tar_tutorial.ltl`.

---

## The 512-byte header

```text
0    name        100 bytes  NUL-terminated
100  mode         8 bytes   octal ASCII
108  uid          8 bytes   octal
116  gid          8 bytes   octal
124  size        12 bytes   octal
136  mtime       12 bytes   octal
148  chksum       8 bytes   octal, computed with field as spaces
156  typeflag     1 byte    "0" file, "1" link, "2" symlink, "5" dir
157  linkname   100 bytes
257  magic        6 bytes   "ustar"
263  version      2 bytes   "00"
265  uname/gname/devmajor/devminor (unused here)
345  prefix     155 bytes   for names > 100 chars
```

`write_entry` zero-fills the header, writes each field with
`put_str`/`put_oct` (octal padded with leading zeros + trailing
space), computes the checksum over the header with bytes 148–155
treated as spaces, then stores it back and sets byte 155 to space —
the POSIX checksum convention.

## Read path

`read(archive)` walks blocks: an all-zero header ends the archive
(the standard two-block terminator collapses to "first zero block").
Name resolution handles the ustar `prefix/name` split for long
paths. `octal()` skips non-octal bytes defensively. After each
entry's data, the reader skips `size % 512` padding.

## Write path

`write(entries)` concatenates `write_entry` output plus two 512-byte
zero blocks. Each entry is a map — `{name, bytes, mode, mtime,
type, link}` all optional except `name`:

- `type` defaults to regular file (`"0"`); use `type_dir()` (`"5"`)
  for directories (trailing `/` in name is conventional)
- `mode` defaults to 0644, `mtime` to 0
- `bytes` defaults to empty — directories and symlinks carry none

## Verified round-trip

```text
archive: 3 entries -> 3072 bytes (hdr+pad per entry + 1024 zero tail)
e1 hello.txt  size=6  mode=0644  mtime=1700000000  bytes="hi tar"
e2 docs/      type="5" (dir)
e3 latest     type="2" link="hello.txt" (symlink)
magic@257 = "ustar", version "00"
```

`tests/test_tar_tutorial.py` pins the byte count, header magic,
checksum field layout, and every decoded field.

## When to use it

**Use it** to read/write tar archives in pure Lateralus — packaging,
bundling, fixture generation — without shelling out to `tar`.

**Don't expect** GNU longname (`././@LongLink`) extensions, sparse
files, PAX extended headers, or compression (that's gzip's job —
`stdlib/compress`/`gzip` handle the outer layer). Names > 100 chars
need the prefix field, which `write_entry` doesn't populate — keep
names short or split manually.

That is `stdlib/tar.ltl`: 512-byte headers, octal fields, and a
checksum — the whole format, readable in one sitting.
