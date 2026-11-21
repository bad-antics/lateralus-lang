"""
tests/test_semver_tutorial.py - Comprehensive tests for stdlib/semver.ltl
Verifies Semantic Versioning 2.0.0 parsing, formatting, comparison, bumping,
caret/tilde compatibility checks, and round-trip serialization.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_semver_parsing_and_accessors():
    semver_src = Path("stdlib/semver.ltl").read_text(encoding="utf-8")
    driver = """
let v1 = parse("1.2.3")
let v2 = parse("v2.4.0-rc.1+x86.64")
let v3 = parse("0.1.0-alpha")

let maj1 = major(v1)
let min1 = minor(v1)
let pat1 = patch(v1)
let pre1 = prerelease(v1)
let bld1 = build_meta(v1)
let stable1 = is_stable(v1)
let is_pre1 = is_prerelease(v1)

let maj2 = major(v2)
let min2 = minor(v2)
let pat2 = patch(v2)
let pre2 = prerelease(v2)
let bld2 = build_meta(v2)
let stable2 = is_stable(v2)
let is_pre2 = is_prerelease(v2)
"""
    c = Compiler()
    res = c.compile_source(semver_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["maj1"] == 1
    assert ns["min1"] == 2
    assert ns["pat1"] == 3
    assert ns["pre1"] == ""
    assert ns["bld1"] == ""
    assert ns["stable1"] is True
    assert ns["is_pre1"] is False

    assert ns["maj2"] == 2
    assert ns["min2"] == 4
    assert ns["pat2"] == 0
    assert ns["pre2"] == "rc.1"
    assert ns["bld2"] == "x86.64"
    assert ns["stable2"] is False
    assert ns["is_pre2"] is True

def test_semver_comparisons_and_bumping():
    semver_src = Path("stdlib/semver.ltl").read_text(encoding="utf-8")
    driver = """
let a = parse("1.0.0")
let b = parse("1.0.1")
let c = parse("1.1.0")
let d = parse("2.0.0")
let pre_rel = parse("1.0.0-alpha")

let lt_ab = lt(a, b)
let gt_ca = gt(c, a)
let eq_aa = eq(a, parse("1.0.0+ignored.metadata"))
let pre_lower = lt(pre_rel, a) // prerelease < stable

let bumped_maj = bump_major(a)
let bumped_min = bump_minor(a)
let bumped_pat = bump_patch(a)

let caret_ok = satisfies_caret(parse("1.3.2"), 1, 2)
let caret_fail = satisfies_caret(parse("2.0.0"), 1, 2)
let tilde_ok = satisfies_tilde(parse("1.2.9"), 1, 2)
let tilde_fail = satisfies_tilde(parse("1.3.0"), 1, 2)

let roundtrip = to_string(parse("v3.5.7-beta.2+build.101"))
"""
    c = Compiler()
    res = c.compile_source(semver_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["lt_ab"] is True
    assert ns["gt_ca"] is True
    assert ns["eq_aa"] is True
    assert ns["pre_lower"] is True

    assert ns["bumped_maj"] == [2, 0, 0, "", ""]
    assert ns["bumped_min"] == [1, 1, 0, "", ""]
    assert ns["bumped_pat"] == [1, 0, 1, "", ""]

    assert ns["caret_ok"] is True
    assert ns["caret_fail"] is False
    assert ns["tilde_ok"] is True
    assert ns["tilde_fail"] is False

    assert ns["roundtrip"] == "3.5.7-beta.2+build.101"
