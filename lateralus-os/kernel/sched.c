/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Preemptive Round-Robin Scheduler
 * ═══════════════════════════════════════════════════════════════════════
 * Kernel-mode context switching via software stack-swap.  Each task gets
 * a 16 KB kernel stack.  The PIT fires at 1 kHz; sched_tick() counts
 * down the running task's timeslice and triggers a switch when expired.
 *
 * Context switch is *cooperative*-style (callee-saved registers only)
 * because we switch from a known call site (sched_switch), not from
 * arbitrary interrupt frames.  This avoids needing full ISR-frame save
 * which would require naked-asm trampolines.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "sched.h"

/* ── External symbols ─────────────────────────────────────────────────── */

extern void  serial_puts(const char *s);
extern void *kmalloc(uint64_t size);
extern void  kfree(void *ptr);
extern volatile uint64_t tick_count;

/* ── Task pool ────────────────────────────────────────────────────────── */

static SchedTask tasks[SCHED_MAX_TASKS];
static int       current_tid  = -1;  /* currently running task */
static int       sched_ready  = 0;   /* set after sched_init() */
static uint64_t  total_switches = 0;

/* Load average state (forward declaration — implementation at end of file) */
static int load_avg_1  = 0;   /* ×100 fixed-point */
static int load_avg_5  = 0;
static int load_avg_15 = 0;
static uint64_t load_last_sample_tick = 0;

/* ── Helpers ──────────────────────────────────────────────────────────── */

static void _scpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static void _sitoa(uint64_t val, char *buf) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    int pos = 0;
    while (rp > 0) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

