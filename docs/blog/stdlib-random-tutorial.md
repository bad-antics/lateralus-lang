# Random Numbers with `stdlib/random.ltl`

Games, simulations, sampling, jitter — eventually every program needs
randomness. `stdlib/random.ltl` is the small wrapper that exposes
Lateralus's PRNG: uniform floats, inclusive integer ranges, choice,
sample, shuffle, and — critically for testing — `seed()` for
reproducible streams.

This tutorial covers the whole seven-function surface, the inclusive-vs-
exclusive range traps, why `shuffle` copies instead of mutating, and how
to pin randomness in tests. Companion:
`examples/random_tutorial.ltl`.

---

## Seeding: the most important function here

```text
random_seed(42)
random_float()  -> 0.6394267984578837   # same every run, everywhere
```

The generator is a Mersenne Twister — deterministic given a seed, stable
across runs and platforms. `random_seed(s)` reseeds the *global* stream:
every subsequent draw shifts the sequence, so the order of calls is part
of your program's observable behaviour. Call it once at startup (or in
test setup) and never again mid-computation unless you mean to fork the
stream.

## The function surface

| Function | Returns | Range semantics |
|---|---|---|
| `random()` | float | `[0.0, 1.0)` — never 1.0 |
| `uniform(lo, hi)` | float | `[lo, hi)` — same exclusion |
| `rand_int(lo, hi)` | int | `[lo, hi]` **inclusive both ends** |
| `choice(lst)` | element | uniform pick; errors on empty |
| `sample(lst, k)` | list | k **unique** elements, order random |
| `shuffle(lst)` | new list | permutation; **input untouched** |
| `seed(s)` | — | reseed the global stream |

Two traps worth memorizing:

1. **`rand_int` is inclusive, `uniform`/`random` are exclusive.** It's the
   Python `randint` vs `random` convention — `rand_int(1, 10)` can return
   10; `uniform(1.0, 10.0)` never does.
2. **`shuffle` does not mutate.** It builds a shuffled copy — your source
   list is still in original order afterwards (verified in STEP 4, where
   `orig` prints `[1,2,3,4,5]` after shuffling).

## Building blocks

`uniform` is one line of module code:

```text
uniform(lo, hi) = lo + random() * (hi - lo)
```

Affine scaling of a `[0,1)` draw. Same trick gives you `randrange`-style
ints (`lo + rand_int(0, hi-lo)`), exponential-ish waits, or any
distribution you can map through the CDF — though for anything serious
(Box-Muller gaussians, Dirichlet, etc.) prefer a dedicated library.

## Choice, sample, shuffle

- `choice` picks one element uniformly — `choice([])` raises rather than
  returning a sentinel, so guard empty lists yourself (the companion
  prints `<empty>` for demonstration).
- `sample(lst, k)` picks k **distinct** elements — it's a subset, not k
  independent draws. Asking for `k > len(lst)` errors.
- `shuffle` is Fisher-Yates on a copy — O(n), unbiased, and safe to call
  on shared data.

## Reproducible tests

Because the stream is seedable, the tutorial pins exact outputs:

```text
random_seed(42) -> random() = 0.6394267984578837
                 -> rand_int(1,10) = 1, then 5
random_seed(7)  -> uniform(10,20) = 13.238327648331623
random_seed(42) -> choice = "blue", sample = [2,1,6],
                   shuffle([1..5]) = [4,2,3,5,1]
random_seed(99) -> rand_int(1,100) = 52
```

Reseed before each section and the vectors stay readable — you're
demonstrating *the function*, not accumulating stream state.

## Running the companion

```text
=== LATERALUS STDLIB RANDOM TUTORIAL ===
STEP 1 random() = 0.6394267984578837
STEP 1 rand_int(1,10) x2 = 1, 5
STEP 2 uniform(10,20) = 13.238327648331623
STEP 2 uniform(-5,5) = -3.4915082607549808
STEP 3 choice = blue
STEP 3 choice(empty) = <empty>
STEP 4 shuffle = [4,2,3,5,1] orig still = [1,2,3,4,5]
STEP 5 sample([1..8],3) = [2,1,6]
STEP 6 different seed -> rand_int(1,100) = 52
PINNED_VECTORS: seed42_rand=0.6394267984578837 ints=1,5 uni=13.238327648331623,-3.4915082607549808 choice=blue sample=2,1,6 shuffle=4,2,3,5,1|1,2,3,4,5 seed99_1_100=52
```

`tests/test_random_tutorial.py` pins the transcript — if the PRNG
implementation ever changes, this test fails loudly instead of your
game's drop rates silently shifting.

## When (not) to use it

**Use it** for gameplay, simulations, sampling, jitter, load-testing
data — anywhere reproducibility or statistical quality at the "good
enough" level suffices.

**Don't use it** for anything security-adjacent: tokens, nonces,
passwords, session IDs. `stdlib/random.ltl` is a deterministic PRNG —
an attacker who observes enough outputs can reconstruct the state. For
those, the codegen exposes `random_bytes`/`random_token`/`random_urlsafe`
backed by `secrets` — reach for those instead.

That is `stdlib/random.ltl`: seven functions, one seed, and a companion
script that makes the whole stream reproducible.
