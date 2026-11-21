"""
Regression tests for stdlib/semver.ltl.

index_of()/split() are not runtime builtins — parse() raised NameError.
is_valid() also crashed (ValueError from int()) on non-numeric input
because parse() raises instead of returning an error.
Now uses _index_of()/str_split() and a validating pre-check.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "semver.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_parse_vectors():
    ns = _load()
    assert ns["parse"]("1.2.3") == [1, 2, 3, "", ""]
    assert ns["parse"]("v2.0.0") == [2, 0, 0, "", ""]
    assert ns["parse"]("1.2.3-beta.1+build.42") == [1, 2, 3, "beta.1", "build.42"]
    assert ns["parse"]("10.20.30") == [10, 20, 30, "", ""]


def test_compare_and_predicates():
    ns = _load()
    a = ns["parse"]("1.2.3")
    b = ns["parse"]("1.2.4")
    rc = ns["parse"]("1.2.3-rc.1")
    assert ns["compare"](a, b) == -1
    assert ns["compare"](a, rc) == 1  # stable > prerelease
    assert ns["lt"](a, b) is True
    assert ns["gt"](a, b) is False
    assert ns["eq"](a, ns["parse"]("1.2.3")) is True


def test_is_valid_and_helpers():
    ns = _load()
    for good in ["1.2.3", "v2.0.0", "1.2.3-beta.1+build.42", "10.20.30"]:
        assert ns["is_valid"](good) is True, good
    for bad in ["x", "1.2.x", "", "1..2", "1.2.3.4"]:
        assert ns["is_valid"](bad) is False, bad
    assert ns["bump_minor"](ns["parse"]("1.2.3")) == [1, 3, 0, "", ""]
    assert ns["bump_major"](ns["parse"]("1.2.3")) == [2, 0, 0, "", ""]
    assert ns["to_string"](ns["parse"]("v1.2.3-rc+build")) == "1.2.3-rc+build"
    assert ns["satisfies_caret"](ns["parse"]("1.5.0"), 1, 2) is True
    assert ns["satisfies_caret"](ns["parse"]("2.0.0"), 1, 2) is False
