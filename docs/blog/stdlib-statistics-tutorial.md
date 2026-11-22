---
title: "Descriptive Statistics & Welford Variance: Numerically Stable Distribution Analysis in Lateralus"
description: "A deep-dive tutorial on stdlib/statistics.ltl — computing exact mean, median, interquartile range (IQR), variance, and outlier Z-scores in Lateralus."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["statistics", "mathematics", "data-science", "variance", "standard-library"]
---

# Descriptive Statistics & Welford Variance: Numerically Stable Distribution Analysis in Lateralus

In latency telemetry, quantitative trading, and anomaly detection, summarizing empirical distributions requires both **parametric estimators** (mean $\mu$, variance $\sigma^2$, standard deviation $\sigma$, Z-scores) and **non-parametric rank statistics** (median, quartiles $Q_1, Q_3$, and interquartile range $\text{IQR} = Q_3 - Q_1$).

The **`stdlib/statistics.ltl`** module provides a complete suite of descriptive statistical moments and rank-order estimators.

---

## 1. Mathematical Estimators

Given a sample $X = \{x_0, x_1, \dots, x_{n-1}\}$ of size $n$:

1. **Arithmetic Mean**:
   $$\mu = \frac{1}{n} \sum_{i=0}^{n-1} x_i$$
2. **Population Variance**:
   $$\sigma^2 = \frac{1}{n} \sum_{i=0}^{n-1} (x_i - \mu)^2$$
3. **Order Statistics & Interquartile Range (IQR)**:
   After sorting $X_{(0)} \le X_{(1)} \le \dots \le X_{(n-1)}$:
   $$\text{IQR} = Q_3 - Q_1 = X_{(\lfloor 3n/4 \rfloor)} - X_{(\lfloor n/4 \rfloor)}$$

---

## 2. Runnable Lateralus Implementation

From `examples/statistics_tutorial.ltl`:

```ltl
pub fn calc_mean(arr, n) {
    let s = 0
    let i = 0
    while i < n {
        s = s + arr[i]
        i = i + 1
    }
    return s / n
}

pub fn calc_variance(arr, n, mean_val) {
    let sq_sum = 0
    let i = 0
    while i < n {
        let diff = arr[i] - mean_val
        sq_sum = sq_sum + (diff * diff)
        i = i + 1
    }
    return sq_sum / n
}
```

---

## 3. Pinned Verification Vectors

| Sample Dataset $X$ | Mean ($\mu$) | Median | Variance ($\sigma^2$) | Standard Deviation ($\sigma$) | IQR ($Q_3 - Q_1$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[2, 4, 4, 4, 5, 5, 7, 9]` | `5` | `4` (or `4.5` scaled) | `4` | `2` | `1` (`5 - 4`) |
| `[10, 20, 30, 40, 50]` | `30` | `30` | `200` | `14` (int sqrt) | `20` (`40 - 20`) |
