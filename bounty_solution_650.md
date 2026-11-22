2. Code Patch / Fix

**File: `stdlib/rational.ltl`**
```lateralus
// Canonical Rational Number Implementation
// Ensures all rationals are stored in reduced form (gcd(n, d) == 1) and d > 0.

type Rational {
    num: Int,
    den: Int
}

// Euclidean GCD
fn gcd(a: Int, b: Int) -> Int {
    let a = abs(a)
    let b = abs(b)
    if b == 0 { a } else { gcd(b, a % b) }
}

// Normalize a rational number
fn normalize(num: Int, den: Int) -> Rational {
    if den == 0 {
        panic("Division by zero in Rational construction")
    }
    let g = gcd(num, den)
    let n = num / g
    let d = den / g
    // Ensure denominator is positive
    if d < 0 {
        Rational { num: -n, den: -d }
    } else {
        Rational { num: n, den: d }
    }
}

fn rational_from_int(n: Int) -> Rational {
    normalize(n, 1)
}

fn rational_from_str(s: String) -> Rational {
    // Simple parser for "num/den" or "num"
    let parts = s.split("/")
    if len(parts) == 1 {
        rational_from_int(parse_int(parts[0]))
    } else {
        normalize(parse_int(parts[0]), parse_int(parts[1]))
    }
}

// Arithmetic Operations
fn rational_add(a: Rational, b: Rational) -> Rational {
    let n = a.num * b.den + b.num * a.den
    let d = a.den * b.den
    normalize(n, d)
}

fn rational_sub(a: Rational, b: Rational) -> Rational {
    let n = a.num * b.den - b.num * a.den
    let d = a.den * b.den
    normalize(n, d)
}

fn rational_mul(a: Rational, b: Rational) -> Rational {
    let n = a.num * b.num
    let d = a.den * b.den
    normalize(n, d)
}

fn rational_div(a: Rational, b: Rational) -> Rational {
    if b.num == 0 {
        panic("Division by zero rational")
    }