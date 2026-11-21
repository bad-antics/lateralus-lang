# Colors as Integers: `stdlib/color.ltl` in Practice

CSS gives you `#ff7f50`. Lateralus gives you `16744144`. `stdlib/color.ltl`
stores every color as a single packed integer — `0xRRGGBB` for opaque
colors, `0xAARRGGBB` when alpha matters — which makes colors first-class
values you can store in lists, sort, compare, and pass around without
allocating objects.

This tutorial unpacks the representation, walks every public function, and
pins the behaviour with a runnable companion script
(`examples/color_tutorial.ltl`) and pytest coverage.

---

## The packed representation

```text
rgb(r, g, b)  = r·65536 + g·256 + b        # 0xRRGGBB
rgba(r,g,b,a) = a·16777216 + rgb(r,g,b)    # 0xAARRGGBB
```

Every channel is clamped to `[0, 255]` on the way in, so
`rgb(300, -5, 128)` silently becomes `#ff0080` — convenient, but it means
out-of-range inputs never error. If you need strict validation, clamp (or
reject) before calling `rgb`.

Extraction is the mirror image — shifts become divides and masks become
mods:

```text
red(c)   = floor(c / 65536) % 256
green(c) = floor(c / 256) % 256
blue(c)  = c % 256
alpha(c) = floor(c / 16777216) % 256
```

`alpha()` returns `0` for colors built with `rgb()` — there is no implicit
"opaque" flag; the alpha byte simply reads as zero. `to_hex` formats the
three colour channels as `#rrggbb` lowercase, ignoring alpha entirely.

## The manipulation functions

All of them decompose → transform → recompose through `rgb`, so clamping
and packing stay in one place:

- **`lighten(c, f)`** — moves each channel `f` of the way toward 255:
  `c + int((255 − c) · f)`. `f = 0.25` on coral (`#ff7f50`) gives `#ff9f7b`.
- **`darken(c, f)`** — scales each channel by `1 − f`:
  `int(c · (1 − f))`. Same input, `f = 0.25` → `#bf5f3c`.
- **`mix(a, b, r)`** — per-channel lerp `a·(1−r) + b·r`. `mix(coral,
  teal, 0.5)` → `#7f7f68`.
- **`invert(c)`** — channel-wise complement `255 − c`. Inverting teal
  (`#008080`) yields `#ff7f7f` — note it is *not* the same as swapping to
  the "opposite" hue on a colour wheel; it's a per-channel bit flip.
- **`grayscale(c)`** — Rec.601 luma `0.299·R + 0.587·G + 0.114·B`, the
  same coefficients NTSC television used, chosen to match human brightness
  perception better than a naive average.

## Named constants

The module predefines the eight CSS basics as `pub const` values:

```text
BLACK 0x000000   WHITE 0xFFFFFF   RED 0xFF0000   GREEN 0x00FF00
BLUE 0x0000FF    YELLOW 0xFFFF00 CYAN 0x00FFFF  MAGENTA 0xFF00FF
```

Because they're plain ints, you can do arithmetic on them —
`GREEN + 0x0000FF` — though for anything non-trivial `mix` is clearer.

## Running the companion script

```text
=== LATERALUS STDLIB COLOR TUTORIAL ===
STEP 1: rgb(255,127,80) = #ff7f50  (r=255 g=127 b=80)
STEP 2: rgba(200,30,30,128) = #c81e1e  (r=200 g=30 b=30)
STEP 3: to_hex round-trip #FF7F50 -> #ff7f50
STEP 4: lighten(coral, 0.25) = #ff9f7b
STEP 5: darken(coral, 0.25) = #bf5f3c
STEP 6: mix(coral, teal, 0.5) = #7f7f68
STEP 7: invert(teal) = #ff7f7f
STEP 8: grayscale(coral) = #9f9f9f
STEP 9: clamp test rgb(300,-5,128) = #ff0080
PINNED_VECTORS: coral=#ff7f50 lighten25=#ff9f7b darken25=#bf5f3c mix=#7f7f68 invert_teal=#ff7f7f gray_coral=#9f9f9f
```

Every step is pinned by `tests/test_color_tutorial.py`, including the two
subtleties most likely to bite: `int()` truncation (lighten adds
`int(128·0.25) = 32`, not 32.5) and the Rec.601 weights producing `#9f9f9f`
rather than the naive-average `#a0a0a0`.

## When packed ints win — and when they don't

**Use `stdlib/color.ltl`** for UI theming, chart palettes, terminal
colours, and anywhere a color is data: the int representation sorts,
compares, hashes, and serialises for free.

**Don't use it** for colour science: there is no gamma correction, no
OKLab/CIELAB perceptual space, no alpha compositing (`rgba` stores alpha
but nothing blends two translucent colours). For those you want a
float-triple pipeline — this module is deliberately the "CSS hex colour"
subset, and its value is exactly that focus.

That is `stdlib/color.ltl` end to end: one packed-int invariant, fourteen
public functions plus eight constants, and a companion script that pins
every transformation so you can verify the module against your own
expected hex values.
