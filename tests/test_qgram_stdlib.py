"""
Regression tests for stdlib/qgram.ltl.

int_of() used the missing char_at() builtin — query() crashed with
NameError on any scored lookup.  Uses slice() instead.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "qgram.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_qgrams_padded():
    ns = _load()
    grams = ns["qgrams"]("kitten", 2)
    assert len(grams) == 7  # len(text)+1 with sentinel padding
    assert "ki" in grams and "en" in grams


def test_overlap_and_jaccard():
    ns = _load()
    assert ns["overlap"]("kitten", "sitting", 2) == 2
    assert abs(ns["jaccard"]("kitten", "sitting", 2) - 0.15384615384615385) < 1e-9


def test_build_index_and_query():
    ns = _load()
    idx = ns["build_index"](["the cat sat", "a dog barks", "cat dog"], 2)
    ranked = ns["query"](idx, "cat", 2)
    # docs 0 and 2 both contain "cat"; doc 1 does not
    doc_ids = {r[0] for r in ranked}
    assert doc_ids == {0, 2}
    scores = [r[1] for r in ranked]
    assert scores == sorted(scores, reverse=True)
