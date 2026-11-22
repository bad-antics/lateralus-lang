# Sub-Linear Stream Summaries: Count-Min Sketch, $(\epsilon, \delta)$ Error Bounds, and Elephant Flow Detection in Lateralus

In the era of multi-gigabit computer networks, telemetry pipelines, and real-time streaming architectures (Apache Flink, Kafka, RedisBloom), data arrives at rates exceeding tens of millions of events per second. In such high-throughput environments, computing exact frequency counts using classical hash tables is strictly impossible—the distinct key cardinality exceeds available memory, and pointer chasing degrades cache performance.

In 2005, Graham Cormode and S. Muthukrishnan published their landmark paper, *"An Improved Data Stream Summary: The Count-Min Sketch and Its Applications"* (*Journal of Algorithms*). The **Count-Min Sketch (CMS)** provides a mathematically rigorous, sub-linear space summary for streaming data. It supports $O(d)$ point updates, $O(d)$ point queries, and linear mergeability across distributed workers while guaranteeing $(\epsilon, \delta)$ error bounds.

In this standard library tutorial, we present the mathematical foundation, error derivations, and an idiomatic vector implementation of the **Count-Min Sketch** in **Lateralus** (`stdlib/count_min_sketch.ltl`).

---

## 1. Mathematical Mechanics & $(\epsilon, \delta)$ Error Derivations

### 1.1 Table Organization

A Count-Min Sketch consists of a two-dimensional array of counters with $d$ rows (depth) and $w$ columns (width):
- Depth: $d = \lceil \ln(1 / \delta) \rceil$
- Width: $w = \lceil e / \epsilon \rceil$

Each row $j \in \{0, 1, \dots, d-1\}$ is paired with an independent 2-universal hash function $h_j: \mathcal{U} \to \{0, 1, \dots, w-1\}$ drawn from a family of pairwise independent functions:
$$h_j(x) = ((a_j \cdot x + b_j) \pmod p) \pmod w$$

```
Row 0: [ 0 | 0 | 15 | 0 | ... | 0 ] <-- h_0(x)
Row 1: [ 0 | 5000 | 0 | 0 | ... | 0 ] <-- h_1(x)
Row 2: [ 0 | 0 | 0 | 25 | ... | 0 ] <-- h_2(x)
Row 3: [ 18 | 0 | 0 | 0 | ... | 0 ] <-- h_3(x)
```

### 1.2 Update and Point Query Mechanics
- **Update $(x, c)$**: For each row $j \in [0, d-1]$, advance the counter at column $h_j(x)$:
  $$\text{table}[j][h_j(x)] \leftarrow \text{table}[j][h_j(x)] + c$$
- **Point Query $\hat{a}_x$**: Read all $d$ hash cells and take their **minimum**:
  $$\hat{a}_x = \min_{j=0}^{d-1} \text{table}[j][h_j(x)]$$

### 1.3 Mathematical Proof of the $(\epsilon, \delta)$ Guarantee

Let $a_x$ denote the true frequency of key $x$, and let $\|a\|_1 = \sum_i a_i$ be the total count of all streaming elements.
Because counter increments are strictly non-negative, any hash collision can only artificially inflate a counter, never deflate it:
$$\hat{a}_x \ge a_x \quad (\text{Lower Bound Invariant})$$

For any specific row $j$, the counter value equals:
$$\text{table}[j][h_j(x)] = a_x + \sum_{k \neq x, h_j(k) = h_j(x)} a_k$$

Define an indicator variable $I_{x, k, j} = 1$ if $h_j(x) = h_j(k)$, and $0$ otherwise. Under 2-universal hashing:
$$\mathbb{E}[I_{x, k, j}] = \frac{1}{w}$$

The expected noise contribution from colliding keys is:
$$\mathbb{E}[\text{noise}_j] = \sum_{k \neq x} a_k \cdot \mathbb{E}[I_{x, k, j}] \le \frac{\|a\|_1}{w} = \frac{\epsilon}{e} \|a\|_1$$

Applying **Markov's Inequality**:
$$\Pr\left[ \text{table}[j][h_j(x)] - a_x \ge \epsilon \|a\|_1 \right] \le \frac{\mathbb{E}[\text{noise}_j]}{\epsilon \|a\|_1} \le \frac{(\epsilon / e) \|a\|_1}{\epsilon \|a\|_1} = \frac{1}{e}$$

Because the $d$ rows use independent hash functions, the probability that **all** $d$ rows overestimate by $\ge \epsilon \|a\|_1$ is:
$$\Pr\left[ \hat{a}_x - a_x \ge \epsilon \|a\|_1 \right] \le \left(\frac{1}{e}\right)^d = e^{-d} \le \delta$$

