# Standard Library Deep Dive: Reservoir Sampling (Algorithm R) for Unbounded Streams

**Reservoir Sampling** is a family of randomized algorithms for choosing a simple random sample of $k$ items without replacement from a data stream of unknown or unbounded length $n$, in a single pass. First attributed to Alan G. Waterman and popularized by Donald Knuth in *The Art of Computer Programming* (Volume 2), **Algorithm R** solves a fundamental Big Data dilemma:

> *How do you sample $k$ items uniformly at random from an unbounded stream when you cannot store the entire dataset in memory, cannot know $n$ in advance, and cannot re-read earlier items?*

---

## 1. Algorithmic Formulation (Algorithm R)

Given an incoming stream of items $S = (s_1, s_2, \dots, s_n)$ and desired reservoir size $k$:

1. **Initialization**: Fill the reservoir with the first $k$ elements:
   $$R[0 \dots k-1] \leftarrow S[0 \dots k-1]$$
2. **Stream Ingestion**: For each subsequent element $S[i]$ (for $i \ge k$, 0-indexed):
   - Generate a random integer $j$ uniformly distributed in the closed interval $[0, i]$.
   - If $j < k$, evict element $R[j]$ and overwrite it: $R[j] \leftarrow S[i]$.
   - Otherwise ($j \ge k$), discard $S[i]$.

---

## 2. Rigorous Proof of Uniform Probability by Mathematical Induction

We prove that after processing $n$ elements ($n \ge k$), every item $s_m$ ($0 \le m < n$) resides in the reservoir with probability:

$$P(s_m \in R_n) = \frac{k}{n}$$

### Base Case ($n = k$)
The reservoir is filled with the first $k$ items. Each item is chosen with probability $k/k = 1$. The base case holds.

### Inductive Step
Assume the inductive hypothesis holds for stream length $i - 1$: every element $s_m$ ($m < i$) is in the reservoir with probability:

$$P(s_m \in R_{i-1}) = \frac{k}{i-1}$$

Now, the $i$-th element arrives (index $i$, where $i \ge k$):

1. **For the new element $s_i$**:
   It is inserted into the reservoir if $j \in [0, k-1]$ out of $[0, i]$. There are $k$ favorable outcomes out of $i + 1$ integers. Hence:
   $$P(s_i \in R_i) = \frac{k}{i+1}$$

2. **For any prior element $s_m$ ($m < i$)**:
   $s_m$ remains in the reservoir if and only if:
   - It was already in the reservoir at step $i-1$, AND
   - It was not replaced by $s_i$.

   The probability that $s_m$ is replaced is the probability that $s_i$ is accepted ($k / (i+1)$) multiplied by the probability that index $j$ specifically hits the slot containing $s_m$ ($1/k$):
   $$P(\text{replaced}) = \frac{k}{i+1} \times \frac{1}{k} = \frac{1}{i+1}$$

   Therefore, the survival probability at step $i$ is:
   $$P(\text{survives}) = 1 - \frac{1}{i+1} = \frac{i}{i+1}$$

   Multiplying by the inductive hypothesis:
   $$P(s_m \in R_i) = P(s_m \in R_{i-1}) \times P(\text{survives}) = \frac{k}{i} \times \frac{i}{i+1} = \frac{k}{i+1}$$

By mathematical induction, every element across the entire stream of length $n$ has an exact, uniform selection probability of $\frac{k}{n}$. $\blacksquare$

---

## 3. Lateralus Reference Implementation

```lateralus
fn make_rng(seed) {
    let state = dict()
    state["seed"] = seed
    return state
}

fn lcg_next(state) {
    let a = 1103515245
    let c = 12345
    let m = 2147483647
    let next_seed = (state["seed"] * a + c) % m
    if next_seed < 0 {
        next_seed = 0 - next_seed
    }
    state["seed"] = next_seed
    return next_seed
}

fn rand_int(state, max_val) {
    if max_val <= 0 {
        return 0
    }
    let r = lcg_next(state)
    return r % (max_val + 1)
}

pub fn reservoir_sample(stream, k, seed) {
    let n = len(stream)
    let reservoir = []

    if n <= k {
        let idx = 0
        while idx < n {
            reservoir = push(reservoir, stream[idx])
            idx = idx + 1
        }
        return reservoir
    }

    let i = 0
    while i < k {
        reservoir = push(reservoir, stream[i])
        i = i + 1
    }

    let rng = make_rng(seed)

    while i < n {
        let j = rand_int(rng, i)
        if j < k {
            reservoir[j] = stream[i]
        }
        i = i + 1
    }

    return reservoir
}
```

---

## 4. Complexity & Resource Bounds

| Dimension | Reservoir Sampling (Algorithm R) | Naive In-Memory Shuffle |
| :--- | :---: | :---: |
| **Time Complexity** | $O(n)$ single pass | $O(n \log n)$ or $O(n)$ |
| **Auxiliary Memory** | $O(k)$ strict constant | $O(n)$ full stream retention |
| **Stream Length Knowledge** | Unneeded (Unbounded stream) | Required beforehand |
| **Cache Locality** | High (Sequential streaming read) | Low (Random access shuffle) |

---

## 5. Industrial Applications

1. **Financial Regulatory Auditing**:
   Uniformly drawing $k$ transactions from millions of streaming clearinghouse trades for Anti-Money Laundering (AML) inspection.
2. **Distributed Telemetry Sub-Sampling (Apache Kafka / Flink)**:
   Extracting statistical metrics from terabytes of unbounded IoT log streams without buffer overflows.
3. **Machine Learning Continuous Batching**:
   Maintaining a stationary representative replay buffer in online reinforcement learning.
