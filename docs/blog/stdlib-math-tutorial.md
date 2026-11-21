# Extended Math with `stdlib/math.ltl`

Beyond `+ - * /`, real programs need sqrt, trig, logs, primes, and
number theory. `stdlib/math.ltl` implements them in pure Lateralus —
Newton-Raphson sqrt, Taylor-series trig/logs, and integer helpers.

This tutorial exercises the whole surface. Companion:
`examples/math_tutorial.ltl`.

---

## API tour

- **Constants:** `PI`, `E`, `TAU`, `PHI`, `INF`, `SQRT2`
- **Basics:** `abs_val`, `sqrt` (Newton), `pow`, `floor`, `ceil`,
  `round_val`, `clamp`, `sign`, `lerp`, `hypot`
- **Integer:** `factorial`, `gcd`, `lcm`, `is_prime`, `isqrt`,
  `fibonacci`
- **Transcendental:** `sin`, `cos`, `tan`, `radians`, `degrees`, `ln`,
  `log2`, `log10` — Taylor/minimax series, not libm

## Verified accuracy

- `sqrt(99)` → 9.9498743710662 (Newton converges to ~1e-7)
- `sin(PI/2)` → 1.0, `ln(E)` → 0.9999999999999255
- `is_prime(97)` true, `is_prime(91)` false; `gcd(48,18)`=6,
  `fibonacci(10)`=55

## Quirk documented

`lcm` is annotated `-> int` but computes `(a*b)/gcd` — `/` yields
float, so `lcm(4,6)` returns `12.0`. (The `/`→float codegen class is
being fixed centrally in PR #404.)

## Running the tutorial

```bash
python -m lateralus_lang run examples/math_tutorial.ltl
python -m lateralus_lang check examples/math_tutorial.ltl
python -m pytest tests/test_math_tutorial.py -x -q
```
