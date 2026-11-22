"""
Regression tests for stdlib/bloom.ltl.

The previous revision could not run: `import hash` does not resolve at
runtime, it called hash_fnv1a_* names that stdlib/hash.ltl does not
export, it used missing char_code/xor builtins, and `/` produced floats
for word indexing.  This revision is self-contained and verified here.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "bloom.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_fnv1a_reference_values():
    ns = _load()
    # FNV-1a 32 of "abc" (known reference value)
    assert ns["fnv1a_32"]("abc") == 440920331
    # empty string -> offset basis
    assert ns["fnv1a_32"]("") == 2166136261


def test_bloom_membership_no_false_negatives():
    ns = _load()
    f = ns["new_filter"](128, 4)
    for key in ["apple", "banana", "cherry"]:
        ns["add"](f, key)
    assert f["count"] == 3
    for key in ["apple", "banana", "cherry"]:
        assert ns["contains_key"](f, key) is True
    # absent key may rarely false-positive; check a spread of probes and
    # require the vast majority to be negative (no false negatives is
    # the guarantee; FP rate is probabilistic)
    negatives = sum(
        1 for i in range(200)
        if not ns["contains_key"](f, f"probe_{i}")
    )
    assert negatives >= 190  # <= ~5% FP on this sizing


def test_optimal_params_and_union_intersect():
    ns = _load()
    assert ns["optimal_params"](100, 10) == [900, 9]
    assert ns["optimal_params"](100, 1) == [1200, 12]
    a = ns["new_filter"](64, 3)
    b = ns["new_filter"](64, 3)
    ns["add"](a, "x")
    ns["add"](a, "y")
    ns["add"](b, "y")
    ns["add"](b, "z")
    u = ns["union"](a, b)
    assert ns["contains_key"](u, "x") is True
    assert ns["contains_key"](u, "y") is True
    assert ns["contains_key"](u, "z") is True
    inter = ns["intersect"](a, b)
    assert ns["contains_key"](inter, "x") is False
    assert ns["contains_key"](inter, "y") is True
    # mismatched shapes -> nil
    assert ns["union"](a, ns["new_filter"](32, 3)) is None
