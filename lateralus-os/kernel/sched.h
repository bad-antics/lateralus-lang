/* =======================================================================
 * LateralusOS — Preemptive Task Scheduler
 * =======================================================================
 * Round-robin preemptive scheduler with 4 priority levels.  Each task
 * gets its own kernel stack and a saved register context.  The PIT timer
 * (IRQ0, 1 kHz) drives preemption via sched_tick().
 *
 * Priority levels:
 *   0 = IDLE       — runs only when nothing else is ready
 *   1 = NORMAL     — default for user tasks
 *   2 = HIGH       — I/O handlers, drivers
 *   3 = REALTIME   — interrupt-level work, never starved
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_SCHED_H
#define LATERALUS_SCHED_H

#include "../gui/types.h"

/* -- Limits ------------------------------------------------------------- */

#define SCHED_MAX_TASKS    32
#define SCHED_STACK_SIZE   16384   /* 16 KB per task stack */
#define SCHED_NUM_PRIOS    4
#define SCHED_TIMESLICE    10      /* ticks per time slice (10 ms @ 1 kHz) */

/* -- Task states -------------------------------------------------------- */

#define TASK_FREE       0
#define TASK_READY      1
#define TASK_RUNNING    2
#define TASK_BLOCKED    3
#define TASK_SLEEPING   4
#define TASK_DEAD       5

/* -- Priority levels ---------------------------------------------------- */

#define PRIO_IDLE       0
#define PRIO_NORMAL     1
#define PRIO_HIGH       2
#define PRIO_REALTIME   3

/* -- Signals ------------------------------------------------------------ */

#define SIG_NONE     0   /* no signal */
#define SIG_TERM     1   /* graceful termination */
#define SIG_KILL     2   /* forced kill (cannot be caught) */
#define SIG_INT      3   /* interrupt (Ctrl+C equivalent) */
#define SIG_STOP     4   /* pause/suspend */
#define SIG_CONT     5   /* resume from stop */
#define SIG_USR1     6   /* user-defined 1 */
#define SIG_USR2     7   /* user-defined 2 */
#define SIG_ALARM    8   /* alarm timer fired */
#define SIG_CHILD    9   /* child exited */
#define SIG_MAX     10   /* number of signal types */

/* Signal handler function pointer.
   Handler receives signal number, runs in context of receiving task. */
typedef void (*SignalHandler)(int signum);

/* Default handlers (sentinel values) */
#define SIG_DFL  ((SignalHandler)0)   /* default action (term/ignore) */
#define SIG_IGN  ((SignalHandler)1)   /* ignore signal */

/* -- Saved CPU context (pushed/popped on switch) ------------------------ */

typedef struct {
    uint64_t r15, r14, r13, r12;
    uint64_t rbx, rbp;
    uint64_t rflags;
    uint64_t rip;                 /* return address for switch */
} TaskContext;

/* -- Task entry function ------------------------------------------------ */

typedef void (*TaskEntry)(void *arg);

/* -- Task Control Block ------------------------------------------------- */

typedef struct {
    /* Identification */
    char        name[32];
    uint16_t    tid;              /* task ID (index into pool) */
    uint8_t     state;            /* TASK_FREE / READY / RUNNING / etc */
    uint8_t     priority;         /* 0..3 */

    /* Process relationships */
    int16_t     parent_tid;       /* parent task (who spawned us), -1=none */
    int16_t     wait_tid;         /* child TID we are waiting on, -1=none */
    int16_t     vfs_task_id;      /* VFS fd table slot for this task, -1=none */
    uint8_t     _pad[2];          /* alignment padding */

    /* Scheduling */
    uint64_t    rsp;              /* saved stack pointer */
    uint8_t    *stack_base;       /* bottom of allocated stack */
    uint32_t    timeslice;        /* remaining ticks in current slice */
    uint64_t    total_ticks;      /* total ticks this task has run */

    /* Sleep support */
    uint64_t    wake_tick;        /* tick at which to wake (if SLEEPING) */

    /* Exit */
    int32_t     exit_code;

    /* Signals */
    uint16_t    sig_pending;               /* bitmask of pending signals */
    uint16_t    sig_blocked;               /* bitmask of blocked signals */
    SignalHandler sig_handlers[SIG_MAX];   /* per-signal handlers */

    /* Stats */
    uint64_t    created_tick;
    uint64_t    switches;         /* number of times scheduled in */
} SchedTask;

/* -- Public API --------------------------------------------------------- */

/* Initialize the scheduler and create the idle task.
   Must be called before any task_create(). */
void sched_init(void);

/* Create a new task. Returns tid (0..MAX-1) or -1 on failure. */
int sched_create(const char *name, TaskEntry entry, void *arg,
                 uint8_t priority);

/* Yield the current time slice voluntarily. */
void sched_yield(void);

/* Put the current task to sleep for `ms` milliseconds. */
void sched_sleep(uint32_t ms);

/* Terminate the current task. Does not return. */
void sched_exit(int32_t code) __attribute__((noreturn));

/* Called from PIT IRQ handler every tick (1 kHz).
   Decrements the running task's timeslice and triggers a
   context switch when it reaches zero. */
void sched_tick(void);

/* Get the currently running task's tid. */
int sched_current_tid(void);

/* Get number of tasks in each state. */
void sched_stats(int *ready, int *blocked, int *sleeping, int *total);

/* Print task list to serial. */
void sched_list(void);

/* Block / unblock a task (for IPC wait). */
void sched_block(int tid);
void sched_unblock(int tid);

/* Terminate a task by TID. Returns 0 on success, -1 if not found. */
int sched_kill(int tid);

/* Wait for a child task to exit. Returns exit_code, or -1 on error.
   Blocks the caller until the child enters TASK_DEAD. */
int sched_wait(int child_tid);

/* Reap dead tasks — free their stacks and mark slots FREE.
   Called periodically from sched_tick(). Only reaps tasks whose
   parent is not waiting on them (or who have no parent). */
void sched_reap(void);

/* Get pointer to task struct by tid (NULL if out of range or FREE). */
const SchedTask *sched_get_task(int tid);

/* -- Signals --- */

/* Send a signal to a task. Returns 0 on success, -1 if task not found.
   SIG_KILL cannot be blocked or caught — always terminates. */
int sched_signal(int tid, int signum);

/* Install a signal handler for the current task.
   Returns previous handler, or SIG_DFL on error. */
SignalHandler sched_sigaction(int signum, SignalHandler handler);

/* Block/unblock signals for the current task (bitmask ops). */
void sched_sigmask_block(uint16_t mask);
void sched_sigmask_unblock(uint16_t mask);

/* Deliver pending signals. Called from sched_tick() or after unblock. */
void sched_deliver_signals(int tid);

/* -- Load Average --- */

/* Sample the runnable task count (called every 5s from sched_tick). */
void sched_load_sample(void);

/* Get load averages (fixed-point ×100, e.g. 150 = 1.50).
   load1 = 1-min, load5 = 5-min, load15 = 15-min. */
void sched_load_avg(int *load1, int *load5, int *load15);

#endif /* LATERALUS_SCHED_H */
