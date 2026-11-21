"""
tests/test_semver.py  -  stdlib/semver.ltl precedence regression tests
===========================================================================
Guards SemVer 2.0.0 section 11 pre-release precedence in `semver.compare`:
dot-separated identifiers are compared individually, numeric identifiers
numerically, numeric identifiers rank below non-numeric ones, and a larger
set of identifiers wins when all preceding identifiers are equal.

Regression for: semver.compare reversed numeric prerelease precedence
(`1.0.0-beta.2` sorted above `1.0.0-beta.11`).
"""
import functools
import itertools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest

from lateralus_lang.compiler import Compiler, Target

ROOT = pathlib.Path(__file__).parent.parent
SEMVER = ROOT / "stdlib" / "semver.ltl"


@pytest.fixture(scope="module")
def semver():
    """Compile and exec the real stdlib/semver.ltl via the Python backend."""
    r = Compiler().compile_source(
        SEMVER.read_text(), target=Target.PYTHON, filename="semver.ltl"
    )
    assert r.ok, f"stdlib/semver.ltl failed: {r.errors[0].message if r.errors else '?'}"
    ns = {"__name__": "semver_under_test"}
    exec(r.python_src, ns)
    return ns


def V(spec):
    """Build the documented version list [major, minor, patch, pre, build]."""
    core, _, pre = spec.partition("-")
    major, minor, patch = (core.split(".") + ["0", "0"])[:3]
    return [int(major), int(minor), int(patch), pre, ""]


# SemVer 2.0.0 section 11 published ordering, strictly ascending.
PRECEDENCE_CHAIN = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
    "1.0.1",
    "1.1.0",
    "2.0.0",
]


@pytest.mark.stdlib
@pytest.mark.parametrize(
    "lower,higher", list(itertools.combinations(PRECEDENCE_CHAIN, 2))
)
def test_published_precedence_chain(semver, lower, higher):
    """Every pair in the spec's ordering compares in the documented direction."""
    assert semver["compare"](V(lower), V(higher)) == -1
    assert semver["compare"](V(higher), V(lower)) == 1


@pytest.mark.stdlib
@pytest.mark.parametrize("spec", PRECEDENCE_CHAIN)
def test_compare_is_reflexive(semver, spec):
    assert semver["compare"](V(spec), V(spec)) == 0


@pytest.mark.stdlib
@pytest.mark.parametrize(
    "a,b,expected",
    [
        # Numeric identifiers compare numerically, not lexicographically.
        ("1.0.0-beta.2", "1.0.0-beta.11", -1),
        ("1.0.0-beta.11", "1.0.0-beta.2", 1),
        ("1.0.0-alpha.9", "1.0.0-alpha.10", -1),
        ("1.0.0-100", "1.0.0-99", 1),
        ("1.0.0-0", "1.0.0-1", -1),
        # Numeric identifiers always rank below non-numeric ones.
        ("1.0.0-1", "1.0.0--", -1),
        ("1.0.0--", "1.0.0-1", 1),
        ("1.0.0-2", "1.0.0-alpha", -1),
        # Non-numeric identifiers compare lexically in ASCII order.
        ("1.0.0-A", "1.0.0-a", -1),
        ("1.0.0-rc.1.alpha", "1.0.0-rc.1.1", 1),
        # A larger set of identifiers wins when the shared ones are equal.
        ("1.0.0-alpha", "1.0.0-alpha.1", -1),
        ("1.0.0-a.1", "1.0.0-a.1.0", -1),
        ("1.0.0-a.1.2", "1.0.0-a.1.10", -1),
        # Pre-release ranks below the matching stable release.
        ("1.0.0-rc.1", "1.0.0", -1),
        ("1.0.0", "1.0.0-rc.1", 1),
        # major.minor.patch still dominates the pre-release tag.
        ("1.0.0-rc.1", "1.0.1-alpha", -1),
        ("2.0.0-alpha", "1.9.9", 1),
        # Equality.
        ("1.0.0-beta.2", "1.0.0-beta.2", 0),
        ("1.0.0", "1.0.0", 0),
    ],
)
def test_compare_cases(semver, a, b, expected):
    assert semver["compare"](V(a), V(b)) == expected


@pytest.mark.stdlib
def test_sorting_matches_published_order(semver):
    """compare() is a usable sort key over the full precedence chain."""
    shuffled = (
        PRECEDENCE_CHAIN[::3] + PRECEDENCE_CHAIN[1::3] + PRECEDENCE_CHAIN[2::3]
    )
    assert sorted(
        shuffled,
        key=functools.cmp_to_key(lambda x, y: semver["compare"](V(x), V(y))),
    ) == PRECEDENCE_CHAIN


@pytest.mark.stdlib
def test_helpers_delegate_to_compare(semver):
    """lt/gt/lte/gte/eq inherit the corrected pre-release ordering."""
    older = V("1.0.0-beta.2")
    newer = V("1.0.0-beta.11")
    assert semver["lt"](older, newer)
    assert semver["gt"](newer, older)
    assert not semver["gt"](older, newer)
    assert semver["lte"](older, older)
    assert semver["gte"](older, older)
    assert semver["eq"](older, V("1.0.0-beta.2"))
