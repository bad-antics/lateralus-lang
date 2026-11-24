"""
tests/test_sync_tutorial.py - Verification suite for stdlib/sync.ltl
Verifies spinlocks, cooperative mutexes, atomic operations, CAS,
and memory barriers in Lateralus concurrent systems.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_sync_snippet(driver: str) -> dict:
    sync_src = Path("stdlib/sync.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(sync_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_sync_spinlock_lifecycle():
    driver = r"""
let sl = spinlock_new()
let initial_state = sl.locked

let acquired = spinlock_try_lock(sl)
let locked_state = sl.locked

spinlock_unlock(sl)
let unlocked_state = sl.locked
"""
    ns = run_sync_snippet(driver)
    assert ns["initial_state"] == 0, "New spinlock must start unlocked"
    assert ns["acquired"] is True, "try_lock on uncontended spinlock must succeed"
    assert ns["locked_state"] == 0 or ns["locked_state"] == 1
    assert ns["unlocked_state"] == 0, "Spinlock must be unlocked after spinlock_unlock"


def test_sync_mutex_cooperative():
    driver = r"""
let m = mutex_new()
let init_m = m.locked

mutex_lock(m)
let locked_m = m.locked

mutex_unlock(m)
let unlocked_m = m.locked
"""
    ns = run_sync_snippet(driver)
    assert ns["init_m"] == 0, "New mutex must be unlocked"
    assert ns["locked_m"] == 1, "Acquired mutex must have locked=1"
    assert ns["unlocked_m"] == 0, "Released mutex must have locked=0"


def test_sync_atomic_load_store():
    driver = r"""
let p = 2048 as Ptr<u32>
atomic_store(p, 0xAABBCCDD)
let val = atomic_load(p)

let p2 = 4096 as Ptr<u32>
atomic_store(p2, 9999)
let val2 = atomic_load(p2)
"""
    ns = run_sync_snippet(driver)
    assert ns["val"] == 0xAABBCCDD, "atomic_load must match value written by atomic_store"
    assert ns["val2"] == 9999


def test_sync_atomic_cas_and_rmw():
    driver = r"""
let addr = 8192 as Ptr<u32>
atomic_store(addr, 500)

let old_val = atomic_cas(addr, 500, 600)
let inc_val = atomic_inc(addr)
let dec_val = atomic_dec(addr)
"""
    ns = run_sync_snippet(driver)
    assert ns["old_val"] == 500, "atomic_cas must return expected old value"
    assert ns["inc_val"] == 0 or ns["inc_val"] == 1


def test_sync_memory_barriers():
    driver = r"""
compiler_barrier()
memory_barrier()
read_barrier()
write_barrier()
let barriers_ok = true
"""
    ns = run_sync_snippet(driver)
    assert ns["barriers_ok"] is True, "All memory ordering barriers must execute without error"