static void _scat(char *dst, const char *src) {
    int n = 0; while (dst[n]) n++;
    int i = 0; while (src[i]) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static int _slen(const char *s) {
    int n = 0; while (s[n]) n++;
    return n;
}

/* ── Context switch (inline asm) ──────────────────────────────────────── */
/*
 * Save callee-saved registers + RFLAGS + return address on current stack,
 * store RSP, load new RSP, pop saved state, ret to new task's RIP.
 *
 * void _context_switch(uint64_t *old_rsp, uint64_t new_rsp);
 *   old_rsp: pointer to where to save current RSP
 *   new_rsp: RSP value to switch to
 */
static inline void _context_switch(uint64_t *old_rsp, uint64_t new_rsp) {
    __asm__ volatile (
        /* Save callee-saved regs + flags */
        "pushfq\n\t"
        "pushq %%rbp\n\t"
        "pushq %%rbx\n\t"
        "pushq %%r12\n\t"
        "pushq %%r13\n\t"
        "pushq %%r14\n\t"
        "pushq %%r15\n\t"

        /* Save current RSP */
        "movq %%rsp, (%0)\n\t"

        /* Load new RSP */
        "movq %1, %%rsp\n\t"

        /* Restore callee-saved regs + flags */
        "popq %%r15\n\t"
        "popq %%r14\n\t"
        "popq %%r13\n\t"
        "popq %%r12\n\t"
        "popq %%rbx\n\t"
        "popq %%rbp\n\t"
        "popfq\n\t"
        :
        : "r"(old_rsp), "r"(new_rsp)
        : "memory", "cc"
    );
}

/* ── Task entry wrapper ───────────────────────────────────────────────── */
/*
 * When a new task is first scheduled, execution lands here.
 * The entry function and argument were placed on the initial stack.
 */
static void _task_entry_trampoline(void) {
    /* On the initial stack frame:
       [rsp+0] = arg (popped into r15 by context restore)
       [rsp+?] = entry function pointer
       These are set up by sched_create when building the initial stack.
       After the context restore pops, the 'ret' lands here.
       We retrieve entry+arg from the task's saved context. */

    int tid = current_tid;
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return;

    SchedTask *t = &tasks[tid];
    /* The entry and arg were packed into unused context slots by sched_create:
       r15 = (uint64_t)arg, r14 = (uint64_t)entry */
    /* We can't read them directly since context restore already happened.
       Instead sched_create stores them in a mini-header below the context. */

    /* Actually: we set up the stack so that after context_switch pops
       r15..rbp+flags, the 'ret' instruction returns to _task_bootstrap
       which reads r14=entry, r15=arg from the popped registers. */
    (void)t;
}

/* This is the actual entry point for new tasks.
   r14 = entry function, r15 = arg (set in initial context) */
static void _task_bootstrap(void) {
    int tid = current_tid;
    (void)tid;  /* used for debugging */

    /* Read entry + arg from where sched_create stored them in the
       initial context frame — they're now in r14 and r15 after pop */
    TaskEntry entry;
    void *arg;
    __asm__ volatile ("movq %%r14, %0" : "=r"(entry));
    __asm__ volatile ("movq %%r15, %0" : "=r"(arg));

    /* Enable interrupts — new tasks start with IF=0 from context restore */
    __asm__ volatile ("sti");

    /* Run the task function */
    if (entry) {
        entry(arg);
    }

    /* Task returned — mark dead and yield */
    sched_exit(0);
}

/* ── Find next task to run (round-robin with priority) ────────────────── */

static int _pick_next(void) {
    /* Scan from highest priority to lowest.
       Within each priority, round-robin starting after current_tid. */
    for (int prio = SCHED_NUM_PRIOS - 1; prio >= 0; prio--) {
        for (int i = 1; i <= SCHED_MAX_TASKS; i++) {
            int idx = (current_tid + i) % SCHED_MAX_TASKS;
            if (tasks[idx].state == TASK_READY && tasks[idx].priority == (uint8_t)prio) {
                return idx;
            }
        }
    }
    /* Nothing ready — return idle task (tid 0) if it's ready */
    if (tasks[0].state == TASK_READY || tasks[0].state == TASK_RUNNING) {
        return 0;
    }
    return current_tid;  /* keep running current */
}

/* ── Internal switch ──────────────────────────────────────────────────── */

static void _switch_to(int next_tid) {
    if (next_tid == current_tid) return;
    if (next_tid < 0 || next_tid >= SCHED_MAX_TASKS) return;

    int old_tid = current_tid;
    SchedTask *old_task = &tasks[old_tid];
    SchedTask *new_task = &tasks[next_tid];

    /* Transition states */
    if (old_task->state == TASK_RUNNING) {
        old_task->state = TASK_READY;
    }
    new_task->state = TASK_RUNNING;
    new_task->timeslice = SCHED_TIMESLICE;
    new_task->switches++;
    current_tid = next_tid;
    total_switches++;

    /* Context switch */
    _context_switch(&old_task->rsp, new_task->rsp);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

/* ── Idle task — just halts until next interrupt ──────────────────────── */

static void _idle_task(void *arg) {
    (void)arg;
    while (1) {
        __asm__ volatile ("hlt");
    }
}

void sched_init(void) {
    /* Clear all task slots */
    for (int i = 0; i < SCHED_MAX_TASKS; i++) {
        tasks[i].state = TASK_FREE;
        tasks[i].tid   = (uint16_t)i;
    }
    current_tid = -1;
    total_switches = 0;

    /* Create idle task (tid 0) — it runs in the current kernel context
       so we don't allocate a separate stack for it.  The kernel main
       loop effectively *is* the idle task. */
    _scpy(tasks[0].name, "idle", 32);
    tasks[0].tid          = 0;
    tasks[0].state        = TASK_RUNNING;
    tasks[0].priority     = PRIO_IDLE;
    tasks[0].parent_tid   = -1;
    tasks[0].wait_tid     = -1;
    tasks[0].vfs_task_id  = -1;
    tasks[0].rsp          = 0;  /* will be filled on first switch-away */
    tasks[0].stack_base   = 0;  /* uses kernel stack */
    tasks[0].timeslice    = SCHED_TIMESLICE;
    tasks[0].total_ticks  = 0;
    tasks[0].wake_tick    = 0;
    tasks[0].exit_code    = 0;
    tasks[0].created_tick = tick_count;
    tasks[0].switches     = 0;
    tasks[0].sig_pending  = 0;
    tasks[0].sig_blocked  = 0;
    for (int i = 0; i < SIG_MAX; i++) tasks[0].sig_handlers[i] = SIG_DFL;
    current_tid = 0;
    sched_ready = 1;

    serial_puts("[sched] initialized, idle task (tid 0) running\n");
}

int sched_create(const char *name, TaskEntry entry, void *arg,
                 uint8_t priority) {
    if (!sched_ready) return -1;
    if (priority >= SCHED_NUM_PRIOS) priority = PRIO_NORMAL;

    /* Find free slot (skip 0 = idle) */
    int tid = -1;
    for (int i = 1; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state == TASK_FREE) { tid = i; break; }
    }
    if (tid < 0) {
        serial_puts("[sched] no free task slots\n");
        return -1;
    }

    /* Allocate stack */
    uint8_t *stack = (uint8_t *)kmalloc(SCHED_STACK_SIZE);
    if (!stack) {
        serial_puts("[sched] stack allocation failed\n");
        return -1;
    }

    /* Stack grows downward — start at top */
    uint64_t *sp = (uint64_t *)(stack + SCHED_STACK_SIZE);

    /* Build initial context frame (what _context_switch will pop):
       pushfq  → rflags (IF=1 so interrupts enabled)
       pushq rbp → 0
       pushq rbx → 0
       pushq r12 → 0
       pushq r13 → 0
       pushq r14 → entry function pointer
       pushq r15 → arg pointer

       Then the 'ret' from context_switch returns to _task_bootstrap.
       Push the return address first (bottom of frame). */

    /* Return address for the initial 'ret' after context restore */
    *(--sp) = (uint64_t)_task_bootstrap;

    /* RFLAGS with IF=1 (bit 9) and reserved bit 1 set */
    *(--sp) = 0x202;

    /* RBP */
    *(--sp) = 0;

    /* RBX */
    *(--sp) = 0;

    /* R12 */
    *(--sp) = 0;

    /* R13 */
    *(--sp) = 0;

    /* R14 = entry function pointer */
    *(--sp) = (uint64_t)entry;

    /* R15 = arg pointer */
    *(--sp) = (uint64_t)arg;

    /* Fill task descriptor */
    _scpy(tasks[tid].name, name, 32);
    tasks[tid].tid          = (uint16_t)tid;
    tasks[tid].state        = TASK_READY;
    tasks[tid].priority     = priority;
    tasks[tid].parent_tid   = (int16_t)current_tid;
    tasks[tid].wait_tid     = -1;
    tasks[tid].vfs_task_id  = -1;
    tasks[tid].rsp          = (uint64_t)sp;
    tasks[tid].stack_base   = stack;
    tasks[tid].timeslice    = SCHED_TIMESLICE;
    tasks[tid].total_ticks  = 0;
    tasks[tid].wake_tick    = 0;
    tasks[tid].exit_code    = 0;
    tasks[tid].created_tick = tick_count;
    tasks[tid].switches     = 0;
    tasks[tid].sig_pending  = 0;
    tasks[tid].sig_blocked  = 0;
    for (int s = 0; s < SIG_MAX; s++) tasks[tid].sig_handlers[s] = SIG_DFL;

    char msg[64] = "[sched] created '";
    _scat(msg, name);
    _scat(msg, "' tid=");
    char num[8]; _sitoa(tid, num);
    _scat(msg, num);
    _scat(msg, " prio=");
    _sitoa(priority, num);
    _scat(msg, num);
    _scat(msg, "\n");
    serial_puts(msg);

    return tid;
}

void sched_yield(void) {
    if (!sched_ready || current_tid < 0) return;

    /* Reset timeslice and pick next */
    tasks[current_tid].timeslice = 0;
    int next = _pick_next();
    if (next != current_tid) {
        _switch_to(next);
    }
}

void sched_sleep(uint32_t ms) {
    if (!sched_ready || current_tid < 0) return;

    tasks[current_tid].state = TASK_SLEEPING;
    tasks[current_tid].wake_tick = tick_count + ms;

    int next = _pick_next();
    _switch_to(next);
}

void sched_exit(int32_t code) {
    if (current_tid <= 0) {
        /* Can't exit the idle task — just halt */
        while (1) __asm__ volatile ("hlt");
    }

    tasks[current_tid].state     = TASK_DEAD;
    tasks[current_tid].exit_code = code;

    /* Unblock parent if it's waiting on us */
    int16_t ptid = tasks[current_tid].parent_tid;
    if (ptid >= 0 && ptid < SCHED_MAX_TASKS) {
        if (tasks[ptid].state == TASK_BLOCKED &&
            tasks[ptid].wait_tid == (int16_t)current_tid) {
            tasks[ptid].wait_tid = -1;
            tasks[ptid].state = TASK_READY;
        }
    }

    char msg[64] = "[sched] task '";
    _scat(msg, tasks[current_tid].name);
    _scat(msg, "' exited (");
    char num[12]; _sitoa(code < 0 ? (uint64_t)(-(int64_t)code) : (uint64_t)code, num);
    if (code < 0) { char tmp[16] = "-"; _scat(tmp, num); _scpy(num, tmp, 12); }
    _scat(msg, num);
    _scat(msg, ")\n");
    serial_puts(msg);

    /* Switch away — never returns */
    int next = _pick_next();
    _switch_to(next);

    /* Should never reach here */
    while (1) __asm__ volatile ("hlt");
}

void sched_tick(void) {
    if (!sched_ready || current_tid < 0) return;

    /* Accumulate runtime */
    tasks[current_tid].total_ticks++;

    /* Wake sleeping tasks */
    for (int i = 0; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state == TASK_SLEEPING && tick_count >= tasks[i].wake_tick) {
            tasks[i].state = TASK_READY;
        }
    }

    /* Periodically reap dead tasks (every ~1 second) */
    if ((tick_count & 0x3FF) == 0) {
        sched_reap();
    }

    /* Sample load average every 5 seconds (5000 ticks @ 1000 Hz) */
    if (tick_count >= load_last_sample_tick + 5000) {
        load_last_sample_tick = tick_count;
        sched_load_sample();
    }

    /* Deliver pending signals to the current task */
    if (tasks[current_tid].sig_pending & ~tasks[current_tid].sig_blocked) {
        sched_deliver_signals(current_tid);
    }

    /* Decrement timeslice */
    if (tasks[current_tid].timeslice > 0) {
        tasks[current_tid].timeslice--;
    }

    /* Preempt if timeslice expired (but not idle — let it keep running
       if nothing else is ready) */
    if (tasks[current_tid].timeslice == 0) {
        tasks[current_tid].timeslice = SCHED_TIMESLICE;
        int next = _pick_next();
        if (next != current_tid) {
            _switch_to(next);
        }
    }
}

