# Frame of Reference (FoR) & Delta-of-Delta Compression: Invariants, Time-Series Mechanics, and Applications in Lateralus

## 1. Introduction & Theoretical Foundations

In modern columnar query engines and high-throughput time-series databases (such as Apache Parquet, Apache Lucene, ClickHouse, InfluxDB, and Prometheus TSDB), raw numeric streams frequently exhibit strong local clustering or periodic regularity.

Two primary classes of numerical columns dominate analytical systems:
1. **Narrow-Range Clustered Integers**: Epoch timestamps, sequential foreign keys, virtual memory addresses, or hardware counter readings that span high base values (e.g. $4,194,304 \dots 4,194,320$) while varying within small local bounds. Storing each value as a full 64-bit integer wastes up to 60 bits per row.
2. **Periodic Time-Series Timestamps**: Real-time telemetry, IoT sensors, and financial market tickers emitted at approximately uniform intervals (e.g. every $10$ seconds, with minor microsecond network jitter). Consecutive differences are nearly identical.

To maximize storage density and memory bandwidth efficiency, analytical systems deploy two complementary encoding codecs implemented in Lateralus's standard library `stdlib/frame_of_reference.ltl`:
- **Frame of Reference (FoR)**: Subtracts a baseline reference (typically the column minimum) to minimize residual bit width.
- **Gorilla Delta-of-Delta (DoD)**: Calculates second-order differences on monotonically increasing timestamps, collapsing steady-rate sequences into zeros.

---

## 2. Mathematical Foundations & Compression Dynamics

### Frame of Reference (FoR) Mechanics
Let an integer column $X = [x_0, x_1, \dots, x_{n-1}]$ be given. We designate the reference frame $R$ as the minimum element of the sequence:
$$R = \min_{0 \le i < n} x_i$$

Each scalar value is transformed into a non-negative residual delta:
$$\Delta_i = x_i - R \ge 0$$

The maximum delta $\Delta_{\max} = \max_i \Delta_i$ dictates the exact bit width $w$ required to represent every residual without overflow:
$$w = \begin{cases} 1 & \text{if } \Delta_{\max} \le 0 \\ \lfloor \log_2 \Delta_{\max} \rfloor + 1 & \text{if } \Delta_{\max} > 0 \end{cases}$$

Lateralus calculates this bit width using efficient binary right-shifts:
```lateralus
fn bit_width(v: int) -> int {
    if v <= 0 { return 1 }
    let b = 0
    while v > 0 { v = v >> 1; b = b + 1 }
    return b
}
```

#### Bit-Budget Comparison
For $n = 1,000,000$ integers clustered within a range of $15$ above a large base:
- **Raw 64-bit Storage**:
  $$S_{\text{raw}} = 1,000,000 \times 64\text{ bits} = 8,000,000\text{ bytes} \approx 8.0\text{ MB}$$
- **FoR Encoded Storage**:
  $\Delta_{\max} = 15 \implies w = 4\text{ bits}$ per residual.
  $$S_{\text{FoR}} = 8\text{ bytes (reference)} + \frac{1,000,000 \times 4\text{ bits}}{8\text{ bits/byte}} = 500,008\text{ bytes} \approx 500\text{ KB}$$
**Net Compression**: A **$16 \times$** storage reduction ($93.75\%$ memory savings).

---

### Gorilla Delta-of-Delta (DoD) Time-Series Encoding
In Facebook's seminal paper (*"Gorilla: A Fast, Scalable, In-Memory Time Series Database"* by Pelkonen et al., 2015), timestamps $T = [t_0, t_1, \dots, t_{n-1}]$ are compressed via second-order differencing.

1. **First-Order Differences (Inter-arrival intervals)**:
   $$d_i = t_i - t_{i-1} \quad (i \ge 1)$$
2. **Second-Order Differences (Delta-of-Delta)**:
   $$D_i = d_i - d_{i-1} = (t_i - t_{i-1}) - (t_{i-1} - t_{i-2}) \quad (i \ge 2)$$

#### Behavior Under Regular Telemetry
When sensors sample at a steady frequency (e.g. every $10$ seconds):
$$t_i - t_{i-1} = 10 \implies D_i = 10 - 10 = 0$$
All subsequent second-order differences become exactly $0$. Instead of repeatedly writing 64-bit epoch timestamps, the stream encodes a string of $0$s, allowing downstream bit-packing or run-length encoding to achieve near-zero storage costs.

---

## 3. Algorithmic Architecture in Lateralus

`stdlib/frame_of_reference.ltl` provides both codecs with strict lossless guarantees:

### Frame of Reference Workflow
- **`encode(xs)`**: Extracts $R = \min(X)$, builds array $\Delta_i = x_i - R$, computes bit width $w = \text{bit\_width}(\max(\Delta))$, and returns `{"ref": R, "deltas": deltas, "bit_width": w}`.
- **`decode(enc)`**: Reconstructs each original element via addition $x_i = R + \Delta_i$.

### Delta-of-Delta Workflow
- **`encode_dod(xs)`**: Stores $t_0$ (`first`), $d_1 = t_1 - t_0$ (`second_delta`), and emits list $D_i$ for $i \ge 2$ (`dods`).
- **`decode_dod(enc)`**: Rebuilds the sequence iteratively:
  $$d_i = d_{i-1} + D_i$$
  $$t_i = t_{i-1} + d_i$$
  Achieving exact bit-level round-trip equality:
  $$\text{decode\_dod}(\text{encode\_dod}(T)) \equiv T$$

---

## 4. Lateralus `stdlib/frame_of_reference.ltl` API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `encode(xs: list)` | `(list) -> map` | Compresses integer list into `{"ref": int, "deltas": list, "bit_width": int}`. |
| `decode(enc: map)` | `(map) -> list` | Restores original integer list from FoR reference and residuals. |
| `encode_dod(xs: list)` | `(list) -> map` | Computes Gorilla-style delta-of-delta encoding, returning `{"first": int, "second_delta": int, "dods": list}`. |
| `decode_dod(enc: map)` | `(map) -> list` | Reconstructs monotonic timestamp series from second-order differences. |

---

## 5. Practical Implementation & Verification

### Executing the Runnable Example
An end-to-end telemetry and timestamp compression script is provided in `examples/frame_of_reference_tutorial.ltl`:
```shell
$ python -m lateralus_lang check examples/frame_of_reference_tutorial.ltl
✓ examples/frame_of_reference_tutorial.ltl: OK
```

The example demonstrates:
- FoR compression on memory page addresses, reducing 64-bit scalars to 4-bit deltas.
- Gorilla delta-of-delta encoding on sensor timestamps with network jitter.
- Verifying exact lossless round-trip recovery across both codecs.

### Pinned Golden Test Vectors
The companion test suite `tests/stdlib_frame_of_reference_tutorial.ltl` verifies:
- Empty array edge case handling for FoR and DoD.
- Monochromatic uniform arrays ($R = v, \Delta_i = 0, w = 1$).
- Clustered integer interval tests verifying exact bit-width formulas.
- Constant-rate timestamp sequences verifying all $D_i = 0$.
- Jittered time-series streams verifying positive and negative delta-of-delta signed integers.
- Single-element boundary conditions.

Validate the test suite with the Lateralus compiler:
```shell
$ python -m lateralus_lang check tests/stdlib_frame_of_reference_tutorial.ltl
✓ tests/stdlib_frame_of_reference_tutorial.ltl: OK
```
