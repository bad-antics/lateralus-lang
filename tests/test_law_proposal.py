"""Tests for witness-based law proposal (6th verification pillar)."""
from __future__ import annotations

from lateralus_lang.law_mutator import (
    _build_line_to_fn_map,
    _py_to_ltl_literal,
    generate_mutants,
    mutation_test_file,
    synthesize_proposals,
)

# ─── Utilities ────────────────────────────────────────────────────────────

def test_literal_rendering():
    assert _py_to_ltl_literal(True) == "true"
    assert _py_to_ltl_literal(False) == "false"
    assert _py_to_ltl_literal(42) == "42"
    assert _py_to_ltl_literal(-3) == "-3"
    assert _py_to_ltl_literal(3.5) == "3.5"
    assert _py_to_ltl_literal("hi") == '"hi"'
    assert _py_to_ltl_literal('a"b') == '"a\\"b"'


def test_line_to_fn_map():
    source = (
        "def alpha(x):\n"
        "    y = x + 1\n"
        "    return y\n"
        "\n"
        "def beta(x):\n"
        "    return x * 2\n"
    )
    m = _build_line_to_fn_map(source, {"alpha", "beta"})
    assert m.get(2) == "alpha"
    assert m.get(3) == "alpha"
    assert m.get(6) == "beta"


def test_line_to_fn_map_filters_user_fns():
    source = (
        "def not_user(x):\n"
        "    return x\n"
        "\n"
        "def user(x):\n"
        "    return x + 1\n"
    )
    m = _build_line_to_fn_map(source, {"user"})
    assert 2 not in m  # not_user is not in the set
    assert m.get(5) == "user"


# ─── End-to-end: weak-law source → synthesized witness ───────────────────

# A tiny Python program where `is_positive` is under-specified: the only
# law checks a positive input. Mutating `> 0` → `> 1` survives, because the
# existing law never probes the boundary.
_WEAK_SPEC_SOURCE = '''
def is_positive(x):
    return x > 0

# "Law runner tail" — assertion over one positive value only.
assert is_positive(5) == True, "law_only_positive violated"
print("all laws pass")
'''


def test_synthesis_finds_witness_for_boundary_mutation():
    """`x > 0` mutated to `x > 1` survives a one-sided law — synthesis
    must propose a witness at x=1 (or x=0) that discriminates the two."""
    mutants = generate_mutants(_WEAK_SPEC_SOURCE, user_fns={"is_positive"})
    # Pick the `>  →  <` or boundary-shifting mutant we expect to survive
    gt_muts = [m for m in mutants if "> 0" in _WEAK_SPEC_SOURCE.splitlines()[m.line_no - 1] or True]
    assert any(m.containing_fn == "is_positive" for m in mutants), \
        "containing_fn should be populated"

    # Find a concrete surviving mutant: one that still lets the sole
    # assertion (is_positive(5)) pass. `> 1` does; `< 0` does not.
    survivors = []
    for mut in mutants:
        if mut.containing_fn != "is_positive":
            continue
        from lateralus_lang.law_mutator import _run_python, apply_mutant
        mutated = apply_mutant(_WEAK_SPEC_SOURCE, mut, user_fns={"is_positive"})
        if mutated == _WEAK_SPEC_SOURCE:
            continue
        code, _ = _run_python(mutated, timeout=5.0)
        if code == 0:
            survivors.append(mut)

    assert survivors, "expected at least one mutation to survive the weak law"

    proposals = synthesize_proposals(
        _WEAK_SPEC_SOURCE, survivors, {"is_positive"}, trials=200, seed=7,
    )
    assert proposals, "synthesis should produce at least one proposal"

    p = proposals[0]
    assert p.fn_name == "is_positive"
    assert isinstance(p.witness_args, tuple)
    assert len(p.witness_args) == 1
    assert "@law" in p.ltl_source
    assert "is_positive(" in p.ltl_source
    assert "return" in p.ltl_source
    # Witness must produce the claimed `expected` when fed to the original
    assert (p.witness_args[0] > 0) == p.expected


def test_proposed_law_text_is_parseable_ltl():
    """The emitted `@law` snippet must be syntactically valid Lateralus."""
    mutants = generate_mutants(_WEAK_SPEC_SOURCE, user_fns={"is_positive"})
    from lateralus_lang.law_mutator import _run_python, apply_mutant
    survivors = []
    for mut in mutants:
        if mut.containing_fn != "is_positive":
            continue
        mutated = apply_mutant(_WEAK_SPEC_SOURCE, mut, user_fns={"is_positive"})
        if mutated == _WEAK_SPEC_SOURCE:
            continue
        code, _ = _run_python(mutated, timeout=5.0)
        if code == 0:
            survivors.append(mut)
    proposals = synthesize_proposals(
        _WEAK_SPEC_SOURCE, survivors, {"is_positive"}, trials=200, seed=7,
    )
    assert proposals

    # Wrap the proposal in a tiny module and parse it via the real compiler
    from lateralus_lang.compiler import Compiler, Target
    source = (
        "fn is_positive(x: int) -> bool {\n"
        "    return x > 0\n"
        "}\n\n"
        + proposals[0].ltl_source + "\n"
    )
    result = Compiler().compile_source(source, target=Target.PYTHON, filename="t.ltl")
    assert result.ok, f"proposed law did not parse: {[e.message for e in result.errors]}"


def test_mutation_test_file_propose_e2e(tmp_path):
    """CLI-facing entry point wires --propose all the way through to output."""
    ltl_src = (
        "fn is_positive(x: int) -> bool {\n"
        "    return x > 0\n"
        "}\n\n"
        "@law\n"
        "fn is_positive_on_five() -> bool {\n"
        "    return is_positive(5) == true\n"
        "}\n"
    )
    ltl_file = tmp_path / "weak.ltl"
    ltl_file.write_text(ltl_src)
    out_file = tmp_path / "proposals.ltl"

    # Capture stdout
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mutation_test_file(
            ltl_file, trials=50, seed=7, propose=True,
            propose_output=out_file, verbose=False,
        )
    output = buf.getvalue()

    # The weak law permits a surviving mutant → rc should be 1
    assert rc == 1
    assert "Proposed laws" in output
    assert out_file.exists()
    content = out_file.read_text()
    assert "@law" in content
    assert "is_positive(" in content


def test_proposals_empty_when_no_survivors(tmp_path):
    """Strong-law file → no survivors → no proposals, rc==0."""
    ltl_src = (
        "fn double(x: int) -> int {\n"
        "    return x * 2\n"
        "}\n\n"
        "@law\n"
        "fn double_doubles(x: int) -> bool {\n"
        "    return double(x) == x + x\n"
        "}\n"
    )
    f = tmp_path / "strong.ltl"
    f.write_text(ltl_src)

    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mutation_test_file(f, trials=50, seed=7, propose=True, verbose=False)
    assert rc == 0
    assert "Proposed laws" not in buf.getvalue()