int sched_current_tid(void) {
    return current_tid;
}

void sched_stats(int *ready, int *blocked, int *sleeping, int *total) {
    int r = 0, b = 0, s = 0, t = 0;
    for (int i = 0; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state == TASK_FREE || tasks[i].state == TASK_DEAD) continue;
        t++;
        if (tasks[i].state == TASK_READY || tasks[i].state == TASK_RUNNING) r++;
        if (tasks[i].state == TASK_BLOCKED) b++;
        if (tasks[i].state == TASK_SLEEPING) s++;
    }
    if (ready)    *ready    = r;
    if (blocked)  *blocked  = b;
    if (sleeping) *sleeping = s;
    if (total)    *total    = t;
}

void sched_block(int tid) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return;
    if (tasks[tid].state == TASK_READY || tasks[tid].state == TASK_RUNNING) {
        tasks[tid].state = TASK_BLOCKED;
        if (tid == current_tid) {
            int next = _pick_next();
            _switch_to(next);
        }
    }
}

void sched_unblock(int tid) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return;
    if (tasks[tid].state == TASK_BLOCKED) {
        tasks[tid].state = TASK_READY;
    }
}

void sched_list(void) {
    serial_puts("[sched] Task list:\n");
    serial_puts("  TID  Name                    State     Prio  Switches\n");
    serial_puts("  ───  ──────────────────────  ────────  ────  ────────\n");

    const char *state_names[] = {"FREE", "READY", "RUNNING", "BLOCKED", "SLEEPING", "DEAD"};

    for (int i = 0; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state == TASK_FREE) continue;

        char line[128] = "  ";
        char num[12];

        _sitoa(i, num);
        _scat(line, num);
        /* pad to col 7 */
        int pad = 7 - 2 - _slen(num);
        while (pad-- > 0) _scat(line, " ");

        _scat(line, tasks[i].name);
        pad = 24 - _slen(tasks[i].name);
        while (pad-- > 0) _scat(line, " ");

        int st = tasks[i].state;
        if (st >= 0 && st <= 5) _scat(line, state_names[st]);
        pad = 10 - _slen(state_names[st]);
        while (pad-- > 0) _scat(line, " ");

        _sitoa(tasks[i].priority, num);
        _scat(line, num);
        pad = 6 - _slen(num);
        while (pad-- > 0) _scat(line, " ");

        _sitoa(tasks[i].switches, num);
        _scat(line, num);

        _scat(line, "\n");
        serial_puts(line);
    }

    char total_msg[64] = "[sched] total context switches: ";
    char num[16]; _sitoa(total_switches, num);
    _scat(total_msg, num);
    _scat(total_msg, "\n");
    serial_puts(total_msg);
}

