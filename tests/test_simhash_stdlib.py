"""
Regression tests for stdlib/simhash.ltl.

The previous revision called `xxhash_hash64`, which is not defined
anywhere in the repo (and stdlib imports do not resolve at runtime, so
stdlib/xxhash.ltl could not be reached; its str helpers also need the
missing `bytes_of` builtin).  fingerprint() now uses a self-contained
FNV-1a 64 per-token hash.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_A = "the quick brown fox jumps over the lazy dog"
DOC_A_PUNCT = "the quick, brown fox! jumps over the lazy dog."
DOC_B = "completely unrelated text about cooking pasta"


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "simhash.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_fingerprint_deterministic():
    ns = _load()
    assert ns["fingerprint"](DOC_A) == ns["fingerprint"](DOC_A)


def test_hamming_and_similarity():
    ns = _load()
    fa = ns["fingerprint"](DOC_A)
    fb = ns["fingerprint"](DOC_B)
    assert ns["hamming"](fa, fa) == 0
    d = ns["hamming"](fa, fb)
    assert d > 10  # unrelated docs differ in many bit positions
    assert ns["similarity"](fa, fa) == 1.0


def test_near_duplicate_punctuation_insensitive():
    ns = _load()
    assert ns["near_duplicate"](DOC_A, DOC_A_PUNCT, 10) is True
    assert ns["near_duplicate"](DOC_A, DOC_B, 10) is False


def test_fingerprint_all():
    ns = _load()
    fps = ns["fingerprint_all"]([DOC_A, DOC_A, DOC_B])
    assert len(fps) == 3
    assert fps[0] == fps[1]
    assert fps[0] != fps[2]
