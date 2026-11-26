/*
 * amicable_numbers_sum.c
 *
 * Lateralus Python-to-C99 port: Amicable Numbers pair counter and sum.
 *
 * Reference semantics (CPython):
 *   def amicable(upper):
 *       s = [0] * upper
 *       for d in range(1, upper // 2 + 1):
 *           for m in range(2 * d, upper, d):
 *               s[m] += d
 *       count = total = 0
 *       for a in range(2, upper):
 *           b = s[a]
 *           if a < b < upper and s[b] == a:
 *               count += 1
 *               total += a + b
 *       return count, total
 *
 * Build:  cc -std=c99 -O2 -o amicable amicable_numbers_sum.c
 * Run:    ./amicable            (parity tests + 3-run median benchmark)
 * Exit status is non-zero if any parity check fails.
 */

#define _POSIX_C_SOURCE 199309L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef struct {
    uint64_t count; /* number of unique amicable pairs (a < b < upper) */
    uint64_t sum;   /* sum of a + b over all such pairs                */
} amicable_result;

/* Single-pass amicable pair counter/sum for all values in [2, upper). */
static int amicable_sum(uint32_t upper, amicable_result *out)
{
    out->count = 0;
    out->sum = 0;

    if (upper < 3) {
        return 0;
    }

    uint32_t *s = (uint32_t *)calloc((size_t)upper, sizeof(uint32_t));
    if (s == NULL) {
        return -1;
    }

    /* Sieve proper-divisor sums: s[m] = sum of proper divisors of m. */
    for (uint32_t d = 1; d <= upper / 2; d++) {
        for (uint32_t m = 2u * d; m < upper; m += d) {
            s[m] += d;
        }
    }

    /* Single pass: count each pair once via a < b, both members < upper. */
    for (uint32_t a = 2; a < upper; a++) {
        uint32_t b = s[a];
        if (b > a && b < upper && s[b] == a) {
            out->count += 1;
            out->sum += (uint64_t)a + (uint64_t)b;
        }
    }

    free(s);
    return 0;
}

static double now_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static int cmp_double(const void *x, const void *y)
{
    double a = *(const double *)x;
    double b = *(const double *)y;
    return (a > b) - (a < b);
}

/* Parity self-tests against well-known reference values. */
static int run_parity_tests(void)
{
    int failures = 0;
    amicable_result r;

    /* upper = 285: only the pair (220, 284) -> count 1, sum 504 */
    if (amicable_sum(285, &r) != 0 || r.count != 1 || r.sum != 504) {
        fprintf(stderr, "FAIL upper=285: got count=%llu sum=%llu (want 1, 504)\n",
                (unsigned long long)r.count, (unsigned long long)r.sum);
        failures++;
    }

    /* upper = 284: 284 excluded -> no complete pair */
    if (amicable_sum(284, &r) != 0 || r.count != 0 || r.sum != 0) {
        fprintf(stderr, "FAIL upper=284: got count=%llu sum=%llu (want 0, 0)\n",
                (unsigned long long)r.count, (unsigned long long)r.sum);
        failures++;
    }

    /* upper = 10000: 5 pairs (220/284, 1184/1210, 2620/2924, 5020/5564, 6232/6368);
     * sum of all members = 31626 */
    if (amicable_sum(10000, &r) != 0 || r.count != 5 || r.sum != 31626) {
        fprintf(stderr, "FAIL upper=10000: got count=%llu sum=%llu (want 5, 31626)\n",
                (unsigned long long)r.count, (unsigned long long)r.sum);
        failures++;
    }

    /* degenerate bounds */
    if (amicable_sum(0, &r) != 0 || r.count != 0 || r.sum != 0) {
        fprintf(stderr, "FAIL upper=0\n");
        failures++;
    }
    if (amicable_sum(2, &r) != 0 || r.count != 0 || r.sum != 0) {
        fprintf(stderr, "FAIL upper=2\n");
        failures++;
    }

    return failures;
}

int main(void)
{
    const uint32_t upper = 200000;
    const int runs = 3;

    int failures = run_parity_tests();
    if (failures != 0) {
        fprintf(stderr, "parity: %d failure(s)\n", failures);
        return 1;
    }
    printf("parity: OK\n");

    double times[3];
    amicable_result result = {0, 0};

    for (int i = 0; i < runs; i++) {
        double t0 = now_seconds();
        if (amicable_sum(upper, &result) != 0) {
            fprintf(stderr, "allocation failure\n");
            return 2;
        }
        times[i] = now_seconds() - t0;
    }

    qsort(times, (size_t)runs, sizeof(double), cmp_double);

    printf("upper=%u pairs=%llu sum=%llu\n", upper,
           (unsigned long long)result.count, (unsigned long long)result.sum);
    printf("median_of_%d_seconds=%.6f\n", runs, times[runs / 2]);
    return 0;
}