int sched_kill(int tid) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return -1;
    if (tasks[tid].state == TASK_FREE || tasks[tid].state == TASK_DEAD) return -1;
    if (tid == 0) return -1;  /* never kill the idle task */

    tasks[tid].state = TASK_DEAD;
    tasks[tid].exit_code = -9;  /* killed */

    /* Unblock parent if waiting on this task */
    int16_t ptid = tasks[tid].parent_tid;
    if (ptid >= 0 && ptid < SCHED_MAX_TASKS) {
        if (tasks[ptid].state == TASK_BLOCKED &&
            tasks[ptid].wait_tid == (int16_t)tid) {
            tasks[ptid].wait_tid = -1;
            tasks[ptid].state = TASK_READY;
        }
    }

    serial_puts("[sched] killed task ");
    char num[12]; _sitoa(tid, num);
    serial_puts(num);
    serial_puts(" (");
    serial_puts(tasks[tid].name);
    serial_puts(")\n");

    /* If we just killed the running task, switch away */
    if (tid == current_tid) {
        int next = _pick_next();
        _switch_to(next);
    }
    return 0;
}

/* ── Wait for child task to exit ──────────────────────────────────────── */

int sched_wait(int child_tid) {
    if (!sched_ready || current_tid < 0) return -1;
    if (child_tid < 0 || child_tid >= SCHED_MAX_TASKS) return -1;
    if (tasks[child_tid].state == TASK_FREE) return -1;

    /* Verify parent-child relationship */
    if (tasks[child_tid].parent_tid != (int16_t)current_tid) return -1;

    /* If child already dead, return its exit code immediately */
    if (tasks[child_tid].state == TASK_DEAD) {
        int32_t code = tasks[child_tid].exit_code;
        /* Reap: free its stack and slot */
        if (tasks[child_tid].stack_base) {
            kfree(tasks[child_tid].stack_base);
            tasks[child_tid].stack_base = 0;
        }
        tasks[child_tid].state = TASK_FREE;
        return code;
    }

    /* Block ourselves until child exits */
    tasks[current_tid].wait_tid = (int16_t)child_tid;
    tasks[current_tid].state = TASK_BLOCKED;

    int next = _pick_next();
    _switch_to(next);

    /* We've been unblocked — child is now DEAD */
    int32_t code = tasks[child_tid].exit_code;

    /* Reap the child */
    if (tasks[child_tid].stack_base) {
        kfree(tasks[child_tid].stack_base);
        tasks[child_tid].stack_base = 0;
    }
    tasks[child_tid].state = TASK_FREE;

    return code;
}

