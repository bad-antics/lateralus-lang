/* =======================================================================
 * LateralusOS — IPC Message Queue Implementation
 * =======================================================================
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#include "ipc.h"
#include "sched.h"

/* -- External symbols --------------------------------------------------- */

extern void serial_puts(const char *s);

/* -- Internal queue structure ------------------------------------------- */

typedef struct {
    char        name[32];
    uint8_t     active;
    IpcMessage  ring[IPC_QUEUE_CAPACITY];
    uint16_t    head;             /* read pointer */
    uint16_t    tail;             /* write pointer */
    uint16_t    count;            /* number of messages */

    /* Blocked task lists (simple arrays for now) */
    int         blocked_senders[SCHED_MAX_TASKS];
    int         num_blocked_senders;
    int         blocked_receivers[SCHED_MAX_TASKS];
    int         num_blocked_receivers;

    /* Stats */
    uint64_t    total_sent;
    uint64_t    total_received;
} IpcQueueInternal;

static IpcQueueInternal queues[IPC_MAX_QUEUES];
static int ipc_initialized = 0;

/* -- Helpers ------------------------------------------------------------ */

static int _streq(const char *a, const char *b) {
    while (*a && *b) { if (*a != *b) return 0; a++; b++; }
    return *a == *b;
}

static void _icpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static void _icat(char *dst, const char *src) {
    int n = 0; while (dst[n]) n++;
    int i = 0; while (src[i]) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static void _iitoa(uint64_t val, char *buf) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    int pos = 0;
    while (rp > 0) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

static void _mcpy(void *dst, const void *src, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
}

static int _ilen(const char *s) {
    int n = 0; while (s[n]) n++;
    return n;
}

/* =======================================================================
 * Public API
 * ======================================================================= */

void ipc_init(void) {
    for (int i = 0; i < IPC_MAX_QUEUES; i++) {
        queues[i].active = 0;
        queues[i].head   = 0;
        queues[i].tail   = 0;
        queues[i].count  = 0;
        queues[i].num_blocked_senders   = 0;
        queues[i].num_blocked_receivers = 0;
        queues[i].total_sent     = 0;
        queues[i].total_received = 0;
    }
    ipc_initialized = 1;
    serial_puts("[ipc] initialized, 16 queue slots\n");
}

IpcQueue ipc_create(const char *name) {
    if (!ipc_initialized) return IPC_INVALID;

    /* Check for duplicate name */
    for (int i = 0; i < IPC_MAX_QUEUES; i++) {
        if (queues[i].active && _streq(queues[i].name, name)) {
            return i;  /* already exists — return it */
        }
    }

    /* Find free slot */
    for (int i = 0; i < IPC_MAX_QUEUES; i++) {
        if (!queues[i].active) {
            _icpy(queues[i].name, name, 32);
            queues[i].active = 1;
            queues[i].head   = 0;
            queues[i].tail   = 0;
            queues[i].count  = 0;
            queues[i].num_blocked_senders   = 0;
            queues[i].num_blocked_receivers = 0;
            queues[i].total_sent     = 0;
            queues[i].total_received = 0;

            char msg[64] = "[ipc] created queue '";
            _icat(msg, name);
            _icat(msg, "' (id=");
            char num[8]; _iitoa(i, num);
            _icat(msg, num);
            _icat(msg, ")\n");
            serial_puts(msg);
            return i;
        }
    }

    serial_puts("[ipc] no free queue slots\n");
    return IPC_INVALID;
}

IpcQueue ipc_find(const char *name) {
    for (int i = 0; i < IPC_MAX_QUEUES; i++) {
        if (queues[i].active && _streq(queues[i].name, name)) {
            return i;
        }
    }
    return IPC_INVALID;
}

void ipc_destroy(IpcQueue q) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return;

    /* Wake all blocked tasks */
    for (int i = 0; i < queues[q].num_blocked_senders; i++) {
        sched_unblock(queues[q].blocked_senders[i]);
    }
    for (int i = 0; i < queues[q].num_blocked_receivers; i++) {
        sched_unblock(queues[q].blocked_receivers[i]);
    }

    queues[q].active = 0;
    serial_puts("[ipc] destroyed queue '");
    serial_puts(queues[q].name);
    serial_puts("'\n");
}

/* -- Internal enqueue/dequeue ------------------------------------------- */

