"""
Regression tests for stdlib/base64.ltl.

The previous revision used the missing `char_code` builtin and raw `/`
division (which yields floats in Lateralus), corrupting sextet math and
string indexing.  Now uses `ord` + `int()`.  Verified against Python's
base64 for the RFC 4648 test vectors.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "base64.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


@pytest.fixture(scope="module")
def b64():
    return _load()


@pytest.mark.parametrize("s", ["", "a", "ab", "abc", "f", "fo", "foo",
                               "foob", "fooba", "foobar", "hello world"])
def test_encode_matches_python_base64(b64, s):
    assert b64["encode"](s) == base64.b64encode(s.encode()).decode()


@pytest.mark.parametrize("s", ["", "a", "ab", "abc", "foobar", "hello world"])
def test_decode_roundtrip(b64, s):
    assert b64["decode"](b64["encode"](s)) == s


def test_urlsafe_and_utils(b64):
    assert b64["encode_url"]("a?b") == "YT9i"
    assert b64["is_valid"]("aGVsbG8=") is True
    assert b64["is_valid"]("aGVsbG8") is False
    assert b64["encoded_length"](3) == 4
    assert b64["decoded_length"]("aGVsbG8=") == 5
