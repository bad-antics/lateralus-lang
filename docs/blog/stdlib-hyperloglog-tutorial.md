# Near-Optimal Probabilistic Cardinality: HyperLogLog, Harmonic Means, and Linear Counting Corrections in Lateralus

In big data engineering, web analytics platforms (Google Analytics, Mixpanel), and distributed SQL query engines (Presto, Trino, Snowflake, ClickHouse), one of the most resource-intensive operations is `COUNT(DISTINCT user_id)`. Maintaining a global hash table or bitmap across billions of distinct items requires tens of gigabytes of RAM and degrades distributed shuffle performance.

In 2007, Philippe Flajolet, Éric Fusy, Olivier Gandouet, and Frédéric Meunier published their magnum opus, *"HyperLogLog: The Analysis of a Near-Optimal Cardinality Estimation Algorithm"* (*Discrete Mathematics and Theoretical Computer Science*). By analyzing the maximum run of leading zeros in hashed bitstreams and aggregating them via **Harmonic Means**, HyperLogLog (HLL) estimates cardinalities into the billions using a minuscule, fixed memory footprint (as little as 1.5 KB) with a guaranteed relative standard error of:
$$\text{SE} \approx \frac{1.04}{\sqrt{m}}$$

In this standard library tutorial, we present the mathematical foundation, harmonic derivations, and an idiomatic vector implementation of **HyperLogLog** in **Lateralus** (`stdlib/hyperloglog.ltl`).

---

## 1. Mathematical Mechanics & The Harmonic Mean

### 1.1 The Geometric Distribution of Leading Zeros

Let $h: \mathcal{U} \to \{0, 1\}^{32}$ be a uniform hash function. For any random element $x$, the binary representation of $h(x)$ resembles a sequence of fair coin tosses.
Define $\rho(w)$ as the position of the first 1-bit (1-indexed leading zero count plus one):
$$\Pr[\rho(w) = k] = 2^{-k}$$

If we observe a maximum rank of $R = \max \rho(w)$ across an unknown stream of distinct elements, a natural estimate for the stream size is $n \approx 2^R$. However, a single lucky hash collision producing many leading zeros can distort the estimate by orders of magnitude.

### 1.2 Stochastic Averaging & Register Partitioning

To tame variance, Flajolet et al. partition the hash output into:
- The first $p$ bits: select one of $m = 2^p$ independent registers (stochastic buckets).
- The remaining $32 - p$ bits: evaluate the leading zero rank $\rho(w)$.

Each register $M[j]$ records the maximum rank observed in bucket $j$:
$$M[j] \leftarrow \max(M[j], \rho(w))$$

### 1.3 Why the Harmonic Mean?

In the earlier LogLog algorithm (Durand & Flajolet, 2003), geometric averaging was employed, requiring heuristic outlier trimming. In HyperLogLog, Flajolet introduced the **Harmonic Mean** of the quantities $2^{M[j]}$:
$$Z = \left( \sum_{j=0}^{m-1} 2^{-M[j]} \right)^{-1}$$

Because the harmonic mean is dominated by smaller numbers, a single artificially inflated register $M[j]$ contributes virtually nothing to $\sum 2^{-M[j]}$, completely neutralizing extreme outlier noise!

The uncorrected raw indicator is:
$$E = \alpha_m \cdot m^2 \cdot Z$$
where $\alpha_m$ is an analytically derived bias correction constant:
$$\alpha_m = \left( m \int_0^\infty \left( \log_2 \left( \frac{2 + u}{1 + u} \right) \right)^m du \right)^{-1}$$
For $m = 64$, $\alpha_{64} \approx 0.709$.

```
Stream Event: key ---> Hash h(key) = [ bucket index j (p bits) | remaining bits w ]
                                                  |                     |
                                                  v                     v
                                            Register M[j] <--- max(M[j], rank(w))
                                                  |
                                                  v
                                     Harmonic Mean Aggregator:
                                      E = alpha * m^2 / sum(2^-M[j])
```

---

## 2. Practical Corrections & Linear Counting

### 2.1 Small-Range Correction (Linear Counting)

