# Ports

Idiomatic programs from other languages, ported to Lateralus with no external
dependencies, per the recurring port micro-bounty in `BOUNTIES.md`. Each port
keeps the original's algorithm and constants, and the verification notes below
record how parity and wall time were measured.

## nbody

`nbody.py` — Sun plus the four Jovian planets, symmetric symplectic integrator,
eight parallel arrays, about fifty lines. Reports total energy per unit mass at
n = 500,000 timesteps of 0.01 days.

`nbody.ltl` — same algorithm, same constants, same array layout.

Energies are printed as integers scaled by 1e9 rather than as decimal strings:
Lateralus has no `printf`, and scaling keeps the cross-language comparison exact
instead of approximate.

### Verification

```
$ python3 examples/ports/nbody.py
-4286150
-4285578

$ lateralus c examples/ports/nbody.ltl -o nbody.c && gcc -O2 -o nbody nbody.c -lm && ./nbody
-4286150
-4285578
```

Identical, at n = 500,000.

`lateralus run examples/ports/nbody.ltl` also produces both numbers, at about
150x the C time — the interpreter is a tree walker, and 500,000 steps through
five bodies is well past what it is for. The size is chosen for the C backend,
as the bounty rules require.

### Wall time, n = 500,000

| | time |
|---|---|
| CPython 3.14 | 4.25 s |
| Lateralus → C99, `gcc -O2` | **0.05 s** |

~85x. Three consecutive runs each reported 0.05 s real.

### Notes for whoever ports the next one

Two shapes are worth knowing before writing code against the C backend:

- The loops live in `main()` rather than in functions taking lists. A `list`
  parameter still has no element type, so `xs[i]` inside such a function unpacks
  to `ltl_value_t` and does not compile in scalar context.
- `PI` and `SOLAR_MASS` are written out at each use instead of being top-level
  `let`s. A top-level `let` becomes a C global, and a global initialised from
  another global is not a compile-time constant.

Both are backend limitations, not language ones, and both are worth fixing
rather than working around forever.
