"""
tests/test_queue_tutorial.py - Regression & tutorial tests for stdlib/queue.ltl
Pins execution order for regular and urgent tasks in priority work queue.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_queue_priority_order():
    q_src = Path("stdlib/queue.ltl").read_text(encoding="utf-8")
    driver = """
let q = new()
q = push_back(q, "job-1")
q = push_back(q, "job-2")
q = push_front(q, "urgent-1")
q = push_back(q, "job-3")

let step1 = pop_front(q)
let j1 = step1[0]
q = step1[1]

let step2 = pop_front(q)
let j2 = step2[0]
q = step2[1]

let step3 = pop_front(q)
let j3 = step3[0]
q = step3[1]

let step4 = pop_front(q)
let j4 = step4[0]
q = step4[1]

let final_empty = is_empty(q)
"""
    c = Compiler()
    res = c.compile_source(q_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["j1"] == "urgent-1"
    assert ns["j2"] == "job-1"
    assert ns["j3"] == "job-2"
    assert ns["j4"] == "job-3"
    assert ns["final_empty"] is True

def test_queue_empty_pop_and_drain():
    q_src = Path("stdlib/queue.ltl").read_text(encoding="utf-8")
    driver = """
let q = new()
let empty_pop = pop_front(q)
let empty_val = empty_pop[0]
let empty_rem = empty_pop[1]

q = push_back(q, "a")
q = push_back(q, "b")
q = push_back(q, "c")
let drained_res = drain(q, 2)
let batch = drained_res[0]
let remaining = drained_res[1]
"""
    c = Compiler()
    res = c.compile_source(q_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    assert ns["empty_val"] is None
    assert ns["batch"] == ["a", "b"]
    assert ns["remaining"] == ["c"]