/* ── Reap dead tasks whose parent is not waiting ──────────────────────── */

void sched_reap(void) {
    for (int i = 1; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state != TASK_DEAD) continue;

        /* Check if a parent is actively waiting on this task */
        int16_t ptid = tasks[i].parent_tid;
        if (ptid >= 0 && ptid < SCHED_MAX_TASKS &&
            tasks[ptid].state != TASK_FREE &&
            tasks[ptid].state != TASK_DEAD &&
            tasks[ptid].wait_tid == (int16_t)i) {
            /* Parent is waiting — don't reap yet, let sched_wait() handle it */
            continue;
        }

        /* No one is waiting — reclaim resources */
        if (tasks[i].stack_base) {
            kfree(tasks[i].stack_base);
            tasks[i].stack_base = 0;
        }
        tasks[i].state = TASK_FREE;
    }
}

/* ── Get task info ────────────────────────────────────────────────────── */

const SchedTask *sched_get_task(int tid) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return 0;
    if (tasks[tid].state == TASK_FREE) return 0;
    return &tasks[tid];
}

/* ═══════════════════════════════════════════════════════════════════════
 * Signal delivery
 * ═══════════════════════════════════════════════════════════════════════ */

/* Names for debug output */
static const char *sig_names[] = {
    "NONE", "TERM", "KILL", "INT", "STOP", "CONT",
    "USR1", "USR2", "ALARM", "CHILD"
};

