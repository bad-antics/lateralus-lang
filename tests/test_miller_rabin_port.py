"""
Unit tests validating Python and Lateralus implementations of Miller-Rabin Primality Test.
"""

from examples.ports.miller_rabin.miller_rabin import power, is_prime, count_primes

def test_modular_power():
    assert power(2, 10, 1000) == 24
    assert power(3, 4, 100) == 81
    assert power(7, 0, 13) == 1
    assert power(5, 3, 1000) == 125

def test_miller_rabin_small_primes():
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
    for p in primes:
        assert is_prime(p) is True

def test_miller_rabin_composites_and_carmichael():
    # Composites
    assert is_prime(0) is False
    assert is_prime(1) is False
    assert is_prime(4) is False
    assert is_prime(9) is False
    assert is_prime(100) is False

    # Carmichael numbers (pseudoprimes that fool Fermat tests, must be recognized as composite)
    assert is_prime(561) is False
    assert is_prime(1105) is False
    assert is_prime(1729) is False

def test_prime_counting_pi():
    assert count_primes(100) == 25
    assert count_primes(1000) == 168
    assert count_primes(10000) == 1229
    assert count_primes(50000) == 5133
