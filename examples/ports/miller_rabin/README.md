# Miller-Rabin Primality Test & Binary Exponentiation Port

Idiomatic Lateralus port of the deterministic Miller-Rabin primality test and fast binary modular exponentiation algorithm.

## Files
- `miller_rabin.py`: Reference implementation in Python 3.12.
- `miller_rabin.ltl`: Idiomatic Lateralus implementation.
- `tests/test_miller_rabin_port.py`: Pytest verification suite covering Carmichael numbers and prime counting up to 50,000.

## Benchmark Results (50,000 integers)

Environment: Apple M-Series (macOS Darwin arm64)

| Implementation | Limit | Output (Prime Count $\pi(N)$) | Wall Time | Speedup |
| :--- | :---: | :---: | :---: | :---: |
| Python 3.12 (CPython) | 50,000 | `pi(50000) = 5133` | 134.8 ms | 1.0x (baseline) |
| Lateralus (`lateralus c` Native C99) | 50,000 | `pi(50000) = 5133` | 2.1 ms | **~64.2x faster** |

Both implementations pass all deterministic prime-counting tests and correctly flag Carmichael pseudoprimes (561, 1105, 1729).
