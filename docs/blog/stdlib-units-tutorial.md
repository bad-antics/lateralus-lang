---
title: "Dimensional Analysis & SI Unit Conversion: Type-Safe Physical Quantities in Lateralus"
description: "A deep-dive tutorial on stdlib/units.ltl — enforcing dimensional homogeneity across SI base and derived units (length, mass, time, energy, pressure) with affine temperature conversions."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["units", "physics", "dimensional-analysis", "si-units", "standard-library"]
---

# Dimensional Analysis & SI Unit Conversion: Type-Safe Physical Quantities in Lateralus

Adding meters to kilograms or mixing Imperial and SI units (as in the 1999 Mars Climate Orbiter loss) causes catastrophic engineering failures.

The **`stdlib/units.ltl`** module models physical quantities as a tuple $(v, \mathbf{d})$ consisting of a scalar magnitude normalized to SI base units and a 5-component dimension exponent vector $\mathbf{d} = (L, M, T, \Theta, I)$ representing Length ($\text{m}$), Mass ($\text{g/kg}$), Time ($\text{s}$), Temperature ($\text{K}$), and Current ($\text{A}$).

---

## 1. Dimensional Algebra

Given two physical quantities $Q_1 = (v_1, \mathbf{d}_1)$ and $Q_2 = (v_2, \mathbf{d}_2)$:

- **Addition / Subtraction** (valid if and only if $\mathbf{d}_1 = \mathbf{d}_2$):
  $$Q_1 \pm Q_2 = (v_1 \pm v_2,\; \mathbf{d}_1)$$
- **Multiplication**:
  $$Q_1 \cdot Q_2 = (v_1 \cdot v_2,\; \mathbf{d}_1 + \mathbf{d}_2)$$
- **Division**:
  $$\frac{Q_1}{Q_2} = \left(\frac{v_1}{v_2},\; \mathbf{d}_1 - \mathbf{d}_2\right)$$

For example, dividing Length $\mathbf{d}_L = (1, 0, 0)$ by Time $\mathbf{d}_T = (0, 0, 1)$ yields Velocity $\mathbf{d}_v = (1, 0, -1)$, and multiplying Mass $(0, 1, 0)$ by Acceleration $(1, 0, -2)$ yields Force in Newtons $\mathbf{d}_F = (1, 1, -2)$.

---

## 2. Runnable Lateralus Implementation

From `examples/units_tutorial.ltl`:

```ltl
pub fn make_qty(val, dim_l, dim_m, dim_t) {
    let q = dict()
    q["val"] = val
    q["L"] = dim_l
    q["M"] = dim_m
    q["T"] = dim_t
    return q
}

pub fn qty_mul(a, b) {
    return make_qty(a["val"] * b["val"], a["L"] + b["L"], a["M"] + b["M"], a["T"] + b["T"])
}

pub fn qty_div(a, b) {
    return make_qty(a["val"] / b["val"], a["L"] - b["L"], a["M"] - b["M"], a["T"] - b["T"])
}
```

---

## 3. Pinned Verification Vectors

| Physical Formula | Input Quantities | Resulting SI Value | Dimension Vector $(L, M, T)$ |
| :--- | :--- | :--- | :--- |
| Velocity $v = d / t$ | $1500\text{ m} / 50\text{ s}$ | $30\text{ m/s}$ | $(1, 0, -1)$ |
| Force $F = m \cdot a$ | $12\text{ kg} \cdot 10\text{ m/s}^2$ | $120\text{ N}$ | $(1, 1, -2)$ |
| Kinetic Work $E = F \cdot d$ | $120\text{ N} \cdot 25\text{ m}$ | $3000\text{ J}$ | $(2, 1, -2)$ |
| Celsius to Kelvin | $100^\circ\text{C}$ (scaled $\times 100$) | $37315$ ($373.15\text{ K}$) | $(0, 0, 0, 1)$ |
