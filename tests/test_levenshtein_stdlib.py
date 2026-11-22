"""
Regression tests for stdlib/levenshtein.ltl.

char_at() is not a runtime builtin — distance()/bounded()/damerau()
all raised NameError on any non-empty input.  Now uses slice().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "levenshtein.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def _ref_dl(a: str, b: str) -> int:
    """Optimal-string-alignment Damerau-Levenshtein reference."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            v = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, d[i - 2][j - 2] + 1)
            d[i][j] = v
    return d[n][m]


def test_distance_classic_vectors():
    ns = _load()
    assert ns["distance"]("kitten", "sitting") == 3
    assert ns["distance"]("abc", "abd") == 1
    assert ns["distance"]("", "abc") == 3
    assert ns["distance"]("abc", "abc") == 0
    assert ns["distance"]("flaw", "lawn") == 2


def test_bounded_early_exit():
    ns = _load()
    assert ns["bounded"]("abc", "abd", 0) == 1
    assert ns["bounded"]("abc", "abc", 0) == 0
    assert ns["bounded"]("abcdef", "xbcdyf", 0) == 1
    # bound exceeded -> k+1 sentinel
    assert ns["bounded"]("kitten", "sitting", 2) == 3
    assert ns["bounded"]("abc", "xyz", 1) == 2


def test_similarity_and_damerau():
    ns = _load()
    assert abs(ns["similarity"]("kitten", "sitting") - (1 - 3 / 7)) < 1e-9
    assert ns["similarity"]("abc", "abc") == 1.0
    for a, b in [("ca", "abc"), ("kitten", "sitting"), ("", "ab"), ("ab", "ba")]:
        assert ns["damerau"](a, b) == _ref_dl(a, b), (a, b)
