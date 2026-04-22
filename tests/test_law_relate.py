"""Tests for cross-function relational law discovery (pillar 9)."""
from __future__ import annotations

from lateralus_lang.law_relator import (
    RELATIONS,
    RelationalLaw,
    find_relational_laws,
    relate_file,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────

def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


# ─── Smoke ────────────────────────────────────────────────────────────────

def test_relations_catalog_nonempty():
    assert len(RELATIONS) >= 6
    kinds = {r.kind for r in RELATIONS}
    assert "inverse" in kinds
    assert "involution" in kinds
    assert "commuting" in kinds
    assert "equivalent" in kinds


# ─── Inverse pair ─────────────────────────────────────────────────────────

def test_find_inverse_pair(tmp_path):
    src = """fn inc(x: int) -> int {
    return x + 1
}

fn dec(x: int) -> int {
    return x - 1
}
"""
    f = _write(tmp_path, "inv.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    kinds = {l.relation_kind for l in laws}
    assert "inverse" in kinds
    inv_laws = [l for l in laws if l.relation_kind == "inverse"]
    # Both directions: inc(dec(x))==x AND dec(inc(x))==x
    names = {(l.f_name, l.g_name) for l in inv_laws}
    assert ("inc", "dec") in names or ("dec", "inc") in names


# ─── Involution ──────────────────────────────────────────────────────────

def test_find_involution(tmp_path):
    src = """fn negate(x: int) -> int {
    return 0 - x
}
"""
    f = _write(tmp_path, "inv2.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    invols = [l for l in laws if l.relation_kind == "involution"]
    assert len(invols) == 1
    assert invols[0].f_name == "negate"
    assert invols[0].g_name == "negate"


# ─── Idempotent composition ──────────────────────────────────────────────

def test_find_idempotent_composition(tmp_path):
    src = """fn abs_val(x: int) -> int {
    if x < 0 {
        return 0 - x
    }
    return x
}
"""
    f = _write(tmp_path, "idem.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    idems = [l for l in laws if l.relation_kind == "idempotent_compose"]
    assert len(idems) == 1
    assert idems[0].f_name == "abs_val"


# ─── Extensional equivalence ─────────────────────────────────────────────

def test_find_equivalent_pair(tmp_path):
    src = """fn double(x: int) -> int {
    return x * 2
}

fn twice(x: int) -> int {
    return x + x
}
"""
    f = _write(tmp_path, "eq.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    eqs = [l for l in laws if l.relation_kind == "equivalent"]
    assert len(eqs) == 1
    names = {eqs[0].f_name, eqs[0].g_name}
    assert names == {"double", "twice"}


# ─── Commuting ───────────────────────────────────────────────────────────

def test_find_commuting(tmp_path):
    # Any two additive shifts commute: (x+a)+b == (x+b)+a
    src = """fn add5(x: int) -> int {
    return x + 5
}

fn add7(x: int) -> int {
    return x + 7
}
"""
    f = _write(tmp_path, "com.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    coms = [l for l in laws if l.relation_kind == "commuting"]
    assert len(coms) >= 1


# ─── Absorption ──────────────────────────────────────────────────────────

def test_find_absorbs(tmp_path):
    # abs(negate(x)) == abs(x): negate is absorbed by abs
    src = """fn negate(x: int) -> int {
    return 0 - x
}

fn abs_val(x: int) -> int {
    if x < 0 {
        return 0 - x
    }
    return x
}
"""
    f = _write(tmp_path, "abs.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    absorbs = [l for l in laws if l.relation_kind == "absorbs"]
    # abs_val absorbs negate
    assert any(l.f_name == "abs_val" and l.g_name == "negate" for l in absorbs)


# ─── Non-relational functions yield no laws ──────────────────────────────

def test_unrelated_functions_no_laws(tmp_path):
    src = """fn foo(x: int) -> int {
    return x * 3 + 7
}

fn bar(x: int) -> int {
    return x * x - 2
}
"""
    f = _write(tmp_path, "no.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    # Neither commutes nor equivalent nor inverse — nothing should match
    kinds = {l.relation_kind for l in laws}
    assert "inverse" not in kinds
    assert "equivalent" not in kinds


# ─── Emitted LTL is parseable ─────────────────────────────────────────────

def test_emitted_laws_parse(tmp_path):
    src = """fn inc(x: int) -> int {
    return x + 1
}

fn dec(x: int) -> int {
    return x - 1
}
"""
    f = _write(tmp_path, "p.ltl", src)
    laws = find_relational_laws(f, trials=30, seed=2)
    assert laws

    from lateralus_lang.compiler import Compiler, Target
    for law in laws:
        snippet = src + "\n\n" + law.as_ltl_law() + "\n"
        r = Compiler().compile_source(snippet, target=Target.PYTHON, filename="p.ltl")
        assert r.ok, f"Law did not parse: {law.as_ltl_law()}  errors={r.errors}"


# ─── Equivalent-on-arity-2 ────────────────────────────────────────────────

def test_equivalent_arity2(tmp_path):
    src = """fn add_ab(a: int, b: int) -> int {
    return a + b
}

fn add_ba(a: int, b: int) -> int {
    return b + a
}
"""
    f = _write(tmp_path, "eq2.ltl", src)
    laws = find_relational_laws(f, trials=40, seed=1)
    arity2 = [l for l in laws if l.arity == 2]
    assert any(l.relation_kind == "equivalent" for l in arity2)


# ─── File driver — return code ────────────────────────────────────────────

def test_relate_file_rc_success(tmp_path, capsys):
    src = """fn inc(x: int) -> int {
    return x + 1
}

fn dec(x: int) -> int {
    return x - 1
}
"""
    f = _write(tmp_path, "r.ltl", src)
    rc = relate_file(f, trials=30, seed=1)
    assert rc == 0
    out = capsys.readouterr().out
    assert "inverse" in out
    assert "inc_inverse_dec" in out or "dec_inverse_inc" in out


def test_relate_file_rc_nothing_found(tmp_path, capsys):
    src = """fn weird(x: int) -> int {
    return x * 3 + 17
}
"""
    f = _write(tmp_path, "nr.ltl", src)
    rc = relate_file(f, trials=30, seed=1)
    assert rc == 1
    assert "No relational laws found" in capsys.readouterr().out


# ─── --apply writes banner and is idempotent ─────────────────────────────

def test_relate_apply_idempotent(tmp_path, capsys):
    src = """fn inc(x: int) -> int {
    return x + 1
}

fn dec(x: int) -> int {
    return x - 1
}

fn main() {
    println("hi")
}

main()
"""
    f = _write(tmp_path, "a.ltl", src)

    rc1 = relate_file(f, trials=30, seed=1, apply=True)
    assert rc1 == 0
    first = f.read_text()
    assert "lateralus relate" in first
    assert "@law" in first
    assert first.count("lateralus relate (auto-generated") == 1

    # Running --apply again must not accumulate duplicate blocks
    capsys.readouterr()
    rc2 = relate_file(f, trials=30, seed=1, apply=True)
    assert rc2 == 0
    second = f.read_text()
    assert second.count("lateralus relate (auto-generated") == 1
    # Body length should stay stable between runs
    assert abs(len(second) - len(first)) < 20


# ─── -o writes output file ────────────────────────────────────────────────

def test_relate_output_file(tmp_path):
    src = """fn negate(x: int) -> int {
    return 0 - x
}
"""
    f = _write(tmp_path, "o.ltl", src)
    out_path = tmp_path / "out.ltl"
    rc = relate_file(f, trials=30, seed=1, output=str(out_path))
    assert rc == 0
    content = out_path.read_text()
    assert "@law" in content
    assert "negate_involution" in content


# ─── as_ltl_law format sanity ─────────────────────────────────────────────

def test_law_name_same_fn():
    law = RelationalLaw(
        relation_kind="involution",
        f_name="negate", g_name="negate",
        arity=1, param_types=[int],
        trials_passed=80,
        lhs_expr="negate(negate(x))", rhs_expr="x",
    )
    assert law.law_name() == "negate_involution"
    ltl = law.as_ltl_law()
    assert "@law" in ltl
    assert "(negate(negate(x))) == (x)" in ltl


def test_law_name_diff_fns():
    law = RelationalLaw(
        relation_kind="inverse",
        f_name="inc", g_name="dec",
        arity=1, param_types=[int],
        trials_passed=80,
        lhs_expr="inc(dec(x))", rhs_expr="x",
    )
    assert law.law_name() == "inc_inverse_dec"
