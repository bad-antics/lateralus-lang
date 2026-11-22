# Extended Euclidean Algorithm Tutorial: Bézout's Identity and Modular Inverses

## Overview

The classical Euclidean algorithm computes the greatest common divisor $\gcd(a, b)$ of two integers by repeatedly taking remainders. The **Extended Euclidean Algorithm** extends this process by simultaneously computing the integer **Bézout coefficients** $x$ and $y$ that satisfy **Bézout's identity**:
$$a \cdot x + b \cdot y = \gcd(a, b)$$

In computational number theory and public-key cryptography, the Extended Euclidean Algorithm is the primary engine for computing **modular multiplicative inverses**:
- An integer $a$ has a modular inverse modulo $m$ if and only if $a$ and $m$ are coprime ($\gcd(a, m) = 1$).
- When $\gcd(a, m) = 1$, Bézout's identity reduces to:
  $$a \cdot x + m \cdot y = 1 \implies a \cdot x \equiv 1 \pmod m$$
  Thus, $x \pmod m$ is the unique modular inverse $a^{-1} \pmod m$.

In modern crypto protocols, modular inverses are ubiquitous:
- **RSA Cryptosystem**: Deriving private decryption exponents $d \equiv e^{-1} \pmod{\phi(n)}$.
- **Elliptic Curve Cryptography (ECC)**: Point doubling and addition slopes $\lambda = \frac{3x_1^2 + a}{2y_1} \pmod p$ in curves like secp256k1 (Bitcoin/Ethereum) and ed25519.
- **Zero-Knowledge Proofs**: Finite field division and polynomial interpolation (Lagrange basis coefficients).

---

## State Transition Matrix

The algorithm tracks linear combinations iteratively using Euclidean division quotients $q = \lfloor r_{k-1} / r_k \rfloor$:

$$\begin{aligned}
r_{k+1} &= r_{k-1} - q \cdot r_k \\
s_{k+1} &= s_{k-1} - q \cdot s_k \\
t_{k+1} &= t_{k-1} - q \cdot t_k
\end{aligned}$$

Initial conditions:
$$\begin{aligned}
r_0 &= a, & r_1 &= b \\
s_0 &= 1, & s_1 &= 0 \\
t_0 &= 0, & t_1 &= 1
\end{aligned}$$

At every step $k$, the invariant $a \cdot s_k + b \cdot t_k = r_k$ holds. When remainder $r$ reaches 0, $r_{k-1} = \gcd(a, b)$, and $s_{k-1}, t_{k-1}$ are the respective Bézout coefficients $x, y$.

Time complexity is $O(\log(\min(a, b)))$ with $O(1)$ auxiliary space.

---

## Lateralus Implementation

```lateralus
fn ext_gcd(a: int, b: int) -> dict {
    let mut old_r = a;
    let mut r = b;
    let mut old_s = 1;
    let mut s = 0;
    let mut old_t = 0;
    let mut t = 1;

    while r != 0 {
        let quotient = idiv(old_r, r);
        let temp_r = r;
        r = old_r - quotient * r;
        old_r = temp_r;

        let temp_s = s;
        s = old_s - quotient * s;
        old_s = temp_s;

        let temp_t = t;
        t = old_t - quotient * t;
        old_t = temp_t;
    }

    let mut result = {};
    result["gcd"] = old_r;
    result["x"] = old_s;
    result["y"] = old_t;
    return result;
}

fn mod_inverse(a: int, m: int) -> int {
    let res = ext_gcd(a, m);
    if res["gcd"] != 1 {
        return -1; // Inverse does not exist (not coprime)
    }
    let mut inv = res["x"] % m;
    if inv < 0 {
        inv = inv + m;
    }
    return inv;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_ext_gcd_tutorial.ltl` validates:

1. **Bézout Identity**:
   - $a = 35, b = 15 \implies \gcd = 5$, $35(1) + 15(-2) = 5$.
   - $a = 120, b = 23 \implies \gcd = 1$, $120(x) + 23(y) = 1$.
2. **Modular Multiplicative Inverse**:
   - $3^{-1} \pmod{11} = 4$, verifying $(3 \times 4) \equiv 1 \pmod{11}$.
3. **RSA Private Key Exponent Generation**:
   - Public exponent $e = 17$, $\phi(n) = 3120 \implies d = 2753$, verifying $(17 \times 2753) \equiv 1 \pmod{3120}$.
4. **Non-Invertible Moduli Detection**:
   - $\gcd(6, 9) = 3 \neq 1 \implies -1$ returned.
5. **Boundary Invariants**:
   - $\gcd(a, 0) = a$ with coefficients $(1, 0)$.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_ext_gcd_tutorial.ltl
python -m lateralus_lang check examples/ext_gcd_tutorial.ltl
pytest tests/test_compiler.py
```
