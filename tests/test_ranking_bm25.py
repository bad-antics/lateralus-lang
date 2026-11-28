"""
tests/test_ranking_bm25.py — Verification of BM25 IDF precision and document ranking
Resolves Issue #808: BM25 rare term IDF understatement and result reversal in large corpora.
"""
import math
import subprocess
import sys
import tempfile
import pathlib
import pytest

from lateralus_lang import Compiler, Target


def transpile_ranking_module():
    """Transpile stdlib/ranking.ltl to Python code and import it as a module."""
    root = pathlib.Path(__file__).resolve().parent.parent
    ranking_ltl = root / "stdlib" / "ranking.ltl"

    compiler = Compiler()
    result = compiler.compile_file(str(ranking_ltl), Target.PYTHON)
    assert result.ok, f"Compilation failed: {result.errors}"
    py_code = result.python_src
    
    # Execute into a namespace
    ns = {}
    exec(py_code, ns)
    return ns


@pytest.fixture(scope="module")
def ranking():
    return transpile_ranking_module()


def test_idf_bm25_high_precision_large_n(ranking):
    """Verify idf_bm25 at N=1000, df=1 matches theoretical ln(1001/1.5).
    Previously, unreduced series truncated at 4.37805.
    With range-reduction, accuracy matches math.log within floating point limits.
    """
    idf_fn = ranking["idf_bm25"]
    calc = idf_fn(1, 1000)
    expected = math.log(1001.0 / 1.5)
    assert calc == pytest.approx(expected, rel=1e-7)
    assert abs(calc - 6.503289671207057) < 1e-6


def test_bm25_rare_term_ranks_above_common_term(ranking):
    """Issue #808 reproduction corpus:
    A 1,000-document corpus where doc0 has ['rare', 'filler'] and doc1 has ['common', 'common'].
    Query is ['rare', 'common'].
    With accurate IDF, doc0 must score ~6.503 and doc1 ~5.954, ensuring doc0 ranks first.
    """
    term_freq = ranking["term_freq"]
    bm25_score = ranking["bm25_score"]

    docs = [["rare", "filler"], ["common", "common"]]
    docs += [["common", "filler"] for _ in range(14)]
    docs += [["filler", "filler"] for _ in range(984)]

    query = ["rare", "common"]
    df = [sum(term in doc for doc in docs) for term in query]

    corpus = [
        [term_freq(doc) for doc in docs],
        [len(doc) for doc in docs],
        2.0,  # avgdl
        [query, df],
        len(docs),
    ]

    score_rare = bm25_score(corpus, 0, query)
    score_common = bm25_score(corpus, 1, query)

    # Expected: score_rare (~6.503) > score_common (~5.954)
    assert score_rare == pytest.approx(6.503289671207057, rel=1e-5)
    assert score_common == pytest.approx(5.954163936271456, rel=1e-5)
    assert score_rare > score_common


def test_idf_monotonicity_with_df(ranking):
    """IDF must strictly decrease as document frequency increases."""
    idf_fn = ranking["idf_bm25"]
    n = 500
    prev_idf = float("inf")
    for df in [1, 2, 5, 10, 50, 100, 250]:
        curr_idf = idf_fn(df, n)
        assert curr_idf < prev_idf
        prev_idf = curr_idf
