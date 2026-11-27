"""
Unit tests validating Python and Lateralus implementations of the Extended GCD port.
"""

from examples.ports.egcd.egcd import egcd, mod_inv, sum_inverses

def test_egcd_known_values():
    g, x = egcd(10, 6)
    assert g == 2
    g, x = egcd(35, 15)
    assert g == 5
    g, x = egcd(17, 31)
    assert g == 1

def test_mod_inv_coprime():
    # 3 * 7 = 21 = 2 * 10 + 1 => inv(3, 10) = 7
    assert mod_inv(3, 10) == 7
    # 2 * 3 = 6 = 1 * 5 + 1 => inv(2, 5) = 3
    assert mod_inv(2, 5) == 3
    # Prime modulus 1000000007
    p = 1000000007
    assert (2 * mod_inv(2, p)) % p == 1
    assert (17 * mod_inv(17, p)) % p == 1

def test_mod_inv_non_coprime():
    assert mod_inv(4, 8) == -1
    assert mod_inv(6, 9) == -1

def test_sum_inverses_bounds():
    p = 1000000007
    assert sum_inverses(10, p) == 728968262
    assert sum_inverses(100, p) == 632742311
    assert sum_inverses(1000, p) == 184900353
    assert sum_inverses(100000, p) == 337069953
