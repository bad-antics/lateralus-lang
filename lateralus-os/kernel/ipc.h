/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Inter-Process Communication (IPC)
 * ═══════════════════════════════════════════════════════════════════════
 * Kernel message queues for task-to-task communication.  Each queue is
 * a bounded ring buffer of fixed-size messages.
 *
 * Features:
 *   - Up to 16 named message queues
 *   - Blocking send (waits if full) / blocking recv (waits if empty)
 *   - Non-blocking try_send / try_recv
 *   - Task wakeup on send/recv via scheduler block/unblock
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_IPC_H
#define LATERALUS_IPC_H

#include "../gui/types.h"

/* ── Limits ───────────────────────────────────────────────────────────── */

#define IPC_MAX_QUEUES     16
#define IPC_QUEUE_CAPACITY 32
#define IPC_MSG_MAX_SIZE   256     /* max payload bytes per message */

/* ── Message ──────────────────────────────────────────────────────────── */

typedef struct {
    uint16_t sender_tid;          /* sender task ID */
    uint16_t type;                /* user-defined message type tag */
    uint16_t length;              /* payload length in bytes */
    uint8_t  payload[IPC_MSG_MAX_SIZE];
} IpcMessage;

/* ── Queue handle ─────────────────────────────────────────────────────── */

typedef int IpcQueue;             /* opaque handle (index into pool) */

#define IPC_INVALID  (-1)

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialize the IPC subsystem */
void ipc_init(void);

/* Create a named message queue.
   Returns queue handle (>= 0) or IPC_INVALID on failure. */
IpcQueue ipc_create(const char *name);

/* Find an existing queue by name.
   Returns queue handle or IPC_INVALID if not found. */
IpcQueue ipc_find(const char *name);

/* Destroy a queue, waking any blocked tasks. */
void ipc_destroy(IpcQueue q);

/* Blocking send — blocks if queue is full.
   Returns 0 on success, -1 on error (queue destroyed). */
int ipc_send(IpcQueue q, uint16_t type, const void *data, uint16_t len);

/* Non-blocking send. Returns 0 on success, -1 if full or error. */
int ipc_try_send(IpcQueue q, uint16_t type, const void *data, uint16_t len);

/* Blocking receive — blocks if queue is empty.
   Copies message into `out`. Returns 0 on success, -1 on error. */
int ipc_recv(IpcQueue q, IpcMessage *out);

/* Non-blocking receive. Returns 0 on success, -1 if empty. */
int ipc_try_recv(IpcQueue q, IpcMessage *out);

/* Peek at head message without removing. Returns 0 on success, -1 if empty. */
int ipc_peek(IpcQueue q, IpcMessage *out);

/* Get number of pending messages in queue. */
int ipc_pending(IpcQueue q);

/* Print IPC stats to serial. */
void ipc_list(void);

#endif /* LATERALUS_IPC_H */