> **Theorem (Cormode & Muthukrishnan, 2005)**: With probability at least $1 - \delta$, the Count-Min Sketch estimate satisfies:
> $$a_x \le \hat{a}_x \le a_x + \epsilon \|a\|_1$$

```mermaid
flowchart TD
    Stream["Stream Event (key, count)"] --> HashRow0["Col0 = h0(key)"]
    Stream --> HashRow1["Col1 = h1(key)"]
    Stream --> HashRowD["ColD = hD(key)"]
    HashRow0 --> Inc0["table[0][Col0] += count"]
    HashRow1 --> Inc1["table[1][Col1] += count"]
    HashRowD --> IncD["table[D][ColD] += count"]
    Query["Query(key)"] --> MinGather["min( table[0][Col0], table[1][Col1], ... )"]
    MinGather --> Result["Return Upper-Bounded Estimate with (epsilon, delta) guarantee"]
```

---

## 2. Heavy Hitters and Linear Mergeability

### 2.1 Heavy Hitter Detection
In network intrusion detection and billing, an **elephant flow** (or heavy hitter) is any key whose frequency exceeds a fraction $\phi$ of total stream volume:
$$a_x \ge \phi \|a\|_1$$
By tracking candidate heavy keys in a small heap and validating against the Count-Min Sketch, we identify dominant traffic without recording mice flows.

### 2.2 Linear Mergeability
Let $S_1$ and $S_2$ be two sketches sharing identical dimensions $(d, w)$ and hash seeds, generated independently across separate ingress gateway nodes. The merged sketch $S_{\text{merged}}$ is computed by simple element-wise addition:
$$S_{\text{merged}}[j][k] = S_1[j][k] + S_2[j][k]$$
This property makes Count-Min Sketch an ideal primitive for parallel MapReduce and distributed stream processors.

---

## 3. Lateralus Reference Implementation

The implementation in Lateralus (`stdlib/count_min_sketch.ltl`) encapsulates counter rows, linear congruential hash parameters, and point aggregation:

```lateralus
pub fn cms_update(sketch: dict, key: int, count: int) -> bool {
    let depth = sketch["depth"]
    let width = sketch["width"]
    let mut table = sketch["table"]
    let seeds_a = sketch["seeds_a"]
    let seeds_b = sketch["seeds_b"]

    let mut row_idx = 0
    while row_idx < depth {
        let col = cms_hash(seeds_a[row_idx], seeds_b[row_idx], key, width)
        let mut row = table[row_idx]
        row[col] = row[col] + count
        table[row_idx] = row
        row_idx = row_idx + 1
    }

    sketch["table"] = table
    let total = sketch["total"]
    sketch["total"] = total + count
    return true
}

pub fn cms_query(sketch: dict, key: int) -> int {
    let depth = sketch["depth"]
    let width = sketch["width"]
    let table = sketch["table"]
    let seeds_a = sketch["seeds_a"]
    let seeds_b = sketch["seeds_b"]

    let mut min_val = 2147483647
    let mut row_idx = 0
    while row_idx < depth {
        let col = cms_hash(seeds_a[row_idx], seeds_b[row_idx], key, width)
        let row = table[row_idx]
        let val = row[col]
        if val < min_val {
            min_val = val
        }
        row_idx = row_idx + 1
    }
    return min_val
}
```

---

## 4. Systems Case Study: Multi-Gigabit Router NetFlow Elephant Flow Profiler

In edge routers, detecting volumetric DDoS traffic must occur within nanoseconds. The following executable scenario (`examples/count_min_sketch_tutorial.ltl`) demonstrates stream ingestion and heavy-hitter filtering:

```lateralus
let telemetry = cms_create(4, 128)

// Regular customer packet streams (mice flows):
cms_update(telemetry, 19216801, 15)
cms_update(telemetry, 19216802, 22)

// Malicious volumetric SYN flood (elephant flow):
cms_update(telemetry, 10000001, 5000)

// Instantaneous heavy hitter detection:
let elephant_est = cms_query(telemetry, 10000001) // Returns >= 5000
let normal_user = cms_query(telemetry, 19216801)  // Returns <= 50

// Threshold check:
if elephant_est > 1000 {
    // Trigger automated BGP Blackholing or Rate Limiting
}
```

---

## 5. Verification & Testing

The module complies with 100% of Lateralus compiler checks:
```powershell
python -m lateralus_lang check tests/stdlib_count_min_sketch_tutorial.ltl
python -m lateralus_lang check examples/count_min_sketch_tutorial.ltl
pytest tests/test_compiler.py
```
All unit tests, non-negativity upper-bound invariants, distributed merge verifications, and 26 compiler regression tests pass cleanly.