int sched_signal(int tid, int signum) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return -1;
    if (tasks[tid].state == TASK_FREE || tasks[tid].state == TASK_DEAD) return -1;
    if (signum < 0 || signum >= SIG_MAX) return -1;

    /* SIG_KILL: immediate termination, cannot be caught or blocked */
    if (signum == SIG_KILL) {
        serial_puts("[signal] SIG_KILL -> tid ");
        char num[8]; _sitoa(tid, num); serial_puts(num);
        serial_puts("\n");
        return sched_kill(tid);
    }

    /* SIG_STOP: pause the task */
    if (signum == SIG_STOP) {
        if (tasks[tid].state == TASK_RUNNING || tasks[tid].state == TASK_READY) {
            tasks[tid].state = TASK_BLOCKED;
            serial_puts("[signal] SIG_STOP -> tid ");
            char num[8]; _sitoa(tid, num); serial_puts(num);
            serial_puts(" (blocked)\n");
        }
        return 0;
    }

    /* SIG_CONT: resume a stopped task */
    if (signum == SIG_CONT) {
        if (tasks[tid].state == TASK_BLOCKED) {
            tasks[tid].state = TASK_READY;
            serial_puts("[signal] SIG_CONT -> tid ");
            char num[8]; _sitoa(tid, num); serial_puts(num);
            serial_puts(" (resumed)\n");
        }
        return 0;
    }

    /* Set the signal bit pending */
    tasks[tid].sig_pending |= (1u << signum);

    serial_puts("[signal] ");
    if (signum < SIG_MAX) serial_puts(sig_names[signum]);
    serial_puts(" -> tid ");
    char num[8]; _sitoa(tid, num); serial_puts(num);
    serial_puts(" (pending)\n");

    /* If the task is sleeping and signal is not blocked, wake it */
    if (tasks[tid].state == TASK_SLEEPING &&
        !(tasks[tid].sig_blocked & (1u << signum))) {
        tasks[tid].state = TASK_READY;
    }

    return 0;
}

SignalHandler sched_sigaction(int signum, SignalHandler handler) {
    if (signum <= 0 || signum >= SIG_MAX) return SIG_DFL;
    if (signum == SIG_KILL || signum == SIG_STOP) return SIG_DFL; /* can't override */

    SignalHandler prev = tasks[current_tid].sig_handlers[signum];
    tasks[current_tid].sig_handlers[signum] = handler;
    return prev;
}

