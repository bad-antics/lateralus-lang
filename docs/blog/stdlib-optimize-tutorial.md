# Numerical Methods with `stdlib/optimize.ltl`

`stdlib/optimize.ltl` is a compact numerical-methods library: root
finding, integration, differentiation, 1D minimization, interpolation,
and fixed-point iteration — thirteen functions, all taking your
function as a first-class value.

This tutorial works through the whole module with problems whose exact
answers you already know, so every approximation can be checked against
ground truth. Companion: `examples/optimize_tutorial.ltl`.

---

## Functions as values

The module's signature move: every solver takes `f: fn` — your function
as an argument. `bisect(f_quad, 1.0, 2.0, 1e-12)` finds the root of
`x² − 2` without knowing anything about quadratics. Lateralus supports
first-class functions, so `f_quad`, `df_quad`, lambdas — anything
callable works.

## Root finding: three ways to √2

| Method | Idea | Result on x²−2, [1,2] |
|---|---|---|
| `bisect` | halve the interval, keep the sign-change half | `1.4142135623733338` |
| `newton` | follow the tangent line: `x − f(x)/f′(x)` | `1.4142135623730951` — exact to the last bit |
| `secant` | Newton with a finite-difference slope | `1.4142135623730954` |

Newton wins on convergence speed *when it converges* — it needs `f′`
and can diverge or hit a flat derivative (the module bails at
`|f′| < 1e-15`). Bisection is bulletproof but linear (≈1 bit per
iteration). Secant is the derivative-free middle ground. All three cap
at 100 iterations.

## Integration: trapezoid vs Simpson

∫₀¹ x² dx = 1/3 exactly. With n=100 panels:

```text
trapezoid = 0.33335000000000004    (error ~1.7e-5)
simpson   = 0.3333333333333334     (error ~1e-16 — machine precision)
```

Simpson's 1-4-2-1 weighting is exact for cubics, which is why it
crushes the trapezoid rule here — worth remembering before reaching for
the simpler method.

## Differentiation

```text
forward_diff(x², 3, h=1e-5)  = 6.000009999951316   (O(h) error)
central_diff(x², 3, h=1e-5)  = 6.000000000039306   (O(h²) — 100x better)
second_derivative(x², 3)     = 2.000000000279556   (f″ = 2 ✓)
```

Central differences cost two evaluations but buy an order of accuracy —
the classic accuracy-per-evaluation tradeoff.

## Minimization without derivatives

`golden_section_min` shrinks `[a,b]` by the golden ratio φ ≈ 0.618,
keeping the half containing the minimum — derivative-free, robust,
linear convergence. On `(x−2)²` over `[0,4]` it lands on
`1.9999999999999998`.

`gradient_descent_1d` is the other end of the spectrum: you supply
`df`, it takes fixed steps `x −= lr·df(x)`. On x² from x₀=5 with
lr=0.1, 50 steps → `7.1e-05` — converging to 0 geometrically (each step
multiplies the error by `1 − 2·lr = 0.8`).

## Interpolation and fixed point

- `lerp(a,b,t)` — linear blend; `bilinear` composes it over a unit
  square for 2D interpolation from four corners.
- `lagrange_interp(xs, ys, x)` — the polynomial through your points;
  three points of x² reproduce `2.25` at x=1.5 exactly.
- `fixed_point(g, x0, tol)` — iterate `x ← g(x)` until it stops moving;
  the Babylonian `g(x) = ½(x + 2/x)` converges to √2 from x₀=1 — a
  300-year-old root-finding algorithm that predates Newton.

## Running the companion

```text
STEP 1 root of x^2-2 = sqrt(2):
  bisect   = 1.4142135623733338
  newton   = 1.4142135623730951
  secant   = 1.4142135623730954
STEP 2 integrate x^2 on [0,1] (exact = 0.3333...):
  trapezoid n=100  = 0.33335000000000004
  simpson  n=100  = 0.3333333333333334
STEP 3 derivatives of x^2 at x=3 (f'=6, f''=2):
  forward = 6.000009999951316
  central = 6.000000000039306
  second  = 2.000000000279556
STEP 4 minimize (x-2)^2 on [0,4]:
  golden_section = 1.9999999999999998
STEP 5 interpolation:
  lerp(0,10,0.3) = 3.0
  bilinear center = 7.5
  lagrange x^2 at 1.5 = 2.25
STEP 6 fixed_point g(x)=0.5*(x+2/x) from 1.0:
  = 1.414213562373095
```

`tests/test_optimize_tutorial.py` pins every approximation to full
float precision — these aren't rounded "about right" values, they're
the exact IEEE-754 outputs, so any change to the algorithms trips the
test immediately.

## When to use it

**Use it** for scalar problems: root-finding a univariate equation,
quick integrals, derivatives for sensitivity analysis, 1D optimization,
small interpolations. The algorithms are textbook-correct and readable.

**Don't use it** for systems: no multivariate Newton, no ODE solvers,
no linear algebra beyond what `stdlib/linalg.ltl` gives you, no adaptive
stepping. For anything production-grade, these methods are the *right
algorithms* — pair them with your own convergence criteria and error
bounds, because the module's fixed iteration caps are teaching wheels.

That is `stdlib/optimize.ltl`: thirteen numerical methods, one
first-class-function trick, and answers you can verify to the last bit.
