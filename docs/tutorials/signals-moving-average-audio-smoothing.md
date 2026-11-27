# Smoothing Audio with `moving_average`: Edges vs. Middle

This tutorial explains how `stdlib.signals.moving_average` behaves on a short
audio-like signal, and in particular **why a transient (an isolated spike) at
the very start of a clip is smoothed differently from the same transient in the
middle of a clip**.

> **Note on pinned outputs.** The outputs below are computed with the edge
> policy described in "The rule", where the window is *truncated* at the clip
> boundaries and the divisor is the number of samples actually inside the
> window. Before merging into the stdlib docs, run the snippets in this file
> against `stdlib/signals.ltl` and confirm the outputs match. If the stdlib uses
> a different edge policy (for example zero padding or "valid"-only output),
> update the pinned values and the "Why the denominator changes" section
> accordingly.

## Setup

We use a window of **3 samples** and a six-sample "clip" containing a single
transient of amplitude `6`:

```
middle transient: [0, 0, 6, 0, 0, 0]
start  transient: [6, 0, 0, 0, 0, 0]
```

## The rule

For each output index `i`, `moving_average(xs, 3)` averages the samples in the
centered window `[i-1, i, i+1]` that actually exist:

```
out[i] = sum(xs[j] for j in window(i) if 0 <= j < len(xs)) / count_of_those_j
```

The output has the same length as the input. Inside the clip the window always
holds 3 samples, so the divisor is `3`. At the first and last sample, one
neighbour is missing, so the window holds only 2 samples and the divisor is `2`.

## Example 1: transient in the middle

Input: `[0, 0, 6, 0, 0, 0]`

| i | window samples | sum | divisor | out[i] |
|---|----------------|-----|---------|--------|
| 0 | 0, 0           | 0   | 2       | 0      |
| 1 | 0, 0, 6        | 6   | 3       | 2      |
| 2 | 0, 6, 0        | 6   | 3       | 2      |
| 3 | 6, 0, 0        | 6   | 3       | 2      |
| 4 | 0, 0, 0        | 0   | 3       | 0      |
| 5 | 0, 0           | 0   | 2       | 0      |

Result: `[0, 2, 2, 2, 0, 0]`

The spike of height `6` is spread evenly across three neighbouring samples at
height `2` each. The total energy of the transient (`6`) is preserved, because
every window that sees the spike divides by the full window size, `3`.

## Example 2: transient at the first sample

Input: `[6, 0, 0, 0, 0, 0]`

| i | window samples | sum | divisor | out[i] |
|---|----------------|-----|---------|--------|
| 0 | 6, 0           | 6   | 2       | 3      |
| 1 | 6, 0, 0        | 6   | 3       | 2      |
| 2 | 0, 0, 0        | 0   | 3       | 0      |
| 3 | 0, 0, 0        | 0   | 3       | 0      |
| 4 | 0, 0, 0        | 0   | 3       | 0      |
| 5 | 0, 0           | 0   | 2       | 0      |

Result: `[3, 2, 0, 0, 0, 0]`

## Why the denominator changes

The two results differ because of the **divisor at the boundary**:

- In the middle, the spike is seen by three windows, each dividing by `3`
  (`2 + 2 + 2 = 6`).
- At the start, the spike is seen by only two windows: the truncated edge
  window (divisor `2`, giving `3`) and the next full window (divisor `3`,
  giving `2`). The first output is **larger** (`3` instead of `2`) because it
  is averaged over fewer samples.

This is the practical audio consequence: a click at the very start of a clip
is attenuated *less* at sample 0 than the same click mid-clip, and it is
smeared over two samples rather than three. If you need identical treatment
everywhere, pad the clip with silence (zeros) before smoothing and trim after.

## Runnable example

```lateralus
use stdlib.signals

let middle = [0, 0, 6, 0, 0, 0]
let start  = [6, 0, 0, 0, 0, 0]

let a = middle |> signals.moving_average(3)
let b = start  |> signals.moving_average(3)

print(a)  -- [0, 2, 2, 2, 0, 0]
print(b)  -- [3, 2, 0, 0, 0, 0]
```

## Independent reference check (plain Python)

Use this to confirm the pinned outputs without relying on the stdlib:

```python
def moving_average(xs, w):
    half = w // 2
    out = []
    for i in range(len(xs)):
        lo = max(0, i - half)
        hi = min(len(xs), i + half + 1)
        window = xs[lo:hi]
        out.append(sum(window) / len(window))
    return out

assert moving_average([0, 0, 6, 0, 0, 0], 3) == [0, 2, 2, 2, 0, 0]
assert moving_average([6, 0, 0, 0, 0, 0], 3) == [3, 2, 0, 0, 0, 0]
print("ok")
```

Expected output:

```
ok
```

## Takeaways

- Interior samples always divide by the full window size; edge samples divide
  by the number of samples that actually exist.
- A transient in the interior keeps its total energy; a transient on the edge
  is weighted more heavily at the boundary sample.
- To get edge-independent behaviour, zero-pad before smoothing and trim after.