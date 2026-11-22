# Mastering Token Bucket Rate Limiters in Lateralus: Traffic Shaping, Burst Capacity, and Lazy Refill

Microservices, public APIs, and ingress gateways are perpetually vulnerable to traffic surges, malicious scraper bots, and cascading database overloads. Uncontrolled request spikes degrade service latency and exhaust worker threads.

While naive **Fixed Window** limiters suffer from double-burst edge vulnerabilities (where double the rate limit can be consumed across window boundaries), the **Token Bucket Algorithm** provides the gold standard for network traffic shaping:
- **Average Rate Enforcement**: Guarantees a steady long-term consumption bound.
- **Controlled Burst Tolerance**: Absorbs legitimate transient spikes up to bucket capacity.
- **Zero Background Timers**: Replenishes tokens lazily on-demand upon incoming requests, eliminating CPU polling overhead.

In this tutorial, we demonstrate how to design, simulate, and verify a Token Bucket rate limiter in Lateralus.

---

## 1. Mathematical Formulation: Lazy Continuous Replenishment

A token bucket maintains:
- **`capacity`**: Maximum number of tokens the bucket can accumulate.
- **`refill_rate`**: Number of tokens added per second.
- **`tokens`**: Current active token counter ($0 \le \text{tokens} \le \text{capacity}$).
- **`last_refill`**: Timestamp of the most recent evaluation.

Rather than running a high-frequency background timer, tokens are computed lazily on each arrival:

$$\Delta t = \text{now} - \text{last\_refill}$$
$$\text{new\_tokens} = \min(\text{capacity}, \text{tokens} + \Delta t \times \text{refill\_rate})$$

```lateralus
fn rl_replenish(current_tokens: int, last_time: int, now_time: int, capacity: int, refill_rate: int) -> int {
    let delta = now_time - last_time;
    if delta <= 0 {
        return current_tokens;
    }
    let added = delta * refill_rate;
    return min_val(capacity, current_tokens + added);
}
```

---

## 2. Request Admission & Rejection Semantics

When a request arrives requiring $C$ tokens (typically $C = 1$):
- If $\text{tokens} \ge C$: deduct $C$ tokens and admit the request (`200 OK`).
- If $\text{tokens} < C$: reject the request immediately without execution (`429 Too Many Requests`).

---

## 3. Real-World API Gateway Scenario

In edge reverse proxies, burst protection allows web clients to load complex dashboards (triggering 4 simultaneous AJAX requests) while blocking sustained automated scrapers.

See `examples/rate_limiter_tutorial.ltl` for a runnable demonstration simulating bursts, subsequent HTTP 429 throttling, and timestamp recovery.

---

## 4. End-to-End Verification with Golden Vectors

Our verification suite confirms:
- Initial full capacity burst absorption.
- Total token exhaustion resulting in immediate zero-token rejection.
- Timestamp progression injecting predictable token quotas.
- Upper-bound clamping preventing overflow beyond configured capacity.

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/rate_limiter_tutorial.ltl
python -m lateralus_lang check tests/stdlib_rate_limiter_tutorial.ltl
pytest tests/test_compiler.py
```
