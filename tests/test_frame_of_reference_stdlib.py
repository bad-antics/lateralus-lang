"""
Regression tests for stdlib/frame_of_reference.ltl.

encode_dod previously emitted no element count, so decode_dod could not
distinguish a 1-element column from a 2-element constant-delta column:
encode_dod([5, 5]) decoded as [5] — silent data loss.  encode_dod now
records `count` and decode_dod prefers it (with a legacy fallback).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "frame_of_reference.ltl"),
        target=Target.PYTHON,
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_dod_roundtrip_including_constant_pairs():
    ns = _load()
    cases = [
        [],
        [5],
        [5, 5],          # was decoded as [5] before the fix
        [10, 10, 10, 10],
        [1, 2, 4, 7, 11],
        [-3, -1, 2, 2, 9],
        [0, 1],
    ]
    for xs in cases:
        assert ns["decode_dod"](ns["encode_dod"](xs)) == xs, xs


def test_legacy_encoding_still_decodes():
    ns = _load()
    # encoding produced before `count` existed
    enc = {"first": 1, "second_delta": 2, "dods": [1, 1]}
    assert ns["decode_dod"](enc) == [1, 3, 6, 10]


def test_for_encode_decode_roundtrip():
    ns = _load()
    for xs in [[5, 5], [1, 2, 4, 7, 11], [], [-3, -1, 2]]:
        assert ns["decode"](ns["encode"](xs)) == xs, xs
