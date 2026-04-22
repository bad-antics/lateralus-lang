"""Tests for ternary algebraic structure law discovery (pillar 10)."""
from __future__ import annotations

from lateralus_lang.law_triangulator import (
    TERNARY_RELATIONS,
    TernaryLaw,
    find_ternary_laws,
    triangulate_file,
)


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


# ─── Catalog ──────────────────────────────────────────────────────────────

def test_catalog_contains_expected_relations():
    kinds = {r.kind for r in TERNARY_RELATIONS}
    assert "left_distributive" in kinds
    assert "right_distributive" in kinds
    assert "homomorphism" in kinds
    assert "anti_homomorphism" in kinds


# ─── Distributivity ───────────────────────────────────────────────────────

def test_distributivity_times_over_plus(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}
"""
    f = _write(tmp_path, "dist.ltl", src)
    laws = find_ternary_laws(f, trials=40, seed=1)
    kinds = [(l.relation_kind, l.f_name, l.g_name) for l in laws]
    assert ("left_distributive",  "times", "plus") in kinds
    assert ("right_distributive", "times", "plus") in kinds


def test_no_distributivity_plus_over_times(tmp_path):
    # Addition does NOT distribute over multiplication:
    #   a + (b * c)  ≠  (a + b) * (a + c)
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}
"""
    f = _write(tmp_path, "nd.ltl", src)
    laws = find_ternary_laws(f, trials=40, seed=1)
    # plus over times should NOT appear
    kinds = [(l.relation_kind, l.f_name, l.g_name) for l in laws]
    assert ("left_distributive",  "plus", "times") not in kinds
    assert ("right_distributive", "plus", "times") not in kinds


# ─── Homomorphism ─────────────────────────────────────────────────────────

def test_negate_is_homomorphism_over_plus(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn negate(x: int) -> int {
    return 0 - x
}
"""
    f = _write(tmp_path, "hom.ltl", src)
    laws = find_ternary_laws(f, trials=40, seed=1)
    hom = [l for l in laws if l.relation_kind == "homomorphism"]
    assert any(l.f_name == "plus" and l.g_name == "negate" for l in hom)


def test_double_is_homomorphism_over_plus(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn double(x: int) -> int {
    return x * 2
}
"""
    f = _write(tmp_path, "hom2.ltl", src)
    laws = find_ternary_laws(f, trials=40, seed=1)
    hom = [l for l in laws if l.relation_kind == "homomorphism"]
    assert any(l.f_name == "plus" and l.g_name == "double" for l in hom)


# ─── Non-homomorphism ─────────────────────────────────────────────────────

def test_square_is_not_homomorphism_over_plus(tmp_path):
    # (x+y)^2  ≠  x^2 + y^2 in general
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn square(x: int) -> int {
    return x * x
}
"""
    f = _write(tmp_path, "nh.ltl", src)
    laws = find_ternary_laws(f, trials=40, seed=1)
    hom = [(l.relation_kind, l.f_name, l.g_name) for l in laws]
    assert ("homomorphism", "plus", "square") not in hom
    assert ("anti_homomorphism", "plus", "square") not in hom


# ─── Emitted LTL is parseable ─────────────────────────────────────────────

def test_emitted_ternary_laws_parse(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}

fn negate(x: int) -> int {
    return 0 - x
}
"""
    f = _write(tmp_path, "p.ltl", src)
    laws = find_ternary_laws(f, trials=30, seed=2)
    assert laws

    from lateralus_lang.compiler import Compiler, Target
    for law in laws:
        snippet = src + "\n\n" + law.as_ltl_law() + "\n"
        r = Compiler().compile_source(snippet, target=Target.PYTHON, filename="p.ltl")
        assert r.ok, f"Law did not parse: {law.as_ltl_law()}  errors={r.errors}"


# ─── File driver ──────────────────────────────────────────────────────────

def test_triangulate_file_rc_success(tmp_path, capsys):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}
"""
    f = _write(tmp_path, "t.ltl", src)
    rc = triangulate_file(f, trials=30, seed=1)
    assert rc == 0
    out = capsys.readouterr().out
    assert "distributive" in out


def test_triangulate_file_rc_nothing_found(tmp_path, capsys):
    src = """fn weird(x: int) -> int {
    return x * 3 + 17
}
"""
    f = _write(tmp_path, "nt.ltl", src)
    rc = triangulate_file(f, trials=30, seed=1)
    assert rc == 1
    assert "No ternary structure laws" in capsys.readouterr().out


# ─── --apply is idempotent ────────────────────────────────────────────────

def test_triangulate_apply_idempotent(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}

fn main() {
    println("hi")
}

main()
"""
    f = _write(tmp_path, "a.ltl", src)

    rc1 = triangulate_file(f, trials=30, seed=1, apply=True)
    assert rc1 == 0
    first = f.read_text()
    assert "lateralus triangulate" in first
    assert first.count("lateralus triangulate (auto-generated") == 1

    rc2 = triangulate_file(f, trials=30, seed=1, apply=True)
    assert rc2 == 0
    second = f.read_text()
    assert second.count("lateralus triangulate (auto-generated") == 1
    assert abs(len(second) - len(first)) < 20


# ─── -o writes output ────────────────────────────────────────────────────

def test_triangulate_output_file(tmp_path):
    src = """fn plus(a: int, b: int) -> int {
    return a + b
}

fn times(a: int, b: int) -> int {
    return a * b
}
"""
    f = _write(tmp_path, "o.ltl", src)
    out_path = tmp_path / "out.ltl"
    rc = triangulate_file(f, trials=30, seed=1, output=str(out_path))
    assert rc == 0
    content = out_path.read_text()
    assert "@law" in content
    assert "distributive" in content


# ─── TernaryLaw rendering ─────────────────────────────────────────────────

def test_law_name_format():
    law = TernaryLaw(
        relation_kind="left_distributive",
        f_name="times", g_name="plus",
        f_arity=2, g_arity=2,
        param_types=[int, int],
        trials_passed=80,
        lhs_expr="times(x, plus(y, z))",
        rhs_expr="plus(times(x, y), times(x, z))",
    )
    assert law.law_name() == "times_left_distributive_plus"
    ltl = law.as_ltl_law()
    assert "x: int, y: int, z: int" in ltl
    assert "times(x, plus(y, z))" in ltl
    assert "plus(times(x, y), times(x, z))" in ltl


def test_homomorphism_law_has_two_params():
    law = TernaryLaw(
        relation_kind="homomorphism",
        f_name="plus", g_name="negate",
        f_arity=2, g_arity=1,
        param_types=[int, int],
        trials_passed=80,
        lhs_expr="negate(plus(x, y))",
        rhs_expr="plus(negate(x), negate(y))",
    )
    ltl = law.as_ltl_law()
    # Homomorphism uses (x, y), not (x, y, z)
    assert "x: int, y: int" in ltl
    assert ", z:" not in ltl
