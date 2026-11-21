"""
tests/test_ringbuf_tutorial.py - Comprehensive tests for stdlib/ringbuf.ltl
Verifies circular buffer creation, overwrite semantics, FIFO popping, peeking,
indexed access, drainage, and conversion to list.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_ringbuf_basic_fifo_and_peeking():
    rb_src = Path("stdlib/ringbuf.ltl").read_text(encoding="utf-8")
    driver = """
let b0 = new(4)
let empty_check = is_empty(b0)
let cap0 = capacity(b0)

let b1 = push(b0, 10)
let b2 = push(b1, 20)
let b3 = push(b2, 30)

let cnt3 = count(b3)
let full_check = is_full(b3)
let front3 = peek_front(b3)
let back3 = peek_back(b3)
let list3 = to_list(b3)

// Pop oldest (10)
let p1 = pop(b3)
let popped_val = p1[0]
let b_popped = p1[1]
let cnt_after = count(b_popped)
let list_after = to_list(b_popped)
"""
    c = Compiler()
    res = c.compile_source(rb_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["empty_check"] is True
    assert ns["cap0"] == 4
    assert ns["cnt3"] == 3
    assert ns["full_check"] is False
    assert ns["front3"] == 10
    assert ns["back3"] == 30
    assert ns["list3"] == [10, 20, 30]

    assert ns["popped_val"] == 10
    assert ns["cnt_after"] == 2
    assert ns["list_after"] == [20, 30]

def test_ringbuf_wrap_around_and_overwriting():
    rb_src = Path("stdlib/ringbuf.ltl").read_text(encoding="utf-8")
    driver = """
// Buffer with capacity 3
let b = new(3)
b = push(b, "A")
b = push(b, "B")
b = push(b, "C")
let is_f = is_full(b)

// Push 4th item: should overwrite "A"
b = push(b, "D")
let list_overwritten = to_list(b)
let front_ovr = peek_front(b)
let back_ovr = peek_back(b)

// Push 5th item: should overwrite "B"
b = push(b, "E")
let list_ovr2 = to_list(b)

// Logical indexing with at()
let item0 = at(b, 0) // oldest ("C")
let item1 = at(b, 1) // ("D")
let item2 = at(b, 2) // newest ("E")
let item_oob = at(b, 99)

// Drain & Clear
let drained = drain(b)
let b_cleared = clear(b)
let is_empty_cleared = is_empty(b_cleared)
"""
    c = Compiler()
    res = c.compile_source(rb_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["is_f"] is True
    assert ns["list_overwritten"] == ["B", "C", "D"]
    assert ns["front_ovr"] == "B"
    assert ns["back_ovr"] == "D"

    assert ns["list_ovr2"] == ["C", "D", "E"]
    assert ns["item0"] == "C"
    assert ns["item1"] == "D"
    assert ns["item2"] == "E"
    assert ns["item_oob"] is None

    assert ns["drained"] == ["C", "D", "E"]
    assert ns["is_empty_cleared"] is True
