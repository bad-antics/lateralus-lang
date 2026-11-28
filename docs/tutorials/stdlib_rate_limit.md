# Standard Library Tutorial: `stdlib.rate_limit`

In modern web applications and API integrations, protecting endpoints against abuse and managing traffic spikes is crucial. The Lateralus standard library provides a robust rate-limiting module (`stdlib.rate_limit`) built natively on top of token-bucket semantics.

This tutorial walks through a practical web application scenario: protecting a booking endpoint that receives requests in bursts, exploring how the `RateLimiter` rejects excess requests, verifying whether rejected requests consume tokens, and understanding how token refill rates affect retries.

---

## 1. Core Concepts

The `RateLimiter` works using a **token bucket** algorithm:
- **Capacity (Burst Allowance):** The maximum number of tokens the bucket can hold. This defines how many requests can be processed immediately in a burst.
- **Refill Rate:** The speed at which tokens are replenished over time (e.g., tokens per second).
- **Token Consumption:** Each incoming request attempts to consume one or more tokens. If sufficient tokens are available, the request succeeds and tokens are deducted. If insufficient tokens are available, the request is rejected immediately, and **no tokens are spent**.

---

## 2. Runnable Example: Burst Allowance & Token Exhaustion

Let's test a pinned test vector representing a booking endpoint configured with a capacity of **two tokens** and a **zero refill rate** (meaning tokens do not replenish automatically during the test).

```lateralus
use stdlib.rate_limit.{RateLimiter, RateLimitConfig}

fn main() -> Result<(), String> {
    // Configure a rate limiter with capacity = 2 and refill_rate = 0.0
    let config = RateLimitConfig {
        capacity: 2,
        refill_rate: 0.0
    }
    
    let limiter = RateLimiter.new(config)

    // 1. A request for three tokens should fail without spending any.
    // Since capacity is 2, requesting 3 exceeds the bucket capacity.
    let burst_request = limiter.try_acquire(3)
    match burst_request {
        Ok(_) => return Err("Expected large burst to fail"),
        Err(err) => {
            println("Large burst correctly rejected: {err}")
        }
    }

    // Verify bucket is still intact (tokens remaining should still be 2)
    let remaining_before = limiter.tokens_remaining()
    assert(remaining_before == 2, "Rejected request should not spend tokens!")

    // 2. Two single requests should then succeed.
    let req1 = limiter.try_acquire(1)
    assert(req1.is_ok(), "First single request should succeed")

    let req2 = limiter.try_acquire(1)
    assert(req2.is_ok(), "Second single request should succeed")

    println("Two single requests processed successfully. Tokens left: {limiter.tokens_remaining()}")

    // 3. The next single request should fail because tokens are now exhausted (0 remaining).
    let req3 = limiter.try_acquire(1)
    match req3 {
        Ok(_) => return Err("Expected exhausted bucket request to fail"),
        Err(err) => {
            println("Exhausted request correctly rejected: {err}")
        }
    }

    Ok(())
}
```

---

## 3. Handling Retries with a Nonzero Refill Rate

In real-world production environments, a zero refill rate is only useful for hard static limits or manual resets. For standard API rate limiting, you will configure a nonzero refill rate (e.g., replenishing 5 tokens per second).

```lateralus
use stdlib.rate_limit.{RateLimiter, RateLimitConfig}
use std.time.sleep

fn main() -> Result<(), String> {
    // Configure bucket with capacity = 2 and refill_rate = 2.0 tokens/sec
    let config = RateLimitConfig {
        capacity: 2,
        refill_rate: 2.0
    }
    
    let limiter = RateLimiter.new(config)

    // Exhaust both tokens
    let _ = limiter.try_acquire(1)
    let _ = limiter.try_acquire(1)
    
    // Next request fails immediately
    let failed = limiter.try_acquire(1)
    assert(failed.is_err(), "Should be rate limited")

    println("Tokens exhausted. Waiting 500ms for refill...")
    sleep(500) // 500ms at 2 tokens/sec adds ~1 token back

    // Retry request succeeds once refilled
    let retry = limiter.try_acquire(1)
    assert(retry.is_ok(), "Retry should succeed after token refill")
    println("Retry succeeded successfully!")

    Ok(())
}
```

## Summary

- **Burst Allowance:** Controlled by `capacity`. Allows legitimate users to send quick bursts of traffic up to the limit.
- **Atomicity & Safety:** Failed requests (due to exceeding capacity or empty buckets) **do not consume tokens**, preventing unfair penalization of clients.
- **Refill Dynamics:** Combine `capacity` and `refill_rate` to balance smooth rate-limiting with graceful error recovery via retries.