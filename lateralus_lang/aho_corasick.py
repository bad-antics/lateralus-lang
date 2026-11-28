"""
LATERALUS Standard Library — aho_corasick
Python implementation of stdlib/aho_corasick.ltl

Bit-for-bit mirror of the Lateralus Aho-Corasick multi-pattern matcher
(Spiral Wave 10). Used as the runtime backing for `import aho_corasick`
in transpiled Lateralus code (see codegen/python.py alias map).

Node representation: parallel lists indexed by node id.
  goto_map[id] = dict { byte_int -> child_id }
  fail[id]     = int fallback node
  output[id]   = list of pattern-ids that end here
Automaton is a dict of those three lists + patterns.
"""
from __future__ import annotations


def _ac_new_node(auto: dict) -> None:
    auto["goto"] = auto["goto"] + [{}]
    auto["fail"] = auto["fail"] + [0]
    auto["output"] = auto["output"] + [[]]


def build(patterns) -> dict:
    auto: dict = {"goto": [], "fail": [], "output": [], "patterns": list(patterns)}
    _ac_new_node(auto)  # root = 0

    # -- build goto/output trie ------------------------------------
    for pi, p in enumerate(patterns):
        node = 0
        for j in range(len(p)):
            c = ord(p[j])
            children = auto["goto"][node]
            if c in children:
                node = children[c]
            else:
                _ac_new_node(auto)
                new_id = len(auto["goto"]) - 1
                auto["goto"][node][c] = new_id
                node = new_id
        auto["output"][node] = auto["output"][node] + [pi]

    # -- BFS compute fail pointers ---------------------------------
    queue: list = []
    root_keys = list(auto["goto"][0].keys())
    for kk in root_keys:
        child = auto["goto"][0][kk]
        auto["fail"][child] = 0
        queue = queue + [child]

    while len(queue) > 0:
        u = queue[0]
        queue = queue[1:]
        kids = auto["goto"][u]
        for c in list(kids.keys()):
            v = kids[c]
            queue = queue + [v]
            # walk fail chain from u to find longest proper suffix
            f = auto["fail"][u]
            while f > 0 and c not in auto["goto"][f]:
                f = auto["fail"][f]
            fallback = 0
            if c in auto["goto"][f] and auto["goto"][f][c] != v:
                fallback = auto["goto"][f][c]
            auto["fail"][v] = fallback
            # merge output of fallback into v
            auto["output"][v] = auto["output"][v] + auto["output"][fallback]
    return auto


def find_all(auto: dict, text: str) -> list:
    """Return [[pattern_id, end_position_exclusive], ...]."""
    hits: list = []
    node = 0
    for i in range(len(text)):
        c = ord(text[i])
        while node > 0 and c not in auto["goto"][node]:
            node = auto["fail"][node]
        if c in auto["goto"][node]:
            node = auto["goto"][node][c]
        for pid in auto["output"][node]:
            hits = hits + [[pid, i + 1]]
    return hits


def find_all_starts(auto: dict, text: str) -> list:
    """Return [(pattern_id, start_position)] pairs."""
    raw = find_all(auto, text)
    pats = auto["patterns"]
    out: list = []
    for pid, end in raw:
        out = out + [[pid, end - len(pats[pid])]]
    return out


def contains_any(auto: dict, text: str) -> bool:
    """True if any pattern occurs in text."""
    node = 0
    for i in range(len(text)):
        c = ord(text[i])
        while node > 0 and c not in auto["goto"][node]:
            node = auto["fail"][node]
        if c in auto["goto"][node]:
            node = auto["goto"][node][c]
        if len(auto["output"][node]) > 0:
            return True
    return False