static int _enqueue(IpcQueue q, uint16_t type, const void *data, uint16_t len) {
    IpcQueueInternal *queue = &queues[q];
    if (queue->count >= IPC_QUEUE_CAPACITY) return -1;
    if (len > IPC_MSG_MAX_SIZE) len = IPC_MSG_MAX_SIZE;

    IpcMessage *msg = &queue->ring[queue->tail];
    msg->sender_tid = (uint16_t)sched_current_tid();
    msg->type   = type;
    msg->length = len;
    if (data && len > 0) {
        _mcpy(msg->payload, data, len);
    }

    queue->tail = (queue->tail + 1) % IPC_QUEUE_CAPACITY;
    queue->count++;
    queue->total_sent++;

    /* Wake one blocked receiver */
    if (queue->num_blocked_receivers > 0) {
        queue->num_blocked_receivers--;
        int tid = queue->blocked_receivers[queue->num_blocked_receivers];
        sched_unblock(tid);
    }

    return 0;
}

static int _dequeue(IpcQueue q, IpcMessage *out) {
    IpcQueueInternal *queue = &queues[q];
    if (queue->count == 0) return -1;

    _mcpy(out, &queue->ring[queue->head], sizeof(IpcMessage));
    queue->head = (queue->head + 1) % IPC_QUEUE_CAPACITY;
    queue->count--;
    queue->total_received++;

    /* Wake one blocked sender */
    if (queue->num_blocked_senders > 0) {
        queue->num_blocked_senders--;
        int tid = queue->blocked_senders[queue->num_blocked_senders];
        sched_unblock(tid);
    }

    return 0;
}

/* -- Blocking send ------------------------------------------------------ */

int ipc_send(IpcQueue q, uint16_t type, const void *data, uint16_t len) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return -1;

    while (queues[q].count >= IPC_QUEUE_CAPACITY) {
        /* Queue full — block sender */
        int tid = sched_current_tid();
        if (queues[q].num_blocked_senders < SCHED_MAX_TASKS) {
            queues[q].blocked_senders[queues[q].num_blocked_senders++] = tid;
        }
        sched_block(tid);

        /* Woken up — check if queue was destroyed */
        if (!queues[q].active) return -1;
    }

    return _enqueue(q, type, data, len);
}

/* -- Non-blocking send -------------------------------------------------- */

int ipc_try_send(IpcQueue q, uint16_t type, const void *data, uint16_t len) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return -1;
    if (queues[q].count >= IPC_QUEUE_CAPACITY) return -1;
    return _enqueue(q, type, data, len);
}

/* -- Blocking receive --------------------------------------------------- */

int ipc_recv(IpcQueue q, IpcMessage *out) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return -1;

    while (queues[q].count == 0) {
        /* Queue empty — block receiver */
        int tid = sched_current_tid();
        if (queues[q].num_blocked_receivers < SCHED_MAX_TASKS) {
            queues[q].blocked_receivers[queues[q].num_blocked_receivers++] = tid;
        }
        sched_block(tid);

        /* Woken up — check if queue was destroyed */
        if (!queues[q].active) return -1;
    }

    return _dequeue(q, out);
}

/* -- Non-blocking receive ----------------------------------------------- */

int ipc_try_recv(IpcQueue q, IpcMessage *out) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return -1;
    if (queues[q].count == 0) return -1;
    return _dequeue(q, out);
}

/* -- Peek --------------------------------------------------------------- */

int ipc_peek(IpcQueue q, IpcMessage *out) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return -1;
    if (queues[q].count == 0) return -1;
    _mcpy(out, &queues[q].ring[queues[q].head], sizeof(IpcMessage));
    return 0;
}

/* -- Pending count ------------------------------------------------------ */

int ipc_pending(IpcQueue q) {
    if (q < 0 || q >= IPC_MAX_QUEUES || !queues[q].active) return 0;
    return queues[q].count;
}

/* -- List queues -------------------------------------------------------- */

void ipc_list(void) {
    serial_puts("[ipc] Queue list:\n");
    serial_puts("  ID  Name                    Pending  Sent      Received\n");
    serial_puts("  --  ----------------------  -------  --------  --------\n");

    for (int i = 0; i < IPC_MAX_QUEUES; i++) {
        if (!queues[i].active) continue;

        char line[128] = "  ";
        char num[16];

        _iitoa(i, num);
        _icat(line, num);
        int pad = 6 - 2 - _ilen(num);
        while (pad-- > 0) _icat(line, " ");

        _icat(line, queues[i].name);
        pad = 24 - _ilen(queues[i].name);
        while (pad-- > 0) _icat(line, " ");

        _iitoa(queues[i].count, num);
        _icat(line, num);
        pad = 9 - _ilen(num);
        while (pad-- > 0) _icat(line, " ");

        _iitoa(queues[i].total_sent, num);
        _icat(line, num);
        pad = 10 - _ilen(num);
        while (pad-- > 0) _icat(line, " ");

        _iitoa(queues[i].total_received, num);
        _icat(line, num);

        _icat(line, "\n");
        serial_puts(line);
    }
}
