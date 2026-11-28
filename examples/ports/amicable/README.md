# Amicable Numbers Port (Python -> Lateralus C99)

Counts and sums all amicable number pairs `(a, b)` with `2 <= a < b < upper` using $O(\sqrt{n})$ proper-divisor summation.

## Exact Output Parity (`upper = 200000`)

```bash
python3 examples/ports/amicable/amicable.py 200000
# upper=200000 pairs=20 sum=2896242

PYTHONPATH=. python3 -m lateralus_lang c examples/ports/amicable/amicable.ltl -o /tmp/amicable.c
gcc -O3 /tmp/amicable.c -lm -o /tmp/amicable
/tmp/amicable
# upper=200000 pairs=20 sum=2896242
```

## Benchmark (3-Run Median Wall Time, `upper = 200000`)

| Implementation | Median Wall Time | Output | Speedup |
|---|---:|---|---:|
| CPython 3.13 (`amicable.py`) | 13,254.3 ms | `upper=200000 pairs=20 sum=2896242` | 1.0x |
| Lateralus C99 (`gcc -O3`) | 1,362.6 ms | `upper=200000 pairs=20 sum=2896242` | 9.7x |

*Note: Compiled without external libraries on Linux x86_64.*
