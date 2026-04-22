"""Tests for --apply insertion + harden self-closure loop (7th pillar)."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

from lateralus_lang.law_mutator import (
    _APPLY_BANNER_END,
    _APPLY_BANNER_START,
    ProposedLaw,
    apply_proposals_to_source,
    harden_file,
    mutation_test_file,
)

_WEAK_LTL = """\
fn is_positive(x: int) -> bool {
    return x > 0
}

@law
fn is_positive_on_five() -> bool {
    return is_positive(5) == true
}
"""


# ─── apply_proposals_to_source ───────────────────────────────────────────

def test_apply_inserts_banner_and_proposal(tmp_path: Path):
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)
    props = [
        ProposedLaw(
            fn_name="is_positive",
            witness_args=(1,),
            expected=True,
            mutant_yields=False,
            ltl_source=(
                "@law\n"
                "fn is_positive_witness_00001() -> bool {\n"
                "    return is_positive(1) == true\n"
                "}"
            ),
        )
    ]
    added, already = apply_proposals_to_source(f, props)
    assert added == 1
    assert already == 0

    out = f.read_text()
    assert _APPLY_BANNER_START in out
    assert _APPLY_BANNER_END in out
    assert "is_positive_witness_00001" in out


def test_apply_is_idempotent(tmp_path: Path):
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)
    props = [
        ProposedLaw(
            fn_name="is_positive",
            witness_args=(1,),
            expected=True,
            mutant_yields=False,
            ltl_source=(
                "@law\n"
                "fn is_positive_witness_00001() -> bool {\n"
                "    return is_positive(1) == true\n"
                "}"
            ),
        )
    ]
    apply_proposals_to_source(f, props)
    first = f.read_text()

    # Re-apply the same proposal
    added, already = apply_proposals_to_source(f, props)
    assert added == 0
    assert already == 1
    assert f.read_text() == first  # byte-for-byte unchanged


def test_apply_merges_multiple_iterations(tmp_path: Path):
    """Different proposals across iterations must all end up in one block."""
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)
    p1 = ProposedLaw("is_positive", (1,), True, False,
                     "@law\nfn is_positive_witness_00001() -> bool {\n"
                     "    return is_positive(1) == true\n}")
    p2 = ProposedLaw("is_positive", (0,), False, True,
                     "@law\nfn is_positive_witness_00002() -> bool {\n"
                     "    return is_positive(0) == false\n}")
    apply_proposals_to_source(f, [p1])
    apply_proposals_to_source(f, [p2])

    out = f.read_text()
    assert out.count(_APPLY_BANNER_START) == 1
    assert out.count(_APPLY_BANNER_END) == 1
    assert "is_positive_witness_00001" in out
    assert "is_positive_witness_00002" in out


def test_apply_empty_is_noop(tmp_path: Path):
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)
    before = f.read_text()
    added, already = apply_proposals_to_source(f, [])
    assert added == 0 and already == 0
    assert f.read_text() == before


# ─── verify --mutate --propose --apply e2e ───────────────────────────────

def test_verify_with_apply_actually_improves_score(tmp_path: Path):
    """After --apply, rerunning --mutate should catch at least one more
    mutant (strictly higher score or fewer survivors)."""
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc1 = mutation_test_file(
            f, trials=50, seed=7, propose=True, apply=True, verbose=False,
        )
    out1 = buf.getvalue()
    assert "inserted" in out1

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mutation_test_file(
            f, trials=50, seed=7, propose=True, apply=False, verbose=False,
        )
    out2 = buf.getvalue()

    # Second pass should catch the witness-targeted mutant
    def survivors(text: str) -> int:
        import re
        m = re.search(r"Survivors:\s+(\d+)", text)
        return int(m.group(1)) if m else 0

    assert survivors(out2) < survivors(out1), \
        f"expected fewer survivors after --apply, got {survivors(out1)}→{survivors(out2)}"


# ─── harden subcommand ───────────────────────────────────────────────────

def test_harden_converges_on_equivalent_mutations(tmp_path: Path):
    """On a file with equivalent mutations, harden must not loop forever —
    it must detect a fixpoint when no new witnesses appear."""
    f = tmp_path / "weak.ltl"
    f.write_text(_WEAK_LTL)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = harden_file(f, trials=50, seed=7, max_iter=6, verbose=False)
    out = buf.getvalue()

    assert "iter 1:" in out
    # Either reached target or hit fixpoint / max_iter — no hang
    assert ("Final score:" in out)
    # Must have made at least one insertion
    inserted = f.read_text()
    assert _APPLY_BANNER_START in inserted


def test_harden_stops_at_target_score(tmp_path: Path):
    """A strong-law file starts at 100% and harden returns 0 immediately."""
    strong = (
        "fn double(x: int) -> int {\n"
        "    return x * 2\n"
        "}\n\n"
        "@law\n"
        "fn double_doubles(x: int) -> bool {\n"
        "    return double(x) == x + x\n"
        "}\n"
    )
    f = tmp_path / "strong.ltl"
    f.write_text(strong)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = harden_file(f, trials=40, seed=7, max_iter=3)
    out = buf.getvalue()
    assert rc == 0
    assert "reached target" in out
    # And source must be unchanged (no banner inserted)
    assert _APPLY_BANNER_START not in f.read_text()
