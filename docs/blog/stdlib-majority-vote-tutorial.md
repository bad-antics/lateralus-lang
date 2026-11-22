# Boyer-Moore Majority Vote & Streaming Heavy Hitters in Lateralus

## 1. Introduction

The **Majority Element Problem** asks for an element that appears strictly more than $\lfloor n/2 \rfloor$ times in an array or streaming sequence of length $n$.

Traditional techniques carry substantial overheads:
- **Sorting**: Requires $\mathcal{O}(n \log n)$ comparisons and in-place mutation or memory copying.
- **Hash Map Frequency Counting**: Requires $\mathcal{O}(n)$ auxiliary memory, making it impractical for continuous, unbounded network telemetry streams or memory-constrained embedded smart contracts and microcontrollers.

Invented by Robert S. Boyer and J Strother Moore in 1981, the **Boyer-Moore Majority Vote Algorithm** solves this problem in:

$$\mathcal{O}(n) \text{ time} \quad \text{and strictly} \quad \mathcal{O}(1) \text{ auxiliary space!}$$

By pairing up distinct elements and eliminating them, the algorithm mathematically guarantees that if a majority element exists, it will survive as the final candidate.

Furthermore, this principle generalizes cleanly to the **Misra-Gries Algorithm** (1982) for identifying all "heavy hitters" appearing more than $\lfloor n/k \rfloor$ times using merely $k - 1$ counters—a critical tool for Byzantine Fault Tolerant (BFT) distributed consensus.

This tutorial provides an implementation of the Boyer-Moore Majority Vote and Misra-Gries heavy hitter algorithms in Lateralus (`stdlib/majority_vote.ltl`), along with blockchain validator consensus voting examples and golden test vectors.

---

## 2. Core Mathematical Principles

### 2.1 The Element Pairing Principle
The underlying invariant rests on an intuitive algebraic insight:
> If we discard two distinct elements from a multiset, any element that was a strict majority ($> n/2$) remains a strict majority of the remaining $n - 2$ elements.

By continually maintaining a single candidate and an integer counter:
1. When `count == 0`, we adopt the current element as the candidate and set `count = 1`.
2. When the current element matches the candidate, we increment `count`.
3. When the current element differs from the candidate, we decrement `count` (pairing and cancelling the two distinct elements).

### 2.2 Verification Pass
If the input is guaranteed to contain a majority element, the final candidate is guaranteed to be correct after a single pass. If a majority element might not exist, a secondary $\mathcal{O}(n)$ verification pass simply counts occurrences of the nominated candidate to confirm whether $\text{count} > \lfloor n/2 \rfloor$.

### 2.3 Generalization to Misra-Gries ($k=3$)
To detect all elements with frequency $> \lfloor n/3 \rfloor$:
- At most 2 such elements can exist simultaneously (since $3 \times (n/3 + 1) > n$).
- We maintain 2 candidate registers (`cand1`, `cand2`) and 2 counters (`count1`, `count2`).
- When encountering an element distinct from both candidates, if both counters are non-zero, both counters decrement simultaneously (cancelling a triplet of 3 distinct elements).

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
pub fn majority_vote(nums) {
    let n = len(nums)
    if n == 0 {
        let res = dict()
        res["candidate"] = nil
        res["count"] = 0
        res["is_majority"] = false
        return res
    }

    let candidate = nums[0]
    let count = 0

    let i = 0
    while i < n {
        let x = nums[i]
        if count == 0 {
            candidate = x
            count = 1
        } else {
            if x == candidate {
                count = count + 1
            } else {
                count = count - 1
            }
        }
        i = i + 1
    }

    let actual_count = 0
    let j = 0
    while j < n {
        if nums[j] == candidate {
            actual_count = actual_count + 1
        }
        j = j + 1
    }

    let threshold = idiv(n, 2)
    let res = dict()
    res["candidate"] = candidate
    res["count"] = actual_count
    res["is_majority"] = (actual_count > threshold)

    return res
}

pub fn majority_two_thirds(nums) {
    let n = len(nums)
    if n == 0 {
        return []
    }

    let cand1 = nums[0]
    let cand2 = nums[0]
    let count1 = 0
    let count2 = 0

    let i = 0
    while i < n {
        let x = nums[i]
        if x == cand1 {
            count1 = count1 + 1
        } else {
            if x == cand2 {
                count2 = count2 + 1
            } else {
                if count1 == 0 {
                    cand1 = x
                    count1 = 1
                } else {
                    if count2 == 0 {
                        cand2 = x
                        count2 = 1
                    } else {
                        count1 = count1 - 1
                        count2 = count2 - 1
                    }
                }
            }
        }
        i = i + 1
    }

    let actual1 = 0
    let actual2 = 0
    let j = 0
    while j < n {
        if nums[j] == cand1 {
            actual1 = actual1 + 1
        } else {
            if nums[j] == cand2 {
                actual2 = actual2 + 1
            }
        }
        j = j + 1
    }

    let threshold = idiv(n, 3)
    let winners = []
    if actual1 > threshold {
        winners = push(winners, cand1)
    }
    if cand2 != cand1 and actual2 > threshold {
        winners = push(winners, cand2)
    }

    return winners
}
```

---

## 4. Real-World Engineering Applications

1. **Byzantine Fault Tolerant (BFT) Blockchain Consensus**: Tallying validator votes in Tendermint or PBFT rounds to establish $2/3+$ commit supermajorities without allocating dynamic hash tables.
2. **Network Streaming Telemetry & Heavy Hitters**: Real-time detection of high-volume IP flows and DDoS packet floods directly on network switches with strict SRAM limits.
3. **Distributed System Quorum Resolution**: Determining authoritative leader votes and split-brain resolution in Raft and Paxos clusters.
4. **Data Mining & Real-Time Trend Detection**: Identifying trending search queries or dominant streaming metrics over high-velocity unbounded event queues.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_majority_vote_tutorial.ltl
python -m lateralus_lang check examples/majority_vote_tutorial.ltl
pytest tests/test_compiler.py
```
