"""
tests/test_deque_tutorial.py - Comprehensive tests for stdlib/deque.ltl
Verifies double-ended queue operations: bidirectional push/pop/peek, size queries,
cyclic rotation (left/right), reversals, extensions, and list conversions.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_deque_bidirectional_push_pop_and_peek():
    dq_src = Path("stdlib/deque.ltl").read_text(encoding="utf-8")
    driver = """
let d = new()
let empty_check = is_empty(d)

d = push_back(d, 20)
d = push_front(d, 10)
d = push_back(d, 30)

let sz = size(d)
let f_val = front(d)
let b_val = back(d)
let as_list = to_list(d)

// Pop front (10)
let p_f = pop_front(d)
let val_front = p_f[0]
let d_after_f = p_f[1]

// Pop back (30)
let p_b = pop_back(d_after_f)
let val_back = p_b[0]
let d_remaining = p_b[1]
let rem_list = to_list(d_remaining)
"""
    c = Compiler()
    res = c.compile_source(dq_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["empty_check"] is True
    assert ns["sz"] == 3
    assert ns["f_val"] == 10
    assert ns["b_val"] == 30
    assert ns["as_list"] == [10, 20, 30]

    assert ns["val_front"] == 10
    assert ns["val_back"] == 30
    assert ns["rem_list"] == [20]

def test_deque_rotation_and_transformations():
    dq_src = Path("stdlib/deque.ltl").read_text(encoding="utf-8")
    driver = """
let d = from_list([1, 2, 3, 4, 5])

let rot_l = rotate_left(d, 2)
let rot_r = rotate_right(d, 2)
let rev = reverse(d)

let has_3 = contains(d, 3)
let has_99 = contains(d, 99)
let elem_2 = at(d, 2)
let elem_oob = at(d, 10)

let ext = extend(d, [6, 7])
let ext_f = extend_front(d, [0])
let filtered = remove_all(from_list([1, 2, 3, 2, 4]), 2)
let cleared = clear(d)
"""
    c = Compiler()
    res = c.compile_source(dq_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["rot_l"] == [3, 4, 5, 1, 2]
    assert ns["rot_r"] == [4, 5, 1, 2, 3]
    assert ns["rev"] == [5, 4, 3, 2, 1]

    assert ns["has_3"] is True
    assert ns["has_99"] is False
    assert ns["elem_2"] == 3
    assert ns["elem_oob"] is None

    assert ns["ext"] == [1, 2, 3, 4, 5, 6, 7]
    assert ns["ext_f"] == [0, 1, 2, 3, 4, 5]
    assert ns["filtered"] == [1, 3, 4]
    assert ns["cleared"] == []
