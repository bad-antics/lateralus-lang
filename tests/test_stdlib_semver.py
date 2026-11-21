"""
Regression tests for stdlib/semver.ltl.
Covers SemVer 2.0.0 Section 11 prerelease comparison rules (Issue #79).
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent
SEMVER_LTL = REPO_ROOT / "stdlib" / "semver.ltl"


def _compile_semver():
    result = Compiler().compile_source(SEMVER_LTL.read_text("utf-8"), target=Target.PYTHON)
    assert result.ok, f"compile failed: {result.errors}"
    ns = {"__name__": "semver_test"}
    exec(result.python_src, ns)
    return ns


def test_semver_compare_prerelease_precedence():
    """Verify numeric vs non-numeric and numeric vs numeric precedence under SemVer 2.0.0 section 11."""
    ns = _compile_semver()
    compare = ns["compare"]

    cases = [
        ("beta.2", "beta.11", -1),
        ("beta.11", "beta.2", 1),
        ("alpha.9", "alpha.10", -1),
        ("1", "-", -1),
        ("alpha", "alpha.1", -1),
        ("alpha.1", "alpha.beta", -1),
        ("beta", "beta.2", -1),
        ("rc.1", "", -1),
        ("", "rc.1", 1),
        ("beta.2", "beta.2", 0),
    ]

    for a, b, expected in cases:
        v_a = [1, 0, 0, a, ""]
        v_b = [1, 0, 0, b, ""]
        actual = compare(v_a, v_b)
        assert actual == expected, f"Failed: {a!r} vs {b!r}, got {actual}, expected {expected}"


def test_semver_compare_all_targets():
    """Ensure semver.ltl compiles cleanly to Python, JavaScript, and C targets."""
    source = SEMVER_LTL.read_text("utf-8")
    for target in [Target.PYTHON, Target.JAVASCRIPT, Target.C]:
        res = Compiler().compile_source(source, target=target)
        assert res.ok, f"target {target.name} compile failed: {res.errors}"
