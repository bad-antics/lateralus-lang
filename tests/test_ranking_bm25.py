"""
tests/test_ranking_bm25.py — Regression tests for stdlib/ranking.ltl

Guards issue #808: the BM25 IDF used a fixed 12-term atanh logarithm series
that converged far too slowly for large arguments.  At N=1000, df=1 the
series returned ~4.378 instead of the true ln(1001/1.5) = 6.503289671207057,
which underweighted rare terms and could reverse ranking order.

The fix adds octave-style range reduction (factor x = m * 2**e with m in
[1, 2)) plus an e*ln(2) correction so the fast-converging series is only ever
evaluated on a well-behaved argument.  These tests compile the .ltl module,
import the generated Python, and assert the IDF value and ranking order.
"""
from __future__ import annotations

import importlib.util
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RANKING_LTL = REPO_ROOT / "stdlib" / "ranking.ltl"
LTLC = REPO_ROOT / "bin" / "ltlc"


def _compile_ranking(tmp_path: Path):
    """Compile stdlib/ranking.ltl to Python and import the resulting module."""
    assert RANKING_LTL.exists(), f"missing {RANKING_LTL}"
    out = tmp_path / "ranking_check.py"
    result = subprocess.run(
        [sys.executable, str(LTLC), "py", str(RANKING_LTL), "-o", str(out)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, f"compile failed: {result.stderr[:800]}"
    assert out.exists(), "compiler did not emit output file"

    spec = importlib.util.spec_from_file_location("ranking_check", str(out))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_idf_rare_term_value(tmp_path):
    """idf_bm25(1, 1000) must match ln((N - df + 0.5)/(df + 0.5) + 1)."""
    m = _compile_ranking(tmp_path)
    got = m.idf_bm25(1, 1000)
    expected = math.log(1001 / 1.5)  # 6.503289671207057
    assert abs(got - expected) < 1e-6, f"idf_bm25(1,1000)={got} expected={expected}"


def test_idf_matches_reference_across_range(tmp_path):
    """IDF should track the closed-form across a range of (df, N)."""
    m = _compile_ranking(tmp_path)
    for df, n in [(1, 1000), (1, 10), (5, 100), (50, 1000), (1, 2), (999, 1000)]:
        got = m.idf_bm25(df, n)
        expected = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
        assert abs(got - expected) < 1e-6, (
            f"idf_bm25({df},{n})={got} expected={expected}"
        )


def test_rare_term_ranks_first(tmp_path):
    """A rare term (df=1) must outrank a common term (df=N) in a 1000-doc corpus."""
    m = _compile_ranking(tmp_path)
    n = 1000
    idf_rare = m.idf_bm25(1, n)
    idf_common = m.idf_bm25(n, n)
    # Rare term should carry essentially the full ln(1001/1.5) weight while the
    # ubiquitous term is near zero; the rare document must therefore rank first.
    assert idf_rare > idf_common
    assert abs(idf_rare - math.log(1001 / 1.5)) < 1e-6
    # Construct BM25 term scores directly (tokenize() has an unrelated int()
    # limitation, so exercise the scoring path via term_freq tables).
    # doc0: rare term once; doc1: common term once. Same length => same norm.
    docs_tf = []
    for term in ("rareterm", "commont"):
        tf = m.term_freq([term])
        docs_tf.append(tf)
    doc_lens = [1, 1]
    avgdl = 1.0
    df = [["rareterm", "commont"], [1, n]]
    idx = [docs_tf, doc_lens, avgdl, df, n]
    score_rare = m.bm25_term_score(idx, 0, "rareterm", 1.5, 0.75)
    score_common = m.bm25_term_score(idx, 1, "commont", 1.5, 0.75)
    assert score_rare > score_common, (
        f"rare score {score_rare} should exceed common {score_common}"
    )
    assert abs(score_rare - idf_rare) < 1e-6  # tf=1, dl==avgdl => factor 1