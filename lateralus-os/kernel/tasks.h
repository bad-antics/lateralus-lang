/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Cooperative Task Scheduler
 * ═══════════════════════════════════════════════════════════════════════
 * Simple periodic task scheduler — tasks are callback-based and run
 * cooperatively (no preemption, no context switching).
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_TASKS_H
#define LATERALUS_TASKS_H

#include "../gui/types.h"

/* ── Limits ───────────────────────────────────────────────────────────── */

#define MAX_TASKS 16

/* ── Task callback ────────────────────────────────────────────────────── */

typedef void (*TaskFn)(void *data);

/* ── Task descriptor ──────────────────────────────────────────────────── */

typedef struct {
    char     name[32];
    TaskFn   fn;
    void    *data;
    uint32_t interval;    /* ticks between runs (1000 = 1 second) */
    uint64_t next_run;    /* next tick to run */
    uint8_t  active;
    uint8_t  oneshot;     /* 1 = remove after first execution */
    uint64_t run_count;   /* how many times this task has run */
    uint64_t last_run;    /* tick of last execution */
} Task;

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialize the task scheduler */
void tasks_init(void);

/* Create a periodic task. Returns task id (0..MAX_TASKS-1) or -1. */
int task_create(const char *name, TaskFn fn, void *data,
                uint32_t interval_ms);

/* Create a one-shot task (runs once after delay). Returns task id or -1. */
int task_create_oneshot(const char *name, TaskFn fn, void *data,
                         uint32_t delay_ms, uint64_t current_tick);

/* Remove a task by id */
void task_remove(int id);

/* Run all due tasks. Call from timer/main loop at 1kHz. */
void tasks_tick(uint64_t current_tick);

/* Get number of active tasks */
int tasks_active_count(void);

/* List tasks into buffer (human-readable) */
void tasks_list(char *buf, uint32_t buflen);

#endif /* LATERALUS_TASKS_H */