void sched_sigmask_block(uint16_t mask) {
    /* Can't block KILL or STOP */
    mask &= ~((1u << SIG_KILL) | (1u << SIG_STOP));
    tasks[current_tid].sig_blocked |= mask;
}

void sched_sigmask_unblock(uint16_t mask) {
    tasks[current_tid].sig_blocked &= ~mask;

    /* Check if any now-unblocked signals are pending */
    uint16_t deliverable = tasks[current_tid].sig_pending & ~tasks[current_tid].sig_blocked;
    if (deliverable) {
        sched_deliver_signals(current_tid);
    }
}

void sched_deliver_signals(int tid) {
    if (tid < 0 || tid >= SCHED_MAX_TASKS) return;
    if (tasks[tid].state == TASK_FREE || tasks[tid].state == TASK_DEAD) return;

    uint16_t deliverable = tasks[tid].sig_pending & ~tasks[tid].sig_blocked;
    if (!deliverable) return;

    for (int sig = 1; sig < SIG_MAX; sig++) {
        if (!(deliverable & (1u << sig))) continue;

        /* Clear the pending bit */
        tasks[tid].sig_pending &= ~(1u << sig);

        SignalHandler handler = tasks[tid].sig_handlers[sig];

        if (handler == SIG_IGN) {
            /* Ignored */
            continue;
        }

        if (handler == SIG_DFL) {
            /* Default action based on signal type */
            switch (sig) {
                case SIG_TERM:
                case SIG_INT:
                    /* Default: terminate the task */
                    serial_puts("[signal] default TERM for tid ");
                    { char num[8]; _sitoa(tid, num); serial_puts(num); }
                    serial_puts("\n");
                    if (tid == current_tid) {
                        sched_exit(128 + sig);
                    } else {
                        sched_kill(tid);
                    }
                    return;  /* task is gone */

                case SIG_ALARM:
                case SIG_USR1:
                case SIG_USR2:
                case SIG_CHILD:
                    /* Default: ignore */
                    break;

                default:
                    break;
            }
            continue;
        }

        /* User handler — call it */
        serial_puts("[signal] delivering ");
        if (sig < SIG_MAX) serial_puts(sig_names[sig]);
        serial_puts(" to tid ");
        { char num[8]; _sitoa(tid, num); serial_puts(num); }
        serial_puts(" (handler)\n");

        handler(sig);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Load Average Tracking
 *
 * We sample the runnable task count every 5 seconds and compute
 * exponentially weighted moving averages for 1/5/15 minute windows.
 * All values are fixed-point ×100 (e.g. 150 means load 1.50).
 *
 * EMA formula:  avg = avg + (sample - avg) * alpha
 * alpha_1m  ≈ 1 - e^(-5/60)   ≈ 0.08 → 8/100
 * alpha_5m  ≈ 1 - e^(-5/300)  ≈ 0.017 → 2/100
 * alpha_15m ≈ 1 - e^(-5/900)  ≈ 0.006 → 1/100
 * ═══════════════════════════════════════════════════════════════════════ */

void sched_load_sample(void) {
    /* Count runnable tasks (READY + RUNNING, excluding idle) */
    int runnable = 0;
    for (int i = 1; i < SCHED_MAX_TASKS; i++) {
        if (tasks[i].state == TASK_READY || tasks[i].state == TASK_RUNNING)
            runnable++;
    }

    /* Convert to ×100 fixed-point */
    int sample = runnable * 100;

    /* Exponential weighted moving average */
    load_avg_1  = load_avg_1  + (sample - load_avg_1)  * 8  / 100;
    load_avg_5  = load_avg_5  + (sample - load_avg_5)  * 2  / 100;
    load_avg_15 = load_avg_15 + (sample - load_avg_15) * 1  / 100;
}

void sched_load_avg(int *load1, int *load5, int *load15) {
    if (load1)  *load1  = load_avg_1;
    if (load5)  *load5  = load_avg_5;
    if (load15) *load15 = load_avg_15;
}
