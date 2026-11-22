"""
Regression tests for stdlib/ranking.ltl.

ascii_lower() called int(c), which raises ValueError for any
non-numeric character — tokenize() crashed on ordinary text before the
A-Z fallback table was ever reached.  The dead conversion is removed.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOCS = ["the cat sat on the mat", "a dog barks", "cat and dog"]


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "ranking.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_tokenize_lowercases_and_strips_punct():
    ns = _load()
    assert ns["tokenize"]("The Quick brown FOX!") == [
        "the", "quick", "brown", "fox",
    ]


def test_build_index_and_bm25_rank():
    ns = _load()
    idx = ns["build_index"](DOCS)
    ranked = ns["rank_bm25"](idx, "cat")
    # doc 2 ("cat and dog") and doc 0 ("the cat sat...") both contain cat;
    # doc 1 does not and must score lowest
    assert ranked[-1][0] == 1
    assert ranked[-1][1] == 0.0
    top_two = {r[0] for r in ranked[:2]}
    assert top_two == {0, 2}
    # scores sorted descending
    scores = [r[1] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_tfidf_vector():
    ns = _load()
    idx = ns["build_index"](DOCS)
    tf = ns["term_freq"](ns["tokenize"]("cat"))
    vec = ns["tfidf_vector"](tf, idx[3], idx[4])
    assert vec[0] == ["cat"]
    assert vec[1][0] > 0
