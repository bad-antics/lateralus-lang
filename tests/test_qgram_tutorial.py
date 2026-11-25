"""
tests/test_qgram_tutorial.py - Tests for stdlib/qgram.ltl
Verifies q-gram tokenization, overlap counts, Jaccard similarity, and inverted index search.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_qgram_tokenization_and_jaccard():
    qgram_src = Path("stdlib/qgram.ltl").read_text(encoding="utf-8")
    driver = """
let g = qgrams("cat", 2)
let o = overlap("cat", "hat", 2)
let sim_identical = jaccard("hello", "hello", 2)
let sim_typo = jaccard("algorithm", "algoritm", 2)
let sim_unrelated = jaccard("cat", "dog", 2)
"""
    c = Compiler()
    res = c.compile_source(qgram_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert len(ns["g"]) == 4  # "\x01c", "ca", "at", "t\x01"
    assert ns["o"] == 2       # "at", "t\x01"
    assert ns["sim_identical"] == 1.0
    assert 0.70 < ns["sim_typo"] < 0.75
    assert ns["sim_unrelated"] == 0.0

def test_qgram_inverted_index_query():
    qgram_src = Path("stdlib/qgram.ltl").read_text(encoding="utf-8")
    driver = """
let corpus = [
    "lateralus core language",
    "python asyncio loop",
    "ladder logic plc system"
]
let idx = build_index(corpus, 2)
let results = query(idx, "lateralus", 2)
let top_doc = results[0][0]
let top_score = results[0][1]
"""
    c = Compiler()
    res = c.compile_source(qgram_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["top_doc"] == 0
    assert ns["top_score"] == 9