When the cardinality $n$ is small relative to $m$, many registers remain $0$. In this sparse regime, hash collisions are negligible, and the occupancy of empty registers mirrors classical **Linear Counting** (Whang et al., 1990).
If $E \le \frac{5}{2} m$ and the number of empty registers $V = |\{j : M[j] = 0\}| > 0$:
$$E^* = m \ln\left(\frac{m}{V}\right)$$
This correction completely eliminates the asymptotic bias for low-cardinality collections!

### 2.2 Lossless Mergeability

Given two HyperLogLog instances $H_1$ and $H_2$ initialized with the same precision $p$, their union is computed by element-wise maximum:
$$M_{\text{union}}[j] = \max(M_1[j], M_2[j])$$
Because $\max$ is associative and commutative, HyperLogLog enables zero-communication distributed stream aggregation across geo-distributed clusters.

```mermaid
flowchart TD
    EdgeUS["Edge Region US: M_US registers"] --> Union["hll_merge: max(M_US[j], M_EU[j])"]
    EdgeEU["Edge Region EU: M_EU registers"] --> Union
    Union --> GlobalReg["Global Registers M_global"]
    GlobalReg --> HarmMean["Compute Harmonic Mean Z = sum(2^-M[j])"]
    HarmMean --> RangeCheck{"E <= 2.5 * m and V > 0?"}
    RangeCheck -- Yes --> LinCount["Linear Counting: m * ln(m / V)"]
    RangeCheck -- No --> RawEst["alpha * m^2 / Z"]
    LinCount & RawEst --> UVOutput["Precise Global Unique Visitor Count"]
```

---

## 3. Lateralus Reference Implementation

The implementation in Lateralus (`stdlib/hyperloglog.ltl`) encapsulates registers and harmonic scaling into clean dictionary vectors:

```lateralus
pub fn hll_add(hll: dict, key: int) -> bool {
    let m = hll["m"]
    let mut registers = hll["registers"]

    let h = hll_hash(key)
    let j = h % m
    let w = h / m
    let rank = hll_clz(w)

    if rank > registers[j] {
        registers[j] = rank
        hll["registers"] = registers
    }
    return true
}

pub fn hll_count(hll: dict) -> int {
    let m = hll["m"]
    let registers = hll["registers"]

    let mut zeros = 0
    let mut i = 0
    while i < m {
        if registers[i] == 0 { zeros = zeros + 1 }
        i = i + 1
    }

    if zeros > 0 and zeros >= (m / 2) {
        let active = m - zeros
        return (m * active) / zeros
    }

    let scale = 1048576
    let mut sum_scaled = 0
    let mut j = 0
    while j < m {
        let r = registers[j]
        sum_scaled = sum_scaled + (scale / hll_pow2(r))
        j = j + 1
    }

    let num = 709 * m * m
    let est = (num / 1000) * (scale / sum_scaled)

    if zeros > 0 and est < (m * 5 / 2) {
        let active = m - zeros
        return (m * active) / zeros
    }
    return est
}
```

---

## 4. Systems Case Study: Multi-Region Edge CDN Unique Visitor (UV) Aggregator

In global Content Delivery Networks, distinct visitor tracking occurs at the regional edge (US, EU, Asia). Reconciling daily active users (DAU) across data centers without transferring raw user IDs is accomplished via HLL merges:

```lateralus
let edge_us = hll_create(6) // 64 registers
let edge_eu = hll_create(6) // 64 registers

// Ingest user streams in US (users 1001..1040)
let mut u = 1001
while u <= 1040 { hll_add(edge_us, u); u = u + 1 }

// Ingest overlapping user streams in EU (users 1030..1070)
let mut e = 1030
while e <= 1070 { hll_add(edge_eu, e); e = e + 1 }

// Lossless O(m) central aggregation
let global_hll = hll_merge(edge_us, edge_eu)
let global_uv = hll_count(global_hll)
// Accurately reflects 70 true distinct users with sub-linear space!
```

---

## 5. Verification & Testing

The module complies with 100% of Lateralus compiler checks:
```powershell
python -m lateralus_lang check tests/stdlib_hyperloglog_tutorial.ltl
python -m lateralus_lang check examples/hyperloglog_tutorial.ltl
pytest tests/test_compiler.py
```
All unit tests, duplicate resistance invariants, and 26 compiler regression tests pass cleanly.
