"""
Unit tests validating Python and Lateralus implementations of the Collatz port.
"""

from examples.ports.collatz.collatz import collatz_len, max_collatz_under

def test_collatz_len_known_values():
    assert collatz_len(1) == 1
    assert collatz_len(2) == 2
    assert collatz_len(3) == 8
    assert collatz_len(4) == 3
    assert collatz_len(5) == 6
    assert collatz_len(6) == 9
    assert collatz_len(7) == 17
    assert collatz_len(13) == 10

def test_max_collatz_under_bounds():
    # Under 10: 9 has length 20
    start_10, len_10 = max_collatz_under(10)
    assert start_10 == 9
    assert len_10 == 20

    # Under 100: 97 has length 119
    start_100, len_100 = max_collatz_under(100)
    assert start_100 == 97
    assert len_100 == 119

    # Under 1000: 871 has length 179
    start_1k, len_1k = max_collatz_under(1000)
    assert start_1k == 871
    assert len_1k == 179

    # Under 10000: 6171 has length 262
    start_10k, len_10k = max_collatz_under(10000)
    assert start_10k == 6171
    assert len_10k == 262

    # Under 100000: 77031 has length 351
    start_100k, len_100k = max_collatz_under(100000)
    assert start_100k == 77031
    assert len_100k == 351
