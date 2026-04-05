/* =======================================================================
 * LateralusOS — Cooperative Task Scheduler Implementation
 * =======================================================================
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#include "tasks.h"

/* -- Static task pool --------------------------------------------------- */

static Task task_pool[MAX_TASKS];
static int  task_count = 0;

/* -- Tiny helpers ------------------------------------------------------- */

static int _tlen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void _tcpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static void _tcat(char *dst, const char *src, int max) {
    int n = _tlen(dst);
    int i = 0;
    while (src[i] && n + i < max - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static void _titoa(uint64_t val, char *buf, int buflen) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    int pos = 0;
    while (rp > 0 && pos < buflen - 1) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

/* -- Initialize --------------------------------------------------------- */

void tasks_init(void) {
    for (int i = 0; i < MAX_TASKS; i++) {
        task_pool[i].active = 0;
    }
    task_count = 0;
}

/* -- Create periodic task ----------------------------------------------- */

int task_create(const char *name, TaskFn fn, void *data,
                uint32_t interval_ms) {
    for (int i = 0; i < MAX_TASKS; i++) {
        if (!task_pool[i].active) {
            _tcpy(task_pool[i].name, name, 32);
            task_pool[i].fn        = fn;
            task_pool[i].data      = data;
            task_pool[i].interval  = interval_ms;
            task_pool[i].next_run  = 0;  /* run immediately on first tick */
            task_pool[i].active    = 1;
            task_pool[i].oneshot   = 0;
            task_pool[i].run_count = 0;
            task_pool[i].last_run  = 0;
            task_count++;
            return i;
        }
    }
    return -1;
}

/* -- Create one-shot task ----------------------------------------------- */

int task_create_oneshot(const char *name, TaskFn fn, void *data,
                         uint32_t delay_ms, uint64_t current_tick) {
    for (int i = 0; i < MAX_TASKS; i++) {
        if (!task_pool[i].active) {
            _tcpy(task_pool[i].name, name, 32);
            task_pool[i].fn        = fn;
            task_pool[i].data      = data;
            task_pool[i].interval  = 0;
            task_pool[i].next_run  = current_tick + delay_ms;
            task_pool[i].active    = 1;
            task_pool[i].oneshot   = 1;
            task_pool[i].run_count = 0;
            task_pool[i].last_run  = 0;
            task_count++;
            return i;
        }
    }
    return -1;
}

/* -- Remove task -------------------------------------------------------- */

void task_remove(int id) {
    if (id < 0 || id >= MAX_TASKS) return;
    if (task_pool[id].active) {
        task_pool[id].active = 0;
        task_count--;
    }
}

/* -- Tick — run all due tasks ------------------------------------------- */

void tasks_tick(uint64_t current_tick) {
    for (int i = 0; i < MAX_TASKS; i++) {
        if (!task_pool[i].active) continue;
        if (current_tick < task_pool[i].next_run) continue;

        /* Run the task */
        if (task_pool[i].fn) {
            task_pool[i].fn(task_pool[i].data);
        }

        task_pool[i].run_count++;
        task_pool[i].last_run = current_tick;

        if (task_pool[i].oneshot) {
            task_pool[i].active = 0;
            task_count--;
        } else {
            task_pool[i].next_run = current_tick + task_pool[i].interval;
        }
    }
}

/* -- Active count ------------------------------------------------------- */

int tasks_active_count(void) {
    return task_count;
}

/* -- List tasks --------------------------------------------------------- */

void tasks_list(char *buf, uint32_t buflen) {
    buf[0] = 0;
    char num[24];

    _tcat(buf, "ID  Name                    Interval  Runs\n", (int)buflen);
    _tcat(buf, "--  ----------------------  --------  ----\n", (int)buflen);

    for (int i = 0; i < MAX_TASKS; i++) {
        if (!task_pool[i].active) continue;

        _titoa((uint64_t)i, num, 24);
        _tcat(buf, num, (int)buflen);
        /* Pad to column 4 */
        int pad = 4 - _tlen(num);
        while (pad-- > 0) _tcat(buf, " ", (int)buflen);

        _tcat(buf, task_pool[i].name, (int)buflen);
        /* Pad to column 28 */
        pad = 28 - 4 - _tlen(task_pool[i].name);
        while (pad-- > 0) _tcat(buf, " ", (int)buflen);

        _titoa(task_pool[i].interval, num, 24);
        _tcat(buf, num, (int)buflen);
        _tcat(buf, "ms", (int)buflen);
        pad = 10 - _tlen(num) - 2;
        while (pad-- > 0) _tcat(buf, " ", (int)buflen);

        _titoa(task_pool[i].run_count, num, 24);
        _tcat(buf, num, (int)buflen);
        _tcat(buf, "\n", (int)buflen);
    }
}
