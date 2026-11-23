# Miller-Rabin Primality Test Tutorial: Modular Exponentiation and Compositeness Witnesses

## Overview

Primality testing is the bedrock of modern public-key cryptography. In algorithms such as RSA, Diffie-Hellman, and elliptic curve cryptography, generating secure keys requires generating random large integers and verifying whether they are prime.

Trial division requires $O(\sqrt{n})$ time, which is computationally intractable for 2048-bit or 4096-bit numbers. Naive Fermat primality testing ($a^{n-1} \equiv 1 \pmod n$) is vulnerable to **Carmichael numbers** (such as $561, 1105, 1729$), which fool Fermat's test for all coprime bases.

The **Miller-Rabin primality test** (conceived by Gary L. Miller in 1976 and adapted by Michael O. Rabin in 1980) solves both challenges. It runs in $O(k \log^3 n)$ time using fast binary modular exponentiation and quadratic residue properties. For a small fixed set of prime bases, it is **100% deterministic** for all 64-bit integers.

---

## Mathematical Formulation

Let $n > 2$ be an odd integer to be tested.

### 1. Factorization of $n - 1$

Because $n$ is odd, $n - 1$ is even. We factor out powers of 2:
$$n - 1 = 2^s \cdot d$$
where $d$ is an odd positive integer and $s \ge 1$.

### 2. Witness Testing

For a chosen base $a \in [2, n - 2]$:
1. Compute the sequence:
   $$x_0 = a^d \pmod n$$
2. If $x_0 = 1$ or $x_0 = n - 1$, $n$ passes the test for base $a$ (it is a probable prime).
3. Otherwise, iteratively square $x$:
   $$x_{r+1} = x_r^2 \pmod n \quad \text{for } r \in [0, s-2]$$
   - If at any point $x_{r+1} = n - 1$, $n$ passes the test.
4. If $x$ reaches the end without ever equaling $n - 1$, $a$ is a **witness for the compositeness of $n$**, and $n$ is definitely composite.

### 3. Binary Modular Exponentiation: $O(\log e)$

Modular powers $a^e \pmod m$ are computed in $O(\log e)$ multiplications using square-and-multiply bitwise shifting:
- If current least-significant bit of $e$ is 1: $\text{res} \leftarrow (\text{res} \cdot b) \pmod m$.
- Square base: $b \leftarrow (b \cdot b) \pmod m$.
- Shift exponent: $e \leftarrow e \gg 1$.

---

## Lateralus Implementation

```lateralus
fn mod_pow(base: int, exp: int, m: int) -> int {
    if m == 1 {
        return 0;
    }
    let mut res = 1;
    let mut b = base % m;
    let mut e = exp;
    while e > 0 {
        if (e & 1) == 1 {
            res = (res * b) % m;
        }
        b = (b * b) % m;
        e = e >> 1;
    }
    return res;
}

fn miller_rabin_witness(a: int, d: int, s: int, n: int) -> bool {
    let mut x = mod_pow(a, d, n);
    if x == 1 || x == (n - 1) {
        return true;
    }

    let mut r = 1;
    while r < s {
        x = (x * x) % n;
        if x == (n - 1) {
            return true;
        }
        r = r + 1;
    }
    return false;
}

fn is_prime(n: int) -> bool {
    if n < 2 {
        return false;
    }
    if n == 2 || n == 3 || n == 5 || n == 7 || n == 11 || n == 13 || n == 17 || n == 19 || n == 23 || n == 29 || n == 31 || n == 37 {
        return true;
    }
    if (n % 2 == 0) || (n % 3 == 0) || (n % 5 == 0) || (n % 7 == 0) {
        return false;
    }

    let mut d = n - 1;
    let mut s = 0;
    while (d & 1) == 0 {
        d = d >> 1;
        s = s + 1;
    }

    let bases = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37];
    let mut i = 0;
    while i < len(bases) {
        let a = bases[i];
        if a < n {
            let passes = miller_rabin_witness(a, d, s, n);
            if passes == false {
                return false;
            }
        }
        i = i + 1;
    }
    return true;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_miller_rabin_tutorial.ltl` validates:

1. **Modular Exponentiation**:
   - $2^{10} \pmod{1000} = 24$.
   - $3^5 \pmod 7 = 5$.
   - Fermat's Little Theorem: $2^{12} \pmod{13} = 1$.
2. **Small Known Primes**:
   - Primes from 2 up to 10,007 correctly identified.
3. **Composites**:
   - Even numbers, composite odd numbers correctly identified as false.
4. **Carmichael Pseudoprimes**:
   - Carmichael numbers $561, 1105, 1729, 2465$ (which fool Fermat test) correctly identified as composite.
5. **Boundary Invariants**:
   - $n \le 1$ returns false.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_miller_rabin_tutorial.ltl
python -m lateralus_lang check examples/miller_rabin_tutorial.ltl
pytest tests/test_compiler.py
```
