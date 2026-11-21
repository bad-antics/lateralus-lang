# Near-Duplicate Detection with SimHash in Lateralus

In large-scale data engineering—crawling web pages, deduplicating document stores, filtering spam, or detecting code plagiarism—one frequently encounters documents that are nearly, but not completely, identical. Standard cryptographic hash functions like SHA-256 or BLAKE2s are explicitly engineered with the **avalanche effect**: changing a single byte or punctuation mark alters approximately 50% of the output bits. While critical for security, cryptographic hashes are useless for clustering similar documents.

**Locality-Sensitive Hashing (LSH)** solves this by doing the exact opposite: items that are semantically or lexically close produce fingerprints whose distance is directly proportional to the difference between the inputs.

In this tutorial, we explore `stdlib/simhash.ltl`, the Lateralus Spiral Wave 10 module providing 64-bit SimHash locality-sensitive fingerprinting, Hamming distance calculation, and constant-time near-duplicate detection.

---

## The Mathematics of SimHash

Introduced by Moses Charikar in 2002 (STOC '02), SimHash maps high-dimensional feature vectors into compact bit strings such that the cosine distance between two feature vectors is preserved as the Hamming distance between their binary fingerprints.

For two document feature vectors $\mathbf{u}$ and $\mathbf{v}$ with angle $\theta(\mathbf{u}, \mathbf{v})$:

$$\Pr[h_i(\mathbf{u}) = h_i(\mathbf{v})] = 1 - \frac{\theta(\mathbf{u}, \mathbf{v})}{\pi}$$

The expected Hamming distance $D_H$ between two $b$-bit fingerprints is:

$$D_H(f_1, f_2) = b \cdot \frac{\theta(\mathbf{u}, \mathbf{v})}{\pi}$$

### Fingerprint Construction Algorithm

Given a document $D$:

1. **Tokenization & Weighting**: The document is split into tokens (words or shingles). Each unique token $t$ is assigned a weight $w(t)$ (commonly term frequency, TF-IDF, or 1).
2. **Accumulator Vector Initialization**: Allocate a 64-element accumulator array $V = [0, 0, \dots, 0]$.
3. **Bitwise Projection**:
   - For each token $t$, compute a uniform 64-bit hash $h(t)$.
   - For each bit position $i \in [0, 63]$:
     - If the $i$-th bit of $h(t)$ is `1`, add the token's weight: $V[i] \leftarrow V[i] + w(t)$.
     - If the $i$-th bit of $h(t)$ is `0`, subtract the token's weight: $V[i] \leftarrow V[i] - w(t)$.
4. **Sign Thresholding**:
   - The final 64-bit fingerprint bit $f[i]$ is `1` if $V[i] \ge 0$, and `0` if $V[i] < 0$.

```text
Tokens:      ["quick", "brown", "fox"]
Hashes:      h("quick") = 1 0 1 1 ...
             h("brown") = 0 0 1 1 ...
             h("fox")   = 1 1 0 1 ...
---------------------------------------------
Accumulator: V          = [+1, -1, +1, +3, ...]
---------------------------------------------
Fingerprint: F          =  1   0   1   1  ...
```

---

## Exploring `stdlib/simhash.ltl`

The Lateralus standard library implementation (`stdlib/simhash.ltl`) exposes the following public API:

```lateralus
pub fn fingerprint(text: str) -> int
pub fn hamming(a: int, b: int) -> int
pub fn similarity(a: int, b: int) -> float
pub fn near_duplicate(a: str, b: str, threshold_bits: int) -> bool
pub fn fingerprint_all(docs: list) -> list
```

### 1. Tokenization and Normalization

Before computing bit projections, the tokenizer lowercases words and strips punctuation, ensuring that casing and formatting variations do not skew similarity calculations:

```lateralus
fn simhash_tokenize(text: str) -> list {
    let toks = []
    let buf = ""
    let i = 0
    while i < len(text) {
        let c = char_at(text, i)
        let oc = ord(c)
        let is_alnum = false
        if oc >= 48 && oc <= 57 { is_alnum = true }
        if oc >= 97 && oc <= 122 { is_alnum = true }
        if oc >= 65 && oc <= 90 {
            is_alnum = true
            c = chr(oc + 32)   // lowercase
        }
        if is_alnum {
            buf = buf + c
        } else {
            if len(buf) > 0 { toks = toks + [buf]; buf = "" }
        }
        i = i + 1
    }
    if len(buf) > 0 { toks = toks + [buf] }
    return toks
}
```

### 2. Fingerprint Accumulation

The `fingerprint` function executes the accumulator loop across all 64 bits:

```lateralus
pub fn fingerprint(text: str) -> int {
    let tokens = simhash_tokenize(text)
    let v = []
    let i = 0
    while i < 64 { v = v + [0]; i = i + 1 }

    let t = 0
    while t < len(tokens) {
        let h = token_hash64(tokens[t])
        let b = 0
        while b < 64 {
            let bit = (h >> b) & 1
            if bit == 1 { v[b] = v[b] + 1 } else { v[b] = v[b] - 1 }
            b = b + 1
        }
        t = t + 1
    }

    let fp = 0
    let k = 0
    while k < 64 {
        if v[k] >= 0 { fp = fp | (1 << k) }
        k = k + 1
    }
    return fp
}
```

### 3. Constant-Time Hamming Distance

Once fingerprints are stored as 64-bit integers, calculating the distance between any pair of documents requires only bitwise XOR and bit-counting (popcount), executing in constant time:

```lateralus
pub fn hamming(a: int, b: int) -> int {
    let x = a ^ b
    let count = 0
    let i = 0
    while i < 64 {
        count = count + ((x >> i) & 1)
        i = i + 1
    }
    return count
}
```

---

## Executable Tutorial: `examples/simhash_tutorial.ltl`

The runnable tutorial provides a self-contained demonstration of document tokenization, fingerprint calculation, and threshold matching across three representative scenarios:

1. **Exact duplicate with normalized case & punctuation**
2. **Near-duplicate paraphrased text (1-2 words changed)**
3. **Completely unrelated text domain**

```lateralus
// Helper string primitives
fn char_at(s: str, i: int) -> str { return slice(s, i, i + 1) }

// [SimHash implementation]

fn main() {
    print("=== LATERALUS STDLIB SIMHASH TUTORIAL ===")

    let doc_a = "The quick brown fox jumps over the lazy dog"
    let doc_b = "THE QUICK BROWN FOX, JUMPS OVER THE LAZY DOG!!!"
    let doc_c = "The fast brown fox leaps over a sleepy dog"
    let doc_d = "Quantum tensor networks accelerate Hamiltonian simulation in lattice QCD"

    print("STEP 1: Document Tokenization")
    let tokens_a = simhash_tokenize(doc_a)
    print("  doc_a tokens count: " + str(len(tokens_a)))

    print("STEP 2: Computing 64-bit Locality-Sensitive Fingerprints")
    let fp_a = fingerprint(doc_a)
    let fp_b = fingerprint(doc_b)
    let fp_c = fingerprint(doc_c)
    let fp_d = fingerprint(doc_d)

    print("  fp_a = " + str(fp_a))
    print("  fp_b = " + str(fp_b))
    print("  fp_c = " + str(fp_c))
    print("  fp_d = " + str(fp_d))

    print("STEP 3: Pairwise Hamming Distances & Cosine Similarities")
    let dist_exact = hamming(fp_a, fp_b)
    let dist_near = hamming(fp_a, fp_c)
    let dist_far = hamming(fp_a, fp_d)

    print("  doc_a vs doc_b (case/punctuation normalized):")
    print("    Hamming Distance: " + str(dist_exact) + " bits")
    print("    Near-Duplicate: " + str(near_duplicate(doc_a, doc_b, 3)))

    print("  doc_a vs doc_c (paraphrased variant):")
    print("    Hamming Distance: " + str(dist_near) + " bits")
    print("    Near-Duplicate (threshold=12): " + str(near_duplicate(doc_a, doc_c, 12)))

    print("  doc_a vs doc_d (completely disjoint domain):")
    print("    Hamming Distance: " + str(dist_far) + " bits")
    print("    Near-Duplicate (threshold=12): " + str(near_duplicate(doc_a, doc_d, 12)))

    // Pinned verification vectors for automated test suites
    print("PINNED_VECTORS: exact_dist=" + str(dist_exact) + " near_dist=" + str(dist_near) + " far_dist=" + str(dist_far))
}

main()
```

### Running and Verifying

Run the example with `lateralus run`:

```bash
lateralus run examples/simhash_tutorial.ltl
```

Output:

```text
=== LATERALUS STDLIB SIMHASH TUTORIAL ===
STEP 1: Document Tokenization
  doc_a tokens count: 9
STEP 2: Computing 64-bit Locality-Sensitive Fingerprints
  fp_a = 14607312263354641902
  fp_b = 14607312263354641902
  fp_c = 14912431120926964047
  fp_d = 10207751738674989474
STEP 3: Pairwise Hamming Distances & Cosine Similarities
  doc_a vs doc_b (case/punctuation normalized):
    Hamming Distance: 0 bits
    Near-Duplicate: True
  doc_a vs doc_c (paraphrased variant):
    Hamming Distance: 11 bits
    Near-Duplicate (threshold=12): True
  doc_a vs doc_d (completely disjoint domain):
    Hamming Distance: 28 bits
    Near-Duplicate (threshold=12): False
PINNED_VECTORS: exact_dist=0 near_dist=11 far_dist=28
```

### Analysis of Pinned Vectors

- **`exact_dist = 0`**: `doc_a` and `doc_b` produce identical fingerprints ($D_H = 0$) because tokenization correctly normalizes capitalization and punctuation.
- **`near_dist = 11`**: Despite substituting multiple terms ("quick" $\rightarrow$ "fast", "jumps" $\rightarrow$ "leaps", "lazy" $\rightarrow$ "sleepy"), only 11 out of 64 bits differ. With an allowable threshold of 12 bits, `near_duplicate` evaluates to `True`.
- **`far_dist = 28`**: Comparing `doc_a` with a technical sentence on lattice quantum chromodynamics yields 28 differing bits—approaching the expected 32-bit distance of two randomly uncorrelated 64-bit integers.

---

## Composition in the Spiral Wave Search Lane

In production pipelines, SimHash combines seamlessly with other Lateralus Wave 10 modules:

- **`qgram`**: Rapidly candidates matching documents via inverted index lookups.
- **`levenshtein`**: Performs fine-grained edit distance on top candidates.
- **`simhash`**: Clusters and collapses massive document collections into near-duplicate groups in $O(1)$ comparison time per pair.

See `examples/spiral_search.ltl` for a complete pipeline combining all five Wave 10 search primitives.
