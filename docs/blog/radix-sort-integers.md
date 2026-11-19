# Sorting integer lists with radix_sort

Use `stdlib/radix_sort.ltl` when your keys are integers within a fixed
width. This tutorial covers its three integer radix functions:

| Function | Valid input values (inclusive) | Byte passes |
| --- | --- | --- |
| `radix_sort_u32(xs)` | 0 to 4294967295 | 4 |
| `radix_sort_u64(xs)` | 0 to 18446744073709551615 | 8 |
| `radix_sort_i32(xs)` | -2147483648 to 2147483647 | 4, with sign mapping |

Each takes a list and returns its values in ascending order. Duplicates
remain in the result; an empty list returns `[]`, and a singleton keeps
its value. Choose the function for the range of **every** input value.
These are input contracts, not range checks performed by the module.
There is no signed 64-bit radix API in this module.

## Start with a pinned example

The complete example is [examples/radix_sort_tutorial.ltl](../../examples/radix_sort_tutorial.ltl):

```text
fn main() {
    print(radix_sort_u32([4294967295, 0, 3, 3, 1]))
    print(radix_sort_u64([18446744073709551615, 0, 4294967296]))
    print(radix_sort_i32([-2147483648, 0, 2147483647, -1]))
}
```

Its exact output is:

```text
[0, 1, 3, 3, 4294967295]
[0, 4294967296, 18446744073709551615]
[-2147483648, -1, 0, 2147483647]
```

The first vector preserves both copies of `3`. The second crosses the
32-bit boundary and includes the largest unsigned 64-bit value. The
third includes both signed 32-bit limits and puts negative values first.

## Run it from a source checkout

This recipe targets commit `599cda9f9f4d18d9054e8f315d117d3cb74126b8`
and Python 3.10+. At this baseline, the normal `import radix_sort` CLI
path fails to resolve the module. Instead, concatenate the unchanged
stdlib source with the example. The function names above are the direct
names in that combined source, without an import prefix.

From the repository root, run:

```sh
PYTHONPATH="$PWD" python - <<'PY'
from pathlib import Path
import subprocess
import sys
import tempfile

source = Path("stdlib/radix_sort.ltl").read_text()
example = Path("examples/radix_sort_tutorial.ltl").read_text()
with tempfile.TemporaryDirectory() as directory:
    program = Path(directory) / "radix_sort_example.ltl"
    program.write_text(source + "\n" + example)
    subprocess.run([sys.executable, "-m", "lateralus_lang", "run", str(program)],
                   check=True)
PY
```

`PYTHONPATH` also lets the generated Python program find the runtime
while the temporary Lateralus file lives outside the checkout. The CLI
invokes `main()`; the example needs no extra call to it. No installation
or additional dependency is needed for this source-checkout recipe.

## Why the passes work

`radix_pass` selects one byte with `(value >> shift) & 0xff`, puts each
value in one of 256 buckets, then collects buckets from 0 through 255.
Values enter each bucket in their existing order. That stability lets a
later, more significant byte pass preserve the order established by
earlier bytes. `radix_sort_u32` uses shifts 0, 8, 16 and 24;
`radix_sort_u64` continues through shift 56.

For signed 32-bit values, the module first maps each key with
`(value ^ 0x80000000) & 0xffffffff`. This maps the negative half into
the lower unsigned half: -2147483648 maps to 0, -1 to 2147483647,
0 to 2147483648, and 2147483647 to 4294967295. After the unsigned
sort, it flips the bit back and subtracts `1 << 32` where needed to
restore negative values. This explains why applying the unsigned API
directly to negative numbers is outside its contract.

## Check the vectors and edge cases

```sh
python -m unittest discover -s tests -p test_radix_sort_tutorial.py -v
```

The tests run the real CLI with combined source, assert its exit status
and exact output, and compare additional valid lists with Python's
`sorted`. They cover empty and singleton lists for all three APIs,
duplicate negative values, reversed inputs and byte boundaries. These
checks establish the examples' results; they make no speed comparison.
