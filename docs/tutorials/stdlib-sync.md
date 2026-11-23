# Tutorial: Synchronization Primitives & Atomic Operations in Lateralus (`stdlib.sync`)

The `stdlib.sync` module provides low-level synchronization primitives, atomic memory operations, and hardware memory barriers for concurrent programming and operating system development in Lateralus. Designed to operate in freestanding bare-metal environments as well as hosted user-space execution, `stdlib.sync` ensures race-free data access across SMP (symmetric multiprocessing) cores.

This tutorial covers:
1. **Spinlocks**: Uncontended acquisition, busy-waiting loops, and non-blocking `try_lock`
2. **Cooperative Mutexes**: Task-yielding mutual exclusion for coroutine and kernel schedulers
3. **Atomic Memory Access**: Non-elided atomic loads (`atomic_load`) and stores (`atomic_store`)
4. **Read-Modify-Write (RMW) Primitives**: Atomic addition (`atomic_add`), increment/decrement, and compare-and-swap (`atomic_cas`)
5. **Hardware & Compiler Barriers**: `compiler_barrier()`, `memory_barrier()`, `read_barrier()`, and `write_barrier()`

---

## 1. Spinlocks

A `Spinlock` is a lightweight synchronization lock that busy-waits using atomic test-and-set instructions (`xchgl`) with CPU pause hints (`sys.pause()`) to minimize bus contention on multi-core systems.

```lateralus
import sync

// Initialize unlocked spinlock (locked = 0)
let lock = sync.spinlock_new()

// Non-blocking try_lock: returns true if acquired
if sync.spinlock_try_lock(lock) {
    // Critical section
    sync.spinlock_unlock(lock)
}

// Blocking acquisition: spins until lock is free
sync.spinlock_lock(lock)
// ... critical section ...
sync.spinlock_unlock(lock)
```

---

## 2. Cooperative Mutexes

Unlike busy-waiting spinlocks, a `Mutex` cooperatively yields control to the scheduler when contended, preventing CPU starvation in task-based runtimes.

```lateralus
import sync

let m = sync.mutex_new()

sync.mutex_lock(m)
assert m.locked == 1

sync.mutex_unlock(m)
assert m.locked == 0
```

---

## 3. Atomic Loads and Stores

Atomic memory operations guarantee that a 32-bit word is read or written in a single bus cycle without torn reads or stores:

```lateralus
import sync

let counter_addr = 0x2000 as Ptr<u32>

// Atomically store value
sync.atomic_store(counter_addr, 42)

// Atomically load value
let current = sync.atomic_load(counter_addr)
assert current == 42
```

---

## 4. Atomic RMW & Compare-and-Swap (CAS)

Atomic RMW primitives allow lock-free data structures like lock-free queues, reference counters, and sequence generators:

```lateralus
import sync

let seq_addr = 0x3000 as Ptr<u32>
sync.atomic_store(seq_addr, 100)

// Atomic compare-and-swap (CAS)
// If *seq_addr == 100, update to 101. Returns old value.
let old = sync.atomic_cas(seq_addr, 100, 101)
assert old == 100
```

---

## 5. Memory Ordering & Barriers

Modern out-of-order execution pipelines and hardware cache hierarchies can reorder instructions across cores. Memory barriers enforce strict memory consistency:

```lateralus
import sync

// Prevent compiler from reordering across barrier
sync.compiler_barrier()

// Full memory fence (mfence: serialize both loads and stores)
sync.memory_barrier()

// Read fence (lfence: serialize loads)
sync.read_barrier()

// Write fence (sfence: serialize stores)
sync.write_barrier()
```

---

## Synchronization Primitive Summary

| Primitive | Operation | SMP Safety | Scheduler Yield | Hardware Instruction |
|---|---|---|---|---|
| `Spinlock` | `spinlock_lock` | Yes | No (Busy-wait) | `lock xchgl` + `pause` |
| `Spinlock` | `spinlock_unlock` | Yes | No | `mfence` |
| `Spinlock` | `spinlock_try_lock` | Yes | No | `lock xchgl` |
| `Mutex` | `mutex_lock` | Cooperative | Yes | `sys.pause()` loop |
| `Atomic` | `atomic_load` | Yes | No | `volatile` load |
| `Atomic` | `atomic_store` | Yes | No | `volatile` store + `mfence` |
| `Atomic` | `atomic_cas` | Yes | No | `lock cmpxchgl` |
| `Barrier` | `memory_barrier` | Full Fence | No | `mfence` |
