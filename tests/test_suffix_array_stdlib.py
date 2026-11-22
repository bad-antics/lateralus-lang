"""
Regression tests for stdlib/suffix_array.ltl.

char_at() is not a runtime builtin (sa_char_codes/build/lcp raised
NameError) and (lo+hi)/2 produced a float index in search().
Now uses ord(slice(...)) and idiv().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "suffix_array.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_build_matches_reference():
    ns = _load()
    for text in ["mississippi", "banana", "aaaa", "abc"]:
        sa = ns["build"](text)
        assert sa == sorted(range(len(text)), key=lambda i: text[i:]), text
        assert ns["build"]("") == []


def test_lcp_and_search():
    ns = _load()
    text = "mississippi"
    sa = ns["build"](text)
    lcp = ns["lcp"](text, sa)
    # Kasai invariant: lcp[i] = lcp(suffix sa[i-1], suffix sa[i])
    for i in range(1, len(sa)):
        a, b = text[sa[i - 1]:], text[sa[i]:]
        k = 0
        while k < min(len(a), len(b)) and a[k] == b[k]:
            k += 1
        assert lcp[i] == k, (i, lcp[i], k)
    for pat in ["issi", "pi", "xyz"]:
        pos = ns["search"](text, sa, pat)
        if pat in text:
            assert text.startswith(pat, pos), (pat, pos)
        else:
            assert pos == -1


def test_longest_repeated():
    ns = _load()
    assert ns["longest_repeated"]("banana") == "ana"
    assert ns["longest_repeated"]("mississippi") == "issi"
    assert ns["longest_repeated"]("abc") == ""
